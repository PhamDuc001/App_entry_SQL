import sys
import os

# Ensure encodings module can be found
if hasattr(sys, '_MEIPASS'):
    # Running in PyInstaller bundle
    base_path = sys._MEIPASS
    
    # Add the base path to sys.path if not already there
    if base_path not in sys.path:
        sys.path.insert(0, base_path)
    
    # Ensure Python can find the encodings module
    encodings_path = os.path.join(base_path, 'encodings')
    if os.path.exists(encodings_path) and encodings_path not in sys.path:
        sys.path.insert(0, encodings_path)
