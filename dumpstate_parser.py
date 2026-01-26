#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dumpstate_parser.py

Module để parse file dumpstate.txt từ Bugreport và map PID -> Process Name.
[UPDATED] 
- Fix lỗi Long Path trên Server (Đọc trực tiếp từ Zip, không giải nén).
- Cải tiến logic Mapping: Group + Timestamp Matching.
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
    """
    app_lower = app_name.lower()
    for group_num, app_list in APP_GROUPS.items():
        for app_pattern in app_list:
            if app_pattern in app_lower:
                return group_num
    return 0


def parse_pid_mapping(dumpstate_content: str) -> Dict[int, str]:
    """
    Parse phần 'Total PSS by process:' từ nội dung dumpstate.txt.
    Trích xuất mapping {PID: process_name}.
    """
    pid_mapping: Dict[int, str] = {}
    
    start_marker = "Total PSS by process:"
    end_marker = "Total PSS by OOM adjustment:"
    
    start_idx = dumpstate_content.find(start_marker)
    if start_idx == -1:
        return pid_mapping
    
    end_idx = dumpstate_content.find(end_marker, start_idx)
    if end_idx == -1:
        section = dumpstate_content[start_idx:start_idx + 50000]
    else:
        section = dumpstate_content[start_idx:end_idx]
    
    # Format: "    314,911K: com.android.systemui (pid 2009)"
    pattern = r'^\s*([\d,]+)K:\s+(.+?)\s+\(pid\s+(\d+)'
    
    for line in section.split('\n'):
        match = re.match(pattern, line)
        if match:
            process_name = match.group(2).strip()
            pid = int(match.group(3))
            pid_mapping[pid] = process_name
            
    return pid_mapping


def find_largest_txt_in_folder(folder_path: str) -> Optional[str]:
    """
    Tìm file .txt có dung lượng lớn nhất trong folder (Dùng cho mode Extracted).
    """
    largest_file = None
    largest_size = 0
    
    folder = Path(folder_path)
    if not folder.exists():
        return None
    
    for txt_file in folder.glob('*.txt'):
        try:
            size = txt_file.stat().st_size
            if size > largest_size:
                largest_size = size
                largest_file = txt_file
        except:
            continue
    
    if largest_file:
        try:
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
    
    [CRITICAL FIX] Fix lỗi Long Path trên Server:
    - KHÔNG giải nén (extractall) ra ổ cứng.
    - Đọc trực tiếp (stream) từ file Zip trong RAM.
    """
    path_obj = Path(path)
    
    if extracted:
        # Case 1: Đã giải nén sẵn -> tìm trong folder
        if path_obj.is_dir():
            return find_largest_txt_in_folder(str(path_obj))
        return None
    else:
        # Case 2: File .zip -> Đọc từ Memory
        if not path_obj.suffix.lower() == '.zip':
            return None
        
        if not path_obj.exists():
            return None
        
        try:
            # Mở file zip mà KHÔNG giải nén ra disk
            with zipfile.ZipFile(str(path_obj), 'r') as zip_ref:
                largest_zinfo = None
                max_size = 0
                
                # Duyệt danh sách file trong zip
                for zinfo in zip_ref.infolist():
                    # Bỏ qua folder và file không phải .txt
                    if zinfo.is_dir() or not zinfo.filename.lower().endswith('.txt'):
                        continue
                    
                    # Tìm file .txt lớn nhất (chính là bugreport)
                    if zinfo.file_size > max_size:
                        max_size = zinfo.file_size
                        largest_zinfo = zinfo
                
                # Đọc nội dung file tìm được
                if largest_zinfo:
                    with zip_ref.open(largest_zinfo) as f:
                        content_bytes = f.read()
                        try:
                            return content_bytes.decode('utf-8')
                        except UnicodeDecodeError:
                            return content_bytes.decode('latin-1')
            
            return None
            
        except Exception as e:
            print(f"[Error] Cannot read zip {path}: {e}")
            return None


def get_bugreport_group_from_name(filename: str) -> int:
    """Xác định group number từ tên file bugreport (dựa vào 'Xpart' hoặc 'partX')."""
    # Match cả "2part" và "part2"
    match = re.search(r'(\d)part', filename.lower())
    if not match:
        match = re.search(r'part(\d)', filename.lower())
    if match:
        group = int(match.group(1))
        if 1 <= group <= 6:
            return group
    return 0


def get_app_name_from_log(filename: str) -> str:
    """Extract app name từ log filename (phần cuối trước .log)."""
    name = Path(filename).stem.lower()
    # Format: A266_260108_164459_camera -> lấy phần cuối
    parts = name.split('_')
    if parts:
        return parts[-1]
    return ""


def build_trace_bugreport_mapping(folder_path: str, extracted: bool = False) -> Dict[str, Dict[int, str]]:
    """
    Build mapping {trace_path: pid_mapping} dựa trên sorted filename approach.
    
    Logic:
    1. List tất cả .log files và bugreport folders/zips
    2. Sort theo tên (chronological order)
    3. Iterate và assign bugreport cho traces dựa trên group
    
    Returns:
        Dict[trace_path, {pid: process_name}] - mapping cho mỗi trace file
    """
    folder = Path(folder_path)
    if not folder.exists():
        return {}
    
    # 1. Thu thập tất cả items (logs + bugreports)
    items = []
    
    for item in folder.iterdir():
        name_lower = item.name.lower()
        
        if item.is_file() and name_lower.endswith('.log'):
            # Trace file
            app_name = get_app_name_from_log(item.name)
            app_group = get_app_group(app_name)
            items.append({
                'path': str(item),
                'name': item.name,
                'type': 'trace',
                'group': app_group,
                'app': app_name
            })
            
        elif 'bugreport' in name_lower:
            # Bugreport - có thể là folder (extracted) hoặc .zip
            is_valid = False
            if extracted and item.is_dir():
                is_valid = True
            elif not extracted and item.is_file() and name_lower.endswith('.zip'):
                is_valid = True
            
            if is_valid:
                br_group = get_bugreport_group_from_name(item.name)
                items.append({
                    'path': str(item),
                    'name': item.name,
                    'type': 'bugreport',
                    'group': br_group
                })
    
    # 2. Sort theo tên (chronological order based on timestamp in name)
    items.sort(key=lambda x: x['name'])
    
    # 3. Iterate và assign
    # pending_traces[group] = list of trace paths waiting for bugreport
    pending_traces: Dict[int, List[str]] = {i: [] for i in range(1, 7)}
    
    # result[trace_path] = pid_mapping
    result: Dict[str, Dict[int, str]] = {}
    
    # Track max group seen to detect cycle wrap-around
    max_group_seen = 0
    
    for item in items:
        if item['type'] == 'trace':
            group = item['group']
            if group == 0:
                continue
            
            # Detect cycle wrap-around: group went back to smaller number
            if group < max_group_seen:
                # New cycle! Mark all remaining pending as no mapping
                for g in range(1, 7):
                    for trace_path in pending_traces[g]:
                        result[trace_path] = {}  # Empty dict = no mapping
                    pending_traces[g] = []
                max_group_seen = 0  # Reset for new cycle
            
            # Add to pending for this group
            pending_traces[group].append(item['path'])
            max_group_seen = max(max_group_seen, group)
            
        elif item['type'] == 'bugreport':
            group = item['group']
            if group == 0:
                continue
            
            # Parse PID mapping từ bugreport
            content = find_dumpstate_content(item['path'], extracted=extracted)
            pid_mapping = {}
            if content:
                pid_mapping = parse_pid_mapping(content)
            
            # Assign mapping cho tất cả pending traces của group này
            for trace_path in pending_traces[group]:
                result[trace_path] = pid_mapping
            
            # Clear pending for this group
            pending_traces[group] = []
            max_group_seen = max(max_group_seen, group)
    
    # 4. Traces còn lại trong pending = no bugreport
    for group in range(1, 7):
        for trace_path in pending_traces[group]:
            result[trace_path] = {}  # Empty dict = no mapping
    
    return result


def collect_bugreport_mappings(folder_path: str, extracted: bool = False) -> Dict[str, Dict[int, str]]:
    """Scan folder và thu thập PID mapping."""
    mappings: Dict[str, Dict[int, str]] = {}
    folder = Path(folder_path)
    
    if not folder.exists():
        return mappings
    
    if extracted:
        for item in folder.iterdir():
            if item.is_dir() and 'bugreport' in item.name.lower():
                content = find_dumpstate_content(str(item), extracted=True)
                if content:
                    pid_map = parse_pid_mapping(content)
                    if pid_map:
                        mappings[str(item)] = pid_map
    else:
        for zip_file in folder.glob('*Bugreport*.zip'):
            content = find_dumpstate_content(str(zip_file), extracted=False)
            if content:
                pid_map = parse_pid_mapping(content)
                if pid_map:
                    mappings[str(zip_file)] = pid_map
    
    return mappings


def _extract_timestamp_val(filename: str) -> int:
    """Helper: Trích xuất timestamp từ tên file để so sánh."""
    matches = re.findall(r'_(\d{6})', filename)
    if len(matches) >= 2:
        try:
            return int(matches[-2] + matches[-1])
        except:
            pass
    if matches:
        return int(matches[-1])
    return 0


def get_bugreport_for_log(log_filename: str, bugreport_mappings: Dict[str, Dict[int, str]], 
                           occurrence: int = 1) -> Optional[Dict[int, str]]:
    """
    Xác định Bugreport mapping dựa trên APP GROUP và THỨ TỰ CYCLE.
    [UPDATED LOGIC]
    """
    if not bugreport_mappings:
        return None
    
    log_name = Path(log_filename).name
    
    # 1. Xác định App Group
    log_name_lower = log_name.lower()
    app_group = 0
    for group_num, app_list in APP_GROUPS.items():
        for app_pattern in app_list:
            if app_pattern in log_name_lower:
                app_group = group_num
                break
        if app_group > 0:
            break
            
    if app_group == 0:
        print(f"  [Mapping] Unknown group for {log_name}, skipping...")
        return None

    # 2. Lọc Bugreport thuộc Group này
    candidates = []
    for br_path in bugreport_mappings.keys():
        br_name = Path(br_path).name
        if get_bugreport_group_from_name(br_name) == app_group:
            candidates.append(br_path)
    
    if not candidates:
        print(f"  [Mapping] No bugreports found for Group {app_group} (App: {log_name})")
        return None
        
    # 3. Sắp xếp candidates theo tên (tức là theo thời gian)
    candidates.sort()
    
    # 4. Tính toán Cycle Index từ occurrence
    # Log 1,2 -> Cycle 1 (Index 0); Log 3,4 -> Cycle 2 (Index 1)
    cycle_index = (occurrence - 1) // 2
    
    # 5. Chọn Bugreport
    selected_br = None
    if cycle_index < len(candidates):
        selected_br = candidates[cycle_index]
        # print(f"  [Mapping] {log_name} (Occ {occurrence}) -> {Path(selected_br).name}")
    else:
        # Fallback: Lấy cái cuối cùng
        selected_br = candidates[-1]
        print(f"  [Mapping Warning] Cycle {cycle_index+1} out of range. Using last: {Path(selected_br).name}")

    if selected_br:
        return bugreport_mappings[selected_br]
        
    return None