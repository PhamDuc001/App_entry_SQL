---
description: Analyze Python/Java/C++ code and generate comprehensive report
---

# Code Analysis Workflow

## Overview
This workflow analyzes code in Python, Java, or C++ and generates a comprehensive report including architecture, patterns, and recommendations.

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
