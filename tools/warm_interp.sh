#!/usr/bin/env bash
# warm_interp.sh — ceiling of a "warm interpreter" (fork-server / snapshot)
# optimization for repeated test invocations: N fresh `python -m pytest`
# processes vs N `pytest.main()` calls inside one already-started process.
# (Repeated pytest.main() in one process is not production-safe — module
# caching can leak state between runs — it is used only to bound the saving.)
PERF=/usr/lib/linux-tools/6.8.0-147-generic/perf; W=/home/user/work; OUT=/home/user/agent-tax/results/warminterp
S=/tmp/claude-0/-home-user-agent-tax/bb9091d6-0001-5f4a-a230-6236adda4caf/scratchpad; N=5
echo "workload,mode,iteration,wall_s,passed" > $OUT/warminterp.csv
for spec in "pytest:$W/pytest-dev__pytest-10051:testing/logging" "sympy:$W/sympy__sympy-24066:sympy/physics/units" "flask:$W/pallets__flask-5014:tests/test_blueprints.py"; do
  name=${spec%%:*}; rest=${spec#*:}; base=${rest%%:*}; target=${rest#*:}
  cd $base/repo; export VIRTUAL_ENV=$base/venv PATH=$base/venv/bin:$PATH
  python -m pytest -q -p no:cacheprovider $target >/dev/null 2>&1   # warm page cache
  $PERF stat -x, -e task-clock -o $S/fresh.stat -- bash -c "for i in \$(seq $N); do s=\$(date +%s.%N); python -m pytest -q -p no:cacheprovider $target > $S/out.txt 2>&1; e=\$(date +%s.%N); echo \"$name,fresh,\$i,\$(echo \"\$e - \$s\" | bc),\$(grep -oE '[0-9]+ passed' $S/out.txt | head -1 | cut -d' ' -f1)\" >> $OUT/warminterp.csv; done"
  fresh_tc=$(grep task-clock $S/fresh.stat | cut -d, -f1)
  $PERF stat -x, -e task-clock -o $S/warm.stat -- python - <<PY >> $OUT/warminterp.csv 2>/dev/null
import pytest, time, io, contextlib, re
for i in range(1, $N + 1):
    buf = io.StringIO(); t = time.perf_counter()
    with contextlib.redirect_stdout(buf): pytest.main(["-q", "-p", "no:cacheprovider", "$target"])
    m = re.search(r"(\d+) passed", buf.getvalue()); print(f"$name,warm,{i},{time.perf_counter()-t:.3f},{m.group(1) if m else 'NA'}")
PY
  warm_tc=$(grep task-clock $S/warm.stat | cut -d, -f1)
  echo "$name total task-clock ms: fresh x$N = $fresh_tc, warm x$N (one process) = $warm_tc" | tee -a $OUT/task_clock.txt
done
cat $OUT/warminterp.csv
