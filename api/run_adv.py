from urllib.parse import urlparse
from threading import Thread
import http.client, sys
from queue import Queue
import argparse
import json
import csv
import time


MAX_CONCURRENT = 1500
req_q = Queue(MAX_CONCURRENT * 2)
data_q = Queue(MAX_CONCURRENT * 2)

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
        (url, body) = req_q.get()
        
        resp = getResponse(url, body)
        if resp and resp.status == 200:
            data = resp.read()
            data_q.put(data)
        else:
            #print (resp.status)
            pass
        req_q.task_done()


def main():

    defaulturl = "https://a0bn4o2c71.execute-api.ap-east-1.amazonaws.com/latest"    # ap-east-1
    #defaulturl = "https://v1pe8p505h.execute-api.us-west-2.amazonaws.com/latest"   # us-west-2
    #defaulturl = "https://h6r05ug8ga.execute-api.me-south-1.amazonaws.com/latest"  # me-south-2
    #defaulturl = "https://8rq4dl2w8f.execute-api.us-west-1.amazonaws.com/latest"   # us-west-1

    parser = argparse.ArgumentParser("Makes concurrent requests to lambda URLs")
    parser.add_argument('-c', '--count', action='store', type=int, help='number of requests to make (max:{0})'.format(MAX_CONCURRENT), default=5)
    parser.add_argument('-o', '--out', action='store', help='path to results file', default="results.csv")
    parser.add_argument('-u', '--url', action='store', help='url to call', required=True) #default=defaulturl)
    parser.add_argument('-a', '--attack', action='store_true', help='whether to run thrashers', default=False)
    args = parser.parse_args()

    # Start enough threads
    for i in range(2*args.count):
        t = Thread(target=worker, args=())
        t.daemon = True
        t.start()

    # Wait a bit and invoke second batch (thrashers)
    if args.attack:
        for i in range(args.count):
            req_q.put((args.url, "0"))

    # Wait for everything to finish
    try:
        req_q.join()
    except KeyboardInterrupt:
        sys.exit(1)
    
    # Write to file
    first = True
    with open(args.out+"-all", 'w') as csvfile:
        with open(args.out, 'w') as scsvfile:
            while not data_q.empty():
                item = data_q.get()
                #print(item)
                item_d = json.loads(item.decode("utf-8"))
                if first:
                    writer = csv.DictWriter(csvfile, fieldnames=list(item_d.keys()))
                    swriter = csv.DictWriter(scsvfile, fieldnames=list(item_d.keys()))
                    writer.writeheader()
                    swriter.writeheader()
                    first = False
                writer.writerow(item_d)
                if item_d["Role"] == "sampler": swriter.writerow(item_d)


if __name__ == '__main__':
    main()
