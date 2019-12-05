# Modify contents of this function to include code that needs to be run multiple times on aws lambdas
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
    print(output)
