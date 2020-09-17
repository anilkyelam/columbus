#
# Analyze the pvalues of different experiments 
# to figure out the right pvalue threshold
#

prefix=$1
if [ -z "$prefix" ];  then    prefix=$(date +"%m-%d");    fi    # today
for d in `ls -d out/${prefix}*`; 
do 
    expname=`basename $d`; 
    echo $expname; 
    
    # Parse pvalues from log file into csv file
    python analyze.py -i $expname -pt; 
    if [ $? -ne 0 ]; then
        # ignore
        continue
    fi 

    fileparam="$fileparam -d out/$expname/pvalues.csv -l $expname"

    # Generate twin plot with pvalue and mean diff
    plotname=pvalue_vs_mean_$prefix;
    plot=out/$expname/${plotname}.pdf
    python plot.py -d out/$expname/pvalues.csv -xl "Entries" -yc "Mean Diff" -yc "Pvalue" -tw 2 --ylog -o $plot
    echo "Plot at: $plot"
    display $plot &
done

mkdir -p plots

# Generate pvalue CDF
plotname=pvalues_cdf_$prefix;
plot=plots/${plotname}.pdf
python plot.py -z cdf $fileparam -xl "log(PValues)" -yc "Pvalue" -o $plot -nt 1 -nh 1
# python plot.py -z cdf $fileparam -xl "Pvalues" -yc "Pvalues" -o $plot -nm 
echo "Plot at: $plot"
display $plot &

# # Generate mean diff CDF
plotname=meandiff_cdf_$prefix;
plot=plots/${plotname}.pdf
python plot.py -z cdf $fileparam -xl "Mean Diff (Cycles)" -yc "Mean Diff" --xlog -o $plot
echo "Plot at: $plot"
display $plot &

