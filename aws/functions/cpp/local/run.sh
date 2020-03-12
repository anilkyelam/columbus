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

# Run thrashers/samplers
taskset 0x1 ./thrasher 1 &
PIDS+=($!)
taskset 0x2 ./thrasher 2 &
PIDS+=($!)
taskset 0x4 ./sampler 1 &
PIDS+=($!)
taskset 0x8 ./sampler 2 &
PIDS+=($!)

read -p "Press [enter] to quit\n"
ctrl_c_handler
