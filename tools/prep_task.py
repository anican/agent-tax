"""prep_task.py — write a task's issue text and (hidden) eval metadata to $WORK/<task>/.
usage: $ANA_PY tools/prep_task.py <instance_id>...
ISSUE.md is what the agent sees (the prompt). meta.json holds base commit etc.
eval/ holds test_patch + FAIL_TO_PASS/PASS_TO_PASS; the agent does not read it
while solving (used only for post-hoc resolution checks)."""
import json, os, sys, pandas as pd
d = pd.read_parquet('/home/user/agent-tax/data/verified.parquet').set_index('instance_id')
for iid in sys.argv[1:]:
    r = d.loc[iid]; base = f"/home/user/work/{iid}"
    os.makedirs(f"{base}/eval", exist_ok=True)
    open(f"{base}/ISSUE.md", "w").write(r.problem_statement)
    json.dump({"instance_id": iid, "repo": r.repo, "base_commit": r.base_commit, "version": r.version,
               "difficulty": r.difficulty, "environment_setup_commit": r.environment_setup_commit},
              open(f"{base}/meta.json", "w"), indent=1)
    open(f"{base}/eval/test.patch", "w").write(r.test_patch)
    json.dump({"FAIL_TO_PASS": json.loads(r.FAIL_TO_PASS), "PASS_TO_PASS": json.loads(r.PASS_TO_PASS)},
              open(f"{base}/eval/tests.json", "w"))
    print(iid, r.repo, r.base_commit[:10], r.version, r.difficulty)
