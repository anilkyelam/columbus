#!/bin/bash
# type "finish" to exit

PIDS=()

# On ctrl-c, kill everything
ctrl_c_handler() {
    #echo "$PIDS"
    for pid in "${PIDS[@]}"; do     kill $pid;  done
    # pkill thrasher
    # pkill sampler
    exit 0
}

trap 'ctrl_c_handler' SIGINT

# Rebuild
make clean
make

secs_since_epoch=$(date +%s)
secs_since_epoch=$((secs_since_epoch+2))    # now + 2 secs
#echo ${secs_since_epoch}

# Run thrashers/samplers
taskset 0x1 ./lambda 0 ${secs_since_epoch} &
PIDS+=($!)
taskset 0x2 ./lambda 1 ${secs_since_epoch} &
PIDS+=($!)

read -p "Press [enter] to quit\n"
ctrl_c_handler
