#!/bin/bash
# set -e  # stop on error

resdir=$1
if ! [[ $resdir ]]; then
    # Pick latest under "out"
    resdir=$(find out/ -maxdepth 1 -name '[0-9][0-9]-[0-9][0-9]*' | sort | tail -n1)
fi

# get data files
files=$(find $resdir -name 'samples*')
while read -r i; do
    base=$(basename $i)
    label=${base/#"samples"} 
    fileparam="$fileparam -d $i -l $label"
    # echo "$i $base"
done <<< "$files"

mkdir -p plots
plot=plots/$(basename $resdir).png
python plot.py -z cdf $fileparam -yc "Latencies" -o $plot -nm -nt 5
echo "Plot at: $plot"
# gv $plot
display $plot
