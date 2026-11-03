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

