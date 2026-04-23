from sql_query.base import query_df
from perfetto.trace_processor.api import TraceProcessor
from typing import Dict, Optional, Any, Tuple, List
import pandas as pd

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

