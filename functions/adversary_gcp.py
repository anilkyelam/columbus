import os
import subprocess
import random
import uuid
import json
import time
import datetime
import numpy as np
import rdrand

def hello_world(request):
    st_time = time.time()

    result = {}

    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
    result["MAC Addr"] = mac
    
    result['IP'] = os.uname()[1]

    # Extract the device minor number 
    # from the above raw device number 
    times = []
    i = 10000
    while(i!=0):
        rdrand.rdrand_get_bits(1000000)
        i = i-1
	
    etime = time.time()
    result['Duration'] = etime - st_time
    return json.dumps(result)