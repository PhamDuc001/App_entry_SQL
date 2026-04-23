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

import pickle
import traceback

import xlsxwriter
from perfetto.trace_processor.api import TraceProcessor, TraceProcessorConfig

from sql_query import *
# from atracetosystrace import convert_trace

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------
# TRACE_PROCESSOR_BIN = r"D:\Tools\CheckList\Bringup\Plan_convert_SQL\perfetto\trace_processor"
if sys.platform == "win32":
    TP_FILENAME = "trace_processor.exe"
else:
    TP_FILENAME = "trace_processor.exe"

# Local
# RELATIVE_BIN_PATH = os.path.join("perfetto", TP_FILENAME)
# Build
RELATIVE_BIN_PATH = os.path.join("perfetto_bin", TP_FILENAME)
#==============================================================
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

CACHE_VERSION = "1.0"  # Reaction cache version

# ---------------------------------------------------------------------------
# Analysis Logic (Reaction Specific)
# ---------------------------------------------------------------------------

def analyze_reaction_trace(tp: TraceProcessor, trace_path: str) -> Dict[str, Any]:
    """
    Phân tích Reaction Time Sequence:
    Touch -> AddStartingWindow -> Choreographer -> startAnimation
    """
    metrics: Dict[str, Any] = {}
    
    # 1. Init Views
    ensure_slice_with_names_view(tp)
    
    # 2. Identify App & System Server
    app_pkg = detect_app_from_launch(tp)
    if not app_pkg:
        pass

    # App Process Info
    app_proc = find_app_process(tp)
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
        print(f"    [WARN] Cannot find SystemUI PID in trace: {trace_path}")
        pass

    # [startAnimation] (System Server)
    otr_info = get_onTransactionReady(tp)     # get startAnimation
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

    # --- Choreographer ~ startAnimation ---
    if cho_end and otr_ts and otr_ts > cho_end:
        metrics["Choreographer ~ startAnimation"] = to_ms(otr_ts - cho_end)
    else:
        metrics["Choreographer ~ startAnimation"] = 0.0

    # --- startAnimation Duration ---
    metrics["startAnimation"] = to_ms(otr_dur)

    # --- startAnimation ~ drawFrame ---
    if launcher_pid:
        drawFrame = get_drawFrame(tp, launcher_pid)

    df_end = None
    if drawFrame is not None:
        df_ts, df_dur, df_end = drawFrame
        metrics["drawFrame"] = to_ms(df_dur)
        metrics["startAnimation ~ drawFrame"] = to_ms(df_ts - otr_end)
    else:
        metrics["drawFrame"] = "" 
        metrics["startAnimation ~ drawFrame"] = ""

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



