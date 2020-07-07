#!/bin/bash
# set -e  # stop on error

for f in `ls out/05-21-15-*/stats.json`; do
    echo $f
    dir=`dirname $f`
    region=`jq '.Region' $f | tr -d '"'`
    count=`jq '.Count' $f`
    clusters=`jq '.Clusters' $f`
    errorrate=`jq '."Error Rate"' $f`
    sizes=`jq '.Sizes[]' $f`
    errors=`echo $count $errorrate | awk '{print $1*$2/100.0}'`
    # echo "Size" > $dir/clusters
    # echo "$sizes" >> $dir/clusters
    echo $region, $count, $clusters, $errors
    
    # Plot
    plot=${dir}/colocation-$region.pdf
    python plot.py -z hist -l $region --fontsize=25 \
        -xl "Cluster Size" \
        -yc "Size" --ylim 150 \
        -o $plot -d ${dir}/clusters
    echo "Plot at: $plot"
    display $plot &
done
