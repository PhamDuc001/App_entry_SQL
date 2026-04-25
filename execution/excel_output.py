import os
import datetime
from typing import Dict, Any, List

import xlsxwriter

from execution.config import APP_MAPPING
from execution.excel_sheet import create_sheet

def create_excel_output(
    dut_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ref_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    output_folder: str,
    header_title: str,
    dut_device_code: str,
    ref_device_code: str,
    dut_folder_path: str = "",
    ref_folder_path: str = "",
    dut_model: str = "",
    dut_version: str = "",
    ref_version: str = ""
) -> None:
    """
    Tạo 2 file Excel: execution_entry.xlsx và execution_reentry.xlsx.
    
    Mỗi file chứa nhiều sheets theo app name.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Tạo tên file theo format mới: execution_entry_{DUT_MODEL}_DUT - {DUT_VERSION}_REF - {REF_VERSION}_{timestamp}
    if dut_model and dut_version and ref_version:
        file_prefix = f"execution_{{}}_{dut_model}_DUT-{dut_version}_REF-{ref_version}"
    else:
        file_prefix = "execution_{}"
    
    # Tạo 2 files
    for launch_type in ['entry', 'reentry']:
        output_path = os.path.join(
            output_folder,
            f"{file_prefix.format(launch_type)}_{timestamp}.xlsx"
        )
        
        wb = xlsxwriter.Workbook(output_path)
        
        # Lấy danh sách apps chỉ từ DUT (các app được chọn để chạy)
        all_apps = set(dut_results.keys())
        
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
                ref_device_code,
                dut_folder_path,
                ref_folder_path
            )
        
        wb.close()
        print(f"\n Created: {output_path}")

