"""callgrind_check.py — cross-check perf's user-space category shares with
valgrind/callgrind instruction counts on a small sample of commands.

For each sample command: restore its checkpoint, run it once under
`valgrind --tool=callgrind --trace-children=yes`, and 3 times under the same
`perf record -a -g` setup as the main replays. Both sides are then classified
with the SAME taxonomy, using only the leaf function (stack context removed,
because callgrind's flat self-cost has no per-sample stack), restricted to
user-space (callgrind cannot see the kernel).

Units differ: callgrind counts instructions executed (Ir); perf counts
timer samples of on-CPU time. Agreement is expected only to the extent that
CPI is similar across categories.

usage: $ANA_PY tools/callgrind_check.py
"""
import glob, json, os, re, shutil, subprocess, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
from common import classify, load_calls
from replay import Env, restore, swap_venv, sq, run_record, AT, WORK
from taxonomy import categorize, is_kernel

OUT = f"{AT}/results/callgrind"
# (name, task, seq, command override or None)  — reduced subsets where the recorded command is long
SAMPLE = [
    ("grep_sed", "django__django-16595", 4, None),
    ("git_diff_status", "sympy__sympy-24066", 11, None),
    ("flask_pytest_blueprints", "pallets__flask-5014", 6, None),
    ("sympy_repro_script", "sympy__sympy-24066", 6, None),
    ("sympy_pytest_quantities", "sympy__sympy-24066", 9, "python -m pytest -q sympy/physics/units/tests/test_quantities.py 2>&1 | tail -5"),
    ("django_runtests_optimizer", "django__django-16595", 6, None),
]

def merge(cat):
    # buckets comparable between perf and callgrind (no stack context on either side)
    return cat

def parse_annotate(path):
    out = subprocess.run(f"callgrind_annotate --inclusive=no --threshold=100 {path}", shell=True,
                         capture_output=True, text=True).stdout
    cmd = re.search(r"^Cmd:\s*(.*)$", out, re.M)
    comm = os.path.basename(cmd.group(1).split()[0]) if cmd else "?"
    rows = []
    for line in out.splitlines():
        m = re.match(r"^\s*([\d,]+)\s+\([\s\d.]+%\)\s+(.*?):(.*?) \[(.*)\]\s*$", line)
        if m:
            ir = int(m.group(1).replace(",", "")); fn = m.group(3).strip(); obj = m.group(4)
            rows.append((comm, fn, obj, ir))
    return rows

def main():
    os.makedirs(OUT, exist_ok=True)
    summary = {}
    for name, task, seq, override in SAMPLE:
        d = f"{OUT}/{name}"; os.makedirs(d, exist_ok=True)
        calls = load_calls(f"{AT}/logs/{task}/calls.jsonl")
        c = dict([x for x in calls if x["kind"] == "cmd" and x["seq"] == seq][0])
        if override: c["cmd"] = override
        cls = classify(c["cmd"]); swap_venv(f"{WORK}/{task}/venv"); E = Env(task, calls)
        print(f"[callgrind] {name}: {c['cmd'][:80]!r}", flush=True)
        if not glob.glob(f"{d}/callgrind.out.*"):
            cwd, env = E.prepare(c, cls)
            r = subprocess.run(f"timeout -s KILL 1800 valgrind --tool=callgrind --trace-children=yes -q "
                               f"--callgrind-out-file={d}/callgrind.out.%p bash -c {sq(c['cmd'])} > {d}/out.txt 2>&1",
                               shell=True, cwd=cwd, env=env)
            print(f"   valgrind rc={r.returncode}", flush=True)
        for rep in range(1, 4):
            if not os.path.exists(f"{d}/rep{rep}.profile.json"):
                cwd, env = E.prepare(c, cls); run_record(c["cmd"], cwd, env, d, rep)
        E.cleanup()
        restore(task, [x for x in calls if x["kind"] == "snap" and x["reason"] == "episode_end"][-1]["snap"])
        # callgrind side
        cg = Counter()
        for f in glob.glob(f"{d}/callgrind.out.*"):
            for comm, fn, obj, ir in parse_annotate(f):
                fn = "[unknown]" if fn in ("???", "0x0000000000000000") or fn.startswith("0x") else fn
                cat, sub, rid = categorize("cmd", comm, fn, obj, "", "")
                cg[cat] += ir
        # perf side: user-space samples only, leaf-only categorization
        pf = Counter()
        for rep in range(1, 4):
            prof = json.load(open(f"{d}/rep{rep}.profile.json"))
            for g, comm, sym, dso, sc, ctx, n in prof["samples"]:
                if g != "cmd" or is_kernel(dso): continue
                cat, sub, rid = categorize(g, comm, sym, dso, "", "")
                pf[cat] += n
        tc, tp = sum(cg.values()), sum(pf.values())
        cats = sorted(set(cg) | set(pf), key=lambda k: -(pf.get(k, 0) / max(tp, 1) + cg.get(k, 0) / max(tc, 1)))
        summary[name] = {"task": task, "seq": seq, "cmd": c["cmd"], "cls": cls, "callgrind_Ir": tc, "perf_user_samples": tp,
                         "shares": {k: {"callgrind_pct": 100 * cg.get(k, 0) / max(tc, 1), "perf_pct": 100 * pf.get(k, 0) / max(tp, 1)} for k in cats}}
        print(json.dumps(summary[name]["shares"], indent=0)[:600], flush=True)
    json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
    # markdown
    lines = []
    for name, s in summary.items():
        lines.append(f"\n**{name}** (`{s['task']}` seq {s['seq']}, class {s['cls']}; callgrind {s['callgrind_Ir']:,} Ir, perf {s['perf_user_samples']} user-space samples over 3 reps)\n")
        lines.append("| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |")
        lines.append("|---|---|---|---|")
        for k, v in s["shares"].items():
            if v["callgrind_pct"] < 0.5 and v["perf_pct"] < 0.5: continue
            lines.append(f"| {k} | {v['callgrind_pct']:.1f} | {v['perf_pct']:.1f} | {v['perf_pct'] - v['callgrind_pct']:+.1f} |")
    open(f"{OUT}/summary.md", "w").write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
