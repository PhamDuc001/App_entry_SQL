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

def process_single_trace(args: Tuple[str, int, str]) -> Tuple[str, int, str, Optional[Dict[str, Any]], str]:
    """
    Xử lý một trace file duy nhất (để chạy trong multiprocessing pool).
    
    Args:
        args: (file_path, occurrence, app_name)
    
    Returns:
        (app_name, occurrence, category, metrics, filename) hoặc (app_name, occurrence, category, None, filename) nếu lỗi
    """
    file_path, occurrence, app_name = args
    filename = Path(file_path).stem
    config = TraceProcessorConfig(bin_path=TRACE_PROCESSOR_BIN)
    
    try:
        with TraceProcessor(trace=convert_trace(file_path), config=config) as tp:
            metrics = analyze_trace(tp, file_path)
            category = 'entry' if occurrence % 2 == 1 else 'reentry'
            return (app_name, occurrence, category, metrics, filename)
    except Exception as e:
        print(f"    [ERROR] {Path(file_path).name}: {e}")
        return (app_name, occurrence, 'entry' if occurrence % 2 == 1 else 'reentry', None, filename)


def process_all_traces(folder_path: str, label: str, num_workers: int = 8, target_apps: List[str] = None) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Xử lý tất cả traces trong folder với multiprocessing và phân loại theo app và entry/re-entry.
    
    Args:
        folder_path: Đường dẫn folder chứa traces
        label: "DUT" hoặc "REF"
        num_workers: Số lượng processes chạy song song (default: 4)
    
    Returns:
        Dict[app_name, Dict["entry"|"reentry", List[metrics_dict]]]
    """
    trace_files = collect_trace_files(folder_path)
    app_groups = group_traces_by_app(trace_files, target_apps)
    
    
    # Chuẩn bị danh sách tasks cho multiprocessing
    tasks = []
    for app_name, file_list in app_groups.items():
        for file_path, occurrence in file_list:
            tasks.append((file_path, occurrence, app_name))
    
    print(f"\n[{label}] Processing {len(tasks)} trace files with {num_workers} workers...")
    
    # Chạy song song với Pool
    results = defaultdict(lambda: {'entry': [None] * 100, 'reentry': [None] * 100})  # Pre-allocate
    
    pool = Pool(processes=num_workers)
    try:
        for i, (app_name, occurrence, category, metrics, filename) in enumerate(pool.imap(process_single_trace, tasks)):
            if metrics:
                cycle_index = (occurrence - 1) // 2
                while len(results[app_name][category]) <= cycle_index:
                    results[app_name][category].append(None)
                
                results[app_name][category][cycle_index] = metrics
                print(f"  - [{i+1}/{len(tasks)}] {app_name} - {category} - cycle {cycle_index + 1} - {filename}")
    finally:
        pool.close() 
        pool.join()  
    
    # Loại bỏ None values và trim lists
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
            write_value_or_empty(ws, row_idx, col_idx, diff_val, fmt_diff)
        else:
            ws.write(row_idx, col_idx, "", fmt_text)

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
        # PREPARE DATA FOR LEFT TABLE (PROCESS)
        # ---------------------------------------------------------
        dut_p = all_dut_proc[cycle_idx] if cycle_idx < len(all_dut_proc) else []
        ref_p = all_ref_proc[cycle_idx] if cycle_idx < len(all_ref_proc) else []
        
        merged_p = {}
        for x in dut_p: merged_p[x['proc_name']] = {'dut': x['dur_ms'], 'ref': 0.0}
        for x in ref_p:
            name = x['proc_name']
            if name not in merged_p: merged_p[name] = {'dut': 0.0, 'ref': 0.0}
            merged_p[name]['ref'] = x['dur_ms']
            
        final_proc = []
        for name, v in merged_p.items():
            final_proc.append({'name': name, 'dut': v['dut'], 'ref': v['ref'], 'diff': v['dut'] - v['ref']})
        
        # Sort Diff -> Take Top 10
        top_proc = sorted(final_proc, key=lambda x: x['diff'], reverse=True)[:10]

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

def run_analysis(dut_folder: str, ref_folder: str, target_apps: List[str] = None) -> None:
    """
    Phân tích hiệu năng từ các trace trong DUT và REF folders
    
    Args:
        dut_folder: Đường dẫn folder DUT
        ref_folder: Đường dẫn folder REF
    """
    num_workers = min(cpu_count(), 8)
    
    if not os.path.exists(dut_folder):
        raise FileNotFoundError(f"DUT folder not found: {dut_folder}")
    if not os.path.exists(ref_folder):
        raise FileNotFoundError(f"REF folder not found: {ref_folder}")
    
    print("=" * 70)
    print("BATCH EXECUTION TIME ANALYSIS")
    print(f"Workers: {num_workers} | Available CPUs: {cpu_count()}")
    print("=" * 70)
    
    start_time = datetime.datetime.now()

    # Process DUT folder
    print("\n[1/2] Processing DUT folder...")
    dut_results = process_all_traces(dut_folder, "DUT", num_workers, target_apps)
    
    # Process REF folder
    print("\n[2/2] Processing REF folder...")
    ref_results = process_all_traces(ref_folder, "REF", num_workers, target_apps)
    
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
    if len(sys.argv) not in [3, 4]:
        print("Usage: python execution_sql_batch.py <dut_folder> <ref_folder> [num_workers]")
        print("  num_workers: Number of parallel processes (default: 4)")
        sys.exit(1)
    
    dut_folder = sys.argv[1]
    ref_folder = sys.argv[2]
    
    try:
        run_analysis(dut_folder, ref_folder)
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
