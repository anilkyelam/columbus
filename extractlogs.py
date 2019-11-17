import gzip
import os
import sys
fp = open("finaloutput", "w+")
def getInfos(currentDir):
    infos = []
    for root, dirs, files in os.walk(currentDir): # Walk directory tree
        for f in files:
            if f != '.DS_Store':
                with gzip.open(root+"/"+f, 'rb') as f:
                    file_content = f.read()
                    print (file_content)
                    fp.write(str(file_content))

getInfos(sys.argv[1])
fp.close()
