import sys
import os
from pathlib import Path

# Add the parent directory to the path to import the module
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# from utopia_preprocess.no_load_app_entry_analyze.analyze_app_start.device_performance_analyzer import DUT, REF, Config, DeviceComparator
from abnormal_memory import DUT, REF, Config, DeviceComparator

def test_device_performance_analyzer_with_paths(dut_path_str, ref_path_str):
    """
    Test the device_performance_analyzer.py script with the provided DUT and REF logs.
    """
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
    dut_path = r"\\107.113.53.40\memory_sluggish\Performance TG\Projects\2025_Projects\BOS\A266B\Issue\8.5_P251218-06606\A266BZA1_BOS_6GB_260108_log"
    ref_path = r"\\107.113.53.40\memory_sluggish\Performance TG\Projects\2025_Projects\BOS\A266B\Issue\8.5_P251218-06606\A266BYH3_BOS_6GB_80_250821_LOG"
    return test_device_performance_analyzer_with_paths(dut_path, ref_path)

if __name__ == "__main__":
    print("Running device_performance_analyzer test with new paths...")
    success = test_device_performance_analyzer()
    if success:
        print("\nTEST PASSED")
    else:
        print("\nTEST FAILED")
        sys.exit(1)
