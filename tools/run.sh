#!/usr/bin/env bash
# run.sh — log one agent shell command for the TIME VIEW and checkpoint afterwards.
# usage: tools/run.sh <task> [-p phase] [-C dir] -- <command string>
#   phase: setup | solve (default) | eval
#   dir:   working directory (default: $WORK/<task>/repo)
# Appends one JSON line (kind=cmd) to logs/<task>/calls.jsonl with ns timestamps,
# exit code, the checkpoint the command started from (pre_snap), then runs snap.sh.
source /home/user/agent-tax/tools/env.sh
task=$1; shift
phase=solve; cwd=$WORK/$task/repo
while [ $# -gt 0 ]; do
  case $1 in
    -p) phase=$2; shift 2;;
    -C) cwd=$2; shift 2;;
    --) shift; break;;
    *) break;;
  esac
done
cmd="$*"
logdir=$AT_ROOT/logs/$task; mkdir -p "$logdir/out"
seq=$(( $(cat "$logdir/.seq" 2>/dev/null || echo 0) + 1 )); echo $seq > "$logdir/.seq"
pre_snap=$(cat "$logdir/.last_snap" 2>/dev/null || echo none)
venv=$WORK/$task/venv
if [ -x "$venv/bin/python" ]; then export VIRTUAL_ENV=$venv PATH=$venv/bin:$PATH; fi
out=$logdir/out/$(printf %04d $seq).txt
cd "$cwd" || exit 97
start_ns=$(date +%s%N)
bash -c "$cmd" 2>&1 | tee "$out"
rc=${PIPESTATUS[0]}
end_ns=$(date +%s%N)
truncate -s '<204800' "$out"
jq -nc --arg task "$task" --argjson seq $seq --arg phase "$phase" --arg cmd "$cmd" \
  --arg cwd "$cwd" --argjson start_ns $start_ns --argjson end_ns $end_ns --argjson rc $rc \
  --arg pre_snap "$pre_snap" --arg venv "$( [ -n "$VIRTUAL_ENV" ] && echo "$VIRTUAL_ENV")" \
  '{kind:"cmd",task:$task,seq:$seq,phase:$phase,cmd:$cmd,cwd:$cwd,start_ns:$start_ns,end_ns:$end_ns,dur_s:(($end_ns-$start_ns)/1e9),rc:$rc,pre_snap:$pre_snap,venv:$venv}' \
  >> "$logdir/calls.jsonl"
[ -d "$WORK/$task/repo/.git" ] && "$AT_ROOT/tools/snap.sh" "$task" "after_cmd:$seq" >/dev/null
echo "[run.sh] seq=$seq rc=$rc dur=$(( (end_ns-start_ns)/1000000 ))ms" >&2
exit $rc
