# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all
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
                if '__pycache__' in root: 
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, site_pkg) # e.g. perfetto/sub/file
                dest_dir = os.path.dirname(rel_path)
                perfetto_datas.append((full_path, dest_dir))
        break

# --- 2. PROJECT RESOURCES ---
added_datas = [
    ('ui/styles.qss', 'ui'),                      # GUI Styles
    ('perfetto/trace_processor', 'perfetto_bin'), # COPY BINARY TO 'perfetto_bin' to avoid conflict
    ('prefix.html', '.'),
    ('suffix.html', '.'),
    ('systrace_trace_viewer.html', '.')
]

added_datas.extend(perfetto_datas)

# --- 3. HIDDEN IMPORTS ---
perfetto_hidden = collect_submodules('perfetto')

# Collect all encodings modules to fix "No module named 'encodings'" error
encodings_datas, encodings_binaries, encodings_hiddenimports = collect_all('encodings')

a = Analysis(
    ['main_qt.py'],
    pathex=[],
    binaries=encodings_binaries,
    datas=added_datas + encodings_datas,  
    hiddenimports=[
    'execution_sql', 'reaction_sql', 'memory_main', 'pageboost_main',
    'sql_query', 'atracetosystrace', 'backup_query',
    # MemoryStatus modules
    'MemoryStatus', 'MemoryStatus.memory_main', 'MemoryStatus.abnormal_memory',
    'MemoryStatus.app_start_kill_analyzer', 'MemoryStatus.analyze_pss',
    'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
    'pandas', 'xlsxwriter', 'openpyxl',
    *perfetto_hidden,
    *encodings_hiddenimports,
    'multiprocessing', 'collections', 'pathlib',
    # Critical Python standard library modules
    'codecs', 'io', 'os', 'sys', 'importlib', 'importlib.abc',
    'importlib.util', 'importlib.machinery', 'zipimport',
    # Additional essential modules
    'typing', 'datetime', 'json', 'csv', 're', 'math', 'random',
    'string', 'collections.abc', 'itertools', 'functools', 'operator',
    'dataclasses', 'zipfile'
],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
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
