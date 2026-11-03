"""replay.py — Phase B: replay every recorded command of a task under profiling.

usage: $ANA_PY tools/replay.py <task> [--reps 3] [--seqs 4,5,...] [--no-warmup]

For each recorded command (kind=cmd in logs/<task>/calls.jsonl), in order:
  warm-up : one unprofiled execution (fills page cache / bytecode caches the
            way the original episode had them warm)
  rep k   : (a) restore checkpoint -> perf stat + /usr/bin/time -v
            (b) restore checkpoint -> perf record -a -g (cpu-clock, 999 Hz)
                -> perf script | perfparse.py -> profile.json (perf.data deleted)
Results go to results/<task>/<seq>/rep<k>.{stat.csv,time.txt,profile.json,meta.json}.

Environment per command (see DECISIONS.md D6):
  solve-phase command        : working tree restored to its pre-command
                               checkpoint, task venv (interpreter swapped to the
                               symbol-rich replay interpreter)
  setup command run in the task dir (clone, venv creation): runs in an empty
                               scratch dir instead, so the real repo/venv survive
  package install command    : working tree restored, then a *fresh scratch
                               venv* that reproduces the pre-command package set
                               (empty for setup installs; the episode-start
                               package set for solve-phase installs)
"""
import argparse, json, os, re, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import classify, load_calls

AT = "/home/user/agent-tax"; WORK = "/home/user/work"
PERF = "/usr/lib/linux-tools/6.8.0-147-generic/perf"
ANA_PY = "/home/user/anavenv/bin/python"
REPLAY_PY = "/root/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11"
STAT_EVENTS = "task-clock,context-switches,cpu-migrations,page-faults,minor-faults,major-faults"
TIMEOUT = 600

def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, **kw)

def swap_venv(venv):
    """Point the task venv at the symbol-rich replay interpreter (same 3.11 ABI)."""
    for f in ("python", "python3", "python3.11"):
        p = f"{venv}/bin/{f}"
        if os.path.islink(p) or os.path.exists(p): os.remove(p)
        os.symlink(REPLAY_PY, p)
    cfg = open(f"{venv}/pyvenv.cfg").read()
    home = os.path.dirname(REPLAY_PY)
    cfg = re.sub(r"(?m)^home = .*", f"home = {home}", cfg)
    cfg = re.sub(r"(?m)^executable = .*", f"executable = {REPLAY_PY}", cfg)
    cfg = re.sub(r"(?m)^version = .*", "version = 3.11.15", cfg)
    open(f"{venv}/pyvenv.cfg", "w").write(cfg)

def restore(task, snap):
    if snap and snap != "none":
        r = sh(f"{AT}/tools/restore.sh {task} {snap}")
        if r.returncode: raise RuntimeError(f"restore {task} {snap} failed")

def start_packages(task, calls):
    """Package spec list describing the venv at episode start."""
    fz = f"{AT}/logs/{task}/freeze_start.txt"
    if os.path.exists(fz):
        return [l.strip() for l in open(fz) if l.strip() and not l.startswith(("-e ", "#")) and " @ " not in l], True
    pkgs = []
    for c in calls:
        if c["kind"] == "cmd" and c["phase"] == "setup":
            out = open(f"{AT}/logs/{task}/out/{c['seq']:04d}.txt", errors="replace").read()
            for m in re.finditer(r"Successfully installed (.+)", out):
                for nv in m.group(1).split():
                    n, v = nv.rsplit("-", 1)
                    if "dev" in v or "+" in v: continue        # the editable project itself
                    pkgs.append(f"{n}=={v}")
    return pkgs, False

class Env:
    def __init__(self, task, calls):
        self.task = task; self.calls = calls
        self.repo = f"{WORK}/{task}/repo"; self.venv = f"{WORK}/{task}/venv"
        self.scratch = f"{WORK}/{task}/replay_scratch"
        self.svenv = f"{WORK}/{task}/replay_venv"
        self.pkgs = None

    def prepare(self, c, cls):
        """Return (cwd, env) for one execution of command c, after resetting state."""
        env = dict(os.environ)
        env.pop("VIRTUAL_ENV", None)
        if c["phase"] == "setup" and os.path.realpath(c["cwd"]) == os.path.realpath(f"{WORK}/{self.task}"):
            shutil.rmtree(self.scratch, ignore_errors=True); os.makedirs(self.scratch)
            return self.scratch, env
        restore(self.task, c["pre_snap"])
        venv = self.venv
        if cls == "package install":
            shutil.rmtree(self.svenv, ignore_errors=True)
            sh(f"{REPLAY_PY} -m venv {self.svenv}", check=True, stdout=subprocess.DEVNULL)
            if c["phase"] != "setup":
                if self.pkgs is None: self.pkgs, _ = start_packages(self.task, self.calls)
                sh(f"cd {self.repo} && {self.svenv}/bin/python -m pip install -q -e . " + " ".join(f"'{p}'" for p in self.pkgs),
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            venv = self.svenv
        env["VIRTUAL_ENV"] = venv
        env["PATH"] = f"{venv}/bin:" + env["PATH"]
        return c["cwd"], env

def run_stat(cmd, cwd, env, d, rep):
    t0 = time.time()
    p = sh(f"{PERF} stat -x, -o {d}/rep{rep}.stat.csv -e {STAT_EVENTS} -- /usr/bin/time -v -o {d}/rep{rep}.time.txt "
           f"timeout -s KILL {TIMEOUT} bash -c {sq(cmd)} > {d}/rep{rep}.out.txt 2>&1", cwd=cwd, env=env)
    return p.returncode, time.time() - t0

def run_record(cmd, cwd, env, d, rep):
    data = f"{d}/rep{rep}.perf.data"; pidf = f"{d}/rep{rep}.root.pid"
    t0 = time.time()
    p = sh(f"{PERF} record -z -q -o {data} -e cpu-clock -F 999 -a -g -- {AT}/tools/replay_exec.sh {pidf} {sq(cmd)} "
           f"> /dev/null 2>&1", cwd=cwd, env=env)
    wall = time.time() - t0
    root = open(pidf).read().strip()
    q = sh(f"{PERF} script -i {data} -F comm,pid,tid,cpu,time,ip,sym,dso --show-task-events 2>/dev/null | "
           f"{ANA_PY} {AT}/tools/perfparse.py {root} {d}/rep{rep}.profile.json")
    os.remove(pidf)
    return p.returncode, wall

def sq(s):
    return "'" + s.replace("'", "'\\''") + "'"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task"); ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--seqs", default=""); ap.add_argument("--no-warmup", action="store_true")
    a = ap.parse_args()
    os.system("sysctl -qw kernel.perf_event_max_stack=512")
    calls = load_calls(f"{AT}/logs/{a.task}/calls.jsonl")
    cmds = [c for c in calls if c["kind"] == "cmd"]
    if a.seqs: cmds = [c for c in cmds if c["seq"] in {int(x) for x in a.seqs.split(",")}]
    swap_venv(f"{WORK}/{a.task}/venv")
    E = Env(a.task, calls)
    for c in cmds:
        cls = classify(c["cmd"])
        d = f"{AT}/results/{a.task}/{c['seq']:04d}"; os.makedirs(d, exist_ok=True)
        if os.path.exists(f"{d}/done.json"): continue
        print(f"[replay] {a.task} seq={c['seq']} class={cls} orig={c['dur_s']:.2f}s :: {c['cmd'][:70]!r}", flush=True)
        meta = {"task": a.task, "seq": c["seq"], "phase": c["phase"], "cls": cls, "cmd": c["cmd"],
                "orig_rc": c["rc"], "orig_dur_s": c["dur_s"], "reps": []}
        if not a.no_warmup:
            cwd, env = E.prepare(c, cls)
            sh(f"timeout -s KILL {TIMEOUT} bash -c {sq(c['cmd'])} > /dev/null 2>&1", cwd=cwd, env=env)
        for rep in range(1, a.reps + 1):
            cwd, env = E.prepare(c, cls); rc_s, wall_s = run_stat(c["cmd"], cwd, env, d, rep)
            cwd, env = E.prepare(c, cls); rc_r, wall_r = run_record(c["cmd"], cwd, env, d, rep)
            meta["reps"].append({"rep": rep, "stat_rc": rc_s, "stat_wall_s": wall_s, "rec_rc": rc_r, "rec_wall_s": wall_r})
            print(f"    rep{rep}: stat rc={rc_s} {wall_s:.2f}s | record rc={rc_r} {wall_r:.2f}s", flush=True)
        json.dump(meta, open(f"{d}/done.json", "w"), indent=1)
    # leave the task repo in its episode-end state
    end = [c for c in calls if c["kind"] == "snap" and c["reason"] == "episode_end"]
    if end: restore(a.task, end[-1]["snap"])
    shutil.rmtree(E.scratch, ignore_errors=True); shutil.rmtree(E.svenv, ignore_errors=True)

if __name__ == "__main__":
    main()
