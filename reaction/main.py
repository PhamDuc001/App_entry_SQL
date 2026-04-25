from reaction.analyzer import *
from reaction.excel_output import create_excel_output
from shared.trace_utils import collect_trace_files, extract_device_info

# ---------------------------------------------------------------------------
# Cache System for Reaction Mode
# ---------------------------------------------------------------------------

def get_or_process_folder_with_cache(folder_path: str, label: str, num_workers: int, target_apps: List[str]):
    """
    Xử lý quét Reaction Trace với Incremental Smart Cache.
    
    Args:
        folder_path: Đường dẫn thư mục chứa trace files
        label: Nhãn để log (DUT/REF)
        num_workers: Số lượng worker processes
        target_apps: Danh sách app cần xử lý
    """
    cache_path = os.path.join(folder_path, ".reaction_cache.pkl")
    current_targets = sorted(target_apps) if target_apps else None
    
    cached_data = {}
    cached_targets = []
    cache_valid = False
    
    # 1. ĐỌC CACHE HIỆN TẠI
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                cache_content = pickle.load(f)
            if isinstance(cache_content, dict) and cache_content.get("version") == CACHE_VERSION:
                cached_targets = cache_content.get("target_apps")
                cached_data = cache_content.get("data", {})
                cache_valid = True
                print(f"  -> [{label}] Found valid cache. Base apps: {cached_targets}")
        except Exception as e:
            print(f"  -> [{label}] [ERROR] Failed to read cache: {e}. Processing from scratch...")
    else:
        print(f"  -> [{label}] No cache found. Processing from scratch...")

    # 2. XỬ LÝ LOGIC TÌM APP CÒN THIẾU
    missing_apps = None
    if cache_valid:
        if current_targets is None:
            if cached_targets is None:
                return cached_data
            else:
                cached_data = {} 
        else:
            if cached_targets is None:
                return {app: data for app, data in cached_data.items() if app in current_targets}
            else:
                missing_apps = sorted(list(set(current_targets) - set(cached_targets)))
                if not missing_apps:
                    print(f"  -> [{label}] All requested apps {current_targets} already in cache. Using cached data...")
                    return {app: data for app, data in cached_data.items() if app in current_targets}
                else:
                    print(f"  -> [{label}] Will process ONLY missing apps: {missing_apps}...")
    else:
        missing_apps = current_targets

    # 3. CHẠY QUÉT TRACE
    print(f"  -> [{label}] Processing trace files for: {missing_apps if missing_apps else 'ALL APPS'}...")
    new_data = process_all_traces(folder_path, label, num_workers, missing_apps)
    
    # 4. GỘP DỮ LIỆU
    merged_data = {**cached_data, **new_data}
    if missing_apps is None or cached_targets is None:
        merged_targets = None
    else:
        merged_targets = sorted(list(set(cached_targets) | set(missing_apps)))

    # 5. LƯU LẠI CACHE
    try:
        cache_content_to_save = {"version": CACHE_VERSION, "target_apps": merged_targets, "data": merged_data}
        with open(cache_path, 'wb') as f: pickle.dump(cache_content_to_save, f)
        print(f"  -> [{label}] Saved data to cache: {cache_path}")
    except Exception as e:
        print(f"  -> [{label}] [WARN] Could not save cache: {e}")
        
    # 6. TRẢ VỀ KẾT QUẢ
    if current_targets is None:
        return merged_data
    else:
        return {app: data for app, data in merged_data.items() if app in current_targets}


# ---------------------------------------------------------------------------
# Main Function for External Call
# ---------------------------------------------------------------------------

def run_analysis(dut_folder: str, ref_folder: str, target_apps: List[str] = None) -> None:
    """
    Phân tích Reaction Time từ các trace trong DUT và REF folders
    
    Args:
        dut_folder: Đường dẫn folder DUT
        ref_folder: Đường dẫn folder REF
        target_apps: Danh sách app cần xử lý
    """
    num_workers = min(cpu_count(), 8)

    print("="*70)
    print("REACTION TIME ANALYSIS")
    print(f"Workers: {num_workers} | Available CPUs: {cpu_count()}")
    print("="*70)

    # 1. Processing with Cache
    print(f"\n[1/2] Processing DUT folder...")
    dut_res = get_or_process_folder_with_cache(dut_folder, "DUT", num_workers, target_apps)
    
    print(f"\n[2/2] Processing REF folder...")
    ref_res = get_or_process_folder_with_cache(ref_folder, "REF", num_workers, target_apps)

    # 2. Extract device info from DUT and REF folders
    dut_model, dut_version, header_title = extract_device_info(dut_folder)
    ref_model, ref_version, _ = extract_device_info(ref_folder)
    
    # 3. Generating Excel
    print("\n[3/3] Creating Excel files...")
    create_excel_output(dut_res, ref_res, dut_folder, header_title, dut_model, dut_version, ref_version)
    print("\nDone.")

# ---------------------------------------------------------------------------
# Standalone Execution
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Reaction Time Analysis')
    parser.add_argument('dut_folder', help='Path to DUT folder')
    parser.add_argument('ref_folder', help='Path to REF folder')
    
    args = parser.parse_args()
    
    try:
        run_analysis(args.dut_folder, args.ref_folder)
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

