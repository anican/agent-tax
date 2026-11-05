# TASKS.md — SWE-bench Verified tasks used

Selection criteria (see DECISIONS.md D3, D5): repo versions that run on
Python 3.11; at least 4 repos; a mix of `<15 min fix` (easy) and
`15 min - 1 hour` (medium) difficulty; one repo with compiled extensions
(scikit-learn). Selection was made from the issue *titles* only.

Work order is breadth-first: wave 1 (tasks 1–3) gets Phase A + Phase B
before wave 2 starts.

| # | Wave | Instance ID | Repo | Version | Difficulty | Notes |
|---|---|---|---|---|---|---|
| 1 | 1 | django__django-16595 | django/django | 5.0 | <15 min fix | Migration optimizer / AlterField |
| 2 | 1 | sympy__sympy-24066 | sympy/sympy | 1.12 | 15 min - 1 hour | units dimension detection |
| 3 | 1 | pallets__flask-5014 | pallets/flask | 2.3 | <15 min fix | Blueprint empty name |
| 4 | 2 | scikit-learn__scikit-learn-26194 | scikit-learn/scikit-learn | 1.3 | 15 min - 1 hour | compiled extensions (Cython/C) |
| 5 | 2 | psf__requests-5414 | psf/requests | 2.26 | <15 min fix | |
| 6 | 2 | pytest-dev__pytest-10081 | pytest-dev/pytest | 7.2 | <15 min fix | |
| 7 | 2 | django__django-16667 | django/django | 5.0 | 15 min - 1 hour | |
| 8 | 2 | sympy__sympy-24562 | sympy/sympy | 1.12 | <15 min fix | only if time allows |

Outcome columns (setup time, setup failures, episode length, resolved) are
in the "Results" table below, filled in as each task finishes.

## Results

All 8 tasks installed within the 20-minute limit; none were skipped. Setup
time is the sum of the logged setup commands (clone, venv, installs/builds).
Episode wall time runs from the issue being shown to the agent until the
agent declared it done (cap: 45 min; no episode came close). "Resolved"
applies the hidden SWE-bench `test_patch` after the episode and runs the
`FAIL_TO_PASS` tests only (PASS_TO_PASS not checked).

| Instance ID | Setup wall time | Setup issues | Episode wall time | Agent actions | Resolved (FAIL_TO_PASS) |
|---|---|---|---|---|---|
| django__django-16595 | 58 s | none | 88 s | 6 cmds + 2 edits | resolved (1 FAIL_TO_PASS test(s)) |
| sympy__sympy-24066 | 15 s | none | 64 s | 8 cmds + 2 edits | resolved (1 FAIL_TO_PASS test(s)) |
| pallets__flask-5014 | 15 s | `werkzeug==2.3.7` pinned at setup; pytest 9 broke the test suite (`monkeypatch.notset`), agent pinned `pytest<8` mid-episode; 11 pre-existing test failures (deprecation warnings from newer deps) | 78 s | 7 cmds + 2 edits | resolved (1 FAIL_TO_PASS test(s)) |
| scikit-learn__scikit-learn-26194 | 677 s | pinned `numpy<2 scipy<1.12 cython<3 setuptools<70`; explicit `setup.py build_ext -i -j4` (154 s) then `pip install --no-build-isolation -e .`, which rebuilt all extensions again in a temp dir (488 s) | 146 s | 9 cmds + 3 edits | resolved (2 FAIL_TO_PASS test(s)) |
| psf__requests-5414 | 18 s | 12 pre-existing failures in tests/test_requests.py with current urllib3/deps (same with and without the fix) | 120 s | 8 cmds + 2 edits | resolved (1 FAIL_TO_PASS test(s)) |
| pytest-dev__pytest-10081 | 35 s | `SETUPTOOLS_SCM_PRETEND_VERSION` needed (shallow clone has no tags) | 53 s | 6 cmds + 2 edits | resolved (1 FAIL_TO_PASS test(s)) |
| django__django-16667 | 36 s | none | 59 s | 6 cmds + 3 edits | unresolved (2 FAIL_TO_PASS test(s)) |
| sympy__sympy-24562 | 15 s | none | 106 s | 5 cmds + 2 edits | resolved (1 FAIL_TO_PASS test(s)) |

django__django-16667 is unresolved: the hidden test expects
`SelectDateWidget.value_from_datadict` to return the pseudo-ISO date `0-0-0`
on overflow; the agent's fix catches `OverflowError` but returns the raw
values (`9223372036854775808-12-1`). The form still reports "Enter a valid
date." instead of crashing, which is what the agent checked.

## Extension (2026-11-05): fresh tasks solved with a different model (DECISIONS.md D18)

Selected the same way as the original 8 (titles only, Python-3.11-capable
repo versions), from tasks the agent had not seen in the original study.

| # | Instance ID | Repo | Version | Difficulty |
|---|---|---|---|---|
| E1 | django__django-16569 | django/django | 5.0 | <15 min fix |
| E2 | sympy__sympy-24539 | sympy/sympy | 1.12 | <15 min fix |
| E3 | pytest-dev__pytest-10051 | pytest-dev/pytest | 7.2 | 15 min - 1 hour |

### Extension results

| Instance ID | Setup wall time | Setup issues | Episode wall time | Agent actions | Resolved (FAIL_TO_PASS) |
|---|---|---|---|---|---|
