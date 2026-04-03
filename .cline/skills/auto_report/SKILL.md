---
name: auto_report
description: Tự động tạo performance report chuẩn từ JSON data (v3 per-cycle). Output Markdown report có executive summary, pass/fail per app, per-cycle breakdown, detailed findings, và recommendations.
---

# Auto Performance Report Generator (v3 – Per-Cycle)

## Overview

Skill này cho phép AI agent tự động tạo **standardized performance report** từ DUT + REF JSON files. Report có format chuẩn phù hợp cho việc chia sẻ với các team khác (App team, System team, management).

### ⚠️ v3 – Per-Cycle Data

> Từ v3, `sequence` metrics là **array per-cycle** (e.g., `[220, 235, 244]`).  
> `extend.memory` và `uptime_minutes` cũng là per-cycle arrays + `*_avg` fields.  
> Report PHẢI bao gồm per-cycle breakdown nếu phát hiện bất thường.

## Input Data

- 1 DUT JSON file (v3 format – per-cycle arrays)
- 1 REF JSON file (v3 format)
- (Optional) Test round ID, model name, tester name

**Cách tính average từ per-cycle arrays:**
```python
values = [v for v in metric_array if v > 0]
avg = sum(values) / len(values) if values else 0
```

---

## Report Template

Agent phải tạo report theo đúng format sau:

### Header
```markdown
# App Launch Performance Report

| Field | Value |
|-------|-------|
| **Model** | A266M |
| **DUT** | {device_code} / {version} |
| **REF** | {device_code} / {version} |
| **Test Date** | {timestamp} |
| **Generated** | {current_date} |
```

### Executive Summary
```markdown
## Executive Summary

- **Total Apps Tested**: {N}
- **Pass**: {pass_count} apps ✅
- **Fail**: {fail_count} apps 🔴
- **Warning**: {warn_count} apps ⚠️
- **Cycle Anomalies Detected**: {anomaly_count} apps ⚡

### Overall Assessment
[1-2 sentences: overall result, main concern areas, highlight if per-cycle anomalies found]
```

### Pass/Fail Table
```markdown
## App Results Overview

| # | App | Exec (DUT avg) | Exec (REF avg) | Diff | Status | Cycle Note |
|---|-----|----------------|----------------|------|--------|------------|
| 1 | calculator | 540.4 ms | 504.8 ms | +35.6 ms (+7.1%) | ⚠️ | Cycle 2,3 spike |
| 2 | gallery | 959.5 ms | 622.2 ms | +337.3 ms (+54.2%) | 🔴 | Consistent |
```

**Status criteria:**
- ✅ Pass: Avg diff < 30ms AND < 5%
- ⚠️ Warning: Avg diff 30-100ms OR 5-15%, OR per-cycle anomaly detected
- 🔴 Fail: Avg diff > 100ms OR > 15%

**Cycle Note criteria:**
- "Consistent" – All cycles behave similarly
- "Cycle N spike" – Specific cycle(s) have outlier values
- "Worsening" – Pattern: DUT has more spike cycles than REF

### Per-Cycle Breakdown (for failed/warning apps)
```markdown
### 🔴 gallery – Per-Cycle Timing

#### Sequence Breakdown (ms)
| Metric | DUT C1 | DUT C2 | DUT C3 | DUT Avg | REF C1 | REF C2 | REF C3 | REF Avg | Diff Avg |
|--------|--------|--------|--------|---------|--------|--------|--------|---------|----------|
| App Execution | 954.7 | 832.4 | 1091.4 | 959.5 | 622.1 | 610.3 | 634.2 | 622.2 | **+337.3** |
| Running | 256.6 | 252.1 | 259.8 | 256.2 | 207.1 | 205.8 | 209.4 | 207.4 | +48.8 |
| D-state | 284.4 | 218.6 | 336.7 | 279.9 | 25.1 | 27.2 | 28.5 | 26.9 | **+253.0** |

#### Memory Per-Cycle (MB)
| Metric | DUT C1 | DUT C2 | DUT C3 | DUT Avg | REF C1 | REF C2 | REF C3 | REF Avg |
|--------|--------|--------|--------|---------|--------|--------|--------|---------|
| MemFree | 150 | 130 | 141 | 140.3 | 155 | 148 | 134 | 145.7 |
| PSS | 67.1 | 67.2 | 66.7 | 67.0 | 45.2 | 44.8 | 45.5 | 45.2 |
| Pageboost | 24.0 | 24.0 | 24.0 | 24.0 | 27.5 | 27.8 | 27.9 | 27.7 |
```

### Detailed Findings (per failed/warning app)
```markdown
## Detailed Findings

### 🔴 gallery (+337.3ms / +54.2%)

**Launch State**: Cold (all 3 cycles)

**Key Issues Found**:
1. 🔴 D-state increased +253ms avg
   - Per-cycle: Cycle 1 (+259ms), Cycle 2 (+191ms), Cycle 3 (+308ms)
   - Pattern: Consistent across all cycles
2. 🟡 start_process_abnormal: `.android.scloud` at Cycle 2
   - Correlates with Running spike at Cycle 2
3. ✅ Compiler: speed-profile (both DUT & REF) – OK

**Cycle Anomaly**:
- D-state: Cycle 3 has highest spike (336.7ms DUT vs 28.5ms REF = +308ms)
- MemFree: Cycle 2 lowest (130 MB) – potential memory pressure

**Root Cause**: D-state spike likely due to I/O contention from parallel processes

**Recommendations**:
| Team | Action |
|------|--------|
| App Team + SWPL | Investigate parallel process: .android.scloud |
| Kernel Memory | Check Block I/O at gallery launch |
```

### Summary Recommendations
```markdown
## Action Items Summary

| # | Issue | Affected Apps | Responsible | Priority |
|---|-------|--------------|-------------|----------|
| 1 | D-state regression | gallery | Kernel Memory | High |
| 2 | Running +250ms | message | App Team | High |
| 3 | Cycle spike pattern change | calculator | App TG | Medium |
| 4 | Parallel process | gallery, message | SWPL | Medium |
```

---

## Generation Rules

1. **Complete report** – Always include ALL sections, even if empty (write "None found")
2. **Data-driven** – Every finding must reference specific metric values
3. **Per-Cycle FIRST** – Always show per-cycle breakdown for failed/warning apps
4. **Consistent format** – Use exact table format as shown above
5. **DUT vs REF** – Always show both values side-by-side
6. **Prioritized** – Sort action items by severity (High → Low)
7. **No fabrication** – Only report data from JSON, never make up values
8. **Percentage + Absolute** – Show both for execution time diff
9. **Actionable** – Each recommendation must specify team AND action
10. **Pattern Detection** – Flag when spike pattern changes (e.g., REF 1/3 cycles → DUT 2/3 cycles)
11. **Average from per-cycle** – Calculate average from non-zero values in the array

## Pass/Fail Thresholds

| Category | Criteria |
|----------|----------|
| **✅ Pass** | Avg diff < 30ms AND relative < 5% |
| **⚠️ Warning** | Avg diff ≥ 30ms AND ≤ 100ms, OR relative 5-15%, OR per-cycle anomaly |
| **🔴 Fail** | Avg diff > 100ms OR relative > 15% |

> For entries where REF has no data for an app, mark as "⚪ No baseline" and skip comparison.

## References

- [json_schema.md](../app_launch_rca/references/json_schema.md) – JSON structure (v3)
- [metric_glossary.md](../app_launch_rca/references/metric_glossary.md) – Metric definitions
- [team_routing.md](../app_launch_rca/references/team_routing.md) – Issue → Team mapping
