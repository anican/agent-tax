#!/usr/bin/env bash
# coldcache.sh — cost of a cold page cache (as after sandbox recycling or a
# host-side eviction) for representative test commands: warm run vs run after
# `sync; echo 3 > /proc/sys/vm/drop_caches`. perf stat gives task-clock and
# major faults; wall from /usr/bin/time. 3 pairs per command.
PERF=/usr/lib/linux-tools/6.8.0-147-generic/perf; W=/home/user/work; OUT=/home/user/agent-tax/results/coldcache
S=/tmp/claude-0/-home-user-agent-tax/bb9091d6-0001-5f4a-a230-6236adda4caf/scratchpad
echo "workload,state,rep,wall_s,task_clock_ms,major_faults,minor_faults" > $OUT/coldcache.csv
run() { # name state rep cwd venv cmd
  local name=$1 state=$2 rep=$3 cwd=$4 venv=$5 cmd=$6
  ( cd $cwd && VIRTUAL_ENV=$venv PATH=$venv/bin:$PATH $PERF stat -x, -o $S/cc.stat -e task-clock,major-faults,minor-faults -- /usr/bin/time -f %e -o $S/cc.time bash -c "$cmd" >/dev/null 2>&1 )
  echo "$name,$state,$rep,$(cat $S/cc.time),$(grep task-clock $S/cc.stat | cut -d, -f1),$(grep major-faults $S/cc.stat | cut -d, -f1),$(grep minor-faults $S/cc.stat | cut -d, -f1)" >> $OUT/coldcache.csv
}
declare -A CWD VENV CMD
CWD[django]=$W/django__django-16595/repo/tests; VENV[django]=$W/django__django-16595/venv; CMD[django]="python runtests.py migrations.test_optimizer --parallel 1"
CWD[sympy]=$W/sympy__sympy-24066/repo; VENV[sympy]=$W/sympy__sympy-24066/venv; CMD[sympy]="python -m pytest -q -p no:cacheprovider sympy/physics/units"
CWD[pytest]=$W/pytest-dev__pytest-10051/repo; VENV[pytest]=$W/pytest-dev__pytest-10051/venv; CMD[pytest]="python -m pytest -q -p no:cacheprovider testing/logging"
CWD[grep]=$W/django__django-16595/repo; VENV[grep]=$W/django__django-16595/venv; CMD[grep]="grep -rn 'def reduce' django/db/migrations | wc -l"
for name in django sympy pytest grep; do
  run $name warmup 0 "${CWD[$name]}" "${VENV[$name]}" "${CMD[$name]}"
  for rep in 1 2 3; do
    run $name warm $rep "${CWD[$name]}" "${VENV[$name]}" "${CMD[$name]}"
    sync; echo 3 > /proc/sys/vm/drop_caches; sleep 1
    run $name cold $rep "${CWD[$name]}" "${VENV[$name]}" "${CMD[$name]}"
  done
done
grep -v warmup $OUT/coldcache.csv
