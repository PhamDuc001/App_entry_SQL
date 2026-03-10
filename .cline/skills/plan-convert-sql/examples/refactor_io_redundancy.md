# Case Study: Loại bỏ I/O Redundancy

## Bối cảnh

File `execution_sql.py` (2888 lines) có hàm `find_dumpstate_content()` mở file zip lớn (50-200MB),
được gọi **~1100 lần thừa** trong một lần chạy analysis.

## Vấn đề phát hiện

```
Gọi find_dumpstate_content():
├── Worker (line 256)          → 100 lần ✅ (cần thiết, 1 lần/trace)
├── MEMORY Section (line 1024) → 400 lần ❌ (4 metrics × cycles × 2)
├── ABNORMAL Section (1224,48) → 500 lần ❌ (5 rows × cycles × 2)
└── JSON Export (2395, 2417)   → 200 lần ❌ (2 sections × cycles × 2)
                                 ────────
                        Tổng thừa: ~1100 lần
```

## Root Cause

Worker đã **pre-compute** tất cả dữ liệu cần thiết:
```python
# Worker: Đọc 1 lần, lưu kết quả
dumpstate_content = find_dumpstate_content(bugreport_path)
extend_data['App_PSS'] = parse_pss_for_app(dumpstate_content, app_name)
extend_data['Uptime'] = parse_uptime(dumpstate_content)
# ... lưu vào metrics['Precomputed_Extend_Data']
```

Nhưng downstream code **không dùng** data đã pre-compute, mà mở file lại:
```python
# MEMORY Section: Mở file lại thay vì đọc Precomputed
dumpstate_content = find_dumpstate_content(bugreport_path)  # ❌
# Rồi lại đọc từ Precomputed (?!)
val = extend_data.get('App_PSS', 0.0)
```

## Giải pháp

**Nguyên tắc: Chỉ thay nguồn dữ liệu, không đổi logic business**

```python
# BEFORE (mở zip + parse lại)
dumpstate_content = find_dumpstate_content(bugreport_path)
if dumpstate_content:
    val = parse_uptime(dumpstate_content)

# AFTER (đọc trực tiếp từ pre-computed)
extend_data = cycle.get('Precomputed_Extend_Data', {})
val = extend_data.get('Uptime', "")
```

## Cạm bẫy suýt gặp

**Variable Name Collision** — Trùng tên biến inner/outer scope:
```python
# BUG:
extend_data = {}                                    # outer (accumulator)
extend_data["key1"] = "value1"                      # ✅
for cycle in cycles:
    extend_data = cycle.get('Precomputed_Extend_Data', {})  # ← OVERWRITES outer!
extend_data["key2"] = "value2"                      # ← Ghi vào WRONG dict

# FIX:
for cycle in cycles:
    precomp = cycle.get('Precomputed_Extend_Data', {})  # ← Tên khác
```

## Kết quả

| Metric | Trước | Sau |
|--------|-------|-----|
| Số lần mở zip | ~1200 | ~100 |
| Thời gian I/O ước tính | 30-90 phút | 3-8 phút |
| Lines code | 2888 | 2858 (-30 lines) |
| Logic business | Không đổi | Không đổi |

## Quy tắc rút ra

1. **Tìm Pre-Compute trước khi đọc lại** — Nếu worker đã parse, consumer nên dùng kết quả
2. **grep_search tên function** — Đếm số lần gọi, phân loại cần/thừa
3. **Check Variable Scope sau refactor** — Tên biến mới có trùng outer scope không?
4. **Đánh giá Cost-Benefit** — Nếu complexity thấp + gain cao → refactor
