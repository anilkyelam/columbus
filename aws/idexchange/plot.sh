#!/bin/bash
# set -e  # stop on error


# Plot colocation clusters for each experiment
# Current candidates for the paper: 09-22-15-08, 09-22-15-15, 09-22-15-18, 09-22-15-21, 09-22-15-24, 09-22-01-34, 09-17-14-13
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
    plot=${dir}/colocation-$region.pdf
    python plot.py -z hist -l $region -fs 25 \
        -yc "Size" \
        -yl " " \
        -xl "Number of neighbors" \
        -o $plot -d ${dir}/clusters -of pdf
    echo "Plot at: $plot"
    cp $plot plots/
    display $plot &
done


# # Plot error rates for different lambda sizes
# # data from experiments: 09-22-01-02, 09-22-01-06, 09-22-01-09, 09-22-01-12, 09-22-01-16, 09-22-01-19
# # May need to repeat multiple times and get average but the numbers were consistent in general
# datafile=plots/errorrates.dat
# plot=plots/errorrates.pdf
# python plot.py -xc "Size" -xl "Lambda Size (MB)" -yc "Rate" -yl "Error rate" -fs 18 -z bar -cmi 2 \
#     -o $plot -d $datafile -of pdf
# echo "Plot at: $plot"
# display $plot &


# # Plot KS-values for different lambda sizes 
# # Data from experiments: 
# # 09-22-01-02, membus128
# # 09-22-01-06, membus256
# # 09-22-01-09, membus512
# # 09-22-01-12, membus1024
# # 09-22-01-16, membus1536
# # 09-22-01-19, membus3008
# # Assuming ksvalues.csv file is already generated for these runs. See ks-samples.sh
# plot=plots/ksvalues.pdf
# python plot.py -z cdf -xl "KS measure" -yc "KSvalue" -o $plot -fs 15 --vline 3 -nm \
#     -d out/09-22-01-02/ksvalues.csv -l "128 MB"     \
#     -d out/09-22-01-06/ksvalues.csv -l "256 MB"     \
#     -d out/09-22-01-09/ksvalues.csv -l "512 MB"     \
#     -d out/09-22-01-12/ksvalues.csv -l "1 GB"       \
#     -d out/09-22-01-16/ksvalues.csv -l "1.5 GB"     \
#     -d out/09-22-01-19/ksvalues.csv -l "3 GB"
# echo "Plot at: $plot"
# display $plot &


# # Plot colocation correltion between two experiments
# # Data from runs: 09-17-14-13, 09-17-14-07
# former=09-17-14-07
# latter=09-17-14-13
# plot=plots/correlation.pdf
# sizes=`jq '.Sizes[]' out/$former/stats.json`
# echo "Size" > out/$former/clusters
# echo "$sizes" >> out/$former/clusters
# sizes=`jq '.Sizes[]' out/$latter/stats.json`
# echo "Size" > out/$latter/clusters
# echo "$sizes" >> out/$latter/clusters
# python plot.py -z hist -fs 20 \
#     -d out/${former}/clusters -l "Run 1" \
#     -d out/${latter}/clusters -l "Run 2" \
#     -yc "Size" \
#     -yl "% of total lambdas" \
#     -xl "Number of neighbors" \
#     -o $plot -of pdf
# echo "Plot at: $plot"
# display $plot &


# # Plot run times for various lambda counts
# # data from experiments: NONE
# # May need to repeat multiple times and get average but the numbers were consistent in general
# datafile=plots/runtimes.dat
# plot=plots/runtimes.pdf
# python plot.py -xc "Count" -xl "Run Size (Lambda Count)" -yl "Time (secs)" -fs 20  --xstr \
#     -yc "Protocol Time" -l "FAKE DATA FOR NOW" \
#     -o $plot -d $datafile -of pdf
# echo "Plot at: $plot"
# display $plot &



# # Plot colocation densities in various regions
# # data from experiments: 09-22-15-08, 09-22-15-15, 09-22-15-18, 09-22-15-21, 09-22-15-24, 09-22-01-34, 09-17-14-13
# datafile=plots/density.dat
# plot=plots/density.pdf
# python plot.py -xc "Region" -xl " " -yl "Count" -fs 20 -z bar  --xstr \
#     -yc "Density" -l "Avg. Lambdas Per Server"\
#     -o $plot -d $datafile -of pdf
# echo "Plot at: $plot"
# display $plot &


# # # Get & Plot weekly and other variations in colocation density for regions
# # # Parse data from runs
# (bash show.sh 09-2[6-9] && bash show.sh 09-30 && bash show.sh 10-0[1-7] ) | grep 1000 | grep sa-east-1 | awk ' BEGIN {  print "Date,Density" } {  print substr($1,1,5)","$12} ' > plots/density-sa-east-1.dat
# (bash show.sh 09-2[6-9] && bash show.sh 09-30 && bash show.sh 10-0[1-7] ) | grep 1000 | grep us-east-2 | awk ' BEGIN {  print "Date,Density" } {  print substr($1,1,5)","$12} ' > plots/density-us-east-2.dat
# plot=plots/weekly-density.pdf
# python plot.py -xc "Date" -xl " " -yl "Density" -fs 15 --xstr   \
#     -d plots/density-sa-east-1.dat -yc "Density" -l "sa-east-1"     \
#     -d plots/density-us-east-2.dat  -l "us-east-2"     \
#     -o $plot -of pdf
# echo "Plot at: $plot"
# display $plot &