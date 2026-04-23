import os
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List, Union
from collections import defaultdict
import pandas as pd
from perfetto.trace_processor import TraceProcessor
from perfetto.trace_processor.api import TraceProcessorConfig


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
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
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


