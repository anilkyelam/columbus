#!/bin/bash
# set -e  # stop on error

resdir=$1
desc=$2
plotname=$3
if ! [[ $resdir ]]; then
    # Pick latest under "out"
    resdir=$(find out/ -maxdepth 1 -name '[0-9][0-9]-[0-9][0-9]*' | sort | tail -n1)
fi

# if desc is provided, save it too
if [[ $desc ]]; then
    echo "$desc" > $resdir/desc
fi

# get data files
files=$(find $resdir -name 'base_samples*')
while read -r i; do
    base=$(basename $i)
    label=${base/#"samples"} 
    fileparam="$fileparam -d $i -l $label -cmi 0 -li 0"
    # echo "$i $base"
done <<< "$files"

labelincr=1
files=$(find $resdir -name 'bit_samples*')
while read -r i; do
    base=$(basename $i)
    label=${base/#"samples"} 
    fileparam="$fileparam -d $i -l $label -cmi $labelincr -li $labelincr"
    labelincr=0
    # echo "$i $base"
done <<< "$files"

mkdir -p plots
if [ -z "$plotname" ];  then    plotname=`basename $resdir`;    fi
plot=plots/${plotname}.png
python plot.py -z cdf $fileparam -t "$desc" -xl "Latency (Cycles)" -yc "Latencies" -o $plot -nm -nt 5 -ll none
echo "Plot at: $plot"
# gv $plot
display $plot
