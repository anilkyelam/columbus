from urllib.parse import urlparse
from threading import Thread
import http.client, sys
from queue import Queue
import argparse
import json
import csv
import awscli.clidriver as aws


MAX_CONCURRENT = 1000
req_q = Queue(MAX_CONCURRENT * 2)
data_q = Queue(MAX_CONCURRENT * 2)

def getResponse(ourl):
    try:
        url = urlparse(ourl)
        conn = http.client.HTTPSConnection(url.netloc,timeout=500)   
        conn.request("GET", url.path)
        res = conn.getresponse()
        return res
    except Exception as e:
        print(e)
        return None

def getResponseWithCli(idx, fn_name):
    try:
        outfile = "/ramdisk/output{0}.txt" % idx
        driver = aws.create_clidriver()
        driver.main(["lambda", "invoke", "--function-name", "membus", outfile ])
        return open(outfile, 'r').read()
    except Exception as e:
        print(e)
        return None

def worker(idx):
    while True:
        fn_name = req_q.get()
        
        resp = getResponseWithCli(idx, "membus")
        data_q.put(resp)
        else:
            #print (resp.status)
            pass

        req_q.task_done()

def main():
    for i in range(1):
        t = Thread(target=worker, args=(i))
        t.daemon = True
        t.start()
    try:
        for i in range(1):
            req_q.put("https://k07kpp2s0j.execute-api.me-south-1.amazonaws.com/first")
        req_q.join()
    except KeyboardInterrupt:
        sys.exit(1)
    first = True
    with open(sys.argv[1], 'w+') as csvfile:
        while not data_q.empty():
            item = data_q.get()
            item_i = json.loads(item)
            item_d = json.loads(item_i)
            if first:
                writer = csv.DictWriter(csvfile, fieldnames=list(item_d.keys()))
                writer.writeheader()
                print (data_q.qsize())
                first = False
            writer.writerow(item_d)

if __name__ == '__main__':
    #main()
    getResponseWithCli("membus")