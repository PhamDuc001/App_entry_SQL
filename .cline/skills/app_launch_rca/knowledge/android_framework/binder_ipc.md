---
id: AF-002
title: Android Binder IPC Mechanism
category: android_framework
tags: [binder, IPC, transaction, sync, async]
sources:
  - https://source.android.com/devices/architecture/binder
  - https://developer.android.com/guide/components/bound-services
last_updated: 2026-03-26
---

# Android Binder IPC Mechanism

## Overview
Binder is Android’s primary **inter‑process communication (IPC)** mechanism. It allows processes to invoke methods on remote objects, pass data, and receive callbacks. Binder works via a kernel driver that manages **transactions** between a client and a service.

## Key Concepts
- **Binder driver** – kernel component that queues and routes transactions.
- **Transaction** – a request from a client to a service, identified by a transaction code.
- **Sync vs Async** – Synchronous calls block the client until the service replies; asynchronous calls return immediately and use a callback.
- **Thread pool** – Services typically have a thread pool that processes incoming Binder calls.
- **Binder buffers** – Fixed‑size buffers (typically 1 MB) that hold marshalled data; overflow can cause `TRANSACTION_FAILED` errors.

## Relation to Performance Metrics
- `binder_transaction.count` in our JSON reflects the number of Binder calls made during the trace.
- A spike in this count (threshold > 10) often indicates **excessive IPC**, which can increase `Sleeping` time as the app waits for remote services.
- High `Sleeping` combined with many Binder calls may point to **contention on the Binder thread pool** or inefficient service design.

## Practical Checks
1. Compare `binder_transaction.count` between DUT and REF.
2. If increased, inspect the trace for `binder` events to identify which services are involved.
3. Look for long‑running transactions (`duration` field) that could block the UI thread.

## Suggested Actions for the Agent
- Recommend profiling the offending service (e.g., using `adb shell dumpsys activity services`).
- Suggest reducing cross‑process calls or batching data.
- If Binder buffer overflow is suspected, advise increasing the buffer size via system properties.

---

*Further reading in the linked sources.*
