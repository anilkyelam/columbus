lambdas=(101 303 510 950)       #from run.sh

phase=$1
round=$2

file=data/results_${lambda}_${phase}_${round}
base=data/results_base_${lambda}_0_0

# Include all baseline curves
for lambda in ${lambdas[@]}; do
    base=data/results_base_${lambda}_0_0
    if [ -f "$base" ]; then
        plots="${plots} -d ${base}  -l 'L${lambda} - Base' -ls dashed "
    else
        echo "Base results file $file not found, moving on"
    fi
done 

for lambda in ${lambdas[@]}; do
    data=data/results_${lambda}_${phase}_${round}
    if [ -f "$data" ]; then
        plots="${plots} -d ${data}  -l 'L${lambda}' "
    else
        echo "Data results file $file not found, moving on"
    fi
done

desc="CDF of sampled latencies (Phase:${phase},Round:${round} vs Baseline)"
outfile=results/latcdf_${phase}_${round}.eps
outfile_nt=results/latcdf_${phase}_${round}_nt.eps      #no tail version
eval "python plot.py -t \"$desc\" -yc 'Cycles' -xl 'Latency (Cycles)' -yl 'CDF' -z cdf -nm -o ${outfile} ${plots} " 1> /dev/null
eval "python plot.py -t \"$desc\" -yc 'Cycles' -xl 'Latency (Cycles)' -yl 'CDF' -z cdf -nm -o ${outfile_nt} ${plots} -nt " 1> /dev/null
gv ${outfile} &
gv ${outfile_nt} &
