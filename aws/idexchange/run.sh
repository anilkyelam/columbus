#
# Run lambda colocation experiments
#

# # Colococation by regions
# for reg in us-east-2 us-west-2 eu-west-1 eu-north-1 ap-southeast-1 sa-east-1; do
#     echo $reg
#     aws configure set region $reg
#     # bash setup.sh -n=membus1536 -s=1536
#     # python3 invoke.py --name=membus1536 -c=100 -p=3 -s
#     python3 invoke.py --name=membus1536 -c=1000 -p=3 -b=1 -d=90 -s
# done
# bash ks-values.sh 09-22-15

# # Colocation and error rate by sizes
# for size in 128 256 512 1024 1536 3008; do
#     # echo $size
#     # bash setup.sh -n=membus$size -s=$size
#     python3 invoke.py --name=membus$size -c=1000 -p=3 -b=1 -d=90 -s
#     # bash ks-values.sh
# done


while true
do
    # Run on every fourth hour
    hour=$(date +%H)
    minute=$(date +%M)
    while ((hour % 4)) || [[ $minute != "25" ]]; do
        sleep 1
        hour=$(date +%H)
        minute=$(date +%M)
    done

    region=us-east-2
    aws configure set region $region
    echo $region
    # bash setup.sh -n=membus1536 -s=1536
    # python3 invoke.py --name=membus1536 -c=100 -p=3 -s
    python3 invoke.py --name=membus1536 -c=1000 -p=3 -b=1 -d=90 -s -ed "hourly pattern runs"
done



# # ARCHIVING THE LINE OF EXPERIMENTS CHECKING FOR COLOCATION ACROSS CLOUD CONTAINERS LIKE VMS

# # Prepare to run a VM per region during each run just to see if VMs and lambdas are colocated
# pushd cpp/
# g++ local_main.cpp kstest.cpp timsort.cpp -o local_membus
# popd

# # Colococation by regions
# while true 
# do
#     while [ $(date +%H:%M) != "13:55" ]; do sleep 1; done
#     echo "Executing at " $(date)

#     # Start ec2 instances first, and WAIT until they are ready
#     # us-east-2
#     region=us-east-2
#     aws configure set region $region
#     for ec2 in "i-0a5c4cf1580ab9974" "i-0a891c4c49b5e85a1" "i-0280072a129b4bc03"; do 
#         echo $ec2
#         aws ec2 start-instances --instance-ids $ec2
#     done
#     # sa-east-1
#     region=sa-east-1
#     aws configure set region $region
#     for ec2 in "i-0f8466476e9aef188" "i-0cb4673b6fc3e9628"; do
#         echo $ec2
#         aws ec2 start-instances --instance-ids $ec2
#     done

#     # Give VMs 15 mins to be ready
#     while [ $(date +%H:%M) != "14:00" ]; do sleep 1; done

#     # Kick off local membus scripts in each ec2 instance
#     # us-east-2
#     region=us-east-2
#     aws configure set region $region
#     for ec2 in "i-0a5c4cf1580ab9974" "i-0a891c4c49b5e85a1" "i-0280072a129b4bc03"; do 
#         echo $ec2
#         dnsname=$(aws ec2 describe-instances --instance-ids $ec2 --query "Reservations[*].Instances[*].PublicDnsName" --output=text)
#         echo $dnsname
#         scp cpp/local_membus $dnsname:~/
#         ssh $dnsname "./local_membus > out" &
#     done
#     # # sa-east-1
#     # region=sa-east-1
#     # aws configure set region $region
#     # for ec2 in "i-0f8466476e9aef188" "i-0cb4673b6fc3e9628"; do
#     #     echo $ec2
#     #     dnsname=$(aws ec2 describe-instances --instance-ids $ec2 --query "Reservations[*].Instances[*].PublicDnsName" --output=text)
#     #     scp cpp/local_membus $dnsname:~/
#     #     ssh $dnsname "./local_membus > out" &
#     # done

#     # Now start the lambda runs
#     echo "Starting lambda runs"
#     # sleep 60

#     region=us-east-2
#     aws configure set region $region
#     echo $region
#     # bash setup.sh -n=membus1536 -s=1536
#     # python3 invoke.py --name=membus1536 -c=100 -p=3 -s
#     python3 invoke.py --name=membus1536 -c=1000 -p=3 -b=1 -d=90 -s -ed "daily runs"

#     region=sa-east-1
#     aws configure set region $region
#     echo $region
#     # bash setup.sh -n=membus1536 -s=1536
#     # python3 invoke.py --name=membus1536 -c=100 -p=3 -s
#     python3 invoke.py --name=membus1536 -c=1000 -p=3 -b=1 -d=90 -s -ed "daily runs"
#     echo "Executed at " $(date)

#     # Collect output from VMs and stop them
#     # us-east-2
#     mkdir -p out/vms
#     region=us-east-2
#     aws configure set region $region
#     for ec2 in "i-0a5c4cf1580ab9974" "i-0a891c4c49b5e85a1" "i-0280072a129b4bc03"; do 
#         echo $ec2
#         dnsname=$(aws ec2 describe-instances --instance-ids $ec2 --query "Reservations[*].Instances[*].PublicDnsName" --output=text)
#         echo $dnsname
#         scp $dnsname:~/out out/vms/vmout-$region-$ec2-$(date +"%m-%d");                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
#         ssh $dnsname "pkill local_membus"
#         aws ec2 stop-instances --instance-ids $ec2
#     done
#     # sa-east-1
#     region=sa-east-1
#     aws configure set region $region
#     for ec2 in "i-0f8466476e9aef188" "i-0cb4673b6fc3e9628"; do
#         echo $ec2
#         dnsname=$(aws ec2 describe-instances --instance-ids $ec2 --query "Reservations[*].Instances[*].PublicDnsName" --output=text)
#         echo $dnsname
#         scp $dnsname:~/out out/vms/vmout-$region-$ec2-$(date +"%m-%d");
#         ssh $dnsname "pkill local_membus"
#         aws ec2 stop-instances --instance-ids $ec2
#     done

#     # To look at latency values of the VMs
#     # egrep "\[Lambda- .+[0-9]+.+" out/vms/vmout-* | awk '{ if($9 > $14) print $9-$14; else print $14-$9 }' | datamash max 1 
# done

