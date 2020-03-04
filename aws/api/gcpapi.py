# TO RUN : python3 no_of_calls path_to_gcpapi.py "URL" "path_to_csv"

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
            pass

        req_q.task_done()

def main():
    no_of_calls = int(sys.argv[1])
    for i in range(no_of_calls):
        t = Thread(target=worker, args=())
        t.daemon = True
        t.start()
    try:
        for i in range(no_of_calls):
            req_q.put(sys.argv[2])

        req_q.join()
    except KeyboardInterrupt:
        sys.exit(1)
    first = True

    print ("Successful runs = " + str(data_q.qsize()))
    
    counter = 0
    with open(sys.argv[3], 'w+') as csvfile:
        while not data_q.empty():
            item = data_q.get()

            item_d = json.loads(item)
            if(item_d == {}):
                continue
            
            if first:
                writer = csv.DictWriter(csvfile, fieldnames=list(item_d.keys()))
                writer.writeheader()
                first = False

            counter = counter+1
            writer.writerow(item_d)
    
    print("Runs that passed the check = " + str(counter))

if __name__ == '__main__':
    main()
