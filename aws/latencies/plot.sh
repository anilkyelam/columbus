python plot.py  -z bar -l "AWS"  --fontsize=25 --lloc=topleft \
    -xc "Offset" -xl "Offset (Bytes)" \
    -yc "Latencies" -yl "CPU Cycles" --ylim 8000 --ylog \
    -d latencies -o membus_aws.pdf
display membus_aws.pdf