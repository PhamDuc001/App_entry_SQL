---
id: OS-001
title: Linux CPU Scheduling & Priority
category: os_internals
tags: [Runnable, priority, CFS, nice, cgroups]
sources:
  - https://www.kernel.org/doc/html/latest/scheduler/sched-design-CFS.html
  - https://source.android.com/devices/architecture/scheduling
last_updated: 2026-03-26
---

# Linux CPU Scheduling & Priority

## Overview
Linux uses the **Completely Fair Scheduler (CFS)** as its default scheduler. Each task gets a *virtual runtime* that represents the amount of CPU time it has received. The scheduler aims to keep the virtual runtimes of all runnable tasks as equal as possible.

## Key Concepts
- **Nice value**: Ranges from -20 (high priority) to +19 (low priority). A lower nice means the task receives more CPU share.
- **CFS weight**: Internally derived from the nice value; higher weight → more CPU.
- **cgroups**: Allow grouping tasks and assigning a *share* of CPU cycles, useful for isolating app processes.
- **Runnable time**: Sum of time a task spends in the *R* state (ready to run). Sudden spikes often indicate contention or priority inversion.

## Relation to Performance Metrics
- **`Runnable` metric** in our JSON reflects the total runnable time across all cycles. A large increase can be caused by:
  1. **Priority changes** (nice adjusted by the app or system).
  2. **cgroup limits** being hit (e.g., background apps throttled).
  3. **CPU starvation** due to high‑priority foreground tasks.
- **`priority_by_cycle`** data in the trace shows the distribution of *nice* values per cycle. When the high‑priority percentage drops, the scheduler may be giving more CPU to lower‑priority tasks, leading to longer runnable times.

## Practical Example
If `Runnable` rises by >50 ms compared to REF and the `priority_by_cycle` shows a drop of >15 % in high‑priority slices, the likely cause is a **priority shift** (e.g., an app moved to background). The AI should suggest:
- Verify the app’s process state (foreground/background).
- Check cgroup allocations for the app.
- Look for recent `nice` adjustments in the trace.

---

*This article is a concise reference for the AI agent; deeper details can be found in the linked sources.*
