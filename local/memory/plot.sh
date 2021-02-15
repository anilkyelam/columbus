# python plot.py -z cdf -yc "Time" --xmin 0 --xmax 100  \
#     -d time_caches1 -l "Mostly caches"  \
#     -d time_caches2 -l "Mostly caches"  \
#     -d time_caches2 -l "Mostly DRAM"  \
#     -o access_times.png -of png -nm
# display access_times.png &

python plot.py -z cdf -yc "Time" -nt 1 \
    -d time_caches -l "Mostly caches"  \
    -d time_dram   -l "Mostly DRAM"  \
    -o access_times.png -of png -nm
display access_times.png &

