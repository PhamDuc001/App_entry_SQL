#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shared/config.py

Centralized configuration for TraceTool.
Contains all shared constants: APP_MAPPING, TARGET_APPS, trace processor config, etc.
"""

import os
import sys

from sql_query.base import get_resource_path

# ---------------------------------------------------------------------------
# Trace Processor Binary Configuration
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    TP_FILENAME = "trace_processor.exe"
else:
    TP_FILENAME = "trace_processor"  # Linux/macOS binary không có extension

# Hai chế độ chạy: Local (dev) và Build (PyInstaller)
RELATIVE_BIN_PATH_LOCAL = os.path.join("perfetto", TP_FILENAME)
RELATIVE_BIN_PATH_BUILD = os.path.join("perfetto_bin", TP_FILENAME)

def get_trace_processor_bin(mode: str = "local") -> str:
    """
    Lấy đường dẫn tới trace_processor binary.
    
    Args:
        mode: "local" cho dev mode, "build" cho PyInstaller mode
        
    Returns:
        Absolute path tới trace_processor binary
    """
    if mode == "build":
        return get_resource_path(RELATIVE_BIN_PATH_BUILD)
    return get_resource_path(RELATIVE_BIN_PATH_LOCAL)


# ---------------------------------------------------------------------------
# App Mapping (package-style keys → Display Names)
# Dùng chung cho execution và reaction modules
# ---------------------------------------------------------------------------
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
    "comsec.androidappmyfiles": "MyFiles",
    "comexampleedittexttest3": "SIP",
    "comsecandroidappsbrowser": "Internet",
    "comsamsungandroidappnotes": "Notes",
    "comandroidsettings": "Settings",
    "comsecandroidappvoicenote": "VoiceNote",
    "comgoogleandroidappsmessaging": "Messages",
}

# ---------------------------------------------------------------------------
# Target Apps — dùng cho cả execution và reaction
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Cold/Warm Launch Keys — dùng cho execution masking logic
# ---------------------------------------------------------------------------
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
# App Name Normalization — fix common typos
# ---------------------------------------------------------------------------
APP_NAME_NORMALIZATION = {
    "calender": "calendar",  # Fix "calender" → "calendar"
    "recorder": "voice"
}

# ---------------------------------------------------------------------------
# Cache Configuration
# ---------------------------------------------------------------------------
CACHE_VERSION = "1.0"  # Tăng lên "1.1", "2.0"... khi thay đổi cấu trúc data
