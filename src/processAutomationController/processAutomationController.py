from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMetaObject, Qt, pyqtSlot
from PyQt5.QtWidgets import QFileDialog
import subprocess
from utils.helpers import run_async
import time
import os
from config import Config
from processAutomationController.dxf_handler import DxfAutomationMixin
from utils.dxf_handler import (
    select_and_list_dxf_files,
    display_dxf_summary_in_process_mode,
)

# Restored original ProcessAutomationController implementation

class ProcessAutomationController(QObject, DxfAutomationMixin):
    progress_update_signal = pyqtSignal(int)
    automation_log_signal = pyqtSignal(str)  # emits textual status updates for GUI log

    def __init__(self, main_window):
        """Initialize controller; ensure QObject base constructed first.

        Sets up state flags, connects UI button signals (if present), and prepares
        threading attributes for later DXF / LenMark automation. No long-running
        work or dialogs should occur here.
        """
        super().__init__()  # IMPORTANT: construct QObject base before using signals/slots
        self.main_window = main_window
        # Core process state
        self.process_running = False
        self.worker_signals = None
        self.file_loaded = False
        # Connect external signals
        try:
            self.main_window.file_loaded_signal.connect(self.check_file_loaded)
        except Exception:
            pass
        # DXF automation state (used by DxfAutomationMixin)
        self._dxf_files = []
        self._dxf_folder_selected = False
        self.loaded_dxf_files = []  # populated asynchronously
        # LenMark threaded automation holders
        self._lenmark_thread = None
        self._lenmark_worker = None
        # DXF loader / play threads
        self._dxf_loader_thread = None
        self._dxf_loader_worker = None
        self._dxf_play_thread = None
        self._dxf_play_worker = None
        # Progress signal hookup
        try:
            self.progress_update_signal.connect(self.update_progress_bar)
        except Exception:
            pass
        # Attempt to connect UI buttons if present
        try:
            if hasattr(self.main_window, 'home_screen') and self.main_window.home_screen:
                hs = self.main_window.home_screen
                if hasattr(hs, 'loadFileButton') and hs.loadFileButton is not None:
                    try:
                        hs.loadFileButton.clicked.disconnect()
                    except Exception:
                        pass
                    hs.loadFileButton.clicked.connect(self.load_dxf_files_dialog)
                if hasattr(hs, 'playPauseButton') and hs.playPauseButton is not None:
                    try:
                        hs.playPauseButton.toggled.disconnect()
                    except Exception:
                        pass
                    hs.playPauseButton.toggled.connect(self._play_button_clicked)
        except Exception:
            pass
        # Log ready state
        self.automation_log_signal.emit('[DXF] Controller initialized.')

    def heatedBufferRecoat(self):
        """Perform the heated buffer recoat."""
        self.set_motion_control_buttons_enabled(False)
        
        layerHeight = self.main_window.printer_status.layerHeight

        if Config.DEVELOPMENT_MODE:
            layerHeight = 0.1

        heatedBufferHeight = self.main_window.printer_status.heatedBufferHeight
       
        if Config.DEVELOPMENT_MODE:
            heatedBufferHeight = 0.5

        recoatCount = int(heatedBufferHeight / layerHeight)
        sequence = self.main_window.printer_status.heatedBufferRecoatingSequence

        for i in range(recoatCount):
            if not self.process_running:
                break

            while True:
                setpoint = self.main_window.printer_status.chamberTemperatureSetpoint
                temps = self.main_window.printer_status.chamberTemperatures
                if all(temps.get(pos, 0) >= setpoint for pos in ['middle-center']):
                    time.sleep(2)
                    break
                if not self.process_running:
                    self.progress_update_signal.emit(0)
                    break
                time.sleep(1)

            # Pause handling
            while not self.main_window.home_screen.playPauseButton.isChecked():
                if not self.process_running:
                    break
                time.sleep(1)

            if not self.process_running:
                break

            sequence_replaced = replace_placeholders(sequence, self.main_window.printer_status)
            for line in sequence_replaced.split('\n'):
                self.main_window.moonraker_api.send_gcode(line)

        self.set_motion_control_buttons_enabled(True)

    def dose_recoat_layer(self):
        """Perform a single recoat using the layer height from the parameters screen."""
        self.set_motion_control_buttons_enabled(False)
        sequence = self.main_window.printer_status.printingRecoatingSequence
        sequence_replaced = replace_placeholders(sequence, self.main_window.printer_status)
        for line in sequence_replaced.split('\n'):
            self.main_window.moonraker_api.send_gcode(line)
        self.progress_update_signal.emit(100)
        self.set_motion_control_buttons_enabled(True)

    def prepare_powder_loading(self):
        self.set_motion_control_buttons_enabled(False)
        sequence = self.main_window.printer_status.powderLoadingSequence
        sequence_replaced = replace_placeholders(sequence, self.main_window.printer_status)
        for line in sequence_replaced.split('\n'):
            self.main_window.moonraker_api.send_gcode(line)
        self.set_motion_control_buttons_enabled(True)

    def move_to_starting_sequence(self):
        self.set_motion_control_buttons_enabled(False)
        sequence = self.main_window.printer_status.moveToStartingSequence
        sequence_replaced = replace_placeholders(sequence, self.main_window.printer_status)
        for line in sequence_replaced.split('\n'):
            self.main_window.moonraker_api.send_gcode(line)
        self.set_motion_control_buttons_enabled(True)

    def prepare_for_part_removal_sequence(self):
        self.set_motion_control_buttons_enabled(False)
        sequence = self.main_window.printer_status.prepareForPartRemovalSequence
        sequence_replaced = replace_placeholders(sequence, self.main_window.printer_status)
        for line in sequence_replaced.split('\n'):
            self.main_window.moonraker_api.send_gcode(line)
        self.set_motion_control_buttons_enabled(True)

    @run_async
    def start_initial_levelling_recoating(self, layer_count):
        if self.process_running:
            print("Process already running.")
            return
        self.process_running = True
        self.progress_update_signal.emit(0)
        self.initialLevellingRecoat()
        self.progress_update_signal.emit(100)
        self.process_running = False

    @run_async
    def start_heated_buffer_recoating(self, layer_count):
        if self.process_running:
            print("Process already running.")
            return
        self.process_running = True
        self.progress_update_signal.emit(0)
        self.heatedBufferRecoat()
        self.progress_update_signal.emit(100)
        self.process_running = False

    @run_async
    def start_powder_loading(self, layer_count):
        if self.process_running:
            print("Process already running.")
            return
        self.process_running = True
        self.progress_update_signal.emit(0)
        self.prepare_powder_loading()
        self.progress_update_signal.emit(100)
        self.process_running = False

    @run_async
    def start_move_to_starting_position(self, layer_count):
        if self.process_running:
            print("Process already running.")
            return
        self.process_running = True
        self.progress_update_signal.emit(0)
        self.move_to_starting_sequence()
        self.progress_update_signal.emit(100)
        self.process_running = False

    @run_async
    def start_prepare_for_part_removal(self, layer_count):
        if self.process_running:
            print("Process already running.")
            return
        self.process_running = True
        self.progress_update_signal.emit(0)
        self.prepare_for_part_removal_sequence()
        self.progress_update_signal.emit(100)
        self.process_running = False

    @run_async
    def start_printing_sequence(self, layer_count):
        self.set_motion_control_buttons_enabled(False)
        self.progress_update_signal.emit(0)
        self.initialLevellingRecoat()
        self.progress_update_signal.emit(10)
        print("Initial Levelling Recoat done")
        self.heatedBufferRecoat()
        self.progress_update_signal.emit(20)
        print("Heated Buffer Recoat done")
        initial_temp = self.main_window.printer_status.chamberTemperatureSetpoint
        cooldown_temp = initial_temp - 5
        for i in range(layer_count):
            if i < 10:
                self.set_chamber_temp(initial_temp)
            else:
                self.set_chamber_temp(cooldown_temp)
            if not self.process_running:
                self.progress_update_signal.emit(0)
                break
            while not self.main_window.home_screen.playPauseButton.isChecked():
                if not self.process_running:
                    self.progress_update_signal.emit(0)
                    break
                time.sleep(1)
            while True:
                setpoint = self.main_window.printer_status.chamberTemperatureSetpoint
                temps = self.main_window.printer_status.chamberTemperatures
                if all(temps.get(pos, 0) >= setpoint for pos in ['middle-center']):
                    time.sleep(2)
                    break
                if not self.process_running:
                    self.progress_update_signal.emit(0)
                    break
                time.sleep(1)
            if not self.process_running:
                self.progress_update_signal.emit(0)
                break
            print("-------------------------------------------")
            print("Marking layer number: ", i+1)
            print(f"Marking for file: {self.main_window.file}")
            while not self.file_loaded:
                time.sleep(0.5)
                print("Waiting for file to get loaded...")
            print("ENTRY 1 - After file loaded")
            print("ENTRY 2 - About to send marking command")
            future = self.main_window.scancard.start_mark()
            print("ENTRY 3 - After sending marking command")
            _ = future.result()
            time.sleep(5)
            print("ENTRY 4 - checking scancard status")
            while self.main_window.printer_status.scancard_status == "Marking":
                print("Marking in progress...")
                time.sleep(1)
                if not self.process_running:
                    self.progress_update_signal.emit(0)
                    break
            print("ENTRY 5 - After marking done")
            if not self.process_running:
                self.progress_update_signal.emit(0)
                break
            print("ENTRY 6 - Before loading file at end of marking")
            if i != layer_count - 1:
                self.main_window.pick_current_file()
            print("ENTRY 7 - After loading file at end of marking")
            print("After Laser Recoating...")
            self.dose_recoat_layer()
            progress = int((i + 1) / layer_count * 60) + 20
            self.progress_update_signal.emit(progress)
        print("******************************")
        self.heatedBufferRecoat()
        self.progress_update_signal.emit(100)
        self.set_motion_control_buttons_enabled(True)
        print("########### PRINTING DONE #############")

    def stop_process(self):
        self.process_running = False
        self.main_window.home_screen.playPauseButton.setChecked(False)
        self.progress_update_signal.emit(0)
        # Attempt to stop worker thread if active
        if self._lenmark_worker and hasattr(self._lenmark_worker, 'request_stop'):
            try:
                self._lenmark_worker.request_stop()
            except Exception:
                pass
        # Stop any custom DXF runners
        if hasattr(self, '_dxf_play_worker') and self._dxf_play_worker and hasattr(self._dxf_play_worker, 'request_stop'):
            try:
                self._dxf_play_worker.request_stop()
            except Exception:
                pass

    @pyqtSlot()
    def load_dxf_files_dialog(self):
        """Open folder picker, load DXF file list, update logs and Process Mode box.

        Delegates to utils.dxf_handler helpers. Runs on GUI thread (blocking dialog).
        """
        folder, files = select_and_list_dxf_files(self.main_window, self.automation_log_signal)
        if not folder:
            return
        # Persist selections
        try:
            self.main_window.input_dir = folder
        except Exception:
            pass
        self.loaded_dxf_files = files or []
        # Display summary after popup (utils function already showed popup)
        try:
            display_dxf_summary_in_process_mode(self.main_window, folder, files)
        except Exception as e:
            self.automation_log_signal.emit(f"[DXF] Failed to update Process Mode summary: {e}")

    # DXF-related methods now provided by DxfAutomationMixin (load_dxf_files_dialog etc.)

    # _play_button_clicked provided by mixin

    # start_play_loaded_dxfs provided by mixin

    def set_motion_control_buttons_enabled(self, enabled):
        for button in self.main_window.control_screen.motion_control_buttons:
            button.setEnabled(enabled)

    # ---------------- DXF Multi-layer Automation (LenMark) -----------------
    # _ensure_dxf_input_dir provided by mixin

    # _gather_dxf_files provided by mixin

    # _wait_for_chamber_temperature provided by mixin

    # start_dxf_layer_marking provided by mixin

    # ---------------- Simplified DXF Mark Sequence (Spec-requested) -----------------
    # start_dxf_mark_sequence provided by mixin

    # ---------------- LenMark full sequential automation (Test Button) -----------------
    def run_lenmark_sequence(self):
        """Run full LenMark_3DS sequential DXF marking without freezing GUI.

        Implementation details:
          - Spawns a QThread with a worker object.
          - Worker calls utils.lenmark_automation.auto_mark_all_dxf_files()
            passing a stop_flag_getter tied to worker state.
          - Logs progress lines via automation_log_signal.emit.
          - Re-enables related buttons at end and logs completion.
          - If no DXF folder/files loaded, logs a warning and returns.
        """
        # Avoid duplicate runs
        if getattr(self, '_lenmark_thread', None) and self._lenmark_thread.isRunning():
            self.automation_log_signal.emit('[Lenmark] Sequence already running.')
            return

        folder = getattr(self.main_window, 'input_dir', None)
        if not folder or not os.path.isdir(folder):
            self.automation_log_signal.emit('❌ No DXF files loaded')
            return

        # Build DXF list (non-recursive, natural sort) if not already prepared
        dxf_paths = []
        try:
            names = [n for n in os.listdir(folder) if n.lower().endswith('.dxf') and os.path.isfile(os.path.join(folder, n))]
            import re as _re
            def _nat_key(s: str):
                return [int(t) if t.isdigit() else t.lower() for t in _re.split(r'(\d+)', s)]
            names.sort(key=_nat_key)
            dxf_paths = [os.path.join(folder, n) for n in names]
        except Exception:
            pass
        if not dxf_paths:
            self.automation_log_signal.emit('❌ No DXF files loaded')
            return

        # Disable interactive buttons (best-effort)
        try:
            hs = getattr(self.main_window, 'home_screen', None)
            if hs:
                for btn_name in ('loadFileButton', 'playPauseButton'):
                    btn = getattr(hs, btn_name, None)
                    if btn:
                        btn.setEnabled(False)
        except Exception:
            pass

        # Local import to avoid altering top-level imports per spec
        try:
            from utils.lenmark_automation import auto_mark_all_dxf_files  # type: ignore
        except Exception as e:
            self.automation_log_signal.emit(f'[Lenmark] Import failure: {e}')
            return

        controller = self

        class _LenmarkWorker(QObject):
            finished = pyqtSignal()
            log = pyqtSignal(str)

            def __init__(self, folder_path: str):
                super().__init__()
                self._folder = folder_path
                self._stop = False

            def request_stop(self):
                self._stop = True

            def _stop_flag(self):
                return self._stop

            @pyqtSlot()
            def run(self):
                def _log(msg: str):
                    self.log.emit(msg)
                try:
                    _log('[Lenmark] Starting sequence...')
                    auto_mark_all_dxf_files(self._folder, log=_log, stop_flag_getter=self._stop_flag)
                except Exception as e:
                    _log(f'[Lenmark] Sequence error: {e}')
                finally:
                    self.finished.emit()

        # Thread lifecycle
        self._lenmark_thread = QThread()
        self._lenmark_worker = _LenmarkWorker(folder)
        self._lenmark_worker.moveToThread(self._lenmark_thread)
        self._lenmark_worker.log.connect(self.automation_log_signal.emit)

        def _cleanup():
            # Re-enable buttons
            try:
                hs = getattr(controller.main_window, 'home_screen', None)
                if hs:
                    for btn_name in ('loadFileButton', 'playPauseButton'):
                        btn = getattr(hs, btn_name, None)
                        if btn:
                            btn.setEnabled(True)
            except Exception:
                pass
            controller.automation_log_signal.emit('✅ LenMark sequence complete.')
            try:
                controller._lenmark_thread.quit()
                controller._lenmark_thread.wait(3000)
            except Exception:
                pass
            try:
                controller._lenmark_thread.deleteLater()
            except Exception:
                pass
            controller._lenmark_thread = None
            controller._lenmark_worker = None

        self._lenmark_worker.finished.connect(_cleanup)
        self._lenmark_thread.started.connect(self._lenmark_worker.run)
        self._lenmark_thread.start()


def replace_placeholders(sequence: str, printer_status) -> str:
    placeholders = {
        "{layerHeight}": printer_status.layerHeight,
        "{initialLevellingHeight}": printer_status.initialLevellingHeight,
        "{heatedBufferHeight}": printer_status.heatedBufferHeight,
        "{powderLoadingExtraHeightGap}": printer_status.powderLoadingExtraHeightGap,
        "{bedTemperature}": printer_status.bedTemperature,
        "{volumeTemperature}": printer_status.volumeTemperature,
        "{chamberTemperature}": printer_status.chamberTemperature,
        "{p}": printer_status.p,
        "{i}": printer_status.i,
        "{d}": printer_status.d,
        "{powderLoadingHeight}": printer_status.initialLevellingHeight + 2 * printer_status.heatedBufferHeight + printer_status.partHeight,
        "{dosingHeight}": printer_status.dosingHeight
    }
    for placeholder, value in placeholders.items():
        sequence = sequence.replace(placeholder, str(value))
    return sequence
