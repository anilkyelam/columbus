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
    start = time.time()
    result = {}
    result["In"] = "Both"
    result['Start Time'] = int(round(time.time() * 1000))
    time.sleep(6)
    
    up_times = open('/proc/uptime', mode='r').read().split()
    result['UP Time'] = up_times[0]
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    result['Boot Time'] = str(bt)
    
    # CPU frequencies
    cpufreq = psutil.cpu_freq()
    result["Frequency"]= cpufreq.current

    if_addrs = psutil.net_if_addrs()
    for interface_name, interface_addresses in if_addrs.items():
        for address in interface_addresses:
            result["Interface"]= interface_name
            if str(address.family) == 'AddressFamily.AF_INET':
                result["IP Address"] =address.address

    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
    result["MAC Address"] = mac

    i = 100000
    num_bits = 100000
    if(rdrand.HAS_SEED != 0):
        result['Rdseed Enabled']=1
        start1 = time.time()
        while(i!=0):
            rdrand.rdseed_get_bits(num_bits)
            i = i-1
        end = time.time()

    else:
        result['Rdseed Enabled']=0
        start1 = time.time()
        while(i!=0):
            rdrand.rdrand_get_bits(num_bits)
            i = i-1
        end = time.time()
    
    result["Total Time"] = end - start
    result["Exec Time"] = end - start1
    return json.dumps(result)
