---
id: OS-003
title: Block I/O, D-state & Page Cache
category: os_internals
tags: [D-state, Uninterruptible Sleep, block_io, pagecache, readahead]
sources:
  - https://www.kernel.org/doc/html/latest/block/index.html
  - https://source.android.com/devices/architecture/storage
last_updated: 2026-03-26
---

# Block I/O, D-state & Page Cache

## Overview
`D-state` (Uninterruptible Sleep) appears when a task is waiting for a **blocking I/O operation** to complete. The kernel places the task in a *wait queue* until the I/O finishes. The **page cache** stores recently accessed disk blocks in RAM to reduce I/O latency; `readahead` pre‑fetches data before it is requested.

## Key Concepts
- **D-state** – Task cannot be scheduled until the I/O completes; high values often indicate storage bottlenecks or contention.
- **Block I/O path** – From the VFS layer down to the block driver; latency can be measured per request.
- **Page cache** – Cached pages that can satisfy reads without hitting the storage device.
- **Readahead** – Proactive fetching of sequential blocks; mis‑configured readahead can increase D-state.

## Relation to Performance Metrics
- `Uninterruptible Sleep` metric in our JSON reflects total time spent in D-state across all apps.
- A spike > 30 ms (threshold) suggests **slow storage** or **excessive page faults**.
- `Pageboostd_MB` (prefetch amount) decreasing can be a symptom of reduced readahead.

## Practical Checks
1. Compare `Uninterruptible Sleep` between DUT and REF.
2. If increased, look at `block_io_by_cycle` to identify which libraries/files cause the I/O.
3. Examine `Pageboostd_MB` – a drop may indicate disabled or throttled prefetch.

## Suggested Actions for the Agent
- Recommend checking storage health (e.g., `iostat`, `blkid`).
- Suggest enabling/disabling readahead heuristics.
- Correlate high D-state with specific app I/O patterns from the trace.

---

*Further reading in the linked sources.*
