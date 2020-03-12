#!/bin/bash 

# Use this script to clear all functions and rules created. Essentially, invoke this script before running createFunctions.sh
for i in {1..10}
do
	# delete functions and their zips from local machine
	rm function$i.py 
	rm function$i.zip

	# deletes lambda function
	aws lambda delete-function --function-name "function$i"
	# delete all targets within a rule before deleting the rule
	for j in {1..5}
	do
		aws events remove-targets --rule "Rule$i" --ids "$i$j"
	done
	# delete the rule
	aws events delete-rule --name "Rule$i"

	# TODO : Add code to remove log groups from CloudWatch logs 
done