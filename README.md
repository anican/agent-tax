# agent-tax
Where do agent sandbox cycles go? A datacenter-tax case study on SWE-bench workloads.

An exploratory, Accelerometer-style characterization of coding-agent sandbox
workloads: 8 SWE-bench Verified tasks solved live by a coding agent inside a
Firecracker microVM (time view), and every shell command replayed under
`perf` (CPU view, timer-based on-CPU sampling).

- **REPORT.md** — pre-registered hypotheses, results, verdicts, caveats
- **ENV.md** — measurement environment (no hardware counters; kernel symbols OK)
- **TASKS.md** — tasks, setup, outcomes
- **DECISIONS.md** — every judgment call made during the unattended run
- **TAXONOMY.md** — leaf-function → category rules
- `tools/` — instrumentation, replay, analysis; `logs/` — raw episode logs;
  `results/` — per-replay counters/profiles and summary tables; `figs/` — figures
