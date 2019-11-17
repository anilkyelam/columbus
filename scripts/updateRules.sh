#!/bin/bash 

# use this script to update cron job time for all 10 rules
for i in {1..10}
do
	aws events put-rule --name "Rule$i" --schedule-expression "cron(39 00 16 11 ? 2019)"
done