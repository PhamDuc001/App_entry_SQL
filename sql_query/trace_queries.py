"""
Trace-specific query functions for app launch analysis.
These functions query specific trace events (slices) from Perfetto.
"""
from sql_query.base import query_df, find_slice
from perfetto.trace_processor.api import TraceProcessor
from typing import Dict, Optional, Any, Tuple, List
import pandas as pd


def detect_app_from_launch(tp: TraceProcessor) -> Optional[str]:
    """Tim app package tu event 'launching:%'."""
    row = find_slice(tp, name_like='launching:%')
    if row is None:
        return None
    name = str(row['name'])
    return name.split("launching:", 1)[1].strip() if "launching:" in name else None

def find_app_process(tp: TraceProcessor) -> Optional[Tuple[int, int, str, int]]:
    """Tim process chinh cua app dua vao activityStart/Resume."""
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
    return int(r['upid']), int(r['pid']), str(r['name'] or ""), int(r['tid'])

def get_first_deliver_input(tp: TraceProcessor) -> Optional[int]:
    """Lay timestamp bat dau cua deliverInputEvent dau tien."""
    row = find_slice(tp, name_like='deliverInputEvent%')
    return int(row['ts']) if row is not None else None

def get_end_deliver_input(tp: TraceProcessor, launch_pid: int):
    """Lay (ts, end_ts) cua dispatchInputEvent UP."""
    row = find_slice(tp, name_like='dispatchInputEvent MotionEvent%UP%')
    if row is not None:
        return int(row['ts']), int(row['end_ts'])
    return None, None

def get_launcher_pid(tp: TraceProcessor) -> Optional[int]:
    """Lay PID cua Launcher process."""
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
    """Lay (ts, end_ts) cua activityIdle trong system_server."""
    row = find_slice(tp, name_exact='activityIdle')
    if row is not None:
        return int(row['ts']), int(row['end_ts'])
    return None, None

def get_start_proc_start(tp: TraceProcessor, app_pkg: str) -> Optional[Tuple[int, int, int]]:
    """Lay 'Start proc: <pkg>' trong thread ActivityManager."""
    sql = """
    SELECT ts, dur
    FROM slice_with_names
    WHERE name like 'startProcess:%';
    """
    df = query_df(tp, sql)
    if df is None:
        return None
    
    row = df.iloc[0]
    if row is not None:
        return int(row['ts']), int(row['dur']), int(row['ts']) + int(row['dur'])
    return None

def has_bind_application(tp: TraceProcessor, app_upid: int) -> bool:
    """Kiem tra xem app co bindApplication khong (Cold launch)."""
    row = find_slice(tp, name_exact='bindApplication', upid=app_upid)
    return row is not None

def get_event_ts(tp: TraceProcessor, app_upid: int, name: str) -> Optional[Tuple[int, int, int]]:
    """Lay (ts, dur, end_ts) cua event cu the trong app process."""
    row = find_slice(tp, name_exact=name, upid=app_upid)
    if row is not None:
        return int(row['ts']), int(row['dur']), int(row['end_ts'])
    return None

def get_choreographer(tp: TraceProcessor, tid: int, min_ts: int = 0) -> Optional[Tuple[int, int, int]]:
    """
    Lay thong tin Choreographer dau tien xuat hien sau thoi diem min_ts.
    """
    if tid is None:
        return None

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
    """Lay end timestamp cua launching:<pkg>."""
    row = find_slice(tp, name_like=f'launching: {app_pkg}')
    if row is not None:
        return int(row['end_ts'])
    row_fallback = find_slice(tp, name_like=f'launching:{app_pkg}')
    return int(row_fallback['end_ts']) if row_fallback is not None else None

def get_animating(tp: TraceProcessor) -> int:
    """Lay end time cua animating (Process Track)."""
    sql = """
    SELECT s.ts + s.dur as end_ts
    FROM slice s 
    JOIN process_track pt ON s.track_id = pt.id
    WHERE pt.name = 'animating' AND s.name = 'animating'
    LIMIT 1;
    """
    df = query_df(tp, sql)
    if df is None:
        raise RuntimeError("KHONG TIM THAY 'animating' - Log bi loi hoac khong day du!")
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
        SELECT 
            s.ts, 
            s.dur
        FROM slice s
        JOIN thread_track tt ON s.track_id = tt.id
        JOIN thread t ON tt.utid = t.utid
        JOIN process p ON t.upid = p.upid
        JOIN LastAnimator la ON 1=1
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
    Tim Choreographer#doFrame tren cung thread voi addStartingWindow
    trong process SystemUI (dua tren sysui_pid cung cap).
    """
    if not sysui_pid:
        return None

    sql = f"""
    WITH TargetTrigger AS (
        SELECT tid, ts
        FROM slice_with_names
        WHERE name = 'addStartingWindow'
        AND pid = {sysui_pid}
        ORDER BY ts ASC
        LIMIT 1
    )
    SELECT s.ts, s.dur, (s.ts + s.dur) as end_ts
    FROM slice_with_names s
    JOIN TargetTrigger t ON s.tid = t.tid
    WHERE s.name LIKE 'Choreographer#doFrame%'
    AND s.ts >= t.ts
    ORDER BY s.ts ASC
    LIMIT 1;
    """

    df = query_df(tp, sql)
    if df is None:
        return None

    row = df.iloc[0]
    return int(row['ts']), int(row['dur']), int(row['end_ts'])