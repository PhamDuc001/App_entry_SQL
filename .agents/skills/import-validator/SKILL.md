---
name: import-validator
description: Validate that all function references have correct imports after refactoring. Detects missing imports, stale imports, and broken cross-module references before runtime testing.
---

# import-validator

After any refactoring (moving functions, splitting files, renaming), validate that all imports are correct and no references are broken.

## Usage

- After moving a function from one file to another
- After splitting a module into multiple files
- After renaming a function or class
- After adding a new module to a package
- Before committing refactoring changes

## Steps

### Step 1: Identify Changed Files

```
Use: git diff --name-only
List all files that were modified/added/deleted.
```

### Step 2: For Each Moved/Removed Function

For each function that was moved or removed:

1. Use `search_files` to find ALL references to the function name across the project
2. For each reference found, verify the file imports the function correctly:
   - Direct import: `from module import function_name` - check module is correct
   - Star import: `from package import *` - check package `__init__.py` exports the function
   - Same-module call: no import needed if caller is in the same file

### Step 3: Validate Package __init__.py

For each package that uses `from package import *`:

1. Read `package/__init__.py`
2. Verify it has `from new_module import *` for the new file
3. Verify it does NOT still import from the old location (if function was moved)

### Step 4: Validate PyInstaller hiddenimports

If the project uses PyInstaller (check for `.spec` file):

1. Read the `.spec` file
2. Verify all new modules are listed in `hiddenimports`
3. Verify removed modules are not still listed

### Step 5: Runtime Import Test

Run a quick Python import test to catch errors that static analysis misses:

```bash
python -c "from package import *; print('OK')"
python -c "from package.module import function_name; print('OK')"
```

IMPORTANT: `python -c "import module"` only verifies the module loads. It does NOT verify that all names are resolvable at runtime. Use the specific function import test above.

### Step 6: Report Findings

Output a validation report:

```
IMPORT VALIDATION REPORT
========================
Moved functions:
  - function_a: old_module -> new_module
  - function_b: old_module -> new_module

Import status:
  [OK] sql_query/analysis.py - imports function_a from trace_queries
  [OK] sql_query/__init__.py - exports function_a from trace_queries
  [MISSING] some_file.py - uses function_a but has no import
  [STALE] other_file.py - still imports function_a from old_module

PyInstaller:
  [OK] TraceTool.spec - includes sql_query.trace_queries

Runtime test:
  [OK] from sql_query import * - passed
  [OK] from sql_query.trace_queries import function_a - passed
```

## Common Patterns in This Project

### sql_query package
- Uses `from sql_query import *` in analysis.py
- `__init__.py` re-exports from all sub-modules
- When adding a new sub-module, MUST add `from sql_query.new_module import *` to `__init__.py`

### execution package
- Uses `from execution.config import *` in excel_output.py, excel_sheet.py
- Uses `from execution.excel_sheet import create_sheet` in excel_output.py

### reaction package
- Uses `from sql_query import *` in analyzer.py (cross-package dependency)
- Uses `from reaction.main import run_analysis` in `__init__.py`

## Red Flags

- Function defined in file A but only importable via file B's `__init__.py` -> Will fail at runtime if `__init__.py` doesn't re-export
- `from module import *` with no `__all__` -> May silently miss exports
- Private functions (starting with `_`) moved to new file -> Need explicit `__all__` or direct import