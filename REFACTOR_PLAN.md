# Refactoring Plan: Plan_convert_SQL Module Separation

## Current State

| File | Lines | Role |
|------|-------|------|
| `sql_query.py` | 2032 | ALL SQL queries + analyze_trace() |
| `execution_sql.py` | 3063 | Execution processing + Excel + JSON + cache + run_analysis() |
| `reaction_sql.py` | 725 | Reaction processing + Excel + cache + run_analysis() |
| `dumpstate_parser.py` | 809 | Bugreport/dumpstate parsing (keep as-is) |
| `main_qt.py` | 16 | PyQt6 entry point |
| `ui/window.py` | ? | UI - calls execution_sql.run_analysis() and reaction_sql.run_analysis() |

### Key Differences from srv_perf_cpu_core Project
- Standalone project with direct imports (`from sql_query import *`)
- PyQt6 UI integration via `importlib.reload(execution_sql)`
- Caching system (`get_or_process_folder_with_cache` with pickle)
- `convert_trace` at `utils/trace/atracetosystrace.py` (not root)
- New function: `get_layout_depth_slices()`
- `extract_version_and_model()` present in both execution and reaction

### External Callers
- `ui/window.py` calls: `execution_sql.run_analysis()`, `reaction_sql.run_analysis()`
- These must continue working after refactor

---

## Success Criteria
1. `import execution_sql; execution_sql.run_analysis(...)` still works
2. `import reaction_sql; reaction_sql.run_analysis(...)` still works
3. `from sql_query import analyze_trace` still works
4. Zero logic changes - pure structural refactor
5. All Python syntax valid

---

## Step 1: Split `sql_query.py` -> `sql_query/` package

### 1.1 `sql_query/base.py` (~400 lines)
Core utilities and simple queries shared by all modules.

**Imports needed:**
```python
import os, sys, subprocess
import pandas as pd
from typing import Dict, Optional, Any, Tuple, List, Union
from perfetto.trace_processor.api import TraceProcessor, TraceProcessorConfig
```

**Functions to extract:**
- `get_resource_path()` (both overloads)
- `to_ms()`
- `query_df()`
- `ensure_slice_with_names_view()`
- `find_slice()`
- `detect_app_from_launch()`
- `find_app_process()`
- `get_first_deliver_input()`
- `get_end_deliver_input()`
- `get_launcher_pid()`
- `get_activity_idle_end()`
- `get_start_proc_start()`
- `has_bind_application()`
- `get_event_ts()`
- `get_choreographer()`
- `get_launching_end()`
- `get_animating()`
- `get_onTransactionReady()`
- `get_addStartingWindow()`
- `get_drawFrame()` (both overloads)
- `get_reaction_choreographer()`

### 1.2 `sql_query/sequence_queries.py` (~450 lines)
Step sequence and process state queries.

**Imports needed:**
```python
from sql_query.base import to_ms, query_df, ensure_slice_with_names_view, find_slice
from perfetto.trace_processor.api import TraceProcessor
from typing import Dict, Optional, Any, Tuple, List
from collections import defaultdict
```

**Functions to extract:**
- `get_thread_state_summary()`
- `get_slice_on_app_process()`
- `process_multiple_slices_data()`
- `get_abnormal_processes()`
- `process_abnormal_data()`
- `get_background_process_states()`
- `_query_end_ts_dependent_data()`

### 1.3 `sql_query/loadapk_asset.py` (~200 lines)
LoadApkAsset domain queries.

**Imports needed:**
```python
from sql_query.base import query_df
from perfetto.trace_processor.api import TraceProcessor
from typing import Dict, Optional, Any, Tuple, List
```

**Functions to extract:**
- `get_system_pids()`
- `get_loadApkAsset()`
- `process_loadapk_data()`
- `get_pid_list()`
- `get_pid_systemUI()`

### 1.4 `sql_query/cpu_queries.py` (~350 lines)
CPU by Process/Thread + Priority distribution.

**Imports needed:**
```python
from sql_query.base import query_df, to_ms
from perfetto.trace_processor.api import TraceProcessor
from typing import Dict, Optional, Any, Tuple, List
from collections import defaultdict
import pandas as pd
```

**Functions to extract:**
- `get_top_cpu_usage_process()`
- `process_cpu_data_process()`
- `get_top_cpu_usage_thread()`
- `process_cpu_data_thread()`
- `get_priority_distribution()`
- `get_layout_depth_slices()`

### 1.5 `sql_query/binder_transaction.py` (~80 lines)
Binder Transaction statistics queries.

**Imports needed:**
```python
from sql_query.base import query_df
from perfetto.trace_processor.api import TraceProcessor
from typing import Optional, Tuple
```

**Functions to extract:**
- `get_binder_transaction()`

**Note**: `get_binder_transaction()` is used by both `analyze_trace()` (in `analysis.py`) and the Excel Statistics table (in `execution/excel_extended_sections.py`). It queries `binder transaction` slices and returns count + duration.

### 1.6 `sql_query/block_io.py` (~350 lines)
Block I/O domain queries.

**Imports needed:**
```python
from sql_query.base import query_df
from sql_query.loadapk_asset import get_pid_list, get_pid_systemUI, process_block_io_data
from perfetto.trace_processor.api import TraceProcessor
from typing import Dict, Optional, Any, Tuple, List
from collections import defaultdict
import pandas as pd
import os
```

**Functions to extract:**
- `top_block_IO()`
- `process_block_io_data()`
- `extract_raw_ftrace_data()`
- `get_kernel_block_io()`
- `_query_kernel_bio_from_raw()`
- `get_camera_hal_pid()`
- `get_hal_library_block_io()`
- `process_hal_block_io_data()`

### 1.7 `sql_query/analysis.py` (~400 lines)
Main orchestrator - calls all above.

**Imports needed:**
```python
from sql_query.base import *
from sql_query.sequence_queries import *
from sql_query.loadapk_asset import *
from sql_query.cpu_queries import *
from sql_query.binder_transaction import get_binder_transaction
from sql_query.block_io import *
from pathlib import Path
```

**Functions to extract:**
- `analyze_trace()`

### 1.8 `sql_query/__init__.py`
Re-export everything for backward compatibility:
```python
from sql_query.base import *
from sql_query.sequence_queries import *
from sql_query.loadapk_asset import *
from sql_query.cpu_queries import *
from sql_query.binder_transaction import *
from sql_query.block_io import *
from sql_query.analysis import *
```

### 1.9 Old `sql_query.py` -> rename to `sql_query_old.py` backup, then create wrapper:
```python
# sql_query.py - backward compatibility wrapper
from sql_query import *
```
**IMPORTANT**: This won't work because `sql_query.py` and `sql_query/` can't coexist.
**Solution**: Delete old `sql_query.py`, create `sql_query/` package. All existing imports `from sql_query import X` will resolve to the package.

---

## Step 2: Split `execution_sql.py` -> `execution/` package

### 2.1 `execution/config.py` (~100 lines)
**Contents:**
- `APP_MAPPING` dict
- `TARGET_APPS` list
- `COLD_ONLY_KEYS`, `WARM_ONLY_KEYS` sets
- `APP_NAME_NORMALIZATION` dict
- Session/proxy config
- `TRACE_PROCESSOR_BIN` path
- `CURRENT_DIR`

### 2.2 `execution/processor.py` (~350 lines)
**Contents:**
- `collect_trace_files()`
- `group_traces_by_app()`
- `_process_single_trace_worker()`
- `process_single_trace()`
- `process_all_traces()`
- `select_common_end_ts_type()`
- `get_metrics_for_end_ts_type()`
- `get_or_process_folder_with_cache()`

### 2.3 `execution/excel_output.py` (~100 lines)
**Contents:**
- `create_excel_output()` - main orchestrator
- `write_value_or_empty()`
- `get_filtered_metric_rows()`

### 2.4 `execution/excel_metrics_sheet.py` (~260 lines, lines 627-886)
**Contents:**
- `create_sheet()` - first part: format definitions, pre-process (common end_ts), check global state, header row, main sequence metric rows
- Inner helper functions: `get_cycle_title()`, `get_t_key()`, `parse_prio_key()`, `get_category_total_time()`, `get_prio_breakdown()`
- Process Start Overlap Section (lines 887-992)

### 2.5 `execution/excel_memory_section.py` (~200 lines, lines 993-1189)
**Contents:**
- MEMORY SECTION (lines 993-1100)
- LOADAPKASSETS SECTION EXTENDED (lines 1101-1189) - the short header section in sequence table

Each function takes `(ws, row_idx, dut_cycles, ref_cycles, total_cols, fmt_section_header, fmt_section_value, ...) -> int`

### 2.6 `execution/excel_abnormal_section.py` (~160 lines, lines 1190-1349)
**Contents:**
- ABNORMAL SECTION (lines 1190-1251) - header section in sequence table
- Abnormal Process & Background Activity Table (lines 1252-1349) - detailed table

### 2.7 `execution/excel_cpu_section.py` (~210 lines, lines 1350-1557)
**Contents:**
- Top CPU Usage Tables - Process (left) + Thread (right) per cycle
- Tiered matching logic for DUT vs REF comparison

### 2.8 `execution/excel_priority_section.py` (~190 lines, lines 1558-1749)
**Contents:**
- PRIORITY STATICS TABLE (FULL & FINAL)
- Category/Priority breakdown with frequency grouping
- Note: Lines 1742-1849 contain commented-out LAYOUT ANALYSIS code - include as-is

### 2.9 `execution/excel_blockio_section.py` (~140 lines, lines 1850-1987)
**Contents:**
- Top Block I/O Libraries table
- Format definitions, data collection, library aggregation

### 2.10 `execution/excel_loadapk_table.py` (~110 lines, lines 1988-2091)
**Contents:**
- LoadApkAssets Table (categorized by system_server, system_ui, launching_app)
- Header, sub-header, data rows

### 2.11 `execution/excel_stats_section.py` (~140 lines, lines 2092-2228)
**Contents:**
- Statistics Table (Binder Transaction, etc.)
- Format definitions, dur/count pattern

### 2.12 `execution/json_output.py` (~580 lines, lines 2229-2851)
**Contents:**
- `extract_version_and_model()` (line 2229)
- `extract_device_code()` (line 2254)
- `export_avg_to_json()` (line 2275) with inner `calculate_metrics_for_app()`:
  - STATE per cycle
  - SEQUENCE METRICS (AVG)
  - EXTEND METRICS (Start Process Abnormal, LoadApkAssets)
  - TOP CPU BY PROCESS DIFF (TOP 5)
  - TOP CPU BY THREAD DIFF (TOP 5)
  - PRIORITY STATICS (BY CYCLE)
  - BLOCK I/O
  - BUILD & WRITE PER-APP JSON FILES

### 2.13 `execution/main.py` (~50 lines)
**Contents:**
- `run_analysis()` - entry point called by UI
- `main()` - CLI entry point

### 2.14 `execution/__init__.py`
```python
from execution.main import run_analysis
```

### 2.15 Old `execution_sql.py` -> wrapper
```python
# execution_sql.py - backward compatibility wrapper
from execution.main import run_analysis, main
```

---

## Step 3: Split `reaction_sql.py` -> `reaction/` package

### 3.1 `reaction/analyzer.py` (~300 lines)
**Contents:**
- Config constants (APP_MAPPING, TARGET_APPS, session/proxy, TRACE_PROCESSOR_BIN)
- `analyze_reaction_trace()`
- `process_single_trace()`
- `process_all_traces()`
- `collect_trace_files()`
- `get_or_process_folder_with_cache()`
- `extract_version_and_model()`

### 3.2 `reaction/excel_output.py` (~200 lines)
**Contents:**
- `create_excel_output()`
- `write_value_or_empty()`

### 3.3 `reaction/main.py` (~50 lines)
**Contents:**
- `run_analysis()` - entry point
- `main()` - CLI entry point

### 3.4 `reaction/__init__.py`
```python
from reaction.main import run_analysis
```

### 3.5 Old `reaction_sql.py` -> wrapper
```python
# reaction_sql.py - backward compatibility wrapper
from reaction.main import run_analysis, main
```

---

## Step 4: Files NOT Changed
- `dumpstate_parser.py` - already self-contained (809 lines)
- `main_qt.py` - entry point
- `ui/window.py` - no changes needed (imports execution_sql.run_analysis still works via wrapper)
- `utils/` - already organized
- `MemoryStatus/` - already organized
- `Pageboostd/` - already organized
- `perfetto/` - already organized

---

## Implementation Order (Surgical, Step-by-Step)

1. Create `sql_query/` package with all sub-modules
2. Delete old `sql_query.py` (replaced by package)
3. Verify: `python -c "from sql_query import analyze_trace"` works
4. Create `execution/` package with all sub-modules
5. Replace `execution_sql.py` with thin wrapper
6. Verify: `python -c "import execution_sql; print('OK')"` works
7. Create `reaction/` package with all sub-modules
8. Replace `reaction_sql.py` with thin wrapper
9. Verify: `python -c "import reaction_sql; print('OK')"` works
10. Full integration test via UI
11. Git commit

---

## Risk Mitigation
- Keep old files as `_old.py` backups until verified
- Verify after EACH step, not at the end
- The `importlib.reload()` pattern in UI means the wrapper approach is critical
- `from sql_query import *` in execution_sql.py will resolve to the package's `__init__.py`

---

## Dependency Graph (No Circular Dependencies)

```
sql_query/base.py  (no internal deps)
       |
       +---> sql_query/sequence_queries.py
       +---> sql_query/loadapk_asset.py
       +---> sql_query/cpu_queries.py
       +---> sql_query/binder_transaction.py  (standalone, only depends on base)
       +---> sql_query/block_io.py  (also depends on loadapk_asset)
       |
       +---> sql_query/analysis.py  (depends on ALL above)
       
execution/config.py  (no internal deps)
       |
       +---> execution/processor.py  (depends on config, sql_query, dumpstate_parser)
       |
       +---> execution/excel_metrics_sheet.py  (depends on config)
       |       |
       |       +---> execution/excel_memory_section.py
       |       +---> execution/excel_abnormal_section.py
       |       +---> execution/excel_cpu_section.py
       |       +---> execution/excel_priority_section.py
       |       +---> execution/excel_blockio_section.py
       |       +---> execution/excel_loadapk_table.py
       |       +---> execution/excel_stats_section.py
       |
       +---> execution/excel_output.py  (depends on config, excel_metrics_sheet)
       +---> execution/json_output.py  (depends on config, sql_query)
       +---> execution/main.py  (depends on processor, excel_output, json_output, config)
       
reaction/analyzer.py  (depends on sql_query, config constants)
       +---> reaction/excel_output.py
       +---> reaction/main.py  (depends on analyzer, excel_output)