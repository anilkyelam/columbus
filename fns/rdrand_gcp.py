import os
import subprocess
import random
import uuid
import json
import time
import datetime
import rdrand

def hello_world(request):
    result = {}
    result['start_time'] = int(round(time.time() * 1000))



    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
    result["MAC Addr"] = mac

    result['IP'] = os.uname()[1]
    # result["osname"] = str(os.uname())

    # Extract the device minor number 
    # from the above raw device number 
    itimes = []
    times = []
    i = 1000
    start = time.time()
    while(i!=0):
        start1 = time.time()
        rdrand.rdseed_get_bits(1000)
        i = i-1
        end1 = time.time()
        time.sleep(0.001)
        itimes.append(end1-start1)
    end = time.time()
    print (end-start)
    end = time.time()
    imax_value = max(itimes)
    iavg_value = sum(itimes)/len(itimes)
    result['imax_value'] = imax_value
    result['iavg_value'] = iavg_value

    time.sleep(7)
    i = 1000
    while(i!=0):
        start1 = time.time()
        rdrand.rdseed_get_bits(1000)
        i = i-1
        end1 = time.time()
        times.append(end1-start1)
        time.sleep(0.001)
    imax_value = max(times)
    iavg_value = sum(times)/len(times)
    result['fmax_value'] = imax_value
    result['favg_value'] = iavg_value
    result['rdseed'] = rdrand.HAS_SEED
    

    return json.dumps(result)
