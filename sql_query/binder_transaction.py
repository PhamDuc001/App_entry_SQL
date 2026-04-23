from sql_query.base import query_df
from perfetto.trace_processor.api import TraceProcessor
from typing import Optional, Tuple
import pandas as pd

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
