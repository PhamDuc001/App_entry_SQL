# Rule for Cline SR - Code Explanation Style

## Rule Name: `/explain rule {function_name}`

## Purpose
Khi được yêu cầu `/explain rule {tên_hàm}`, Cline SR sẽ phân tích chi tiết logic flow của hàm đó với phong cách chuẩn hóa như sau:

## Structure Template

### 1. Tổng Quan về Hàm
- Mô tả ngắn gọn mục đích chính của hàm
- File chứa hàm
- Vai trò trong hệ thống

### 2. Logic Flow Chi Tiết Từng Bước
Phân tích từng bước trong hàm với format:
```python
# Code snippet
```
**Logic:** Giải thích ý tưởng và mục đích
**Ví dụ:** Input/Output minh họa cụ thể

### 3. Flow Chart Tổng Quan
Sơ đồ luồng xử lý dạng text:
```
Input
    ↓
Step 1
    ↓
Step 2
    ↓
...
    ↓
Output
```

### 4. Ví Dụ Minh Họa Đầy Đủ
Scenario thực tế với:
- Cấu trúc folder/files
- Data flow từ input đến output
- Kết quả cuối cùng

## Cấu Trúc Folder Tham Khảo

### A. Cấu Trúc Project

```
Plan_convert_SQL/
├── main_qt.py                    # GUI entry point
├── execution_sql.py              # Execution analysis logic
├── reaction_sql.py               # Reaction analysis logic  
├── sql_query.py                  # SQL query functions
├── dumpstate_parser.py           # Bugreport parsing
├── atracetosystrace.py          # Trace conversion
├── ui/
│   ├── window.py                 # Main GUI window
│   └── styles.qss                # GUI styling
├── MemoryStatus/
│   ├── abnormal_memory.py        # Memory analysis
│   ├── analyze_pss.py           # PSS analysis
│   └── memory_main.py           # Memory main logic
├── Pageboostd/
│   └── pageboost_main.py         # Pageboost analysis
├── perfetto/
│   └── trace_processor          # Perfetto tool
├── build/                       # Build output
└── .clinerules/                 # Cline SR rules
    └── explain_rule.md          # This rule file
```

### B. Cấu Trúc Folder Dữ Liệu (DUT/REF)

```
DUT/ hoặc REF/
├── A576BYK7_BOS_251128_251128_085009_camera.log                  # Camera app - Cycle 1 Entry
├── A576BYK7_BOS_251128_251128_085027_camera.log                  # Camera app - Cycle 1 Reentry
├── A576BYK7_BOS_251128_251128_085123_1part_Bugreport.zip          # Bugreport Group 1
├── A576BYK7_BOS_251128_251128_090007_helloworld.log              # Helloworld app - Cycle 1 Entry
├── A576BYK7_BOS_251128_251128_090025_calllog.log                 # Calllog app - Cycle 1 Entry
├── A576BYK7_BOS_251128_251128_090035_dial.log                    # Dial app - Cycle 1 Entry
├── A576BYK7_BOS_251128_251128_090058_clock.log                   # Clock app - Cycle 1 Entry
├── A576BYK7_BOS_251128_251128_090134_calllog.log                 # Calllog app - Cycle 1 Reentry
├── A576BYK7_BOS_251128_251128_090144_dial.log                    # Dial app - Cycle 1 Reentry
├── A576BYK7_BOS_251128_251128_090207_clock.log                   # Clock app - Cycle 1 Reentry
├── A576BYK7_BOS_251128_251128_090304_2part_Bugreport.zip          # Bugreport Group 2
```

**Quy tắc đặt tên file:**
- `{DeviceCode}_{Location}_{Date}_{Time}_{app}.log`
- `{DeviceCode}_{Location}_{Date}_{Time}_{group}part_Bugreport.zip`
- Entry/Reentry được xác định theo thứ tự thời gian (file lẻ = entry, file chẵn = reentry)
- Bugreport được nhóm theo app groups (1-6)

## Quy Tắc Giải Thích

### A. Format Chung
- Sử dụng markdown với syntax highlighting
- Code blocks cho code snippets
- Bold cho emphasis
- Numbered lists cho các bước

### B. Chi Tiết Mỗi Bước
1. **Code snippet**: Trích dẫn đoạn code liên quan
2. **Logic**: Giải thích "tại sao" và "như thế nào"
3. **Ví dụ**: Input/Output cụ thể với data thật

### C. Ví Dụ Minh Họa
- Scenario thực tế với file paths
- Data structures minh họa
- Expected output format

### D. Language
- Tiếng Việt (cho project này)
- Technical terms giữ nguyên tiếng Anh
- Clear, concise, structured

## Áp Dụng Cho Các Hàm Chính

### Core Functions
- `process_all_traces()` (execution_sql.py)
- `analyze_trace()` (sql_query.py) 
- `run_analysis()` (execution_sql.py)
- `collect_bugreport_mappings()` (dumpstate_parser.py)

### GUI Functions
- `MainWindow.__init__()` (ui/window.py)
- `WorkerThread.run()` (ui/window.py)

### Analysis Functions
- Memory analysis functions
- Pageboost analysis functions
- Reaction analysis functions

## Example Output Structure
```markdown
# Phân Tích Chi Tiết Logic Flow của `{function_name}`

## Tổng Quan về `{function_name}`
...

## Logic Flow Chi Tiết Từng Bước

### Bước 1: ...
```python
# Code
```
**Logic:** ...
**Ví dụ:** ...

### Bước 2: ...
...

## Flow Chart Tổng Quan
...

## Ví Dụ Minh Họa Đầy Đủ
...
```

## Usage Examples

### Example 1: Core Function
```
User: /explain rule process_all_traces
```
→ Phân tích chi tiết hàm `process_all_traces` trong execution_sql.py

### Example 2: GUI Function  
```
User: /explain rule MainWindow.__init__
```
→ Phân tích logic khởi tạo GUI window

### Example 3: Analysis Function
```
User: /explain rule analyze_trace
```
→ Phân tích logic phân tích trace data

## Implementation Notes

1. **File Location**: Luôn kiểm tra file chứa hàm trước khi phân tích
2. **Dependencies**: Xác định các hàm phụ thuộc để giải thích đầy đủ
3. **Data Flow**: Theo dõi luồng data từ input đến output
4. **Error Handling**: Phân tích các trường hợp error và fallback logic
5. **Performance**: Ghi chú các điểm tối ưu performance (multiprocessing, caching, etc.)

## Quality Standards

- **Completeness**: Phải cover tất cả các logic branches chính
- **Accuracy**: Code examples phải chính xác và executable
- **Clarity**: Giải thích dễ hiểu cho developer levels khác nhau
- **Consistency**: Đúng format template cho mọi hàm
- **Practicality**: Ví dụ thực tế có thể áp dụng ngay

Rule này đảm bảo consistency trong việc giải thích code và giúp developer hiểu rõ logic flow của từng hàm trong project.
