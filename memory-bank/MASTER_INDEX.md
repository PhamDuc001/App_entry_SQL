# MASTER INDEX — Android Perf Memory Bank

> File này là trung tâm điều hướng. Agent đọc file này để biết
> có bao nhiêu model+variant, và để trả lời câu hỏi cross-model.

---

## Registry — Tất cả Model + Variant

| Model  | Variant | Folder path                  | Sessions | DUT gần nhất | Ngày cập nhật |
|--------|---------|------------------------------|----------|--------------|---------------|
| A266B  | 4GB     | models/A266B_4GB/            | 0        | —            | —             |
| A266B  | 6GB     | models/A266B_6GB/            | 0        | —            | —             |
| A165F  | 4GB     | models/A165F_4GB/            | 0        | —            | —             |
| A075F  | 4GB     | models/A075F_4GB/            | 0        | —            | —             |

Khi thêm model+variant mới: append dòng vào bảng trên + tạo folder tương ứng.

---

## Cross-Model Insights

### Performance ranking (Camera Cold — cập nhật thủ công)
<!-- Agent cập nhật khi có đủ data từ master_summary.json -->

### Patterns xuất hiện ở nhiều model
<!-- Ghi ở đây khi phát hiện vấn đề không phải riêng 1 model -->

### RAM impact (4GB vs 6GB)
<!-- So sánh 4GB vs 6GB trên cùng model khi có data -->

---

## Hướng dẫn truy vấn nhanh

Câu hỏi: "Model nào nhanh nhất?"
→ Đọc master_summary.json, sort theo Camera Cold avg

Câu hỏi: "A266B 4GB vs 6GB khác nhau thế nào?"
→ Đọc master_summary.json, filter model=A266B, compare variant

Câu hỏi: "A266B ZA3 Camera Cold bao nhiêu?"
→ Đọc models/A266B_4GB/perf_history.json hoặc A266B_6GB (hỏi variant nếu không rõ)

Câu hỏi: "A266B 4GB có regression nào không?"
→ Đọc models/A266B_4GB/insights.md + perf_history.json
