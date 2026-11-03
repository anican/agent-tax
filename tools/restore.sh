#!/usr/bin/env bash
# restore.sh — make the task repo's working tree equal to checkpoint refs/snaps/<n>,
# rewriting ONLY files that differ (so unchanged files keep their mtimes and
# Python bytecode caches stay valid, as they would have been in the original run).
# Ignored files (build outputs, __pycache__, .pytest_cache) are left alone.
# usage: tools/restore.sh <task> <snap_n>
source /home/user/agent-tax/tools/env.sh
task=$1; n=$2; repo=$WORK/$task/repo
cd "$repo" || exit 1
target_commit=$(git rev-parse "refs/snaps/$n") || exit 1
target=$(git rev-parse "$target_commit^{tree}")
want_head=$(git rev-parse "$target_commit^1")
[ "$(git rev-parse HEAD)" != "$want_head" ] && git checkout -q --detach "$want_head"
cur=$(GIT_INDEX_FILE=$WORK/$task/restore.index sh -c 'git add -A . 2>/dev/null; git write-tree')
[ "$cur" = "$target" ] && exit 0
git diff-tree -r -z --no-renames --name-status "$cur" "$target" > "$WORK/$task/.restore.diff"
GIT_INDEX_FILE=$WORK/$task/restore.target.index git read-tree "$target"
while IFS= read -r -d '' st && IFS= read -r -d '' path; do
  if [ "$st" = D ]; then rm -f -- "$path"
  else GIT_INDEX_FILE=$WORK/$task/restore.target.index git checkout-index -f -- "$path"; fi
done < "$WORK/$task/.restore.diff"
git reset -q   # real index back to HEAD (the agent never staged anything)
