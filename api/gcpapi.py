from urllib.parse import urlparse
from threading import Thread
import http.client, sys
from queue import Queue
import argparse
import json
import csv


MAX_CONCURRENT = 1000
req_q = Queue(MAX_CONCURRENT * 2)
data_q = Queue(MAX_CONCURRENT * 2)

def getResponse(ourl):
    try:
        url = urlparse(ourl)
        conn = http.client.HTTPSConnection(url.netloc, timeout=300)   
        conn.request("GET", url.path)
        res = conn.getresponse()
        return res
    except Exception as e:
        print(e)
        return None
def worker():
    while True:
        url = req_q.get()
        
        resp = getResponse(url)
        if resp and resp.status == 200:
            data = resp.read()
            data_q.put(data)
        else:
            print (resp.status)

        req_q.task_done()
def main():
    for i in range(200):
        t = Thread(target=worker, args=())
        t.daemon = True
        t.start()
    try:
        for i in range(200):
            req_q.put("https://europe-west1-zinc-wares-258309.cloudfunctions.net/rdrand")
        req_q.join()
    except KeyboardInterrupt:
        sys.exit(1)
    first = True
    with open(sys.argv[1], 'w+') as csvfile:
        while not data_q.empty():
            item = data_q.get()

            item_d = json.loads(item)
            
            if first:
                writer = csv.DictWriter(csvfile, fieldnames=list(item_d.keys()))
                writer.writeheader()
                print (data_q.qsize())
                first = False

            writer.writerow(item_d)

if __name__ == '__main__':
    main()
