# Refactoring Checklist Template

> Copy template này vào implementation plan khi refactor.

## Pre-Refactor Analysis

- [ ] Đọc hiểu TOÀN BỘ code liên quan
- [ ] Chạy `analyze_complexity.py` trên target file
- [ ] Chạy `find_redundancy.py` trên target file
- [ ] Xác định rõ mục tiêu: Performance / Readability / Maintainability
- [ ] Liệt kê TẤT CẢ nơi bị ảnh hưởng (`grep_search`)
- [ ] Đánh giá Cost-Benefit: Nên refactor hay giữ nguyên?

## During Refactor

- [ ] Thay đổi từng file MỘT, theo thứ tự dependency
- [ ] Comment `[REFACTORED]` tại mỗi vị trí sửa
- [ ] KHÔNG thay đổi logic business
- [ ] Kiểm tra variable scope (inner vs outer) sau MỖI thay đổi
- [ ] Kiểm tra import statements (thừa/thiếu)

## Post-Refactor Verification

- [ ] Đọc lại code refactored
- [ ] Tìm variable name collision (grep tên biến mới)
- [ ] Verify output trước/sau giống nhau
- [ ] Check edge cases: None, empty, 0, missing keys
- [ ] Chạy `check_imports.py` để verify imports

## Documentation

- [ ] Cập nhật comments giải thích WHY
- [ ] Ghi walkthrough tóm tắt thay đổi
- [ ] Note performance improvement (nếu có)
