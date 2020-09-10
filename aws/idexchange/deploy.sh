#!/bin/bash

#
# Creates/Updates a lamnbda function
#
# === Prerequisites ====
# 1. AWS CLI. (sudo apt install awscli)
# 2. Install AWS Lambda cpp SDK: https://github.com/awslabs/aws-lambda-cpp
# 3. Login to AWS: run "aws configure". Admin access recommended for no-hassle runs.
# 4. Json tool "jq". (sudo apt install jq)
# 5. Run the script with --setup option for other one-time setup stuff


# Parse command line arguments
for i in "$@"
do
case $i in
    -s|--setup)             # one-time setup
    SETUP=1
    ;;
    
    -a=*|--account=*)       # Account id
    ACCOUNTID="${i#*=}"
    ;;
    
    -n=*|--name=*)          # Function name
    NAME="${i#*=}"
    ;;
    
    -s=*|--size=*)          # Function size in MB. Multiples of 64MB, from 128-3008
    SIZE="${i#*=}"
    ;;

    *)                      # unknown option
    ;;
esac
done

NAME=${NAME:-membus}    # Default lambda name
ROLE=membus-cpp-s3      # Creates this role if not exists
SIZE=${SIZE:-128}

# One-time setup
if [[ $SETUP ]]; then
    # Prepare cmake
    mkdir -p cpp/build
    pushd cpp/build/
    cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=~/lambda-install
    popd
fi

# Get account id from aws cli if not set
if [ -z ${ACCOUNTID+x} ]; then
    ACCOUNTID=$(aws sts get-caller-identity | jq -r ".Account")
    if [ -z ${ACCOUNTID+x} ]; then
        # Still not set
        echo "ERROR! Cannot figure out account id"
        exit 1
    fi
fi

# 
# Instructions at: https://github.com/awslabs/aws-lambda-cpp
#

# Rebuild
dir=$(dirname "$0")
pushd $dir/cpp/build
# cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=~/out
make
make aws-lambda-package-hello
popd

# Create role 
aws iam get-role --role-name ${ROLE}
if [ $? -ne 0 ]; then
    # Does not exist
    aws iam create-role --role-name ${ROLE} --assume-role-policy-document file://$dir/cpp/trust-policy.json
    aws iam attach-role-policy --role-name ${ROLE} --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    aws iam attach-role-policy --role-name ${ROLE} --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess      # To write responses to S3 
fi

# Create or update function
aws lambda get-function --function-name ${NAME} 1>/dev/null
if [ $? -ne 0 ]; then
    # Does not exist
    aws lambda create-function --function-name ${NAME} --role "arn:aws:iam::${ACCOUNTID}:role/${ROLE}" \
        --runtime provided --timeout 900 --memory-size ${SIZE} --handler hello --zip-file fileb://$dir/cpp/build/hello.zip
else
    # Update function
    echo "Updating function"
    aws lambda update-function-configuration --function-name ${NAME} --memory-size ${SIZE} --timeout 900
    aws lambda update-function-configuration --function-name ${NAME} --role "arn:aws:iam::${ACCOUNTID}:role/${ROLE}"
    aws lambda update-function-code --function-name ${NAME} --zip-file fileb://$dir/cpp/build/hello.zip
fi

# We don't want lambdas to be re-triggered if they failed for some reason
aws lambda put-function-event-invoke-config --function-name ${NAME} --maximum-retry-attempts 0

# Test by invoking it
echo "Skip invoking function using CLI"
# aws lambda invoke --function-name ${NAME} output.txt 
# echo "$(cat output.txt)"
# rm output.txt