#
# 1. bash setup.sh
# 2. Get URL or Lambda name
# 3. python3 invoke.py -u https://ockhe03c0i.execute-api.us-west-1.amazonaws.com/latest/membus -c 10    or,
# 3. python3 invoke.py -n membus1536 -c 10  
#

from urllib.parse import urlparse
from threading import Thread,Lock
import http.client, sys
from queue import Queue
import argparse
import json
import csv
import time
import os
from datetime import datetime
import subprocess
import re
import statistics
import random
import copy
import numpy as np


MAX_CONCURRENT = 1500
req_q = Queue(MAX_CONCURRENT * 2)
data_q = Queue(MAX_CONCURRENT * 2)
order_q = Queue(MAX_CONCURRENT * 2)
samples = False

# Endpoint of the covert channel
class ChannelInfo:
    id = None
    sender_id = None
    receiver_id = None
    rate_bps = None
    bits_xmited = None
    sender_erasures = None      # erasures detected on sender
    receiver_erasures = None      # erasures detected on receiver
    sent_data = None
    rcvd_data = None
    error_rate = None

# Find majority elements in a list
def find_majority(arr): 
    max_count = 0
    max_val = 0
    for val in arr: 
        count = 0
        for val2 in arr: 
            if(val == val2): 
                count += 1
        if count > max_count:   
            max_val = val
            max_count = count
        
    return max_val if max_count > len(arr)/2 else None

# Function to calculate hamming distance  
def hammingDistance(n1, n2) : 
    x = n1 ^ n2  
    setBits = 0
    while (x > 0) : 
        setBits += x & 1
        x >>= 1
    return setBits 

# Call URL
def getResponse(ourl, body):
    try:
        url = urlparse(ourl)
        conn = http.client.HTTPSConnection(url.netloc,timeout=500)   
        conn.request("POST", url.path, body)
        res = conn.getresponse()
        return res
    except Exception as e:
        print(e)
        return None

# Invoker for each Lambda instance
responded = {}
last_updated = None
def worker():
    global responded
    global last_updated

    while True:
        (url, id, guid, syncpt, phases, bits_in_id, bit_duration, start_delay, 
        use_s3, s3bucket, s3prefix, tmpdir, aws_profile, retrys3, shared_lock, 
        channel, chrate, chthresh) = req_q.get()

        s3file = guid
        body = { 
            "id": id, 
            "stime": syncpt, 
            "phases": phases, 
            "log": True,   
            "maxbits": bits_in_id, 
            "bitduration": bit_duration,
            "samples": samples, 
            "s3bucket": s3bucket if use_s3 else "", 
            "s3key": s3file if use_s3 else "",
            "guid": guid,
            "channel": channel,
            "repeat_phases": False if channel else True,
            "rate": chrate,
            "threshold": chthresh
        }

        # Invoke lambda (unless this is a follow-up run that just downloads resuts of an earlier experiment)
        if not retrys3: 
            resp = getResponse(url, json.dumps(body))
            order_q.put(id)

        # Wait for the results
        if use_s3:
            S3_FILE_CHECK_TIMEOUT_SECS = 10     # 150 FIXME
            timeout_secs = start_delay + phases*(bits_in_id+1)*bit_duration + S3_FILE_CHECK_TIMEOUT_SECS if not retrys3 else S3_FILE_CHECK_TIMEOUT_SECS
            start = time.time()
            timeout = time.time() + timeout_secs
            found = False

            # Check for S3 file no matter how the API returns. Asychronous calls to API currently 
            # return 500 status (which needs to be fixed) but the lambdas still continue to run.
            # if resp:
            #     if resp.status in (200, 504):
            #         # Returned or timed out, wait for the S3 file
            #         print("Lambda {0} status: ".format(id), resp.status, resp.read())
            #         pass
            #     else:
            #         print("Lambda {0}: Failed. ".format(id), resp.read())
            #         req_q.task_done()
            #         return

            while True:
                # Making s3 command per each thread would hit the AWS quota limits. Instead, make one thread 
                # update the responded lambdas in one call
                S3_QUERY_INTERVAL_SECS = 30
                acquired = shared_lock.acquire(False)
                if acquired:
                    # Doesn't matter who acquires the lock and does the work
                    try:
                        now = time.time()
                        if (last_updated is None) or ((now - last_updated) > S3_QUERY_INTERVAL_SECS):
                            last_updated = now

                            # Query S3 for all responded lambdas               
                            # Set shell to true and pass entire command as a single string for usual shell like environment
                            # which is required to enable default aws 
                            # The command returns IDs of all lambdas that responded (NOTE: Uses awk in shell)
                            command = "aws s3 ls {0}/{1} | awk '{{ print $4 }}' | awk -F'-' '{{ print $5 }}'".format(s3bucket, s3prefix) if aws_profile is None else \
                                        "aws s3 ls {0}/{1} --profile {2} | awk '{{ print $4 }}' | awk -F'-' '{{ print $5 }}'".format(s3bucket, s3prefix, aws_profile)
                            p = subprocess.run([command], stdout=subprocess.PIPE, shell=True)
                            if p.returncode != 0:
                                print("ERROR! Cannot query or parse results from S3 {0}".format(s3bucket))
                                sys.exit(1)

                            # print(p.stdout.split())
                            for id_ in [int(x) for x in p.stdout.split()]:
                                responded[id_] = True
                            # print(responded.keys())
                    finally:
                        shared_lock.release()

                if id in responded:
                    found = True
                    break

                if time.time() > timeout:
                    found = False
                    break

                # WARNING: This print stdout seems necessary for the control to move forward
                time.sleep(1)
                progress = int((time.time() - start) * 50 / timeout_secs)
                sys.stdout.write("\rLambda {0}: Waiting [{1}{2}]".format(id, '#'*progress, '.'*(50-progress)))
                
            if found:
                tmppath = os.path.join(tmpdir, str(id))
                command = "aws s3 cp s3://{0}/{1} {2}".format(s3bucket, s3file, tmppath) if aws_profile is None else \
                            "aws s3 cp s3://{0}/{1} {2} --profile {3}".format(s3bucket, s3file, tmppath, aws_profile)
                p = subprocess.run([command], stdout=subprocess.PIPE, shell=True)
                if p.returncode != 0:
                    print("Lambda {0} failed: Failed to copy file from S3 {1}/{2}".format(id, s3bucket, s3file))
                    req_q.task_done()
                    return
                with open(tmppath, 'r') as f:
                    data_q.put(f.read())
            else:
                print("Lambda {0} failed: Fetching S3 file timed out".format(id, s3bucket, s3file))
                req_q.task_done()
                return
        elif resp and resp.status == 200:
            data = resp.read()
            data_q.put(data)
        else:
            print (resp.status)

        req_q.task_done()


def main():
    parser = argparse.ArgumentParser("Makes concurrent requests to lambda URLs")
    # Exp metadata
    parser.add_argument('-c', '--count', action='store', type=int, help='number of requests to make (max:{0})'.format(MAX_CONCURRENT), default=5)
    parser.add_argument('-od', '--outdir', action='store', help='name of output dir')
    parser.add_argument('-en', '--expname', action='store', help='Custom name for this experiment, defaults to datetime')
    parser.add_argument('-ed', '--expdesc', action='store', help='Description/comments for this run', default="")
    parser.add_argument('-o', '--out', action='store', help='path to results file', default="results.csv")
    parser.add_argument('-u', '--url', action='store', help='url to invoke lambda. Looks in .api_cache by default.')
    parser.add_argument('-p', '--phases', action='store', type=int, help='number of phases to run', default=1)
    parser.add_argument('-i', '--idbits', action='store', type=int, help='number of bits in ID', default=10)
    parser.add_argument('-b', '--bitduration', action='store', type=int, help='time to communicate for each bit in seconds', default=1)
    parser.add_argument('-d', '--delay', action='store', type=int, help='initial delay for lambdas to sync up (in seconds)', default=30)
    parser.add_argument('-n', '--name', action='store', help='lambda name, if URL should be retrieved from cache', default="membusv2")
    parser.add_argument('-s', '--samples', action='store_true', help='save observed latency samples to log', default=False)
    parser.add_argument('-seq', '--sequence', action='store_true', help='invoke lambdas sequentially one after another (requires huge start-up delay)', default=False)
    parser.add_argument('--useapi', action='store_true', help='Use response returned by API for data rather than writing to storage account', default=False)
    parser.add_argument('--retrys3', action='store_true', help='Do not invoke lambdas, just retry downloading results from S3 for an earlier experiment (provided with --outdir)', default=False)
    parser.add_argument('-ch', '--channel', action='store_true', help='Setup covert channel between two neighbors and measure bandwidth', default=False)
    parser.add_argument('-chr', '--chrate', action='store', type=int,  help='Send data on the channel at this rate in bps', default=1000)
    parser.add_argument('-cht', '--chthresh', action='store', type=int,  help='Custom threshold to use to classify 0 and 1 bits in the receiver', default=10500)
    
    # Launch lambdas from another account (make sure the credentials are added as a profile as directed in: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html)
    parser.add_argument('-sa', '--secaccount', action='store', help='profile name of the second account if we want to some launch lambdas from a different account, expects URL in cache')
    parser.add_argument('-sn', '--secname', action='store', help='name of the second lambda if we want to some launch different kinds of lambdas, expects URL in cache')
    parser.add_argument('-su', '--securl', action='store', help='second URL if we want to some launch lambdas from a different account/lambdas')
    parser.add_argument('-ss3p', '--secs3prefix', action='store', help='prefix of S3 bucket where the second account lambdas write to')

    
    args = parser.parse_args()

    # Prerequisite: AWS CLI configured to access the account
    p = subprocess.run(["aws", "configure", "get", "region"], stdout=subprocess.PIPE)
    if p.returncode != 0:
        print("Failed to get default region from aws cli. Cannot get url from cache. Provide --url.")
        return -1
    region = re.sub('\s+','', p.stdout.decode("utf-8"))
    s3bucket = "lambda-cpp-" + region
    s3bucket_sec = (args.secs3prefix + region) if args.secs3prefix else s3bucket

    # Find URL in cache if not specified.
    if not args.url:
        if not args.name:
            print("Provide --url or --name to get URL from cache.")
            return -1

        p = subprocess.run(["aws", "sts", "get-caller-identity"], stdout=subprocess.PIPE)
        if p.returncode != 0:
            print("Failed to get account id from aws cli. Cannot get url from cache. Provide --url.")
            return -1
        accountid = json.loads(p.stdout.decode("utf-8"), strict=False)["Account"]

        url_cache = os.path.join(".api_cache", "{0}_{1}_{2}".format(accountid, region, args.name))
        if not os.path.exists(url_cache):
            print("Cannot find url cache at: {0}. Provide actual url using --url.".format(url_cache))
            return -1

        with open(url_cache, 'r') as file:
            args.url = re.sub('\s+','', file.read())
            print("Found url in cache {0}: {1}".format(url_cache, args.url))

    # If second account is provided, get its URL from the cache too
    if args.secaccount or args.secname:
        p = subprocess.run(["aws", "sts", "get-caller-identity", "--profile", args.secaccount], stdout=subprocess.PIPE) if args.secaccount \
                else subprocess.run(["aws", "sts", "get-caller-identity"], stdout=subprocess.PIPE)
        if p.returncode != 0:
            print("Failed to get account id from aws cli for second lambda. Is the profile added properly? Or provide --securl.")
            return -1
        secaccountid = json.loads(p.stdout.decode("utf-8"), strict=False)["Account"]

        url_cache = os.path.join(".api_cache", "{0}_{1}_{2}".format(secaccountid, region, args.secname if args.secname else args.name))
        if not os.path.exists(url_cache):
            print("Cannot find url cache for second lambda at: {0}. Provide actual url using --securl.".format(url_cache))
            return -1

        with open(url_cache, 'r') as file:
            args.securl = re.sub('\s+','', file.read())
            print("Found second lambda url in cache {0}: {1}".format(url_cache, args.securl))

    # Make output dir
    if not args.outdir:     args.outdir = datetime.now().strftime("%m-%d-%H-%M")
    resdir = os.path.join("out", args.outdir)
    tmpdir = os.path.join(resdir, "tmp")
    if not os.path.exists(resdir):
        os.makedirs(resdir)
        os.makedirs(tmpdir)

    # Lambda sync point
    sync_point = int(time.time()) + args.delay       # now + delay, assuming (api invoke + lambda create + lambda setup) happens within this delay for all lambdas
    unique_id = datetime.now().strftime("%m-%d-%H-%M") if not args.retrys3 else args.outdir

    # Start enough threads
    global samples
    samples = args.samples
    for i in range(args.count):
        t = Thread(target=worker, args=())
        t.daemon = True
        t.start()

    # Invoke lambdas
    phases = args.phases
    start = time.time()
    lambda_tags = {}
    shared_lock = Lock()
    for i in range(args.count):
        id = i+1
        guid = unique_id + "-" + str(id)     # globally unique lambda id
        s3prefix = unique_id

        if not args.securl or random.randint(0, 1) == 0:
            tag = accountid if args.secaccount else (args.name if args.secname else "DEFAULT")
            print("Invoking lambda {0} with tag {1}".format(id, tag))
            req_q.put((args.url, id, guid, sync_point, phases, args.idbits, args.bitduration, args.delay,
                not args.useapi, s3bucket, s3prefix, tmpdir, None, args.retrys3, shared_lock, 
                args.channel, args.chrate, args.chthresh))
            lambda_tags[id] = tag
        else:
            # if second account if provided, use it for every other lambda
            tag = secaccountid if args.secaccount else (args.secname if args.secname else "SECOND")
            print("Invoking lambda {0} with tag {1}".format(id, tag))
            req_q.put((args.securl, id, guid, sync_point, phases, args.idbits, args.bitduration, args.delay,
                not args.useapi, s3bucket_sec, s3prefix, tmpdir, args.secaccount, args.retrys3, shared_lock,
                args.channel, args.chrate, args.chthresh))
            lambda_tags[id] = tag

        if args.sequence:
            # If invoking in sequence, wait until the request is made
            order_q.get()

    end = time.time()
    print("Invoking all lambdas took {0} seconds".format(int(end-start)))

    # Wait for everything to finish 
    try:
        req_q.join()
    except KeyboardInterrupt:
        sys.exit(1)
    
    # Paths for output files
    logpath = os.path.join(resdir, "log")
    respath = os.path.join(resdir, args.out)
    statspath = os.path.join(resdir, "stats.json")
    configpath = os.path.join(resdir, "config.json")
    chanpath = os.path.join(resdir, "channels.csv")
    chanstatspath = os.path.join(resdir, "channelstats.json")

    # Save configuration        
    config = {
        "Name": args.expname if args.expname else args.outdir,
        "Comments": args.expdesc,
        "Lambda Name":  args.name,
        "Lambda URL": args.url,
        "Lambda Count": args.count,
        "Phases": args.phases,
        "Bit Duration (secs)": args.bitduration,
        "Num bits": args.idbits,
        "Outdir": resdir,
        "Region": region,
    }
    with open(configpath, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

    # Parse responses and organize results into files
    first = True
    idstats = {}
    chaninfo = {}
    chanid = 0
    with open(respath, 'w') as csvfile:
        with open(logpath, "w") as logfile:
            while not data_q.empty():

                # get response
                item = data_q.get()
                # print(item)   #raw
                item_d = json.loads(item.decode("utf-8") if isinstance(item, bytes) else item , strict=False)

                # # Get lambda run time
                # if "Start Time" in item_d and "End Time" in item_d:
                    
                # If logs exist, put them in seperate file
                if "Logs" in item_d:
                    logfile.write(item_d["Logs"] + "\n")
                    item_d["Logs"] = logpath
                else:
                    item_d["Logs"] = "-"

                # If samples exist, put them in seperate file(s)
                if "Base Sample" in item_d:
                    sfilepath = os.path.join(resdir, "base_samples{0}".format(item_d["Id"]))
                    with open(sfilepath, "w") as sfile:
                        sfile.write("Latencies\n")
                        sfile.write("\n".join(item_d["Base Sample"].split(",")))
                        # print(item_d["Base Sample"])
                    item_d["Base Sample"] = sfilepath
                else:
                    item_d["Base Sample"] = "-"

                if "Bit-1 Sample" in item_d:
                    sfilepath = os.path.join(resdir, "bit1_samples{0}".format(item_d["Id"]))
                    with open(sfilepath, "w") as sfile:
                        sfile.write("Latencies\n")
                        # print(item_d["Bit Sample"])
                        sfile.write("\n".join(item_d["Bit-1 Sample"].split(",")))
                    item_d["Bit-1 Sample"] = sfilepath
                else:
                    item_d["Bit-1 Sample"] = "-"
                
                if "Bit-0 Sample" in item_d:
                    sfilepath = os.path.join(resdir, "bit0_samples{0}".format(item_d["Id"]))
                    with open(sfilepath, "w") as sfile:
                        sfile.write("Latencies\n")
                        # print(item_d["Bit Sample"])
                        sfile.write("\n".join(item_d["Bit-0 Sample"].split(",")))
                    item_d["Bit-0 Sample"] = sfilepath
                else:
                    item_d["Bit-0 Sample"] = "-"

                if "Predecessors" in item_d:
                    item_d["Warm Start"] = "Yes" if len([s for s in item_d["Predecessors"].split(",") if s]) > 0 else "No"

                if "Id" in item_d:
                    id = int(item_d["Id"])
                    item_d["Tag"] = lambda_tags[id]

                if "Channel" in item_d:
                    cinfo = item_d["Channel"]
                    # print(cinfo)
                    role = cinfo["Role"]
                    sender_id = int(cinfo["Sender Id"])
                    if sender_id not in chaninfo:
                        chanid += 1
                        chaninfo[sender_id] = {}
                        chaninfo[sender_id]["Id"] = chanid
                        chaninfo[sender_id]["Sender"] = sender_id
                        chaninfo[sender_id]["Receiver"] = cinfo["Receiver Id"]
                        chaninfo[sender_id]["Rate"] = cinfo["Rate"]
                        chaninfo[sender_id]["Bits"] = cinfo["Bits"]
                        chaninfo[sender_id]["Sent Data"] = None
                        chaninfo[sender_id]["Rcvd Data"] = None
                        chaninfo[sender_id]["Sender Erasures"] = None
                        chaninfo[sender_id]["Receiver Erasures"] = None
                    if role == "Sender":    
                        chaninfo[sender_id]["Sent Data"] = cinfo["Data"]
                        chaninfo[sender_id]["SErasures"] = cinfo["Erasures"]
                    else:                   
                        chaninfo[sender_id]["Rcvd Data"] = cinfo["Data"]
                        chaninfo[sender_id]["RErasures"] = cinfo["Erasures"]
                    item_d["Channel"] = chaninfo[sender_id]["Id"]
                else:
                    item_d["Channel"] = "-"
                item_d["Bit-0 Pvalue"] = "-"        # TODO: Remove
                item_d["Bit-1 Pvalue"] = "-"        # TODO: Remove

                # Write col headers
                if first:
                    writer = csv.DictWriter(csvfile, fieldnames=list(item_d.keys()))
                    writer.writeheader()
                    #first = False  

                # append row to results
                writer.writerow(item_d)

                # Print stdout
                cols = ["Success", "Phases", "Id"]
                for i in range(phases): cols += ["Phase {0}".format(i+1)]
                cols += ["Warm Start", "Account", "Logs", "Tag", "Error"]

                firstline = ""
                line = ""
                id = 0
                for k in cols:
                    format_str = " {:<25}" if k in ["Logs", "Base Sample", "Bit-0 Pvalue", "Bit-1 Pvalue", "Error"] else " {:<10}"
                    if k in item_d:
                        if first: 
                            # col headers
                            firstline += format_str.format(k) 

                        # Preprocess each line
                        post_val = item_d[k]
                        if k == "Id":   
                            # FIXME: Assumes Id comes before "Phase *" cols
                            id = int(item_d[k])
                            idstats[id] = []
                        if "Phase " in k:
                            val = int(item_d[k])
                            idstats[id].append(val)
                            post_val = "{:<4}".format(val)

                        line += format_str.format(post_val)

                # if first:
                #     print("============== LAMBDAS ===================")
                #     print(firstline)
                # print(line)

                first = False

        print("Full results at: ", respath)
    
    # Analyze id stats
    if idstats:
        # print(idstats)
        errorsk = "errors"
        clusters = {}
        for id, vals in idstats.items():
            # print(id, vals)
            maj = find_majority(vals)
            key = maj if maj else errorsk
            if key not in clusters.keys():
                clusters[key] = []
            clusters[key].append(id)

        sizes = [len(v) for k,v in clusters.items() if k != errorsk]        
        stats_ = {
            "Name": args.expname if args.expname else args.outdir,
            "Region": region,
            "Run":  args.outdir,
            "Count": args.count,
            "Clusters": len([k for k in clusters.keys() if k != errorsk]),
            "Error Rate": len(clusters[errorsk])*100/args.count if errorsk in clusters else 0,
            "Mean": statistics.mean(sizes) if sizes else 0,
            "Median": statistics.median(sizes) if sizes else 0,
            "Min": min(sizes) if sizes else 0,
            "Max": max(sizes) if sizes else 0,
            "Sizes": sizes
        }

        # print(stats_)
        with open(statspath, 'w', encoding='utf-8') as f:
            json.dump(stats_, f, ensure_ascii=False, indent=4)

    # Analyze covert channel bandwidth info
    if chaninfo:
        error_list = []
        error1_list = []
        error0_list = []
        count = 0
        rate = 0
        with open(chanpath, 'w') as csvfile:
            first = True
            for sender_id, channel in chaninfo.items():

                # Calculate errors
                errors = 0
                bit1errors = 0
                bit0errors = 0
                ones = 0
                zeroes = 0
                nbits = int(channel["Bits"])
                sent_data = channel["Sent Data"]
                rcvd_data = channel["Rcvd Data"]
                if not sent_data or not rcvd_data:
                    print("ERROR with channel {}", sender_id)
                    continue
                for i in range(nbits):
                    if sent_data[i] != rcvd_data[i]:    errors += 1
                    if sent_data[i] == "1" and sent_data[i] != rcvd_data[i]:    bit1errors += 1
                    if sent_data[i] == "0" and sent_data[i] != rcvd_data[i]:    bit0errors += 1
                    if sent_data[i] == "1":             ones += 1
                    if sent_data[i] == "0":             zeroes += 1
                channel["Errors"] = errors
                channel["Error %"] = errors * 100 / nbits
                error_list.append(errors * 100 / nbits)
                channel["Ones"] = ones
                channel["OneErrs"] = bit1errors
                channel["OneErr%"] = int(bit1errors * 100 / ones) if ones else "-"
                if ones:    error1_list.append(bit1errors * 100 / ones)
                channel["Zeroes"] = zeroes
                channel["ZeroErrs"] = bit0errors
                channel["ZeroErr%"] = int(bit0errors * 100 / zeroes) if zeroes else "-"
                if zeroes:  error0_list.append(bit0errors * 100 / zeroes)
                rate = int(channel["Rate"])

                # Write to file
                if first:
                    writer = csv.DictWriter(csvfile, fieldnames=list(channel.keys()))
                    writer.writeheader()
                # append row to results
                writer.writerow(channel)

                # Print stdout
                cols = ["Id", "Sender", "Receiver", "Rate", "Bits", "Errors", "Ones", "OneErrs", "OneErr%", 
                        "Zeroes", "ZeroErrs", "ZeroErr%", "SErasures", "RErasures", "Confidence"]

                firstline = ""
                line = ""
                for k in cols:
                    format_str = "{:<10}"
                    if k in channel:
                        if first:   firstline += format_str.format(k)       # col headers
                        line += format_str.format(copy.deepcopy(channel[k]))

                if first:
                    print("========== CHANNELS ===============")
                    print(firstline)
                print(line)
                count += 1
                first = False

        error_mean = np.mean(error_list)
        channel_stats = {
            "Channel Count": count,
            "Channel Rate": rate,
            "Effective Channel Rate": rate - (2 * error_mean * rate / 100),
            "Channel Threshold": args.chthresh,
            "Errors Mean": np.mean(error_list), 
            "Errors Std" : np.std(error_list),
            "1-bit Errors Mean": np.mean(error1_list), 
            "1-bit Errors Std" : np.std(error1_list),
            "0-bit Errors Mean": np.mean(error0_list), 
            "0-bit Errors Std" : np.std(error0_list),
        }
        print(channel_stats)
        with open(chanstatspath, 'w', encoding='utf-8') as f:
            json.dump(channel_stats, f, ensure_ascii=False, indent=4)
        print("Channel info at: ", chanpath)


if __name__ == '__main__':
    main()
