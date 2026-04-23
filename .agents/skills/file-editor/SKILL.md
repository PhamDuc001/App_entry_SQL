---
name: file-editor
description: PyNeat Code Cleaner and Security Scanner - Automatically clean, refactor, and secure Python code with AI-powered analysis
---

# file-editor

Enhanced file editing that handles Unicode issues and provides safer editing workflow for this project.

## Usage

- When `replace_in_file` fails due to Unicode matching issues
- When editing files containing Vietnamese comments
- When making multiple changes to the same file
- When editing large files where only small sections change

## The Unicode Problem

This project contains Vietnamese comments (Unicode characters like a, o, u, e, d).
The `replace_in_file` tool requires EXACT character matching, which fails when:
1. The SEARCH block contains Unicode that doesn't match the file encoding
2. Line endings differ (CRLF vs LF)
3. Invisible characters (BOM, zero-width spaces) exist

## Decision Tree: Which Tool to Use

```
Need to edit a file?
|
+-- Small change (< 10 lines, ASCII only)?
|   +-- YES -> Use replace_in_file
|   +-- NO -> Continue below
|
+-- File contains Vietnamese/Unicode comments?
|   +-- YES -> Use write_to_file (rewrite entire file)
|   +-- NO -> Use replace_in_file with precise SEARCH blocks
|
+-- Multiple changes to same file?
|   +-- YES -> Use write_to_file (avoid multiple replace_in_file calls)
|   +-- NO -> Use replace_in_file
|
+-- replace_in_file failed 2+ times?
    +-- YES -> Switch to write_to_file immediately
    +-- NO -> Try one more time with shorter SEARCH block
```

## Rules for replace_in_file

### Rule 1: Keep SEARCH blocks SHORT
Use the MINIMUM lines needed for unique matching. Do NOT include long unchanged sections.

BAD:
```
------- SEARCH
def get_camera_hal_pid(tp: TraceProcessor) -> Optional[int]:
    """
    Tim PID cua tien trinh Camera HAL dua tren slice dac trung.
    """
    sql = """
    SELECT pid
    FROM slice_with_names
    WHERE name LIKE '%camera3->process_capture_request%'
    LIMIT 1;
    """
    df = query_df(tp, sql)
    if df is not None and not df.empty:
        return int(df.iloc[0]['pid'])
    return None

def get_hal_library_block_io
=======
+++++++ REPLACE
```

GOOD:
```
------- SEARCH
def get_camera_hal_pid(tp: TraceProcessor) -> Optional[int]:
=======
+++++++ REPLACE
```

### Rule 2: Avoid Unicode in SEARCH blocks
If the file has Vietnamese comments, use only the function signature (ASCII) in SEARCH.

### Rule 3: After 2 failures, switch to write_to_file
Do NOT keep retrying replace_in_file. It wastes time and context.

### Rule 4: For new files, always use write_to_file
No matching needed, so no Unicode issues.

## Workflow for Large Refactoring

When making many changes to a file:

1. Read the entire file first
2. Make ALL changes in a single `write_to_file` call
3. This avoids the cascading failure problem where one failed replace_in_file blocks subsequent edits

## Post-Edit Verification

After editing, always verify:

```bash
# Quick syntax check
python -c "import ast; ast.parse(open('file.py', encoding='utf-8').read()); print('Syntax OK')"

# Import check
python -c "from module import function; print('Import OK')"
```

## File Encoding Rules

- All Python files in this project use UTF-8 encoding
- When writing files with `write_to_file`, use ASCII-safe comments when possible
- If Vietnamese comments must be preserved, they will be handled correctly by write_to_file
- NEVER add BOM (Byte Order Mark) to files