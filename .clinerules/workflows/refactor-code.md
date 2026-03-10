# Workflow: Refactor Code (Plan_convert_SQL)

---

## 📋 Mục đích

Workflow này hướng dẫn Cline cách refactor code trong Plan_convert_SQL hiệu quả, tận dụng skill system, analysis scripts, và refactor templates.

---

## 🎤 Khi nào sử dụng

- User muốn refactor function dài/complex
- User muốn improve code quality (readability, maintainability)
- User muốn optimize performance
- User muốn fix code smells
- User muốn apply design patterns
- Sau khi debug issue, refactor để tránh lặp lại

---

## 🛠️ CÔNG CỤ SỬ DỤNG

### Từ Skill System:
- `.cline/skills/plan-convert-sql/SKILL.md` - Section 6 "Refactoring Patterns"
- `.cline/skills/plan-convert-sql/examples/refactor_io_redundancy.md` - Real-world refactor cases
- `.cline/skills/plan-convert-sql/examples/data_flow_patterns.md` - Data pipeline patterns

### Từ Scripts:
- `analyze_complexity.py` - Tìm functions cần refactor (dài, CC cao)
- `find_redundancy.py` - Tìm code lặp, I/O loops cần refactor
- `check_imports.py` - Tìm unused imports cần cleanup

### Từ Templates:
- `.cline/skills/plan-convert-sql/resources/code_review_template.md` - Review trước refactor
- `.cline/skills/plan-convert-sql/resources/refactor_checklist.md` - Checklist refactor

### Từ Cline:
- `read_file` - Đọc code
- `replace_in_file` - Apply refactor
- `grep_search` - Tìm usages để kiểm tra impact

---

## 🔄 QUY TRÌNH CHUẨN

### Phase 1: Identify refactor targets

```
1. Run analysis scripts:
   python analyze_complexity.py execution_sql.py
   python find_redundancy.py execution_sql.py
   python check_imports.py execution_sql.py

2. Identify refactor needs:
   - Functions quá dài (>50, >100 lines)
   - Functions CC cao (>10, >15)
   - Nesting quá sâu (>5)
   - I/O trong loops
   - Duplicate code
   - Unused imports
   - Code smells
```

---

### Phase 2: Review & Plan

```
3. Review code cần refactor:
   - Đọc function definition
   - Hiểu logic, data flow
   - Xem edge cases được xử lý

4. Plan refactor:
   - Tách function con (helper functions)
   - Extract constants/magic numbers
   - Simplify logic
   - Apply patterns từ SKILL.md Section 6

5. Assess risks:
   - Có breaking changes không?
   - Có impact downstream consumers không?
   - Có cần backward compatibility không?

6. Use code_review_template.md:
   - Document current issues
   - Document proposed changes
   - Assess risks & mitigations
```

---

### Phase 3: Implement refactor

```
7. Apply refactor step-by-step:
   - Thêm helper functions
   - Simplify main function
   - Update calls

8. Tại mỗi step:
   - Verify không break logic
   - Verify không break edge cases
   - Run tests nếu có

9. Final verification:
   - Verify output giống nhau (before vs after)
   - Verify performance không giảm
   - Verify code readability improve
```

---

### Phase 4: Document & Validate

```
10. Update documentation:
    - Update docstrings
    - Update comments
    - Update memory_bank.md nếu cần

11. Create test plan:
    - Test original failing case
    - Test edge cases
    - Test performance

12. Sign-off:
    - Sử dụng refactor_checklist.md
    - Review checklist items
    - Approved nếu pass
```

---

## 📐 CÁC REFACTOR PATTERNS PHỔ BIẾN

### Pattern 1: Pre-compute Pattern (Performance)

**Mục đích:** Parse I/O data 1 lần, tránh parse lại trong loops

**When dùng:**
- I/O operations được gọi nhiều lần trong loop
- Data từ I/O được dùng nhiều lần

**Steps:**
1. Parse data 1 lần ở đầu loop/function
2. Lưu vào dict (precomputed_data)
3. Gắn precomputed_data vào main data structure
4. Consumer chỉ đọc từ precomputed_data

**Example:**
```python
# BEFORE (parse 4x mỗi cycle):
for cycle in cycles:
    pss = parse_pss_for_app(dumpstate_content, app_name)
    pageboost = parse_pageboostd_for_app(dumpstate_content, app_name)
    uptime = parse_uptime(dumpstate_content)
    ...

# AFTER (parse 1x):
extend_data = {
    'App_PSS': parse_pss_for_app(dumpstate_content, app_name),
    'Pageboostd': parse_pageboostd_for_app(dumpstate_content, app_name),
    'Uptime': parse_uptime(dumpstate_content),
    ...
}
metrics['Precomputed_Extend_Data'] = extend_data

# Consumer (just read):
precomp = cycle.get('Precomputed_Extend_Data', {})
pss = precomp.get('App_PSS', 0.0)
```

**Reference:** SKILL.md Section 7.2, examples/refactor_io_redundancy.md

---

### Pattern 2: Extract Helper Functions (Readability)

**Mục đích:** Tách function dài thành các helper functions nhỏ, focused

**When dùng:**
- Function >100 lines
- CC >10
- Multiple responsibilities

**Steps:**
1. Đọc function, identify logical sections
2. Extract từng section thành helper function
3. Helper function nhận rõ parameters, trả về rõ output
4. Main function chỉ orchestrate calls

**Example:**
```python
# BEFORE (1200 lines):
def create_sheet(...):
    # 1200 lines of Excel writing code
    # Mix of sequence, memory, CPU, priority, I/O tables...

# AFTER:
def write_sequence_table(ws, row_idx, dut_cycles, ref_cycles, max_cycles, fmts):
    # ~150 lines for sequence metrics
    return row_idx

def write_memory_section(ws, row_idx, dut_cycles, ref_cycles, max_cycles, fmts):
    # ~100 lines for memory section
    return row_idx

def create_sheet(...):
    row_idx = 2
    row_idx = write_sequence_table(ws, row_idx, ...)
    row_idx = write_memory_section(ws, row_idx, ...)
    # ... orchestrate calls
```

**Reference:** SKILL.md Section 6.1

---

### Pattern 3: Backward-Compatible Extension (Compatibility)

**Mục đích:** Thêm mới vào data structure mà không break existing code

**When dùng:**
- Thêm field mới vào dict/list
- Extend data format

**Steps:**
1. Add new field vào data structure
2. Existing code dùng .get() với default → không crash
3. New code có thể dùng field mới

**Example:**
```python
# Add new field backward-compatible:
result['existing_key'] = existing_value
result['new_key'] = new_value

# Old code (không break):
val = result.get('existing_key', default_value)

# New code (sử dụng field mới):
val = result.get('new_key', default_value)
```

**Reference:** SKILL.md Section 6.3

---

### Pattern 4: Extract Constants (Magic Numbers)

**Mục đích:** Replace magic numbers với named constants

**When dùng:**
- Magic numbers xuất hiện nhiều lần
- Numbers không rõ nghĩa

**Example:**
```python
# BEFORE:
top_5 = sorted(results, key=lambda x: x['diff'], reverse=True)[:5]

# AFTER:
TOP_N = 5  # Configurable constant
top_N = sorted(results, key=lambda x: x['diff'], reverse=True)[:TOP_N]
```

---

## ✅ REFACTOR CHECKLIST (từ refactor_checklist.md)

### Planning
- [ ] Đã đọc và hiểu toàn bộ function
- [ ] Đã xác định bugs và issues
- [ ] Đã đánh giá rủi ro của từng thay đổi
- [ ] Đã đề xuất mitigation strategies

### Code Quality
- [ ] Logic đúng với yêu cầu
- [ ] Edge cases được xử lý (None, empty, 0)
- [ ] Variable scope đúng
- [ ] Type đúng

### Performance
- [ ] Không có I/O trong vòng lặp thừa
- [ ] Không tạo object/list lặp lại
- [ ] Algorithm complexity hợp lý

### Safety
- [ ] Error handling đầy đủ
- [ ] Backward compatible
- [ ] Không ghi đè data volatile

### Testing
- [ ] Test plan rõ ràng
- [ ] Test với real data
- [ ] Test edge cases
- [ ] Verify không break existing functionality

---

## 🎯 PROMPT EXAMPLES CHO USER

### Prompt 1: Refactor function dài
```
"Refactor create_sheet function trong execution_sql.py:

Yêu cầu:
1. Run analyze_complexity.py execution_sql.py
2. Đọc SKILL.md Section 6.1 "Extract Helper Functions"
3. Đọc create_sheet function (~line 700-1900)
4. Tách thành helper functions:
   - write_sequence_table()
   - write_memory_section()
   - write_abnormal_section()
   - write_top_cpu_tables()
   - write_priority_table()
   - write_block_io_table()
5. Use code_review_template.md để review plan
6. Implement refactor step-by-step
7. Test với real data, verify Excel output giống nhau
8. Use refactor_checklist.md để sign-off"
```

---

### Prompt 2: Refactor I/O redundancy
```
"Refactor để loại bỏ I/O redundancy trong Plan_convert_SQL:

Yêu cầu:
1. Run find_redundancy.py execution_sql.py
2. Tìm I/O operations inside loops
3. Đọc SKILL.md Section 7.2 "Optimization Examples"
4. Đọc examples/refactor_io_redundancy.md (case study)
5. Apply Pre-compute pattern:
   - Parse dumpstate CHỈ 1 LẦN ở đầu worker
   - Lưu vào Precomputed_Extend_Data
   - Consumer chỉ đọc, không parse lại
6. Use code_review_template.md để review
7. Implement refactor
8. Test với real data, verify output giống nhau
9. Measure speedup (before vs after)"
```

---

### Prompt 3: Clean up code
```
"Clean up code trong execution_sql.py:

Yêu cầu:
1. Run check_imports.py execution_sql.py
2. Tìm unused imports → xóa
3. Tìm unused global variables → xóa
4. Run find_redundancy.py execution_sql.py
5. Tìm commented-out code → xóa
6. Tìm duplicate code → refactor
7. Run analyze_complexity.py execution_sql.py
8. Tìm functions >50 lines → cân nhắc refactor
9. Use refactor_checklist.md để review
10. Apply cleanups step-by-step
11. Test với real data sau mỗi cleanup"
```

---

## 💡 TIPS CHO CLINE

1. **Luôn chạy scripts trước** - analyze_complexity.py, find_redundancy.py, check_imports.py
2. **Tham khảo SKILL.md Section 6** - Refactoring patterns, common scenarios
3. **Đọc examples/** - Real-world refactor cases, học từ đã implement
4. **Dùng code_review_template.md** - Review trước refactor, assess risks
5. **Dùng refactor_checklist.md** - Sign-off checklist
6. **Tách thành các steps nhỏ** - Implement từng step, test sau mỗi step
7. **Test với real data** - Verify output giống nhau before vs after
8. **Document changes** - Update docstrings, comments, memory_bank.md

---

## 📚 TÀI LIỆU THAM KHẢO

### Từ Skill System:
- `.cline/skills/plan-convert-sql/SKILL.md` - Section 6 "Refactoring Patterns"
- `.cline/skills/plan-convert-sql/examples/refactor_io_redundancy.md` - Pre-compute pattern
- `.cline/skills/plan-convert-sql/examples/data_flow_patterns.md` - Data pipeline patterns

### Từ Scripts:
- Scripts README: `.cline/skills/plan-convert-sql/scripts/README.md`

### Từ Templates:
- `.cline/skills/plan-convert-sql/resources/code_review_template.md`
- `.cline/skills/plan-convert-sql/resources/refactor_checklist.md`

---

## 🔗 LINK TỚI WORKFLOWS KHÁC

- `read-understand-code.md` - Đọc hiểu code trước khi refactor
- `debug-issue.md` - Debug trước khi refactor để tránh lặp lại bug
- `implement-feature.md` - Implement feature với refactor mindset từ đầu

---

**Workflow này kết hợp toàn bộ khả năng của skill system để giúp Cline refactor Plan_convert_SQL hiệu quả nhất.**