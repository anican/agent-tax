# Process-start cost decomposition (this microVM)

Measured with `tools/microbench/spawnbench.c`: a C launcher does
fork+execve+waitpid N times (no shell in the loop); wall time per spawn from
the launcher, CPU time from `perf stat -e task-clock` on the launcher
(includes the children). 3 runs each (N = 2000, 1000 for grep, 300 for python).
Raw: `spawn_cost.csv`; profiles of the three C variants: `spawn_profile_*.txt`;
CPUID cost: `cpuid_cost.txt` (~11 µs per CPUID, leaves 0/2/4).

| Target | What runs | wall µs/spawn | CPU µs/spawn | Δ CPU vs previous row |
|---|---|---|---|---|
| nolibc | no libc, no ld.so (`exit` syscall only) | 137 ± 5 | 114 ± 3 |  |
| static_glibc | `int main(){return 0;}`, static glibc (no ld.so) | 768 ± 8 | 709 ± 8 | +595 |
| dynamic_glibc | same, dynamically linked (ld.so + libc.so) | 884 ± 23 | 811 ± 21 | +102 |
| dynamic_glibc_tunables | dynamic, with `GLIBC_TUNABLES` cache sizes set | 870 ± 11 | 799 ± 11 | -12 |
| bin_true | `/bin/true` | 909 ± 13 | 832 ± 11 | +33 |
| grep_small | `grep -q main` on a 1-line file | 1089 ± 18 | 993 ± 14 | +161 |
| python_S_c_pass | `python -S -c pass` (no site) | 8788 ± 3875 | 6434 ± 235 | +5441 |
| python_I_c_pass | `python -I -c pass` (isolated, site on) | 8576 ± 316 | 8119 ± 33 | +1685 |
| python_c_pass | `python -c pass` | 8441 ± 132 | 8173 ± 122 | +54 |
| python_import_json | `python -c "import json,re,os"` | 16113 ± 1418 | 14848 ± 204 | +6675 |

What it says:

- The kernel floor for fork+exec+exit+wait of a trivial process is ~110 µs
  of CPU here (nolibc row; dominated by fork's page-table copy, memcg
  charging and scheduler work, see `spawn_profile_nolibc.txt`).
- **glibc's own start-up adds ~590 µs even for a statically linked binary**
  (no dynamic loader involved). The profile of the static variant is led by
  `intel_check_word` / `get_common_cache_info` — the CPUID-driven cache-size
  detection in `init_cacheinfo` — so this is the CPUID VM-exit cost
  (D16), not symbol resolution. ~590 µs / 11 µs ≈ 55 CPUIDs per start.
- The dynamic loader itself (relocation, symbol lookup, mmap of libc) adds
  only ~100 µs more on top.
- `GLIBC_TUNABLES` cache-size settings do **not** avoid the detection (glibc
  2.39 runs `handle_intel` unconditionally and applies tunables afterwards):
  no measurable change. Avoiding it would need a glibc change (or a libc that
  does not probe caches at start-up, e.g. musl) — not tested here.
- A bare CPython start (`-S -c pass`) costs ~6.3 ms of CPU; `site` adds
  ~1.8 ms; importing `json, re, os` on top adds ~6.6 ms. For comparison,
  the whole live `grep`/`sed` commands of the agent episodes took ~12 ms wall
  including the `run.sh` wrapper (a bash + date + tee + jq ≈ 6 process
  starts).
