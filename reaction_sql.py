#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reaction_sql.py

Xử lý batch traces để phân tích REACTION TIME (Sequence).
Tạo 2 file Excel: reaction_entry_... và reaction_reentry_...
"""

import os
import sys
import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List
from collections import defaultdict
from multiprocessing import Pool, cpu_count

import xlsxwriter
from perfetto.trace_processor.api import TraceProcessor, TraceProcessorConfig

from sql_query import *
# from atracetosystrace import convert_trace

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------
# TRACE_PROCESSOR_BIN = r"D:\Tools\CheckList\Bringup\Plan_convert_SQL\perfetto\trace_processor"
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
    "comsecandroidappmyfiles": "MyFiles",
    "comexampleedittexttest3": "SIP",
    "comsecandroidappsbrowser": "Internet",
    "comsamsungandroidappnotes": "Notes",
    "comandroidsettings": "Settings",
    "comsecandroidappvoicenote": "VoiceNote",
    "comgoogleandroidappsmessaging": "Messages",
}

# skip_apps = ['sip', 'menu', 'dial']
TARGET_APPS = [
    "camera",
    "helloworld",
    "calllog",
    "clock",
    "contact",
    "calendar",
    "calculator",
    "gallery",
    "message",
    "menu",
    "myfile",
    "sip",
    "internet",
    "note",
    "setting",
    "voice",
    "recent"
]
# ---------------------------------------------------------------------------
# Analysis Logic (Reaction Specific)
# ---------------------------------------------------------------------------

def analyze_reaction_trace(tp: TraceProcessor, trace_path: str) -> Dict[str, Any]:
    """
    Phân tích Reaction Time Sequence:
    Touch -> AddStartingWindow -> Choreographer -> onTransactionReady
    """
    metrics: Dict[str, Any] = {}
    
    # 1. Init Views
    ensure_slice_with_names_view(tp)
    
    # 2. Identify App & System Server
    app_pkg = detect_app_from_launch(tp)
    if not app_pkg:
        pass

    # App Process Info
    app_proc = find_app_process(tp, app_pkg) if app_pkg else None
    app_upid = app_proc[0] if app_proc else None

    # 3. Get Event Timestamps
    
    # [Touch Down]
    touch_down_ts = get_first_deliver_input(tp)
    if touch_down_ts is None:
        raise RuntimeError("Không tìm thấy Touch Down")

    # [Touch Up]
    launcher_pid = get_launcher_pid(tp)
    touch_up_ts = None
    if launcher_pid:
        t_up, t_up_end = get_end_deliver_input(tp, launcher_pid)
        touch_up_ts = t_up # Start Time của Touch Up slice

    # [AddStartingWindow] (System Server)
    asw_info = get_addStartingWindow(tp)
    asw_ts, asw_dur, asw_end = asw_info if asw_info else (None, None, None)

    # [Choreographer] (SystemUI Process - Reaction Logic)
    cho_ts, cho_dur, cho_end = (None, None, None)
    sysui_pids = get_pid_systemUI(tp)
    if sysui_pids:
        sysui_pid = int(sysui_pids[0])
        # sysui_pid = sysui_pids
        cho_info = get_reaction_choreographer(tp, sysui_pid)
        if cho_info:
            cho_ts, cho_dur, cho_end = cho_info
    else:
        print(f"    [WARN] Không tìm thấy SystemUI PID trong trace: {trace_path}")
        pass




    # [onTransactionReady] (System Server)
    otr_info = get_onTransactionReady(tp)
    otr_ts, otr_dur, otr_end = otr_info if otr_info else (None, None, None)

    # [drawFrame] - Empty for now
    df_ts = None

    # 4. Calculate Metrics
    
    # --- Touch Duration ---
    # Touch Duration = Touch Up - Touch Down
    if touch_up_ts and touch_down_ts:
        metrics["Touch Duration"] = to_ms(touch_up_ts - touch_down_ts)
    else:
        metrics["Touch Duration"] = 0.0

    # --- Touch Up ~ AddStartingWindow ---
    # Tính từ Start TouchUp -> Start AddStartingWindow
    if touch_up_ts and asw_ts and asw_ts > touch_up_ts:
        metrics["Touch Up ~ AddStartingWindow"] = to_ms(asw_ts - touch_up_ts)
    else:
        metrics["Touch Up ~ AddStartingWindow"] = 0.0

    # --- AddStartingWindow Duration ---
    metrics["AddStartingWindow"] = to_ms(asw_dur)

    # --- AddStartingWindow ~ Choreographer ---
    if asw_ts and cho_ts and cho_ts > asw_ts:
        metrics["AddStartingWindow ~ Choreographer"] = to_ms(cho_ts - asw_end)
    else:
        metrics["AddStartingWindow ~ Choreographer"] = 0.0

    # --- Choreographer Duration ---
    metrics["Choreographer"] = to_ms(cho_dur)

    # --- Choreographer ~ onTransactionReady ---
    if cho_ts and otr_ts and otr_ts > cho_ts:
        metrics["Choreographer ~ onTransactionReady"] = to_ms(otr_ts - cho_ts)
    else:
        metrics["Choreographer ~ onTransactionReady"] = 0.0

    # --- onTransactionReady Duration ---
    metrics["onTransactionReady"] = to_ms(otr_dur)

    # --- onTransactionReady ~ drawFrame ---
    if launcher_pid:
        drawFrame = get_drawFrame(tp, launcher_pid)

    df_end = None
    if drawFrame is not None:
        df_ts, df_dur, df_end = drawFrame
        metrics["drawFrame"] = to_ms(df_dur)
        metrics["onTransactionReady ~ drawFrame"] = to_ms(df_ts - otr_end)
    else:
        metrics["drawFrame"] = "" 
        metrics["onTransactionReady ~ drawFrame"] = ""

    # --- App Reaction Time --- 
    if touch_down_ts and df_end is not None:
        # print(f"Touch Down: {touch_down_ts}, OTR End: {otr_end}")
        metrics["App Reaction Time"] = to_ms(df_end - touch_down_ts)
    else:
        metrics["App Reaction Time"] = 0.0

    metrics["App Package"] = app_pkg if app_pkg else "Unknown"
    return metrics


# ---------------------------------------------------------------------------
# Batch Processing (Multiprocessing)
# ---------------------------------------------------------------------------

def process_single_trace(args: Tuple[str, int, str]) -> Tuple[str, int, str, Optional[Dict[str, Any]]]:
    file_path, occurrence, app_name = args
    config = TraceProcessorConfig(bin_path=TRACE_PROCESSOR_BIN)
    
    try:
        with TraceProcessor(trace=file_path, config=config) as tp:
            # GỌI HÀM PHÂN TÍCH MỚI
            metrics = analyze_reaction_trace(tp, file_path)
            category = 'entry' if occurrence % 2 == 1 else 'reentry'
            return (app_name, occurrence, category, metrics)
    except Exception as e:
        print(f"    [ERROR REACTION] {Path(file_path).name}: {e}")
        return (app_name, occurrence, 'entry' if occurrence % 2 == 1 else 'reentry', None)


def process_all_traces(folder_path: str, label: str, num_workers: int = 8, target_apps: List[str] = None):
    # Fallback nếu không truyền
    if target_apps is None:
        target_apps = TARGET_APPS

    trace_files = sorted([str(f) for f in Path(folder_path).glob("*.log")])
    
    if label == "DUT":
        print(f"Target Apps Filter: {target_apps}")

    app_groups = defaultdict(list)
    app_occurrence_count = defaultdict(int)
    
    for file_path in trace_files:
        filename = Path(file_path).stem
        parts = filename.split('_')
        
        if len(parts) >= 2:
            raw_app_name = parts[-1] 
            app_name = raw_app_name.lower() 
            
            # SỬA: Check trong target_apps được truyền vào
            if app_name not in target_apps:
                continue
            
            app_occurrence_count[app_name] += 1
            app_groups[app_name].append((file_path, app_occurrence_count[app_name]))

    tasks = []
    for app_name, file_list in app_groups.items():
        for file_path, occurrence in file_list:
            tasks.append((file_path, occurrence, app_name))

    print(f"\n[{label}] Processing {len(tasks)} files (Reaction Analysis)...")
    
    # Pre-allocate results structure
    results = defaultdict(lambda: {'entry': [None] * 50, 'reentry': [None] * 50})

    pool = Pool(processes=num_workers)
    try:
        for i, (app_name, occurrence, category, metrics) in enumerate(pool.imap(process_single_trace, tasks)):
            if metrics:
                cycle_index = (occurrence - 1) // 2
                while len(results[app_name][category]) <= cycle_index:
                    results[app_name][category].append(None)
                results[app_name][category][cycle_index] = metrics
                print(f"  - [{i+1}/{len(tasks)}] {app_name} - {category} - cycle {cycle_index + 1}")
    finally:
        pool.close()
        pool.join()

    cleaned = {}
    for app, cats in results.items():
        cleaned[app] = {
            'entry': [m for m in cats['entry'] if m is not None],
            'reentry': [m for m in cats['reentry'] if m is not None]
        }
    return cleaned


# ---------------------------------------------------------------------------
# Excel Output
# ---------------------------------------------------------------------------

def write_value_or_empty(ws, row, col, value, fmt):
    """Helper: Ghi giá trị vào Excel, nếu 0.0 hoặc rỗng thì để trắng."""
    if value == 0.0 or value == "" or value is None:
        ws.write(row, col, "", fmt)
    else:
        ws.write(row, col, value, fmt)

def create_excel_output(
    dut_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ref_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    output_folder: str,
    header_title: str
) -> None:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for launch_type in ['entry', 'reentry']:
        output_path = os.path.join(
            output_folder,
            f"reaction_{launch_type}_{timestamp}.xlsx"
        )
        
        wb = xlsxwriter.Workbook(output_path)
        
        # --- Formats  ---
        fmt_header_main = wb.add_format({"bold": True, "align": "center", "bg_color": "#D3D3D3"})
        fmt_header_dut = wb.add_format({"bold": True, "align": "center", "bg_color": "#90EE90"})
        fmt_header_ref = wb.add_format({"bold": True, "align": "center", "bg_color": "#FFB366"})
        fmt_header_diff = wb.add_format({"bold": True, "align": "center", "bg_color": "#FFFF99"})
        
        fmt_label = wb.add_format({"align": "left"})
        # Format highlight
        fmt_label_highlight = wb.add_format({"align": "left", "italic": True, "font_color": "#008000"})
        
        fmt_val = wb.add_format({"num_format": "0.000", "align": "center"})
        fmt_text = wb.add_format({"align": "center"})
        
        # Conditional formatting  Diff
        fmt_diff_slow = wb.add_format({"num_format": "0.000", "align": "center", "bg_color": "#FFB3B3"})  # Đỏ nhạt
        fmt_diff_fast = wb.add_format({"num_format": "0.000", "align": "center", "bg_color": "#B3FFB3"})  # Xanh nhạt
        fmt_diff_normal = wb.add_format({"num_format": "0.000", "align": "center"})
        
        all_apps = set(dut_results.keys()) | set(ref_results.keys())
        
        for app_name in sorted(all_apps):
            sheet_name = APP_MAPPING.get(f"com.sec.android.{app_name}", app_name.capitalize())
            ws = wb.add_worksheet(sheet_name)
            
            dut_cycles = dut_results.get(app_name, {}).get(launch_type, [])
            ref_cycles = ref_results.get(app_name, {}).get(launch_type, [])
            
            if not dut_cycles and not ref_cycles:
                continue
            
            # Calculate number of cycles max 
            num_dut_cycles = len(dut_cycles)
            num_ref_cycles = len(ref_cycles)
            max_cycles = max(num_dut_cycles, num_ref_cycles)
            
            # === HEADER ROW ===
            # A1: Header Title 
            ws.write("A1", header_title, fmt_header_main)
            
            # Merge Header DUT
            col_offset = 1
            ws.merge_range(0, col_offset, 0, col_offset + max_cycles, "DUT (ms)", fmt_header_dut)
            
            # Merge Header REF
            col_offset += max_cycles + 1
            ws.merge_range(0, col_offset, 0, col_offset + max_cycles, "REF (ms)", fmt_header_ref)
            
            # Header Diff
            col_offset += max_cycles + 1
            ws.write(0, col_offset, "Diff", fmt_header_diff)

            # === SUB-HEADER ROW (Cycle 1... Avg) ===
            col_idx = 1
            # DUT Sub-headers
            for i in range(1, max_cycles + 1):
                ws.write(1, col_idx, f"Cycle {i}", fmt_header_dut)
                col_idx += 1
            ws.write(1, col_idx, "Avg", fmt_header_dut)
            col_idx += 1
            
            # REF Sub-headers
            for i in range(1, max_cycles + 1):
                ws.write(1, col_idx, f"Cycle {i}", fmt_header_ref)
                col_idx += 1
            ws.write(1, col_idx, "Avg", fmt_header_ref)
            col_idx += 1
            
            # Diff Sub-header (Empty)
            ws.write(1, col_idx, "", fmt_header_diff)
            
            # Set width
            ws.set_column("A:A", 35)
            ws.set_column(1, col_idx, 12)
            
            # === DEFINE ROWS ===
            prefix = "1st" if launch_type == "entry" else "2rd"
            
            # Structure metric table
            metric_rows = [
                (f"{prefix} {app_name} (Reaction)", "App Reaction Time"),
                ("", ""),
                ("Touch Duration", "Touch Duration"),
                ("~", "Touch Up ~ AddStartingWindow"),
                ("AddStartingWindow", "AddStartingWindow"),
                ("~", "AddStartingWindow ~ Choreographer"),
                ("Choreographer", "Choreographer"),
                ("~", "Choreographer ~ onTransactionReady"),
                ("onTransactionReady", "onTransactionReady"),
                ("~", "onTransactionReady ~ drawFrame"),
                ("drawFrame", "drawFrame"),
            ]
            
            # Các key cần bôi màu xanh nghiêng
            highlight_keys = []
            
            # === DATA ROWS ===
            row_idx = 2
            for display_name, metric_key in metric_rows:
                if display_name == "":  # Separator
                    row_idx += 1
                    continue
                
                # 1. Ghi tên dòng (Label) với format tương ứng
                if metric_key in highlight_keys:
                    ws.write(row_idx, 0, display_name, fmt_label_highlight)
                else:
                    ws.write(row_idx, 0, display_name, fmt_label)
                
                # --- DUT DATA ---
                col_idx = 1
                dut_values = []
                for i in range(max_cycles):
                    if i < len(dut_cycles):
                        # Lấy giá trị, nếu key chưa có (ví dụ drawFrame rỗng) thì trả về 0.0
                        val = dut_cycles[i].get(metric_key, 0.0)
                        # Nếu giá trị là string rỗng (do logic placeholder) thì coi là 0.0
                        if val == "": val = 0.0
                        
                        write_value_or_empty(ws, row_idx, col_idx, float(val), fmt_val)
                        dut_values.append(float(val))
                    else:
                        ws.write(row_idx, col_idx, "", fmt_val)
                    col_idx += 1
                
                # DUT Avg
                dut_avg = sum(dut_values) / len(dut_values) if dut_values else 0.0
                write_value_or_empty(ws, row_idx, col_idx, dut_avg, fmt_val)
                col_idx += 1
                
                # --- REF DATA ---
                ref_values = []
                for i in range(max_cycles):
                    if i < len(ref_cycles):
                        val = ref_cycles[i].get(metric_key, 0.0)
                        if val == "": val = 0.0
                        
                        write_value_or_empty(ws, row_idx, col_idx, float(val), fmt_val)
                        ref_values.append(float(val))
                    else:
                        ws.write(row_idx, col_idx, "", fmt_val)
                    col_idx += 1
                
                # REF Avg
                ref_avg = sum(ref_values) / len(ref_values) if ref_values else 0.0
                write_value_or_empty(ws, row_idx, col_idx, ref_avg, fmt_val)
                col_idx += 1
                
                # --- DIFF (DUT - REF) ---
                # Only diff if 2 sets have data
                if dut_avg != 0 and ref_avg != 0:
                    diff_val = dut_avg - ref_avg
                    
                    # Warining > 10ms
                    if diff_val > 10:
                        fmt_diff = fmt_diff_slow
                    elif diff_val < -10:
                        fmt_diff = fmt_diff_fast
                    else:
                        fmt_diff = fmt_diff_normal
                    
                    write_value_or_empty(ws, row_idx, col_idx, diff_val, fmt_diff)
                else:
                    ws.write(row_idx, col_idx, "", fmt_diff_normal)
                
                row_idx += 1
                
        wb.close()
        print(f"\n Created: {output_path}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def collect_trace_files(folder_path: str) -> List[str]:
    """Helper: Collect file .log trong folder"""
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted([str(f) for f in folder.glob("*.log")])

# ... (phần đầu file giữ nguyên) ...

# ---------------------------------------------------------------------------
# Main Function for External Call
# ---------------------------------------------------------------------------

def run_analysis(dut_folder: str, ref_folder: str, target_apps: List[str] = None) -> None:
    """
    Phân tích Reaction Time từ các trace trong DUT và REF folders
    
    Args:
        dut_folder: Đường dẫn folder DUT
        ref_folder: Đường dẫn folder REF
    """
    num_workers = min(cpu_count(), 8)

    print("="*60)
    print("REACTION TIME ANALYSIS")
    print("="*60)

    # 1. Processing
    dut_res = process_all_traces(dut_folder, "DUT", num_workers, target_apps)
    ref_res = process_all_traces(ref_folder, "REF", num_workers, target_apps)

    # 2. Extract Header Title từ file đầu tiên của DUT
    header_title = "Reaction Metric" # Default
    dut_files = collect_trace_files(dut_folder)
    if dut_files:
        first_file = Path(dut_files[0]).stem
        parts = first_file.split("_")
        if len(parts) >= 2:
            header_title = f"{parts[0]}_{parts[1]}"
        else:
            header_title = first_file

    # 3. Generating Excel
    print("\nGenerating Excel...")
    create_excel_output(dut_res, ref_res, dut_folder, header_title)
    print("\nDone.")

# ---------------------------------------------------------------------------
# Standalone Execution
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print("Usage: python reaction_sql.py <dut_folder> <ref_folder>")
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
