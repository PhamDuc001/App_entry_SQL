---
description: Build a new CLI tool or automation script
---

# Build Tool Workflow

## Overview
This workflow guides you through building a production-ready CLI tool or automation script in Python.

## Clarifying Questions

Để xây dựng tool, tôi cần hiểu rõ requirements:

1. **Mục đích chính**: Tool này làm gì?
   - _______

2. **Input**:
   - Input format là gì? (CSV, JSON, TXT, etc.)
   - Input đến từ đâu? (file, stdin, API, database)
   - Có ví dụ về input không?
   - _______

3. **Output**:
   - Output format mong muốn là gì? (CSV, JSON, HTML, Excel, etc.)
   - Output đến đâu? (file, stdout, API, database)
   - Có ví dụ về output mong muốn không?
   - _______

4. **Functionality**:
   - Các features chính là gì?
   - 1. _______
   - 2. _______
   - 3. _______

5. **CLI Framework**: Bạn muốn dùng framework nào?
   - [ ] argparse (standard library)
   - [ ] click (decorator-based)
   - [ ] typer (type-hint based)
   - [ ] Không quan trọng, chọn phù hợp nhất

6. **Configuration**:
   - Cần configuration không?
   - [ ] Có, từ file (YAML, TOML, JSON)
   - [ ] Có, từ environment variables
   - [ ] Có, từ CLI arguments
   - [ ] Không cần

7. **Constraints**:
   - [ ] Không được thay đổi API hiện tại
   - [ ] Phải maintain backward compatibility
   - [ ] Time limit: _______
   - [ ] Khác: _______

## Interactive Planning Process

```
Step 1: User đưa ra request xây dựng tool
    ↓
Step 2: Agent hỏi clarifying questions (7 câu hỏi)
    ↓
Step 3: User trả lời các câu hỏi
    ↓
Step 4: Agent validates thông tin
    ↓
Step 5: Nếu chưa đủ, hỏi thêm
    ↓
Step 6: Khi đủ thông tin, tạo plan chi tiết
    ↓
Step 7: User review và feedback
    ↓
Step 8: Agent refine plan
    ↓
Step 9: User approve plan
    ↓
Step 10: Implement tool theo plan
```

## Steps

### 1. Requirements Gathering
- Understand the tool's purpose
- Identify target users
- Define key features
- Plan CLI interface

### 2. Architecture Design
- Choose CLI framework (argparse, click, typer)
- Design module structure
- Plan configuration system
- Define logging strategy

### 3. Implementation
- Build CLI interface
- Implement core logic
- Add error handling
- Integrate logging

### 4. Testing
- Write unit tests
- Create integration tests
- Test edge cases
- Validate error handling

### 5. Packaging
- Create setup.py/pyproject.toml
- Write README
- Add examples
- Prepare for distribution

## Usage
```
/build-tool log analyzer
/build-tool file processor
/build-tool automation script
```

## Output
Complete CLI tool with:
- CLI interface
- Core functionality
- Error handling
- Logging
- Configuration
- Tests
- Documentation
- Package files
