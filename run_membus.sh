region="me-south-1"
number_of_victims=10
number_of_adv=10
account="same"
uv="https://cocun088vc.execute-api.me-south-1.amazonaws.com/latest"
ua="https://cocun088vc.execute-api.me-south-1.amazonaws.com/latest"
victim_size=128
adv_size=128

run_num=$1


outdir=results/membus/${region}
mkdir $outdir
outdir=results/membus/${region}/${number_of_victims}_${victim_size}_${number_of_adv}_${adv_size}_${account}
mkdir $outdir
python3 api/awsapi_membus.py -nv $number_of_victims -uv $uv -ua $ua -o ${outdir}/no_thrashers_${run_num}.csv
python3 api/awsapi_membus.py -nv $number_of_victims -na $number_of_adv -uv $uv -ua $ua -o ${outdir}/thrashers_${run_num}.csv -a
sleep 5
python3 plot.py -z scatter -t "Region: $region, Num Lambdas: $number_of_victims" \
    -yc "Difference" -xl "Function Number" -yl "CPU Kilo Cycles" \
    -d ${outdir}/thrashers_${run_num}.csv -l "With Adversary" \
    -d ${outdir}/no_thrashers_${run_num}.csv -l "Without Adversary" \
    -o ${outdir}/plot-${run_num}.png &

numfile=results/membus/numbers
echo $region, $number_of_victims >> $numfile
python3 plot.py -p -yc "Difference" \
    -d ${outdir}/no_thrashers_${run_num}.csv \
    -d ${outdir}/thrashers_${run_num}.csv >> $numfile