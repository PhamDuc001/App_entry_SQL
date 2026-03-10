# Workflow: Debug Issues (Plan_convert_SQL)

---

## 📋 Mục đích

Workflow này hướng dẫn Cline cách debug issues trong Plan_convert_SQL hiệu quả, tận dụng skill system, analysis scripts, và debug tools.

---

## 🎤 Khi nào sử dụng

- User gặp lỗi khi chạy Plan_convert_SQL
- User báo cáo bug/issue cụ thể
- Function không hoạt động như mong đợi
- Data bị thiếu hoặc sai trong output
- Performance issue (quá chậm, memory leak)
- Exception/traceback xuất hiện

---

## 🛠️ CÔNG CỤ SỬ DỤNG

### Từ Skill System:
- `.cline/skills/plan-convert-sql/SKILL.md` - Section 8 "Error Handling & Debugging"
- `.cline/skills/plan-convert-sql/examples/` - Real-world debug cases

### Từ Scripts:
- `analyze_complexity.py` - Tìm functions phức tạp (có thể gây bug)
- `find_redundancy.py` - Tìm I/O trong loops (performance issues)
- `check_imports.py` - Tìm circular imports, missing imports

### Từ Cline:
- `grep_search` - Tìm error message, exception types
- `search_files` - Tìm patterns trong code
- `read_file` - Đọc code tại vị trí lỗi
- `list_code_definition_names` - Xem structure

---

## 🔄 QUY TRÌNH CHUẨN

### Phase 1: Thu thập thông tin (Information Gathering)

```
1. Xác định symptom:
   - Lỗi gì? (Exception, wrong output, crash, hang)
   - Ở đâu? (Function, line, module)
   - Khi nào? (Bắt đầu, giữa, cuối process)
   - Context? (Input data, environment)

2. Thu thập evidence:
   - Error message/traceback (nếu có)
   - Input data causing issue
   - Expected output vs actual output
   - Environment info (Python version, dependencies)
```

---

### Phase 2: Locate bug (Localization)

```
3. Search error patterns:
   - Use: grep_search(error_message)
   - Use: search_files(directory, "raise|except", "*.py")
   - Tìm nơi exception được raise/handle

4. Đọc code tại vị trí lỗi:
   - Use: read_file(file_path, start_line, end_line)
   - Tập trung vào:
     * Exception handling
     * Variable scope
     * Data types
     * Edge cases

5. Run analysis scripts:
   python analyze_complexity.py <file_with_bug>
   python find_redundancy.py <file_with_bug>
   python check_imports.py <file_with_bug>
```

---

### Phase 3: Hypothesize & Test

```
6. Tạo hypothesis:
   - Nguyên nhân gốc là gì?
   - Có multiple hypotheses không?
   - Prioritize theo likelihood

7. Design tests:
   - Test unit: Tách function ra khỏi context
   - Test with real data: Input gây lỗi
   - Test edge cases: None, empty, 0, negative values

8. Validate hypothesis:
   - Confirm/và bác bỏ từng hypothesis
   - Thiếu evidence → chạy thêm scripts/debug
```

---

### Phase 4: Fix & Validate

```
9. Implement fix:
   - Refer to SKILL.md Section 8.3 "Debug Tools"
   - Đề xuất fixes với risk assessment
   - Use code_review_template.md để review

10. Test fix:
    - Unit test với original failing case
    - Test với edge cases
    - Test không break existing functionality

11. Document:
    - Lý do bug xảy ra
    - Cách fix
    - Lessons learned
```

---

## 📐 CÁC SCENARIO KHÁC NHAU

### Scenario 1: Exception/Traceback rõ ràng

**User request:**
"Got error: 'KeyError: Priority_Data not found in cycle_data'
in execution_sql.py line ~2480"

**Cline workflow:**
```bash
# Step 1: Search error location
grep_search("Priority_Data")
grep_search("KeyError")

# Step 2: Read code at error location
read_file(execution_sql.py, 2470, 2490)

# Step 3: Analyze issue
- Line 2480: cycle_data.get("Priority_Data", {})
- Nhưng code đang dùng direct access: cycle_data["Priority_Data"]
- Issue: Missing .get() safe access

# Step 4: Check SKILL.md
- Section 8.1 "Common Error Scenarios"
- Example 3: Missing data in dict

# Step 5: Check other places
grep_search('cycle_data\["Priority_Data"\]')
grep_search('cycle_data.get("Priority_Data")')

# Step 6: Propose fix
# Thay thế: cycle_data["Priority_Data"]
# Bằng: cycle_data.get("Priority_Data", {})

# Step 7: Validate
# Check các trường hợp khác có cùng pattern không
```

---

### Scenario 2: Output bị thiếu data

**User request:**
"JSON output thiếu section priority_by_cycle, các section khác có data"

**Cline workflow:**
```bash
# Step 1: Check SKILL.md
- Section 4.4 "JSON Export Flow"
- Section 3.1 "calculate_metrics_for_app"

# Step 2: Search priority code
grep_search("priority_by_cycle")
grep_search("Priority_Data")

# Step 3: Read calculate_metrics_for_app
read_file(execution_sql.py, 2300, 2550)
# Tìm section "# 4. PRIORITY STATICS"

# Step 4: Analyze logic:
- Input: cycle.get("Priority_Data", {})
- Nếu empty → priority_cycles_data = []
- Check: analyze_trace() có collect Priority_Data không?

# Step 5: Check sql_query.py
grep_search("Priority" sql_query.py
# Tìm function get_priority_stats()

# Step 6: Run analyze_complexity.py
python analyze_complexity.py execution_sql.py
# Xem get_priority_stats CC, lines

# Step 7: Hypotheses:
H1: analyze_trace() không collect Priority_Data
H2: Priority_Data bị filter/skip
H3: Bug trong calculation logic

# Step 8: Test hypotheses:
- Print Priority_Data trong worker
- Check analyze_trace() implementation
- Xem trace data có info priority không

# Step 9: Fix based on root cause
```

---

### Scenario 3: Cache không hoạt động

**User request:**
"Cache system không load được dù file .perf_cache.pkl tồn tại, luôn re-process"

**Cline workflow:**
```bash
# Step 1: Check SKILL.md
- Section 4.2 "Cache System Flow" (chi tiết)
- Section 3.1 → get_or_process_folder_with_cache()

# Step 2: Read cache function
read_file(execution_sql.py, 1920, 2050)

# Step 3: Trace logic cache validation:
1. Check .perf_cache.pkl exists?
2. Check cache version == CACHE_VERSION?
3. Check target_apps match?

# Step 4: Find print statements
grep_search("Found valid cache")
grep_search("Cache version mismatch")

# Step 5: Hypotheses:
H1: Cache file exists nhưng corrupt
H2: CACHE_VERSION khác với trong file
H3: Print statement bị skip vì condition

# Step 6: Debug steps:
- Add debug print: print(f"Cache exists: {os.path.exists(cache_path)}")
- Add debug print: print(f"Cache content: {cache_content.get('version')}")
- Check pickle load success/failure

# Step 7: Validate fix
- Test với cache file tồn tại
- Verify "Found valid cache" xuất hiện
- Verify data được load (không re-process)
```

---

### Scenario 4: Performance issue (quá chậm)

**User request:**
"Process 10 apps mất 10 phút, quá chậm, cần tối ưu"

**Cline workflow:**
```bash
# Step 1: Run find_redundancy.py
python find_redundancy.py execution_sql.py

# Step 2: Check I/O in loops (PERFORMANCE HOTSPOT):
# Output: I/O OPERATIONS INSIDE LOOPS
# - find_dumpstate_content() called in loop
# - get_memory_data_for_cycle() called in loop

# Step 3: Check SKILL.md
- Section 7.2 "Optimization Examples"
- Section 7.1 "Bottleneck Identification"

# Step 4: Analyze code:
read_file(execution_sql.py, 440, 470)  # worker function

# Step 5: Check if already optimized:
grep_search("Precomputed_Extend_Data")

# Step 6: Hypotheses:
H1: Dumpstate đang được parse nhiều lần (nên đã optimize với Precomputed)
H2: I/O khác trong loop chưa optimize
H3: Num_workers quá ít

# Step 7: Validate:
- Check dumpstate parse count (1x = đã optimize, >1x = bug)
- Check num_workers default value
- Check các I/O calls khác trong loop

# Step 8: Propose optimizations:
- Nếu dumpstate parse >1x → Fix bug (đã có Precomputed nhưng không dùng)
- Nếu num_workers thấp → Tăng default
- Nếu có I/O khác → Apply pre-compute pattern
```

---

### Scenario 5: Multiprocessing hang/crash

**User request:**
"Process_all_traces bị hang, không exit, CPU usage thấp"

**Cline workflow:**
```bash
# Step 1: Check SKILL.md
- Section 4.1 "Trace Processing Flow" → multiprocessing

# Step 2: Read process_all_traces
read_file(execution_sql.py, 416, 520)

# Step 3: Check exception handling:
grep_search("except Exception" execution_sql.py

# Step 4: Analyze pool setup:
pool = Pool(processes=num_workers)
try:
    for i, (app_name, occurrence, category, metrics, filename) in enumerate(pool.imap(...)):
        ...
finally:
    pool.close()
    pool.join()

# Step 5: Check worker function:
read_file(execution_sql.py, 430, 460)  # _process_single_trace_worker

# Step 6: Hypotheses:
H1: Worker exception quá rộng (catch Exception)
H2: Deadlock trong pool
H3: File I/O blocking worker

# Step 7: Check exception handling in worker:
except Exception as e:  # ← CRITICAL: Catch quá rộng
    print(f"    [ERROR] {Path(file_path).name}: {e}")
    return (app_name, occurrence, 'entry' if occurrence % 2 == 1 else 'reentry', None, filename)

# Step 8: Impact analysis:
- Catch Exception → Catch KeyboardInterrupt (Ctrl+C không hoạt động)
- User không thể stop process
- Không có traceback → khó debug

# Step 9: Propose fix:
- Catch specific exceptions: (FileNotFoundError, ValueError, KeyError, IOError)
- Log traceback cho unhandled exceptions
```

---

### Scenario 6: Wrong cycle data alignment

**User request:**
"Excel columns bị lệch, cycle data không khớp với DUT/REF labels"

**Cline workflow:**
```bash
# Step 1: Check SKILL.md
- Section 4.1 → Cycle index calculation
- Section 3.1 → process_all_traces FIX 1, FIX 2

# Step 2: Search cycle calculation
grep_search("cycle_index")
grep_search("occurrence // 2")

# Step 3: Read process_all_traces
read_file(execution_sql.py, 494, 510)

# Step 4: Analyze cycle calculation:
cycle_index = (occurrence - 1) // 2
# Trace 1,2 → Cycle 0
# Trace 3,4 → Cycle 1

# Step 5: Check list extension:
while len(target_list) <= cycle_index:
    target_list.append(None)

# Step 6: Check FIX comments:
# [FIX 1] Luôn tính cycle_index, kể cả khi metrics=None
# [FIX 2] KHÔNG lọc bỏ None, giữ nguyên cấu trúc

# Step 7: Check if fix applied:
grep_search("FIX 1\|FIX 2")

# Step 8: Validate:
- Kiểm tra logic cycle_index
- Kiểm tra list extension
- Kiểm tra None values được giữ nguyên

# Step 9: Hypotheses:
H1: Logic cycle_index đúng, nhưng apply sai chỗ
H2: List extension không đúng
H3: None bị lọc bỏ sau khi FIX 2

# Step 10: Test with data:
- Tạo test case: 4 traces, 2 None ở cycle 0
- Verify Excel columns đúng
```

---

## 🔑 CÔNG CỤ DEBUG KHÁC NHAU

### 1. Print Debugging

```python
# Add debug prints:
print(f"[DEBUG] app_name={app_name}, occurrence={occurrence}")
print(f"[DEBUG] cycle_index={cycle_index}, metrics_keys={metrics.keys() if metrics else 'None'}")
print(f"[DEBUG] target_list_length={len(target_list)}, cycle_index={cycle_index}")
```

---

### 2. Check Data Types

```python
# Verify data types:
print(f"[DEBUG] type(cycle)={type(cycle)}, isinstance(cycle, dict)={isinstance(cycle, dict)}")
print(f"[DEBUG] priority_data={cycle.get('Priority_Data', 'MISSING')}")
```

---

### 3. Trace Execution Flow

```python
# Add markers to trace:
print(f"[DEBUG] Entering _process_single_trace_worker")
# ... code ...
print(f"[DEBUG] Before Perfetto query")
# ... code ...
print(f"[DEBUG] After Perfetto query, metrics_keys={metrics.keys()}")
```

---

### 4. Validate Assumptions

```python
# Validate assumptions:
assert isinstance(cycle, dict), f"Expected dict, got {type(cycle)}"
assert "Priority_Data" in cycle or cycle is None, f"Missing Priority_Data in cycle {cycle.keys()}"
```

---

### 5. Run Scripts Before Debug

```bash
# Always run scripts first:
python analyze_complexity.py execution_sql.py
python find_redundancy.py execution_sql.py
python check_imports.py execution_sql.py
```

---

## ⚠️ CÁC BUG PHỔ BIẾN TRONG PLAN_CONVERT_SQL

### Bug 1: Missing safe dict access

**Symptom:** KeyError exception

**Common locations:**
- `cycle_data["Priority_Data"]` → Should be `cycle_data.get("Priority_Data", {})`
- `cycle["CPU_Process_Data"]` → Should be `cycle.get("CPU_Process_Data", [])`

**Fix:** Use `.get()` with default value

---

### Bug 2: Exception quá rộng trong worker

**Symptom:** Không thể Ctrl+C stop, không có traceback

**Location:** `_process_single_trace_worker` line ~449

**Fix:**
```python
# Before:
except Exception as e:
    return (app_name, occurrence, 'entry' if occurrence % 2 == 1 else 'reentry', None, filename)

# After:
except (FileNotFoundError, ValueError, KeyError, IOError) as recoverable_error:
    return (app_name, occurrence, 'entry' if occurrence % 2 == 1 else 'reentry', None, filename)
except Exception as e:
    print(f"    [FATAL] {Path(file_path).name}: {type(e).__name__}: {e}")
    traceback.print_exc()
    return (app_name, occurrence, 'entry' if occurrence % 2 == 1 else 'reentry', None, filename)
```

---

### Bug 3: Cycle index miscalculation

**Symptom:** Excel columns lệch, data sai vị trí

**Root cause:** Không tính cycle_index khi metrics=None

**Fix:** Luôn tính cycle_index, extend list trước khi assign

---

### Bug 4: I/O trong loop (performance)

**Symptom:** Process quá chậm, CPU low, I/O high

**Common I/O in loops:**
- `find_dumpstate_content()` inside loop
- `get_memory_data_for_cycle()` inside loop
- `pickle.load/dump()` inside loop

**Fix:** Pre-compute outside loop (see `Precomputed_Extend_Data` pattern)

---

### Bug 5: Missing imports

**Symptom:** NameError, function không tìm thấy

**Check:** `check_imports.py`

**Fix:** Add missing imports, remove unused imports

---

## ✅ DEBUG CHECKLIST

### Information Gathering
- [ ] Thu thập error message/traceback
- [ ] Xác định symptom (lỗi, crash, sai output, chậm)
- [ ] Xác định context (input, environment, timing)
- [ ] Thu thập expected vs actual output

### Localization
- [ ] Grep_search error message
- [ ] Đọc code tại vị trí lỗi
- [ ] Run analyze_complexity.py để hiểu structure
- [ ] Run find_redundancy.py để tìm I/O loops

### Hypothesis
- [ ] Tạo hypotheses (có thể >1)
- [ ] Prioritize theo likelihood
- [ ] Design tests để validate từng hypothesis

### Investigation
- [ ] Tham khảo SKILL.md Section 8
- [ ] Check examples/ cho similar cases
- [ ] Run check_imports.py nếu cần
- [ ] Add debug prints nếu cần

### Fix
- [ ] Đề xuất fix với risk assessment
- [ ] Test fix với original failing case
- [ ] Test edge cases
- [ ] Test không break existing functionality

### Documentation
- [ ] Document root cause
- [ ] Document fix
- [ ] Update code_review_template.md
- [ ] Update memory_bank.md nếu cần

---

## 🎯 PROMPT EXAMPLES CHO USER

### Prompt 1: Exception rõ ràng
```
"Debug issue trong execution_sql.py:

Vấn đề:
Error: KeyError: 'Priority_Data' not found in cycle_data
Location: execution_sql.py, line ~2480, calculate_metrics_for_app function

Yêu cầu:
1. Grep_search 'Priority_Data' để tìm tất cả usages
2. Đọc code tại vị trí lỗi
3. Check SKILL.md Section 8.1 "Common Error Scenarios"
4. Tìm nguyên nhân: Tại sao Priority_Data missing?
5. Đề xuất fix: Sử dụng .get() với default value
6. Tìm các chỗ khác có cùng pattern cần fix
7. Sử dụng code_review_template.md để review fix"
```

---

### Prompt 2: Performance issue
```
"Debug performance issue trong Plan_convert_SQL:

Vấn đề:
Process 10 apps mất 10 phút (quá chậm)
CPU usage: ~20% (CPU không bottleneck)
I/O: High

Yêu cầu:
1. Run find_redundancy.py execution_sql.py
2. Tìm I/O operations inside loops (⚠️ Performance hotspot)
3. Check SKILL.md Section 7.2 "Optimization Examples"
4. Analyze: Có I/O nào chưa apply pre-compute pattern không?
5. Check Precomputed_Extend_Data pattern đã đúng chưa
6. Đề xuất optimizations với expected speedup
7. Sử dụng refactor_checklist.md để review plan"
```

---

### Prompt 3: Cache không hoạt động
```
"Debug cache system trong execution_sql.py:

Vấn đề:
File .perf_cache.pkl tồn tại trong folder
Nhưng process vẫn re-processing (không load cache)
Print 'Found valid cache file' KHÔNG xuất hiện

Yêu cầu:
1. Đọc SKILL.md Section 4.2 "Cache System Flow"
2. Đọc get_or_process_folder_with_cache function (~line 1920)
3. Trace logic cache validation:
   - Check file exists?
   - Check version match?
   - Check target_apps match?
4. Add debug prints để trace:
   - File path
   - Cache content (version, target_apps)
   - Current targets
5. Tìm nguyên nhân tại sao cache không load
6. Đề xuất fix
7. Test fix với real cache file"
```

---

### Prompt 4: Output thiếu data
```
"Debug JSON output thiếu data trong execution_sql.py:

Vấn đề:
File JSON 'calculator_dut.json' bị thiếu section 'priority_by_cycle'
Các section khác (sequence, extend, block_io_by_cycle) đều có data
Cache đang hoạt động bình thường

Yêu cầu:
1. Đọc SKILL.md Section 4.4 "JSON Export Flow"
2. Grep_search 'priority_by_cycle' để tìm code tạo section này
3. Đọc calculate_metrics_for_app function, section "# 4. PRIORITY STATICS"
4. Analyze logic:
   - Input: cycle.get("Priority_Data", {})
   - Calculation logic
   - Conditions để append vào result
5. Check sql_query.py: get_priority_stats() function
6. Tìm nguyên nhân:
   - Priority_Data không được collect?
   - Calculation logic có bug?
   - Conditions quá strict?
7. Thêm debug prints trong worker và export function
8. Đề xuất fix
9. Test với real trace data"
```

---

### Prompt 5: Multiprocessing hang
```
"Debug multiprocessing hang trong Plan_convert_SQL:

Vấn đề:
process_all_traces bị hang, không exit
Process stuck, không output logs
CPU usage: Low (~5%)
Memory usage: Stable

Yêu cầu:
1. Đọc SKILL.md Section 4.1 "Trace Processing Flow"
2. Đọc process_all_traces function (~line 416)
3. Đọc _process_single_trace_worker function (~line 430)
4. Check exception handling in worker:
   - Exception type được catch?
   - Có log traceback không?
   - Có catch KeyboardInterrupt không?
5. Check pool setup:
   - Pool(processes=num_workers)
   - try/finally blocks
   - pool.close(), pool.join()
6. Grep_search "except Exception"
7. Đề xuất fix với risk assessment:
   - Specific exceptions
   - Traceback logging
   - Ctrl+C handling
8. Sử dụng code_review_template.md để review"
```

---

## 💡 TIPS CHO CLINE

1. **Luôn chạy scripts đầu tiên** - analyze_complexity.py, find_redundancy.py, check_imports.py
2. **Grep_search nhiều** - Tìm error message, exception types, function names
3. **Tham khảo SKILL.md Section 8** - Error handling patterns, debug workflow
4. **Check examples/** - Real-world debug cases, có thể có similar issue
5. **Tạo nhiều hypotheses** - Đừng chỉ có 1 hypothesis, test từng cái
6. **Add debug prints** - Khi cần trace execution flow
7. **Sử dụng code_review_template.md** - Khi đề xuất fix
8. **Document root cause** - Để tránh bug lặp lại

---

## 📚 TÀI LIỆU THAM KHẢO

### Từ Skill System:
- `.cline/skills/plan-convert-sql/SKILL.md` - Section 8 "Error Handling & Debugging"
- `.cline/skills/plan-convert-sql/examples/refactor_io_redundancy.md` - Debug cases
- `.cline/skills/plan-convert-sql/examples/data_flow_patterns.md` - Debug patterns

### Từ Scripts:
- Scripts README: `.cline/skills/plan-convert-sql/scripts/README.md`

### Từ Templates:
- `.cline/skills/plan-convert-sql/resources/code_review_template.md`
- `.cline/skills/plan-convert-sql/resources/refactor_checklist.md`

---

## 🔗 LINK TỚI WORKFLOWS KHÁC

- `read-understand-code.md` - Đọc code trước khi debug
- `refactor-code.md` - Sau khi debug, refactor nếu cần
- `implement-feature.md` - Debug feature mới đang implement

---

**Workflow này kết hợp toàn bộ khả năng của skill system để giúp Cline debug issues Plan_convert_SQL hiệu quả nhất.**