from PyQt5 import uic
from PyQt5.QtWidgets import (QWidget, QToolButton, QPushButton, QLineEdit, QLabel,
                             QComboBox, QFrame, QProgressBar, QSizePolicy, QVBoxLayout, QFileDialog, QHBoxLayout, QTextEdit, QApplication, QListWidget)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import pyqtSlot, Qt, QTimer
import numpy as np
import pyqtgraph as pg
from ui.custom_widgets import ImageWidget
from utils.helpers import run_async  # Import the run_async decorator
from PyQt5.QtWidgets import QMessageBox
import os
import time
import subprocess
import traceback
from typing import Callable, List, Optional

import pyautogui
from utils.embed_lenmark import embed_lenmark_in_preview


try:
    from config import Config
except Exception:
    class Config:  # Fallback minimal config
        LENMARK_EXE_PATH = r"C:\Program Files (x86)\LenMark_3DS\LenMark_3DS.exe"
        LENMARK_CONNECT_TITLE_PATTERNS = ["LenMark_3DS", "LenMark", "LenMark 3D", ".*LenMark.*"]

def mark_all_dxf_files(
    folder_path: str,
    *,
    load_delay: float = 2.5,
    pre_mark_delay: float = 0.2,
    mark_duration: float = 5.0,
    inter_file_delay: float = 0.5,
    mark_hotkey: str = "f2",
    close_doc_hotkey: tuple = ("ctrl", "w"),
    launch_wait_timeout: float = 40.0,
    log: Optional[Callable[[str], None]] = None,
    progress_cb: Optional[Callable[[int], None]] = None,
    stop_flag_getter: Optional[Callable[[], bool]] = None,
    use_double_click_list: bool = False  # set True only if you implement coordinate logic
) -> dict:
    """
    Automate LenMark to mark every DXF file in a folder.

    Parameters
    ----------
    folder_path : str
        Directory containing DXF files.
    load_delay : float
        Seconds to wait after opening a DXF before sending mark hotkey.
    pre_mark_delay : float
        Short delay before pressing the mark hotkey.
    mark_duration : float
        Approximate time LenMark needs to finish marking a single file.
    inter_file_delay : float
        Delay between finishing one file and starting the next.
    mark_hotkey : str
        Key to trigger marking (default F2).
    close_doc_hotkey : tuple
        Hotkey sequence to close the current document (default Ctrl+W).
    launch_wait_timeout : float
        Max seconds to wait for LenMark window to appear after launch.
    log : callable(str)
        Logging callback (defaults to print).
    progress_cb : callable(int)
        Progress callback: receives integer 0–100.
    stop_flag_getter : callable() -> bool
        If provided and returns True, the loop aborts cleanly.
    use_double_click_list : bool
        If True, (NOT IMPLEMENTED here) would attempt to double-click file in UI instead
        of using Ctrl+O + path typing. Requires custom coordinate/template logic.

    Returns
    -------
    dict with keys:
        processed: List[str]  - successfully marked filenames
        failed:    List[str]  - filenames that failed
        skipped:   List[str]  - skipped due to stop request
        total:     int        - total candidate files discovered
        completed: bool       - True if all processed without stop
    """
    _log = log or print

    result = {
        "processed": [],
        "failed": [],
        "skipped": [],
        "total": 0,
        "completed": False,
    }

    # Basic validation
    if not folder_path or not os.path.isdir(folder_path):
        _log(f"[DXF] Folder not found: {folder_path}")
        return result

    # Gather DXFs
    dxf_files: List[str] = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(".dxf") and os.path.isfile(os.path.join(folder_path, f))
    ]

    # Sort with numeric awareness (img_01, img_2, img_10)
    def sort_key(name: str):
        digits = "".join(ch for ch in name if ch.isdigit())
        try:
            return (int(digits), name.lower())
        except ValueError:
            return (10**9, name.lower())

    dxf_files.sort(key=sort_key)

    if not dxf_files:
        _log("[DXF] No .dxf files found in folder.")
        return result

    result["total"] = len(dxf_files)
    _log(f"🚀 Starting LenMark automation for {len(dxf_files)} DXF file"
         f"{'s' if len(dxf_files) != 1 else ''}.")

    # Ensure pyautogui settings
    pyautogui.FAILSAFE = True  # Move mouse to top-left to abort in emergencies
    pyautogui.PAUSE = 0.05

    # Launch LenMark if not already open
    def _try_get_window():
        # pyautogui relies on PyGetWindow internally
        try:
            import pygetwindow as gw
            patterns = getattr(Config, "LENMARK_CONNECT_TITLE_PATTERNS", ["LenMark"])
            for w in gw.getAllTitles():
                for pat in patterns:
                    # Crude match: substring or simple wildcard-ish match
                    if pat.strip("*").lower() in w.lower():
                        win = gw.getWindowsWithTitle(w)
                        if win:
                            return win[0]
        except Exception:
            pass
        return None

    win = _try_get_window()
    if not win:
        exe_path = getattr(Config, "LENMARK_EXE_PATH", None)
        if not exe_path or not os.path.isfile(exe_path):
            _log(f"[DXF] LenMark executable not configured / missing: {exe_path}")
            return result
        _log(f"[DXF] Launching LenMark: {exe_path}")
        try:
            subprocess.Popen([exe_path])
        except Exception as e:
            _log(f"[DXF] Failed to launch LenMark: {e}")
            return result

        # Wait for window
        start_wait = time.time()
        while time.time() - start_wait < launch_wait_timeout:
            win = _try_get_window()
            if win:
                break
            time.sleep(1)
        if not win:
            _log("[DXF] LenMark window not detected within timeout.")
            return result

    # Focus window
    try:
        if win and win.isMinimized:
            win.restore()
        if win:
            win.activate()
            time.sleep(0.5)
    except Exception:
        pass

    # Helper to open a file using Ctrl+O -> type path -> Enter
    def open_file_via_dialog(abs_path: str):
        pyautogui.hotkey("ctrl", "o")
        time.sleep(0.6)
        # Clear any residual text: send Ctrl+A then backspace
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.press("backspace")
        time.sleep(0.05)
        # Type full path (escape braces for safety)
        to_type = abs_path.replace("{", "{{}").replace("}", "{}}")
        pyautogui.write(to_type, interval=0.01)
        time.sleep(0.05)
        pyautogui.press("enter")

    # (Optional) placeholder for a double-click approach
    def open_file_by_double_click(name: str):
        """
        Placeholder for UI file list double-click approach.
        Not implemented because it requires:
          - Known coordinates, or
          - Image templates (pyautogui.locateOnScreen)
        You can implement if you capture specific regions.
        """
        raise NotImplementedError("Double-click method not implemented; integrate coordinates/template matching if needed.")

    stopped_early = False

    for idx, fname in enumerate(dxf_files, start=1):
        if stop_flag_getter and stop_flag_getter():
            _log("[DXF] Stop requested by user; aborting remaining files.")
            stopped_early = True
            result["skipped"].extend(dxf_files[idx-1:])  # include current and remaining as skipped
            break

        abs_path = os.path.join(folder_path, fname)
        _log(f"[{idx}/{len(dxf_files)}] Opening {fname}...")
        try:
            if use_double_click_list:
                open_file_by_double_click(fname)  # currently raises NotImplementedError
            else:
                open_file_via_dialog(abs_path)

            # Wait for load
            time.sleep(load_delay)

            if stop_flag_getter and stop_flag_getter():
                _log("[DXF] Stop requested after load; aborting before mark.")
                stopped_early = True
                result["skipped"].extend(dxf_files[idx-1:])
                break

            _log(f"[{idx}/{len(dxf_files)}] Marking...")
            time.sleep(pre_mark_delay)
            pyautogui.press(mark_hotkey)
            # Wait for marking to (approximately) finish
            time.sleep(mark_duration)

            # Close file
            pyautogui.hotkey(*close_doc_hotkey)
            time.sleep(inter_file_delay)

            _log(f"✅ {fname} done.")
            result["processed"].append(fname)
        except Exception as e:
            _log(f"❌ Failed {fname}: {e}")
            if os.getenv("LENMARK_AUTOMATION_DEBUG"):
                traceback.print_exc()
            result["failed"].append(fname)
            # Attempt to continue with next file
            time.sleep(0.5)

        # Progress callback
        if progress_cb:
            pct = int(idx / len(dxf_files) * 100)
            try:
                progress_cb(pct)
            except Exception:
                pass

    if not stopped_early:
        if len(result['processed']) + len(result['failed']) == len(dxf_files):
            _log("🎯 All DXF files processed.")
            result["completed"] = True
        else:
            _log("⚠ Incomplete processing (interrupted or unexpected skip).")
    else:
        _log("⏹ Automation stopped by user before completion.")

    _log(f"Summary: processed={len(result['processed'])} failed={len(result['failed'])} skipped={len(result['skipped'])}")
    return result


class HomeScreen(QWidget):
    def __init__(self, main_window):
        super(HomeScreen, self).__init__()
        self.main_window = main_window
        self.is_paused = False  # Add this line to initialize the pause flag

        # Load the UI file
        try:
            uic.loadUi('ui/home_screen/home_screen.ui', self)
            print("HomeScreen UI loaded successfully")
        except Exception as e:
            print(f"Failed to load UI file: {e}")

        # Initialize labels
        self.bedTargetTemperature = self.findChild(QLabel, "bedTargetTemperature")
        self.bedActualTemperature = self.findChild(QLabel, "bedActualTemperature")
        self.chamberTargetTemperature = self.findChild(QLabel, "chamberTargetTemperature")
        self.chamberActualTemperature = self.findChild(QLabel, "chamberActualTemperature")
        self.volumeTargetTemperature = self.findChild(QLabel, "volumeTargetTemperature")
        self.volumeActualTemperature = self.findChild(QLabel, "volumeActualTemperature")
        self.fileInfoLabel = self.findChild(QLabel, "fileInfoLabel")
        self.maxTempLabel = self.findChild(QLabel, "maxTempLabel")  # Find the maxTempLabel

        # Initialize QPushButtons (if any)
        # Auto-scale all labels
        for lbl in [self.bedTargetTemperature, self.bedActualTemperature, self.chamberTargetTemperature, self.chamberActualTemperature, self.volumeTargetTemperature, self.volumeActualTemperature, self.fileInfoLabel, self.maxTempLabel]:
            if lbl:
                lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                font = lbl.font()
                font.setPointSize(14)
                lbl.setFont(font)
        self.stopButton = self.findChild(QPushButton, "stopButton")
        self.playPauseButton = self.findChild(QPushButton, "playPauseButton")
        self.loadFileButton = self.findChild(QPushButton, "loadFileButton")
        self.stopHeatingButton = self.findChild(QPushButton, "stopHeatingButton")
        self.setPIDButton = self.findChild(QPushButton, "setPIDButton")

        # Initialize QLineEdits for PID parameters
        # Auto-scale all buttons
        for btn in [self.stopButton, self.playPauseButton, self.loadFileButton, self.stopHeatingButton, self.setPIDButton]:
            if btn:
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                font = btn.font()
                font.setPointSize(12)
                btn.setFont(font)
                btn.setMinimumSize(0, 0)
                btn.setMaximumSize(16777215, 16777215)
                if hasattr(btn, 'setIconSize'):
                    btn.setIconSize(btn.size())
        self.p_LineEdit = self.findChild(QLineEdit, "p_LineEdit")
        self.i_LineEdit = self.findChild(QLineEdit, "i_LineEdit")
        self.d_lineEdit = self.findChild(QLineEdit, "d_lineEdit")

        # Initialize QProgressBars
        self.bedTempBar = self.findChild(QProgressBar, "bedTempBar")
        self.printProgressBar = self.findChild(QProgressBar, "printProgressBar")
        self.volumeTempBar = self.findChild(QProgressBar, "volumeTempBar")
        self.chamberTempBar = self.findChild(QProgressBar, "chamberTempBar")

        # Initialize additional widget elements (graph and camera feed areas)
        # Auto-scale all progress bars
        for bar in [self.bedTempBar, self.printProgressBar, self.volumeTempBar, self.chamberTempBar]:
            if bar:
                bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                bar.setMinimumSize(0, 0)
                bar.setMaximumSize(16777215, 16777215)
        self.chamberTempGraphWidget = self.findChild(QWidget, "chamberTempGraphWidget")
        self.layerPreviewWidget = self.findChild(QWidget, "layerPreviewWidget")

        # Replace the QWidget with the custom ImageWidget
        thermal_camera_container = self.findChild(QWidget, "thermalCameraWidget")
        self.thermalCameraWidget = ImageWidget(thermal_camera_container)
        layout = QVBoxLayout(thermal_camera_container)
        layout.addWidget(self.thermalCameraWidget)
        self.thermalCameraWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Replace the QWidget with the custom ImageWidget
        rgb_camera_container = self.findChild(QWidget, "rgbCameraWidget")
        self.rgbCameraWidget = ImageWidget(rgb_camera_container)
        layout = QVBoxLayout(rgb_camera_container)
        layout.addWidget(self.rgbCameraWidget)
        self.rgbCameraWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Connect the temperatures_updated signal to the update_thermal_camera_widget slot
        self.main_window.printer_status.temperatures_updated.connect(self.update_thermal_camera_widget)
        self.main_window.printer_status.rgb_frame_updated.connect(self.update_rgb_camera_widget)
        self.main_window.printer_status.maxtemp_updated.connect(self.update_max_temp_label)  # Connect the maxtemp_updated signal

        # Initialize the plot for max temperature
        self.max_temp_plot = pg.PlotWidget()
        self.chamberTempGraphWidget.setLayout(QVBoxLayout())  # Set a layout for chamberTempGraphWidget
        self.chamberTempGraphWidget.layout().addWidget(self.max_temp_plot)
        self.max_temp_curve = self.max_temp_plot.plot(pen='r')
        self.max_temp_data = []

        # Connect buttons to their respective slots
        self.playPauseButton.clicked.connect(self.toggle_printing)
        self.stopButton.clicked.connect(self.stop_printing)
        # Rewire Load File button to a unified handler that chooses DXF vs EMD flow
        try:
            self.loadFileButton.clicked.disconnect()
        except Exception:
            pass
        self.loadFileButton.clicked.connect(self._on_load_file_clicked)

        # Persistent process mode selector (EMD vs DXF)
        mode_row = QHBoxLayout()
        self.processModeLabel = QLabel("Process Mode:")
        self.processModeLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        font = self.processModeLabel.font()
        font.setPointSize(12)
        self.processModeLabel.setFont(font)
        self.processModeComboBox = QComboBox()
        self.processModeComboBox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.processModeComboBox.addItems(["EMD (API)", "DXF (Automation)"])
        # Default to DXF if not specified
        default_mode = getattr(self.main_window, "process_mode", "DXF")
        self.processModeComboBox.setCurrentText("DXF (Automation)" if default_mode == "DXF" else "EMD (API)")
        # Set the initial process mode
        self.main_window.process_mode = default_mode
        mode_row.addWidget(self.processModeLabel)
        mode_row.addWidget(self.processModeComboBox)
        # Append to the bottom of the screen
        if self.layout() is None:
            self.setLayout(QVBoxLayout())
        self.layout().addLayout(mode_row)

        def _on_mode_changed(index: int):
            text = self.processModeComboBox.currentText()
            self.main_window.process_mode = "DXF" if "DXF" in text else "EMD"
            print(f"[UI] Process mode set to: {self.main_window.process_mode}")

        self.processModeComboBox.currentIndexChanged.connect(_on_mode_changed)

        # Lightweight on-screen automation log so LenMark actions are visible in the UI
        try:
            self.automationLogText = QTextEdit()
            self.automationLogText.setReadOnly(True)
            self.automationLogText.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            font = self.automationLogText.font()
            font.setPointSize(10)
            self.automationLogText.setFont(font)
            self.automationLogText.setMinimumHeight(120)
            if self.layout() is None:
                self.setLayout(QVBoxLayout())
            self.layout().addWidget(self.automationLogText)
        except Exception as e:
            print(f"Failed to add automation log widget: {e}")

        # Add a lightweight 'Test LenMark' button
        try:
            self.testLenmarkButton = QPushButton("Test LenMark Launch")
            self.testLenmarkButton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            font = self.testLenmarkButton.font()
            font.setPointSize(12)
            self.testLenmarkButton.setFont(font)
            self.layout().addWidget(self.testLenmarkButton)
            def _run_test():
                # Launch the full sequential automation over current DXF folder
                self.main_window.process_automation_controller.run_lenmark_sequence()
            self.testLenmarkButton.clicked.connect(_run_test)
        except Exception as e:
            print(f"Failed to add Test LenMark button: {e}")

        # Embed LenMark_3DS in the preview widget after UI is ready
        def _embed_lenmark():
            try:
                embed_lenmark_in_preview(self.layerPreviewWidget)
            except Exception as e:
                print(f"[LenMark] Embed error: {e}")
        QTimer.singleShot(3000, _embed_lenmark)

    def start_printing_sequence(self):
        self.main_window.process_automation_controller.start_printing_sequence(self.main_window.layer_count)


    def toggle_printing(self):
        if self.playPauseButton.isChecked():
            if self.is_paused:
                self.is_paused = False
            else:
                # Decide route based on mode
                mode = getattr(self.main_window, "process_mode", "DXF")
                if mode == "DXF":
                    # Ensure folder selected (ask if missing)
                    if not getattr(self.main_window, "input_dir", None):
                        from PyQt5.QtWidgets import QFileDialog
                        folder = QFileDialog.getExistingDirectory(self, "Select DXF Folder")
                        if not folder:
                            QMessageBox.warning(self, "DXF Directory Required", "No folder selected.")
                            self.playPauseButton.setChecked(False)
                            return
                        self.main_window.input_dir = folder
                    # Start DXF automation (hands‑free LenMark sequence)
                    # Use simplified spec-defined sequence
                    self.main_window.process_automation_controller.start_dxf_mark_sequence()
                else:
                    # Original printing flow
                    self.main_window.process_automation_controller.process_running = True
                    self.start_printing_sequence()
        else:
            self.is_paused = True  # Set the pause flag

    def stop_printing(self):
        self.main_window.process_automation_controller.stop_process()

    @pyqtSlot(np.ndarray, dict)
    def update_thermal_camera_widget(self, frame, temps):
        if frame is not None:
            image = QImage(frame.data, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_BGR888)
            self.thermalCameraWidget.setImage(image)

    @pyqtSlot(np.ndarray)
    def update_rgb_camera_widget(self, frame):
        if frame is not None:
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            self.rgbCameraWidget.setImage(image)

    @pyqtSlot(float)
    def update_max_temp_label(self, max_temp):
        """Slot to update the text of maxTempLabel with the maximum temperature."""
        self.maxTempLabel.setText(f"Max Temp: {max_temp:.2f}°C")
        self.update_max_temp_plot(max_temp)

    def update_max_temp_plot(self, max_temp):
        """Update the max temperature plot with the new value."""
        self.max_temp_data.append(max_temp)
        # Keep only the last 60 entries (assuming 1 entry per second for the last minute)
        if len(self.max_temp_data) > 60:
            self.max_temp_data.pop(0)
        self.max_temp_curve.setData(self.max_temp_data)



###----------------- Loading files with QFileDialog -----------------###
    def load_file(self):
        # For DXF automation mode we always open a fresh folder selection dialog
        if getattr(self.main_window, 'process_mode', 'DXF') == 'DXF':
            self.load_dxf_folder()
            return
        try:
            print("Load directory button clicked")
            import os
            # Resolve workspace root (three levels up from this file: src/ui/home_screen -> workspace)
            try:
                here = os.path.dirname(os.path.abspath(__file__))
                workspace_root = os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir))
            except Exception:
                workspace_root = os.getcwd()
            # Determine initial directory and title based on mode
            if self.main_window.process_mode == "DXF":
                # If configured to force a fixed DXF folder, always use it
                try:
                    from config import Config
                    if getattr(Config, 'LENMARK_DXF_USE_FIXED_DIR', False):
                        fixed_dir = getattr(Config, 'LENMARK_DXF_FIXED_DIR', r"C:\\LenmarkDXF")
                        try:
                            os.makedirs(fixed_dir, exist_ok=True)
                        except Exception:
                            pass
                        print(f"Selected directory: {fixed_dir}")
                        print(f"Opening directory {fixed_dir}...")
                        # Directly set without showing dialog; users will copy files here
                        self.main_window.get_input_directory(fixed_dir)
                        QMessageBox.information(self, "DXF Folder", f"Using fixed DXF folder:\n{fixed_dir}\n\nCopy img_XX.dxf files there and press Play.")
                        return
                except Exception:
                    pass
                initial_dir = os.path.join(workspace_root, "dxf_to_emd", "input")
                title = "Select DXF Directory"
            else:
                initial_dir = os.path.join(workspace_root, "dxf_to_emd", "output")
                title = "Select EMD Directory"

            if not os.path.exists(initial_dir):
                # Fallback to workspace root if the expected dir doesn't exist
                initial_dir = workspace_root

            # Use a non-native Qt dialog to avoid Windows native dialog hangs
            dialog = QFileDialog(self, title)
            dialog.setOption(QFileDialog.DontUseNativeDialog, True)
            dialog.setFileMode(QFileDialog.Directory)
            dialog.setOption(QFileDialog.ShowDirsOnly, True)
            dialog.setDirectory(initial_dir)
            dialog.setWindowModality(Qt.ApplicationModal)
            dialog.setWindowFlag(Qt.WindowStaysOnTopHint, True)

            if dialog.exec_() == QFileDialog.Accepted:
                selected_paths = dialog.selectedFiles()
                if selected_paths:
                    self.dirName = selected_paths[0]
                    print(f"Selected directory: {self.dirName}")
                    print(f"Opening directory {self.dirName}...")
                    self.main_window.get_input_directory(self.dirName)
                else:
                    print("No directory selected (empty selection)")
            else:
                print("Directory selection canceled")
        except Exception as e:
            print(f"Error in load_file: {e}")
            import traceback
            traceback.print_exc()

    def append_automation_log(self, message: str):
        # Append messages to console with a timestamp (log removed from UI)
        from datetime import datetime
        ts = datetime.now().strftime('%H:%M:%S')
        print(f"[{ts}] {message}")
        try:
            if hasattr(self, 'automationLogText') and self.automationLogText is not None:
                self.automationLogText.append(f"[{ts}] {message}")
        except Exception:
            pass

    # ---------------- New: Always-prompt DXF folder loader -----------------
    def load_dxf_folder(self):
        """Prompt user every time to pick a DXF folder and register its DXF files.

        Spec requirements implemented:
          1. Always show dialog (QFileDialog.getExistingDirectory)
          2. Warn + abort if canceled
          3. Scan for *.dxf (case-insensitive)
          4. Warn if none found
          5. If found: sort, store path, log folder + list, popup summary
          6. Populate QListWidget named 'dxfListWidget' if present
        """
        try:
            from PyQt5.QtWidgets import QMessageBox, QFileDialog
            import os
            # Choose initial directory (workspace root / last dir / current working dir)
            initial_dir = getattr(self.main_window, 'input_dir', None)
            if not initial_dir or not os.path.isdir(initial_dir):
                try:
                    here = os.path.dirname(os.path.abspath(__file__))
                    initial_dir = os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir, 'dxf_to_emd', 'input'))
                except Exception:
                    initial_dir = os.getcwd()
            # Use a non-native dialog for improved stability (native sometimes failed to appear)
            dialog = QFileDialog(self, "Select DXF Folder")
            dialog.setOption(QFileDialog.DontUseNativeDialog, True)
            dialog.setFileMode(QFileDialog.Directory)
            dialog.setOption(QFileDialog.ShowDirsOnly, True)
            dialog.setDirectory(initial_dir)
            folder = ''
            if dialog.exec_() == QFileDialog.Accepted:
                sel = dialog.selectedFiles()
                if sel:
                    folder = sel[0]
            if not folder:
                QMessageBox.warning(self, "DXF Folder", "No folder selected.")
                return
            # Scan for .dxf files
            try:
                entries = os.listdir(folder)
            except Exception as e:
                QMessageBox.warning(self, "DXF Folder", f"Failed to list folder: {e}")
                return
            dxf_files = [f for f in entries if f.lower().endswith('.dxf') and os.path.isfile(os.path.join(folder, f))]
            if not dxf_files:
                QMessageBox.warning(self, "DXF Folder", "No DXF files found in the selected folder.")
                return
            dxf_files.sort()  # alphabetical
            # Store folder for controller usage
            self.main_window.input_dir = folder
            self.main_window.layer_count = len(dxf_files)
            self.main_window.current_layer = 0
            # Emit automation logs
            ctrl = self.main_window.process_automation_controller
            ctrl.automation_log_signal.emit(f"📂 DXF folder changed → {folder}")
            # Log all file names (batch in one or multiple messages; here one per file for clarity)
            ctrl.automation_log_signal.emit("[DXF] File list:")
            for name in dxf_files:
                ctrl.automation_log_signal.emit(f" - {name}")
            # Update optional list widget
            list_widget = self.findChild(QListWidget, 'dxfListWidget')
            if list_widget is not None:
                list_widget.clear()
                list_widget.addItems(dxf_files)
            # Popup summary
            QMessageBox.information(self, "DXF Folder Loaded", f"✅ Found {len(dxf_files)} DXF files in:\n{folder}")
        except Exception as e:
            try:
                QMessageBox.warning(self, "DXF Folder", f"Unexpected error: {e}")
            except Exception:
                pass
            self.append_automation_log(f"[DXF] Error loading folder: {e}")

    # ------------- Unified Load File button handler -------------
    def _on_load_file_clicked(self):
        """Decide which load flow to use based on current process mode.

        DXF mode: delegate to controller's load_dxf_files_dialog (central logging & natural sort)
        EMD mode: fall back to original self.load_file() logic (legacy behaviour)
        """
        mode = getattr(self.main_window, "process_mode", "DXF")
        if mode == "DXF":
            ctrl = getattr(self.main_window, 'process_automation_controller', None)
            if ctrl is not None:
                try:
                    ctrl.load_dxf_files_dialog()
                    return
                except Exception as e:
                    self.append_automation_log(f"[DXF] Fallback to legacy loader due to error: {e}")
            # Fallback to local folder loader if controller path failed
            self.load_dxf_folder()
        else:
            # Legacy EMD flow
            self.load_file()
