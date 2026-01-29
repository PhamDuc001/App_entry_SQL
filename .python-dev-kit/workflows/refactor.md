---
description: Refactor Python code for better maintainability
---

# Refactor Workflow

## Overview
This workflow refactors Python code to improve maintainability, readability, and structure.

## Clarifying Questions

Để refactor, tôi cần hiểu rõ vấn đề:

1. **Vấn đề với code hiện tại**:
   - Code có vấn đề gì?
   - [ ] Code smells (long functions, deep nesting, etc.)
   - [ ] Duplication
   - [ ] Poor naming
   - [ ] High complexity
   - [ ] Khác: _______

2. **Mục tiêu refactor**:
   - Mục tiêu là gì?
   - [ ] Improve readability
   - [ ] Improve maintainability
   - [ ] Apply design patterns
   - [ ] Reduce complexity
   - [ ] Khác: _______

3. **Design patterns**:
   - Có patterns muốn apply không?
   - [ ] Có: _______
   - [ ] Không, agent đề xuất

4. **Constraints**:
   - [ ] Không được thay đổi API
   - [ ] Phải maintain backward compatibility
   - [ ] Không được break tests
   - [ ] Khác: _______

## Interactive Planning Process

```
Step 1: User đưa ra request refactor
    ↓
Step 2: Agent hỏi clarifying questions (4 câu hỏi)
    ↓
Step 3: User trả lời các câu hỏi
    ↓
Step 4: Agent validates thông tin
    ↓
Step 5: Nếu chưa đủ, hỏi thêm
    ↓
Step 6: Khi đủ thông tin, analyze current code
    ↓
Step 7: Plan refactoring
    ↓
Step 8: Apply refactoring
    ↓
Step 9: Verify changes
    ↓
Step 10: Update documentation
```

## Steps

### 1. Analyze Current Code
- Identify code smells
- Find duplication
- Assess complexity

### 2. Plan Refactoring
- Define refactoring goals
- Identify patterns to apply
- Plan changes incrementally

### 3. Apply Refactoring
- Extract methods/functions
- Apply design patterns
- Improve naming
- Reduce complexity

### 4. Verify Changes
- Run tests
- Ensure behavior unchanged
- Update documentation

## Usage
```
/refactor authentication module
/refactor reduce complexity
/refactor apply design patterns
```

## Output
- Refactored code
- Refactoring report
- Before/after comparison
- Updated tests
