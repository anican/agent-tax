"""density_report.py — summarize results/density/density.csv into
results/density/summary.md and figs/density.png."""
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
AT = "/home/user/agent-tax"
d = pd.read_csv(f"{AT}/results/density/density.csv")
g = d.groupby(["workload", "n"]).agg(wall_mean=("wall_mean_s", "mean"), wall_max=("wall_max_s", "mean"),
                                     makespan=("makespan_s", "mean"), makespan_sd=("makespan_s", "std"),
                                     busy=("cpu_busy_frac", "mean"), steal=("steal_frac", "mean"),
                                     rc_nonzero=("rc_nonzero", "max")).reset_index()
base = g[g.n == 1].set_index("workload")
g["slowdown_mean"] = g.apply(lambda r: r.wall_mean / base.loc[r.workload, "wall_mean"], axis=1)
g["slowdown_max"] = g.apply(lambda r: r.wall_max / base.loc[r.workload, "wall_mean"], axis=1)
g["throughput_x"] = g.apply(lambda r: r.n / r.makespan * base.loc[r.workload, "makespan"], axis=1)
g["ideal_slowdown"] = g.n.apply(lambda n: max(1.0, n / 4))
g.to_csv(f"{AT}/results/density/summary.csv", index=False, float_format="%.3f")
L = ["| Workload | N concurrent | per-instance wall s (mean / max) | slowdown vs N=1 (mean / max) | ideal (N/4 vCPUs) | throughput × N=1 | CPU busy % | steal % |", "|---|---|---|---|---|---|---|---|"]
for _, r in g.iterrows():
    L.append(f"| {r.workload} | {r.n} | {r.wall_mean:.2f} / {r.wall_max:.2f} | {r.slowdown_mean:.2f} / {r.slowdown_max:.2f} | {r.ideal_slowdown:.2f} | {r.throughput_x:.2f} | {r.busy*100:.0f} | {r.steal*100:.2f} |")
open(f"{AT}/results/density/summary.md", "w").write("\n".join(L) + "\n")
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
for wl, s in g.groupby("workload"):
    ax[0].plot(s.n, s.slowdown_mean, marker="o", label=wl); ax[1].plot(s.n, s.throughput_x, marker="o", label=wl)
ns = sorted(g.n.unique()); ax[0].plot(ns, [max(1, n / 4) for n in ns], "k--", lw=1, label="ideal (N/4 vCPUs)")
ax[1].plot(ns, [min(n, 4) for n in ns], "k--", lw=1, label="ideal (min(N,4))")
for a in ax: a.set_xscale("log", base=2); a.set_xlabel("N concurrent copies of the tool command"); a.grid(alpha=.3)
ax[0].set_yscale("log", base=2); ax[0].set_ylabel("mean per-instance slowdown vs N=1"); ax[0].legend(fontsize=8)
ax[1].set_ylabel("aggregate throughput (× N=1)"); fig.suptitle("Sandbox density on a 4-vCPU Firecracker VM: concurrent identical tool commands (mean of 3)")
fig.tight_layout(); fig.savefig(f"{AT}/figs/density.png", dpi=140)
print("\n".join(L))
