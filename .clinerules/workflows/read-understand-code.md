# Workflow: Đọc và Hiểu Code (Plan_convert_SQL)

---

## 📋 Mục đích

Workflow này hướng dẫn Cline cách đọc và hiểu code trong Plan_convert_SQL hiệu quả, tận dụng toàn bộ khả năng từ skill system và analysis scripts.

---

## 🎤 Khi nào sử dụng

- User muốn hiểu một function/module cụ thể
- User muốn trace data flow qua hệ thống
- User muốn tìm hiểu architecture của Plan_convert_SQL
- User cần giải thích cách một feature hoạt động
- User muốn biết data structures được sử dụng ở đâu

---

## 🛠️ CÔNG CỤ SỬ DỤNG

### Từ Skill System:
- `.cline/skills/plan-convert-sql/SKILL.md` - Documentation đầy đủ
- `.cline/skills/plan-convert-sql/examples/` - Real-world examples
- `.cline/skills/plan-convert-sql/resources/` - Templates

### Từ Scripts:
- `analyze_complexity.py` - Phân tích function structure
- `find_redundancy.py` - Tìm data flow patterns
- `check_imports.py` - Hiểu dependencies

### Từ Cline:
- `read_file` - Đọc code
- `list_code_definition_names` - Xem structure
- `search_files` - Tìm usage patterns
- `grep_search` - Tìm references

---

## 🔄 QUY TRÌNH CHUẨN

### Phase 1: Thu thập thông tin (Discovery)

```
1. Xác định scope:
   - File/Function nào cần hiểu?
   - Mục tiêu là gì? (trace data flow, hiểu logic, tìm bug, etc.)

2. Kiểm tra Skill documentation:
   - Đọc section tương ứng trong SKILL.md
   - Ví dụ: "Section 3.1. Core Processing Functions"
   
3. Chạy analysis scripts:
   python analyze_complexity.py <file_path>
   python check_imports.py <file_path>
```

---

### Phase 2: Đọc và phân tích code

```
4. Đọc function definition:
   - Use: read_file(file_path, start_line, end_line)
   - Tập trung vào:
     * Function signature (input, output)
     * Key variables
     * Control flow
     * Data transformations

5. Xem data structures:
   - Nếu function nhận/trả về dict/list → hiểu structure
   - Tham khảo SKILL.md "Section 2.1. Key Data Structures"
   - Trace data flow từ input → output

6. Tìm usage của function:
   - Use: grep_search(function_name)
   - Xem function được gọi ở đâu
   - Hiểu context sử dụng
```

---

### Phase 3: Hiểu data flow

```
7. Trace data flow:
   - Input đến từ đâu?
   - Đi qua các transformations nào?
   - Output được dùng ở đâu?
   
8. Sử dụng find_redundancy.py:
   python find_redundancy.py <file_path>
   - Xem most called functions → hiểu dependencies
   - Xem duplicate patterns → hiểu code repetition

9. Tìm references trong codebase:
   - Use: search_files(directory, regex, file_pattern)
   - Tìm các functions/classes liên quan
   - Hiểu architecture relationships
```

---

### Phase 4: Tổng hợp và giải thích

```
10. Tạo giải thích chi tiết:
    - Overview: Function làm gì?
    - Input/Output format
    - Logic chính (step-by-step)
    - Data structures sử dụng
    - Edge cases được xử lý
    - Performance characteristics

11. Nếu cần, so sánh với examples:
    - Tham khảo examples/refactor_io_redundancy.md
    - Tham khảo examples/data_flow_patterns.md
    
12. Cung cấp context từ SKILL.md:
    - "Xem SKILL.md section X để hiểu pattern Y"
    - Link đến các examples liên quan
```

---

## 📐 CÁC SCENARIO KHÁC NHAU

### Scenario 1: Hiểu function mới (basic)

**User request:**
"Giải thích function calculate_metrics_for_app trong execution_sql.py"

**Cline workflow:**
```bash
# Step 1: Check SKILL.md reference
- Đọc SKILL.md Section 3.1 "Key Functions"

# Step 2: Run analyze_complexity.py
python analyze_complexity.py execution_sql.py
# → Tìm calculate_metrics_for_app trong output:
#   Lines: 2300-2500
#   Complexity: CC=12
#   Args: 6
#   Nesting: 5

# Step 3: Read function
read_file(execution_sql.py, 2300, 2500)

# Step 4: Analyze
- Xem docstring (nếu có)
- Tách thành các sections (1, 2, 3, 4, 5, 6)
- Hiểu input/output:
  * Input: cycles (list of dict), app_name, launch_type, ...
  * Output: dict with sequence, extend, top_process, etc.

# Step 5: Trace data flow
- sequence: được tính từ valid_cycles
- extend: từ Precomputed_Extend_Data
- top_process: so sánh DUT vs REF CPU data

# Step 6: Giải thích cho user
```

---

### Scenario 2: Trace data flow qua hệ thống

**User request:**
"Trace data flow từ trace file đến Excel output"

**Cline workflow:**
```bash
# Step 1: Start từ entry point
- Đọc SKILL.md Section 4.1 "Trace Processing Flow"

# Step 2: Trace từng bước:
1. collect_trace_files() → list .log files
2. group_traces_by_app() → {app: [(file, occurrence)]}
3. build_trace_bugreport_mapping() → {file: mapping_info}
4. process_all_traces() → multiprocessing
   - _process_single_trace_worker() → analyze_trace()
5. create_sheet() → write Excel

# Step 3: Run find_redundancy.py
python find_redundancy.py execution_sql.py
# → Tìm most called functions để hiểu flow

# Step 4: Check data structures
- SKILL.md Section 2.1 "Key Data Structures"
- Xem format DUT/REF results
- Xem format cycle data

# Step 5: Tạo flowchart dạng text
Trace File → analyze_trace() → Metrics Dict → create_sheet() → Excel
```

---

### Scenario 3: Hiểu cache system

**User request:**
"Giải thích cache system trong Plan_convert_SQL hoạt động như thế nào"

**Cline workflow:**
```bash
# Step 1: Read SKILL.md
- Section 4.2 "Cache System Flow" (chi tiết nhất)
- Section 3.1 "Key Functions" → get_or_process_folder_with_cache()

# Step 2: Read function implementation
read_file(execution_sql.py, 1920, 2050)  # function cache

# Step 3: Trace logic:
1. Check .perf_cache.pkl exists?
   - NO → Process all, save cache
   - YES → Check version
     - Mismatch → Re-process all
     - Match → Compare target_apps
       - Cache == current → Load and return
       - Cache is None → Extract subset
       - Cache is subset of current → Process missing, merge, save

# Step 4: Analyze complexity
python analyze_complexity.py execution_sql.py
# → get_or_process_folder_with_cache CC=?

# Step 5: Giải thích với examples
- Cache hit: ⚡ FAST (seconds)
- Cache miss: SLOW (minutes)
- Partial cache: Medium (only missing apps)
```

---

### Scenario 4: Hiểu CPU diff calculation

**User request:**
"Giải thích cách tính TOP 5 CPU diff trong Plan_convert_SQL"

**Cline workflow:**
```bash
# Step 1: Read SKILL.md
- Section 4.3 "CPU Diff Calculation Flow"
- Section 3.1 → calculate_metrics_for_app() section 3

# Step 2: Read code
read_file(execution_sql.py, 2425, 2470)

# Step 3: Phân tích từng bước:
1. Build REF lookup maps (ref_by_sql, ref_by_dump)
2. For each DUT process:
   - Match REF bằng Tiered Matching:
     a. SQL name match (nếu không phải PID-xxxx)
     b. Dumpstate name fallback
   - Calculate diff = DUT - REF
   - 3 trường hợp:
     * Match found → diff = DUT - REF
     * No match + has dumpstate → diff = DUT (new process)
     * No match + no dumpstate → diff = 0 (noise)

# Step 4: Run find_redundancy.py
python find_redundancy.py execution_sql.py
# → Tìm get() calls lặp nhiều

# Step 5: Tóm tắt logic
- Matching: SQL name → Dumpstate name
- Diff: DUT - REF (hoặc DUT nếu mới)
- Filter: 0.0 diff = bỏ qua noise
- Sort: descending, take TOP 5
```

---

### Scenario 5: Hiểu multiprocessing architecture

**User request:**
"Giải thích cách Plan_convert_SQL dùng multiprocessing để xử lý traces"

**Cline workflow:**
```bash
# Step 1: Read SKILL.md
- Section 4.1 "Trace Processing Flow" → multiprocessing section

# Step 2: Read key functions:
1. process_all_traces() - main orchestration
2. _process_single_trace_worker() - worker function
3. analyze_trace() - trace processing

# Step 3: Trace parallel processing:
- Tasks: [(file_path, occurrence, app_name, pid_mapping, mapping_info, folder_path)]
- Pool(processes=num_workers)
- pool.imap(_process_single_trace_worker, tasks) → parallel execution

# Step 4: Check data sharing:
- Global variables: _BUGREPORT_MAPPINGS (không dùng)
- Precomputed data: Precomputed_Extend_Data (parse tại worker)
- Results: collected in results dict

# Step 5: Analyze complexity
python analyze_complexity.py execution_sql.py
# → process_all_traces CC=?

# Step 6: Giải thích advantages:
- Parallel processing → faster
- Pre-compute dumpstate at worker → avoid repeated I/O
- Results aggregation → main thread handles
```

---

## 🔑 CÁC SKILL SECTIONS PHỔ BIẾN DÙNG ĐỂ ĐỌC CODE

| Mục đích | Section trong SKILL.md | Nội dung chính |
|----------|------------------------|---------------|
| Hiểu function cụ thể | Section 3.1 | Mô tả signature, input/output, steps |
| Trace data flow | Section 4 (1-4) | Flowcharts chi tiết từng workflow |
| Hiểu data structures | Section 2.1 | Format dicts, lists, nested structures |
| Refactor code | Section 6 | Patterns, common scenarios |
| Tối ưu performance | Section 7 | Bottlenecks, optimizations |
| Debug issues | Section 8 | Error handling, debug tips |
| Add new metric | Section 9.1 | Steps để implement metric mới |
| Code review checklist | Section 10 | Checklist để đánh giá code |
| Tool usage | Section 11 | Tool nào cho task nào |
| Real-world examples | Section 12 | Examples hoàn chỉnh |

---

## 📝 CÁC PATTERNS ĐỂ ĐỌC CODE HIỆU QUẢ

### Pattern 1: Start from high-level, drill down

```
1. Đọc SKILL.md → Hiểu architecture tổng quan
2. Đọc main entry point (run_analysis)
3. Trace xuống các helper functions
4. Đọc data flow diagram
5. Drill vào từng function detail
```

**Ví dụ:** Đọc trace processing
```
run_analysis()
  ↓
process_all_traces()
  ↓
_process_single_trace_worker()
  ↓
analyze_trace()
  ↓
Perfetto queries (sql_query.py)
```

---

### Pattern 2: Understand data structures first

```
1. Đọc SKILL.md Section 2.1 "Key Data Structures"
2. Hiểu input format
3. Hiểu output format
4. Trace transformations
5. Tìm tại sao format lại như vậy
```

**Ví dụ:** Đọc calculate_metrics_for_app
```
Input: cycles = [
  {
    "App Execution Time": 447.703,
    "CPU_Process_Data": [...],
    "Precomputed_Extend_Data": {...}
  }
]

Output: result = {
  "sequence": {...},
  "extend": {...},
  "top_process_consume_by_cycle": [...]
}
```

---

### Pattern 3: Use tools to support understanding

```
1. analyze_complexity.py → Hiểu function structure
   - Lines, CC, nesting depth
   - Top functions by complexity
   
2. find_redundancy.py → Hiểu data flow
   - Most called functions
   - I/O patterns
   
3. check_imports.py → Hiểu dependencies
   - Các modules được import
   - Circular imports
   
4. list_code_definition_names → Xem structure
   - Tất cả functions/classes trong file
   
5. search_files → Tìm usage
   - Function được gọi ở đâu?
   - Data được dùng ở đâu?
```

---

### Pattern 4: Trace from both ends

```
1. Trace from user request → output:
   - User clicks "Analyze"
   - run_analysis() được gọi
   - ... → Excel/JSON created
   
2. Trace from specific data → source:
   - Về TOP 5 CPU diff trong Excel đến từ đâu?
   - calculate_metrics_for_app() section 3
   - DUT/REF CPU data từ analyze_trace()
   - SQL queries trong sql_query.py
   
3. Nối hai trace → hiểu toàn bộ flow
```

---

## ⚠️ CÁC TRAP CẦN TRÁNH

### Trap 1: Đọc quá nhiều code cùng lúc

**Vấn đề:** Đọc 2000+ lines cùng lúc → không hiểu gì

**Giải pháp:**
- Bắt đầu với function mục tiêu (50-100 lines)
- Mở rộng dần khi cần
- Dùng SKILL.md làm map

---

### Trap 2: Không hiểu data structures

**Vấn đề:** Đọc code nhưng không hiểu input/output format

**Giải pháp:**
- Luôn đọc SKILL.md Section 2.1 trước
- Tìm examples trong examples/ folder
- Trace data format qua transformations

---

### Trap 3: Bỏ qua context

**Vấn đề:** Đọc function isolated, không biết tại sao tồn tại

**Giải pháp:**
- Grep_search để tìm references
- Hiểu function được gọi ở đâu, khi nào
- Xem edge cases được xử lý

---

### Trap 4: Không run scripts trước

**Vấn đề:** Đọc code thủ công, mất thời gian

**Giải pháp:**
- Luôn run analyze_complexity.py trước
- Dùng script outputs để focus vào functions quan trọng
- Tận dụng automated analysis

---

## ✅ CHECKLIST CHO "ĐỌC HIỂU CODE"

Khi đọc code, đảm bảo:

### Understanding
- [ ] Đọc SKILL.md section tương ứng
- [ ] Chạy analyze_complexity.py để hiểu structure
- [ ] Hiểu function signature (input, output)
- [ ] Hiểu logic chính (step-by-step)
- [ ] Hiểu data structures được sử dụng
- [ ] Hiểu tại sao function tồn tại (mục đích)

### Tracing
- [ ] Tìm function được gọi ở đâu (grep_search)
- [ ] Tìm functions được gọi bởi function này
- [ ] Trace data flow từ input → output
- [ ] Hiểu dependencies với các modules khác

### Patterns
- [ ] Tìm patterns tương tự trong examples/
- [ ] Tham khảo SKILL.md sections cho patterns
- [ ] So sánh với các functions tương tự

### Validation
- [ ] Chạy find_redundancy.py để validate understanding
- [ ] Check imports để hiểu dependencies
- [ ] Xem code review checklist (SKILL.md Section 10)

---

## 🎯 PROMPT EXAMPLES CHO USER

### Prompt 1: Hiểu function cơ bản
```
"Đọc và giải thích function process_all_traces trong execution_sql.py:

Yêu cầu:
1. Đọc SKILL.md Section 3.1 và 4.1 trước
2. Chạy analyze_complexity.py execution_sql.py
3. Giải thích:
   - Input parameters là gì?
   - Output format trả về thế nào?
   - Logic xử lý chính (multiprocessing, trace mapping)
   - Các helper functions được gọi
   - Cache system hoạt động ở đâu trong function này?"
```

---

### Prompt 2: Trace data flow
```
"Trace data flow của TOP 5 CPU diff trong Plan_convert_SQL:

Yêu cầu:
1. Đọc SKILL.md Section 4.3 "CPU Diff Calculation Flow"
2. Bắt đầu từ Excel output → trace ngược về source
3. Giải thích:
   - Data ở đâu đến?
   - Đi qua transformations nào?
   - Cách match processes giữa DUT và REF?
   - Cách tính diff?"
```

---

### Prompt 3: Hiểu architecture mới
```
"Giải thích architecture của Plan_convert_SQL:

Yêu cầu:
1. Đọc SKILL.md Section 2 "ARCHITECTURE"
2. Chạy analyze_complexity.py trên toàn bộ project
3. Giải thích:
   - Cấu trúc thư mục và vai trò từng file
   - Data flow từ trace file → Excel/JSON
   - Multiprocessing được áp dụng ở đâu
   - Cache system hoạt động như thế nào
   - Các format data chính"
```

---

### Prompt 4: Hiểu feature cụ thể
```
"Giải thích feature Precomputed_Extend_Data trong Plan_convert_SQL:

Yêu cầu:
1. Đọc SKILL.md Section 7.2 "Optimization Examples"
2. Tìm trong execution_sql.py nơi parse dumpstate
3. Giải thích:
   - Precomputed_Extend_Data chứa gì?
   - Được parse ở đâu? (_process_single_trace_worker)
   - Được sử dụng ở đâu? (Excel, JSON export)
   - Lợi ích performance so với parse lại mỗi lần?
   - Có patterns tương tự trong examples/?"
```

---

## 💡 TIPS CHO CLINE

1. **Luôn tham khảo SKILL.md trước** - Documentation đầy đủ, tiết kiệm thời gian
2. **Chạy scripts đầu tiên** - analyze_complexity.py → có overview nhanh
3. **Dùng grep_search nhiều** - Tìm references, understand context
4. **Đọc examples/** - Real-world cases, dễ hiểu hơn lý thuyết
5. **Xem data structures** - SKILL.md Section 2.1 là key
6. **Trace from both ends** - Input → output và output → input
7. **Dùng find_redundancy.py** - Hiểu data flow, dependencies
8. **Tóm tắt bằng flowchart text** - Dễ hiểu hơn mô tả dài

---

## 📚 TÀI LIỆU THAM KHẢO

### Từ Skill System:
- `.cline/skills/plan-convert-sql/SKILL.md` - Documentation chính
- `.cline/skills/plan-convert-sql/examples/refactor_io_redundancy.md` - Pre-compute pattern
- `.cline/skills/plan-convert-sql/examples/data_flow_patterns.md` - Data pipeline patterns

### Từ Scripts:
- Scripts README: `.cline/skills/plan-convert-sql/scripts/README.md`

### Từ Templates:
- `.cline/skills/plan-convert-sql/resources/code_review_template.md`
- `.cline/skills/plan-convert-sql/resources/refactor_checklist.md`

---

**Workflow này kết hợp toàn bộ khả năng của skill system để giúp Cline đọc và hiểu code Plan_convert_SQL hiệu quả nhất.**