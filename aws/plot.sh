#!/bin/bash
# set -e  # stop on error


# Plot colocation clusters for each experiment
# Current candidates for the paper: 09-22-15-08, 09-22-15-15, 09-22-15-18, 09-22-15-21, 09-22-15-24, 09-22-01-34, 09-17-14-13
# prefix=$1
# if [ -z "$prefix" ];  then    prefix=$(date +"%m-%d");    fi    # today
# for f in `ls -d out/${prefix}*/stats.json`
# do
#     echo $f
#     dir=`dirname $f`
#     region=`jq '.Region' $f | tr -d '"'`
#     count=`jq '.Count' $f`
#     clusters=`jq '.Clusters' $f`
#     errorrate=`jq '."Error Rate"' $f`
#     sizes=`jq '.Sizes[]' $f`
#     errors=`echo $count $errorrate | awk '{print $1*$2/100.0}'`
#     echo "Size" > $dir/clusters
#     echo "$sizes" >> $dir/clusters
#     echo $region, $count, $clusters, $errorrate
    
#     # Plot
#     plot=${dir}/colocation-$region.pdf
#     python plot.py -z hist -l $region -fs 25 --xmax=15 \
#         -yc "Size" \
#         -yl " % of lambdas " \
#         -xl "Number of neighbors" \
#         -o $plot -d ${dir}/clusters -of pdf
#     echo "Plot at: $plot"
#     cp $plot plots/
#     display $plot &
# done


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
# python plot.py -z cdf -xl "KS measure" -yc "KSvalue" -nm -o $plot -fs 18 --vline 3  \
#     -d out/09-22-01-02/ksvalues.csv -l "128 MB" -ls densedot       \
#     -d out/09-22-01-06/ksvalues.csv -l "256 MB" -ls dashdot      \
#     -d out/09-22-01-09/ksvalues.csv -l "512 MB" -ls dash     \
#     -d out/09-22-01-12/ksvalues.csv -l "1 GB"   -ls densedash      \
#     -d out/09-22-01-16/ksvalues.csv -l "1.5 GB" -ls dashdotdot    \
#     -d out/09-22-01-19/ksvalues.csv -l "3 GB"   -ls solid
# echo "Plot at: $plot"
# display $plot &


# # Plot colocation correltion between two experiments
# # Data from runs: 09-17-14-13, 09-17-14-07
# # former=09-17-14-07
# # latter=09-17-14-13
# former=10-13-23-34
# latter=10-13-23-38
# plot=plots/correlation.pdf
# sizes=`jq '.Sizes[]' out/$former/stats.json`
# echo "Size" > out/$former/clusters
# echo "$sizes" >> out/$former/clusters
# sizes=`jq '.Sizes[]' out/$latter/stats.json`
# echo "Size" > out/$latter/clusters
# echo "$sizes" >> out/$latter/clusters
# python plot.py -z hist -fs 18 \
#     -d out/${former}/clusters -l "Run 1" \
#     -d out/${latter}/clusters -l "Run 2" \
#     -yc "Size" \
#     -yl "% of total lambdas" \
#     -xl "Number of neighbors" \
#     -o $plot -of pdf
# echo "Plot at: $plot"
# display $plot &


# # Plot run times for various lambda counts
# # data from experiments: 10-16-16-[46 to 58]
# datafile=plots/runtimes.dat
# plot=plots/runtimes.pdf
# python plot.py -xc "Count" -xl "Run Size (Lambda Count)" -yl "Time (secs)" -fs 18 --xstr -z bar \
#     -yc "Protocol Time" -ll none \
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


# # Plot non-singleton clusters in various regions
# # data from experiments: 09-22-15-08, 09-22-15-15, 09-22-15-18, 09-22-15-21, 09-22-15-24, 09-22-01-34, 09-17-14-13
# datafile=plots/cluster.dat
# plot=plots/clusters.pdf
# python plot.py -xc "Region" -xl " " -yl "Count" -z bar -fs 18 --ymax 400  --xstr \
#     -yc "Clusters" -l "Non-singleton co-resident groups"\
#     -o $plot -d $datafile -of pdf
# echo "Plot at: $plot"
# display $plot &


# # Get & Plot daily and hourly variations in colocation density for regions
# # Daily density
# (bash show.sh 09-2[6-9] && bash show.sh 09-30) | grep 1000 | grep sa-east-1 | awk ' BEGIN {  print "Date,Density" } {  print substr($1,1,5)","$9} ' > plots/density-sa-east-1-daily1.dat
# (bash show.sh 09-2[6-9] && bash show.sh 09-30) | grep 1000 | grep us-east-2 | awk ' BEGIN {  print "Date,Density" } {  print substr($1,1,5)","$9} ' > plots/density-us-east-2-daily1.dat
# (bash show.sh 10-0[2-6] ) | grep 1000 | grep sa-east-1 | awk ' BEGIN {  print "Date,Density" } {  print substr($1,1,5)","$9} ' > plots/density-sa-east-1-daily2.dat
# (bash show.sh 10-0[2-6] ) | grep 1000 | grep us-east-2 | awk ' BEGIN {  print "Date,Density" } {  print substr($1,1,5)","$9} ' > plots/density-us-east-2-daily2.dat
# plot=plots/daily-density.pdf
# python plot.py -xc "Date" -xl " " -yl "Average Density" -yc "Density" -fs 15 --xstr --ymin 0 --ymax 8 \
#     -d plots/density-us-east-2-daily1.dat -l "US East, Week 1"     \
#     -d plots/density-us-east-2-daily2.dat -l "US East, Week 2"     \
#     -d plots/density-sa-east-1-daily1.dat -l "SA East, Week 1"     \
#     -d plots/density-sa-east-1-daily2.dat -l "SA East, Week 2"     \
#     -o $plot -of pdf
# echo "Plot at: $plot"
# display $plot &

# # Hourly density
# bash show.sh 10-15-*-25 | grep "us-east-2" | grep membus1536 | grep 1000 | awk ' BEGIN {  print "Date,Density" } {  print substr($1,1,8)","$9} ' > plots/density-us-east-2-hourly1.dat
# bash show.sh 10-16-*-25 | grep "us-east-2" | grep membus1536 | grep 1000 | awk ' BEGIN {  print "Date,Density" } {  print substr($1,1,8)","$9} ' > plots/density-us-east-2-hourly2.dat
# plot=plots/hourly-density.pdf
# python plot.py -xc "Date" -xl " " -yl "Avgerage Density" -yc "Density" -fs 15 --xstr --ymin 0 --ymax 5.5  \
#     -d plots/density-us-east-2-hourly1.dat -l "Day 1"     \
#     -d plots/density-us-east-2-hourly2.dat -l "Day 2"    \
#     -o $plot -of pdf
# echo "Plot at: $plot"
# display $plot &


# # Plot percentage of lambdas in each colocated cluster when different accounts are used
# two_acc_run=10-08-01-19
# python analyze.py -i $two_acc_run --dataaz
# plot=plots/different-accounts.pdf
# python plot.py -xc "Cluster" -xl "Group Size" -yl "Percentage" -d out/$two_acc_run/tags.csv -fs 18 --ymax 125     \
#     -yc "Tag 0 %" -l "Account 0"    \
#     -yc "Tag 1 %" -l "Account 1"    \
#     -z barstacked -o $plot -of pdf
# echo "Plot at: $plot"
# display $plot &


# # # Plot percentage of lambdas in each colocated cluster when different lambda sizes are used
# two_size_run=10-19-02-06
# python analyze.py -i $two_size_run --dataaz
# plot=plots/different-sizes.pdf
# python plot.py -xc "Cluster" -xl "Group Size" -yl "Percentage" -d out/$two_size_run/tags.csv -fs 18  --ymax=125     \
#     -yc "Tag 0 %" -l "1.5 GB Lambdas"    \
#     -yc "Tag 1 %" -l "2 GB Lambdas"     \
#     -z barstacked -o $plot -of pdf
# echo "Plot at: $plot"
# display $plot &

# # Plot channel errors and capacity
plot=plots/channel_rate_3gb.pdf
python plot.py -o $plot -yl "Errors %" -tyl "Rate (bits per sec)" --xlog  --twin 3  -fs 18    \
    -dyc out/chstats_membus3008 "Byte Errors Mean" -l "Byte Errors, Mean"         -ls dash       \
    -dyc out/chstats_membus3008 "Byte Errors 95per" -l "Byte Errors, 95%"         -ls dashdot        \
    -dyc out/chstats_membus3008 "Effective Rate 95per" -l "Effective Bit Rate (Goodput)"     -ls solid              \
    -xc "Channel Rate" -xl "Raw Bit Rate (bps)" 
echo "Plot at: $plot"
display $plot &

