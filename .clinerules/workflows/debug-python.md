---
description: Debug Python code using systematic 4-phase methodology
---

# Debug Python Workflow

## Overview
This workflow uses a systematic 4-phase methodology to debug Python code and identify root causes.

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
