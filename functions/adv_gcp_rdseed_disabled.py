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
    if(rdrand.HAS_SEED==0):
        result['Start Time'] = int(round(time.time() * 1000))
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

        i = 10000
        num_bits = 10000
        start = time.time()
        while(i!=0):
            rdrand.rdrand_get_bits(num_bits)
            i = i-1
        end = time.time()
        print (end-start)
        result["Exec Time"] = end - start

    return json.dumps(result)