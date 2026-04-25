# Codebase Guide — Code Patterns & Data Flow

## Architecture Overview

```
.log files (DUT folder)          .log files (REF folder)
        │                                │
        ▼                                ▼
collect_trace_files()            collect_trace_files()
        │                                │
        ▼                                ▼
group_traces_by_app()            group_traces_by_app()
        │                                │
        ▼                                ▼
_process_single_trace_worker()   _process_single_trace_worker()
  ├── convert_trace()              (multiprocessing Pool)
  ├── TraceProcessor(trace)
  ├── analyze_trace()  ◄──── sql_query.py owns this
  └── dumpstate_parser.*()
        │                                │
        ▼                                ▼
   dut_results{}                   ref_results{}
        │                                │
        └──────────────┬─────────────────┘
                       ▼
              create_excel_output()
              export_avg_to_json()
```

---

## File Responsibilities

### `sql_query.py` — Extraction Layer
**Owns:** Everything that touches `TraceProcessor`. This file must remain pure — no file I/O,
no dumpstate parsing, no Excel logic.

Key functions:
- `ensure_slice_with_names_view()` — creates the shared SQL view; **always called first**
- `find_slice()` — generic single-row query; use this over raw SQL whenever possible
- `query_df()` — generic multi-row query; wraps all errors, returns None on failure
- `analyze_trace(tp, file_path, pid_mapping)` — **master extractor**; returns the full metrics dict

**Rule:** If data comes from the `.log` trace → it lives in `sql_query.py`.

### `execution_sql.py` — Orchestration Layer
**Owns:** File discovery, batch processing, dumpstate integration, Excel/JSON output.

Key functions:
- `_process_single_trace_worker(args)` — multiprocessing entry point; merges trace metrics
  with dumpstate data into `Precomputed_Extend_Data`
- `create_sheet()` — Excel sheet builder; handles masking, end_ts alignment, all sections
- `export_avg_to_json()` → `calculate_metrics_for_app()` — JSON export with cycle aggregation

**Rule:** If data comes from bugreport/dumpstate → it lives here, stored in `Precomputed_Extend_Data`.

---

## The `metrics` Dict — Structure Reference

`analyze_trace()` returns a dict. Key fields Agent must know:

```python
metrics = {
    # Timeline (ms floats)
    "App Execution Time": float,
    "Bind Application": float,
    "Activity Start": float,
    "Activity Resume": float,
    "Choreographer": float,
    "ActivityIdle": float,
    # ... all transition keys (see SKILL.md timeline group)

    # Thread states (ms floats)
    "Running": float,
    "Runnable": float,
    "Uninterruptible Sleep": float,
    "Sleeping": float,

    # Launch classification
    "Launch Type": "Cold" | "Warm",

    # end_ts variant support
    "end_ts_variants": {"activityIdle": float, "animating": float, ...},
    "data_by_end_ts": {
        "activityIdle": {"Running": float, "Block_IO_Data": [...], ...},
        # mirrors top-level structure per end event
    },

    # Extended structured data
    "Block_IO_Data": [{"libraryName": str, "timeTotal_ms": float, ...}],
    "LoadApkAsset_Data": {
        "system_server": [{"name": str, "dur_ms": float}],
        "system_ui": [...],
        "launching_app": [...]
    },
    "CPU_Process_Data": [{"sql_name": str, "dumpstate_name": str|None, "dur_ms": float}],
    "CPU_Thread_Data": [{"thread_name": str, "proc_name": str, "dur_ms": float}],
    "Binder_Transaction_Data": {"duration_ms": float, "count": int},
    "Priority_Data": {
        "bindApplication": {"<priority>_<freq_mhz>": float_ms, ...},
        "activityStart": {...},
        "activityResume": {...},
        "Choreographer": {...}
    },
    "Abnormal_Process_Data": [{"proc_name": str, ...}],
    "Background_Process_States": [{"Thread name": str, ...}],

    # Injected by _process_single_trace_worker (NOT from sql_query.py)
    "Precomputed_Extend_Data": {
        "MemFree": float,        # MB
        "MemAvailable": float,   # MB
        "App_PSS": float,        # MB
        "Pageboostd": float,     # MB
        "Uptime": float,         # minutes
        "Start_Reason": str | list,
        "Kill_Reason": list[str],
        "Crash_Count": int,
        "Compiler": str          # e.g. "verify", "speed-profile"
    }
}
```

---

## Adding a New Metric — Complete Checklist

Follow in order. Skipping steps causes silent 0-values or mismatched DUT/REF comparisons.

### Step 1: Extract in `sql_query.py`

```python
# Inside analyze_trace(), after existing queries:
def get_my_new_metric(tp: TraceProcessor, app_upid: int) -> float:
    row = find_slice(tp, name_exact='mySliceName', upid=app_upid)
    if row is not None:
        return to_ms(row['dur'])
    return 0.0

# Then in analyze_trace() return dict:
metrics["My New Metric"] = get_my_new_metric(tp, app_upid)
```

**If the metric varies by end_ts** (it's part of a time window): also add it to the
`data_by_end_ts[end_type]` dict inside the per-end_ts calculation block.

### Step 2: Classify the metric (edit `execution_sql.py`)

```python
# If Cold-launch only:
COLD_ONLY_KEYS.add("My New Metric")

# If Warm-launch only:
WARM_ONLY_KEYS.add("My New Metric")
```

### Step 3: Add to Excel row list

In `get_filtered_metric_rows()`, add a tuple in the correct section:
```python
("My New Metric Label", "My New Metric"),  # (display_name, dict_key)
```

### Step 4: Add to JSON export

In `calculate_metrics_for_app()`, add the key to `sequence_metrics` list:
```python
sequence_metrics = [
    ...,
    "My New Metric",  # add here
]
```

### Step 5: Add to workflow JSON (if diagnostically relevant)

Create a check node in the appropriate Flow JSON. See `references/workflow-design.md`.

---

## Pattern: CPU Process Tiered Matching

This pattern appears in both `create_sheet()` and `calculate_metrics_for_app()`. It must stay
consistent between both — **never modify one without checking the other**.

```python
# Tier 1: Match by exact sql_name (process name from perfetto)
if not dut_sql.startswith("PID-") and dut_sql in ref_by_sql:
    ref_val = ref_by_sql[dut_sql]['dur_ms']

# Tier 2: Fallback to dumpstate_name (human-readable name from bugreport)
elif dut_dump and dut_dump in ref_by_dump:
    ref_val = ref_by_dump[dut_dump]['dur_ms']
    display_name = dut_dump

# Tier 3: Unknown process (PID-based, no dumpstate) → diff = 0.0 (ignored)
else:
    if dut_sql.startswith("PID-") and dut_dump:
        display_name = dut_dump
    diff = 0.0  # discard — no reliable identity
```

**Why this matters:** PID values change between traces. `sql_name` uses PID when the process
name isn't in perfetto — fallback to `dumpstate_name` ensures correct cross-device matching.

---

## Pattern: Priority × Frequency Key Encoding

`Priority_Data` stores time (ms) keyed as `"<priority>_<freq_mhz>"`:

```python
# Example key: "120_1800" means priority=120, frequency=1800MHz
parts = str(key).split('_')
priority = int(parts[0])
freq_mhz = int(parts[1]) if len(parts) >= 2 else 0
```

In JSON export, this is decoded into structured lists per category:
```json
{
  "priority_by_cycle": [{"cycle": 1, "data": {"bindApplication": [{"priority": 120, "percentage": 85.3}]}}],
  "frequency_by_cycle": [{"cycle": 1, "data": {"bindApplication": [{"frequency": 1800, "percentage": 72.1}]}}]
}
```

The workflow uses `frequency_by_cycle` and `priority_by_cycle` keys directly in `node_12_frequency_check`
and `node_08_priority_check` operators.

---

## Pattern: end_ts Alignment (Critical for Correctness)

Before any DUT/REF metric comparison in `create_sheet()`:

```python
common_type = select_common_end_ts_type(dut_cycle, ref_cycle)
# Returns: "activityIdle" | "animating" | "startPreviewRequest" | None

if common_type:
    adj_dut = get_metrics_for_end_ts_type(dut_cycle, common_type)
    adj_ref = get_metrics_for_end_ts_type(ref_cycle, common_type)
else:
    # Mismatch — use raw cycles but flag it
    end_ts_types_used.append("mismatch")
```

`get_metrics_for_end_ts_type()` overlays `data_by_end_ts[end_type]` fields over the base metrics.
Fields NOT in `data_by_end_ts` (e.g., `Precomputed_Extend_Data`) retain their original values.

**Never bypass this alignment.** Comparing `activityIdle`-based DUT data with `animating`-based
REF data inflates Running/Sleeping/Sleeping differences artificially.

---

## Common Pitfalls & Fixes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Metric shows 0.0 in Excel | `write_value_or_empty()` treats 0.0 as empty intentionally | Check if `analyze_trace()` actually returns > 0 for that trace |
| Cycle data is None in results | Worker exception swallowed silently | Add logging inside `except` block; check `convert_trace()` output |
| Cold metrics appear in Warm rows | Missing entry in `COLD_ONLY_KEYS` | Add key to set in both `create_sheet()` and `calculate_metrics_for_app()` |
| Wrong column offsets in Excel | `max_cycles` recalculated late in function | Freeze `max_cycles` before any section drawing; don't use `len()` on modified lists |
| CPU process diff is 0 for unknown process | PID-based name with no dumpstate | Expected behavior; dumpstate bugreport wasn't captured or process wasn't listed |
| `select_common_end_ts_type` returns None | End events are different between DUT and REF | Check if one device captured `activityIdle` and the other only `animating` |
| App not grouped correctly | `group_traces_by_app()` keyword match too loose | Check `APP_NAME_NORMALIZATION` dict and `TARGET_APPS` keyword list |
| `Precomputed_Extend_Data` empty | No bugreport matched to trace | Check `build_trace_bugreport_mapping()` output; verify folder structure |

---

## Multiprocessing Rules

- **Worker args** must be passed explicitly — no global state. Worker signature:
  `(file_path, occurrence, app_name, pid_mapping, mapping_info, folder_path)`
- **Pool.imap** (not `map`) is used for ordered streaming results with progress printing
- **`pool.close()` then `pool.join()`** — always in finally block
- **Port allocation** for TraceProcessor: each worker calls `test_trace_processor_config()`
  which finds a free port. Workers are isolated — no shared TraceProcessor instances
- **None cycles** are preserved in result lists (`cleaned_results`). Downstream code must
  handle `if cycle is not None` guards — never assume all cycles are populated
