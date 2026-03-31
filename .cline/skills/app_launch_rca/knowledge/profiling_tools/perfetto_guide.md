---
id: PT-001
title: Perfetto Trace & Profiling Guide
category: profiling_tools
tags: [trace, perfetto, SQL, TraceProcessor, slices, counters]
sources:
  - https://perfetto.dev/docs
  - https://source.android.com/devices/architecture/tracing
last_updated: 2026-03-26
---

# Perfetto Trace & Profiling Guide

## Overview
Perfetto is Android’s unified tracing system. It records **system-wide events** (CPU scheduling, binder IPC, memory allocations, etc.) into a binary trace file (`*.trace`). The trace can be queried with **TraceProcessor** using SQL‑like syntax, enabling powerful analysis of performance data.

## Key Concepts
- **Slices** – Represent a duration of an activity (e.g., a method call, a scheduling slice). Each slice has a `ts` (timestamp) and `dur` (duration).
- **Counters** – Time‑series values (e.g., CPU frequency, memory usage) stored as `value` at a given `ts`.
- **Tracks** – Logical grouping of slices/counters (e.g., `android.os.Binder`, `sched`, `gfx`).
- **TraceProcessor** – A fast, in‑process SQL engine that can query `.trace` files directly.

## Typical Workflow
1. **Capture** – `adb shell perfetto -c <config> -o /data/misc/perfetto-traces/trace.trace`
2. **Pull** – `adb pull /data/misc/perfetto-traces/trace.trace` to the host.
3. **Query** – `trace_processor --run <trace.trace> "SELECT ..."`
4. **Visualize** – Use the Perfetto UI (`perfetto.dev`) to explore slices and counters.

## Mapping to Project Metrics
| Metric | Perfetto Source | Typical Query Example |
|--------|----------------|-----------------------|
| `Running` / `Runnable` / `Sleeping` | `sched` track slices (`state = 'R'`, `'S'`, `'D'`) | `SELECT SUM(dur) FROM sched WHERE state='R' AND utid=...;` |
| `binder_transaction.count` | `android.os.Binder` track | `SELECT COUNT(*) FROM android_os_binder WHERE transaction_id IS NOT NULL;` |
| `frequency_by_cycle` | `cpu_freq` counter | `SELECT ts, value FROM cpu_freq WHERE cpu=0;` |
| `priority_by_cycle` | `sched` slice `nice` field | `SELECT ts, nice FROM sched WHERE utid=...;` |
| `MemFree_MB`, `MemAvailable_MB` | `meminfo` counters | `SELECT ts, value FROM meminfo WHERE name='MemFree';` |
| `Pageboostd_MB` | Custom instrumentation or `android.os.PageBoost` events | `SELECT ts, value FROM pageboost;` |

## Practical Tips for the Agent
- **Identify the right utid** – Use `SELECT utid FROM thread WHERE name='<process>'` to isolate a specific app.
- **Correlate slices** – Join `binder` slices with `sched` slices to see how IPC affects CPU state.
- **Detect spikes** – Query for `MAX(dur)` of `sched` slices to find long‑running tasks.
- **Export to CSV** – `trace_processor --run <trace> "SELECT ..." > out.csv` for further analysis.

## Suggested Actions When Anomalies Appear
- If `Running` time spikes, look for long `sched` slices with high `cpu` usage.
- If `binder_transaction.count` is high, drill down into `android_os_binder` slices to see which services are called.
- For memory pressure, query `meminfo` counters and correlate with `sched` `D` state slices.

---

*For deeper details, see the linked Perfetto documentation.*
