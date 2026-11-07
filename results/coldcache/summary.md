# Cold vs warm page cache (sandbox recycling cost)

`tools/coldcache.sh`: each command run warm, then after `sync; echo 3 >
/proc/sys/vm/drop_caches` (cold); 3 pairs per command; wall from
`/usr/bin/time`, CPU and faults from `perf stat`. Workloads: django
`runtests.py migrations.test_optimizer`, sympy `pytest sympy/physics/units`,
pytest `pytest testing/logging`, and `grep -rn` over `django/db/migrations`.

| Workload (N=1 test command) | warm wall s | cold wall s | wall Δ | warm CPU ms | cold CPU ms | CPU Δ | major faults (cold) |
|---|---|---|---|---|---|---|---|
| django | 0.26 | 0.43 | +62% | 266 | 349 | +32% | 211 |
| sympy | 1.02 | 1.20 | +18% | 1023 | 1132 | +11% | 168 |
| pytest | 1.40 | 1.54 | +10% | 1335 | 1420 | +6% | 165 |
| grep | 0.00 | 0.01 | +nan% | 6 | 9 | +61% | 8 |

- A cold cache adds 0.1–0.2 s of wall time per test command here (10–60%),
  from ~170–210 major faults (interpreter, venv `.so`/`.pyc` files and the
  repository being re-read from the virtio disk), and 7–30% more CPU
  (kernel read path, readahead, page-cache fill).
- The absolute cost is small per command but is paid on *every* command
  after a recycle; the original study's replays ran warm (D6), so its CPU
  view under-represents this kernel I/O work for freshly started sandboxes.
