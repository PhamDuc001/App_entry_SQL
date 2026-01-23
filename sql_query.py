# import os
# import sys
# from pathlib import Path
# from typing import Dict, Optional, Any, Tuple, List, Union
# from collections import defaultdict
# import pandas as pd
# from perfetto.trace_processor import TraceProcessor


# # -------------------------------------------------------------------
# def get_resource_path(relative_path):
#     """
#     Hàm lấy đường dẫn file.
#     - Nếu chạy file .exe (Frozen): Lấy từ thư mục tạm sys._MEIPASS
#     - Nếu chạy code .py (Dev): Lấy từ thư mục hiện tại của project
#     """
#     if hasattr(sys, '_MEIPASS'):
#         # PyInstaller tạo ra thư mục tạm này
#         return os.path.join(sys._MEIPASS, relative_path)
#     return os.path.join(os.path.abspath("."), relative_path)

# # [File: sql_query.py]

# def get_resource_path(relative_path):
#     """
#     Hàm lấy đường dẫn file resource chuẩn cho cả Dev, Onedir và Onefile.
#     """
#     # Nếu đang chạy file .exe (PyInstaller đóng gói)
#     if getattr(sys, 'frozen', False):
#         # Chế độ Onefile: dùng _MEIPASS
#         if hasattr(sys, '_MEIPASS'):
#             base_path = sys._MEIPASS
#         # Chế độ Onedir (Folder): dùng thư mục chứa file .exe
#         else:
#             base_path = os.path.dirname(sys.executable)
            
#     # Nếu đang chạy code Python thuần (Dev mode)
#     else:
#         base_path = os.path.dirname(os.path.abspath(__file__))
        
#     return os.path.join(base_path, relative_path)

# # -------------------------------------------------------------------
# # 1. HELPER FUNCTIONS & UTILS
# # -------------------------------------------------------------------

# def to_ms(ns: Optional[Union[int, float]]) -> float:
#     """Chuyển nanoseconds -> milliseconds (3 chữ số thập phân)."""
#     if ns is None:
#         return 0.0
#     return round(ns / 1_000_000.0, 3)

# def query_df(tp: TraceProcessor, sql: str) -> Optional[pd.DataFrame]:
#     """Thực thi SQL và trả về pandas.DataFrame (hoặc None nếu rỗng/lỗi)."""
#     try:
#         res = tp.query(sql)
#         if not res:
#             return None
#         df = res.as_pandas_dataframe()
#         if df is None or df.empty:
#             return None
#         return df
#     except Exception as e:
#         print(f"[SQL Error] {e}")
#         return None

# def ensure_slice_with_names_view(tp: TraceProcessor) -> None:
#     """
#     Tạo view global slice_with_names.
#     Nâng cấp: Thêm thread_name và pid để tiện filter ngay trong View.
#     """
#     sql = """
#     CREATE VIEW IF NOT EXISTS slice_with_names AS
#     SELECT
#         s.id, s.ts, s.dur, s.name, s.track_id, s.depth,
#         t.utid, t.name AS thread_name,
#         th.tid, th.upid,
#         p.pid, p.name AS process_name
#     FROM slice s
#     LEFT JOIN thread_track t ON s.track_id = t.id
#     LEFT JOIN thread th      ON t.utid = th.utid
#     LEFT JOIN process p      ON th.upid = p.upid;
#     """
#     tp.query(sql)

# # -------------------------------------------------------------------
# # 2. CORE GENERIC QUERY FUNCTION (HÀM TÌM KIẾM TỔNG QUÁT)
# # -------------------------------------------------------------------

# def find_slice(
#     tp: TraceProcessor, 
#     name_exact: str = None, 
#     name_like: str = None, 
#     upid: int = None,
#     pid: int = None,
#     tid: int = None,
#     thread_name: str = None,
#     order_by: str = 'ts',
#     limit: int = 1
# ) -> Optional[pd.Series]:
#     """
#     Hàm tìm kiếm slice đa năng.
#     Trả về: 1 dòng (pd.Series) đầu tiên tìm thấy hoặc None.
#     """
#     conditions = []
#     if name_exact:
#         conditions.append(f"name = '{name_exact}'")
#     if name_like:
#         conditions.append(f"name LIKE '{name_like}'")
#     if upid is not None:
#         conditions.append(f"upid = {upid}")
#     if pid is not None:
#         conditions.append(f"pid = {pid}")
#     if tid is not None:
#         conditions.append(f"tid = {tid}")
#     if thread_name:
#         conditions.append(f"thread_name = '{thread_name}'")

#     where_clause = " AND ".join(conditions)
#     if not where_clause:
#         where_clause = "1=1" 

#     sql = f"""
#         SELECT ts, dur, (ts+dur) as end_ts, name, tid, pid, upid
#         FROM slice_with_names
#         WHERE {where_clause}
#         ORDER BY {order_by}
#         LIMIT {limit};
#     """
    
#     df = query_df(tp, sql)
#     if df is None:
#         return None
#     return df.iloc[0]

# # -------------------------------------------------------------------
# # 3. REFACTORED SIMPLE QUERIES (Sử dụng find_slice)
# # -------------------------------------------------------------------

# def detect_app_from_launch(tp: TraceProcessor) -> Optional[str]:
#     """Tìm app package từ event 'launching:%'."""
#     row = find_slice(tp, name_like='launching:%')
#     if row is None:
#         return None
#     name = str(row['name'])
#     return name.split("launching:", 1)[1].strip() if "launching:" in name else None

# def find_app_process(tp: TraceProcessor, app_pkg: str) -> Optional[Tuple[int, int, str, int]]:
#     """Tìm process chính của app dựa vào activityStart/Resume."""
#     # Logic: Tìm process có activityStart hoặc activityResume
#     sql = """
#     SELECT DISTINCT upid, pid, tid, name
#     FROM slice_with_names
#     WHERE name IN ('activityStart', 'activityResume')
#     ORDER BY ts LIMIT 1;
#     """
#     df = query_df(tp, sql)
#     if df is None:
#         return None
#     r = df.iloc[0]
#     # Trả về: (upid, pid, name, tid)
#     return int(r['upid']), int(r['pid']), str(r['name'] or ""), int(r['tid'])

# def get_first_deliver_input(tp: TraceProcessor) -> Optional[int]:
#     """Lấy timestamp bắt đầu của deliverInputEvent đầu tiên."""
#     row = find_slice(tp, name_like='deliverInputEvent%')
#     return int(row['ts']) if row is not None else None

# def get_end_deliver_input(tp: TraceProcessor, launch_pid: int):
#     """Lấy (ts, end_ts) của dispatchInputEvent UP."""
#     # Logic cũ: tìm dispatchInputEvent...UP
#     row = find_slice(tp, name_like='dispatchInputEvent MotionEvent%UP%')
#     if row is not None:
#         return int(row['ts']), int(row['end_ts'])
#     return None, None

# def get_launcher_pid(tp: TraceProcessor) -> Optional[int]:
#     """Lấy PID của Launcher process."""
#     sql = """
#     SELECT p.pid
#     FROM process p JOIN thread t ON p.upid = t.upid
#     WHERE t.is_main_thread = 1 AND t.name LIKE 'id.app.launcher%';
#     """
#     df = query_df(tp, sql)
#     if df is None:
#         return None
#     return int(df.iloc[0]['pid'])

# def get_activity_idle_end(tp: TraceProcessor, app_upid: int) -> Tuple[Optional[int], Optional[int]]:
#     """Lấy (ts, end_ts) của activityIdle trong system_server."""
#     row = find_slice(tp, name_exact='activityIdle')
#     if row is not None:
#         return int(row['ts']), int(row['end_ts'])
#     return None, None

# def get_start_proc_start(tp: TraceProcessor, app_pkg: str) -> Optional[Tuple[int, int, int]]:
#     """Lấy 'Start proc: <pkg>' trong thread ActivityManager."""
#     sql = """
#     SELECT ts, dur
#     FROM slice_with_names
#     WHERE name like 'startProcess:%';
#     """
#     df = query_df(tp, sql)
#     if df is None:
#         return None # <--- SỬA: Trả về None thay vì (None, None, None)
    
#     row = df.iloc[0]
#     if row is not None:
#         return int(row['ts']), int(row['dur']), int(row['ts']) + int(row['dur'])
#     return None

# def has_bind_application(tp: TraceProcessor, app_upid: int) -> bool:
#     """Kiểm tra xem app có bindApplication không (Cold launch)."""
#     row = find_slice(tp, name_exact='bindApplication', upid=app_upid)
#     return row is not None

# def get_event_ts(tp: TraceProcessor, app_upid: int, name: str) -> Optional[Tuple[int, int, int]]:
#     """Lấy (ts, dur, end_ts) của event cụ thể trong app process."""
#     row = find_slice(tp, name_exact=name, upid=app_upid)
#     if row is not None:
#         return int(row['ts']), int(row['dur']), int(row['end_ts'])
#     return None

# def get_choreographer(tp: TraceProcessor, tid: int, min_ts: int = 0) -> Optional[Tuple[int, int, int]]:
#     """
#     Lấy thông tin Choreographer đầu tiên xuất hiện sau thời điểm min_ts.
#     """
#     if tid is None:
#         return None

#     # Truy vấn trực tiếp để filter theo timestamp
#     sql = f"""
#     SELECT ts, dur, (ts+dur) as end_ts
#     FROM slice_with_names
#     WHERE name LIKE 'Choreographer#doFrame%'
#       AND tid = {tid}
#       AND ts >= {min_ts}
#     ORDER BY ts ASC
#     LIMIT 1;
#     """
    
#     df = query_df(tp, sql)
#     if df is None:
#         return None
        
#     row = df.iloc[0]
#     return int(row['ts']), int(row['dur']), int(row['end_ts'])

# def get_launching_end(tp: TraceProcessor, app_pkg: str) -> Optional[int]:
#     """Lấy end timestamp của launching:<pkg>."""
#     # Thử tìm có dấu cách
#     row = find_slice(tp, name_like=f'launching: {app_pkg}')
#     if row is not None:
#         return int(row['end_ts'])
#     # Thử tìm không dấu cách (fallback)
#     row_fallback = find_slice(tp, name_like=f'launching:{app_pkg}')
#     return int(row_fallback['end_ts']) if row_fallback is not None else None

# def get_animating(tp: TraceProcessor) -> int:
#     """Lấy end time của animating (Process Track)."""
#     sql = """
#     SELECT s.ts + s.dur as end_ts
#     FROM slice s 
#     JOIN process_track pt ON s.track_id = pt.id
#     WHERE pt.name = 'animating' AND s.name = 'animating'
#     LIMIT 1;
#     """
#     df = query_df(tp, sql)
#     if df is None:
#         # Nếu không thấy thì raise error hoặc return 0 tuỳ logic, ở đây giữ logic cũ raise error
#         raise RuntimeError("KHÔNG TÌM THẤY 'animating' - Log bị lỗi hoặc không đầy đủ!")
#     return int(df.iloc[0]["end_ts"])

# def get_binder_transaction(tp: TraceProcessor, app_tid: int, end_ts: int):
#     """
#     Tính thống kê Binder Transaction.
#     Chỉ tính các transaction bắt đầu trước thời điểm end_ts (kết thúc launch).
#     """
#     # Nếu không có end_ts hợp lệ thì trả về 0 để tránh lỗi SQL
#     if end_ts is None:
#         return 0, 0.0
#     sql = f"""
#     SELECT COUNT(id) AS cnt, SUM(dur) / 1000000.0 AS total_ms 
#     FROM slice_with_names
#     WHERE name = 'binder transaction' 
#       AND tid = {app_tid}
#       AND ts < {end_ts};
#     """
#     df = query_df(tp, sql)
#     if df is None:
#         return 0, 0.0 
        
#     row = df.iloc[0]
#     return int(row['cnt']), float(row['total_ms'] or 0.0)

# # -------------------------------------------------------------------
# # 3.1 REACTION QUERIES
# # -------------------------------------------------------------------
# def get_onTransactionReady(tp: TraceProcessor) -> Optional[Tuple[int, int, int]]:
#     """
#     Get 'onTransactionReady' trong system_server.
#     Return: (start_time, dur_time, end_time)
#     """
#     sql = f"""
#     SELECT ts, dur, (ts + dur) as end_ts
#     FROM slice_with_names
#     WHERE name = 'onTransactionReady';
#     """
#     df = query_df(tp, sql)
#     if df is None:
#         return None, None, None
#     row = df.iloc[0]
#     return int(row['ts']), int(row['dur']), int(row['end_ts'])

# def get_addStartingWindow(tp: TraceProcessor) -> Optional[Tuple[int, int, int]]:
#     """
#     Get 'addStartingWindow' trong system_server.
#     Return: (start_time, dur_time, end_time)
#     """
#     sql = f"""
#     SELECT ts, dur, (ts + dur) as end_ts
#     FROM slice_with_names
#     WHERE name = 'addStartingWindow';
#     """
#     df = query_df(tp, sql)
#     if df is None:
#         return None, None, None
#     row = df.iloc[0]
#     return int(row['ts']), int(row['dur']), int(row['end_ts'])

# def get_drawFrame(tp: TraceProcessor, app_upid: int) -> Optional[Tuple[int, int, int]]:
#     return None

# def get_drawFrame(tp: TraceProcessor, launcher_pid: int) -> Optional[Tuple[int, int, int]]:
#     """
#     Get 'DrawFrame' in launcher process:
#     -> Earliest DrawFrame after animator last.
    
#     Return: (ts, dur, end_ts)
#     """
#     if not launcher_pid:
#         return None

#     sql = f"""
#     WITH LastAnimator AS (
#         -- Bước 1: Lấy timestamp của slice 'animator' cuối cùng (Process Track)
#         SELECT s.ts
#         FROM slice s
#         JOIN process_track pt ON s.track_id = pt.id
#         JOIN process p ON pt.upid = p.upid
#         WHERE 
#             s.name = 'animator'
#             AND p.pid = {launcher_pid}
#         ORDER BY s.ts DESC
#         LIMIT 1
#     ),
#     TargetDrawFrame AS (
#         -- Bước 2: Tìm DrawFrame (Thread Track) xảy ra sau Animator
#         SELECT 
#             s.ts, 
#             s.dur
#         FROM slice s
#         JOIN thread_track tt ON s.track_id = tt.id
#         JOIN thread t ON tt.utid = t.utid
#         JOIN process p ON t.upid = p.upid
#         JOIN LastAnimator la ON 1=1 -- Cross join để lấy biến 'la.ts'
#         WHERE 
#             s.name LIKE '%DrawFrame%' 
#             AND p.pid = {launcher_pid}
#             AND s.ts > la.ts 
#         ORDER BY s.ts ASC 
#         LIMIT 1
#     )
#     SELECT * FROM TargetDrawFrame;
#     """

#     df = query_df(tp, sql)
#     if df is None:
#         return None

#     row = df.iloc[0]
#     ts = int(row['ts'])
#     dur = int(row['dur']) if pd.notna(row['dur']) else 0
#     return ts, dur, ts + dur

# def get_reaction_choreographer(tp: TraceProcessor, sysui_pid: int) -> Optional[Tuple[int, int, int]]:
#     """
#     Tìm Choreographer#doFrame trên cùng thread với addStartingWindow
#     trong process SystemUI (dựa trên sysui_pid cung cấp).
    
#     Logic:
#     1. Tìm 'addStartingWindow' trong process SystemUI -> Lấy ts và tid.
#     2. Tìm 'Choreographer#doFrame%' trên cùng tid đó và có ts >= ts của addStartingWindow.
#     """
#     if not sysui_pid:
#         return None

#     sql = f"""
#     WITH TargetTrigger AS (
#         -- Bước 1: Tìm addStartingWindow đầu tiên trong PID được cung cấp
#         SELECT tid, ts
#         FROM slice_with_names
#         WHERE name = 'addStartingWindow'
#         AND pid = {sysui_pid}
#         ORDER BY ts ASC
#         LIMIT 1
#     )
#     SELECT s.ts, s.dur, (s.ts + s.dur) as end_ts
#     FROM slice_with_names s
#     JOIN TargetTrigger t ON s.tid = t.tid -- Bắt buộc cùng Thread ID
#     WHERE s.name LIKE 'Choreographer#doFrame%'
#     AND s.ts >= t.ts -- Phải xảy ra sau hoặc ngay tại lúc addStartingWindow
#     ORDER BY s.ts ASC
#     LIMIT 1;
#     """

#     df = query_df(tp, sql)
#     if df is None:
#         return None

#     row = df.iloc[0]
#     return int(row['ts']), int(row['dur']), int(row['end_ts'])
# # -------------------------------------------------------------------
# # 4. COMPLEX QUERIES (Giữ nguyên logic phức tạp)
# # -------------------------------------------------------------------

# def get_thread_state_summary(tp: TraceProcessor, app_tid: int,
#                              ts_start: int, ts_dur: int) -> Dict[str, float]:
#     """
#     Tổng thời gian các state (Running, R, S, D...) của một thread.
#     Sử dụng SPAN_JOIN giữa intervals và thread_state.
#     """
#     if ts_dur <= 0:
#         return {}

#     # 1. View state_view
#     sql = f"""
#     DROP VIEW IF EXISTS state_view;
#     CREATE VIEW state_view AS
#     SELECT
#         thread_state.state,
#         thread_state.ts,
#         thread_state.dur
#     FROM thread_state
#     JOIN thread USING (utid)
#     WHERE thread.tid = {app_tid};
#     """
#     tp.query(sql)

#     # 2. View intervals
#     sql = f"""
#     DROP VIEW IF EXISTS intervals;
#     CREATE VIEW intervals AS
#     SELECT {ts_start} AS ts, {ts_dur} AS dur;
#     """
#     tp.query(sql)

#     # 3. Span join
#     sql = """
#     DROP TABLE IF EXISTS target_view;
#     CREATE VIRTUAL TABLE target_view
#     USING span_join (intervals, state_view);
#     """
#     tp.query(sql)

#     # 4. Aggregate
#     sql = """
#     SELECT
#         state,
#         SUM(dur) / 1e6 AS total_duration_ms
#     FROM target_view
#     GROUP BY state
#     ORDER BY total_duration_ms DESC;
#     """
#     df = query_df(tp, sql)

#     # 5. Cleanup
#     tp.query("DROP TABLE IF EXISTS target_view;")
#     tp.query("DROP VIEW  IF EXISTS intervals;")
#     tp.query("DROP VIEW  IF EXISTS state_view;")

#     if df is None:
#         return {}

#     result: Dict[str, float] = {}
#     for _, row in df.iterrows():
#         state = str(row["state"])
#         try:
#             total_ms = float(row["total_duration_ms"])
#         except (TypeError, ValueError):
#             continue
#         result[state] = total_ms

#     return result

# # [File: sql_query.py]

# def top_block_IO(tp: TraceProcessor, app_pid: int, start_time: int, end_time: int):
#     """
#     Lấy danh sách library slices có Block I/O.
#     - Filter slices trong khoảng start_time -> end_time.
#     - Logic: Trạng thái Block I/O (D) xảy ra ngay sau khi slice thư viện BẮT ĐẦU (StartTime) 
#       và khoảng cách không quá 500ns.
#     - [UPDATED] Chỉ lấy slice bắt đầu bằng '1' (loại bỏ '0').
#     """
#     # Xử lý fallback nếu thời gian không hợp lệ
#     if start_time is None: start_time = 0
#     if end_time is None: end_time = 1 << 60 # Số rất lớn

#     sql = f"""
#         WITH 
#         target_context AS (
#             SELECT t.utid
#             FROM thread t
#             JOIN process p USING (upid)
#             WHERE p.pid = {app_pid} AND t.is_main_thread = 1
#             LIMIT 1
#         ),
#         lib_slices AS (
#             SELECT 
#             s.id, s.ts, s.dur, s.name, 
#             tt.utid, (s.ts + s.dur) AS end_ts
#             FROM slice s
#             JOIN thread_track tt ON s.track_id = tt.id
#             WHERE tt.utid = (SELECT utid FROM target_context)
            
#             -- [UPDATED] Chỉ lấy slice bắt đầu bằng '1', bỏ '0' (odex)
#             AND s.name LIKE '1%' 
            
#             -- Giới hạn phạm vi tìm kiếm slice
#             AND s.ts >= {start_time} 
#             AND s.ts <= {end_time}
#         ),
#         io_states AS (
#             SELECT ts, dur, utid 
#             FROM thread_state
#             WHERE utid = (SELECT utid FROM target_context)
#             AND state = 'D'
#             -- Tối ưu: Chỉ lấy state 'D' trong khoảng thời gian quan tâm
#             AND ts >= {start_time}
#         )
#         SELECT 
#         lib.name,
#         io.dur,
#         MIN(io.ts) AS first_io_ts
#         FROM lib_slices lib
#         JOIN io_states io 
#         ON lib.utid = io.utid 
#         -- Logic: IO xảy ra sau khi slice BẮT ĐẦU (lib.ts)
#         AND io.ts >= lib.ts
#         AND (io.ts - lib.ts) <= 150000 
        
#         GROUP BY lib.id
#         ORDER BY lib.ts;
#     """
#     return query_df(tp, sql)

# def process_block_io_data(df) -> List[Dict[str, Any]]:
#     """Xử lý DataFrame Block I/O thành list dict."""
#     if df is None or df.empty:
#         return []
    
#     library_stats = defaultdict(lambda: {'timeTotal': 0, 'occurenceTotal': 0})
#     for _, row in df.iterrows():
#         name_parts = row['name'].split(' , ')
#         if len(name_parts) >= 2:
#             library_name = name_parts[1].strip()
#             duration = int(row['dur'])
#             library_stats[library_name]['timeTotal'] += duration
#             library_stats[library_name]['occurenceTotal'] += 1
    
#     result = []
#     for lib_name, stats in library_stats.items():
#         result.append({
#             'libraryName': lib_name,
#             'timeTotal': stats['timeTotal'],
#             'timeTotal_ms': stats['timeTotal'] / 1000000.0,
#             'occurenceTotal': stats['occurenceTotal']
#         })
#     result.sort(key=lambda x: x['timeTotal'], reverse=True)
#     return result[:10]

# def get_loadApkAsset(tp: TraceProcessor, app_pids: List[int], start_time: int, end_time: int):
#     """Lấy danh sách LoadApkAssets > 50ms."""
#     if not app_pids:
#         return None
#     pids_str = ','.join(map(str, app_pids))
#     sql = f"""
#         SELECT slice.name, slice.dur
#         FROM slice 
#         JOIN thread_track ON slice.track_id = thread_track.id 
#         JOIN thread USING (utid) 
#         JOIN process USING (upid)
#         WHERE slice.name LIKE 'LoadApkAssets%' 
#         AND slice.dur/1e6 > 50 
#         AND slice.ts > {start_time} AND slice.ts < {end_time}
#         AND process.pid IN ({pids_str})
#         ORDER BY slice.ts;
#     """
#     return query_df(tp, sql)

# def process_loadapk_data(df) -> List[Dict[str, Any]]:
#     if df is None or df.empty:
#         return []
#     result = []
#     for _, row in df.iterrows():
#         result.append({
#             'name': str(row['name']),
#             'dur_ms': row['dur'] / 1000000.0
#         })
#     return result
# # ==============================================================
# # ==============Get top CPU by Process and Thread===============
# # ==============================================================
# # --- 1. Query cho Process (Group by Process Name) ---
# def get_top_cpu_usage_process(tp: TraceProcessor, start_time: int, dur_time: int, cpu_cores: List[int]):
#     """
#     Query top CPU usage by process. 
#     [UPDATED] Trả về thêm cột 'raw_pid' để Python có thể map lại tên nếu cần.
#     """
#     if not cpu_cores or dur_time <= 0: return None
#     cpu_cores_str = ','.join(map(str, cpu_cores))
    
#     sql = f"""
#     DROP VIEW IF EXISTS cpu_view_proc;
#     CREATE VIEW cpu_view_proc AS
#     SELECT 
#         sched_slice.ts, sched_slice.dur, sched_slice.cpu,
#         COALESCE(
#             process.name, 
#             CASE 
#                 WHEN main_thread.name LIKE '%binder%' OR main_thread.name LIKE '%kworker%' THEN NULL
#                 ELSE main_thread.name
#             END, 
#             'PID-' || process.pid
#         ) as proc_name,
#         process.pid as raw_pid  -- [QUAN TRỌNG] Cần cột này để mapping hoạt động
#     FROM sched_slice 
#     JOIN thread USING (utid) JOIN process USING (upid)
#     LEFT JOIN thread AS main_thread ON (process.pid = main_thread.tid)
#     WHERE NOT thread.name LIKE 'swapper%' ORDER BY ts ASC;
    
#     DROP VIEW IF EXISTS intervals_proc;
#     CREATE VIEW intervals_proc AS SELECT {start_time} AS ts, {dur_time} AS dur;
    
#     DROP TABLE IF EXISTS target_proc;
#     CREATE VIRTUAL TABLE target_proc USING SPAN_JOIN(intervals_proc, cpu_view_proc);
    
#     SELECT 
#         proc_name,
#         raw_pid, -- [QUAN TRỌNG] Chọn cột raw_pid ra kết quả cuối
#         SUM(dur)/1e6 AS dur_ms,
#         COUNT(*) AS Occurences, 
#         ROUND(SUM(dur) * 100.0 / {dur_time}*7, 2) AS dur_percent
#     FROM target_proc
#     WHERE cpu IN ({cpu_cores_str})
#     GROUP BY COALESCE(proc_name, raw_pid)
#     ORDER BY dur_ms DESC;
#     """
#     df = query_df(tp, sql)
#     tp.query("DROP TABLE IF EXISTS target_proc; DROP VIEW IF EXISTS intervals_proc; DROP VIEW IF EXISTS cpu_view_proc;")
#     return df

# def process_cpu_data_process(df, pid_mapping: Dict[int, str] = None) -> List[Dict[str, Any]]:
#     """
#     Process CPU data for processes, with optional PID to process name mapping.
    
# <<<<<<< HEAD
#     [UPDATED] Returns enhanced data structure:
#     - sql_name: Original name from SQL (may be PID-XXX or real name like composer@2.4-se)
#     - dumpstate_name: Full process name from bugreport dumpstate (e.g., android.hardware.graphics.composer@2.4-service)
#     - raw_pid: Process ID for additional lookups
#     - dur_ms, occurences, dur_percent: Performance metrics
    
#     Cross-mapping giữa DUT-REF sử dụng cả sql_name và dumpstate_name.
# =======
#     [SIMPLIFIED] Chỉ resolve "PID-xxx" -> real name từ pid_mapping.
#     Cross-mapping giữa DUT-REF sẽ xử lý ở create_sheet.
# >>>>>>> c9f9404bc02bbb3a27679a1c24127d54eab9de13
#     """
#     if df is None or df.empty: 
#         return []
    
#     result = []
#     for _, row in df.iterrows():
#         sql_name = str(row.get('proc_name', ''))  # Original name from SQL
#         raw_pid = row.get('raw_pid')
        
#         # Lookup dumpstate_name from pid_mapping
#         dumpstate_name = None
#         if pid_mapping and raw_pid is not None:
#             try:
#                 pid_int = int(raw_pid)
#                 if pid_int in pid_mapping:
#                     dumpstate_name = pid_mapping[pid_int]
#             except (ValueError, TypeError):
#                 pass
        
#         # Fallback dumpstate_name to sql_name if not found
#         if not dumpstate_name:
#             dumpstate_name = sql_name if not sql_name.startswith("PID-") else None
        
#         # Final fallback: if dumpstate_name still None, use PID format
#         if not dumpstate_name:
#             dumpstate_name = f'PID-{int(raw_pid)}' if raw_pid is not None else 'Unknown'
        
#         result.append({
#             'sql_name': sql_name,                    # Original SQL name
#             'dumpstate_name': dumpstate_name,        # Full name from dumpstate
#             'raw_pid': int(raw_pid) if raw_pid is not None else None,
#             'dur_ms': float(row['dur_ms']),
#             'occurences': int(row['Occurences']),
#             'dur_percent': float(row['dur_percent'])
#         })
    
#     # Debug output
#     print(f"[CPU Process] Processed {len(result)} entries")
#     for item in result[:5]:
#         print(f"  SQL: {item['sql_name'][:30]:30} | Dump: {item['dumpstate_name'][:40]:40} | {item['dur_ms']:.2f}ms")
    
#     return result

# # --- 2. Query cho Thread (Group by TID/Thread Name) ---
# def get_top_cpu_usage_thread(tp: TraceProcessor, start_time: int, dur_time: int, cpu_cores: List[int]):
#     if not cpu_cores or dur_time <= 0: return None
#     cpu_cores_str = ','.join(map(str, cpu_cores))
    
#     sql = f"""
#     DROP VIEW IF EXISTS cpu_view_thread;
#     CREATE VIEW cpu_view_thread AS
#     SELECT 
#         sched_slice.ts, sched_slice.dur, sched_slice.cpu,
#         thread.tid, thread.name as thread_name,
#         COALESCE(process.name, main_thread.name, 'PID-' || process.pid) as proc_name
#     FROM sched_slice 
#     JOIN thread USING (utid) JOIN process USING (upid)
#     LEFT JOIN thread AS main_thread ON (process.pid = main_thread.tid)
#     WHERE NOT thread.name LIKE 'swapper%' ORDER BY ts ASC;
    
#     DROP VIEW IF EXISTS intervals_thread;
#     CREATE VIEW intervals_thread AS SELECT {start_time} AS ts, {dur_time} AS dur;
    
#     DROP TABLE IF EXISTS target_thread;
#     CREATE VIRTUAL TABLE target_thread USING SPAN_JOIN(intervals_thread, cpu_view_thread);
    
#     SELECT 
#         tid, thread_name, proc_name,
#         SUM(dur)/1e6 AS dur_ms,
#         COUNT(*) AS Occurences, 
#         ROUND(SUM(dur) * 100.0 / {dur_time}*7, 2) AS dur_percent
#     FROM target_thread
#     WHERE cpu IN ({cpu_cores_str})
#     GROUP BY thread_name, proc_name, tid
#     ORDER BY dur_ms DESC;
#     """
#     df = query_df(tp, sql)
#     tp.query("DROP TABLE IF EXISTS target_thread; DROP VIEW IF EXISTS intervals_thread; DROP VIEW IF EXISTS cpu_view_thread;")
#     return df

# def process_cpu_data_thread(df) -> List[Dict[str, Any]]:
#     if df is None or df.empty: return []
#     return [{
#         'tid': str(row['tid']),
#         'dur_ms': float(row['dur_ms']),
#         'thread_name': str(row['thread_name']) if row['thread_name'] else 'unknown',
#         'proc_name': str(row['proc_name']) if row['proc_name'] else 'Unknown',
#         'occurences': int(row['Occurences']),
#         'dur_percent': float(row['dur_percent'])
#     } for _, row in df.iterrows()]






# def get_pid_list(tp: TraceProcessor) -> List[int]:
#     """Lấy PID system_server, systemui, surfaceflinger."""
#     sql = """
#         SELECT p.pid
#         FROM process p JOIN thread t ON p.upid = t.upid
#         WHERE t.is_main_thread = 1 
#           AND (t.name = 'system_server' OR t.name = 'surfaceflinger' OR t.name LIKE '%ndroid.systemui%');
#     """
#     df = query_df(tp, sql)
#     if df is None:
#         return []
#     return df["pid"].tolist()

# def get_pid_systemUI(tp: TraceProcessor):
#     """Systemui PID"""
#     sql = """
#         SELECT p.pid
#         FROM process p JOIN thread t ON p.upid = t.upid
#         WHERE t.is_main_thread = 1 
#           AND (t.name LIKE '%ndroid.systemui%');
#     """
#     df = query_df(tp, sql)
#     if df is None:
#         return []
#     return df["pid"].tolist()

# def get_slice_on_app_process(tp: TraceProcessor, app_pid: int, slice_names: list):
#     """Lấy danh sách nhiều slice trên cả Thread/Process Track."""
#     if not slice_names:
#         return None
#     values_clause = ", ".join([f"('{name}')" for name in slice_names])
#     sql = f"""
#     WITH 
#     TargetProcess AS (SELECT DISTINCT upid FROM process WHERE pid = {app_pid}),
#     TargetPatterns(pattern) AS (VALUES {values_clause})
#     SELECT s.name AS slice_name, s.ts, s.dur
#     FROM slice s
#     JOIN thread_track tt ON s.track_id = tt.id
#     JOIN thread t ON tt.utid = t.utid
#     JOIN TargetProcess p ON t.upid = p.upid
#     JOIN TargetPatterns tn ON s.name LIKE tn.pattern
#     UNION ALL
#     SELECT s.name AS slice_name, s.ts, s.dur
#     FROM slice s
#     JOIN process_track pt ON s.track_id = pt.id
#     JOIN TargetProcess p ON pt.upid = p.upid
#     JOIN TargetPatterns tn ON s.name LIKE tn.pattern
#     ORDER BY ts;
#     """
#     return query_df(tp, sql)

# def process_multiple_slices_data(df) -> Dict[str, List[int]]:
#     if df is None or df.empty:
#         return {}
#     result = {}
#     for _, row in df.iterrows():
#         slice_name = str(row['slice_name'])
#         ts = int(row['ts'])
#         dur = int(row['dur'])
#         if slice_name not in result:
#             result[slice_name] = [ts, dur]
#     return result
# # -------------------------------------------------------------------
# # ABNORMAL PROCESSES 
# # -------------------------------------------------------------------
# def get_abnormal_processes(tp: TraceProcessor, threshold_time: int, exclude_pid: int, target_slices: List[str] = None):
#     """
#     Lấy danh sách các process khởi chạy (bindApplication) trước khi App chính hoàn tất launch.
#     Loại trừ PID của App chính.
#     """
#     if not threshold_time or not exclude_pid:
#         return None

#     if target_slices is None:
#         target_slices = ['bindApplication']
    
#     # Format list cho SQL: 'bindApplication', 'activityStart'
#     slice_names_str = ", ".join([f"'{s}'" for s in target_slices])
    
#     sql = f"""
#     SELECT 
#         process.pid,
#         -- Fix tên process null: Ưu tiên process.name -> thread.name -> PID
#         COALESCE(process.name, thread.name, 'PID-' || process.pid) as proc_name,
#         slice.name as slice_name,
#         slice.ts as start_time,
#         slice.dur as duration_ns
#     FROM slice
#     JOIN thread_track ON slice.track_id = thread_track.id
#     JOIN thread USING (utid)
#     JOIN process USING (upid)
#     WHERE 
#         slice.name IN ({slice_names_str})
#         AND slice.ts < {threshold_time}
#         AND process.pid != {exclude_pid}
#     ORDER BY slice.ts ASC;
#     """
    
#     return query_df(tp, sql)

# def process_abnormal_data(df) -> List[Dict[str, Any]]:
#     """
#     Chuyển đổi DataFrame Abnormal Process thành list dictionary để hiển thị (tương tự process_cpu_usage_data).
#     """
#     if df is None or df.empty:
#         return []
    
#     result = []
#     for _, row in df.iterrows():
#         result.append({
#             'pid': str(row['pid']),
#             'proc_name': str(row['proc_name']),
#             'slice_name': str(row['slice_name']),
#             'start_time': int(row['start_time']),
#             'duration_ms': to_ms(row['duration_ns']) # Dùng hàm to_ms có sẵn
#         })
#     return result


# def get_background_process_states(tp: TraceProcessor, start_ts: int, end_ts: int) -> List[Dict[str, Any]]:
#     """
#     Lấy danh sách các background process (theo pattern gms, google...) 
#     có hoạt động (Running + Runnable) > 10ms trong khoảng thời gian launch.
#     """
#     if not start_ts or not end_ts or start_ts >= end_ts:
#         return []

#     duration = end_ts - start_ts

#     # Danh sách các pattern tên process cần tìm
#     target_patterns = [
#         '%gms.persistent%', 
#         '%googlequicksearchbox%', 
#         '%com.google.android.play%',
#         '%.apps.messaging%'
#     ]
    
#     # Tạo câu điều kiện OR (Fix lỗi process name null)
#     or_clauses = " OR ".join([f"COALESCE(p.name, t.name) LIKE '{pat}'" for pat in target_patterns])

#     # 1. Tìm Main Thread ID (tid) của các process này
#     sql_find_tid = f"""
#     SELECT 
#         COALESCE(p.name, t.name) AS proc_name,
#         t.tid
#     FROM process p
#     JOIN thread t ON p.upid = t.upid
#     WHERE t.is_main_thread = 1
#       AND ({or_clauses});
#     """
    
#     df_procs = query_df(tp, sql_find_tid)
    
#     if df_procs is None or df_procs.empty:
#         return []

#     results = []
    
#     # 2. Lặp qua từng process và kiểm tra điều kiện > 10ms
#     for _, row in df_procs.iterrows():
#         proc_name = str(row['proc_name'])
#         tid = int(row['tid'])
        
#         # Tái sử dụng hàm tính toán state
#         states = get_thread_state_summary(tp, tid, start_ts, duration)
        
#         runnable = states.get("R", 0.0) + states.get("R+", 0.0)
#         running = states.get("Running", 0.0)
        
#         # [LOGIC MỚI] Chỉ lấy nếu tổng Running + Runnable > 10ms
#         if (runnable + running) > 10000000.0:
#             item = {
#                 "Thread name": proc_name
#                 # Không cần các thông số chi tiết nữa vì bảng chỉ hiện tên
#             }
#             results.append(item)

#     return results

# # ====================================
# # ======Abnormal process state========
# # ====================================

# # def get_background_process_states(tp: TraceProcessor, start_ts: int, end_ts: int) -> List[Dict[str, Any]]:
# #     """
# #     Lấy thông tin State (Running, Runnable, Sleeping...) của các background process cụ thể
# #     trong khoảng thời gian từ start_ts đến end_ts.
    
# #     [UPDATED] Fix lỗi process.name bị Null: 
# #     Sử dụng COALESCE(p.name, t.name) để lấy tên process từ main thread nếu bảng process thiếu tên.
# #     """
# #     if not start_ts or not end_ts or start_ts >= end_ts:
# #         return []

# #     duration = end_ts - start_ts

# #     # Danh sách các pattern tên process cần tìm
# #     target_patterns = [
# #         '%gms.persistent%', 
# #         '%googlequicksearchbox%', 
# #         '%com.google.android.play%',
# #         '%.apps.messaging%'
# #     ]
    
# #     # [FIX] Tạo câu điều kiện kiểm tra trên cả p.name và t.name
# #     # COALESCE(p.name, t.name) sẽ trả về p.name nếu có, nếu không trả về t.name
# #     or_clauses = " OR ".join([f"COALESCE(p.name, t.name) LIKE '{pat}'" for pat in target_patterns])

# #     # 1. Tìm Main Thread ID (tid) của các process này
# #     sql_find_tid = f"""
# #     SELECT 
# #         COALESCE(p.name, t.name) AS proc_name,
# #         t.tid
# #     FROM process p
# #     JOIN thread t ON p.upid = t.upid
# #     WHERE t.is_main_thread = 1
# #       AND ({or_clauses});
# #     """
    
# #     df_procs = query_df(tp, sql_find_tid)
    
# #     # Debug: In ra nếu tìm thấy process để kiểm tra
# #     # if df_procs is not None and not df_procs.empty:
# #     #     print(f"  [DEBUG] Found background processes: {df_procs['proc_name'].tolist()}")

# #     if df_procs is None or df_procs.empty:
# #         return []

# #     results = []
    
# #     # 2. Lặp qua từng process tìm được và tính toán State summary
# #     for _, row in df_procs.iterrows():
# #         proc_name = str(row['proc_name'])
# #         tid = int(row['tid'])
        
# #         # Tái sử dụng hàm get_thread_state_summary đã có trong sql_query.py
# #         states = get_thread_state_summary(tp, tid, start_ts, duration)
        
# #         runnable = states.get("R", 0.0) + states.get("R+", 0.0)
        
# #         item = {
# #             "Thread name": proc_name,
# #             "Sleeping": states.get("S", 0.0),             
# #             "Runnable": runnable,                         
# #             "Running": states.get("Running", 0.0),        
# #             "Uninterruptible Sleep": states.get("D", 0.0) 
# #         }
# #         results.append(item)

# #     return results

# # -------------------------------------------------------------------
# # 5. MAIN ANALYSIS LOGIC
# # -------------------------------------------------------------------



# # [File: sql_query.py]

# # [File: sql_query.py]

# def analyze_trace(tp: TraceProcessor, trace_path: str, pid_mapping: Dict[int, str] = None) -> Dict[str, Any]:
#     """
#     Analyze a trace file and extract performance metrics.
    
#     Args:
#         tp: TraceProcessor instance
#         trace_path: Path to the trace file
#         pid_mapping: Optional dict {PID: process_name} from dumpstate for CPU process mapping
    
#     Returns:
#         Dict containing all extracted metrics
#     """
#     metrics: Dict[str, Any] = {}

#     ensure_slice_with_names_view(tp)

#     # 1. Detect Recent Case & Launch Type
#     file_name = Path(trace_path).stem.lower()
#     # Kiểm tra flag is_recent dựa trên tên file
#     is_recent = "recent" in file_name 
    
#     app_pkg = detect_app_from_launch(tp)
    
#     # Nếu là Recent mà không thấy launching slice, gán pkg giả định
#     if not app_pkg:
#         if is_recent:
#             app_pkg = "com.sec.android.app.launcher" 
#         else:
#             raise RuntimeError(f"Không tìm được launching:... trong trace {trace_path}")

#     # 2. Identify App Process (UPID/PID)
#     # - Recent: Process chính chứa Resume/Choreographer thường là Launcher
#     # - App thường: Tìm theo activityStart/Resume của app
#     app_upid, app_pid, app_name, app_tid = None, None, None, None
    
#     if is_recent:
#         # Recent: Tìm process chứa 'activityResume' (Thường là Launcher)
#         row_resume = find_slice(tp, name_exact='activityResume')
#         if row_resume is not None:
#             app_upid = int(row_resume['upid'])
#             app_pid = int(row_resume['pid'])
#             app_tid = int(row_resume['tid'])
#             app_name = str(row_resume.get('process_name', 'Launcher'))
#         else:
#             # Fallback nếu không thấy Resume, thử tìm theo Launcher PID
#             launcher_pid = get_launcher_pid(tp)
#             if launcher_pid:
#                 app_pid = launcher_pid
#                 # Lấy UPID từ PID
#                 df_upid = query_df(tp, f"SELECT upid FROM process WHERE pid = {app_pid}")
#                 if df_upid is not None:
#                      app_upid = int(df_upid.iloc[0]['upid'])
#                      app_tid = app_pid # Fallback
#             else:
#                 raise RuntimeError("Recent: Không tìm thấy process phù hợp (Resume/Launcher)")
#     else:
#         # Logic App thường
#         app_proc = find_app_process(tp, app_pkg)
#         if not app_proc:
#             raise RuntimeError(f"Không tìm được process cho app {app_pkg}")
#         app_upid, app_pid, app_name, app_tid = app_proc

#     # 3. Execution Interval
    
#     # [Touch Down]
#     touch_down_ts = get_first_deliver_input(tp)
#     if touch_down_ts is None:
#         raise RuntimeError("Không tìm thấy deliverInputEvent trong trace")

#     # [Animating] (Recent không có animating trong system_server)
#     animating_end = 0
#     if not is_recent:
#         try:
#             animating_end = get_animating(tp)
#         except RuntimeError:
#             # raise RuntimeError("Trace không hợp lệ: Không tìm thấy 'animating'")
#             print("[WARN] Không tìm thấy 'animating', bỏ qua.") # SỬA: Print thay vì raise
#             animating_end = 0

#     # [Launching End]
#     launching_end = get_launching_end(tp, app_pkg)
    
#     # [Activity Idle]
#     start_idle, end_idle = get_activity_idle_end(tp, app_upid)

#     # [Calculated End TS]
#     end_ts = None
#     is_camera = "camera" in (app_pkg or "").lower()
#     is_internet = "internet" in file_name or "browser" in (app_pkg or "").lower()
    
#     if is_camera:
#         slices_name = ["StartPreviewRequest", "onCreate", "OpenCameraRequest", "onResume"]
#         df = get_slice_on_app_process(tp, app_pid, slices_name)
#         result = process_multiple_slices_data(df)
        
#         metrics["onCreate"] = to_ms(result.get("onCreate", [0, 0])[1])
#         metrics["OpenCameraRequest"] = to_ms(result.get("OpenCameraRequest", [0, 0])[1])
#         metrics["onResume"] = to_ms(result.get("onResume", [0, 0])[1])
#         metrics["StartPreviewRequest"] = to_ms(result.get("StartPreviewRequest", [0, 0])[1])
        
#         preview_data = result.get("StartPreviewRequest", [0, 0])
#         if preview_data[1] > 0:
#             end_ts = preview_data[0] + preview_data[1]
#         else:
#             end_ts = animating_end 

#     elif is_recent:
#         # RECENT: Ưu tiên activityIdle -> Launching End -> Fallback
#         if end_idle:
#             end_ts = end_idle
#         elif launching_end:
#             end_ts = launching_end
#         else:
#             # Fallback an toàn: Touch Down + 500ms
#             end_ts = touch_down_ts + 500_000_000

#     else:   
#         # APP THƯỜNG
#         if is_internet and start_idle and launching_end and (launching_end + 100_000_000 < start_idle):
#             end_ts = animating_end
#             start_idle = None
#             end_idle = None
#         elif end_idle:
#             end_ts = end_idle
#         else:
#             end_ts = animating_end
#             start_idle = None
#             end_idle = None

#     # Max với animating_end (chỉ áp dụng với App thường)
#     if not is_recent:
#         end_ts = max(end_ts, animating_end) if end_ts else animating_end

#     metrics["App Execution Time"] = to_ms(end_ts - touch_down_ts) if end_ts else 0.0

#     # 4. Detailed Metrics

#     # [Touch Down ~ Start Proc]
#     start_proc_info = get_start_proc_start(tp, app_pkg)
    
#     # SỬA: Kiểm tra kỹ start_proc_info và phần tử đầu tiên
#     if start_proc_info and start_proc_info[0] is not None:
#         start_proc_ts, start_proc_dur, start_proc_end = start_proc_info
#         # Thêm try-except hoặc kiểm tra None để an toàn tuyệt đối
#         if start_proc_ts is not None and touch_down_ts is not None:
#             metrics["Touch Down ~ Start Proc"] = to_ms(start_proc_ts - touch_down_ts)
#         else:
#             metrics["Touch Down ~ Start Proc"] = 0.0
#         metrics["Start Proc"] = to_ms(start_proc_dur)  
#     else:
#         start_proc_ts, start_proc_dur, start_proc_end = None, None, None
#         metrics["Touch Down ~ Start Proc"] = 0.0
#         metrics["Start Proc"] = 0.0

#     # [Launch Type]
#     if is_recent:
#         metrics["Launch Type"] = "Warm" # Recent luôn là Warm
#     else:
#         metrics["Launch Type"] = "Cold" if has_bind_application(tp, app_upid) else "Warm"

#     # [ActivityThreadMain], [BindApp]
#     act_main = get_event_ts(tp, app_upid, "ActivityThreadMain")
#     if act_main:
#         act_main_ts, act_main_dur, act_main_end = act_main
#         metrics["Activity Thread Main"] = to_ms(act_main_dur)
#     else:
#         act_main_ts, act_main_dur, act_main_end = None, None, None
#         metrics["Activity Thread Main"] = 0.0

#     bind_app = get_event_ts(tp, app_upid, "bindApplication")
#     if bind_app:
#         bind_app_ts, bind_app_dur, bind_app_end = bind_app
#         metrics["Bind Application"] = to_ms(bind_app_dur)
#     else:
#         bind_app_ts, bind_app_dur, bind_app_end = None, None, None
#         metrics["Bind Application"] = 0.0

#     # [Activity Start] 
#     # FIX: Recent activityStart nằm ở Launcher, App thường nằm ở App Process
#     act_start_ts, act_start_dur, act_start_end = None, None, None
    
#     if is_recent:
#         launcher_pid = get_launcher_pid(tp)
#         if launcher_pid:
#             # Tìm activityStart trong Launcher process
#             row_start = find_slice(tp, name_exact='activityStart', pid=launcher_pid)
#             if row_start is not None:
#                 act_start_ts = int(row_start['ts'])
#                 act_start_dur = int(row_start['dur'])
#                 act_start_end = int(row_start['end_ts'])
#     else:
#         act_start_info = get_event_ts(tp, app_upid, "activityStart")
#         if act_start_info:
#             act_start_ts, act_start_dur, act_start_end = act_start_info

#     metrics["Activity Start"] = to_ms(act_start_dur) if act_start_dur else 0.0

#     # [Activity Resume]
#     cho_threshold = 0
#     act_resume = get_event_ts(tp, app_upid, "activityResume")
#     if act_resume:
#         act_resume_ts, act_resume_dur, act_resume_end = act_resume
#         metrics["Activity Resume"] = to_ms(act_resume_dur)
#         cho_threshold = act_resume_end
#     else:
#         act_resume_ts, act_resume_dur, act_resume_end = None, None, None
#         metrics["Activity Resume"] = 0.0

#     # [Touch Info]
#     launcher_pid = get_launcher_pid(tp)
#     if launcher_pid is not None:
#         touch_up, touch_up_end = get_end_deliver_input(tp, launcher_pid)
#         if touch_up is not None:
#             metrics["Touch Duration"] = to_ms(touch_up - touch_down_ts) 
#             # Dùng act_start_ts đã fix ở trên
#             if act_start_ts and act_start_ts > touch_up:
#                 metrics["Touch Up ~ Activity Start"] = to_ms(act_start_ts - touch_up)
#             else:
#                  metrics["Touch Up ~ Activity Start"] = 0.0
#         else:
#             metrics["Touch Duration"] = 0.0
#             metrics["Touch Up ~ Activity Start"] = 0.0
#     else:
#         metrics["Touch Duration"] = 0.0
#         metrics["Touch Up ~ Activity Start"] = 0.0

#     # [Time Gaps]
#     if start_proc_end and act_main_ts:
#         metrics["Start Proc ~ ActivityThreadMain"] = to_ms(act_main_ts - start_proc_end) if act_main_ts > start_proc_end else 0.0
#     else:
#         metrics["Start Proc ~ ActivityThreadMain"] = 0.0

#     if act_main_end and bind_app_ts:
#         metrics["ActivityThreadMain ~ bindApplication"] = to_ms(bind_app_ts - act_main_end) if bind_app_ts > act_main_end else 0.0
#     else:
#         metrics["ActivityThreadMain ~ bindApplication"] = 0.0

#     if bind_app_end and act_start_ts:
#         metrics["bindApplication ~ activityStart"] = to_ms(act_start_ts - bind_app_end) if act_start_ts > bind_app_end else 0.0
#     else:
#         metrics["bindApplication ~ activityStart"] = 0.0

#     if act_start_end and act_resume_ts:
#         metrics["activityStart ~ activityResume"] = to_ms(act_resume_ts - act_start_end) if act_resume_ts > act_start_end else 0.0
#     else:
#         metrics["activityStart ~ activityResume"] = 0.0

#     # [Choreographer]
#     cho_info = get_choreographer(tp, app_pid, cho_threshold if cho_threshold else 0)
#     if cho_info:
#         cho_ts, cho_dur, cho_end = cho_info
        
#         if is_camera and end_ts > cho_ts:
#              metrics["Choreographer"] = to_ms(end_ts - cho_ts)
#         else:
#              # Fallback: Dùng duration của chính slice Choreographer 
#              metrics["Choreographer"] = to_ms(cho_dur) if cho_dur else 0.0
#     else:
#         cho_ts, cho_dur, cho_end = None, None, None
#         metrics["Choreographer"] = 0.0

#     if act_resume_end and cho_ts:
#         metrics["ActivityResume ~ Choreographer"] = to_ms(cho_ts - act_resume_end) if cho_ts > act_resume_end else 0.0
#     else:
#         metrics["ActivityResume ~ Choreographer"] = 0.0

#     if cho_end and start_idle and not is_camera:
#         metrics["Choreographer ~ ActivityIdle"] = to_ms(start_idle - cho_end) if cho_end is not None else 0.0
#     elif launching_end is not None and start_idle and is_camera:
#         metrics["Choreographer ~ ActivityIdle"] = to_ms(start_idle - launching_end) if launching_end is not None else 0.0
#     else:
#         metrics["Choreographer ~ ActivityIdle"] = 0.0

#     # [ActivityIdle]
#     if start_idle and end_idle:
#         metrics["ActivityIdle"] = to_ms(end_idle - start_idle)
#     else:
#         metrics["ActivityIdle"] = 0.0

#     if end_idle and animating_end and not is_recent:
#         metrics["ActivityIdle ~ Animating end"] = to_ms(animating_end - end_idle) if animating_end > end_idle else 0.0
#     else:
#         metrics["ActivityIdle ~ Animating end"] = to_ms(animating_end - cho_end) if animating_end > cho_end else 0.0

#     # [Thread State]
#     state_summary = get_thread_state_summary(tp, app_tid, touch_down_ts, (end_ts - touch_down_ts) if end_ts else 0)
#     metrics["Running"] = state_summary.get("Running", 0.0)
#     metrics["Runnable"] = state_summary.get("R", 0.0) + state_summary.get("R+", 0.0)
#     metrics["Uninterruptible Sleep"] = state_summary.get("D", 0.0)
#     metrics["Sleeping"] = state_summary.get("S", 0.0)

#     # [Block I/O]
#     safe_start_time = touch_down_ts if touch_down_ts else 0
#     safe_end_time = end_ts if end_ts else (safe_start_time + 10_000_000_000) # Fallback +10s

#     # print(f"[DEBUG] App_pid: {app_pid}, Safe End Time: {safe_end_time}")
#     block_io_df = top_block_IO(tp, app_pid, safe_start_time, safe_end_time)
#     metrics["Block_IO_Data"] = process_block_io_data(block_io_df)

#     # [LoadApkAssets]
#     load_apk_pids = get_pid_list(tp) 
#     if not load_apk_pids:
#         load_apk_pids = [app_pid]
#     if app_pid not in load_apk_pids:
#         load_apk_pids.append(app_pid)
#     loadapk_df = get_loadApkAsset(tp, load_apk_pids, touch_down_ts, end_ts if end_ts else 0)
#     metrics["LoadApkAsset_Data"] = process_loadapk_data(loadapk_df)

#     # [CPU Usage]
#     cpu_cores = [1,2,3,4,5,6,7]
#     dur_time = (end_ts - touch_down_ts) if end_ts else 0

#     # 1. Get Top Process (with PID mapping from dumpstate)
#     cpu_proc_df = get_top_cpu_usage_process(tp, touch_down_ts, dur_time, cpu_cores)
#     metrics["CPU_Process_Data"] = process_cpu_data_process(cpu_proc_df, pid_mapping)
    
#     # 2. Get Top Thread
#     cpu_thread_df = get_top_cpu_usage_thread(tp, touch_down_ts, dur_time, cpu_cores)
#     metrics["CPU_Thread_Data"] = process_cpu_data_thread(cpu_thread_df)

#     # [Binder]
#     binder_count, binder_dur = get_binder_transaction(tp, app_tid, end_ts if end_ts else 0)
#     metrics["Binder_Transaction_Data"] = {
#         'count': binder_count if binder_count is not None else 0,
#         'duration_ms': binder_dur if binder_dur is not None else 0.0
#     }

#     # [Abnormal process]
#     check_threshold = end_ts if end_ts else 0
#     target_abnormal_slices = ['bindApplication'] 
#     abnormal_df = get_abnormal_processes(tp, check_threshold, app_pid, target_abnormal_slices)
#     metrics["Abnormal_Process_Data"] = process_abnormal_data(abnormal_df)

#     # [Background Process States]
#     bg_start_ts = touch_down_ts if touch_down_ts else 0
#     bg_end_ts = end_ts if end_ts else 0
#     metrics["Background_Process_States"] = get_background_process_states(tp, bg_start_ts, bg_end_ts)

#     metrics["PID_Mapping"] = pid_mapping if pid_mapping else {}
    
#     # DEBUG: In ra thông tin PID_Mapping để kiểm tra
#     if pid_mapping:
#         print(f"[DEBUG] PID_Mapping saved: {len(pid_mapping)} entries")
#         print(f"[DEBUG] Sample PID_Mapping: {dict(list(pid_mapping.items())[:5])}")
#     else:
#         print("[DEBUG] No PID_Mapping available")
    
#     metrics["App Package"] = app_pkg 
#     return metrics



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

def find_app_process(tp: TraceProcessor, app_pkg: str) -> Optional[Tuple[int, int, str, int]]:
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
    Get 'onTransactionReady' trong system_server.
    Return: (start_time, dur_time, end_time)
    """
    sql = f"""
    SELECT ts, dur, (ts + dur) as end_ts
    FROM slice_with_names
    WHERE name = 'onTransactionReady';
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

def get_loadApkAsset(tp: TraceProcessor, app_pids: List[int], start_time: int, end_time: int):
    """Lấy danh sách LoadApkAssets > 50ms."""
    if not app_pids:
        return None
    pids_str = ','.join(map(str, app_pids))
    sql = f"""
        SELECT slice.name, slice.dur
        FROM slice 
        JOIN thread_track ON slice.track_id = thread_track.id 
        JOIN thread USING (utid) 
        JOIN process USING (upid)
        WHERE slice.name LIKE 'LoadApkAssets%' 
        AND slice.dur/1e6 > 50 
        AND slice.ts > {start_time} AND slice.ts < {end_time}
        AND process.pid IN ({pids_str})
        ORDER BY slice.ts;
    """
    return query_df(tp, sql)

def process_loadapk_data(df) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    result = []
    for _, row in df.iterrows():
        result.append({
            'name': str(row['name']),
            'dur_ms': row['dur'] / 1000000.0
        })
    return result
# ==============================================================
# ==============Get top CPU by Process and Thread===============
# ==============================================================
# --- 1. Query cho Process (Group by Process Name) ---
def get_top_cpu_usage_process(tp: TraceProcessor, start_time: int, dur_time: int, cpu_cores: List[int]):
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
        AND slice.ts >= {start_time} -- Điều kiện thời gian bắt đầu
        AND slice.ts <= {end_time}   -- Điều kiện thời gian kết thúc
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

# ====================================
# ======Abnormal process state========
# ====================================

# def get_background_process_states(tp: TraceProcessor, start_ts: int, end_ts: int) -> List[Dict[str, Any]]:
#     """
#     Lấy thông tin State (Running, Runnable, Sleeping...) của các background process cụ thể
#     trong khoảng thời gian từ start_ts đến end_ts.
    
#     [UPDATED] Fix lỗi process.name bị Null: 
#     Sử dụng COALESCE(p.name, t.name) để lấy tên process từ main thread nếu bảng process thiếu tên.
#     """
#     if not start_ts or not end_ts or start_ts >= end_ts:
#         return []

#     duration = end_ts - start_ts

#     # Danh sách các pattern tên process cần tìm
#     target_patterns = [
#         '%gms.persistent%', 
#         '%googlequicksearchbox%', 
#         '%com.google.android.play%',
#         '%.apps.messaging%'
#     ]
    
#     # [FIX] Tạo câu điều kiện kiểm tra trên cả p.name và t.name
#     # COALESCE(p.name, t.name) sẽ trả về p.name nếu có, nếu không trả về t.name
#     or_clauses = " OR ".join([f"COALESCE(p.name, t.name) LIKE '{pat}'" for pat in target_patterns])

#     # 1. Tìm Main Thread ID (tid) của các process này
#     sql_find_tid = f"""
#     SELECT 
#         COALESCE(p.name, t.name) AS proc_name,
#         t.tid
#     FROM process p
#     JOIN thread t ON p.upid = t.upid
#     WHERE t.is_main_thread = 1
#       AND ({or_clauses});
#     """
    
#     df_procs = query_df(tp, sql_find_tid)
    
#     # Debug: In ra nếu tìm thấy process để kiểm tra
#     # if df_procs is not None and not df_procs.empty:
#     #     print(f"  [DEBUG] Found background processes: {df_procs['proc_name'].tolist()}")

#     if df_procs is None or df_procs.empty:
#         return []

#     results = []
    
#     # 2. Lặp qua từng process tìm được và tính toán State summary
#     for _, row in df_procs.iterrows():
#         proc_name = str(row['proc_name'])
#         tid = int(row['tid'])
        
#         # Tái sử dụng hàm get_thread_state_summary đã có trong sql_query.py
#         states = get_thread_state_summary(tp, tid, start_ts, duration)
        
#         runnable = states.get("R", 0.0) + states.get("R+", 0.0)
        
#         item = {
#             "Thread name": proc_name,
#             "Sleeping": states.get("S", 0.0),             
#             "Runnable": runnable,                         
#             "Running": states.get("Running", 0.0),        
#             "Uninterruptible Sleep": states.get("D", 0.0) 
#         }
#         results.append(item)

#     return results

# -------------------------------------------------------------------
# 5. MAIN ANALYSIS LOGIC
# -------------------------------------------------------------------



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
            raise RuntimeError(f"Không tìm được launching:... trong trace {trace_path}")

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
                raise RuntimeError("Recent: Không tìm thấy process phù hợp (Resume/Launcher)")
    else:
        # Logic App thường
        app_proc = find_app_process(tp, app_pkg)
        if not app_proc:
            raise RuntimeError(f"Không tìm được process cho app {app_pkg}")
        app_upid, app_pid, app_name, app_tid = app_proc

    # 3. Execution Interval
    
    # [Touch Down]
    touch_down_ts = get_first_deliver_input(tp)
    if touch_down_ts is None:
        raise RuntimeError("Không tìm thấy deliverInputEvent trong trace")

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

    # [Thread State]
    state_summary = get_thread_state_summary(tp, app_tid, touch_down_ts, (end_ts - touch_down_ts) if end_ts else 0)
    metrics["Running"] = state_summary.get("Running", 0.0)
    metrics["Runnable"] = state_summary.get("R", 0.0) + state_summary.get("R+", 0.0)
    metrics["Uninterruptible Sleep"] = state_summary.get("D", 0.0)
    metrics["Sleeping"] = state_summary.get("S", 0.0)

    # [Block I/O]
    safe_start_time = touch_down_ts if touch_down_ts else 0
    safe_end_time = end_ts if end_ts else (safe_start_time + 10_000_000_000) # Fallback +10s

    block_io_df = top_block_IO(tp, app_pid, safe_start_time, safe_end_time)
    metrics["Block_IO_Data"] = process_block_io_data(block_io_df)

    # [LoadApkAssets]
    load_apk_pids = get_pid_list(tp) 
    if not load_apk_pids:
        load_apk_pids = [app_pid]
    if app_pid not in load_apk_pids:
        load_apk_pids.append(app_pid)
    loadapk_df = get_loadApkAsset(tp, load_apk_pids, touch_down_ts, end_ts if end_ts else 0)
    metrics["LoadApkAsset_Data"] = process_loadapk_data(loadapk_df)

    # [CPU Usage]
    cpu_cores = [1,2,3,4,5,6,7]
    dur_time = (end_ts - touch_down_ts) if end_ts else 0

    # 1. Get Top Process (with PID mapping from dumpstate)
    cpu_proc_df = get_top_cpu_usage_process(tp, touch_down_ts, dur_time, cpu_cores)
    metrics["CPU_Process_Data"] = process_cpu_data_process(cpu_proc_df, pid_mapping)
    
    # 2. Get Top Thread
    cpu_thread_df = get_top_cpu_usage_thread(tp, touch_down_ts, dur_time, cpu_cores)
    metrics["CPU_Thread_Data"] = process_cpu_data_thread(cpu_thread_df)

    # [Binder]
    binder_count, binder_dur = get_binder_transaction(tp, app_tid, end_ts if end_ts else 0)
    metrics["Binder_Transaction_Data"] = {
        'count': binder_count if binder_count is not None else 0,
        'duration_ms': binder_dur if binder_dur is not None else 0.0
    }

    # [Abnormal process]
    abnormal_start = touch_down_ts if touch_down_ts else 0
    abnormal_end = end_ts if end_ts else 0
    target_abnormal_slices = ['bindApplication'] 
    abnormal_df = get_abnormal_processes(tp, abnormal_start, abnormal_end, app_pid, target_abnormal_slices)
    metrics["Abnormal_Process_Data"] = process_abnormal_data(abnormal_df)

    # [Background Process States]
    bg_start_ts = touch_down_ts if touch_down_ts else 0
    bg_end_ts = end_ts if end_ts else 0
    metrics["Background_Process_States"] = get_background_process_states(tp, bg_start_ts, bg_end_ts)

    metrics["PID_Mapping"] = pid_mapping if pid_mapping else {}
    metrics["App Package"] = app_pkg 
    return metrics