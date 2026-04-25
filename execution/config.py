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
from sql_query.base import get_resource_path
from utils.trace.atracetosystrace import convert_trace
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
# v54.0 binary (upgraded from v30.0 Python wrapper)
if sys.platform == "win32":
    TP_FILENAME = "trace_processor.exe"
else:
    TP_FILENAME = "trace_processor"

# Local
RELATIVE_BIN_PATH = os.path.join("perfetto", TP_FILENAME)
# Build
# RELATIVE_BIN_PATH = os.path.join("perfetto_bin", TP_FILENAME)
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

# CRITICAL: Set environment variables TRƯỚC KHI import bất cứ thứ gì
os.environ['NUMPY_EXPERIMENTAL_ARRAY_FUNCTION'] = '0'

# Ép Python kết nối thẳng vào localhost, bỏ qua Proxy/VPN
os.environ['NO_PROXY'] = '127.0.0.1,localhost'
os.environ['no_proxy'] = '127.0.0.1,localhost'



