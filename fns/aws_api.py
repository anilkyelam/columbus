import json
import os
import subprocess
import random
import uuid
import boto3
import sys

def lambda_handler(event, context):
    
    result = {}
    
    result['Boot ID'] = open('/proc/sys/kernel/random/boot_id', mode='r').read()
    
    up_times = open('/proc/uptime', mode='r').read().split()
    result['UP Time 1'] = up_times[0]
    result['UP Time 2'] = up_times[1]
    
    
    file_handles = open('/proc/sys/fs/file-nr', mode='r').read().split()
    result['File NR 1'] = file_handles[0]
    result['File NR 2'] = file_handles[1]
    result['File NR 3'] = file_handles[2]
    
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
    result["MAC Addr"] = mac
    
    # result["osname"] = str(os.uname())
    
    device = os.stat("/home").st_dev
    result["raw_device_num"] = device
    # Extract the device minor number 
    # from the above raw device number 
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
