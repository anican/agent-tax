"""importtime.py — run selected recorded commands with PYTHONPROFILEIMPORTTIME=1
(same as `python -X importtime`, but inherited by every python child process)
and report, per command, the summed top-level cumulative import time versus the
command's wall time and task-clock CPU time.

usage: $ANA_PY tools/importtime.py <task>:<seq> [...]
Output: results/importtime/<task>_<seq>.json and results/importtime/summary.csv
Note: import time here is wall time inside the import system as measured by
CPython (includes I/O waits and module-level code execution of imported modules).
"""
import json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import classify, load_calls
from replay import Env, restore, swap_venv, sq, AT, WORK, PERF

def main():
    os.makedirs(f"{AT}/results/importtime", exist_ok=True)
    rows = []
    for spec in sys.argv[1:]:
        task, seq = spec.split(":"); seq = int(seq)
        calls = load_calls(f"{AT}/logs/{task}/calls.jsonl")
        c = [x for x in calls if x["kind"] == "cmd" and x["seq"] == seq][0]
        swap_venv(f"{WORK}/{task}/venv"); E = Env(task, calls); cls = classify(c["cmd"])
        res = []
        for rep in range(3):
            cwd, env = E.prepare(c, cls)
            env["PYTHONPROFILEIMPORTTIME"] = "1"
            t0 = time.time()
            # the recorded command may pipe stderr into tail/grep, which would swallow the
            # importtime report: run its python part with stderr sent to a file instead
            core = c["cmd"]
            while re.search(r"\|[^|]*$", core) and not core.rstrip().endswith("EOF"):
                core = re.sub(r"\s*(2>&1\s*)?\|[^|]*$", "", core)
            errf = f"{AT}/results/importtime/.stderr"; statf = f"{AT}/results/importtime/.stat"
            subprocess.run(f"{PERF} stat -x, -o {statf} -e task-clock -- bash -c {sq(core)} >/dev/null 2>{errf}", shell=True,
                           cwd=cwd, env=env)
            wall = time.time() - t0
            txt = open(errf, errors="replace").read() + open(statf).read()
            top = [int(m.group(2)) for m in re.finditer(r"import time:\s+(\d+) \|\s+(\d+) \| (\S.*)", txt)]
            tc = re.search(r"([\d.]+),msec,task-clock", txt)
            res.append({"wall_s": wall, "task_clock_s": float(tc.group(1)) / 1000 if tc else None,
                        "top_level_import_s": sum(top) / 1e6, "n_top_level": len(top)})
        restore(task, [x for x in calls if x["kind"] == "snap" and x["reason"] == "episode_end"][-1]["snap"])
        r = {"task": task, "seq": seq, "cls": cls, "cmd": c["cmd"][:120], "profiled_cmd": core, "reps": res}
        json.dump(r, open(f"{AT}/results/importtime/{task}_{seq}.json", "w"), indent=1)
        m = lambda k: sum(x[k] or 0 for x in res) / len(res)
        rows.append(f"{task},{seq},{cls},{m('wall_s'):.3f},{m('task_clock_s'):.3f},{m('top_level_import_s'):.3f},{m('top_level_import_s')/m('wall_s')*100:.1f}")
        print(rows[-1], flush=True)
    with open(f"{AT}/results/importtime/summary.csv", "a") as f:
        for r in rows: f.write(r + "\n")

if __name__ == "__main__":
    main()
