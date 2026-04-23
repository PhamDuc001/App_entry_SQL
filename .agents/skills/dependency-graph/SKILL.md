---
name: dependency-graph
description: Build and query function-level dependency graph for the project. Shows which functions call which, what imports what, and impact analysis for refactoring.
---

# dependency-graph

Build a function-level dependency graph to understand cross-module relationships and assess refactoring impact.

## Usage

- Before moving a function to a different file
- Before renaming a function or class
- When asked "what does this function depend on?" or "who calls this function?"
- When planning a refactoring to understand the scope of changes

## Steps

### Step 1: Build the Graph

Use `search_files` and `list_code_definition_names` to build the dependency graph:

1. For each Python package, run `list_code_definition_names` to get all function/class names
2. For each function, use `search_files` with the function name to find all callers
3. For each file, use `search_files` with `^from |^import ` to find all imports

### Step 2: Format the Graph

Output in this format:

```
DEPENDENCY GRAPH
================

## sql_query/base.py (DEFINITIONS)
  get_resource_path()     <- used by: block_io.py, processor.py
  to_ms()                 <- used by: analysis.py, sequence_queries.py, excel_sheet.py
  query_df()              <- used by: ALL sql_query modules
  ensure_slice_with_names_view() <- used by: analysis.py
  find_slice()            <- used by: trace_queries.py

## sql_query/trace_queries.py (DEFINITIONS)
  detect_app_from_launch() <- used by: analysis.py
  get_choreographer()     <- used by: analysis.py
  get_animating()         <- used by: analysis.py
  ... (15 functions total)

## sql_query/analysis.py (CALLS)
  -> sql_query.base: ensure_slice_with_names_view, to_ms, query_df, find_slice
  -> sql_query.trace_queries: detect_app_from_launch, find_app_process, get_choreographer, ...
  -> sql_query.sequence_queries: get_thread_state_summary, _query_end_ts_dependent_data, ...
  -> sql_query.block_io: top_block_IO, process_block_io_data, get_kernel_block_io
  -> sql_query.cpu_queries: get_priority_distribution, get_layout_depth_slices
  -> sql_query.loadapk_asset: get_pid_list, get_loadApkAsset, process_loadapk_data
  -> sql_query.binder_transaction: get_binder_transaction
```

### Step 3: Impact Analysis

When planning to move/rename a function, report:

```
IMPACT ANALYSIS: Moving get_camera_hal_pid from block_io.py to loadapk_asset.py
=============================================================================

Callers to update:
  [MUST UPDATE] sql_query/sequence_queries.py - line 3: from sql_query.block_io import ... get_camera_hal_pid
    -> Change to: from sql_query.loadapk_asset import ... get_camera_hal_pid

  [OK] sql_query/block_io.py - function removed from here

  [OK] sql_query/__init__.py - re-exports from loadapk_asset (already correct)

No other callers found. Safe to proceed.
```

### Step 4: Circular Dependency Detection

Check for circular imports:

```
CIRCULAR DEPENDENCY CHECK
=========================
sql_query/base.py -> (no sql_query imports)
sql_query/trace_queries.py -> sql_query/base
sql_query/sequence_queries.py -> sql_query/base, sql_query/block_io, sql_query/loadapk_asset, sql_query/cpu_queries, sql_query/binder_transaction
sql_query/analysis.py -> sql_query/base, sql_query/trace_queries, sql_query/sequence_queries, sql_query/loadapk_asset, sql_query/cpu_queries, sql_query/binder_transaction, sql_query/block_io

No circular dependencies detected.
```

If circular dependency found:
```
WARNING: Circular dependency detected!
  module_a -> module_b -> module_c -> module_a
  
Fix options:
  1. Move shared function to a lower-level module
  2. Use late import (import inside function)
  3. Extract shared dependency to a new base module
```

## Quick Reference: Current Dependencies

```
Level 0 (no deps):     sql_query/base.py
Level 1 (depends on 0): sql_query/trace_queries.py, sql_query/binder_transaction.py
Level 2 (depends on 0-1): sql_query/block_io.py, sql_query/cpu_queries.py, sql_query/loadapk_asset.py
Level 3 (depends on 0-2): sql_query/sequence_queries.py
Level 4 (depends on 0-3): sql_query/analysis.py

execution/config.py (standalone constants)
execution/processor.py -> sql_query.*, execution/config
execution/excel_sheet.py -> execution/config
execution/excel_output.py -> execution/config, execution/excel_sheet
execution/json_output.py -> execution/config, execution/processor
execution/main.py -> execution/processor, execution/excel_output, execution/json_output

reaction/analyzer.py -> sql_query.*
reaction/excel_output.py -> reaction/(local)
reaction/main.py -> reaction/analyzer, reaction/excel_output
```

## Rules

1. NEVER create a circular dependency
2. Lower-level modules (base.py) must NOT import from higher-level modules
3. When in doubt, put the function in the LOWEST possible level
4. Cross-package imports (reaction -> sql_query) are OK but document them