---
name: plan-convert-sql
description: Specialized skill for Plan_convert_SQL - Android performance trace analysis tool. Use when analyzing execution_sql.py, processing traces, implementing CPU/priority analysis, working with cache system, modifying JSON/Excel export, or optimizing performance of this codebase. Covers code reading, refactoring, debugging, and feature development for this specific project.
---

# Plan_convert_SQL

A specialized skill set for working with Plan_convert_SQL, an Android performance trace analysis tool that processes system traces from DUT and REF devices, compares execution metrics, and generates Excel/JSON reports.

## Usage
```
# Reading code Function only
reading --function <function_name>
# Reading code All file
reading --file <path_to_file>
# Refactor function
refactor --function <function_name>
# Feature development 
develop --feature <feature_description>
# Debugging
debug --debug <debug_description>

```
---

## 1. PROJECT OVERVIEW

### 1.1. What is Plan_convert_SQL?

Plan_convert_SQL is a performance analysis tool for Android system traces that helps developers:

- **Process trace files** from multiple Android devices (DUT vs REF)
- **Analyze execution time** of app launches (Cold and Warm)
- **Compare CPU usage** between devices
- **Measure memory** and system state
- **Generate reports** in Excel and JSON formats
- **Identify performance bottlenecks** through TOP processes analysis

### 1.2. Supported Applications

The tool analyzes these Android apps:
- Calculator, Camera, Gallery, Messages, Dialer
- Clock, Contacts, Calendar, Notes
- My Files, Internet, Settings
- Voice Note, SIP, Helloworld

---

## 2. ARCHITECTURE

```
Plan_convert_SQL/
├── main_qt.py                    # GUI entry point (PyQt5)
├── execution_sql.py              # Core analysis logic (main file)
├── sql_query.py                  # Perfetto SQL queries
├── dumpstate_parser.py           # Parse bugreport files
├── ui/
│   ├── window.py                 # PyQt5 UI implementation
│   └── styles.qss                # UI styling
├── perfetto/
│   └── trace_processor           # Perfetto trace processor binary
├── MemoryStatus/                 # Memory analysis tools
├── Pageboostd/                   # Pageboostd analysis
└── .cline/skills/plan-convert-sql/  # This skill
```

### 2.1. Key Data Structures

**DUT/REF Results Format:**
```python
{
    "app_name": {
        "entry": [cycle_1, cycle_2, cycle_3, ...],  # Cold launch cycles
        "reentry": [cycle_1, cycle_2, ...]            # Warm launch cycles
    }
}

# Each cycle is a dict:
{
    "App Execution Time": 447.703,
    "Touch Down ~ Start Proc": 10.732,
    "Bind Application": 57.332,
    "Activity Start": 114.563,
    "Activity Resume": 23.097,
    "Choreographer": 46.753,
    "Running": 185.82,
    "CPU_Process_Data": [...],
    "Priority_Data": {...},
    "Block_IO_Data": [...],
    "Memory_Data": {...},
    "Precomputed_Extend_Data": {...}  # Cached memory/abnormal info
}
```

**JSON Export Format:**
```python
{
    "device_code": "ZB6",
    "timestamp": "2026-03-03T10:00:00",
    "type": "DUT",
    "app": "calculator",
    "entry": {
        "State": ["Cold", "Cold", "Cold"],
        "sequence": {...},
        "extend": {...},
        "top_process_consume_by_cycle": [...],
        "priority_by_cycle": [...],
        "frequency_by_cycle": [...],
        "block_io_by_cycle": [...],
        "binder_transaction": {...}
    }
}
```

---

## 3. KEY FUNCTIONS

### 3.1. Core Processing Functions

#### `process_all_traces(folder_path, label, num_workers, target_apps, extracted)`
- **Purpose:** Process all trace files in a folder with multiprocessing
- **Location:** execution_sql.py
- **Input:** Folder path, worker count, target apps list
- **Output:** `{app_name: {'entry': [...], 'reentry': [...]}}`
- **Key Steps:**
  1. Collect and group trace files by app name
  2. Build trace-to-bugreport mapping
  3. Use multiprocessing pool for parallel trace processing
  4. Parse dumpstate for memory/abnormal data at worker level
  5. Store precomputed data in metrics dict

#### `analyze_trace(tp, file_path, pid_mapping)`
- **Purpose:** Analyze a single trace file using Perfetto queries
- **Location:** sql_query.py
- **Input:** TraceProcessor instance, file path, PID mapping
- **Output:** Dict with all metrics (execution time, CPU, priority, etc.)
- **Key Metrics Collected:**
  - Execution timeline (Touch Down → Activity Idle)
  - CPU Process Data (with dumpstate name mapping)
  - CPU Thread Data
  - Priority Distribution (by frequency)
  - Block I/O Data
  - Binder Transaction stats
  - Abnormal Process list
  - Background Process states

#### `get_or_process_folder_with_cache(folder_path, label, num_workers, target_apps, extracted)`
- **Purpose:** Process traces with smart cache system (incremental processing)
- **Location:** execution_sql.py
- **Cache File:** `.perf_cache.pkl` (saved in processed folder)
- **Cache Logic:**
  - Check if cache exists and is valid version
  - If cache has ALL apps → Load and return
  - If cache is subset of target → Process missing apps, merge, save
  - If cache is invalid → Re-process all, save

### 3.2. Metrics Calculation Functions

#### `calculate_metrics_for_app(cycles, app_name, launch_type, folder_path, compare_cycles, is_dut)`
- **Purpose:** Calculate metrics for export to JSON
- **Location:** execution_sql.py (nested function in export_avg_to_json)
- **Input:** Cycles data, app info, compare_cycles for CPU diff, is_dut flag
- **Output:** Dict with all computed metrics
- **Key Sections:**
  1. State (Cold/Warm per cycle)
  2. Sequence metrics (averaged)
  3. Extend metrics (memory, abnormal, loadapkassets)
  4. **TOP CPU by Process Diff (TOP 5)**
  5. Priority by cycle
  6. Frequency by cycle
  7. Block I/O by cycle
  8. Binder transaction stats

### 3.3. Export Functions

#### `export_avg_to_json(dut_results, ref_results, output_folder, ...)`
- **Purpose:** Export metrics to JSON files
- **Output Files:** `app_name_dut.json`, `app_name_ref.json` in `Output/` folder
- **Format:** Per-app JSON with flattened structure

#### `create_sheet(wb, sheet_name, dut_cycles, ref_cycles, ...)`
- **Purpose:** Create Excel sheet for one app
- **Features:**
  - Main sequence table with DUT/REF/Avg/Diff columns
  - Process start overlap table
  - Memory, LoadApkAssets, Abnormal sections
  - Top CPU usage tables (Process and Thread)
  - Priority Statics table
  - Top Block I/O libraries
  - Binder transaction statistics

---

## 4. PROJECT-SPECIFIC WORKFLOWS

### 4.1. Trace Processing Flow

```
User selects DUT and REF folders
    ↓
collect_trace_files() → Get list of .log files (sorted A-Z)
    ↓
group_traces_by_app() → Group by app name using TARGET_APPS filter
    ↓
build_trace_bugreport_mapping() → Map trace → bugreport file
    ↓
process_all_traces() with multiprocessing (num_workers)
    ↓
for each trace file (in parallel):
    analyze_trace() → Call Perfetto queries
    ├── Get execution timeline metrics
    ├── Get CPU Process Data (with dumpstate name mapping)
    ├── Get CPU Thread Data
    ├── Get Priority Distribution
    ├── Get Block I/O Data
    ├── Get Binder Transaction stats
    ├── Parse dumpstate for memory/abnormal info
    │   ├── parse_pss_for_app()
    │   ├── parse_pageboostd_for_app()
    │   ├── parse_uptime()
    │   ├── parse_start_reasons()
    │   ├── parse_kill_reasons()
    │   ├── count_crashes()
    │   └── parse_compiler_type()
    └── Store precomputed data in metrics['Precomputed_Extend_Data']
    ↓
Results: {app_name: {'entry': [...], 'reentry': [...]}}
```

### 4.2. Cache System Flow

```
User requests processing
    ↓
Check .perf_cache.pkl exists in folder?
    ├─ NO
    │   ├── Process all trace files
    │   ├── Save to cache: {
    │   │     "version": "1.0",
    │   │     "target_apps": current_targets,
    │   │     "data": results
    │   │ }
    │   └── Return results
    │
    └─ YES
        └─ Check cache version
            ├─ Version mismatch
            │   └─ Re-process all → Save new cache
            │
            └─ Version matches
                └─ Compare target_apps
                    ├─ cache == current
                    │   └── Load and return (⚡ FAST)
                    │
                    ├─ cache == None (ALL)
                    │   └── Extract subset if current is specific
                    │
                    └─ cache != None and subset of current
                        └── Missing apps detected
                            ├── Process ONLY missing apps
                            ├── Merge: cached_data + new_data
                            ├── Save merged cache
                            └── Return requested subset
```

### 4.3. CPU Diff Calculation Flow

```
For each cycle in calculate_metrics_for_app():
    ├─ Determine dut_cycle and ref_cycle (based on is_dut flag)
    ├─ Get CPU_Process_Data from both cycles
    │   ├── dut_p = dut_cycle.get("CPU_Process_Data", [])
    │   └── ref_p = ref_cycle.get("CPU_Process_Data", [])
    │
    ├─ Build REF lookup maps (for fast matching)
    │   ├── ref_by_sql = {sql_name: process_data}
    │   └── ref_by_dump = {dumpstate_name: process_data}
    │
    ├─ For each process in dut_p:
    │   ├── Match REF process using Tiered Matching:
    │   │   1. Try SQL name (if not PID-xxxx)
    │   │   2. Try dumpstate name (fallback)
    │   │
    │   ├── Calculate diff = dut_val - ref_val
    │   │   ├── If match found: diff = DUT - REF
    │   │   ├── If no match + has dumpstate: diff = DUT (new process)
    │   │   └── If no match + no dumpstate: diff = 0 (skip noise)
    │   │
    │   └─ Append to matched_results
    │
    ├─ Sort matched_results by diff (descending)
    ├─ Select TOP 5
    └─ Append to cpu_cycles_data
```

### 4.4. JSON Export Flow

```
export_avg_to_json()
    ↓
For each app in all_apps:
    ├─ Get dut_entry_cycles and ref_entry_cycles
    │
    ├─ Call calculate_metrics_for_app(DUT cycles, compare=REF cycles, is_dut=True)
    │   ├── Calculate avg sequence metrics
    │   ├── Calculate extend metrics (memory, abnormal)
    │   ├── Calculate TOP 5 CPU diff
    │   ├── Calculate priority_by_cycle
    │   ├── Calculate frequency_by_cycle
    │   ├── Calculate block_io_by_cycle
    │   └── Calculate binder_transaction avg
    │
    └─ Save to app_name_dut.json
    
    ├─ Call calculate_metrics_for_app(REF cycles, compare=DUT cycles, is_dut=False)
    └─ Save to app_name_ref.json
```

---

## 5. CODE READING & UNDERSTANDING

### 5.1. Reading execution_sql.py

**Start with entry point:**
```
main_qt.py → run_analysis()
    ↓
process_all_traces() for DUT
    ↓
process_all_traces() for REF
    ↓
create_excel_output()
    ↓
export_avg_to_json()
```

**Key functions to understand:**
1. `process_all_traces()` - Core trace processing logic
2. `calculate_metrics_for_app()` - Metrics calculation for export
3. `create_sheet()` - Excel sheet creation with all sections
4. `get_or_process_folder_with_cache()` - Cache system

### 5.2. Understanding Data Flow

**Trace → Metrics Flow:**
```
Trace file (.log)
    ↓
analyze_trace() → Execute Perfetto queries
    ↓
Metrics dict with:
    ├── Timeline metrics (App Execution Time, etc.)
    ├── CPU_Process_Data: [{sql_name, dur_ms, dumpstate_name}, ...]
    ├── CPU_Thread_Data: [{thread_name, proc_name, dur_ms}, ...]
    ├── Priority_Data: {category: {priority_freq: duration_ms, ...}}
    ├── Block_IO_Data: [{libraryName, timeTotalMs}, ...]
    ├── Binder_Transaction_Data: {duration_ms, count}
    ├── Abnormal_Process_Data: [{proc_name, ...}]
    └── Precomputed_Extend_Data: {MemFree, MemAvailable, ...}
```

### 5.3. Tracing Specific Features

**To trace how a feature works:**
1. Find where it's called (grep_search feature name)
2. Read the function definition
3. Understand input/output format
4. Trace back to data source

**Example: Trace TOP 5 CPU diff**
```
grep_search: "top_process_consume_by_cycle"
    ↓
Found in calculate_metrics_for_app() (line ~2425)
    ↓
Read the section "# 3. TOP CPU BY PROCESS DIFF (TOP 5)"
    ↓
Understand logic:
    - Build REF lookup maps
    - Match processes using tiered approach
    - Calculate diff
    - Sort and select TOP 5
    ↓
Trace where data comes from:
    - dut_p = dut_cycle.get("CPU_Process_Data", [])
    - ref_p = ref_cycle.get("CPU_Process_Data", [])
    ↓
Data source: analyze_trace() in sql_query.py
```

---

## 6. REFACTORING PATTERNS SPECIFIC TO PLAN_CONVERT_SQL

### 6.1. Common Refactoring Scenarios

#### Scenario 1: Add new metric to sequence table

**Where to modify:**
1. `sql_query.py` - Add Perfetto SQL query to collect the metric
2. `execution_sql.py` - Add metric to `sequence_metrics` list
3. `execution_sql.py` - Add metric to Excel column writing logic

**Example:**
```python
# Step 1: Add SQL query in sql_query.py
query = "SELECT value FROM trace_counter_counter WHERE name = 'new_metric'"

# Step 2: Add to sequence_metrics in execution_sql.py
sequence_metrics = [
    "App Execution Time",
    ...,
    "New Metric"  # Add here
]

# Step 3: Add to Excel output in create_sheet()
val = cycle.get("New Metric", 0.0)
write_value_or_empty(ws, row_idx, col_idx, val, fmt_val)
```

#### Scenario 2: Add new section to Excel report

**Where to modify:** `create_sheet()` function in execution_sql.py

**Pattern:**
```python
# 1. Add section header
row_idx += 3
ws.merge_range(row_idx, 0, row_idx, total_cols - 1, "NEW SECTION", fmt_section_header)
row_idx += 1

# 2. Write labels and data
for metric in new_metrics:
    ws.write(row_idx, 0, metric, fmt_label)
    
    # Fill DUT data
    col_idx = 1
    for cycle in dut_cycles:
        val = cycle.get(metric, 0.0)
        write_value_or_empty(ws, row_idx, col_idx, val, fmt_section_value)
        col_idx += 1
    
    # Calculate and write DUT Avg
    # ... similar for REF Avg and Diff
    
    row_idx += 1
```

### 6.2. Critical Variable Scope Issues

**Example from code:**
```python
# BUG: Variable name collision
for cycle in dut_cycles:
    metrics = calculate_metrics(cycle)  # Local variable
    # Later...
    if metrics:  # ERROR: metrics is from last iteration only!
        process(metrics)
```

**Fix:**
```python
all_metrics = []
for cycle in dut_cycles:
    cycle_metrics = calculate_metrics(cycle)  # Different name
    all_metrics.append(cycle_metrics)

for metrics in all_metrics:
    process(metrics)
```

### 6.3. Backward-Compatible Extension Pattern

**Adding new data structure without breaking existing code:**

```python
# Extend the metrics dict
result["existing_key"] = existing_value
result["new_key"] = new_value  # Add new field

# Consumer code (use .get() to be safe)
val = result.get("new_key", default_value)  # Won't crash if key missing
```

---

## 7. PERFORMANCE OPTIMIZATION FOR PLAN_CONVERT_SQL

### 7.1. Bottleneck Identification

**Common performance issues in this codebase:**
1. **Perfetto trace processing** - Slow, uses subprocess
2. **File I/O in loops** - Reading bugreport files multiple times
3. **String operations** - Large JSON dumps
4. **Excel writing** - xlsxwriter can be slow for large data

### 7.2. Optimization Examples

#### Example 1: Pre-compute dumpstate data (Already implemented)

**Problem:** Dumpstate parsing is slow
**Solution:** Parse once at worker level, cache in `Precomputed_Extend_Data`

```python
# Worker level (already done)
def _process_single_trace_worker(args):
    # ... process trace ...
    
    # Parse dumpstate ONCE
    extend_data = {}
    extend_data['App_PSS'] = parse_pss_for_app(dumpstate_content, app_name)
    extend_data['Pageboostd'] = parse_pageboostd_for_app(dumpstate_content, app_name)
    
    # Store in metrics
    metrics['Precomputed_Extend_Data'] = extend_data
    return metrics

# Consumer level (already done)
precomp = cycle.get('Precomputed_Extend_Data', {})
pss = precomp.get('App_PSS', 0.0)  # Just read from dict
```

#### Example 2: Cache system optimization (Already implemented)

**Problem:** Re-processing same folder takes long time
**Solution:** Incremental cache that remembers processed apps

```python
# Already implemented in get_or_process_folder_with_cache()
- Check cache version
- Only process missing apps
- Merge cached + new data
- Save merged cache
```

### 7.3. Further Optimization Opportunities

1. **Lazy Excel writing:** Only write sheets for apps that actually have data
2. **Batch JSON dumps:** Combine multiple app exports into fewer writes
3. **Progressive result display:** Show partial results as they complete
4. **Cache Perfetto queries:** If same trace is analyzed multiple times

---

## 8. ERROR HANDLING & DEBUGGING

### 8.1. Common Error Scenarios

**Scenario 1: Trace file processing fails**
```python
try:
    metrics = analyze_trace(tp, file_path, pid_mapping)
except Exception as e:
    print(f"    [ERROR] {Path(file_path).name}: {e}")
    return (app_name, occurrence, category, None, filename)  # Return None
```

**Scenario 2: Cycle index out of range**
```python
for idx, cycle in valid_cycles_with_idx:
    c_comp = compare_cycles[idx] if compare_cycles and idx < len(compare_cycles) else None
    # Safe access with None check
```

**Scenario 3: Missing data in dict**
```python
val = data.get('nested', {}).get('key', 0.0)  # Safe chain access
```

### 8.2. Debug Workflow

```
1. Identify symptom (what's wrong?)
   ↓
2. Locate where it fails (grep_search, read code)
   ↓
3. Print/log relevant variables
   ↓
4. Hypothesize root cause
   ↓
5. Test hypothesis
   ↓
6. Fix + add guards
   ↓
7. Verify with real data
```

### 8.3. Debug Tools

```python
# Print cycle data
print(f"Cycle {idx}: {cycle.keys()}")

# Print CPU process data
for proc in cycle.get("CPU_Process_Data", [])[:5]:
    print(f"  {proc}")

# Check cache content
with open(cache_path, 'rb') as f:
    cache = pickle.load(f)
    print(f"Cache: {cache.keys()}")
```

---

## 9. FEATURE DEVELOPMENT

### 9.1. Adding New Metrics to JSON Export

**Steps:**
1. Identify where metric is calculated in `calculate_metrics_for_app()`
2. Add calculation logic
3. Add to result dict
4. Test with real data

**Example: Add uptime_minutes to extend data**
```python
# Already in calculate_metrics_for_app() (line ~2350)
for _, cycle in valid_cycles_with_idx:
    precomp = cycle.get('Precomputed_Extend_Data', {})
    ut = precomp.get('Uptime', 0)
    if ut and ut > 0: uptime_vals.append(ut)

if uptime_vals: abnormal_info["uptime_minutes"] = round(sum(uptime_vals)/len(uptime_vals), 2)
```

### 9.2. Modifying CPU Diff Logic

**Location:** `calculate_metrics_for_app()`, section "# 3. TOP CPU BY PROCESS DIFF"

**Examples of changes:**
- Change TOP 5 to TOP 10
- Add filter threshold (ignore diff < 10ms)
- Change matching logic
- Add new fields (dut_time, ref_time)

### 9.3. Changing JSON Format

**Location:** `calculate_metrics_for_app()`

**Example: Format change for priority_by_cycle**
```python
# Old format (dict):
"priority": {
    "120": 100.0
}

# New format (list of objects):
"priority": [
    {"priority": 120, "percentage": 100.0}
]

# Already implemented (line ~2480)
prio_list = []
for prio_id, pct in prio_acc.items():
    percentage = round((pct/total_dur)*100, 2)
    if percentage > 0:
        prio_list.append({
            "priority": int(prio_id),
            "percentage": percentage
        })
```

---

## 10. CODE QUALITY CHECKLIST SPECIFIC TO PLAN_CONVERT_SQL

```
□ CORRECTNESS
  □ Trace file grouping correct (entry/re-entry alternation)?
  □ Cycle index calculation correct (occurrence // 2)?
  □ Masking logic correct for Cold/Warm metrics?
  □ Cache merge logic preserves all data?
  □ CPU diff calculation correct (DUT - REF)?
  □ Priority/Frequency percentage sums to ~100%?

□ ROBUSTNESS
  □ Handle missing trace files gracefully?
  □ Handle None cycles in valid_cycles_with_idx?
  □ Safe dict access with .get() and defaults?
  □ Cache version validation?
  □ Exception handling in worker processes?

□ PERFORMANCE
  □ Dumpstate parsed once (Precomputed_Extend_Data)?
  □ Cache system working (not re-processing)?
  □ Multiprocessing enabled (num_workers)?
  □ No I/O in tight loops?
  □ Lazy evaluation where possible?

□ MAINTAINABILITY
  □ Clear function names?
  □ Consistent code style?
  □ Type hints where appropriate?
  □ Backward compatible extensions?
  □ Comments explain WHY (not just WHAT)?

□ PLAN_CONVERT_SQL SPECIFIC
  □ TOP 5 CPU processes have correct diff?
  □ Priority by cycle format correct (list of objects)?
  □ Frequency by cycle separate from priority?
  □ JSON export includes all necessary fields?
  □ Excel tables have correct column structure?
  □ Cache file format valid?
```

---

## 11. TOOL USAGE BEST PRACTICES FOR PLAN_CONVERT_SQL

### 11.1. Recommended tool usage order

| Task | First tool | Second tool | Third tool |
|------|-----------|-------------|-----------|
| Understand new feature | `grep_search` (feature name) | `read_file` (function) | Trace data flow |
| Add new metric | `grep_search` (similar metric) | `read_file` (current code) | `replace_in_file` |
| Fix bug | `grep_search` (error message) | `read_file` (context) | `replace_in_file` |
| Refactor function | `read_file` (entire function) | `write_to_file` or `replace_in_file` | Verify |
| Debug cache issue | `read_file` (cache logic) | Add debug prints | Test |
| Modify Excel format | `read_file` (create_sheet) | `replace_in_file` | Test with data |

### 11.2. Key files to understand

**For trace processing:**
- `sql_query.py` - All Perfetto queries
- `execution_sql.py::process_all_traces()` - Main processing loop
- `execution_sql.py::_process_single_trace_worker()` - Worker logic

**For export:**
- `execution_sql.py::export_avg_to_json()` - JSON export
- `execution_sql.py::create_sheet()` - Excel creation

**For cache:**
- `execution_sql.py::get_or_process_folder_with_cache()` - Cache logic

**For parsing:**
- `dumpstate_parser.py` - Bugreport parsing functions

---

## 12. EXAMPLE WORKFLOWS

### 12.1. Add new metric to sequence table

**User request:** "Add 'Jank Count' to the sequence table in Excel"

**Steps:**
1. Check if Perfetto already collects this metric
   ```bash
   grep_search -r "jank" sql_query.py
   ```

2. Add SQL query in sql_query.py
   ```python
   # Add new query function
   def get_jank_count(tp):
       query = "SELECT value FROM trace_counter_counter WHERE name = 'jank_count'"
       result = tp.query(query)
       return result[0]['value'] if result else 0
   ```

3. Add metric to metrics dict in analyze_trace()
   ```python
   metrics['Jank Count'] = get_jank_count(tp)
   ```

4. Add to sequence_metrics list in calculate_metrics_for_app()
   ```python
   sequence_metrics = [
       "App Execution Time",
       ...
       "Jank Count"
   ]
   ```

5. Verify Excel output with real data

### 12.2. Change TOP 5 to TOP 10 in CPU diff

**Steps:**
1. Find the code
   ```bash
   grep_search "TOP 5"
   ```

2. Locate line: `top_5 = sorted(matched_results, key=lambda x: x['diff'], reverse=True)[:5]`

3. Change to TOP 10
   ```python
   top_10 = sorted(matched_results, key=lambda x: x['diff'], reverse=True)[:10]
   cpu_cycles_data.append({
       "cycle": idx + 1,
       "process": top_10  # Update variable name
   })
   ```

4. Test with real DUT/REF data

### 12.3. Add new section to Excel report

**Example:** Add "Temperature" section

**Steps:**
1. Parse temperature data in worker (dumpstate_parser.py)
   ```python
   def parse_temperature(dumpstate_content):
       # Parse temp values
       return {"cpu_temp": 45.2, "battery_temp": 36.8}
   ```

2. Add to Precomputed_Extend_Data in worker
   ```python
   extend_data['Temperature'] = parse_temperature(dumpstate_content)
   ```

3. Add section in create_sheet()
   ```python
   row_idx += 3
   ws.merge_range(row_idx, 0, row_idx, total_cols - 1, "TEMPERATURE", fmt_section_header)
   row_idx += 1
   
   for temp_metric in ["CPU Temperature (°C)", "Battery Temperature (°C)"]:
       ws.write(row_idx, 0, temp_metric, fmt_label)
       # Fill data from precomputed...
       row_idx += 1
   ```

---

## SUMMARY

This skill provides comprehensive knowledge for working with Plan_convert_SQL codebase, including:

- **Architecture understanding** of the trace analysis pipeline
- **Key functions** and their roles in the system
- **Project-specific workflows** (trace processing, cache, CPU diff, JSON export)
- **Refactoring patterns** specific to this codebase
- **Performance optimizations** relevant to trace analysis
- **Error handling** strategies
- **Feature development** guidelines
- **Code quality checklist** for Plan_convert_SQL

When activated, Cline will have deep knowledge of the Plan_convert_SQL tool and can effectively:
- Read and understand the codebase
- Implement new features and metrics
- Refactor existing code
- Debug issues
- Optimize performance
- Extend functionality

Use this skill when working on execution_sql.py, adding metrics, modifying export formats, or improving the trace analysis pipeline.