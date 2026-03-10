# Workflow: Implement New Feature (Plan_convert_SQL)

---

## 📋 Mục đích

Workflow này hướng dẫn Cline cách implement new feature trong Plan_convert_SQL hiệu quả, tận dụng skill system, analysis scripts, và development patterns.

---

## 🎤 Khi nào sử dụng

- User muốn add metric mới vào Excel/JSON output
- User muốn add section mới vào report
- User muốn modify existing feature logic
- User muốn implement performance optimization
- User muốn add data analysis capability
- User muốn extend functionality

---

## 🛠️ CÔNG CỤ SỬ DỤNG

### Từ Skill System:
- `.cline/skills/plan-convert-sql/SKILL.md` - Section 9 "Feature Development"
- `.cline/skills/plan-convert-sql/examples/` - Real-world implementation examples
- `.cline/skills/plan-convert-sql/resources/` - Templates

### Từ Scripts:
- `analyze_complexity.py` - Phân tích complexity sau implement
- `find_redundancy.py` - Tìm I/O redundancy cần tránh
- `check_imports.py` - Kiểm tra imports cần thêm

### Từ Templates:
- `.cline/skills/plan-convert-sql/resources/code_review_template.md` - Review feature

### Từ Cline:
- `read_file` - Đọc code tương tự đã có
- `replace_in_file` - Implement feature
- `grep_search` - Tìm patterns để follow

---

## 🔄 QUY TRÌNH CHUẨN

### Phase 1: Understand Requirements

```
1. Xác định requirements:
   - Feature làm gì?
   - Input data từ đâu?
   - Output format mong muốn?
   - Excel hay JSON hoặc cả hai?

2. Tham khảo existing patterns:
   - Đọc SKILL.md Section 9 "Feature Development"
   - Tìm feature tương tự đã implement
   - Làm theo patterns đã có

3. Design data flow:
   - Data source → Processing → Output
   - Tích hợp vào existing workflows
```

---

### Phase 2: Design & Plan

```
4. Plan implementation:
   - Thêm Perfetto SQL query? (sql_query.py)
   - Add metric vào metrics dict? (analyze_trace)
   - Add vào Excel output? (create_sheet)
   - Add vào JSON export? (export_avg_to_json)

5. Assess impact:
   - Breaking changes?
   - Backward compatible?
   - Performance impact?

6. Use code_review_template.md:
   - Document requirements
   - Document changes
   - Assess risks
```

---

### Phase 3: Implement

```
7. Implement step-by-step:
   - Step 1: Data collection (Perfetto query hoặc parse dumpstate)
   - Step 2: Data processing logic
   - Step 3: Excel output
   - Step 4: JSON output

8. Tại mỗi step:
   - Test với sample data
   - Verify format đúng
   - Verify không break existing code
```

---

### Phase 4: Test & Validate

```
9. Test với real trace data:
   - Test với DUT trace
   - Test với REF trace
   - Test với multiple cycles

10. Verification:
    - Excel output đúng format?
    - JSON output đúng format?
    - Data calculation đúng?
    - Không break existing metrics?

11. Documentation:
    - Update docstrings
    - Update comments
    - Update memory_bank.md nếu cần
```

---

## 📐 CÁC SCENARIO KHÁC NHAU

### Scenario 1: Add metric mới vào sequence table

**User request:**
"Add metric 'Jank Count' vào sequence table trong Excel report"

**Cline workflow:**
```bash
# Step 1: Check SKILL.md
- Section 9.1 "Adding New Metrics to JSON Export"
- Section 6.1 "Add new metric to sequence table" (example)

# Step 2: Check if Perfetto has data
grep_search "jank" sql_query.py

# Step 3: Design implementation:
1. Add SQL query in sql_query.py
2. Add metric to metrics dict in analyze_trace()
3. Add to sequence_metrics list
4. Add logic write vào Excel

# Step 4: Implement - SQL query (sql_query.py):
def get_jank_count(tp):
    """Get number of jank frames."""
    query = """
    SELECT value
    FROM trace_counter_counter
    WHERE name = 'jank_count'
    """
    result = tp.query(query)
    return result[0]['value'] if result else 0

# Step 5: Implement - Add to metrics (analyze_trace):
metrics['Jank Count'] = get_jank_count(tp)

# Step 6: Implement - Add to sequence list (calculate_metrics_for_app):
sequence_metrics = [
    "App Execution Time",
    ...
    "Jank Count"  # Add here
]

# Step 7: Implement - Write to Excel (create_sheet):
# Tự động viết vì đã trong sequence_metrics loop

# Step 8: Test:
- Verify Jank Count xuất hiện trong Excel
- Verify data đúng (không negative, hợp lý)
- Verify không break existing metrics

# Step 9: Use code_review_template.md
- Document: Added Jank Count metric
- Changes: sql_query.py, analyze_trace, calculate_metrics_for_app
- Risks: Rất thấp
```

---

### Scenario 2: Add section mới vào Excel

**User request:**
"Add new section 'Temperature' vào Excel report with CPU temp và Battery temp"

**Cline workflow:**
```bash
# Step 1: Check SKILL.md
- Section 9.2 "Modifying CPU Diff Logic" (patterns tương tự)
- Section 6.1 "Add new section to Excel report" (example)

# Step 2: Design section:
Section header: "TEMPERATURE"
Rows: CPU Temperature (°C), Battery Temperature (°C)
Format: Average value, Diff column

# Step 3: Parse dumpstate (dumpstate_parser.py):
def parse_temperature(dumpstate_content):
    """Parse CPU and Battery temperature."""
    temp_data = {'cpu_temp': None, 'battery_temp': None}
    
    for line in dumpstate_content.split('\n'):
        if 'CPU temp:' in line:
            temp_data['cpu_temp'] = float(line.split(':')[-1].strip())
        elif 'Battery temp:' in line:
            temp_data['battery_temp'] = float(line.split(':')[-1].strip())
    
    return temp_data

# Step 4: Add to Precomputed_Extend_Data (worker):
extend_data['Temperature'] = parse_temperature(dumpstate_content)

# Step 5: Add section to Excel (create_sheet):
row_idx += 3
ws.merge_range(row_idx, 0, row_idx, total_cols - 1, "TEMPERATURE", fmt_section_header)
row_idx += 1

temp_metrics = ["CPU Temperature (°C)", "Battery Temperature (°C)"]

for metric in temp_metrics:
    ws.write(row_idx, 0, metric, fmt_label)
    
    # Fill DUT data
    col_idx = 1
    dut_values = []
    for i in range(max_cycles):
        if i < len(dut_cycles) and dut_cycles[i]:
            precomp = dut_cycles[i].get('Precomputed_Extend_Data', {})
            temp = precomp.get('Temperature', {})
            val = temp.get('cpu_temp' if 'CPU' in metric else 'battery_temp', 0.0)
            write_value_or_empty(ws, row_idx, col_idx, val, fmt_section_value)
            if val > 0: dut_values.append(val)
        col_idx += 1
    
    # DUT Avg
    dut_avg = sum(dut_values) / len(dut_values) if dut_values else 0.0
    write_value_or_empty(ws, row_idx, col_idx, dut_avg, fmt_val)
    col_idx += 1
    
    # Fill REF data (similar pattern)
    ...
    
    # Diff
    if dut_avg > 0 and ref_avg > 0:
        diff = dut_avg - ref_avg
        # Format màu sắc cho temperature
        if 'CPU' in metric:
            # CPU: Lower is better
            fmt = fmt_diff_fast if diff > 5 else fmt_diff_slow if diff < -5 else fmt_diff_normal
        else:
            # Battery: Lower is better
            fmt = fmt_diff_fast if diff > 3 else fmt_diff_slow if diff < -3 else fmt_diff_normal
        write_value_or_empty(ws, row_idx, col_idx, diff, fmt)
    
    row_idx += 1

# Step 6: Test với real data
- Verify section xuất hiện
- Verify data parse đúng
- Verify Diff color logic đúng

# Step 7: Use code_review_template.md
```

---

### Scenario 3: Change TOP 5 to TOP 10 in CPU diff

**User request:**
"Change TOP 5 CPU processes to TOP 10 in both Excel and JSON output"

**Cline workflow:**
```bash
# Step 1: Check SKILL.md
- Section 4.3 "CPU Diff Calculation Flow"
- Section 3.1 → calculate_metrics_for_app() section 3

# Step 2: Search code
grep_search "TOP 5\|top_5\|:5\]"

# Step 3: Tìm locations cần thay đổi:
1. calculate_metrics_for_app() - JSON export (line ~2425)
2. create_sheet() - Excel output (line ~1000-1100)

# Step 4: Đọc code
read_file(execution_sql.py, 2425, 2470)  # JSON export

# Step 5: Implement - JSON export:
# BEFORE:
top_5 = sorted(matched_results, key=lambda x: x['diff'], reverse=True)[:5]
cpu_cycles_data.append({"cycle": idx + 1, "process": top_5})

# AFTER:
top_10 = sorted(matched_results, key=lambda x: x['diff'], reverse=True)[:10]
cpu_cycles_data.append({"cycle": idx + 1, "process": top_10})

# Step 6: Implement - Excel output:
# Tìm dòng "[:5]" và thay bằng "[:10]"
grep_search("\[:5\]" execution_sql.py

# Step 7: Replace (create_sheet):
# Line ~1100 (before):
top_proc = sorted(matched_results, key=lambda x: x['diff'], reverse=True)[:5]

# After:
top_proc = sorted(matched_results, key=lambda x: x['diff'], reverse=True)[:10]

# Step 8: Test:
- Run với real DUT/REF data
- Verify Excel có 10 processes (không phải 5)
- Verify JSON có 10 processes
- Verify diff calculation đúng

# Step 9: Use code_review_template.md
- Document: Changed TOP 5 → TOP 10
- Changes: 2 locations (calculate_metrics_for_app, create_sheet)
- Risks: Rất thấp
```

---

### Scenario 4: Add metric mới vào JSON extend section

**User request:**
"Add 'Memory Growth' metric vào JSON extend section:
- growth_mb = pss_activityIdle - pss_start_proc
- Tính average growth cho tất cả cycles"

**Cline workflow:**
```bash
# Step 1: Check SKILL.md
- Section 9.1 "Adding New Metrics to JSON Export"
- Section 3.1 → calculate_metrics_for_app() section 2.3 (Memory)

# Step 2: Đọc calculate_metrics_for_app
read_file(execution_sql.py, 2340, 2370)

# Step 3: Analyze current memory section:
# Đã có:
extend_data["memory"] = {
    "MemFree_MB": ...,
    "MemAvailable_MB": ...,
    "App_PSS_MB": ...,
    "Pageboostd_MB": ...
}

# Step 4: Design new metric:
- Cần PSS ở 2 timepoints: start_proc, activityIdle
- Perfetto có PSS theo thời gian không?
- Nếu không → dùng Precomputed_Extend_Data App_PSS

# Step 5: Implement:
# Trong section 2.3 "Extend Metrics" → "Memory — [REFACTORED] Đọc từ Precomputed_Extend_Data":
memory_data = {}
pss_growth_vals = []

for idx, cycle in valid_cycles_with_idx:
    precomp = cycle.get('Precomputed_Extend_Data', {})
    
    # Use App_PSS (single value, không có timepoint)
    # Workaround: Tính growth = PSS - average_previous_PSS
    # Hoặc: Growth = PSS - first_cycle_PSS
    
    pss = precomp.get('App_PSS', 0.0)
    if pss > 0: pss_vals.append(pss)

# Calculate growth relative to first cycle:
if len(pss_vals) > 1:
    first_pss = pss_vals[0]
    growths = [p - first_pss for p in pss_vals[1:]]
    if growths:
        memory_data["Memory_Growth_MB"] = round(sum(growths)/len(growths), 2)

# Add to extend_data:
if memory_data: extend_data["memory"] = memory_data

# Step 6: Test với real trace:
- Verify Memory_Growth_MB xuất hiện trong JSON
- Verify giá trị hợp lý (có thể negative, có thể positive)
- Verify tính toán đúng

# Step 7: Use code_review_template.md
```

---

### Scenario 5: Modify JSON format (priority_by_cycle)

**User request:**
"Change JSON format cho priority_by_cycle:
- Old format: dict {"120": 100.0}
- New format: list of objects [{"priority": 120, "percentage": 100.0}]
- Filter out percentage = 0.0"

**Cline workflow:**
```bash
# Step 1: Check SKILL.md
- Section 9.3 "Changing JSON Format"
- Section 3.1 → calculate_metrics_for_app() section 4

# Step 2: Đọc current implementation
read_file(execution_sql.py, 2480, 2510)

# Step 3: Analyze old format:
for prio_id, pct in prio_acc.items():
    percentage = round((pct/total_dur)*100, 2)
    if percentage > 0:
        prio_cycle_result[prio_id] = percentage  # Old: dict

# Step 4: Implement new format:
for prio_id, pct in prio_acc.items():
    percentage = round((pct/total_dur)*100, 2)
    if percentage > 0:
        prio_list.append({
            "priority": int(prio_id),
            "percentage": percentage
        })  # New: list of objects

if prio_list:
    prio_cycle_result[cat] = prio_list  # Store list instead of dict

# Step 5: Test:
- Export JSON
- Verify format: list of objects
- Verify percentage = 0.0 được filter
- Verify percentage sums ~100%

# Step 6: Check downstream consumers:
grep_search("priority_by_cycle"  # Tìm code đọc priority_by_cycle
# Có consumer nào phụ thuộc vào dict format không?

# Step 7: Use code_review_template.md
- Document: Format change dict → list
- Changes: calculate_metrics_for_app()
- Risks: Breaking change nếu consumers phụ thuộc format cũ
- Mitigations: Check consumers, có thể cần update
```

---

## ✅ FEATURE IMPLEMENTATION CHECKLIST

### Requirements
- [ ] Requirements rõ ràng, không ambiguous
- [ ] Input data source xác định
- [ ] Output format xác định
- [ ] Edge cases được xem xét

### Design
- [ ] Tham khảo existing patterns
- [ ] Data flow rõ ràng
- [ ] Integration vào existing workflows
- [ ] Breaking changes được đánh giá

### Implementation
- [ ] SQL query đúng (nếu có)
- [ ] Data processing logic đúng
- [ ] Excel output đúng format
- [ ] JSON output đúng format

### Testing
- [ ] Test với real trace data
- [ ] Test với multiple cycles
- [ ] Test edge cases
- [ ] Verify không break existing features

### Documentation
- [ ] Docstrings được update
- [ ] Comments được update
- [ ] SKILL.md được update (nếu feature mới quan trọng)
- [ ] memory_bank.md được update (nếu cần)

---

## 🎯 PROMPT EXAMPLES CHO USER

### Prompt 1: Add metric mới
```
"Add metric mới 'Frame Time Distribution' vào Plan_convert_SQL:

Requirements:
1. Collect frame time distribution từ trace events
2. Group vào buckets: <16ms, 16-33ms, 33-50ms, >50ms
3. Export vào JSON trong extend section:
   extend.frametime = {
     "fast_ms": 120.5,    # <16ms total
     "normal_ms": 45.2,   # 16-33ms total
     "slow_ms": 8.3,      # 33-50ms total
     "very_slow_ms": 2.1  # >50ms total
   }

Implementation:
1. Check SKILL.md Section 9.1 "Adding New Metrics"
2. Check sql_query.py xem có Perfetto counter nào về frame time không
3. Nếu không, cần custom SQL query
4. Add metric vào calculate_metrics_for_app() section 2 (extend)
5. Test với real trace data
6. Use code_review_template.md để review"
```

---

### Prompt 2: Modify CPU diff logic
```
"Modify CPU diff calculation trong Plan_convert_SQL:

Requirements:
1. Change từ TOP 5 → TOP 10 processes
2. Add 'dut_time' field vào output
3. Add 'ref_time' field vào output
4. Giữ existing 'diff' field

JSON format:
{
  "cycle": 1,
  "process": [
    {
      "name": "system_server",
      "dut_time": 150.5,
      "ref_time": 100.2,
      "diff": 50.3
    }
  ]
}

Implementation:
1. Đọc SKILL.md Section 4.3 "CPU Diff Calculation Flow"
2. Tìm code trong calculate_metrics_for_app() section 3
3. Uncomment dut_time và ref_time fields
4. Change [:5] → [:10]
5. Test với real DUT/REF data
6. Verify Excel và JSON output đều updated
7. Use code_review_template.md để review"
```

---

### Prompt 3: Add section mới
```
"Add new section 'Thread Activity' vào Excel report:

Requirements:
1. Section header: "THREAD ACTIVITY"
2. Hiển thị top 5 threads theo CPU time cho mỗi cycle
3. Format: Thread Name (Process) | DUT Time | REF Time | Diff
4. Hiển thị cho cả DUT và REF cycles
5. Diff màu sắc: >50ms = đỏ, <-50ms = xanh, khác = vàng

Implementation:
1. Check SKILL.md Section 6.1 "Add new section to Excel report"
2. Check SKILL.md Section 3.1 → analyze_trace() CPU_Thread_Data
3. Add section vào create_sheet() function (sau Process start table)
4. Use format tương tự Top Process CPU table
5. Test với real trace data
6. Verify section xuất hiện đúng vị trí
7. Verify data calculation đúng
8. Use code_review_template.md để review"
```

---

### Prompt 4: Modify JSON format
```
"Modify JSON format cho block_io_by_cycle trong Plan_convert_SQL:

Current format:
{
  "cycle": 1,
  "data": [
    {"name": "lib.so", "val": 150.5}
  ]
}

New requirements:
1. Change 'val' → 'duration_ms'
2. Add 'percentage' field: percentage của block io trong cycle này
3. Filter out percentage < 1%
4. Sort theo duration_ms descending

New format:
{
  "cycle": 1,
  "data": [
    {
      "name": "lib.so",
      "duration_ms": 150.5,
      "percentage": 15.2
    }
  ]
}

Implementation:
1. Đọc SKILL.md Section 9.3 "Changing JSON Format"
2. Tìm block_io_by_cycle calculation trong calculate_metrics_for_app()
3. Modify code:
   - Rename val → duration_ms
   - Calculate percentage = (duration / total_block_io) * 100
   - Filter percentage < 1
   - Sort descending
4. Test với real trace data
5. Verify format đúng
6. Verify percentage tính đúng
7. Check downstream consumers
8. Use code_review_template.md để review breaking changes"
```

---

### Prompt 5: Feature mới hoàn chỉnh
```
"Implement feature mới 'Energy Consumption Analysis' cho Plan_convert_SQL:

Requirements:
1. Collect energy data từ trace (uid_energy_counter events)
2. Calculate energy consumption per app launch
3. Group by energy consumers (CPU, GPU, Modem, Wifi, Bluetooth)
4. Export vào JSON:
   extend.energy = {
     "total_mah": 12.5,
     "cpu_mah": 8.2,
     "gpu_mah": 2.1,
     "modem_mah": 1.5,
     "wifi_mah": 0.5,
     "bluetooth_mah": 0.2
   }

5. Export vào Excel (mới section "ENERGY CONSUMPTION")

Implementation:
1. Đọc SKILL.md Section 9.1 "Adding New Metrics"
2. Check Perfetto uid_energy_counter events
3. Add SQL query in sql_query.py: get_energy_consumption()
4. Add metric to Precomputed_Extend_Data in worker
5. Add to calculate_metrics_for_app() extend section
6. Add new section to create_sheet()
7. Test với real trace data
8. Verify energy data có vẻ hợp lý
9. Use code_review_template.md để review
10. Update SKILL.md Section 9.1 với example này"
```

---

## 💡 TIPS CHO CLINE

1. **Luôn tham khảo existing patterns** - Đừng reinvent, follow đã có
2. **Đọc SKILL.md Section 9** - Feature development guidelines
3. **Grep_search nhiều** - Tìm patterns tương tự để follow
4. **Test từng step** - Đừng implement tất cả rồi mới test
5. **Dùng code_review_template.md** - Review trước implement
6. **Check downstream impact** - Đừng break existing consumers
7. **Document changes** - Update docstrings, comments
8. **Backward compatible** - Mặc định là phải,除非 user yêu cầu breaking change

---

## 📚 TÀI LIỆU THAM KHẢO

### Từ Skill System:
- `.cline/skills/plan-convert-sql/SKILL.md` - Section 9 "Feature Development"
- `.cline/skills/plan-convert-sql/examples/` - Real-world examples
- `.cline/skills/plan-convert-sql/examples/data_flow_patterns.md` - Data pipeline patterns

### Từ Scripts:
- Scripts README: `.cline/skills/plan-convert-sql/scripts/README.md`

### Từ Templates:
- `.cline/skills/plan-convert-sql/resources/code_review_template.md`

---

## 🔗 LINK TỚI WORKFLOWS KHÁC

- `read-understand-code.md` - Đọc hiểu code trước khi implement
- `debug-issue.md` - Debug sau implement nếu có bug
- `refactor-code.md` - Refactor sau implement nếu cần improve

---

**Workflow này kết hợp toàn bộ khả năng của skill system để giúp Cline implement features Plan_convert_SQL hiệu quả nhất.**