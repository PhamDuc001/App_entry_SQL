# CLINE RULES — Android Perf Memory Bank (v5 — JSON-aligned)
# Đặt tại ROOT của project. Cline SR đọc tự động.

---

## MEMORY BANK — BẮT BUỘC ĐỌC KHI KHỞI ĐỘNG

Trước khi làm BẤT CỨ task nào, đọc tuần tự:
1. memory-bank/MASTER_INDEX.md
2. memory-bank/models/[MODEL]_[VARIANT]/activeContext.md  (model đang làm việc)
3. memory-bank/models/[MODEL]_[VARIANT]/insights.md
4. memory-bank/models/[MODEL]_[VARIANT]/perf_history.json (khi cần số liệu)

---

## KIẾN TRÚC 2 TẦNG

TẦNG MASTER (cross-model):
  memory-bank/MASTER_INDEX.md          — registry + cross-model insights
  memory-bank/master_summary.json      — avg summary mỗi model+variant

TẦNG PER-MODEL (chi tiết):
  memory-bank/models/[MODEL]_[VARIANT]/
  ├── projectbrief.md
  ├── activeContext.md
  ├── insights.md
  ├── perf_history.json    ← raw session data, schema v5
  └── sessions/[device_code]_[DATE].md

---

## MAPPING: JSON GỐC → MEMORY BANK

Khi nhận file DUT_all_apps_YYYYMMDD_HHMMSS.json hoặc REF tương tự:

| JSON gốc (top-level)               | Memory Bank           |
|------------------------------------|-----------------------|
| device_code                        | device_code (TÊN DUT) |
| timestamp                          | timestamp             |
| type ("DUT" / "REF")               | type                  |

| JSON gốc (per-app)                 | Ý nghĩa               |
|------------------------------------|-----------------------|
| app.entry                          | Lần vào app thứ NHẤT mỗi cycle (odd traces) |
| app.reentry                        | Lần vào app thứ HAI mỗi cycle (even traces) |
| entry.State / reentry.State        | List trạng thái TỪNG cycle: Cold hoặc Warm  |
| entry.sequence                     | Lưu NGUYÊN toàn bộ   |
| entry.extend.memory                | MemFree, PSS...       |
| entry.extend.abnormal              | uptime, start_reasons |
| entry.extend.loadapkassets         | loadapkassets         |
| entry.extend.start_process_abnormal| process anomalies     |
| entry.binder_transaction           | binder duration+count |
| entry.block_io_by_cycle            | block IO per cycle    |
| entry.top_process_consume_by_cycle | top process per cycle |
| entry.priority_by_cycle            | CPU priority per cycle|
| entry.frequency_by_cycle           | CPU freq per cycle    |

QUAN TRỌNG — KHÔNG HARDCODE:
- sequence keys khác nhau theo từng app (camera có onCreate/OpenCameraRequest,
  clock có Bind Application/Activity Thread Main, v.v.) → lưu NGUYÊN dict
- Danh sách apps là ĐỘNG (calendar, camera, clock, message, gallery, v.v.)
  → không giả định cố định 3 app

---

## FORMAT LƯU VÀO perf_history.json (schema v5)

Append entry với cấu trúc sau vào mảng "sessions":

{
  "device_code": "[từ JSON gốc]",
  "type": "DUT",
  "timestamp": "[từ JSON gốc, ISO datetime]",
  "device_info": { "build": "", "chipset": "", "ram": "", "storage": "" },
  "apps_data": [
    {
      "app": "[tên app]",
      "entry": {
        "State": [...],
        "sequence": { ...lưu nguyên từ JSON gốc... },
        "extend": {
          "memory": { "MemFree_MB":0, "MemAvailable_MB":0, "App_PSS_MB":0, "Pageboostd_MB":0 },
          "abnormal": { "uptime_minutes":0, "start_reasons":[] },
          "loadapkassets": {},
          "start_process_abnormal": []
        },
        "binder_transaction": { "duration_ms":0, "count":0 },
        "block_io_by_cycle": [...lưu nguyên...],
        "top_process_consume_by_cycle": [...lưu nguyên...],
        "priority_by_cycle": [...lưu nguyên...],
        "frequency_by_cycle": [...lưu nguyên...]
      },
      "reentry": { ...cấu trúc giống entry... }
    }
  ],
  "verdict": { "regressions":[], "improvements":[], "watch":[] },
  "notes": ""
}

---

## SAU KHI PHÂN TÍCH XONG MỘT SESSION (thứ tự thực hiện)

1. Nhận DUT_all_apps_*.json + REF_all_apps_*.json
2. Xác định model + variant (hỏi nếu không rõ)
3. Tạo thư mục models/[MODEL]_[VARIANT]/ nếu chưa có → WORKFLOW E
4. Append cả 2 entries (DUT + REF) vào perf_history.json
5. Tạo session MD: models/[MODEL]_[VARIANT]/sessions/[device_code]_[YYYYMMDD].md
6. Cập nhật activeContext.md
7. Cập nhật master_summary.json (avg App Execution Time per app)
8. Cập nhật MASTER_INDEX.md
9. Cập nhật insights nếu có pattern mới

---

## PATH TRUY CẬP KHI QUERY

- entry ET (all cycles avg): apps_data[i].entry.sequence["App Execution Time"]
- reentry ET (all cycles avg): apps_data[i].reentry.sequence["App Execution Time"]
- entry States:           apps_data[i].entry.State  → ['Cold','Cold','Cold'] hoặc mix
- reentry States:         apps_data[i].reentry.State
- Memory PSS:             apps_data[i].entry.extend.memory.App_PSS_MB
- Binder:                 apps_data[i].entry.binder_transaction.duration_ms
- Top process cycle 1:    apps_data[i].entry.top_process_consume_by_cycle[0].process

Trích dẫn: "A266B 4GB / BOS (2026-03-09) Camera Cold = 816ms"

---

## NGƯỠNG ĐÁNH GIÁ (DUT - REF)

| Metric group              | Regression | Improvement |
|---------------------------|------------|-------------|
| Timeline / Thread states  | > +10ms    | < -10ms     |
| Uninterruptible Sleep     | > +30ms    | < -30ms     |
| Block I/O / Binder / APK  | > +50ms    | < -50ms     |
