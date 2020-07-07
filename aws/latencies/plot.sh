python plot.py  -z bar -l "AWS" \
    -xc "Offset" -xl "Offset (Bytes)" \
    -yc "Latencies" -yl "Kilo CPU Cycles" --ylim 8 --ymul 0.001 \
    -d latencies -o membus_aws.pdf
display membus_aws.pdf