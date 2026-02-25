# Python Dev Kit - Hướng Dẫn Sử Dụng Workflows Chi Tiết

## Table of Contents
1. [Giới Thiệu](#giới-thiệu)
2. [Interactive Planning - Quan Trọng](#interactive-planning---quan-trọng)
3. [Cấu Hình Ban Đầu](#cấu-hình-ban-đầu)
4. [12 Workflows Chi Tiết](#12-workflows-chi-tiết)
5. [Kịch Bản Thực Tế](#kịch-bản-thực-tế)
6. [Quy Trình Phát Triển Tool](#quy-trình-phát-triển-tool)
7. [Tips và Best Practices](#tips-và-best-practices)

---

## Giới Thiệu

Python Dev Kit là bộ công cụ AI chuyên sâu cho phát triển Python tools, hỗ trợ đọc hiểu code đa ngôn ngữ (Python, Java, C++) và tích hợp với Cline thông qua rules, workflows, và memory bank.

### Cấu Trúc
```
.python-dev-kit/
├── agents/           # 15 Specialist Agents
├── skills/           # 10 Skills (kiến thức chuyên sâu)
├── workflows/        # 12 Slash Commands
└── rules/            # 3 Workspace Rules
```

### Khi Nào Dùng Workflow vs Agent
- **Workflow**: Dùng cho các tác vụ có quy trình chuẩn hóa (ví dụ: `/analyze-code`, `/build-tool`)
- **Agent**: Dùng khi cần chuyên gia cụ thể (ví dụ: `Use the code-analyzer agent`)

---

## Interactive Planning - Quan Trọng

### Tại Sao Interactive Planning Quan Trọng?

Trước khi thực hiện bất kỳ task nào, agents và workflows trong Python Dev Kit **PHẢI** hỏi user để thu thập thông tin chi tiết. Điều này đảm bảo:

1. **Hiểu rõ requirements**: Tránh hiểu sai hoặc thiếu thông tin
2. **Tối ưu thời gian**: Không làm việc không cần thiết
3. **Kết quả phù hợp**: Đáp ứng đúng nhu cầu thực tế của user
4. **Tránh sai lầm**: Giảm thiểu rework do thiếu thông tin

### Quy Trình Interactive Planning

```
Step 1: User đưa ra request ban đầu
    ↓
Step 2: Agent/Workflow hỏi clarifying questions
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
Step 10: Implement theo plan
```

### Các Câu Hỏi Mẫu Cho Từng Loạii Task

#### 1. Phân Tích Code (/analyze-code)

**Agent sẽ hỏi**:
```
Trước khi phân tích, tôi cần biết:

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
```

#### 2. Xây Dựng Tool (/build-tool)

**Agent sẽ hỏi**:
```
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
```

#### 3. Debug (/debug-python)

**Agent sẽ hỏi**:
```
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
```

#### 4. Tối Ưu (/optimize)

**Agent sẽ hỏi**:
```
Để tối ưu, tôi cần hiểu rõ vấn đề:

1. **Performance issue**:
   - Code chạy chậm như thế nào?
   - [ ] Rất chậm (>10s)
   - [ ] Chậm (1-10s)
   - [ ] Hơi chậm (<1s)
   - [ ] Khác: _______

2. **Bottlenecks nghi ngờ**:
   - Bạn nghi ngờ bottleneck ở đâu?
   - [ ] I/O operations
   - [ ] Database queries
   - [ ] Algorithm complexity
   - [ ] Memory usage
   - [ ] Không biết

3. **Requirements**:
   - Target performance là gì?
   - _______
   - Có thể sacrifice readability không?
   - [ ] Có, tối ưu là ưu tiên
   - [ ] Không, maintain readability

4. **Constraints**:
   - [ ] Không được thay đổi API
   - [ ] Phải maintain backward compatibility
   - [ ] Memory limit: _______
   - [ ] Khác: _______
```

#### 5. Test (/test)

**Agent sẽ hỏi**:
```
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
```

#### 6. Refactor (/refactor)

**Agent sẽ hỏi**:
```
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
```

### Ví Dụ Dialog Thực Tế

#### Ví Dụ 1: Xây Dựng CLI Tool

**User**:
```
/build-tool CLI tool for log analysis
```

**Agent**:
```
Để xây dựng CLI tool cho log analysis, tôi cần hiểu rõ requirements:

1. **Mục đích chính**: Tool này làm gì?
   - Phân tích log files
   - Tìm patterns/errors
   - Generate reports

2. **Input**:
   - Input format là gì? (CSV, JSON, TXT, etc.)
   - Input đến từ đâu? (file, stdin, API, database)
   - Có ví dụ về input không?

3. **Output**:
   - Output format mong muốn là gì? (CSV, JSON, HTML, Excel, etc.)
   - Output đến đâu? (file, stdout, API, database)
   - Có ví dụ về output mong muốn không?

4. **Functionality**:
   - Các features chính là gì?
   - 1. Parse log files
   - 2. Extract errors/warnings
   - 3. Generate statistics
   - 4. Khác: _______

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
```

**User**:
```
1. Mục đích: Phân tích log files để tìm errors và warnings
2. Input: TXT files từ folder
3. Output: CSV report với statistics
4. Features:
   - Parse log files
   - Extract errors/warnings
   - Generate statistics
   - Filter by time range
5. Framework: Không quan trọng
6. Config: Có, từ CLI arguments
7. Constraints: Không có
```

**Agent**:
```
Cảm ơn thông tin! Tôi sẽ tạo CLI tool với:
- Framework: click (decorator-based, dễ sử dụng)
- Input: TXT files từ folder (có thể specify folder path)
- Output: CSV report với statistics
- Features: Parse, extract errors/warnings, generate stats, filter by time
- Config: CLI arguments (--input, --output, --start-time, --end-time)

Kế hoạch chi tiết:
1. Create CLI structure with click
2. Implement log parser
3. Implement error/warning extractor
4. Implement statistics generator
5. Implement time range filter
6. Add error handling
7. Create tests
8. Write documentation

Bạn có muốn điều chỉnh gì không?
```

#### Ví Dụ 2: Debug Lỗi

**User**:
```
/debug-python PyQt6 window not showing
```

**Agent**:
```
Để debug vấn đề PyQt6 window không showing, tôi cần thông tin chi tiết:

1. **Lỗi cụ thể**:
   - Error message là gì?
   - Lỗi xảy ra khi nào? (conditions, inputs)
   - Window không hiển thị ngay từ đầu hay sau một action?

2. **Context**:
   - File/function nào bị lỗi?
   - Lỗi xảy ra trong môi trường nào? (development, production)
   - PyQt6 version là gì?

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
   - Window nên hiển thị như thế nào?
```

**User**:
```
1. Lỗi: Không có error message, window không hiển thị
2. Context: main_window.py, development, PyQt6 6.5.0
3. Logs: Không có
4. Reproduction: Có, chạy app thì window không hiện
5. Đã thử: Chưa
6. Expected: Window nên hiển thị với toolbar và menu
```

**Agent**:
```
Cảm ơn thông tin! Tôi sẽ debug theo 4-phase methodology:

**Phase 1: Reproduce**
- Chạy app và xác nhận window không hiển thị
- Check console output
- Verify PyQt6 installation

**Phase 2: Isolate**
- Check MainWindow.__init__()
- Check setup_ui()
- Check show() call
- Check event loop

**Phase 3: Analyze**
- Examine code flow
- Check variable states
- Identify root cause

**Phase 4: Fix**
- Implement fix
- Test solution
- Add tests

Bạn có thể cung cấp code của main_window.py không? Hoặc tôi có thể đọc từ path?
```

### Best Practices Cho Interactive Planning

1. **Hỏi 5-10 câu hỏi**: Đủ để hiểu requirements nhưng không quá nhiều
2. **Cung cấp options**: Cho user chọn thay vì phải viết từ đầu
3. **Validate thông tin**: Kiểm tra thông tin đã đủ chưa
4. **Iterative refinement**: Hỏi thêm nếu cần
5. **Confirm trước khi implement**: Luôn confirm plan với user

---

## Cấu Hình Ban Đầu

### Bước 1: Copy vào Project
Copy folder `.python-dev-kit/` vào project của bạn:
```bash
# Từ antigravity-kit
cp -r .python-dev-kit/ /path/to/your/project/
```

### Bước 2: Cấu Hình Cline
Đảm bảo Cline load rules từ `.python-dev-kit/rules/`:
- `python-standards.md`: Tiêu chuẩn code Python
- `code-review.md`: Checklist code review
- `memory-bank.md`: Lưu context project

### Bước 3: Populate Memory Bank
Edit `.python-dev-kit/rules/memory-bank.md` với thông tin project:
```markdown
## Project Context

### Project Information
- **Project Name**: [Tên project]
- **Purpose**: [Mục đích]
- **Tech Stack**: [Công nghệ]
- **Key Dependencies**: [Dependencies chính]
```

---

## 12 Workflows Chi Tiết

### 1. /analyze-code

**Mô tả**: Phân tích code Python/Java/C++ và tạo báo cáo chi tiết

**Kịch bản sử dụng**:
- Khi bắt đầu làm việc với codebase mới
- Khi cần hiểu cấu trúc của module
- Khi cần review architecture

**Cách sử dụng**:
```
/analyze-code path/to/module.py
/analyze-code path/to/JavaFile.java
/analyze-code path/to/CPPFile.cpp
```

**Agent liên quan**: `code-analyzer`

**Skills được load**: `code-comprehension`, `static-analysis`, `pattern-recognition`, `dependency-mapping`

**Kết quả mong đợi**:
```markdown
# Code Analysis Report

## Overview
- Language: Python
- Framework: PyQt6
- Module Structure: [chi tiết]

## Architecture
- Design Patterns: [liệt kê]
- Component Relationships: [mô tả]
- Data Flow: [giải thích]

## Findings
- Patterns Identified: [patterns]
- Code Smells: [issues]
- Performance Issues: [bottlenecks]
- Security Vulnerabilities: [vulnerabilities]

## Recommendations
- Refactoring Suggestions: [gợi ý]
- Performance Improvements: [tối ưu]
- Best Practices: [khuyến nghị]
```

**Ví dụ thực tế**:
```
/analyze-code D:\Tools\CheckList\Bringup\Github\p4_tool\main_window.py
```

**Tips**:
- Sử dụng workflow này trước khi bắt đầu bất kỳ thay đổi lớn
- Kết quả giúp bạn hiểu bức tranh tổng quan
- Lưu báo cáo vào memory bank để tham khảo sau

---

### 2. /build-tool

**Mô tả**: Xây dựng CLI tool hoặc automation script mới

**Kịch bản sử dụng**:
- Khi cần tạo CLI tool mới
- Khi cần automation script
- Khi cần package Python utility

**Cách sử dụng**:
```
/build-tool log analyzer
/build-tool file processor
/build-tool automation script
```

**Agent liên quan**: `tool-builder`

**Skills được load**: `tool-development`, `argparse-patterns`, `packaging`, `automation-scripts`

**Kết quả mong đợi**:
- CLI interface hoàn chỉnh
- Core functionality
- Error handling
- Logging
- Configuration
- Tests
- Documentation
- Package files (setup.py/pyproject.toml)

**Ví dụ thực tế**:
```
/build-tool CLI tool for Perforce operations
```

**Agent sẽ tạo**:
```python
# CLI structure
tool_name/
├── src/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point
│   ├── core/               # Core business logic
│   ├── config/             # Configuration
│   └── utils/              # Utilities
├── tests/
│   ├── unit/
│   └── integration/
├── setup.py or pyproject.toml
└── README.md
```

**Tips**:
- Agent sẽ hỏi clarifying questions về requirements
- Chọn CLI framework phù hợp (argparse, click, typer)
- Tự động tạo tests và documentation
- Package sẵn sàng để cài đặt với pip

---

### 3. /debug-python

**Mô tả**: Debug Python code sử dụng 4-phase methodology

**Kịch bản sử dụng**:
- Khi có lỗi không rõ nguyên nhân
- Khi function không hoạt động như mong đợi
- Khi cần systematic debugging

**Cách sử dụng**:
```
/debug-python function X failing
/debug-python why login fails
/debug-python error in module.py
```

**Agent liên quan**: `debugger`

**Skills được load**: `debugging-methodology`, `logging-patterns`, `error-handling`

**Kết quả mong đợi**:
- Root cause identification
- Fix implementation
- Tests to prevent regression
- Documentation of the issue

**4-Phase Methodology**:

**Phase 1: Reproduce**
```
1. Understand the problem
2. Reproduce the issue consistently
3. Identify conditions that trigger the bug
4. Document expected vs actual behavior
```

**Phase 2: Isolate**
```
1. Narrow down the scope
2. Identify specific component causing issue
3. Use binary search approach
4. Create minimal reproducible example
```

**Phase 3: Analyze**
```
1. Examine code flow
2. Check variable states
3. Analyze logs and stack traces
4. Identify root cause
```

**Phase 4: Fix**
```
1. Implement the fix
2. Test the solution
3. Verify fix doesn't break other functionality
4. Add tests to prevent regression
```

**Ví dụ thực tế**:
```
/debug-python PyQt6 window not showing
```

**Agent sẽ**:
1. Reproduce: Chạy code và xác nhận lỗi
2. Isolate: Tìm ra component gây lỗi
3. Analyze: Phân tích code flow
4. Fix: Sửa lỗi và test

**Tips**:
- Luôn reproduce lỗi trước khi fix
- Sử dụng logging để trace execution
- Tạo minimal example để isolate issue
- Luôn thêm tests sau khi fix

---

### 4. /optimize

**Mô tả**: Tối ưu performance Python code

**Kịch bản sử dụng**:
- Khi code chạy chậm
- Khi cần giảm memory usage
- Khi cần tối ưu database queries

**Cách sử dụng**:
```
/optimize slow function
/optimize database queries
/optimize memory usage
```

**Agent liên quan**: `performance-tuner`

**Skills được load**: `performance-optimization`, `profiling`, `caching-strategies`, `concurrency`

**Kết quả mong đợi**:
- Performance analysis report
- Optimized code
- Before/after comparison
- Performance metrics

**Quy trình tối ưu**:

**1. Profile First**
```bash
# CPU profiling
cProfile -o profile.stats script.py

# Memory profiling
python -m memory_profiler script.py

# Statistical profiling
py-spy record -o profile.svg python script.py
```

**2. Analyze Results**
- Identify hot spots
- Find memory leaks
- Analyze call graphs

**3. Optimize Strategically**
- Algorithm optimization
- Data structure selection
- Caching strategies
- Concurrency patterns

**4. Verify Improvements**
- Profile after changes
- Measure performance gain
- Ensure correctness

**Ví dụ thực tế**:
```
/optimize PyQt6 interface performance
```

**Agent sẽ**:
1. Profile code với cProfile/py-spy
2. Identify bottlenecks
3. Suggest optimizations (caching, async, etc.)
4. Implement và verify

**Tips**:
- Luôn profile trước khi optimize
- Focus vào bottlenecks thực sự
- Đo lường trước và sau khi optimize
- Cân bằng giữa performance và readability

---

### 5. /cross-lang

**Mô tả**: Map code giữa Python, Java, và C++

**Kịch bản sử dụng**:
- Khi cần hiểu code Java/C++
- Khi cần port code sang Python
- Khi cần tích hợp multi-language components

**Cách sử dụng**:
```
/cross-lang JavaFile.java → Python
/cross-lang CPPFile.cpp → Python
/cross-lang map Java patterns to Python
```

**Agent liên quan**: `java-bridge` hoặc `cpp-bridge`

**Skills được load**: `java-patterns`, `cpp-patterns`, `python-java-interop`, `python-cpp-interop`, `cross-language-bridge`

**Kết quả mong đợi**:
- Python equivalent code
- Mapping documentation
- Comparison of patterns
- Best practices for target language

**Ví dụ thực tế**:
```
/cross-lang D:\Tools\CheckList\Bringup\Github\legacy_tool\JavaClass.java → Python
```

**Agent sẽ**:
1. Phân tích Java code
2. Map types và patterns sang Python
3. Áp dụng Pythonic idioms
4. Cung cấp code Python equivalent

**Type Mapping Examples**:

| Java Type | Python Equivalent |
|-----------|------------------|
| `int`, `long` | `int` |
| `float`, `double` | `float` |
| `boolean` | `bool` |
| `String` | `str` |
| `List<T>` | `list` |
| `Map<K,V>` | `dict` |
| `Set<T>` | `set` |

**Tips**:
- Đừng chỉ translate syntax, hãy translate concepts
- Áp dụng Pythonic idioms thay vì Java/C++ patterns
- Cẩn trọng với memory management (C++ → Python)
- Sử dụng type hints để rõ ràng hơn

---

### 6. /test

**Mô tả**: Tạo và chạy tests cho Python code

**Kịch bản sử dụng**:
- Khi cần tạo test suite
- Khi cần improve coverage
- Khi cần validate changes

**Cách sử dụng**:
```
/test authentication service
/test run all tests
/test improve coverage
```

**Agent liên quan**: `test-engineer`

**Skills được load**: `testing-strategies`, `pytest-patterns`, `mocking`, `property-testing`

**Kết quả mong đợi**:
- Comprehensive test suite
- Test coverage report
- Test results
- Recommendations for improvement

**Test Pyramid**:
```
        E2E Tests (10%)
       /             \
    Integration Tests (30%)
   /                   \
Unit Tests (60%)
```

**Ví dụ thực tế**:
```
/test PyQt6 interface
```

**Agent sẽ tạo**:
```python
# Unit tests
def test_main_window_creation():
    window = MainWindow()
    assert window is not None
    assert window.windowTitle() == "P4 Tool"

# Integration tests
def test_perforce_integration():
    tool = P4Tool()
    result = tool.connect()
    assert result.success

# Fixtures
@pytest.fixture
def main_window():
    return MainWindow()
```

**Tips**:
- Mục tiêu coverage > 80%
- Tests phải độc lập và nhanh
- Sử dụng fixtures cho setup/teardown
- Test edge cases và error conditions

---

### 7. /review

**Mô tả**: Code review với checklist chi tiết

**Kịch bản sử dụng**:
- Khi review pull request
- Khi review changes
- Khi cần quality check

**Cách sử dụng**:
```
/review authentication module
/review pull request #123
/review recent changes
```

**Agent liên quan**: `security-auditor`, `python-architect`

**Skills được load**: `security-patterns`, `clean-code`, `code-review`

**Kết quả mong đợi**:
- Comprehensive review report
- Issues found with severity
- Recommendations for improvement
- Approval status

**Review Checklist**:

**Functionality**
- [ ] Requirements met
- [ ] Edge cases handled
- [ ] Error handling complete

**Code Quality**
- [ ] Follows PEP 8
- [ ] Type hints present
- [ ] Docstrings complete
- [ ] No code duplication

**Security**
- [ ] Input validation
- [ ] Output encoding
- [ ] No hardcoded secrets
- [ ] Secure dependencies

**Performance**
- [ ] Efficient algorithms
- [ ] Appropriate data structures
- [ ] No obvious bottlenecks

**Testing**
- [ ] Unit tests cover logic
- [ ] Integration tests present
- [ ] Edge cases tested

**Ví dụ thực tế**:
```
/review PyQt6 interface changes
```

**Agent sẽ**:
1. Review code theo checklist
2. Identify issues với severity (critical, major, minor)
3. Cung cấp recommendations
4. Đưa ra approval status

**Tips**:
- Review cả functionality và code quality
- Focus trên security và performance
- Cung cấp constructive feedback
- Document decisions trong memory bank

---

### 8. /document

**Mô tả**: Tạo documentation cho Python projects

**Kịch bản sử dụng**:
- Khi cần tạo README
- Khi cần API docs
- Khi cần user guides

**Cách sử dụng**:
```
/document API reference
/document user guide
/document architecture
```

**Agent liên quan**: `documentation-writer`

**Skills được load**: `documentation-patterns`, `docstring-patterns`, `sphinx`, `markdown`

**Kết quả mong đợi**:
- README file
- API documentation
- User guides
- Developer guides
- Architecture documentation

**README Structure**:
```markdown
# Project Name

Short description

## Features
- Feature 1
- Feature 2

## Installation
```bash
pip install project-name
```

## Quick Start
```python
from project_name import main
main()
```

## Usage
Detailed usage examples...

## API Reference
Link to API docs...

## Contributing
Guidelines...

## License
MIT License
```

**Ví dụ thực tế**:
```
/document PyQt6 interface
```

**Agent sẽ tạo**:
- README với installation và usage
- API docs với docstrings
- User guide với examples
- Architecture documentation

**Tips**:
- Be clear and concise
- Provide examples
- Keep documentation updated
- Use consistent style

---

### 9. /profile

**Mô tả**: Profile Python code performance

**Kịch bản sử dụng**:
- Khi cần identify bottlenecks
- Khi cần measure performance
- Khi cần analyze resource usage

**Cách sử dụng**:
```
/profile CPU usage
/profile memory usage
/profile function X
```

**Agent liên quan**: `performance-tuner`

**Skills được load**: `profiling`, `caching-strategies`, `concurrency`

**Kết quả mong đợi**:
- Performance profile report
- Flame graphs
- Bottleneck identification
- Optimization recommendations

**Profiling Tools**:

**CPU Profiling**
```bash
# cProfile
python -m cProfile -o profile.stats script.py

# py-spy (statistical)
py-spy record -o profile.svg python script.py
```

**Memory Profiling**
```bash
# memory_profiler
python -m memory_profiler script.py

# objgraph
python -c "import objgraph; objgraph.show_most_common_types()"
```

**Ví dụ thực tế**:
```
/profile PyQt6 interface performance
```

**Agent sẽ**:
1. Chọn profiling tool phù hợp
2. Run profiler
3. Analyze results
4. Generate flame graph
5. Identify bottlenecks

**Tips**:
- Profile trước khi optimize
- Sử dụng py-spy cho production code
- Tạo flame graphs để visualize
- Focus trên hot spots

---

### 10. /refactor

**Mô tả**: Refactor Python code để improve maintainability

**Kịch bản sử dụng**:
- Khi code có code smells
- Khi cần improve architecture
- Khi cần apply design patterns

**Cách sử dụng**:
```
/refactor authentication module
/refactor reduce complexity
/refactor apply design patterns
```

**Agent liên quan**: `python-architect`

**Skills được load**: `python-patterns`, `clean-code`, `design-patterns`

**Kết quả mong đợi**:
- Refactored code
- Refactoring report
- Before/after comparison
- Updated tests

**Refactoring Steps**:

**1. Analyze Current Code**
- Identify code smells
- Find duplication
- Assess complexity

**2. Plan Refactoring**
- Define refactoring goals
- Identify patterns to apply
- Plan changes incrementally

**3. Apply Refactoring**
- Extract methods/functions
- Apply design patterns
- Improve naming
- Reduce complexity

**4. Verify Changes**
- Run tests
- Ensure behavior unchanged
- Update documentation

**Ví dụ thực tế**:
```
/refactor MainWindow to use modern PyQt6 patterns
```

**Agent sẽ**:
1. Analyze current MainWindow code
2. Identify code smells (long methods, deep nesting)
3. Apply design patterns (MVC, Observer)
4. Refactor code
5. Update tests

**Tips**:
- Refactor incrementally
- Luôn run tests sau mỗi change
- Maintain behavior
- Update documentation

---

### 11. /integrate

**Mô tả**: Tích hợp multi-language components

**Kịch bản sử dụng**:
- Khi cần tích hợp Python với Java/C++
- Khi cần create bindings
- Khi cần handle data conversion

**Cách sử dụng**:
```
/integrate Python and Java components
/integrate C++ library with Python
/integrate multi-language system
```

**Agent liên quan**: `multi-language-analyst`

**Skills được load**: `cross-language-analysis`, `pattern-extraction`, `code-mapping`

**Kết quả mong đợi**:
- Integration layer
- Communication protocols
- Data conversion utilities
- Integration tests

**Integration Approaches**:

**Python ↔ Java**
```python
# Option 1: JPype
import jpype
jpype.startJVM()
java_class = jpype.JClass("com.example.Class")

# Option 2: PyJNIus
from jnius import autoclass
JavaClass = autoclass("com.example.Class")
```

**Python ↔ C++**
```python
# Option 1: ctypes
from ctypes import cdll
lib = cdll.LoadLibrary("./mylib.so")

# Option 2: pybind11
# C++ side
#include <pybind11/pybind11.h>
PYBIND11_MODULE(example, m) {
    m.def("add", [](int a, int b) { return a + b; });
}

# Option 3: Cython
# mymodule.pyx
def add(int a, int b):
    return a + b
```

**Ví dụ thực tế**:
```
/integrate C++ Perforce API with Python PyQt6 interface
```

**Agent sẽ**:
1. Analyze C++ API
2. Design integration layer
3. Create bindings (pybind11/Cython)
4. Implement data conversion
5. Create integration tests

**Tips**:
- Chọn integration approach phù hợp
- Handle type conversion carefully
- Test cross-language calls
- Document integration points

---

### 12. /explain

**Mô tả**: Giải thích logic flow của function theo format chuẩn hóa

**Kịch bản sử dụng**:
- Khi cần hiểu logic flow chi tiết
- Khi cần document function
- Khi cần explain code cho team

**Cách sử dụng**:
```
/explain function_name
/explain process_all_traces
/explain analyze_trace
```

**Agent liên quan**: `code-analyzer`

**Skills được load**: `code-comprehension`, `static-analysis`, `pattern-recognition`

**Kết quả mong đợi**:
Giải thích chi tiết theo format:
```markdown
# Phân Tích Chi Tiết Logic Flow của `{function_name}`

## Tổng Quan về `{function_name}`
- Mô tả ngắn gọn mục đích chính của hàm
- File chứa hàm
- Vai trò trong hệ thống

## Logic Flow Chi Tiết Từng Bước
[Phân tích từng bước với format:
- Code snippet
- Logic: Giải thích ý tưởng và mục đích
- Ví dụ: Input/Output minh họa cụ thể]

## Flow Chart Tổng Quan
```
Input
    ↓
Step 1
    ↓
Step 2
    ↓
...
    ↓
Output
```

## Ví Dụ Minh Họa Đầy Đủ
[Scenario thực tế với:
- Cấu trúc folder/files
- Data flow từ input đến output
- Kết quả cuối cùng]
```

**Ví dụ thực tế**:
```
/explain MainWindow.setup_ui
```

**Agent sẽ trả về**:
```markdown
# Phân Tích Chi Tiết Logic Flow của `MainWindow.setup_ui`

## Tổng Quan về `MainWindow.setup_ui`
- Mô tả: Thiết lập giao diện chính của ứng dụng PyQt6
- File: main_window.py
- Vai trò: Khởi tạo tất cả UI components và layouts

## Logic Flow Chi Tiết Từng Bước

### Step 1: Create Central Widget
```python
self.central_widget = QWidget()
self.setCentralWidget(self.central_widget)
```
**Logic**: Tạo widget trung tâm và set làm widget chính của window
**Ví dụ**: Input: MainWindow instance → Output: central_widget được tạo

### Step 2: Create Main Layout
```python
self.main_layout = QVBoxLayout(self.central_widget)
```
**Logic**: Tạo vertical layout cho central widget
**Ví dụ**: Input: central_widget → Output: main_layout được tạo

### Step 3: Create and Add Widgets
```python
self.toolbar = QToolBar("Main Toolbar")
self.addToolBar(self.toolbar)
self.main_layout.addWidget(self.toolbar)
```
**Logic**: Tạo toolbar và add vào layout
**Ví dụ**: Input: main_layout → Output: toolbar được thêm

## Flow Chart Tổng Quan
```
MainWindow instance
    ↓
Create central widget
    ↓
Create main layout
    ↓
Create toolbar
    ↓
Create menu bar
    ↓
Create status bar
    ↓
Connect signals/slots
    ↓
UI ready
```

## Ví Dụ Minh Họa Đầy Đủ

### Scenario: Khởi tạo ứng dụng P4 Tool

**Cấu trúc folder**:
```
p4_tool/
├── main_window.py
├── widgets/
│   ├── toolbar.py
│   └── status_bar.py
└── resources/
    └── icons/
```

**Data Flow**:
```
User launches app
    ↓
MainWindow.__init__() called
    ↓
setup_ui() called
    ↓
Create widgets (toolbar, menu, status bar)
    ↓
Connect signals (button clicks, menu actions)
    ↓
Show window
    ↓
UI ready for user interaction
```

**Kết quả cuối cùng**: Giao diện PyQt6 hoàn chỉnh với toolbar, menu bar, và status bar
```

**Tips**:
- Sử dụng workflow này để hiểu logic flow sâu
- Kết quả có thể dùng để document code
- Giúp onboarding team members mới
- Hữu ích cho code review

---

## Kịch Bản Thực Tế

### Kịch Bản 1: Bắt Đầu Với Codebase Mới

**Mục tiêu**: Hiểu cấu trúc và logic của codebase mới

**Quy trình**:
```
1. /analyze-code path/to/project
   → Phân tích toàn bộ codebase

2. Use explorer-agent to find key files
   → Tìm entry points, main modules

3. Use code-archaeologist to understand legacy code
   → Hiểu patterns và architecture

4. Populate memory bank với findings
   → Lưu kiến thức về project
```

**Ví dụ**:
```
/analyze-code D:\Tools\CheckList\Bringup\Github\p4_tool
Use explorer-agent to find main entry points
Use code-archaeologist to understand Perforce integration
```

---

### Kịch Bản 2: Hiểu Logic Flow Phức Tạp

**Mục tiêu**: Hiểu chi tiết cách một function hoạt động

**Quy trình**:
```
1. /explain complex_function_name
   → Giải thích logic flow chi tiết

2. Use code-analyzer agent to analyze dependencies
   → Hiểu các function được gọi

3. /explain related_function
   → Hiểu các function liên quan
```

**Ví dụ**:
```
/explain MainWindow.process_perforce_command
/explain P4Connection.execute_command
```

---

### Kịch Bản 3: Xây Dựng CLI Tool Mới

**Mục tiêu**: Tạo CLI tool hoàn chỉnh

**Quy trình**:
```
1. /plan create CLI tool for log analysis
   → Lập kế hoạch chi tiết

2. /build-tool log analyzer CLI
   → Implement tool

3. /test log analyzer
   → Tạo và chạy tests

4. /document log analyzer
   → Tạo documentation

5. /review log analyzer
   → Code review
```

**Ví dụ**:
```
/plan create CLI tool for Perforce operations
/build-tool p4 CLI tool
/test p4 CLI tool
/document p4 CLI tool
/review p4 CLI tool
```

---

### Kịch Bản 4: Debug Lỗi Phức Tạp

**Mục tiêu**: Tìm và fix lỗi khó

**Quy trình**:
```
1. /debug-python function X failing with error Y
   → Systematic debugging

2. /profile function X
   → Check performance issues

3. /optimize function X
   → Tối ưu nếu cần

4. /test function X
   → Verify fix
```

**Ví dụ**:
```
/debug-python PyQt6 window not showing after button click
/profile MainWindow.show_dialog
/optimize MainWindow.show_dialog
/test MainWindow.show_dialog
```

---

### Kịch Bản 5: Đọc Hiểu Code Ngoại Ngôn Ngữ

**Mục tiêu**: Port code Java/C++ sang Python

**Quy trình**:
```
1. /analyze-code JavaFile.java
   → Phân tích Java code

2. /cross-lang JavaFile.java → Python
   → Map sang Python

3. /test Python equivalent
   → Test ported code

4. /review Python equivalent
   → Code review

5. /document Python equivalent
   → Documentation
```

**Ví dụ**:
```
/analyze-code D:\legacy\PerforceManager.java
/cross-lang PerforceManager.java → Python
/test PerforceManager
/review PerforceManager
/document PerforceManager
```

---

### Kịch Bản 6: Cải Tiện Code Legacy

**Mục tiêu**: Refactor và improve code cũ

**Quy trình**:
```
1. /analyze-code legacy_module.py
   → Phân tích code hiện tại

2. /review legacy_module.py
   → Identify issues

3. /refactor legacy_module.py
   → Refactor code

4. /test legacy_module.py
   → Verify behavior unchanged

5. /optimize legacy_module.py
   → Tối ưu performance

6. /document legacy_module.py
   → Update documentation
```

**Ví dụ**:
```
/analyze-code D:\p4_tool\legacy\old_processor.py
/review D:\p4_tool\legacy\old_processor.py
/refactor D:\p4_tool\legacy\old_processor.py
/test D:\p4_tool\legacy\old_processor.py
/optimize D:\p4_tool\legacy\old_processor.py
/document D:\p4_tool\legacy\old_processor.py
```

---

### Kịch Bản 7: Tích Hợp Multi-Language Components

**Mục tiêu**: Tích hợp Python với Java/C++ libraries

**Quy trình**:
```
1. /analyze-code C++Library.cpp
   → Phân tích C++ library

2. /cross-lang C++Library.cpp → Python bindings
   → Tạo Python bindings

3. /integrate C++ library with Python
   → Tích hợp components

4. /test integration
   → Test cross-language calls

5. /document integration
   → Document integration points
```

**Ví dụ**:
```
/analyze-code D:\p4_tool\cpp\p4api.cpp
/cross-lang p4api.cpp → Python bindings
/integrate p4api with PyQt6 interface
/test p4api integration
/document p4api integration
```

---

### Kịch Bản 8: Task Phức Tạp Đòi Hợp Nhiều Chuyên Gia

**Mục tiêu**: Sử dụng nhiều agents cho task lớn

**Quy trình**:
```
Use orchestrator agent to coordinate:
1. code-analyzer: Phân tích code hiện tại
2. python-architect: Thiết kế kiến trúc mới
3. tool-builder: Implement changes
4. test-engineer: Tạo tests
5. performance-tuner: Tối ưu performance
6. security-auditor: Review security
7. documentation-writer: Cập nhật docs
```

**Ví dụ**:
```
Use orchestrator agent to coordinate redesigning the entire PyQt6 interface with modern patterns
```

---

## Quy Trình Phát Triển Tool Đầy Đủ

### Phase 1: Discovery & Planning

```
1. /analyze-code project
   → Hiểu codebase hiện tại

2. /plan new feature or improvement
   → Lập kế hoạch chi tiết

3. Use explorer-agent to find relevant code
   → Tìm code cần thay đổi
```

### Phase 2: Design & Architecture

```
1. Use python-architect agent to design architecture
   → Thiết kế kiến trúc mới

2. /document architecture decisions
   → Document các quyết định

3. Populate memory bank with architecture
   → Lưu vào memory bank
```

### Phase 3: Implementation

```
1. /build-tool new component
   → Implement component mới

2. /test new component
   → Tạo và chạy tests

3. /debug-python if issues arise
   → Debug nếu có lỗi
```

### Phase 4: Quality Assurance

```
1. /review changes
   → Code review

2. /optimize if needed
   → Tối ưu performance

3. /test comprehensive
   → Full test suite
```

### Phase 5: Documentation & Deployment

```
1. /document changes
   → Cập nhật docs

2. /profile performance
   → Measure performance

3. Populate memory bank with lessons learned
   → Lưu bài học
```

---

## Tips và Best Practices

### 1. Khi Nào Dùng Workflow vs Agent

**Dùng Workflow khi**:
- Tác vụ có quy trình chuẩn hóa
- Cần step-by-step guidance
- Tác vụ phổ biến (analyze, build, test, debug)

**Dùng Agent khi**:
- Cần chuyên gia cụ thể
- Task phức tạp cần nhiều perspectives
- Cần deep expertise trong domain cụ thể

### 2. Sử Dụng Orchestrator

**Khi nào dùng orchestrator**:
- Task lớn, phức tạp
- Cần nhiều chuyên gia cùng làm việc
- Cần synthesis kết quả từ nhiều agents

**Ví dụ**:
```
Use orchestrator agent to coordinate:
- Redesigning entire architecture
- Building new feature from scratch
- Major refactoring project
```

### 3. Populate Memory Bank

**Khi nào populate**:
- Sau khi phân tích codebase mới
- Sau khi đưa ra quyết định kiến trúc
- Sau khi học được patterns mới
- Sau khi fix bugs quan trọng

**Cách populate**:
```markdown
## Project Context

### Project Information
- **Project Name**: p4_tool
- **Purpose**: PyQt6 tool for Perforce operations
- **Tech Stack**: Python, PyQt6, Perforce API
- **Key Dependencies**: PyQt6, P4Python

### Architecture Decisions
- Decision: Use MVC pattern for UI
- Rationale: Separation of concerns
- Trade-offs: More complex but more maintainable

### Code Patterns Used
- Pattern: Observer pattern for Perforce events
- When to use: When need to react to Perforce changes
- Example: See perforce_observer.py

### Known Issues
- Issue: Memory leak in large file operations
- Workaround: Process files in chunks
- Status: To be fixed in v2.0
```

### 4. Debugging Best Practices

**Luôn follow 4-phase methodology**:
1. Reproduce
2. Isolate
3. Analyze
4. Fix

**Sử dụng tools phù hợp**:
- pdb/ipdb cho step-by-step debugging
- Logging cho production debugging
- Profiling cho performance issues

### 5. Testing Best Practices

**Test pyramid**:
- 60% unit tests
- 30% integration tests
- 10% E2E tests

**Coverage target**:
- >80% code coverage
- Test edge cases
- Test error conditions

### 6. Performance Best Practices

**Profile trước khi optimize**:
- Đừng optimize dựa trên cảm tính
- Measure trước và sau
- Focus trên bottlenecks thực sự

**Caching strategies**:
- functools.lru_cache cho expensive functions
- Redis cho distributed caching
- Memoization cho pure functions

### 7. Security Best Practices

**Luôn validate input**:
- Never trust user input
- Sanitize data từ external sources
- Use parameterized queries

**Secrets management**:
- Never hardcode secrets
- Use environment variables
- Add .env to .gitignore

### 8. Documentation Best Practices

**Document as you code**:
- Viết docstrings cho public functions
- Cập nhật README khi thay đổi
- Document architecture decisions

**Use consistent style**:
- Google style hoặc NumPy style docstrings
- Markdown cho documentation
- Sphinx cho API docs

### 9. Code Review Best Practices

**Review checklist**:
- Functionality
- Code quality
- Security
- Performance
- Testing
- Documentation

**Provide constructive feedback**:
- Explain why change is needed
- Suggest improvements
- Be respectful

### 10. Multi-Language Best Practices

**Map concepts, not just syntax**:
- Hiểu paradigm differences
- Áp dụng idioms của target language
- Cân bằng giữa performance và readability

**Test integration points**:
- Test cross-language calls
- Verify data conversion
- Check error handling

---

## Ví Dụ Hoàn Chỉnh: Cải Tiến PyQt6 Interface

### Scenario
Bạn muốn cải tiến giao diện PyQt6 của tool p4_tool với modern UI patterns.

### Quy Trình Chi Tiết

#### Step 1: Phân Tích Hiện Tại
```
/analyze-code D:\Tools\CheckList\Bringup\Github\p4_tool
Use explorer-agent to find main UI components
Use code-archaeologist to understand current architecture
```

**Kết quả**: Báo cáo chi tiết về cấu trúc hiện tại

#### Step 2: Lập Kế Hoạch
```
/plan redesign PyQt6 interface with modern patterns
```

**Kết quả**: Kế hoạch chi tiết với:
- New architecture (MVC pattern)
- UI components cần refactor
- Timeline và milestones

#### Step 3: Thiết Kế Kiến Trúc
```
Use python-architect agent to design new PyQt6 architecture
```

**Kết quả**: Thiết kế kiến trúc mới với:
- Separation of concerns
- Design patterns (Observer, Strategy)
- Module structure

#### Step 4: Implement Changes
```
/build-tool modern PyQt6 interface components
```

**Agent sẽ tạo**:
- New UI components
- Refactored MainWindow
- Improved layouts
- Better signal/slot connections

#### Step 5: Debug Nếu Cần
```
/debug-python if new UI has issues
```

**Agent sẽ**:
- Reproduce issue
- Isolate problem
- Fix bug
- Test fix

#### Step 6: Tối Ưu Performance
```
/optimize PyQt6 interface performance
```

**Agent sẽ**:
- Profile UI rendering
- Identify bottlenecks
- Optimize (caching, lazy loading, etc.)
- Verify improvements

#### Step 7: Test
```
/test PyQt6 interface
```

**Agent sẽ tạo**:
- Unit tests cho components
- Integration tests cho UI
- E2E tests cho workflows
- Coverage report

#### Step 8: Code Review
```
/review PyQt6 interface changes
```

**Agent sẽ kiểm tra**:
- Functionality
- Code quality (PEP 8, type hints)
- Security
- Performance
- Testing

#### Step 9: Document
```
/document PyQt6 interface
```

**Agent sẽ tạo**:
- Updated README
- API documentation
- User guide
- Architecture documentation

#### Step 10: Populate Memory Bank
```
Edit .python-dev-kit/rules/memory-bank.md
```

**Thêm thông tin**:
- Architecture decisions
- Patterns used
- Lessons learned
- Known issues

---

## Kết Luận

Python Dev Kit cung cấp 12 workflows và 15 agents để hỗ trợ bạn trong mọi giai đoạn phát triển Python tools:

### Workflows cho Tác Vụ Phổ Biến
- `/analyze-code` - Phân tích code
- `/build-tool` - Xây dựng tool
- `/debug-python` - Debug lỗi
- `/optimize` - Tối ưu performance
- `/test` - Testing
- `/review` - Code review
- `/document` - Documentation
- `/profile` - Profiling
- `/refactor` - Refactoring
- `/cross-lang` - Multi-language mapping
- `/integrate` - Integration
- `/explain` - Giải thích logic flow

### Agents cho Chuyên Gia Cụ Thể
- `python-architect` - Thiết kế kiến trúc
- `code-analyzer` - Phân tích code
- `tool-builder` - Xây dựng tool
- `java-bridge` - Java → Python
- `cpp-bridge` - C++ → Python
- `performance-tuner` - Tối ưu performance
- `test-engineer` - Testing
- `debugger` - Debugging
- `documentation-writer` - Documentation
- `security-auditor` - Security
- `multi-language-analyst` - Multi-language
- `orchestrator` - Điều phối agents
- `project-planner` - Lập kế hoạch
- `code-archaeologist` - Legacy code
- `explorer-agent` - Khám phá codebase

### Quy Trình Phát Triển
1. **Discovery**: `/analyze-code`, `Use explorer-agent`
2. **Planning**: `/plan`, `Use python-architect`
3. **Implementation**: `/build-tool`, `/debug-python`
4. **Quality**: `/test`, `/review`, `/optimize`
5. **Documentation**: `/document`, `/explain`
6. **Integration**: `/integrate`, `/cross-lang`

### Best Practices
- Luôn populate memory bank
- Sử dụng workflows cho tác vụ phổ biến
- Sử dụng agents cho chuyên gia cụ thể
- Follow quy trình systematic
- Document decisions và lessons learned

Bộ kit này sẽ giúp bạn phát triển Python tools hiệu quả hơn, với quy trình có hệ thống và hỗ trợ từ các chuyên gia AI!
