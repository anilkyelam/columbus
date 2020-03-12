region="me-south-1"
number_of_victims=100
number_of_adv=100
account="diff"
uv="https://cocun088vc.execute-api.me-south-1.amazonaws.com/latest"
ua="https://0roo1pxdo2.execute-api.me-south-1.amazonaws.com/latest"
victim_size=128
adv_size=128

run_num=$1

#Account 2
#https://8x75yd2z29.execute-api.us-east-1.amazonaws.com/latest
#https://cocun088vc.execute-api.me-south-1.amazonaws.com/latest
#https://9mfzg99e6h.execute-api.sa-east-1.amazonaws.com/latest
#https://0roo1pxdo2.execute-api.me-south-1.amazonaws.com/latest - membus att
#https://cnk7vvk1w8.execute-api.us-east-1.amazonaws.com/latest - att

#Account1
#https://6fdhepb68i.execute-api.me-south-1.amazonaws.com/latest
#https://bq599d7eu2.execute-api.us-east-1.amazonaws.com/latest


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