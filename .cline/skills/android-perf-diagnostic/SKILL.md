---
name: android-perf-diagnostic
description: >
  Use this skill whenever the task involves analyzing DUT/REF performance JSON files,
  running diagnostic workflows on app launch data, identifying performance regressions,
  or reporting findings with team suggestions. Trigger on any mention of: analyzing results,
  running diagnostic, checking performance, DUT vs REF comparison, finding regressions,
  Flow 1 / Flow 2 / Flow 3, or when the user provides DUT_all_apps_*.json and REF_all_apps_*.json files.
---

# Android Performance Diagnostic Skill

## Mục đích
Skill này hướng dẫn cách **phân tích file DUT/REF JSON** sinh ra từ `execution_sql.py`,
chạy đúng 3 diagnostic flows, và báo cáo findings theo đúng team suggestion đã định nghĩa.

---

## NGUYÊN TẮC BẮT BUỘC

```
✗ KHÔNG tự đặt tên team (vd: "Storage Team", "Framework Team")
✗ KHÔNG viết "Root Cause Analysis" hay kết luận ngoài workflow
✗ KHÔNG bỏ qua Flow 1 dù kết quả có vẻ hiển nhiên
✗ KHÔNG gộp nhiều finding vào 1 suggestion chung
✗ KHÔNG dùng % để đánh giá — chỉ dùng ms/MB/count theo ngưỡng tuyệt đối
✗ KHÔNG ghi "not implemented" — nếu thiếu data phải ghi "data not exported yet"
✗ KHÔNG emit finding của sub-node nếu sub-node chưa thực sự chạy

✓ LUÔN chạy Flow 1 → Flow 2 → Flow 3 theo đúng thứ tự, cho từng app
✓ LUÔN dùng ĐÚNG câu suggestion (copy nguyên văn từ bảng Team Routing bên dưới)
✓ MỖI node trigger = 1 finding độc lập
✓ Chỉ flag khi delta VƯỢT ngưỡng (không flag khi bằng đúng ngưỡng)
✓ Sub-nodes chỉ chạy khi parent node trigger
✓ node_24: ghi rõ từng cycle bị flag, tên process và diff ms
```

---

## USAGE — QUY TRÌNH SỬ DỤNG
```
# Single session
review --dut <path_to_dut_folder> --ref <path_to_ref_folder>

# Multi-session (multiple DUT versions)
review --sessions <path1> <path2> ... --labels <DUT1> <REF1> <DUT2> <REF2> ...
```
## Steps
### Bước 0 — Chuẩn bị file
```
1. Nhận 2 file từ người dùng:
   - DUT_all_apps_[YYYYMMDD]_[HHMMSS].json
   - REF_all_apps_[YYYYMMDD]_[HHMMSS].json

2. Xác định model + variant (hỏi nếu không rõ)

3. Copy 2 file vào memory-bank/raw/ (giữ nguyên tên)

4. Đọc danh sách app từ apps_data[].app — KHÔNG hardcode
```

### Bước 1 — Đọc metrics từ mỗi app

Với từng app, trích các trường sau từ `entry` (và `reentry` nếu có):

| Metric | JSON path |
|--------|-----------|
| `uptime_minutes` | `extend.abnormal.uptime_minutes` |
| `ANR / FATAL` | `extend.abnormal.crash_count_avg` |
| `touch_duration` | `sequence["Touch Duration"]` |
| `Running` | `sequence["Running"]` |
| `Sleeping` | `sequence["Sleeping"]` |
| `Runnable` | `sequence["Runnable"]` |
| `Uninterruptible_Sleep` | `sequence["Uninterruptible Sleep"]` |
| `State` | `entry.State` (list) |
| `compiler` | `extend.abnormal.compiler` |
| `binder.count` | `binder_transaction.count` |
| `loadApkAssets` | `extend.loadapkassets` |
| `MemFree_MB` | `extend.memory.MemFree_MB` |
| `MemAvailable_MB` | `extend.memory.MemAvailable_MB` |
| `Pageboostd_MB` | `extend.memory.Pageboostd_MB` |
| `App_PSS_MB` | `extend.memory.App_PSS_MB` |

Deep fields — đọc từ file raw gốc khi node yêu cầu:

| Field | Khi nào đọc |
|-------|------------|
| `frequency_by_cycle` | Flow 2 node_12 trigger |
| `priority_by_cycle` | Flow 2 node_08 trigger |
| `start_process_abnormal` | Flow 3 node_23 |
| `top_process_consume_by_cycle` | Flow 3 node_24 |

> Nếu metric = 0 hoặc không có trong JSON → ghi rõ `"data not available"`, không để 0 như thể đã đo được.

---

### Bước 2 — Chạy Flow 1: Initial Validation

Chạy cho **mọi app**, không bỏ qua.

```
[node_01] uptime_minutes
  Điều kiện: DUT.uptime > 10 OR REF.uptime > 10
  FINDING: "Suggest re-test DUT or REF to correct test condition"

[node_02] ANR / FATAL
  Điều kiện: tồn tại trong data (exists)
  FINDING: "Suggest check FATAL/ANR"
  DB_QUERY: "Search history about ANR/FATAL" → params: [app]

[node_03] touch_duration
  Điều kiện: DUT − REF > 10ms
  FINDING: "Suggest system team for noticing this problem"
```

---

### Bước 3 — Chạy Flow 2: Core Performance State

Chạy cho **mọi app**, không bỏ qua.

```
[node_01] Running  (ngưỡng: DUT − REF > 50ms)
  FINDING: "Suggest app team checking running time increase from app side"
  → Chạy đồng thời sub-group (dù finding trên đã emit):
      [node_10] compiler
                Điều kiện: DUT.compiler == "verify" AND DUT.compiler != REF.compiler
                FINDING: "Suggest App TG apply speed-profile"
      [node_12] frequency_by_cycle  (ngưỡng: DUT% < REF% by >15%, per section)
                Sections: bindApplication, activityStart, activityResume, Choreographer
                FINDING: "Suggest system team check frequency problem"
      [node_14] DB_QUERY: "Check new app version or fix" → params: [app, version]
                (ambient query — luôn chạy khi node_01 trigger, không cần node_10/12 trigger)

[node_02] Sleeping  (ngưỡng: DUT − REF > 50ms)
  KHÔNG có finding trực tiếp cho Sleeping
  → Chạy sub-group:
      [node_19] binder.count  (ngưỡng: DUT − REF > 10 count)
                FINDING: "Suggest App team check binder increase"
      [node_23] DB_QUERY: "Check app fix history" → params: [app, version]
                (ambient query — luôn chạy khi node_02 trigger)

[node_03] Runnable  (ngưỡng: DUT − REF > 50ms)
  → Chạy trực tiếp (không qua group):
      [node_08] priority_by_cycle  (ngưỡng: DUT% < REF% by >15%, per section)
                Sections: bindApplication, activityStart, activityResume, Choreographer
                Lưu ý: priority value cao = priority thấp (scale ngược)
                FINDING: "Suggest system team check scheduling priority"

[node_04] State  (điều kiện: DUT.State == "COLD" AND REF.State == "WARM")
  → Chạy sub-group:
      [node_35] beks  (so sánh DUT vs REF, có khác nhau không)
                FINDING: "Suggest System team check BEKS config"
                Lưu ý: beks chưa được export — ghi "data not exported yet" nếu không có
      [node_36] start/kill reasons  (3 điều kiện phải đồng thời đúng)
                cond:   DUT.start_reasons.length != REF.start_reasons.length
                        OR DUT.kill_reasons.length != REF.kill_reasons.length
                cond_1: DUT.start_reasons.length != 0 AND REF.start_reasons.length != 0
                cond_2: DUT.start_reasons.length == DUT.kill_reasons.length (balanced)
                FINDING: "Suggest App team check start/kill issue"
                ⚠ JSON dùng start_reasons/kill_reasons (plural) — không phải singular
      [node_37] DB_QUERY: "Check start state history" → params: [app, version]
                (ambient query — luôn chạy khi node_04 trigger)
```

---

### Bước 4 — Chạy Flow 3: Resource Usage and Process Analysis

Chạy cho **mọi app**, không bỏ qua.

```
[node_01] loadApkAssets  (ngưỡng: DUT − REF > 30ms)
  → Chạy trực tiếp node_07 (chỉ memory, KHÔNG chạy apk/pageboost):
      [node_07] MemFree / MemAvailable
                Điều kiện: REF.MemFree − DUT.MemFree > 50 OR REF.MemAvail − DUT.MemAvail > 50
                ⚠ Direction: REF − DUT (DUT thấp hơn = tệ hơn)
                FINDING: "Suggest Kernel Memory team check mem free, mem available issue"
                DB_QUERY: "Check memory history for similar issues" → params: [model, app]

[node_02] Uninterruptible Sleep  (ngưỡng: DUT − REF > 30ms)
  → Chạy sub-group (tất cả 3 node):
      [node_07] MemFree / MemAvailable  (giống trên)
                FINDING: "Suggest Kernel Memory team check mem free, mem available issue"
                DB_QUERY: "Check memory history for similar issues" → params: [model, app]
      [node_08] apk_size
                Điều kiện: apk_size tồn tại trong data
                Nếu chưa export → ghi "data not exported yet", không emit finding
                FINDING: "Suggest app team optimize size"
                DB_QUERY: "Check apksize by app and version, then compare" → params: [app, version]
      [node_11] Pageboostd_MB  (ngưỡng: REF − DUT > 10MB)
                ⚠ Direction: REF − DUT
                FINDING: "Suggest Kernel Memory team check pageboost operation"

[node_23] start_process_abnormal  (DUT only, không compare REF)
  Điều kiện: DUT.start_process_abnormal có bất kỳ process nào
  FINDING: "Suggest App team and SWPL investigate"
  DB_QUERY: "Search history similar issue" → params: [model, process_name]

[node_24] top_process_consume_by_cycle  (DUT only, per-cycle loop)
  Logic: duyệt TỪNG cycle → mỗi process có diff > 300ms → lưu {cycle, process_name, diff}
  Sau khi duyệt hết → nếu có bất kỳ finding nào:
  FINDING (per process per cycle): "Cycle {X} | {process_name} | diff {Y}ms"
  Suggestion: "Suggest SWPL check with owner of process"
  DB_QUERY: "Check if other models or apps have similar issue" → params: [model, process_name]

[node_25] App_PSS_MB  (ngưỡng: DUT − REF > 50MB)
  FINDING: "Suggest app owner to debug PSS increase issue"
  DB_QUERY: "Search history" → params: [app]
```

---

### Bước 5 — Output format bắt buộc

Với từng app:

```
## [APP_NAME] — PASS / FINDINGS DETECTED

### Flow 1: Initial Validation
- [node_01] uptime: DUT=Xmin REF=Ymin → PASS / ⚠ FINDING: "..."
- [node_02] ANR/FATAL: → PASS / ⚠ FINDING: "..."
- [node_03] touch_duration: DUT=Xms REF=Yms delta=Zms → PASS / ⚠ FINDING: "..."

### Flow 2: Core Performance State
- [node_01] Running: DUT=Xms REF=Yms delta=Zms → PASS / ⚠ FINDING: "..."
  - [node_10] compiler: DUT=[X] REF=[Y] → PASS / ⚠ FINDING: "..."
  - [node_12] frequency: → PASS / ⚠ FINDING: "..."
  - [node_14] DB_QUERY sent
- [node_02] Sleeping: DUT=Xms REF=Yms delta=Zms → PASS / (sub-nodes)
  - [node_19] binder count: DUT=X REF=Y delta=Z → PASS / ⚠ FINDING: "..."
  - [node_23] DB_QUERY sent
- [node_03] Runnable: DUT=Xms REF=Yms delta=Zms → PASS / (sub-node)
  - [node_08] priority: → PASS / ⚠ FINDING: "..."
- [node_04] State: DUT=[...] REF=[...] → PASS / (sub-nodes)
  - [node_35] beks: → PASS / ⚠ FINDING: "..." / data not exported yet
  - [node_36] start/kill: → PASS / ⚠ FINDING: "..."
  - [node_37] DB_QUERY sent

### Flow 3: Resource Usage
- [node_01] loadApkAssets: DUT=Xms REF=Yms delta=Zms → PASS / ⚠ (sub)
  - [node_07] MemFree: REF=X DUT=Y delta=Z → PASS / ⚠ FINDING: "..."
- [node_02] Uninterruptible Sleep: DUT=Xms REF=Yms delta=Zms → PASS / ⚠ (sub)
  - [node_07] MemFree/MemAvail: REF=X DUT=Y → PASS / ⚠ FINDING: "..."
  - [node_08] apk_size: → PASS / ⚠ FINDING: "..." / data not exported yet
  - [node_11] Pageboostd: REF=X DUT=Y delta=Z → PASS / ⚠ FINDING: "..."
- [node_23] parallel process: [cycle1: [...], cycle2: [...]] → PASS / ⚠ FINDING: "..."
- [node_24] top CPU per cycle:
  - Cycle 1 | [process_name] | diff Xms → PASS / ⚠ FINDING: "..."
  - Cycle 2 | [process_name] | diff Xms → PASS / ⚠ FINDING: "..."
- [node_25] PSS: DUT=XMB REF=YMB delta=ZMB → PASS / ⚠ FINDING: "..."

### Summary Findings for [APP_NAME]
- [node_XX] "..." (suggestion phrase nguyên văn)
- [node_XX] Cycle X | process_name | diff Yms → "Suggest SWPL check with owner of process"
```

> **Không thêm bất kỳ section nào ngoài format trên.**
> Không có "Overall Status", "Priority Matrix", "Root Cause", "Recommendation".

---

### Bước 6 — Lưu session vào Memory Bank

Sau khi phân tích xong tất cả apps:

```
1. Extract summary fields từ DUT và REF (10 fields per app per section)
2. Append 2 entries vào data/[MODEL]_[VARIANT].json (DUT trước, REF sau)
3. Cập nhật registry.json (sessions_count, avg_summary, last_date, verdict_totals)
4. Nếu phát hiện pattern mới → append vào insights.md section ## [MODEL]_[VARIANT]
5. Xác nhận: "Đã lưu [MODEL]_[VARIANT] / [session_id]: [app] DUT=Xms REF=Yms, ..."
```

---

## TEAM ROUTING — SUGGESTION PHRASES

Copy nguyên văn khi emit finding. **Không được paraphrase.**

| Issue | Suggestion phrase |
|-------|-------------------|
| Uptime > 10 min | `"Suggest re-test DUT or REF to correct test condition"` |
| ANR / FATAL | `"Suggest check FATAL/ANR"` |
| Touch duration | `"Suggest system team for noticing this problem"` |
| Running time tăng | `"Suggest app team checking running time increase from app side"` |
| Compiler = verify | `"Suggest App TG apply speed-profile"` |
| CPU frequency thấp | `"Suggest system team check frequency problem"` |
| Binder count tăng | `"Suggest App team check binder increase"` |
| Thread priority thấp | `"Suggest system team check scheduling priority"` |
| BEKS mismatch | `"Suggest System team check BEKS config"` |
| Start/kill count lệch | `"Suggest App team check start/kill issue"` |
| MemFree/MemAvail thấp | `"Suggest Kernel Memory team check mem free, mem available issue"` |
| APK size tăng | `"Suggest app team optimize size"` |
| Pageboost giảm | `"Suggest Kernel Memory team check pageboost operation"` |
| Parallel process | `"Suggest App team and SWPL investigate"` |
| Top CPU process | `"Suggest SWPL check with owner of process"` |
| PSS tăng | `"Suggest app owner to debug PSS increase issue"` |

---

## NGƯỠNG ĐẦY ĐỦ

| Metric | Direction | Threshold | Unit |
|--------|-----------|-----------|------|
| Running | DUT − REF | > 50 | ms |
| Sleeping | DUT − REF | > 50 | ms |
| Runnable | DUT − REF | > 50 | ms |
| Uninterruptible Sleep | DUT − REF | > 30 | ms |
| touch_duration | DUT − REF | > 10 | ms |
| loadApkAssets | DUT − REF | > 30 | ms |
| App_PSS_MB | DUT − REF | > 50 | MB |
| MemFree_MB | **REF − DUT** | > 50 | MB |
| MemAvailable_MB | **REF − DUT** | > 50 | MB |
| Pageboostd_MB | **REF − DUT** | > 10 | MB |
| binder count | DUT − REF | > 10 | count |
| top_process diff | DUT per process | > 300 | ms |
| frequency % | DUT% < REF% per section | > 15 | % |
| priority % | DUT% < REF% per section | > 15 | % |
| uptime | DUT or REF | > 10 | min |
