---
id: AF-001
title: Android App Launch Internals
category: android_framework
tags: [Cold, Warm, Hot, Zygote, bindApplication, activityStart]
sources:
  - https://source.android.com/devices/architecture/app-launch
  - https://developer.android.com/topic/performance/vitals/launch-time
last_updated: 2026-03-26
---

# Android App Launch Internals

## Overview
App launch on Android proceeds through three main phases:
1. **Cold launch** – Process does not exist; the system starts a new Zygote fork, loads the APK, and creates the app process.
2. **Warm launch** – Process exists but has been killed; the system reuses the existing process, skipping heavy initialization.
3. **Hot launch** – Process is already running; only activity start is needed.

## Key Steps
- **Zygote fork** – The Zygote process forks a new process, inheriting a pre‑loaded runtime and shared libraries.
- **bindApplication** – The system binds the application to the new process, loading resources and initializing the `Application` object.
- **Activity lifecycle** – `activityStart` and subsequent callbacks (`onCreate`, `onStart`, `onResume`).

## Relation to Performance Metrics
- `sequence["Touch Down ~ Start Proc"]` captures the latency from user interaction to process start.
- `State` array (`Cold`, `Warm`, `Hot`) indicates which launch type occurred.
- High `Running` or `Runnable` times often stem from heavy initialization in the **Cold** phase.

## Practical Checks
1. Compare `State` between DUT and REF – a shift from `Cold` to `Warm` reduces launch time.
2. Examine `Touch Down ~ Start Proc` – large differences (>10 ms) point to Zygote or bindApplication delays.
3. Look at `binder_transaction` counts – excessive binder calls during launch can indicate inefficient IPC.

## Suggested Actions for the Agent
- When a Cold launch shows high latency, recommend profiling Zygote fork and `bindApplication` steps.
- Suggest optimizing resource loading (e.g., lazy init, reducing static initializers).
- If binder transactions are high, advise reviewing IPC usage during launch.

---

*Further reading in the linked sources.*
