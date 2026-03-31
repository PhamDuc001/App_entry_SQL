---
id: OS-002
title: Android Memory Management & LMK
category: os_internals
tags: [MemFree, MemAvailable, PSS, LMK, swap]
sources:
  - https://source.android.com/devices/architecture/memory
  - https://www.kernel.org/doc/html/latest/mm/lowmemorykiller.html
last_updated: 2026-03-26
---

# Android Memory Management & LMK

## Overview
Android devices use a combination of Linux kernel memory management and Android‑specific low‑memory‑killer (LMK) policies. The kernel tracks **free pages** (`MemFree`) and **available memory** (`MemAvailable`). Android adds a **PSS (Proportional Set Size)** metric for per‑process memory usage and an LMK daemon that kills background processes when memory becomes scarce.

## Key Concepts
- **MemFree** – Physical pages not allocated to any process.
- **MemAvailable** – Estimate of memory that can be allocated without swapping, taking into account reclaimable caches.
- **PSS** – Provides a more accurate per‑process memory usage by accounting for shared pages proportionally.
- **LMK (Low‑Memory Killer)** – Configurable thresholds that trigger process termination when free memory drops below certain levels.
- **Swap** – Rare on Android, but when present it can mask low‑memory symptoms.

## Relation to Performance Metrics
- A drop in `MemFree` or `MemAvailable` > 50 MB compared to REF often indicates **memory pressure**.
- An increase in `App_PSS_MB` for a specific app signals that the app is holding onto more memory (e.g., leaks, large caches).
- LMK activity can be inferred from sudden drops in memory metrics and corresponding `kill` events in the trace.

## Practical Checks
1. **Memory drop detection** – Compare `MemFree`/`MemAvailable` between DUT and REF.
2. **PSS increase** – Flag when `App_PSS_MB` rises > 50 MB.
3. **LMK evidence** – Look for `lowmemorykiller` logs or `kill` events in the trace.

## Suggested Actions for the Agent
- When memory metrics exceed thresholds, recommend:
  - Review app memory usage patterns (caches, bitmaps).
  - Check for LMK‑triggered kills in the trace.
  - Verify whether swap is enabled (should be disabled on most devices).

---

*For deeper reading, see the linked sources.*
