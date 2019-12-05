import os
import subprocess
import random
import uuid
import json
import time
import datetime
import numpy as np
import rdrand

def handler(event, context):

    result = {}

    result['Boot ID'] = open('/proc/sys/kernel/random/boot_id', mode='r').read()

    up_times = open('/proc/uptime', mode='r').read().split()
    result['UP Time 1'] = up_times[0]

    file_handles = open('/proc/sys/fs/file-nr', mode='r').read().split()
    result['File NR 1'] = file_handles[0]

    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
    result["MAC Addr"] = mac

    zone = open('/proc/zoneinfo', mode='r').read().split()
    result['nr_active_anon'] = zone[9]
    result['nr_inactive_file'] = zone[11]
    result['IP'] = os.uname()[1]
    # result["osname"] = str(os.uname())

    # Extract the device minor number 
    # from the above raw device number 
    times = []
    i = 10000
    while(i!=0):
        rdrand.rdrand_get_bits(1000000)
        i = i-1

    return json.dumps(result)