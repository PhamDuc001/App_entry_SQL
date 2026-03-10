# SKILL: Android Perf Memory Bank (v7 — Hybrid Pointer)

## Kiến trúc tối ưu token
- `data/*.json` = summary (~725 tok/session) + pointer đến file gốc
- `raw/*.json`  = file JSON gốc từ execution_sql.py (KHÔNG bao giờ copy vào data)
- `registry.json` = metadata + avg_summary cross-model (không cần mở data khi query nhanh)
- `insights.md` = tất cả pattern/insights trong 1 file

**Nguyên tắc:** Agent EXTRACT 10 fields quan trọng → lưu vào summary.
Khi cần deep analysis → đọc file gốc theo `source_file` pointer.
**Tiết kiệm 93% token** so với copy full data.

---

## WORKFLOW A — Lưu session mới

```
1. IDENTIFY  → model + variant? (hỏi nếu không rõ)
2. COPY RAW  → Sao chép DUT_*.json + REF_*.json vào memory-bank/raw/ (giữ nguyên tên file)
3. LOOKUP    → Tìm data_file trong registry.json
4. NEW?      → Chưa có data_file → WORKFLOW E trước
5. EXTRACT   → Từ DUT file: trích State, App_Execution_Time, Running, Uninterruptible_Sleep,
               App_PSS_MB, MemFree_MB, uptime_minutes, start_reasons, kill_reasons,
               binder_duration_ms, binder_count — cho từng app, entry + reentry
6. EXTRACT   → Tương tự từ REF file
7. BUILD     → Tạo 2 summary entries:
               DUT: { session_id, type:"DUT", device_code, timestamp,
                      source_file:"raw/DUT_*.json", apps:{...summary...}, verdict, notes }
               REF: { session_id (CÙNG với DUT), type:"REF", source_file:"raw/REF_*.json", ... }
8. APPEND    → Thêm DUT entry, rồi REF entry vào data/[MODEL]_[VARIANT].json
9. REGISTRY  → Cập nhật registry.json: active, sessions_count, last_device_code,
               last_date, avg_summary (tách dut/ref), verdict_totals
10. INSIGHTS → Pattern mới? → append vào ## [MODEL]_[VARIANT] trong insights.md
11. CONFIRM  → "Đã lưu A266B 4GB / BOS_20260309:
                camera entry DUT=816ms REF=?ms | PSS DUT=122MB"
```

---

## WORKFLOW B — Query summary (90% use cases)

```
1. LOOKUP  → registry.json → data_file
2. READ    → data/[MODEL]_[VARIANT].json (~725 tok)
3. FILTER  → type="DUT" | type="REF" | pair cùng session_id
4. ACCESS  → apps[app_name].entry.[field]
5. ANSWER
```

**Paths truy cập summary:**
```
App Execution Time:   apps.camera.entry.App_Execution_Time
Reentry ET:           apps.camera.reentry.App_Execution_Time
Thread Running:       apps.camera.entry.Running
Unint. Sleep:         apps.camera.entry.Uninterruptible_Sleep
PSS:                  apps.camera.entry.App_PSS_MB
MemFree:              apps.camera.entry.MemFree_MB
Uptime:               apps.camera.entry.uptime_minutes
Start reasons:        apps.camera.entry.start_reasons        ← list
Kill reasons:         apps.camera.entry.kill_reasons         ← list, null nếu không có
Binder:               apps.camera.entry.binder_duration_ms
State per cycle:      apps.camera.entry.State                ← ["Cold","Cold","Cold"]
```

**So sánh DUT vs REF:**
```
→ Tìm 2 entries cùng session_id (type="DUT" và type="REF")
→ delta = DUT.apps.camera.entry.App_Execution_Time - REF.apps.camera.entry.App_Execution_Time
→ Flag nếu |delta| > ngưỡng
```

---

## WORKFLOW C — Deep analysis (10% use cases)

Dùng khi cần: top process, block IO, priority, frequency, loadapk, sequence full keys,
start_process_abnormal — các field KHÔNG có trong summary.

```
1. READ    → data/[MODEL]_[VARIANT].json → tìm session_id cần → lấy source_file
2. OPEN    → raw/[source_file]
3. NAVIGATE→ apps_data[?app==camera].entry.top_process_consume_by_cycle
             apps_data[?app==camera].entry.block_io_by_cycle
             apps_data[?app==camera].entry.priority_by_cycle
             apps_data[?app==camera].entry.frequency_by_cycle
             apps_data[?app==camera].entry.extend.loadapkassets
             apps_data[?app==camera].entry.extend.start_process_abnormal
             apps_data[?app==camera].entry.sequence  (tất cả keys timeline)
4. ANSWER
```

---

## WORKFLOW D — Cross-model ranking

```
1. READ    → registry.json ONLY (không cần mở data files)
2. FILTER  → Theo variant nếu cần fair comparison (cùng RAM)
3. RANK    → Sort theo avg_summary.dut_entry_ET hoặc ref_entry_ET
4. TABLE:
```

| Model | Variant | Camera DUT ET | Camera REF ET | Regressions |
|-------|---------|--------------|--------------|-------------|
| A266B | 6GB     | 1250ms       | 1100ms       | 0           |
| A266B | 4GB     | 1350ms       | 1100ms       | 2           |
| A165F | 4GB     | 1480ms       | 1200ms       | 4           |

---

## WORKFLOW E — Thêm model+variant mới

```
1. CREATE  → data/[MODEL]_[VARIANT].json
   {
     "_model": "[MODEL]", "_variant": "[VARIANT]",
     "_schema": "android-perf-data-v7",
     "sessions": []
   }

2. REGISTRY → Append vào variants[]:
   {
     "model":"[MODEL]", "variant":"[VARIANT]",
     "data_file":"data/[MODEL]_[VARIANT].json",
     "chipset":"", "ref_device":"",
     "sessions_count":0, "last_device_code":"", "last_date":"",
     "avg_summary": {
       "[app]": {"dut_entry_ET":null,"dut_reentry_ET":null,
                  "ref_entry_ET":null,"ref_reentry_ET":null}
     },
     "verdict_totals":{"regressions":0,"improvements":0},
     "notes":""
   }

3. INSIGHTS → Append section:
   ## [MODEL]_[VARIANT]
   ### Recurring Issues
   ### Performance Trend

XONG. Không folder, không file nào khác.
```

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

---

## RULES BẤT DI BẤT DỊCH

```
✓ LUÔN copy raw file vào raw/ TRƯỚC khi extract summary
✓ LUÔN lưu cả DUT và REF (cùng session_id để ghép cặp)
✓ LUÔN đọc State list — đừng assume entry=Cold, reentry=Warm
✓ LUÔN dùng start_reasons / kill_reasons (plural, là list)

✗ KHÔNG copy top_process / priority / frequency / block_io vào summary
✗ KHÔNG hardcode danh sách app (đọc từ apps_data[].app)
✗ KHÔNG hardcode sequence keys (khác nhau theo app)
✗ KHÔNG xóa file trong raw/
```
