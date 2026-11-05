"""ext_cpu_view.py — CPU-view summary of the extension episodes (different
model, D18) next to the original study's episode-only shares.
Writes results/summary/extension_cpu_view.md (+ .csv)."""
import os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
os.environ["AT_INCLUDE_EXT"] = "1"
import analyze
from taxonomy import CATS
OUT = analyze.OUT
cat, *_ = analyze.load_profiles()
ep = cat[cat.phase == "solve"].copy()
ep["set"] = ep.task.apply(lambda t: "extension (new model)" if analyze.is_ext(t) else "original (8 episodes)")
def shares(df, keys):
    t = df.groupby(keys + ["rep", "cat"])["n"].sum().unstack("cat", fill_value=0)
    t = t.div(t.sum(axis=1), axis=0) * 100
    return t.groupby(level=keys).mean(), t.groupby(level=keys).std()
m_set, s_set = shares(ep, ["set"])
m_task, s_task = shares(ep[ep.set.str.startswith("extension")], ["task"])
m_cls, s_cls = shares(ep[ep.set.str.startswith("extension")], ["cls"])
cols = [c for c in CATS if c in m_set.columns]
def table(title, m, s):
    L = [f"| {title} | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for idx in m.index:
        L.append(f"| {idx} | " + " | ".join(f"{m.loc[idx, c]:.1f} ± {s.loc[idx, c]:.1f}" for c in cols) + " |")
    return "\n".join(L)
ncmd = ep.groupby("set")[["task", "seq"]].apply(lambda x: len(x.drop_duplicates()))
md = ["Episode commands only (setup excluded), mean ± std over 3 replays, pooled over commands (time-weighted). "
      f"Commands: {', '.join(f'{k}: {v}' for k, v in ncmd.items())}.", "",
      table("Set", m_set.reindex(columns=cols).fillna(0), s_set.reindex(columns=cols).fillna(0)), "",
      table("Extension task", m_task.reindex(columns=cols).fillna(0), s_task.reindex(columns=cols).fillna(0)), "",
      table("Extension class", m_cls.reindex(columns=cols).fillna(0), s_cls.reindex(columns=cols).fillna(0))]
open(f"{OUT}/extension_cpu_view.md", "w").write("\n".join(md) + "\n")
pd.concat([m_set, m_task, m_cls]).to_csv(f"{OUT}/extension_cpu_view.csv", float_format="%.2f")
print("\n".join(md))
