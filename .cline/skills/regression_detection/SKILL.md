---
name: regression_detection
description: So sánh kết quả test hiện tại vs lịch sử theo version (ZC1, ZB1, ZA1...) để phát hiện regression, improvement, và trend.
---

# Regression Detection

## Overview

Skill này cho phép AI agent so sánh kết quả performance test **qua nhiều versions** (builds) để phát hiện regression hoặc improvement. Agent sử dụng field `version` trong JSON (ví dụ: ZC1, ZB1, ZA1) để track performance trend.

## Input Data

### Required
- **Nhiều JSON files** từ các test sessions khác nhau, **cùng device_code** nhưng **khác version**
- Agent cần user cung cấp đường dẫn đến tất cả JSON files hoặc thư mục chứa chúng

### Version Parsing
- `version` field trong JSON: "ZC1", "ZB1", "ZA1", etc.
- Sort order: Alphabetical hoặc theo timestamp
- User có thể cung cấp version order nếu cần

---

## Analysis Workflow

### Step 1: Load & Group by Version
1. Load tất cả JSON files
2. Group theo `version` + `type` (DUT/REF)
3. Sort versions theo thứ tự (mới nhất → cũ nhất)

### Step 2: Version-over-Version Trend (per app)

Cho mỗi app, tạo trend table:

```markdown
### App: calculator

| Metric | ZA1 | ZB1 | ZC1 | Trend |
|--------|-----|-----|-----|-------|
| App Execution Time | 480 | 504 | 540 | 📈 Increasing (+12.5%) |
| Running | 190 | 204 | 233 | 📈 Increasing (+22.6%) |
| D-state | 5.2 | 6.9 | 18.9 | 🔴 Spike at ZC1 (+263%) |
| Binder count | 95 | 97 | 100 | ➡️ Stable |
| Compiler | speed-profile | verify | verify | ⚠️ Changed at ZB1 |
```

### Step 3: Regression Classification

| Type | Definition | Example |
|------|-----------|---------|
| **Regression** | Metric worsened > threshold in latest version | Running: 204 → 233 (+14%) |
| **Improvement** | Metric improved > threshold in latest version | D-state: 50 → 18 (-64%) |
| **Spike** | Sudden large change (not gradual) | PSS: 28 → 28 → 95 at ZC1 |
| **Gradual degradation** | Small but consistent worsening across versions | Running: 190 → 198 → 204 → 233 |
| **Stable** | Metric unchanged within noise margin | Binder: 95 → 97 → 100 (±5%) |

### Step 4: Root-Cause Correlation

Khi phát hiện regression:
1. **Compiler change?** – compiler type changed cùng version?
2. **Memory change?** – MemFree/Pageboost thay đổi?
3. **Process change?** – New abnormal processes appeared?
4. **Frequency change?** – CPU frequency distribution changed?

### Step 5: Report

```markdown
# Regression Report: calculator
## Version: ZB1 → ZC1

### Regressions Found
| Metric | ZB1 | ZC1 | Change | Severity |
|--------|-----|-----|--------|----------|
| D-state | 6.9 | 18.9 | +174% | 🔴 |
| Running | 204 | 233 | +14% | 🟡 |

### Possible Root Cause
- D-state spike correlates with Pageboost decrease (3.38 → 0.15 MB)
- Running increase may be related to compiler still being "verify"

### Recommendation
- Kernel Memory team: Check pageboost regression in ZC1
- App TG: Apply speed-profile (ongoing from ZB1)
```

---

## Threshold Definitions

| Metric | Significant Change | Major Regression |
|--------|-------------------|-----------------|
| Execution Time | >5% or >30ms | >15% or >100ms |
| Running/Sleeping/Runnable | >10% or >20ms | >25% or >50ms |
| D-state | >50% or >15ms | >100% or >30ms |
| Binder count | >10% or >10 | >25% or >25 |
| PSS | >10% or >10MB | >25% or >50MB |
| Pageboost | >30% or >5MB | >50% or >10MB |
| MemFree | >10% or >50MB | >20% or >100MB |

## Important Rules

1. **Noise margin**: Changes <5% hoặc <5ms thường là noise, không report as regression
2. **Context matters**: Compiler change từ speed-profile → verify giải thích Running increase
3. **Version pairs**: Always compare consecutive versions (ZA1→ZB1, ZB1→ZC1), not just first/last
4. **Cold/Warm consistency**: Cùng State type mới so sánh được (Cold vs Cold)
5. **NEVER create report files** – KHÔNG tự động tạo file .md, .py, hoặc bất kỳ file report nào
   - Chỉ print toàn bộ nội dung report trong khung chat (message response)
   - Nếu user yêu cầu lưu file → Hỏi xác nhận trước khi tạo
   - Nếu user reject → Agent hiểu và chỉ print, không tạo lại file khác

## References

- [json_schema.md](../app_launch_rca.skill/references/json_schema.md)
- [metric_glossary.md](../app_launch_rca.skill/references/metric_glossary.md)
- [regression_criteria.md](references/regression_criteria.md)
