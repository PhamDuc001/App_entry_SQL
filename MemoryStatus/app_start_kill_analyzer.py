"""
Module for analyzing app start and kill events from dumpstate logs
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict


# App mappings
APP_PACKAGE_MAPPING = {
    'camera': 'com.sec.android.app.camera',
    'helloworld': 'com.samsung.performance.helloworld_v6',
    'calllog': 'com.samsung.android.dialer',
    'dial': 'com.samsung.android.dialer',
    'clock': 'com.sec.android.app.clockpackage',
    'contact': 'com.samsung.android.app.contacts',
    'calendar': 'com.samsung.android.calendar',
    'calculator': 'com.samsung.android.calendar',
    'gallery': 'com.sec.android.gallery3d',
    'message': 'com.samsung.android.messaging',
    'menu': 'com.sec.android.app.launcher',
    'myfile': 'com.sec.android.app.myfiles',
    'sip': 'com.samsung.android.honeyboard',
    'internet': 'com.sec.android.app.sbrowser',
    'note': 'com.samsung.android.app.notes',
    'setting': 'com.android.settings',
    'voice': 'com.sec.android.app.voicenote',
    'recent': 'com.sec.android.app.launcher'
}

FOLDER_APP_PART_MAPPING = {
    'camera': 1,
    'helloworld': 2,
    'calllog': 2,
    'dial': 2,
    'clock': 2,
    'contact': 3,
    'calendar': 3,
    'calculator': 3,
    'gallery': 4,
    'message': 4,
    'menu': 4,
    'myfile': 5,
    'sip': 5,
    'internet': 5,
    'note': 6,
    'setting': 6,
    'voice': 6,
    'recent': 6
}

# Reverse mapping for package to app name
PACKAGE_APP_MAPPING = {v: k for k, v in APP_PACKAGE_MAPPING.items()}

# Pre-compiled regex patterns
PROC_START_PATTERN = re.compile(r"I am_proc_start: \[.*?,.*?,.*?,(.*?),(.*?),")
KILL_PATTERN = re.compile(r"I am_kill : \[[^,]*,[^,]*,[^,]*,[^,]*,([^,]+),[^\]]*\]")
APP_TRANSITION_PATTERN = re.compile(r"I am_app_transition: \[(.*?),(?:.*?,){5}.*?\]")


@dataclass
class AppStartKillInfo:
    """Data class for app start/kill information"""
    app_name: str
    start_count: int = 0
    start_reasons: List[str] = None
    kill_count: int = 0
    kill_reasons: List[str] = None
    folder_name: str = ""  # Add folder name to track which folder this data came from
    
    def __post_init__(self):
        if self.start_reasons is None:
            self.start_reasons = []
        if self.kill_reasons is None:
            self.kill_reasons = []


class AppStartKillAnalyzer:
    """Analyzer for app start and kill events"""
    
    def __init__(self):
        self.app_info: Dict[str, AppStartKillInfo] = {}
        
    def analyze_file(self, file_path: Path, target_app: str) -> AppStartKillInfo:
        """
        Analyze a dumpstate file for app start/kill events for a specific app
        
        Args:
            file_path: Path to the dumpstate file
            target_app: Target app name to analyze
            
        Returns:
            AppStartKillInfo: Information about app start/kill events
        """
        # Get package name for the target app
        target_package = APP_PACKAGE_MAPPING.get(target_app)
        if not target_package:
            raise ValueError(f"Unknown app: {target_app}")
            
        # Initialize app info
        app_info = AppStartKillInfo(app_name=target_app)
        
        # Track if we've found the first app transition
        found_first_transition = False
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    # Check for app transition (first occurrence for target app)
                    if not found_first_transition:
                        transition_match = APP_TRANSITION_PATTERN.search(line)
                        if transition_match and transition_match.group(1) == target_package:
                            found_first_transition = True
                            # Stop processing after finding the first transition
                            break
                    
                    # Check for process start events
                    start_match = PROC_START_PATTERN.search(line)
                    if start_match:
                        package_name, start_reason = start_match.groups()
                        # Skip counting if start reason is 'activelaunch'
                        if package_name == target_package and start_reason != 'activelaunch':
                            app_info.start_count += 1
                            app_info.start_reasons.append(start_reason)
                    
                    # Check for kill events
                    kill_match = KILL_PATTERN.search(line)
                    if kill_match:
                        kill_reason = kill_match.group(1)
                        # Extract package name from the kill log (it's the 3rd field)
                        package_match = re.search(r"I am_kill : \[[^,]*,[^,]*,([^,]+),", line)
                        if package_match:
                            package_name = package_match.group(1)
                            if package_name == target_package:
                                app_info.kill_count += 1
                                app_info.kill_reasons.append(kill_reason)
                            
        except (IOError, OSError) as e:
            print(f"Error reading file {file_path}: {e}")
            
        return app_info
    
    def analyze_folder(self, folder_path: Path, part_name: str) -> List[AppStartKillInfo]:
        """
        Analyze all dumpstate files in a folder for all apps corresponding to the part
        
        Args:
            folder_path: Path to the folder containing dumpstate files
            part_name: Part name (e.g., '1part', '2part', etc.)
            
        Returns:
            List[AppStartKillInfo]: List of app start/kill information for all apps in this part
        """
        # Find all apps corresponding to this part
        target_apps = []
        for app, part in FOLDER_APP_PART_MAPPING.items():
            if f"{part}part" == part_name:
                target_apps.append(app)
                
        if not target_apps:
            return []
            
        # Find the largest dumpstate file in the folder
        largest_file = self._find_largest_file(folder_path)
        if not largest_file:
            return []
            
        # Analyze the file for each app in this part
        app_infos = []
        for target_app in target_apps:
            app_info = self.analyze_file(largest_file, target_app)
            # Set the folder name
            app_info.folder_name = folder_path.name
            app_infos.append(app_info)
            
        return app_infos
    
    def _find_largest_file(self, directory: Path) -> Optional[Path]:
        """Find largest file in directory"""
        try:
            return max(
                (f for f in directory.rglob("*") if f.is_file()),
                key=lambda f: f.stat().st_size,
                default=None
            )
        except (ValueError, OSError):
            return None
