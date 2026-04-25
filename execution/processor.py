from execution.config import *

def collect_trace_files(folder_path: str) -> List[str]:
    """
    Collect file .log trong folder, đã sort theo tên (A-Z).
    
    Returns:
        List[str]: All file .log
    """
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Folder không tồn tại: {folder_path}")
    
    log_files = sorted([str(f) for f in folder.glob("*.log")])
    return log_files

def group_traces_by_app(trace_files: List[str], target_apps: List[str] = None) -> Dict[str, List[Tuple[str, int]]]:
    if target_apps is None:
        target_apps = TARGET_APPS
        
    app_groups = defaultdict(list)
    app_occurrence_count = defaultdict(int)
    
    print(f"Target Apps Filter: {target_apps}")
    
    for file_path in trace_files:
        filename = Path(file_path).stem
        parts = filename.split('_')
        
        if len(parts) >= 2:
            raw_app_name = parts[-1]
            app_name = raw_app_name.lower()
            
            # [FIX STEP 1] Normalize app name (fix typos like "calender" → "calendar")
            if app_name in APP_NAME_NORMALIZATION:
                original_name = app_name
                app_name = APP_NAME_NORMALIZATION[app_name]
                print(f"  [NORMALIZED] '{original_name}' → '{app_name}'")
            
            # NEW: Check if app_name contains any target keyword
            matched_keyword = None
            for keyword in target_apps:
                if keyword in app_name:
                    matched_keyword = keyword
                    break
            
            if matched_keyword is None:
                continue
                
            # Use the matched keyword as the standardized app name
            standardized_name = matched_keyword
        else:
            continue
            
        app_occurrence_count[standardized_name] += 1
        occurrence = app_occurrence_count[standardized_name]
        app_groups[standardized_name].append((file_path, occurrence))
        
    return dict(app_groups)


# ---------------------------------------------------------------------------
# Batch Processing Logic với Multiprocessing
# ---------------------------------------------------------------------------

def _process_single_trace_worker(args):
    # Unpack thêm folder_path (cần truyền vào từ process_all_traces)
    file_path, occurrence, app_name, pid_mapping, mapping_info, folder_path = args 
    filename = Path(file_path).stem
    config = TraceProcessorConfig(bin_path=TRACE_PROCESSOR_BIN)
    
    try:
        with TraceProcessor(trace=convert_trace(file_path), config=config) as tp:
            metrics = analyze_trace(tp, file_path, pid_mapping)
            category = 'entry' if occurrence % 2 == 1 else 'reentry'
            
            # ========================================================
            # [TỐI ƯU MỚI] PARSE DUMPSTATE & MEMORY NGAY TẠI WORKER
            # ========================================================
            cycle_idx = (occurrence - 1) // 2
            extend_data = {}
            
            # 1. Đọc Memory Data
            if folder_path:
                mem_data = get_memory_data_for_cycle(folder_path, app_name, cycle_idx)
                if mem_data:
                    extend_data['MemFree'] = mem_data.get('MemFree', 0)
                    extend_data['MemAvailable'] = mem_data.get('MemAvailable', 0)
            
            # 2. Đọc Dumpstate (PSS, Pageboost, Uptime, Start/Kill, Crash, Compiler)
            bugreport_path = mapping_info.get('bugreport_path', '') if mapping_info else ''
            if bugreport_path:
                dumpstate_content = find_dumpstate_content(bugreport_path)
                if dumpstate_content:
                    extend_data['App_PSS'] = parse_pss_for_app(dumpstate_content, app_name)
                    extend_data['Pageboostd'] = parse_pageboostd_for_app(dumpstate_content, app_name)
                    extend_data['Uptime'] = parse_uptime(dumpstate_content)
                    extend_data['Start_Reason'] = parse_start_reasons(dumpstate_content, app_name)
                    extend_data['Kill_Reason'] = parse_kill_reasons(dumpstate_content, app_name)
                    extend_data['Crash_Count'] = count_crashes(dumpstate_content)
                    extend_data['Compiler'] = parse_compiler_type(dumpstate_content, app_name)
            
            # Gắn data đã parse sẵn vào metrics để lưu Cache
            metrics['Precomputed_Extend_Data'] = extend_data
            # ========================================================
            
            return (app_name, occurrence, category, metrics, filename)
    except Exception as e:
        print(f"    [ERROR] {Path(file_path).name}: {e}")
        return (app_name, occurrence, 'entry' if occurrence % 2 == 1 else 'reentry', None, filename)


def process_single_trace(args: Tuple[str, int, str], pid_mapping: Dict[int, str] = None) -> Tuple[str, int, str, Optional[Dict[str, Any]], str]:
    """
    Xử lý một trace file duy nhất.
    
    Args:
        args: (file_path, occurrence, app_name)
        pid_mapping: Optional dict {PID: process_name} from dumpstate
    
    Returns:
        (app_name, occurrence, category, metrics, filename) hoặc (app_name, occurrence, category, None, filename) nếu lỗi
    """
    file_path, occurrence, app_name = args
    filename = Path(file_path).stem
    config = TraceProcessorConfig(bin_path=TRACE_PROCESSOR_BIN)
    
    try:
        with TraceProcessor(trace=convert_trace(file_path), config=config) as tp:
            metrics = analyze_trace(tp, file_path, pid_mapping)
            category = 'entry' if occurrence % 2 == 1 else 'reentry'
            return (app_name, occurrence, category, metrics, filename)
    except Exception as e:
        print(f"    [ERROR] {Path(file_path).name}: {e}")
        return (app_name, occurrence, 'entry' if occurrence % 2 == 1 else 'reentry', None, filename)



# [File: execution_sql.py] -> function process_all_traces

def process_all_traces(folder_path: str, label: str, num_workers: int = 8, 
                       target_apps: List[str] = None, extracted: bool = False) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Xử lý tất cả traces.
    [UPDATED] Fix lỗi dồn cycle khi có trace bị lỗi (giữ nguyên None trong list kết quả).
    """
    trace_files = collect_trace_files(folder_path)
    app_groups = group_traces_by_app(trace_files, target_apps)
    
    # Build mapping using sorted filename approach
    print(f"\n[{label}] Building trace-bugreport mapping (extracted={extracted})...")
    trace_mapping = build_trace_bugreport_mapping(folder_path, extracted)
    
    valid_count = sum(1 for m in trace_mapping.values() if m and m.get('bugreport_path'))
    print(f"[{label}] Mapped {valid_count}/{len(trace_mapping)} traces to bugreports")
    
    tasks = []
    for app_name, file_list in app_groups.items():
        for file_path, occurrence in file_list:
            mapping_info = trace_mapping.get(file_path, {})
            pid_mapping = mapping_info.get('pid_mapping', {}) if mapping_info else {}
            if not pid_mapping: pid_mapping = None
            
            # [CẬP NHẬT] Thêm folder_path vào cuối
            tasks.append((file_path, occurrence, app_name, pid_mapping, mapping_info, folder_path))
    
    print(f"[{label}] Processing {len(tasks)} trace files with {num_workers} workers...")
    
    # Khởi tạo list với dung lượng dư thừa để tránh index error
    results = defaultdict(lambda: {'entry': [], 'reentry': []})
    task_mapping_info = {t[0]: t[4] for t in tasks}
    
    pool = Pool(processes=num_workers)
    try:
        for i, (app_name, occurrence, category, metrics, filename) in enumerate(pool.imap(_process_single_trace_worker, tasks)):
            
            # [FIX 1] Luôn tính toán cycle index, kể cả khi metrics là None (lỗi)
            # Logic: Trace 1,2 -> Cycle 0; Trace 3,4 -> Cycle 1
            cycle_index = (occurrence - 1) // 2
            
            # Mở rộng list nếu cần thiết để đảm bảo index tồn tại
            target_list = results[app_name][category]
            while len(target_list) <= cycle_index:
                target_list.append(None)
            
            if metrics:
                # Nếu có data, bổ sung thông tin trace file
                trace_file = None
                for task in tasks:
                    if Path(task[0]).stem == filename:
                        trace_file = task[0]
                        break
                
                if trace_file:
                    metrics['trace_file'] = trace_file
                    metrics['trace_mapping'] = task_mapping_info.get(trace_file, {})
                
                print(f"  - [{i+1}/{len(tasks)}] {app_name} - {category} - cycle {cycle_index + 1} - {filename} - OK")
                results[app_name][category][cycle_index] = metrics
            else:
                # Nếu metrics None (lỗi), giữ nguyên giá trị None tại index đó
                print(f"  - [{i+1}/{len(tasks)}] {app_name} - {category} - cycle {cycle_index + 1} - {filename} - FAILED/EMPTY")
                results[app_name][category][cycle_index] = None

    finally:
        pool.close() 
        pool.join()  
    
    # [FIX 2] KHÔNG lọc bỏ None. Giữ nguyên cấu trúc [Data, None, Data] để Excel vẽ đúng cột.
    cleaned_results = {}
    for app_name, categories in results.items():
        cleaned_results[app_name] = {
            'entry': categories['entry'], # Giữ nguyên list gốc
            'reentry': categories['reentry']
        }
    
    return cleaned_results



# ---------------------------------------------------------------------------
# Excel Creation - Helper Functions
# ---------------------------------------------------------------------------

def select_common_end_ts_type(dut_metrics: Dict[str, Any], ref_metrics: Dict[str, Any]) -> Optional[str]:
    """
    Chọn end_ts type mà CẢ DUT và REF đều có.
    Ưu tiên: Chọn type có giá trị LỚN NHẤT (execution time dài nhất).
    
    Args:
        dut_metrics: Metrics từ DUT cycle
        ref_metrics: Metrics từ REF cycle
        
    Returns:
        Common end_ts type name hoặc None nếu không có common type
    """
    dut_variants = dut_metrics.get("end_ts_variants", {})
    ref_variants = ref_metrics.get("end_ts_variants", {})
    
    # Tìm các types mà CẢ HAI đều có (value > 0)
    dut_types = {k for k, v in dut_variants.items() if v and v > 0}
    ref_types = {k for k, v in ref_variants.items() if v and v > 0}
    common_types = dut_types & ref_types
    
    if not common_types:
        return None
    
    # Chọn type có giá trị LỚN NHẤT (average của DUT và REF)
    best_type = None
    best_value = 0
    
    for etype in common_types:
        avg_value = (dut_variants.get(etype, 0) + ref_variants.get(etype, 0)) / 2
        if avg_value > best_value:
            best_value = avg_value
            best_type = etype
    
    return best_type


def get_metrics_for_end_ts_type(metrics: Dict[str, Any], end_ts_type: str) -> Dict[str, Any]:
    """
    Lấy data tương ứng với end_ts_type từ metrics.
    Nếu không có data_by_end_ts, fallback về metrics root.
    
    Args:
        metrics: Full metrics dict từ analyze_trace
        end_ts_type: Type cần lấy ("activityIdle", "animating", "startPreviewRequest")
        
    Returns:
        Dict chứa data cho end_ts_type đó, hoặc metrics root nếu không có
    """
    data_by_end_ts = metrics.get("data_by_end_ts", {})
    
    if end_ts_type and end_ts_type in data_by_end_ts:
        # Merge: base metrics + data từ end_ts_type
        result = metrics.copy()
        type_data = data_by_end_ts[end_ts_type]
        
        # Override các fields phụ thuộc end_ts
        for key in ["Running", "Runnable", "Uninterruptible Sleep", "Sleeping",
                    "LoadApkAsset_Data", "CPU_Process_Data",
                    "CPU_Thread_Data", "Binder_Transaction_Data",
                    "Abnormal_Process_Data", "Background_Process_States", "App Execution Time"]:
            if key in type_data:
                result[key] = type_data[key]
                
        # [NEW LOGIC cho Block I/O & Function Block I/O] 
        # Luôn lấy từ mốc thời gian xa nhất (end_ts lớn nhất) để gom đủ data
        end_ts_variants = metrics.get("end_ts_variants", {})
        if end_ts_variants:
            furthest_type = max(end_ts_variants.keys(), key=lambda k: end_ts_variants.get(k) or 0)
            
            # 1. Xử lý cho Library Block I/O
            if furthest_type in data_by_end_ts and "Block_IO_Data" in data_by_end_ts[furthest_type]:
                result["Block_IO_Data"] = data_by_end_ts[furthest_type]["Block_IO_Data"]
            elif "Block_IO_Data" in type_data:
                result["Block_IO_Data"] = type_data["Block_IO_Data"]
                
            # 2. Xử lý cho Function Block I/O
            if furthest_type in data_by_end_ts and "Function_Block_IO_Data" in data_by_end_ts[furthest_type]:
                result["Function_Block_IO_Data"] = data_by_end_ts[furthest_type]["Function_Block_IO_Data"]
            elif "Function_Block_IO_Data" in type_data:
                result["Function_Block_IO_Data"] = type_data["Function_Block_IO_Data"]
                
        else:
            # Fallback nếu không có variants
            if "Block_IO_Data" in type_data:
                result["Block_IO_Data"] = type_data["Block_IO_Data"]
            if "Function_Block_IO_Data" in type_data:
                result["Function_Block_IO_Data"] = type_data["Function_Block_IO_Data"]
                
        return result
    
    # Fallback: return metrics as-is (backward compatible)
    return metrics


    

        




