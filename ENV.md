# ENV.md — measurement environment

Collected 2026-11-03 at the start of the study.

| Item | Value |
|---|---|
| Platform | claude.ai cloud session (Claude Code remote container) |
| Virtualization | KVM guest (`Hypervisor detected: KVM`); kernel command line contains `--firecracker-init`, i.e. a **Firecracker microVM** |
| CPU model | `Intel(R) Xeon(R) Processor @ 2.80GHz` (generic name exposed by the hypervisor; microcode reported as `0x1`) |
| vCPUs | 4 (1 thread/core, 4 cores, 1 socket, 1 NUMA node) |
| Caches (as reported to guest) | L1d 128 KiB total (4×32 KiB), L2 4 MiB total, L3 33 MiB shared |
| ISA features of note | `hypervisor`, `avx2`, `avx512f` flags present |
| Memory | 16,477,348 kB (~15.7 GiB) MemTotal; **no swap** |
| Disk | `/dev/vda` ext4, 256 GB device but a per-session writable allowance of ~30 GB (`df` Avail ≈ 32.1 GB at start, 9.2 GB used) |
| Kernel | `Linux 6.18.44-fc-v230 #1 SMP PREEMPT_DYNAMIC x86_64` |
| Clocksource | `tsc` (kvm-clock also registered) |
| OS userspace | Ubuntu 24.04.5 LTS |
| Running as root | **yes** (`uid=0(root)`) |
| `/proc/sys/kernel/kptr_restrict` | `0` |
| `/proc/sys/kernel/perf_event_paranoid` | `2` (irrelevant as root) |
| `/proc/sys/kernel/nmi_watchdog` | `0` |
| Transparent huge pages | `madvise` |
| cgroups | v1 hierarchy (memory cgroup per Bash tool invocation) |
| perf | `/usr/bin/perf` is a broken Ubuntu wrapper (no tools for kernel `6.18.44-fc`). The study uses `/usr/lib/linux-tools/6.8.0-147-generic/perf` (perf 6.8.12) directly; set as `$PERF` in `tools/env.sh`. |
| PMUs visible to perf | `breakpoint msr power software tracepoint uprobe` — **no `cpu` PMU** |
| valgrind | 3.22.0 (works) |
| Pythons | `/usr/bin/python3.11` (3.11.x, frame pointers on — used for task venvs), `/usr/bin/python3.12` (no frame pointers), `/usr/local/bin/python3` 3.13.18 (used only for analysis scripts) |
| Compilers | gcc/g++ (Ubuntu 24.04), cmake, ninja; no gfortran |

## Kernel symbol resolution check

`$PERF record -e cpu-clock -F 999 -a -g -- sh -c 'for i in $(seq 200); do ls -R /usr/lib/python3* >/dev/null; done'`
captured 5,327 samples, and `perf report` resolved kernel symbols with full
call chains (e.g. `__d_lookup_rcu ← lookup_fast ← open_last_lookups ←
path_openat ← do_filp_open ← do_sys_openat2 ← __x64_sys_openat`; idle time
appears as `pv_native_safe_halt ← arch_cpu_idle ← … ← start_kernel`).
`/proc/kallsyms` is readable with real addresses (129,930 symbols).
**Result: kernel symbols resolve**, so kernel-side attribution (process
lifecycle, page faults, filesystem metadata, scheduling) is possible.
Note the perf userspace tool (6.8) is older than the kernel (6.18); no
problems were observed from the mismatch in this check.

## What is NOT available

- **No hardware performance counters.** The guest exposes no `cpu` PMU, so
  `cycles`, `instructions`, IPC, cache-miss, branch-miss, TLB and
  front-end/back-end stall data are **unavailable** in this environment.
  (`perf stat -e cycles` reports `<not supported>`.)
- Consequently all CPU-view profiles use the `cpu-clock` software event:
  **timer-based sampling of on-CPU time**, not cycle sampling. A sample says
  "this function was running on a CPU when the timer fired"; it says nothing
  about how efficiently it ran.
- Steal time and hypervisor (host-side) work are invisible to in-guest
  sampling except through the `steal` column of `/proc/stat`.
