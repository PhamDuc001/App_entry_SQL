# main_qt.py
import sys
import multiprocessing
from PyQt6.QtWidgets import QApplication
from ui.window import MainWindow

def main():
    multiprocessing.freeze_support() 
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()