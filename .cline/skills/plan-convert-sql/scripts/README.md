# Scripts — Python Dev Kit

Các script phân tích code tự động, không cần cài thêm dependencies (chỉ dùng Python stdlib).

## Danh sách Scripts

### 1. `analyze_complexity.py`
**Phân tích complexity của file/directory Python.**

```bash
# Phân tích 1 file
python analyze_complexity.py execution_sql.py

# Phân tích toàn bộ project
python analyze_complexity.py D:\FE\Personal\Plan_convert_SQL
```

**Output bao gồm:**
- Tổng lines (code/blank/comment)
- Số functions, classes, imports
- Top functions theo Cyclomatic Complexity
- Warnings: function quá dài (>50 lines), CC cao (>10), nesting sâu (>5)

---

### 2. `find_redundancy.py`
**Tìm code patterns lặp lại, I/O trong vòng lặp.**

```bash
python find_redundancy.py execution_sql.py
```

**Phát hiện:**
- Duplicate function calls trong cùng scope
- I/O operations (file read/write, zip) inside loops ← **Performance hotspot**
- Similar code blocks (potential copy-paste)
- Most called functions (top 10)

---

### 3. `check_imports.py`
**Kiểm tra import thừa/thiếu, circular imports.**

```bash
# Kiểm tra 1 file
python check_imports.py execution_sql.py

# Kiểm tra toàn bộ project (phát hiện circular imports)
python check_imports.py D:\FE\Personal\Plan_convert_SQL
```

**Phát hiện:**
- Unused imports (import nhưng không dùng)
- Wildcard imports (`from module import *`)
- Circular import candidates (A imports B, B imports A)

---

## Cách Agent sử dụng

Agent có thể chạy scripts qua `run_command`:

```python
# Ví dụ: Phân tích trước khi refactor
run_command("python D:\\FE\\Personal\\Plan_convert_SQL\\Python_dev-kit\\scripts\\analyze_complexity.py <target_file>")

# Ví dụ: Tìm redundancy
run_command("python D:\\FE\\Personal\\Plan_convert_SQL\\Python_dev-kit\\scripts\\find_redundancy.py <target_file>")
```
