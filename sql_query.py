import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List, Union
from collections import defaultdict
import pandas as pd
from perfetto.trace_processor import TraceProcessor


# -------------------------------------------------------------------
def get_resource_path(relative_path):
    """
    Hàm lấy đường dẫn file.
    - Nếu chạy file .exe (Frozen): Lấy từ thư mục tạm sys._MEIPASS
    - Nếu chạy code .py (Dev): Lấy từ thư mục hiện tại của project
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller tạo ra thư mục tạm này
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# [File: sql_query.py]

def get_resource_path(relative_path):
    """
    Hàm lấy đường dẫn file resource chuẩn cho cả Dev, Onedir và Onefile.
    """
    # Nếu đang chạy file .exe (PyInstaller đóng gói)
    if getattr(sys, 'frozen', False):
        # Chế độ Onefile: dùng _MEIPASS
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        # Chế độ Onedir (Folder): dùng thư mục chứa file .exe
        else:
            base_path = os.path.dirname(sys.executable)
            
    # Nếu đang chạy code Python thuần (Dev mode)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(base_path, relative_path)

# -------------------------------------------------------------------
# 1. HELPER FUNCTIONS & UTILS
# -------------------------------------------------------------------

def to_ms(ns: Optional[Union[int, float]]) -> float:
    """Chuyển nanoseconds -> milliseconds (3 chữ số thập phân)."""
    if ns is None:
        return 0.0
    return round(ns / 1_000_000.0, 3)

def query_df(tp: TraceProcessor, sql: str) -> Optional[pd.DataFrame]:
    """Thực thi SQL và trả về pandas.DataFrame (hoặc None nếu rỗng/lỗi)."""
    try:
        res = tp.query(sql)
        if not res:
            return None
        df = res.as_pandas_dataframe()
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        print(f"[SQL Error] {e}")
        return None

def ensure_slice_with_names_view(tp: TraceProcessor) -> None:
    """
    Tạo view global slice_with_names.
    Nâng cấp: Thêm thread_name và pid để tiện filter ngay trong View.
    """
    sql = """
    CREATE VIEW IF NOT EXISTS slice_with_names AS
    SELECT
        s.id, s.ts, s.dur, s.name, s.track_id, s.depth,
        t.utid, t.name AS thread_name,
        th.tid, th.upid,
        p.pid, p.name AS process_name
    FROM slice s
    LEFT JOIN thread_track t ON s.track_id = t.id
    LEFT JOIN thread th      ON t.utid = th.utid
    LEFT JOIN process p      ON th.upid = p.upid;
    """
    tp.query(sql)

# -------------------------------------------------------------------
# 2. CORE GENERIC QUERY FUNCTION (HÀM TÌM KIẾM TỔNG QUÁT)
# -------------------------------------------------------------------

def find_slice(
    tp: TraceProcessor, 
    name_exact: str = None, 
    name_like: str = None, 
    upid: int = None,
    pid: int = None,
    tid: int = None,
    thread_name: str = None,
    order_by: str = 'ts',
    limit: int = 1
) -> Optional[pd.Series]:
    """
    Hàm tìm kiếm slice đa năng.
    Trả về: 1 dòng (pd.Series) đầu tiên tìm thấy hoặc None.
    """
    conditions = []
    if name_exact:
        conditions.append(f"name = '{name_exact}'")
    if name_like:
        conditions.append(f"name LIKE '{name_like}'")
    if upid is not None:
        conditions.append(f"upid = {upid}")
    if pid is not None:
        conditions.append(f"pid = {pid}")
    if tid is not None:
        conditions.append(f"tid = {tid}")
    if thread_name:
        conditions.append(f"thread_name = '{thread_name}'")

    where_clause = " AND ".join(conditions)
    if not where_clause:
        where_clause = "1=1" 

    sql = f"""
        SELECT ts, dur, (ts+dur) as end_ts, name, tid, pid, upid
        FROM slice_with_names
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT {limit};
    """
    
    df = query_df(tp, sql)
    if df is None:
        return None
    return df.iloc[0]

# -------------------------------------------------------------------
# 3. REFACTORED SIMPLE QUERIES (Sử dụng find_slice)
# -------------------------------------------------------------------

def detect_app_from_launch(tp: TraceProcessor) -> Optional[str]:
    """Tìm app package từ event 'launching:%'."""
    row = find_slice(tp, name_like='launching:%')
    if row is None:
        return None
    name = str(row['name'])
    return name.split("launching:", 1)[1].strip() if "launching:" in name else None

def find_app_process(tp: TraceProcessor) -> Optional[Tuple[int, int, str, int]]:
    """Tìm process chính của app dựa vào activityStart/Resume."""
    # Logic: Tìm process có activityStart hoặc activityResume
    sql = """
    SELECT DISTINCT upid, pid, tid, name
    FROM slice_with_names
    WHERE name IN ('activityStart', 'activityResume')
    ORDER BY ts LIMIT 1;
    """
    df = query_df(tp, sql)
    if df is None:
        return None
    r = df.iloc[0]
    # Trả về: (upid, pid, name, tid)
    return int(r['upid']), int(r['pid']), str(r['name'] or ""), int(r['tid'])

def get_first_deliver_input(tp: TraceProcessor) -> Optional[int]:
    """Lấy timestamp bắt đầu của deliverInputEvent đầu tiên."""
    row = find_slice(tp, name_like='deliverInputEvent%')
    return int(row['ts']) if row is not None else None

def get_end_deliver_input(tp: TraceProcessor, launch_pid: int):
    """Lấy (ts, end_ts) của dispatchInputEvent UP."""
    # Logic cũ: tìm dispatchInputEvent...UP
    row = find_slice(tp, name_like='dispatchInputEvent MotionEvent%UP%')
    if row is not None:
        return int(row['ts']), int(row['end_ts'])
    return None, None

def get_launcher_pid(tp: TraceProcessor) -> Optional[int]:
    """Lấy PID của Launcher process."""
    sql = """
    SELECT p.pid
    FROM process p JOIN thread t ON p.upid = t.upid
    WHERE t.is_main_thread = 1 AND t.name LIKE 'id.app.launcher%';
    """
    df = query_df(tp, sql)
    if df is None:
        return None
    return int(df.iloc[0]['pid'])

def get_activity_idle_end(tp: TraceProcessor, app_upid: int) -> Tuple[Optional[int], Optional[int]]:
    """Lấy (ts, end_ts) của activityIdle trong system_server."""
    row = find_slice(tp, name_exact='activityIdle')
    if row is not None:
        return int(row['ts']), int(row['end_ts'])
    return None, None

def get_start_proc_start(tp: TraceProcessor, app_pkg: str) -> Optional[Tuple[int, int, int]]:
    """Lấy 'Start proc: <pkg>' trong thread ActivityManager."""
    sql = """
    SELECT ts, dur
    FROM slice_with_names
    WHERE name like 'startProcess:%';
    """
    df = query_df(tp, sql)
    if df is None:
        return None # <--- SỬA: Trả về None thay vì (None, None, None)
    
    row = df.iloc[0]
    if row is not None:
        return int(row['ts']), int(row['dur']), int(row['ts']) + int(row['dur'])
    return None

def has_bind_application(tp: TraceProcessor, app_upid: int) -> bool:
    """Kiểm tra xem app có bindApplication không (Cold launch)."""
    row = find_slice(tp, name_exact='bindApplication', upid=app_upid)
    return row is not None

def get_event_ts(tp: TraceProcessor, app_upid: int, name: str) -> Optional[Tuple[int, int, int]]:
    """Lấy (ts, dur, end_ts) của event cụ thể trong app process."""
    row = find_slice(tp, name_exact=name, upid=app_upid)
    if row is not None:
        return int(row['ts']), int(row['dur']), int(row['end_ts'])
    return None

def get_choreographer(tp: TraceProcessor, tid: int, min_ts: int = 0) -> Optional[Tuple[int, int, int]]:
    """
    Lấy thông tin Choreographer đầu tiên xuất hiện sau thời điểm min_ts.
    """
    if tid is None:
        return None

    # Truy vấn trực tiếp để filter theo timestamp
    sql = f"""
    SELECT ts, dur, (ts+dur) as end_ts
    FROM slice_with_names
    WHERE name LIKE 'Choreographer#doFrame%'
      AND tid = {tid}
      AND ts >= {min_ts}
    ORDER BY ts ASC
    LIMIT 1;
    """
    
    df = query_df(tp, sql)
    if df is None:
        return None
        
    row = df.iloc[0]
    return int(row['ts']), int(row['dur']), int(row['end_ts'])

def get_launching_end(tp: TraceProcessor, app_pkg: str) -> Optional[int]:
    """Lấy end timestamp của launching:<pkg>."""
    # Thử tìm có dấu cách
    row = find_slice(tp, name_like=f'launching: {app_pkg}')
    if row is not None:
        return int(row['end_ts'])
    # Thử tìm không dấu cách (fallback)
    row_fallback = find_slice(tp, name_like=f'launching:{app_pkg}')
    return int(row_fallback['end_ts']) if row_fallback is not None else None

def get_animating(tp: TraceProcessor) -> int:
    """Lấy end time của animating (Process Track)."""
    sql = """
    SELECT s.ts + s.dur as end_ts
    FROM slice s 
    JOIN process_track pt ON s.track_id = pt.id
    WHERE pt.name = 'animating' AND s.name = 'animating'
    LIMIT 1;
    """
    df = query_df(tp, sql)
    if df is None:
        # Nếu không thấy thì raise error hoặc return 0 tuỳ logic, ở đây giữ logic cũ raise error
        raise RuntimeError("KHÔNG TÌM THẤY 'animating' - Log bị lỗi hoặc không đầy đủ!")
    return int(df.iloc[0]["end_ts"])

def get_binder_transaction(tp: TraceProcessor, app_tid: int, end_ts: int):
    """
    Tính thống kê Binder Transaction.
    Chỉ tính các transaction bắt đầu trước thời điểm end_ts (kết thúc launch).
    """
    # Nếu không có end_ts hợp lệ thì trả về 0 để tránh lỗi SQL
    if end_ts is None:
        return 0, 0.0
    sql = f"""
    SELECT COUNT(id) AS cnt, SUM(dur) / 1000000.0 AS total_ms 
    FROM slice_with_names
    WHERE name = 'binder transaction' 
      AND tid = {app_tid}
      AND ts < {end_ts};
    """
    df = query_df(tp, sql)
    if df is None:
        return 0, 0.0 
        
    row = df.iloc[0]
    return int(row['cnt']), float(row['total_ms'] or 0.0)

# -------------------------------------------------------------------
# 3.1 REACTION QUERIES
# -------------------------------------------------------------------
def get_onTransactionReady(tp: TraceProcessor) -> Optional[Tuple[int, int, int]]:
    """
    Get 'startAnimation' trong system_server.
    Return: (start_time, dur_time, end_time)
    """
    sql = f"""
    SELECT ts, dur, (ts + dur) as end_ts
    FROM slice_with_names
    WHERE name like 'AIDL%startAnimation%';
    """
    df = query_df(tp, sql)
    if df is None:
        return None, None, None
    row = df.iloc[0]
    return int(row['ts']), int(row['dur']), int(row['end_ts'])

def get_addStartingWindow(tp: TraceProcessor) -> Optional[Tuple[int, int, int]]:
    """
    Get 'addStartingWindow' trong system_server.
    Return: (start_time, dur_time, end_time)
    """
    sql = f"""
    SELECT ts, dur, (ts + dur) as end_ts
    FROM slice_with_names
    WHERE name = 'addStartingWindow';
    """
    df = query_df(tp, sql)
    if df is None:
        return None, None, None
    row = df.iloc[0]
    return int(row['ts']), int(row['dur']), int(row['end_ts'])

def get_drawFrame(tp: TraceProcessor, app_upid: int) -> Optional[Tuple[int, int, int]]:
    return None

def get_drawFrame(tp: TraceProcessor, launcher_pid: int) -> Optional[Tuple[int, int, int]]:
    """
    Get 'DrawFrame' in launcher process:
    -> Earliest DrawFrame after animator last.
    
    Return: (ts, dur, end_ts)
    """
    if not launcher_pid:
        return None

    sql = f"""
    WITH LastAnimator AS (
        -- Bước 1: Lấy timestamp của slice 'animator' cuối cùng (Process Track)
        SELECT s.ts
        FROM slice s
        JOIN process_track pt ON s.track_id = pt.id
        JOIN process p ON pt.upid = p.upid
        WHERE 
            s.name = 'animator'
            AND p.pid = {launcher_pid}
        ORDER BY s.ts DESC
        LIMIT 1
    ),
    TargetDrawFrame AS (
        -- Bước 2: Tìm DrawFrame (Thread Track) xảy ra sau Animator
        SELECT 
            s.ts, 
            s.dur
        FROM slice s
        JOIN thread_track tt ON s.track_id = tt.id
        JOIN thread t ON tt.utid = t.utid
        JOIN process p ON t.upid = p.upid
        JOIN LastAnimator la ON 1=1 -- Cross join để lấy biến 'la.ts'
        WHERE 
            s.name LIKE '%DrawFrame%' 
            AND p.pid = {launcher_pid}
            AND s.ts > la.ts 
        ORDER BY s.ts ASC 
        LIMIT 1
    )
    SELECT * FROM TargetDrawFrame;
    """

    df = query_df(tp, sql)
    if df is None:
        return None

    row = df.iloc[0]
    ts = int(row['ts'])
    dur = int(row['dur']) if pd.notna(row['dur']) else 0
    return ts, dur, ts + dur

def get_reaction_choreographer(tp: TraceProcessor, sysui_pid: int) -> Optional[Tuple[int, int, int]]:
    """
    Tìm Choreographer#doFrame trên cùng thread với addStartingWindow
    trong process SystemUI (dựa trên sysui_pid cung cấp).
    
    Logic:
    1. Tìm 'addStartingWindow' trong process SystemUI -> Lấy ts và tid.
    2. Tìm 'Choreographer#doFrame%' trên cùng tid đó và có ts >= ts của addStartingWindow.
    """
    if not sysui_pid:
        return None

    sql = f"""
    WITH TargetTrigger AS (
        -- Bước 1: Tìm addStartingWindow đầu tiên trong PID được cung cấp
        SELECT tid, ts
        FROM slice_with_names
        WHERE name = 'addStartingWindow'
        AND pid = {sysui_pid}
        ORDER BY ts ASC
        LIMIT 1
    )
    SELECT s.ts, s.dur, (s.ts + s.dur) as end_ts
    FROM slice_with_names s
    JOIN TargetTrigger t ON s.tid = t.tid -- Bắt buộc cùng Thread ID
    WHERE s.name LIKE 'Choreographer#doFrame%'
    AND s.ts >= t.ts -- Phải xảy ra sau hoặc ngay tại lúc addStartingWindow
    ORDER BY s.ts ASC
    LIMIT 1;
    """

    df = query_df(tp, sql)
    if df is None:
        return None

    row = df.iloc[0]
    return int(row['ts']), int(row['dur']), int(row['end_ts'])
# -------------------------------------------------------------------
# 4. COMPLEX QUERIES (Giữ nguyên logic phức tạp)
# -------------------------------------------------------------------

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

def top_block_IO(tp: TraceProcessor, app_pid: int, start_time: int, end_time: int):
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
    return result[:10]
# ===========================LoadApkAsset Query ==============================

def get_system_pids(tp: TraceProcessor) -> Dict[str, int]:
    """
    Lấy PID system_server và systemui.
    [FIX] Tìm qua bảng Thread vì bảng Process bị thiếu name.
    """
    pids = {'system_server': None, 'system_ui': None}
    
    # 1. Tìm System Server (Main thread name = 'system_server')
    sql_ss = """
    SELECT p.pid 
    FROM process p
    JOIN thread t ON p.upid = t.upid
    WHERE t.name = 'system_server' 
    AND t.is_main_thread = 1
    LIMIT 1;
    """
    df_ss = query_df(tp, sql_ss)
    if df_ss is not None and not df_ss.empty:
        pids['system_server'] = int(df_ss.iloc[0]['pid'])
        
    # 2. Tìm System UI (Main thread name like ...)
    sql_ui = """
    SELECT p.pid 
    FROM process p
    JOIN thread t ON p.upid = t.upid
    WHERE t.name LIKE '%ndroid.systemui%' 
    AND t.is_main_thread = 1
    LIMIT 1;
    """
    df_ui = query_df(tp, sql_ui)
    if df_ui is not None and not df_ui.empty:
        pids['system_ui'] = int(df_ui.iloc[0]['pid'])
        
    return pids

def get_loadApkAsset(tp: TraceProcessor, app_pids: List[int], start_time: int, end_time: int):
    """
    Lấy danh sách LoadApkAssets > 50ms.
    [FIX] Bỏ điều kiện lọc PID trong SQL để lấy toàn bộ dữ liệu thô (tránh sót do PID sai).
    Việc lọc sẽ thực hiện bằng Python sau.
    """
    sql = f"""
        SELECT 
            slice.name, 
            slice.dur,
            process.pid,
            thread.name as thread_name
        FROM slice 
        JOIN thread_track ON slice.track_id = thread_track.id 
        JOIN thread USING (utid) 
        JOIN process USING (upid)
        WHERE slice.name LIKE 'LoadApkAssets%' 
        AND slice.dur > 50000000 -- > 50ms (ns)
        AND slice.ts >= {start_time} 
        AND slice.ts <= {end_time}
        ORDER BY slice.ts;
    """
    return query_df(tp, sql)

def process_loadapk_data(df, app_pid: int, sys_pids: Dict[str, int]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Phân loại data LoadApkAssets vào các nhóm: system_server, system_ui, launching_app.
    """
    result = {
        'system_server': [],
        'system_ui': [],
        'launching_app': []
    }
    
    if df is None or df.empty:
        return result
        
    ss_pid = sys_pids.get('system_server')
    ui_pid = sys_pids.get('system_ui')
    
    for _, row in df.iterrows():
        try:
            pid = int(row['pid'])
        except:
            continue
            
        dur_ms = row['dur'] / 1000000.0
        item = {
            'name': str(row['name']),
            'dur_ms': dur_ms
        }
        
        # Logic phân loại (Ưu tiên PID, fallback sang Thread Name)
        matched = False
        
        if pid == app_pid:
            result['launching_app'].append(item)
            matched = True
        elif ss_pid and pid == ss_pid:
            result['system_server'].append(item)
            matched = True
        elif ui_pid and pid == ui_pid:
            result['system_ui'].append(item)
            matched = True
            
        # Fallback nếu PID mapping fail
        if not matched:
            t_name = str(row.get('thread_name', '')).lower()
            if 'system_server' in t_name:
                result['system_server'].append(item)
            elif 'systemui' in t_name:
                result['system_ui'].append(item)
            elif str(app_pid) in t_name: # Hiếm khi xảy ra
                result['launching_app'].append(item)
            
    return result
# ==============================================================
# ==============Get top CPU by Process and Thread===============
# ==============================================================
# --- 1. Query cho Process (Group by Process Name) ---
def get_top_cpu_usage_process(tp: TraceProcessor, start_time: int, dur_time: int, cpu_cores: List[int]):
    # print(f"StartTime =  {start_time}, Duration = {dur_time}")
    """
    Query top CPU usage by process. 
    [UPDATED] Trả về thêm cột 'raw_pid' để Python có thể map lại tên nếu cần.
    """
    if not cpu_cores or dur_time <= 0: return None
    cpu_cores_str = ','.join(map(str, cpu_cores))
    
    sql = f"""
    DROP VIEW IF EXISTS cpu_view_proc;
    CREATE VIEW cpu_view_proc AS
    SELECT 
        sched_slice.ts, sched_slice.dur, sched_slice.cpu,
        COALESCE(
            process.name, 
            CASE 
                WHEN main_thread.name LIKE '%binder%' OR main_thread.name LIKE '%kworker%' THEN NULL
                ELSE main_thread.name
            END, 
            'PID-' || process.pid
        ) as proc_name,
        process.pid as raw_pid  -- [QUAN TRỌNG] Cần cột này để mapping hoạt động
    FROM sched_slice 
    JOIN thread USING (utid) JOIN process USING (upid)
    LEFT JOIN thread AS main_thread ON (process.pid = main_thread.tid)
    WHERE NOT thread.name LIKE 'swapper%' ORDER BY ts ASC;
    
    DROP VIEW IF EXISTS intervals_proc;
    CREATE VIEW intervals_proc AS SELECT {start_time} AS ts, {dur_time} AS dur;
    
    DROP TABLE IF EXISTS target_proc;
    CREATE VIRTUAL TABLE target_proc USING SPAN_JOIN(intervals_proc, cpu_view_proc);
    
    SELECT 
        proc_name,
        raw_pid, -- [QUAN TRỌNG] Chọn cột raw_pid ra kết quả cuối
        SUM(dur)/1e6 AS dur_ms,
        COUNT(*) AS Occurences, 
        ROUND(SUM(dur) * 100.0 / {dur_time}*7, 2) AS dur_percent
    FROM target_proc
    WHERE cpu IN ({cpu_cores_str})
    GROUP BY COALESCE(proc_name, raw_pid)
    ORDER BY dur_ms DESC;
    """
    df = query_df(tp, sql)
    tp.query("DROP TABLE IF EXISTS target_proc; DROP VIEW IF EXISTS intervals_proc; DROP VIEW IF EXISTS cpu_view_proc;")
    return df

# [File: sql_query.py]

def process_cpu_data_process(df, pid_mapping: Dict[int, str] = None) -> List[Dict[str, Any]]:
    """
    Process CPU data.
    [UPDATED] Trả về cả sql_name và dumpstate_name để execution_sql.py tự xử lý logic matching.
    """
    if df is None or df.empty: 
        return []
    
    result = []
    for _, row in df.iterrows():
        # 1. Lấy tên gốc từ SQL (Trace)
        sql_name = str(row.get('proc_name', ''))
        if not sql_name: 
            sql_name = 'Unknown'
            
        raw_pid = row.get('raw_pid')
        
        # 2. Tìm tên từ Dumpstate (nếu có PID)
        dumpstate_name = None
        if pid_mapping and raw_pid is not None:
            try:
                pid_val = int(raw_pid)
                dumpstate_name = pid_mapping.get(pid_val)
            except (ValueError, TypeError):
                pass
        
        # 3. Trả về cấu trúc dữ liệu đầy đủ
        result.append({
            'dur_ms': float(row['dur_ms']),
            'sql_name': sql_name,           # Tên hiển thị trên Trace (VD: composer@2.4-se hoặc PID-902)
            'dumpstate_name': dumpstate_name, # Tên thật từ Bugreport (VD: android...service)
            'raw_pid': raw_pid,
            'occurences': int(row['Occurences']),
            'dur_percent': float(row['dur_percent'])
        })
    
    return result

# --- 2. Query cho Thread (Group by TID/Thread Name) ---
def get_top_cpu_usage_thread(tp: TraceProcessor, start_time: int, dur_time: int, cpu_cores: List[int]):
    if not cpu_cores or dur_time <= 0: return None
    cpu_cores_str = ','.join(map(str, cpu_cores))
    
    sql = f"""
    DROP VIEW IF EXISTS cpu_view_thread;
    CREATE VIEW cpu_view_thread AS
    SELECT 
        sched_slice.ts, sched_slice.dur, sched_slice.cpu,
        thread.tid, thread.name as thread_name,
        COALESCE(process.name, main_thread.name, 'PID-' || process.pid) as proc_name
    FROM sched_slice 
    JOIN thread USING (utid) JOIN process USING (upid)
    LEFT JOIN thread AS main_thread ON (process.pid = main_thread.tid)
    WHERE NOT thread.name LIKE 'swapper%' ORDER BY ts ASC;
    
    DROP VIEW IF EXISTS intervals_thread;
    CREATE VIEW intervals_thread AS SELECT {start_time} AS ts, {dur_time} AS dur;
    
    DROP TABLE IF EXISTS target_thread;
    CREATE VIRTUAL TABLE target_thread USING SPAN_JOIN(intervals_thread, cpu_view_thread);
    
    SELECT 
        tid, thread_name, proc_name,
        SUM(dur)/1e6 AS dur_ms,
        COUNT(*) AS Occurences, 
        ROUND(SUM(dur) * 100.0 / {dur_time}*7, 2) AS dur_percent
    FROM target_thread
    WHERE cpu IN ({cpu_cores_str})
    GROUP BY thread_name, proc_name, tid
    ORDER BY dur_ms DESC;
    """
    df = query_df(tp, sql)
    tp.query("DROP TABLE IF EXISTS target_thread; DROP VIEW IF EXISTS intervals_thread; DROP VIEW IF EXISTS cpu_view_thread;")
    return df

def process_cpu_data_thread(df) -> List[Dict[str, Any]]:
    if df is None or df.empty: return []
    return [{
        'tid': str(row['tid']),
        'dur_ms': float(row['dur_ms']),
        'thread_name': str(row['thread_name']) if row['thread_name'] else 'unknown',
        'proc_name': str(row['proc_name']) if row['proc_name'] else 'Unknown',
        'occurences': int(row['Occurences']),
        'dur_percent': float(row['dur_percent'])
    } for _, row in df.iterrows()]






def get_pid_list(tp: TraceProcessor) -> List[int]:
    """Lấy PID system_server, systemui, surfaceflinger."""
    sql = """
        SELECT p.pid
        FROM process p JOIN thread t ON p.upid = t.upid
        WHERE t.is_main_thread = 1 
          AND (t.name = 'system_server' OR t.name = 'surfaceflinger' OR t.name LIKE '%ndroid.systemui%');
    """
    df = query_df(tp, sql)
    if df is None:
        return []
    return df["pid"].tolist()

def get_pid_systemUI(tp: TraceProcessor):
    """Systemui PID"""
    sql = """
        SELECT p.pid
        FROM process p JOIN thread t ON p.upid = t.upid
        WHERE t.is_main_thread = 1 
          AND (t.name LIKE '%ndroid.systemui%');
    """
    df = query_df(tp, sql)
    if df is None:
        return []
    return df["pid"].tolist()

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
def get_priority_distribution(tp: TraceProcessor, tid: int, start_ts: int, end_ts: int) -> Dict[str, float]:
    """
    Tính thống kê Priority và Frequency.
    [FIXED] Sửa lỗi SQL truy vấn bảng Counter (tính dur tự động, lấy cpu từ track).
    """
    if not tid or not start_ts or not end_ts or start_ts >= end_ts:
        return {}
    
    duration = end_ts - start_ts
    
    # Clean up
    tp.query("DROP TABLE IF EXISTS freq_prio_span; DROP TABLE IF EXISTS sched_in_window; DROP VIEW IF EXISTS target_freq; DROP VIEW IF EXISTS target_sched; DROP VIEW IF EXISTS span_window;")

    # --- QUERY 1: Lấy Priority + Frequency ---
    # Lưu ý: Cần tính toán cột 'dur' cho bảng counter bằng hàm LEAD
    sql_full = f"""
    -- 1. Window
    CREATE VIEW span_window AS SELECT {start_ts} as ts, {duration} as dur;

    -- 2. Sched Slice
    CREATE VIEW target_sched AS 
    SELECT s.ts, s.dur, s.priority, s.cpu
    FROM sched_slice s
    JOIN thread t ON s.utid = t.utid
    WHERE t.tid = {tid};

    -- 3. Frequency (FIXED)
    -- Counter không có dur, phải tính bằng (ts kế tiếp - ts hiện tại)
    -- Counter không có cpu, phải lấy từ cpu_counter_track
    CREATE VIEW target_freq AS
    SELECT 
        c.ts, 
        LEAD(c.ts, 1, (SELECT end_ts FROM trace_bounds)) OVER (PARTITION BY c.track_id ORDER BY c.ts) - c.ts AS dur,
        CAST(c.value AS INT) as freq_val,
        t.cpu
    FROM counter c
    JOIN cpu_counter_track t ON c.track_id = t.id
    WHERE t.name LIKE '%cpufreq%'; 

    -- 4. SPAN JOIN 1: Cắt Sched theo Window
    CREATE VIRTUAL TABLE sched_in_window USING SPAN_JOIN(span_window, target_sched);
    
    -- 5. SPAN JOIN 2: Join với Freq theo CPU
    CREATE VIRTUAL TABLE freq_prio_span USING SPAN_JOIN(
        sched_in_window PARTITIONED cpu, 
        target_freq PARTITIONED cpu
    );

    SELECT priority, freq_val, SUM(dur) as total_dur
    FROM freq_prio_span 
    WHERE dur > 0
    GROUP BY priority, freq_val;
    """
    
    df = None
    try:
        df = query_df(tp, sql_full)
    except Exception as e:
        print(f"  [SQL Error Prio+Freq] {e}")
        df = None

    result = {}
    
    # Nếu thành công -> Trả về Priority + Frequency
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            prio = int(row['priority'])
            # Frequency thường là kHz, chia 1000 ra MHz
            freq_val = row['freq_val']
            freq_mhz = int(freq_val / 1000) if freq_val > 10000 else int(freq_val) # Xử lý nếu đơn vị khác lạ
            
            dur_ms = float(row['total_dur']) / 1e6
            result[f"{prio}_{freq_mhz}"] = dur_ms
        
        # Cleanup
        tp.query("DROP TABLE IF EXISTS freq_prio_span; DROP TABLE IF EXISTS sched_in_window; DROP VIEW IF EXISTS target_freq; DROP VIEW IF EXISTS target_sched; DROP VIEW IF EXISTS span_window;")
        return result

    # --- QUERY 2 (FALLBACK): Nếu lỗi hoặc không có Freq, chỉ lấy Priority ---
    # print(f"  [Fallback] No frequency data for TID {tid}, getting Priority only.")
    
    tp.query("DROP TABLE IF EXISTS freq_prio_span; DROP TABLE IF EXISTS sched_in_window; DROP VIEW IF EXISTS target_freq; DROP VIEW IF EXISTS target_sched; DROP VIEW IF EXISTS span_window;")
    
    sql_simple = f"""
    CREATE VIEW span_window AS SELECT {start_ts} as ts, {duration} as dur;
    
    CREATE VIEW target_sched AS 
    SELECT s.ts, s.dur, s.priority
    FROM sched_slice s JOIN thread t ON s.utid = t.utid
    WHERE t.tid = {tid};
    
    CREATE VIRTUAL TABLE prio_span_simple USING SPAN_JOIN(span_window, target_sched);
    
    SELECT priority, SUM(dur) as total_dur
    FROM prio_span_simple GROUP BY priority;
    """
    
    df_simple = query_df(tp, sql_simple)
    if df_simple is not None and not df_simple.empty:
        for _, row in df_simple.iterrows():
            prio = int(row['priority'])
            dur_ms = float(row['total_dur']) / 1e6
            result[f"{prio}_0"] = dur_ms # 0 = No Freq
            
    tp.query("DROP TABLE IF EXISTS prio_span_simple; DROP VIEW IF EXISTS target_sched; DROP VIEW IF EXISTS span_window;")
    
    return result
# -------------------------------------------------------------------
# ===================== Layout depth ================================
# -------------------------------------------------------------------

def get_layout_depth_slices(tp: TraceProcessor, tid: int, start_ts: int, end_ts: int, max_depth: int = 6) -> Dict[int, List[str]]:
    """
    Lấy danh sách các Slice Name trên Main Thread, phân nhóm theo Depth.
    [FIXED] Join thêm bảng thread để lọc theo tid.
    """
    if not tid or not start_ts or not end_ts or start_ts >= end_ts:
        return {}

    # Query lấy name và depth
    # Logic: slice -> thread_track -> thread (để check tid)
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
                # Có thể filter bớt các slice quá ngắn hoặc không quan trọng ở đây nếu muốn
                result[depth].append(name)
                
    return result


# -------------------------------------------------------------------
# 5. MAIN ANALYSIS LOGIC
# -------------------------------------------------------------------


def _query_end_ts_dependent_data(
    tp: TraceProcessor,
    touch_down_ts: int,
    end_ts: int,
    app_pid: int,
    app_tid: int,
    pid_mapping: Dict[int, str] = None
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
    
    # [Block I/O]
    safe_start_time = touch_down_ts if touch_down_ts else 0
    safe_end_time = end_ts if end_ts else (safe_start_time + 10_000_000_000)
    block_io_df = top_block_IO(tp, app_pid, safe_start_time, safe_end_time)
    data["Block_IO_Data"] = process_block_io_data(block_io_df)
    
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



# [File: sql_query.py]

# [File: sql_query.py]

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
            print(f"Không tìm được launching:... trong trace {trace_path}")
            raise RuntimeError(f"Không tìm được launching:... trong trace {trace_path}")
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
        print("Không tìm thấy deliverInputEvent trong trace")

    # [Animating] (Recent không có animating trong system_server)
    animating_end = 0
    if not is_recent:
        try:
            animating_end = get_animating(tp)
        except RuntimeError:
            # raise RuntimeError("Trace không hợp lệ: Không tìm thấy 'animating'")
            print("[WARN] Không tìm thấy 'animating', bỏ qua.") # SỬA: Print thay vì raise
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
                pid_mapping=pid_mapping
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
        metrics["Block_IO_Data"] = process_block_io_data(block_io_df)
        
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


    