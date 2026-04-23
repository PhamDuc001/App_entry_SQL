"""
Quick verification tests for sql_query package.
Category 1: Import Tests - Verify all functions are importable from correct locations.
Category 2: Signature Tests - Verify function parameters haven't changed.
Category 3: Logic Tests - Verify pure functions work correctly.

Run: python tests/test_sql_query_imports.py
Or:  python -m pytest tests/test_sql_query_imports.py -v
"""
import sys
import os
import inspect

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =========================================================================
# CATEGORY 1: IMPORT TESTS
# =========================================================================

def test_base_imports():
    """Verify all base.py functions are importable."""
    from sql_query.base import get_resource_path, to_ms, query_df, ensure_slice_with_names_view, find_slice
    print("  [OK] All 5 functions imported from sql_query.base")

def test_trace_queries_imports():
    """Verify all trace_queries.py functions are importable."""
    from sql_query.trace_queries import (
        detect_app_from_launch,
        find_app_process,
        get_first_deliver_input,
        get_end_deliver_input,
        get_launcher_pid,
        get_activity_idle_end,
        get_start_proc_start,
        has_bind_application,
        get_event_ts,
        get_choreographer,
        get_launching_end,
        get_animating,
        get_onTransactionReady,
        get_addStartingWindow,
        get_drawFrame,
        get_reaction_choreographer,
    )
    print("  [OK] All 16 functions imported from sql_query.trace_queries")

def test_sequence_queries_imports():
    """Verify all sequence_queries.py functions are importable."""
    from sql_query.sequence_queries import (
        get_thread_state_summary,
        get_slice_on_app_process,
        process_multiple_slices_data,
        get_abnormal_processes,
        process_abnormal_data,
        get_background_process_states,
        _query_end_ts_dependent_data,
        get_layout_depth_slices,
    )
    print("  [OK] All 8 functions imported from sql_query.sequence_queries")

def test_block_io_imports():
    """Verify all block_io.py functions are importable."""
    from sql_query.block_io import (
        top_block_IO,
        process_block_io_data,
        extract_raw_ftrace_data,
        get_kernel_block_io,
        _query_kernel_bio_from_raw,
        get_hal_library_block_io,
        process_hal_block_io_data,
    )
    print("  [OK] All 7 functions imported from sql_query.block_io")

def test_cpu_queries_imports():
    """Verify all cpu_queries.py functions are importable."""
    from sql_query.cpu_queries import (
        get_top_cpu_usage_process,
        process_cpu_data_process,
        get_top_cpu_usage_thread,
        process_cpu_data_thread,
        get_priority_distribution,
    )
    print("  [OK] All 5 functions imported from sql_query.cpu_queries")

def test_loadapk_asset_imports():
    """Verify all loadapk_asset.py functions are importable."""
    from sql_query.loadapk_asset import (
        get_system_pids,
        get_loadApkAsset,
        process_loadapk_data,
        get_pid_list,
        get_camera_hal_pid,
        get_pid_systemUI,
    )
    print("  [OK] All 6 functions imported from sql_query.loadapk_asset")

def test_binder_transaction_imports():
    """Verify binder_transaction.py functions are importable."""
    from sql_query.binder_transaction import get_binder_transaction
    print("  [OK] 1 function imported from sql_query.binder_transaction")

def test_analysis_imports():
    """Verify analysis.py is importable."""
    from sql_query.analysis import analyze_trace
    print("  [OK] analyze_trace imported from sql_query.analysis")

def test_package_star_import():
    """Verify 'from sql_query import *' works (tests __init__.py re-exports)."""
    import sql_query
    # Check key functions are accessible via package
    assert hasattr(sql_query, 'to_ms'), "to_ms not accessible via sql_query package"
    assert hasattr(sql_query, 'detect_app_from_launch'), "detect_app_from_launch not accessible via sql_query package"
    assert hasattr(sql_query, 'analyze_trace'), "analyze_trace not accessible via sql_query package"
    assert hasattr(sql_query, 'get_layout_depth_slices'), "get_layout_depth_slices not accessible via sql_query package"
    assert hasattr(sql_query, 'get_camera_hal_pid'), "get_camera_hal_pid not accessible via sql_query package"
    print("  [OK] Package star import works - key functions accessible")


# =========================================================================
# CATEGORY 2: SIGNATURE TESTS (for moved/refactored functions)
# =========================================================================

def test_trace_queries_signatures():
    """Verify trace_queries function signatures haven't changed."""
    from sql_query.trace_queries import (
        detect_app_from_launch, find_app_process, get_choreographer,
        get_animating, has_bind_application, get_event_ts,
    )
    
    # detect_app_from_launch(tp)
    sig = inspect.signature(detect_app_from_launch)
    assert 'tp' in sig.parameters, "detect_app_from_launch missing 'tp'"
    
    # find_app_process(tp)
    sig = inspect.signature(find_app_process)
    assert 'tp' in sig.parameters, "find_app_process missing 'tp'"
    
    # get_choreographer(tp, tid, min_ts=0)
    sig = inspect.signature(get_choreographer)
    params = list(sig.parameters.keys())
    assert 'tp' in params, "get_choreographer missing 'tp'"
    assert 'tid' in params, "get_choreographer missing 'tid'"
    assert 'min_ts' in params, "get_choreographer missing 'min_ts'"
    assert sig.parameters['min_ts'].default == 0, "get_choreographer min_ts default should be 0"
    
    # get_animating(tp)
    sig = inspect.signature(get_animating)
    assert 'tp' in sig.parameters, "get_animating missing 'tp'"
    
    # has_bind_application(tp, app_upid)
    sig = inspect.signature(has_bind_application)
    params = list(sig.parameters.keys())
    assert 'tp' in params, "has_bind_application missing 'tp'"
    assert 'app_upid' in params, "has_bind_application missing 'app_upid'"
    
    # get_event_ts(tp, app_upid, name)
    sig = inspect.signature(get_event_ts)
    params = list(sig.parameters.keys())
    assert 'tp' in params, "get_event_ts missing 'tp'"
    assert 'app_upid' in params, "get_event_ts missing 'app_upid'"
    assert 'name' in params, "get_event_ts missing 'name'"
    
    print("  [OK] trace_queries signatures verified")

def test_sequence_queries_signatures():
    """Verify sequence_queries function signatures (especially moved functions)."""
    from sql_query.sequence_queries import get_layout_depth_slices, get_thread_state_summary
    
    # get_layout_depth_slices(tp, tid, start_ts, end_ts, max_depth=6) - MOVED from cpu_queries
    sig = inspect.signature(get_layout_depth_slices)
    params = list(sig.parameters.keys())
    assert 'tp' in params, "get_layout_depth_slices missing 'tp'"
    assert 'tid' in params, "get_layout_depth_slices missing 'tid'"
    assert 'start_ts' in params, "get_layout_depth_slices missing 'start_ts'"
    assert 'end_ts' in params, "get_layout_depth_slices missing 'end_ts'"
    assert 'max_depth' in params, "get_layout_depth_slices missing 'max_depth'"
    assert sig.parameters['max_depth'].default == 6, "get_layout_depth_slices max_depth default should be 6"
    
    # get_thread_state_summary(tp, app_tid, ts_start, ts_dur)
    sig = inspect.signature(get_thread_state_summary)
    params = list(sig.parameters.keys())
    assert 'tp' in params, "get_thread_state_summary missing 'tp'"
    assert 'app_tid' in params, "get_thread_state_summary missing 'app_tid'"
    
    print("  [OK] sequence_queries signatures verified")

def test_loadapk_asset_signatures():
    """Verify loadapk_asset function signatures (especially moved functions)."""
    from sql_query.loadapk_asset import get_camera_hal_pid, get_system_pids
    
    # get_camera_hal_pid(tp) - MOVED from block_io
    sig = inspect.signature(get_camera_hal_pid)
    assert 'tp' in sig.parameters, "get_camera_hal_pid missing 'tp'"
    
    # get_system_pids(tp)
    sig = inspect.signature(get_system_pids)
    assert 'tp' in sig.parameters, "get_system_pids missing 'tp'"
    
    print("  [OK] loadapk_asset signatures verified")


# =========================================================================
# CATEGORY 3: LOGIC TESTS (pure functions, no TraceProcessor needed)
# =========================================================================

def test_to_ms():
    """Verify to_ms conversion logic."""
    from sql_query.base import to_ms
    
    assert to_ms(None) == 0.0, "to_ms(None) should be 0.0"
    assert to_ms(0) == 0.0, "to_ms(0) should be 0.0"
    assert to_ms(1_000_000) == 1.0, "to_ms(1_000_000) should be 1.0"
    assert to_ms(500_000) == 0.5, "to_ms(500_000) should be 0.5"
    assert to_ms(1_500_000) == 1.5, "to_ms(1_500_000) should be 1.5"
    assert to_ms(1) == 0.0, "to_ms(1) should round to 0.0"
    print("  [OK] to_ms logic verified (6 cases)")

def test_process_block_io_data():
    """Verify process_block_io_data handles None/empty input."""
    from sql_query.block_io import process_block_io_data
    
    assert process_block_io_data(None) == [], "process_block_io_data(None) should return []"
    print("  [OK] process_block_io_data edge cases verified")

def test_process_cpu_data_thread():
    """Verify process_cpu_data_thread handles None/empty input."""
    from sql_query.cpu_queries import process_cpu_data_thread
    
    assert process_cpu_data_thread(None) == [], "process_cpu_data_thread(None) should return []"
    print("  [OK] process_cpu_data_thread edge cases verified")

def test_process_cpu_data_process():
    """Verify process_cpu_data_process handles None/empty input."""
    from sql_query.cpu_queries import process_cpu_data_process
    
    assert process_cpu_data_process(None) == [], "process_cpu_data_process(None) should return []"
    print("  [OK] process_cpu_data_process edge cases verified")

def test_process_abnormal_data():
    """Verify process_abnormal_data handles None/empty input."""
    from sql_query.sequence_queries import process_abnormal_data
    
    assert process_abnormal_data(None) == [], "process_abnormal_data(None) should return []"
    print("  [OK] process_abnormal_data edge cases verified")

def test_process_multiple_slices_data():
    """Verify process_multiple_slices_data handles None/empty input."""
    from sql_query.sequence_queries import process_multiple_slices_data
    
    assert process_multiple_slices_data(None) == {}, "process_multiple_slices_data(None) should return {}"
    print("  [OK] process_multiple_slices_data edge cases verified")

def test_get_layout_depth_slices_validation():
    """Verify get_layout_depth_slices input validation (no TraceProcessor needed)."""
    from sql_query.sequence_queries import get_layout_depth_slices
    
    # Invalid inputs should return empty dict
    assert get_layout_depth_slices(None, 0, 0, 0) == {}, "Should return {} for tid=0"
    assert get_layout_depth_slices(None, 123, 0, 0) == {}, "Should return {} for start_ts=0"
    assert get_layout_depth_slices(None, 123, 100, 0) == {}, "Should return {} for end_ts=0"
    assert get_layout_depth_slices(None, 123, 200, 100) == {}, "Should return {} for start_ts >= end_ts"
    print("  [OK] get_layout_depth_slices input validation verified")

def test_get_priority_distribution_validation():
    """Verify get_priority_distribution input validation."""
    from sql_query.cpu_queries import get_priority_distribution
    
    assert get_priority_distribution(None, 0, 100, 200) == {}, "Should return {} for tid=0"
    assert get_priority_distribution(None, 123, 0, 200) == {}, "Should return {} for start_ts=0"
    assert get_priority_distribution(None, 123, 100, 100) == {}, "Should return {} for start_ts >= end_ts"
    print("  [OK] get_priority_distribution input validation verified")


# =========================================================================
# RUN ALL TESTS
# =========================================================================

if __name__ == "__main__":
    tests = [
        # Category 1: Import Tests
        ("Import: base", test_base_imports),
        ("Import: trace_queries", test_trace_queries_imports),
        ("Import: sequence_queries", test_sequence_queries_imports),
        ("Import: block_io", test_block_io_imports),
        ("Import: cpu_queries", test_cpu_queries_imports),
        ("Import: loadapk_asset", test_loadapk_asset_imports),
        ("Import: binder_transaction", test_binder_transaction_imports),
        ("Import: analysis", test_analysis_imports),
        ("Import: package star", test_package_star_import),
        # Category 2: Signature Tests
        ("Signature: trace_queries", test_trace_queries_signatures),
        ("Signature: sequence_queries", test_sequence_queries_signatures),
        ("Signature: loadapk_asset", test_loadapk_asset_signatures),
        # Category 3: Logic Tests
        ("Logic: to_ms", test_to_ms),
        ("Logic: process_block_io_data", test_process_block_io_data),
        ("Logic: process_cpu_data_thread", test_process_cpu_data_thread),
        ("Logic: process_cpu_data_process", test_process_cpu_data_process),
        ("Logic: process_abnormal_data", test_process_abnormal_data),
        ("Logic: process_multiple_slices_data", test_process_multiple_slices_data),
        ("Logic: get_layout_depth_slices validation", test_get_layout_depth_slices_validation),
        ("Logic: get_priority_distribution validation", test_get_priority_distribution_validation),
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 60)
    print("SQL_QUERY VERIFICATION TESTS")
    print("=" * 60)
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)