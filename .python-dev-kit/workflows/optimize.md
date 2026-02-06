---
description: Optimize Python code performance
---

# Optimize Workflow

## Overview
This workflow profiles and optimizes Python code for better performance.

## Clarifying Questions

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

## Interactive Planning Process

```
Step 1: User đưa ra request tối ưu
    ↓
Step 2: Agent hỏi clarifying questions (4 câu hỏi)
    ↓
Step 3: User trả lời các câu hỏi
    ↓
Step 4: Agent validates thông tin
    ↓
Step 5: Nếu chưa đủ, hỏi thêm
    ↓
Step 6: Khi đủ thông tin, bắt đầu profiling
    ↓
Step 7: Profile code
    ↓
Step 8: Analyze results
    ↓
Step 9: Optimize strategically
    ↓
Step 10: Verify improvements
```

## Steps

### 1. Profile First
- Measure before optimizing
- Identify actual bottlenecks
- Use appropriate profiling tools (cProfile, py-spy, memory_profiler)

### 2. Analyze Results
- Find hot spots
- Identify inefficient patterns
- Understand resource usage

### 3. Optimize Strategically
- Focus on bottlenecks
- Choose right optimization technique:
  - Algorithm optimization
  - Data structure selection
  - Caching strategies
  - Concurrency patterns
  - I/O optimization

### 4. Verify Improvements
- Profile after changes
- Measure performance gain
- Ensure correctness

## Usage
```
/optimize slow function
/optimize database queries
/optimize memory usage
```

## Output
- Performance analysis report
- Optimized code
- Before/after comparison
- Performance metrics
