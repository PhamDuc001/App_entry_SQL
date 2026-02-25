import sys
import os
from pathlib import Path
import zipfile
import shutil

# Add the parent directory to the path to import the module
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# from utopia_preprocess.no_load_app_entry_analyze.analyze_app_start.device_performance_analyzer import DUT, REF, Config, DeviceComparator
from abnormal_memory import DUT, REF, Config, DeviceComparator


def extract_all_zips_in_folder(folder_path):
    """
    Extract all .zip files in the given folder to subfolders.
    Handles long paths and network share issues.
    """
    folder_path = Path(folder_path)
    if not folder_path.exists():
        print(f"ERROR: Folder does not exist: {folder_path}")
        return False
    
    zip_files = list(folder_path.glob("*.zip"))
    if not zip_files:
        print(f"No .zip files found in {folder_path}")
        return True
    
    for zip_file in zip_files:
        try:
            # Create extraction folder name
            extract_folder = folder_path / zip_file.stem
            
            # Skip if extraction folder already exists
            if extract_folder.exists():
                print(f"Skipping {zip_file.name} - extraction folder already exists")
                continue
            
            print(f"Extracting {zip_file.name} to {extract_folder.name}/")
            
            # Create extraction folder first
            extract_folder.mkdir(exist_ok=True)
            
            # Extract with better error handling
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                # Get list of files in zip
                file_list = zip_ref.namelist()
                
                for file_info in zip_ref.infolist():
                    try:
                        # Handle long paths by truncating if necessary
                        extracted_path = extract_folder / file_info.filename
                        
                        # Create parent directories if they don't exist
                        if file_info.is_dir():
                            extracted_path.mkdir(parents=True, exist_ok=True)
                        else:
                            # Ensure parent directory exists
                            extracted_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Extract file with original permissions
                            with zip_ref.open(file_info) as source:
                                with open(extracted_path, "wb") as target:
                                    shutil.copyfileobj(source, target)
                    
                    except (OSError, IOError) as e:
                        print(f"WARNING: Could not extract {file_info.filename}: {e}")
                        continue
            
            print(f"Successfully extracted {zip_file.name}")
            
        except Exception as e:
            print(f"ERROR: Failed to extract {zip_file.name}: {e}")
            # Continue with other files instead of returning False
            continue
    
    return True



def test_device_performance_analyzer_with_paths(dut_path_str, ref_path_str):
    """
    Test the device_performance_analyzer.py script with the provided DUT and REF logs.
    """
    # Extract zip files in both folders first
    print("Extracting zip files in DUT folder...")
    if not extract_all_zips_in_folder(dut_path_str):
        return False
    
    print("Extracting zip files in REF folder...")
    if not extract_all_zips_in_folder(ref_path_str):
        return False

    # Convert string paths to Path objects
    dut_path = Path(dut_path_str)
    ref_path = Path(ref_path_str)
    
    # Check if paths exist
    if not dut_path.exists():
        print(f"ERROR: DUT path does not exist: {dut_path}")
        return False
        
    if not ref_path.exists():
        print(f"ERROR: REF path does not exist: {ref_path}")
        return False
    
    print(f"Using DUT path: {dut_path}")
    print(f"Using REF path: {ref_path}")
    
    try:
        # Create DUT and REF devices
        config = Config()
        dut = DUT(dut_path, config)
        ref = REF(ref_path, config)
        
        # Create comparator
        comparator = DeviceComparator(dut, ref, config)
        
        # Compare devices
        print("Comparing devices...")
        comparison_result = comparator.compare()
        
        # Generate report
        output_path = dut_path / f"DevicePerformance_Test_Report_New.xlsx"
        print(f"Generating Excel report at: {output_path}")
        success = comparator.generate_excel_report(output_path)
        
        if success:
            print(f"SUCCESS: Excel report created: {output_path}")
        else:
            print("ERROR: Failed to create Excel report")
            return False
            
        # Generate console summary
        console_result = comparator.generate_console_report()
        print("Console Summary Report:")
        print(console_result)
        
        return True
        
    except Exception as e:
        print(f"ERROR: Exception occurred during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_device_performance_analyzer():
    """
    Test the device_performance_analyzer.py script with default DUT and REF logs.
    """
    # Define the paths for DUT and REF as specified in the task
    dut_path = r"\\107.113.53.40\memory_sluggish\Performance TG\Projects\2025_Projects\BOS\M166S\8.5_Issue\6GB\P260114-04918\M166SZA7_BOS_6GB_260113_log"
    ref_path = r"\\107.113.53.40\memory_sluggish\Performance TG\Projects\2025_Projects\BOS\M166S\8.5_Issue\6GB\P260114-04918\M166SYH2_6GB_BOS_250818_Log"
    return test_device_performance_analyzer_with_paths(dut_path, ref_path)

if __name__ == "__main__":
    print("Running device_performance_analyzer test with new paths...")
    success = test_device_performance_analyzer()
    if success:
        print("\nTEST PASSED")
    else:
        print("\nTEST FAILED")
        sys.exit(1)
