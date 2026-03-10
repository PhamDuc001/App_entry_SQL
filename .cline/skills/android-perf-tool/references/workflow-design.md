# Workflow Design Guide — Diagnostic JSON Workflows

## Execution Model

All three Flow JSONs share the same execution model: **`exhaustive_sequential`**.

- Agent executes **all branches** from every `check_group`, regardless of results
- No short-circuit — a failed check does not block sibling checks
- `result` and `database_query` nodes at the same `on_true.next` array run **in parallel**
- All findings are collected and presented together at the end

---

## Node Type Reference

### `check_group`
Fan-out hub. Always runs all children. No condition logic.

```json
"node_XX_my_group": {
  "type": "check_group",
  "description": "Purpose of this group",
  "next": ["node_A", "node_B", "node_C"]
}
```
- `next` must be an array (never a string)
- Can be nested: a `check` can point to another `check_group`

---

### `check`
Single binary condition. Fires `on_true` if operator evaluates true.

```json
"node_XX": {
  "type": "check",
  "source": ["DUT", "REF"],
  "keys": ["metric_key"],
  "threshold": 50,
  "operator": "DUT.metric_key - REF.metric_key > threshold",
  "on_true": { "next": "node_YY" }
}
```

`on_true.next` may be a string (single node) or an array (parallel nodes).

**Operator patterns:**
```
"DUT.metric - REF.metric > threshold"            simple diff threshold
"REF.metric - DUT.metric > threshold"            reversed diff (memory/pageboost)
"exists"                                          key presence check
"DUT.State == 'COLD' AND REF.State == 'WARM'"    state comparison
"## Analysis Rules: ..."                          analytical instruction for AI
"For each cycle, if process.diff > threshold..."  per-cycle accumulation loop
```

**source field:** Always declare `["DUT", "REF"]` for comparative checks.
Use `"DUT"` (string, not array) when checking DUT alone (e.g. top_process, parallel_process).

---

### `comparison`
Diff check. Fires `on_diff` when values differ beyond threshold.

```json
"node_XX": {
  "type": "comparison",
  "source": ["DUT", "REF"],
  "keys": ["metric_key"],
  "threshold": 10,
  "operator": "DUT.metric_key - REF.metric_key > threshold",
  "on_diff": { "next": "node_YY" }
}
```

Use `comparison` (not `check`) when the semantic is "values differ" rather than "value exceeds limit".

---

### `custom_check`
Complex multi-condition logic. All `additional_condition_N` are ANDed with `condition`.

```json
"node_XX": {
  "type": "custom_check",
  "description": "What this detects",
  "logic": {
    "source": ["DUT", "REF"],
    "keys": ["key1", "key2"],
    "condition": "primary condition",
    "additional_condition_1": "AND this",
    "additional_condition_2": "AND this"
  },
  "on_true": { "next": "node_YY" }
}
```

---

### `result`
Terminal node. **Never has a `next` field.**

```json
"node_XX": {
  "type": "result",
  "problem": "Description {DUT.metric - REF.metric} ms",
  "suggestion": "Suggest <team> check <issue>"
}
```

Interpolation: `{DUT.key}`, `{REF.key}`, `{DUT.key - REF.key}`, `{cycle}`, `{process_name}`, `{diff}`

---

### `database_query`
Async history lookup. Non-blocking. Usually paired with a sibling `result` node.

```json
"node_XX": {
  "type": "database_query",
  "query": "Check history about <topic>",
  "params": ["app", "version"]
}
```

Valid params: `"app"`, `"version"`, `"model"`, `"process_name"`, `"apk"`

**Pairing pattern:**
```json
"on_true": { "next": ["node_XX_result", "node_YY_query"] }
```

> ⚠ Some `database_query` nodes run independently (not paired with a result):
> - `node_14_query_running_version` in Flow 2 — runs in the `running_sub_issues` group regardless of compiler/frequency findings
> - `node_23_query_sleeping` in Flow 2 — runs in `sleeping_sub_issues` group regardless of binder finding
> These are "ambient" queries that always fetch history context when the parent check triggers.

---

## Naming Conventions

```
node_00_*        check_group root
node_01–09       primary checks
node_10+         sub-checks, result nodes, query nodes
*_check          condition node
*_issue / *_found / *_condition    result node
*_query_*        database_query node
*_sub / *_sub_issues               intermediate check_group
```

Node IDs must be unique across the entire flow file.

---

## Flow Structure Template

```json
{
  "workflow_name": "Android App Performance Root Diagnostic - Flow N: <Topic>",
  "execution_mode": "exhaustive_sequential",
  "nodes": {
    "node_00_check": {
      "type": "check_group",
      "description": "<Topic> Analysis",
      "next": ["node_01_first_check", "node_02_second_check"]
    },
    "node_01_first_check": {
      "type": "check",
      "source": ["DUT", "REF"],
      "keys": ["metric"],
      "threshold": 50,
      "operator": "DUT.metric - REF.metric > threshold",
      "on_true": {
        "next": ["node_10_issue", "node_11_query"]
      }
    },
    "node_10_issue": {
      "type": "result",
      "problem": "Issue found: {DUT.metric - REF.metric} ms",
      "suggestion": "Suggest <team> check <issue>"
    },
    "node_11_query": {
      "type": "database_query",
      "query": "Check history for <topic>",
      "params": ["app", "version"]
    }
  }
}
```

---

## Design Rules

**DO:**
- Pair every `result` with a sibling `database_query` (unless it is an ambient standalone query)
- Use `check_group` to fan out related checks — never chain checks directly
- One problem per `result` node
- Match JSON keys exactly to `export_avg_to_json()` output (see Mapping table below)

**DON'T:**
- Add `next` to `result` nodes
- Reuse node IDs across the flow
- Hardcode absolute thresholds — all metrics use DUT−REF or REF−DUT diff
- Skip `source` field — always declare `["DUT", "REF"]` or `"DUT"` explicitly

---

## Diagnostic Flow Map

### Flow 1 — Initial Validation

```
node_00 (check_group)
├── node_01_uptime_check
│     uptime > 10 min (DUT or REF)
│     → node_04 [result] Suggest re-test DUT or REF to correct test condition
│
├── node_02_anr_fatal_check
│     ANR or FATAL exists
│     → node_05 [result] Suggest check FATAL/ANR
│     → node_06 [db_query] params: [app]
│
└── node_03_touch_duration_check  (comparison)
      DUT.touch_duration - REF.touch_duration > 10ms
      → node_07 [result] Suggest system team for noticing this problem
```

### Flow 2 — Core Performance State

```
node_00 (check_group)
├── node_01_running_check
│     DUT.Running - REF.Running > 50ms
│     → node_05 [result] Suggest app team checking running time increase from app side
│     → node_06 (check_group — runs IN PARALLEL with node_05)
│           ├── node_10_compiler_check  (custom_check)
│           │     DUT.compiler == "verify" AND DUT.compiler != REF.compiler
│           │     → node_15 [result] Suggest App TG apply speed-profile
│           ├── node_12_frequency_check
│           │     DUT high-freq % < REF high-freq % by >15% (analytical, per-cycle)
│           │     sections: bindApplication, activityStart, activityResume, Choreographer
│           │     → node_17 [result] Suggest system team check frequency problem
│           └── node_14 [db_query] params: [app, version]  ← ambient query, always runs
│
├── node_02_sleeping_check
│     DUT.Sleeping - REF.Sleeping > 50ms
│     → node_07 (check_group — NO direct result for Sleeping itself)
│           ├── node_19_binder_check
│           │     DUT.binder.count - REF.binder.count > 10
│           │     → node_24 [result] Suggest App team check binder increase
│           └── node_23 [db_query] params: [app, version]  ← ambient query
│
├── node_03_runnable_check
│     DUT.Runnable - REF.Runnable > 50ms
│     → node_08_priority_check  (direct check, no group)
│           DUT high-priority % < REF high-priority % by >15% (analytical, per-cycle)
│           note: high value = low priority (scale inverted)
│           sections: bindApplication, activityStart, activityResume, Choreographer
│           → node_34 [result] Suggest system team check scheduling priority
│
└── node_04_start_state_check
      DUT.State == "COLD" AND REF.State == "WARM"
      → node_09 (check_group)
            ├── node_35_beks_check  (comparison)
            │     beks differs between DUT and REF
            │     → node_38 [result] Suggest System team check BEKS config
            ├── node_36_start_kill_check  (custom_check — 3 conditions ALL must be true)
            │     cond:   DUT.start_reason.length != REF.start_reason.length
            │             OR DUT.kill_reason.length != REF.kill_reason.length
            │     cond_1: DUT.start_reason.length != 0 AND REF.start_reason.length != 0
            │     cond_2: DUT.start_reason.length - DUT.kill_reason.length == 0
            │     → node_39 [result] Suggest App team check start/kill issue
            │     ⚠ JSON export uses start_reasons/kill_reasons (plural list);
            │       workflow file has start_reason/kill_reason (singular) — known typo
            └── node_37 [db_query] params: [app, version]  ← ambient query
```

### Flow 3 — Resource Usage and Process Analysis

```
node_00 (check_group)
├── node_01_load_apk_asset_check
│     DUT.loadApkAssets - REF.loadApkAssets > 30ms
│     → node_07_memory_check_detailed  (direct — only memory check, NOT apk/pageboost)
│           REF.MemFree_MB - DUT.MemFree_MB > 50 OR REF.MemAvailable_MB - DUT.MemAvailable_MB > 50
│           → node_13 [result] Suggest Kernel Memory team check mem free, mem available issue
│           → node_14 [db_query] params: [model, app]
│
├── node_02_block_io_check
│     DUT."Uninterruptible Sleep" - REF."Uninterruptible Sleep" > 30ms
│     → node_06 (check_group — triggers ALL three sub-checks)
│           ├── node_07_memory_check_detailed  (same node as above, may be triggered twice)
│           │     → node_13 [result] Suggest Kernel Memory team check mem free, mem available issue
│           │     → node_14 [db_query] params: [model, app]
│           ├── node_08_apk_size_check
│           │     apk_size exists
│           │     → node_15 [result] Suggest app team optimize size
│           │     → node_16 [db_query] params: [app, version]
│           └── node_11_pageboost_check
│                 REF.Pageboostd_MB - DUT.Pageboostd_MB > 10MB
│                 → node_21 [result] Suggest Kernel Memory team check pageboost operation
│
└── node_03_process_abnormal (check_group)
      ├── node_23_parallel_process_check  (custom_check — DUT only)
      │     DUT.start_process_abnormal has any process_name
      │     on_true passes: {process_name}
      │     → node_26 [result] Suggest App team and SWPL investigate
      │     → node_27 [db_query] params: [model, process_name]
      ├── node_24_top_cpu_check  (DUT only, per-cycle loop)
      │     for each cycle: if process.diff > 300ms → accumulate {cycle, process_name, diff}
      │     after all cycles checked → on_true passes: [cycle, process_name, diff]
      │     → node_28 [result] Suggest SWPL check with owner of process
      │     → node_29 [db_query] params: [model, process_name]
      └── node_25_pss_check
            DUT.App_PSS_MB - REF.App_PSS_MB > 50MB
            → node_30 [result] Suggest app owner to debug PSS increase issue
            → node_31 [db_query] params: [app]
```

---

## Mapping: Workflow Keys → JSON Export Keys

### Flow 1 — Initial Validation

| Workflow key | JSON export path | Direction | Threshold | Suggestion |
|-------------|-----------------|-----------|-----------|------------|
| `uptime_minutes` | `entry.extend.abnormal.uptime_minutes` | DUT or REF > limit | 10 min | `"Suggest re-test DUT or REF to correct test condition"` |
| `ANR`, `FATAL` | `entry.extend.abnormal.crash_count_avg` | exists | — | `"Suggest check FATAL/ANR"` |
| `touch_duration` | `entry.sequence["Touch Duration"]` | DUT − REF | 10 ms | `"Suggest system team for noticing this problem"` |

### Flow 2 — Core Performance State

| Workflow key | JSON export path | Direction | Threshold | Suggestion |
|-------------|-----------------|-----------|-----------|------------|
| `Running` | `entry.sequence["Running"]` | DUT − REF | 50 ms | `"Suggest app team checking running time increase from app side"` |
| `compiler` | `entry.extend.abnormal.compiler` | DUT=="verify" AND DUT!=REF | — | `"Suggest App TG apply speed-profile"` |
| `frequency_by_cycle` | `entry.frequency_by_cycle` | DUT%<REF% per section | 15 % | `"Suggest system team check frequency problem"` |
| `Sleeping` | `entry.sequence["Sleeping"]` | DUT − REF | 50 ms | → triggers binder sub-group |
| `binder` (count) | `entry.binder_transaction.count` | DUT − REF | 10 count | `"Suggest App team check binder increase"` |
| `Runnable` | `entry.sequence["Runnable"]` | DUT − REF | 50 ms | → triggers priority check |
| `priority_by_cycle` | `entry.priority_by_cycle` | DUT%<REF% per section | 15 % | `"Suggest system team check scheduling priority"` |
| `State` | `entry.State` | DUT==COLD AND REF==WARM | — | → triggers start state sub-group |
| `beks` | *(not yet exported)* | comparison diff | — | `"Suggest System team check BEKS config"` |
| `start_reasons` | `entry.extend.abnormal.start_reasons` | count diff + balance check | — | `"Suggest App team check start/kill issue"` |
| `kill_reasons` | `entry.extend.abnormal.kill_reasons` | count diff + balance check | — | `"Suggest App team check start/kill issue"` |

### Flow 3 — Resource Usage and Process Analysis

| Workflow key | JSON export path | Direction | Threshold | Suggestion |
|-------------|-----------------|-----------|-----------|------------|
| `loadApkAssets` | `entry.extend.loadapkassets` | DUT − REF | 30 ms | → triggers memory check only |
| `Uninterruptible Sleep` | `entry.sequence["Uninterruptible Sleep"]` | DUT − REF | 30 ms | → triggers memory + apk + pageboost group |
| `MemFree_MB` | `entry.extend.memory.MemFree_MB` | **REF − DUT** | 50 MB | `"Suggest Kernel Memory team check mem free, mem available issue"` |
| `MemAvailable_MB` | `entry.extend.memory.MemAvailable_MB` | **REF − DUT** | 50 MB | `"Suggest Kernel Memory team check mem free, mem available issue"` |
| `apk_size` | *(not yet exported)* | exists | — | `"Suggest app team optimize size"` |
| `Pageboostd_MB` | `entry.extend.memory.Pageboostd_MB` | **REF − DUT** | 10 MB | `"Suggest Kernel Memory team check pageboost operation"` |
| `start_process_abnormal` | `entry.extend.start_process_abnormal` | DUT has any process_name | — | `"Suggest App team and SWPL investigate"` |
| `top_process_consume_by_cycle` | `entry.top_process_consume_by_cycle` | per-process DUT diff | 300 ms | `"Suggest SWPL check with owner of process"` |
| `App_PSS_MB` | `entry.extend.memory.App_PSS_MB` | DUT − REF | 50 MB | `"Suggest app owner to debug PSS increase issue"` |

> ⚠ `MemFree_MB`, `MemAvailable_MB`, `Pageboostd_MB` use **REF − DUT**.
> Positive result = DUT has less free memory / pageboost than REF → DUT is worse.

> ⚠ `top_process` loop: check each cycle independently. Each process with `diff > 300ms`
> produces one finding: `{cycle, process_name, diff}`. Do not aggregate before checking.

> ⚠ `apk_size` and `beks` are not yet exported by `export_avg_to_json()`. Add extraction
> in `dumpstate_parser.py` and export in `calculate_metrics_for_app()` to enable these nodes.

---

## Team Routing — Quick Reference

| Issue | Exact suggestion phrase |
|-------|------------------------|
| Test condition (uptime) | `"Suggest re-test DUT or REF to correct test condition"` |
| ANR / FATAL | `"Suggest check FATAL/ANR"` |
| Touch duration | `"Suggest system team for noticing this problem"` |
| Running time increase | `"Suggest app team checking running time increase from app side"` |
| Compiler verify | `"Suggest App TG apply speed-profile"` |
| CPU frequency low | `"Suggest system team check frequency problem"` |
| Binder count increase | `"Suggest App team check binder increase"` |
| Thread priority low | `"Suggest system team check scheduling priority"` |
| BEKS mismatch | `"Suggest System team check BEKS config"` |
| Start/kill count diff | `"Suggest App team check start/kill issue"` |
| MemFree / MemAvailable low | `"Suggest Kernel Memory team check mem free, mem available issue"` |
| APK size increase | `"Suggest app team optimize size"` |
| Pageboost decrease | `"Suggest Kernel Memory team check pageboost operation"` |
| Parallel process detected | `"Suggest App team and SWPL investigate"` |
| Top CPU process high | `"Suggest SWPL check with owner of process"` |
| PSS increase | `"Suggest app owner to debug PSS increase issue"` |

---

## Reviewing Existing Workflow Logic

1. **Coverage** — Does each metric group (CPU, memory, I/O, process) have a check?
2. **Threshold + unit** — ms for time, MB for memory, count for binder, % for frequency/priority, min for uptime
3. **Direction** — `MemFree`, `MemAvailable`, `Pageboostd_MB` use REF−DUT; all others use DUT−REF
4. **Chain logic** — Does `Running` emit a result AND trigger a sub-group? Does `Sleeping` skip the direct result? Does `Runnable` go straight to a single check (not a group)?
5. **Custom conditions** — `compiler_check` needs 2 conditions; `start_kill_check` needs all 3 AND'd
6. **Team routing** — Suggestion phrase matches Team Routing table exactly
7. **History coverage** — Every `result` has a sibling `database_query` (except ambient queries)
8. **Node existence** — All nodes referenced in `next` arrays exist in the file
