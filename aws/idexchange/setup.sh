#!/bin/bash

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
    
    -n=*|--name=*)          # Function name
    lambdafn="${i#*=}"
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
lambdafn=${lambdafn:-membusv2}    # Default lambda name

# Get account id from aws cli if not set
if [ -z ${accountid+x} ]; then
    accountid=$(aws sts get-caller-identity | jq -r ".Account")
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
    bash cpp/deploy.sh --setup
fi

# Set region
aws configure set region ${region}

# Build code and create/update function on AWS
bash deploy.sh --name=$lambdafn --account=$accountid

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
        --type AWS_PROXY \
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

# Test Lambda and API
echo "Invoking function using API. Result:"
curl -X POST $url > output.txt
echo "$(cat output.txt)"
rm output.txt
