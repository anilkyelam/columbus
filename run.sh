# Parameters
accountid=017371402075
lambdafn=membus

# region=me-south-1
# region=us-west-2
# region=us-east-2
region=ca-central-1
# region=sa-east-1
# region=eu-west-2
# region=eu-west-3
# region=ap-east-1
# region=ap-south-1
# region=eu-north-1
region=$1
run_num=3
lambda_num=$2
#lambda_num=200
#url="https://bhoisf0ri8.execute-api.sa-east-1.amazonaws.com/latest"
#url="https://uux88xb5mh.execute-api.eu-west-2.amazonaws.com/latest"


# Create everything
if [ -z "$url" ]; then

    # Set region
    aws configure set region ${region}

    # Build code and Create function on AWS
    bash functions/cpp/deploy.sh --create

    # Create and test API gateway
    # https://docs.aws.amazon.com/lambda/latest/dg/with-on-demand-https-example.html
    apid=$(aws apigateway create-rest-api --name $lambdafn --endpoint-configuration types=REGIONAL | jq -r ".id")
    resourceid=$(aws apigateway get-resources --rest-api-id $apid | jq -r ".items[].id")

    aws apigateway put-method --rest-api-id $apid --resource-id $resourceid \
        --http-method POST --authorization-type NONE

    aws apigateway put-integration --rest-api-id $apid --resource-id $resourceid \
        --http-method POST --type AWS --integration-http-method POST \
        --uri arn:aws:apigateway:$region:lambda:path/2015-03-31/functions/arn:aws:lambda:$region:$accountid:function:$lambdafn/invocations

    aws apigateway put-method-response --rest-api-id $apid \
        --resource-id $resourceid --http-method POST \
        --status-code 200 --response-models application/json=Empty

    aws apigateway put-integration-response --rest-api-id $apid \
        --resource-id $resourceid --http-method POST \
        --status-code 200 --response-templates application/json=""

    aws lambda add-permission --function-name $lambdafn \
        --statement-id apigateway-test-$apid --action lambda:InvokeFunction \
        --principal apigateway.amazonaws.com \
        --source-arn "arn:aws:execute-api:$region:$accountid:$apid/*/*/"

    aws lambda add-permission --function-name $lambdafn \
        --statement-id apigateway-latest-$apid --action lambda:InvokeFunction \
        --principal apigateway.amazonaws.com \
        --source-arn "arn:aws:execute-api:$region:$accountid:$apid/latest/*/"

    aws apigateway create-deployment --rest-api-id $apid --stage-name latest

    # final url
    url="https://${apid}.execute-api.${region}.amazonaws.com/latest"
    echo $url
fi

# check if url works
curlout=$(curl -s -X POST ${url} | jq -r '.Role // ""')
if [ -z "$curlout" ]; then 
    echo "ERROR! API not setup properly"; 
    exit -1;
fi

echo "URL verified succesfully, starting lambda runs"

# Deploy lambdas, with and without thrashers
outdir=results/membus/${region}
mkdir $outdir
python api/awsapi2.py -u ${url} -c ${lambda_num} -o ${outdir}/no-thrashers-${run_num}.csv
python api/awsapi2.py -u ${url} -c ${lambda_num} -o ${outdir}/with-thrashers-${run_num}.csv -a

# Plot
/usr/bin/python plot.py -z scatter -t "Region: $region, Num Lambdas: $lambda_num" \
    -yc "Difference" -xl "Function Number" -yl "CPU Kilo Cycles" \
    -d ${outdir}/with-thrashers-${run_num}.csv -l "With Adversary" \
    -d ${outdir}/no-thrashers-${run_num}.csv -l "Without Adversary" \
    -o ${outdir}/plot-${run_num}.png &

numfile=results/membus/numbers
echo $region, $lambda_num >> $numfile
/usr/bin/python plot.py -p -yc "Difference" \
    -d ${outdir}/no-thrashers-${run_num}.csv \
    -d ${outdir}/with-thrashers-${run_num}.csv >> $numfile

# /usr/bin/python plot.py -z scatter \
#     -yc "Difference" -xl "Function Number" -yl "CPU Kilo Cycles" \
#     -d ${outdir}/with-thrasher-${run_num}.csv -l "With Adversary" \
#     -d ${outdir}/no-thrasher-${run_num}.csv -l "Without Adversary" \
#     -o ${outdir}/plot-${run_num}.png

# /usr/bin/python plot.py -p \
#     -yc "Difference" -xl "Function Number" -yl "CPU Cycles" \
#     -d ${outdir}/with-thrasher-${run_num}.csv -l "With Adversary" \
#     -d ${outdir}/no-thrasher-${run_num}.csv -l "Without Adversary" 