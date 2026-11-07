#!/usr/bin/env bash
# replay_exec.sh <pidfile> <cmd> — workload launcher for perf record: records its
# own pid (the root of the replayed process tree), then execs the command
# under a 10-minute hard cap.
echo $$ > "$1"
exec timeout -s KILL 600 bash -c "$2"
