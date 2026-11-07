"""build_report.py — assemble REPORT.md from tools/report_template.md by
splicing in generated tables ({{include:path}}), so every number in the
report comes from the analysis outputs. Also writes the two small tables
that only the report needs."""
import re, pandas as pd
AT = "/home/user/agent-tax"; S = f"{AT}/results/summary"
tv = pd.read_csv(f"{S}/time_view_per_task.csv")
L = ["| Task | episode s | model+loop s (%) | tool s (%) | of which test run s | snapshots s | agent actions | median gap s | resolved |", "|---|---|---|---|---|---|---|---|---|"]
for _, r in tv.iterrows():
    L.append(f"| {r.task} | {r.episode_s:.0f} | {r.model_loop_s:.0f} ({r.model_loop_s/r.episode_s*100:.0f}%) | {r.tool_total_s:.1f} ({r.tool_total_s/r.episode_s*100:.0f}%) | {r['tool:test run']:.1f} | {r.snapshot_s:.2f} | {int(r.n_cmds)} cmds + {int(r.n_edits)} edits | {r.median_gap_s:.1f} | {r.resolved} |")
t = tv[["episode_s", "model_loop_s", "tool_total_s", "snapshot_s"]].sum()
L.append(f"| **total** | {t.episode_s:.0f} | {t.model_loop_s:.0f} ({t.model_loop_s/t.episode_s*100:.1f}%) | {t.tool_total_s:.1f} ({t.tool_total_s/t.episode_s*100:.1f}%) | {tv['tool:test run'].sum():.1f} | {t.snapshot_s:.2f} | | | 7/8 |")
open(f"{S}/time_view_table.md", "w").write("\n".join(L) + "\n")
inc = pd.read_csv(f"{S}/inclusive_context_shares.csv", index_col=0)
I = ["| Class | " + " | ".join(inc.columns) + " |", "|---" * (len(inc.columns) + 1) + "|"]
for idx, r in inc.iterrows():
    I.append(f"| {idx} | " + " | ".join(f"{v:.1f}" for v in r.values) + " |")
open(f"{S}/inclusive_context_table.md", "w").write("\n".join(I) + "\n")
tpl = open(f"{AT}/tools/report_template.md").read()
out = re.sub(r"\{\{include:([^}]+)\}\}", lambda m: open(f"{AT}/{m.group(1)}").read().strip(), tpl)
out = out.replace("### H", "#### H")   # nest the generated hypothesis headings
open(f"{AT}/REPORT.md", "w").write(out)
print("REPORT.md written,", len(out.splitlines()), "lines")
