# Workflow Design Guide — Diagnostic JSON Workflows

## Execution Model

All three Flow JSONs share the same execution model: **`exhaustive_sequential`**.

This means:
- The AI agent executes **all branches** from every `check_group`, regardless of results
- There is **no short-circuit** — a failed check does not block sibling checks
- `result` nodes and `database_query` nodes at the same level run **in parallel**
- The agent collects all findings and presents them together

**Implication for design:** Never assume a child node will only run if its parent's condition
is true. Every `check_group` child is always visited. Use `check_group` to fan out, not to gate.

---

## Node Type Reference

### `check_group`
Fan-out hub. Always runs all children. No condition.

```json
"node_XX_my_group": {
  "type": "check_group",
  "description": "Human-readable purpose of this group",
  "next": [
    "node_A_first_check",
    "node_B_second_check",
    "node_C_third_check"
  ]
}
```

**Rules:**
- `next` must be an array (never a string)
- `description` is optional but strongly recommended
- Can be nested: a check can lead to another check_group

---

### `check`
Single binary condition. If `operator` evaluates true → go to `on_true.next`.

```json
"node_XX_my_check": {
  "type": "check",
  "source": ["DUT", "REF"],
  "keys": ["metric_key"],
  "threshold": 50,
  "operator": "DUT.metric_key - REF.metric_key > threshold",
  "on_true": {
    "next": "node_YY_result_node"
  }
}
```

**`on_true.next`** can be:
- A string → single node
- An array → multiple nodes run in parallel (use when pairing `result` + `database_query`)

**Operator patterns:**
```
# Simple threshold diff
"DUT.metric - REF.metric > threshold"

# Existence check
"exists"  (checks if keys are present in data)

# State comparison
"DUT.State == 'COLD' AND REF.State == 'WARM'"

# Complex analytical operator (free-form prompt for AI)
"## Analysis Rules: Focus on highest frequency..."
```

When the operator is a long string with `##` headers and backticks, the AI agent interprets
it as an analytical instruction, not a literal expression. Use this for multi-dimensional
comparisons (frequency analysis, priority analysis) where a simple diff isn't sufficient.

---

### `comparison`
Diff-based check between DUT and REF. Fires `on_diff` when values differ beyond threshold.

```json
"node_XX_my_comparison": {
  "type": "comparison",
  "source": ["DUT", "REF"],
  "keys": ["metric_key"],
  "threshold": 10,
  "operator": "DUT.metric_key - REF.metric_key > threshold",
  "on_diff": {
    "next": "node_YY_issue_node"
  }
}
```

Use `comparison` (not `check`) when the semantic is "these two values are different" rather
than "this value exceeds a limit".

---

### `custom_check`
Complex multi-condition logic that doesn't fit simple threshold patterns.

```json
"node_XX_my_custom": {
  "type": "custom_check",
  "description": "What this check detects",
  "logic": {
    "source": ["DUT", "REF"],
    "keys": ["key1", "key2"],
    "condition": "DUT.key1.length != REF.key1.length OR DUT.key2.length != REF.key2.length",
    "additional_condition_1": "DUT.key1.length != 0 && REF.key1.length != 0",
    "additional_condition_2": "DUT.key1.length - DUT.key2.length == 0"
  },
  "on_true": {
    "next": "node_YY_result"
  }
}
```

All `additional_condition_N` fields are ANDed with `condition`. Number them sequentially.

---

### `result`
Terminal node. Reports a finding. **No `next` field ever.**

```json
"node_XX_my_issue": {
  "type": "result",
  "problem": "Description with interpolated values: {DUT.metric - REF.metric} ms",
  "suggestion": "Suggest <team> check <specific issue>"
}
```

**Interpolation syntax:** `{DUT.key}`, `{REF.key}`, `{DUT.key - REF.key}`, `{process_name}`

**Suggestion conventions:**
| Responsible team | Phrase to use |
|-----------------|---------------|
| App developer | "Suggest App team check ..." |
| System/kernel | "Suggest system team check ..." |
| Memory/kernel | "Suggest Kernel Memory team check ..." |
| App TG (compiler) | "Suggest App TG apply ..." |
| SWPL + App | "Suggest App team and SWPL investigate" |
| Re-test required | "Suggest re-test DUT or REF to correct test condition" |

---

### `database_query`
Async history lookup. Always paired with a sibling `result` node. Non-blocking.

```json
"node_XX_query_history": {
  "type": "database_query",
  "query": "Check history about <topic>",
  "params": ["param1", "param2"]
}
```

**Valid params:** `"app"`, `"version"`, `"model"`, `"process_name"`, `"apk"`

**Pattern:** Always pair with a result node under the same `on_true.next` array:
```json
"on_true": {
  "next": [
    "node_XX_result_node",      ← immediate finding
    "node_YY_query_history"     ← async context lookup
  ]
}
```

---

## Naming Conventions

```
node_00_entry_point        ← 00 = group entry (check_group root)
node_01_first_check        ← 01-09 = primary checks
node_04_retest_condition   ← result nodes get descriptive names
node_06_query_anr_history  ← query nodes prefixed with "query_"
node_10_compiler_check     ← 10+ = sub-checks branched from primary checks
node_15_compiler_verify    ← result nodes at deeper levels use higher numbers
```

**Rules:**
- Node IDs must be unique across the entire flow file
- Use `_check` suffix for condition nodes
- Use `_issue` / `_found` / `_condition` suffix for result nodes
- Use `_query_` infix for database_query nodes
- Use `_sub_issues` / `_sub` suffix for intermediate check_groups

---

## Flow Structure Template

Use this as a starting point for any new diagnostic flow:

```json
{
  "workflow_name": "Android App Performance Root Diagnostic - Flow N: <Topic>",
  "execution_mode": "exhaustive_sequential",
  "nodes": {

    "node_00_<topic>_check": {
      "type": "check_group",
      "description": "<Topic> Analysis",
      "next": [
        "node_01_<first_check>",
        "node_02_<second_check>"
      ]
    },

    "node_01_<first_check>": {
      "type": "check",
      "source": ["DUT", "REF"],
      "keys": ["<metric_key>"],
      "threshold": <value>,
      "operator": "DUT.<metric_key> - REF.<metric_key> > threshold",
      "on_true": {
        "next": [
          "node_10_<first_issue>",
          "node_11_query_<first_history>"
        ]
      }
    },

    "node_10_<first_issue>": {
      "type": "result",
      "problem": "<Issue description> {DUT.<metric> - REF.<metric>} ms",
      "suggestion": "Suggest <team> check <issue>"
    },

    "node_11_query_<first_history>": {
      "type": "database_query",
      "query": "Check history for <topic>",
      "params": ["app", "version"]
    }

  }
}
```

---

## Design Rules & Anti-Patterns

### ✅ DO

- **Pair every diagnostic result with a database_query** — always give the AI historical context
- **Use check_group for related checks** — group checks by subsystem (memory, CPU, I/O)
- **Keep result nodes focused** — one problem per result node; split compound issues
- **Use threshold-based operators** for quantitative metrics; analytical operators for distributions
- **Match JSON key names exactly** to the keys in the exported JSON from `export_avg_to_json()`

### ❌ DON'T

- **Don't add `next` to result nodes** — they are terminal by definition
- **Don't create chains of checks** without a check_group — siblings must fan out from a group
- **Don't use the same node ID twice** — even across different check branches
- **Don't hardcode device-specific values** — thresholds must be relative (DUT - REF), not absolute
- **Don't skip the `source` field** on check nodes — always declare `["DUT", "REF"]` or `["DUT"]`

---

## Mapping: Workflow Keys → JSON Export Keys

The workflow operators reference data keys that come directly from `export_avg_to_json()` output.
This is the authoritative mapping:

| Workflow key | JSON export path | Produced by |
|-------------|-----------------|-------------|
| `uptime_minutes` | `entry.extend.abnormal.uptime_minutes` | `dumpstate_parser.parse_uptime()` |
| `ANR`, `FATAL` | `entry.extend.abnormal.crash_count_avg` | `dumpstate_parser.count_crashes()` |
| `touch_duration` | `entry.sequence["Touch Duration"]` | `sql_query.py` |
| `Running` | `entry.sequence["Running"]` | `sql_query.py` |
| `Sleeping` | `entry.sequence["Sleeping"]` | `sql_query.py` |
| `Runnable` | `entry.sequence["Runnable"]` | `sql_query.py` |
| `State` | `entry.State` | List of per-cycle states: `["Cold","Cold","Cold"]`. Read the list to determine Cold/Warm per cycle. NOT derived from section name (entry ≠ Cold, reentry ≠ Warm). |
| `compiler` | `entry.extend.abnormal.compiler` | `dumpstate_parser.parse_compiler_type()` |
| `frequency_by_cycle` | `entry.frequency_by_cycle` | `Priority_Data` in `sql_query.py` |
| `priority_by_cycle` | `entry.priority_by_cycle` | `Priority_Data` in `sql_query.py` |
| `binder` | `entry.binder_transaction` | `Binder_Transaction_Data` in `sql_query.py` |
| `MemFree_MB` | `entry.extend.memory.MemFree_MB` | `dumpstate_parser.get_memory_data_for_cycle()` |
| `MemAvailable_MB` | `entry.extend.memory.MemAvailable_MB` | same |
| `App_PSS_MB` | `entry.extend.memory.App_PSS_MB` | `dumpstate_parser.parse_pss_for_app()` |
| `Pageboostd_MB` | `entry.extend.memory.Pageboostd_MB` | `dumpstate_parser.parse_pageboostd_for_app()` |
| `loadApkAssets` | `entry.extend.loadapkassets` | `LoadApkAsset_Data` in `sql_query.py` |
| `start_process_abnormal` | `entry.extend.start_process_abnormal` | `Abnormal_Process_Data` |
| `top_process_consume_by_cycle` | `entry.top_process_consume_by_cycle` | `CPU_Process_Data` tiered match |
| `apk_size` | *(not currently exported)* | Must be added to export if needed |
| `beks` | *(not currently exported)* | System-level config; add to dumpstate parser |
| `start_reasons` | `entry.extend.abnormal.start_reasons` | `dumpstate_parser.parse_start_reasons()` — list, per-cycle |
| `kill_reasons` | `entry.extend.abnormal.kill_reasons` | `dumpstate_parser.parse_kill_reasons()` — list, optional (only present if app was killed) |

**Note on `apk_size` and `beks`:** These appear in Flow 2 (`node_08_apk_size_check`) and
Flow 2 (`node_35_beks_check`) but are not yet exported by `export_avg_to_json()`. To make
these nodes functional, add extraction in `dumpstate_parser.py` and export in
`calculate_metrics_for_app()`.

---

## Reviewing Existing Workflow Logic

When reviewing or improving a diagnostic workflow, check:

1. **Coverage** — Does each major metric group (CPU, memory, I/O, process) have a corresponding check?
2. **Threshold sanity** — Are thresholds relative (DUT-REF) not absolute? Are values in correct units (ms, MB)?
3. **Team routing** — Does each `result.suggestion` route to the correct team?
4. **History coverage** — Every `result` should have a sibling `database_query` for context
5. **Key accuracy** — Do operator key names match the JSON export mapping table above?
6. **Missing nodes** — Nodes referenced in `next` arrays must exist in the same JSON file
