#
# Experiments for setting up the covert channel and measuring bandwidth/error rate
# 

# The script assumes that the following lambda is properly setup
LAMBDA_NAME=membus1536
LAMBDA_COUNT=100

# #============================ PICKING THRESHOLD ======================================#
# # Experiemnts to empirically find the best threshold for each channel rate
# # Threshold may vary because scheduling may affect each bit duration differently!
# ratefiles=""
# for rate in 10 50 100 200 400 500 1000 5000; do 
#     files=""
#     for threshold in 9600 9800 10000 10200 10400 10600 10800 11000 12000 13000 14000; do
#         # Invoke lambdas on AWS
#         expname=$(date +"%m-%d-%H-%M")
#         python3 invoke.py -n ${LAMBDA_NAME} -c ${LAMBDA_COUNT} -p 3 -d 15 -ch --chrate ${rate} --chthresh ${threshold} \
#             --expname ${expname} -ed "measuring channel errors; bps = ${rate}; threshold=${ATOMIC_OPS_LATENCY_WITH_LOCKING_THRESHOLD} mus"

#         # Parse stats
#         expdir=out/${expname}
#         chstatsfile=${expdir}/channelstats.json
#         if [ ! -f $chstatsfile ]; then
#             echo "Channel stats file not found at $chstatsfile. Continuing..."
#             continue
#         fi
        
#         # aggregate files
#         files="$files $chstatsfile"
#     done
    
#     # echo $files
#     # Convert to csv
#     datafile=out/chstats_${LAMBDA_NAME}_rate${rate}
#     jq -s "." $files | \
#         jq -r '(map(keys) | add | unique) as $cols | map(. as $row | $cols | map($row[.])) as $rows | $cols, $rows[] | @csv' \
#         | tr -d '"' > ${datafile}
    
#     ratefiles="${ratefiles} -d ${datafile} -l ${rate}bps"
# done 

# # Error by threshold plots. This helps pick the right threshold that 
# # results in min errors for each channel rate 
# mkdir -p plots
# plot=plots/channel_errors_vs_threshold_${LAMBDA_NAME}.pdf
# python plot.py ${ratefiles} -o $plot                    \
#     -yc "Errors Mean" -ls solid            \
#     -xc "Channel Threshold" -xl "Latency Threshold"
# echo "Plot at: $plot"
# display $plot &

# plot=plots/channel_errors1bit_vs_threshold_${LAMBDA_NAME}.pdf
# python plot.py ${ratefiles} -o $plot                    \
#     -yc "1-bit Errors Mean" -ls solid            \
#     -xc "Channel Threshold" -xl "Latency Threshold"
# echo "Plot at: $plot"
# display $plot &

# plot=plots/channel_errors0bit_vs_threshold_${LAMBDA_NAME}.pdf
# python plot.py ${ratefiles} -o $plot                    \
#     -yc "0-bit Errors Mean" -ls solid            \
#     -xc "Channel Threshold" -xl "Latency Threshold"
# echo "Plot at: $plot"
# display $plot &


#============================ GETTING CHANNEL ERROR RATE USING ABOVE THRESHOLD ======================================#

files=""
for rate in 10 50 100 200 500 1000 2000 5000 10000; do
    # Select threshold (based on plots at plots/channel_errors*_vs_threshold_membus1536.pdf)
    if [[ $rate -ge 100 ]]; then thresh=10800; else thresh=13500; fi

    # Invoke lambdas on AWS
    # expname=$(date +"%m-%d-%H-%M")
    if [[ $rate -eq 10 ]]; then     expname=02-03-19-33;    fi
    if [[ $rate -eq 50 ]]; then     expname=02-03-19-34;    fi
    if [[ $rate -eq 100 ]]; then    expname=02-03-19-35;    fi
    if [[ $rate -eq 200 ]]; then    expname=02-03-19-39;    fi
    if [[ $rate -eq 500 ]]; then    expname=02-03-19-42;    fi
    if [[ $rate -eq 1000 ]]; then   expname=02-03-19-46;    fi
    if [[ $rate -eq 2000 ]]; then   expname=02-03-19-49;    fi
    if [[ $rate -eq 5000 ]]; then   expname=02-03-19-52;    fi
    if [[ $rate -eq 10000 ]]; then  expname=02-03-19-56;    fi

    # python3 invoke.py -n ${LAMBDA_NAME} -c ${LAMBDA_COUNT} -p 3 -d 15 -ch --chrate ${rate} --chthresh ${thresh} \
    #     --expname ${expname} -ed "measuring channel errors; bps = ${rate}; threshold=${ATOMIC_OPS_LATENCY_WITH_LOCKING_THRESHOLD} mus"

    # Parse stats
    expdir=out/${expname}
    chstatsfile=${expdir}/channelstats.json
    if [ ! -f $chstatsfile ]; then
        echo "Channel stats file not found at $chstatsfile. Continuing..."
        continue
    fi
    
    # aggregate files
    files="$files $chstatsfile"
done

# echo $files
# Convert to csv
datafile=out/chstats_${LAMBDA_NAME}
jq -s "." $files | 
    jq -r '(map(keys) | add | unique) as $cols | map(. as $row | $cols | map($row[.])) as $rows | $cols, $rows[] | @csv' \
    | tr -d '"' > ${datafile}

# Plot errors vs channel rate
mkdir -p plots
plot=plots/channel_bps_${LAMBDA_NAME}.pdf
python plot.py -d ${datafile} -o $plot  -yl "Avg Error %" --xlog    \
    -yc "Errors Mean" -l ""   -ls solid            \
    -xc "Channel Rate" -xl "Data Rate (bps)"
echo "Plot at: $plot"
display $plot &

