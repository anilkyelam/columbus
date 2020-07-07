python plot.py -xc "Offset" -xl "Offset (Bytes)" -yc "Latencies" -yl "CPU Cycles" -z bar -d results/latencies -o results/membus_azure.eps
gv results/membus_azure.eps