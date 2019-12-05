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
    if(rdrand.HAS_SEED != 0):
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
        result['imax_rdseed_value'] = imax_value
        result['iavg_rdseed_value'] = iavg_value
        result['imax_rdrand_value'] = 0
        result['iavg_rdrand_value'] = 0

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
        result['fmax_rdseed_value'] = imax_value
        result['favg_rdseed_value'] = iavg_value
        result['fmax_rdrand_value'] = 0
        result['favg_rdrand_value'] = 0
    else:
        start = time.time()
        while(i!=0):
            start1 = time.time()
            rdrand.rdrand_get_bits(1000)
            i = i-1
            end1 = time.time()
            time.sleep(0.001)
            itimes.append(end1-start1)
        end = time.time()
        print (end-start)
        end = time.time()
        imax_value = max(itimes)
        iavg_value = sum(itimes)/len(itimes)
        result['imax_rdseed_value'] = 0
        result['iavg_rdseed_value'] = 0
        result['imax_rdrand_value'] = imax_value
        result['iavg_rdrand_value'] = iavg_value

        time.sleep(7)
        i = 1000
        while(i!=0):
            start1 = time.time()
            rdrand.rdrand_get_bits(1000)
            i = i-1
            end1 = time.time()
            times.append(end1-start1)
            time.sleep(0.001)
        imax_value = max(times)
        iavg_value = sum(times)/len(times)
        result['fmax_rdseed_value'] = 0
        result['favg_rdseed_value'] = 0
        result['fmax_rdrand_value'] = imax_value
        result['favg_rdrand_value'] = iavg_value
        

    return json.dumps(result)

