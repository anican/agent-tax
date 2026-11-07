#!/usr/bin/env bash
# episode.sh — start/stop an agent episode: sampler + start/end checkpoints.
# usage: tools/episode.sh start <task> | tools/episode.sh end <task> <resolved|unresolved|unknown> [note]
source /home/user/agent-tax/tools/env.sh
act=$1; task=$2; logdir=$AT_ROOT/logs/$task; mkdir -p "$logdir"
case $act in
  start)
    setsid nohup "$AT_ROOT/tools/sample.sh" "$logdir/sampler.csv" >/dev/null 2>&1 < /dev/null &
    echo $! > "$logdir/.sampler.pid"
    [ -x "$WORK/$task/venv/bin/python" ] && "$WORK/$task/venv/bin/python" -m pip freeze --all > "$logdir/freeze_start.txt" 2>/dev/null
    "$AT_ROOT/tools/snap.sh" "$task" episode_start
    jq -nc --arg task "$task" --argjson t $(date +%s%N) '{kind:"episode_start",task:$task,ts_ns:$t}' >> "$logdir/calls.jsonl";;
  end)
    "$AT_ROOT/tools/snap.sh" "$task" episode_end
    jq -nc --arg task "$task" --argjson t $(date +%s%N) --arg r "${3:-unknown}" --arg note "${4:-}" \
      '{kind:"episode_end",task:$task,ts_ns:$t,resolved:$r,note:$note}' >> "$logdir/calls.jsonl"
    kill "$(cat "$logdir/.sampler.pid")" 2>/dev/null; rm -f "$logdir/.sampler.pid";;
esac
