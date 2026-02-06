---
description: Generate and run tests for Python code
---

# Test Workflow

## Overview
This workflow generates comprehensive tests and runs them for Python code.

## Clarifying Questions

Để tạo tests, tôi cần thông tin:

1. **Code cần test**:
   - File/module cần test ở đâu?
   - _______

2. **Test data**:
   - Có test data không?
   - [ ] Có, ở đây: _______
   - [ ] Không có

3. **Coverage target**:
   - Coverage target là bao nhiêu?
   - [ ] >90%
   - [ ] >80%
   - [ ] >70%
   - [ ] Không quan trọng

4. **Test types**:
   - Cần test types nào?
   - [ ] Unit tests
   - [ ] Integration tests
   - [ ] E2E tests
   - [ ] Tất cả

5. **Edge cases**:
   - Có edge cases quan trọng không?
   - 1. _______
   - 2. _______
   - 3. _______

## Interactive Planning Process

```
Step 1: User đưa ra request tạo tests
    ↓
Step 2: Agent hỏi clarifying questions (5 câu hỏi)
    ↓
Step 3: User trả lời các câu hỏi
    ↓
Step 4: Agent validates thông tin
    ↓
Step 5: Nếu chưa đủ, hỏi thêm
    ↓
Step 6: Khi đủ thông tin, thiết kế test strategy
    ↓
Step 7: Create test suite
    ↓
Step 8: Run tests
    ↓
Step 9: Analyze results
    ↓
Step 10: Improve coverage nếu cần
```

## Steps

### 1. Design Test Strategy
- Identify what needs testing
- Determine test types needed (unit, integration, E2E)
- Understand dependencies

### 2. Create Test Suite
- Write unit tests with pytest
- Add integration tests
- Include edge cases
- Implement mocking where needed

### 3. Run Tests
- Execute test suite
- Check coverage
- Identify failing tests

### 4. Analyze Results
- Review test failures
- Fix issues
- Improve coverage

## Usage
```
/test authentication service
/test run all tests
/test improve coverage
```

## Output
- Comprehensive test suite
- Test coverage report
- Test results
- Recommendations for improvement
