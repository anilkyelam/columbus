#
# Analyze the KS (Kolmogorov Smirinov) test values for 
# latency samples obtained in different experiments 
# to figure out the right threshold for 0/1-bit
#

prefix=$1
if [ -z "$prefix" ];  then    prefix=$(date +"%m-%d");    fi    # today
for d in `ls -d out/${prefix}*`; 
do 
    expname=`basename $d`; 
    echo $expname; 
    
    # Parse pvalues from log file into csv file
    python analyze.py -i $expname -ks; 
    if [ $? -ne 0 ]; then
        # ignore
        continue
    fi 

    fileparam="$fileparam -d out/$expname/ksvalues.csv -l $expname"

    # # Generate twin plot with pvalue and mean diff
    # plotname=kstest_$prefix;
    # plot=out/$expname/${plotname}.pdf
    # python plot.py -d out/$expname/pvalues.csv -xl "Entries" -yc "Mean Diff" -yc "Pvalue" -tw 2 --ylog -o $plot
    # echo "Plot at: $plot"
    # display $plot &
done

mkdir -p plots

# # Generate KS Statistic CDF
# plotname=ksmax_cdf_$prefix;
# plot=plots/${plotname}.pdf
# python plot.py -z cdf $fileparam -xl "KS Max Statistic" -yc "KS Max" -o $plot -ll rightout -fs 11
# # python plot.py -z cdf $fileparam -xl "Pvalues" -yc "Pvalues" -o $plot -nm 
# echo "Plot at: $plot"
# display $plot &

# Generate KS Statistic CDF
plotname=ks_smean_cdf_$prefix;
plot=plots/${plotname}.pdf
python plot.py -z cdf $fileparam -xl "KS Shallow Mean Statistic" -yc "KS SMean" -o $plot -ll rightout -fs 11 --vline 3  #--xlog
# python plot.py -z cdf $fileparam -xl "Pvalues" -yc "Pvalues" -o $plot -nm 
echo "Plot at: $plot"
display $plot &

# # Generate KS Statistic CDF
# plotname=ks_dmean_cdf_$prefix;
# plot=plots/${plotname}.pdf
# python plot.py -z cdf $fileparam -xl "KS Deep Mean Statistic" -yc "KS DMean" -o $plot -ll rightout -fs 11 #--xlog
# # python plot.py -z cdf $fileparam -xl "Pvalues" -yc "Pvalues" -o $plot -nm 
# echo "Plot at: $plot"
# display $plot &

# # Generate CVM Statistic CDF
# plotname=cvmtest_cdf_$prefix;
# plot=plots/${plotname}.pdf
# python plot.py -z cdf $fileparam -xl "CVM Statistic" -yc "CVM" -o $plot -ll rightout -fs 11
# # python plot.py -z cdf $fileparam -xl "Pvalues" -yc "Pvalues" -o $plot -nm 
# echo "Plot at: $plot"
# display $plot &

# # # Generate mean diff CDF
# plotname=meandiff_cdf_$prefix;
# plot=plots/${plotname}.pdf
# python plot.py -z cdf $fileparam -xl "Mean Diff (Cycles)" -yc "Mean Diff" --xlog -o $plot
# echo "Plot at: $plot"
# display $plot &