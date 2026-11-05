# Warm-interpreter ceiling (fork-server / snapshot opportunity)

`tools/warm_interp.sh`: 5 fresh `python -m pytest -q <target>` processes vs 5
`pytest.main()` calls inside one already-running process (warm page cache in
both). This bounds what a warm-interpreter mechanism (fork server, CRIU
snapshot) could save per tool call; repeated `pytest.main()` in one process
is **not** a safe implementation (module state leaks — see the sympy pass
count).

| Workload (pytest target) | fresh process, mean wall s (5 runs) | warm process, 1st call s | warm, calls 2–5 mean s | wall saving (steady state) | total CPU, 5 fresh vs 5 warm (ms) | passed fresh / warm |
|---|---|---|---|---|---|---|
| pytest `testing/logging` | 1.41 | 1.26 | 1.11 | 21% | 6854 vs 5860 | 59 / 59 |
| sympy `sympy/physics/units` | 1.02 | 0.84 | 0.49 | 52% | 5150 vs 3002 | 70 / 67 |
| flask `tests/test_blueprints.py` | 0.39 | 0.28 | 0.15 | 63% | 1978 vs 1004 | 59 / 59 |

- Steady-state saving per invocation: 22% (pytest's own suite, whose
  collection dominates), 52% (sympy, import-heavy), 63% (flask). Total CPU
  for 5 runs drops 15% / 42% / 49%.
- The first in-process call is only 10–27% cheaper than a fresh process: the
  saving comes from imports and collection already being done, which is
  exactly the import share measured with `-X importtime` (median 39% of
  command wall time).
- Caveat visible in the data: sympy passes 70 tests fresh but 67 on warm
  re-runs — state carried across runs changes results. A production
  mechanism must fork from the warmed state (copy-on-write) rather than
  re-run in place.
