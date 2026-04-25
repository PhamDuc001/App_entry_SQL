# shared/app_config.py
"""
Centralized app configuration used across execution, reaction, and other modules.
Single source of truth for APP_MAPPING, TARGET_APPS, and related constants.
"""

# Package name -> Display name mapping
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

# Target app keywords for trace file matching
TARGET_APPS = [
    "camera",
    "hello",
    "call",
    "clock",
    "contact",
    "calendar",
    "calender",
    "calculator",
    "gallery",
    "message",
    "menu",
    "myfile",
    "internet",
    "note",
    "setting",
    "voice",
    "recent",
]

# App name normalization map - fix common typos/misspellings
APP_NAME_NORMALIZATION = {
    "calender": "calendar",
    "recorder": "voice",
}

# Metrics only applicable to Cold launch
COLD_ONLY_KEYS = {
    "Touch Down ~ Start Proc",
    "Start Proc",
    "Start Proc ~ ActivityThreadMain",
    "Activity Thread Main",
    "ActivityThreadMain ~ bindApplication",
    "Bind Application",
    "bindApplication ~ activityStart",
}

# Metrics only applicable to Warm launch
WARM_ONLY_KEYS = {
    "Touch Duration",
    "Touch Up ~ Activity Start",
}
