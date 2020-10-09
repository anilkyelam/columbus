#
# List all runs with information for the given date/time pattern prefix
# Works for runs starting 08-20-*
#

prefix=$1
if [ -z "$prefix" ];  then    prefix=$(date +"%m-%d");    fi    # today

OUT=`echo Exp,Lambda,Region,Phases,Bit-Time,Count,Responded,Clusters,Density,Max Size,Errors,Size 1,Size 2,Size 3-5,Size 6-10,Unaccounted,Samples`
# for f in `ls out/08-20-1*/stats.json`; do
for f in `ls out/${prefix}*/stats.json`; do
    # Data from stats.json
    # echo $f
    dir=`dirname $f`
    name=`jq '.Name' $f | tr -d '"'`
    region=`jq '.Region' $f | tr -d '"'`
    count=`jq '.Count' $f`
    responded=`tail -n +2 $dir/results.csv | wc -l`
    clusters=`jq '.Clusters' $f`
    errorrate=`jq '."Error Rate"' $f`
    sizes=`jq '.Sizes[]' $f`
    maxsize=`jq '.Max' $f`
    density=`echo $responded $clusters | awk '{ printf("%.2f",$1*1.0/$2); }'`

    # Data from config.json
    phases=`jq '.Phases' $dir/config.json`
    lambda=`jq '."Lambda Name"' $dir/config.json | tr -d '"'`
    bitdur=`jq '."Bit Duration (secs)"' $dir/config.json`
    samples=`ls $dir/base_samples* 2> /dev/null | wc -l | awk '{ if ($1 > 0) print "Yes"; else print "No"; }'`

    # Inferred stats
    errors=`echo $count $errorrate | awk '{print $1*$2/100.0}'`
    size1=`grep -o "1" <<< "${sizes[*]}" | wc -l`
    size2=`grep -o "2" <<< "${sizes[*]}" | wc -l`
    size3=`egrep -o "3" <<< "${sizes[*]}" | wc -l`
    size4=`egrep -o "4" <<< "${sizes[*]}" | wc -l`
    size5=`egrep -o "5" <<< "${sizes[*]}" | wc -l`
    size6=`egrep -o "6" <<< "${sizes[*]}" | wc -l`
    size7=`egrep -o "7" <<< "${sizes[*]}" | wc -l`
    size8=`egrep -o "8" <<< "${sizes[*]}" | wc -l`
    size9=`egrep -o "9" <<< "${sizes[*]}" | wc -l`
    size10=`egrep -o "10" <<< "${sizes[*]}" | wc -l`
    size3_5=`echo $size3 $size4 $size5 | awk '{print $1+$2+$3}'`
    size6_10=`echo $size6 $size7 $size8 $size9 $size10 | awk '{print $1+$2+$3+$4+$5}'`
    unaccounted=`echo $responded $errors $size1 $size2 $size3 $size4 $size5 $size6 $size7 $size8 $size9 $size10 | awk '{print $1-$2-$3-($4*2)-($5*3)-($6*4)-($7*5)-($8*6)-($9*7)-($10*8)-($11*9)-($12*10)}'`

    # Print all
    LINE=`echo $name, $lambda, $region, $phases, $bitdur, $count, $responded, $clusters, $density, $maxsize, $errorrate, $size1, $size2, $size3_5, $size6_10, $unaccounted, $samples`
    OUT=`echo -e "${OUT}\n${LINE}"`
done

echo "$OUT" | column -s, -t