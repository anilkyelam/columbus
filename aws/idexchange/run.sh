#
# Run lambda colocation experiments
#

# Colococation by regions
for reg in us-east-2 us-west-2 eu-west-1 eu-north-1 ap-southeast-1 sa-east-1; do
    echo $reg
    aws configure set region $reg
    # bash setup.sh -n=membus1536 -s=1536
    # python3 invoke.py --name=membus1536 -c=100 -p=3 -s
    python3 invoke.py --name=membus1536 -c=1000 -p=3 -b=1 -d=90 -s
done
bash ks-values.sh 09-22-15

# # Colocation and error rate by sizes
# for size in 128 256 512 1024 1536 3008; do
#     # echo $size
#     # bash setup.sh -n=membus$size -s=$size
#     python3 invoke.py --name=membus$size -c=1000 -p=3 -b=1 -d=90 -s
#     # bash ks-values.sh
# done