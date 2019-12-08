import subprocess
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

def get_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def lambda_handler(event, context):
    result = {}
    result['start_time'] = int(round(time.time() * 1000))
    # CPU frequencies
    cpufreq = psutil.cpu_freq()
    result["Current Frequency"]= cpufreq.current
    # get all network interfaces (virtual and physical)
    if_addrs = psutil.net_if_addrs()
    for interface_name, interface_addresses in if_addrs.items():
        for address in interface_addresses:
            result["Interface:"]= interface_name
            elif str(address.family) == 'AddressFamily.AF_PACKET':
                result[" MAC Address"]=address.address
    # get IO statistics since boot
    net_io = psutil.net_io_counters()
    result["Total Bytes Sent:"] =get_size(net_io.bytes_sent)
    result["Total Bytes Received"]=get_size(net_io.bytes_recv)

    itimes = []
    times = []
    i = 5000
    if(rdrand.HAS_SEED != 0):
        result['rdseed']=1
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
        i = 5000
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
        i = 5000
        result['rdseed']=0
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
        result['fmax_rdseed_value'] = 0
        result['favg_rdseed_value'] = 0
        result['fmax_rdrand_value'] = imax_value
        result['favg_rdrand_value'] = iavg_value
        

    return json.dumps(result)
