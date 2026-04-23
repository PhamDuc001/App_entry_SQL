"""
Debug script: Run execution analysis with specific DUT/REF folders.
Tests one app at a time to avoid long runs and utilize caching.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execution_sql import run_analysis

DUT_FOLDER = r"D:\Log PLM\VOC\test\A266B\6GB_P251218-06591\A266BZA5_BOS_6GB_260122_log"
REF_FOLDER = r"D:\Log PLM\VOC\test\A266B\6GB_P251218-06591\A266BYH3_BOS_6GB_80_250821_LOG"

# Available apps - uncomment ONE at a time to test
# After first run, cache is saved so subsequent runs only process new apps

# Test 1: Camera
# target_apps = ["camera"]

# Test 2: Clock  
target_apps = ["clock"]

# Test 3: Calculator
# target_apps = ["calculator"]

# Test 4: Internet
# target_apps = ["internet"]

# Test 5: Phone
# target_apps = ["phone"]

# Test 6: Contacts
# target_apps = ["contacts"]

# Test 7: All apps (remove target_apps parameter)
# target_apps = None

if __name__ == "__main__":
    print(f"DUT: {DUT_FOLDER}")
    print(f"REF: {REF_FOLDER}")
    print(f"Target apps: {target_apps}")
    print("-" * 60)
    
    try:
        run_analysis(DUT_FOLDER, REF_FOLDER, target_apps=target_apps)
        print("\nSUCCESS: Analysis completed without errors.")
    except Exception as e:
        print(f"\nFAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()