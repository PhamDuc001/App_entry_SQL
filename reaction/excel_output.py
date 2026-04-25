import os
import datetime
from typing import Dict, Any, List

import xlsxwriter

from reaction.analyzer import APP_MAPPING
from shared.excel import write_value_or_empty

def create_excel_output(
    dut_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ref_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    output_folder: str,
    header_title: str,
    dut_model: str = "",
    dut_version: str = "",
    ref_version: str = ""
) -> None:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Tạo tên file theo format mới: reaction_entry_{DUT_MODEL}_DUT - {DUT_VERSION}_REF - {REF_VERSION}_{timestamp}
    if dut_model and dut_version and ref_version:
        file_prefix = f"reaction_{{}}_{dut_model}_DUT-{dut_version}_REF-{ref_version}"
    else:
        file_prefix = "reaction_{}"
    
    for launch_type in ['entry', 'reentry']:
        output_path = os.path.join(
            output_folder,
            f"{file_prefix.format(launch_type)}_{timestamp}.xlsx"
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
                ("~", "Choreographer ~ startAnimation"),
                ("startAnimation", "startAnimation"),
                ("~", "startAnimation ~ drawFrame"),
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
                        
                        write_value_or_empty(ws, row_idx, col_idx, float(val), fmt_val, empty_if_blank=True)
                        dut_values.append(float(val))
                    else:
                        ws.write(row_idx, col_idx, "", fmt_val)
                    col_idx += 1
                
                # DUT Avg
                valid_dut = [v for v in dut_values if v > 0]
                if valid_dut:
                    dut_avg = sum(valid_dut) / len(valid_dut)
                else:
                    dut_avg = 0.0
                write_value_or_empty(ws, row_idx, col_idx, dut_avg, fmt_val, empty_if_blank=True)
                col_idx += 1
                
                # --- REF DATA ---
                ref_values = []
                for i in range(max_cycles):
                    if i < len(ref_cycles):
                        val = ref_cycles[i].get(metric_key, 0.0)
                        if val == "": val = 0.0
                        
                        write_value_or_empty(ws, row_idx, col_idx, float(val), fmt_val, empty_if_blank=True)
                        ref_values.append(float(val))
                    else:
                        ws.write(row_idx, col_idx, "", fmt_val)
                    col_idx += 1
                
                # REF Avg
                valid_ref = [v for v in ref_values if v > 0]
                if valid_ref:
                    ref_avg = sum(valid_ref) / len(valid_ref)
                else:
                    ref_avg = 0.0
                write_value_or_empty(ws, row_idx, col_idx, ref_avg, fmt_val, empty_if_blank=True)
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
                    
                    write_value_or_empty(ws, row_idx, col_idx, diff_val, fmt_diff, empty_if_blank=True)
                else:
                    ws.write(row_idx, col_idx, "", fmt_diff_normal)
                
                row_idx += 1
                
        wb.close()
        print(f"\n Created: {output_path}")



