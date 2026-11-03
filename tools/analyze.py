"""analyze.py — Phase C: turn logs/ and results/ into tables (results/summary/*.csv,
*.md) and figures (figs/*.png).

usage: $ANA_PY tools/analyze.py
"""
import glob, json, os, re, sys
from collections import Counter, defaultdict
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from common import classify, load_calls, CLASSES
from taxonomy import categorize, inclusive_flags, CATS

AT = "/home/user/agent-tax"; OUT = f"{AT}/results/summary"; FIG = f"{AT}/figs"
os.makedirs(OUT, exist_ok=True); os.makedirs(FIG, exist_ok=True)
CAT_COLORS = dict(zip(CATS, ["#4C72B0", "#DD8452", "#C44E52", "#8172B3", "#937860", "#DA8BC3",
                             "#55A868", "#64B5CD", "#CCB974", "#8C8C8C", "#2F4B7C", "#B0B0B0", "#E0E0E0", "#000000"]))
CLS_ORDER = ["search/read", "git", "package install", "build", "test run", "other"]

# ------------------------------------------------------------------ CPU VIEW
def load_profiles():
    rows, leaf_rows, incl_rows, kth_rows, groups_rows = [], [], [], [], []
    cache = {}
    for done in sorted(glob.glob(f"{AT}/results/*/*/done.json")):
        meta = json.load(open(done)); d = os.path.dirname(done)
        for r, pf in [(r, f"{d}/{t}{r['rep']}.profile.json") for r in meta["reps"] for t in ("rep", "loop")]:
            if not os.path.exists(pf): continue
            prof = json.load(open(pf))
            # commands with looped profiles: weight every sample by 1/(1+ITER) so the
            # command still counts as ONE execution (rep + ITER loop executions averaged)
            has_loop = os.path.exists(f"{d}/loop{r['rep']}.profile.json")
            w = 1.0 / (1 + meta.get("loop_iterations", 30)) if has_loop else 1.0
            base = dict(task=meta["task"], seq=meta["seq"], phase=meta["phase"], cls=meta["cls"], rep=r["rep"],
                        src="loop" if "/loop" in pf else "rep")
            groups_rows.append({**base, **{f"g_{k}": v for k, v in prof["groups"].items()}})
            for g, comm, sym, dso, sc, ctx, n in prof["samples"]:
                key = (g, comm, sym, dso, sc, ctx)
                if key not in cache: cache[key] = categorize(*key)
                cat, sub, rid = cache[key]
                if g == "cmd":
                    rows.append({**base, "cat": cat, "sub": sub, "rule": rid, "n": n * w, "raw": n})
                    leaf_rows.append({**base, "sym": sym, "dso": os.path.basename(dso), "cat": cat, "n": n * w})
                    for f in inclusive_flags(sym, dso, sc, ctx):
                        incl_rows.append({**base, "flag": f, "n": n * w})
                    if sc: incl_rows.append({**base, "flag": f"syscall:{sc}", "n": n * w})
                else:
                    kth_rows.append({**base, "comm": re.sub(r"[/:]\d+.*", "", comm), "cat": cat, "sym": sym, "n": n})
    return (pd.DataFrame(rows), pd.DataFrame(leaf_rows), pd.DataFrame(incl_rows),
            pd.DataFrame(kth_rows), pd.DataFrame(groups_rows))

def shares_by(df, keys):
    """category share of samples, pooled over commands; per rep, then mean/std over reps."""
    t = df.groupby(keys + ["rep", "cat"])["n"].sum().unstack("cat", fill_value=0)
    t = t.div(t.sum(axis=1), axis=0) * 100
    m = t.groupby(level=keys).mean(); s = t.groupby(level=keys).std()
    return m.reindex(columns=[c for c in CATS if c in m.columns]), s.reindex(columns=[c for c in CATS if c in s.columns])

def cpu_view(cat, leaf, incl, kth, groups):
    cat = cat.copy(); cat["all"] = "ALL"
    m_cls, s_cls = shares_by(cat, ["cls"]); m_all, s_all = shares_by(cat, ["all"])
    m = pd.concat([m_cls.reindex([c for c in CLS_ORDER if c in m_cls.index]), m_all]).fillna(0)
    s = pd.concat([s_cls.reindex([c for c in CLS_ORDER if c in s_cls.index]), s_all]).fillna(0)
    samples = pd.concat([cat.groupby(["cls", "rep"])["raw"].sum().groupby("cls").mean(),
                         pd.Series({"ALL": cat.groupby("rep")["raw"].sum().mean()})])
    ncmd = pd.concat([cat.groupby("cls")[["task", "seq"]].apply(lambda x: len(x.drop_duplicates())),
                      pd.Series({"ALL": len(cat[["task", "seq"]].drop_duplicates())})])
    m.to_csv(f"{OUT}/cpu_category_shares_mean.csv", float_format="%.2f")
    s.to_csv(f"{OUT}/cpu_category_shares_std.csv", float_format="%.2f")
    # markdown table: mean ± std
    cols = [c for c in CATS if c in m.columns]
    lines = ["| Class | #cmds | raw samples/rep | " + " | ".join(cols) + " |", "|---" * (len(cols) + 3) + "|"]
    for idx in m.index:
        lines.append(f"| {idx} | {ncmd.get(idx, 0)} | {samples.get(idx, 0):.0f} | " +
                     " | ".join(f"{m.loc[idx, c]:.1f} ± {s.loc[idx, c]:.1f}" for c in cols) + " |")
    open(f"{OUT}/cpu_category_shares.md", "w").write("\n".join(lines) + "\n")
    # figure: stacked bar
    fig, ax = plt.subplots(figsize=(11, 5.5))
    bottom = np.zeros(len(m))
    labels = [f"{i}\n(n={ncmd.get(i, 0)})" for i in m.index]
    for c in cols:
        ax.bar(labels, m[c].values, bottom=bottom, color=CAT_COLORS[c], label=c, edgecolor="white", linewidth=0.5)
        bottom += m[c].values
    ax.set_ylabel("% of sampled on-CPU time (cpu-clock timer samples)")
    ax.set_title("CPU view: category shares of on-CPU time by command class (mean of 3 replays)")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
    ax.set_ylim(0, 100); fig.tight_layout(); fig.savefig(f"{FIG}/cpu_category_shares.png", dpi=150); plt.close(fig)
    # sub-categories (all classes pooled)
    sub = cat.groupby(["cat", "sub", "rule"])["n"].sum() / cat["n"].sum() * 100
    sub.sort_values(ascending=False).to_frame("share_pct").to_csv(f"{OUT}/cpu_subcategory_shares.csv", float_format="%.2f")
    subcls = cat.groupby(["cls", "cat", "sub"])["n"].sum()
    subcls = (subcls / subcls.groupby("cls").transform("sum") * 100).to_frame("share_pct")
    subcls.to_csv(f"{OUT}/cpu_subcategory_shares_by_class.csv", float_format="%.2f")
    # top-20 leaf functions
    tot = leaf["n"].sum()
    top = leaf.groupby(["sym", "dso", "cat"])["n"].sum().sort_values(ascending=False).head(20)
    top = (top / tot * 100).to_frame("share_pct").reset_index()
    top.to_csv(f"{OUT}/top20_leaf_functions.csv", index=False, float_format="%.2f")
    tl = ["| # | Leaf function | DSO | Category | % of on-CPU samples |", "|---|---|---|---|---|"]
    for i, r in top.iterrows():
        tl.append(f"| {i+1} | `{r.sym}` | {r.dso} | {r["cat"]} | {r.share_pct:.2f} |")
    open(f"{OUT}/top20_leaf_functions.md", "w").write("\n".join(tl) + "\n")
    # top leaves per class
    tc = leaf.groupby(["cls", "sym", "dso", "cat"])["n"].sum()
    tc = (tc / tc.groupby("cls").transform("sum") * 100).rename("share_pct").reset_index()
    tc.sort_values(["cls", "share_pct"], ascending=[True, False]).groupby("cls").head(10).to_csv(
        f"{OUT}/top10_leaf_functions_by_class.csv", index=False, float_format="%.2f")
    # inclusive metrics
    tot_cls = cat.groupby("cls")["n"].sum(); tot_cls["ALL"] = cat["n"].sum()
    inc = incl.copy(); inc_all = inc.copy(); inc_all["cls"] = "ALL"; inc = pd.concat([inc, inc_all])
    inc = inc.groupby(["cls", "flag"])["n"].sum().unstack("flag", fill_value=0)
    inc = inc.div(tot_cls.reindex(inc.index), axis=0) * 100
    keep = [c for c in inc.columns if not c.startswith("syscall:")]
    inc[keep].reindex([c for c in CLS_ORDER + ["ALL"] if c in inc.index]).to_csv(f"{OUT}/inclusive_context_shares.csv", float_format="%.2f")
    sysc = inc[[c for c in inc.columns if c.startswith("syscall:")]]
    sysc.T.sort_values("ALL", ascending=False).head(25).to_csv(f"{OUT}/syscall_inclusive_shares.csv", float_format="%.2f")
    # accelerometer inputs
    acc = m[[c for c in ["compression", "hashing/crypto", "memory movement"] if c in m.columns]].copy()
    for c in ["compression", "hashing/crypto", "memory movement"]:
        if c not in acc: acc[c] = 0.0
    acc = acc[["compression", "hashing/crypto", "memory movement"]]
    acc_s = s.reindex(columns=acc.columns).fillna(0)
    al = ["| Class | compression % | hashing/crypto % | memory movement % |", "|---|---|---|---|"]
    for idx in acc.index:
        al.append(f"| {idx} | " + " | ".join(f"{acc.loc[idx, c]:.2f} ± {acc_s.loc[idx, c]:.2f}" for c in acc.columns) + " |")
    open(f"{OUT}/accelerometer_inputs.md", "w").write("\n".join(al) + "\n")
    acc.to_csv(f"{OUT}/accelerometer_inputs.csv", float_format="%.3f")
    # per-command shares (for variance across repeats)
    pc = cat.groupby(["task", "seq", "cls", "rep", "cat"])["n"].sum().unstack("cat", fill_value=0)
    tot_pc = pc.sum(axis=1); pc = pc.div(tot_pc, axis=0) * 100; pc["samples"] = tot_pc
    pc.to_csv(f"{OUT}/per_command_rep_shares.csv", float_format="%.2f")
    # kernel threads & background
    if len(kth):
        k = kth[kth["n"] > 0]
        k.groupby(["comm", "cat"])["n"].sum().sort_values(ascending=False).head(30).to_csv(f"{OUT}/kthread_samples.csv")
    g = groups.fillna(0); g.to_csv(f"{OUT}/sample_groups_per_run.csv", index=False)
    return m, s

# ------------------------------------------------------------------ COUNTERS
def parse_stat(path):
    v = {}
    for line in open(path):
        p = line.strip().split(",")
        if len(p) >= 3 and p[2]:
            try: v[p[2]] = float(p[0])
            except ValueError: v[p[2]] = np.nan
    return v

def parse_time(path):
    v = {}; keys = {"User time (seconds)": "user_s", "System time (seconds)": "sys_s",
                    "Voluntary context switches": "vol_cs", "Involuntary context switches": "invol_cs",
                    "Maximum resident set size (kbytes)": "maxrss_kb", "Minor (reclaiming a frame) page faults": "minflt",
                    "Major (requiring I/O) page faults": "majflt", "File system inputs": "fs_in", "File system outputs": "fs_out",
                    "Elapsed (wall clock) time (h:mm:ss or m:ss)": "wall"}
    for line in open(path):
        if ":" not in line: continue
        k, _, val = line.strip().rpartition(": ")
        if k in keys:
            if keys[k] == "wall":
                parts = [float(x) for x in val.split(":")]; sec = 0
                for p in parts: sec = sec * 60 + p
                v["wall_s"] = sec
            else: v[keys[k]] = float(val)
    return v

def counters():
    rows = []
    for done in sorted(glob.glob(f"{AT}/results/*/*/done.json")):
        meta = json.load(open(done)); d = os.path.dirname(done)
        for r in meta["reps"]:
            sp, tp = f"{d}/rep{r['rep']}.stat.csv", f"{d}/rep{r['rep']}.time.txt"
            if not (os.path.exists(sp) and os.path.exists(tp)): continue
            row = dict(task=meta["task"], seq=meta["seq"], cls=meta["cls"], rep=r["rep"], rc=r["stat_rc"], orig_rc=meta["orig_rc"])
            row.update(parse_stat(sp)); row.update(parse_time(tp)); rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/counters_per_run.csv", index=False, float_format="%.4f")
    cols = ["task-clock", "context-switches", "cpu-migrations", "page-faults", "minor-faults", "major-faults",
            "user_s", "sys_s", "vol_cs", "invol_cs", "maxrss_kb", "wall_s"]
    per_cmd = df.groupby(["task", "seq", "cls"])[cols].mean().reset_index()   # mean over reps
    agg = per_cmd.groupby("cls")[cols].agg(["mean", "median"])
    per_cmd["cpu_s"] = per_cmd["task-clock"] / 1000
    tot = per_cmd.groupby("cls")[["cpu_s", "context-switches", "cpu-migrations", "page-faults", "vol_cs", "invol_cs", "user_s", "sys_s", "wall_s"]].sum()
    tot.loc["ALL"] = tot.sum()
    rates = pd.DataFrame({
        "commands": per_cmd.groupby("cls").size().reindex(tot.index).fillna(len(per_cmd)),
        "CPU s (task-clock, sum)": tot["cpu_s"],
        "sys share of CPU %": tot["sys_s"] / (tot["user_s"] + tot["sys_s"]) * 100,
        "CPU utilization (task-clock / wall)": tot["cpu_s"] / tot["wall_s"],
        "ctx switches / CPU-s": tot["context-switches"] / tot["cpu_s"],
        "voluntary cs / CPU-s": tot["vol_cs"] / tot["cpu_s"],
        "involuntary cs / CPU-s": tot["invol_cs"] / tot["cpu_s"],
        "cpu migrations / CPU-s": tot["cpu-migrations"] / tot["cpu_s"],
        "page faults / CPU-s": tot["page-faults"] / tot["cpu_s"],
    })
    rates.loc["ALL", "commands"] = len(per_cmd)
    med = per_cmd.groupby("cls")[["task-clock", "context-switches", "page-faults", "maxrss_kb", "wall_s"]].median()
    med.columns = ["median task-clock ms", "median ctx sw", "median page faults", "median maxRSS kB", "median wall s"]
    rates = rates.join(med)
    rates = rates.reindex([c for c in CLS_ORDER + ["ALL"] if c in rates.index])
    rates.to_csv(f"{OUT}/counters_by_class.csv", float_format="%.2f")
    # repeat variability of task-clock
    cv = df.groupby(["task", "seq", "cls"])["task-clock"].agg(lambda x: x.std() / x.mean() * 100 if x.mean() > 0 else np.nan)
    cv.rename("task_clock_cv_pct").reset_index().to_csv(f"{OUT}/counters_repeat_cv.csv", index=False, float_format="%.2f")
    lines = ["| Class | " + " | ".join(rates.columns) + " |", "|---" * (len(rates.columns) + 1) + "|"]
    for idx, r in rates.iterrows():
        lines.append(f"| {idx} | " + " | ".join(f"{x:,.0f}" if abs(x) >= 100 else f"{x:.2f}" for x in r.values) + " |")
    open(f"{OUT}/counters_by_class.md", "w").write("\n".join(lines) + "\n")
    rcm = df[df.rc != df.orig_rc][["task", "seq", "cls", "rep", "rc", "orig_rc"]]
    rcm.to_csv(f"{OUT}/replay_rc_mismatches.csv", index=False)
    return rates, df

# ------------------------------------------------------------------ TIME VIEW
def time_view():
    rows, tl = [], {}
    for f in sorted(glob.glob(f"{AT}/logs/*/calls.jsonl")):
        task = f.split("/")[-2]
        calls = load_calls(f)
        st = [c for c in calls if c["kind"] == "episode_start"]; en = [c for c in calls if c["kind"] == "episode_end"]
        if not st or not en: continue
        t0, t1 = st[0]["ts_ns"], en[-1]["ts_ns"]
        cmds = [c for c in calls if c["kind"] == "cmd" and c["phase"] == "solve" and t0 <= c["start_ns"] <= t1]
        snaps = [c for c in calls if c["kind"] == "snap" and t0 <= c["start_ns"] <= t1 and c["reason"] not in ("episode_start", "episode_end")]
        setup = [c for c in calls if c["kind"] == "cmd" and c["phase"] == "setup"]
        r = {"task": task, "episode_s": (t1 - t0) / 1e9, "n_cmds": len(cmds), "n_edits": sum(1 for s in snaps if s["reason"] == "edit"),
             "setup_s": sum(c["dur_s"] for c in setup), "snapshot_s": sum(s["dur_s"] for s in snaps)}
        for cl in CLS_ORDER: r[f"tool:{cl}"] = 0.0
        for c in cmds: r[f"tool:{classify(c['cmd'])}"] += c["dur_s"]
        r["tool_total_s"] = sum(c["dur_s"] for c in cmds)
        r["model_loop_s"] = r["episode_s"] - r["tool_total_s"] - r["snapshot_s"]
        # agent actions: a command together with its own post-command snapshot, or an
        # edit checkpoint (one extra tool call per edit). Gaps are measured between actions.
        after = {s["reason"].split(":")[1]: s for s in snaps if s["reason"].startswith("after_cmd:")}
        actions = [(c["start_ns"], after[str(c["seq"])]["end_ns"] if str(c["seq"]) in after else c["end_ns"]) for c in cmds]
        actions += [(s["start_ns"], s["end_ns"]) for s in snaps if s["reason"] == "edit"]
        gaps = []; prev_end = t0
        for a0, a1 in sorted(actions):
            gaps.append((a0 - prev_end) / 1e9); prev_end = max(prev_end, a1)
        gaps.append((t1 - prev_end) / 1e9)
        r["n_gaps"] = len(gaps)
        r["mean_gap_s"] = float(np.mean(gaps))
        r["median_gap_s"] = float(np.median(gaps)); r["max_gap_s"] = float(np.max(gaps))
        ev = json.load(open(f"{AT}/logs/{task}/eval.json")) if os.path.exists(f"{AT}/logs/{task}/eval.json") else {}
        r["resolved"] = ev.get("result", "unknown")
        rows.append(r); tl[task] = (t0, t1, cmds, snaps)
    df = pd.DataFrame(rows)
    if df.empty: return df
    df.to_csv(f"{OUT}/time_view_per_task.csv", index=False, float_format="%.3f")
    # stacked horizontal bars
    parts = ["model_loop_s"] + [f"tool:{c}" for c in CLS_ORDER] + ["snapshot_s"]
    colors = ["#BBBBBB", "#4C72B0", "#DD8452", "#C44E52", "#8172B3", "#55A868", "#937860", "#000000"]
    names = ["model + agent loop (gaps)"] + [f"tool: {c}" for c in CLS_ORDER] + ["instrumentation (snapshots)"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 0.6 * len(df) + 2))
    for ax, norm in zip(axes, [False, True]):
        left = np.zeros(len(df))
        for p, col, nm in zip(parts, colors, names):
            v = df[p].values.astype(float)
            if norm: v = v / df["episode_s"].values * 100
            ax.barh(df["task"], v, left=left, color=col, label=nm); left += v
        ax.set_xlabel("% of episode wall-clock" if norm else "seconds of episode wall-clock")
        ax.invert_yaxis()
    axes[1].legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
    axes[1].set_yticklabels([])
    fig.suptitle("TIME VIEW: where episode wall-clock time goes (gaps between tool calls ≈ model + loop time)")
    fig.tight_layout(); fig.savefig(f"{FIG}/time_breakdown.png", dpi=150); plt.close(fig)
    # sampler timelines
    for task, (t0, t1, cmds, snaps) in tl.items():
        p = f"{AT}/logs/{task}/sampler.csv"
        if not os.path.exists(p): continue
        s = pd.read_csv(p)
        if len(s) < 3: continue
        busy = s[["user", "nice", "system", "irq", "softirq", "steal"]].sum(axis=1).diff()
        tot = s[["user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal"]].sum(axis=1).diff()
        x = (s["ts_us"] * 1000 - t0) / 1e9
        fig, ax = plt.subplots(2, 1, figsize=(13, 5), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
        ax[0].plot(x, (busy / tot * 100), lw=0.8, color="#333333", label="CPU busy % (all 4 vCPUs)")
        ax[0].plot(x, (s["steal"].diff() / tot * 100), lw=0.8, color="#C44E52", label="steal %")
        for c in cmds:
            ax[0].axvspan((c["start_ns"] - t0) / 1e9, (c["end_ns"] - t0) / 1e9, color="#4C72B0", alpha=0.25, lw=0)
        ax[0].set_ylabel("%"); ax[0].set_ylim(0, 100); ax[0].legend(loc="upper right", fontsize=8)
        ax[0].set_title(f"{task}: CPU busy timeline (200 ms /proc/stat samples); blue spans = tool calls")
        ax[1].plot(x, (s["mem_total_kb"] - s["mem_avail_kb"]) / 1024 / 1024, color="#55A868")
        ax[1].set_ylabel("mem used GiB"); ax[1].set_xlabel("seconds since episode start")
        ax[1].set_xlim(0, (t1 - t0) / 1e9)
        fig.tight_layout(); fig.savefig(f"{FIG}/timeline_{task}.png", dpi=120); plt.close(fig)
    return df

def main():
    tv = time_view()
    cat, leaf, incl, kth, groups = load_profiles()
    if len(cat): cpu_view(cat, leaf, incl, kth, groups)
    counters()
    print(tv.to_string() if len(tv) else "no episodes")
    print(open(f"{OUT}/cpu_category_shares.md").read() if os.path.exists(f"{OUT}/cpu_category_shares.md") else "")

if __name__ == "__main__":
    main()
