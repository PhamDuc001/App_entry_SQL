# PROMPT TEMPLATES — Android Perf Diagnostic

Dùng các template này khi ra lệnh cho Agent phân tích DUT/REF.
Copy nguyên văn, chỉ thay phần trong [].

---

## TEMPLATE 1 — Phân tích đầy đủ (dùng hàng ngày)

```
Phân tích hiệu năng theo workflow chuẩn cho [MODEL] [VARIANT].

File DUT: [DUT_all_apps_YYYYMMDD_HHMMSS.json]
File REF: [REF_all_apps_YYYYMMDD_HHMMSS.json]

Yêu cầu:
1. Chạy đúng thứ tự Flow 1 → Flow 2 → Flow 3 cho từng app
2. Với mỗi node, ghi rõ: giá trị đo được, delta, có vượt ngưỡng không
3. Chỉ tạo FINDING khi delta vượt ngưỡng theo bảng trong .clinerules
4. Dùng ĐÚNG câu suggestion từ workflow — không tự đặt tên team
5. Xuất theo format: node-by-node, sau đó Summary Findings per app
6. Sau khi xong diagnostic, lưu session vào memory bank
```

---

## TEMPLATE 2 — Phân tích nhanh 1 app cụ thể

```
Chạy diagnostic workflow cho app [camera/gallery/clock/...] trong session:
File DUT: [tên file]
File REF: [tên file]

Chạy đủ Flow 1 + Flow 2 + Flow 3. Ghi rõ từng node PASS hay FINDING.
Dùng đúng suggestion phrase từ workflow, không thêm team hay phân tích ngoài workflow.
```

---

## TEMPLATE 3 — Chỉ kiểm tra 1 metric nghi ngờ

```
Trong session [device_code]_[YYYYMMDD], app [tên app]:
- Kiểm tra node [node_id] theo Flow [1/2/3]
- DUT value: [X]ms / REF value: [Y]ms
- Ngưỡng: [Z]ms
- Nếu trigger: chạy tiếp các sub-node theo workflow
- Dùng đúng suggestion phrase, không tự kết luận
```

---

## TEMPLATE 4 — Re-run diagnostic sau khi đã có summary

```
Đọc session [session_id] từ data/[MODEL]_[VARIANT].json.
Re-run diagnostic Flow 2 node_01 (Running) và Flow 3 node_02 (Uninterruptible Sleep)
cho app [tên app].

Nếu cần deep data (top_process, frequency, priority), đọc từ raw/[source_file].
Ghi rõ từng node và sub-node. Dùng đúng suggestion phrase.
```

---

## LỖI PHỔ BIẾN CẦN TRÁNH KHI VIẾT PROMPT

| Prompt sai | Tại sao sai | Thay bằng |
|-----------|------------|-----------|
| "Phân tích performance và đưa ra root cause" | Agent tự suy luận ngoài workflow | "Chạy Flow 1→2→3 và báo cáo từng node" |
| "Gallery có vấn đề gì?" | Quá mở, agent tự quyết | "Chạy diagnostic workflow cho app gallery" |
| "Team nào cần fix?" | Agent tự đặt tên team | "Liệt kê suggestion phrase từ các FINDING" |
| "Tại sao I/O wait cao?" | Yêu cầu phân tích ngoài workflow | "Chạy Flow 3 node_02 và sub-nodes cho app này" |
| "Summary thôi, không cần chi tiết" | Bỏ qua node → bỏ sót finding | "Chạy đủ 3 Flow, ghi PASS/FINDING từng node" |

---

## VÍ DỤ PROMPT ĐẦY ĐỦ (copy và dùng ngay)

```
Phân tích hiệu năng theo workflow chuẩn cho A266M 8GB.

File DUT: DUT_all_apps_20260309_145646.json
File REF: REF_all_apps_20260309_145646.json

Yêu cầu:
1. Với từng app (đọc từ apps_data[].app, không hardcode):
   - Flow 1: kiểm tra uptime, ANR/FATAL, touch_duration
   - Flow 2: kiểm tra Running, Sleeping, Runnable, State theo đúng ngưỡng
   - Flow 3: kiểm tra loadApkAssets, Uninterruptible Sleep, process anomalies, PSS
2. Mỗi node: ghi [node_id] | DUT=X | REF=Y | delta=Z | PASS hoặc ⚠ FINDING
3. Sub-nodes chỉ chạy khi parent trigger — ghi rõ đã chạy sub-node nào
4. FINDING chỉ dùng suggestion phrase từ workflow (không tự đặt tên team)
5. Cuối mỗi app: Summary Findings (chỉ các node trigger)
6. Sau khi phân tích xong: lưu session vào memory bank data/A266M_8GB.json

Không thêm Root Cause Analysis, Priority Matrix, hay bất kỳ section nào ngoài format trên.
```
