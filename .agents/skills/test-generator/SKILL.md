---
name: test-generator
description: Generate unit test stubs for Python functions to enable quick verification after refactoring without running the full pipeline.
---

# test-generator

Generate lightweight unit test stubs that can be run quickly to verify function behavior after refactoring.

## Usage

- After refactoring to verify functions still work correctly
- When full pipeline test takes too long (>60 seconds)
- When you need to test a specific function in isolation
- When adding a new function that should be tested

## Steps

### Step 1: Identify Functions to Test

Focus on functions that:
1. Were moved during refactoring
2. Have cross-module dependencies
3. Are called by multiple callers
4. Have complex logic (not simple getters)

Skip:
- Simple utility functions (to_ms, get_resource_path)
- Functions that only call other functions (thin wrappers)

### Step 2: Generate Test File

Create `tests/test_<module>.py` with this structure:

```python
"""
Quick verification tests for <module>.
Run: python -m pytest tests/test_<module>.py -v
Or:  python tests/test_<module>.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Verify all functions are importable."""
    from sql_query.trace_queries import (
        detect_app_from_launch,
        find_app_process,
        get_choreographer,
        get_animating,
        # ... list all public functions
    )
    print(f"  [OK] All {N} functions imported successfully from trace_queries")

def test_function_signatures():
    """Verify function signatures haven't changed."""
    import inspect
    from sql_query.trace_queries import get_choreographer
    
    sig = inspect.signature(get_choreographer)
    params = list(sig.parameters.keys())
    assert 'tp' in params, "get_choreographer missing 'tp' parameter"
    assert 'tid' in params, "get_choreographer missing 'tid' parameter"
    assert 'min_ts' in params, "get_choreographer missing 'min_ts' parameter"
    print("  [OK] Function signatures verified")

def test_return_types():
    """Verify return types with mock data."""
    # For functions that don't need TraceProcessor:
    from sql_query.base import to_ms
    
    assert to_ms(None) == 0.0
    assert to_ms(1_000_000) == 1.0
    assert to_ms(0) == 0.0
    print("  [OK] Return types verified for to_ms")

if __name__ == "__main__":
    print("Running quick verification tests...")
    test_imports()
    test_function_signatures()
    test_return_types()
    print("\nAll tests passed!")
```

### Step 3: Test Categories

#### Category 1: Import Tests (ALWAYS generate)
Fastest test. Verifies all functions are importable from their new locations.

```python
def test_imports():
    from sql_query.trace_queries import detect_app_from_launch
    from sql_query.loadapk_asset import get_camera_hal_pid
    from sql_query.sequence_queries import get_layout_depth_slices
    # Each import tests that __init__.py and direct imports work
```

#### Category 2: Signature Tests (Generate for moved functions)
Verifies function parameters haven't changed.

```python
def test_signatures():
    import inspect
    from sql_query.trace_queries import get_choreographer
    sig = inspect.signature(get_choreographer)
    assert 'tp' in sig.parameters
    assert 'tid' in sig.parameters
```

#### Category 3: Logic Tests (Generate for utility functions)
Tests pure functions that don't need external dependencies.

```python
def test_to_ms():
    from sql_query.base import to_ms
    assert to_ms(None) == 0.0
    assert to_ms(1_000_000) == 1.0
    assert to_ms(500_000) == 0.5

def test_process_block_io_data():
    from sql_query.block_io import process_block_io_data
    assert process_block_io_data(None) == []
    assert process_block_io_data(pd.DataFrame()) == []
```

#### Category 4: Integration Smoke Tests (Generate for critical paths)
Quick end-to-end test using real trace files if available.

```python
def test_execution_smoke():
    """Quick smoke test - runs analysis on 1 trace file."""
    from execution_sql import run_analysis
    # Use smallest available test folder
    dut = r"D:\Log PLM\VOC\test\A266B\6GB_P251218-06591\A266BZA5_BOS_6GB_260122_log"
    ref = r"D:\Log PLM\VOC\test\A266B\6GB_P251218-06591\A266BYH3_BOS_6GB_80_250821_LOG"
    # Delete cache first!
    for folder in [dut, ref]:
        cache = os.path.join(folder, ".perf_cache.pkl")
        if os.path.exists(cache):
            os.remove(cache)
    run_analysis(dut, ref, target_apps=["clock"])
```

### Step 4: Run Tests

```bash
# Quick import verification (< 5 seconds)
python -c "from sql_query.trace_queries import *; print('OK')"

# Full test file
python tests/test_trace_queries.py

# With pytest
python -m pytest tests/ -v
```

## Test File Naming Convention

```
tests/
  test_sql_query_base.py
  test_sql_query_trace_queries.py
  test_sql_query_sequence_queries.py
  test_sql_query_block_io.py
  test_sql_query_cpu_queries.py
  test_sql_query_loadapk_asset.py
  test_execution_processor.py
  test_execution_excel_sheet.py
  test_integration.py          # Smoke tests with real data
```

## Important Notes

- This project has NO existing test suite. Start with import tests only.
- Most functions require TraceProcessor (Perfetto) which needs real trace files.
- Focus on what CAN be tested without trace files: imports, signatures, pure functions.
- For full verification, use the integration smoke test with debug_execution.py.
- Always delete `.perf_cache.pkl` before running integration tests.