---
name: multi_dut_comparison
description: So sánh performance data từ nhiều DUT devices (variants) cùng 1 REF baseline để phát hiện device-specific vs common issues.
---

# Multi-DUT Performance Comparison

## Overview

Skill này cho phép AI agent so sánh dữ liệu app launch performance từ **nhiều DUT devices** (ví dụ: 4GB, 6GB, 8GB variants) cùng **1 REF baseline**. Agent sẽ identify issues chung (common across DUTs) vs riêng lẻ (device-specific), giúp PE xác định scope ảnh hưởng và phân bổ root-cause chính xác hơn.

## Input Data

### Required
- **Nhiều DUT JSON files**: Từ các test sessions khác nhau (khác device_code/variant)
- **1 REF JSON file**: Baseline chung (có thể cùng 1 REF cho tất cả DUTs hoặc mỗi DUT 1 REF riêng)

### JSON Schema
Xem `../app_launch_rca.skill/references/json_schema.md` để hiểu cấu trúc JSON.

---

## Analysis Workflow

### Step 1: Load & Normalize
1. Load tất cả DUT JSON files và REF JSON file(s)
2. Xác định `device_code` và `version` của mỗi file
3. Tìm **common apps**: apps có mặt trong TẤT CẢ DUT files

### Step 2: Per-App Cross-DUT Comparison

Cho mỗi app, tạo comparison table:

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

### Step 3: Issue Classification

#### Common Issues (affect ALL DUTs)
- Metrics tăng consistently trên **tất cả** DUTs so với REF
- Thường chỉ ra **REF có gì khác** hoặc **hệ thống chung** có vấn đề

#### Variant-Specific Issues
- Metrics tăng chỉ trên **1-2 DUTs**
- Thường liên quan đến **RAM size**, **device config**, hoặc **build variant**

#### Best/Worst Performer
- Identify DUT nào perform tốt nhất/tệ nhất per app
- Phân tích tại sao (frequency? memory? compiler?)

### Step 4: Pattern Detection

1. **Memory-correlated**: D-state tăng phù hợp với MemFree giảm? (ảnh hưởng 4GB > 8GB?)
2. **Frequency-correlated**: Running tăng trên DUT có lower frequency?
3. **Compiler-correlated**: DUTs có cùng compiler type behave tương tự?
4. **Version-correlated**: DUTs có cùng version behave tương tự?

### Step 5: Report

```markdown
# Multi-DUT Comparison Report
## Overview
- REF: BOS / ZB1
- DUT1: 4GB / ZC1
- DUT2: 6GB / ZC1
- DUT3: 8GB / ZC1

## Common Issues (All DUTs)
| App | Issue | Severity |
|-----|-------|----------|
| calculator | Compiler verify (all DUTs) | 🟡 |
| message | Running +300ms (all DUTs) | 🔴 |

## Variant-Specific Issues
| App | Affected DUT | Issue | Likely Cause |
|-----|-------------|-------|-------------|
| gallery | 4GB only | D-state +280ms | Memory pressure |
| camera | 8GB only | start_process_abnormal | Build variant issue |

## Recommendations
1. [Common] All DUTs: Compiler verify → suggest App TG
2. [4GB specific] Memory pressure → Kernel Memory team
3. [8GB specific] Process issue → SWPL investigate
```

---

## Important Rules

1. **Always normalize** – So sánh cùng app, cùng launch type (entry/reentry)
2. **Statistical thinking** – 1 bad cycle ≠ systematic issue. Look for patterns across cycles
3. **RAM-aware** – 4GB devices sẽ tự nhiên có higher D-state. Phân biệt "expected" vs "abnormal"
4. **Version-aware** – Nếu DUTs có different versions, flag this in report
5. **Reference cross-reference** – Sử dụng `../app_launch_rca.skill/` cho metric definitions và team routing

## References

- [json_schema.md](../app_launch_rca.skill/references/json_schema.md)
- [metric_glossary.md](../app_launch_rca.skill/references/metric_glossary.md)
- [team_routing.md](../app_launch_rca.skill/references/team_routing.md)
- [comparison_strategy.md](references/comparison_strategy.md)
