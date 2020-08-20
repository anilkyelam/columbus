

for reg in eu-west-3 eu-west-2 ap-south-1 us-west-2 us-east-2 me-south-1; do
    echo $reg
    aws configure set region $reg
    bash setup.sh -n=membus1536 -s=1536
    python3 invoke.py --name=membus1536 -c=200 -p=3
done

# Show stats
for f in `ls out/*/stats.json`; do
    # echo $f
    # jq '.Region, .Count, .Clusters,."Error Rate",.Max' $f
    jq '.Region, .Clusters' $f
done