from PyQt5.QtCore import QObject, pyqtSlot
from utils.helpers import run_async
import subprocess
import time
import os
from config import Config

from typing import List, Tuple, Optional

class DxfAutomationMixin:
    """Mixin encapsulating DXF / LenMark automation routines.

    Converted to a plain Python mixin (no QObject inheritance) to avoid MRO
    conflicts when combined with a primary QObject subclass.
    Expects the following attributes/signals to exist on self (provided by the
    consuming controller):
      - self.main_window
      - self.automation_log_signal (pyqtSignal(str))
      - self.progress_update_signal (pyqtSignal(int))
      - self.process_running (bool flag)
      - self.loaded_dxf_files (list)
    """

    # (DXF folder loading removed; use utils.dxf_handler functions instead.)

    # ---------------- Play button handler for launching DXFs sequentially -----------------
    def _play_button_clicked(self, checked: bool):
        """Hook for Play button; launches DXF marking sequence if in DXF mode.

        If the button represents toggle, only start on checked True.
        """
        process_mode = getattr(self.main_window, 'process_mode', 'DXF')
        if not checked:
            return
        if process_mode != 'DXF':
            return
        self.start_play_loaded_dxfs()

    def start_play_loaded_dxfs(self):
        """Start background thread that launches each DXF via subprocess.Popen.

        Uses small delay between launches; UI remains responsive.
        """
        if getattr(self, '_dxf_play_thread', None) is not None:
            self.automation_log_signal.emit('[DXF] A DXF play sequence is already running.')
            return
        if not self.loaded_dxf_files:
            self.automation_log_signal.emit('[DXF] No DXF files loaded. Use Load File first.')
            return
        exe = getattr(Config, 'LENMARK_EXE_PATH', None)
        if not exe or not os.path.isfile(exe):
            self.automation_log_signal.emit(f'[DXF] LenMark executable not found: {exe}')
            return

        from PyQt5.QtCore import QThread, pyqtSignal
        class DxfPlayWorker(QObject):
            progress = pyqtSignal(int)
            log = pyqtSignal(str)
            finished = pyqtSignal()

            def __init__(self, exe_path: str, files: list[str], delay: float = 2.0):
                super().__init__()
                self._exe = exe_path
                self._files = files
                self._delay = delay
                self._stop = False

            def request_stop(self):
                self._stop = True

            def run(self):
                total = len(self._files)
                for idx, path in enumerate(self._files, start=1):
                    if self._stop:
                        self.log.emit('[DXF] Play sequence stopped by user.')
                        break
                    name = os.path.basename(path)
                    try:
                        subprocess.Popen([self._exe, path])
                        self.log.emit(f'[DXF] Launched: {name}')
                    except Exception as e:
                        self.log.emit(f'[DXF] Launch failed for {name}: {e}')
                    pct = int(idx / total * 100)
                    self.progress.emit(pct)
                    for _ in range(int(self._delay * 10)):
                        if self._stop:
                            break
                        time.sleep(0.1)
                self.finished.emit()

        self._dxf_play_thread = QThread()
        self._dxf_play_worker = DxfPlayWorker(exe, self.loaded_dxf_files)
        self._dxf_play_worker.moveToThread(self._dxf_play_thread)
        self._dxf_play_thread.started.connect(self._dxf_play_worker.run)
        self._dxf_play_worker.progress.connect(self.progress_update_signal.emit)
        self._dxf_play_worker.log.connect(self.automation_log_signal.emit)

        def _on_play_finished():
            self.automation_log_signal.emit('[DXF] ✅ Play sequence completed.')
            try:
                self.main_window.home_screen.playPauseButton.setChecked(False)
                self.main_window.home_screen.playPauseButton.setEnabled(True)
            except Exception:
                pass
            try:
                self._dxf_play_thread.quit()
                self._dxf_play_thread.wait(2000)
                self._dxf_play_thread.deleteLater()
            except Exception:
                pass
            self._dxf_play_thread = None
            self._dxf_play_worker = None

        self._dxf_play_worker.finished.connect(_on_play_finished)
        try:
            self.main_window.home_screen.playPauseButton.setEnabled(False)
        except Exception:
            pass
        self._dxf_play_thread.start()
        self.automation_log_signal.emit('[DXF] ▶️ Starting DXF play sequence in background...')

    # ---------------- DXF Multi-layer Automation (LenMark) -----------------
    def _ensure_dxf_input_dir(self):
        """Ensure self.main_window.input_dir is set; open a folder dialog if missing.
        Returns True if directory is valid, False otherwise.
        """
        path = getattr(self.main_window, 'input_dir', None)
        if path and os.path.isdir(path):
            return True
        try:
            from PyQt5.QtWidgets import QFileDialog
            folder = QFileDialog.getExistingDirectory(self.main_window, "Select DXF Folder")
        except Exception:
            folder = ''
        if folder and os.path.isdir(folder):
            self.main_window.input_dir = folder
            self.automation_log_signal.emit(f"[DXF] Selected input folder: {folder}")
            return True
        self.automation_log_signal.emit("[DXF] No folder selected; aborting DXF automation.")
        return False

    def _gather_dxf_files(self):
        """Collect DXF files matching img_*.dxf case-insensitive and sort.
        Populates self._dxf_files.
        """
        folder = getattr(self.main_window, 'input_dir', None)
        self._dxf_files = []
        if not folder or not os.path.isdir(folder):
            return
        for name in os.listdir(folder):
            lower = name.lower()
            if lower.startswith('img_') and lower.endswith('.dxf'):
                self._dxf_files.append(os.path.join(folder, name))
        def sort_key(p: str):
            base = os.path.basename(p)
            num_part = ''.join(ch for ch in base if ch.isdigit())
            try:
                return int(num_part)
            except Exception:
                return base.lower()
        self._dxf_files.sort(key=sort_key)
        self.automation_log_signal.emit(f"[DXF] Found {len(self._dxf_files)} DXF files.")

    def _wait_for_chamber_temperature(self):
        """Block until chamber reaches setpoint unless in DEVELOPMENT_MODE."""
        if Config.DEVELOPMENT_MODE:
            return
        setpoint = self.main_window.printer_status.chamberTemperatureSetpoint
        temps = self.main_window.printer_status.chamberTemperatures
        start = time.time()
        while True:
            temps = self.main_window.printer_status.chamberTemperatures
            if all(temps.get(pos, 0) >= setpoint for pos in ['middle-center']):
                break
            if not self.process_running:
                break
            if time.time() - start > 600:
                self.automation_log_signal.emit("[DXF] Temperature wait timeout; continuing anyway.")
                break
            time.sleep(1)

    @run_async
    def start_dxf_layer_marking(self):  # retained name for existing callers
        """Hands-free multi-layer DXF automation: import + mark each img_*.dxf sequentially.

        Updated to match new spec:
          - Logs precise messages
          - Sleeps briefly after import
          - Emits success / failure messages with ✅ / ❌ icons
        """
        if self.process_running:
            self.automation_log_signal.emit("[DXF] Process already running; request ignored.")
            return
        self.process_running = True
        self.progress_update_signal.emit(0)
        self.set_motion_control_buttons_enabled(False)
        try:
            if not self._ensure_dxf_input_dir():
                return
            self._gather_dxf_files()
            if not self._dxf_files:
                self.automation_log_signal.emit("[DXF] No matching img_*.dxf files found.")
                return
            total = len(self._dxf_files)
            try:
                from utils.lenmark_automation import import_dxf_only, run_mark_only
            except Exception as e:
                self.automation_log_signal.emit(f"❌ DXF Automation Failed: LenMark automation unavailable: {e}")
                return
            for idx, dxf_path in enumerate(self._dxf_files, start=1):
                if not self.process_running:
                    self.automation_log_signal.emit("[DXF] Process stopped externally.")
                    break
                filename = os.path.basename(dxf_path)
                try:
                    self._wait_for_chamber_temperature()
                    self.automation_log_signal.emit(f"[DXF] Importing file: {filename}")
                    import_dxf_only(dxf_path, log_cb=lambda m: self.automation_log_signal.emit(m))
                    time.sleep(1)
                    self.automation_log_signal.emit(f"[DXF] Starting Mark (F2)...")
                    run_mark_only(log_cb=lambda m: self.automation_log_signal.emit(m), close_after_mark=True)
                    self.automation_log_signal.emit(f"[DXF] ✅ Mark completed for {filename}")
                    self.dose_recoat_layer()
                except Exception as e:
                    self.automation_log_signal.emit(f"❌ DXF Automation Failed: {e}")
                    break
                progress = int(idx / total * 100)
                self.progress_update_signal.emit(progress)
            else:
                self.automation_log_signal.emit("✅ All DXF files marked successfully.")
        finally:
            self.set_motion_control_buttons_enabled(True)
            self.process_running = False
            self.progress_update_signal.emit(100 if self.progress_update_signal else 0)

    @run_async
    def start_dxf_mark_sequence(self):
        """Simplified sequence per spec:
        1. Launch/connect LenMark once implicitly per operation (each helper handles it)
        2. For every img_*.dxf in selected folder:
            - Import with import_dxf_only
            - Mark using run_mark_only (F2)
            - Wait 1-2 seconds (using 1.5s)
            - Update progress + log after success
        3. Close each DXF after marking (run_mark_only(close_after_mark=True) already issues close)
        4. Emit final success log or failure log.
        5. Respect self.process_running for external stop.
        """
        if self.process_running:
            self.automation_log_signal.emit("[DXF] Process already running; request ignored.")
            return
        self.process_running = True
        self.progress_update_signal.emit(0)
        completed_all = False
        try:
            self.main_window.home_screen.playPauseButton.setEnabled(False)
        except Exception:
            pass
        try:
            if not self._ensure_dxf_input_dir():
                return
            self._gather_dxf_files()
            if not self._dxf_files:
                self.automation_log_signal.emit("[DXF] No matching img_*.dxf files found.")
                return
            from utils.lenmark_automation import import_dxf_only, run_mark_only
            total = len(self._dxf_files)
            for idx, dxf_path in enumerate(self._dxf_files, start=1):
                if not self.process_running:
                    self.automation_log_signal.emit("[DXF] Process stopped externally.")
                    break
                filename = os.path.basename(dxf_path)
                try:
                    self.automation_log_signal.emit(f"[DXF] Importing {filename}")
                    import_dxf_only(dxf_path, log_cb=lambda m: self.automation_log_signal.emit(m))
                    self.automation_log_signal.emit(f"[DXF] Marking {filename}")
                    run_mark_only(log_cb=lambda m: self.automation_log_signal.emit(m), close_after_mark=True)
                    time.sleep(1.5)
                    self.automation_log_signal.emit(f"[DXF] ✅ Completed {filename}")
                    progress = int(idx / total * 100)
                    self.progress_update_signal.emit(progress)
                except Exception as e:
                    self.automation_log_signal.emit(f"❌ DXF automation failed: {e}")
                    break
            else:
                completed_all = True
                self.automation_log_signal.emit("✅ All DXF files marked successfully.")
        finally:
            self.process_running = False
            try:
                self.main_window.home_screen.playPauseButton.setEnabled(True)
                self.main_window.home_screen.playPauseButton.setChecked(False)
            except Exception:
                pass
            if completed_all:
                try:
                    if self.main_window.home_screen.printProgressBar.value() < 100:
                        self.progress_update_signal.emit(100)
                except Exception:
                    pass

    # ---------------- LenMark full sequential automation (Test Button) -----------------
    @run_async
    def run_lenmark_sequence(self):
        """Sequentially import & mark every .dxf in the selected folder using LenMark.

        Behavior (spec):
          - Validates folder + discovers .dxf files (natural sorted)
          - For each file logs:
              [i/N] Importing: name
              [i/N] Marking:   name
              ✅ Done: name
          - Uses helpers import_dxf_only + run_mark_only
          - Waits ~2s after marking (settle) before next file
          - Final success log: 🎯 All DXF files processed.
        Safe if no folder or empty; GUI remains responsive via @run_async.
        """
        if getattr(self, 'process_running', False):
            self.automation_log_signal.emit('[DXF] Another automation is already running; ignoring request.')
            return
        folder = getattr(self.main_window, 'input_dir', None)
        if not folder or not os.path.isdir(folder):
            self.automation_log_signal.emit('[DXF] No DXF folder selected. Use "Load File" first.')
            return
        try:
            entries = os.listdir(folder)
        except Exception as e:
            self.automation_log_signal.emit(f'[DXF] Failed to list directory: {e}')
            return
        dxf_files = [f for f in entries if f.lower().endswith('.dxf') and os.path.isfile(os.path.join(folder, f))]
        import re
        def natural_key(s: str):
            return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]
        dxf_files.sort(key=natural_key)
        if not dxf_files:
            self.automation_log_signal.emit('[DXF] No .dxf files found in folder.')
            return
        total = len(dxf_files)
        self.process_running = True
        try:
            if hasattr(self.main_window.home_screen, 'testLenmarkButton'):
                self.main_window.home_screen.testLenmarkButton.setEnabled(False)
            if hasattr(self.main_window.home_screen, 'playPauseButton'):
                self.main_window.home_screen.playPauseButton.setEnabled(False)
        except Exception:
            pass
        self.progress_update_signal.emit(0)
        try:
            try:
                from utils.lenmark_automation import import_dxf_only, run_mark_only
            except Exception as e:
                self.automation_log_signal.emit(f'[DXF] Automation helpers unavailable: {e}')
                return
            for idx, name in enumerate(dxf_files, start=1):
                if not self.process_running:
                    self.automation_log_signal.emit('[DXF] Automation stopped by user.')
                    break
                full_path = os.path.join(folder, name)
                self.automation_log_signal.emit(f'[{idx}/{total}] Importing: {name}')
                try:
                    import_dxf_only(full_path, log_cb=lambda m: self.automation_log_signal.emit(m))
                except Exception as e_imp:
                    self.automation_log_signal.emit(f'❌ Failed import: {name} ({e_imp}); skipping.')
                    continue
                if not self.process_running:
                    self.automation_log_signal.emit('[DXF] Stopped before marking.')
                    break
                self.automation_log_signal.emit(f'[{idx}/{total}] Marking: {name}')
                try:
                    run_mark_only(log_cb=lambda m: self.automation_log_signal.emit(m), close_after_mark=True)
                except Exception as e_mark:
                    self.automation_log_signal.emit(f'❌ Failed marking: {name} ({e_mark}); skipping.')
                    continue
                import time as _t
                settle = getattr(Config, 'LENMARK_POST_MARK_DELAY_SEC', 2.0)
                _t.sleep(settle)
                self.automation_log_signal.emit(f'✅ Done: {name}')
                pct = int(idx / total * 100)
                self.progress_update_signal.emit(pct)
            else:
                self.automation_log_signal.emit('🎯 All DXF files processed.')
                self.progress_update_signal.emit(100)
        finally:
            self.process_running = False
            try:
                if hasattr(self.main_window.home_screen, 'testLenmarkButton'):
                    self.main_window.home_screen.testLenmarkButton.setEnabled(True)
                if hasattr(self.main_window.home_screen, 'playPauseButton'):
                    self.main_window.home_screen.playPauseButton.setEnabled(True)
                    self.main_window.home_screen.playPauseButton.setChecked(False)
            except Exception:
                pass
        """Run a LenMark automation sequence over ALL .dxf files in the selected input directory.

        Spec behavior:
          1. Reads all .dxf in self.main_window.input_dir (alphabetical)
          2. For each file: import_dxf_only -> run_mark_only (F2) -> short wait
          3. Logs progress via automation_log_signal
          4. Updates progress bar (linear %)
          5. Skips failed files but continues
          6. Respects stop via self.process_running flag
          7. Runs in background thread (decorated with run_async)
          8. Final log on success: "🎯 All DXF files processed." unless stopped early
        """
        if self.process_running:
            self.automation_log_signal.emit("[DXF] Another automation is already running; ignoring request.")
            return
        folder = getattr(self.main_window, 'input_dir', None)
        if not folder or not os.path.isdir(folder):
            self.automation_log_signal.emit("[DXF] No DXF folder selected. Use 'Load File' first.")
            return
        try:
            entries = os.listdir(folder)
        except Exception as e:
            self.automation_log_signal.emit(f"[DXF] Failed to list directory: {e}")
            return
        dxf_files = [f for f in entries if f.lower().endswith('.dxf') and os.path.isfile(os.path.join(folder, f))]
        dxf_files.sort()
        if not dxf_files:
            self.automation_log_signal.emit("[DXF] No .dxf files found in folder.")
            return
        total = len(dxf_files)
        self.process_running = True
        self.progress_update_signal.emit(0)
        try:
            self.main_window.home_screen.playPauseButton.setEnabled(False)
            if hasattr(self.main_window.home_screen, 'testLenmarkButton'):
                self.main_window.home_screen.testLenmarkButton.setEnabled(False)
        except Exception:
            pass
        self.automation_log_signal.emit(f"🚀 Starting LenMark automation for {total} DXF file{'s' if total != 1 else ''}.")
        try:
            from utils.lenmark_automation import import_dxf_only, run_mark_only
        except Exception as e:
            self.automation_log_signal.emit(f"[DXF] Automation library unavailable: {e}")
            self.process_running = False
            return
        completed_all = False
        for idx, name in enumerate(dxf_files, start=1):
            if not self.process_running:
                self.automation_log_signal.emit("[DXF] Automation stopped by user.")
                break
            full_path = os.path.join(folder, name)
            try:
                self.automation_log_signal.emit(f"[{idx}/{total}] Importing: {name}")
                import_dxf_only(full_path, log_cb=lambda m: self.automation_log_signal.emit(m))
                if not self.process_running:
                    self.automation_log_signal.emit("[DXF] Automation stopped before marking.")
                    break
                self.automation_log_signal.emit(f"[{idx}/{total}] Marking: {name}")
                run_mark_only(log_cb=lambda m: self.automation_log_signal.emit(m), close_after_mark=True)
                time.sleep(1.0)
                self.automation_log_signal.emit(f"✅ Done: {name}")
            except Exception as e:
                self.automation_log_signal.emit(f"❌ Failed: {name} ({e}); skipping.")
            progress = int(idx / total * 100)
            self.progress_update_signal.emit(progress)
        else:
            completed_all = True
        if completed_all and self.process_running:
            self.automation_log_signal.emit("🎯 All DXF files processed.")
        self.process_running = False
        try:
            self.main_window.home_screen.playPauseButton.setEnabled(True)
            if hasattr(self.main_window.home_screen, 'testLenmarkButton'):
                self.main_window.home_screen.testLenmarkButton.setEnabled(True)
        except Exception:
            pass
        if completed_all:
            self.progress_update_signal.emit(100)
