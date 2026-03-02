#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
execution_sql_batch.py

Xử lý batch traces từ 2 folders (DUT & REF), phân loại entry/re-entry,
và xuất 2 file Excel với multiple cycles.

Usage:
    python execution_sql_batch.py <dut_folder> <ref_folder>
"""

import os
import sys

# CRITICAL: Set environment variables TRƯỚC KHI import bất cứ thứ gì
# Đây là fix quan trọng nhất cho NumPy CPU dispatcher error
os.environ['NUMPY_EXPERIMENTAL_ARRAY_FUNCTION'] = '0'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMPY_DISABLE_CPU_FEATURES'] = 'AVX2'

# Force numpy initialization early to prevent conflicts
try:
    import numpy.core.multiarray
    numpy.core.multiarray._initialize()
except ImportError:
    pass
except Exception:
    pass

import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List
from collections import defaultdict

import xlsxwriter
import json

import pickle
import traceback

from perfetto.trace_processor.api import TraceProcessor, TraceProcessorConfig
from sql_query import *
from atracetosystrace import convert_trace
from multiprocessing import Pool, cpu_count
from dumpstate_parser import (
    build_trace_bugreport_mapping,
    collect_bugreport_mappings, 
    get_bugreport_for_log, 
    get_app_group,
    get_bugreport_group_from_name,
    # New imports for extended profiling table
    parse_uptime,
    parse_pss_for_app,
    parse_pageboostd_for_app,
    parse_start_reasons,
    parse_kill_reasons,
    parse_compiler_type,
    count_crashes,
    get_memory_data_for_cycle,
    find_dumpstate_content
)

# ---------------------------------------------------------------------------
# Configuration 
# ---------------------------------------------------------------------------
# TRACE_PROCESSOR_BIN = r"D:\Tools\CheckList\Bringup\Plan_convert_SQL\perfetto\trace_processor"
# TP_FILENAME = "trace_processor" if sys.platform == "win32" else "trace_processor.exe"
if sys.platform == "win32":
    try:
        TP_FILENAME = "trace_processor"
    except (FileNotFoundError, OSError, Exception):
        TP_FILENAME = "trace_processor.exe"
else:
    TP_FILENAME = "trace_processor.exe"

# Local
# RELATIVE_BIN_PATH = os.path.join("perfetto", TP_FILENAME)
# Build
RELATIVE_BIN_PATH = os.path.join("perfetto_bin", TP_FILENAME)
#===============================================================
TRACE_PROCESSOR_BIN = get_resource_path(RELATIVE_BIN_PATH)

APP_MAPPING = {
    "comsamsungperformancehelloworld_v6": "Helloworld",
    "comsamsungandroiddialer": "Dial",
    "comsecandroidappclockpackage": "Clock",
    "comsecandroidappcamera": "Camera",
    "comsamsungandroidappcontacts": "Contacts",
    "comsamsungandroidcalendar": "Calendar",
    "comsecandroidapppopupcalculator": "Calculator",
    "com.sec.android.gallery3d": "Gallery",
    "comsamsungandroidmessaging": "Messages",
    "comsec.androidappmyfiles": "MyFiles",
    "comexampleedittexttest3": "SIP",
    "comsecandroidappsbrowser": "Internet",
    "comsamsungandroidappnotes": "Notes",
    "comandroidsettings": "Settings",
    "comsecandroidappvoicenote": "VoiceNote",
    "comgoogleandroidappsmessaging": "Messages",
}

TARGET_APPS = [
    "camera",      # sẽ match cả "camera"
    "hello",       # sẽ match cả "hello", "helloworld"  
    "call",        # sẽ match cả "calllog"
    "clock",
    "contact",
    "calendar",
    "calender",
    "calculator",
    "gallery",
    "message",
    "menu",
    "myfile",      # sẽ match cả "myfile", "myfiles"
    "internet",
    "note",        # sẽ match cả "note", "notes"
    "setting",
    "voice",       # sẽ match cả "voice", "voicerecorder"
    "recent"
]


COLD_ONLY_KEYS = {
    "Touch Down ~ Start Proc",
    "Start Proc",
    "Start Proc ~ ActivityThreadMain",
    "Activity Thread Main",
    "ActivityThreadMain ~ bindApplication",
    "Bind Application",
    "bindApplication ~ activityStart"
}

WARM_ONLY_KEYS = {
    "Touch Duration",
    "Touch Up ~ Activity Start"
}

# App name normalization map - fix common typos/misspellings
APP_NAME_NORMALIZATION = {
    "calender": "calendar",  # Fix "calender" → "calendar"
    "recorder": "voice"
}

CACHE_VERSION = "1.0"  # Tăng lên "1.1", "2.0"... 

# ---------------------------------------------------------------------------
# Helper functions and analyze_trace 
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Batch Processing Logic
# ---------------------------------------------------------------------------

# skip_apps = ['sip', 'menu', 'dial']

def collect_trace_files(folder_path: str) -> List[str]:
    """
    Collect file .log trong folder, đã sort theo tên (A-Z).
    
    Returns:
        List[str]: All file .log
    """
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Folder không tồn tại: {folder_path}")
    
    log_files = sorted([str(f) for f in folder.glob("*.log")])
    return log_files

def group_traces_by_app(trace_files: List[str], target_apps: List[str] = None) -> Dict[str, List[Tuple[str, int]]]:
    if target_apps is None:
        target_apps = TARGET_APPS
        
    app_groups = defaultdict(list)
    app_occurrence_count = defaultdict(int)
    
    print(f"Target Apps Filter: {target_apps}")
    
    for file_path in trace_files:
        filename = Path(file_path).stem
        parts = filename.split('_')
        
        if len(parts) >= 2:
            raw_app_name = parts[-1]
            app_name = raw_app_name.lower()
            
            # [FIX STEP 1] Normalize app name (fix typos like "calender" → "calendar")
            if app_name in APP_NAME_NORMALIZATION:
                original_name = app_name
                app_name = APP_NAME_NORMALIZATION[app_name]
                print(f"  [NORMALIZED] '{original_name}' → '{app_name}'")
            
            # NEW: Check if app_name contains any target keyword
            matched_keyword = None
            for keyword in target_apps:
                if keyword in app_name:
                    matched_keyword = keyword
                    break
            
            if matched_keyword is None:
                continue
                
            # Use the matched keyword as the standardized app name
            standardized_name = matched_keyword
        else:
            continue
            
        app_occurrence_count[standardized_name] += 1
        occurrence = app_occurrence_count[standardized_name]
        app_groups[standardized_name].append((file_path, occurrence))
        
    return dict(app_groups)


# ---------------------------------------------------------------------------
# Batch Processing Logic với Multiprocessing
# ---------------------------------------------------------------------------

# Global variable để lưu bugreport mappings cho multiprocessing
_BUGREPORT_MAPPINGS = {}
_ALL_FILES_SORTED = []


def _process_single_trace_worker(args):
    # Unpack thêm folder_path (cần truyền vào từ process_all_traces)
    file_path, occurrence, app_name, pid_mapping, mapping_info, folder_path = args 
    filename = Path(file_path).stem
    config = TraceProcessorConfig(bin_path=TRACE_PROCESSOR_BIN)
    
    try:
        with TraceProcessor(trace=convert_trace(file_path), config=config) as tp:
            metrics = analyze_trace(tp, file_path, pid_mapping)
            category = 'entry' if occurrence % 2 == 1 else 'reentry'
            
            # ========================================================
            # [TỐI ƯU MỚI] PARSE DUMPSTATE & MEMORY NGAY TẠI WORKER
            # ========================================================
            cycle_idx = (occurrence - 1) // 2
            extend_data = {}
            
            # 1. Đọc Memory Data
            if folder_path:
                mem_data = get_memory_data_for_cycle(folder_path, app_name, cycle_idx)
                if mem_data:
                    extend_data['MemFree'] = mem_data.get('MemFree', 0)
                    extend_data['MemAvailable'] = mem_data.get('MemAvailable', 0)
            
            # 2. Đọc Dumpstate (PSS, Pageboost, Uptime, Start/Kill, Crash, Compiler)
            bugreport_path = mapping_info.get('bugreport_path', '') if mapping_info else ''
            if bugreport_path:
                dumpstate_content = find_dumpstate_content(bugreport_path)
                if dumpstate_content:
                    extend_data['App_PSS'] = parse_pss_for_app(dumpstate_content, app_name)
                    extend_data['Pageboostd'] = parse_pageboostd_for_app(dumpstate_content, app_name)
                    extend_data['Uptime'] = parse_uptime(dumpstate_content)
                    extend_data['Start_Reason'] = parse_start_reasons(dumpstate_content, app_name)
                    extend_data['Kill_Reason'] = parse_kill_reasons(dumpstate_content, app_name)
                    extend_data['Crash_Count'] = count_crashes(dumpstate_content)
                    extend_data['Compiler'] = parse_compiler_type(dumpstate_content, app_name)
            
            # Gắn data đã parse sẵn vào metrics để lưu Cache
            metrics['Precomputed_Extend_Data'] = extend_data
            # ========================================================
            
            return (app_name, occurrence, category, metrics, filename)
    except Exception as e:
        print(f"    [ERROR] {Path(file_path).name}: {e}")
        return (app_name, occurrence, 'entry' if occurrence % 2 == 1 else 'reentry', None, filename)


def process_single_trace(args: Tuple[str, int, str], pid_mapping: Dict[int, str] = None) -> Tuple[str, int, str, Optional[Dict[str, Any]], str]:
    """
    Xử lý một trace file duy nhất.
    
    Args:
        args: (file_path, occurrence, app_name)
        pid_mapping: Optional dict {PID: process_name} from dumpstate
    
    Returns:
        (app_name, occurrence, category, metrics, filename) hoặc (app_name, occurrence, category, None, filename) nếu lỗi
    """
    file_path, occurrence, app_name = args
    filename = Path(file_path).stem
    config = TraceProcessorConfig(bin_path=TRACE_PROCESSOR_BIN)
    
    try:
        with TraceProcessor(trace=convert_trace(file_path), config=config) as tp:
            metrics = analyze_trace(tp, file_path, pid_mapping)
            category = 'entry' if occurrence % 2 == 1 else 'reentry'
            return (app_name, occurrence, category, metrics, filename)
    except Exception as e:
        print(f"    [ERROR] {Path(file_path).name}: {e}")
        return (app_name, occurrence, 'entry' if occurrence % 2 == 1 else 'reentry', None, filename)



# [File: execution_sql.py] -> function process_all_traces

def process_all_traces(folder_path: str, label: str, num_workers: int = 8, 
                       target_apps: List[str] = None, extracted: bool = False) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Xử lý tất cả traces.
    [UPDATED] Fix lỗi dồn cycle khi có trace bị lỗi (giữ nguyên None trong list kết quả).
    """
    trace_files = collect_trace_files(folder_path)
    app_groups = group_traces_by_app(trace_files, target_apps)
    
    # Build mapping using sorted filename approach
    print(f"\n[{label}] Building trace-bugreport mapping (extracted={extracted})...")
    trace_mapping = build_trace_bugreport_mapping(folder_path, extracted)
    
    valid_count = sum(1 for m in trace_mapping.values() if m and m.get('bugreport_path'))
    print(f"[{label}] Mapped {valid_count}/{len(trace_mapping)} traces to bugreports")
    
    tasks = []
    for app_name, file_list in app_groups.items():
        for file_path, occurrence in file_list:
            mapping_info = trace_mapping.get(file_path, {})
            pid_mapping = mapping_info.get('pid_mapping', {}) if mapping_info else {}
            if not pid_mapping: pid_mapping = None
            
            # [CẬP NHẬT] Thêm folder_path vào cuối
            tasks.append((file_path, occurrence, app_name, pid_mapping, mapping_info, folder_path))
    
    print(f"[{label}] Processing {len(tasks)} trace files with {num_workers} workers...")
    
    # Khởi tạo list với dung lượng dư thừa để tránh index error
    results = defaultdict(lambda: {'entry': [], 'reentry': []})
    task_mapping_info = {t[0]: t[4] for t in tasks}
    
    pool = Pool(processes=num_workers)
    try:
        for i, (app_name, occurrence, category, metrics, filename) in enumerate(pool.imap(_process_single_trace_worker, tasks)):
            
            # [FIX 1] Luôn tính toán cycle index, kể cả khi metrics là None (lỗi)
            # Logic: Trace 1,2 -> Cycle 0; Trace 3,4 -> Cycle 1
            cycle_index = (occurrence - 1) // 2
            
            # Mở rộng list nếu cần thiết để đảm bảo index tồn tại
            target_list = results[app_name][category]
            while len(target_list) <= cycle_index:
                target_list.append(None)
            
            if metrics:
                # Nếu có data, bổ sung thông tin trace file
                trace_file = None
                for task in tasks:
                    if Path(task[0]).stem == filename:
                        trace_file = task[0]
                        break
                
                if trace_file:
                    metrics['trace_file'] = trace_file
                    metrics['trace_mapping'] = task_mapping_info.get(trace_file, {})
                
                print(f"  - [{i+1}/{len(tasks)}] {app_name} - {category} - cycle {cycle_index + 1} - OK")
                results[app_name][category][cycle_index] = metrics
            else:
                # Nếu metrics None (lỗi), giữ nguyên giá trị None tại index đó
                print(f"  - [{i+1}/{len(tasks)}] {app_name} - {category} - cycle {cycle_index + 1} - FAILED/EMPTY")
                results[app_name][category][cycle_index] = None

    finally:
        pool.close() 
        pool.join()  
    
    # [FIX 2] KHÔNG lọc bỏ None. Giữ nguyên cấu trúc [Data, None, Data] để Excel vẽ đúng cột.
    cleaned_results = {}
    for app_name, categories in results.items():
        cleaned_results[app_name] = {
            'entry': categories['entry'], # Giữ nguyên list gốc
            'reentry': categories['reentry']
        }
    
    return cleaned_results



# ---------------------------------------------------------------------------
# Excel Creation - Helper Functions
# ---------------------------------------------------------------------------

def select_common_end_ts_type(dut_metrics: Dict[str, Any], ref_metrics: Dict[str, Any]) -> Optional[str]:
    """
    Chọn end_ts type mà CẢ DUT và REF đều có.
    Ưu tiên: Chọn type có giá trị LỚN NHẤT (execution time dài nhất).
    
    Args:
        dut_metrics: Metrics từ DUT cycle
        ref_metrics: Metrics từ REF cycle
        
    Returns:
        Common end_ts type name hoặc None nếu không có common type
    """
    dut_variants = dut_metrics.get("end_ts_variants", {})
    ref_variants = ref_metrics.get("end_ts_variants", {})
    
    # Tìm các types mà CẢ HAI đều có (value > 0)
    dut_types = {k for k, v in dut_variants.items() if v and v > 0}
    ref_types = {k for k, v in ref_variants.items() if v and v > 0}
    common_types = dut_types & ref_types
    
    if not common_types:
        return None
    
    # Chọn type có giá trị LỚN NHẤT (average của DUT và REF)
    best_type = None
    best_value = 0
    
    for etype in common_types:
        avg_value = (dut_variants.get(etype, 0) + ref_variants.get(etype, 0)) / 2
        if avg_value > best_value:
            best_value = avg_value
            best_type = etype
    
    return best_type


def get_metrics_for_end_ts_type(metrics: Dict[str, Any], end_ts_type: str) -> Dict[str, Any]:
    """
    Lấy data tương ứng với end_ts_type từ metrics.
    Nếu không có data_by_end_ts, fallback về metrics root.
    
    Args:
        metrics: Full metrics dict từ analyze_trace
        end_ts_type: Type cần lấy ("activityIdle", "animating", "startPreviewRequest")
        
    Returns:
        Dict chứa data cho end_ts_type đó, hoặc metrics root nếu không có
    """
    data_by_end_ts = metrics.get("data_by_end_ts", {})
    
    if end_ts_type and end_ts_type in data_by_end_ts:
        # Merge: base metrics + data từ end_ts_type
        result = metrics.copy()
        type_data = data_by_end_ts[end_ts_type]
        
        # Override các fields phụ thuộc end_ts
        for key in ["Running", "Runnable", "Uninterruptible Sleep", "Sleeping",
                    "Block_IO_Data", "LoadApkAsset_Data", "CPU_Process_Data",
                    "CPU_Thread_Data", "Binder_Transaction_Data",
                    "Abnormal_Process_Data", "Background_Process_States", "App Execution Time"]:
            if key in type_data:
                result[key] = type_data[key]
        
        return result
    
    # Fallback: return metrics as-is (backward compatible)
    return metrics


# ---------------------------------------------------------------------------
# Excel Creation
# ---------------------------------------------------------------------------

def create_excel_output(
    dut_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ref_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    output_folder: str,
    header_title: str,
    dut_device_code: str,
    ref_device_code: str,
    dut_folder_path: str = "",
    ref_folder_path: str = ""
) -> None:
    """
    Tạo 2 file Excel: execution_entry.xlsx và execution_reentry.xlsx.
    
    Mỗi file chứa nhiều sheets theo app name.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Tạo 2 files
    for launch_type in ['entry', 'reentry']:
        output_path = os.path.join(
            output_folder,
            f"execution_{launch_type}_{timestamp}.xlsx"
        )
        
        wb = xlsxwriter.Workbook(output_path)
        
        # Lấy danh sách tất cả apps từ cả DUT và REF
        all_apps = set(dut_results.keys()) | set(ref_results.keys())
        
        for app_name in sorted(all_apps):
            sheet_name = APP_MAPPING.get(
                f"com.sec.android.{app_name}",
                app_name.capitalize()
            )
            
            dut_cycles = dut_results.get(app_name, {}).get(launch_type, [])
            ref_cycles = ref_results.get(app_name, {}).get(launch_type, [])
            
            if not dut_cycles and not ref_cycles:
                continue
            
            create_sheet(
                wb, 
                sheet_name, 
                dut_cycles, 
                ref_cycles, 
                header_title,
                launch_type,
                app_name,
                dut_device_code,
                ref_device_code,
                dut_folder_path,
                ref_folder_path
            )
        
        wb.close()
        print(f"\n Created: {output_path}")


def write_value_or_empty(ws, row, col, value, fmt):
    """
    Ghi giá trị vào Excel, nếu là 0.0 thì để trống
    """
    if value == 0.0:
        ws.write(row, col, "", fmt)
    else:
        ws.write(row, col, value, fmt)

def get_filtered_metric_rows(launch_type: str, app_name: str, has_cold: bool, has_warm: bool) -> List[Tuple[str, str]]:
    """
    Trả về danh sách các hàng metric cần hiển thị.
    - Kết hợp logic lọc Cold/Warm.
    - Kết hợp logic riêng cho Camera app.
    """
    prefix = "1st" if launch_type == "entry" else "2nd"
    if prefix == "1st":
        launch_type = "Enter Execution"
    elif prefix == "2nd":
        launch_type = "Enter Execution"
    else:
        launch_type = "Enter Execution"

    # Capitalize app name first letter
    app_display = app_name.capitalize()
    execution_label = f"{prefix} {launch_type} ({app_display})"
    
    # Kiểm tra xem đây có phải là Camera không (dựa trên tên app)
    is_camera = "camera" in app_name.lower()
    
    # 1. Base Metrics (Luôn hiển thị)
    rows = [
        (execution_label, "App Execution Time"),
        # Lưu ý: Đã bỏ hàng "Launch Type" theo yêu cầu
        ("", ""),
    ]

    # 2. Cold Only Block (Chỉ hiện nếu có ít nhất 1 cycle Cold)
    if has_cold:
        rows.extend([
            ("Touch Down ~ Start Proc", "Touch Down ~ Start Proc"),
            ("Start Proc", "Start Proc"),
            ("    ~", "Start Proc ~ ActivityThreadMain"),
            ("ActivityThreadMain", "Activity Thread Main"),
            ("    ~", "ActivityThreadMain ~ bindApplication"),
            ("BindApplication", "Bind Application"),
            ("    ~", "bindApplication ~ activityStart"),
        ])

    # 3. Warm Only Block (Chỉ hiện nếu có ít nhất 1 cycle Warm)
    if has_warm:
        rows.extend([
            ("Touch Duration", "Touch Duration"),
            ("Touch Up ~ ActivityStart", "Touch Up ~ Activity Start"),
        ])

    # 4. Activity Start (Luôn có)
    rows.append(("ActivityStart", "Activity Start"))
    
    # 5. Middle Block: Tách biệt logic cho Camera và App thường
    if is_camera:
        # === LOGIC RIÊNG CHO CAMERA ===
        rows.extend([
            ("onCreate", "onCreate"),
            ("OpenCameraRequest", "OpenCameraRequest"),
            ("    ~", "activityStart ~ activityResume"),
            ("ActivityResume", "Activity Resume"),
            ("onResume", "onResume"),
            ("    ~", "ActivityResume ~ Choreographer"),
            ("Choreographer", "Choreographer"),
            ("    StartPreviewRequest", "StartPreviewRequest"),
            ("    ~", "Choreographer ~ ActivityIdle"),
            ("ActivityIdle", "ActivityIdle"),
            ("    ~ Animating end", "ActivityIdle ~ Animating end"),
        ])
    else:
        # === LOGIC CHO APP THƯỜNG ===
        rows.extend([
            ("    ~", "activityStart ~ activityResume"),
            ("ActivityResume", "Activity Resume"),
            ("    ~", "ActivityResume ~ Choreographer"),
            ("Choreographer", "Choreographer"),
            ("    ~", "Choreographer ~ ActivityIdle"),
            ("ActivityIdle", "ActivityIdle"),
            ("    ~ Animating end", "ActivityIdle ~ Animating end"),
        ])
    
    # 6. State Metrics (Luôn có ở cuối)
    rows.extend([
        ("", ""),
        ("Running", "Running"),
        ("Runnable", "Runnable"),
        ("Uninterruptible Sleep", "Uninterruptible Sleep"),
        ("Sleeping", "Sleeping"),
    ])
    
    return rows

def create_sheet(
    wb: xlsxwriter.Workbook,
    sheet_name: str,
    dut_cycles: List[Dict[str, Any]],
    ref_cycles: List[Dict[str, Any]],
    header_title: str,
    launch_type: str,
    app_name: str,
    dut_device_code: str,
    ref_device_code: str,
    dut_folder_path: str = "",
    ref_folder_path: str = ""
) -> None:
    ws = wb.add_worksheet(sheet_name)
    
    # --- Formats ---
    fmt_header_main = wb.add_format({"bold": True, "align": "center", "bg_color": "#D3D3D3", "border": 1, "border_color": "#000000"})
    fmt_header_dut = wb.add_format({"bold": True, "align": "center", "bg_color": "#90EE90", "border": 1, "border_color": "#000000"})
    fmt_header_ref = wb.add_format({"bold": True, "align": "center", "bg_color": "#FFB366", "border": 1, "border_color": "#000000"})
    fmt_header_diff = wb.add_format({"bold": True, "align": "center", "bg_color": "#FFFF99", "border": 1, "border_color": "#000000"})
    fmt_label = wb.add_format({"align": "left", "border": 1, "border_color": "#000000"})
    fmt_label_highlight = wb.add_format({"align": "left", "italic": True, "font_color": "#008000"}) 
    # Format riêng cho "Start proc" (Căn trái ngang, giữa dọc)
    fmt_start_proc = wb.add_format({"align": "left", "valign": "vcenter", "border": 1, "border_color": "#000000"})
    fmt_val = wb.add_format({"num_format": "0.000", "align": "center", "border": 1, "border_color": "#000000"})
    fmt_text = wb.add_format({"align": "center", "border": 1, "border_color": "#000000"})
    fmt_diff_slow = wb.add_format({"num_format": "0.000", "align": "center", "bg_color": "#FFB3B3", "border": 1, "border_color": "#000000"})
    fmt_diff_fast = wb.add_format({"num_format": "0.000", "align": "center", "bg_color": "#B3FFB3", "border": 1, "border_color": "#000000"})
    fmt_diff_normal = wb.add_format({"num_format": "0.000", "align": "center", "border": 1, "border_color": "#000000"})
    
    # Format for new section headers (MEMORY, LOADAPKASSETS, ABNORMAL)
    fmt_section_header = wb.add_format({
        "bold": True, 
        "align": "left",
        "bg_color": "#FFFFFF",
        "font_color": "#000000",
        "border": 1,
        "border_color": "#000000"
    })
    fmt_section_value = wb.add_format({"align": "center", "border": 1, "border_color": "#000000"})
    fmt_section_text = wb.add_format({"align": "left", "border": 1, "border_color": "#000000", "text_wrap": True})
    
    # Số lượng cycles
    num_dut_cycles = len(dut_cycles)
    num_ref_cycles = len(ref_cycles)
    max_cycles = max(num_dut_cycles, num_ref_cycles)
    
    # =========================================================================
    # [NEW] PRE-PROCESS: Chọn common end_ts type cho mỗi cycle pair
    # Điều này đảm bảo DUT và REF được so sánh với cùng time window
    # =========================================================================
    adjusted_dut_cycles = []
    adjusted_ref_cycles = []
    end_ts_types_used = []  # Track which type was used for each cycle
    
    for i in range(max_cycles):
        dut_cycle = dut_cycles[i] if i < num_dut_cycles else None
        ref_cycle = ref_cycles[i] if i < num_ref_cycles else None
        
        if dut_cycle and ref_cycle:
            # Có cả DUT và REF → tìm common end_ts type
            common_type = select_common_end_ts_type(dut_cycle, ref_cycle)
            
            if common_type:
                # Lấy data cho common type
                adj_dut = get_metrics_for_end_ts_type(dut_cycle, common_type)
                adj_ref = get_metrics_for_end_ts_type(ref_cycle, common_type)
                end_ts_types_used.append(common_type)
            else:
                # Không có common type → dùng data gốc, sẽ có warning
                adj_dut = dut_cycle
                adj_ref = ref_cycle
                end_ts_types_used.append("mismatch")
        elif dut_cycle:
            adj_dut = dut_cycle
            adj_ref = None
            end_ts_types_used.append("dut_only")
        elif ref_cycle:
            adj_dut = None
            adj_ref = ref_cycle
            end_ts_types_used.append("ref_only")
        else:
            adj_dut = None
            adj_ref = None
            end_ts_types_used.append(None)
        
        adjusted_dut_cycles.append(adj_dut)
        adjusted_ref_cycles.append(adj_ref)
    
    # Replace cycles với adjusted versions
    # dut_cycles = [c for c in adjusted_dut_cycles if c is not None] + [None] * (max_cycles - len([c for c in adjusted_dut_cycles if c is not None]))
    # ref_cycles = [c for c in adjusted_ref_cycles if c is not None] + [None] * (max_cycles - len([c for c in adjusted_ref_cycles if c is not None]))
    
    # Rebuild lists to maintain original length
    dut_cycles = adjusted_dut_cycles
    ref_cycles = adjusted_ref_cycles

    # --- CHECK GLOBAL STATE (ALL COLD / ALL WARM) ---
    all_cycles_data = [c for c in dut_cycles + ref_cycles if c is not None]
    has_cold = any(c.get("Launch Type") == "Cold" for c in all_cycles_data)
    has_warm = any(c.get("Launch Type") == "Warm" for c in all_cycles_data)

    # --- HEADER ROW ---
    ws.write("A1", header_title, fmt_header_main)
    
    # DUT header with device code
    dut_header_text = f"DUT - {dut_device_code} (ms)" if dut_device_code else "DUT (ms)"
    col_offset = 1
    ws.merge_range(0, col_offset, 0, col_offset + max_cycles, dut_header_text, fmt_header_dut)
    
    # REF header with device code
    ref_header_text = f"REF - {ref_device_code} (ms)" if ref_device_code else "REF (ms)"
    col_offset += max_cycles + 1
    ws.merge_range(0, col_offset, 0, col_offset + max_cycles, ref_header_text, fmt_header_ref)
    
    # Diff header
    col_offset += max_cycles + 1
    ws.write(0, col_offset, "Diff", fmt_header_diff)

    # --- SUB-HEADER ROW: Thay đổi thành "1 (Cold)" hoặc "1 (Warm)" ---
    col_idx = 1
    
    def get_cycle_title(idx, cycle_list):
        # [FIX] Thêm điều kiện kiểm tra cycle_list[idx] is not None
        if idx < len(cycle_list) and cycle_list[idx] is not None:
            l_type = cycle_list[idx].get("Launch Type", "Unknown")
            return f"{idx + 1} ({l_type})"
        return f"{idx + 1}"

    # DUT Sub-headers
    for i in range(max_cycles):
        title = get_cycle_title(i, dut_cycles)
        ws.write(1, col_idx, title, fmt_header_dut)
        col_idx += 1
    ws.write(1, col_idx, "Avg", fmt_header_dut)
    col_idx += 1
    
    # REF Sub-headers
    for i in range(max_cycles):
        title = get_cycle_title(i, ref_cycles)
        ws.write(1, col_idx, title, fmt_header_ref)
        col_idx += 1
    ws.write(1, col_idx, "Avg", fmt_header_ref)
    col_idx += 1
    
    ws.write(1, col_idx, "", fmt_header_diff)
    
    ws.set_column("A:A", 35) # Tăng độ rộng cột A cho đẹp
    ws.set_column(1, col_idx, 15) # Tăng độ rộng cột dữ liệu để chứa title dài
    
    # --- DATA ROWS ---
    # Gọi hàm lọc hàng mới (Đã bao gồm logic Camera)
    metric_rows = get_filtered_metric_rows(launch_type, app_name, has_cold, has_warm)
    
    highlight_metrics = ["onCreate", "OpenCameraRequest", "onResume", "StartPreviewRequest"]
    
    row_idx = 2
    for display_name, metric_key in metric_rows:
        if display_name == "":  # Separator
            row_idx += 1
            continue
            
        # Write Label
        if metric_key in highlight_metrics:
            ws.write(row_idx, 0, display_name, fmt_label_highlight)
        else:
            ws.write(row_idx, 0, display_name, fmt_label)
        
        # --- WRITE DUT DATA (Masking Logic) ---
        col_idx = 1
        dut_values = []
        for i in range(max_cycles):
            if i < len(dut_cycles) and dut_cycles[i] is not None:
                cycle_data = dut_cycles[i]
                c_type = cycle_data.get("Launch Type")
                
                # Logic Masking: Kiểm tra xem có nên ghi dữ liệu không
                should_write = True
                if c_type == "Warm" and metric_key in COLD_ONLY_KEYS:
                    should_write = False
                elif c_type == "Cold" and metric_key in WARM_ONLY_KEYS:
                    should_write = False
                
                if should_write:
                    val = cycle_data.get(metric_key, 0.0)
                    write_value_or_empty(ws, row_idx, col_idx, float(val), fmt_val)
                    dut_values.append(float(val))
                else:
                    ws.write(row_idx, col_idx, "", fmt_text) # Để trống
            else:
                ws.write(row_idx, col_idx, "", fmt_val)
            col_idx += 1
        
        # DUT Avg
        valid_dut = [v for v in dut_values if v > 0]
        if valid_dut:
            dut_avg = sum(valid_dut) / len(valid_dut)
            write_value_or_empty(ws, row_idx, col_idx, dut_avg, fmt_val)
        else:
            dut_avg = 0.0
            write_value_or_empty(ws, row_idx, col_idx, 0.0, fmt_val)
        col_idx += 1
        
        # --- WRITE REF DATA (Masking Logic) ---
        ref_values = []
        for i in range(max_cycles):
            if i < len(ref_cycles) and ref_cycles[i] is not None:
                cycle_data = ref_cycles[i]
                c_type = cycle_data.get("Launch Type")
                
                # Logic Masking
                should_write = True
                if c_type == "Warm" and metric_key in COLD_ONLY_KEYS:
                    should_write = False
                elif c_type == "Cold" and metric_key in WARM_ONLY_KEYS:
                    should_write = False
                
                if should_write:
                    val = cycle_data.get(metric_key, 0.0)
                    write_value_or_empty(ws, row_idx, col_idx, float(val), fmt_val)
                    ref_values.append(float(val))
                else:
                    ws.write(row_idx, col_idx, "", fmt_text)
            else:
                ws.write(row_idx, col_idx, "", fmt_val)
            col_idx += 1
        
        # REF Avg
        valid_ref = [v for v in ref_values if v > 0]
        if valid_ref:
            ref_avg = sum(valid_ref) / len(valid_ref)
            write_value_or_empty(ws, row_idx, col_idx, ref_avg, fmt_val)
        else:
            ref_avg = 0.0
            write_value_or_empty(ws, row_idx, col_idx, 0.0, fmt_val)
        col_idx += 1
        
        # --- DIFF COLUMN ---
        diff_val = dut_avg - ref_avg
        if metric_key == "Uninterruptible Sleep":
            if diff_val > 30:  # Ngưỡng 30ms cho Uninterruptible Sleep
                fmt_diff = fmt_diff_slow      
            elif diff_val < -30:
                fmt_diff = fmt_diff_fast      
            else:
                fmt_diff = fmt_diff_normal     
        else:
            # Các metric khác giữ nguyên ngưỡng 10ms
            if diff_val > 10:
                fmt_diff = fmt_diff_slow      
            elif diff_val < -10:
                fmt_diff = fmt_diff_fast      
            else:
                fmt_diff = fmt_diff_normal     

        ws.write(row_idx, col_idx, diff_val, fmt_diff)

        row_idx += 1
    
    # ---------------------------------------------------------
    # === [NEW] Process Start Overlap Section (Merged into Sequence Table) ===
    # ---------------------------------------------------------
    
    # 1. Chuẩn bị dữ liệu Process Names cho từng cột
    # Map: {column_index: [list_of_process_names]}
    proc_overlap_map = {} 
    max_proc_rows = 0 # Số dòng cần thiết để hiển thị hết process nhiều nhất
    
    current_col = 1
    
    # --- Thu thập dữ liệu DUT ---
    for i in range(max_cycles):
        procs = []
        if i < len(dut_cycles) and dut_cycles[i] is not None:
            # Lấy data từ 2 nguồn: Abnormal & Background
            abnormal = dut_cycles[i].get("Abnormal_Process_Data", [])
            bg = dut_cycles[i].get("Background_Process_States", [])
            
            # Dùng set để lọc trùng
            names = set()
            for p in abnormal:
                names.add(p.get('proc_name', ''))
            for p in bg:
                names.add(p.get('Thread name', ''))
            
            # Lọc bỏ rỗng và sort
            procs = sorted([n for n in names if n and n != 'Unknown'])
            
        proc_overlap_map[current_col] = procs
        if len(procs) > max_proc_rows:
            max_proc_rows = len(procs)
        current_col += 1
        
    # Bỏ qua cột DUT Avg
    current_col += 1
    
    # --- Thu thập dữ liệu REF ---
    for i in range(max_cycles):
        procs = []
        if i < len(ref_cycles) and ref_cycles[i] is not None:
            abnormal = ref_cycles[i].get("Abnormal_Process_Data", [])
            bg = ref_cycles[i].get("Background_Process_States", [])
            
            names = set()
            for p in abnormal:
                names.add(p.get('proc_name', ''))
            for p in bg:
                names.add(p.get('Thread name', ''))
            
            procs = sorted([n for n in names if n and n != 'Unknown'])
            
        proc_overlap_map[current_col] = procs
        if len(procs) > max_proc_rows:
            max_proc_rows = len(procs)
        current_col += 1
        
    # Bỏ qua REF Avg và Diff
    current_col += 2 # Skip REF Avg, Diff
    if not proc_overlap_map or max_proc_rows == 0:
        pass
    else:
        # 2. Vẽ Header cho phần này
        # Dòng tiêu đề: "Process start overlap"
        # ws.write(row_idx, 0, "Process start overlap", fmt_label_highlight)
        # for c in range(1, current_col):
        #     ws.write(row_idx, c, "", fmt_text)
        last_col = 2 * max_cycles + 3  # Index của cột Diff
        ws.merge_range(row_idx, 0, row_idx, last_col, "", fmt_text)
        
        row_idx += 1
        # 3. Vẽ dữ liệu (Dynamic Rows) với merge logic cho "Start proc"
        # Nếu không có process nào overlap thì ít nhất cũng hiện dòng label
        total_rows_to_draw = max(1, max_proc_rows)
        
        # Merge cột A cho "Start proc" nếu có nhiều dòng
        if total_rows_to_draw > 1:
            ws.merge_range(row_idx, 0, row_idx + total_rows_to_draw - 1, 0, "Start proc", fmt_start_proc)
        else:
            ws.write(row_idx, 0, "Start proc", fmt_start_proc)
                
        for r in range(total_rows_to_draw):
            # Các cột dữ liệu
            # Loop qua map đã chuẩn bị
            for c_idx, p_list in proc_overlap_map.items():
                if r < len(p_list):
                    # Ghi tên process
                    ws.write(row_idx, c_idx, p_list[r], fmt_text)
                else:
                    # Ô trống có viền
                    ws.write(row_idx, c_idx, "", fmt_text)
                    
            # Fill viền cho các cột Avg/Diff (để bảng liền mạch)
            # DUT Avg index = 1 + max_cycles
            dut_avg_idx = 1 + max_cycles
            ws.write(row_idx, dut_avg_idx, "", fmt_val)
                    
            # REF Avg index
            ref_avg_idx = dut_avg_idx + 1 + max_cycles
            ws.write(row_idx, ref_avg_idx, "", fmt_val)
                    
            # Diff index
            diff_idx = ref_avg_idx + 1
            ws.write(row_idx, diff_idx, "", fmt_val)
                    
            row_idx += 1

    # =========================================================================
    # [NEW] EXTENDED PROFILING SECTIONS
    # =========================================================================
    
    # Calculate column indices (same as main table)
    total_cols = 1 + max_cycles + 1 + max_cycles + 1 + 1  # Metric + DUT cycles + DUT Avg + REF cycles + REF Avg + Diff
    dut_avg_col = 1 + max_cycles
    ref_avg_col = dut_avg_col + 1 + max_cycles
    diff_col = ref_avg_col + 1
    
    # ---------------------------------------------------------
    # === MEMORY SECTION ===
    # ---------------------------------------------------------
    row_idx += 1  # Empty separator
    
    # Section header - merged across all columns
    ws.merge_range(row_idx, 0, row_idx, total_cols - 1, "MEMORY", fmt_section_header)
    row_idx += 1
    
    # Memory metrics: MemFree, MemAvailable, App PSS, Pageboostd
    memory_metrics = ["MemFree (MB)", "MemAvailable (MB)", "App PSS (MB)", "Pageboostd (MB)"]
    
    for metric in memory_metrics:
        ws.write(row_idx, 0, metric, fmt_label)
        
        dut_values = []
        ref_values = []
        
        for i in range(max_cycles):
            # Get memory data for DUT — [REFACTORED] Đọc từ Precomputed_Extend_Data
            if i < num_dut_cycles and dut_folder_path:
                val = 0.0
                dut_cycle = dut_cycles[i] if i < len(dut_cycles) else None
                if dut_cycle is not None:
                    extend_data = dut_cycle.get('Precomputed_Extend_Data', {})
                    if "MemFree" in metric:
                        val = extend_data.get('MemFree', 0.0)
                    elif "MemAvailable" in metric:
                        val = extend_data.get('MemAvailable', 0.0)
                    elif "App PSS" in metric:
                        val = extend_data.get('App_PSS', 0.0)
                    elif "Pageboostd" in metric:
                        val = extend_data.get('Pageboostd', 0.0)
                    
                ws.write(row_idx, 1 + i, val if val > 0 else "", fmt_section_value)
                if val > 0:
                    dut_values.append(val)
            else:
                ws.write(row_idx, 1 + i, "", fmt_section_value)
            
            # Get memory data for REF
            if i < num_ref_cycles and ref_folder_path:
                # Use ref_cycles directly (not adjusted) to ensure trace_mapping is available
                ref_cycle = ref_cycles[i] if i < len(ref_cycles) else None
                
                if "MemFree" in metric:
                    val = 0.0
                    if ref_cycle is not None:
                        extend_data = ref_cycle.get('Precomputed_Extend_Data', {})
                        val = extend_data.get('MemFree', 0.0)
                elif "MemAvailable" in metric:
                    val = 0.0
                    if ref_cycle is not None:
                        extend_data = ref_cycle.get('Precomputed_Extend_Data', {})
                        val = extend_data.get('MemAvailable', 0.0)
                elif "App PSS" in metric:
                    val = 0.0
                    if ref_cycle is not None:
                        extend_data = ref_cycle.get('Precomputed_Extend_Data', {})
                        val = extend_data.get('App_PSS', 0.0)
                elif "Pageboostd" in metric:
                    val = 0.0
                    if ref_cycle is not None:
                        extend_data = ref_cycle.get('Precomputed_Extend_Data', {})
                        val = extend_data.get('Pageboostd', 0.0)
                else:
                    val = 0.0
                    
                ws.write(row_idx, dut_avg_col + 1 + i, val if val > 0 else "", fmt_section_value)
                if val > 0:
                    ref_values.append(val)
            else:
                ws.write(row_idx, dut_avg_col + 1 + i, "", fmt_section_value)
        
        # Calculate and write averages
        dut_avg = sum(dut_values) / len(dut_values) if dut_values else 0.0
        ref_avg = sum(ref_values) / len(ref_values) if ref_values else 0.0
        
        ws.write(row_idx, dut_avg_col, dut_avg if dut_avg > 0 else "", fmt_val)
        ws.write(row_idx, ref_avg_col, ref_avg if ref_avg > 0 else "", fmt_val)
        
        # Diff calculation
        if dut_avg > 0 and ref_avg > 0:
            diff = dut_avg - ref_avg
            # For memory, higher is better for Free/Available, so positive diff is good
            if "Free" in metric or "Available" in metric:
                # fmt_diff = fmt_diff_fast if diff > 0 else (fmt_diff_slow if diff < 0 else fmt_diff_normal)
                fmt_diff = fmt_diff_normal
            else:
                # fmt_diff = fmt_diff_slow if diff > 0 else (fmt_diff_fast if diff < 0 else fmt_diff_normal)
                fmt_diff = fmt_diff_normal
            ws.write(row_idx, diff_col, diff, fmt_diff)
        else:
            ws.write(row_idx, diff_col, "", fmt_val)
        
        row_idx += 1
    
    # ---------------------------------------------------------
    # === LOADAPKASSETS SECTION (EXTENDED) ===
    # ---------------------------------------------------------
    
    # 1. Thu thập dữ liệu trước
    all_dut_loadapk = [cycle.get("LoadApkAsset_Data", {}) if cycle else {} for cycle in dut_cycles]
    all_ref_loadapk = [cycle.get("LoadApkAsset_Data", {}) if cycle else {} for cycle in ref_cycles]
    
    target_categories = ["system_server", "system_ui", "launching_app"]
    
    # 2. Kiểm tra xem có bất kỳ dữ liệu nào không
    has_loadapk_data = False
    for cycle_data in all_dut_loadapk + all_ref_loadapk:
        if isinstance(cycle_data, dict):
            for cat in target_categories:
                # Kiểm tra nếu category có list asset và list đó không rỗng
                if cycle_data.get(cat):
                    has_loadapk_data = True
                    break
        if has_loadapk_data: break
    
    # 3. Chỉ vẽ bảng nếu có dữ liệu
    if has_loadapk_data:
        row_idx += 1  # Dòng trống ngăn cách
        
        # Vẽ Header Section
        ws.merge_range(row_idx, 0, row_idx, total_cols - 1, "LOADAPKASSETS (>50ms)", fmt_section_header)
        row_idx += 1
        
        # Vẽ từng Category
        for category in target_categories:
            # Label Category
            ws.write(row_idx, 0, category.title(), fmt_label)
            
            # Fill DUT Cycles
            col_idx = 1
            dut_sum_vals = []
            for i in range(max_cycles):
                val = 0.0
                if i < len(all_dut_loadapk):
                    cycle_data = all_dut_loadapk[i]
                    if isinstance(cycle_data, dict):
                        assets = cycle_data.get(category, [])
                        # TÍNH TỔNG: Cộng dồn thời gian
                        val = sum(item.get('dur_ms', 0.0) for item in assets)
                
                write_value_or_empty(ws, row_idx, col_idx, val, fmt_section_value)
                if val > 0: dut_sum_vals.append(val)
                col_idx += 1
            
            # DUT Avg
            dut_avg = sum(dut_sum_vals) / len(dut_sum_vals) if dut_sum_vals else 0.0
            write_value_or_empty(ws, row_idx, col_idx, dut_avg, fmt_val)
            col_idx += 1

            # Fill REF Cycles
            ref_sum_vals = []
            for i in range(max_cycles):
                val = 0.0
                if i < len(all_ref_loadapk):
                    cycle_data = all_ref_loadapk[i]
                    if isinstance(cycle_data, dict):
                        assets = cycle_data.get(category, [])
                        # TÍNH TỔNG
                        val = sum(item.get('dur_ms', 0.0) for item in assets)
                
                write_value_or_empty(ws, row_idx, col_idx, val, fmt_section_value)
                if val > 0: ref_sum_vals.append(val)
                col_idx += 1
            
            # REF Avg
            ref_avg = sum(ref_sum_vals) / len(ref_sum_vals) if ref_sum_vals else 0.0
            write_value_or_empty(ws, row_idx, col_idx, ref_avg, fmt_val)
            col_idx += 1
            
            # Diff
            if dut_avg > 0 or ref_avg > 0:
                diff = dut_avg - ref_avg
                # Format màu sắc nếu chênh lệch lớn
                fmt = fmt_diff_normal
                if diff > 50: fmt = fmt_diff_slow
                elif diff < -50: fmt = fmt_diff_fast
                write_value_or_empty(ws, row_idx, col_idx, diff, fmt)
            else:
                ws.write(row_idx, col_idx, "", fmt_val)
            
            row_idx += 1

    
    # ---------------------------------------------------------
    # === ABNORMAL SECTION ===
    # ---------------------------------------------------------
    row_idx += 1  # Empty separator
    
    ws.merge_range(row_idx, 0, row_idx, total_cols - 1, "ABNORMAL", fmt_section_header)
    row_idx += 1
    
    # Abnormal metrics: Uptime, Start reason, Kill reason, Crash count, Compiler
    abnormal_rows = ["Uptime (minute)", "Start reason", "Kill reason", "Crash count", "Compiler"]
    
    for metric in abnormal_rows:
        ws.write(row_idx, 0, metric, fmt_label)
        
        for i in range(max_cycles):
            # Get DUT abnormal data — [REFACTORED] Đọc từ Precomputed_Extend_Data
            dut_val = ""
            if i < len(dut_cycles):
                dut_cycle = dut_cycles[i]
                if dut_cycle:
                    extend_data = dut_cycle.get('Precomputed_Extend_Data', {})
                    if "Uptime" in metric:
                        dut_val = extend_data.get('Uptime', "")
                    elif metric == "Start reason":
                        dut_val = extend_data.get('Start_Reason', "")
                    elif metric == "Kill reason":
                        reasons = extend_data.get('Kill_Reason', [])
                        dut_val = ", ".join(reasons) if reasons else ""
                    elif metric == "Crash count":
                        dut_val = extend_data.get('Crash_Count', "")
                    elif metric == "Compiler":
                        dut_val = extend_data.get('Compiler', "")
            
            ws.write(row_idx, 1 + i, dut_val, fmt_section_text if isinstance(dut_val, str) else fmt_section_value)
            
            # Get REF abnormal data — [REFACTORED] Đọc từ Precomputed_Extend_Data
            ref_val = ""
            if i < len(ref_cycles):
                ref_cycle = ref_cycles[i]
                if ref_cycle:
                    extend_data = ref_cycle.get('Precomputed_Extend_Data', {})
                    if "Uptime" in metric:
                        ref_val = extend_data.get('Uptime', "")
                    elif metric == "Start reason":
                        ref_val = extend_data.get('Start_Reason', "")
                    elif metric == "Kill reason":
                        reasons = extend_data.get('Kill_Reason', [])
                        ref_val = ", ".join(reasons) if reasons else ""
                    elif metric == "Crash count":
                        ref_val = extend_data.get('Crash_Count', "")
                    elif metric == "Compiler":
                        ref_val = extend_data.get('Compiler', "")
            
            ws.write(row_idx, dut_avg_col + 1 + i, ref_val, fmt_section_text if isinstance(ref_val, str) else fmt_section_value)
        
        # Avg and Diff are mostly N/A for text fields
        ws.write(row_idx, dut_avg_col, "", fmt_val)
        ws.write(row_idx, ref_avg_col, "", fmt_val)
        ws.write(row_idx, diff_col, "", fmt_val)
        
        row_idx += 1

    # ---------------------------------------------------------
    # === Abnormal Process & Background Activity Table ===
    # ---------------------------------------------------------
    row_idx += 3

    # Format riêng cho cột Cycle (Căn giữa dọc và ngang)
    fmt_cycle_merge = wb.add_format({
        "bold": True, 
        "align": "center", 
        "valign": "vcenter", 
        "bg_color": "#E0E0E0", 
        "border": 1, 
        "border_color": "#000000"
    })

    # Format header
    fmt_abnormal_header = wb.add_format({"bold": True, "align": "center", "bg_color": "#FFCCCB", "border": 1, "border_color": "#000000"})
    fmt_abnormal_subheader = wb.add_format({"bold": True, "align": "center", "bg_color": "#FFE4E1", "border": 1, "border_color": "#000000"})
    fmt_abnormal_val = wb.add_format({"align": "left", "border": 1, "border_color": "#000000"})
    
    # --- HEADER ROWS ---
    # Row 1: Header chính "Process start" (Gộp cả DUT và REF)
    ws.merge_range(row_idx, 0, row_idx, 2, "Process start", fmt_abnormal_header)
    row_idx += 1

    # Row 2: Sub-headers
    ws.write(row_idx, 0, "Cycle", fmt_abnormal_subheader)
    ws.write(row_idx, 1, "DUT", fmt_abnormal_subheader)
    ws.write(row_idx, 2, "REF", fmt_abnormal_subheader)
    row_idx += 1

    # --- DATA ROWS PER CYCLE ---
    max_cycles_abnormal = max(len(dut_cycles), len(ref_cycles))

    for i in range(max_cycles_abnormal):
        # 1. Thu thập & Gộp danh sách tên Process cho DUT
        dut_names_set = set()
        if i < len(dut_cycles) and dut_cycles[i] is not None:
            # Nguồn 1: Abnormal (bindApplication)
            abnormal_data = dut_cycles[i].get("Abnormal_Process_Data", [])
            for p in abnormal_data:
                proc_name = p.get('proc_name', 'Unknown')
                dut_names_set.add(f"{proc_name} (start proc)")
            
            # Nguồn 2: Background Active (>10ms)
            bg_data = dut_cycles[i].get("Background_Process_States", [])
            for p in bg_data:
                dut_names_set.add(p.get('Thread name', 'Unknown'))
        
        sorted_dut_names = sorted(list(dut_names_set))

        # 2. Thu thập & Gộp danh sách tên Process cho REF
        ref_names_set = set()
        if i < len(ref_cycles) and ref_cycles[i] is not None:
            # Nguồn 1: Abnormal
            abnormal_data = ref_cycles[i].get("Abnormal_Process_Data", [])
            for p in abnormal_data:
                proc_name = p.get('proc_name', 'Unknown')
                ref_names_set.add(f"{proc_name} (start proc)")
            
            # Nguồn 2: Background Active
            bg_data = ref_cycles[i].get("Background_Process_States", [])
            for p in bg_data:
                ref_names_set.add(p.get('Thread name', 'Unknown'))
        
        sorted_ref_names = sorted(list(ref_names_set))

        # 3. Tính số dòng cần thiết (max giữa DUT và REF)
        num_rows = max(len(sorted_dut_names), len(sorted_ref_names))
        if num_rows == 0: num_rows = 1 # Luôn giữ ít nhất 1 dòng cho cycle

        # 4. Ghi cột Cycle (Merge ô nếu có nhiều process)
        cycle_label = f"Cycle {i + 1}"
        if num_rows > 1:
            ws.merge_range(row_idx, 0, row_idx + num_rows - 1, 0, cycle_label, fmt_cycle_merge)
        else:
            ws.write(row_idx, 0, cycle_label, fmt_cycle_merge)

        # 5. Ghi dữ liệu từng dòng
        for r in range(num_rows):
            # Ghi bên DUT
            if r < len(sorted_dut_names):
                ws.write(row_idx, 1, sorted_dut_names[r], fmt_abnormal_val)
            else:
                ws.write(row_idx, 1, "", fmt_abnormal_val)

            # Ghi bên REF
            if r < len(sorted_ref_names):
                ws.write(row_idx, 2, sorted_ref_names[r], fmt_abnormal_val)
            else:
                ws.write(row_idx, 2, "", fmt_abnormal_val)
            
            row_idx += 1

    # Set column widths
    ws.set_column(0, 0, 15) # Cột Cycle
    ws.set_column(1, 2, 35) # Cột Tên Process (Rộng hơn để hiển thị tên dài)

    
    # =========================================================================
    # === Top CPU Usage Tables (Logic: Tiered Matching) ===
    # =========================================================================
    row_idx += 3

    # Load Data
    all_dut_proc = [cycle.get("CPU_Process_Data", []) if cycle else [] for cycle in dut_cycles]
    all_ref_proc = [cycle.get("CPU_Process_Data", []) if cycle else [] for cycle in ref_cycles]
    all_dut_thread = [cycle.get("CPU_Thread_Data", []) if cycle else [] for cycle in dut_cycles]
    all_ref_thread = [cycle.get("CPU_Thread_Data", []) if cycle else [] for cycle in ref_cycles]

    # Formats
    fmt_cpu_header = wb.add_format({"bold": True, "align": "center", "bg_color": "#FFE4B5", "border": 1})
    fmt_cpu_sub = wb.add_format({"bold": True, "align": "center", "bg_color": "#FFF8DC", "border": 1})
    fmt_cpu_val = wb.add_format({"num_format": "0.000", "align": "center", "border": 1})
    fmt_cpu_text = wb.add_format({"align": "left", "border": 1})
    fmt_diff_slow = wb.add_format({"num_format": "0.000", "align": "center", "bg_color": "#FFB3B3", "border": 1})
    fmt_diff_fast = wb.add_format({"num_format": "0.000", "align": "center", "bg_color": "#B3FFB3", "border": 1})
    fmt_diff_norm = wb.add_format({"num_format": "0.000", "align": "center", "border": 1})

    max_cycles = max(len(all_dut_proc), len(all_ref_proc))

    for cycle_idx in range(max_cycles):
        # ---------------------------------------------------------
        # PREPARE DATA FOR LEFT TABLE (PROCESS) - [IMPROVED TIERED MATCHING]
        # ---------------------------------------------------------
        dut_p = all_dut_proc[cycle_idx] if cycle_idx < len(all_dut_proc) else []
        ref_p = all_ref_proc[cycle_idx] if cycle_idx < len(all_ref_proc) else []
        
        # 1. Tạo Lookup Map cho REF
        ref_by_sql = {}   # Tra cứu nhanh bằng tên SQL
        ref_by_dump = {}  # Tra cứu nhanh bằng tên Dumpstate
        
        for item in ref_p:
            s_name = item['sql_name']
            d_name = item.get('dumpstate_name')
            
            # Add to SQL Map (Cộng dồn nếu trùng tên do phân mảnh)
            if s_name not in ref_by_sql:
                ref_by_sql[s_name] = item.copy()
            else:
                ref_by_sql[s_name]['dur_ms'] += item['dur_ms']

            # Add to Dumpstate Map (Chỉ những process có tên mapping mới vào đây)
            if d_name:
                if d_name not in ref_by_dump:
                    ref_by_dump[d_name] = item.copy()
                else:
                    ref_by_dump[d_name]['dur_ms'] += item['dur_ms']
        
        matched_results = []
        used_ref_sql_names = set() # Đánh dấu các REF đã được match để không in lại ở phần REF-only
        
        # 2. Duyệt DUT và tìm REF tương ứng
        for dut_item in dut_p:
            dut_sql = dut_item['sql_name']
            dut_dump = dut_item.get('dumpstate_name')
            dut_val = dut_item['dur_ms']
            
            ref_val = 0.0
            display_name = dut_sql # Mặc định dùng tên SQL
            match_found = False
            
            # --- CHECK 1: Match chính xác theo SQL Name ---
            if not dut_sql.startswith("PID-") and dut_sql in ref_by_sql:
                ref_item = ref_by_sql[dut_sql]
                ref_val = ref_item['dur_ms']
                match_found = True

            # --- CHECK 2: Fallback sang Dumpstate Name ---
            # Chỉ chạy nếu Check 1 thất bại VÀ DUT có mapping tên thật
            elif dut_dump and dut_dump in ref_by_dump:
                ref_item = ref_by_dump[dut_dump]
                ref_val = ref_item['dur_ms']
                match_found = True
                display_name = dut_dump # Hiển thị tên thật cho đẹp
            
            # --- CHECK 3: Tên hiển thị ---
            else:
                if dut_sql.startswith("PID-") and dut_dump:
                    display_name = dut_dump
            
            # --- TÍNH DIFF (LOGIC MỚI) ---
            if match_found:
                # Trường hợp A: Tìm thấy process tương ứng bên REF
                diff = dut_val - ref_val
            else:
                # Trường hợp B: Không tìm thấy bên REF
                if dut_dump:
                    # B.1: DUT có dumpstate name (Process được định danh rõ ràng)
                    # -> Đây là Process Lạ (có trên DUT, không có trên REF)
                    # -> Diff = DUT (để hiện lên Top)
                    ref_val = 0.0
                    diff = dut_val
                else:
                    # B.2: DUT KHÔNG có dumpstate name (Thiếu bugreport hoặc PID ảo)
                    # -> Không đủ bằng chứng là process lạ.
                    # -> Diff = 0 (để ẩn đi/loại bỏ nhiễu)
                    ref_val = 0.0
                    diff = 0.0
            
            matched_results.append({
                'name': display_name,
                'dut': dut_val,
                'ref': ref_val,
                'diff': diff
            })

        # 3. Sort & Select Top 10
        top_proc = sorted(matched_results, key=lambda x: x['diff'], reverse=True)[:10]

        # ---------------------------------------------------------
        # PREPARE DATA FOR RIGHT TABLE (THREAD)
        # ---------------------------------------------------------
        dut_t = all_dut_thread[cycle_idx] if cycle_idx < len(all_dut_thread) else []
        ref_t = all_ref_thread[cycle_idx] if cycle_idx < len(all_ref_thread) else []
        
        # Match Thread by (Thread Name, Process Name) vì TID thay đổi
        merged_t = {}
        def get_t_key(item): return (item['thread_name'], item['proc_name'])
        
        for x in dut_t: merged_t[get_t_key(x)] = {'dut': x['dur_ms'], 'ref': 0.0}
        for x in ref_t:
            k = get_t_key(x)
            if k not in merged_t: merged_t[k] = {'dut': 0.0, 'ref': 0.0}
            merged_t[k]['ref'] = x['dur_ms']
            
        final_thread = []
        for (tname, pname), v in merged_t.items():
            # Display name: "Thread (Process)"
            disp = f"{tname} ({pname})"
            final_thread.append({'name': disp, 'dut': v['dut'], 'ref': v['ref'], 'diff': v['dut'] - v['ref']})
            
        # Sort Diff -> Take Top 10
        top_thread = sorted(final_thread, key=lambda x: x['diff'], reverse=True)[:10]

        # ---------------------------------------------------------
        # DRAW HEADERS
        # ---------------------------------------------------------
        # Header Left (Process): Cols 0-3 (A-D)
        ws.merge_range(row_idx, 0, row_idx, 3, f"Top Process CPU - Cycle {cycle_idx+1}", fmt_cpu_header)
        
        # Header Right (Thread): Cols 5-8 (F-I) -> Offset 5
        col_off = 5 
        ws.merge_range(row_idx, col_off, row_idx, col_off+3, f"Top Thread CPU - Cycle {cycle_idx+1}", fmt_cpu_header)
        
        row_idx += 1
        
        # Sub-headers Left
        headers = ["Name", "DUT", "REF", "Diff"]
        for i, h in enumerate(headers): ws.write(row_idx, i, h, fmt_cpu_sub)
            
        # Sub-headers Right
        for i, h in enumerate(headers): ws.write(row_idx, col_off+i, h, fmt_cpu_sub)
            
        row_idx += 1
        
        # ---------------------------------------------------------
        # DRAW DATA ROWS (SIDE BY SIDE)
        # ---------------------------------------------------------
        num_rows = max(len(top_proc), len(top_thread))
        
        for r in range(num_rows):
            # --- Draw Left (Process) ---
            if r < len(top_proc):
                item = top_proc[r]
                ws.write(row_idx, 0, item['name'], fmt_cpu_text)
                write_value_or_empty(ws, row_idx, 1, item['dut'], fmt_cpu_val)
                write_value_or_empty(ws, row_idx, 2, item['ref'], fmt_cpu_val)
                
                diff = item['diff']
                fmt = fmt_diff_slow if diff > 50 else (fmt_diff_fast if diff < -50 else fmt_diff_norm)
                write_value_or_empty(ws, row_idx, 3, diff, fmt)
            else:
                # Fill borders if empty
                for c in range(4): ws.write(row_idx, c, "", fmt_cpu_val)

            # --- Draw Right (Thread) ---
            if r < len(top_thread):
                item = top_thread[r]
                ws.write(row_idx, col_off+0, item['name'], fmt_cpu_text)
                write_value_or_empty(ws, row_idx, col_off+1, item['dut'], fmt_cpu_val)
                write_value_or_empty(ws, row_idx, col_off+2, item['ref'], fmt_cpu_val)
                
                diff = item['diff']
                fmt = fmt_diff_slow if diff > 50 else (fmt_diff_fast if diff < -50 else fmt_diff_norm)
                write_value_or_empty(ws, row_idx, col_off+3, diff, fmt)
            else:
                for c in range(4): ws.write(row_idx, col_off+c, "", fmt_cpu_val)
                
            row_idx += 1
            
        row_idx += 1 # Space between cycles

    # Set Column Widths
    # Process
    ws.set_column(0, 0, 35) # Process Name
    ws.set_column(1, 3, 10) # Values
    
    # Gap
    ws.set_column(4, 4, 2)  # Cột E nhỏ lại làm vách ngăn
    
    # Thread
    ws.set_column(5, 5, 40) # Thread Name (Process)
    ws.set_column(6, 8, 10) # Values
    

    # ---------------------------------------------------------
    # === PRIORITY STATICS TABLE (FULL & FINAL) ===
    # ---------------------------------------------------------
    row_idx += 3
    
    # 1. DEFINING FORMATS
    # Header chính (Priority Statics) - Màu tím nhạt, chữ đậm, border
    fmt_prio_main_title = wb.add_format({
        "bold": True, "align": "center", "valign": "vcenter", 
        "bg_color": "#D8BFD8", "border": 1, "border_color": "#000000", "font_size": 12
    })
    
    # Header cột (DUT Cy1...)
    fmt_prio_col_header = wb.add_format({
        "bold": True, "align": "center", "bg_color": "#E6E6FA", "border": 1, "border_color": "#000000"
    })
    
    # Category Row (bindApplication...) - Merge, bg xám, chữ đen/đậm
    fmt_prio_cat_merge = wb.add_format({
        "bold": True, "align": "left", "valign": "vcenter",
        "bg_color": "#D3D3D3", "font_color": "#000000",
        "border": 1, "border_color": "#000000"
    })
    
    # Value Cell - Percentage
    fmt_prio_val = wb.add_format({
        "num_format": "0.00%", "align": "center", "border": 1, "border_color": "#000000"
    }) 
    
    # Priority Label Cell (120, 98...)
    fmt_prio_label = wb.add_format({
        "align": "left", "bold": True, "border": 1, "border_color": "#000000"
    })

    # Frequency Label Cell (@1800MHz...) - Nghiêng, căn phải
    fmt_prio_freq_label = wb.add_format({
        "align": "right", "italic": True, "font_color": "#555555", 
        "border": 1, "border_color": "#000000"
    })

    # 2. PREPARE DATA
    all_dut_prio = [cycle.get("Priority_Data", {}) if cycle else {} for cycle in dut_cycles]
    all_ref_prio = [cycle.get("Priority_Data", {}) if cycle else {} for cycle in ref_cycles]
    
    categories = ['bindApplication', 'activityStart', 'activityResume', 'Choreographer']
    
    # Check if any data exists
    has_prio_data = False
    for cycle_data in all_dut_prio + all_ref_prio:
        if cycle_data: has_prio_data = True; break
    
    if has_prio_data:
        # Xác định cột cuối cùng của bảng
        last_col = 1 + len(dut_cycles) + len(ref_cycles) - 1 
        
        # 3. DRAW MAIN TITLE (MERGED)
        ws.merge_range(row_idx, 0, row_idx, last_col, "Priority Statics", fmt_prio_main_title)
        row_idx += 1
        
        # 4. DRAW COLUMN HEADERS
        ws.write(row_idx, 0, "Category/Priority", fmt_prio_col_header)
        
        col_idx = 1
        for i in range(1, len(dut_cycles) + 1):
            ws.write(row_idx, col_idx, f"DUT Cy{i}", fmt_prio_col_header)
            col_idx += 1
        
        for i in range(1, len(ref_cycles) + 1):
            ws.write(row_idx, col_idx, f"REF Cy{i}", fmt_prio_col_header)
            col_idx += 1
            
        row_idx += 1
        
        # --- Helper Functions ---
        def parse_prio_key(k_str):
            """Parse key '120_1800' -> (120, 1800)"""
            try:
                if '_' in str(k_str):
                    p, f = str(k_str).split('_')
                    return int(p), int(f)
                return int(k_str), 0
            except:
                return 0, 0

        def get_category_total_time(c_data):
            """Tổng thời gian chạy của cả category (Mẫu số)"""
            return sum(c_data.values())

        def get_prio_breakdown(c_data, target_prio):
            """
            Trả về: (Tổng thời gian của Priority, List các (freq, time) của priority đó)
            """
            total_p_time = 0.0
            freq_list = []
            for k, v in c_data.items():
                p, f = parse_prio_key(k)
                if p == target_prio:
                    total_p_time += v
                    if f > 0: # Chỉ add nếu có frequency hợp lệ
                        freq_list.append((f, v))
            
            # Sort freq giảm dần (High freq first)
            freq_list.sort(key=lambda x: x[0], reverse=True)
            return total_p_time, freq_list

        # 5. DRAW DATA BY CATEGORY
        for category in categories:
            # 5a. Tìm tất cả Priority ID xuất hiện trong Category này
            all_seen_priorities = set()
            
            # Quét toàn bộ DUT và REF để lấy danh sách Priority duy nhất
            for data_pool in [all_dut_prio, all_ref_prio]:
                for cycle_data in data_pool:
                    cat_data = cycle_data.get(category, {})
                    for key in cat_data.keys():
                        p_id, _ = parse_prio_key(key)
                        if p_id > 0: all_seen_priorities.add(p_id)
            
            if not all_seen_priorities:
                continue 
                
            sorted_priorities = sorted(list(all_seen_priorities), reverse=True) # Priority cao (số nhỏ) hoặc tùy ý
            
            # 5b. Vẽ Category Header (MERGED ROW)
            ws.merge_range(row_idx, 0, row_idx, last_col, category, fmt_prio_cat_merge)
            row_idx += 1
            
            # 5c. Vẽ từng Priority Group
            for prio in sorted_priorities:
                # --- A. DÒNG TỔNG PRIORITY (Vd: 120) ---
                ws.write(row_idx, 0, str(prio), fmt_prio_label)
                col_idx = 1
                
                # Fill DUT & REF (Total Prio %)
                for pool in [all_dut_prio, all_ref_prio]:
                    for i in range(len(dut_cycles)): # Assume symmetric cycle count or check len
                        val = ""
                        if i < len(pool):
                            cycle_data = pool[i].get(category, {})
                            if cycle_data:
                                total_run = get_category_total_time(cycle_data)
                                p_time, _ = get_prio_breakdown(cycle_data, prio)
                                if total_run > 0 and p_time > 0:
                                    val = p_time / total_run
                        
                        write_value_or_empty(ws, row_idx, col_idx, val, fmt_prio_val)
                        col_idx += 1
                row_idx += 1
                
                # --- B. CÁC DÒNG FREQUENCY CON (Vd: @1800MHz) ---
                # Tìm tập hợp Frequency của Priority này để vẽ
                seen_freqs = set()
                for pool in [all_dut_prio, all_ref_prio]:
                    for cycle_data in pool:
                        cat_data = cycle_data.get(category, {})
                        _, f_list = get_prio_breakdown(cat_data, prio)
                        for f, _ in f_list: seen_freqs.add(f)
                
                sorted_freqs = sorted(list(seen_freqs), reverse=True)
                
                for freq in sorted_freqs:
                    ws.write(row_idx, 0, f"{freq}MHz", fmt_prio_freq_label)
                    col_idx = 1
                    
                    # Fill DUT & REF (Freq %)
                    for pool in [all_dut_prio, all_ref_prio]:
                        for i in range(len(dut_cycles)):
                            val = ""
                            if i < len(pool):
                                cycle_data = pool[i].get(category, {})
                                if cycle_data:
                                    total_run = get_category_total_time(cycle_data)
                                    # Construct exact key
                                    key = f"{prio}_{freq}"
                                    f_time = cycle_data.get(key, 0.0)
                                    
                                    if total_run > 0 and f_time > 0:
                                        val = f_time / total_run # % đóng góp của Freq này trong Tổng thời gian chạy
                            
                            write_value_or_empty(ws, row_idx, col_idx, val, fmt_prio_val)
                            col_idx += 1
                    row_idx += 1


    # # ---------------------------------------------------------
    # # === LAYOUT ANALYSIS (UNIQUE SLICES) (NEW) ===
    # # ---------------------------------------------------------
    # row_idx += 3
    
    # # Formats
    # fmt_layout_header = wb.add_format({"bold": True, "align": "center", "bg_color": "#FFDAB9", "border": 1, "border_color": "#000000"}) # Peach Puff
    # fmt_layout_cat = wb.add_format({"bold": True, "align": "left", "bg_color": "#808080", "font_color": "#FFFFFF", "border": 1}) # Dark Grey
    # fmt_layout_depth = wb.add_format({"bold": True, "align": "left", "indent": 1, "bg_color": "#F0F8FF", "border": 1}) # Alice Blue
    # fmt_layout_val = wb.add_format({"align": "left", "text_wrap": True, "valign": "top", "border": 1, "font_size": 9}) # Wrap text cho dễ đọc

    # # Prepare Data
    # all_dut_layout = [cycle.get("Layout_Data", {}) if cycle else {} for cycle in dut_cycles]
    # all_ref_layout = [cycle.get("Layout_Data", {}) if cycle else {} for cycle in ref_cycles]
    
    # layout_cats = ['bindApplication', 'activityStart', 'activityResume', 'Choreographer']
    # max_depth_check = 6
    
    # # Check data exists
    # has_layout_data = False
    # for d in all_dut_layout + all_ref_layout:
    #     if d: has_layout_data = True; break
        
    # if has_layout_data:
    #     # 1. Header Structure
    #     ws.merge_range(row_idx, 0, row_idx, 0, "Unique Layout Analysis (Set Diff)", fmt_layout_header)
    #     col_idx = 1
    #     for i in range(len(dut_cycles)):
    #         ws.write(row_idx, col_idx, f"DUT Cy{i+1} (Unique)", fmt_layout_header)
    #         col_idx += 1
    #     for i in range(len(ref_cycles)):
    #         ws.write(row_idx, col_idx, f"REF Cy{i+1} (Unique)", fmt_layout_header)
    #         col_idx += 1
    #     row_idx += 1
        
    #     # 2. Loop Categories
    #     for cat in layout_cats:
    #         # Draw Category Header (Merged)
    #         last_col = 1 + len(dut_cycles) + len(ref_cycles) - 1
    #         ws.merge_range(row_idx, 0, row_idx, last_col, cat, fmt_layout_cat)
    #         row_idx += 1
            
    #         # 3. Loop Depths
    #         for depth in range(max_depth_check + 1):
    #             ws.write(row_idx, 0, f"Depth {depth}", fmt_layout_depth)
    #             col_idx = 1
                
    #             # Để so sánh, ta cần dữ liệu của cả DUT và REF tại cycle i.
    #             # Giả sử so sánh cặp: DUT Cy1 vs REF Cy1. 
    #             # Nếu thiếu 1 bên (vd REF không có Cy3), thì bên còn lại coi như Unique toàn bộ.
                
    #             # --- FILL DUT COLUMNS ---
    #             for i in range(len(dut_cycles)):
    #                 val_str = ""
    #                 if i < len(all_dut_layout):
    #                     dut_slices = []
    #                     if all_dut_layout[i].get(cat):
    #                         dut_slices = all_dut_layout[i][cat].get(depth, [])
                        
    #                     # Lấy REF tương ứng để compare
    #                     ref_slices = []
    #                     if i < len(all_ref_layout) and all_ref_layout[i].get(cat):
    #                         ref_slices = all_ref_layout[i][cat].get(depth, [])
                            
    #                     # Logic: DUT Unique = DUT - REF
    #                     dut_set = set(dut_slices)
    #                     ref_set = set(ref_slices)
                        
    #                     diff = dut_set - ref_set
                        
    #                     if diff:
    #                         # Convert back to list and sort for readability
    #                         val_str = ", ".join(sorted(list(diff)))
    #                     elif not dut_set and not ref_set:
    #                         val_str = "" # Cả 2 đều trống
    #                     elif not diff:
    #                         val_str = "" # Giống hệt nhau (hoặc DUT là tập con của REF)

    #                 ws.write(row_idx, col_idx, val_str, fmt_layout_val)
    #                 col_idx += 1
                    
    #             # --- FILL REF COLUMNS ---
    #             for i in range(len(ref_cycles)):
    #                 val_str = ""
    #                 if i < len(all_ref_layout):
    #                     ref_slices = []
    #                     if all_ref_layout[i].get(cat):
    #                         ref_slices = all_ref_layout[i][cat].get(depth, [])
                            
    #                     # Lấy DUT tương ứng để compare
    #                     dut_slices = []
    #                     if i < len(all_dut_layout) and all_dut_layout[i].get(cat):
    #                         dut_slices = all_dut_layout[i][cat].get(depth, [])
                            
    #                     # Logic: REF Unique = REF - DUT
    #                     dut_set = set(dut_slices)
    #                     ref_set = set(ref_slices)
                        
    #                     diff = ref_set - dut_set
                        
    #                     if diff:
    #                         val_str = ", ".join(sorted(list(diff)))

    #                 ws.write(row_idx, col_idx, val_str, fmt_layout_val)
    #                 col_idx += 1
                
    #             # Tăng row sau mỗi Depth
    #             row_idx += 1

    # =============== Top Block I/O Table (MOVED TO POSITION 5) ================
    row_idx += 3
    
    # Formats cho Block I/O table
    fmt_blockio_header = wb.add_format({"bold": True, "align": "center", "bg_color": "#ADD8E6", "border": 1, "border_color": "#000000"})
    fmt_blockio_val = wb.add_format({"num_format": "0.000", "align": "center", "border": 1, "border_color": "#000000"})
    
    # Thu thập Block I/O data từ tất cả cycles
    all_dut_block_io = [cycle.get("Block_IO_Data", []) if cycle else [] for cycle in dut_cycles]
    all_ref_block_io = [cycle.get("Block_IO_Data", []) if cycle else [] for cycle in ref_cycles]
    
    # Lấy danh sách tất cả library names xuất hiện
    all_library_names = set()
    for cycle_data in all_dut_block_io:
        for lib in cycle_data:
            all_library_names.add(lib['libraryName'])
    for cycle_data in all_ref_block_io:
        for lib in cycle_data:
            all_library_names.add(lib['libraryName'])
    
    # Nếu không có data, skip
    if not all_library_names:
        row_idx += 3  
    else:
        # ---------------------------------------------------------
        # BƯỚC 1: Tính toán Avg và Diff cho từng Library để Sort
        # ---------------------------------------------------------
        lib_stats = []
        for lib_name in all_library_names:
            # Tính DUT Stats (Lấy timeTotal_ms)
            dut_times = []
            for cycle_data in all_dut_block_io:
                # Tìm library trong cycle này, nếu không có trả về 0.0
                found_ms = next((item['timeTotal_ms'] for item in cycle_data if item['libraryName'] == lib_name), 0.0)
                dut_times.append(found_ms)
            
            dut_avg = sum(dut_times) / len(dut_times) if dut_times else 0.0

            # Tính REF Stats (Lấy timeTotal_ms)
            ref_times = []
            for cycle_data in all_ref_block_io:
                found_ms = next((item['timeTotal_ms'] for item in cycle_data if item['libraryName'] == lib_name), 0.0)
                ref_times.append(found_ms)
            
            ref_avg = sum(ref_times) / len(ref_times) if ref_times else 0.0

            # Tính Diff
            diff = dut_avg - ref_avg
            
            if (diff > 0):
                lib_stats.append({
                'name': lib_name,
                'dut_times': dut_times,
                'dut_avg': dut_avg,
                'ref_times': ref_times,
                'ref_avg': ref_avg,
                'diff': diff
            })
        # ---------------------------------------------------------
        # BƯỚC 2: Sort theo Diff giảm dần (Cao xuống thấp)
        # ---------------------------------------------------------
        sorted_lib_stats = sorted(lib_stats, key=lambda x: x['diff'], reverse=True)

        # ---------------------------------------------------------
        # BƯỚC 3: Vẽ Header (Bỏ cột Count, Thêm Avg & Diff)
        # ---------------------------------------------------------
        
        # Merge Header chính
        # Cấu trúc: Name | DUT Cy... | DUT Avg | REF Cy... | REF Avg | Diff
        total_cols = 1 + len(dut_cycles) + 1 + len(ref_cycles) + 1 + 1 
        ws.merge_range(row_idx, 0, row_idx, total_cols - 1, "Top Block I/O Libraries", fmt_blockio_header)
        
        row_idx += 1
        ws.write(row_idx, 0, "Library Name", fmt_blockio_header)
        
        col_idx = 1
        # DUT Headers
        for i in range(1, len(dut_cycles) + 1):
            ws.write(row_idx, col_idx, f"DUT Cy{i}", fmt_blockio_header)
            col_idx += 1
        ws.write(row_idx, col_idx, "DUT Avg", fmt_blockio_header)
        col_idx += 1
        
        # REF Headers
        for i in range(1, len(ref_cycles) + 1):
            ws.write(row_idx, col_idx, f"REF Cy{i}", fmt_blockio_header)
            col_idx += 1
        ws.write(row_idx, col_idx, "REF Avg", fmt_blockio_header)
        col_idx += 1
        
        # Diff Header
        ws.write(row_idx, col_idx, "Diff", fmt_blockio_header)

        # Set width
        ws.set_column(0, 0, 50)       # Library name rộng hơn
        ws.set_column(1, col_idx, 12) # Các cột giá trị

        # ---------------------------------------------------------
        # BƯỚC 4: Ghi Data
        # ---------------------------------------------------------
        row_idx += 1
        for lib in sorted_lib_stats:
            ws.write(row_idx, 0, lib['name'], fmt_label)
            col_idx = 1
            
            # Write DUT Cycles
            for val in lib['dut_times']:
                write_value_or_empty(ws, row_idx, col_idx, val, fmt_blockio_val)
                col_idx += 1
            
            # Write DUT Avg
            write_value_or_empty(ws, row_idx, col_idx, lib['dut_avg'], fmt_blockio_val)
            col_idx += 1
            
            # Write REF Cycles
            for val in lib['ref_times']:
                write_value_or_empty(ws, row_idx, col_idx, val, fmt_blockio_val)
                col_idx += 1
            
            # Write REF Avg
            write_value_or_empty(ws, row_idx, col_idx, lib['ref_avg'], fmt_blockio_val)
            col_idx += 1
            
            # Write Diff (Tô màu nếu chênh lệch lớn)
            diff_val = lib['diff']
            if diff_val > 50:
                fmt_diff = fmt_diff_slow
            elif diff_val < -50:
                fmt_diff = fmt_diff_fast
            else:
                fmt_diff = fmt_diff_normal
            
            write_value_or_empty(ws, row_idx, col_idx, diff_val, fmt_diff)
            
            row_idx += 1
    
    
    # ---------------------------------------------------------
    # === LoadApkAssets Table (UPDATED FOR CATEGORIES) ===
    # ---------------------------------------------------------
    row_idx += 3

    # Thu thập data từ tất cả cycles
    # Lưu ý: Mỗi cycle data bây giờ là Dict {'system_server': [], 'system_ui': [], ...}
    all_dut_loadapk = [cycle.get("LoadApkAsset_Data", {}) if cycle else {} for cycle in dut_cycles]
    all_ref_loadapk = [cycle.get("LoadApkAsset_Data", {}) if cycle else {} for cycle in ref_cycles]

    # Các category cần hiển thị theo thứ tự
    target_categories = ["system_server", "system_ui", "launching_app"]

    # Kiểm tra xem có dữ liệu nào không để quyết định vẽ bảng
    has_data = False
    for cycle_data in all_dut_loadapk + all_ref_loadapk:
        if not isinstance(cycle_data, dict): continue # Skip nếu data cũ/lỗi
        for cat in target_categories:
            if cycle_data.get(cat):
                has_data = True
                break
        if has_data: break

    if has_data:
        # === HEADER ROW ===
        ws.merge_range(row_idx, 0, row_idx, 0, "LoadApkAssets (>50ms)", fmt_blockio_header)
        
        col_idx = 1
        for i in range(1, len(dut_cycles) + 1):
            ws.write(row_idx, col_idx, f"DUT Cycle {i}", fmt_blockio_header)
            col_idx += 1
        
        for i in range(1, len(ref_cycles) + 1):
            ws.write(row_idx, col_idx, f"REF Cycle {i}", fmt_blockio_header)
            col_idx += 1
        
        # === SUB-HEADER ROW ===
        row_idx += 1
        ws.write(row_idx, 0, "Category / Asset Name", fmt_blockio_header)
        
        col_idx = 1
        for _ in range(len(dut_cycles)):
            ws.write(row_idx, col_idx, "(ms)", fmt_blockio_header)
            col_idx += 1
        for _ in range(len(ref_cycles)):
            ws.write(row_idx, col_idx, "(ms)", fmt_blockio_header)
            col_idx += 1
        
        ws.set_column(0, 0, 50)
        
        # === DATA ROWS ===
        row_idx += 1

        for category in target_categories:
            # 1. Thu thập tất cả tên Asset trong category này từ mọi cycle
            cat_asset_names = set()
            for cycle_data in all_dut_loadapk + all_ref_loadapk:
                if isinstance(cycle_data, dict):
                    assets = cycle_data.get(category, [])
                    for a in assets:
                        cat_asset_names.add(a['name'])
            
            sorted_assets = sorted(list(cat_asset_names))

            if not sorted_assets:
                continue

            # 2. Hiển thị tên Category (In đậm, Background màu tối hoặc khác biệt)
            # Merge hết các cột để làm tiêu đề ngăn cách
            total_cols_table = 1 + len(dut_cycles) + len(ref_cycles)
            ws.merge_range(row_idx, 0, row_idx, total_cols_table - 1, category.title(), fmt_section_header)
            row_idx += 1

            # 3. Vẽ từng Asset trong category đó
            for asset_name in sorted_assets:
                ws.write(row_idx, 0, asset_name, fmt_label)
                col_idx = 1

                # Fill DUT Cycles
                for cycle_data in all_dut_loadapk:
                    val = ""
                    if isinstance(cycle_data, dict):
                        assets = cycle_data.get(category, [])
                        found_item = next((x for x in assets if x['name'] == asset_name), None)
                        if found_item:
                            val = found_item['dur_ms']
                    
                    write_value_or_empty(ws, row_idx, col_idx, val, fmt_blockio_val)
                    col_idx += 1
                
                # Fill REF Cycles
                for cycle_data in all_ref_loadapk:
                    val = ""
                    if isinstance(cycle_data, dict):
                        assets = cycle_data.get(category, [])
                        found_item = next((x for x in assets if x['name'] == asset_name), None)
                        if found_item:
                            val = found_item['dur_ms']
                    
                    write_value_or_empty(ws, row_idx, col_idx, val, fmt_blockio_val)
                    col_idx += 1
                
                row_idx += 1

    # ---------------------------------------------------------
    # === Statistics Table (Binder Transaction, etc.) ===
    # ---------------------------------------------------------
    row_idx += 3
    
    # Thu thập Binder Transaction data từ tất cả cycles
    all_dut_binder = [cycle.get("Binder_Transaction_Data", {}) if cycle else {} for cycle in dut_cycles]
    # print("all_dut_binder", all_dut_binder)
    all_ref_binder = [cycle.get("Binder_Transaction_Data", {}) if cycle else {} for cycle in ref_cycles]
    
    # Format cho Statistics table
    fmt_stats_header = wb.add_format({"bold": True, "align": "center", "bg_color": "#E6E6FA", "border": 1, "border_color": "#000000"})
    fmt_stats_subheader = wb.add_format({"bold": True, "align": "center", "bg_color": "#F0E68C", "border": 1, "border_color": "#000000"})
    fmt_stats_val = wb.add_format({"num_format": "0.000", "align": "center", "border": 1, "border_color": "#000000"})
    fmt_stats_count = wb.add_format({"num_format": "0", "align": "center", "border": 1, "border_color": "#000000"})
    fmt_stats_empty = wb.add_format({"align": "center", "border": 1, "border_color": "#000000"})
    
    # Header row
    ws.merge_range(row_idx, 0, row_idx, 0, "Thống kê", fmt_stats_header)
    
    col_idx = 1
    # DUT cycles headers (merge 2 columns for each: Dur + Count)
    for i in range(1, len(dut_cycles) + 1):
        ws.merge_range(row_idx, col_idx, row_idx, col_idx + 1, f"DUT Cycle {i}", fmt_stats_header)
        col_idx += 2
    
    # Avg DUT header
    ws.merge_range(row_idx, col_idx, row_idx, col_idx + 1, "Avg DUT", fmt_stats_header)
    col_idx += 2
    
    # REF cycles headers
    for i in range(1, len(ref_cycles) + 1):
        ws.merge_range(row_idx, col_idx, row_idx, col_idx + 1, f"REF Cycle {i}", fmt_stats_header)
        col_idx += 2
    
    # Avg REF header
    ws.merge_range(row_idx, col_idx, row_idx, col_idx + 1, "Avg REF", fmt_stats_header)
    col_idx += 2
    
    # Diff header
    ws.merge_range(row_idx, col_idx, row_idx, col_idx + 1, "Diff", fmt_stats_header)
    
    # Sub-header row (Dur | Count pattern)
    row_idx += 1
    ws.write(row_idx, 0, "Name", fmt_stats_subheader)
    
    col_idx = 1
    # DUT cycles sub-headers
    for i in range(len(dut_cycles)):
        ws.write(row_idx, col_idx, "Dur", fmt_stats_subheader)
        ws.write(row_idx, col_idx + 1, "Count", fmt_stats_subheader)
        col_idx += 2
    
    # Avg DUT sub-headers
    ws.write(row_idx, col_idx, "Dur", fmt_stats_subheader)
    ws.write(row_idx, col_idx + 1, "Count", fmt_stats_subheader)
    col_idx += 2
    
    # REF cycles sub-headers
    for i in range(len(ref_cycles)):
        ws.write(row_idx, col_idx, "Dur", fmt_stats_subheader)
        ws.write(row_idx, col_idx + 1, "Count", fmt_stats_subheader)
        col_idx += 2
    
    # Avg REF sub-headers
    ws.write(row_idx, col_idx, "Dur", fmt_stats_subheader)
    ws.write(row_idx, col_idx + 1, "Count", fmt_stats_subheader)
    col_idx += 2
    
    # Diff sub-headers
    ws.write(row_idx, col_idx, "Dur", fmt_stats_subheader)
    ws.write(row_idx, col_idx + 1, "Count", fmt_stats_subheader)
    
    # Data row: binder transaction
    row_idx += 1
    ws.write(row_idx, 0, "binder transaction", fmt_label)
    
    col_idx = 1
    
    # DUT cycles data
    dut_dur_values = []
    dut_count_values = []
    for binder_data in all_dut_binder:
        dur = binder_data.get('duration_ms', 0.0)
        count = binder_data.get('count', 0)
        
        write_value_or_empty(ws, row_idx, col_idx, dur, fmt_stats_val)
        ws.write(row_idx, col_idx + 1, count if count > 0 else "", fmt_stats_count)
        
        dut_dur_values.append(dur)
        dut_count_values.append(count)
        col_idx += 2
    
    # Avg DUT
    avg_dut_dur = sum(dut_dur_values) / len(dut_dur_values) if dut_dur_values else 0.0
    avg_dut_count = sum(dut_count_values) / len(dut_count_values) if dut_count_values else 0.0
    
    write_value_or_empty(ws, row_idx, col_idx, avg_dut_dur, fmt_stats_val)
    ws.write(row_idx, col_idx + 1, int(avg_dut_count) if avg_dut_count > 0 else "", fmt_stats_count)
    col_idx += 2
    
    # REF cycles data
    ref_dur_values = []
    ref_count_values = []
    for binder_data in all_ref_binder:
        dur = binder_data.get('duration_ms', 0.0)
        count = binder_data.get('count', 0)
        
        write_value_or_empty(ws, row_idx, col_idx, dur, fmt_stats_val)
        ws.write(row_idx, col_idx + 1, count if count > 0 else "", fmt_stats_count)
        
        ref_dur_values.append(dur)
        ref_count_values.append(count)
        col_idx += 2
    
    # Avg REF
    avg_ref_dur = sum(ref_dur_values) / len(ref_dur_values) if ref_dur_values else 0.0
    avg_ref_count = sum(ref_count_values) / len(ref_count_values) if ref_count_values else 0.0
    
    write_value_or_empty(ws, row_idx, col_idx, avg_ref_dur, fmt_stats_val)
    ws.write(row_idx, col_idx + 1, int(avg_ref_count) if avg_ref_count > 0 else "", fmt_stats_count)
    col_idx += 2
    
    # Diff (DUT - REF)
    diff_dur = avg_dut_dur - avg_ref_dur
    diff_count = int(avg_dut_count - avg_ref_count)
    
    write_value_or_empty(ws, row_idx, col_idx, diff_dur, fmt_stats_val)
    ws.write(row_idx, col_idx + 1, diff_count if diff_count != 0 else "", fmt_stats_count)
    
    # Set column widths for statistics table
    ws.set_column(0, 0, 30)
    ws.set_column(1, col_idx + 1, 10)

def extract_device_code(header_title):
    """
    Extract device code từ header_title
    Ví dụ: 
    - A166B-YLJ-4GB-BOS-TEST_251226 -> YLJ
    - A166B_YLJ_4GB_BOS_TEST_251226 -> YLJ
    """
    # Chuẩn hóa: replace tất cả '_' bằng '-'
    normalized = header_title.replace('_', '-')
    parts = normalized.split('-')
    
    if len(parts) >= 2:
        return parts[1]
    
    return ""


# ---------------------------------------------------------------------------
# JSON Export
# ---------------------------------------------------------------------------

def export_avg_to_json(
    dut_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ref_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    output_folder: str,
    dut_device_code: str,
    ref_device_code: str,
    dut_folder_path: str = "",
    ref_folder_path: str = ""
) -> None:
    """
    Xuất metrics ra file JSON.
    [UPDATED v2]
    - Tách thành nhiều file JSON theo từng app (app_name_dut.json, app_name_ref.json)
    - Chỉ lấy entry data, bỏ reentry
    - Bỏ top_cpu_by_cycle data (process + thread)
    """
    
    def calculate_metrics_for_app(cycles: List[Dict[str, Any]], app_name: str, launch_type: str, folder_path: str = "") -> Dict[str, Any]:
        """Tính toán metrics cho một app/launch_type"""
        if not cycles: return {}
        
        # Lấy danh sách các cycle hợp lệ (không bị None)
        valid_cycles_with_idx = [(i, c) for i, c in enumerate(cycles) if c is not None]
        if not valid_cycles_with_idx: return {}
        
        valid_cycles = [c for _, c in valid_cycles_with_idx]
        result = {}

        # ========================
        # 0. STATE (Per Cycle)
        # ========================
        current_state = "Cold" if launch_type == "entry" else "Warm"
        result["State"] = [current_state for _ in valid_cycles]
        
        # ========================
        # 1. SEQUENCE METRICS (AVG)
        # ========================
        sequence_metrics = [
            "App Execution Time", "Touch Down ~ Start Proc", "Start Proc",
            "Start Proc ~ ActivityThreadMain", "Activity Thread Main",
            "ActivityThreadMain ~ bindApplication", "Bind Application",
            "bindApplication ~ activityStart", "Touch Duration", "Touch Up ~ Activity Start",
            "Activity Start", "activityStart ~ activityResume", "Activity Resume",
            "ActivityResume ~ Choreographer", "Choreographer",
            "Choreographer ~ ActivityIdle", "ActivityIdle", "ActivityIdle ~ Animating end",
            "Running", "Runnable", "Uninterruptible Sleep", "Sleeping",
            "onCreate", "OpenCameraRequest", "onResume", "StartPreviewRequest"
        ]
        
        # [NEW] Định nghĩa lại keys để mask giống hệt Excel
        COLD_ONLY_KEYS = {
            "Touch Down ~ Start Proc", "Start Proc", "Start Proc ~ ActivityThreadMain",
            "Activity Thread Main", "ActivityThreadMain ~ bindApplication",
            "Bind Application", "bindApplication ~ activityStart"
        }
        WARM_ONLY_KEYS = {
            "Touch Duration", "Touch Up ~ Activity Start"
        }
        
        sequence_data = {}
        for metric in sequence_metrics:
            values = []
            for cycle in valid_cycles:
                # [NEW] Masking Logic: Bỏ qua metric nếu không đúng loại Launch Type
                # c_type = cycle.get("Launch Type")
                c_type = "Cold" if launch_type == "entry" else "Warm"
                if c_type == "Cold" and metric in WARM_ONLY_KEYS:
                    continue  # Bỏ qua Touch Duration cho cycle Cold
                if c_type == "Warm" and metric in COLD_ONLY_KEYS:
                    continue  # Bỏ qua Start Proc... cho cycle Warm
                
                val = cycle.get(metric, 0.0)
                if val and val > 0: 
                    values.append(float(val))
                    
            if values: 
                sequence_data[metric] = round(sum(values) / len(values), 3)
                
        if sequence_data: result["sequence"] = sequence_data
        
        # ========================
        # 2. EXTEND METRICS
        # ========================
        extend_data = {}

        # 2.1 START PROCESS ABNORMAL (List of Lists per Cycle)
        abnormal_process_list = []
        
        for cycle in valid_cycles:
            cycle_procs = []
            bg_states = cycle.get("Abnormal_Process_Data", [])
            if bg_states:
                for item in bg_states:
                    p_name = item.get('proc_name', '')
                    if p_name:
                        cycle_procs.append(p_name)
            
            abnormal_process_list.append(cycle_procs)
            
        extend_data["start_process_abnormal"] = abnormal_process_list

        # 2.2 LoadApkAssets
        loadapk_categories = ["system_server", "system_ui", "launching_app"]
        loadapk_data = {}
        for category in loadapk_categories:
            values = []
            for cycle in valid_cycles:
                cycle_loadapk = cycle.get("LoadApkAsset_Data", {})
                if isinstance(cycle_loadapk, dict):
                    assets = cycle_loadapk.get(category, [])
                    total = sum(item.get('dur_ms', 0.0) for item in assets)
                    if total > 0: values.append(total)
            if values: loadapk_data[category] = round(sum(values) / len(values), 3)
        if loadapk_data: extend_data["loadapkassets"] = loadapk_data
        
        # 2.3 Memory — [REFACTORED] Đọc từ Precomputed_Extend_Data
        if folder_path:
            memory_data = {}
            mem_free_vals, mem_avail_vals, pss_vals, pb_vals = [], [], [], []
            
            for idx, cycle in valid_cycles_with_idx:
                precomp = cycle.get('Precomputed_Extend_Data', {})
                
                mem_free = precomp.get('MemFree', 0.0)
                if mem_free > 0: mem_free_vals.append(mem_free)
                
                mem_avail = precomp.get('MemAvailable', 0.0)
                if mem_avail > 0: mem_avail_vals.append(mem_avail)
                
                pss = precomp.get('App_PSS', 0.0)
                if pss > 0: pss_vals.append(pss)
                
                pb = precomp.get('Pageboostd', 0.0)
                if pb > 0: pb_vals.append(pb)

            if mem_free_vals: memory_data["MemFree_MB"] = round(sum(mem_free_vals)/len(mem_free_vals), 2)
            if mem_avail_vals: memory_data["MemAvailable_MB"] = round(sum(mem_avail_vals)/len(mem_avail_vals), 2)
            if pss_vals: memory_data["App_PSS_MB"] = round(sum(pss_vals)/len(pss_vals), 2)
            if pb_vals: memory_data["Pageboostd_MB"] = round(sum(pb_vals)/len(pb_vals), 2)
            if memory_data: extend_data["memory"] = memory_data
            
        # 2.4 Abnormal — [REFACTORED] Đọc từ Precomputed_Extend_Data
        if folder_path:
            abnormal_info = {}
            uptime_vals, start_reasons, kill_reasons, crash_counts, compilers = [], [], [], [], []
            
            for _, cycle in valid_cycles_with_idx:
                precomp = cycle.get('Precomputed_Extend_Data', {})
                
                ut = precomp.get('Uptime', 0)
                if ut and ut > 0: uptime_vals.append(ut)
                
                sr = precomp.get('Start_Reason', "")
                if sr:
                    # Xử lý an toàn đề phòng hàm parser trả về string hoặc list
                    if isinstance(sr, list):
                        start_reasons.extend(sr)
                    else:
                        start_reasons.append(sr)

                kr = precomp.get('Kill_Reason', [])
                if kr: kill_reasons.extend(kr)
                
                cc = precomp.get('Crash_Count', 0)
                if cc and cc > 0: crash_counts.append(cc)
                
                ct = precomp.get('Compiler', '')
                if ct: compilers.append(ct)

            if uptime_vals: abnormal_info["uptime_minutes"] = round(sum(uptime_vals)/len(uptime_vals), 2)
            if start_reasons: abnormal_info["start_reasons"] = list((start_reasons))
            if kill_reasons: abnormal_info["kill_reasons"] = list((kill_reasons))
            if crash_counts: abnormal_info["crash_count_avg"] = round(sum(crash_counts)/len(crash_counts), 1)
            if compilers:
                from collections import Counter
                abnormal_info["compiler"] = Counter(compilers).most_common(1)[0][0]
            if abnormal_info: extend_data["abnormal"] = abnormal_info
        
        if extend_data: result["extend"] = extend_data

        # =========================================================
        # 3. TOP CPU (BY CYCLE) - [REMOVED]
        # =========================================================
        # Bỏ theo yêu cầu - không cần top_cpu_by_cycle

        # =========================================================
        # 4. PRIORITY STATICS (BY CYCLE)
        # =========================================================
        priority_cycles_data = []
        prio_categories = ['bindApplication', 'activityStart', 'activityResume', 'Choreographer']
        
        for idx, cycle in valid_cycles_with_idx:
            prio_data = cycle.get("Priority_Data", {})
            cycle_result = {}
            has_data = False
            
            for cat in prio_categories:
                if cat in prio_data and prio_data[cat]:
                    raw_map = prio_data[cat]
                    total_dur = sum(raw_map.values())
                    
                    if total_dur > 0:
                        prio_acc = defaultdict(float)
                        freq_acc = defaultdict(float)
                        
                        for key, val_ms in raw_map.items():
                            parts = str(key).split('_')
                            if len(parts) >= 1:
                                p_id = parts[0]
                                prio_acc[p_id] += val_ms
                                if len(parts) >= 2 and parts[1] != "0":
                                    freq_acc[parts[1]] += val_ms

                        prio_pct = {k: round((v/total_dur)*100, 2) for k, v in prio_acc.items()}
                        freq_pct = {k: round((v/total_dur)*100, 2) for k, v in freq_acc.items()}
                        
                        cycle_result[cat] = {"priority": prio_pct, "frequency": freq_pct}
                        has_data = True
            
            if has_data: priority_cycles_data.append({"cycle": idx + 1, "data": cycle_result})
        if priority_cycles_data: result["priority_by_cycle"] = priority_cycles_data

        # 5. BLOCK I/O
        bio_cycles = []
        for idx, cycle in valid_cycles_with_idx:
            bio = sorted(cycle.get("Block_IO_Data", []), key=lambda x: x.get('timeTotalMs', 0), reverse=True)[:10]
            bio_list = [{"name": x.get('libraryName', 'Unknown'), "val": x.get('timeTotalMs', 0)} for x in bio]
            if bio_list: bio_cycles.append({"cycle": idx+1, "data": bio_list})
        if bio_cycles: result["block_io_by_cycle"] = bio_cycles
        
        # 6. BINDER
        b_durs, b_counts = [], []
        for cycle in valid_cycles:
            b = cycle.get("Binder_Transaction_Data", {})
            if b.get('duration_ms', 0) > 0: b_durs.append(b['duration_ms'])
            if b.get('count', 0) > 0: b_counts.append(b['count'])
        if b_durs or b_counts:
            result["binder_transaction"] = {
                "duration_ms": round(sum(b_durs)/len(b_durs), 3) if b_durs else 0,
                "count": int(sum(b_counts)/len(b_counts)) if b_counts else 0
            }

        return result

    # =====================
    # BUILD & WRITE PER-APP JSON FILES
    # =====================
    timestamp = datetime.datetime.now().isoformat()
    
    # Lấy danh sách tất cả apps từ cả DUT và REF
    all_apps = set(dut_results.keys()) | set(ref_results.keys())
    
    # Tạo output directory
    output_dir = os.path.join(output_folder, "Output")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n Exporting per-app JSON files...")
    
    # Export từng app cho DUT và REF
    for app_name in sorted(all_apps):
        # =====================
        # DUT - Chỉ lấy entry
        # =====================
        dut_entry_cycles = dut_results.get(app_name, {}).get("entry", [])
        if dut_entry_cycles:
            dut_metrics = calculate_metrics_for_app(dut_entry_cycles, app_name, "entry", dut_folder_path)
            if dut_metrics:
                # Flatten structure: device_code, timestamp, type, app, entry
                dut_json = {
                    "device_code": dut_device_code,
                    "timestamp": timestamp,
                    "type": "DUT",
                    "app": app_name,
                    "entry": dut_metrics
                }
                
                # Write to file: app_name_dut.json
                dut_file_path = os.path.join(output_dir, f"{app_name}_dut.json")
                with open(dut_file_path, 'w', encoding='utf-8') as f:
                    json.dump(dut_json, f, indent=2, ensure_ascii=False)
                print(f"  Created: {app_name}_dut.json")
        
        # =====================
        # REF - Chỉ lấy entry
        # =====================
        ref_entry_cycles = ref_results.get(app_name, {}).get("entry", [])
        if ref_entry_cycles:
            ref_metrics = calculate_metrics_for_app(ref_entry_cycles, app_name, "entry", ref_folder_path)
            if ref_metrics:
                # Flatten structure
                ref_json = {
                    "device_code": ref_device_code,
                    "timestamp": timestamp,
                    "type": "REF",
                    "app": app_name,
                    "entry": ref_metrics
                }
                
                # Write to file: app_name_ref.json
                ref_file_path = os.path.join(output_dir, f"{app_name}_ref.json")
                with open(ref_file_path, 'w', encoding='utf-8') as f:
                    json.dump(ref_json, f, indent=2, ensure_ascii=False)
                print(f"  Created: {app_name}_ref.json")



# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def get_or_process_folder_with_cache(folder_path: str, label: str, num_workers: int, target_apps: List[str], extracted: bool):
    """
    Xử lý quét Trace với Incremental Smart Cache (Cache Cộng Dồn).
    Tự động nhận diện App còn thiếu, chỉ quét bù những App đó và gộp vào Cache cũ.
    """
    cache_path = os.path.join(folder_path, ".perf_cache.pkl")
    
    # Chuẩn hóa danh sách App user yêu cầu hiện tại (None = ALL APPS)
    current_targets = sorted(target_apps) if target_apps else None
    
    cached_data = {}
    cached_targets = []
    cache_valid = False
    
    # 1. ĐỌC CACHE HIỆN TẠI
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                cache_content = pickle.load(f)
            
            # Kiểm tra format và CACHE_VERSION
            if isinstance(cache_content, dict) and cache_content.get("version") == CACHE_VERSION:
                cached_targets = cache_content.get("target_apps")
                cached_data = cache_content.get("data", {})
                cache_valid = True
                print(f"  -> [{label}] Found valid cache file (Version {CACHE_VERSION}).")
            else:
                print(f"  -> [{label}] Cache version mismatch or invalid format. Ignoring old cache...")
        except Exception as e:
            print(f"  -> [{label}] [ERROR] Failed to read cache: {e}. Processing from scratch...")

    # 2. XỬ LÝ LOGIC TÌM APP CÒN THIẾU (MISSING APPS)
    missing_apps = None # Mặc định None là quét tất cả (ALL APPS)
    
    if cache_valid:
        if current_targets is None:
            # TH1: User muốn ALL APPS
            if cached_targets is None:
                print(f"  -> [{label}] Cache already contains ALL APPS. Loading (⚡)...")
                return cached_data
            else:
                print(f"  -> [{label}] Requested ALL APPS, but cache only has {cached_targets}.")
                print(f"  -> [{label}] Must process ALL from scratch...")
                cached_data = {} # Reset data cũ để tạo cache ALL mới
                
        else:
            # TH2: User muốn danh sách App cụ thể
            if cached_targets is None:
                # Cache có ALL APPS, chỉ việc trích xuất tập con
                print(f"  -> [{label}] Cache contains ALL APPS. Extracting {current_targets} (⚡)...")
                return {app: data for app, data in cached_data.items() if app in current_targets}
            else:
                # Tính danh sách App còn thiếu
                missing_apps = sorted(list(set(current_targets) - set(cached_targets)))
                
                if not missing_apps:
                    print(f"  -> [{label}] All requested apps {current_targets} are in cache. Extracting (⚡)...")
                    return {app: data for app, data in cached_data.items() if app in current_targets}
                else:
                    print(f"  -> [{label}] Cache is missing apps: {missing_apps}.")
                    print(f"  -> [{label}] Will process ONLY missing apps and MERGE...")
    else:
        # Không có cache hợp lệ
        missing_apps = current_targets

    # 3. CHẠY QUÉT TRACE (CHỈ CHO NHỮNG APP CÒN THIẾU)
    print(f"  -> [{label}] Processing trace files for: {missing_apps if missing_apps else 'ALL APPS'}...")
    new_data = process_all_traces(folder_path, label, num_workers, missing_apps, extracted)
    
    # 4. GỘP DỮ LIỆU (MERGE)
    # Gộp từ điển: Data cũ + Data mới
    merged_data = {**cached_data, **new_data}
    
    # Gộp danh sách target_apps
    if missing_apps is None or cached_targets is None:
        merged_targets = None # Đại diện cho ALL APPS
    else:
        merged_targets = sorted(list(set(cached_targets) | set(missing_apps)))

    # 5. LƯU LẠI CACHE ĐÃ GỘP
    try:
        cache_content_to_save = {
            "version": CACHE_VERSION,
            "target_apps": merged_targets,
            "data": merged_data
        }
        with open(cache_path, 'wb') as f:
            pickle.dump(cache_content_to_save, f)
        print(f"  -> [{label}] Saved MERGED data to cache: {cache_path}")
    except Exception as e:
        print(f"  -> [{label}] [WARN] Could not save cache: {e}")
        
    # 6. TRẢ VỀ CHÍNH XÁC NHỮNG GÌ USER YÊU CẦU LẦN NÀY
    if current_targets is None:
        return merged_data
    else:
        # Lọc lại chỉ lấy data của các app nằm trong current_targets
        return {app: data for app, data in merged_data.items() if app in current_targets}


# def get_or_process_folder_with_cache(folder_path: str, label: str, num_workers: int, target_apps: List[str], extracted: bool):
#     """
#     Xử lý quét Trace với Smart Cache (Target-App Aware & Subset-Aware).
#     Có thể trích xuất data nếu user chỉ yêu cầu một phần của Cache.
#     """
#     cache_path = os.path.join(folder_path, ".perf_cache.pkl")
    
#     # Chuẩn hóa target_apps hiện tại
#     current_targets = sorted(target_apps) if target_apps else None
    
#     if os.path.exists(cache_path):
#         print(f"  -> [{label}] Found cache file: {cache_path}")
#         try:
#             with open(cache_path, 'rb') as f:
#                 cache_content = pickle.load(f)
            
#             if isinstance(cache_content, dict) and "target_apps" in cache_content and "data" in cache_content:
#                 cached_targets = cache_content["target_apps"]
#                 cached_data = cache_content["data"]
                
#                 # CASE 1: Giống hệt nhau (Khớp 100%)
#                 if current_targets == cached_targets and cache_content.get("version") == CACHE_VERSION:
#                     print(f"  -> [{label}] Target apps exactly matched! Loading from cache ...")
#                     return cached_data
                
#                 # CASE 2: Yêu cầu hiện tại là TẬP CON của Cache (Ví dụ: Cache có ALL, user chỉ cần Gallery)
#                 elif current_targets is not None and cache_content.get("version") == CACHE_VERSION:
#                     # Nếu Cache lưu ALL (None), hoặc Cache chứa đủ các app đang yêu cầu
#                     if cached_targets is None or set(current_targets).issubset(set(cached_targets)):
#                         print(f"  -> [{label}] Requested apps {current_targets} are available in Cache!")
#                         print(f"  -> [{label}] Extracting subset from cache ...")
                        
#                         # Trích xuất riêng data của những app được yêu cầu
#                         subset_data = {
#                             app: data for app, data in cached_data.items() 
#                             if app in current_targets
#                         }
#                         return subset_data
                
#                 # CASE 3: Yêu cầu thêm App mới mà Cache chưa có (VD: Cache có Gallery, user đòi thêm Camera)
#                 print(f"  -> [{label}] Target apps missing in cache! (Old: {cached_targets}, Requested: {current_targets})")
#                 print(f"  -> [{label}] Cache invalidated. Processing from scratch...")
#             else:
#                 print(f"  -> [{label}] Old cache format detected. Invalidating...")
                
#         except Exception as e:
#             print(f"  -> [{label}] [ERROR] Failed to read cache: {e}. Processing from scratch...")
            
#     # CHẠY QUÉT TỪ ĐẦU (Nếu không có cache hoặc cache không đủ data)
#     print(f"  -> [{label}] Processing trace files...")
#     results = process_all_traces(folder_path, label, num_workers, target_apps, extracted)
    
#     # LƯU CACHE
#     try:
#         cache_content_to_save = {
#             "version": CACHE_VERSION,
#             "target_apps": current_targets,
#             "data": results
#         }
#         with open(cache_path, 'wb') as f:
#             pickle.dump(cache_content_to_save, f)
#         print(f"  -> [{label}] Saved data & app filter to cache: {cache_path}")
#     except Exception as e:
#         print(f"  -> [{label}] [WARN] Could not save cache: {e}")
        
#     return results


def run_analysis(dut_folder: str, ref_folder: str, target_apps: List[str] = None, extracted: bool = False) -> None:
    """
    Phân tích hiệu năng từ các trace trong DUT và REF folders
    
    Args:
        dut_folder: Đường dẫn folder DUT
        ref_folder: Đường dẫn folder REF
        target_apps: Danh sách apps cần xử lý (optional)
        extracted: True nếu các Bugreport đã được giải nén thành folder
    """
    num_workers = min(cpu_count(), 16)
    
    if not os.path.exists(dut_folder):
        raise FileNotFoundError(f"DUT folder not found: {dut_folder}")
    if not os.path.exists(ref_folder):
        raise FileNotFoundError(f"REF folder not found: {ref_folder}")
    
    print("=" * 70)
    print("BATCH EXECUTION TIME ANALYSIS")
    print(f"Workers: {num_workers} | Available CPUs: {cpu_count()}")
    print(f"Extracted mode: {extracted}")
    print("=" * 70)
    
    start_time = datetime.datetime.now()

    # # Process DUT folder
    # print("\n[1/2] Processing DUT folder...")
    # dut_results = process_all_traces(dut_folder, "DUT", num_workers, target_apps, extracted)
    
    # # Process REF folder
    # print("\n[2/2] Processing REF folder...")
    # ref_results = process_all_traces(ref_folder, "REF", num_workers, target_apps, extracted)

    # Process DUT folder (Sử dụng Cache)
    print("\n[1/2] Processing DUT folder...")
    dut_results = get_or_process_folder_with_cache(dut_folder, "DUT", num_workers, target_apps, extracted)
    
    # Process REF folder (Sử dụng Cache)
    print("\n[2/2] Processing REF folder...")
    ref_results = get_or_process_folder_with_cache(ref_folder, "REF", num_workers, target_apps, extracted)
    
    # Extract header title từ file đầu tiên
    dut_files = collect_trace_files(dut_folder)
    if dut_files:
        first_file = Path(dut_files[0]).stem
        parts = first_file.split("_")
        header_title = "_".join(parts[:2]) if len(parts) >= 2 else "Metric"
    else:
        header_title = "Metric"

    # Extract REF header title
    ref_files = collect_trace_files(ref_folder)
    if ref_files:
        first_ref_file = Path(ref_files[0]).stem
        parts = first_ref_file.split("_")
        header_title_ref = "_".join(parts[:2]) if len(parts) >= 2 else "Metric"
    else:
        header_title_ref = "Metric"

    # Extract device codes
    dut_device_code = extract_device_code(header_title)
    ref_device_code = extract_device_code(header_title_ref)
    
    # Create Excel outputs
    print("\n[3/3] Creating Excel files...")
    output_folder = dut_folder  # Lưu vào thư mục DUT
    create_excel_output(dut_results, ref_results, output_folder, header_title, dut_device_code, ref_device_code, dut_folder, ref_folder)
    
    # Export JSON data
    print("\n[4/4] Exporting JSON data...")
    export_avg_to_json(dut_results, ref_results, dut_folder, dut_device_code, ref_device_code, dut_folder, ref_folder)
    
    end_time = datetime.datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    print("\n" + "=" * 70)
    print(f" COMPLETED in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print("=" * 70)

# ---------------------------------------------------------------------------
# Standalone Execution
# ---------------------------------------------------------------------------

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch Execution Time Analysis')
    parser.add_argument('dut_folder', help='Path to DUT folder')
    parser.add_argument('ref_folder', help='Path to REF folder')
    parser.add_argument('--extracted', action='store_true', 
                        help='Set if Bugreport files are already extracted to folders')
    
    args = parser.parse_args()
    
    try:
        run_analysis(args.dut_folder, args.ref_folder, extracted=True)
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

# Export json v2
'''
        # ========================
        # 1. SEQUENCE METRICS (AVG)
        # ========================
        sequence_metrics = [
            "App Execution Time", "Touch Down ~ Start Proc", "Start Proc",
            "Start Proc ~ ActivityThreadMain", "Activity Thread Main",
            "ActivityThreadMain ~ bindApplication", "Bind Application",
            "bindApplication ~ activityStart", "Touch Duration", "Touch Up ~ Activity Start",
            "Activity Start", "activityStart ~ activityResume", "Activity Resume",
            "ActivityResume ~ Choreographer", "Choreographer",
            "Choreographer ~ ActivityIdle", "ActivityIdle", "ActivityIdle ~ Animating end",
            "Running", "Runnable", "Uninterruptible Sleep", "Sleeping",
            "onCreate", "OpenCameraRequest", "onResume", "StartPreviewRequest"
        ]
        
        # [NEW] Định nghĩa lại keys để mask giống hệt Excel
        COLD_ONLY_KEYS = {
            "Touch Down ~ Start Proc", "Start Proc", "Start Proc ~ ActivityThreadMain",
            "Activity Thread Main", "ActivityThreadMain ~ bindApplication",
            "Bind Application", "bindApplication ~ activityStart"
        }
        WARM_ONLY_KEYS = {
            "Touch Duration", "Touch Up ~ Activity Start"
        }
        
        sequence_data = {}
        for metric in sequence_metrics:
            values = []
            for cycle in valid_cycles:
                # [NEW] Masking Logic: Bỏ qua metric nếu không đúng loại Launch Type
                # c_type = cycle.get("Launch Type")
                c_type = "Cold" if launch_type == "entry" else "Warm"
                if c_type == "Cold" and metric in WARM_ONLY_KEYS:
                    continue  # Bỏ qua Touch Duration cho cycle Cold
                if c_type == "Warm" and metric in COLD_ONLY_KEYS:
                    continue  # Bỏ qua Start Proc... cho cycle Warm
                
                val = cycle.get(metric, 0.0)
                if val and val > 0: 
                    values.append(float(val))
                    
            if values: 
                sequence_data[metric] = round(sum(values) / len(values), 3)
                
        if sequence_data: result["sequence"] = sequence_data
'''
