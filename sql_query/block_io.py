from sql_query.base import query_df
from sql_query.loadapk_asset import get_pid_list, get_pid_systemUI
from perfetto.trace_processor.api import TraceProcessor
from typing import Dict, Optional, Any, Tuple, List
from collections import defaultdict
import pandas as pd
import os

def top_block_IO(tp: TraceProcessor, app_pid: int, start_time: int, end_time: int):
    # print(f"app_pid, {app_pid}, end_time, {end_time}")
    """
    Lấy danh sách library slices có Block I/O.
    - Filter slices trong khoảng start_time -> end_time.
    - Logic: Trạng thái Block I/O (D) xảy ra ngay sau khi slice thư viện BẮT ĐẦU (StartTime) 
      và khoảng cách không quá 500ns.
    - [UPDATED] Chỉ lấy slice bắt đầu bằng '1' (loại bỏ '0').
    """
    # Xử lý fallback nếu thời gian không hợp lệ
    if start_time is None: start_time = 0
    if end_time is None: end_time = 1 << 60 # Số rất lớn
    sql = f"""
        WITH 
        target_context AS (
            SELECT t.utid
            FROM thread t
            JOIN process p USING (upid)
            WHERE p.pid = {app_pid} AND t.is_main_thread = 1
            LIMIT 1
        ),
        lib_slices AS (
            SELECT 
            s.id, s.ts, s.dur, s.name, 
            tt.utid, (s.ts + s.dur) AS end_ts
            FROM slice s
            JOIN thread_track tt ON s.track_id = tt.id
            WHERE tt.utid = (SELECT utid FROM target_context)
            
            -- [UPDATED] Chỉ lấy slice bắt đầu bằng '1', bỏ '0' (odex)
            AND s.name LIKE '1%' 
            
            -- Giới hạn phạm vi tìm kiếm slice
            AND s.ts >= {start_time} 
            AND s.ts <= {end_time}
        ),
        io_states AS (
            SELECT ts, dur, utid 
            FROM thread_state
            WHERE utid = (SELECT utid FROM target_context)
            AND state = 'D'
            -- Tối ưu: Chỉ lấy state 'D' trong khoảng thời gian quan tâm
            AND ts >= {start_time}
        )
        SELECT 
        lib.name,
        io.dur,
        MIN(io.ts) AS first_io_ts
        FROM lib_slices lib
        JOIN io_states io 
        ON lib.utid = io.utid 
        -- Logic: IO xảy ra sau khi slice BẮT ĐẦU (lib.ts)
        AND io.ts >= lib.ts
        AND (io.ts - lib.ts) <= 150000 
        
        GROUP BY lib.id
        ORDER BY lib.ts;
    """
    return query_df(tp, sql)

def process_block_io_data(df) -> List[Dict[str, Any]]:
    """Xử lý DataFrame Block I/O thành list dict."""
    if df is None or df.empty:
        return []
    
    library_stats = defaultdict(lambda: {'timeTotal': 0, 'occurenceTotal': 0})
    for _, row in df.iterrows():
        name_parts = row['name'].split(' , ')
        if len(name_parts) >= 2:
            library_name = name_parts[1].strip()
            duration = int(row['dur'])
            library_stats[library_name]['timeTotal'] += duration
            library_stats[library_name]['occurenceTotal'] += 1
    
    result = []
    for lib_name, stats in library_stats.items():
        result.append({
            'libraryName': lib_name,
            'timeTotal': stats['timeTotal'],
            'timeTotal_ms': stats['timeTotal'] / 1000000.0,
            'occurenceTotal': stats['occurenceTotal']
        })
    result.sort(key=lambda x: x['timeTotal'], reverse=True)
    return result[:20]
# ===========================LoadApkAsset Query ==============================

def extract_raw_ftrace_data(trace_path: str) -> Optional[bytes]:
    """
    Trích xuất raw ftrace data từ file .log (atrace format).
    Trả về bytes của ftrace text thuần (không wrap HTML) để TraceProcessor
    có thể parse đầy đủ sched_blocked_reason events.
    
    Returns:
        bytes: Raw ftrace data, hoặc None nếu file không hợp lệ.
    """
    try:
        with open(trace_path, 'rb') as f:
            content = f.read()
        
        if not content or b'\nTRACE:' not in content:
            return None
        
        parts = content.split(b'\nTRACE:', 1)
        data = parts[1]
        
        # Decode sang text
        trace_text = data.decode('latin-1')
        
        # Strip leading whitespace
        if trace_text.startswith('\r\n'):
            trace_text = trace_text.replace('\r\n', '\n')
        elif trace_text.startswith('\r\r\n'):
            trace_text = trace_text.replace('\r\r\n', '\n')
        trace_text = trace_text[1:]  # Bỏ newline đầu
        
        # Decompress nếu cần
        if not trace_text.startswith('# tracer'):
            try:
                trace_text = zlib.decompress(trace_text.encode('latin-1')).decode('latin-1')
            except Exception:
                return None
        
        trace_text = trace_text.replace('\r', '')
        while trace_text and trace_text[0] == '\n':
            trace_text = trace_text[1:]
        
        return trace_text.encode('utf-8')
    except Exception as e:
        print(f"[extract_raw_ftrace] Error: {e}")
        return None


def get_kernel_block_io(tp: TraceProcessor, app_pid: int, start_time: int, dur_time: int,
                        trace_path: str = None) -> List[Dict[str, Any]]:
    """
    Query Block I/O từ tầng Kernel, chỉ tập trung vào Main Thread.
    
    Nếu trace_path được cung cấp, sẽ tạo TraceProcessor riêng từ raw ftrace data
    để đảm bảo sched_blocked_reason events không bị mất qua HTML conversion.
    """
    if not dur_time or dur_time <= 0:
        return []

    end_time = start_time + dur_time
    
    # SQL chỉ lấy blocked_function và duration_ms trên Main Thread
    sql = f"""
    SELECT 
        ts.blocked_function,
        SUM(MIN(ts.ts + ts.dur, {end_time}) - MAX(ts.ts, {start_time})) / 1e6 AS duration_ms
    FROM thread_state ts
    JOIN thread t USING (utid)
    JOIN process p USING (upid)
    WHERE p.pid = {app_pid}
      AND t.is_main_thread = 1
      AND ts.state = 'D'
      AND ts.blocked_function IS NOT NULL
      AND (ts.blocked_function LIKE '%io_schedule%' OR ts.blocked_function LIKE '%blk_%')
      AND ts.ts < {end_time} AND (ts.ts + ts.dur) > {start_time}
    GROUP BY ts.blocked_function;
    """
    
    # Debug: Kiểm tra blocked_function availability trên TP hiện tại
    debug_sql = "SELECT COUNT(*) as total, SUM(CASE WHEN blocked_function IS NOT NULL THEN 1 ELSE 0 END) as has_bf FROM thread_state WHERE state = 'D';"
    debug_df = query_df(tp, debug_sql)
    has_bf_in_current_tp = False
    if debug_df is not None:
        has_bf = int(debug_df.iloc[0].get('has_bf', 0) or 0)
        total = int(debug_df.iloc[0].get('total', 0) or 0)
        # print(f"[Kernel Block I/O] Current TP: D-state rows={total}, has blocked_function={has_bf}")
        has_bf_in_current_tp = has_bf > 0
    
    # Nếu TP hiện tại có blocked_function → query trực tiếp (nhanh hơn)
    if has_bf_in_current_tp:
        df = query_df(tp, sql)
    elif trace_path:
        # TP hiện tại KHÔNG có blocked_function → tạo TP mới từ raw ftrace
        # print(f"[Kernel Block I/O] blocked_function missing in current TP, loading raw ftrace from: {Path(trace_path).name}")
        df = _query_kernel_bio_from_raw(trace_path, sql)
    else:
        # print(f"[Kernel Block I/O] No blocked_function data and no trace_path provided, skipping.")
        return []
    
    if df is None or df.empty:
        return []
        
    # Chuyển đổi format sang giống với format của Library Block I/O để dễ merge
    results = []
    for _, row in df.iterrows():
        results.append({
            'libraryName': f"[Kernel] {row['blocked_function']}",
            'timeTotal_ms': float(row['duration_ms']),
            'occurenceTotal': 0
        })
    return results


def _query_kernel_bio_from_raw(trace_path: str, sql: str) -> Optional[pd.DataFrame]:
    """
    Tạo TraceProcessor tạm từ raw ftrace data và chạy SQL query.
    Đây là workaround cho việc HTML systrace conversion làm mất sched_blocked_reason.
    """
    raw_data = extract_raw_ftrace_data(trace_path)
    if raw_data is None:
        print(f"[Kernel Block I/O] Cannot extract raw ftrace from {trace_path}")
        return None
    
    tmp_file = None
    try:
        # Ghi raw ftrace vào file tạm
        tmp_file = tempfile.NamedTemporaryFile(suffix='.systrace', delete=False, mode='wb')
        tmp_file.write(raw_data)
        tmp_file.close()
        
        # Tạo TP mới từ raw data
        tp_bin = get_resource_path(os.path.join("perfetto", "trace_processor.exe"))
        config = TraceProcessorConfig(bin_path=tp_bin)
        
        with TraceProcessor(trace=tmp_file.name, config=config) as tp_raw:
            # Verify blocked_function exists
            verify_sql = "SELECT COUNT(*) as cnt FROM thread_state WHERE blocked_function IS NOT NULL;"
            verify_df = query_df(tp_raw, verify_sql)
            if verify_df is not None:
                cnt = int(verify_df.iloc[0]['cnt'] or 0)
                print(f"[Kernel Block I/O] Raw TP: {cnt} rows with blocked_function")
            
            return query_df(tp_raw, sql)
    except Exception as e:
        print(f"[Kernel Block I/O] Error querying raw trace: {e}")
        return None
    finally:
        # Cleanup file tạm
        if tmp_file and os.path.exists(tmp_file.name):
            try:
                os.unlink(tmp_file.name)
            except Exception:
                pass

# -------------------------------------------------------------------
# ===================== Camera HAL Block IO ================================
# -------------------------------------------------------------------

def get_camera_hal_pid(tp: TraceProcessor) -> Optional[int]:
    """
    Tìm PID của tiến trình Camera HAL dựa trên slice đặc trưng.
    """
    sql = """
    SELECT pid
    FROM slice_with_names
    WHERE name LIKE '%camera3->process_capture_request%'
    LIMIT 1;
    """
    df = query_df(tp, sql)
    if df is not None and not df.empty:
        return int(df.iloc[0]['pid'])
    return None

def get_hal_library_block_io(tp: TraceProcessor, hal_pid: int, start_time: int, end_time: int):
    """
    Lấy danh sách library slices có Block I/O cho tiến trình HAL.
    Quét trên TOÀN BỘ luồng (threads) của HAL thay vì chỉ Main Thread.
    """
    if start_time is None: start_time = 0
    if end_time is None: end_time = 1 << 60
    sql = f"""
        WITH 
        target_context AS (
            SELECT t.utid
            FROM thread t
            JOIN process p USING (upid)
            WHERE p.pid = {hal_pid}
            -- Bỏ điều kiện t.is_main_thread = 1 và LIMIT 1 để lấy tất cả worker threads của HAL
        ),
        lib_slices AS (
            SELECT 
            s.id, s.ts, s.dur, s.name, 
            tt.utid, (s.ts + s.dur) AS end_ts
            FROM slice s
            JOIN thread_track tt ON s.track_id = tt.id
            WHERE tt.utid IN (SELECT utid FROM target_context)
            AND s.name LIKE '1%' 
            AND s.ts >= {start_time} 
            AND s.ts <= {end_time}
        ),
        io_states AS (
            SELECT ts, dur, utid 
            FROM thread_state
            WHERE utid IN (SELECT utid FROM target_context)
            AND state = 'D'
            AND ts >= {start_time}
        )
        SELECT 
        lib.name,
        io.dur,
        MIN(io.ts) AS first_io_ts
        FROM lib_slices lib
        JOIN io_states io 
        ON lib.utid = io.utid 
        AND io.ts >= lib.ts
        AND (io.ts - lib.ts) <= 150000 
        GROUP BY lib.id
        ORDER BY lib.ts;
    """
    return query_df(tp, sql)

def process_hal_block_io_data(df) -> List[Dict[str, Any]]:
    """Xử lý DataFrame Library Block I/O của HAL thành list dict."""
    if df is None or df.empty:
        return []
    
    library_stats = defaultdict(lambda: {'timeTotal': 0, 'occurenceTotal': 0})
    for _, row in df.iterrows():
        name_parts = row['name'].split(' , ')
        if len(name_parts) >= 2:
            library_name = name_parts[1].strip()
            duration = int(row['dur'])
            library_stats[library_name]['timeTotal'] += duration
            library_stats[library_name]['occurenceTotal'] += 1
    
    result = []
    for lib_name, stats in library_stats.items():
        result.append({
            'libraryName': f"[HAL] {lib_name}", # Thêm prefix [HAL]
            'timeTotal': stats['timeTotal'],
            'timeTotal_ms': stats['timeTotal'] / 1000000.0,
            'occurenceTotal': stats['occurenceTotal']
        })
    result.sort(key=lambda x: x['timeTotal'], reverse=True)
    return result
# -------------------------------------------------------------------
# 5. MAIN ANALYSIS LOGIC
# -------------------------------------------------------------------


