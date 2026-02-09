---
description: Analyze performance data from JSON and diagnose DUT vs REF issues
---

# Performance Analysis Workflow

## Overview
Workflow để Agent phân tích `analysis_input.json` và diagnose tại sao DUT chậm hơn REF.

## Input Files
- `{DUT_folder}/Output/analysis_input.json` - Combined comparison data

## Knowledge Base Structure
```
knowledge/
├── diagnosis_rules.json      # Master rules - check paths cho mỗi state
├── solutions.json            # Solutions database
├── team_responsibility.json  # Team mapping
└── tables/                   # Table-specific analysis rules
    ├── sequence.json        # State metrics (Running, Runnable, etc.)
    ├── top_cpu.json         # Top CPU process/thread
    ├── priority.json        # Priority distribution
    ├── block_io.json        # Block I/O libraries
    ├── loadapk.json         # LoadApkAssets
    ├── memory.json          # Memory metrics
    ├── abnormal.json        # Abnormal process/activity
    ├── binder.json          # Binder transaction
    └── frequency.json       # CPU frequency (TODO)
```

---

## Analysis Flow

### Step 1: Identify Primary Issue
Đọc `analysis_input.json` → `apps.{app}.{launch_type}.state_diff`

Tìm state có diff lớn nhất vượt threshold:
- Running diff > 10ms → CPU issue
- Runnable diff > 10ms → Priority/Scheduling issue
- Uninterruptible Sleep diff > 30ms → I/O issue
- Sleeping diff > 10ms → IPC issue

### Step 2: Follow Check Paths
Đọc `knowledge/diagnosis_rules.json` → `diagnosis_flow.{state}.check_paths`

Mỗi check_path trỏ đến 1 table JSON:
```json
{
  "path_id": "run_1",
  "table_ref": "tables/abnormal.json",
  "data_key": "abnormal_process_start",
  "condition": "Có process nào start trong khi app launch"
}
```

### Step 3: Analyze Each Table
Với mỗi table_ref, đọc file tương ứng và phân tích theo logic trong đó.

### Step 4: Generate Report
Output structured report với:
1. Primary issue (state)
2. Check results từ mỗi table
3. Team responsible (từ `team_responsibility.json`)
4. Solutions (từ `solutions.json` nếu có)

---

## Output Format
```markdown
## Performance Analysis Report

### Summary
- App: {app_name}
- Launch Type: {entry/reentry}
- DUT Slower by: XX ms
- Primary Issue: [Running/Runnable/Uninterruptible Sleep/Sleeping]

### Check Results

#### 1. {Check Name} ({table_ref})
- **Finding**: [Mô tả finding]
- **Evidence**: [Data từ JSON]
- **Team**: [Team name]
- **Solution**: [Nếu có trong knowledge base]

...
```

---

## How to Extend

### Add new check:
1. Thêm check path mới vào `diagnosis_rules.json`
2. Tạo/update table JSON tương ứng trong `tables/`

### Add new solution:
1. Update `solutions.json` với problem-solution mapping

### Add new table:
1. Tạo file `tables/{table_name}.json`
2. Reference trong `diagnosis_rules.json`
