#
# 1. bash setup.sh
# 2. Get URL or Lambda name
# 3. python3 invoke.py -u https://ockhe03c0i.execute-api.us-west-1.amazonaws.com/latest/membus -c 10    or,
# 3. python3 invoke.py -n membus1536 -c 10  
#

from urllib.parse import urlparse
from threading import Thread
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


MAX_CONCURRENT = 1500
req_q = Queue(MAX_CONCURRENT * 2)
data_q = Queue(MAX_CONCURRENT * 2)
samples = False

# Find majority elements in a list
def find_majority(arr): 
    maxCount = 0
    maxVal = 0
    for val in arr: 
        count = 0
        for val2 in arr: 
            if(val == val2): 
                count += 1
        if count > maxCount:   
            maxVal = val
            maxCount = count
        
    if maxCount > len(arr)/2: 
        return maxVal    
    return None

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
def worker():
    while True:
        (url, id, syncpt, phases, bits_in_id, bit_duration, start_delay, use_s3, s3bucket, s3file, tmpdir) = req_q.get()
        
        body = { "id": id, "stime": syncpt, "phases": phases, "log": True, 
                    "maxbits": bits_in_id, "bitduration": bit_duration,
                    "samples": samples, "s3bucket": s3bucket, "s3key": s3file }
        resp = getResponse(url, json.dumps(body))
        if use_s3:
            wait_secs = start_delay + phases*(bits_in_id+1)*bit_duration + 30
            start = time.time()
            timeout = time.time() + wait_secs
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

            while time.time() < timeout:
                # Set shell to true and pass entire command as a single string for usual shell like environment
                # which is required to enable default aws credentials
                p = subprocess.run(["aws s3 ls {0}/{1}".format(s3bucket, s3file)], stdout=subprocess.PIPE, shell=True)
                if p.returncode == 0:
                    found = True
                    break

                # WARNING: This print stdout seems necessary for the control to move forward
                progress = int((time.time() - start) * 50 / wait_secs)
                sys.stdout.write("\rLambda {0}: Waiting [{1}{2}]".format(id, '#'*progress, '.'*(50-progress), p.stdout))
                time.sleep(1)
                
            if found:
                tmppath = os.path.join(tmpdir, str(id))
                p = subprocess.run(["aws s3 cp s3://{0}/{1} {2}".format(s3bucket, s3file, tmppath)], stdout=subprocess.PIPE, shell=True)
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
    parser.add_argument('-c', '--count', action='store', type=int, help='number of requests to make (max:{0})'.format(MAX_CONCURRENT), default=5)
    parser.add_argument('-o', '--out', action='store', help='path to results file', default="results.csv")
    parser.add_argument('-u', '--url', action='store', help='url to invoke lambda. Looks in .api_cache by default.')
    parser.add_argument('-p', '--phases', action='store', type=int, help='number of phases to run', default=1)
    parser.add_argument('-i', '--idbits', action='store', type=int, help='number of bits in ID', default=10)
    parser.add_argument('-b', '--bitduration', action='store', type=int, help='time to communicate for each bit in seconds', default=1)
    parser.add_argument('-d', '--delay', action='store', type=int, help='initial delay for lambdas to sync up (in seconds)', default=30)
    parser.add_argument('-n', '--name', action='store', help='lambda name, if URL should be retrieved from cache', default="membusv2")
    parser.add_argument('-s', '--samples', action='store_true', help='save observed latency samples to log', default=False)
    parser.add_argument('--useapi', action='store_true', help='Use response returned by API for data rather than writing to storage account', default=False)
    parser.add_argument('-od', '--outdir', action='store', help='name of output dir')
    parser.add_argument('-en', '--expname', action='store', help='Custom name for this experiment, defaults to datetime')
    parser.add_argument('-ed', '--expdesc', action='store', help='Description/comments for this run', default="")
    args = parser.parse_args()

    # Prerequisite: AWS CLI configured to access the account
    p = subprocess.run(["aws", "configure", "get", "region"], stdout=subprocess.PIPE)
    if p.returncode != 0:
        print("Failed to get default region from aws cli. Cannot get url from cache. Provide --url.")
        return -1
    region = re.sub('\s+','', p.stdout.decode("utf-8"))
    s3bucket = "lambda-cpp-" + region

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

    # Make output dir
    if not args.outdir:     args.outdir = datetime.now().strftime("%m-%d-%H-%M")
    resdir = os.path.join("out", args.outdir)
    tmpdir = os.path.join(resdir, "tmp")
    if not os.path.exists(resdir):
        os.makedirs(resdir)
        os.makedirs(tmpdir)

    # Lambda sync point
    sync_point = int(time.time()) + args.delay       # now + delay, assuming (api invoke + lambda create + lambda setup) happens within this delay for all lambdas
    unique_id = datetime.now().strftime("%m-%d-%H-%M")

    # Start enough threads
    global samples
    samples = args.samples
    for i in range(args.count):
        t = Thread(target=worker, args=())
        t.daemon = True
        t.start()

    # Invoke lambdas
    phases = args.phases
    s3file = unique_id
    for i in range(args.count):
        req_q.put((args.url, i+1, sync_point, phases, args.idbits, args.bitduration, args.delay,
            not args.useapi,
            s3bucket if not args.useapi else "", 
            s3file+"-"+str(i) if not args.useapi else "",
            tmpdir))

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
    with open(respath, 'w') as csvfile:
        with open(logpath, "w") as logfile:
            while not data_q.empty():

                # get response
                item = data_q.get()
                # print(item)   #raw
                item_d = json.loads(item.decode("utf-8") if isinstance(item, bytes) else item , strict=False)

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

                # if "Bit-1 Pvalue" in item_d:
                #     val = item_d["Bit-1 Pvalue"]
                #     item_d["Bit-1 Pvalue"] = float(val)
                
                # if "Bit-0 Pvalue" in item_d:
                #     val = item_d["Bit-0 Pvalue"]
                #     item_d["Bit-0 Pvalue"] = float(val)

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
                cols += ["Logs", "Base Sample", "Bit-0 Pvalue", "Bit-1 Pvalue", "Error"]

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

                if first:
                    print("")
                    print(firstline)
                print(line)

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
            "Mean": statistics.mean(sizes),
            "Median": statistics.median(sizes),
            "Min": min(sizes),
            "Max": max(sizes),
            "Sizes": sizes
        }

        print(stats_)
        with open(statspath, 'w', encoding='utf-8') as f:
            json.dump(stats_, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    main()
