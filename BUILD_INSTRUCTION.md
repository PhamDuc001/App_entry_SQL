# Build Instructions for TraceTool (.exe)

**Target Audience:** Developers & AI Agents
**Goal:** Build a standalone `TraceTool.exe` from the python source code.

## 1. Context & Prerequisites

### Project Structure
- **Entry Point:** `main_qt.py`
- **Configuration:** `TraceTool.spec` (PyInstaller specification)
- **Binary Dependencies:** `perfetto` (Python package + `trace_processor` binary)

### Requirements
- **OS:** Windows 10/11 (x64)
- **Python:** 3.10+
- **Environment:**
  - `pip install pyinstaller`
  - Ensure all project dependencies are installed (`pip install -r requirements.txt` if available, otherwise manual install).

### Quick Check
Run this command to verify PyInstaller is ready:
```powershell
pyinstaller --version
# Expected: >= 6.0.0
```

## 2. Configuration Setup (Critical Setup)

To build successfully, you **MUST** ensure the code handles resource paths correctly for frozen applications.

### 2.1. Resource Path Helper (`sql_query.py`)
Ensure this function exists to handle `_MEIPASS` pathing:
```python
def get_resource_path(relative_path):
    """
    Returns absolute path to resource, works for dev and for PyInstaller.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
```

### 2.2. Binary Path Configuration (`execution_sql.py` & `reaction_sql.py`)
The build process renames the binary folder to Avoid conflicts. Ensure code points to `perfetto_bin`:

```python
# MUST MATCH: 'perfetto_bin' folder defined in .spec file
TP_FILENAME = "trace_processor"
RELATIVE_BIN_PATH = os.path.join("perfetto", TP_FILENAME) 
TRACE_PROCESSOR_BIN = get_resource_path(RELATIVE_BIN_PATH)
```

## 3. The Spec File (`TraceTool.spec`)

**WARNING:** Do not use default `pyinstaller main_qt.py` command. You must use the provided spec file logic below to handle hidden imports and the elusive `trace_processor.descriptor`.

**Copy this content to `TraceTool.spec` if it is missing or incorrect:**

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import site
import os

# --- 1. ROBUST PERFETTO COLLECTION ---
# Collects proper package data including 'trace_processor.descriptor'
# Searches both system and user site-packages.
perfetto_datas = []
search_paths = site.getsitepackages()
if hasattr(site, 'getusersitepackages'):
    user_site = site.getusersitepackages()
    if isinstance(user_site, str):
        search_paths.append(user_site)
    elif isinstance(user_site, list):
        search_paths.extend(user_site)

for site_pkg in search_paths:
    perfetto_path = os.path.join(site_pkg, 'perfetto')
    if os.path.exists(perfetto_path):
        # Manual walk ensures we get ALL files including descriptors
        for root, dirs, files in os.walk(perfetto_path):
            for f in files:
                if '__pycache__' in root: continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, site_pkg) # e.g. perfetto/sub/file
                dest_dir = os.path.dirname(rel_path)
                perfetto_datas.append((full_path, dest_dir))
        break

# --- 2. PROJECT RESOURCES ---
added_datas = [
    ('ui/styles.qss', 'ui'),                      # GUI Styles
    ('perfetto/trace_processor', 'perfetto_bin'), # COPY BINARY TO 'perfetto_bin'
    ('prefix.html', '.'),
    ('suffix.html', '.'),
    ('systrace_trace_viewer.html', '.')
]
added_datas.extend(perfetto_datas)

# --- 3. HIDDEN IMPORTS ---
perfetto_hidden = collect_submodules('perfetto')

a = Analysis(
    ['main_qt.py'],
    pathex=[],
    binaries=[],
    datas=added_datas, 
    hiddenimports=[
        'execution_sql', 'reaction_sql', 'memory_main', 'pageboost_main',
        'sql_query', 'atracetosystrace', 'backup_query',
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'pandas', 'xlsxwriter', 'openpyxl',
        *perfetto_hidden,
        'multiprocessing', 'collections', 'pathlib'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TraceTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # KEEP TRUE FOR DEBUGGING
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TraceTool',
)
```

## 4. Build Procedure

Execute these commands in PowerShell from the project root:

```powershell
# 1. CLEANUP (Prevent cache issues)
Remove-Item -Recurse -Force dist/TraceTool -ErrorAction SilentlyContinue

# 2. BUILD
python -m PyInstaller --clean -y TraceTool.spec
```

## 5. Verification Checklist

After the build completes, an AI Agent should verify these paths exist:

1.  `dist/TraceTool/TraceTool.exe` (Executable)
2.  `dist/TraceTool/_internal/perfetto_bin/trace_processor` (Binary)
3.  `dist/TraceTool/_internal/perfetto/trace_processor/trace_processor.descriptor` (Descriptor)
4.  `dist/TraceTool/_internal/ui/styles.qss` (Styles)

## 6. Troubleshooting

-   **`ModuleNotFoundError: perfetto`**: The spec file didn't find the package. Check `search_paths` logic in spec file.
-   **`No such file or directory: ...trace_processor.descriptor`**: The manual walk in spec file failed. Verify `perfetto` package installation has this file.
-   **`ImportError` at runtime**: Run `TraceTool.exe` from a terminal to see the traceback. It often indicates a missing `hiddenimport`.