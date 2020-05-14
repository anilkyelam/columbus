#
# 1. bash setup.sh
# 2. Get URL
# 3. python3 invoke.py -u https://ockhe03c0i.execute-api.us-west-1.amazonaws.com/latest/membus -c 10
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


MAX_CONCURRENT = 1500
req_q = Queue(MAX_CONCURRENT * 2)
data_q = Queue(MAX_CONCURRENT * 2)

# Function to calculate hamming distance  
def hammingDistance(n1, n2) : 
    x = n1 ^ n2  
    setBits = 0
    while (x > 0) : 
        setBits += x & 1
        x >>= 1
    return setBits 

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


def worker():
    while True:
        (url, id, syncpt, phases) = req_q.get()
        
        body = { "id": id, "stime": syncpt, "phases": phases, "log": True, "samples": True }
        resp = getResponse(url, json.dumps(body))
        if resp and resp.status == 200:
            data = resp.read()
            data_q.put(data)
        else:
            print (resp.status)
            pass
        req_q.task_done()

def main():
    parser = argparse.ArgumentParser("Makes concurrent requests to lambda URLs")
    parser.add_argument('-c', '--count', action='store', type=int, help='number of requests to make (max:{0})'.format(MAX_CONCURRENT), default=5)
    parser.add_argument('-o', '--out', action='store', help='path to results file', default="results.csv")
    parser.add_argument('-u', '--url', action='store', help='url to invoke lambda. Looks in .api_cache by default.')
    parser.add_argument('-p', '--phases', action='store', type=int, help='number of phases to run', default=1)
    parser.add_argument('-d', '--delay', action='store', type=int, help='initial delay for lambdas to sync up (in seconds)', default=5)
    parser.add_argument('-n', '--name', action='store', help='lambda name, if URL should be retrieved from cache', default="membusv2")
    parser.add_argument('-od', '--outdir', action='store', help='name of output dir')
    args = parser.parse_args()

    # Find URL in cache if not specified.
    if not args.url:
        if not args.name:
            print("Provide --url or --name to get URL from cache.")
            return -1

        p = subprocess.run(["aws", "configure", "get", "region"], stdout=subprocess.PIPE)
        if p.returncode != 0:
            print("Failed to get default region from aws cli. Cannot get url from cache. Provide --url.")
            return -1
        region = re.sub('\s+','', p.stdout.decode("utf-8"))

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

    # Lambda sync point
    sync_point = int(time.time()) + args.delay       # now + delay, assuming (api invoke + lambda create + lambda setup) happens within this delay for all lambdas

    # Start enough threads
    for i in range(args.count):
        t = Thread(target=worker, args=())
        t.daemon = True
        t.start()

    # Invoke lambdas
    phases=args.phases
    for i in range(args.count):
        req_q.put((args.url, i*10+1, sync_point, phases))

    # Wait for everything to finish 
    try:
        req_q.join()
    except KeyboardInterrupt:
        sys.exit(1)
    
    # Pick a folder for logs
    if not args.outdir:     args.outdir = datetime.now().strftime("%m-%d-%H-%M")
    resdir = os.path.join("out", args.outdir)
    if not os.path.exists(resdir):
        os.makedirs(resdir)
    logpath = os.path.join(resdir, "log")
    respath = os.path.join(resdir, args.out)

    first = True
    with open(respath, 'w') as csvfile:
        with open(logpath, "w") as logfile:
            while not data_q.empty():

                # get response
                item = data_q.get()
                # print(item)   #raw
                item_d = json.loads(item.decode("utf-8"), strict=False)

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

                if "Bit Sample" in item_d:
                    sfilepath = os.path.join(resdir, "bit_samples{0}".format(item_d["Id"]))
                    with open(sfilepath, "w") as sfile:
                        sfile.write("Latencies\n")
                        # print(item_d["Bit Sample"])
                        sfile.write("\n".join(item_d["Bit Sample"].split(",")))
                    item_d["Bit Sample"] = sfilepath
                else:
                    item_d["Bit Sample"] = "-"

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
                cols += ["Logs", "Base Sample", "Bit Sample", "Error"]

                firstline = ""
                line = ""
                id = 0
                for k in cols:
                    format_str = " {:<25}" if k in ["Logs", "Base Sample", "Bit Sample", "Error"] else " {:<10}"
                    if k in item_d:
                        if first: 
                            # col headers
                            firstline += format_str.format(k) 

                        # Preprocess each line
                        post_val = item_d[k]
                        if k == "Id":   id = int(item_d[k])
                        if "Phase " in k:
                            val = int(item_d[k])
                            edit = hammingDistance(val, id)
                            post_val = "{:<4}({})".format(val, edit)

                        line += format_str.format(post_val)

                if first:
                    print(firstline)
                print(line)

                first = False

        print("Full results at: ", respath)

if __name__ == '__main__':
    main()
