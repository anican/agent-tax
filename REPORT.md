# Where do agent sandbox cycles go? — Report

Exploratory "datacenter tax" characterization of coding-agent sandbox
workloads, modeled on Accelerometer (Sriraman & Dhanotia, ASPLOS '20).

## Pre-registered hypotheses

Recorded on 2026-11-03, **before any data was collected**. These are not
revised afterwards; the verdicts are in the Results section.

- **H1:** Most episode wall-clock time is model/loop time, not tool execution.
- **H2:** Context switching and threading are significant CPU-time categories.
- **H3:** Memory movement (memcpy/memmove) is a significant CPU-time category.
- **H4:** Process lifecycle (fork/exec, dynamic linking, page faults, Python
  startup/imports) is a significant CPU-time category.

Operationalization (also fixed before data collection):
- "Most" (H1) = more than 50% of the summed episode wall-clock time across
  tasks, and in the majority of individual tasks.
- "Significant" (H2–H4) = at least 5% of the command's sampled on-CPU time,
  aggregated across all replayed commands, or at least 10% in at least one
  command class. "On-CPU time" here means **timer-based on-CPU samples**
  (`cpu-clock` at 999 Hz), not cycles.

_Results follow below once collected._
