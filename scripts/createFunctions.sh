#!/bin/bash 

# Read current GMT date and time and add 5 minutes to it. Store in $time
# NOTE: don't run this script if minutes of current GMT is >= 55
time="$(date -u +"%M %H %d %m ? %Y")"
echo $time
minutes="$(echo $time | cut -c1-2)"
minutes="$(echo "$(($minutes + 5))")"
rest="$(echo $time | cut -c3-)"
time=$minutes$rest
echo $time

for i in {1..10}
do
	# create 10 copies of function.py and zip each one separately
	cp function.py function$i.py
	zip -r function$i.zip function$i.py

	# create a lambda function corresponding to each of the 10 function copies
	# MODIFY role to your role's arn and --zip-file to your path
	aws lambda create-function --function-name "function$i" --runtime "python3.7" --role "arn:aws:iam::263638434136:role/lambda-cli-role" --handler "function$i.handler" --zip-file "fileb://~/Documents/CSE227/scripts/function$i.zip"

	# add a rule scheduled to trigger its targets at a specific time(5 minutes from now)
	aws events put-rule --name "Rule$i" --schedule-expression "cron($time)"
	# add perission to the rule to access target lambda function
	aws lambda add-permission --function-name "function$i" --statement-id "Statement$i" --action 'lambda:InvokeFunction' --principal events.amazonaws.com --source-arn "arn:aws:events:us-west-2:263638434136:rule/Rule$i"

	# add 5 instances of same function to the rule(maximum num of targets allowed per rule is 5)
	for j in {1..5}
	do
		aws events put-targets --rule "Rule$i" --targets "Id"="$i$j","Arn"="arn:aws:lambda:us-west-2:263638434136:function:function$i"
	done

done