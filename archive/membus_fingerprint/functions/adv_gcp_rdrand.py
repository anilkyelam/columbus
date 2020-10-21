import os
import subprocess
import random
import uuid
import json
import time
import psutil
import platform
from datetime import datetime
import rdrand

def hello_world(request):
    result = {}
    result['Start Time'] = int(round(time.time() * 1000))
    up_times = open('/proc/uptime', mode='r').read().split()
    result['UP Time'] = up_times[0]
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    result['Boot Time'] = str(bt)
    # CPU frequencies
    cpufreq = psutil.cpu_freq()
    result["Frequency"]= cpufreq.current
    # CPU usage
    
    # get all network interfaces (virtual and physical)
    if_addrs = psutil.net_if_addrs()
    for interface_name, interface_addresses in if_addrs.items():
        for address in interface_addresses:
            result["Interface"]= interface_name
            if str(address.family) == 'AddressFamily.AF_INET':
                result["IP Address"] =address.address

    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
    result["MAC Address"] = mac

    # result["osname"] = str(os.uname())

    # Extract the device minor number 
    # from the above raw device number 
    itimes = []
    times = []
    i = 5000
    if(rdrand.HAS_SEED != 0):
        result['Rdseed Enabled']=1
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
        iavg_value = sum(itimes)/len(itimes)
        result['Rdseed Latency'] = iavg_value
        result['Rdrand Latency'] = 0

        time.sleep(7)
        i = 5000
        while(i!=0):
            start1 = time.time()
            rdrand.rdseed_get_bits(1000)
            i = i-1
            end1 = time.time()
            times.append(end1-start1)
            time.sleep(0.001)
        iavg_value = sum(times)/len(times)
        result['Contention Rdseed Latency'] = iavg_value
        result['Contention Rdrand Latency'] = 0
    else:
        i = 5000
        result['Rdseed Enabled']=0
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
        result['Rdseed Latency'] = 0
        result['Rdrand Latency'] = iavg_value

        time.sleep(7)
        
        i = 5000
        while(i!=0):
            start1 = time.time()
            rdrand.rdrand_get_bits(1000)
            i = i-1
            end1 = time.time()
            times.append(end1-start1)
            time.sleep(0.001)
        imax_value = max(times)
        iavg_value = sum(times)/len(times)
        result['Contention Rdseed Latency'] = 0
        result['Contention Rdrand Latency'] = iavg_value
        

    return json.dumps(result)