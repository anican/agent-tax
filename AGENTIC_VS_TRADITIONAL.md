# Agentic sandbox workloads vs. traditional datacenter workloads — what is new, what is the same

An empirical comparison, limited to what this study measured (8 SWE-bench
Verified episodes, 81 replayed commands, timer-sampled on-CPU profiles in a
4-vCPU Firecracker microVM; see REPORT.md) plus the two extension experiments
(process-start decomposition, density). Where the "traditional" side comes
from published work rather than from measurements here, it is marked
*(literature)*; the comparison is structural in those rows, not numerical.
Reference points: Kanev et al., "Profiling a warehouse-scale computer"
(ISCA '15: the "datacenter tax" — allocation, memmove, RPC/serialization,
compression, hashing — is reported at roughly a quarter to a third of fleet
cycles) and Sriraman & Dhanotia, "Accelerometer" (ASPLOS '20: orchestration
overheads in microservices and an analytical model for accelerating them).

## 1. Pattern table

| # | Pattern | What was measured here | Traditional microservice / VM fleet | New or same? | Implication / opportunity |
|---|---|---|---|---|---|
| 1 | **The CPU is mostly idle and the critical path is off-box.** | 4-vCPU sandbox 10.8% busy averaged over episodes (28% during tool calls, 3.5% between); 58.7% of episode wall-clock is model/loop time; median gap between agent actions 3.8–4.6 s (REPORT.md, time view). With a second model on 3 fresh tasks (extension, D18): 94.7% model/loop, median gap 5.6–7.5 s — the share is set by how much testing the agent chooses to run, not by the sandbox. | Microservices are provisioned for throughput and run at tens of % utilization by design, with the service itself on the critical path *(literature; typical fleet utilization targets)*. | **New in degree.** The sandbox is a latency-bound *client* of a remote model; it waits ~60% of the time for inference it does not run. | Oversubscribe sandboxes (many per host); schedule for tool-call latency, not sandbox throughput. The density experiment (§3) measures how far this goes on this VM. |
| 2 | **Work arrives as a burst of short-lived processes, not as a long-lived server.** | 53 episode commands in 8 tasks; the agent's `grep`/`sed`/`git` commands run 10–100 ms and are 98% process start-up: CPUID-bound libc init 28%, exec/fork/exit 16%, page faults 12%, rest of ld.so 11% (REPORT.md, search/read class); each live command also spawned ~6 wrapper processes. | A microservice process lives for hours–days; per-request overhead is RPC/serialization, not `execve` *(literature; Kanev's tax has no process-lifecycle component)*. | **New.** "Process lifecycle" is a top-level tax category here and absent from the classic tax. | Avoid exec: persistent tool servers (a long-lived grep/git/python helper), or make exec cheap (see rows 3–4). |
| 3 | **A per-exec hypervisor tax that instruction profilers cannot see.** | One `CPUID` ≈ 11 µs in this guest (VM exit); glibc's cache-size probing issues ~55 of them per process start: a *static* glibc binary costs 709 µs CPU to spawn vs 114 µs for a no-libc binary; `GLIBC_TUNABLES` does not avoid it (results/microbench/). callgrind shows the same code at 0.4% of instructions. | VMs pay VM exits too, but long-lived services amortize start-up; the same CPUID storm happens once per process, i.e. ~never *(structural)*. | **New.** The cost is old (KVM exits) but the *rate* is new: agents exec thousands of times per task. | A glibc change (cache probing via `sysfs`/cached values, or skipping leaf-2/4 enumeration in guests) or a libc that does not probe at start-up would remove ~70% of the cost of every short command here. Verify on other hypervisors first (this guest's 11 µs is unusually slow). |
| 4 | **Interpreter start-up and imports are a tax, repeatedly paid.** | Bare CPython start 6.4 ms CPU, +1.8 ms for `site`, +6.6 ms for `json,re,os`; import machinery is 10% of test-run on-CPU time (15% inclusive), 43% of ad-hoc scripts; `-X importtime` puts imports at a median 39% of sampled commands' wall time; a forked test runner (Django `--parallel 4`) drops it to 4%. | Python services import once at start-up; JIT/warm-up costs exist but are amortized over millions of requests *(structural)*. | **New in degree.** Same mechanism as cold starts in serverless *(literature)*, but here it recurs every tool call within one session. | Snapshot/restore a warmed interpreter (CRIU, fork-server, `python -X frozen_modules`, lazy imports); keep one test-runner process alive across tool calls. The mini-swe-agent comparison shows agents that emit many tiny scripts pay 29–39% of CPU in imports. |
| 5 | **Allocation / GC is the largest classic tax category; memcpy, compression, hashing are small.** | Allocation + cyclic GC 12–14% of test-run/install CPU, ~2× its instruction share (callgrind); memory movement 2.8%, compression 0.4%, hashing 0.2% overall (git: compression 22%). | Kanev et al. report allocation and memmove among the top tax items and compression/hashing/serialization as sizeable *(literature)*; Accelerometer targets compression, hashing, memcpy, serialization for offload. | **Same category, different mix.** Allocation is a shared pain point; the accelerator-friendly categories (compression/hashing/memcpy) are 1–2 orders of magnitude smaller here than in RPC-heavy services. | Accelerometer-style offload has little to gain on agent sandboxes except for git-heavy phases (clone/fetch). The allocator/GC is the better target (pymalloc tuning, GC thresholds, arena reuse). |
| 6 | **Serialization/RPC is nearly absent.** | serialization/parsing 2.0% overall and that is mostly CPython source compile/marshal, not wire formats; no RPC on the sandbox side (the agent harness talks to the model API off-box). | RPC + protobuf serialization is a core tax component in service fleets *(literature)*. | **Different.** The "RPC" of an agent is the model call, and its cost lands in the model service, not the sandbox. | Nothing to accelerate on the sandbox; the model-side serving stack is where RPC tax lives. |
| 7 | **Filesystem metadata and page-cache churn come from the toolchain, not from serving data.** | fs-metadata 18% of git CPU (clone creates ~10k files), 5% of search/read; 45k page faults per CPU-s in search/read; pip/venv creation dominates setup CPU. | Services do metadata work mostly for logging/config; storage services are a separate tier *(structural)*. | **New in kind.** Environment construction (clone, venv, build) is per-task work that a service fleet does at deploy time, once. | Prebuilt, snapshotted environments (as SWE-bench's Docker images do); copy-on-write clones; keep the warm page cache across tool calls (it is lost if the sandbox is recycled). |
| 8 | **Parallelism inside the sandbox is incidental and often wasted.** | Test runs: 8.6% of CPU in scheduling, almost all OpenMP spin-waiting (`sched_yield`, libgomp) in scikit-learn tests on 4 vCPUs; kernel scheduler/futex only 0.3%; most tool calls keep ~1 vCPU busy. | Services are tuned for their core count; thread pools are sized deliberately *(structural)*. | **Same mechanism, new cause.** Libraries assume they own the machine; in a small sandbox that is spin-wait. | Pin `OMP_NUM_THREADS`/`-j` to the sandbox's vCPUs; the hypothesis that context switching is a major tax (H2) was *not* supported. |
| 9 | **Variance comes from the environment's state, not from load.** | Task-clock CV across identical replays: median 8%, p90 19%; one Django clone replay spent 26% of CPU in ext4's recently-deleted-inode scan after a mass delete (D10); steal < 0.5%. A cold page cache (as after sandbox recycling) adds 0.1–0.2 s wall and 6–32% CPU per test command via ~170–210 major faults (`results/coldcache/summary.md`). | Service tail latency is dominated by load, queuing and interference *(literature)*. | **Different.** Filesystem history (what the previous task deleted) changes the next task's cost. | Fresh filesystem per sandbox (overlay/snapshot) rather than reuse; measure with state reset. |
| 10 | **Instrumentation is cheap relative to the loop.** | git snapshot after every action: 0.5% of episode wall-clock; the wrapper's ~6 extra process starts per command are ~1 ms. | Tracing/sampling overhead in services is budgeted at ~1% *(literature)*. | **Same.** | Per-action checkpointing (full working-tree commits) is affordable; it enables replay-based profiling and rollback. |
| 11 | **Resolution does not correlate with resource use; the agent's command style sets the CPU mix.** | 7/8 tasks resolved; the unresolved task used the *least* tool time (4.8 s). Episode CPU is driven by which tests the agent chooses to run (one 67 s `pytest sklearn/metrics` = 23% of all episode tool time). Across agents on the same 8 tasks (`results/summary/mini_vs_own.md`, pooled): a public bash-only agent that reads with `sed -n`, edits with `sed -i`, verifies with throw-away scripts and rarely runs the suite spends 38.5% of CPU in imports, 11.7% in process lifecycle and 10.6% in core logic; this study's episodes spend 22% / 5% / 35% (2nd model: 20% / 6% / 47%). | Service cost scales with request volume; quality and cost are decoupled by design *(structural)*. | **Different.** Cost is a *decision* of the agent (test scope), not a function of input size. | Agent-side policies (run the narrow test first; cap suite size) are a bigger lever than any kernel or hardware change. |

## 2. SWOT-style summary (from the datacenter operator's view)

| | |
|---|---|
| **Strengths** (measured) | Embarrassingly parallel across sandboxes; small memory footprint (median maxRSS 3–80 MB per command, 0.7–0.9 GiB per sandbox incl. OS); no state shared between sandboxes; steal < 0.5% at this density. |
| **Weaknesses** (measured) | ~11% CPU utilization; ~60% of wall-clock waiting on the model; every tool call re-pays process start-up (0.7–1 ms per exec here, ~8 ms per Python start), imports (median 39% of command wall time), and environment construction; VM-exit cost of CPUID makes short commands ~7× more expensive than their kernel floor. |
| **Opportunities** (derived from the measurements; not yet tested) | Oversubscription of sandboxes per host (density experiment, §3); glibc/libc fix for cache probing in guests; warm-interpreter snapshot/fork-server for Python tool calls; prebuilt environment snapshots; sizing OpenMP/`-j` to the sandbox; agent policies that bound test scope. Accelerator offload (compression/hashing/memcpy) buys little outside git-heavy phases. |
| **Threats** (measured or structural) | Each tool call is on the critical path of a ~4 s think–act loop, so sandbox latency variance is directly visible to the user; filesystem-state effects (ext4 inode scans after mass deletes) cause 10–30% swings; density beyond the vCPU count will degrade tool-call latency (quantified in §3); results are specific to one hypervisor and to Python repositories. |

## 3. Density (extension step 2)

`tools/density.py`: N identical copies of a representative tool command
started simultaneously on this 4-vCPU VM (1 thread per core, no SMT), N =
1…32, 3 repetitions each; per-instance wall time, makespan, `/proc/stat`
busy and steal. Full table: `results/density/summary.md`; figure:
`figs/density.png`.

| Workload (N=1 wall) | slowdown at N=4 | N=8 | N=16 | N=32 (ideal 8×) | aggregate throughput at saturation (ideal 4×) |
|---|---|---|---|---|---|
| django `runtests.py migrations.test_optimizer` (0.24 s) | 1.05× | 2.07× | 4.65× | 9.6× | 3.1–3.4× |
| flask `pytest tests` (1.6 s) | 0.97× | 1.96× | 4.09× | 8.4× | 3.7–3.9× |
| sympy `pytest sympy/physics/units` (1.05 s) | 1.01× | 1.91× | 4.19× | 9.0× | 3.5–3.8× |
| `spawnbench 300 /bin/true` (0.27 s; exec-bound) | 0.89× | 1.64× | 3.70× | 7.6× | 4.0–4.3× |

- **Tool-call latency is unaffected until the number of *simultaneously
  executing* tool calls exceeds the vCPU count**, then degrades linearly
  (≈ N/4). Steal stayed at 0–0.9% throughout, so the host did not take
  CPU away from this VM even at 100% busy.
- Python test runs saturate at 3.1–3.9× aggregate throughput instead of
  4× (5–20% loss at N=32); the exec-bound workload reaches the ideal 4×, so
  the CPUID VM exits do **not** serialize across vCPUs. The Python loss is
  consistent with shared-cache/memory contention between interpreters, but
  this VM has no counters to confirm that.
- Combined with the time view (sandboxes ~11% busy on average, ~28% during
  tool calls), the measurement says tool calls from several sandboxes can
  share a core without visible latency cost as long as their *bursts* do not
  coincide; the knee is at (concurrently running tool calls) = (cores), not at
  (sandboxes) = (cores). This is the empirical basis for row 1's
  "oversubscribe" opportunity; it does not measure memory or page-cache
  pressure from many *resident* sandboxes.

## 4. What stays the same

- **The CPU-view mix is a property of the toolchain, not of the model.**
  Replaying the second model's 16 episode commands gives core 55.4%,
  allocation 17.9%, imports 13.8%, process lifecycle 4.9% vs 56.1 / 14.3 /
  10.6 / 2.6% for the original 55 commands (`results/summary/extension_cpu_view.md`);
  the only large difference (scheduling 0.3% vs 8.5%) is the original
  study's OpenMP-heavy scikit-learn task. What the model changes is the
  *time view* (row 1) and the command mix (row 11), not what a given
  command costs.
- Allocation/GC as a top tax category (row 5).
- Kernel page-fault and memory-zeroing costs scale with process creation,
  as in any fork-heavy workload.
- Timer/instruction profilers disagree on memory-bound and trap-bound code
  (GC, CPUID) in the same direction as in service profiling: time-based
  attribution is required for both.
- The datacenter-tax framing itself transfers: orchestration (everything
  that is not the program's own work) is 25–45% of on-CPU time in
  episode commands here (100 − core logic share, by class), the same order as
  the classic tax; what fills it differs (process lifecycle + interpreter
  start-up instead of RPC + serialization).
