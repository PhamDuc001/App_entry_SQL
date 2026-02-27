# GitHub Actions Workflows cho Plan_convert_SQL

## Tổng Quan

Repository này có GitHub Actions workflows để tự động hóa các tác vụ:

- ✅ Format code Python
- ✅ Sort imports
- ✅ Auto-commit thay đổi

---

## Workflows Có Sẵn

### 1. auto-process.yml

**Chức năng:**
- Tự động format code Python với `black`
- Tự động sort imports với `isort`
- Commit và push thay đổi tự động

**Khi nào chạy:**
- Khi có file `.py` hoặc `.sql` thay đổi trên branch `main`
- Chạy thủ công qua `workflow_dispatch`

**Cách chạy thủ công:**
1. Vào GitHub repository
2. Click tab **Actions**
3. Chọn workflow **Auto Process and Commit**
4. Click **Run workflow**
5. Chọn branch và click **Run workflow**

---

## Cấu Trúc Workflow

### Permissions

```yaml
permissions:
  contents: write  # Quan trọng! Cho phép commit
```

### Trigger (Kích hoạt)

```yaml
on:
  push:
    branches: [ main ]
    paths:
      - '*.py'   # File Python
      - '*.sql'  # File SQL
  workflow_dispatch:  # Chạy thủ công
```

### Các Steps

1. **Checkout code** - Clone repository
2. **Set up Python** - Cài đặt Python 3.9
3. **Install dependencies** - Cài đặt black, isort, pylint
4. **Format Python code** - Format code
5. **Check for changes** - Kiểm tra có thay đổi không
6. **Commit changes** - Commit nếu có thay đổi
7. **Generate summary** - Tạo summary

---

## Các Công Cụ Được Sử Dụng

### Black
- **Chức năng:** Formatter Python không cần cấu hình
- **Mục đích:** Đảm bảo code style nhất quán
- **Cách dùng:** `black .`

### isort
- **Chức năng:** Sort imports Python
- **Mục đích:** Đảm bảo imports theo thứ tự chuẩn
- **Cách dùng:** `isort .`

---

## Lưu Ý Quan Trọng

### ⚠️ [skip ci] Tag

Commit message có chứa `[skip ci]` để tránh vòng lặp vô tận:

```yaml
git commit -m "Auto-format Python code [skip ci]"
```

Điều này ngăn workflow tự kích hoạt lại sau khi commit.

---

## Tùy Chỉnh Workflow

### Thêm Format Cho File Loại Khác

```yaml
- name: Format Python code
  run: |
    black .
    isort .
    # Thêm lệnh khác
```

### Thay Đổi Phiên Bản Python

```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.10'  # Đổi thành 3.10, 3.11, etc.
```

### Thêm Linters

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install black isort pylint mypy flake8
```

### Thêm Trigger Cho Branch Khác

```yaml
on:
  push:
    branches: [ main, develop ]  # Thêm branch develop
```

---

## Ví Dụ Workflows Khác

### Workflow Format Code Đơn Giản

```yaml
name: Format Code

on: [workflow_dispatch]

permissions:
  contents: write

jobs:
  format:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - run: pip install black isort
    - run: black . && isort .
    - run: |
        git config --local user.email "bot@example.com"
        git config --local user.name "bot"
        git add .
        git commit -m "Format code [skip ci]" || true
        git push
```

### Workflow Update README

```yaml
name: Update README

on:
  push:
    branches: [ main]
    paths:
      - 'README.md'  # Chạy khi README thay đổi

permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Add last updated date
      run: |
        DATE=$(date +%Y-%m-%d)
        echo "" >> README.md
        echo "Last updated: $DATE" >> README.md
    - run: |
        git config --local user.email "bot@example.com"
        git config --local user.name "bot"
        git add README.md
        git commit -m "Update last updated date [skip ci]" || true
        git push
```

---

## Troubleshooting

### Workflow không chạy?

**Kiểm tra:**
1. File có đúng đường dẫn `.github/workflows/auto-process.yml` không?
2. Branch có phải `main` không?
3. File có thay đổi không (`*.py` hoặc `*.sql`)?

### Commit không được push?

**Kiểm tra:**
1. Permissions có `contents: write` không?
2. Token có quyền commit không?

### Vòng lặp vô tận?

**Giải pháp:**
- Đảm bảo commit message có `[skip ci]`
- Hoặc dùng PAT token thay vì GITHUB_TOKEN

---

## Tài Liệu Tham Khảo

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [Pylint Documentation](https://pylint.pycqa.org/)

---

## Liên Hệ

Nếu có vấn đề hoặc câu hỏi, hãy tạo issue trong repository.
