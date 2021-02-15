#
# Experiments for setting up the covert channel and measuring bandwidth/error rate
# 

# The script assumes that the following lambda is properly setup
LAMBDA_SIZE=3008        # 1536 2304 3008
LAMBDA_NAME=membus${LAMBDA_SIZE}
LAMBDA_COUNT=100

# #============================ PICKING THRESHOLD ======================================#
# # Experiemnts to empirically find the best threshold for each channel rate
# # Threshold may vary because scheduling may affect each bit duration differently!
# ratefiles=""
# for rate in 20 40 60 80; do 
#     # files=""
#     # for threshold in 10000 10400 10800 11000 12000 13000 14000; do
#     #     # Invoke lambdas on AWS
#     #     expname=$(date +"%m-%d-%H-%M")
#     #     python3 invoke.py -n ${LAMBDA_NAME} -c ${LAMBDA_COUNT} -p 3 -d 15 -ch --chrate ${rate} --chthresh ${threshold} \
#     #         --expname ${expname} -ed "measuring channel errors; bps = ${rate}; threshold=${ATOMIC_OPS_LATENCY_WITH_LOCKING_THRESHOLD} mus"

#     #     # Parse stats
#     #     expdir=out/${expname}
#     #     chstatsfile=${expdir}/channelstats.json
#     #     if [ ! -f $chstatsfile ]; then
#     #         echo "Channel stats file not found at $chstatsfile. Continuing..."
#     #         continue
#     #     fi
        
#     #     # aggregate files
#     #     files="$files $chstatsfile"
#     # done
    
#     # echo $files
#     # Convert to csv
#     datafile=out/chstats_${LAMBDA_NAME}_rate${rate}
#     # jq -s "." $files | \
#     #     jq -r '(map(keys) | add | unique) as $cols | map(. as $row | $cols | map($row[.])) as $rows | $cols, $rows[] | @csv' \
#     #     | tr -d '"' > ${datafile}
    
#     ratefiles="${ratefiles} -d ${datafile} -l ${rate}bps"
# done 

# # Error by threshold plots. This helps pick the right threshold that 
# # results in min errors for each channel rate 
# mkdir -p plots
# plot=plots/channel_errors_vs_threshold_${LAMBDA_NAME}.pdf
# python plot.py ${ratefiles} -o $plot                    \
#     -yc "Byte Errors Std" -ls solid            \
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

# TODO: Try with 3 GB lambdas as well! Final try...

files=""
# # for rate in 10 20 30 40 50 60 70 80 90 100; do
# # for rate in 10 50 80 100; do
for rate in 10 25 50 75 100 200 500 750 1000; do
    # Select threshold (based on plots at plots/channel_errors*_vs_threshold_membus1536.pdf)
    # if [[ $rate -ge 100 ]]; then thresh=10800; else thresh=13500; fi
    thresh=14000

#     # Invoke lambdas on AWS
#     expname=$(date +"%m-%d-%H-%M")
#     # if [[ $rate -eq 10 ]]; then     expname=02-03-19-33;    fi
#     # if [[ $rate -eq 50 ]]; then     expname=02-03-19-34;    fi
#     # if [[ $rate -eq 100 ]]; then    expname=02-03-19-35;    fi
#     # if [[ $rate -eq 200 ]]; then    expname=02-03-19-39;    fi
#     # if [[ $rate -eq 500 ]]; then    expname=02-03-19-42;    fi
#     # if [[ $rate -eq 1000 ]]; then   expname=02-03-19-46;    fi
#     # if [[ $rate -eq 2000 ]]; then   expname=02-03-19-49;    fi
#     # if [[ $rate -eq 5000 ]]; then   expname=02-03-19-52;    fi
#     # if [[ $rate -eq 10000 ]]; then  expname=02-03-19-56;    fi
#     # if [[ $rate -eq 10 ]]; then     expname=02-09-00-45;    fi        # 1.5gb, 10-100, 14000 threshold
#     # if [[ $rate -eq 20 ]]; then     expname=02-09-00-47;    fi
#     # if [[ $rate -eq 30 ]]; then     expname=02-09-00-48;    fi
#     # if [[ $rate -eq 40 ]]; then     expname=02-09-00-51;    fi
#     # if [[ $rate -eq 50 ]]; then     expname=02-09-00-55;    fi
#     # if [[ $rate -eq 60 ]]; then     expname=02-09-00-58;    fi
#     # if [[ $rate -eq 70 ]]; then     expname=02-09-01-01;    fi
#     # if [[ $rate -eq 80 ]]; then     expname=02-09-01-05;    fi
#     # if [[ $rate -eq 90 ]]; then     expname=02-09-01-08;    fi
#     # if [[ $rate -eq 100 ]]; then    expname=02-09-01-12;    fi
#     # if [[ $rate -eq 10 ]]; then     expname=02-09-12-57;    fi        # 3gb, 10-100, 14000 threshold
#     # if [[ $rate -eq 50 ]]; then     expname=02-09-12-58;    fi
#     # if [[ $rate -eq 80 ]]; then     expname=02-09-12-59;    fi
#     # if [[ $rate -eq 100 ]]; then    expname=02-09-13-00;    fi
#     # if [[ $rate -eq 200 ]]; then    expname=02-09-15-27;    fi
#     # if [[ $rate -eq 500 ]]; then    expname=02-09-15-29;    fi
#     # if [[ $rate -eq 1000 ]]; then   expname=02-09-15-30;    fi
    if [[ $rate -eq 10   ]] && [[ $LAMBDA_SIZE -eq 3008 ]]; then   expname=02-10-14-59;    fi           # FINAL RUNS!
    if [[ $rate -eq 25   ]] && [[ $LAMBDA_SIZE -eq 3008 ]]; then   expname=02-10-15-00;    fi
    if [[ $rate -eq 50   ]] && [[ $LAMBDA_SIZE -eq 3008 ]]; then   expname=02-10-23-04;    fi
    if [[ $rate -eq 75   ]] && [[ $LAMBDA_SIZE -eq 3008 ]]; then   expname=02-10-15-03;    fi
    if [[ $rate -eq 100  ]] && [[ $LAMBDA_SIZE -eq 3008 ]]; then   expname=02-10-15-04;    fi
    if [[ $rate -eq 200  ]] && [[ $LAMBDA_SIZE -eq 3008 ]]; then   expname=02-10-15-05;    fi
    if [[ $rate -eq 500  ]] && [[ $LAMBDA_SIZE -eq 3008 ]]; then   expname=02-10-15-06;    fi
    if [[ $rate -eq 750  ]] && [[ $LAMBDA_SIZE -eq 3008 ]]; then   expname=02-10-15-08;    fi
    if [[ $rate -eq 1000 ]] && [[ $LAMBDA_SIZE -eq 3008 ]]; then   expname=02-10-15-09;    fi
    if [[ $rate -eq 10   ]] && [[ $LAMBDA_SIZE -eq 2304 ]]; then   expname=02-10-15-28;    fi           # FINAL RUNS!
    if [[ $rate -eq 25   ]] && [[ $LAMBDA_SIZE -eq 2304 ]]; then   expname=02-10-15-29;    fi
    if [[ $rate -eq 50   ]] && [[ $LAMBDA_SIZE -eq 2304 ]]; then   expname=02-10-15-30;    fi
    if [[ $rate -eq 75   ]] && [[ $LAMBDA_SIZE -eq 2304 ]]; then   expname=02-10-15-31;    fi
    if [[ $rate -eq 100  ]] && [[ $LAMBDA_SIZE -eq 2304 ]]; then   expname=02-10-22-26;    fi
    if [[ $rate -eq 200  ]] && [[ $LAMBDA_SIZE -eq 2304 ]]; then   expname=02-10-15-34;    fi
    if [[ $rate -eq 500  ]] && [[ $LAMBDA_SIZE -eq 2304 ]]; then   expname=02-10-15-35;    fi
    if [[ $rate -eq 750  ]] && [[ $LAMBDA_SIZE -eq 2304 ]]; then   expname=02-10-15-36;    fi
    if [[ $rate -eq 1000 ]] && [[ $LAMBDA_SIZE -eq 2304 ]]; then   expname=02-10-15-37;    fi
    if [[ $rate -eq 10   ]] && [[ $LAMBDA_SIZE -eq 1536 ]]; then   expname=02-10-16-03;    fi           # FINAL RUNS!
    if [[ $rate -eq 25   ]] && [[ $LAMBDA_SIZE -eq 1536 ]]; then   expname=02-10-16-05;    fi
    if [[ $rate -eq 50   ]] && [[ $LAMBDA_SIZE -eq 1536 ]]; then   expname=02-10-16-06;    fi
    if [[ $rate -eq 75   ]] && [[ $LAMBDA_SIZE -eq 1536 ]]; then   expname=02-10-16-07;    fi
    if [[ $rate -eq 100  ]] && [[ $LAMBDA_SIZE -eq 1536 ]]; then   expname=02-10-16-08;    fi
    if [[ $rate -eq 200  ]] && [[ $LAMBDA_SIZE -eq 1536 ]]; then   expname=02-10-22-10;    fi
    if [[ $rate -eq 500  ]] && [[ $LAMBDA_SIZE -eq 1536 ]]; then   expname=02-10-16-11;    fi
    if [[ $rate -eq 750  ]] && [[ $LAMBDA_SIZE -eq 1536 ]]; then   expname=02-10-16-12;    fi
    if [[ $rate -eq 1000 ]] && [[ $LAMBDA_SIZE -eq 1536 ]]; then   expname=02-10-16-13;    fi

    # python3 invoke.py -n ${LAMBDA_NAME} -c ${LAMBDA_COUNT} -p 3 -d 15 -ch --chrate ${rate} --chthresh ${thresh} \
    #     --expname ${expname} -ed "FINAL RUNS for ${LAMBDA_NAME}: measuring channel errors; bps = ${rate}; threshold=${ATOMIC_OPS_LATENCY_WITH_LOCKING_THRESHOLD} mus"   \
    #     --retrynos3 --outdir=$expname

    # # # Parse stats
    # expdir=out/${expname}
    # chstatsfile=${expdir}/channelstats.json
    # if [ ! -f $chstatsfile ]; then
    #     echo "Channel stats file not found at $chstatsfile. Continuing..."
    #     continue
    # fi
    
    # # aggregate files
    # files="$files $chstatsfile"
done

# echo $files
# # Convert to csv
# datafile=out/chstats_${LAMBDA_NAME}
# jq -s "." $files | 
#     jq -r '(map(keys) | add | unique) as $cols | map(. as $row | $cols | map($row[.])) as $rows | $cols, $rows[] | @csv' \
#     | tr -d '"' > ${datafile}

# # Plot errors vs channel rate
# mkdir -p plots
# plot=plots/channel_errors_${LAMBDA_NAME}.pdf
# python plot.py -d ${datafile} -o $plot  -yl "Avg Error %"    \
#     -yc "Byte Errors Std" -l ""   -ls solid            \
#     -xc "Channel Rate" -xl "Data Rate (bps)"
# echo "Plot at: $plot"
# display $plot &

# # # # Plot effective channel rate
# # # mkdir -p plots
# plot=plots/channel_rate_${LAMBDA_NAME}.pdf
# python plot.py -d ${datafile} -o $plot  -yl "Effective Channel Rate (bps)"  \
#     -yc "Effective Rate 95per" -l "95% confidence"   -ls solid              \
#     -yc "Effective Rate 999per" -l "99.9% confidence"   -ls solid              \
#     -xc "Channel Rate" -xl "Raw Channel Rate (bps)"
# echo "Plot at: $plot"
# display $plot &

# Aggregate plots
# plot=plots/channel_errors.pdf
# python plot.py -o $plot  -yl "Error Prob" --xlog --ymin 0 --ymax 50 \
#     -dyc out/chstats_membus1536 "Errors Mean" -l "1.5 GB"   -ls solid              \
#     -dyc out/chstats_membus2304 "Errors Mean" -l "2.4 GB"   -ls solid              \
#     -dyc out/chstats_membus3008 "Byte Errors Mean" -l "3 GB"     -ls solid              \
#     -xc "Channel Rate" -xl "Raw Channel Rate (bps)" 
# echo "Plot at: $plot"
# display $plot &

# plot=plots/channel_byte_errors.pdf
# python plot.py -o $plot  -yl "Byte Error Prob" --xlog --ymin 0 --ymax 50 \
#     -dyc out/chstats_membus1536 "Byte Errors Mean" -l "1.5 GB"   -ls solid              \
#     -dyc out/chstats_membus2304 "Byte Errors Mean" -l "2.4 GB"   -ls solid              \
#     -dyc out/chstats_membus3008 "Byte Errors Mean" -l "3 GB"     -ls solid              \
#     -xc "Channel Rate" -xl "Raw Channel Rate (bps)" 
# echo "Plot at: $plot"
# display $plot &

# plot=plots/channel_rate.pdf
# python plot.py -o $plot  -yl "Effective Channel Rate (bps)" --xlog \
#     -dyc out/chstats_membus1536 "Effective Rate 95per" -l "1.5 GB"   -ls solid              \
#     -dyc out/chstats_membus2304 "Effective Rate 95per" -l "2.4 GB"   -ls solid              \
#     -dyc out/chstats_membus3008 "Effective Rate 95per" -l "3 GB"     -ls solid              \
#     -xc "Channel Rate" -xl "Raw Channel Rate (bps)" 
# echo "Plot at: $plot"
# display $plot &

plot=plots/channel_rate_3gb.pdf
python plot.py -o $plot -yl "Errors %" -tyl "Rate (bits per sec)" --xlog  --twin 2     \
    -dyc out/chstats_membus3008 "Byte Errors Mean" -l "Byte Errors, Mean"         -ls solid       \
    -dyc out/chstats_membus3008 "Byte Errors 95per" -l "Byte Errors, 95%"         -ls dashed        \
    -dyc out/chstats_membus3008 "Effective Rate 95per" -l "Effective Bit Rate (Goodput)"     -ls dashdot              \
    -xc "Channel Rate" -xl "Raw Bit Rate (bps)" 
echo "Plot at: $plot"
display $plot &



