# Báo cáo Phân tích & Đề xuất Tối ưu - TraceTool
 
## I. VẤN ĐỀ HIỆN TẠI CẦN REFACTOR (Ưu tiên cao)
 
### 1. Code Duplication nghiêm trọng
 
**Mức độ: Cao** — Nhiều hàm được copy-paste nguyên bản giữa các module:
 
| Hàm bị trùng lặp | Số lần xuất hiện | Vị trí |
|---|---|---|
| `write_value_or_empty()` | 2 | `execution/excel_sheet.py`, `reaction/excel_output.py` |
| `collect_trace_files()` | 2 | `execution/processor.py`, `reaction/main.py` |
| `extract_version_and_model()` | 2 | `execution/json_output.py`, `reaction/main.py` |
| `get_or_process_folder_with_cache()` | 2 | `execution/main.py`, `reaction/main.py` (gần giống 100%) |
| Logic parse model/version từ filename | 4 lần | `execution/main.py` (x2 cho DUT+REF), `reaction/main.py` (x2 cho DUT+REF) |
| `APP_MAPPING` dict | 5+ files | `execution/config.py`, `reaction/analyzer.py`, `MemoryStatus/memory_main.py`, `Pageboostd/pageboost_main.py`, `dumpstate_parser.py` |
| `TRACE_PROCESSOR_BIN` config | 2 | `execution/config.py`, `reaction/analyzer.py` |
 
**Đề xuất:**
- Tạo module `shared/` hoặc `common/` chứa các hàm dùng chung
- Tập trung `APP_MAPPING`, `TARGET_APPS`, `TRACE_PROCESSOR_BIN` vào 1 file config duy nhất
- DRY hóa logic parse model/version thành 1 hàm `extract_device_info(folder_path) -> DeviceInfo`
 
### 2. File backup cũ vẫn trong repo (~6,000 dòng thừa)
 
3 file backup chiếm **33% tổng code**:
- `execution_sql_old_backup.py` — 3,181 dòng
- `sql_query_old_backup.py` — 2,042 dòng
- `reaction_sql_old_backup.py` — 725 dòng
 
**Đề xuất:** Xóa hoàn toàn. Code cũ đã có trong git history nếu cần tham chiếu.
 
### 3. Wildcard imports (`from X import *`)
 
Có 3 chỗ dùng `from sql_query import *` và `from execution.config import *`:
- `execution/config.py` → `from sql_query import *`
- `reaction/analyzer.py` → `from sql_query import *`
- `reaction/excel_output.py` → `from reaction.analyzer import *`
 
**Rủi ro:** Namespace pollution, khó trace nguồn gốc hàm, PyInstaller có thể bỏ sót module.
 
**Đề xuất:** Thay thành explicit imports (vd: `from sql_query.base import to_ms, query_df`)
 
---
 
## II. CODE QUALITY (Ưu tiên trung bình)
 
### 4. Bare `except:` clauses (6 chỗ)
 
Không bắt exception cụ thể, che giấu lỗi thật:
- `sql_query/loadapk_asset.py:84`
- `execution/excel_sheet.py:1087`
- `dumpstate_parser.py:95, 339`
- `MemoryStatus/analyze_pss.py:27, 296`
 
**Đề xuất:** Thay bằng `except (ValueError, TypeError):` hoặc `except Exception as e:` với log.
 
### 5. `excel_sheet.py` quá lớn (1,771 dòng)
 
File này chứa logic format Excel rất phức tạp, khó maintain. 
 
**Đề xuất:** Tách thành:
- `excel_formats.py` — Định nghĩa formats (colors, styles)
- `excel_sections.py` — Các section riêng biệt (header, sequence, memory, CPU, block_io...)
- `excel_sheet.py` — Chỉ giữ orchestration logic
 
### 6. Thiếu type hints ở một số hàm quan trọng
 
Ví dụ `analyze_trace()` trả về `Dict[str, Any]` — quá generic. Nên define dataclass/TypedDict cho metrics.
 
### 7. SQL Injection tiềm ẩn
 
Các hàm trong `sql_query/` dùng f-string để build SQL trực tiếp:
```python
conditions.append(f"name = '{name_exact}'")
conditions.append(f"pid = {pid}")
```
Mặc dù đây là local Perfetto database (không có user input từ bên ngoài), nhưng nếu tên file trace chứa ký tự đặc biệt (ví dụ `'`) sẽ crash. Nên sanitize input.
 
---
 
## III. PERFORMANCE OPTIMIZATION (Ưu tiên trung bình)
 
### 8. Multiprocessing Pool không dùng context manager
 
```python
pool = Pool(processes=num_workers)
try:
    ...
finally:
    pool.close()
    pool.join()
```
 
**Đề xuất:** Dùng `with Pool(...) as pool:` để đảm bảo cleanup.
 
### 9. Cache system dùng `pickle` — rủi ro khi thay đổi cấu trúc data
 
Hiện tại chỉ dùng `CACHE_VERSION = "1.0"` để invalidate. Nếu thêm field mới vào metrics dict mà quên tăng version → lỗi silent.
 
**Đề xuất:**
- Hash cấu trúc output (schema hash) để tự động invalidate cache
- Hoặc chuyển sang JSON cache (human-readable, dễ debug)
- Thêm CLI command `--clear-cache` để xóa cache dễ dàng
 
### 10. `_process_single_trace_worker` tìm task bằng linear scan
 
```python
for task in tasks:
    if Path(task[0]).stem == filename:
        trace_file = task[0]
        break
```
 
**Đề xuất:** Dùng dict lookup thay vì loop O(n) cho mỗi trace.
 
### 11. TraceProcessor binary cứng trên Windows
 
```python
if sys.platform == "win32":
    TP_FILENAME = "trace_processor.exe"
else:
    TP_FILENAME = "trace_processor.exe"  # Cũng là .exe trên Linux???
```
 
Cả 2 nhánh đều trả về `.exe`. Trên Linux nên dùng binary không có extension.
 
---
 
## IV. TESTING (Ưu tiên cao)
 
### 12. Test coverage rất thấp
 
Chỉ có 1 file test (`tests/test_sql_query_imports.py` — 326 dòng) chủ yếu test import và function signatures. **Không có test nào cho business logic**.
 
**Đề xuất tạo tests cho:**
- `to_ms()` — unit test đơn giản
- `group_traces_by_app()` — test với nhiều filename patterns
- `extract_version_and_model()` — test edge cases
- `get_filtered_metric_rows()` — test logic Cold/Warm/Camera
- `process_block_io_data()`, `process_cpu_data_process()` — test với mock DataFrame
- Logic end_ts selection trong `analyze_trace()` — test với mock TraceProcessor
 
### 13. Không có CI/CD pipeline
 
**Đề xuất:** Thêm GitHub Actions workflow để:
- Chạy tests tự động khi push/PR
- Lint check (ruff/flake8)
- Type check (mypy)
 
---
 
## V. HƯỚNG PHÁT TRIỂN TÍNH NĂNG (Ưu tiên tùy nhu cầu)
 
### 14. CLI Mode (không cần GUI)
 
Hiện tại chỉ có GUI (PyQt6). Thêm CLI cho automation/CI:
```bash
python tracetool.py execution --dut ./DUT --ref ./REF --apps camera,clock --format excel,json
```
 
### 15. Dashboard / Web Report
 
Thay vì chỉ xuất Excel, tạo HTML report tương tác:
- Chart so sánh DUT vs REF theo từng metric
- Trend chart qua các cycles
- Highlight outliers/spikes tự động
- Có thể dùng Plotly hoặc ECharts
 
### 16. Comparison History
 
Lưu kết quả các lần chạy để so sánh trend qua thời gian:
- Database SQLite local lưu metrics history
- Chart: Version A → B → C, performance thay đổi ra sao?
- Alert khi metric tụt > X% so với baseline
 
### 17. Auto-diagnosis / RCA (Root Cause Analysis)
 
Dựa trên dữ liệu đã trích xuất, tự động phân tích:
- "App X chậm hơn REF 200ms, nguyên nhân: Block I/O tăng 150ms do thư viện libxyz.so"
- "Cycle 3 bị spike: MemFree thấp → GC pressure → Uninterruptible Sleep tăng"
- Rule-based hoặc threshold-based analysis
 
### 18. Parallel trace processing optimization
 
Hiện tại dùng `multiprocessing.Pool` với `imap`. Có thể optimize:
- `concurrent.futures.ProcessPoolExecutor` — API đơn giản hơn
- Batch traces theo app group thay vì individual files
- Async I/O cho phần đọc file/zip
 
### 19. Config file thay vì hardcode
 
Di chuyển tất cả config (APP_MAPPING, TARGET_APPS, APP_GROUPS, thresholds...) ra file YAML/TOML:
```yaml
apps:
  camera:
    package: "com.sec.android.app.camera"
    display_name: "Camera"
    group: 1
    has_special_end_ts: true
    end_ts_source: "StartPreviewRequest"
```
 
### 20. Plugin system cho custom metrics
 
Cho phép user define custom SQL queries hoặc custom metrics mà không sửa source code.
 
---
 
## VI. TÓM TẮT ƯU TIÊN
 
| # | Hạng mục | Effort | Impact | Ưu tiên |
|---|----------|--------|--------|---------|
| 1 | Xóa 3 file backup cũ | Thấp | Cao | **P0** |
| 2 | Tách code trùng lặp vào `shared/` module | Trung bình | Cao | **P0** |
| 3 | Thay wildcard imports thành explicit | Thấp | Trung bình | **P1** |
| 4 | Fix bare except clauses | Thấp | Trung bình | **P1** |
| 5 | Fix TP_FILENAME bug (Linux = .exe) | Thấp | Cao | **P1** |
| 6 | Thêm unit tests cho core logic | Trung bình | Cao | **P1** |
| 7 | Tách excel_sheet.py | Trung bình | Trung bình | **P2** |
| 8 | CLI mode | Trung bình | Cao | **P2** |
| 9 | Config file (YAML/TOML) | Trung bình | Cao | **P2** |
| 10 | HTML Dashboard report | Cao | Cao | **P3** |
| 11 | Comparison history + trend | Cao | Cao | **P3** |
| 12 | Auto-diagnosis RCA | Cao | Rất cao | **P3** |