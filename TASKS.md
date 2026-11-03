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

| Instance ID | Setup wall time | Setup issues | Episode wall time | Commands | Resolved (FAIL_TO_PASS) |
|---|---|---|---|---|---|
