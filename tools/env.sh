# Source this file: shared paths for the agent-tax study.
export AT_ROOT=/home/user/agent-tax          # this repo (logs, results, report)
export WORK=/home/user/work                  # task clones + venvs (outside the repo)
export PERF=/usr/lib/linux-tools/6.8.0-147-generic/perf   # /usr/bin/perf wrapper is broken on this kernel
export TASK_PY=/usr/bin/python3.11           # frame-pointer build, used for task venvs
export ANA_PY=/home/user/anavenv/bin/python  # analysis-only interpreter (pandas, matplotlib)
export GIT_AUTHOR_NAME=snap GIT_AUTHOR_EMAIL=snap@localhost
export GIT_COMMITTER_NAME=snap GIT_COMMITTER_EMAIL=snap@localhost
