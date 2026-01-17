#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dumpstate_parser.py

Module để parse file dumpstate.txt từ Bugreport và map PID -> Process Name.
Sử dụng cho bảng Top CPU Process trong execution_sql.py.
"""

import os
import re
import zipfile
import shutil
from typing import Dict, Optional, List
from pathlib import Path


# ---------------------------------------------------------------------------
# App Group Mapping (6 nhóm test)
# ---------------------------------------------------------------------------
APP_GROUPS = {
    1: ['camera'],
    2: ['hello', 'call', 'dial', 'clock'],
    3: ['contact', 'calendar', 'calculator'],
    4: ['gallery', 'message', 'menu'],
    5: ['myfile', 'sip', 'internet'],
    6: ['note', 'setting', 'voice', 'recent'],
}


def get_app_group(app_name: str) -> int:
    """
    Map tên app -> group number (1-6).
    Sử dụng logic 'contains' để match các case như hello/helloworld, myfiles/myfile.
    
    Args:
        app_name: Tên app từ file .log (vd: 'camera', 'hello', 'helloworld')
    
    Returns:
        Group number (1-6) hoặc 0 nếu không tìm thấy
    """
    app_lower = app_name.lower()
    for group_num, app_list in APP_GROUPS.items():
        for app_pattern in app_list:
            if app_pattern in app_lower:
                return group_num
    return 0  # Không tìm thấy group


def parse_pid_mapping(dumpstate_content: str) -> Dict[int, str]:
    """
    Parse phần 'Total PSS by process:' từ nội dung dumpstate.txt.
    Trích xuất mapping {PID: process_name}.
    
    Format dòng:
        314,911K: com.android.systemui (pid 2009)    (26,367K in swap)
    
    Args:
        dumpstate_content: Nội dung file dumpstate.txt
    
    Returns:
        Dict mapping {PID (int): process_name (str)}
    """
    pid_mapping: Dict[int, str] = {}
    
    # Tìm vị trí bắt đầu "Total PSS by process:"
    start_marker = "Total PSS by process:"
    end_marker = "Total PSS by OOM adjustment:"
    
    start_idx = dumpstate_content.find(start_marker)
    if start_idx == -1:
        return pid_mapping
    
    end_idx = dumpstate_content.find(end_marker, start_idx)
    if end_idx == -1:
        # Nếu không tìm thấy end marker, lấy 50000 ký tự tiếp theo
        section = dumpstate_content[start_idx:start_idx + 50000]
    else:
        section = dumpstate_content[start_idx:end_idx]
    
    # Regex để parse mỗi dòng
    # Format: "    314,911K: com.android.systemui (pid 2009)"
    # Có thể có thêm info như "/ activities" sau pid
    pattern = r'^\s*([\d,]+)K:\s+(.+?)\s+\(pid\s+(\d+)'
    
    for line in section.split('\n'):
        match = re.match(pattern, line)
        if match:
            # memory_kb = match.group(1)  # Không cần dùng
            process_name = match.group(2).strip()
            pid = int(match.group(3))
            pid_mapping[pid] = process_name
    
    return pid_mapping


def find_largest_txt_in_folder(folder_path: str) -> Optional[str]:
    """
    Tìm file .txt có dung lượng lớn nhất trong folder.
    
    Args:
        folder_path: Đường dẫn folder
    
    Returns:
        Nội dung file .txt lớn nhất hoặc None
    """
    largest_file = None
    largest_size = 0
    
    folder = Path(folder_path)
    if not folder.exists():
        return None
    
    for txt_file in folder.glob('*.txt'):
        size = txt_file.stat().st_size
        if size > largest_size:
            largest_size = size
            largest_file = txt_file
    
    if largest_file:
        try:
            # Thử đọc với encoding utf-8, fallback sang latin-1
            try:
                return largest_file.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                return largest_file.read_text(encoding='latin-1')
        except Exception as e:
            print(f"[Error] Cannot read {largest_file}: {e}")
            return None
    
    return None


def find_dumpstate_content(path: str, extracted: bool = False) -> Optional[str]:
    """
    Tìm và đọc nội dung file dumpstate.txt.
    
    Args:
        path: Đường dẫn đến file .zip hoặc folder đã giải nén
        extracted: 
            - True: path là folder đã giải nén sẵn
            - False: path là file .zip, cần giải nén tạm thời
    
    Returns:
        Nội dung file dumpstate.txt hoặc None nếu không tìm thấy
    """
    path_obj = Path(path)
    
    if extracted:
        # Path là folder đã giải nén, tìm .txt lớn nhất
        if path_obj.is_dir():
            return find_largest_txt_in_folder(str(path_obj))
        return None
    else:
        # Path là file .zip, cần giải nén tạm thời
        if not path_obj.suffix.lower() == '.zip':
            return None
        
        if not path_obj.exists():
            return None
        
        # Tạo folder tạm để giải nén
        temp_folder = path_obj.parent / f"_temp_{path_obj.stem}"
        
        try:
            # Giải nén
            with zipfile.ZipFile(str(path_obj), 'r') as zip_ref:
                zip_ref.extractall(str(temp_folder))
            
            # Tìm file .txt lớn nhất
            content = find_largest_txt_in_folder(str(temp_folder))
            
            return content
        except Exception as e:
            print(f"[Error] Cannot extract {path}: {e}")
            return None
        finally:
            # Xóa folder tạm
            if temp_folder.exists():
                try:
                    shutil.rmtree(str(temp_folder))
                except Exception as e:
                    print(f"[Warning] Cannot delete temp folder {temp_folder}: {e}")


def get_bugreport_group_from_name(filename: str) -> int:
    """
    Xác định group number từ tên file bugreport.
    
    Ví dụ: A576BYK7_BOS_251128_251128_085123_1part_Bugreport.zip -> group 1
    
    Args:
        filename: Tên file (không bao gồm path)
    
    Returns:
        Group number (1-6) hoặc 0 nếu không xác định được
    """
    # Pattern: tìm "Xpart" trong tên file (X = 1-6)
    match = re.search(r'(\d)part', filename.lower())
    if match:
        group = int(match.group(1))
        if 1 <= group <= 6:
            return group
    return 0


def collect_bugreport_mappings(folder_path: str, extracted: bool = False) -> Dict[str, Dict[int, str]]:
    """
    Scan folder và thu thập PID mapping từ tất cả các Bugreport.
    
    Args:
        folder_path: Đường dẫn folder chứa .zip hoặc folder đã giải nén
        extracted: True nếu các bugreport đã được giải nén thành folder
    
    Returns:
        Dict mapping {bugreport_path: {PID: process_name}}
        Trong đó bugreport_path là đường dẫn đến file .zip hoặc folder
    """
    mappings: Dict[str, Dict[int, str]] = {}
    folder = Path(folder_path)
    
    if not folder.exists():
        return mappings
    
    if extracted:
        # Tìm các folder có tên chứa "Bugreport"
        for item in folder.iterdir():
            if item.is_dir() and 'bugreport' in item.name.lower():
                content = find_dumpstate_content(str(item), extracted=True)
                if content:
                    pid_map = parse_pid_mapping(content)
                    if pid_map:
                        mappings[str(item)] = pid_map
    else:
        # Tìm các file .zip có tên chứa "Bugreport"
        for zip_file in folder.glob('*Bugreport*.zip'):
            content = find_dumpstate_content(str(zip_file), extracted=False)
            if content:
                pid_map = parse_pid_mapping(content)
                if pid_map:
                    mappings[str(zip_file)] = pid_map
    
    return mappings


def get_bugreport_for_log(log_filename: str, bugreport_mappings: Dict[str, Dict[int, str]], 
                           log_files: List[str]) -> Optional[Dict[int, str]]:
    """
    Xác định Bugreport mapping tương ứng cho một file .log dựa trên thứ tự timestamp.
    
    Logic: 
    - Các file được sắp xếp theo timestamp trong tên
    - Bugreport xuất hiện SAU nhóm các file .log
    - Tìm Bugreport gần nhất (theo thứ tự) sau file log này
    
    Args:
        log_filename: Tên file .log cần tìm mapping
        bugreport_mappings: Dict {bugreport_path: {pid: name}} từ collect_bugreport_mappings()
        log_files: Danh sách tất cả files trong folder (đã sort theo tên)
    
    Returns:
        Dict {PID: process_name} hoặc None nếu không tìm thấy
    """
    if not bugreport_mappings or not log_files:
        return None
    
    # Tìm vị trí của file log hiện tại
    try:
        log_idx = -1
        for i, f in enumerate(log_files):
            if Path(f).name == Path(log_filename).name or f == log_filename:
                log_idx = i
                break
        
        if log_idx == -1:
            return None
        
        # Tìm bugreport gần nhất SAU file log này
        # Sort bugreport paths để tìm đúng thứ tự
        sorted_bugreports = sorted(bugreport_mappings.keys())
        
        for br_path in sorted_bugreports:
            br_name = Path(br_path).name
            # Tìm vị trí của bugreport trong list files
            for i, f in enumerate(log_files):
                if Path(f).name == br_name or 'bugreport' in Path(f).name.lower():
                    if i > log_idx:
                        # Tìm thấy bugreport sau log file
                        return bugreport_mappings[br_path]
        
        # Fallback: Dựa vào app group
        # Xác định app name từ log filename
        log_name = Path(log_filename).stem.lower()
        app_group = 0
        for group_num, app_list in APP_GROUPS.items():
            for app_pattern in app_list:
                if app_pattern in log_name:
                    app_group = group_num
                    break
            if app_group > 0:
                break
        
        if app_group > 0:
            # Tìm bugreport có cùng group
            for br_path, pid_map in bugreport_mappings.items():
                br_group = get_bugreport_group_from_name(Path(br_path).name)
                if br_group == app_group:
                    return pid_map
        
        # Nếu vẫn không tìm thấy, trả về mapping đầu tiên có sẵn
        if sorted_bugreports:
            return bugreport_mappings[sorted_bugreports[0]]
        
    except Exception as e:
        print(f"[Warning] Error finding bugreport for {log_filename}: {e}")
    
    return None


# ---------------------------------------------------------------------------
# Test function
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Test với sample data
    sample_content = """
Total PSS by process:
    314,911K: com.android.systemui (pid 2009)                             (   26,367K in swap)
    276,444K: system (pid 1335)                                           (   23,311K in swap)
    219,752K: com.sec.android.app.launcher (pid 2806 / activities)        (   17,672K in swap)
    182,059K: surfaceflinger (pid 1006)                                   (   36,180K in swap)
     73,464K: com.samsung.android.honeyboard (pid 4350)                   (    6,980K in swap)

Total PSS by OOM adjustment:
    649,176K: Native                                                      (  261,292K in swap)
    """
    
    result = parse_pid_mapping(sample_content)
    print("Parsed PID Mapping:")
    for pid, name in result.items():
        print(f"  PID {pid} -> {name}")
    
    # Test get_app_group
    test_apps = ['camera', 'hello', 'helloworld', 'calllog', 'myfiles', 'settings']
    print("\nApp Group Mapping:")
    for app in test_apps:
        print(f"  {app} -> Group {get_app_group(app)}")
