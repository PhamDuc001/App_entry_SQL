---
name: trace_deep_dive
description: Phân tích chi tiết metrics của 1 app cụ thể khi PE cần debug root cause sâu hơn. Drill down per-cycle vào sequence, frequency, priority, block I/O, memory, processes.
---

# Trace Deep Dive Analysis (v3 – Per-Cycle Native)

## Overview

Skill này cho phép AI agent thực hiện **deep-dive analysis** vào 1 app cụ thể khi Performance Engineer đã identify issue qua RCA skill nhưng cần hiểu chi tiết hơn. Với v3 JSON format, **per-cycle data là native** – Agent truy cập trực tiếp từ `sequence` arrays mà không cần tính toán thêm.

### ⚠️ v3 – Per-Cycle Data is Native

> Tất cả `sequence` metrics đã là **array per-cycle**: `[cycle1, cycle2, cycle3]`.  
> `extend.memory` và `uptime_minutes` cũng là per-cycle arrays + `*_avg` fields.  
> Agent KHÔNG cần tính per-cycle từ raw data – data đã sẵn sàng.

**Cách tính average (chỉ khi cần):**
```python
values = [v for v in metric_array if v > 0]
avg = sum(values) / len(values) if values else 0
```

## When to Use

- PE đã chạy `app_launch_rca` và tìm thấy issue
- Cần hiểu **tại sao** Running tăng (frequency? compiler? process interference?)
- Cần xem **cycle nào** có vấn đề (outlier cycle vs consistent issue)
- Cần deep-dive vào **1 section** cụ thể
- Cần **cross-correlate** per-cycle anomalies (ví dụ: D-state spike ở C2 + MemFree drop ở C2)

---

## Analysis Workflow

### Step 1: Focus Selection
Agent hỏi user:
1. App nào? (e.g., "calculator", "gallery")
2. Focus area? (Running, Sleeping, D-state, overall)
3. DUT JSON path + REF JSON path

### Step 2: Cycle-by-Cycle Breakdown (from v3 arrays)

> **v3**: Data đã có sẵn trong sequence arrays. Truy cập trực tiếp:
> ```python
> dut_running = dut_app["entry"]["sequence"]["Running"]  # [220.5, 235.1, 243.7]
> ref_running = ref_app["entry"]["sequence"]["Running"]  # [198.3, 205.4, 210.5]
> ```

```markdown
### calculator – Running Time per Cycle

| Cycle | DUT (ms) | REF (ms) | Diff | Flag |
|-------|----------|----------|------|------|
| 1 | 220.5 | 198.3 | +22.2 | - |
| 2 | 235.1 | 205.4 | +29.7 | ⚠️ |
| 3 | 243.7 | 210.5 | +33.2 | ⚠️ |
| **Avg** | **233.1** | **204.7** | **+28.4** | |
| **Trend** | 📈 Increasing | ➡️ Stable | | |
| **Outlier** | None | None | | |
```

### Step 3: Section-by-Section Analysis

> **v3**: Each section metric is per-cycle array. Show avg AND per-cycle.

```markdown
### calculator – Timing Breakdown

| Section | DUT [C1,C2,C3] | DUT Avg | REF [C1,C2,C3] | REF Avg | Diff Avg | % of Total |
|---------|-----------------|---------|-----------------|---------|----------|------------|
| Touch→Start | [12,13,12] | 12.3 | [11,11,12] | 11.3 | +1.0 | 2.3% |
| ActivityThreadMain | [**52,50,20**] | 40.7 | [50,20,20] | 30.0 | **+10.7** | ⚡ Pattern! |
| Activity Start | [135,130,140] | 135.0 | [107,105,108] | 106.5 | **+28.4** | 25.0% |
```

**Pattern Detection**:
- ActivityThreadMain: DUT spikes 2/3 cycles [52, 50, **20**], REF only 1/3 [50, **20**, **20**]
- → Average diff is only 10.7ms, but **pattern change is significant**

### Step 4: Frequency Deep Dive

Per section, per cycle frequency analysis (from `frequency_by_cycle`):

```markdown
### calculator – Frequency at bindApplication

| Cycle | DUT @2400 | REF @2400 | DUT @2002 | REF @2002 | Flag |
|-------|-----------|-----------|-----------|-----------|------|
| 1 | 94.0% | 96.1% | 6.0% | 3.9% | - |
| 2 | 84.3% | 90.5% | 15.7% | 9.5% | ⚠️ -6.2% |
| 3 | 100.0% | 87.5% | 0.0% | 12.5% | ✅ DUT better |
```

### Step 5: Priority Deep Dive

```markdown
### calculator – Priority at activityStart

| Cycle | DUT @110 | REF @110 | DUT @120 | REF @120 | Flag |
|-------|----------|----------|----------|----------|------|
| 1 | 100.0% | 100.0% | 0.0% | 0.0% | ✅ |
| 2 | 100.0% | 99.1% | 0.0% | 0.9% | ✅ |
| 3 | 98.7% | 100.0% | 1.3% | 0.0% | - |
```

### Step 6: Process Interference Analysis

> Correlate `top_process_consume_by_cycle` with **sequence per-cycle spikes**.

```markdown
### calculator – Top CPU at Cycle 3 (worst cycle)

| # | Process | DUT (ms) | REF (ms) | Diff | Concern |
|---|---------|----------|----------|------|---------|
| 1 | system_server | 1185.0 | 808.7 | **+376.3** | 🔴 Major |
| 2 | surfaceflinger | 674.8 | 622.4 | +52.4 | 🟡 |

💡 system_server consuming +376ms in cycle 3 → correlates with Running spike at C3
```

### Step 7: Memory Per-Cycle Correlation (NEW in v3)

> **v3**: Memory data is per-cycle. Correlate with sequence spikes.

```markdown
### gallery – Memory & D-state Correlation

| Cycle | D-state (DUT) | MemFree (DUT) | Pageboost (DUT) | PSS (DUT) |
|-------|---------------|---------------|-----------------|-----------|
| 1 | 284.4 | 1800.5 | 23.95 | 67.08 |
| 2 | 218.6 | **1200.3** ⚡ | 23.95 | 67.20 |
| 3 | **336.7** ⚡ | 1500.2 | 23.95 | 66.68 |

💡 Cycle 2: MemFree lowest (1200 MB) → memory pressure
💡 Cycle 3: D-state highest (336.7 ms) → I/O contention
```

### Step 8: Block I/O Detail (if D-state is high)

```markdown
### gallery – Block I/O Sources (Cycle 3 - highest D-state)

| Library/File | Time (ms) | Type |
|-------------|-----------|------|
| SamsungGallery2018.apk | 0 | APK |
| OneUISansKR-VF.ttf | 0 | Font |
| icudt76l.dat | 0 | ICU |
```

### Step 9: LoadApkAsset Deep Dive (if applicable)

```markdown
### gallery – LoadApkAsset Analysis

**Total LoadApkAsset Time**:
| Metric | DUT (ms) | REF (ms) | Diff |
|--------|----------|----------|------|
| **Total** | **167.82** | **0** | **+167.82** 🔴 |

**Correlation with Memory (per-cycle)**:
| Cycle | Pageboost (DUT) | Pageboost (REF) | MemFree (DUT) | MemFree (REF) |
|-------|-----------------|-----------------|---------------|---------------|
| 1 | 24.0 | 27.5 | 1800 | 1900 |
| 2 | **15.0** ⚡ | 27.8 | **1200** ⚡ | 1850 |
| 3 | 24.0 | 27.9 | 1500 | 1870 |

💡 Pageboost drop at C2 correlates with MemFree drop → Cache eviction
```

### Step 10: Correlation Summary

```markdown
### Root Cause Hypothesis

1. **Activity Start tăng +28.4ms** (biggest section contributor)
   - Frequency: Normal (>95% @2400)
   - Priority: Normal (100% @110)
   - Hypothesis: App-side code increase in onCreate/onStart

2. **ActivityThreadMain pattern change** (avg only +10.7ms but 2/3 spike)
   - ZA1/ZB1: 1/3 cycles spike  
   - ZC1: 2/3 cycles spike
   - Hypothesis: App initialization regression in new build

3. **D-state spike at Cycle 3** (336.7ms DUT vs 28.5ms REF)
   - Correlates with: MemFree OK (1500MB), Pageboost OK (24MB)
   - Block I/O: APK files involved
   - Hypothesis: Background I/O contention at C3
```

---

## Interactive Deep Dive Questions

Agent có thể answer questions like:
- "Cycle nào xấu nhất cho gallery?" → Find max diff from per-cycle arrays
- "ActivityThreadMain spike bao nhiêu cycle?" → Count from `sequence["Activity Thread Main"]`
- "Memory có ổn định giữa các cycle?" → Check variance of `MemFree_MB` array
- "D-state ở cycle 2 correlate gì?" → Cross-reference MemFree[1], Pageboost[1], top_cpu[1]
- "Process nào chiếm CPU ở cycle có spike?" → Match spike cycle with `top_process_consume_by_cycle`

## Important Rules

1. **Per-cycle FIRST, Average SECOND** – Always show per-cycle data before averages
2. **Show raw numbers** – Don't just say "increased", show exact values per cycle
3. **Correlation, not causation** – Mark as "hypothesis", not "definitive cause"
4. **Cross-correlate cycles** – When sequence metric spikes at C2, check memory/freq/priority at C2
5. **Pattern > Average** – A pattern change (1/3→2/3 spike) is MORE significant than small avg diff
6. **Calculate avg from arrays** – `avg = sum([v for v in arr if v > 0]) / count_non_zero`

## References

- [json_schema.md](../app_launch_rca/references/json_schema.md) – JSON structure (v3)
- [metric_glossary.md](../app_launch_rca/references/metric_glossary.md)
- [trace_analysis_guide.md](references/trace_analysis_guide.md)
