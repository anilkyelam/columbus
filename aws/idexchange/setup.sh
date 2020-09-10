#!/bin/bash
# set -e  # stop on error

#
# Sets up a lamnbda function and an API gateway to trigger it
#
# === Prerequisites ====
# 1. AWS CLI. (sudo apt install awscli)
# 2. Install AWS Lambda cpp SDK: https://github.com/awslabs/aws-lambda-cpp
# 3. Login to AWS: run "aws configure". Admin access recommended for no-hassle runs.
# 4. Json tool "jq". (sudo apt install jq)
# 5. Run the script once with --setup option for other one-time setup stuff


# Parse command line arguments
for i in "$@"
do
case $i in
    -s|--setup)            # one-time setup
    SETUP=1
    ;;
    
    -a=*|--account=*)       # Account id, defaults to cli account
    accountid="${i#*=}"
    ;;
    
    -n=*|--name=*)          # Function name, defaults to 'membusv21'
    lambdafn="${i#*=}"
    ;;
    
    -s=*|--size=*)          # Function size in MB. Multiples of 64MB, from 128-3008. Defaults to 128
    SIZE="${i#*=}"
    ;;
        
    -r=*|--region=*)        # Region name, defaults to cli region
    region="${i#*=}"
    ;;

    -f|--force)             # force create apu trigger, even if one exists
    FORCE=1
    ;;

    *)                      # unknown option
    ;;
esac
done

# Defaults
lambdafn=${lambdafn:-membusv21}    # Default lambda name
SIZE=${SIZE:-128}
S3PREFIX=lambda-cpp-

# Get account id from aws cli if not set
if [ -z ${accountid+x} ]; then
    accountid=$(aws sts get-caller-identity | jq -r ".Ac`count")
    if [ -z "${accountid}" ]; then
        # Still not set
        echo "ERROR! Cannot figure out account id"
        exit 1
    fi
fi

# Get region name from aws cli if not set
if [ -z ${region+x} ]; then
    region=$(aws configure get region)
    if [ -z "${region}" ]; then
        # Still not set
        echo "ERROR! Cannot figure out region"
        exit 1
    fi
fi

# One-time setup
if [[ $SETUP ]]; then
    bash deploy.sh --setup
    exit 0
fi

# Set region
aws configure set region ${region}

# Build code and create/update function on AWS
bash deploy.sh --name=$lambdafn --account=$accountid --size=${SIZE}

# Check if we already have a cached api trigger for this lambda
cache_dir=.api_cache
mkdir -p ${cache_dir}
cache_file=${cache_dir}/${accountid}_${region}_${lambdafn}
if [[ -f "$cache_file" ]]; then
    # Cached entry found
    if [ -z "$FORCE" ]; then
        url=$(cat ${cache_file})
        echo "An api trigger for this lambda already exists, use that one or run with -f to force create another one."
        echo "$url"
    fi
fi

# Create API trigger
if [ -z "$url" ]; then
    #
    # Using Proxy integration: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    #
    apid=$(aws apigateway create-rest-api --name $lambdafn --endpoint-configuration types=REGIONAL | jq -r ".id")
    resourceid=$(aws apigateway get-resources --rest-api-id $apid | jq -r ".items[].id")
    proxyid=$(aws apigateway create-resource --rest-api-id $apid --region $region --parent-id $resourceid --path-part {proxy+} |  jq -r ".id")

    aws apigateway put-method --rest-api-id $apid \
       --region $region \
       --resource-id $proxyid \
       --http-method ANY \
       --authorization-type NONE

    aws apigateway put-integration \
        --region $region \
        --rest-api-id $apid \
        --resource-id $proxyid \
        --http-method ANY \
        --type AWS \
        --request-parameters '{ "integration.request.header.X-Amz-Invocation-Type": "'"'"'Event'"'"'" }' \
        --integration-http-method POST \
        --uri arn:aws:apigateway:$region:lambda:path/2015-03-31/functions/arn:aws:lambda:$region:$accountid:function:$lambdafn/invocations

    aws lambda add-permission --function-name $lambdafn \
        --statement-id apigateway-test-$apid --action lambda:InvokeFunction \
        --principal apigateway.amazonaws.com \
        --source-arn "arn:aws:execute-api:$region:$accountid:$apid/*"

    # aws lambda add-permission --function-name $lambdafn \
    #     --statement-id apigateway-latest-$apid --action lambda:InvokeFunction \
    #     --principal apigateway.amazonaws.com \
    #     --source-arn "arn:aws:execute-api:$region:$accountid:$apid/*/*/"

    aws apigateway create-deployment --rest-api-id $apid --stage-name latest

    # Cache the url
    url="https://${apid}.execute-api.${region}.amazonaws.com/latest/membus"
    echo "$url" > ${cache_file}
    echo "New API trigger $apid created"
    echo $url
fi

# Create S3 bucket if it does not exist
s3bucket=${S3PREFIX}${region}
exit_code=0
aws s3 ls ${s3bucket} &> /dev/null || exit_code=$?      # This excepts the command from "stop -e" while also saving the exit code.
if [ $exit_code -ne 0 ]; then
    aws s3 mb s3://${s3bucket}
fi

# Test Lambda and API
echo "TESTING. Invoking function using API. Result:"
secs_since_epoch=$(date +%s)
secs_since_epoch=$((secs_since_epoch+5))    # now + 5 secs
# echo ${secs_since_epoch}
curl -X POST $url -d '{ "id": 11, "stime": '${secs_since_epoch}', "log": 1, "phases": 1, "samples": 1, "s3bucket": "'${s3bucket}'", "s3key":"'$secs_since_epoch'" }'
echo "  <== IGNORE THIS."   # Ignore 500 error, which is expected now.

# Wait for response
WAIT_SECS=20            # now + 10 secs
echo "Waiting for response... ($WAIT_SECS secs)"
sleep $WAIT_SECS
exit_code=0
aws s3 ls ${s3bucket}/${secs_since_epoch} &> /dev/null || exit_code=$?
if [ $exit_code -eq 0 ]; then
    rm out/temp
    aws s3 cp s3://${s3bucket}/${secs_since_epoch} out/temp
    cat out/temp
    echo ""
else
    echo "No output written to S3:///${s3bucket}/${secs_since_epoch}"
fi
