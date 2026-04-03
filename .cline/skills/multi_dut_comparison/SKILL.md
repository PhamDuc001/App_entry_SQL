---
name: multi_dut_comparison
description: So sánh performance data từ nhiều DUT devices (variants) cùng 1 REF baseline, phân tích per-cycle để phát hiện device-specific vs common issues.
---

# Multi-DUT Performance Comparison (v3 – Per-Cycle)

## Overview

Skill này cho phép AI agent so sánh dữ liệu app launch performance từ **nhiều DUT devices** (ví dụ: 4GB, 6GB, 8GB variants) cùng **1 REF baseline**. Agent sẽ identify issues chung (common across DUTs) vs riêng lẻ (device-specific), giúp PE xác định scope ảnh hưởng và phân bổ root-cause chính xác hơn.

### ⚠️ v3 – Per-Cycle Data

> Từ v3, `sequence` metrics là **array per-cycle** (e.g., `[220, 235, 244]`).  
> Agent PHẢI so sánh từng cycle across DUTs để phát hiện variant-specific spike patterns.

**Cách tính average:**
```python
values = [v for v in metric_array if v > 0]
avg = sum(values) / len(values) if values else 0
```

## Input Data

### Required
- **Nhiều DUT JSON files**: Từ các test sessions khác nhau (khác device_code/variant)
- **1 REF JSON file**: Baseline chung

### JSON Schema
Xem `../app_launch_rca/references/json_schema.md` để hiểu cấu trúc JSON v3.

---

## Analysis Workflow

### Step 1: Load & Normalize
1. Load tất cả DUT JSON files và REF JSON file(s)
2. Xác định `device_code` và `version` của mỗi file
3. Tìm **common apps**: apps có mặt trong TẤT CẢ DUT files
4. **Tính average** từ per-cycle arrays cho mỗi metric

### Step 2: Per-App Cross-DUT Comparison (Average)

Cho mỗi app, tạo comparison table sử dụng **average values**:

```markdown
### App: calculator (entry)

| Metric | REF (BOS/ZB1) | DUT1 (4GB/ZC1) | DUT2 (6GB/ZC1) | DUT3 (8GB/ZC1) |
|--------|---------------|-----------------|-----------------|-----------------|
| App Execution Time | 504.77 | 612.34 | 540.37 | 560.21 |
| Running | 204.74 | 280.12 | 233.12 | 245.89 |
| Sleeping | 238.80 | 250.34 | 227.22 | 235.11 |
| D-state | 6.96 | 45.23 | 18.96 | 12.34 |
| Compiler | verify | verify | verify | speed-profile |
| Binder count | 97 | 125 | 100 | 102 |
```

### Step 2.5: Cross-DUT Per-Cycle Pattern Analysis (NEW)

> **CRITICAL**: So sánh PATTERN của per-cycle data giữa các DUTs.

Cho mỗi metric flagged ở Step 2:

```markdown
### calculator – Running per-cycle across DUTs

| Cycle | REF | DUT1 (4GB) | DUT2 (6GB) | DUT3 (8GB) |
|-------|-----|------------|------------|------------|
| C1 | 198 | 220 | 230 | 240 |
| C2 | 205 | 235 | 231 | 248 |
| C3 | 211 | 385 | 239 | 249 |
| Avg | 204.7 | 280.0 | 233.3 | 245.7 |
| Pattern | Stable | ⚡C3 spike | Stable | Stable |
```

**What to detect:**
1. **DUT-specific spike**: One DUT has spike at specific cycle → device-specific issue
2. **Common spike**: All DUTs spike at same cycle → systemic issue
3. **RAM-correlated**: 4GB spikes more than 8GB → memory pressure related

### Step 3: Issue Classification

#### Common Issues (affect ALL DUTs)
- Metrics tăng consistently trên **tất cả** DUTs so với REF
- Per-cycle pattern: ALL DUTs spike at same cycles
- Thường chỉ ra **REF có gì khác** hoặc **hệ thống chung** có vấn đề

#### Variant-Specific Issues
- Metrics tăng chỉ trên **1-2 DUTs**
- Per-cycle pattern: Only specific DUT(s) have spikes
- Thường liên quan đến **RAM size**, **device config**, hoặc **build variant**

#### Best/Worst Performer
- Identify DUT nào perform tốt nhất/tệ nhất per app
- Phân tích tại sao: So sánh per-cycle memory, frequency, compiler

### Step 4: Pattern Detection

1. **Memory-correlated**: Overlapping memory per-cycle arrays:
   - `MemFree_MB` across DUTs: 4GB consistently lower?
   - Does MemFree drop correlate with D-state spike at same cycle?
2. **Frequency-correlated**: Running tăng trên DUT có lower frequency?
3. **Compiler-correlated**: DUTs có cùng compiler type behave tương tự?
4. **Per-cycle sync**: Do all DUTs have issues at the same cycle numbers?

### Step 5: Report

```markdown
# Multi-DUT Comparison Report
## Overview
- REF: BOS / ZB1
- DUT1: 4GB / ZC1
- DUT2: 6GB / ZC1
- DUT3: 8GB / ZC1

## Common Issues (All DUTs)
| App | Issue | Severity | Per-Cycle Note |
|-----|-------|----------|----------------|
| calculator | Compiler verify | 🟡 | Consistent across cycles |
| message | Running +300ms | 🔴 | All DUTs spike at C2,C3 |

## Variant-Specific Issues
| App | Affected DUT | Issue | Per-Cycle Pattern | Likely Cause |
|-----|-------------|-------|-------------------|-------------|
| gallery | 4GB only | D-state +280ms | ⚡ C2,C3 spike | Memory pressure |
| camera | 8GB only | start_process_abnormal | At C1 only | Build variant |

## Recommendations
1. [Common] All DUTs: Compiler verify → suggest App TG
2. [4GB specific] Memory pressure at Cycle 2,3 → Kernel Memory team
3. [8GB specific] Process issue at Cycle 1 → SWPL investigate
```

---

## Important Rules

1. **Always normalize** – So sánh cùng app, cùng launch type (entry/reentry)
2. **Per-Cycle patterns** – Compare cycle-level data across DUTs to find sync/divergence
3. **RAM-aware** – 4GB devices sẽ tự nhiên có higher D-state. Phân biệt "expected" vs "abnormal"
4. **Version-aware** – Nếu DUTs có different versions, flag this in report
5. **Calculate avg from arrays** – Use `avg = sum(non_zero)/len(non_zero)` formula
6. **Reference cross-reference** – Sử dụng `../app_launch_rca/` cho metric definitions

## References

- [json_schema.md](../app_launch_rca/references/json_schema.md) – JSON structure (v3)
- [metric_glossary.md](../app_launch_rca/references/metric_glossary.md)
- [team_routing.md](../app_launch_rca/references/team_routing.md)
