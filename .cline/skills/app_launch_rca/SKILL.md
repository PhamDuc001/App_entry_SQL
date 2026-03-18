---
name: app_launch_rca
description: Phân tích JSON output từ execution_sql (DUT vs REF), áp dụng 3-flow rule-based diagnostic, tạo root-cause report với team routing cho Performance Engineer.
---
# App Launch Performance Root-Cause Analysis

## Overview

Skill này cho phép AI agent phân tích dữ liệu app launch performance từ Android devices. Agent nhận JSON output từ `execution_sql` pipeline, so sánh DUT (Device Under Test) vs REF (Reference), và chạy qua **3 diagnostic flows** để identify root-cause và suggest team routing.

## Input Data

### JSON Files
- **DUT JSON**: `DUT_<model>_<ram>_<timestamp>.json` hoặc `DUT_<model>_<version>_<timestamp>.json` – Chứa failed apps data
- **REF JSON**: `REF_<model>_<ram>_<timestamp>.json` hoặc `REF_<model>_<version>_<timestamp>.json`– Reference baseline data
- Cả 2 file có cùng schema (xem `references/json_schema.md`)

### Cách locate files
- JSON files nằm trong thư mục `Output/` của mỗi test session
- Tên file chứa device_code, RAM size, và timestamp
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
- **Source**: `extend.abnormal.uptime_minutes` (cả DUT và REF)
- **Rule**: Nếu DUT.uptime > 10 mins HOẶC REF.uptime > 10 mins
- **Result**: ⚠️ "Test condition invalid – uptime > 10 mins" → Suggest re-test

#### Check 1.2: ANR/FATAL Check  
- **Source**: Crash count data (nếu có trong extend)
- **Rule**: Nếu tồn tại ANR hoặc FATAL EXCEPTION
- **Result**: 🔴 "FATAL or ANR detected" → Suggest check FATAL/ANR detail

#### Check 1.3: Touch Duration Check
- **Source**: `sequence["Touch Down ~ Start Proc"]` (DUT vs REF)
- **Rule**: Nếu DUT.touch_duration - REF.touch_duration > 10ms
- **Result**: ⚠️ "Touch duration higher on DUT by {diff} ms" → Suggest system team

### Step 3: Flow 2 – Core Performance State Analysis (per app)

#### Check 2.1: Running Time
- **Source**: `sequence.Running` (DUT vs REF)
- **Threshold**: DUT.Running - REF.Running > 50ms
- **On True**:
  - Report: "Running time increased {diff} ms" → Suggest app team
  - **Sub-check 2.1a – Compiler**:
    - Source: `extend.abnormal.compiler`
    - Rule: Nếu DUT.compiler == "verify" VÀ DUT.compiler ≠ REF.compiler
    - Result: "Compiler type is verify" → Suggest app TG apply speed-profile
  - **Sub-check 2.1b – CPU Frequency**:
    - Source: `frequency_by_cycle`
    - Rule: So sánh % thời gian ở **highest frequency** (cycle by cycle, section by section). Flag nếu DUT chạy significantly ít hơn ở high frequency so với REF (>15% diff)
    - Result: "App running at lower CPU frequency" → Suggest system team

#### Check 2.2: Sleeping Time
- **Source**: `sequence.Sleeping` (DUT vs REF)
- **Threshold**: DUT.Sleeping - REF.Sleeping > 50ms
- **On True**:
  - **Sub-check: Binder Transaction**:
    - Source: `binder_transaction.count`
    - Rule: DUT.count - REF.count > 10
    - Result: "Binder transactions increased by {diff}" → Suggest app team

#### Check 2.3: Runnable Time
- **Source**: `sequence.Runnable` (DUT vs REF)
- **Threshold**: DUT.Runnable - REF.Runnable > 50ms
- **On True**:
  - **Sub-check: Thread Priority**:
    - Source: `priority_by_cycle`
    - Rule: So sánh priority distribution (higher value = lower priority). Flag nếu DUT có ít high-priority time hơn REF (>15% diff)
    - Result: "Lower thread priority on DUT" → Suggest system team

#### Check 2.4: Start State (Cold/Warm Mismatch)
- **Source**: `State` array (DUT vs REF)
- **Rule**: DUT.State == "Cold" AND REF.State == "Warm" (trên cùng cycle)
- **On True**:
  - **Sub-check 2.4a – Start/Kill Reasons**:
    - Source: `extend.abnormal.start_reasons`
    - Rule: DUT start_reason count ≠ REF start_reason count
    - Result: "App start/kill count differs" → Suggest app team

### Step 4: Flow 3 – Resource Usage & Process Analysis (per app)

#### Check 3.1: Uninterruptible Sleep (Block I/O)
- **Source**: `sequence["Uninterruptible Sleep"]` (DUT vs REF)
- **Threshold**: DUT - REF > 30ms
- **On True**:
  - **Sub-check 3.1a – Memory**:
    - Source: `extend.memory.MemFree_MB`, `extend.memory.MemAvailable_MB`
    - Rule: REF.MemFree - DUT.MemFree > 50 MB OR REF.MemAvailable - DUT.MemAvailable > 50 MB
    - Result: "Memory decreased" → Suggest Kernel Memory team
  - **Sub-check 3.1b – Pageboost**:
    - Source: `extend.memory.Pageboostd_MB`
    - Rule: REF.Pageboostd - DUT.Pageboostd > 10 MB
    - Result: "Pageboost prefetch decreased by {diff} MB" → Suggest Kernel Memory team
  - **Sub-check 3.1c – Block I/O Detail**:
    - Source: `block_io_by_cycle`
    - Analysis: List top libraries causing Block I/O, compare DUT vs REF

#### Check 3.2: Abnormal Processes
- **Source**: `extend.start_process_abnormal` (per cycle)
- **Rule**: Nếu có bất kỳ process_name nào trong danh sách
- **Result**: "Parallel process detected: {process_name}" → Suggest App team + SWPL

#### Check 3.3: Top CPU Consumers
- **Source**: `top_process_consume_by_cycle`
- **Threshold**: Nếu process.diff > 300ms ở bất kỳ cycle
- **Result**: "Process {name} consuming too much CPU: diff {diff} ms in cycle {cycle}" → Suggest SWPL check

#### Check 3.4: PSS Memory
- **Source**: `extend.memory.App_PSS_MB` (DUT vs REF)
- **Threshold**: DUT.PSS - REF.PSS > 50 MB
- **Result**: "PSS memory increased by {diff} MB" → Suggest app owner

#### Check 3.5: LoadApkAsset
- **Source**: `extend.loadapkassets` (DUT vs REF)
- **Threshold**: LoadApkAsset time > 50ms
- **On True**:
  - **Primary Check**:
    - Nếu DUT có loadapkassets và REF không có:
      - Report: "LoadApkAsset detected on DUT (total {total} ms, {count} processes) but not on REF"
      - List các processes và thời gian chi tiết
      - Flag issue
    - Nếu cả DUT và REF đều có loadapkassets:
      - So sánh tổng time: DUT.total - REF.total > 50ms
        - Report: "LoadApkAsset increased by {diff} ms (DUT: {dut_total} ms, REF: {ref_total} ms)"
        - Flag issue
      - So sánh số processes: DUT.count > REF.count
        - Report: "DUT has more LoadApkAsset processes ({dut_count}) than REF ({ref_count})"
        - Flag issue
  - **Sub-check 3.5a – Pageboost Correlation**:
    - Source: `extend.memory.Pageboostd_MB`
    - Analysis: Nếu LoadApkAsset cao, kiểm tra Pageboostd_MB
    - Rule: REF.Pageboostd - DUT.Pageboostd > 10 MB
    - Result: "Pageboost prefetch decreased by {diff} MB - likely causing LoadApkAsset slowdown" → Suggest Kernel Memory team
  - **Sub-check 3.5b – Memory Status**:
    - Source: `extend.memory.MemFree_MB`, `extend.memory.MemAvailable_MB`
    - Analysis: Nếu LoadApkAsset cao, kiểm tra memory shortage
    - Rule: REF.MemFree - DUT.MemFree > 50 MB OR REF.MemAvailable - DUT.MemAvailable > 50 MB
    - Result: "Memory decreased - APK cache likely evicted, causing disk I/O" → Suggest Kernel Memory team
  - **Recommendation**: System Team → Review APK resources.arsc size, LoadApkAsset, investigate Pageboost prefetch mechanism

### Step 5: Report Generation

Sau khi chạy 3 flows, tổng hợp report:

```markdown
# Performance Analysis Report
## Test Info
- DUT: {device_code} version {version}
- REF: {device_code} version {version}  
- Timestamp: {timestamp}

## Summary
| App | Status | Key Issues |
|-----|--------|-----------|
| calculator | ⚠️ | Running +35ms, Compiler verify |
| gallery | 🔴 | D-state +253ms, start_process_abnormal |

## Detailed Findings
### [App Name]
#### Flow 1 Results
...
#### Flow 2 Results  
...
#### Flow 3 Results
...
#### Recommendations
- [Team] → [Action]
```

---

## Interactive Q&A

Agent có thể trả lời các câu hỏi cụ thể:
- "App Camera bị chậm ở đâu?" → Focus vào sequence breakdown của camera
- "Tại sao Running tăng?" → Check compiler, frequency, top CPU
- "Pageboost có vấn đề gì?" → So sánh Pageboostd_MB
- "Cycle nào xấu nhất?" → So sánh top_process_consume across cycles

---

## Important Rules

1. **NEVER fabricate data** – Chỉ report data có trong JSON
2. **Always compare DUT vs REF** – Mọi finding phải có so sánh
3. **Report both positives and negatives** – Nếu check pass, cũng ghi nhận
4. **Use thresholds from workflow** – Không tự ý thay đổi threshold
5. **Route to correct team** – Xem `references/team_routing.md`
6. **Ask clarifying questions** khi data ambiguous hoặc thiếu context
7. **NEVER create report files** – KHÔNG tự động tạo file .md, .py, hoặc bất kỳ file report nào
   - Chỉ print toàn bộ nội dung report trong khung chat (message response)
   - Nếu user yêu cầu lưu file → Hỏi xác nhận trước khi tạo
   - Nếu user reject → Agent hiểu và chỉ print, không tạo lại file khác

## References

- [json_schema.md](references/json_schema.md) – JSON structure
- [workflow_rules.md](references/workflow_rules.md) – 3-flow rules detail
- [metric_glossary.md](references/metric_glossary.md) – Metric definitions
- [team_routing.md](references/team_routing.md) – Issue → Team mapping
