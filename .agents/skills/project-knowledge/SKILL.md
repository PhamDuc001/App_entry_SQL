---
name: project-knowledge
description: Domain knowledge base for Plan_convert_SQL project. Contains glossary, architecture, key algorithms, and business logic. Use when starting a new task or when encountering unfamiliar domain terms.
---

# project-knowledge

Domain knowledge base for the Plan_convert_SQL (TraceTool) project. Read this BEFORE making any code changes to understand the business context.

## Usage

- When starting a new task on this project
- When encountering unfamiliar Android trace terms
- When unsure about WHY a function exists or WHAT it measures
- When onboarding to the project for the first time

## Project Overview

Plan_convert_SQL (TraceTool) is a **performance analysis tool** that:
1. Reads Android systrace/atrace files (.log)
2. Queries trace data using Perfetto SQL
3. Extracts app launch timing metrics
4. Compares DUT (Device Under Test) vs REF (Reference device)
5. Outputs Excel and JSON reports

## Architecture

```
main_qt.py          -> PyQt6 GUI entry point
execution_sql.py     -> Thin wrapper: from execution import run_analysis
reaction_sql.py      -> Thin wrapper: from reaction import run_analysis

execution/           -> App Launch Time Analysis (Cold/Warm launch)
  config.py          -> Constants, APP_MAPPING, cache settings
  main.py            -> run_analysis(), cache logic
  processor.py       -> process_single_trace(), multiprocessing worker
  excel_sheet.py     -> create_sheet(), write_value_or_empty(), get_filtered_metric_rows()
  excel_output.py    -> create_excel_output()
  json_output.py     -> export_avg_to_json(), extract_version_and_model()

reaction/            -> Reaction Time Analysis (touch -> response)
  analyzer.py        -> analyze_reaction_trace(), process_all_traces()
  excel_output.py    -> create_excel_output(), write_value_or_empty()
  main.py            -> run_analysis(), cache logic

sql_query/           -> SQL query functions (shared by execution + reaction)
  base.py            -> Utilities: get_resource_path, to_ms, query_df, ensure_slice_with_names_view, find_slice
  trace_queries.py   -> Specific trace queries: detect_app_from_launch, get_choreographer, get_animating, etc.
  sequence_queries.py-> Thread state, slices, abnormal processes, layout depth, _query_end_ts_dependent_data
  block_io.py        -> Block I/O queries (library + kernel + HAL)
  cpu_queries.py     -> CPU usage, priority distribution
  loadapk_asset.py   -> PID lookups, LoadApkAsset, camera HAL PID
  binder_transaction.py -> Binder transaction count/duration
  analysis.py        -> Main orchestrator: analyze_trace()

MemoryStatus/       -> Memory leak analysis (separate module)
Pageboostd/         -> Page boost analysis (separate module)
```

## Glossary - Android Trace Terms

| Term | Meaning | Used In |
|------|---------|---------|
| **Cold launch** | App started from scratch (process not running) | has_bind_application() returns True |
| **Warm launch** | App resumed from background (process still running) | has_bind_application() returns False |
| **Recent launch** | App switched via Recent button | is_recent flag from filename |
| **Choreographer** | Android vsync callback (frame rendering signal) | get_choreographer() |
| **bindApplication** | System binds app process (Cold launch indicator) | has_bind_application() |
| **activityIdle** | System signals app is idle (end of launch) | get_activity_idle_end() |
| **animating** | Window animation playing (Process Track) | get_animating() |
| **deliverInputEvent** | Touch event delivered to app | get_first_deliver_input() |
| **dispatchInputEvent** | Touch dispatch (UP event for touch duration) | get_end_deliver_input() |
| **StartPreviewRequest** | Camera preview start (camera-specific end_ts) | get_slice_on_app_process() |
| **addStartingWindow** | System adds splash window (reaction analysis) | get_addStartingWindow() |
| **Block I/O** | Disk I/O blocking main thread (state D) | top_block_IO(), get_kernel_block_io() |
| **Binder transaction** | IPC between Android processes | get_binder_transaction() |
| **LoadApkAsset** | APK resource loading > 50ms | get_loadApkAsset() |
| **slice_with_names** | SQL view joining slice + thread + process | ensure_slice_with_names_view() |
| **DUT** | Device Under Test (the device being measured) | - |
| **REF** | Reference device (baseline for comparison) | - |

## Key Algorithms

### 1. End Timestamp Selection (CRITICAL)
The most important logic in the project. Different apps use different end_ts:

```
Camera apps:     end_ts = StartPreviewRequest (camera preview ready)
Recent apps:     end_ts = activityIdle > launching_end > touch_down + 500ms
Internet apps:   end_ts = animating_end (special case for idle/launching overlap)
Normal apps:     end_ts = activityIdle > animating_end
```

### 2. Multi End-TS Query
Since R3, the tool queries data for ALL available end_ts types, then selects the common type between DUT and REF for fair comparison. See `select_common_end_ts_type()` in processor.py.

### 3. Cache System
- Cache file: `.perf_cache.pkl` in each trace folder
- Contains: version, target_apps list, processed data
- Smart merge: only processes missing apps, reuses cached data
- Must delete cache after code changes that affect output format

### 4. Trace-Bugreport Mapping
- Traces need PID mapping from bugreport (dumpstate) for CPU process name resolution
- Mapping: trace filename -> bugreport folder -> extract PID names
- Without mapping, CPU data shows "PID-1234" instead of real process names

## File Naming Convention

Trace files follow pattern: `{model}_{version}_{cycle}_{timestamp}_{appname}.log`
- Example: `A266BZA5_BOS_6GB_260122_S1_260122_093153_clock.log`
- `entry` = 1st launch (cold/warm), `reentry` = 2nd launch (warm)

## Common Pitfalls

1. **Never move a function without updating ALL importers** - Use search_files to find all references
2. **Cache must be deleted after refactoring** - Old cache may have different data structure
3. **Camera apps have special logic** - Always test with camera after changes
4. **Unicode in comments** - Vietnamese comments cause replace_in_file matching issues
5. **`from package import *`** - Re-exports via __init__.py, but PyInstaller needs explicit hiddenimports