#!/usr/bin/env bash
# eval_task.sh — post-hoc resolution check (NOT part of the episode, not replayed).
# Restores the episode_end checkpoint, resets the files touched by the hidden
# SWE-bench test_patch to the base commit, applies it, runs FAIL_TO_PASS tests,
# then restores the episode_end checkpoint again.
# usage: tools/eval_task.sh <task>
source /home/user/agent-tax/tools/env.sh
task=$1; W=$WORK/$task; repo=$W/repo; L=$AT_ROOT/logs/$task
endsnap=$(jq -r 'select(.kind=="snap" and .reason=="episode_end") | .snap' "$L/calls.jsonl" | tail -1)
"$AT_ROOT/tools/restore.sh" "$task" "$endsnap"
cd "$repo"; base=$(jq -r .base_commit "$W/meta.json"); repo_name=$(jq -r .repo "$W/meta.json")
files=$(git apply --numstat "$W/eval/test.patch" | cut -f3)
for f in $files; do git cat-file -e "$base:$f" 2>/dev/null && git checkout -q "$base" -- "$f" || rm -f "$f"; done
git apply "$W/eval/test.patch" || { echo "test.patch failed to apply"; exit 2; }
export VIRTUAL_ENV=$W/venv PATH=$W/venv/bin:$PATH
mapfile -t F2P < <(jq -r '.FAIL_TO_PASS[]' "$W/eval/tests.json")
case $repo_name in
  django/django)
    labels=$(printf '%s\n' "${F2P[@]}" | python3 -c '
import sys,re
for l in sys.stdin:
    m=re.match(r"(\w+) \(([\w.]+)\)",l.strip())
    if not m: continue
    name,path=m.groups()
    print(path if path.endswith("."+name) else path+"."+name)')
    (cd tests && python runtests.py --verbosity 2 --parallel 1 $labels) > "$L/eval.txt" 2>&1; rc=$?;;
  sympy/sympy)
    tfiles=$(printf '%s\n' $files | grep '/tests/test_')
    k=$(printf '%s\n' "${F2P[@]}" | paste -sd'|' | sed 's/|/ or /g')
    python -m pytest -q -p no:cacheprovider $tfiles -k "$k" > "$L/eval.txt" 2>&1; rc=$?;;
  *)
    python -m pytest -q -p no:cacheprovider "${F2P[@]}" > "$L/eval.txt" 2>&1; rc=$?;;
esac
tail -5 "$L/eval.txt"
git reset -q; git checkout -q -- . ; git clean -fdq
"$AT_ROOT/tools/restore.sh" "$task" "$endsnap"
res=$([ $rc = 0 ] && echo resolved || echo unresolved)
jq -nc --arg task "$task" --arg res "$res" --argjson rc $rc --argjson n ${#F2P[@]} '{task:$task,fail_to_pass_n:$n,rc:$rc,result:$res}' > "$L/eval.json"
cat "$L/eval.json"
