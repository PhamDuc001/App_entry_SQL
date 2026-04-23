import os
import sys
from typing import Dict, Optional, Any, Tuple, List, Union
import pandas as pd
from perfetto.trace_processor import TraceProcessor


def get_resource_path(relative_path):
    """
    Ham lay duong dan file resource chuan cho ca Dev, Onedir va Onefile.
    """
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    return os.path.join(base_path, relative_path)

# -------------------------------------------------------------------
# HELPER FUNCTIONS & UTILS
# -------------------------------------------------------------------

def to_ms(ns: Optional[Union[int, float]]) -> float:
    """Chuyen nanoseconds -> milliseconds (3 chu so thap phan)."""
    if ns is None:
        return 0.0
    return round(ns / 1_000_000.0, 3)

def query_df(tp: TraceProcessor, sql: str) -> Optional[pd.DataFrame]:
    """Thuc thi SQL va tra ve pandas.DataFrame (hoac None neu rong/loi)."""
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
    Tao view global slice_with_names.
    Nang cap: Them thread_name va pid de tien filter ngay trong View.
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
# CORE GENERIC QUERY FUNCTION
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
    Ham tim kiem slice da nang.
    Tra ve: 1 dong (pd.Series) dau tien tim thay hoac None.
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