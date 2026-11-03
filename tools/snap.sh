#!/usr/bin/env bash
# snap.sh — checkpoint the task repo's working tree without touching HEAD,
# branch or the real index: `git add -A` into a private index, write-tree,
# commit-tree, store as refs/snaps/<n>. Logs kind=snap to calls.jsonl.
# usage: tools/snap.sh <task> <reason>     (reason: edit | start | end | after_cmd:<seq> | ...)
source /home/user/agent-tax/tools/env.sh
task=$1; reason=${2:-manual}
repo=$WORK/$task/repo; logdir=$AT_ROOT/logs/$task; mkdir -p "$logdir"
t0=$(date +%s%N)
cd "$repo" || exit 1
export GIT_INDEX_FILE=$WORK/$task/snap.index   # per (pseudo-)task private index
git add -A . 2>/dev/null
tree=$(git write-tree)
head=$(git rev-parse HEAD)
n=$(( $(cat "$logdir/.snapn" 2>/dev/null || echo 0) + 1 )); echo $n > "$logdir/.snapn"
commit=$(echo "snap $n $reason" | git commit-tree "$tree" -p "$head")
git update-ref "refs/${SNAP_NS:-snaps}/$n" "$commit"
echo "$n" > "$logdir/.last_snap"
t1=$(date +%s%N)
jq -nc --arg task "$task" --argjson n $n --arg reason "$reason" --arg commit "$commit" \
  --arg tree "$tree" --arg head "$head" --argjson start_ns $t0 --argjson end_ns $t1 \
  '{kind:"snap",task:$task,snap:$n,reason:$reason,commit:$commit,tree:$tree,head:$head,start_ns:$start_ns,end_ns:$end_ns,dur_s:(($end_ns-$start_ns)/1e9)}' \
  >> "$logdir/calls.jsonl"
echo "[snap.sh] snap=$n reason=$reason $(( (t1-t0)/1000000 ))ms"
