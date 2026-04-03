---
name: regression_detection
description: So sánh kết quả test hiện tại vs lịch sử theo version (ZC1, ZB1, ZA1...) để phát hiện regression, improvement, trend, và per-cycle pattern changes.
---

# Regression Detection (v3 – Per-Cycle)

## Overview

Skill này cho phép AI agent so sánh kết quả performance test **qua nhiều versions** (builds) để phát hiện regression hoặc improvement. Agent sử dụng field `version` trong JSON và **per-cycle data** để track performance trend và detect pattern changes.

### ⚠️ v3 – Per-Cycle Data

> Từ v3, `sequence` metrics là **arrays per-cycle** (e.g., `[220, 235, 244]`).  
> Agent PHẢI so sánh cả **average trend** VÀ **per-cycle spike patterns** across versions.

**Cách tính average:**
```python
values = [v for v in metric_array if v > 0]
avg = sum(values) / len(values) if values else 0
```

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

### Step 2: Version-over-Version Trend – Average (per app)

Cho mỗi app, tạo trend table sử dụng **calculated averages**:

```markdown
### App: calculator

| Metric | ZA1 | ZB1 | ZC1 | Trend |
|--------|-----|-----|-----|-------|
| App Execution Time (avg) | 480 | 504 | 540 | 📈 Increasing (+12.5%) |
| Running (avg) | 190 | 204 | 233 | 📈 Increasing (+22.6%) |
| D-state (avg) | 5.2 | 6.9 | 18.9 | 🔴 Spike at ZC1 (+263%) |
| Binder count | 95 | 97 | 100 | ➡️ Stable |
| Compiler | speed-profile | verify | verify | ⚠️ Changed at ZB1 |
```

### Step 2.5: Per-Cycle Pattern Evolution (NEW – CRITICAL)

> **Đây là bước QUAN TRỌNG NHẤT** vì per-cycle pattern changes thường bị average che giấu.

Cho mỗi metric flagged ở Step 2, so sánh **per-cycle arrays across versions**:

```markdown
### App: calculator – Activity Thread Main per-cycle across versions

| Version | Cycle 1 | Cycle 2 | Cycle 3 | Avg | Spike Pattern |
|---------|---------|---------|---------|-----|---------------|
| ZA1 | 50.0 | 20.0 | 20.0 | 30.0 | 1/3 cycles spike |
| ZB1 | 50.0 | 22.0 | 20.0 | 30.7 | 1/3 cycles spike |
| ZC1 | 52.3 | 50.1 | 20.5 | 40.9 | ⚡ 2/3 cycles spike |
```

**What to detect:**
1. **Spike count increase**: REF 1/3 cycles spike → DUT 2/3 cycles spike
   - Average diff may be only ~10ms, but PATTERN CHANGE is significant!
2. **New spike cycle**: Cycle N was normal in old version, now spikes
3. **Spike stabilization**: Issue becomes consistent across all cycles (intermittent → permanent)

### Step 3: Regression Classification

| Type | Definition | Example |
|------|-----------|---------|
| **Regression (average)** | Avg worsened > threshold | Running avg: 204 → 233 (+14%) |
| **Regression (pattern)** | Spike pattern worsened | ATM: 1/3 spike → 2/3 spike |
| **Improvement** | Metric improved > threshold | D-state: 50 → 18 (-64%) |
| **Spike** | Sudden large change | PSS: 28 → 28 → 95 at ZC1 |
| **Gradual degradation** | Consistent worsening | Running: 190 → 198 → 204 → 233 |
| **Pattern shift** | Spike moved to different cycles | Spike C1 → Spike C2,C3 |
| **Stable** | Unchanged within noise margin | Binder: 95 → 97 → 100 (±5%) |

### Step 4: Root-Cause Correlation

Khi phát hiện regression:
1. **Compiler change?** – compiler type changed cùng version?
2. **Memory change?** – Per-cycle `MemFree_MB`, `Pageboostd_MB` thay đổi?
   - Compare memory per-cycle arrays across versions
   - MemFree drop at specific cycle correlates with D-state spike?
3. **Process change?** – New abnormal processes appeared at specific cycles?
   - Compare `start_process_abnormal` per-cycle arrays across versions
4. **Frequency change?** – CPU frequency distribution changed?
5. **Per-cycle correlation** – At the spike cycle, what else changed?
   - If Running spikes at C2 in ZC1, check: frequency at C2, priority at C2, top CPU at C2

### Step 5: Report

```markdown
# Regression Report: calculator
## Version: ZB1 → ZC1

### Average Regressions
| Metric | ZB1 (avg) | ZC1 (avg) | Change | Severity |
|--------|-----------|-----------|--------|----------|
| D-state | 6.9 | 18.9 | +174% | 🔴 |
| Running | 204 | 233 | +14% | 🟡 |

### ⚡ Per-Cycle Pattern Changes
| Metric | ZB1 Pattern | ZC1 Pattern | Change |
|--------|-------------|-------------|--------|
| ActivityThreadMain | 1/3 spike [50, 22, 20] | 2/3 spike [52, 50, 20] | 🔴 Pattern worsened |
| D-state | Stable [6.5, 7.0, 7.2] | ⚡C1 spike [18, 19, 20] | 🟡 New C1 issue |

### Memory Evolution (per-cycle)
| Metric | ZB1 [C1, C2, C3] | ZC1 [C1, C2, C3] |
|--------|-------------------|-------------------|
| MemFree_MB | [1500, 1480, 1490] | [1200, 1100, 1400] |
| Pageboostd_MB | [24, 24, 24] | [24, 15, 24] |

### Possible Root Cause
- ActivityThreadMain pattern worsened: Was unstable at C1 only, now C1+C2
  → Indicates regression in app initialization code
- D-state spike correlates with Pageboost decrease (24 → 15 MB at C2)
  → Memory pressure causing I/O fallback
- Running increase may be related to compiler still being "verify"

### Recommendation
- App TG: Investigate ActivityThreadMain C2 regression in ZC1 build
- Kernel Memory: Check pageboost regression at C2 in ZC1
```

---

## Threshold Definitions

| Metric | Significant Change (avg) | Major Regression (avg) | Pattern Change |
|--------|------------------------|-----------------------|----------------|
| Execution Time | >5% or >30ms | >15% or >100ms | +1 spike cycle |
| Running/Sleeping/Runnable | >10% or >20ms | >25% or >50ms | +1 spike cycle |
| D-state | >50% or >15ms | >100% or >30ms | Any new spike |
| Binder count | >10% or >10 | >25% or >25 | N/A |
| PSS | >10% or >10MB | >25% or >50MB | +20MB any cycle |
| Pageboost | >30% or >5MB | >50% or >10MB | Any cycle drop |
| MemFree | >10% or >50MB | >20% or >100MB | >100MB any cycle |

## Important Rules

1. **Noise margin**: Changes <5% hoặc <5ms thường là noise, không report as regression
2. **Pattern > Average**: Spike pattern change (1/3→2/3) quan trọng hơn small avg diff
3. **Version pairs**: Always compare consecutive versions (ZA1→ZB1, ZB1→ZC1)
4. **Cold/Warm consistency**: Cùng State type mới so sánh được (Cold vs Cold)
5. **Per-cycle first**: Always analyze per-cycle patterns BEFORE reporting averages
6. **Calculate avg from arrays**: `avg = sum(non_zero)/len(non_zero)`
7. **NEVER create report files** – Chỉ print trong chat
   - Nếu user yêu cầu lưu file → Hỏi xác nhận trước khi tạo

## References

- [json_schema.md](../app_launch_rca/references/json_schema.md) – JSON structure (v3)
- [metric_glossary.md](../app_launch_rca/references/metric_glossary.md)
- [regression_criteria.md](references/regression_criteria.md)
