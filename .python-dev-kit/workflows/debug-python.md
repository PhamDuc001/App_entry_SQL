---
description: Debug Python code using systematic 4-phase methodology
---

# Debug Python Workflow

## Overview
This workflow uses a systematic 4-phase methodology to debug Python code and identify root causes.

## Clarifying Questions

Để debug, tôi cần thông tin chi tiết:

1. **Lỗi cụ thể**:
   - Error message là gì?
   - _______
   - Lỗi xảy ra khi nào? (conditions, inputs)
   - _______

2. **Context**:
   - File/function nào bị lỗi?
   - _______
   - Lỗi xảy ra trong môi trường nào? (development, production)
   - _______

3. **Logs và Traces**:
   - Có log/trace không?
   - [ ] Có, ở đây: _______
   - [ ] Không có

4. **Reproduction**:
   - Có thể reproduce lỗi không?
   - [ ] Có, cách reproduce: _______
   - [ ] Không, lỗi ngẫu nhiên

5. **Đã thử fix chưa**:
   - Bạn đã thử fix chưa?
   - [ ] Chưa
   - [ ] Có, đã thử: _______

6. **Expected behavior**:
   - Behavior mong muốn là gì?
   - _______

## Interactive Planning Process

```
Step 1: User đưa ra request debug
    ↓
Step 2: Agent hỏi clarifying questions (6 câu hỏi)
    ↓
Step 3: User trả lời các câu hỏi
    ↓
Step 4: Agent validates thông tin
    ↓
Step 5: Nếu chưa đủ, hỏi thêm
    ↓
Step 6: Khi đủ thông tin, bắt đầu 4-phase debugging
    ↓
Step 7: Reproduce lỗi
    ↓
Step 8: Isolate nguyên nhân
    ↓
Step 9: Analyze root cause
    ↓
Step 10: Implement fix và test
```

## Steps

### Phase 1: Reproduce
- Understand the problem
- Reproduce the issue consistently
- Identify conditions that trigger the bug
- Document expected vs actual behavior

### Phase 2: Isolate
- Narrow down the scope
- Identify specific component causing issue
- Use binary search approach
- Create minimal reproducible example

### Phase 3: Analyze
- Examine code flow
- Check variable states
- Analyze logs and stack traces
- Identify root cause

### Phase 4: Fix
- Implement the fix
- Test the solution
- Verify fix doesn't break other functionality
- Add tests to prevent regression

## Usage
```
/debug-python function X failing
/debug-python why login fails
/debug-python error in module.py
```

## Output
- Root cause identification
- Fix implementation
- Tests to prevent regression
- Documentation of the issue
