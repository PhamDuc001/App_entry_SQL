# ui/window.py
import sys
import os
import io
import importlib.util
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                             QLineEdit, QPushButton, QGroupBox, QTextEdit, 
                             QFileDialog, QMessageBox, QApplication, 
                             QButtonGroup, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Danh sách App mặc định
DEFAULT_TARGET_APPS = [
    "camera", "helloworld", "calllog", "clock", "contact", 
    "calendar", "calculator", "gallery", "message", "menu", 
    "myfile", "sip", "internet", "note", "setting", 
    "voice", "recent"
]

# --- CLASS BẮT LOG ---
class PrintRedirector(io.StringIO):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def write(self, text):
        if text.strip():
            self.signal.emit(text.strip())

# --- WORKER THREAD ---
class WorkerThread(QThread):
    log_signal = pyqtSignal(str) 
    finished_signal = pyqtSignal()

    def __init__(self, mode, dut_path, ref_path, root_dir, target_apps, is_merge_enabled=False):
        super().__init__()
        self.mode = mode
        self.dut = dut_path
        self.ref = ref_path
        self.root_dir = root_dir
        self.target_apps = target_apps # List app user chọn
        self.is_merge_enabled = is_merge_enabled  # Thêm tham số merge

    def run(self):
        original_stdout = sys.stdout
        sys.stdout = PrintRedirector(self.log_signal)

        try:
            self.log_signal.emit(f"=== STARTED {self.mode.upper()} MODE ===")
            
            if self.root_dir not in sys.path:
                sys.path.insert(0, self.root_dir)

            if self.mode == "execution":
                import execution_sql
                importlib.reload(execution_sql) # Reload để reset state nếu cần
                # FIX: Truyền target_apps và is_merge_enabled vào hàm run_analysis
                execution_sql.run_analysis(self.dut, self.ref, self.target_apps, is_merge_enabled=self.is_merge_enabled)

            elif self.mode == "reaction":
                import reaction_sql
                importlib.reload(reaction_sql)
                # FIX: Truyền target_apps và is_merge_enabled vào hàm run_analysis
                reaction_sql.run_analysis(self.dut, self.ref, self.target_apps, is_merge_enabled=self.is_merge_enabled)

            elif self.mode == "memory":
                # Run both abnormal_memory and memory_main analyses
                from MemoryStatus import memory_main
                
                # Run memory_main analysis
                self.log_signal.emit("Running memory main analysis...")
                memory_main.diff_memory(self.dut, self.ref)

            elif self.mode == "pageboost":
                from Pageboostd import pageboost_main
                pageboost_main.diff_pageboostd(self.dut, self.ref, extracted=False)

                # Run abnormal_memory analysis
                from MemoryStatus import abnormal_memory
                self.log_signal.emit("Running abnormal memory analysis...")
                config = abnormal_memory.Config()
                dut_device = abnormal_memory.DUT(self.dut, config)
                ref_device = abnormal_memory.REF(self.ref, config)
                abnormal_memory.analyze_device_performance(dut_device, ref_device)

            self.log_signal.emit("\n>>> COMPLETED SUCCESSFULLY! <<<")
            
        except Exception as e:
            self.log_signal.emit(f"\n[ERROR] {e}")
            import traceback
            self.log_signal.emit(traceback.format_exc())
            
        finally:
            sys.stdout = original_stdout
            self.finished_signal.emit()

# --- CUSTOM WIDGET KÉO THẢ ---
class DragDropLineEdit(QLineEdit):
    def __init__(self, placeholder=""):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setAcceptDrops(True) 

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.setText(path)

# --- MAIN WINDOW ---
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trace Analysis Tool (Multi-Mode)")
        self.resize(1000, 850)
        self.setAcceptDrops(True)
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.app_buttons = []  # Lưu danh sách các nút app để check state
        
        # Multi-mode queue
        self.mode_queue = []
        self.current_mode_index = 0
        
        self.setup_ui()
        self.load_stylesheet()

    def load_stylesheet(self):
        qss_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        # Thêm style riêng cho App Toggle Button và disabled state
        self.setStyleSheet(self.styleSheet() + """
            QPushButton.app-btn {
                background-color: #555;
                color: #aaa;
                border: 1px solid #666;
                border-radius: 4px;
                padding: 5px;
                font-size: 11px;
            }
            QPushButton.app-btn:checked {
                background-color: #28a745; /* Green */
                color: white;
                border: 1px solid #1e7e34;
            }
            QPushButton.app-btn:disabled {
                background-color: #2a2a2a !important;
                color: #666 !important;
                border: 1px solid #444 !important;
            }
            QPushButton:disabled {
                background-color: #2a2a2a !important;
                color: #666 !important;
                border: 1px solid #444 !important;
            }
            QLineEdit:disabled {
                background-color: #2a2a2a !important;
                color: #666 !important;
                border: 1px solid #444 !important;
            }
            QPushButton#btnStart:disabled {
                background-color: #ff6b35 !important;
                color: white !important;
                border: 1px solid #e55a2b !important;
                font-weight: bold;
            }
        """)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 1. HEADER
        header_layout = QHBoxLayout()
        title = QLabel("PERFORMANCE ANALYSIS TOOL")
        title.setStyleSheet("font-size: 22px; font-weight: 900; color: #ffffff;")
        header_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(header_layout)

        # 2. MODE SELECTION (Multi-select enabled)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(False)  # ← Cho phép chọn nhiều mode
        mode_grid = QGridLayout()
        mode_grid.setSpacing(15)

        self.btn_exec = self.create_mode_btn("⚡ EXECUTION", "btnModeExec")
        self.btn_reac = self.create_mode_btn("⏱ REACTION", "btnModeReac")
        self.btn_mem = self.create_mode_btn("💾 MEMORY", "btnModeMem")
        self.btn_pb = self.create_mode_btn("🚀 PAGEBOOST", "btnModePb")
        
        self.btn_exec.setChecked(True)  # Default check Execution

        mode_grid.addWidget(self.btn_exec, 0, 0)
        mode_grid.addWidget(self.btn_reac, 0, 1)
        mode_grid.addWidget(self.btn_mem, 1, 0)
        mode_grid.addWidget(self.btn_pb, 1, 1)
        main_layout.addLayout(mode_grid)

        # 3. INPUT AREA
        input_layout = QHBoxLayout()
        grp_dut = QGroupBox("Folder DUT")
        dut_layout = QVBoxLayout()
        self.txt_dut = DragDropLineEdit("Kéo thả folder DUT vào đây...")
        btn_browse_dut = QPushButton("📂 Browse DUT")
        btn_browse_dut.setObjectName("btnBrowseDut")
        btn_browse_dut.clicked.connect(lambda: self.browse_folder(self.txt_dut))
        dut_layout.addWidget(self.txt_dut)
        dut_layout.addWidget(btn_browse_dut)
        grp_dut.setLayout(dut_layout)

        grp_ref = QGroupBox("Folder REF")
        ref_layout = QVBoxLayout()
        self.txt_ref = DragDropLineEdit("Kéo thả folder REF vào đây...")
        btn_browse_ref = QPushButton("📂 Browse REF")
        btn_browse_ref.setObjectName("btnBrowseRef")
        btn_browse_ref.clicked.connect(lambda: self.browse_folder(self.txt_ref))
        ref_layout.addWidget(self.txt_ref)
        ref_layout.addWidget(btn_browse_ref)
        grp_ref.setLayout(ref_layout)

        input_layout.addWidget(grp_dut)
        input_layout.addWidget(grp_ref)
        main_layout.addLayout(input_layout)

        # 4. MERGE TOGGLE BUTTON (Chỉ hiển thị khi Execution mode được chọn)
        self.chk_merge = QPushButton("MERGE MODE: OFF")
        self.chk_merge.setCheckable(True)
        self.chk_merge.setObjectName("btnMerge")
        self.chk_merge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_merge.setFixedHeight(35)
        self.chk_merge.setStyleSheet("""
            QPushButton#btnMerge {
                background-color: #dc3545;
                color: white;
                border: 1px solid #c82333;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton#btnMerge:checked {
                background-color: #28a745;
                border: 1px solid #1e7e34;
            }
        """)
        self.chk_merge.clicked.connect(self.toggle_merge_mode)
        main_layout.addWidget(self.chk_merge)

        # 5. START BUTTON
        self.btn_start = QPushButton("START ANALYSIS PROCESS")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setFixedHeight(45)
        self.btn_start.clicked.connect(self.start_analysis)
        main_layout.addWidget(self.btn_start)

        # 6. APP SELECTION (GRID BUTTONS) - SỬA LẠI PHẦN NÀY
        app_grp = QGroupBox("🎯 Target Apps (Execution & Reaction Only)")
        app_layout = QVBoxLayout()
        
        # Grid chứa các nút
        self.app_grid = QGridLayout()
        self.app_grid.setSpacing(10)
        
        # Tạo nút Select All / Deselect All
        ctrl_layout = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_all.clicked.connect(lambda: self.toggle_all_apps(True))
        
        btn_none = QPushButton("Uncheck All")
        btn_none.clicked.connect(lambda: self.toggle_all_apps(False))
        
        ctrl_layout.addWidget(btn_all)
        ctrl_layout.addWidget(btn_none)
        ctrl_layout.addStretch()
        app_layout.addLayout(ctrl_layout)

        # Render các nút App
        cols = 6 # Số cột
        for i, app_name in enumerate(DEFAULT_TARGET_APPS):
            btn = QPushButton(app_name)
            btn.setCheckable(True)
            btn.setChecked(True) # Mặc định chọn
            btn.setProperty("class", "app-btn") # Để CSS bắt
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            row = i // cols
            col = i % cols
            self.app_grid.addWidget(btn, row, col)
            self.app_buttons.append(btn)

        app_layout.addLayout(self.app_grid)
        app_grp.setLayout(app_layout)
        main_layout.addWidget(app_grp)

        # 7. LOG CONSOLE
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("""
            QTextEdit { background-color: #1e1e1e; color: #00ff00; font-family: Consolas; font-size: 12px; border: 1px solid #555; }
        """)
        main_layout.addWidget(self.txt_log)

    def toggle_merge_mode(self):
        if self.chk_merge.isChecked():
            self.chk_merge.setText("MERGE MODE: ON")
        else:
            self.chk_merge.setText("MERGE MODE: OFF")

    def create_mode_btn(self, text, obj_name):
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setProperty("class", "mode-btn") 
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(50)
        self.mode_group.addButton(btn)
        return btn

    def toggle_all_apps(self, checked):
        for btn in self.app_buttons:
            btn.setChecked(checked)

    def browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục")
        if folder:
            line_edit.setText(folder)

    def log(self, message):
        self.txt_log.append(message)
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def get_selected_apps(self):
        selected = []
        for btn in self.app_buttons:
            if btn.isChecked():
                selected.append(btn.text())
        return selected

    def start_analysis(self):
        dut = self.txt_dut.text().strip()
        ref = self.txt_ref.text().strip()
        
        # Collect selected modes (multi-select)
        selected_modes = []
        if self.btn_exec.isChecked(): selected_modes.append("execution")
        if self.btn_reac.isChecked(): selected_modes.append("reaction")
        if self.btn_mem.isChecked(): selected_modes.append("memory")
        if self.btn_pb.isChecked(): selected_modes.append("pageboost")
        
        if not selected_modes:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất 1 mode!")
            return

        if not os.path.isdir(dut):
            QMessageBox.critical(self, "Lỗi", "Đường dẫn DUT không hợp lệ!")
            return
        if not os.path.isdir(ref):
            QMessageBox.critical(self, "Lỗi", "Đường dẫn REF không hợp lệ!")
            return

        target_apps = self.get_selected_apps()
        # Chỉ check list app nếu có mode Execution hoặc Reaction trong queue
        needs_apps = any(m in ["execution", "reaction"] for m in selected_modes)
        if not target_apps and needs_apps:
            QMessageBox.warning(self, "Cảnh báo", "Bạn chưa chọn App nào để phân tích!")
            return

        # Store queue and start first mode
        self.mode_queue = selected_modes
        self.current_mode_index = 0
        self.txt_log.clear()
        
        self._run_next_mode()
    
    def enable_ui_elements(self, enabled):
        """Enable or disable all interactive UI elements."""
        # Mode buttons
        self.btn_exec.setEnabled(enabled)
        self.btn_reac.setEnabled(enabled)
        self.btn_mem.setEnabled(enabled)
        self.btn_pb.setEnabled(enabled)
        
        # Input fields
        self.txt_dut.setEnabled(enabled)
        self.txt_ref.setEnabled(enabled)
        
        # App buttons
        for btn in self.app_buttons:
            btn.setEnabled(enabled)
        
        # Browse buttons by object name
        btn_browse_dut = self.findChild(QPushButton, "btnBrowseDut")
        btn_browse_ref = self.findChild(QPushButton, "btnBrowseRef")
        if btn_browse_dut:
            btn_browse_dut.setEnabled(enabled)
        if btn_browse_ref:
            btn_browse_ref.setEnabled(enabled)
        
        # Select All/Uncheck All buttons
        for button in self.findChildren(QPushButton):
            if button.text() in ["Select All", "Uncheck All"]:
                button.setEnabled(enabled)

    def _run_next_mode(self):
        """Run the next mode in queue."""
        if self.current_mode_index >= len(self.mode_queue):
            # All modes completed - RE-ENABLE EVERYTHING
            self.enable_ui_elements(True)
            self.btn_start.setEnabled(True)
            self.btn_start.setText("START ANALYSIS PROCESS")
            QMessageBox.information(self, "Hoàn thành", 
                f"Đã hoàn thành tất cả {len(self.mode_queue)} mode!")
            return

        mode = self.mode_queue[self.current_mode_index]
        total = len(self.mode_queue)
        current = self.current_mode_index + 1

        # DISABLE ALL UI ELEMENTS
        self.enable_ui_elements(False)
        self.btn_start.setEnabled(False)
        self.btn_start.setText(f"Running {mode.upper()} ({current}/{total})...")

        dut = self.txt_dut.text().strip()
        ref = self.txt_ref.text().strip()
        target_apps = self.get_selected_apps()

        # Kiểm tra xem có bật Merge mode không (áp dụng cho Execution và Reaction mode)
        is_merge_enabled = False
        if mode in ["execution", "reaction"]:
            is_merge_enabled = self.chk_merge.isChecked()

        self.worker = WorkerThread(mode, dut, ref, self.root_dir, target_apps, is_merge_enabled)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self):
        """Called when a mode finishes. Run next mode or complete."""
        self.current_mode_index += 1
        self._run_next_mode()
