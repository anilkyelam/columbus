import os
import subprocess
import random
import uuid
from rdrand import RdRandom

def hello_world(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    proc = subprocess.Popen(["cat /proc/sys/kernel/random/boot_id"], stdout=subprocess.PIPE, shell=True)
    output = ""
    proc = subprocess.Popen(["cat /proc/uptime"], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    output = output + "uptime: " + str(out) + "\n"
    proc = subprocess.Popen(["cat /proc/meminfo"], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    output = output + "meminfo: " + str(out) + "\n"
    print(out)
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
    output = output + "mac: " + mac + "\n"
    print (os.uname())
    device = os.stat("/home").st_dev

    # Print the raw device number 
    print("Raw device number:", device)
    # Extract the device minor number 
    # from the above raw device number 
    output = output + "times: " + str(os.times()) + "\n"
    print (os.getrandom(200, os.GRND_RANDOM))
    return output