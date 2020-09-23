#
# Get & plot samples of latencies in different regions and kinds of lambdas 
# to make an informed guess on proper p-value threshold
#

# Plot base 0-bit & 1-bit latencies, different CDF curve for each sample
function plot_each() {
    outdir=$1
    plotname=$2
    # get base and 1-bit latency data files for plotting
    fileparam=""
    files=$(find $outdir -name 'base_samples*')
    while read -r i; do
        base=$(basename $i)
        label=${base/#"samples"} 
        fileparam="$fileparam -d $i -l $label -cmi 0 -li 0"
        # echo "$i $base"
    done <<< "$files"

    labelincr=1
    files=$(find $outdir -name 'bit0_samples*')
    while read -r i; do
        base=$(basename $i)
        label=${base/#"samples"} 
        fileparam="$fileparam -d $i -l $label -cmi $labelincr -li $labelincr"
        labelincr=0
        # echo "$i $base"
    done <<< "$files"

    labelincr=1
    files=$(find $outdir -name 'bit1_samples*')
    while read -r i; do
        base=$(basename $i)
        label=${base/#"samples"} 
        fileparam="$fileparam -d $i -l $label -cmi $labelincr -li $labelincr"
        labelincr=0
        # echo "$i $base"
    done <<< "$files"

    # Plot regular samples
    mkdir -p plots
    if [ -z "$plotname" ];  then    plotname=`basename $outdir`;    fi
    plot=plots/${plotname}.pdf
    python plot.py -z cdf $fileparam -xl "Latency (Cycles)" -yc "Latencies" -o $plot -nm -nt 5 -ll none
    echo "Plot at: $plot"
    display $plot &
}


# Plot base 0-bit & 1-bit latencies, different CDF curve for each sample
# for samples reclassified with KS-statistic 
function plot_each_ks() {
    outdir=$1
    plotname=$2
    expname=$3
        
    # Do KS-statistic analysis for the experiment
    # this prepares re-classified samples
    python analyze.py -i $expname -ks; 

    ksdir="$outdir/ksmetric"
    if [ ! -d "$ksdir" ] 
    then
        echo "No samples with KS statisic at $ksdir."
        return
    fi

    # get base and 1-bit latency data files for plotting
    fileparam=""
    files=$(find $outdir -name 'base_samples*')
    while read -r i; do
        base=$(basename $i)
        label=${base/#"samples"} 
        fileparam="$fileparam -d $i -l $label -cmi 0 -li 0"
        # echo "$i $base"
    done <<< "$files"

    labelincr=1
    files=$(find $ksdir -name 'bit0_samples*')
    while read -r i; do
        base=$(basename $i)
        label=${base/#"samples"} 
        fileparam="$fileparam -d $i -l $label -cmi $labelincr -li $labelincr"
        labelincr=0
        # echo "$i $base"
    done <<< "$files"

    labelincr=1
    files=$(find $ksdir -name 'bit1_samples*')
    while read -r i; do
        base=$(basename $i)
        label=${base/#"samples"} 
        fileparam="$fileparam -d $i -l $label -cmi $labelincr -li $labelincr"
        labelincr=0
        # echo "$i $base"
    done <<< "$files"

    # Plot regular samples
    mkdir -p plots
    if [ -z "$plotname" ];  then    plotname=`basename $outdir`;    fi
    plot=plots/${plotname}.pdf
    python plot.py -z cdf $fileparam -xl "Latency (Cycles)" -yc "Latencies" -o $plot -nm -nt 5 -ll none -t "Applied KS Statistic"
    echo "Plot at: $plot"
    display $plot &
}


# Plot base & 1-bit latencies, one CDF curve
function combine() {
    outdir=$1
    plotname=$2

    # combine base and 1-bit latency data files into one file
    cat ${outdir}/base_samples* >  ${outdir}/all_base_samples
    sed -i '/Latencies/d'  ${outdir}/all_base_samples 
    sed -i '1 i\Latencies'  ${outdir}/all_base_samples 
    
    cat  ${outdir}/bit_samples* >  ${outdir}/all_bit_samples
    sed -i '/Latencies/d'  ${outdir}/all_bit_samples 
    sed -i '1 i\Latencies'  ${outdir}/all_bit_samples 

    # Plot
    mkdir -p plots
    if [ -z "$plotname" ];  then    plotname=`basename $outdir`;    fi
    plot=plots/${plotname}_combined.pdf
    python plot.py -z cdf -xl "Latency (Cycles)" -yc "Latencies" -o $plot -nm -nt 5 \
        -d "${outdir}/all_bit_samples" -l "1-Bit"   -ls solid   \
        -d "${outdir}/all_base_samples" -l "Baseline" -ls dashed 
    echo "Plot at: $plot"
    display $plot &
}

# Main()
# region=me-south-1
# for size in 128 512 1024 1536 3008; do
# # for size in 3008; do

#     # Setup & run lambdas
#     # echo Region: $region, Lambda Size: ${size}MB
#     # outdir=latrun-$(date +%m-%d-%H-%M)-${size}
#     # aws configure set region $region
#     # bash setup.sh -n=membus${size} -s=${size}
#     # python3 invoke.py --name=membus${size} --count=100 --phases=1 --outdir=${outdir} --samples
#     # echo "Lat samples 1-bit, ${size} MB, $region" > out/$outdir/desc

#     # # Or just use previous results
#     # outdir=$(basename out/latrun-07-06-*-${size})

#     # # Plot each sample separately
#     # plot_each "out/$outdir" "$outdir"

#     # Plot one
#     # plot_one "out/$outdir" "$outdir"
# done

# Find 
expname=$1
if [ -z "$expname" ];  then  expname=$(ls -t out/ | head -n1);    fi
plot_each "out/$expname" "samples_$expname"
# plot_each_ks "out/$expname" "ks_samples_$expname" "$expname"


# # Final plot for context switching
# plot=plots/lambda_sched_effect.pdf
# prefix="latrun-07-06-*-"
# bit128=$(ls out/latrun-07-06-*-128/all_bit_samples)
# bit512=$(ls out/latrun-07-06-*-512/all_bit_samples)
# bit1024=$(ls out/latrun-07-06-*-1024/all_bit_samples)
# bit1536=$(ls out/latrun-07-06-*-1536/all_bit_samples)
# bit3008=$(ls out/latrun-07-06-*-3008/all_bit_samples)
# base3008=$(ls out/latrun-07-06-*-3008/all_base_samples)
# python plot.py -z cdf -xl "Latency (Cycles)" -yc "Latencies" -o $plot -nm --xlim 30000 \
#     -d ${bit128}    -l "128 MB"     -ls solid   \
#     -d ${bit1024}   -l "1 GB"       -ls solid   \
#     -d ${bit3008}   -l "3 GB"       -ls solid   \
#     -d ${base3008}  -l "No contention"   -ls dashed  
# echo "Plot at: $plot"
# display $plot &
