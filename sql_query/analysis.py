from sql_query.base import *
from sql_query.trace_queries import *
from sql_query.sequence_queries import *
from sql_query.loadapk_asset import *
from sql_query.cpu_queries import *
from sql_query.binder_transaction import get_binder_transaction
from sql_query.block_io import *
from pathlib import Path

def analyze_trace(tp: TraceProcessor, trace_path: str, pid_mapping: Dict[int, str] = None) -> Dict[str, Any]:
    """
    Analyze a trace file and extract performance metrics.
    
    Args:
        tp: TraceProcessor instance
        trace_path: Path to the trace file
        pid_mapping: Optional dict {PID: process_name} from dumpstate for CPU process mapping
    
    Returns:
        Dict containing all extracted metrics
    """
    metrics: Dict[str, Any] = {}

    ensure_slice_with_names_view(tp)

    # 1. Detect Recent Case & Launch Type
    file_name = Path(trace_path).stem.lower()
    # Kiểm tra flag is_recent dựa trên tên file
    is_recent = "recent" in file_name 
    
    app_pkg = detect_app_from_launch(tp)
    
    # Nếu là Recent mà không thấy launching slice, gán pkg giả định
    if not app_pkg:
        if is_recent:
            app_pkg = "com.sec.android.app.launcher" 
        else:
            print(f"Cannot find launching:... in trace {trace_path}")
            raise RuntimeError(f"Cannot find launching:... in trace {trace_path}")
            # return {}
            

    # 2. Identify App Process (UPID/PID)
    # - Recent: Process chính chứa Resume/Choreographer thường là Launcher
    # - App thường: Tìm theo activityStart/Resume của app
    app_upid, app_pid, app_name, app_tid = None, None, None, None
    
    if is_recent:
        # Recent: Tìm process chứa 'activityResume' (Thường là Launcher)
        row_resume = find_slice(tp, name_exact='activityResume')
        if row_resume is not None:
            app_upid = int(row_resume['upid'])
            app_pid = int(row_resume['pid'])
            app_tid = int(row_resume['tid'])
            app_name = str(row_resume.get('process_name', 'Launcher'))
        else:
            # Fallback nếu không thấy Resume, thử tìm theo Launcher PID
            launcher_pid = get_launcher_pid(tp)
            if launcher_pid:
                app_pid = launcher_pid
                # Lấy UPID từ PID
                df_upid = query_df(tp, f"SELECT upid FROM process WHERE pid = {app_pid}")
                if df_upid is not None:
                     app_upid = int(df_upid.iloc[0]['upid'])
                     app_tid = app_pid # Fallback
            else:
                print(f"[WARN] {Path(trace_path).name}: Cannot identify Recent process.")
    else:
        # Logic App thường
        app_proc = find_app_process(tp)
        if not app_proc:
            print(f"[WARN] {Path(trace_path).name}: No activityStart/Resume found. Analysis skipped.")
            return {} 
        app_upid, app_pid, app_name, app_tid = app_proc

    # 3. Execution Interval
    
    # [Touch Down]
    touch_down_ts = get_first_deliver_input(tp)
    if touch_down_ts is None:
        print("Cannot find deliverInputEvent in trace")

    # [Animating] (Recent không có animating trong system_server)
    animating_end = 0
    if not is_recent:
        try:
            animating_end = get_animating(tp)
        except RuntimeError:
            # raise RuntimeError("Trace không hợp lệ: Không tìm thấy 'animating'")
            print("[WARN] Cannot find 'animating', skipping.") # FIXED: Print instead of raise
            animating_end = 0

    # [Launching End]
    launching_end = get_launching_end(tp, app_pkg)
    
    # [Activity Idle]
    start_idle, end_idle = get_activity_idle_end(tp, app_upid)

    # [Calculated End TS]
    end_ts = None
    is_camera = "camera" in (app_pkg or "").lower()
    is_internet = "internet" in file_name or "browser" in (app_pkg or "").lower()
    
    if is_camera:
        slices_name = ["StartPreviewRequest", "onCreate", "OpenCameraRequest", "onResume"]
        df = get_slice_on_app_process(tp, app_pid, slices_name)
        result = process_multiple_slices_data(df)
        
        metrics["onCreate"] = to_ms(result.get("onCreate", [0, 0])[1])
        metrics["OpenCameraRequest"] = to_ms(result.get("OpenCameraRequest", [0, 0])[1])
        metrics["onResume"] = to_ms(result.get("onResume", [0, 0])[1])
        metrics["StartPreviewRequest"] = to_ms(result.get("StartPreviewRequest", [0, 0])[1])
        
        preview_data = result.get("StartPreviewRequest", [0, 0])
        if preview_data[1] > 0:
            end_ts = preview_data[0] + preview_data[1]
        else:
            end_ts = animating_end 

    elif is_recent:
        # RECENT: Ưu tiên activityIdle -> Launching End -> Fallback
        if end_idle:
            end_ts = end_idle
        elif launching_end:
            end_ts = launching_end
        else:
            # Fallback an toàn: Touch Down + 500ms
            end_ts = touch_down_ts + 500_000_000

    else:   
        # APP THƯỜNG
        if is_internet and start_idle and launching_end and (launching_end + 100_000_000 < start_idle):
            end_ts = animating_end
            start_idle = None
            end_idle = None
        elif end_idle:
            end_ts = end_idle
        else:
            end_ts = animating_end
            start_idle = None
            end_idle = None

    # Max với animating_end (chỉ áp dụng với App thường)
    if not is_recent:
        end_ts = max(end_ts, animating_end) if end_ts else animating_end

    metrics["App Execution Time"] = to_ms(end_ts - touch_down_ts) if end_ts else 0.0

    # 4. Detailed Metrics

    # [Touch Down ~ Start Proc]
    start_proc_info = get_start_proc_start(tp, app_pkg)
    
    # SỬA: Kiểm tra kỹ start_proc_info và phần tử đầu tiên
    if start_proc_info and start_proc_info[0] is not None:
        start_proc_ts, start_proc_dur, start_proc_end = start_proc_info
        # Thêm try-except hoặc kiểm tra None để an toàn tuyệt đối
        if start_proc_ts is not None and touch_down_ts is not None:
            metrics["Touch Down ~ Start Proc"] = to_ms(start_proc_ts - touch_down_ts)
        else:
            metrics["Touch Down ~ Start Proc"] = 0.0
        metrics["Start Proc"] = to_ms(start_proc_dur)  
    else:
        start_proc_ts, start_proc_dur, start_proc_end = None, None, None
        metrics["Touch Down ~ Start Proc"] = 0.0
        metrics["Start Proc"] = 0.0

    # [Launch Type]
    if is_recent:
        metrics["Launch Type"] = "Warm" # Recent luôn là Warm
    else:
        metrics["Launch Type"] = "Cold" if has_bind_application(tp, app_upid) else "Warm"

    # [ActivityThreadMain], [BindApp]
    act_main = get_event_ts(tp, app_upid, "ActivityThreadMain")
    if act_main:
        act_main_ts, act_main_dur, act_main_end = act_main
        metrics["Activity Thread Main"] = to_ms(act_main_dur)
    else:
        act_main_ts, act_main_dur, act_main_end = None, None, None
        metrics["Activity Thread Main"] = 0.0

    bind_app = get_event_ts(tp, app_upid, "bindApplication")
    if bind_app:
        bind_app_ts, bind_app_dur, bind_app_end = bind_app
        metrics["Bind Application"] = to_ms(bind_app_dur)
    else:
        bind_app_ts, bind_app_dur, bind_app_end = None, None, None
        metrics["Bind Application"] = 0.0

    # [Activity Start] 
    # FIX: Recent activityStart nằm ở Launcher, App thường nằm ở App Process
    act_start_ts, act_start_dur, act_start_end = None, None, None
    
    if is_recent:
        launcher_pid = get_launcher_pid(tp)
        if launcher_pid:
            # Tìm activityStart trong Launcher process
            row_start = find_slice(tp, name_exact='activityStart', pid=launcher_pid)
            if row_start is not None:
                act_start_ts = int(row_start['ts'])
                act_start_dur = int(row_start['dur'])
                act_start_end = int(row_start['end_ts'])
    else:
        act_start_info = get_event_ts(tp, app_upid, "activityStart")
        if act_start_info:
            act_start_ts, act_start_dur, act_start_end = act_start_info

    metrics["Activity Start"] = to_ms(act_start_dur) if act_start_dur else 0.0

    # [Activity Resume]
    cho_threshold = 0
    act_resume = get_event_ts(tp, app_upid, "activityResume")
    if act_resume:
        act_resume_ts, act_resume_dur, act_resume_end = act_resume
        metrics["Activity Resume"] = to_ms(act_resume_dur)
        cho_threshold = act_resume_end
    else:
        act_resume_ts, act_resume_dur, act_resume_end = None, None, None
        metrics["Activity Resume"] = 0.0

    # [Touch Info]
    launcher_pid = get_launcher_pid(tp)
    if launcher_pid is not None:
        touch_up, touch_up_end = get_end_deliver_input(tp, launcher_pid)
        if touch_up is not None:
            metrics["Touch Duration"] = to_ms(touch_up - touch_down_ts) 
            # Dùng act_start_ts đã fix ở trên
            if act_start_ts and act_start_ts > touch_up:
                metrics["Touch Up ~ Activity Start"] = to_ms(act_start_ts - touch_up)
            else:
                 metrics["Touch Up ~ Activity Start"] = 0.0
        else:
            metrics["Touch Duration"] = 0.0
            metrics["Touch Up ~ Activity Start"] = 0.0
    else:
        metrics["Touch Duration"] = 0.0
        metrics["Touch Up ~ Activity Start"] = 0.0

    # [Time Gaps]
    if start_proc_end and act_main_ts:
        metrics["Start Proc ~ ActivityThreadMain"] = to_ms(act_main_ts - start_proc_end) if act_main_ts > start_proc_end else 0.0
    else:
        metrics["Start Proc ~ ActivityThreadMain"] = 0.0

    if act_main_end and bind_app_ts:
        metrics["ActivityThreadMain ~ bindApplication"] = to_ms(bind_app_ts - act_main_end) if bind_app_ts > act_main_end else 0.0
    else:
        metrics["ActivityThreadMain ~ bindApplication"] = 0.0

    if bind_app_end and act_start_ts:
        metrics["bindApplication ~ activityStart"] = to_ms(act_start_ts - bind_app_end) if act_start_ts > bind_app_end else 0.0
    else:
        metrics["bindApplication ~ activityStart"] = 0.0

    if act_start_end and act_resume_ts:
        metrics["activityStart ~ activityResume"] = to_ms(act_resume_ts - act_start_end) if act_resume_ts > act_start_end else 0.0
    else:
        metrics["activityStart ~ activityResume"] = 0.0

    # [Choreographer]
    cho_info = get_choreographer(tp, app_pid, cho_threshold if cho_threshold else 0)
    if cho_info:
        cho_ts, cho_dur, cho_end = cho_info
        
        if is_camera and end_ts > cho_ts:
             metrics["Choreographer"] = to_ms(end_ts - cho_ts)
        else:
             # Fallback: Dùng duration của chính slice Choreographer 
             metrics["Choreographer"] = to_ms(cho_dur) if cho_dur else 0.0
    else:
        cho_ts, cho_dur, cho_end = None, None, None
        metrics["Choreographer"] = 0.0

    if act_resume_end and cho_ts:
        metrics["ActivityResume ~ Choreographer"] = to_ms(cho_ts - act_resume_end) if cho_ts > act_resume_end else 0.0
    else:
        metrics["ActivityResume ~ Choreographer"] = 0.0

    if cho_end and start_idle and not is_camera:
        metrics["Choreographer ~ ActivityIdle"] = to_ms(start_idle - cho_end) if cho_end is not None else 0.0
    elif launching_end is not None and start_idle and is_camera:
        metrics["Choreographer ~ ActivityIdle"] = to_ms(start_idle - launching_end) if launching_end is not None else 0.0
    else:
        metrics["Choreographer ~ ActivityIdle"] = 0.0

    # [ActivityIdle]
    if start_idle and end_idle:
        metrics["ActivityIdle"] = to_ms(end_idle - start_idle)
    else:
        metrics["ActivityIdle"] = 0.0

    if end_idle and animating_end and not is_recent:
        metrics["ActivityIdle ~ Animating end"] = to_ms(animating_end - end_idle) if animating_end > end_idle else 0.0
    else:
        metrics["ActivityIdle ~ Animating end"] = to_ms(animating_end - cho_end) if animating_end > cho_end else 0.0

    # =========================================================================
    # [NEW] MULTI END_TS QUERY LOGIC
    # Query data cho TẤT CẢ available end_ts types để có thể chọn common type sau
    # =========================================================================
    
    # 1. Collect all available end_ts values
    end_ts_variants = {}
    
    if end_idle and end_idle > 0:
        end_ts_variants["activityIdle"] = end_idle
    
    if animating_end and animating_end > 0:
        end_ts_variants["animating"] = animating_end
    
    # Camera có thêm startPreviewRequest
    if is_camera:
        preview_data = result.get("StartPreviewRequest", [0, 0])
        if preview_data[0] > 0 and preview_data[1] > 0:
            end_ts_variants["startPreviewRequest"] = preview_data[0] + preview_data[1]
    
    metrics["end_ts_variants"] = end_ts_variants
    metrics["end_ts_primary"] = end_ts  # end_ts được chọn theo logic hiện tại (để backward compatible)
    
    # 2. Query data cho MỖI end_ts type
    data_by_end_ts = {}
    
    for end_ts_type, end_ts_value in end_ts_variants.items():
        if end_ts_value and end_ts_value > 0:
            data_by_end_ts[end_ts_type] = _query_end_ts_dependent_data(
                tp=tp,
                touch_down_ts=touch_down_ts,
                end_ts=end_ts_value,
                app_pid=app_pid,
                app_tid=app_tid,
                pid_mapping=pid_mapping,
                trace_path=trace_path
            )
    
    metrics["data_by_end_ts"] = data_by_end_ts
    
    # 3. Backward compatible: Copy data từ primary end_ts vào metrics root
    # Xác định end_ts_type tương ứng với end_ts đã chọn
    primary_type = None
    if end_ts:
        # Tìm type gần nhất với end_ts primary
        for etype, evalue in end_ts_variants.items():
            if evalue == end_ts:
                primary_type = etype
                break
        
        # Fallback: Nếu end_ts = max của nhiều giá trị, chọn type lớn nhất
        if not primary_type and end_ts_variants:
            primary_type = max(end_ts_variants.keys(), key=lambda k: end_ts_variants[k])
    
    if primary_type and primary_type in data_by_end_ts:
        primary_data = data_by_end_ts[primary_type]
        # Copy các fields vào metrics root để backward compatible
        for key in ["Running", "Runnable", "Uninterruptible Sleep", "Sleeping",
                    "Block_IO_Data", "LoadApkAsset_Data", "CPU_Process_Data", 
                    "CPU_Thread_Data", "Binder_Transaction_Data", 
                    "Abnormal_Process_Data", "Background_Process_States"]:
            if key in primary_data:
                metrics[key] = primary_data[key]
    else:
        # Fallback: Query với end_ts primary (logic cũ)
        state_summary = get_thread_state_summary(tp, app_tid, touch_down_ts, (end_ts - touch_down_ts) if end_ts else 0)
        metrics["Running"] = state_summary.get("Running", 0.0)
        metrics["Runnable"] = state_summary.get("R", 0.0) + state_summary.get("R+", 0.0)
        metrics["Uninterruptible Sleep"] = state_summary.get("D", 0.0)
        metrics["Sleeping"] = state_summary.get("S", 0.0)
        
        safe_start_time = touch_down_ts if touch_down_ts else 0
        safe_end_time = end_ts if end_ts else (safe_start_time + 10_000_000_000)
        block_io_df = top_block_IO(tp, app_pid, safe_start_time, safe_end_time)
        library_block_io = process_block_io_data(block_io_df)
        
        # Kernel Block I/O (fallback path)
        dur_time_fb = (end_ts - touch_down_ts) if end_ts and touch_down_ts else 0
        kernel_block_io = get_kernel_block_io(tp, app_pid, safe_start_time, dur_time_fb, trace_path=trace_path)
        metrics["Block_IO_Data"] = library_block_io + kernel_block_io
        
        load_apk_pids = get_pid_list(tp)
        if not load_apk_pids:
            load_apk_pids = [app_pid]
        if app_pid not in load_apk_pids:
            load_apk_pids.append(app_pid)
        loadapk_df = get_loadApkAsset(tp, load_apk_pids, touch_down_ts, end_ts if end_ts else 0)
        metrics["LoadApkAsset_Data"] = process_loadapk_data(loadapk_df)
        
        cpu_cores = [0, 1, 2, 3, 4, 5, 6, 7]
        dur_time = (end_ts - touch_down_ts) if end_ts else 0
        cpu_proc_df = get_top_cpu_usage_process(tp, touch_down_ts, dur_time, cpu_cores)
        metrics["CPU_Process_Data"] = process_cpu_data_process(cpu_proc_df, pid_mapping)
        cpu_thread_df = get_top_cpu_usage_thread(tp, touch_down_ts, dur_time, cpu_cores)
        metrics["CPU_Thread_Data"] = process_cpu_data_thread(cpu_thread_df)
        
        binder_count, binder_dur = get_binder_transaction(tp, app_tid, end_ts if end_ts else 0)
        metrics["Binder_Transaction_Data"] = {
            'count': binder_count if binder_count is not None else 0,
            'duration_ms': binder_dur if binder_dur is not None else 0.0
        }
        
        abnormal_start = touch_down_ts if touch_down_ts else 0
        abnormal_end = end_ts if end_ts else 0
        target_abnormal_slices = ['bindApplication']
        abnormal_df = get_abnormal_processes(tp, abnormal_start, abnormal_end, app_pid, target_abnormal_slices)
        metrics["Abnormal_Process_Data"] = process_abnormal_data(abnormal_df)
        metrics["Background_Process_States"] = get_background_process_states(tp, touch_down_ts if touch_down_ts else 0, end_ts if end_ts else 0)

    # =========================================================
    # [NEW] PRIORITY STATISTICS
    # =========================================================
    prio_data = {}
    
    # Định nghĩa các khoảng thời gian cần soi (Name: (start, end))
    # Lưu ý: Các biến bind_app_ts, bind_app_end... đã được tính ở phần trên của hàm analyze_trace
    target_intervals = {
        'bindApplication': (bind_app_ts, bind_app_end) if 'bind_app_ts' in locals() and bind_app_ts else None,
        'activityStart': (act_start_ts, act_start_end) if 'act_start_ts' in locals() and act_start_ts else None,
        'activityResume': (act_resume_ts, act_resume_end) if 'act_resume_ts' in locals() and act_resume_ts else None,
        'Choreographer': (cho_ts, cho_end) if 'cho_ts' in locals() and cho_ts else None
    }
    
    if app_tid: # Đảm bảo đã tìm được Main Thread ID
        for cat_name, interval in target_intervals.items():
            if interval:
                start, end = interval
                if start and end and end > start:
                    stats = get_priority_distribution(tp, app_tid, start, end)
                    if stats:
                        prio_data[cat_name] = stats
    
    metrics["Priority_Data"] = prio_data

    # =========================================================
    # [NEW] LAYOUT DEPTH ANALYSIS
    # =========================================================
    layout_data = {}
    
    # Sử dụng lại target_intervals đã định nghĩa ở phần Priority
    # (bindApplication, activityStart, activityResume, Choreographer)
    # Nếu chưa có biến target_intervals, hãy copy lại từ đoạn Priority check:
    target_intervals = {
        'bindApplication': (bind_app_ts, bind_app_end) if 'bind_app_ts' in locals() and bind_app_ts else None,
        'activityStart': (act_start_ts, act_start_end) if 'act_start_ts' in locals() and act_start_ts else None,
        'activityResume': (act_resume_ts, act_resume_end) if 'act_resume_ts' in locals() and act_resume_ts else None,
        'Choreographer': (cho_ts, cho_end) if 'cho_ts' in locals() and cho_ts else None
    }
    
    if app_tid:
        for cat_name, interval in target_intervals.items():
            if interval:
                start, end = interval
                if start and end and end > start:
                    # Lấy dữ liệu depth (Max depth = 6)
                    depth_slices = get_layout_depth_slices(tp, app_tid, start, end, max_depth=6)
                    layout_data[cat_name] = depth_slices

    metrics["Layout_Data"] = layout_data

    metrics["PID_Mapping"] = pid_mapping if pid_mapping else {}
    metrics["App Package"] = app_pkg 
    return metrics

    '''
    def get_top_cpu_usage_process(tp: TraceProcessor, start_time: int, dur_time: int, cpu_cores: List[int]):
    if not cpu_cores or dur_time <= 0: return None
    cpu_cores_str = ','.join(map(str, cpu_cores))
    end_time = start_time + dur_time
    
    sql = f"""
    SELECT 
        COALESCE(
            process.name, 
            CASE 
                WHEN main_thread.name LIKE '%binder%' OR main_thread.name LIKE '%kworker%' THEN NULL
                ELSE main_thread.name
            END, 
            'PID-' || process.pid
        ) as proc_name,
        process.pid as raw_pid,
        
        -- Dùng MIN/MAX để lấy đúng khoảng thời gian giao nhau (Overlap Duration)
        SUM(MIN(sched_slice.ts + sched_slice.dur, {end_time}) - MAX(sched_slice.ts, {start_time})) / 1e6 AS dur_ms,
        
        COUNT(*) AS Occurences, 
        
        ROUND(SUM(MIN(sched_slice.ts + sched_slice.dur, {end_time}) - MAX(sched_slice.ts, {start_time})) * 100.0 / ({dur_time} * 7), 2) AS dur_percent
        
    FROM sched_slice 
    JOIN thread USING (utid) 
    JOIN process USING (upid)
    LEFT JOIN thread AS main_thread ON (process.pid = main_thread.tid)
    
    WHERE sched_slice.cpu IN ({cpu_cores_str})
      AND NOT thread.name LIKE 'swapper%' 
      -- Lọc các slice có khoảng thời gian chạm vào window của chúng ta
      AND sched_slice.ts < {end_time} 
      AND (sched_slice.ts + sched_slice.dur) > {start_time}
      
    GROUP BY COALESCE(proc_name, raw_pid)
    ORDER BY dur_ms DESC;
    """
    df = query_df(tp, sql)
    return df
    '''


    