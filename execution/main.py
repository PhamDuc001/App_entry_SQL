import os
import sys
import datetime
import pickle
import traceback
from pathlib import Path
from typing import List
from multiprocessing import cpu_count

from execution.config import CACHE_VERSION
from execution.processor import process_all_traces
from execution.excel_output import create_excel_output
from execution.json_output import export_avg_to_json, extract_device_code
from shared.trace_utils import collect_trace_files, extract_model_and_version_from_trace_name

def get_or_process_folder_with_cache(folder_path: str, label: str, num_workers: int, target_apps: List[str], extracted: bool):
    """
    Xử lý quét Trace với Incremental Smart Cache.
    
    Args:
        folder_path: Đường dẫn thư mục chứa trace files
        label: Nhãn để log (DUT/REF)
        num_workers: Số lượng worker processes
        target_apps: Danh sách app cần xử lý
        extracted: True nếu bugreport đã được giải nén
    """
    cache_path = os.path.join(folder_path, ".perf_cache.pkl")
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
    new_data = process_all_traces(folder_path, label, num_workers, missing_apps, extracted)
    
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


def run_analysis(dut_folder: str, ref_folder: str, target_apps: List[str] = None, extracted: bool = False) -> None:
    """
    Phân tích hiệu năng từ các trace trong DUT và REF folders
    
    Args:
        dut_folder: Đường dẫn folder DUT
        ref_folder: Đường dẫn folder REF
        target_apps: Danh sách apps cần xử lý (optional)
        extracted: True nếu các Bugreport đã được giải nén thành folder
    """
    env_workers = os.environ.get("TRACETOOL_WORKERS")
    num_workers = int(env_workers) if env_workers else min(cpu_count(), 8)
    num_workers = max(1, num_workers)
    
    if not os.path.exists(dut_folder):
        raise FileNotFoundError(f"DUT folder not found: {dut_folder}")
    if not os.path.exists(ref_folder):
        raise FileNotFoundError(f"REF folder not found: {ref_folder}")
    
    print("=" * 70)
    print("BATCH EXECUTION TIME ANALYSIS")
    print(f"Workers: {num_workers} | Available CPUs: {cpu_count()}")
    print(f"Extracted mode: {extracted}")
    print("=" * 70)
    
    start_time = datetime.datetime.now()

    # Process DUT folder
    print(f"\n[1/2] Processing DUT folder...")
    dut_results = get_or_process_folder_with_cache(dut_folder, "DUT", num_workers, target_apps, extracted)
    
    # Process REF folder
    print(f"\n[2/2] Processing REF folder...")
    ref_results = get_or_process_folder_with_cache(ref_folder, "REF", num_workers, target_apps, extracted)
    
    # Extract header title, version và model từ file đầu tiên của DUT
    dut_version = ""
    dut_model = ""
    dut_files = collect_trace_files(dut_folder)
    if dut_files:
        first_file = Path(dut_files[0]).stem
        parts = first_file.split("_")
        header_title = "_".join(parts[:2]) if len(parts) >= 2 else "Metric"
        # [NEW] Cắt chuỗi lấy Model và Version từ phần đầu tiên: A166B-ZD7-4GB-BOS-TEST
        dut_model, dut_version = extract_model_and_version_from_trace_name(dut_files[0])
    else:
        header_title = "Metric"

    # Extract REF header title, version và model
    ref_version = ""
    ref_model = ""
    ref_files = collect_trace_files(ref_folder)
    if ref_files:
        first_ref_file = Path(ref_files[0]).stem
        parts = first_ref_file.split("_")
        header_title_ref = "_".join(parts[:2]) if len(parts) >= 2 else "Metric"
        # [NEW] Cắt chuỗi lấy Model và Version từ phần đầu tiên: A166B-ZD7-4GB-BOS-TEST
        ref_model, ref_version = extract_model_and_version_from_trace_name(ref_files[0])
    else:
        header_title_ref = "Metric"

    # Extract device codes
    dut_device_code = extract_device_code(header_title)
    ref_device_code = extract_device_code(header_title_ref)
    

    # 3. Extract DUT/REF model và version từ tên file trace đầu tiên (đã có sẵn)
    
    # Create Excel outputs
    print("\n[3/3] Creating Excel files...")
    output_folder = dut_folder  # Lưu vào thư mục DUT
    create_excel_output(dut_results, ref_results, output_folder, header_title, dut_device_code, ref_device_code, dut_folder, ref_folder, dut_model, dut_version, ref_version)
    
    # Export JSON data
    print("\n[4/4] Exporting JSON data...")
    export_avg_to_json(
        dut_results, ref_results, dut_folder, 
        dut_device_code, ref_device_code, 
        dut_folder, ref_folder,
        dut_version, ref_version,
        dut_model, ref_model 
    )

    end_time = datetime.datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    print("\n" + "=" * 70)
    print(f" COMPLETED in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print("=" * 70)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Batch Execution Time Analysis')
    parser.add_argument('dut_folder', help='Path to DUT folder')
    parser.add_argument('ref_folder', help='Path to REF folder')
    parser.add_argument('--extracted', action='store_true', help='Set if Bugreport files are already extracted to folders')
    
    args = parser.parse_args()
    
    try:
        run_analysis(args.dut_folder, args.ref_folder, extracted=args.extracted)
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
