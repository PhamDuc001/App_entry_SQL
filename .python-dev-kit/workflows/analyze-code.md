---
description: Analyze Python/Java/C++ code and generate comprehensive report
---

# Code Analysis Workflow

## Overview
This workflow analyzes code in Python, Java, or C++ and generates a comprehensive report including architecture, patterns, and recommendations.

## Clarifying Questions

Trước khi bắt đầu phân tích, tôi cần hiểu rõ yêu cầu của bạn:

1. **Mục tiêu phân tích**: Bạn muốn tập trung vào khía cạnh nào?
   - [ ] Architecture và design patterns
   - [ ] Performance và bottlenecks
   - [ ] Security vulnerabilities
   - [ ] Code quality và code smells
   - [ ] Dependencies và integrations
   - [ ] Khác: _______

2. **Scope**: Bạn muốn phân tích phần nào?
   - [ ] Toàn bộ project
   - [ ] Module cụ thể: _______
   - [ ] File cụ thể: _______
   - [ ] Function/class cụ thể: _______

3. **Vấn đề cụ thể**: Có vấn đề nào bạn quan tâm không?
   - _______

4. **Output format**: Bạn muốn output như thế nào?
   - [ ] Báo cáo chi tiết (markdown)
   - [ ] Tóm tắt ngắn gọn
   - [ ] Visual diagrams
   - [ ] Khác: _______

## Interactive Planning Process

```
Step 1: User đưa ra request phân tích
    ↓
Step 2: Agent hỏi clarifying questions (4 câu hỏi)
    ↓
Step 3: User trả lời các câu hỏi
    ↓
Step 4: Agent validates thông tin
    ↓
Step 5: Nếu chưa đủ, hỏi thêm
    ↓
Step 6: Khi đủ thông tin, bắt đầu phân tích
    ↓
Step 7: Generate báo cáo
    ↓
Step 8: User review và feedback
    ↓
Step 9: Agent refine nếu cần
```

## Steps

### 1. Discovery Phase
- Identify language and framework
- List all modules/files
- Build dependency graph

### 2. Static Analysis
- Parse AST (for Python)
- Extract functions/classes
- Identify patterns

### 3. Dynamic Analysis (if executable)
- Trace execution flow
- Profile performance
- Identify bottlenecks

### 4. Report Generation
- Architecture overview
- Key findings
- Recommendations

## Usage
```
/analyze-code path/to/module.py
/analyze-code path/to/JavaFile.java
/analyze-code path/to/CPPFile.cpp
```

## Output
Comprehensive analysis report including:
- Language and framework identification
- Module structure
- Design patterns used
- Code smells detected
- Performance issues
- Security vulnerabilities
- Refactoring recommendations
