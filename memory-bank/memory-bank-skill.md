# SKILL: Android Perf Memory Bank Manager (v5 — JSON-aligned)

## Input files
- DUT_all_apps_YYYYMMDD_HHMMSS.json
- REF_all_apps_YYYYMMDD_HHMMSS.json
- Cùng format: { device_code, timestamp, type, apps_data[] }

---

## WORKFLOW A — Lưu kết quả session mới

```
1. IDENTIFY   → Xác định model + variant (hỏi nếu không rõ)
2. ROUTE      → Folder: models/[MODEL]_[VARIANT]/
3. NEW?       → Nếu chưa có folder → WORKFLOW E trước
4. PARSE DUT  → Đọc DUT_all_apps_*.json: lấy device_code, timestamp, apps_data
5. PARSE REF  → Đọc REF_all_apps_*.json: lấy device_code, timestamp, apps_data
6. APPEND     → Thêm cả 2 entries vào perf_history.json (DUT trước, REF sau)
               Giữ NGUYÊN cấu trúc apps_data từ JSON gốc
7. WRITE MD   → Tạo sessions/[DUT_device_code]_[date].md (template bên dưới)
8. UPDATE     → activeContext.md: device_code, timestamp, apps đã test
9. SUMMARY    → Tính avg App Execution Time mỗi app → cập nhật master_summary.json
10. INDEX     → Cập nhật MASTER_INDEX.md (sessions_count, last_dut, last_date)
11. INSIGHTS  → Pattern mới? → cập nhật insights.md
12. CONFIRM   → "Đã lưu BOS (A266B 4GB): camera 816ms, clock Xms, ..."
```

### Template session MD:

```markdown
# [MODEL] [VARIANT] / [device_code] — [DATE]

## Device Info
- device_code: 
- Model: 
- Variant: 
- Build: 
- Timestamp: 

## Apps tested
<!-- Liệt kê app names từ apps_data -->

## Results — Entry (lần vào app thứ 1 mỗi cycle)
| App | App Exec Time | Running | Unint. Sleep | PSS MB | Binder ms |
|-----|--------------|---------|--------------|--------|-----------|

## Results — Reentry (lần vào app thứ 2 mỗi cycle)
| App | App Exec Time | Touch Duration | PSS MB |
|-----|--------------|----------------|--------|

## Top Process Issues
<!-- Từ top_process_consume_by_cycle: process nào diff cao nhất -->

## Memory
| App | MemFree MB | MemAvailable MB | App PSS MB | Pageboostd MB |
|-----|-----------|-----------------|------------|---------------|

## Anomalies
| App | uptime_min | start_reasons | start_process_abnormal |
|-----|-----------|---------------|------------------------|

## Verdict
- Regressions: 
- Improvements: 
- Watch: 

## Raw Notes
```

---

## WORKFLOW B — Query trong 1 model+variant

```
1. ROUTE   → Đọc models/[MODEL]_[VARIANT]/perf_history.json
2. FILTER  → Lọc sessions theo type="DUT" (tránh lẫn với REF entries)
3. FIND    → Tìm app đúng trong apps_data[] by app name
4. ACCESS  → entry.sequence / reentry.sequence / extend.memory / v.v.
5. ANSWER  → "A266B 4GB / BOS (2026-03-09) camera Cold = 816ms"
```

Ví dụ path truy cập:
- entry ET:    session.apps_data[?app==camera].entry.sequence["App Execution Time"]
- entry States: session.apps_data[?app==camera].entry.State  (xác định Cold/Warm)
- reentry ET:  session.apps_data[?app==camera].reentry.sequence["App Execution Time"]
- reentry States: session.apps_data[?app==camera].reentry.State
- PSS:        session.apps_data[?app==camera].entry.extend.memory.App_PSS_MB
- Binder:     session.apps_data[?app==camera].entry.binder_transaction.duration_ms
- Top proc:   session.apps_data[?app==camera].entry.top_process_consume_by_cycle[0]

---

## WORKFLOW C — So sánh DUT vs REF (trong cùng session)

```
1. READ    → perf_history.json, tìm cặp DUT+REF cùng ngày/timestamp gần nhau
2. DIFF    → Với mỗi metric: delta = DUT.value - REF.value
3. FLAG    → Áp dụng ngưỡng: Timeline ±10ms, Sleep ±30ms, IO/Binder ±50ms
4. TABLE   → Bảng: Metric | DUT | REF | Delta | Status
```

---

## WORKFLOW D — So sánh cross-model / cross-variant

```
1. READ    → master_summary.json
2. FILTER  → Theo model hoặc variant nếu cần fair comparison
3. RANK    → Sort theo metric người dùng hỏi
4. DETAIL? → Nếu cần chi tiết → đọc perf_history.json của từng folder
```

---

## WORKFLOW E — Khởi tạo model+variant mới

```
1. MKDIR   → memory-bank/models/[MODEL]_[VARIANT]/sessions/
2. CREATE  → 4 files: projectbrief.md, activeContext.md, insights.md, perf_history.json
             perf_history.json schema v5: { _model, _variant, _schema, _field_mapping, sessions:[] }
3. MASTER  → Append entry vào master_summary.json
4. INDEX   → Append dòng vào MASTER_INDEX.md registry table
5. CONFIRM → "Đã khởi tạo A266B 6GB. Sẵn sàng nhận session đầu tiên."
```

---

## LƯU Ý QUAN TRỌNG

1. KHÔNG hardcode danh sách sequence keys — khác nhau theo app
   Camera: có onCreate, OpenCameraRequest, onResume
   Clock: có Bind Application, Activity Thread Main
   → Lưu NGUYÊN sequence dict từ JSON

2. KHÔNG hardcode danh sách app — đọc từ apps_data[].app
   Thực tế: calendar, camera, clock, message (và có thể thêm)

3. Phân biệt entry vs reentry:
   entry.State = ['Cold','Cold','Cold'] → 3 cycles của entry, tất cả Cold
   reentry.State = ['Warm','Warm','Warm'] → 3 cycles của reentry, tất cả Warm
   Nếu reentry rỗng/missing → session này không test reentry

4. Lưu cả DUT lẫn REF vào perf_history.json
   → Dùng field "type" để phân biệt khi query
