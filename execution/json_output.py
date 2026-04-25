from execution.config import *
from execution.processor import select_common_end_ts_type, get_metrics_for_end_ts_type

def extract_version_and_model(file_path: str) -> Tuple[str, str]:
    """
    Extract version và model từ tên file trace đầu tiên
    Ví dụ: A166B-YLJ-4GB-BOS-TEST_ZC5_251226.log
    -> model: A166B, version: ZC5
    """
    if not file_path:
        return "", ""
    
    filename = Path(file_path).stem
    parts = filename.split('_')
    
    if len(parts) >= 2:
        # Model là phần đầu tiên trước dấu '-'
        model_part = parts[0]
        model = model_part.split('-')[0] if '-' in model_part else model_part
        
        # Version là phần thứ hai từ cuối lên (phần trước timestamp)
        version = parts[-2] if len(parts) >= 3 else parts[-1]
        # Nếu version có chứa '-', lấy phần trước dấu '-'
        version = version.split('-')[0] if '-' in version else version
        return model, version
    
    return "", ""

def extract_device_code(header_title):
    """
    Extract device code từ header_title
    Ví dụ: 
    - A166B-YLJ-4GB-BOS-TEST_251226 -> YLJ
    - A166B_YLJ_4GB_BOS_TEST_251226 -> YLJ
    """
    # Chuẩn hóa: replace tất cả '_' bằng '-'
    normalized = header_title.replace('_', '-')
    parts = normalized.split('-')
    
    if len(parts) >= 2:
        return parts[1]
    
    return ""


# ---------------------------------------------------------------------------
# JSON Export
# ---------------------------------------------------------------------------

def export_avg_to_json(
    dut_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ref_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    output_folder: str,
    dut_device_code: str,
    ref_device_code: str,
    dut_folder_path: str = "",
    ref_folder_path: str = "",
    dut_version: str = "",
    ref_version: str = "",
    dut_model: str = "",    
    ref_model: str = ""     
) -> None:
    """
    Xuất metrics ra file JSON.
    [UPDATED v2]
    - Tách thành nhiều file JSON theo từng app (app_name_dut.json, app_name_ref.json)
    - Chỉ lấy entry data, bỏ reentry
    """
    
    def calculate_metrics_for_app(cycles: List[Dict[str, Any]], app_name: str, launch_type: str, folder_path: str = "", compare_cycles: List[Dict[str, Any]] = None, is_dut: bool = True) -> Dict[str, Any]:
        """Tính toán metrics cho một app/launch_type"""
        if not cycles: return {}
        
        # =========================================================
        # [FIX QUAN TRỌNG] Đồng bộ Common End TS Type với Excel
        # Đảm bảo DUT và REF có cùng Time Window (VD: Cùng tính tới ActivityIdle)
        # =========================================================
        adjusted_cycles = []
        adjusted_compare = []
        max_len = max(len(cycles), len(compare_cycles) if compare_cycles else 0)
        
        for i in range(max_len):
            main_c = cycles[i] if i < len(cycles) else None
            comp_c = compare_cycles[i] if compare_cycles and i < len(compare_cycles) else None
            
            if main_c and comp_c:
                # Phân biệt DUT/REF để lấy type chuẩn xác nhất
                dut_c = main_c if is_dut else comp_c
                ref_c = comp_c if is_dut else main_c
                
                common_type = select_common_end_ts_type(dut_c, ref_c)
                if common_type:
                    main_c = get_metrics_for_end_ts_type(main_c, common_type)
                    comp_c = get_metrics_for_end_ts_type(comp_c, common_type)
            
            if i < len(cycles):
                adjusted_cycles.append(main_c)
            if compare_cycles is not None and i < len(compare_cycles):
                adjusted_compare.append(comp_c)
                
        # Ghi đè lại cycles bằng data đã được chuẩn hóa Time Window
        cycles = adjusted_cycles
        if compare_cycles is not None:
            compare_cycles = adjusted_compare
        # =========================================================

        # Lấy danh sách các cycle hợp lệ (không bị None)
        valid_cycles_with_idx = [(i, c) for i, c in enumerate(cycles) if c is not None]
        if not valid_cycles_with_idx: return {}
        
        valid_cycles = [c for _, c in valid_cycles_with_idx]
        result = {}

        # ========================
        # 0. STATE (Per Cycle) - [FIXED] Read actual Launch Type from trace analysis
        # Same logic as Excel: each cycle can independently be Cold or Warm
        # ========================
        result["State"] = [c.get("Launch Type", "Cold" if launch_type == "entry" else "Warm") for c in valid_cycles]
        
        # ========================
        # 1. SEQUENCE METRICS (AVG)
        # ========================
        sequence_metrics = [
            "App Execution Time", "Touch Down ~ Start Proc", "Start Proc",
            "Start Proc ~ ActivityThreadMain", "Activity Thread Main",
            "ActivityThreadMain ~ bindApplication", "Bind Application",
            "bindApplication ~ activityStart", "Touch Duration", "Touch Up ~ Activity Start",
            "Activity Start", "activityStart ~ activityResume", "Activity Resume",
            "ActivityResume ~ Choreographer", "Choreographer",
            "Choreographer ~ ActivityIdle", "ActivityIdle", "ActivityIdle ~ Animating end",
            "Running", "Runnable", "Uninterruptible Sleep", "Sleeping",
            "onCreate", "OpenCameraRequest", "onResume", "StartPreviewRequest"
        ]
        
        # [NEW] Định nghĩa lại keys để mask giống hệt Excel
        COLD_ONLY_KEYS = {
            "Touch Down ~ Start Proc", "Start Proc", "Start Proc ~ ActivityThreadMain",
            "Activity Thread Main", "ActivityThreadMain ~ bindApplication",
            "Bind Application", "bindApplication ~ activityStart"
        }
        WARM_ONLY_KEYS = {
            "Touch Duration", "Touch Up ~ Activity Start"
        }
        
        sequence_data = {}
        for metric in sequence_metrics:
            # [UPDATED v3] Lưu per-cycle values thay vì chỉ average
            # Format: "metric_name": [val_cycle1, val_cycle2, val_cycle3]
            # Giúp phát hiện spike ở từng cycle mà average che giấu
            per_cycle_values = []
            for cycle in valid_cycles:
                # [FIXED] Masking Logic: Read actual Launch Type per cycle (same as Excel)
                c_type = cycle.get("Launch Type", "Cold" if launch_type == "entry" else "Warm")
                if c_type == "Cold" and metric in WARM_ONLY_KEYS:
                    continue  # Bỏ qua Touch Duration cho cycle Cold
                if c_type == "Warm" and metric in COLD_ONLY_KEYS:
                    continue  # Bỏ qua Start Proc... cho cycle Warm
                
                val = cycle.get(metric, 0.0)
                if val and val > 0: 
                    per_cycle_values.append(round(float(val), 3))
                else:
                    per_cycle_values.append(0.0)
                    
            # Chỉ lưu nếu có ít nhất 1 giá trị > 0
            non_zero = [v for v in per_cycle_values if v > 0]
            if non_zero: 
                sequence_data[metric] = per_cycle_values
                
        if sequence_data: result["sequence"] = sequence_data
        
        # ========================
        # 2. EXTEND METRICS
        # ========================
        extend_data = {}

        # 2.1 START PROCESS ABNORMAL (List of Lists per Cycle)
        abnormal_process_list = []
        
        for cycle in valid_cycles:
            cycle_procs = []
            bg_states = cycle.get("Abnormal_Process_Data", [])
            if bg_states:
                for item in bg_states:
                    p_name = item.get('proc_name', '')
                    if p_name:
                        cycle_procs.append(p_name)
            
            abnormal_process_list.append(cycle_procs)
            
        extend_data["start_process_abnormal"] = abnormal_process_list

        # 2.2 LoadApkAssets
        loadapk_categories = ["system_server", "system_ui", "launching_app"]
        loadapk_data = {}
        for category in loadapk_categories:
            values = []
            for cycle in valid_cycles:
                cycle_loadapk = cycle.get("LoadApkAsset_Data", {})
                if isinstance(cycle_loadapk, dict):
                    assets = cycle_loadapk.get(category, [])
                    total = sum(item.get('dur_ms', 0.0) for item in assets)
                    if total > 0: values.append(total)
            if values: loadapk_data[category] = round(sum(values) / len(values), 3)
        if loadapk_data: extend_data["loadapkassets"] = loadapk_data
        
        # 2.3 Memory — [UPDATED v3] Per-cycle + Average
        if folder_path:
            memory_data = {}
            mem_free_vals, mem_avail_vals, pss_vals, pb_vals = [], [], [], []
            
            for idx, cycle in valid_cycles_with_idx:
                precomp = cycle.get('Precomputed_Extend_Data', {})
                
                mem_free = precomp.get('MemFree', 0.0)
                mem_free_vals.append(round(mem_free, 2) if mem_free > 0 else 0.0)
                
                mem_avail = precomp.get('MemAvailable', 0.0)
                mem_avail_vals.append(round(mem_avail, 2) if mem_avail > 0 else 0.0)
                
                pss = precomp.get('App_PSS', 0.0)
                pss_vals.append(round(pss, 2) if pss > 0 else 0.0)
                
                pb = precomp.get('Pageboostd', 0.0)
                pb_vals.append(round(pb, 2) if pb > 0 else 0.0)

            # Per-cycle lists (giúp phát hiện spike ở từng cycle)
            non_zero_mf = [v for v in mem_free_vals if v > 0]
            if non_zero_mf:
                memory_data["MemFree_MB"] = mem_free_vals
                memory_data["MemFree_MB_avg"] = round(sum(non_zero_mf)/len(non_zero_mf), 2)
            
            non_zero_ma = [v for v in mem_avail_vals if v > 0]
            if non_zero_ma:
                memory_data["MemAvailable_MB"] = mem_avail_vals
                memory_data["MemAvailable_MB_avg"] = round(sum(non_zero_ma)/len(non_zero_ma), 2)
            
            non_zero_pss = [v for v in pss_vals if v > 0]
            if non_zero_pss:
                memory_data["App_PSS_MB"] = pss_vals
                memory_data["App_PSS_MB_avg"] = round(sum(non_zero_pss)/len(non_zero_pss), 2)
            
            non_zero_pb = [v for v in pb_vals if v > 0]
            if non_zero_pb:
                memory_data["Pageboostd_MB"] = pb_vals
                memory_data["Pageboostd_MB_avg"] = round(sum(non_zero_pb)/len(non_zero_pb), 2)
            
            if memory_data: extend_data["memory"] = memory_data
            
        # 2.4 Abnormal — [UPDATED v3] Per-cycle + Average cho uptime
        if folder_path:
            abnormal_info = {}
            uptime_vals, start_reasons, kill_reasons, crash_counts, compilers = [], [], [], [], []
            
            for _, cycle in valid_cycles_with_idx:
                precomp = cycle.get('Precomputed_Extend_Data', {})
                
                ut = precomp.get('Uptime', 0)
                uptime_vals.append(round(ut, 2) if ut and ut > 0 else 0.0)
                
                sr = precomp.get('Start_Reason', "")
                if sr:
                    # Xử lý an toàn đề phòng hàm parser trả về string hoặc list
                    if isinstance(sr, list):
                        start_reasons.extend(sr)
                    else:
                        start_reasons.append(sr)

                kr = precomp.get('Kill_Reason', [])
                if kr: kill_reasons.extend(kr)
                
                cc = precomp.get('Crash_Count', 0)
                if cc and cc > 0: crash_counts.append(cc)
                
                ct = precomp.get('Compiler', '')
                if ct: compilers.append(ct)

            # Uptime: per-cycle list + average
            non_zero_ut = [v for v in uptime_vals if v > 0]
            if non_zero_ut:
                abnormal_info["uptime_minutes"] = uptime_vals
                abnormal_info["uptime_minutes_avg"] = round(sum(non_zero_ut)/len(non_zero_ut), 2)
            if start_reasons: abnormal_info["start_reasons"] = list((start_reasons))
            if kill_reasons: abnormal_info["kill_reasons"] = list((kill_reasons))
            if crash_counts: abnormal_info["crash_count_avg"] = round(sum(crash_counts)/len(crash_counts), 1)
            if compilers:
                from collections import Counter
                abnormal_info["compiler"] = Counter(compilers).most_common(1)[0][0]
            if abnormal_info: extend_data["abnormal"] = abnormal_info
        
        if extend_data: result["extend"] = extend_data

        # =========================================================
        # 3. TOP CPU BY PROCESS DIFF (TOP 5)
        # =========================================================
        cpu_cycles_data = []
        for idx, cycle in valid_cycles_with_idx:
            c_main = cycle
            c_comp = compare_cycles[idx] if compare_cycles and idx < len(compare_cycles) else None
            
            # Phân biệt đâu là DUT, đâu là REF để tính Diff = DUT - REF
            dut_cycle = c_main if is_dut else c_comp
            ref_cycle = c_comp if is_dut else c_main
            
            dut_p = dut_cycle.get("CPU_Process_Data", []) if dut_cycle else []
            ref_p = ref_cycle.get("CPU_Process_Data", []) if ref_cycle else []
            
            # 1. Build lookup maps cho REF
            ref_by_sql = {}
            ref_by_dump = {}
            for item in ref_p:
                s_name = item.get('sql_name', '')
                d_name = item.get('dumpstate_name')
                if s_name:
                    if s_name not in ref_by_sql: ref_by_sql[s_name] = item.copy()
                    else: ref_by_sql[s_name]['dur_ms'] += item.get('dur_ms', 0)
                if d_name:
                    if d_name not in ref_by_dump: ref_by_dump[d_name] = item.copy()
                    else: ref_by_dump[d_name]['dur_ms'] += item.get('dur_ms', 0)
            
            matched_results = []
            
            # 2. Duyệt qua DUT để match và tính Diff
            for dut_item in dut_p:
                dut_sql = dut_item.get('sql_name', '')
                dut_dump = dut_item.get('dumpstate_name')
                dut_val = dut_item.get('dur_ms', 0)
                
                ref_val = 0.0
                display_name = dut_sql
                match_found = False
                
                # Logic ghép cặp (Tiered Matching) giống Excel
                if not dut_sql.startswith("PID-") and dut_sql in ref_by_sql:
                    ref_val = ref_by_sql[dut_sql]['dur_ms']
                    match_found = True
                elif dut_dump and dut_dump in ref_by_dump:
                    ref_val = ref_by_dump[dut_dump]['dur_ms']
                    match_found = True
                    display_name = dut_dump
                else:
                    if dut_sql.startswith("PID-") and dut_dump:
                        display_name = dut_dump
                
                # Tính Diff = DUT - REF
                if match_found:
                    diff = dut_val - ref_val
                else:
                    if dut_dump:
                        ref_val = 0.0
                        diff = dut_val
                    else:
                        ref_val = 0.0
                        diff = 0.0 # Bỏ qua process rác không có dumpstate
                
                matched_results.append({
                    "name": display_name,
                    "dut": round(dut_val, 2),
                    "ref": round(ref_val, 2),
                    "diff": round(diff, 2)
                })
                
            # 3. Sort theo Diff giảm dần và lấy Top 5
            top_5 = sorted(matched_results, key=lambda x: x['diff'], reverse=True)[:5]
            
            if top_5:
                cpu_cycles_data.append({
                    "cycle": idx + 1,
                    "process": top_5
                })
                
        if cpu_cycles_data:
            result["top_process_consume_by_cycle"] = cpu_cycles_data
        
        # =========================================================
        # 3.1 TOP CPU BY THREAD DIFF (TOP 5)
        # =========================================================
        cpu_thread_cycles_data = []
        for idx, cycle in valid_cycles_with_idx:
            c_main = cycle
            c_comp = compare_cycles[idx] if compare_cycles and idx < len(compare_cycles) else None
            
            # Phân biệt đâu là DUT, đâu là REF để tính Diff = DUT - REF
            dut_cycle = c_main if is_dut else c_comp
            ref_cycle = c_comp if is_dut else c_main
            
            dut_t = dut_cycle.get("CPU_Thread_Data", []) if dut_cycle else []
            ref_t = ref_cycle.get("CPU_Thread_Data", []) if ref_cycle else []
            
            # Match Thread by (Thread Name, Process Name) vì TID thay đổi
            merged_t = {}
            def get_t_key(item): return (item['thread_name'], item['proc_name'])
            
            for x in dut_t: merged_t[get_t_key(x)] = {'dut': x['dur_ms'], 'ref': 0.0}
            for x in ref_t:
                k = get_t_key(x)
                if k not in merged_t: merged_t[k] = {'dut': 0.0, 'ref': 0.0}
                merged_t[k]['ref'] = x['dur_ms']
                
            final_thread = []
            for (tname, pname), v in merged_t.items():
                # Display name: "Thread (Process)"
                disp = f"{tname} ({pname})"
                final_thread.append({'name': disp, 'dut': v['dut'], 'ref': v['ref'], 'diff': v['dut'] - v['ref']})
            
            # Sort Diff -> Take Top 5
            top_5_thread = sorted(final_thread, key=lambda x: x['diff'], reverse=True)[:5]
            
            if top_5_thread:
                cpu_thread_cycles_data.append({
                    "cycle": idx + 1,
                    "thread": top_5_thread
                })
                
        if cpu_thread_cycles_data:
            result["top_thread_consume_by_cycle"] = cpu_thread_cycles_data

        # =========================================================
        # 4. PRIORITY STATICS (BY CYCLE) - [REFACTORED]
        # =========================================================
        priority_cycles_data = []
        frequency_cycles_data = []
        prio_categories = ['bindApplication', 'activityStart', 'activityResume', 'Choreographer']
        
        for idx, cycle in valid_cycles_with_idx:
            prio_data = cycle.get("Priority_Data", {})
            prio_cycle_result = {}
            freq_cycle_result = {}
            has_data = False
            
            for cat in prio_categories:
                if cat in prio_data and prio_data[cat]:
                    raw_map = prio_data[cat]
                    total_dur = sum(raw_map.values())
                    
                    if total_dur > 0:
                        prio_acc = defaultdict(float)
                        freq_acc = defaultdict(float)
                        
                        for key, val_ms in raw_map.items():
                            parts = str(key).split('_')
                            if len(parts) >= 1:
                                p_id = parts[0]
                                prio_acc[p_id] += val_ms
                                if len(parts) >= 2 and parts[1] != "0":
                                    freq_acc[parts[1]] += val_ms

                        # Priority data: Convert dict to list of objects, filter out 0.0%
                        prio_list = []
                        for prio_id, pct in prio_acc.items():
                            percentage = round((pct/total_dur)*100, 2)
                            if percentage > 0:
                                prio_list.append({
                                    "priority": int(prio_id),
                                    "percentage": percentage
                                })
                        if prio_list:
                            prio_cycle_result[cat] = prio_list
                            has_data = True
                        
                        # Frequency data: Convert dict to list of objects, filter out 0.0%
                        freq_list = []
                        for freq_id, pct in freq_acc.items():
                            percentage = round((pct/total_dur)*100, 2)
                            if percentage > 0:
                                freq_list.append({
                                    "frequency": int(freq_id),
                                    "percentage": percentage
                                })
                        if freq_list:
                            freq_cycle_result[cat] = freq_list
                            has_data = True
            
            if has_data:
                priority_cycles_data.append({"cycle": idx + 1, "data": prio_cycle_result})
                frequency_cycles_data.append({"cycle": idx + 1, "data": freq_cycle_result})
        
        if priority_cycles_data: result["priority_by_cycle"] = priority_cycles_data
        if frequency_cycles_data: result["frequency_by_cycle"] = frequency_cycles_data

        # 5. BLOCK I/O
        bio_cycles = []
        for idx, cycle in valid_cycles_with_idx:
            bio = sorted(cycle.get("Block_IO_Data", []), key=lambda x: x.get('timeTotalMs', 0), reverse=True)[:10]
            bio_list = [{"name": x.get('libraryName', 'Unknown'), "val": x.get('timeTotalMs', 0)} for x in bio]
            if bio_list: bio_cycles.append({"cycle": idx+1, "data": bio_list})
        if bio_cycles: result["block_io_by_cycle"] = bio_cycles
        
        # 6. BINDER
        b_durs, b_counts = [], []
        for cycle in valid_cycles:
            b = cycle.get("Binder_Transaction_Data", {})
            if b.get('duration_ms', 0) > 0: b_durs.append(b['duration_ms'])
            if b.get('count', 0) > 0: b_counts.append(b['count'])
        if b_durs or b_counts:
            result["binder_transaction"] = {
                "duration_ms": round(sum(b_durs)/len(b_durs), 3) if b_durs else 0,
                "count": int(sum(b_counts)/len(b_counts)) if b_counts else 0
            }

        return result

        # =====================
    # BUILD & WRITE CONSOLIDATED JSON FILES (MASTER FILES)
    # =====================
    timestamp = datetime.datetime.now().isoformat()
    
    # Lấy danh sách tất cả apps từ cả DUT và REF
    all_apps = set(dut_results.keys()) | set(ref_results.keys())
    
    # Tạo output directory
    output_dir = os.path.join(output_folder, "Output")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n Exporting consolidated JSON files (1 for DUT, 1 for REF)...")

    # [NEW] Khởi tạo 2 biến Master Dictionary để chứa toàn bộ data
    master_dut = {
        "model": dut_model,
        "device_code": dut_device_code,
        "version": dut_version,
        "timestamp": timestamp,
        "type": "DUT",
        "apps_data": []  # List chứa data của tất cả các app
    }
    
    master_ref = {
        "model": ref_model,
        "device_code": ref_device_code,
        "version": ref_version,
        "timestamp": timestamp,
        "type": "REF",
        "apps_data": []  # List chứa data của tất cả các app
    }
    
    # Export từng app cho DUT và REF
    for app_name in sorted(all_apps):
        
        # =========================================================================
        # [FIX QUAN TRỌNG] Lấy data gốc và Đồng bộ time window (end_ts) giữa DUT & REF 
        # Giống hệt logic tiền xử lý của bảng Excel để metrics (CPU, LoadApk...) khớp 100%
        # =========================================================================
        raw_dut_entry = dut_results.get(app_name, {}).get("entry", [])
        raw_ref_entry = ref_results.get(app_name, {}).get("entry", [])
        
        max_c = max(len(raw_dut_entry), len(raw_ref_entry))
        dut_entry_cycles = []
        ref_entry_cycles = []
        
        for i in range(max_c):
            d_c = raw_dut_entry[i] if i < len(raw_dut_entry) else None
            r_c = raw_ref_entry[i] if i < len(raw_ref_entry) else None
            
            if d_c and r_c:
                common_type = select_common_end_ts_type(d_c, r_c)
                if common_type:
                    dut_entry_cycles.append(get_metrics_for_end_ts_type(d_c, common_type))
                    ref_entry_cycles.append(get_metrics_for_end_ts_type(r_c, common_type))
                else:
                    dut_entry_cycles.append(d_c)
                    ref_entry_cycles.append(r_c)
            elif d_c:
                dut_entry_cycles.append(d_c)
                ref_entry_cycles.append(None)
            elif r_c:
                dut_entry_cycles.append(None)
                ref_entry_cycles.append(r_c)

        # =====================
        # DUT - Chỉ lấy entry
        # =====================
        if any(c is not None for c in dut_entry_cycles):
            # Truyền compare_cycles=ref_entry_cycles và is_dut=True
            dut_metrics = calculate_metrics_for_app(
                dut_entry_cycles, app_name, "entry", dut_folder_path, 
                compare_cycles=ref_entry_cycles, is_dut=True
            )
            if dut_metrics:
                # [NEW] Nhét data của app này vào danh sách tổng của DUT
                master_dut["apps_data"].append({
                    "app": app_name,
                    "entry": dut_metrics
                })
        
        # =====================
        # REF - Chỉ lấy entry
        # =====================
        if any(c is not None for c in ref_entry_cycles):
            # Truyền compare_cycles=dut_entry_cycles và is_dut=False
            ref_metrics = calculate_metrics_for_app(
                ref_entry_cycles, app_name, "entry", ref_folder_path, 
                compare_cycles=dut_entry_cycles, is_dut=False
            )
            if ref_metrics:
                # [NEW] Nhét data của app này vào danh sách tổng của REF
                master_ref["apps_data"].append({
                    "app": app_name,
                    "entry": ref_metrics
                })

    # ===================== 
    # GHI 2 FILE MASTER RA Ổ CỨNG
    # =====================
    safe_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    if master_dut["apps_data"]:
        # [NEW] Đổi format tên file thành DUT_Model_Version_Time
        dut_prefix = f"DUT_{dut_model}_{dut_version}" if (dut_model and dut_version) else "DUT_all_apps"
        dut_file_path = os.path.join(output_dir, f"{dut_prefix}_{safe_time}.json")
        with open(dut_file_path, 'w', encoding='utf-8') as f:
            json.dump(master_dut, f, indent=2, ensure_ascii=False)
        print(f"  -> Created DUT JSON: {os.path.basename(dut_file_path)}")

    if master_ref["apps_data"]:
        # [NEW] Đổi format tên file thành REF_Model_Version_Time
        ref_prefix = f"REF_{ref_model}_{ref_version}" if (ref_model and ref_version) else "REF_all_apps"
        ref_file_path = os.path.join(output_dir, f"{ref_prefix}_{safe_time}.json")
        with open(ref_file_path, 'w', encoding='utf-8') as f:
            json.dump(master_ref, f, indent=2, ensure_ascii=False)
        print(f"  -> Created REF JSON: {os.path.basename(ref_file_path)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

