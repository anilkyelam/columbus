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
    python analyze.py -i $expname; 
    if [ $? -ne 0 ]; then
        # ignore
        continue
    fi 

    fileparam="$fileparam -d out/$expname/pvalues.csv -l $expname"
done

# Generate pvalue CDF
mkdir -p plots
if [ -z "$plotname" ];  then    plotname=pvalues_cdf_$prefix;    fi
plot=plots/${plotname}.pdf
python plot.py -z cdf $fileparam -xl "log(PValues)" -yc "Pvalues" -o $plot -nm --xlog --vline=0.0005
# python plot.py -z cdf $fileparam -xl "Pvalues" -yc "Pvalues" -o $plot -nm 
echo "Plot at: $plot"
display $plot &