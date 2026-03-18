---
name: trace_deep_dive
description: Phân tích chi tiết metrics của 1 app cụ thể khi PE cần debug root cause sâu hơn. Drill down vào frequency, priority, block I/O, processes per cycle.
---

# Trace Deep Dive Analysis

## Overview

Skill này cho phép AI agent thực hiện **deep-dive analysis** vào 1 app cụ thể khi Performance Engineer đã identify issue qua RCA skill nhưng cần hiểu chi tiết hơn. Agent sẽ phân tích **per-cycle data** thay vì chỉ average, so sánh **section-by-section** (bindApplication, activityStart, activityResume, Choreographer), và tìm **correlation patterns**.

## When to Use

- PE đã chạy `app_launch_rca.skill` và tìm thấy issue
- Cần hiểu **tại sao** Running tăng (frequency? compiler? process interference?)
- Cần xem **cycle nào** có vấn đề (outlier cycle vs consistent issue)
- Cần deep-dive vào **1 section** cụ thể

---

## Analysis Workflow

### Step 1: Focus Selection
Agent hỏi user:
1. App nào? (e.g., "calculator", "gallery")
2. Focus area? (Running, Sleeping, D-state, overall)
3. DUT JSON path + REF JSON path

### Step 2: Cycle-by-Cycle Breakdown

Thay vì average, show data cho **từng cycle**:

```markdown
### calculator – Running Time per Cycle

| Cycle | DUT (ms) | REF (ms) | Diff | Flag |
|-------|----------|----------|------|------|
| 1 | 220.5 | 198.3 | +22.2 | - |
| 2 | 235.1 | 205.4 | +29.7 | ⚠️ |
| 3 | 243.7 | 210.5 | +33.2 | ⚠️ |
| **Avg** | **233.1** | **204.7** | **+28.4** | |
| **Trend** | 📈 Increasing | ➡️ Stable | | |
```

### Step 3: Section-by-Section Analysis

Drill down into mỗi lifecycle section:

```markdown
### calculator – Timing Breakdown (Average)

| Section | DUT (ms) | REF (ms) | Diff | % of Total |
|---------|----------|----------|------|------------|
| Touch → Start Proc | 12.3 | 11.3 | +1.0 | 2.3% |
| Start Proc | 8.4 | 10.9 | -2.5 | 1.6% |
| → ActivityThreadMain | 50.1 | 44.9 | +5.2 | 9.3% |
| Bind Application | 58.1 | 54.4 | +3.7 | 10.8% |
| Activity Start | 134.9 | 106.5 | **+28.4** | **25.0%** |
| Activity Resume | 37.2 | 28.2 | +9.0 | 6.9% |
| Choreographer | 52.5 | 54.9 | -2.4 | 9.7% |
| → ActivityIdle | 74.9 | 52.4 | **+22.5** | **13.9%** |
| **Biggest contributor** | | | | Activity Start (+28.4ms) |
```

### Step 4: Frequency Deep Dive

Per section, per cycle frequency analysis:

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

```markdown
### calculator – Top CPU Consumers (Cycle 3 - worst cycle)

| # | Process | DUT (ms) | REF (ms) | Diff | Concern |
|---|---------|----------|----------|------|---------|
| 1 | system_server | 1185.0 | 808.7 | **+376.3** | 🔴 Major |
| 2 | surfaceflinger | 674.8 | 622.4 | +52.4 | 🟡 |
| 3 | systemui | 266.6 | 227.3 | +39.3 | - |
| 4 | launcher | 351.3 | 312.7 | +38.6 | - |
| 5 | calculator | 384.3 | 346.8 | +37.5 | - |

💡 system_server consuming +376ms in cycle 3 → likely preempting calculator
```

### Step 7: Block I/O Detail (if D-state is high)

```markdown
### gallery – Block I/O Sources (Cycle 1)

| Library/File | DUT | REF | Type |
|-------------|-----|-----|------|
| SamsungGallery2018.apk | 0 | 0 | APK |
| OneUISansKR-VF.ttf | 0 | 0 | Font |
| icudt76l.dat | 0 | 0 | ICU |
| libharfbuzz_ng.so | 0 | 0 | Native lib |
```

### Step 8: LoadApkAsset Deep Dive (if applicable)

LoadApkAsset analysis when `extend.loadapkassets` có data:

```markdown
### gallery – LoadApkAsset Analysis

**Total LoadApkAsset Time**:
| Metric | DUT (ms) | REF (ms) | Diff |
|--------|----------|----------|------|
| **Total** | **167.82** | **0** | **+167.82** 🔴 |

**Per-Process Breakdown**:
| Process | DUT (ms) | REF (ms) | Diff | % of DUT |
|---------|----------|----------|------|----------|
| system_server | 62.97 | 0 | +62.97 | 37.5% |
| system_ui | 104.85 | 0 | +104.85 | 62.5% |

**Correlation Analysis**:
- Pageboost: DUT 9.88 MB vs REF 27.73 MB (-17.85 MB 🔴)
- Memory Free: DUT 132.84 MB vs REF 145.91 MB (-13.07 MB)
- Memory Available: DUT 1364.13 MB vs REF 1324.75 MB (+39.38 MB ✅)

💡 **Root Cause Hypothesis**:
- LoadApkAsset on DUT suggests APK cache miss due to reduced pageboost prefetch (-64%)
- Low Pageboost + High LoadApkAsset = Disk I/O needed to reload APK resources
- This causes Running time increase and potentially D-state spike
```

**LoadApkAsset Analysis Steps**:
1. Check if `extend.loadapkassets` exists in DUT/REF
2. Calculate total time per device
3. List processes involved
4. Correlate with Pageboost and Memory metrics
5. Identify cache miss vs normal load pattern

---

### Step 9: Correlation Summary

```markdown
### Root Cause Hypothesis

1. **Activity Start tăng +28.4ms** (biggest section contributor)
   - Frequency: Normal (>95% @2400)
   - Priority: Normal (100% @110)
   - Hypothesis: App-side code increase in onCreate/onStart

2. **system_server CPU spike at cycle 3** (+376ms)
   - Not correlated with app frequency/priority
   - Hypothesis: Background system activity interference

3. **Compiler: verify** (both DUT and REF)
   - Both affected equally → not differentiator for this app
   - But still recommend upgrade to speed-profile
```

---

## Interactive Deep Dive Questions

Agent có thể answer questions like:
- "Cycle nào xấu nhất cho gallery?" → Find max diff cycle
- "Frequency ở activityResume có vấn đề không?" → Check frequency_by_cycle for that section
- "Process nào chiếm CPU nhiều nhất ở cycle 2?" → top_process_consume_by_cycle[1]
- "Block I/O có khác nhau giữa cycles không?" → Compare block_io_by_cycle across cycles

## Important Rules

1. **Per-cycle > Average** – Average hides outlier cycles
2. **Show raw numbers** – Don't just say "increased", show exact values
3. **Correlation, not causation** – Mark as "hypothesis", not "definitive cause"
4. **Reference RCA findings** – Link back to Flow 1/2/3 results

## References

- [json_schema.md](../app_launch_rca.skill/references/json_schema.md)
- [metric_glossary.md](../app_launch_rca.skill/references/metric_glossary.md)
- [trace_analysis_guide.md](references/trace_analysis_guide.md)
