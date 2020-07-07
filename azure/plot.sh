
python plot.py  -z bar -l "Azure" --fontsize=25 \
    -xc "Offset" -xl "Offset (Bytes)" \
    -yc "Latencies" -yl "" --ylim 8 --ymul 0.001 \
    -d results/latencies -o results/membus_azure.pdf
display results/membus_azure.pdf &

# GCP Placeholder
python plot.py  -z bar -l "GCP" --fontsize=25 \
    -xc "Offset" -xl "Offset (Bytes)" \
    -yc "Latencies" -yl "" --ylim 8 --ymul 0.001 \
    -d results/temp_gcp -o results/membus_gcp.pdf
display results/membus_gcp.pdf &