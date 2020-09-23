#!/bin/bash
# set -e  # stop on error

prefix=$1
if [ -z "$prefix" ];  then    prefix=$(date +"%m-%d");    fi    # today
for f in `ls -d out/${prefix}*/stats.json`
do
    echo $f
    dir=`dirname $f`
    region=`jq '.Region' $f | tr -d '"'`
    count=`jq '.Count' $f`
    clusters=`jq '.Clusters' $f`
    errorrate=`jq '."Error Rate"' $f`
    sizes=`jq '.Sizes[]' $f`
    errors=`echo $count $errorrate | awk '{print $1*$2/100.0}'`
    echo "Size" > $dir/clusters
    echo "$sizes" >> $dir/clusters
    echo $region, $count, $clusters, $errorrate
    
    # Plot
    plot=${dir}/colocation-$region.png
    python plot.py -z hist -l $region \
        -yc "Size" \
        -yl "% of total lambdas" \
        -xl "Number of neighbors" \
        -o $plot -d ${dir}/clusters -of png
    echo "Plot at: $plot"
    display $plot &
done


# # Plot error rates for different lambda sizes
# # data from experiments: 09-22-01-02, 09-22-01-06, 09-22-01-09, 09-22-01-12, 09-22-01-16, 09-22-01-19
# # May need to repeat multiple times and get average but the numbers were consistent in general
# datafile=plots/errorrates.dat
# plot=plots/errorrates.png
# python plot.py -xc "Size" -xl "Lambda Size (MB)" -yc "Rate" -yl "Error rate" \
#     -o $plot -d $datafile -of png
# echo "Plot at: $plot"
# display $plot &
