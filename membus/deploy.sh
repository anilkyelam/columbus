
### Constants
region='us-west-1'

### Build
pushd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=~/out
make
make aws-lambda-package-hello

# 
#aws lambda create-function --function-name thrasher --role “arn:aws:iam::017371402075:role/lambda-cpp” --runtime provided --timeout 15 --memory-size 128 --handler hello --zip-file fileb://hello.zip


# Deploy
echo "Updating function"
aws lambda update-function-code --function-name hello-world  --zip-file fileb://hello.zip

echo "Invoking function"
aws lambda invoke --function-name hello-world output.txt
cat output.txt

