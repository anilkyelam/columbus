region="me-south-1"
number_of_victims=15
number_of_adv=13
account="diff"
membus_fn="thrashers"
uv="https://gvfsks9m4g.execute-api.me-south-1.amazonaws.com/latest"
ua="https://4h76vgrbt7.execute-api.me-south-1.amazonaws.com/latest"
victim_size=128
adv_size=3008

run_num=$1
interval_length=$2

#Account 2
#https://9mfzg99e6h.execute-api.sa-east-1.amazonaws.com/latest
#https://cocun088vc.execute-api.me-south-1.amazonaws.com/latest
#https://0roo1pxdo2.execute-api.me-south-1.amazonaws.com/latest - att
#https://8x75yd2z29.execute-api.us-east-1.amazonaws.com/latest
#https://cnk7vvk1w8.execute-api.us-east-1.amazonaws.com/latest - att
#https://s7u2d2f790.execute-api.ap-south-1.amazonaws.com/latest
#https://sf5bp0uega.execute-api.ap-south-1.amazonaws.com/latest - att
#https://5t4jprsnw2.execute-api.me-south-1.amazonaws.com/latest - membus 3 att

#Account1
#https://6fdhepb68i.execute-api.me-south-1.amazonaws.com/latest
#https://bq599d7eu2.execute-api.us-east-1.amazonaws.com/latest
#https://8f124zfh83.execute-api.ap-south-1.amazonaws.com/latest
#https://2chp3eabd6.execute-api.me-south-1.amazonaws.com/latest membus 3
#https://aryln2lfpi.execute-api.me-south-1.amazonaws.com/latest - sampler

#Account2
#https://shpxmboh50.execute-api.ap-south-1.amazonaws.com/latest

#Thrashers Account 2
#https://0rtf63ovd7.execute-api.me-south-1.amazonaws.com/latest

#Sampler Account 2
#https://gub3hmvfr5.execute-api.me-south-1.amazonaws.com/latest


outdir=results/membus/${region}
mkdir $outdir
outdir=results/membus/${region}/${membus_fn}_${number_of_victims}_${victim_size}_${number_of_adv}_${adv_size}_${account}
mkdir $outdir
python3 api/awsapi_membus.py -nv $number_of_victims -na $number_of_adv -uv $uv -ua $ua -o ${outdir}/no_thrashers_${run_num}.csv -i $interval_length
python3 api/awsapi_membus.py -nv $number_of_victims -na $number_of_adv -uv $uv -ua $ua -o ${outdir}/thrashers_${run_num}.csv -i $interval_length -a

