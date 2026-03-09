#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORRECTED JSON Export Section - Replace the entire JSON export section in execution_sql.py
From line "def extract_device_code" onwards, replace with this content.
"""

def extract_device_code(header_title):
    """
    Extract device code từ header_title
    Ví dụ: 
    - A166B-YLJ-4GB-BOS-TEST_251226 -> YLJ
    - A166B_YLJ_4GB_BOS_TEST_251226 -> YLJ
    """
    normalized = header_title.replace('_', '-')
    parts = normalized.split('-')
    
    if len(parts) >= 2:
        return parts[1]
    
    return ""


# ---------------------------------------------------------------------------
# Helper Functions for JSON Export
# ---------------------------------------------------------------------------

def _export_to_single_file(
    dut_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ref_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    output_folder: str,
    dut_device_code: str,
    ref_device_code: str,
    dut_folder_path: str = "",
    ref_folder_path: str = ""
) -> None:
    """
    Xuất metrics ra 2 file JSON duy nhất.
    - execution_dut.json: Chứa tất cả apps với metrics DUT
    - execution_ref.json: Chứa tất cả apps với metrics REF
    Mỗi app CHỈ CÁC data của file đó (execution_dut.json chỉ có dut data, execution_ref.json chỉ có ref data)
    """
    timestamp = datetime.datetime.now().isoformat()
    
    all_apps = sorted(set(dut_results.keys()) | set(ref_results.keys()))
    
    print(f"\n Exporting to single JSON files...")
    
    dut_combined_data = {
        "device_code": dut_device_code,
        "timestamp": timestamp,
        "type": "DUT",
        "apps": {}
    }
    
    ref_combined_data = {
        "device_code": ref_device_code,
        "timestamp": timestamp,
        "type": "REF",
        "apps": {}
    }
    
    for app_name in all_apps:
        dut_entry_cycles = dut_results.get(app_name, {}).get("entry", [])
        ref_entry_cycles = ref_results.get(app_name, {}).get("entry", [])
        
        # execution_dut.json: CHỈ CÓ DUT DATA
        dut_metrics = {}
        if dut_entry_cycles:
            dut_metrics = calculate_metrics_for_app(
                dut_entry_cycles, app_name, "entry", dut_folder_path,
                compare_cycles=ref_entry_cycles, is_dut=True
            )
        dut_combined_data["apps"][app_name] = dut_metrics
        
        # execution_ref.json: CHỈ CÓ REF DATA
        ref_metrics = {}
        if ref_entry_cycles:
            ref_metrics = calculate_metrics_for_app(
                ref_entry_cycles, app_name, "entry", ref_folder_path,
                compare_cycles=dut_entry_cycles, is_dut=False
            )
        ref_combined_data["apps"][app_name] = ref_metrics
    
    dut_output_path = os.path.join(output_folder, "execution_dut.json")
    with open(dut_output_path, 'w', encoding='utf-8') as f:
        json.dump(dut_combined_data, f, indent=2, ensure_ascii=False)
    print(f"  Created: execution_dut.json")
    
    ref_output_path = os.path.join(output_folder, "execution_ref.json")
    with open(ref_output_path, 'w', encoding='utf-8') as f:
        json.dump(ref_combined_data, f, indent=2, ensure_ascii=False)
    print(f"  Created: execution_ref.json")


def _export_to_per_app_files(
    dut_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ref_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    output_folder: str,
    dut_device_code: str,
    ref_device_code: str,
    dut_folder_path: str = "",
    ref_folder_path: str = ""
) -> None:
    """
    [DEPRECATED] Xuất metrics ra nhiều file JSON theo từng app.
    """
    timestamp = datetime.datetime.now().isoformat()
    
    output_dir = os.path.join(output_folder, "Output")
    os.makedirs(output_dir, exist_ok=True)
    
    all_apps = sorted(set(dut_results.keys()) | set(ref_results.keys()))
    
    print(f"\n Exporting per-app JSON files (DEPRECATED)...")
    
    for app_name in all_apps:
        dut_entry_cycles = dut_results.get(app_name, {}).get("entry", [])
        ref_entry_cycles = ref_results.get(app_name, {}).get("entry", [])
        
        if dut_entry_cycles:
            dut_metrics = calculate_metrics_for_app(
                dut_entry_cycles, app_name, "entry", dut_folder_path,
                compare_cycles=ref_entry_cycles, is_dut=True
            )
            if dut_metrics:
                dut_json = {
                    "device_code": dut_device_code,
                    "timestamp": timestamp,
                    "type": "DUT",
                    "app": app_name,
                    "entry": dut_metrics
                }
                
                dut_file_path = os.path.join(output_dir, f"{app_name}_dut.json")
                with open(dut_file_path, 'w', encoding='utf-8') as f:
                    json.dump(dut_json, f, indent=2, ensure_ascii=False)
                print(f"  Created: {app_name}_dut.json")
        
        if ref_entry_cycles:
            ref_metrics = calculate_metrics_for_app(
                ref_entry_cycles, app_name, "entry", ref_folder_path,
                compare_cycles=dut_entry_cycles, is_dut=False
            )
            if ref_metrics:
                ref_json = {
                    "device_code": ref_device_code,
                    "timestamp": timestamp,
                    "type": "REF",
                    "app": app_name,
                    "entry": ref_metrics
                }
                
                ref_file_path = os.path.join(output_dir, f"{app_name}_ref.json")
                with open(ref_file_path, 'w', encoding='utf-8') as f:
                    json.dump(ref_json, f, indent=2, ensure_ascii=False)
                print(f"  Created: {app_name}_ref.json")


# ---------------------------------------------------------------------------
# JSON Export
# ---------------------------------------------------------------------------

def export_avg_to_json(
    dut_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ref_results: Dict[str, Dict[str, List[Dict[str, Any]]]>,
    output_folder: str,
    dut_device_code: str,
    ref_device_code: str,
    dut_folder_path: str = "",
    ref_folder_path: str = "",
    single_file: bool = False
) -> None:
    """
    Xuất metrics ra file JSON.
    
    [UPDATED v3]
    - single_file=False: Tách thành nhiều file JSON theo từng app (DEPRECATED)
    - single_file=True: Tạo 2 file duy nhất chứa tất cả apps (execution_dut.json, execution_ref.json)
    """
    if single_file:
        _export_to_single_file(dut_results, ref_results, output_folder, 
                             dut_device_code, ref_device_code, 
                             dut_folder_path, ref_folder_path)
    else:
        _export_to_per_app_files(dut_results, ref_results, output_folder,
                                  dut_device_code, ref_device_code,
                                  dut_folder_path, ref_folder_path)


# ---------------------------------------------------------------------------
# calculate_metrics_for_app function - Keep existing implementation
# ---------------------------------------------------------------------------
# This function is already defined in export_avg_to_json, move it to module level