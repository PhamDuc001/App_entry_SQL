# CLINE RULES — Android Perf Memory Bank
---

## CẤU TRÚC

```
[project-root]/
├── .clinerules                        ← file này
└── memory-bank/
    ├── registry.json                  ← metadata + avg_summary mọi model+variant
    ├── insights.md                    ← pattern/insights mọi model, 1 file duy nhất
    ├── memory-bank-skill.md           ← workflows A-E chi tiết
    ├── data/
    │   ├── A266B_4GB.json             ← summary sessions (APPEND ONLY, ~725 tok/session)
    │   ├── A266B_6GB.json
    │   ├── A165F_4GB.json
    │   ├── A075F_4GB.json
    │   └── [MODEL]_[VARIANT].json     ← thêm model mới = tạo file này
    └── raw/
        ├── DUT_all_apps_YYYYMMDD_HHMMSS.json   ← file gốc từ execution_sql.py
        ├── REF_all_apps_YYYYMMDD_HHMMSS.json
        └── ...                        ← GIỮ NGUYÊN, không xóa
```

**Quy tắc cốt lõi:**
- `data/*.json` chỉ lưu **summary + pointer** → không copy raw cycle data
- `raw/` chứa file JSON gốc → agent đọc khi cần deep analysis
- Thêm model mới = tạo 1 file `data/[MODEL]_[VARIANT].json` + 2 update nhỏ

---

## ĐỌC KHI BẮT ĐẦU

Thứ tự bắt buộc:
1. `memory-bank/registry.json`  → biết model+variant nào tồn tại, model đang active
2. `memory-bank/insights.md`    → pattern đã biết trước khi làm việc
3. `memory-bank/data/[MODEL]_[VARIANT].json` → khi cần số liệu cụ thể

---

## HIỂU ĐÚNG CẤU TRÚC JSON GỐC

Khi nhận `DUT_all_apps_*.json` hoặc `REF_all_apps_*.json`:

| JSON field | Ý nghĩa |
|-----------|---------|
| `device_code` | Tên thiết bị (vd: BOS, ZA1) |
| `type` | "DUT" hoặc "REF" |
| `timestamp` | ISO datetime |
| `apps_data[].app` | Tên app — ĐỘNG, không hardcode |
| `apps_data[].entry` | Lần vào app **THỨ NHẤT** mỗi cycle (odd traces: 1,3,5...) |
| `apps_data[].reentry` | Lần vào app **THỨ HAI** mỗi cycle (even traces: 2,4,6...) |
| `entry.State` | **List** trạng thái TỪNG cycle: `["Cold","Cold","Cold"]` |
| `entry.sequence` | AVG tất cả cycles — keys KHÁC NHAU theo app, lấy NGUYÊN |
| `entry.extend` | memory + abnormal + loadapkassets + start_process_abnormal |

⚠ **QUAN TRỌNG:**
- `entry.State = ["Cold","Cold","Cold"]` = 3 cycles của entry, tất cả Cold
- entry ≠ Cold, reentry ≠ Warm — State list mới quyết định trạng thái
- `start_reasons` và `kill_reasons` là **list** (plural), không phải string
- `kill_reasons` chỉ xuất hiện khi app bị kill — không phải app nào cũng có

---

## LƯU SESSION MỚI

```
1. COPY     → Sao chép DUT_*.json và REF_*.json vào memory-bank/raw/ (giữ nguyên tên)
2. IDENTIFY → Xác định model + variant (hỏi nếu không rõ)
3. LOOKUP   → Tìm data_file trong registry.json → data/[MODEL]_[VARIANT].json
4. NEW?     → Nếu chưa có → xem mục "THÊM MODEL MỚI"
5. EXTRACT  → Trích 10 fields summary từ mỗi file (DUT + REF)
6. APPEND   → Thêm 2 entries (DUT trước, REF sau) vào data/[MODEL]_[VARIANT].json
              Mỗi entry có session_id = [device_code]_[YYYYMMDD] để ghép cặp
7. REGISTRY → Cập nhật registry.json (xem chi tiết bên dưới)
8. INSIGHTS → Pattern mới? → append vào section ## [MODEL]_[VARIANT] trong insights.md
```

### Fields cần EXTRACT vào summary (không copy phần còn lại):
```
Từ entry (và reentry nếu có):
  State, App_Execution_Time, Running, Uninterruptible_Sleep,
  App_PSS_MB, MemFree_MB, uptime_minutes,
  start_reasons, kill_reasons, binder_duration_ms, binder_count

KHÔNG lưu vào summary (chỉ đọc từ raw/ khi cần):
  top_process_consume_by_cycle, priority_by_cycle,
  frequency_by_cycle, block_io_by_cycle,
  sequence (full keys), loadapkassets, start_process_abnormal
```

### Format entry trong sessions[]:
```json
{
  "session_id": "BOS_20260309",
  "type": "DUT",
  "device_code": "BOS",
  "timestamp": "2026-03-09T14:56:46.582786",
  "source_file": "raw/DUT_all_apps_20260309_145646.json",
  "device_info": { "build": "", "chipset": "", "ram": "", "storage": "" },
  "apps": {
    "camera": {
      "entry": {
        "State": ["Cold", "Cold", "Cold"],
        "App_Execution_Time": 816.814,
        "Running": 281.051,
        "Uninterruptible_Sleep": 31.683,
        "App_PSS_MB": 122.21,
        "MemFree_MB": 364.22,
        "uptime_minutes": 6.0,
        "start_reasons": ["content provider", "content provider", "content provider"],
        "kill_reasons": null,
        "binder_duration_ms": 160.471,
        "binder_count": 143
      },
      "reentry": null
    },
    "clock": { "...cấu trúc giống camera..." }
  },
  "verdict": { "regressions": [], "improvements": [], "watch": [] },
  "notes": ""
}
```

Thứ tự trong sessions[]:
```
sessions[0]: { "type": "DUT", "session_id": "BOS_20260309", ... }
sessions[1]: { "type": "REF", "session_id": "BOS_20260309", ... }  ← cùng session_id
sessions[2]: { "type": "DUT", "session_id": "ZA2_20260312", ... }
sessions[3]: { "type": "REF", "session_id": "ZA2_20260312", ... }
```

### Cập nhật registry.json sau mỗi session:
```
active.model, active.variant, active.last_session, active.last_timestamp
variants[i].sessions_count  += 1
variants[i].last_device_code = device_code
variants[i].last_date        = YYYY-MM-DD
variants[i].avg_summary      = tính lại avg App_Execution_Time (tách DUT/REF)
variants[i].verdict_totals   = cộng dồn regressions/improvements
```

---

## QUERY

**Cross-model / ranking** (không cần mở data files):
```
→ Đọc registry.json → dùng avg_summary.dut_entry_ET / ref_entry_ET
```

**Query đơn giản** (ET, PSS, State, binder, uptime, start/kill reasons):
```
→ Đọc data/[MODEL]_[VARIANT].json
→ Filter type="DUT" hoặc type="REF" hoặc cả hai
→ apps[app_name].entry.App_Execution_Time
→ apps[app_name].entry.App_PSS_MB
→ apps[app_name].entry.State
```

**Ghép cặp DUT-REF**:
```
→ Tìm 2 entries có cùng session_id, type khác nhau
→ delta = DUT.value - REF.value
```

**Deep analysis** (top process, block IO, priority, frequency, loadapk):
```
→ Đọc data/[MODEL]_[VARIANT].json → lấy source_file của session cần
→ Mở raw/[filename] → truy cập apps_data[?app==X].entry.[section]
```

---

## THÊM MODEL MỚI (3 bước)

```
Bước 1 — Tạo file data:
  Copy data/A266B_4GB.json → data/[MODEL]_[VARIANT].json
  Sửa: "_model", "_variant" → sessions: []

Bước 2 — Đăng ký registry.json:
  Append vào "variants": {
    "model": "[MODEL]", "variant": "[VARIANT]",
    "data_file": "data/[MODEL]_[VARIANT].json",
    "chipset": "", "ref_device": "",
    "sessions_count": 0, "last_device_code": "", "last_date": "",
    "avg_summary": { "[app]": {"dut_entry_ET":null,"dut_reentry_ET":null,
                                "ref_entry_ET":null,"ref_reentry_ET":null} },
    "verdict_totals": {"regressions":0,"improvements":0},
    "notes": ""
  }

Bước 3 — Thêm section insights.md:
  ## [MODEL]_[VARIANT]
  ### Recurring Issues
  ### Performance Trend
```

**Không cần tạo folder. Không cần file nào khác.**

---

## NGƯỠNG ĐÁNH GIÁ (từ workflow thực tế)

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
| top_process diff | DUT − REF per process | > 300 | ms |
| frequency % | DUT % < REF % | > 15 | % |
| priority % | DUT % < REF % | > 15 | % |
| uptime | DUT or REF > limit | > 10 | min |

⚠ MemFree, MemAvailable, Pageboostd dùng REF−DUT (DUT thấp hơn REF = DUT tệ hơn)

---

## CHẠY DIAGNOSTIC (khi nhận DUT + REF JSON)

### NGUYÊN TẮC BẮT BUỘC — KHÔNG ĐƯỢC VI PHẠM

```
✗ KHÔNG tự đặt tên team (vd: "Storage Team", "Framework Team")
✗ KHÔNG viết "Root Cause Analysis" hay kết luận ngoài workflow
✗ KHÔNG bỏ qua Flow 1 dù kết quả có vẻ hiển nhiên
✗ KHÔNG gộp nhiều finding vào 1 team chung
✗ KHÔNG dùng % để đánh giá — chỉ dùng ms/MB/count theo ngưỡng tuyệt đối

✓ LUÔN chạy Flow 1 → Flow 2 → Flow 3 theo thứ tự
✓ LUÔN dùng ĐÚNG câu suggestion từ workflow (copy nguyên văn)
✓ MỖI node trigger = 1 finding riêng biệt
✓ Chỉ flag khi delta VƯỢT ngưỡng, không flag khi đúng ngưỡng
```

---

### BƯỚC 1 — ĐỌC DỮ LIỆU

Với từng app, đọc từ entry (và reentry nếu có):
```
uptime_minutes         ← từ extend.abnormal.uptime_minutes
ANR / FATAL            ← từ extend.abnormal.crash_count_avg
touch_duration         ← từ sequence["Touch Duration"]
Running                ← từ sequence["Running"]
Sleeping               ← từ sequence["Sleeping"]
Runnable               ← từ sequence["Runnable"]
Uninterruptible_Sleep  ← từ sequence["Uninterruptible Sleep"]
State                  ← từ entry.State (list)
compiler               ← từ extend.abnormal.compiler
binder.count           ← từ binder_transaction.count
loadApkAssets          ← từ extend.loadapkassets
MemFree_MB             ← từ extend.memory.MemFree_MB
MemAvailable_MB        ← từ extend.memory.MemAvailable_MB
Pageboostd_MB          ← từ extend.memory.Pageboostd_MB
App_PSS_MB             ← từ extend.memory.App_PSS_MB
```

Với deep fields (đọc từ raw/ khi cần):
```
start_process_abnormal, top_process_consume_by_cycle,
frequency_by_cycle, priority_by_cycle
```

---

### BƯỚC 2 — CHẠY FLOW 1 (bắt buộc, mọi app)

```
[node_01] uptime > 10 min (DUT or REF)?
  YES → FINDING: "Suggest re-test DUT or REF to correct test condition"

[node_02] ANR hoặc FATAL exists?
  YES → FINDING: "Suggest check FATAL/ANR"
        DB_QUERY: "Search history about ANR/FATAL" [app]

[node_03] DUT.touch_duration - REF.touch_duration > 10ms?
  YES → FINDING: "Suggest system team for noticing this problem"
```

---

### BƯỚC 3 — CHẠY FLOW 2 (bắt buộc, mọi app)

```
[node_01] DUT.Running - REF.Running > 50ms?
  YES → FINDING: "Suggest app team checking running time increase from app side"
        THEN run sub-group IN PARALLEL:
          [node_10] DUT.compiler == "verify" AND DUT.compiler != REF.compiler?
                    YES → FINDING: "Suggest App TG apply speed-profile"
          [node_12] DUT high-freq% < REF high-freq% by >15% (per section)?
                    YES → FINDING: "Suggest system team check frequency problem"
          [node_14] DB_QUERY: "Check new app version or fix" [app, version]

[node_02] DUT.Sleeping - REF.Sleeping > 50ms?
  YES → run sub-group (NO direct finding for Sleeping):
          [node_19] DUT.binder.count - REF.binder.count > 10?
                    YES → FINDING: "Suggest App team check binder increase"
          [node_23] DB_QUERY: "Check app fix history" [app, version]

[node_03] DUT.Runnable - REF.Runnable > 50ms?
  YES → [node_08] DUT priority% < REF priority% by >15% (per section)?
                  YES → FINDING: "Suggest system team check scheduling priority"

[node_04] DUT.State == "COLD" AND REF.State == "WARM"?
  YES → run sub-group:
          [node_35] beks differs?
                    YES → FINDING: "Suggest System team check BEKS config"
          [node_36] start_reasons.length != REF AND both non-zero AND DUT balanced?
                    YES → FINDING: "Suggest App team check start/kill issue"
          [node_37] DB_QUERY: "Check start state history" [app, version]
```

---

### BƯỚC 4 — CHẠY FLOW 3 (bắt buộc, mọi app)

```
[node_01] DUT.loadApkAssets - REF.loadApkAssets > 30ms?
  YES → [node_07] REF.MemFree - DUT.MemFree > 50MB OR REF.MemAvail - DUT.MemAvail > 50MB?
                  YES → FINDING: "Suggest Kernel Memory team check mem free, mem available issue"
                        DB_QUERY: "Check memory history for similar issues" [model, app]

[node_02] DUT."Uninterruptible Sleep" - REF."Uninterruptible Sleep" > 30ms?
  YES → run sub-group:
          [node_07] (same memory check as above)
          [node_08] apk_size exists?
                    YES → FINDING: "Suggest app team optimize size"
                          DB_QUERY: "Check apksize by app and version" [app, version]
          [node_11] REF.Pageboostd_MB - DUT.Pageboostd_MB > 10MB?
                    YES → FINDING: "Suggest Kernel Memory team check pageboost operation"

[node_03] process_abnormal group:
  [node_23] DUT.start_process_abnormal has any process?
            YES → FINDING: "Suggest App team and SWPL investigate"
                  DB_QUERY: "Search history similar issue" [model, process_name]
  [node_24] Per-cycle: any process diff > 300ms?
            YES → FINDING: "Suggest SWPL check with owner of process"
                  DB_QUERY: "Check if other models or apps have similar issue" [model, process_name]
  [node_25] DUT.App_PSS_MB - REF.App_PSS_MB > 50MB?
            YES → FINDING: "Suggest app owner to debug PSS increase issue"
                  DB_QUERY: "Search history" [app]
```

---

### BƯỚC 5 — OUTPUT FORMAT

Với mỗi app, xuất theo cấu trúc:

```
## [APP_NAME] — [PASS / FINDINGS DETECTED]

### Flow 1: Initial Validation
- [node_01] uptime: DUT=Xmin REF=Ymin → PASS / ⚠ FINDING
- [node_02] ANR/FATAL: → PASS / ⚠ FINDING
- [node_03] touch_duration: delta=Xms → PASS / ⚠ FINDING

### Flow 2: Core Performance State
- [node_01] Running: DUT=Xms REF=Yms delta=Zms → PASS / ⚠ FINDING + sub-nodes
  - [node_10] compiler: → PASS / ⚠ FINDING
  - [node_12] frequency: → PASS / ⚠ FINDING
- [node_02] Sleeping: ... → PASS / sub-nodes
- [node_03] Runnable: ... → PASS / sub-nodes
- [node_04] State: ... → PASS / sub-nodes

### Flow 3: Resource Usage
- [node_01] loadApkAssets: ... → PASS / ⚠ FINDING + sub
- [node_02] Uninterruptible Sleep: ... → PASS / ⚠ FINDING + sub
- [node_23] parallel process: → PASS / ⚠ FINDING
- [node_24] top CPU per cycle: → PASS / ⚠ FINDING
- [node_25] PSS: → PASS / ⚠ FINDING

### Summary Findings for [APP_NAME]
[Chỉ liệt kê các FINDING thực sự trigger, dùng ĐÚNG câu suggestion]
```

**KHÔNG thêm bất kỳ section nào ngoài format trên.**
