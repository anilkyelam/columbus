# 
# Makes concurrent requests to a URL
#
# Usage: python .\prequest.py -u "https://2ueu9j34g7.execute-api.us-east-2.amazonaws.com/default/ScrewYouAmazon" -c 200 -o results2.csv
#

from urlparse import urlparse
from threading import Thread
import httplib, sys
from Queue import Queue
import argparse
import json
import csv

# Global
MAX_CONCURRENT = 1000
req_q = Queue(MAX_CONCURRENT * 2)
data_q = Queue(MAX_CONCURRENT * 2)

def worker(idx):
    while True:
        url = req_q.get()
        
        resp = getResponse(url)
        if resp and resp.status == 200:
            data = resp.read()
            data_q.put(data)
        else:
            print(idx, 
                resp.status if resp else "error", 
                resp.reason if resp else "error")

        req_q.task_done()


def getResponse(ourl):
    try:
        url = urlparse(ourl)
        conn = httplib.HTTPSConnection(url.netloc)   
        conn.request("GET", url.path)
        res = conn.getresponse()
        return res
    except Exception as e:
        print(e)
        return None


def doSomethingWithResult(resp, url):
    print(resp.status, resp.reason)
    data = resp.read()
    print(resp.headers)
    print(data)


def main():
    parser = argparse.ArgumentParser("Makes a specified number of concurrent https requests to a url")
    parser.add_argument('-u', '--url', action='store', help='timeout in seconds, forever if not set', required=True)
    parser.add_argument('-c', '--count', action='store', type=int, help='number of requests to make (max:{0})'.format(MAX_CONCURRENT), required=True)
    parser.add_argument('-o', '--out', action='store', help='path to results file', default="results.csv")
    args = parser.parse_args()

    # Start concurrent threads
    for i in range(args.count):
        t = Thread(target=worker, args=(i,))
        t.daemon = True
        t.start()

    # Send requests 
    try:
        for i in range(args.count):
            req_q.put(args.url)
        req_q.join()
    except KeyboardInterrupt:
        sys.exit(1)

    # Write data to file
    first = True
    with open(args.out, 'wb') as csvfile:
        while not data_q.empty():
            item = data_q.get()
            print(item)

            item_d = json.loads(item)
            if first:
                writer = csv.DictWriter(csvfile, fieldnames=item_d.keys())
                writer.writeheader()
                first = False

            writer.writerow(item_d)


if __name__ == '__main__':
    main()