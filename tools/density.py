"""density.py — sandbox density experiment: run N identical copies of a
representative agent tool command concurrently on this 4-vCPU VM and measure
per-instance slowdown, makespan, aggregate throughput and CPU busy/steal.

Models N agent sandboxes whose tool calls happen to overlap on one host.
usage: $ANA_PY tools/density.py [--levels 1,2,4,...] [--reps 3]
Output: results/density/density.csv, summary.md, figs/density.png
"""
import argparse, csv, os, subprocess, sys, time
import numpy as np
AT = "/home/user/agent-tax"; W = "/home/user/work"
WORKLOADS = {
    "django_test_optimizer": dict(cwd=f"{W}/django__django-16595/repo/tests", venv=f"{W}/django__django-16595/venv",
                                  cmd="python runtests.py migrations.test_optimizer --parallel 1"),
    "flask_pytest_all": dict(cwd=f"{W}/pallets__flask-5014/repo", venv=f"{W}/pallets__flask-5014/venv",
                             cmd="python -m pytest -q -p no:cacheprovider tests"),
    "sympy_pytest_units": dict(cwd=f"{W}/sympy__sympy-24066/repo", venv=f"{W}/sympy__sympy-24066/venv",
                               cmd="python -m pytest -q -p no:cacheprovider sympy/physics/units"),
    "spawn_300_true": dict(cwd=f"{AT}/tools/microbench", venv=None, cmd="./spawnbench 300 /bin/true"),
}

def stat():
    f = open("/proc/stat").readline().split()
    v = list(map(int, f[1:9])); return sum(v), v[3] + v[4], v[7]   # total, idle(+iowait), steal

def run_batch(wl, n):
    env = dict(os.environ)
    if wl["venv"]:
        env["VIRTUAL_ENV"] = wl["venv"]; env["PATH"] = f"{wl['venv']}/bin:" + env["PATH"]
    t_all, i_all, s_all = stat(); t0 = time.perf_counter()
    procs = [subprocess.Popen(["bash", "-c", wl["cmd"]], cwd=wl["cwd"], env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for _ in range(n)]
    walls, rcs = [], []
    pending = {p.pid: p for p in procs}
    while pending:
        pid, status = os.wait()
        if pid in pending:
            walls.append(time.perf_counter() - t0); rcs.append(os.waitstatus_to_exitcode(status)); del pending[pid]
    makespan = time.perf_counter() - t0
    t1, i1, s1 = stat()
    busy = 1 - (i1 - i_all) / max(t1 - t_all, 1); steal = (s1 - s_all) / max(t1 - t_all, 1)
    return dict(makespan=makespan, wall_mean=float(np.mean(walls)), wall_max=max(walls), wall_min=min(walls),
                busy=busy, steal=steal, rc_nonzero=sum(1 for r in rcs if r))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--levels", default="1,2,3,4,6,8,12,16,24,32"); ap.add_argument("--reps", type=int, default=3)
    a = ap.parse_args(); levels = [int(x) for x in a.levels.split(",")]
    os.makedirs(f"{AT}/results/density", exist_ok=True)
    out = open(f"{AT}/results/density/density.csv", "w"); w = csv.writer(out)
    w.writerow(["workload", "n", "rep", "makespan_s", "wall_mean_s", "wall_max_s", "wall_min_s", "cpu_busy_frac", "steal_frac", "rc_nonzero"])
    for name, wl in WORKLOADS.items():
        run_batch(wl, 1)   # warm-up
        for n in levels:
            for rep in range(1, a.reps + 1):
                r = run_batch(wl, n)
                w.writerow([name, n, rep, f"{r['makespan']:.3f}", f"{r['wall_mean']:.3f}", f"{r['wall_max']:.3f}", f"{r['wall_min']:.3f}", f"{r['busy']:.3f}", f"{r['steal']:.4f}", r["rc_nonzero"]])
                out.flush()
                print(f"{name} n={n} rep={rep}: makespan {r['makespan']:.2f}s mean {r['wall_mean']:.2f}s busy {r['busy']*100:.0f}% steal {r['steal']*100:.2f}% rc!=0:{r['rc_nonzero']}", flush=True)
    out.close()

if __name__ == "__main__":
    main()
