from execution.config import *
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


# write_value_or_empty and get_filtered_metric_rows moved to excel_sheet.py

def get_filtered_metric_rows_old_placeholder():
    pass

def _get_filtered_metric_rows(launch_type: str, app_name: str, has_cold: bool, has_warm: bool) -> List[Tuple[str, str]]:
    """
    Trả về danh sách các hàng metric cần hiển thị.
    - Kết hợp logic lọc Cold/Warm.
    - Kết hợp logic riêng cho Camera app.
    """
    prefix = "1st" if launch_type == "entry" else "2nd"
    if prefix == "1st":
        launch_type = "Enter Execution"
    elif prefix == "2nd":
        launch_type = "Enter Execution"
    else:
        launch_type = "Enter Execution"

    # Capitalize app name first letter
    app_display = app_name.capitalize()
    execution_label = f"{prefix} {launch_type} ({app_display})"
    
    # Kiểm tra xem đây có phải là Camera không (dựa trên tên app)
    is_camera = "camera" in app_name.lower()
    
    # 1. Base Metrics (Luôn hiển thị)
    rows = [
        (execution_label, "App Execution Time"),
        # Lưu ý: Đã bỏ hàng "Launch Type" theo yêu cầu
        ("", ""),
    ]

    # 2. Cold Only Block (Chỉ hiện nếu có ít nhất 1 cycle Cold)
    if has_cold:
        rows.extend([
            ("Touch Down ~ Start Proc", "Touch Down ~ Start Proc"),
            ("Start Proc", "Start Proc"),
            ("    ~", "Start Proc ~ ActivityThreadMain"),
            ("ActivityThreadMain", "Activity Thread Main"),
            ("    ~", "ActivityThreadMain ~ bindApplication"),
            ("BindApplication", "Bind Application"),
            ("    ~", "bindApplication ~ activityStart"),
        ])

    # 3. Warm Only Block (Chỉ hiện nếu có ít nhất 1 cycle Warm)
    if has_warm:
        rows.extend([
            ("Touch Duration", "Touch Duration"),
            ("Touch Up ~ ActivityStart", "Touch Up ~ Activity Start"),
        ])

    # 4. Activity Start (Luôn có)
    rows.append(("ActivityStart", "Activity Start"))
    
    # 5. Middle Block: Tách biệt logic cho Camera và App thường
    if is_camera:
        # === LOGIC RIÊNG CHO CAMERA ===
        rows.extend([
            ("onCreate", "onCreate"),
            ("OpenCameraRequest", "OpenCameraRequest"),
            ("    ~", "activityStart ~ activityResume"),
            ("ActivityResume", "Activity Resume"),
            ("onResume", "onResume"),
            ("    ~", "ActivityResume ~ Choreographer"),
            ("Choreographer", "Choreographer"),
            ("    StartPreviewRequest", "StartPreviewRequest"),
            ("    ~", "Choreographer ~ ActivityIdle"),
            ("ActivityIdle", "ActivityIdle"),
            ("    ~ Animating end", "ActivityIdle ~ Animating end"),
        ])
    else:
        # === LOGIC CHO APP THƯỜNG ===
        rows.extend([
            ("    ~", "activityStart ~ activityResume"),
            ("ActivityResume", "Activity Resume"),
            ("    ~", "ActivityResume ~ Choreographer"),
            ("Choreographer", "Choreographer"),
            ("    ~", "Choreographer ~ ActivityIdle"),
            ("ActivityIdle", "ActivityIdle"),
            ("    ~ Animating end", "ActivityIdle ~ Animating end"),
        ])
    
    # 6. State Metrics (Luôn có ở cuối)
    rows.extend([
        ("", ""),
        ("Running", "Running"),
        ("Runnable", "Runnable"),
        ("Uninterruptible Sleep", "Uninterruptible Sleep"),
        ("Sleeping", "Sleeping"),
    ])
    
    return rows

