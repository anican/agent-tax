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

def setup_packages_before(task, calls, seq):
    """Packages installed by setup-phase commands that ran before command `seq`."""
    pkgs = []
    for c in calls:
        if c["kind"] == "cmd" and c["phase"] == "setup" and c["seq"] < seq:
            out = open(f"{AT}/logs/{task}/out/{c['seq']:04d}.txt", errors="replace").read()
            for m in re.finditer(r"Successfully installed (.+)", out):
                for nv in m.group(1).split():
                    n, v = nv.rsplit("-", 1)
                    if "dev" in v or "+" in v: continue
                    pkgs.append(f"{n}=={v}")
    return pkgs

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
    """Per-task replay environment.

    Scratch dirs/venvs are never deleted right before a profiled run: deleting
    thousands of files and immediately creating new ones makes ext4's inode
    allocator scan recently-deleted inodes (`recently_deleted`), which the live
    run did not pay. Each execution gets a fresh directory under replay_trash/,
    and the trash is removed only at the end of the task, followed by a pause
    longer than the ext4 'recently deleted' window."""
    def __init__(self, task, calls):
        self.task = task; self.calls = calls
        self.repo = f"{WORK}/{task}/repo"; self.venv = f"{WORK}/{task}/venv"
        self.trash = f"{WORK}/{task}/replay_trash"; os.makedirs(self.trash, exist_ok=True)
        self.startvenv = f"{WORK}/{task}/replay_startvenv"
        self.n = 0; self.pkgs = None
        cmds = [c for c in calls if c["kind"] == "cmd"]
        inst = [c["seq"] for c in cmds if c["phase"] == "solve" and classify(c["cmd"]) == "package install"]
        self.first_solve_install = min(inst) if inst else None

    def _fresh(self, prefix):
        self.n += 1; p = f"{self.trash}/{prefix}{self.n}"
        return p

    def _populate(self, venv):
        sh(f"{REPLAY_PY} -m venv {venv}", check=True, stdout=subprocess.DEVNULL)
        if self.pkgs is None: self.pkgs, _ = start_packages(self.task, self.calls)
        sh(f"cd {self.repo} && {venv}/bin/python -m pip install -q -e . " + " ".join(f"'{p}'" for p in self.pkgs),
           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def prepare(self, c, cls):
        """Return (cwd, env) for one execution of command c, after resetting state."""
        env = dict(os.environ)
        env.pop("VIRTUAL_ENV", None)
        if c["phase"] == "setup" and os.path.realpath(c["cwd"]) == os.path.realpath(f"{WORK}/{self.task}"):
            d = self._fresh("s"); os.makedirs(d)
            return d, env
        restore(self.task, c["pre_snap"])
        venv = self.venv
        if cls == "build" and c["phase"] == "setup":
            # a setup-time build started from a clean tree: remove ignored build outputs
            # (build/, *.so, generated .c) so every replay is a full build, not a no-op
            sh(f"cd {self.repo} && git clean -qfdX")
        if cls == "package install":
            venv = self._fresh("v")
            if c["phase"] == "setup":
                sh(f"{REPLAY_PY} -m venv {venv}", check=True, stdout=subprocess.DEVNULL)
                prev = setup_packages_before(self.task, self.calls, c["seq"])
                if prev:   # reproduce what earlier setup installs put into the venv
                    sh(f"{venv}/bin/python -m pip install -q " + " ".join(f"'{p}'" for p in prev),
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                self._populate(venv)
        elif c["phase"] == "solve" and self.first_solve_install and c["seq"] < self.first_solve_install:
            # the venv changed during the episode: commands before the first in-episode
            # install see the episode-start package set
            if not os.path.exists(f"{self.startvenv}/bin/python"): self._populate(self.startvenv)
            venv = self.startvenv
        env["VIRTUAL_ENV"] = venv
        env["PATH"] = f"{venv}/bin:" + env["PATH"]
        return c["cwd"], env

    def cleanup(self):
        if os.path.isdir(self.trash) and os.listdir(self.trash):
            shutil.rmtree(self.trash, ignore_errors=True); sh("sync"); time.sleep(70)
        shutil.rmtree(self.trash, ignore_errors=True)

def replay_cmd(c):
    """The command as executed in replays: the stripped deadsnakes interpreter path is
    replaced by the symbol-rich replay interpreter (same 3.11 ABI; DECISIONS.md D3)."""
    return c["cmd"].replace("/usr/bin/python3.11", REPLAY_PY)

def run_stat(cmd, cwd, env, d, rep):
    t0 = time.time()
    p = sh(f"{PERF} stat -x, -o {d}/rep{rep}.stat.csv -e {STAT_EVENTS} -- /usr/bin/time -v -o {d}/rep{rep}.time.txt "
           f"timeout -s KILL {TIMEOUT} bash -c {sq(cmd)} > {d}/rep{rep}.out.txt 2>&1", cwd=cwd, env=env)
    return p.returncode, time.time() - t0

def run_record(cmd, cwd, env, d, rep, tag=None):
    tag = tag or f"rep{rep}"
    data = f"{d}/{tag}.perf.data"; pidf = f"{d}/{tag}.root.pid"
    t0 = time.time()
    p = sh(f"{PERF} record -z -q -o {data} -e cpu-clock -F 999 -a -g -- {AT}/tools/replay_exec.sh {pidf} {sq(cmd)} "
           f"> /dev/null 2>&1", cwd=cwd, env=env)
    wall = time.time() - t0
    root = open(pidf).read().strip()
    q = sh(f"{PERF} script -i {data} -F comm,pid,tid,cpu,time,ip,sym,dso --show-task-events 2>/dev/null | "
           f"{ANA_PY} {AT}/tools/perfparse.py {root} {d}/{tag}.profile.json")
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
        if not a.no_warmup and cls != "build":   # a warm-up full build only costs time
            cwd, env = E.prepare(c, cls)
            sh(f"timeout -s KILL {TIMEOUT} bash -c {sq(replay_cmd(c))} > /dev/null 2>&1", cwd=cwd, env=env)
        for rep in range(1, a.reps + 1):
            # resume support: reuse runs that already completed (e.g. after the batch was killed)
            if os.path.exists(f"{d}/rep{rep}.stat.csv") and os.path.exists(f"{d}/rep{rep}.time.txt"):
                tt = open(f"{d}/rep{rep}.time.txt").read()
                m = re.search(r"Exit status: (\d+)", tt); rc_s = int(m.group(1)) if m else None
                m = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([\d:.]+)", tt)
                wall_s = sum(float(x) * 60 ** i for i, x in enumerate(reversed(m.group(1).split(":")))) if m else None
            else:
                cwd, env = E.prepare(c, cls); rc_s, wall_s = run_stat(replay_cmd(c), cwd, env, d, rep)
            if os.path.exists(f"{d}/rep{rep}.profile.json"):
                rc_r, wall_r = None, None
            else:
                cwd, env = E.prepare(c, cls); rc_r, wall_r = run_record(replay_cmd(c), cwd, env, d, rep)
            meta["reps"].append({"rep": rep, "stat_rc": rc_s, "stat_wall_s": wall_s, "rec_rc": rc_r, "rec_wall_s": wall_r})
            print(f"    rep{rep}: stat rc={rc_s} {wall_s} | record rc={rc_r} {wall_r}", flush=True)
        json.dump(meta, open(f"{d}/done.json", "w"), indent=1)
    # leave the task repo in its episode-end state
    end = [c for c in calls if c["kind"] == "snap" and c["reason"] == "episode_end"]
    if end: restore(a.task, end[-1]["snap"])
    E.cleanup()

if __name__ == "__main__":
    main()
