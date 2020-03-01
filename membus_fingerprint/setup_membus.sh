# Parameters
accountid=128002906036
lambdafn=thrashers

#region=me-south-1
#region=us-east-1
#region=ap-southeast-1
#region=ca-central-1
#region=sa-east-1
#region=eu-west-2
# region=eu-west-3
# region=ap-east-1
region=me-south-1
# region=eu-north-1


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



echo "lambda created"

