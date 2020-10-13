
gcp_file=results/gcp.csv
offset_correction=-9
egrep -o "Total average cycles spent:  ([0-9]+)" $gcp_file| awk 'BEGIN{ print "Offset,Latencies" } { print NR+'$offset_correction'","$5 }' > results/latencies

python plot.py  -z bar -l "GCP" --fontsize=25 --lloc=topleft  \
    -xc "Offset" -xl "Offset (Bytes)" \
    -yc "Latencies" -yl " " --ylim 8000 --ylog \
    -d results/latencies -o results/membus_gcp.pdf
display results/membus_gcp.pdf &
