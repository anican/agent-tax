#!/usr/bin/env bash
# traj_record.sh — optional step B5: re-execute a public mini-swe-agent (bash-only)
# trajectory's commands, in order, through run.sh so every command gets a
# pre-command checkpoint, exactly like our own episodes. The pseudo-task
# "mini__<task>" shares the task's repo and venv (symlinks); its checkpoints
# live under refs/mini/* so they never collide with the agent's refs/snaps/*.
# Commands were reviewed by hand before running (see DECISIONS.md D13).
# usage: tools/traj_record.sh <task> <cmds.json>
source /home/user/agent-tax/tools/env.sh
task=$1; cmds=$2; P=mini__$task; export SNAP_NS=mini
mkdir -p $WORK/$P; ln -sfn $WORK/$task/repo $WORK/$P/repo; ln -sfn $WORK/$task/venv $WORK/$P/venv
cp $WORK/$task/meta.json $WORK/$P/meta.json
base=$(jq -r .base_commit $WORK/$task/meta.json)
(cd $WORK/$task/repo && git checkout -q -f --detach "$base" && git clean -qfd)
rm -rf $AT_ROOT/logs/$P; mkdir -p $AT_ROOT/logs/$P
"$AT_ROOT/tools/snap.sh" $P episode_start >/dev/null
n=$(jq '.cmds | length' "$cmds")
for i in $(seq 0 $((n-1))); do
  c=$(jq -r ".cmds[$i]" "$cmds")
  timeout 600 "$AT_ROOT/tools/run.sh" $P -- "$c" > /dev/null 2>&1
done
"$AT_ROOT/tools/snap.sh" $P episode_end >/dev/null
(cd $WORK/$task/repo && git reset -q)
echo "recorded $n commands for $P"
