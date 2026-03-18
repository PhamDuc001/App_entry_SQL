---
name: auto_report
description: Tự động tạo performance report chuẩn từ JSON data. Output Markdown report có executive summary, pass/fail per app, detailed findings, và recommendations.
---

# Auto Performance Report Generator

## Overview

Skill này cho phép AI agent tự động tạo **standardized performance report** từ DUT + REF JSON files. Report có format chuẩn phù hợp cho việc chia sẻ với các team khác (App team, System team, management).

## Input Data

- 1 DUT JSON file (failed apps hoặc all apps)
- 1 REF JSON file  
- (Optional) Test round ID, model name, tester name

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

### Overall Assessment
[1-2 sentences: overall result, main concern areas]
```

### Pass/Fail Table
```markdown
## App Results Overview

| # | App | Execution (DUT) | Execution (REF) | Diff | Status |
|---|-----|-----------------|-----------------|------|--------|
| 1 | calculator | 540.4 ms | 504.8 ms | +35.6 ms (+7.1%) | ⚠️ |
| 2 | gallery | 959.5 ms | 622.2 ms | +337.3 ms (+54.2%) | 🔴 |
| 3 | message | 1228.6 ms | 980.0 ms | +248.6 ms (+25.4%) | 🔴 |
```

**Status criteria:**
- ✅ Pass: Diff < 30ms AND < 5%
- ⚠️ Warning: Diff 30-100ms OR 5-15%
- 🔴 Fail: Diff > 100ms OR > 15%

### Detailed Findings (per failed/warning app)
```markdown
## Detailed Findings

### 🔴 gallery (+337.3ms / +54.2%)

**Launch State**: Cold (all 3 cycles)

**Timing Breakdown** (DUT avg | REF avg | Diff):
| Section | DUT | REF | Diff |
|---------|-----|-----|------|
| Activity Start | 285.7 | 100.3 | **+185.4** |
| Choreographer→Idle | 324.9 | 299.8 | +25.1 |
| Running | 256.2 | 207.4 | +48.8 |
| D-state | 279.9 | 26.9 | **+253.0** |

**Key Issues Found**:
1. 🔴 D-state increased +253ms → Block I/O issue
2. 🟡 start_process_abnormal: `.android.scloud`, `com.samsung.cmh`
3. 🟡 Compiler: speed-profile (both DUT & REF) – OK

**Root Cause**: D-state spike likely due to I/O contention from parallel processes

**Recommendations**:
| Team | Action |
|------|--------|
| App Team + SWPL | Investigate parallel process: .android.scloud |
| Kernel Memory | Check Block I/O at gallery launch |
```

### Version Info
```markdown
## Environment Info

| Metric | DUT | REF |
|--------|-----|-----|
| Version | ZC1 | ZB1 |
| Uptime | 7 min | 7 min |
```

### Summary Recommendations
```markdown
## Action Items Summary

| # | Issue | Affected Apps | Responsible | Priority |
|---|-------|--------------|-------------|----------|
| 1 | D-state regression | gallery | Kernel Memory | High |
| 2 | Running +250ms | message | App Team | High |
| 3 | Parallel process | gallery, message | SWPL | Medium |
| 4 | Compiler verify | calculator | App TG | Low |
```

---

## Generation Rules

1. **Complete report** – Always include ALL sections, even if empty (write "None found")
2. **Data-driven** – Every finding must reference specific metric values
3. **Consistent format** – Use exact table format as shown above
4. **DUT vs REF** – Always show both values side-by-side
5. **Prioritized** – Sort action items by severity (High → Low)
6. **No fabrication** – Only report data from JSON, never make up values
7. **Percentage + Absolute** – Show both for execution time diff
8. **Top 3 sections** – In detailed findings, highlight top 3 timing contributors
9. **Actionable** – Each recommendation must specify team AND action

## Pass/Fail Thresholds

| Category | Criteria |
|----------|----------|
| **✅ Pass** | Diff < 30ms AND relative < 5% |
| **⚠️ Warning** | Diff ≥ 30ms AND ≤ 100ms, OR relative 5-15% |
| **🔴 Fail** | Diff > 100ms OR relative > 15% |

> For entries where REF has no data for an app, mark as "⚪ No baseline" and skip comparison.

## References

- [json_schema.md](../app_launch_rca.skill/references/json_schema.md)
- [metric_glossary.md](../app_launch_rca.skill/references/metric_glossary.md)
- [team_routing.md](../app_launch_rca.skill/references/team_routing.md)
- [report_template.md](references/report_template.md)
