
python plot.py  -z bar -l "Azure" --fontsize=25 --lloc=topleft  \
    -xc "Offset" -xl "Offset (Bytes)" \
    -yc "Latencies" -yl "" --ylim 8000 --ylog \
    -d results/latencies -o results/membus_azure.pdf
display results/membus_azure.pdf &

# GCP Placeholder
python plot.py  -z bar -l "GCP" --fontsize=25 --lloc=topleft  \
    -xc "Offset" -xl "Offset (Bytes)" \
    -yc "Latencies" -yl "" --ylim 8000 --ylog \
    -d results/temp_gcp -o results/membus_gcp.pdf
display results/membus_gcp.pdf &