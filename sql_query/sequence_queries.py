from sql_query.base import to_ms, query_df, ensure_slice_with_names_view, find_slice
from sql_query.block_io import top_block_IO, process_block_io_data, get_hal_block_io, get_kernel_block_io, get_hal_library_block_io, process_hal_block_io_data
from sql_query.loadapk_asset import get_system_pids, get_loadApkAsset, process_loadapk_data, get_camera_hal_pid
from sql_query.cpu_queries import get_top_cpu_usage_process, process_cpu_data_process, get_top_cpu_usage_thread, process_cpu_data_thread
from sql_query.binder_transaction import get_binder_transaction
from perfetto.trace_processor.api import TraceProcessor
from typing import Dict, Optional, Any, Tuple, List
from collections import defaultdict
import pandas as pd

__all__ = [
    'get_thread_state_summary',
    'get_slice_on_app_process',
    'process_multiple_slices_data',
    'get_abnormal_processes',
    'process_abnormal_data',
    'get_background_process_states',
    '_query_end_ts_dependent_data',
    'get_layout_depth_slices',
]

def get_thread_state_summary(tp: TraceProcessor, app_tid: int,
                             ts_start: int, ts_dur: int) -> Dict[str, float]:
    """
    Tổng thời gian các state (Running, R, S, D...) của một thread.
    Sử dụng SPAN_JOIN giữa intervals và thread_state.
    """
    if ts_dur <= 0:
        return {}

    # 1. View state_view
    sql = f"""
    DROP VIEW IF EXISTS state_view;
    CREATE VIEW state_view AS
    SELECT
        thread_state.state,
        thread_state.ts,
        thread_state.dur
    FROM thread_state
    JOIN thread USING (utid)
    WHERE thread.tid = {app_tid};
    """
    tp.query(sql)

    # 2. View intervals
    sql = f"""
    DROP VIEW IF EXISTS intervals;
    CREATE VIEW intervals AS
    SELECT {ts_start} AS ts, {ts_dur} AS dur;
    """
    tp.query(sql)

    # 3. Span join
    sql = """
    DROP TABLE IF EXISTS target_view;
    CREATE VIRTUAL TABLE target_view
    USING span_join (intervals, state_view);
    """
    tp.query(sql)

    # 4. Aggregate
    sql = """
    SELECT
        state,
        SUM(dur) / 1e6 AS total_duration_ms
    FROM target_view
    GROUP BY state
    ORDER BY total_duration_ms DESC;
    """
    df = query_df(tp, sql)

    # 5. Cleanup
    tp.query("DROP TABLE IF EXISTS target_view;")
    tp.query("DROP VIEW  IF EXISTS intervals;")
    tp.query("DROP VIEW  IF EXISTS state_view;")

    if df is None:
        return {}

    result: Dict[str, float] = {}
    for _, row in df.iterrows():
        state = str(row["state"])
        try:
            total_ms = float(row["total_duration_ms"])
        except (TypeError, ValueError):
            continue
        result[state] = total_ms

    return result

# [File: sql_query.py]

def get_slice_on_app_process(tp: TraceProcessor, app_pid: int, slice_names: list):
    """Lấy danh sách nhiều slice trên cả Thread/Process Track."""
    if not slice_names:
        return None
    values_clause = ", ".join([f"('{name}')" for name in slice_names])
    sql = f"""
    WITH 
    TargetProcess AS (SELECT DISTINCT upid FROM process WHERE pid = {app_pid}),
    TargetPatterns(pattern) AS (VALUES {values_clause})
    SELECT s.name AS slice_name, s.ts, s.dur
    FROM slice s
    JOIN thread_track tt ON s.track_id = tt.id
    JOIN thread t ON tt.utid = t.utid
    JOIN TargetProcess p ON t.upid = p.upid
    JOIN TargetPatterns tn ON s.name LIKE tn.pattern
    UNION ALL
    SELECT s.name AS slice_name, s.ts, s.dur
    FROM slice s
    JOIN process_track pt ON s.track_id = pt.id
    JOIN TargetProcess p ON pt.upid = p.upid
    JOIN TargetPatterns tn ON s.name LIKE tn.pattern
    ORDER BY ts;
    """
    return query_df(tp, sql)

def process_multiple_slices_data(df) -> Dict[str, List[int]]:
    if df is None or df.empty:
        return {}
    result = {}
    for _, row in df.iterrows():
        slice_name = str(row['slice_name'])
        ts = int(row['ts'])
        dur = int(row['dur'])
        if slice_name not in result:
            result[slice_name] = [ts, dur]
    return result
# -------------------------------------------------------------------
# ABNORMAL PROCESSES 
# -------------------------------------------------------------------
def get_abnormal_processes(tp: TraceProcessor, start_time: int, end_time: int, exclude_pid: int, target_slices: List[str] = None):
    """
    Lấy danh sách các process khởi chạy (bindApplication) trong khoảng thời gian [start_time, end_time].
    Loại trừ PID của App chính.
    """
    # Validate inputs
    if not end_time or not exclude_pid:
        return None
    
    if start_time is None:
        start_time = 0

    if target_slices is None:
        target_slices = ['bindApplication']
    
    # Format list cho SQL: 'bindApplication', 'activityStart'
    slice_names_str = ", ".join([f"'{s}'" for s in target_slices])
    
    sql = f"""
    SELECT 
        process.pid,
        -- Fix tên process null: Ưu tiên process.name -> thread.name -> PID
        COALESCE(process.name, thread.name, 'PID-' || process.pid) as proc_name,
        slice.name as slice_name,
        slice.ts as start_time,
        slice.dur as duration_ns
    FROM slice
    JOIN thread_track ON slice.track_id = thread_track.id
    JOIN thread USING (utid)
    JOIN process USING (upid)
    WHERE 
        slice.name IN ({slice_names_str})
        AND slice.ts >= {start_time} 
        AND slice.ts <= {end_time}   
        AND process.pid != {exclude_pid}
    ORDER BY slice.ts ASC;
    """
    
    return query_df(tp, sql)

def process_abnormal_data(df) -> List[Dict[str, Any]]:
    """
    Chuyển đổi DataFrame Abnormal Process thành list dictionary để hiển thị (tương tự process_cpu_usage_data).
    """
    if df is None or df.empty:
        return []
    
    result = []
    for _, row in df.iterrows():
        result.append({
            'pid': str(row['pid']),
            'proc_name': str(row['proc_name']),
            'slice_name': str(row['slice_name']),
            'start_time': int(row['start_time']),
            'duration_ms': to_ms(row['duration_ns']) # Dùng hàm to_ms có sẵn
        })
    return result


def get_background_process_states(tp: TraceProcessor, start_ts: int, end_ts: int) -> List[Dict[str, Any]]:
    """
    Lấy danh sách các background process (theo pattern gms, google...) 
    có hoạt động (Running + Runnable) > 10ms trong khoảng thời gian launch.
    """
    if not start_ts or not end_ts or start_ts >= end_ts:
        return []

    duration = end_ts - start_ts

    # Danh sách các pattern tên process cần tìm
    target_patterns = [
        '%gms.persistent%', 
        '%googlequicksearchbox%', 
        '%com.google.android.play%',
        '%.apps.messaging%'
    ]
    
    # Tạo câu điều kiện OR (Fix lỗi process name null)
    or_clauses = " OR ".join([f"COALESCE(p.name, t.name) LIKE '{pat}'" for pat in target_patterns])

    # 1. Tìm Main Thread ID (tid) của các process này
    sql_find_tid = f"""
    SELECT 
        COALESCE(p.name, t.name) AS proc_name,
        t.tid
    FROM process p
    JOIN thread t ON p.upid = t.upid
    WHERE t.is_main_thread = 1
      AND ({or_clauses});
    """
    
    df_procs = query_df(tp, sql_find_tid)
    
    if df_procs is None or df_procs.empty:
        return []

    results = []
    
    # 2. Lặp qua từng process và kiểm tra điều kiện > 10ms
    for _, row in df_procs.iterrows():
        proc_name = str(row['proc_name'])
        tid = int(row['tid'])
        
        # Tái sử dụng hàm tính toán state
        states = get_thread_state_summary(tp, tid, start_ts, duration)
        
        runnable = states.get("R", 0.0) + states.get("R+", 0.0)
        running = states.get("Running", 0.0)
        
        # [LOGIC MỚI] Chỉ lấy nếu tổng Running + Runnable > 10ms
        if (runnable + running) > 10000000.0:
            item = {
                "Thread name": proc_name
                # Không cần các thông số chi tiết nữa vì bảng chỉ hiện tên
            }
            results.append(item)

    return results


# ==========================Priority static =========================
def _query_end_ts_dependent_data(
    tp: TraceProcessor,
    touch_down_ts: int,
    end_ts: int,
    app_pid: int,
    app_tid: int,
    pid_mapping: Dict[int, str] = None,
    trace_path: str = None
) -> Dict[str, Any]:
    """
    Query tất cả data phụ thuộc vào end_ts.
    Helper function được gọi cho mỗi end_ts type (activityIdle, animating, startPreviewRequest).
    
    Returns:
        Dict containing: Thread State, Block I/O, CPU, Binder, Abnormal, Background data
    """
    data = {}
    
    dur_time = (end_ts - touch_down_ts) if end_ts and touch_down_ts else 0
    
    # [Thread State]
    state_summary = get_thread_state_summary(tp, app_tid, touch_down_ts, dur_time)
    data["Running"] = state_summary.get("Running", 0.0)
    data["Runnable"] = state_summary.get("R", 0.0) + state_summary.get("R+", 0.0)
    data["Uninterruptible Sleep"] = state_summary.get("D", 0.0)
    data["Sleeping"] = state_summary.get("S", 0.0)
    
    # [1] Block I/O tầng Library (App Process)
    safe_start_time = touch_down_ts if touch_down_ts else 0
    safe_end_time = end_ts if end_ts else (safe_start_time + 10_000_000_000)
    
    block_io_df = top_block_IO(tp, app_pid, safe_start_time, safe_end_time)
    library_block_io = process_block_io_data(block_io_df)

    hal_library_block_io = []
    hal_func_block_io = []
    hal_pid = get_camera_hal_pid(tp)
    
    if hal_pid:
        # Lấy Library I/O của HAL
        hal_lib_df = get_hal_library_block_io(tp, hal_pid, safe_start_time, safe_end_time)
        hal_library_block_io = process_hal_block_io_data(hal_lib_df)
        
        # Lấy Function Block I/O của HAL
        dur_time = end_ts - touch_down_ts if end_ts and touch_down_ts else 0
        hal_func_block_io = get_hal_block_io(tp, hal_pid, safe_start_time, dur_time)

    # [2] Kernel Function Block I/O (App Main Thread)
    dur_time = end_ts - touch_down_ts if end_ts and touch_down_ts else 0
    app_func_block_io = get_kernel_block_io(tp, app_pid, safe_start_time, dur_time, trace_path=trace_path)

    # [3] PHÂN TÁCH DATA CHO 2 BẢNG
    data["Block_IO_Data"] = library_block_io + hal_library_block_io
    data["Function_Block_IO_Data"] = app_func_block_io + hal_func_block_io
    
    # [LoadApkAssets Logic]
    # 1. Lấy PID chính xác của System
    sys_pids = get_system_pids(tp)
    # 2. Tạo list PID cần query (App + SS + UI)
    query_pids = [app_pid]
    if sys_pids['system_server']: query_pids.append(sys_pids['system_server'])
    if sys_pids['system_ui']: query_pids.append(sys_pids['system_ui'])
    # 3. Query
    loadapk_df = get_loadApkAsset(tp, query_pids, touch_down_ts, end_ts if end_ts else 0)
    # 4. Process & Categorize
    # Kết quả trả về dạng Dict {category: list} thay vì list phẳng
    data["LoadApkAsset_Data"] = process_loadapk_data(loadapk_df, app_pid, sys_pids)
    
    # [CPU Usage]
    cpu_cores = [0, 1, 2, 3, 4, 5, 6, 7]
    # 1. Get Top Process
    cpu_proc_df = get_top_cpu_usage_process(tp, touch_down_ts, dur_time, cpu_cores)
    data["CPU_Process_Data"] = process_cpu_data_process(cpu_proc_df, pid_mapping)
    
    # 2. Get Top Thread
    cpu_thread_df = get_top_cpu_usage_thread(tp, touch_down_ts, dur_time, cpu_cores)
    data["CPU_Thread_Data"] = process_cpu_data_thread(cpu_thread_df)
    
    # [Binder]
    binder_count, binder_dur = get_binder_transaction(tp, app_tid, end_ts if end_ts else 0)
    data["Binder_Transaction_Data"] = {
        'count': binder_count if binder_count is not None else 0,
        'duration_ms': binder_dur if binder_dur is not None else 0.0
    }
    
    # [Abnormal process]
    abnormal_start = touch_down_ts if touch_down_ts else 0
    abnormal_end = end_ts if end_ts else 0
    target_abnormal_slices = ['bindApplication']
    abnormal_df = get_abnormal_processes(tp, abnormal_start, abnormal_end, app_pid, target_abnormal_slices)
    data["Abnormal_Process_Data"] = process_abnormal_data(abnormal_df)
    
    # [Background Process States]
    bg_start_ts = touch_down_ts if touch_down_ts else 0
    bg_end_ts = end_ts if end_ts else 0
    data["Background_Process_States"] = get_background_process_states(tp, bg_start_ts, bg_end_ts)
    
    # [App Execution Time for this end_ts]
    data["App Execution Time"] = to_ms(end_ts - touch_down_ts) if end_ts and touch_down_ts else 0.0
    
    return data

# ===================== Layout depth ================================

def get_layout_depth_slices(tp: TraceProcessor, tid: int, start_ts: int, end_ts: int, max_depth: int = 6) -> Dict[int, List[str]]:
    """
    Lay danh sach cac Slice Name tren Main Thread, phan nhom theo Depth.
    """
    if not tid or not start_ts or not end_ts or start_ts >= end_ts:
        return {}

    sql = f"""
    SELECT DISTINCT s.name, s.depth
    FROM slice s
    JOIN thread_track tt ON s.track_id = tt.id
    JOIN thread t ON tt.utid = t.utid
    WHERE t.tid = {tid}
    AND s.ts + s.dur >= {start_ts} 
    AND s.ts <= {end_ts}
    AND s.depth <= {max_depth}
    ORDER BY s.depth, s.ts
    """
    
    df = query_df(tp, sql)
    
    result = {d: [] for d in range(max_depth + 1)}
    
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            depth = int(row['depth'])
            name = str(row['name'])
            
            if depth <= max_depth:
                result[depth].append(name)
                
    return result



