"""replay_loop.py — extra statistical power for very short read-only commands.

A 10 ms `grep` yields ~10 cpu-clock samples per replay, too few for category
shares. For solve-phase commands of class search/read or git that are
read-only (no redirection into files, no git state changes) and took < 1 s
live, this records 3 additional profiles, each of
    for i in $(seq 30); do bash -c '<cmd>'; done
(the same `bash -c` structure as the live wrapper), saved as
results/<task>/<seq>/loop<k>.profile.json. analyze.py pools loop<k> with rep<k>.

usage: $ANA_PY tools/replay_loop.py <task>
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import classify, load_calls
from replay import Env, restore, swap_venv, sq, run_record, AT, WORK

ITER = 30
MUTATING = re.compile(r"(?<![0-9&])>(?!&)|\bgit\s+(stash|checkout|reset|commit|add|apply|am|rebase|merge|clean|init|fetch|pull|push|rm|mv)\b|\btee\b|\brm\b|\bmv\b|\bsed\s+-i|\btouch\b|\bmkdir\b")

def eligible(c):
    if c["phase"] != "solve" or c["dur_s"] >= 1.0: return False
    if classify(c["cmd"]) not in ("search/read", "git"): return False
    body = re.sub(r"2>&1|>\s*/dev/null|2>\s*/dev/null", "", c["cmd"])
    return not MUTATING.search(body)

def main():
    task = sys.argv[1]
    calls = load_calls(f"{AT}/logs/{task}/calls.jsonl")
    swap_venv(f"{WORK}/{task}/venv"); E = Env(task, calls)
    for c in calls:
        if c["kind"] != "cmd" or not eligible(c): continue
        d = f"{AT}/results/{task}/{c['seq']:04d}"
        if not os.path.exists(f"{d}/done.json") or os.path.exists(f"{d}/loop3.profile.json"): continue
        loop_cmd = f"for i in $(seq {ITER}); do bash -c {sq(c['cmd'])}; done"
        print(f"[loop] {task} seq={c['seq']} :: {c['cmd'][:70]!r}", flush=True)
        for k in range(1, 4):
            cwd, env = E.prepare(c, classify(c["cmd"]))
            rc, wall = run_record(loop_cmd, cwd, env, d, k, tag=f"loop{k}")
            print(f"    loop{k}: rc={rc} {wall:.2f}s", flush=True)
        meta = json.load(open(f"{d}/done.json")); meta["loop_iterations"] = ITER
        json.dump(meta, open(f"{d}/done.json", "w"), indent=1)
    end = [x for x in calls if x["kind"] == "snap" and x["reason"] == "episode_end"]
    if end: restore(task, end[-1]["snap"])

if __name__ == "__main__":
    main()
