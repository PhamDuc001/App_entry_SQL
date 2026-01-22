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

from perfetto.trace_processor.api import TraceProcessor, TraceProcessorConfig
from sql_query import *
from atracetosystrace import convert_trace
from multiprocessing import Pool, cpu_count
from dumpstate_parser import (
    collect_bugreport_mappings, 
    get_bugreport_for_log, 
    get_app_group,
    get_bugreport_group_from_name
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
RELATIVE_BIN_PATH = os.path.join("perfetto", TP_FILENAME)
# Build
# RELATIVE_BIN_PATH = os.path.join("perfetto_bin", TP_FILENAME)
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

# def _process_single_trace_worker(args):
#     """
#     Worker function cho multiprocessing.
#     Sử dụng global _BUGREPORT_MAPPINGS để lấy pid_mapping.
#     """
#     file_path, occurrence, app_name = args
#     filename = Path(file_path).stem
#     config = TraceProcessorConfig(bin_path=TRACE_PROCESSOR_BIN)
    
#     # Tìm pid_mapping tương ứng cho file này
#     pid_mapping = None
#     if _BUGREPORT_MAPPINGS and _ALL_FILES_SORTED:
#         pid_mapping = get_bugreport_for_log(
#             file_path, 
#             _BUGREPORT_MAPPINGS, 
#             _ALL_FILES_SORTED
#         )
    
#     try:
#         with TraceProcessor(trace=convert_trace(file_path), config=config) as tp:
#             metrics = analyze_trace(tp, file_path, pid_mapping)
#             category = 'entry' if occurrence % 2 == 1 else 'reentry'
#             return (app_name, occurrence, category, metrics, filename)
#     except Exception as e:
#         print(f"    [ERROR] {Path(file_path).name}: {e}")
#         return (app_name, occurrence, 'entry' if occurrence % 2 == 1 else 'reentry', None, filename)

def _process_single_trace_worker(args):
    """
    Worker function cho multiprocessing.
    [UPDATED] Nhận trực tiếp pid_mapping từ tham số, không dùng biến Global.
    """
    # Unpack thêm tham số pid_mapping
    file_path, occurrence, app_name, pid_mapping = args 
    
    filename = Path(file_path).stem
    config = TraceProcessorConfig(bin_path=TRACE_PROCESSOR_BIN)
    
    try:
        with TraceProcessor(trace=convert_trace(file_path), config=config) as tp:
            # Truyền pid_mapping vào analyze_trace
            metrics = analyze_trace(tp, file_path, pid_mapping)
            category = 'entry' if occurrence % 2 == 1 else 'reentry'
            return (app_name, occurrence, category, metrics, filename)
    except Exception as e:
        print(f"    [ERROR] {Path(file_path).name}: {e}")
        # import traceback
        # traceback.print_exc()
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
    [UPDATED] Truyền 'occurrence' để map bugreport theo thứ tự Cycle.
    """
    trace_files = collect_trace_files(folder_path)
    app_groups = group_traces_by_app(trace_files, target_apps)
    bugreport_mappings = collect_bugreport_mappings(folder_path, extracted)

    tasks = []
    for app_name, file_list in app_groups.items():
        for file_path, occurrence in file_list:
            # [LOGIC MỚI] Truyền occurrence vào để xác định Cycle
            pid_mapping = get_bugreport_for_log(
                file_path, 
                bugreport_mappings, 
                occurrence=occurrence # <--- QUAN TRỌNG
            )
            
            tasks.append((file_path, occurrence, app_name, pid_mapping))
    
    print(f"[{label}] Processing {len(tasks)} trace files with {num_workers} workers...")
    
    results = defaultdict(lambda: {'entry': [None] * 100, 'reentry': [None] * 100})
    
    pool = Pool(processes=num_workers)
    try:
        for i, (app_name, occurrence, category, metrics, filename) in enumerate(pool.imap(_process_single_trace_worker, tasks)):
            if metrics:
                cycle_index = (occurrence - 1) // 2
                while len(results[app_name][category]) <= cycle_index:
                    results[app_name][category].append(None)
                
                results[app_name][category][cycle_index] = metrics
                print(f"  - [{i+1}/{len(tasks)}] {app_name} - {category} - cycle {cycle_index + 1} - {filename}")
    finally:
        pool.close() 
        pool.join()  
    
    cleaned_results = {}
    for app_name, categories in results.items():
        cleaned_results[app_name] = {
            'entry': [m for m in categories['entry'] if m is not None],
            'reentry': [m for m in categories['reentry'] if m is not None]
        }
    
    return cleaned_results


# ---------------------------------------------------------------------------
# Excel Creation
# ---------------------------------------------------------------------------

def create_excel_output(
    dut_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ref_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    output_folder: str,
    header_title: str,
    dut_device_code: str,
    ref_device_code: str
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
                ref_device_code
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
    ref_device_code: str
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
    
    # Số lượng cycles
    num_dut_cycles = len(dut_cycles)
    num_ref_cycles = len(ref_cycles)
    max_cycles = max(num_dut_cycles, num_ref_cycles)
    
    # --- CHECK GLOBAL STATE (ALL COLD / ALL WARM) ---
    all_cycles_data = dut_cycles + ref_cycles
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
        if idx < len(cycle_list):
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
            if i < len(dut_cycles):
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
            if i < len(ref_cycles):
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
        if dut_avg > 0 and ref_avg > 0:
            diff_val = dut_avg - ref_avg
            if diff_val > 10:
                fmt_diff = fmt_diff_slow  
            elif diff_val < -10:
                fmt_diff = fmt_diff_fast  
            else:
                fmt_diff = fmt_diff_normal 
            ws.write(row_idx, col_idx, diff_val, fmt_diff)
        else:
            ws.write(row_idx, col_idx, "", fmt_text)

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
        if i < len(dut_cycles):
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
        if i < len(ref_cycles):
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
        if i < len(dut_cycles):
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
        if i < len(ref_cycles):
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
    # === Top CPU Usage Tables (Parallel: Process [A-D] vs Thread [F-I]) ===
    # =========================================================================
    row_idx += 3

    # Load Data
    all_dut_proc = [cycle.get("CPU_Process_Data", []) for cycle in dut_cycles]
    all_ref_proc = [cycle.get("CPU_Process_Data", []) for cycle in ref_cycles]

    all_dut_thread = [cycle.get("CPU_Thread_Data", []) for cycle in dut_cycles]
    all_ref_thread = [cycle.get("CPU_Thread_Data", []) for cycle in ref_cycles]

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
        # PREPARE DATA FOR LEFT TABLE (PROCESS) - [UPDATED CROSS MAPPING]
        # ---------------------------------------------------------
        dut_p = all_dut_proc[cycle_idx] if cycle_idx < len(all_dut_proc) else []
        ref_p = all_ref_proc[cycle_idx] if cycle_idx < len(all_ref_proc) else []
        
        # Lấy Mapping của cả DUT và REF cho cycle hiện tại
        dut_mapping = dut_cycles[cycle_idx].get("PID_Mapping", {}) if cycle_idx < len(dut_cycles) else {}
        ref_mapping = ref_cycles[cycle_idx].get("PID_Mapping", {}) if cycle_idx < len(ref_cycles) else {}
        
        # Tạo Reverse Mapping cho REF: {"ProcessName": PID}
        ref_name_to_pid = {name: pid for pid, name in ref_mapping.items()}
        

        merged_p = {}
        
        # 1. Process DUT Data
        for x in dut_p:
            proc_name = x['proc_name']
            dut_val = x['dur_ms']
            ref_val = 0.0
            
            # Case A: Tìm exact match trên REF (process name giống hệt)
            found_exact = False
            for r in ref_p:
                if r['proc_name'] == proc_name:
                    ref_val = r['dur_ms']
                    found_exact = True
                    break
            
            # Case B: Nếu không tìm thấy exact match, check cross-mapping
            if not found_exact:
                # B.1: Nếu DUT có dạng "PID-xxx", resolve tên thật từ dut_mapping
                if proc_name.startswith("PID-"):
                    try:
                        dut_pid = int(proc_name.replace("PID-", ""))
                        real_name = dut_mapping.get(dut_pid)
                        
                        if real_name:
                            # Tìm PID tương ứng trên REF
                            ref_pid = ref_name_to_pid.get(real_name)
                            
                            if ref_pid:
                                # Tìm "PID-xxx" trong ref_p
                                ref_key = f"PID-{ref_pid}"
                                for r in ref_p:
                                    if r['proc_name'] == ref_key:
                                        ref_val = r['dur_ms']
                                        # Update proc_name để hiển thị tên thật
                                        proc_name = real_name
                                        break
                            else:
                                # REF không có process này, update tên nhưng giữ ref_val=0
                                proc_name = real_name

                            
                    except (ValueError, TypeError) as e:
                        print(f"Error parsing PID from '{proc_name}': {e}")
                
                # B.2: Nếu DUT có tên thật, check xem REF có dạng "PID-xxx" không
                else:
                    ref_pid = ref_name_to_pid.get(proc_name)
                    if ref_pid:
                        ref_key = f"PID-{ref_pid}"
                        for r in ref_p:
                            if r['proc_name'] == ref_key:
                                ref_val = r['dur_ms']
                                break
            
            merged_p[proc_name] = {'dut': dut_val, 'ref': ref_val}

        # 2. Process REF Data (chỉ thêm những process chưa có trong merged_p)
        for x in ref_p:
            name = x['proc_name']
            
            # Nếu REF có dạng "PID-xxx", resolve tên thật
            real_name = name
            if name.startswith("PID-"):
                try:
                    pid_num = int(name.replace("PID-", ""))
                    resolved = ref_mapping.get(pid_num)
                    if resolved:
                        real_name = resolved
                except:
                    pass
            
            # Chỉ thêm nếu chưa có trong merged_p
            if real_name not in merged_p:
                merged_p[real_name] = {'dut': 0.0, 'ref': x['dur_ms']}

        # 3. Flatten to List & Sort
        final_proc = []
        for name, v in merged_p.items():
            final_proc.append({
                'name': name, 
                'dut': v['dut'], 
                'ref': v['ref'], 
                'diff': v['dut'] - v['ref']
            })
        
        top_proc = sorted(final_proc, key=lambda x: x['diff'], reverse=True)[:10]

        # [Phần code vẽ bảng giữ nguyên...]

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
 
    # =============== Top Block I/O Table (MOVED TO POSITION 5) ================
    row_idx += 3
    
    # Formats cho Block I/O table
    fmt_blockio_header = wb.add_format({"bold": True, "align": "center", "bg_color": "#ADD8E6", "border": 1, "border_color": "#000000"})
    fmt_blockio_val = wb.add_format({"num_format": "0.000", "align": "center", "border": 1, "border_color": "#000000"})
    
    # Thu thập Block I/O data từ tất cả cycles
    all_dut_block_io = [cycle.get("Block_IO_Data", []) for cycle in dut_cycles]
    all_ref_block_io = [cycle.get("Block_IO_Data", []) for cycle in ref_cycles]
    
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
    
    
    # === LoadApkAssets Table ===
    row_idx += 3

    # Thu thập LoadApkAsset data từ tất cả cycles
    all_dut_loadapk = [cycle.get("LoadApkAsset_Data", []) for cycle in dut_cycles]
    all_ref_loadapk = [cycle.get("LoadApkAsset_Data", []) for cycle in ref_cycles]

    # Tạo union set của tất cả LoadApkAsset names
    all_loadapk_names = set()
    for cycle_data in all_dut_loadapk:
        for apk in cycle_data:
            all_loadapk_names.add(apk['name'])
    for cycle_data in all_ref_loadapk:
        for apk in cycle_data:
            all_loadapk_names.add(apk['name'])
    
    # print(all_loadapk_names)
    # CHỈ VẼ BẢNG NẾU CÓ DATA
    if all_loadapk_names:
        # print("============================Start LoadApkAssets==============================")
        sorted_loadapk_names = sorted(all_loadapk_names)
        
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
        ws.write(row_idx, 0, "LoadApkAssets Name", fmt_blockio_header)
        
        col_idx = 1
        for i in range(len(dut_cycles)):
            ws.write(row_idx, col_idx, "(ms)", fmt_blockio_header)
            col_idx += 1
        
        for i in range(len(ref_cycles)):
            ws.write(row_idx, col_idx, "(ms)", fmt_blockio_header)
            col_idx += 1
        
        ws.set_column(0, 0, 50)
        ws.set_column(1, col_idx - 1, 12)
        
        # === DATA ROWS - LOGIC ĐÚNG ===
        row_idx += 1
        
        # Tạo flat list của TẤT CẢ entries để phân bổ đúng
        all_entries = []
        for apk_name in sorted_loadapk_names:
            for cycle_idx, cycle_data in enumerate(all_dut_loadapk + all_ref_loadapk):
                for apk in cycle_data:
                    if apk['name'] == apk_name:
                        all_entries.append({
                            'name': apk_name,
                            'dur_ms': apk['dur_ms'],
                            'cycle_idx': cycle_idx,
                            'is_dut': cycle_idx < len(all_dut_loadapk)
                        })
        
        # Group theo name và hiển thị
        current_name = None
        occurrence_num = 0
        
        for entry in all_entries:
            if entry['name'] != current_name:
                current_name = entry['name']
                occurrence_num = 1
            else:
                occurrence_num += 1
            
            # Label
            if occurrence_num > 1:
                # label = f"{entry['name']} (#{occurrence_num})"
                label = entry['name']
            else:
                label = entry['name']
            
            ws.write(row_idx, 0, label, fmt_label)
            col_idx = 1
            
            # Fill data cho cycle tương ứng
            cycle_offset = entry['cycle_idx']
            if entry['is_dut']:
                actual_cycle = cycle_offset
            else:
                actual_cycle = cycle_offset - len(all_dut_loadapk)
            
            # DUT cycles - để trống tất cả trừ cycle chứa entry này
            for i in range(len(all_dut_loadapk)):
                if entry['is_dut'] and i == actual_cycle:
                    write_value_or_empty(ws, row_idx, col_idx, entry['dur_ms'], fmt_blockio_val)
                else:
                    ws.write(row_idx, col_idx, "", fmt_val)
                col_idx += 1
            
            # REF cycles - tương tự
            for i in range(len(all_ref_loadapk)):
                if not entry['is_dut'] and i == actual_cycle:
                    write_value_or_empty(ws, row_idx, col_idx, entry['dur_ms'], fmt_blockio_val)
                else:
                    ws.write(row_idx, col_idx, "", fmt_val)
                col_idx += 1
            
            row_idx += 1

    # ---------------------------------------------------------
    # === Statistics Table (Binder Transaction, etc.) ===
    # ---------------------------------------------------------
    row_idx += 3
    
    # Thu thập Binder Transaction data từ tất cả cycles
    all_dut_binder = [cycle.get("Binder_Transaction_Data", {}) for cycle in dut_cycles]
    # print("all_dut_binder", all_dut_binder)
    all_ref_binder = [cycle.get("Binder_Transaction_Data", {}) for cycle in ref_cycles]
    
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
# Main
# ---------------------------------------------------------------------------

def run_analysis(dut_folder: str, ref_folder: str, target_apps: List[str] = None, extracted: bool = False) -> None:
    """
    Phân tích hiệu năng từ các trace trong DUT và REF folders
    
    Args:
        dut_folder: Đường dẫn folder DUT
        ref_folder: Đường dẫn folder REF
        target_apps: Danh sách apps cần xử lý (optional)
        extracted: True nếu các Bugreport đã được giải nén thành folder
    """
    num_workers = min(cpu_count(), 8)
    
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

    # Process DUT folder
    print("\n[1/2] Processing DUT folder...")
    dut_results = process_all_traces(dut_folder, "DUT", num_workers, target_apps, extracted)
    
    # Process REF folder
    print("\n[2/2] Processing REF folder...")
    ref_results = process_all_traces(ref_folder, "REF", num_workers, target_apps, extracted)
    
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
    create_excel_output(dut_results, ref_results, output_folder, header_title, dut_device_code, ref_device_code)
    
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
        run_analysis(args.dut_folder, args.ref_folder, extracted=args.extracted)
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()



##################################

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List, Union
from collections import defaultdict
import pandas as pd
from perfetto.trace_processor import TraceProcessor


# -------------------------------------------------------------------
def get_resource_path(relative_path):
    """
    Hàm lấy đường dẫn file.
    - Nếu chạy file .exe (Frozen): Lấy từ thư mục tạm sys._MEIPASS
    - Nếu chạy code .py (Dev): Lấy từ thư mục hiện tại của project
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller tạo ra thư mục tạm này
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# [File: sql_query.py]

def get_resource_path(relative_path):
    """
    Hàm lấy đường dẫn file resource chuẩn cho cả Dev, Onedir và Onefile.
    """
    # Nếu đang chạy file .exe (PyInstaller đóng gói)
    if getattr(sys, 'frozen', False):
        # Chế độ Onefile: dùng _MEIPASS
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        # Chế độ Onedir (Folder): dùng thư mục chứa file .exe
        else:
            base_path = os.path.dirname(sys.executable)
            
    # Nếu đang chạy code Python thuần (Dev mode)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(base_path, relative_path)

# -------------------------------------------------------------------
# 1. HELPER FUNCTIONS & UTILS
# -------------------------------------------------------------------

def to_ms(ns: Optional[Union[int, float]]) -> float:
    """Chuyển nanoseconds -> milliseconds (3 chữ số thập phân)."""
    if ns is None:
        return 0.0
    return round(ns / 1_000_000.0, 3)

def query_df(tp: TraceProcessor, sql: str) -> Optional[pd.DataFrame]:
    """Thực thi SQL và trả về pandas.DataFrame (hoặc None nếu rỗng/lỗi)."""
    try:
        res = tp.query(sql)
        if not res:
            return None
        df = res.as_pandas_dataframe()
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        print(f"[SQL Error] {e}")
        return None

def ensure_slice_with_names_view(tp: TraceProcessor) -> None:
    """
    Tạo view global slice_with_names.
    Nâng cấp: Thêm thread_name và pid để tiện filter ngay trong View.
    """
    sql = """
    CREATE VIEW IF NOT EXISTS slice_with_names AS
    SELECT
        s.id, s.ts, s.dur, s.name, s.track_id, s.depth,
        t.utid, t.name AS thread_name,
        th.tid, th.upid,
        p.pid, p.name AS process_name
    FROM slice s
    LEFT JOIN thread_track t ON s.track_id = t.id
    LEFT JOIN thread th      ON t.utid = th.utid
    LEFT JOIN process p      ON th.upid = p.upid;
    """
    tp.query(sql)

# -------------------------------------------------------------------
# 2. CORE GENERIC QUERY FUNCTION (HÀM TÌM KIẾM TỔNG QUÁT)
# -------------------------------------------------------------------

def find_slice(
    tp: TraceProcessor, 
    name_exact: str = None, 
    name_like: str = None, 
    upid: int = None,
    pid: int = None,
    tid: int = None,
    thread_name: str = None,
    order_by: str = 'ts',
    limit: int = 1
) -> Optional[pd.Series]:
    """
    Hàm tìm kiếm slice đa năng.
    Trả về: 1 dòng (pd.Series) đầu tiên tìm thấy hoặc None.
    """
    conditions = []
    if name_exact:
        conditions.append(f"name = '{name_exact}'")
    if name_like:
        conditions.append(f"name LIKE '{name_like}'")
    if upid is not None:
        conditions.append(f"upid = {upid}")
    if pid is not None:
        conditions.append(f"pid = {pid}")
    if tid is not None:
        conditions.append(f"tid = {tid}")
    if thread_name:
        conditions.append(f"thread_name = '{thread_name}'")

    where_clause = " AND ".join(conditions)
    if not where_clause:
        where_clause = "1=1" 

    sql = f"""
        SELECT ts, dur, (ts+dur) as end_ts, name, tid, pid, upid
        FROM slice_with_names
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT {limit};
    """
    
    df = query_df(tp, sql)
    if df is None:
        return None
    return df.iloc[0]

# -------------------------------------------------------------------
# 3. REFACTORED SIMPLE QUERIES (Sử dụng find_slice)
# -------------------------------------------------------------------

def detect_app_from_launch(tp: TraceProcessor) -> Optional[str]:
    """Tìm app package từ event 'launching:%'."""
    row = find_slice(tp, name_like='launching:%')
    if row is None:
        return None
    name = str(row['name'])
    return name.split("launching:", 1)[1].strip() if "launching:" in name else None

def find_app_process(tp: TraceProcessor, app_pkg: str) -> Optional[Tuple[int, int, str, int]]:
    """Tìm process chính của app dựa vào activityStart/Resume."""
    # Logic: Tìm process có activityStart hoặc activityResume
    sql = """
    SELECT DISTINCT upid, pid, tid, name
    FROM slice_with_names
    WHERE name IN ('activityStart', 'activityResume')
    ORDER BY ts LIMIT 1;
    """
    df = query_df(tp, sql)
    if df is None:
        return None
    r = df.iloc[0]
    # Trả về: (upid, pid, name, tid)
    return int(r['upid']), int(r['pid']), str(r['name'] or ""), int(r['tid'])

def get_first_deliver_input(tp: TraceProcessor) -> Optional[int]:
    """Lấy timestamp bắt đầu của deliverInputEvent đầu tiên."""
    row = find_slice(tp, name_like='deliverInputEvent%')
    return int(row['ts']) if row is not None else None

def get_end_deliver_input(tp: TraceProcessor, launch_pid: int):
    """Lấy (ts, end_ts) của dispatchInputEvent UP."""
    # Logic cũ: tìm dispatchInputEvent...UP
    row = find_slice(tp, name_like='dispatchInputEvent MotionEvent%UP%')
    if row is not None:
        return int(row['ts']), int(row['end_ts'])
    return None, None

def get_launcher_pid(tp: TraceProcessor) -> Optional[int]:
    """Lấy PID của Launcher process."""
    sql = """
    SELECT p.pid
    FROM process p JOIN thread t ON p.upid = t.upid
    WHERE t.is_main_thread = 1 AND t.name LIKE 'id.app.launcher%';
    """
    df = query_df(tp, sql)
    if df is None:
        return None
    return int(df.iloc[0]['pid'])

def get_activity_idle_end(tp: TraceProcessor, app_upid: int) -> Tuple[Optional[int], Optional[int]]:
    """Lấy (ts, end_ts) của activityIdle trong system_server."""
    row = find_slice(tp, name_exact='activityIdle')
    if row is not None:
        return int(row['ts']), int(row['end_ts'])
    return None, None

def get_start_proc_start(tp: TraceProcessor, app_pkg: str) -> Optional[Tuple[int, int, int]]:
    """Lấy 'Start proc: <pkg>' trong thread ActivityManager."""
    sql = """
    SELECT ts, dur
    FROM slice_with_names
    WHERE name like 'startProcess:%';
    """
    df = query_df(tp, sql)
    if df is None:
        return None # <--- SỬA: Trả về None thay vì (None, None, None)
    
    row = df.iloc[0]
    if row is not None:
        return int(row['ts']), int(row['dur']), int(row['ts']) + int(row['dur'])
    return None

def has_bind_application(tp: TraceProcessor, app_upid: int) -> bool:
    """Kiểm tra xem app có bindApplication không (Cold launch)."""
    row = find_slice(tp, name_exact='bindApplication', upid=app_upid)
    return row is not None

def get_event_ts(tp: TraceProcessor, app_upid: int, name: str) -> Optional[Tuple[int, int, int]]:
    """Lấy (ts, dur, end_ts) của event cụ thể trong app process."""
    row = find_slice(tp, name_exact=name, upid=app_upid)
    if row is not None:
        return int(row['ts']), int(row['dur']), int(row['end_ts'])
    return None

def get_choreographer(tp: TraceProcessor, tid: int, min_ts: int = 0) -> Optional[Tuple[int, int, int]]:
    """
    Lấy thông tin Choreographer đầu tiên xuất hiện sau thời điểm min_ts.
    """
    if tid is None:
        return None

    # Truy vấn trực tiếp để filter theo timestamp
    sql = f"""
    SELECT ts, dur, (ts+dur) as end_ts
    FROM slice_with_names
    WHERE name LIKE 'Choreographer#doFrame%'
      AND tid = {tid}
      AND ts >= {min_ts}
    ORDER BY ts ASC
    LIMIT 1;
    """
    
    df = query_df(tp, sql)
    if df is None:
        return None
        
    row = df.iloc[0]
    return int(row['ts']), int(row['dur']), int(row['end_ts'])

def get_launching_end(tp: TraceProcessor, app_pkg: str) -> Optional[int]:
    """Lấy end timestamp của launching:<pkg>."""
    # Thử tìm có dấu cách
    row = find_slice(tp, name_like=f'launching: {app_pkg}')
    if row is not None:
        return int(row['end_ts'])
    # Thử tìm không dấu cách (fallback)
    row_fallback = find_slice(tp, name_like=f'launching:{app_pkg}')
    return int(row_fallback['end_ts']) if row_fallback is not None else None

def get_animating(tp: TraceProcessor) -> int:
    """Lấy end time của animating (Process Track)."""
    sql = """
    SELECT s.ts + s.dur as end_ts
    FROM slice s 
    JOIN process_track pt ON s.track_id = pt.id
    WHERE pt.name = 'animating' AND s.name = 'animating'
    LIMIT 1;
    """
    df = query_df(tp, sql)
    if df is None:
        # Nếu không thấy thì raise error hoặc return 0 tuỳ logic, ở đây giữ logic cũ raise error
        raise RuntimeError("KHÔNG TÌM THẤY 'animating' - Log bị lỗi hoặc không đầy đủ!")
    return int(df.iloc[0]["end_ts"])

def get_binder_transaction(tp: TraceProcessor, app_tid: int, end_ts: int):
    """
    Tính thống kê Binder Transaction.
    Chỉ tính các transaction bắt đầu trước thời điểm end_ts (kết thúc launch).
    """
    # Nếu không có end_ts hợp lệ thì trả về 0 để tránh lỗi SQL
    if end_ts is None:
        return 0, 0.0
    sql = f"""
    SELECT COUNT(id) AS cnt, SUM(dur) / 1000000.0 AS total_ms 
    FROM slice_with_names
    WHERE name = 'binder transaction' 
      AND tid = {app_tid}
      AND ts < {end_ts};
    """
    df = query_df(tp, sql)
    if df is None:
        return 0, 0.0 
        
    row = df.iloc[0]
    return int(row['cnt']), float(row['total_ms'] or 0.0)

# -------------------------------------------------------------------
# 3.1 REACTION QUERIES
# -------------------------------------------------------------------
def get_onTransactionReady(tp: TraceProcessor) -> Optional[Tuple[int, int, int]]:
    """
    Get 'onTransactionReady' trong system_server.
    Return: (start_time, dur_time, end_time)
    """
    sql = f"""
    SELECT ts, dur, (ts + dur) as end_ts
    FROM slice_with_names
    WHERE name = 'onTransactionReady';
    """
    df = query_df(tp, sql)
    if df is None:
        return None, None, None
    row = df.iloc[0]
    return int(row['ts']), int(row['dur']), int(row['end_ts'])

def get_addStartingWindow(tp: TraceProcessor) -> Optional[Tuple[int, int, int]]:
    """
    Get 'addStartingWindow' trong system_server.
    Return: (start_time, dur_time, end_time)
    """
    sql = f"""
    SELECT ts, dur, (ts + dur) as end_ts
    FROM slice_with_names
    WHERE name = 'addStartingWindow';
    """
    df = query_df(tp, sql)
    if df is None:
        return None, None, None
    row = df.iloc[0]
    return int(row['ts']), int(row['dur']), int(row['end_ts'])

def get_drawFrame(tp: TraceProcessor, app_upid: int) -> Optional[Tuple[int, int, int]]:
    return None

def get_drawFrame(tp: TraceProcessor, launcher_pid: int) -> Optional[Tuple[int, int, int]]:
    """
    Get 'DrawFrame' in launcher process:
    -> Earliest DrawFrame after animator last.
    
    Return: (ts, dur, end_ts)
    """
    if not launcher_pid:
        return None

    sql = f"""
    WITH LastAnimator AS (
        -- Bước 1: Lấy timestamp của slice 'animator' cuối cùng (Process Track)
        SELECT s.ts
        FROM slice s
        JOIN process_track pt ON s.track_id = pt.id
        JOIN process p ON pt.upid = p.upid
        WHERE 
            s.name = 'animator'
            AND p.pid = {launcher_pid}
        ORDER BY s.ts DESC
        LIMIT 1
    ),
    TargetDrawFrame AS (
        -- Bước 2: Tìm DrawFrame (Thread Track) xảy ra sau Animator
        SELECT 
            s.ts, 
            s.dur
        FROM slice s
        JOIN thread_track tt ON s.track_id = tt.id
        JOIN thread t ON tt.utid = t.utid
        JOIN process p ON t.upid = p.upid
        JOIN LastAnimator la ON 1=1 -- Cross join để lấy biến 'la.ts'
        WHERE 
            s.name LIKE '%DrawFrame%' 
            AND p.pid = {launcher_pid}
            AND s.ts > la.ts 
        ORDER BY s.ts ASC 
        LIMIT 1
    )
    SELECT * FROM TargetDrawFrame;
    """

    df = query_df(tp, sql)
    if df is None:
        return None

    row = df.iloc[0]
    ts = int(row['ts'])
    dur = int(row['dur']) if pd.notna(row['dur']) else 0
    return ts, dur, ts + dur

def get_reaction_choreographer(tp: TraceProcessor, sysui_pid: int) -> Optional[Tuple[int, int, int]]:
    """
    Tìm Choreographer#doFrame trên cùng thread với addStartingWindow
    trong process SystemUI (dựa trên sysui_pid cung cấp).
    
    Logic:
    1. Tìm 'addStartingWindow' trong process SystemUI -> Lấy ts và tid.
    2. Tìm 'Choreographer#doFrame%' trên cùng tid đó và có ts >= ts của addStartingWindow.
    """
    if not sysui_pid:
        return None

    sql = f"""
    WITH TargetTrigger AS (
        -- Bước 1: Tìm addStartingWindow đầu tiên trong PID được cung cấp
        SELECT tid, ts
        FROM slice_with_names
        WHERE name = 'addStartingWindow'
        AND pid = {sysui_pid}
        ORDER BY ts ASC
        LIMIT 1
    )
    SELECT s.ts, s.dur, (s.ts + s.dur) as end_ts
    FROM slice_with_names s
    JOIN TargetTrigger t ON s.tid = t.tid -- Bắt buộc cùng Thread ID
    WHERE s.name LIKE 'Choreographer#doFrame%'
    AND s.ts >= t.ts -- Phải xảy ra sau hoặc ngay tại lúc addStartingWindow
    ORDER BY s.ts ASC
    LIMIT 1;
    """

    df = query_df(tp, sql)
    if df is None:
        return None

    row = df.iloc[0]
    return int(row['ts']), int(row['dur']), int(row['end_ts'])
# -------------------------------------------------------------------
# 4. COMPLEX QUERIES (Giữ nguyên logic phức tạp)
# -------------------------------------------------------------------

def get_thread_state_summary(tp: TraceProcessor, app_tid: int,
                             ts_start: int, ts_dur: int) -> Dict[str, float]:
    """
    Tổng thời gian các state (Running, R, S, D...) của một thread.
    Sử dụng SPAN_JOIN giữa intervals và thread_state.
    """
    if ts_dur <= 0:
        return {}

    # 1. View state_view
    sql = f"""
    DROP VIEW IF EXISTS state_view;
    CREATE VIEW state_view AS
    SELECT
        thread_state.state,
        thread_state.ts,
        thread_state.dur
    FROM thread_state
    JOIN thread USING (utid)
    WHERE thread.tid = {app_tid};
    """
    tp.query(sql)

    # 2. View intervals
    sql = f"""
    DROP VIEW IF EXISTS intervals;
    CREATE VIEW intervals AS
    SELECT {ts_start} AS ts, {ts_dur} AS dur;
    """
    tp.query(sql)

    # 3. Span join
    sql = """
    DROP TABLE IF EXISTS target_view;
    CREATE VIRTUAL TABLE target_view
    USING span_join (intervals, state_view);
    """
    tp.query(sql)

    # 4. Aggregate
    sql = """
    SELECT
        state,
        SUM(dur) / 1e6 AS total_duration_ms
    FROM target_view
    GROUP BY state
    ORDER BY total_duration_ms DESC;
    """
    df = query_df(tp, sql)

    # 5. Cleanup
    tp.query("DROP TABLE IF EXISTS target_view;")
    tp.query("DROP VIEW  IF EXISTS intervals;")
    tp.query("DROP VIEW  IF EXISTS state_view;")

    if df is None:
        return {}

    result: Dict[str, float] = {}
    for _, row in df.iterrows():
        state = str(row["state"])
        try:
            total_ms = float(row["total_duration_ms"])
        except (TypeError, ValueError):
            continue
        result[state] = total_ms

    return result

# [File: sql_query.py]

def top_block_IO(tp: TraceProcessor, app_pid: int, start_time: int, end_time: int):
    """
    Lấy danh sách library slices có Block I/O.
    - Filter slices trong khoảng start_time -> end_time.
    - Logic: Trạng thái Block I/O (D) xảy ra ngay sau khi slice thư viện BẮT ĐẦU (StartTime) 
      và khoảng cách không quá 500ns.
    - [UPDATED] Chỉ lấy slice bắt đầu bằng '1' (loại bỏ '0').
    """
    # Xử lý fallback nếu thời gian không hợp lệ
    if start_time is None: start_time = 0
    if end_time is None: end_time = 1 << 60 # Số rất lớn

    sql = f"""
        WITH 
        target_context AS (
            SELECT t.utid
            FROM thread t
            JOIN process p USING (upid)
            WHERE p.pid = {app_pid} AND t.is_main_thread = 1
            LIMIT 1
        ),
        lib_slices AS (
            SELECT 
            s.id, s.ts, s.dur, s.name, 
            tt.utid, (s.ts + s.dur) AS end_ts
            FROM slice s
            JOIN thread_track tt ON s.track_id = tt.id
            WHERE tt.utid = (SELECT utid FROM target_context)
            
            -- [UPDATED] Chỉ lấy slice bắt đầu bằng '1', bỏ '0' (odex)
            AND s.name LIKE '1%' 
            
            -- Giới hạn phạm vi tìm kiếm slice
            AND s.ts >= {start_time} 
            AND s.ts <= {end_time}
        ),
        io_states AS (
            SELECT ts, dur, utid 
            FROM thread_state
            WHERE utid = (SELECT utid FROM target_context)
            AND state = 'D'
            -- Tối ưu: Chỉ lấy state 'D' trong khoảng thời gian quan tâm
            AND ts >= {start_time}
        )
        SELECT 
        lib.name,
        io.dur,
        MIN(io.ts) AS first_io_ts
        FROM lib_slices lib
        JOIN io_states io 
        ON lib.utid = io.utid 
        -- Logic: IO xảy ra sau khi slice BẮT ĐẦU (lib.ts)
        AND io.ts >= lib.ts
        AND (io.ts - lib.ts) <= 150000 
        
        GROUP BY lib.id
        ORDER BY lib.ts;
    """
    return query_df(tp, sql)

def process_block_io_data(df) -> List[Dict[str, Any]]:
    """Xử lý DataFrame Block I/O thành list dict."""
    if df is None or df.empty:
        return []
    
    library_stats = defaultdict(lambda: {'timeTotal': 0, 'occurenceTotal': 0})
    for _, row in df.iterrows():
        name_parts = row['name'].split(' , ')
        if len(name_parts) >= 2:
            library_name = name_parts[1].strip()
            duration = int(row['dur'])
            library_stats[library_name]['timeTotal'] += duration
            library_stats[library_name]['occurenceTotal'] += 1
    
    result = []
    for lib_name, stats in library_stats.items():
        result.append({
            'libraryName': lib_name,
            'timeTotal': stats['timeTotal'],
            'timeTotal_ms': stats['timeTotal'] / 1000000.0,
            'occurenceTotal': stats['occurenceTotal']
        })
    result.sort(key=lambda x: x['timeTotal'], reverse=True)
    return result[:10]

def get_loadApkAsset(tp: TraceProcessor, app_pids: List[int], start_time: int, end_time: int):
    """Lấy danh sách LoadApkAssets > 50ms."""
    if not app_pids:
        return None
    pids_str = ','.join(map(str, app_pids))
    sql = f"""
        SELECT slice.name, slice.dur
        FROM slice 
        JOIN thread_track ON slice.track_id = thread_track.id 
        JOIN thread USING (utid) 
        JOIN process USING (upid)
        WHERE slice.name LIKE 'LoadApkAssets%' 
        AND slice.dur/1e6 > 50 
        AND slice.ts > {start_time} AND slice.ts < {end_time}
        AND process.pid IN ({pids_str})
        ORDER BY slice.ts;
    """
    return query_df(tp, sql)

def process_loadapk_data(df) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    result = []
    for _, row in df.iterrows():
        result.append({
            'name': str(row['name']),
            'dur_ms': row['dur'] / 1000000.0
        })
    return result
# ==============================================================
# ==============Get top CPU by Process and Thread===============
# ==============================================================
# --- 1. Query cho Process (Group by Process Name) ---
def get_top_cpu_usage_process(tp: TraceProcessor, start_time: int, dur_time: int, cpu_cores: List[int]):
    """
    Query top CPU usage by process. 
    [UPDATED] Trả về thêm cột 'raw_pid' để Python có thể map lại tên nếu cần.
    """
    if not cpu_cores or dur_time <= 0: return None
    cpu_cores_str = ','.join(map(str, cpu_cores))
    
    sql = f"""
    DROP VIEW IF EXISTS cpu_view_proc;
    CREATE VIEW cpu_view_proc AS
    SELECT 
        sched_slice.ts, sched_slice.dur, sched_slice.cpu,
        COALESCE(
            process.name, 
            CASE 
                WHEN main_thread.name LIKE '%binder%' OR main_thread.name LIKE '%kworker%' THEN NULL
                ELSE main_thread.name
            END, 
            'PID-' || process.pid
        ) as proc_name,
        process.pid as raw_pid  -- [QUAN TRỌNG] Cần cột này để mapping hoạt động
    FROM sched_slice 
    JOIN thread USING (utid) JOIN process USING (upid)
    LEFT JOIN thread AS main_thread ON (process.pid = main_thread.tid)
    WHERE NOT thread.name LIKE 'swapper%' ORDER BY ts ASC;
    
    DROP VIEW IF EXISTS intervals_proc;
    CREATE VIEW intervals_proc AS SELECT {start_time} AS ts, {dur_time} AS dur;
    
    DROP TABLE IF EXISTS target_proc;
    CREATE VIRTUAL TABLE target_proc USING SPAN_JOIN(intervals_proc, cpu_view_proc);
    
    SELECT 
        proc_name,
        raw_pid, -- [QUAN TRỌNG] Chọn cột raw_pid ra kết quả cuối
        SUM(dur)/1e6 AS dur_ms,
        COUNT(*) AS Occurences, 
        ROUND(SUM(dur) * 100.0 / {dur_time}*7, 2) AS dur_percent
    FROM target_proc
    WHERE cpu IN ({cpu_cores_str})
    GROUP BY COALESCE(proc_name, raw_pid)
    ORDER BY dur_ms DESC;
    """
    df = query_df(tp, sql)
    tp.query("DROP TABLE IF EXISTS target_proc; DROP VIEW IF EXISTS intervals_proc; DROP VIEW IF EXISTS cpu_view_proc;")
    return df

def process_cpu_data_process(df, pid_mapping: Dict[int, str] = None) -> List[Dict[str, Any]]:
    """
    Process CPU data for processes, with optional PID to process name mapping.
    
    [UPDATED] Chỉ map từ PID sang tên (dùng pid_mapping) nếu tên hiện tại 
    đang bị thiếu (dạng 'PID-xxx'). Giữ nguyên nếu Trace đã có tên chuẩn.
    """
    if df is None or df.empty: 
        return []
    
    result = []
    for _, row in df.iterrows():
        proc_name = str(row.get('proc_name', ''))
        raw_pid = row.get('raw_pid')
        
        # [LOGIC MỚI] Chỉ check mapping nếu tên bắt đầu bằng "PID-"
        if proc_name.startswith("PID-"):
            if pid_mapping and raw_pid is not None:
                try:
                    pid_int = int(raw_pid)
                    if pid_int in pid_mapping:
                        proc_name = pid_mapping[pid_int]
                        # print(f"  [Local Resolve] PID-{pid_int} -> {proc_name}")
                except (ValueError, TypeError):
                    pass
        
        # Fallback: Đảm bảo format PID-xxx nếu vẫn không có tên
        if not proc_name or proc_name.startswith("PID-"):
            if raw_pid is not None:
                try:
                    proc_name = f'PID-{int(raw_pid)}'
                except:
                    proc_name = 'Unknown'
            else:
                proc_name = 'Unknown'
        
        result.append({
            'dur_ms': float(row['dur_ms']),
            'proc_name': proc_name,
            'occurences': int(row['Occurences']),
            'dur_percent': float(row['dur_percent'])
        })
    
    return result

# --- 2. Query cho Thread (Group by TID/Thread Name) ---
def get_top_cpu_usage_thread(tp: TraceProcessor, start_time: int, dur_time: int, cpu_cores: List[int]):
    if not cpu_cores or dur_time <= 0: return None
    cpu_cores_str = ','.join(map(str, cpu_cores))
    
    sql = f"""
    DROP VIEW IF EXISTS cpu_view_thread;
    CREATE VIEW cpu_view_thread AS
    SELECT 
        sched_slice.ts, sched_slice.dur, sched_slice.cpu,
        thread.tid, thread.name as thread_name,
        COALESCE(process.name, main_thread.name, 'PID-' || process.pid) as proc_name
    FROM sched_slice 
    JOIN thread USING (utid) JOIN process USING (upid)
    LEFT JOIN thread AS main_thread ON (process.pid = main_thread.tid)
    WHERE NOT thread.name LIKE 'swapper%' ORDER BY ts ASC;
    
    DROP VIEW IF EXISTS intervals_thread;
    CREATE VIEW intervals_thread AS SELECT {start_time} AS ts, {dur_time} AS dur;
    
    DROP TABLE IF EXISTS target_thread;
    CREATE VIRTUAL TABLE target_thread USING SPAN_JOIN(intervals_thread, cpu_view_thread);
    
    SELECT 
        tid, thread_name, proc_name,
        SUM(dur)/1e6 AS dur_ms,
        COUNT(*) AS Occurences, 
        ROUND(SUM(dur) * 100.0 / {dur_time}*7, 2) AS dur_percent
    FROM target_thread
    WHERE cpu IN ({cpu_cores_str})
    GROUP BY thread_name, proc_name, tid
    ORDER BY dur_ms DESC;
    """
    df = query_df(tp, sql)
    tp.query("DROP TABLE IF EXISTS target_thread; DROP VIEW IF EXISTS intervals_thread; DROP VIEW IF EXISTS cpu_view_thread;")
    return df

def process_cpu_data_thread(df) -> List[Dict[str, Any]]:
    if df is None or df.empty: return []
    return [{
        'tid': str(row['tid']),
        'dur_ms': float(row['dur_ms']),
        'thread_name': str(row['thread_name']) if row['thread_name'] else 'unknown',
        'proc_name': str(row['proc_name']) if row['proc_name'] else 'Unknown',
        'occurences': int(row['Occurences']),
        'dur_percent': float(row['dur_percent'])
    } for _, row in df.iterrows()]






def get_pid_list(tp: TraceProcessor) -> List[int]:
    """Lấy PID system_server, systemui, surfaceflinger."""
    sql = """
        SELECT p.pid
        FROM process p JOIN thread t ON p.upid = t.upid
        WHERE t.is_main_thread = 1 
          AND (t.name = 'system_server' OR t.name = 'surfaceflinger' OR t.name LIKE '%ndroid.systemui%');
    """
    df = query_df(tp, sql)
    if df is None:
        return []
    return df["pid"].tolist()

def get_pid_systemUI(tp: TraceProcessor):
    """Systemui PID"""
    sql = """
        SELECT p.pid
        FROM process p JOIN thread t ON p.upid = t.upid
        WHERE t.is_main_thread = 1 
          AND (t.name LIKE '%ndroid.systemui%');
    """
    df = query_df(tp, sql)
    if df is None:
        return []
    return df["pid"].tolist()

def get_slice_on_app_process(tp: TraceProcessor, app_pid: int, slice_names: list):
    """Lấy danh sách nhiều slice trên cả Thread/Process Track."""
    if not slice_names:
        return None
    values_clause = ", ".join([f"('{name}')" for name in slice_names])
    sql = f"""
    WITH 
    TargetProcess AS (SELECT DISTINCT upid FROM process WHERE pid = {app_pid}),
    TargetPatterns(pattern) AS (VALUES {values_clause})
    SELECT s.name AS slice_name, s.ts, s.dur
    FROM slice s
    JOIN thread_track tt ON s.track_id = tt.id
    JOIN thread t ON tt.utid = t.utid
    JOIN TargetProcess p ON t.upid = p.upid
    JOIN TargetPatterns tn ON s.name LIKE tn.pattern
    UNION ALL
    SELECT s.name AS slice_name, s.ts, s.dur
    FROM slice s
    JOIN process_track pt ON s.track_id = pt.id
    JOIN TargetProcess p ON pt.upid = p.upid
    JOIN TargetPatterns tn ON s.name LIKE tn.pattern
    ORDER BY ts;
    """
    return query_df(tp, sql)

def process_multiple_slices_data(df) -> Dict[str, List[int]]:
    if df is None or df.empty:
        return {}
    result = {}
    for _, row in df.iterrows():
        slice_name = str(row['slice_name'])
        ts = int(row['ts'])
        dur = int(row['dur'])
        if slice_name not in result:
            result[slice_name] = [ts, dur]
    return result
# -------------------------------------------------------------------
# ABNORMAL PROCESSES 
# -------------------------------------------------------------------
def get_abnormal_processes(tp: TraceProcessor, threshold_time: int, exclude_pid: int, target_slices: List[str] = None):
    """
    Lấy danh sách các process khởi chạy (bindApplication) trước khi App chính hoàn tất launch.
    Loại trừ PID của App chính.
    """
    if not threshold_time or not exclude_pid:
        return None

    if target_slices is None:
        target_slices = ['bindApplication']
    
    # Format list cho SQL: 'bindApplication', 'activityStart'
    slice_names_str = ", ".join([f"'{s}'" for s in target_slices])
    
    sql = f"""
    SELECT 
        process.pid,
        -- Fix tên process null: Ưu tiên process.name -> thread.name -> PID
        COALESCE(process.name, thread.name, 'PID-' || process.pid) as proc_name,
        slice.name as slice_name,
        slice.ts as start_time,
        slice.dur as duration_ns
    FROM slice
    JOIN thread_track ON slice.track_id = thread_track.id
    JOIN thread USING (utid)
    JOIN process USING (upid)
    WHERE 
        slice.name IN ({slice_names_str})
        AND slice.ts < {threshold_time}
        AND process.pid != {exclude_pid}
    ORDER BY slice.ts ASC;
    """
    
    return query_df(tp, sql)

def process_abnormal_data(df) -> List[Dict[str, Any]]:
    """
    Chuyển đổi DataFrame Abnormal Process thành list dictionary để hiển thị (tương tự process_cpu_usage_data).
    """
    if df is None or df.empty:
        return []
    
    result = []
    for _, row in df.iterrows():
        result.append({
            'pid': str(row['pid']),
            'proc_name': str(row['proc_name']),
            'slice_name': str(row['slice_name']),
            'start_time': int(row['start_time']),
            'duration_ms': to_ms(row['duration_ns']) # Dùng hàm to_ms có sẵn
        })
    return result


def get_background_process_states(tp: TraceProcessor, start_ts: int, end_ts: int) -> List[Dict[str, Any]]:
    """
    Lấy danh sách các background process (theo pattern gms, google...) 
    có hoạt động (Running + Runnable) > 10ms trong khoảng thời gian launch.
    """
    if not start_ts or not end_ts or start_ts >= end_ts:
        return []

    duration = end_ts - start_ts

    # Danh sách các pattern tên process cần tìm
    target_patterns = [
        '%gms.persistent%', 
        '%googlequicksearchbox%', 
        '%com.google.android.play%',
        '%.apps.messaging%'
    ]
    
    # Tạo câu điều kiện OR (Fix lỗi process name null)
    or_clauses = " OR ".join([f"COALESCE(p.name, t.name) LIKE '{pat}'" for pat in target_patterns])

    # 1. Tìm Main Thread ID (tid) của các process này
    sql_find_tid = f"""
    SELECT 
        COALESCE(p.name, t.name) AS proc_name,
        t.tid
    FROM process p
    JOIN thread t ON p.upid = t.upid
    WHERE t.is_main_thread = 1
      AND ({or_clauses});
    """
    
    df_procs = query_df(tp, sql_find_tid)
    
    if df_procs is None or df_procs.empty:
        return []

    results = []
    
    # 2. Lặp qua từng process và kiểm tra điều kiện > 10ms
    for _, row in df_procs.iterrows():
        proc_name = str(row['proc_name'])
        tid = int(row['tid'])
        
        # Tái sử dụng hàm tính toán state
        states = get_thread_state_summary(tp, tid, start_ts, duration)
        
        runnable = states.get("R", 0.0) + states.get("R+", 0.0)
        running = states.get("Running", 0.0)
        
        # [LOGIC MỚI] Chỉ lấy nếu tổng Running + Runnable > 10ms
        if (runnable + running) > 10000000.0:
            item = {
                "Thread name": proc_name
                # Không cần các thông số chi tiết nữa vì bảng chỉ hiện tên
            }
            results.append(item)

    return results

# ====================================
# ======Abnormal process state========
# ====================================

# def get_background_process_states(tp: TraceProcessor, start_ts: int, end_ts: int) -> List[Dict[str, Any]]:
#     """
#     Lấy thông tin State (Running, Runnable, Sleeping...) của các background process cụ thể
#     trong khoảng thời gian từ start_ts đến end_ts.
    
#     [UPDATED] Fix lỗi process.name bị Null: 
#     Sử dụng COALESCE(p.name, t.name) để lấy tên process từ main thread nếu bảng process thiếu tên.
#     """
#     if not start_ts or not end_ts or start_ts >= end_ts:
#         return []

#     duration = end_ts - start_ts

#     # Danh sách các pattern tên process cần tìm
#     target_patterns = [
#         '%gms.persistent%', 
#         '%googlequicksearchbox%', 
#         '%com.google.android.play%',
#         '%.apps.messaging%'
#     ]
    
#     # [FIX] Tạo câu điều kiện kiểm tra trên cả p.name và t.name
#     # COALESCE(p.name, t.name) sẽ trả về p.name nếu có, nếu không trả về t.name
#     or_clauses = " OR ".join([f"COALESCE(p.name, t.name) LIKE '{pat}'" for pat in target_patterns])

#     # 1. Tìm Main Thread ID (tid) của các process này
#     sql_find_tid = f"""
#     SELECT 
#         COALESCE(p.name, t.name) AS proc_name,
#         t.tid
#     FROM process p
#     JOIN thread t ON p.upid = t.upid
#     WHERE t.is_main_thread = 1
#       AND ({or_clauses});
#     """
    
#     df_procs = query_df(tp, sql_find_tid)
    
#     # Debug: In ra nếu tìm thấy process để kiểm tra
#     # if df_procs is not None and not df_procs.empty:
#     #     print(f"  [DEBUG] Found background processes: {df_procs['proc_name'].tolist()}")

#     if df_procs is None or df_procs.empty:
#         return []

#     results = []
    
#     # 2. Lặp qua từng process tìm được và tính toán State summary
#     for _, row in df_procs.iterrows():
#         proc_name = str(row['proc_name'])
#         tid = int(row['tid'])
        
#         # Tái sử dụng hàm get_thread_state_summary đã có trong sql_query.py
#         states = get_thread_state_summary(tp, tid, start_ts, duration)
        
#         runnable = states.get("R", 0.0) + states.get("R+", 0.0)
        
#         item = {
#             "Thread name": proc_name,
#             "Sleeping": states.get("S", 0.0),             
#             "Runnable": runnable,                         
#             "Running": states.get("Running", 0.0),        
#             "Uninterruptible Sleep": states.get("D", 0.0) 
#         }
#         results.append(item)

#     return results

# -------------------------------------------------------------------
# 5. MAIN ANALYSIS LOGIC
# -------------------------------------------------------------------



# [File: sql_query.py]

# [File: sql_query.py]

def analyze_trace(tp: TraceProcessor, trace_path: str, pid_mapping: Dict[int, str] = None) -> Dict[str, Any]:
    """
    Analyze a trace file and extract performance metrics.
    
    Args:
        tp: TraceProcessor instance
        trace_path: Path to the trace file
        pid_mapping: Optional dict {PID: process_name} from dumpstate for CPU process mapping
    
    Returns:
        Dict containing all extracted metrics
    """
    metrics: Dict[str, Any] = {}

    ensure_slice_with_names_view(tp)

    # 1. Detect Recent Case & Launch Type
    file_name = Path(trace_path).stem.lower()
    # Kiểm tra flag is_recent dựa trên tên file
    is_recent = "recent" in file_name 
    
    app_pkg = detect_app_from_launch(tp)
    
    # Nếu là Recent mà không thấy launching slice, gán pkg giả định
    if not app_pkg:
        if is_recent:
            app_pkg = "com.sec.android.app.launcher" 
        else:
            raise RuntimeError(f"Không tìm được launching:... trong trace {trace_path}")

    # 2. Identify App Process (UPID/PID)
    # - Recent: Process chính chứa Resume/Choreographer thường là Launcher
    # - App thường: Tìm theo activityStart/Resume của app
    app_upid, app_pid, app_name, app_tid = None, None, None, None
    
    if is_recent:
        # Recent: Tìm process chứa 'activityResume' (Thường là Launcher)
        row_resume = find_slice(tp, name_exact='activityResume')
        if row_resume is not None:
            app_upid = int(row_resume['upid'])
            app_pid = int(row_resume['pid'])
            app_tid = int(row_resume['tid'])
            app_name = str(row_resume.get('process_name', 'Launcher'))
        else:
            # Fallback nếu không thấy Resume, thử tìm theo Launcher PID
            launcher_pid = get_launcher_pid(tp)
            if launcher_pid:
                app_pid = launcher_pid
                # Lấy UPID từ PID
                df_upid = query_df(tp, f"SELECT upid FROM process WHERE pid = {app_pid}")
                if df_upid is not None:
                     app_upid = int(df_upid.iloc[0]['upid'])
                     app_tid = app_pid # Fallback
            else:
                raise RuntimeError("Recent: Không tìm thấy process phù hợp (Resume/Launcher)")
    else:
        # Logic App thường
        app_proc = find_app_process(tp, app_pkg)
        if not app_proc:
            raise RuntimeError(f"Không tìm được process cho app {app_pkg}")
        app_upid, app_pid, app_name, app_tid = app_proc

    # 3. Execution Interval
    
    # [Touch Down]
    touch_down_ts = get_first_deliver_input(tp)
    if touch_down_ts is None:
        raise RuntimeError("Không tìm thấy deliverInputEvent trong trace")

    # [Animating] (Recent không có animating trong system_server)
    animating_end = 0
    if not is_recent:
        try:
            animating_end = get_animating(tp)
        except RuntimeError:
            # raise RuntimeError("Trace không hợp lệ: Không tìm thấy 'animating'")
            print("[WARN] Không tìm thấy 'animating', bỏ qua.") # SỬA: Print thay vì raise
            animating_end = 0

    # [Launching End]
    launching_end = get_launching_end(tp, app_pkg)
    
    # [Activity Idle]
    start_idle, end_idle = get_activity_idle_end(tp, app_upid)

    # [Calculated End TS]
    end_ts = None
    is_camera = "camera" in (app_pkg or "").lower()
    is_internet = "internet" in file_name or "browser" in (app_pkg or "").lower()
    
    if is_camera:
        slices_name = ["StartPreviewRequest", "onCreate", "OpenCameraRequest", "onResume"]
        df = get_slice_on_app_process(tp, app_pid, slices_name)
        result = process_multiple_slices_data(df)
        
        metrics["onCreate"] = to_ms(result.get("onCreate", [0, 0])[1])
        metrics["OpenCameraRequest"] = to_ms(result.get("OpenCameraRequest", [0, 0])[1])
        metrics["onResume"] = to_ms(result.get("onResume", [0, 0])[1])
        metrics["StartPreviewRequest"] = to_ms(result.get("StartPreviewRequest", [0, 0])[1])
        
        preview_data = result.get("StartPreviewRequest", [0, 0])
        if preview_data[1] > 0:
            end_ts = preview_data[0] + preview_data[1]
        else:
            end_ts = animating_end 

    elif is_recent:
        # RECENT: Ưu tiên activityIdle -> Launching End -> Fallback
        if end_idle:
            end_ts = end_idle
        elif launching_end:
            end_ts = launching_end
        else:
            # Fallback an toàn: Touch Down + 500ms
            end_ts = touch_down_ts + 500_000_000

    else:   
        # APP THƯỜNG
        if is_internet and start_idle and launching_end and (launching_end + 100_000_000 < start_idle):
            end_ts = animating_end
            start_idle = None
            end_idle = None
        elif end_idle:
            end_ts = end_idle
        else:
            end_ts = animating_end
            start_idle = None
            end_idle = None

    # Max với animating_end (chỉ áp dụng với App thường)
    if not is_recent:
        end_ts = max(end_ts, animating_end) if end_ts else animating_end

    metrics["App Execution Time"] = to_ms(end_ts - touch_down_ts) if end_ts else 0.0

    # 4. Detailed Metrics

    # [Touch Down ~ Start Proc]
    start_proc_info = get_start_proc_start(tp, app_pkg)
    
    # SỬA: Kiểm tra kỹ start_proc_info và phần tử đầu tiên
    if start_proc_info and start_proc_info[0] is not None:
        start_proc_ts, start_proc_dur, start_proc_end = start_proc_info
        # Thêm try-except hoặc kiểm tra None để an toàn tuyệt đối
        if start_proc_ts is not None and touch_down_ts is not None:
            metrics["Touch Down ~ Start Proc"] = to_ms(start_proc_ts - touch_down_ts)
        else:
            metrics["Touch Down ~ Start Proc"] = 0.0
        metrics["Start Proc"] = to_ms(start_proc_dur)  
    else:
        start_proc_ts, start_proc_dur, start_proc_end = None, None, None
        metrics["Touch Down ~ Start Proc"] = 0.0
        metrics["Start Proc"] = 0.0

    # [Launch Type]
    if is_recent:
        metrics["Launch Type"] = "Warm" # Recent luôn là Warm
    else:
        metrics["Launch Type"] = "Cold" if has_bind_application(tp, app_upid) else "Warm"

    # [ActivityThreadMain], [BindApp]
    act_main = get_event_ts(tp, app_upid, "ActivityThreadMain")
    if act_main:
        act_main_ts, act_main_dur, act_main_end = act_main
        metrics["Activity Thread Main"] = to_ms(act_main_dur)
    else:
        act_main_ts, act_main_dur, act_main_end = None, None, None
        metrics["Activity Thread Main"] = 0.0

    bind_app = get_event_ts(tp, app_upid, "bindApplication")
    if bind_app:
        bind_app_ts, bind_app_dur, bind_app_end = bind_app
        metrics["Bind Application"] = to_ms(bind_app_dur)
    else:
        bind_app_ts, bind_app_dur, bind_app_end = None, None, None
        metrics["Bind Application"] = 0.0

    # [Activity Start] 
    # FIX: Recent activityStart nằm ở Launcher, App thường nằm ở App Process
    act_start_ts, act_start_dur, act_start_end = None, None, None
    
    if is_recent:
        launcher_pid = get_launcher_pid(tp)
        if launcher_pid:
            # Tìm activityStart trong Launcher process
            row_start = find_slice(tp, name_exact='activityStart', pid=launcher_pid)
            if row_start is not None:
                act_start_ts = int(row_start['ts'])
                act_start_dur = int(row_start['dur'])
                act_start_end = int(row_start['end_ts'])
    else:
        act_start_info = get_event_ts(tp, app_upid, "activityStart")
        if act_start_info:
            act_start_ts, act_start_dur, act_start_end = act_start_info

    metrics["Activity Start"] = to_ms(act_start_dur) if act_start_dur else 0.0

    # [Activity Resume]
    cho_threshold = 0
    act_resume = get_event_ts(tp, app_upid, "activityResume")
    if act_resume:
        act_resume_ts, act_resume_dur, act_resume_end = act_resume
        metrics["Activity Resume"] = to_ms(act_resume_dur)
        cho_threshold = act_resume_end
    else:
        act_resume_ts, act_resume_dur, act_resume_end = None, None, None
        metrics["Activity Resume"] = 0.0

    # [Touch Info]
    launcher_pid = get_launcher_pid(tp)
    if launcher_pid is not None:
        touch_up, touch_up_end = get_end_deliver_input(tp, launcher_pid)
        if touch_up is not None:
            metrics["Touch Duration"] = to_ms(touch_up - touch_down_ts) 
            # Dùng act_start_ts đã fix ở trên
            if act_start_ts and act_start_ts > touch_up:
                metrics["Touch Up ~ Activity Start"] = to_ms(act_start_ts - touch_up)
            else:
                 metrics["Touch Up ~ Activity Start"] = 0.0
        else:
            metrics["Touch Duration"] = 0.0
            metrics["Touch Up ~ Activity Start"] = 0.0
    else:
        metrics["Touch Duration"] = 0.0
        metrics["Touch Up ~ Activity Start"] = 0.0

    # [Time Gaps]
    if start_proc_end and act_main_ts:
        metrics["Start Proc ~ ActivityThreadMain"] = to_ms(act_main_ts - start_proc_end) if act_main_ts > start_proc_end else 0.0
    else:
        metrics["Start Proc ~ ActivityThreadMain"] = 0.0

    if act_main_end and bind_app_ts:
        metrics["ActivityThreadMain ~ bindApplication"] = to_ms(bind_app_ts - act_main_end) if bind_app_ts > act_main_end else 0.0
    else:
        metrics["ActivityThreadMain ~ bindApplication"] = 0.0

    if bind_app_end and act_start_ts:
        metrics["bindApplication ~ activityStart"] = to_ms(act_start_ts - bind_app_end) if act_start_ts > bind_app_end else 0.0
    else:
        metrics["bindApplication ~ activityStart"] = 0.0

    if act_start_end and act_resume_ts:
        metrics["activityStart ~ activityResume"] = to_ms(act_resume_ts - act_start_end) if act_resume_ts > act_start_end else 0.0
    else:
        metrics["activityStart ~ activityResume"] = 0.0

    # [Choreographer]
    cho_info = get_choreographer(tp, app_pid, cho_threshold if cho_threshold else 0)
    if cho_info:
        cho_ts, cho_dur, cho_end = cho_info
        
        if is_camera and end_ts > cho_ts:
             metrics["Choreographer"] = to_ms(end_ts - cho_ts)
        else:
             # Fallback: Dùng duration của chính slice Choreographer 
             metrics["Choreographer"] = to_ms(cho_dur) if cho_dur else 0.0
    else:
        cho_ts, cho_dur, cho_end = None, None, None
        metrics["Choreographer"] = 0.0

    if act_resume_end and cho_ts:
        metrics["ActivityResume ~ Choreographer"] = to_ms(cho_ts - act_resume_end) if cho_ts > act_resume_end else 0.0
    else:
        metrics["ActivityResume ~ Choreographer"] = 0.0

    if cho_end and start_idle and not is_camera:
        metrics["Choreographer ~ ActivityIdle"] = to_ms(start_idle - cho_end) if cho_end is not None else 0.0
    elif launching_end is not None and start_idle and is_camera:
        metrics["Choreographer ~ ActivityIdle"] = to_ms(start_idle - launching_end) if launching_end is not None else 0.0
    else:
        metrics["Choreographer ~ ActivityIdle"] = 0.0

    # [ActivityIdle]
    if start_idle and end_idle:
        metrics["ActivityIdle"] = to_ms(end_idle - start_idle)
    else:
        metrics["ActivityIdle"] = 0.0

    if end_idle and animating_end and not is_recent:
        metrics["ActivityIdle ~ Animating end"] = to_ms(animating_end - end_idle) if animating_end > end_idle else 0.0
    else:
        metrics["ActivityIdle ~ Animating end"] = to_ms(animating_end - cho_end) if animating_end > cho_end else 0.0

    # [Thread State]
    state_summary = get_thread_state_summary(tp, app_tid, touch_down_ts, (end_ts - touch_down_ts) if end_ts else 0)
    metrics["Running"] = state_summary.get("Running", 0.0)
    metrics["Runnable"] = state_summary.get("R", 0.0) + state_summary.get("R+", 0.0)
    metrics["Uninterruptible Sleep"] = state_summary.get("D", 0.0)
    metrics["Sleeping"] = state_summary.get("S", 0.0)

    # [Block I/O]
    safe_start_time = touch_down_ts if touch_down_ts else 0
    safe_end_time = end_ts if end_ts else (safe_start_time + 10_000_000_000) # Fallback +10s

    block_io_df = top_block_IO(tp, app_pid, safe_start_time, safe_end_time)
    metrics["Block_IO_Data"] = process_block_io_data(block_io_df)

    # [LoadApkAssets]
    load_apk_pids = get_pid_list(tp) 
    if not load_apk_pids:
        load_apk_pids = [app_pid]
    if app_pid not in load_apk_pids:
        load_apk_pids.append(app_pid)
    loadapk_df = get_loadApkAsset(tp, load_apk_pids, touch_down_ts, end_ts if end_ts else 0)
    metrics["LoadApkAsset_Data"] = process_loadapk_data(loadapk_df)

    # [CPU Usage]
    cpu_cores = [0,1,2,3,4,5,6,7]
    dur_time = (end_ts - touch_down_ts) if end_ts else 0

    # 1. Get Top Process (with PID mapping from dumpstate)
    cpu_proc_df = get_top_cpu_usage_process(tp, touch_down_ts, dur_time, cpu_cores)
    metrics["CPU_Process_Data"] = process_cpu_data_process(cpu_proc_df, pid_mapping)
    
    # 2. Get Top Thread
    cpu_thread_df = get_top_cpu_usage_thread(tp, touch_down_ts, dur_time, cpu_cores)
    metrics["CPU_Thread_Data"] = process_cpu_data_thread(cpu_thread_df)

    # [Binder]
    binder_count, binder_dur = get_binder_transaction(tp, app_tid, end_ts if end_ts else 0)
    metrics["Binder_Transaction_Data"] = {
        'count': binder_count if binder_count is not None else 0,
        'duration_ms': binder_dur if binder_dur is not None else 0.0
    }

    # [Abnormal process]
    check_threshold = end_ts if end_ts else 0
    target_abnormal_slices = ['bindApplication'] 
    abnormal_df = get_abnormal_processes(tp, check_threshold, app_pid, target_abnormal_slices)
    metrics["Abnormal_Process_Data"] = process_abnormal_data(abnormal_df)

    # [Background Process States]
    bg_start_ts = touch_down_ts if touch_down_ts else 0
    bg_end_ts = end_ts if end_ts else 0
    metrics["Background_Process_States"] = get_background_process_states(tp, bg_start_ts, bg_end_ts)

    metrics["PID_Mapping"] = pid_mapping if pid_mapping else {}
    metrics["App Package"] = app_pkg 
    return metrics