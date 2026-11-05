# DECISIONS.md

A running log of choices made during this unattended measurement study.
Entries are added in order; earlier entries are not edited except to append
corrections (marked **[correction]**).

## D0. Agent identity (affects every timing in the TIME VIEW)

- The "coding agent" whose episodes are measured is Claude Code running in a
  claude.ai cloud session (Claude Code container version 2.1.317), in **auto**
  permission mode.
- **Effort level: `high`**, as reported by the session's own metadata
  (`get_session` → `session_context.effort_level`) at the start of the study.
- **Model:** the exact model identifier is *not* written into this repository:
  the session's operating instructions forbid putting model identifiers in any
  artifact pushed to a repository. It was reported in the chat reply that
  accompanies this work instead. What matters for the measurements is
  recorded here: the session's configured model and the model that actually
  served the latest turn were the **same** at the start of the study (no
  fallback), and this is re-checked at the end (see the last entry).
- Consequence: the "model/loop time" measured in Phase A is specific to this
  model, this effort level, this harness version and the auto-mode
  permission checks. A different model, effort level or harness would give
  different gaps.

## D1. Time-view approximation

- Every shell command of an episode goes through `tools/run.sh`, which logs
  nanosecond start/end timestamps (`date +%s%N`) around the command.
- **Gaps between consecutive tool calls approximate model + agent-loop time.**
  A gap includes: model inference (prefill + decode, including thinking),
  network round trips to the API, harness work (Claude Code's tool dispatch,
  auto-mode permission classification of Bash commands), the start-up of the
  `run.sh` wrapper itself (a bash process + one `date` fork, a few ms), and
  any non-shell tool calls (the `Edit`/`Write` tools used to edit files, which
  are not shell commands).
- Snapshot time (`tools/snap.sh`) is logged separately (`kind: "snap"`) and
  reported as its own *instrumentation* bucket, so it does not inflate either
  the tool-execution or the model/loop buckets.
- **The logging perturbs behavior slightly**: each command pays for a
  wrapper bash process, `date` forks, a `tee` of its output and a git snapshot
  afterwards (snapshot = `git add -A` into a private index + `write-tree` +
  `commit-tree`). Snapshots never touch the task repo's HEAD, branch or real
  index, so `git status`/`git diff` inside the episode behave as they would
  without instrumentation. The extra Bash calls for edit snapshots add a
  little loop time that a non-instrumented agent would not pay.

## D2. How the agent works in Phase A

- File *exploration* is done with shell commands (`grep`, `sed -n`, `cat`,
  `find`, `ls`) through `run.sh`, not with Claude Code's built-in Read/Grep
  tools, so that it is captured, replayable and profiled. This is a
  deliberate deviation from how Claude Code usually explores (it normally
  favors its built-in Read/Grep tools); it makes the "search/read" class
  visible in the CPU view.
- File *edits* use Claude Code's `Edit` tool (realistic), followed by
  `tools/snap.sh <task> edit` so the post-edit state is checkpointed.
- The agent does not look at the gold patch or the hidden tests
  (`patch`, `test_patch`, `FAIL_TO_PASS`) while solving. Resolution is judged
  afterwards by applying `test_patch` and running `FAIL_TO_PASS` tests.
- Environment setup (venv creation, `pip install`) is also routed through
  `run.sh` but tagged `phase=setup`; it is excluded from the episode
  time-view (SWE-bench normally provides a pre-built environment) but its
  commands are replayed and profiled as the *package install* / *build*
  classes.

## D3. Python version

- All task venvs use `/usr/bin/python3.11` (Ubuntu build, compiled with
  `-fno-omit-frame-pointer -mno-omit-leaf-frame-pointer`), so that
  `perf record -g` frame-pointer unwinding works through the interpreter.
  The uv-managed python-build-standalone interpreters and the system
  `python3.12` are not frame-pointer builds. Tasks were chosen from repo
  versions that support Python 3.11. SWE-bench's own harness uses other
  Python versions for some of these repos (often 3.9); this is a deviation.

## D4. Pushing is blocked

- `git push -u origin claude/environment-diagnostics-8tfnrb` fails with HTTP 403
  ("Claude doesn't have GitHub access to anican/agent-tax"); creating the
  branch through the GitHub API also fails (403 "Resource not accessible by
  integration"). Read access works. The study continues with **local commits
  after every major step**; every later step retries the push. If the
  session container is reclaimed before access is fixed, unpushed results
  are lost.

## D3 [correction]. Interpreters for recording vs. replay

- Phase A (live episodes) uses the task venvs as created, i.e. the deadsnakes
  `/usr/bin/python3.11` (3.11.18). That binary has frame pointers but is
  **stripped**: in a test profile, 58% of interpreter samples resolved to
  `[unknown]` (all static functions: pymalloc, GC, parser, ...). No debug
  symbols are published for it (Ubuntu debuginfod and the PPA return 404).
- Building CPython from the python.org tarball was refused by the session's
  permission classifier ("code from external"), so it was not done.
- Instead, Phase B swaps each task venv's interpreter (the `bin/python*`
  symlinks and `pyvenv.cfg`) to the uv-managed **python-build-standalone
  CPython 3.11.15**, which is **not stripped**, is built with
  `-fno-omit-frame-pointer -mno-omit-leaf-frame-pointer`, and is PGO+LTO
  (clang). Same minor version → same extension ABI, so the installed
  packages keep working. (The earlier statement in D3 that the uv-managed
  interpreters lack frame pointers was wrong.)
- Consequences: the CPU view profiles a different 3.11 build (clang PGO+LTO
  instead of gcc PGO+LTO, 3.11.15 instead of 3.11.18) than the one used
  live. Category shares, not absolute times, are reported. The replay
  interpreter's stdlib was byte-compiled once (`compileall`) before replays
  so the first replay does not pay stdlib compilation the live run never paid.

## D5. Task selection

- 8 tasks from SWE-bench Verified across 6 repos (django, sympy, flask,
  requests, pytest, scikit-learn), picked from repo versions that run on
  Python 3.11, mixing `<15 min fix` and `15 min - 1 hour`. See TASKS.md.
  Selection used only titles/difficulty, not the gold patches.
- Environment setup follows each repo's usual dev install (`pip install -e .`
  + test requirements), with minimal pins where the base commit predates
  current dependency releases (e.g. `werkzeug==2.3.7` for flask 2.3, which
  is what SWE-bench pins too). Any further pins discovered during an episode
  are made by the agent inside the episode (e.g. flask: `pip install "pytest<8"`).

## D6. Replay protocol (Phase B)

- Every recorded command (setup and solve phases) is replayed: 1 unprofiled
  warm-up, then 3 repetitions, each consisting of a `perf stat` +
  `/usr/bin/time -v` run and a separate `perf record -a -g` run (so the
  two tools never perturb each other). Before every run the working tree
  is restored to the command's pre-command checkpoint. 10-minute cap per run.
- Restores rewrite **only files that differ** from the checkpoint, so
  unchanged files keep their mtimes and `__pycache__` stays valid (rewriting
  every file would force a full bytecode recompile on every replay, which the
  live run never did). Ignored files (`__pycache__`, `.pytest_cache`, build
  outputs) are not restored. As a result replays run with *warm* page cache
  and bytecode caches; the live run's first test command paid bytecode
  compilation that replays don't.
- Setup commands that create things in the task directory (clone, venv
  creation) are replayed in an empty scratch directory. Package-install
  commands run against a **fresh scratch venv** each time: empty for setup
  installs, and re-populated with the episode-start package set (unprofiled)
  for installs made during an episode, so `pip install` does real work
  instead of reporting "already satisfied". The pip download cache is warm
  during replays, unlike the first live install, so network/download time is
  under-represented.
- System-wide sampling (`-a`) is used. Samples are attributed to the
  replayed command's process tree (descendants of the launcher pid, tracked
  through fork events); kernel threads (kworker, ksoftirqd, jbd2, ...) are
  kept as a separate group, and samples from idle and from unrelated
  processes (the agent harness, perf itself) are discarded.
- perf.data files are kept zstd-compressed (`perf record -z`) so profiles can
  be re-parsed if the taxonomy or parser changes.

## D7. Parser bug found and fixed before any reported data

- The first replay attempt mis-parsed `perf script` output (perf pads short
  `comm` names with leading spaces; the parser took those header lines for
  stack lines), so almost no samples were attributed to the replayed
  command. It was caught on a sanity check (17 samples for a ~1 s test run),
  all results were deleted, and the replays were restarted with the fixed
  parser. From then on perf.data is kept so this cannot silently recur.

## D8. Looped profiles for very short read-only commands

- A ~10 ms `grep`/`sed`/`git diff` yields ~10 samples per replay at 999 Hz.
  For solve-phase search/read and git commands that took < 1 s live and do
  not modify state, 3 extra profiles of 30 back-to-back executions
  (`for i in $(seq 30); do bash -c '<cmd>'; done`) are recorded
  (`tools/replay_loop.py`). In the analysis every sample of such a command
  is weighted by 1/31 (its 1 normal replay + 30 looped executions), so the
  command still counts as **one execution** in time-weighted aggregates but
  its category shares have much lower variance. Raw sample counts are
  reported alongside.

## D9. Taxonomy choices (details in TAXONOMY.md)

- Attribution is **leaf-first**: the sampled leaf function decides the
  category when it is unambiguous (memcpy → memory movement, malloc →
  allocation, ...). Stack context is used only for generic leaves: an
  interpreter leaf under an import frame → interpreter startup/imports; a
  kernel leaf under an execve/clone/exit syscall or a page fault →
  process lifecycle; under stat/open/getdents → filesystem metadata; under
  futex → scheduling.
- Consequently, `clear_page_erms` reached from a page fault counts as
  *memory movement* (it is a memset of a fresh page) and page-allocator
  leaves as *allocation*; the page-fault total regardless of leaf is
  reported separately as an *inclusive* metric, and H4 is judged on both.
- CPython's cyclic GC is counted under *allocation* (memory management).
- CPython source compilation and `.pyc` unmarshalling count as
  *interpreter startup/imports* when they happen under an import, and as
  *serialization/parsing* otherwise.
- Interpreter teardown (`Py_FinalizeEx` on the stack) counts as *process
  lifecycle* (process exit).
- *Core logic* is split into python (interpreter + extension modules
  executing the program), compiler, and CLI tool (git/grep/sed's own code
  and the libc string/regex routines they call). pip's resolver is Python
  code and so counts as core/python inside the package-install class.
- Two buckets were added beyond the requested list: **other user-space**
  (identified code outside the taxonomy: the bash wrapper, the vDSO, misc
  libc) and **other kernel** was split by syscall in an appendix table.
  **unclassified** holds samples whose leaf symbol did not resolve.

## D10. Replay-fidelity fixes found during wave-1 sanity checks (before any reporting)

- **ext4 inode-allocation artifact.** The first wave-1 replays deleted the
  previous scratch clone/venv right before the next run created thousands of
  files. ext4's inode allocator then repeatedly ran `recently_deleted()` /
  `lookup_bh_lru()` / `__brelse()` (skipping inodes freed in the last few
  dirty-expire intervals): ~6.5% of all samples, concentrated in clone, venv
  and pip-install replays — an artifact of the replay harness, not of agent
  behaviour. Fix: each execution gets a fresh scratch dir; all scratch is
  deleted only at the end of a task, followed by `sync` and a 70 s pause
  (`dirty_expire_centisecs` = 3000). The affected commands (all setup
  commands, and flask seq 6–8) were deleted and re-replayed.
- **Venv state is not checkpointed by snap.sh.** In flask the agent ran
  `pip install "pytest<8"` mid-episode; commands before it were first
  replayed against the post-install venv (exit code 1 instead of 0 for seq 7,
  because the pytest-8 error they were looking at no longer occurred). Fix:
  solve-phase commands that precede the episode's first package install are
  replayed in a venv rebuilt with the episode-start package set
  (`freeze_start.txt` for wave-2 tasks; reconstructed from the setup log's
  "Successfully installed" line for wave-1 tasks). Exact only when an
  episode installs packages at most once (true for every recorded episode
  so far; see TASKS.md).
- **Stripped interpreter in recorded setup commands.** `/usr/bin/python3.11
  -m venv venv` is replayed with the replay interpreter's path substituted
  (otherwise ~8% of all samples were `[unknown]` in the stripped binary).
- Unresolved leaves inside single-purpose stripped libraries/binaries are
  attributed by DSO (libz → compression, libcrypto → hashing/crypto, bash →
  shell glue, git/grep/sed → CLI tool core). Unresolved leaves in
  multi-purpose DSOs (libc, interpreters) stay UNCLASSIFIED.

## D11. Cross-check fixes

- `-X importtime` sampling (`tools/importtime.py`): the first pass under-
  reported imports for pytest commands because pytest's fd-level capture
  swallows the importtime report written to stderr during collection. The
  sampling runs now set `PYTEST_ADDOPTS=--capture=no`; the first-pass numbers
  are kept in `results/importtime/_capture_bug/` for transparency and are not
  used.
- callgrind comparison: the first summary mis-parsed `callgrind_annotate`
  headers ("Profiled target:", not "Cmd:") and recursion suffixes (`'2`),
  putting all python code under "other user-space". Fixed before reporting;
  raw callgrind outputs were reused.

## D12. Cleanup policy

- After a task's Phase B (replays, loops, cross-checks), its venv, the
  replay start-venv and ignored build artifacts are deleted to save disk;
  the clone (with its `refs/snaps/*` checkpoints) and compressed perf.data
  files are kept.

## D13. Optional step B5: public trajectories

- `SWE-bench/experiments` (sparse clone) does not contain trajectories
  itself; its `metadata.yaml` files point to the public S3 bucket
  `swe-bench-submissions`, which is reachable. Most agents' trajectories use
  custom tool calls (editor tools, SWE-agent commands) that are not directly
  replayable as shell commands. The **bash-only mini-swe-agent** entries
  (`bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514`) consist only of
  shell commands, one `bash -c` per step, so they are replayable.
- Trajectories for 5 of our task IDs were downloaded to `/home/user/ext/`
  (outside the repo) and their commands extracted as data
  (`tools/extract_traj_cmds.py`). Two were chosen for replay because their
  venvs still existed: `psf__requests-5414` (39 commands) and
  `pytest-dev__pytest-10081` (24 commands). All commands were read before
  execution: file reads, `sed -i` edits, small Python test scripts (the
  requests ones only use deliberately invalid hosts, so no real network
  I/O), pytest runs, `git diff/add`. Nothing destructive outside the repo.
- Method: the commands are executed once, in order, from the base commit,
  through `run.sh` under a pseudo-task `mini__<task>` (shared repo/venv,
  checkpoints under `refs/mini/*`), which yields per-command checkpoints;
  then the same `replay.py`/`replay_loop.py` pipeline profiles them. The
  pseudo-tasks are excluded from the time view (their timestamps are from
  our re-execution, not from the original agent) and from the main CPU-view
  aggregates; they appear only in a separate comparison table.

## D14. Batch interruption and resume

- The wave-2 replay batch ran into the session's 2-hour limit for a single
  background command and was killed during scikit-learn seq 5 (the 8-minute
  editable install), after reps 1–2 and the rep-3 `perf stat` run had
  completed. `replay.py` was given rep-level resume (reuse finished
  stat/record runs; exit code and wall time recovered from `time -v`), the
  partial rep-3 recording was deleted, and the task was resumed after the
  70 s ext4 quiet period. No completed measurement was discarded or repeated.

## D15. libgomp attribution (found while checking the unclassified bucket)

- After all replays, 5% of test-run samples were `[unknown]` inside
  `libgomp.so.1` (scikit-learn tests using OpenMP), plus 1.8% in
  `__sched_yield`. libgomp's exported entry points resolve; its internal
  functions (barrier waits, spin loops, team management) do not. Since the
  parallel work itself executes in the calling extension's code (e.g. the
  Cython `_middle_term_computer` kernels, which resolve and count as core
  logic), unresolved time *inside* libgomp is thread orchestration
  (spin-waiting at barriers, handing out work). Rule U0f maps it to
  *scheduling/context switch*. This is a DSO-level attribution, consistent
  with D10; it is reported explicitly in the H2 verdict.
- The one scikit-learn `perf stat`/`time` repetition that the batch
  interruption had left empty (seq 5, rep 3; D14) was re-measured; the
  resume check now requires non-empty output files.

## D16. CPUID / VM-exit attribution (post-hoc, evidence-based taxonomy change)

- While checking the top leaf functions, ~25% of all samples of short
  commands (search/read, git; looped profiles) were in glibc's CPU-feature and
  cache-size detection inside ld.so (`intel_check_word`, `handle_intel`,
  `get_common_cache_info`, `update_active`, `init_cpu_features`, ...). That
  code executes CPUID many times per process start.
- Measured directly (`tools/microbench/cpuid_cost.c`, results in
  `results/microbench/`): one CPUID costs **~11 µs** in this guest (leaves 0,
  2 and 4 alike; 3 runs), vs ~1.6 ns for a dependent add, i.e. every CPUID is
  a VM exit. A loop of 2000 `/bin/true` starts costs 1.9 ms of CPU per start,
  and ~67% of those samples are in these functions (≈115 CPUIDs per start at
  11 µs). The callgrind cross-check confirms it from the other side: for
  `grep | sed` these functions are 0.4% of executed instructions but 57% of
  user-space on-CPU time.
- Rule U6v therefore attributes these functions to **virtualization-
  related** ("CPUID VM exits in glibc CPU-feature detection") rather than to
  dynamic linking. Because this changes a category that H4 depends on after
  data collection, the report gives the H4 verdict under both mappings
  (`tools/hypotheses.py`); the verdict does not change.

## D17. Classifier precedence change (post-hoc, one command affected)

- Compound commands that run an ad-hoc Python snippet *and* a git or read
  command (`python -c "..."; git diff --stat`) were first classed as *git*.
  Their CPU time is the Python part, so an ad-hoc `python` invocation now
  takes precedence over git/search-read (class *other*). Only
  scikit-learn seq 14 changed class. The analysis re-derives classes from the
  command text, so the stored replay metadata keeps the old label.

## D0 (end-of-study check)

- At the end of the study (after all measurements) the session metadata
  again reported effort level `high` and the same model for both the
  configured and the last-served model, i.e. no model switch or fallback
  was recorded during the study.

## D18. Extension run (2026-11-05): model switch and scope

- The original study (D0) ran entirely on one model. For this extension the
  session's model was switched by the user to a different one (reported in
  chat, not written here, per the session's rules); effort level is still
  `high` and the permission mode is still `auto`. Any new live episodes
  therefore measure a **different model's** model/loop time and are kept
  separate from the original 8 (task IDs listed in TASKS.md under
  "Extension"); CPU-view replays are model-independent and are pooled only
  where the report says so.
- Time budget: ~3 hours. Plan, in order: (1) process-start cost
  decomposition and the `GLIBC_TUNABLES` mitigation test; (2) a density
  experiment (concurrent replays of representative test commands);
  (3) 2–3 fresh live episodes with the new model + replays. Results are
  committed and pushed after each step.

## D19. Extension episodes: instrumentation note

- In E1 (django__django-16569) the agent's first edit attempt was rejected
  by its Edit tool (file not yet read), but the follow-up checkpoint
  (`snap 6`, reason `edit`) was still taken, so E1's log contains one
  edit checkpoint with no change (identical tree to snap 5). It is left in
  the log; the time view counts it as one extra agent action (it is a real
  tool call the agent made) and the CPU view is unaffected (replays
  restore by tree, and no command sits between snaps 5 and 6).
- Extension episodes were run with the same instrumentation and tool
  discipline as the original 8 (D1–D2), by the switched model (D18).

