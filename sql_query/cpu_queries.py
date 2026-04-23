from sql_query.base import query_df, to_ms
from perfetto.trace_processor.api import TraceProcessor
from typing import Dict, Optional, Any, Tuple, List
from collections import defaultdict
import pandas as pd

# ==============================================================
# ==============Get top CPU by Process and Thread===============
# ==============================================================
# --- 1. Query cho Process (Group by Process Name) ---

# --- 1. Query cho Process (Group by PID/Process Name) ---
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

# --- 3. Query cho CPU Core ---
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

