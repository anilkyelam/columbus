import os
import subprocess
import random
import uuid
import boto3
import sys

def handler(context, events):
    proc = subprocess.Popen(["cat /proc/sys/kernel/random/boot_id"], stdout=subprocess.PIPE, shell=True)
    output = ""
    (out, err) = proc.communicate()
    output = output + "bootId: " + str(out) + "\n"
    print("bootId: " + str(out))
    proc = subprocess.Popen(["cat /proc/uptime"], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    output = output + "uptime: " + str(out) + "\n"
    print ("uptime: " + str(out))
    proc = subprocess.Popen(["cat /proc/stat"], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    output = output + "stat: " + str(out) + "\n"
    print ("stat: " + str(out))
    proc = subprocess.Popen(["cat /proc/softirqs"], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    output = output + "softirqs: " + str(out) + "\n"
    print ("softirqs: " + str(out))
    proc = subprocess.Popen(["cat /proc/interrupts"], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    output = output + "interrupts: " + str(out) + "\n"
    print ("interrupts: " + str(out))
    proc = subprocess.Popen(["cat /proc/zoneinfo"], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    output = output + "zoneinfo: " + str(out) + "\n"
    print ("zoneinfo: " + str(out))
    proc = subprocess.Popen(["cat /proc/sys/fs/file-nr"], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    output = output + "file-nr: " + str(out) + "\n"
    print ("file-nr: " + str(out))
    proc = subprocess.Popen(["cat /proc/meminfo"], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    output = output + "meminfo: " + str(out) + "\n"
    print ("meminfo: " + str(out))
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
    output = output + "mac: " + mac + "\n"
    print ("osname: "+ str(os.uname()))
    device = os.stat("/home").st_dev

    # Print the raw device number 
    print("Raw device number:", device)
    # Extract the device minor number 
    # from the above raw device number 
    output = output + "times: " + str(os.times()) + "\n"
    print (os.getrandom(200, os.GRND_RANDOM))
    print ("times: " + str(os.times()))
    return output
