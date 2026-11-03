"""extract_traj_cmds.py — pull the bash actions out of mini-swe-agent trajectory
files (treated as untrusted data; nothing is executed here).
usage: python -I tools/extract_traj_cmds.py <traj.json> <out.json>"""
import json, re, sys
t = json.load(open(sys.argv[1]))
msgs = t.get("messages") or t.get("trajectory") or []
cmds = []
for m in msgs:
    if m.get("role") != "assistant": continue
    c = m.get("content")
    if isinstance(c, list): c = "".join(x.get("text", "") for x in c if isinstance(x, dict))
    for b in re.findall(r"```bash\s*\n(.*?)\n```", c or "", re.S):
        cmds.append(b.strip())
json.dump({"source": sys.argv[1], "n_steps": len(cmds), "cmds": cmds,
           "exit_status": (t.get("info") or {}).get("exit_status")}, open(sys.argv[2], "w"), indent=1)
print(sys.argv[1].split("/")[-1], len(cmds), "commands")
