# Where do agent sandbox cycles go? — Report

Exploratory "datacenter tax" characterization of coding-agent sandbox
workloads, modeled on Accelerometer (Sriraman & Dhanotia, ASPLOS '20).
8 SWE-bench Verified tasks, solved live by a coding agent in a Firecracker
microVM (TIME VIEW), then every shell command replayed under `perf`
(CPU VIEW). All CPU numbers are **shares of timer-based on-CPU samples**
(`cpu-clock`, 999 Hz) — not cycles: this VM exposes no hardware counters.

Companion files: `ENV.md` (machine), `TASKS.md` (tasks, setup, outcomes),
`DECISIONS.md` (every judgment call, D0–D17), `TAXONOMY.md` (category
rules). Generated tables live in `results/summary/`, figures in `figs/`.

## Pre-registered hypotheses

Recorded on 2026-11-03, **before any data was collected**. These are not
revised afterwards; the verdicts are in the Results section.

- **H1:** Most episode wall-clock time is model/loop time, not tool execution.
- **H2:** Context switching and threading are significant CPU-time categories.
- **H3:** Memory movement (memcpy/memmove) is a significant CPU-time category.
- **H4:** Process lifecycle (fork/exec, dynamic linking, page faults, Python
  startup/imports) is a significant CPU-time category.

Operationalization (also fixed before data collection):
- "Most" (H1) = more than 50% of the summed episode wall-clock time across
  tasks, and in the majority of individual tasks.
- "Significant" (H2–H4) = at least 5% of the command's sampled on-CPU time,
  aggregated across all replayed commands, or at least 10% in at least one
  command class. "On-CPU time" here means **timer-based on-CPU samples**
  (`cpu-clock` at 999 Hz), not cycles.

## Summary of findings

| Hypothesis | Verdict | Key evidence |
|---|---|---|
| H1 model/loop dominates wall-clock | **Supported** | 58.7% of 714 s summed episode time; > 50% in 5 of 8 tasks. Tool time is 90% test runs. |
| H2 context switching / threading significant | **Not supported** (pre-registered rule) | 1.5% of on-CPU time over all replayed commands; largest class 9.9% (< 10%). Episode-only 8.5%, but mostly OpenMP spin-waiting in one scikit-learn task; kernel scheduler + futex only 0.3% overall / 1.5% of episode commands. |
| H3 memory movement significant | **Not supported** | 2.8% overall; largest class 5.8% (git). Kernel page zeroing/copy-to-user is about half of it. |
| H4 process lifecycle + Python startup/imports significant | **Supported** | 5.2% overall (just over the bar, diluted by compiler time), 13.2% of episode commands, 39–52% for short commands (search/read, ad-hoc Python). Holds under both CPUID mappings. |

Three things the hypotheses did not anticipate:

1. **The sandbox CPU is mostly idle.** Averaged over an episode, the 4-vCPU
   sandbox is 10.8% busy (27.7% during tool calls, 3.5% between them).
   Agent sandboxes are a low-utilization, latency-bound workload.
2. **A microVM tax on every process start.** In this guest one `CPUID`
   instruction costs ~11 µs (it is a VM exit). glibc's dynamic loader issues
   ~100 of them per process start for cache-size detection, so ~67% of a
   `/bin/true` start and ~29% of the on-CPU time of the agent's short
   search/read commands is CPUID exit overhead. Instruction counts (callgrind)
   put the same code at 0.4% — this cost is invisible without timing.
3. **Python memory management is the largest orchestration tax.**
   Allocation + cyclic GC is 12–14% of on-CPU time in test runs and package
   installs, ~2× its share of executed instructions (callgrind) — consistent
   with memory-bound pointer chasing. It is the largest orchestration
   category in test runs, package installs and builds (in ad-hoc scripts,
   imports are larger).

## Method in brief

- **Phase A (TIME VIEW).** The agent (Claude Code in this cloud session,
  effort level `high`, auto permission mode; DECISIONS.md D0) solved each
  task normally. Every shell command went through `tools/run.sh` (ns
  timestamps, exit code); every command and edit was checkpointed by
  `tools/snap.sh` (git commit of the working tree into a private ref, not
  touching HEAD/index); `tools/sample.sh` recorded `/proc/stat` and
  `/proc/meminfo` every 200 ms. **Gaps between agent actions approximate
  model + agent-loop time** (inference, API round trip, harness, permission
  checks); snapshots are counted separately as instrumentation.
- **Phase B (CPU VIEW).** Every recorded command (81: 26 setup, 55 in
  episodes) was replayed from its pre-command checkpoint: an unprofiled
  warm-up, then 3 × `perf stat` + `/usr/bin/time -v` and 3 × `perf record -a
  -g -e cpu-clock -F 999`, each from freshly restored state (10-minute cap).
  Read-only commands under 1 s also got 3 looped profiles (30 executions
  each), weighted so each command still counts once (D8). Samples are
  attributed to the replayed command's process tree; kernel threads are
  kept separately (0.14% of command samples); idle and unrelated processes
  are dropped (unrelated: 0.9% of all samples). Leaf function + syscall +
  stack-context flags → category via the ordered rule table in TAXONOMY.md.
- **Replay interpreter.** The live venvs used a stripped Python 3.11; replays
  swap in an unstripped, frame-pointer CPython 3.11.15 (same ABI) so that
  interpreter internals (pymalloc, GC, parser) resolve (D3).
- **Cross-checks.** callgrind on 7 commands (reduced subsets), `-X
  importtime` on 13 commands, a CPUID microbenchmark, and two public
  bash-only mini-swe-agent trajectories for the same tasks, replayed through
  the identical pipeline (D13).

## Results — TIME VIEW

![time breakdown](figs/time_breakdown.png)

{{include:results/summary/time_view_table.md}}

Episode wall-clock was 54–146 s per task (the agent solved 7 of 8 tasks;
TASKS.md). The median gap between consecutive agent actions was 3.8–4.6 s
per task. Tool execution is dominated by test runs (262 of 291 s; 90%); all
search/read commands together took 0.2 s and git 1.2 s. The three tasks
where tool time exceeds model time (requests, scikit-learn, sympy-24562)
each contain one long test invocation (52–69 s). Setup (clone, venv,
install) is excluded from episodes by design (SWE-bench ships pre-built
environments) and would otherwise dominate: scikit-learn's setup alone took
677 s because `pip install -e .` recompiled every extension after an
explicit `build_ext` (TASKS.md).

**Sandbox CPU utilization** from the 200 ms sampler (busy = user + nice +
system + irq + softirq + steal over all 4 vCPUs):

{{include:results/summary/sandbox_utilization.md}}

Per-task timelines (CPU busy %, steal %, memory; blue spans = tool calls)
are in `figs/timeline_<task>.png`; e.g. scikit-learn:

![sklearn timeline](figs/timeline_scikit-learn__scikit-learn-26194.png)

Most tool calls keep about one vCPU busy (~25% of the machine); the
parallel Django test run and OpenMP sections of the scikit-learn tests are
the exceptions. Steal time stayed below 0.5% on average.

## Results — CPU VIEW

### Category shares by command class (all 81 replayed commands)

Mean ± std over the 3 replays (pooled over the commands in each class, i.e.
time-weighted). "raw samples/rep" = timer samples per replay round (999 Hz
per CPU ⇒ ≈ CPU-ms).

![cpu categories](figs/cpu_category_shares.png)

{{include:results/summary/cpu_category_shares.md}}

The ALL row is dominated (72.5% of samples) by two scikit-learn setup
commands that compile C/C++ extensions (`build_ext` and the editable
install that rebuilt them), so it mostly describes **gcc**. The
episode-only view is more representative of what an agent does during a
task:

![cpu categories, episode only](figs/cpu_category_shares_episode_only.png)

{{include:results/summary/cpu_category_shares_episode_only.md}}

Per task (episode commands only):

{{include:results/summary/cpu_category_shares_by_task_episode.md}}

What the classes look like:

- **search/read** (grep, sed -n, cat, find): ~12 ms per command and almost
  none of it is the search itself (core logic 1.9%). It is process creation:
  CPUID-bound CPU-feature detection in ld.so 28% (virtualization-related,
  D16), exec/fork/exit syscalls 16%, page faults 12%, the rest of dynamic
  linking 11% (incl. mmap of libraries), shell glue 8%, kernel page
  allocation 5% and page zeroing/copy 4.5%.
- **git**: zlib inflate (22% compression) and the clone's file creation
  (filesystem metadata 18 ± 8%; the large variance is one replay round of the
  Django clone hitting ext4's recently-deleted-inode scan, see Caveats).
- **test run**: interpreter 57%, allocation + GC 14%, imports 10%,
  scheduling 8.6% (almost all OpenMP runtime and `sched_yield` in the
  scikit-learn tests).
- **package install**: in this data, dominated by the compiler (scikit-learn
  editable install); the episode-only install (flask: `pip install
  "pytest<8"`) is 25% core, 27% allocation, 22% imports.
- **other** (ad-hoc reproduction scripts, `python -c` checks): 43% imports +
  9% process lifecycle — these scripts mostly pay for importing sympy /
  sklearn and exit.

Selected sub-categories (share of all on-CPU samples, all commands):
`results/summary/cpu_subcategory_shares.csv`; by class:
`results/summary/cpu_subcategory_shares_by_class.csv`.

### Top 20 leaf functions (all replayed commands, share of on-CPU samples)

{{include:results/summary/top20_leaf_functions.md}}

`cc1`/`cc1plus`/`as` are stripped compiler binaries (attributed by DSO,
TAXONOMY rule U0c). Top-10 leaves per class:
`results/summary/top10_leaf_functions_by_class.csv`.

### Inclusive (stack-context) shares

Leaf-first attribution undercounts activities whose leaves are generic. The
share of samples with a given frame anywhere on the stack:

{{include:results/summary/inclusive_context_table.md}}

E.g. 15% of test-run on-CPU time is under an import frame (vs 10% when only
interpreter leaves are counted), and 18% of search/read time is inside page
faults.

### perf stat and rusage by class

Sums over commands (mean of 3 reps per command), normalized per CPU-second
of task-clock; medians per command.

{{include:results/summary/counters_by_class.md}}

Short commands are kernel-heavy (sys share 40–42% for search/read and git vs
6% for test runs) and fault-heavy (45k page faults per CPU-second for
search/read). Test runs context-switch ~480 times per CPU-second (281
of them involuntary); at a few µs per switch that is well under 1% of CPU
time, consistent with the H2 verdict. Repeat-to-repeat variability
of task-clock: median CV 8%, p90 19% (`counters_repeat_cv.csv`).

### Accelerometer inputs

On-CPU time share (mean ± std over 3 replays) of the three categories with
off-the-shelf accelerators:

{{include:results/summary/accelerometer_inputs.md}}

Notes for plugging these in: compression in this workload is zlib
inflate — pip unpacking wheels (the larger part in absolute terms) and
`git clone/fetch` (22% of the small git class); hashing is mostly CPython's
siphash for `str` hashing and SHA-256 in pip (wheel hash checks), while
git's SHA-1 is negligible;
memory movement is split about evenly between user-space `memcpy/memset` and
kernel copy/zero (`clear_page_erms`, `rep_movs_alternative`), see
`cpu_subcategory_shares_by_class.csv`. All are timer-sample shares, not
cycle shares.

## Cross-checks

### callgrind vs perf (user-space only, leaf-only rules)

callgrind counts executed instructions; perf counts on-CPU time. Both sides
use the same taxonomy without stack context. Format: callgrind % / perf %.

{{include:results/callgrind/compact.md}}

- For Python commands the two agree on the ranking (core ≫ allocation ≫
  serialization/parsing ≈ memory movement), but **allocation + GC takes
  1.5–2.3× more of the time than of the instructions**, while the interpreter
  loop and the parser take less — consistent with GC/pymalloc being
  memory-bound (high CPI) and the eval loop/parser being compute-bound. No
  cache-miss counters exist here to confirm the mechanism.
- **CPUID**: glibc's feature detection is 0.4% of instructions but 57% of
  user-space time in `grep | sed` (27% in `git diff`).
- **OpenMP**: scheduling is 0.5% of instructions but 7.1% of time in the
  scikit-learn test: valgrind serializes threads, so barrier spin-waits
  barely run under it, while on real CPUs they burn time.
- Per-sample details: `results/callgrind/summary.md`.

### `-X importtime` (PYTHONPROFILEIMPORTTIME=1, mean of 3 runs)

{{include:results/importtime/summary.md}}

Summed top-level import time (wall time inside the import system, including
module-level code and I/O) is a median **39%** of a sampled command's wall
time (range 4–77%). The 4% case is Django's parallel test run, whose forked
workers inherit already-imported modules. This is consistent with the
stack-based perf metric (15% of test-run on-CPU time under an import frame)
given that importtime also counts imports' module-level execution and
waiting. A first pass under-reported pytest commands because pytest's
output capture swallowed the report; it was redone (D11).

### Public trajectories (optional step)

Two bash-only mini-swe-agent trajectories (public SWE-bench submission
`bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514`) for the same
tasks were re-executed and profiled with the identical pipeline (D13).
Episode commands only:

{{include:results/summary/mini_vs_own.md}}

That agent issues 3–5× more commands, many of them tiny Python scripts and
`sed -i` edits, so its CPU goes to interpreter startup/imports (29–39%),
process lifecycle and allocation; this study's agent ran fewer, larger
test commands, so more of its CPU is core interpreter work. The *mix* of
orchestration categories (imports, allocation, lifecycle) is similar; the
proportions depend strongly on how the agent batches work into commands.

## Hypothesis verdicts in detail

Evaluated by `tools/hypotheses.py` with the pre-registered thresholds.

{{include:results/summary/hypotheses.md}}

- **H1 — supported.** The margin is moderate (58.7%) and task-dependent:
  any task with one long test run flips to tool-dominated. The gaps include
  everything that is not tool execution (inference, network, harness,
  permission classification, the extra checkpoint tool call per edit), so
  they upper-bound pure model time.
- **H2 — not supported** under the pre-registered rule (1.5% aggregate;
  largest class 9.9%, just below 10%). Restricted to episode commands the
  category reaches 8.5%, but it is concentrated in one task (scikit-learn,
  18.5% of its episode time) and is mostly OpenMP barrier spin-waiting and
  `sched_yield` — threading *waste*, attributed via the libgomp DSO (D15) —
  rather than kernel context-switch work (kernel scheduler + futex: 0.3%
  overall, 1.5% of episode commands). Off-CPU blocking is invisible to
  on-CPU sampling by design. Note also that timer sampling biases kernel
  time toward interrupt-enable points such as `finish_task_switch` (see
  Caveats), which if anything inflates this category.
- **H3 — not supported.** 2.8% overall, never above 5.8% in any class.
  The largest component is kernel page zeroing/copy for short-lived
  processes, not application `memcpy`.
- **H4 — supported.** 5.2% aggregate is only just above the threshold
  because two compiler-bound setup commands contribute 72.5% of all samples;
  for episode commands it is 13.2%, and for short commands it dominates
  (search/read 39% even after moving the CPUID cost to virtualization; 68%
  with the original mapping). Interpreter startup/imports is the larger
  half overall (3.3% vs 1.8%; 10.6% vs 2.6% for episode commands).

## What did not go as planned (plain list)

- **Pushing to GitHub failed for the whole study** (HTTP 403: the session's
  GitHub App has no write access to `anican/agent-tax`; API branch creation
  also 403). All work is committed locally on
  `claude/environment-diagnostics-8tfnrb` (D4).
- Building CPython from the python.org tarball was refused by the session's
  permission classifier; a uv-managed python-build-standalone 3.11.15 was
  used for replays instead (D3).
- Live episodes ran on a stripped interpreter; replays on a different 3.11
  build (D3).
- The first wave-1 replay mis-parsed `perf script` output; it was caught by
  a sanity check and fully redone (D7).
- Replay-harness artifacts were found and fixed before reporting: ext4
  inode-allocation churn from deleting scratch dirs, venv state not
  checkpointed, stripped interpreter in recorded setup commands (D10).
- The wave-2 batch was killed by the 2-hour background-command limit; it was
  resumed at rep granularity, and one empty `perf stat` repetition was
  re-measured (D14, D15).
- Two cross-check bugs (importtime capture, callgrind header parsing) were
  found and fixed before use (D11).
- Two post-hoc taxonomy/classification changes were made with explicit
  evidence: libgomp → scheduling (D15) and CPUID feature detection →
  virtualization (D16); one command changed class (D17).
- One task (django__django-16667) was not resolved (TASKS.md).
- Only 2 of the 5 downloaded public trajectories were replayed (the others'
  venvs had already been cleaned up).

## Caveats

1. **Timer-based sampling, not cycles.** No hardware PMU is exposed to the
   guest (ENV.md), so every CPU-view number is a share of `cpu-clock`
   samples (999 Hz hrtimer, per CPU) = a share of *on-CPU time*. There is no
   IPC, cycle, cache-miss or stall data; a category with low IPC and one with
   high IPC look the same per unit of time. Sampling via a software hrtimer
   also skids in kernel code that runs with interrupts disabled: such time is
   charged to where interrupts are re-enabled (`_raw_spin_unlock_irqrestore`,
   `finish_task_switch`), biasing attribution toward those functions.
2. **Kernel symbol resolution worked** (kptr_restrict = 0, root, kallsyms
   readable; perf 6.8 userspace on a 6.18 kernel). Call chains were complete;
   frame-pointer unwinding of Python worked with the replay interpreter.
   Some third-party wheels (OpenMP runtime, OpenBLAS, compilers) are
   stripped; their internals are attributed by DSO or left UNCLASSIFIED
   (0.4% of samples overall).
3. **MicroVM.** Everything ran in a Firecracker/KVM guest with 4 vCPUs.
   Hypervisor work is invisible to in-guest sampling except where it shows
   up as time attributed to the trapping guest instruction (CPUID) or as
   steal. "virtualization-related" is therefore a lower bound; the CPUID
   finding is specific to this hypervisor configuration (11 µs per CPUID is
   far slower than typical KVM) and would look very different on bare metal.
4. **Cloud-VM noise.** Absolute times vary (task-clock CV median 8%, p90
   19% across repeats); the report emphasizes shares, with std over 3
   replays. One replay round of the Django clone spent 26% of its samples in
   ext4's recently-deleted-inode scan (a filesystem-state effect that the
   harness fix of D10 reduced but did not eliminate for that command); it
   is kept and shows up as the ±8 pp variance of git's filesystem-metadata
   share.
5. **Replay ≠ live run.** CPU profiles come from replays, not from the live
   episodes: different (symbol-rich) 3.11 build, warm page and bytecode
   caches (the live run's first test invocation also compiled bytecode),
   warm pip download cache, fresh scratch venvs for installs, output written
   to a file instead of a pipe to the agent harness (D3, D6, D10).
6. **Scope.** Python repositories only, SWE-bench Verified only, 8 tasks,
   one agent (Claude Code, one model at effort `high`, auto permission
   mode), which explored with shell commands as instructed (D2). Agents
   that use built-in file tools, containers, or many small scripts (see the
   mini-swe-agent comparison) produce different command mixes. Model time
   depends on the model, effort level, harness version and API load.
7. **Logging perturbation.** Each command paid for the `run.sh` wrapper and
   a git snapshot (0.5% of episode time, shown separately); each edit cost
   one extra tool call for its checkpoint, which inflates model/loop time
   slightly (D1).
8. **Small samples.** Few commands per class for some classes (build: 1
   command; other: 6). Sample counts are listed with every share.

## Reproducing / file map

- `tools/run.sh`, `tools/snap.sh`, `tools/sample.sh`, `tools/episode.sh` —
  Phase A instrumentation; `tools/restore.sh` — checkpoint restore;
  `tools/eval_task.sh` — hidden-test resolution check.
- `tools/replay.py`, `tools/replay_loop.py`, `tools/perfparse.py` —
  Phase B; `tools/taxonomy.py` — categories; `tools/analyze.py`,
  `tools/hypotheses.py` — tables/figures; `tools/build_report.py` — this
  report.
- `tools/callgrind_check.py`, `tools/importtime.py`,
  `tools/microbench/cpuid_cost.c`, `tools/traj_record.sh`,
  `tools/extract_traj_cmds.py` — cross-checks.
- `logs/<task>/calls.jsonl` (every command, edit checkpoint and episode
  marker with ns timestamps), `logs/<task>/sampler.csv`,
  `logs/<task>/out/` (command outputs, truncated at 200 kB),
  `logs/<task>/eval.*` (resolution checks).
- `results/<task>/<seq>/` — per-replay `perf stat` CSV, `time -v`,
  parsed profile JSON (raw zstd `perf.data` kept locally, git-ignored).
