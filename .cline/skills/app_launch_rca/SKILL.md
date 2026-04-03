---
name: app_launch_rca
description: Phân tích JSON output từ execution_sql (DUT vs REF), áp dụng 3-flow rule-based diagnostic với per-cycle anomaly detection, tạo root-cause report với team routing cho Performance Engineer.
---
# App Launch Performance Root-Cause Analysis (v3 – Per-Cycle)

## Overview

Skill này cho phép AI agent phân tích dữ liệu app launch performance từ Android devices. Agent nhận JSON output từ `execution_sql` pipeline, so sánh DUT (Device Under Test) vs REF (Reference), và chạy qua **3 diagnostic flows** để identify root-cause và suggest team routing.

### ⚠️ CRITICAL – Per-Cycle Data Format (v3)

> Từ v3 trở đi, `sequence` metrics là **array per-cycle** thay vì scalar average.  
> Ví dụ: `"Running": [256.6, 252.0, 259.8]` thay vì `"Running": 256.2`.  
> Agent PHẢI phân tích **từng cycle** để phát hiện spike bị average che giấu.

**Cách tính average từ per-cycle data:**
```python
values = [v for v in sequence["Running"] if v > 0]  # Loại 0.0 (no data)
avg = sum(values) / len(values) if values else 0
```

**Tương tự cho memory/uptime:**
- `extend.memory.MemFree_MB` → `[1800, 1200, 1500]` (per-cycle) + `MemFree_MB_avg` → `1500.33`
- `extend.abnormal.uptime_minutes` → `[7, 7, 7]` (per-cycle) + `uptime_minutes_avg` → `7.0`

---

## Knowledge Base

**IMPORTANT**: Agent PHẢI đọc knowledge base trước khi phân tích!

### Step 0: Load Knowledge (BẮT BUỘC)

1. **Đọc INDEX.md trước**: `knowledge/INDEX.md`
   - Đây là chỉ mục toàn bộ knowledge base
   - Tìm các articles liên quan đến vấn đề đang phân tích

2. **Đọc articles cụ thể dựa trên tags**:
   - Khi thấy Cold/Warm/Hot launch → Đọc `knowledge/android_framework/app_launch_internals.md`
   - Khi thấy D-state/Block I/O → Đọc `knowledge/os_internals/io_and_storage.md`
   - Khi thấy Runnable/Priority bất thường → Đọc `knowledge/os_internals/cpu_scheduling.md`
   - Khi thấy Memory metrics bất thường → Đọc `knowledge/os_internals/memory_management.md`
   - Khi thấy Binder count cao → Đọc `knowledge/android_framework/binder_ipc.md`

3. **Áp dụng kiến thức vào phân tích**:
   - Sử dụng knowledge để giải thích root cause
   - Refer đến specific sections trong knowledge articles
   - Áp dụng suggested actions từ knowledge

---

## Input Data

### JSON Files
- **DUT JSON**: `DUT_<model>_<version>_<timestamp>.json` – Chứa DUT data
- **REF JSON**: `REF_<model>_<version>_<timestamp>.json` – Reference baseline data
- Cả 2 file có cùng schema (xem `references/json_schema.md`)

### Cách locate files
- JSON files nằm trong thư mục `Output/` của mỗi test session
- Tên file chứa model, version, và timestamp
- Luôn **yêu cầu user cung cấp đường dẫn** đến cả DUT và REF JSON files

---

## Analysis Workflow

### Step 1: Data Loading & Validation

1. **Load** cả DUT và REF JSON files
2. **Validate** data completeness:
   - Kiểm tra có `apps_data` không
   - Kiểm tra mỗi app có đủ `sequence`, `extend`, `top_process_consume_by_cycle`, `priority_by_cycle`, `frequency_by_cycle`, `block_io_by_cycle`, `binder_transaction` không
   - Ghi chú các fields bị thiếu (không phải lỗi, một số app có thể không có đầy đủ sections)
3. **Match apps**: Tìm các app có mặt trong CẢ DUT và REF

### Step 2: Flow 1 – Initial Validation (per app)

Chạy cho **mỗi app** trong `apps_data`:

#### Check 1.1: Uptime Check
- **Source**: `extend.abnormal.uptime_minutes` (per-cycle array) và `uptime_minutes_avg`
- **Rule**: Nếu **bất kỳ cycle nào** có uptime > 10 mins (DUT hoặc REF)
- **Result**: ⚠️ "Test condition invalid – uptime > 10 mins at cycle {N}" → Suggest re-test
- **Lưu ý**: Kiểm tra từng cycle, ví dụ `uptime_minutes: [5, 12, 7]` → Cycle 2 invalid

#### Check 1.2: ANR/FATAL Check  
- **Source**: Crash count data (nếu có trong extend)
- **Rule**: Nếu tồn tại ANR hoặc FATAL EXCEPTION
- **Result**: 🔴 "FATAL or ANR detected" → Suggest check FATAL/ANR detail

#### Check 1.3: Touch Duration Check
- **Source**: `sequence["Touch Down ~ Start Proc"]` (DUT vs REF, per-cycle)
- **Rule**: Tính avg DUT - avg REF > 10ms, HOẶC bất kỳ cycle nào có diff > 15ms
- **Result**: ⚠️ "Touch duration higher on DUT by {diff} ms" → Suggest system team

### Step 3: Flow 2 – Core Performance State Analysis (per app)

> **CRITICAL**: Tất cả checks dưới đây PHẢI phân tích TỪNG CYCLE + average.

#### Check 2.1: Running Time
- **Source**: `sequence.Running` (DUT vs REF, per-cycle arrays)
- **Threshold (Average)**: avg(DUT.Running) - avg(REF.Running) > 50ms
- **Threshold (Per-Cycle)**: Nếu **≥2 cycles** có diff > 50ms → Flag ngay cả khi avg < 50ms
- **Spike Detection**: Nếu 1 cycle khác biệt lớn so với các cycles khác (>2x) → Flag "Cycle {N} spike"
- **On True**:
  - Report: "Running time increased {avg_diff} ms (cycles: {per_cycle_diffs})"
  - **Sub-check 2.1a – Compiler**: `extend.abnormal.compiler`
  - **Sub-check 2.1b – CPU Frequency**: `frequency_by_cycle`

#### Check 2.2: Sleeping Time
- **Source**: `sequence.Sleeping` (DUT vs REF, per-cycle arrays)
- **Threshold (Average)**: avg(DUT.Sleeping) - avg(REF.Sleeping) > 50ms
- **Threshold (Per-Cycle)**: Nếu **≥2 cycles** có diff > 50ms → Flag
- **On True**:
  - **Sub-check: Binder Transaction**: `binder_transaction.count` DUT vs REF

#### Check 2.3: Runnable Time
- **Source**: `sequence.Runnable` (DUT vs REF, per-cycle arrays)
- **Threshold (Average)**: avg > 50ms diff
- **Threshold (Per-Cycle)**: Nếu **≥2 cycles** có diff > 50ms
- **On True**:
  - **Sub-check: Thread Priority**: `priority_by_cycle`

#### Check 2.4: Start State (Cold/Warm Mismatch)
- **Source**: `State` array (DUT vs REF)
- **Rule**: DUT.State[i] == "Cold" AND REF.State[i] == "Warm" (trên cùng cycle i)
- **On True**:
  - **Sub-check 2.4a – Start/Kill Reasons**: `extend.abnormal.start_reasons`

### Step 4: Flow 3 – Resource Usage & Process Analysis (per app)

#### Check 3.1: Uninterruptible Sleep (Block I/O)
- **Source**: `sequence["Uninterruptible Sleep"]` (per-cycle arrays)
- **Threshold (Average)**: avg diff > 30ms
- **Threshold (Per-Cycle)**: Nếu **≥2 cycles** có diff > 30ms
- **On True**:
  - **Sub-check 3.1a – Memory** (per-cycle):
    - Source: `extend.memory.MemFree_MB` (array), `extend.memory.MemAvailable_MB` (array)
    - Rule: So sánh TỪNG CYCLE: REF.MemFree[i] - DUT.MemFree[i] > 50 MB
    - Report per-cycle diffs, highlight cycles có memory drop lớn
  - **Sub-check 3.1b – Pageboost** (per-cycle):
    - Source: `extend.memory.Pageboostd_MB` (array)
    - Rule: So sánh TỪNG CYCLE: REF.Pageboostd[i] - DUT.Pageboostd[i] > 10 MB
  - **Sub-check 3.1c – Block I/O Detail**: `block_io_by_cycle`

#### Check 3.2: Abnormal Processes
- **Source**: `extend.start_process_abnormal` (per cycle – already per-cycle in v2)
- **Rule**: Nếu có bất kỳ process_name nào trong danh sách
- **NEW – Cross-cycle correlation**: 
  - So sánh DUT vs REF: Process xuất hiện ở DUT nhưng không ở REF
  - Correlate: Process xuất hiện ở cycle N → kiểm tra sequence metrics ở cycle N có spike không

#### Check 3.3: Top CPU Consumers
- **Source**: `top_process_consume_by_cycle`
- **Threshold**: process.diff > 300ms ở bất kỳ cycle
- **Result**: "Process {name} consuming too much CPU: diff {diff} ms in cycle {cycle}"

#### Check 3.4: PSS Memory (per-cycle)
- **Source**: `extend.memory.App_PSS_MB` (per-cycle array)
- **Threshold**: avg diff > 50 MB, HOẶC bất kỳ cycle nào có diff > 70 MB
- **Result**: "PSS memory increased by {diff} MB (cycle breakdown: {per_cycle})"

#### Check 3.5: LoadApkAsset
- **Source**: `extend.loadapkassets` (DUT vs REF)
- **Threshold**: LoadApkAsset time > 50ms
- **Correlation**: So sánh với `Pageboostd_MB` per-cycle và `MemFree_MB` per-cycle

### ⭐ NEW: Step 4.5 – Per-Cycle Anomaly Detection

> **Đây là bước QUAN TRỌNG NHẤT trong v3.**

Chạy sau Flow 3, cho **mỗi app**:

1. **Cycle Consistency Check**: So sánh giá trị từng cycle trong `sequence`:
   - Nếu 1 cycle có giá trị > 2x giá trị trung bình → "Outlier at Cycle {N}"
   - Ví dụ: `"Activity Thread Main": [52.3, 50.1, 20.5]` → Cycle 3 thấp hơn nhiều

2. **Cross-Version Spike Pattern**: So sánh DUT vs REF per-cycle:
   - REF: `"Activity Thread Main": [50.0, 20.0, 20.0]` (1/3 cycles spike)
   - DUT: `"Activity Thread Main": [52.3, 50.1, 20.5]` (2/3 cycles spike)
   - → "Spike worsened: REF 1/3 cycles → DUT 2/3 cycles"
   - → Average chỉ diff 10ms nhưng PATTERN CHANGE là significant

3. **Memory Stability Check**: So sánh `extend.memory` per-cycle:
   - Nếu MemFree dao động lớn giữa cycles (max - min > 100 MB) → "Memory instability"

4. **Uptime per-cycle**: Kiểm tra uptime_minutes per-cycle:
   - Nếu 1 cycle có uptime khác biệt lớn → Flag "Inconsistent test condition"

### Step 5: Report Generation

Sau khi chạy 3 flows + per-cycle anomaly detection, tổng hợp report:

```markdown
# Performance Analysis Report
## Test Info
- DUT: {model} {device_code} version {version}
- REF: {model} {device_code} version {version}  
- Timestamp: {timestamp}

## Summary
| App | Status | Key Issues | Per-Cycle Anomaly |
|-----|--------|-----------|-------------------|
| calculator | ⚠️ | Running +35ms | Cycle 2,3 spike ActivityThreadMain |
| gallery | 🔴 | D-state +253ms | MemFree drop at Cycle 2 |

## Detailed Findings
### [App Name]
#### Per-Cycle Timing (DUT)
| Metric | Cycle 1 | Cycle 2 | Cycle 3 | Avg | Flag |
|--------|---------|---------|---------|-----|------|
| Running | 220.5 | 235.1 | 243.7 | 233.1 | 📈 Increasing |
| D-state | 5.0 | 280.0 | 10.0 | 98.3 | ⚡ Cycle 2 spike |

#### Per-Cycle Timing (REF)
[Tương tự bảng trên]

#### Per-Cycle Diff (DUT - REF)
| Metric | Cycle 1 | Cycle 2 | Cycle 3 | Avg Diff | Pattern |
|--------|---------|---------|---------|----------|---------|
| Running | +22.2 | +29.7 | +33.2 | +28.4 | 📈 Worsening |
| D-state | +2.0 | +253.0 | +5.0 | +86.7 | ⚡ Cycle 2 only |

#### Flow 1/2/3 Results
...
#### Recommendations
- [Team] → [Action]
```

---

## Interactive Q&A

Agent có thể trả lời các câu hỏi cụ thể:
- "App Camera bị chậm ở đâu?" → Focus vào per-cycle sequence breakdown
- "Tại sao Running tăng ở cycle 2?" → Check frequency, priority, top CPU ở cycle 2
- "Cycle nào xấu nhất?" → So sánh per-cycle diff
- "ActivityThreadMain spike ở bao nhiêu cycle?" → Đếm cycles vượt threshold
- "Memory có ổn định không?" → Check per-cycle MemFree/MemAvailable variance

---

## Important Rules

1. **NEVER fabricate data** – Chỉ report data có trong JSON
2. **Always compare DUT vs REF** – Mọi finding phải có so sánh
3. **Per-Cycle FIRST, Average SECOND** – Luôn phân tích từng cycle TRƯỚC rồi mới tính average
4. **Report both positives and negatives** – Nếu check pass, cũng ghi nhận
5. **Use thresholds from workflow** – Không tự ý thay đổi threshold
6. **Route to correct team** – Xem `references/team_routing.md`
7. **Ask clarifying questions** khi data ambiguous hoặc thiếu context
8. **NEVER create report files** – KHÔNG tự động tạo file .md, .py, hoặc bất kỳ file report nào
   - Chỉ print toàn bộ nội dung report trong khung chat (message response)
   - Nếu user yêu cầu lưu file → Hỏi xác nhận trước khi tạo
   - Nếu user reject → Agent hiểu và chỉ print, không tạo lại file khác
9. **Pattern > Average** – Pattern thay đổi (1/3 → 2/3 cycles spike) quan trọng hơn average diff nhỏ

## References

- [json_schema.md](references/json_schema.md) – JSON structure (v3)
- [workflow_rules.md](references/workflow_rules.md) – 3-flow rules detail
- [metric_glossary.md](references/metric_glossary.md) – Metric definitions
- [team_routing.md](references/team_routing.md) – Issue → Team mapping
