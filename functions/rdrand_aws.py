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
    result["Physical cores:"]=psutil.cpu_count(logical=False)
    result["Total cores:"] = psutil.cpu_count(logical=True)
    # CPU frequencies
    cpufreq = psutil.cpu_freq()
    result["Current Frequency"]= cpufreq.current
    # CPU usage


    print("="*40, "Network Information", "="*40)
    # get all network interfaces (virtual and physical)
    if_addrs = psutil.net_if_addrs()
    for interface_name, interface_addresses in if_addrs.items():
        for address in interface_addresses:
            result["Interface:"]= interface_name
            if str(address.family) == 'AddressFamily.AF_INET':
                result["IP Address"] =address.address
                result["Netmask"] =address.netmask
                result["Broadcast IP"]= address.broadcast
            elif str(address.family) == 'AddressFamily.AF_PACKET':
                result[" MAC Address"]=address.address
                result["Netmask"]=address.netmask
                result["Broadcast MAC"]=address.broadcast
    # get IO statistics since boot
    net_io = psutil.net_io_counters()
    result["Total Bytes Sent:"] =get_size(net_io.bytes_sent)
    result["Total Bytes Received"]=get_size(net_io.bytes_recv)
    partitions = psutil.disk_partitions()
    for partition in partitions:
        result["Device"]= partition.device
        result["Mountpoint"]= partition.mountpoint
        result["File system type"]= partition.fstype
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            # this can be catched due to the disk that
            # isn't ready
            continue
        result["Total Size"]= get_size(partition_usage.total)
        result["Used"]= get_size(partition_usage.used)
        result["Free"]= get_size(partition_usage.free)
        result["Percentage"]= partition_usage.percent
    # get IO statistics since boot



    uname = platform.uname()
    result["System"]=uname.system
    result["Node Name"]=uname.node
    result["Release"]=uname.release
    result["Version"]=uname.version
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
