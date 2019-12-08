from urllib.parse import urlparse
from threading import Thread
import http.client, sys
from queue import Queue
import argparse
import json
import csv
import time


MAX_CONCURRENT = 1000
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

    url = "https://h6r05ug8ga.execute-api.me-south-1.amazonaws.com/latest"  # me-south-2
    #url = "https://8rq4dl2w8f.execute-api.us-west-1.amazonaws.com/latest"   # us-west-1

    parser = argparse.ArgumentParser("Makes concurrent requests to lambda URLs")
    parser.add_argument('-c', '--count', action='store', type=int, help='number of requests to make (max:{0})'.format(MAX_CONCURRENT), default=5)
    parser.add_argument('-o', '--out', action='store', help='path to results file', default="results.csv")
    args = parser.parse_args()

    # Start enough threads
    for i in range(2*args.count):
        t = Thread(target=worker, args=())
        t.daemon = True
        t.start()

    # Invoke first batch (samplers)
    for i in range(args.count):
        req_q.put((url, "1"))

    # Wait a bit and invoke second batch (thrashers)
    #time.sleep(6)
    #for i in range(args.count):
    #    req_q.put((url, "0"))

    # Wait for everything to finish
    try:
        req_q.join()
    except KeyboardInterrupt:
        sys.exit(1)
    
    # Write to file
    first = True
    with open(args.out, 'w') as csvfile:
        while not data_q.empty():
            item = data_q.get()
            print(item)
            item_d = json.loads(item.decode("utf-8"))
            if first:
                writer = csv.DictWriter(csvfile, fieldnames=list(item_d.keys()))
                writer.writeheader()
                first = False
            writer.writerow(item_d)


if __name__ == '__main__':
    main()
