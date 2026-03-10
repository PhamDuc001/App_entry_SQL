---
description: Profile Python code performance
---

# Profile Workflow

## Overview
This workflow profiles Python code to identify performance bottlenecks and resource usage.

## Steps

### 1. Choose Profiling Tool
- CPU profiling: cProfile, py-spy
- Memory profiling: memory_profiler, objgraph
- Line-by-line: line_profiler

### 2. Run Profiler
- Execute profiling tool
- Collect performance data
- Generate reports

### 3. Analyze Results
- Identify hot spots
- Find memory leaks
- Analyze call graphs

### 4. Generate Report
- Create flame graphs
- Summarize findings
- Provide recommendations

## Usage
```
/profile CPU usage
/profile memory usage
/profile function X
```

## Output
- Performance profile report
- Flame graphs
- Bottleneck identification
- Optimization recommendations
