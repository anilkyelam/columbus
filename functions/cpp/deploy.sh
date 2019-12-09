#!/bin/bash

# Parse command line arguments
for i in "$@"
do
case $i in
    -c|--create)        # create functions
    CREATE=1
    ;;

    *)                      # unknown option
    ;;
esac
done

# Rebuild
dir=$(dirname "$0")
pushd $dir/build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=~/out
make
make aws-lambda-package-hello

# Create function if required
if [[ $CREATE ]]; then
    aws lambda create-function --function-name membus --role "arn:aws:iam::017371402075:role/lambda-cpp" \
        --runtime provided --timeout 30 --memory-size 128 --handler hello --zip-file fileb://hello.zip
fi

# Deploy
echo "Updating function"
aws lambda update-function-code --function-name membus --zip-file fileb://hello.zip
popd

echo "Invoking function"
aws lambda invoke --function-name membus output.txt 
cat output.txt
rm output.txt
#curl -X POST https://8rq4dl2w8f.execute-api.us-west-1.amazonaws.com/latest -d '1'

