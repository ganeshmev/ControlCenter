from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QStackedWidget, QMessageBox
from ui.loading_screen.loading_screen import LoadingScreen
from ui.tab_screen.tab_screen import TabScreen
from config import Config
from models.printer_status import PrinterStatus
from PyQt5.QtCore import QTimer, pyqtSignal
from temperatureController.chamberTemperatureController import ChamberTemperatureController  # Ensure this import is present
from Feeltek.scanCard import Scancard  # Import Scancard
from processAutomationController.processAutomationController import ProcessAutomationController
from utils.helpers import run_async

if not Config.DEVELOPMENT_MODE:
    from temperatureController.heaterBoard import HeaterBoard
    from thermalCamera.thermal_camera import ThermalCamera
    from rgbCamera.rgbCamera import RGBCamera
    from moonrakerClient.moonrakerClient import MoonrakerAPI

import ui.resources.resource_rc  # Ensure resources are loaded
import traceback
import os
import time

class MainWindow(QMainWindow):
    file_loaded_signal = pyqtSignal(bool)  # Signal emitted when file is loaded

    def __init__(self):
        super(MainWindow, self).__init__()

        # Optimize window size for 1080p and 3840x2400 screens
        import sys
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        screen = app.primaryScreen()
        size = screen.size()
        # If ultra-high-res, use 3840x2400, else use 1920x1080
        if size.width() >= 3840 and size.height() >= 2160:
            self.setGeometry(0, 0, 3840, 2400)
        else:
            self.setGeometry(0, 0, 1920, 1080)
        self.showMaximized()  # Start maximized, user can resize

        # Initialize camera variables
        self.thermal_camera = None
        self.rgb_camera = None

        if not Config.DEVELOPMENT_MODE:
            try:
                # Initialize thermal camera
                self.thermal_camera = ThermalCamera(roi=(0, 11, 80, 74)) 
                self.thermal_camera.thermal_camera_frame_ready.connect(self.update_frame)
                self.thermal_camera.max_temp_signal.connect(self.update_max_temp)
                self.thermal_camera.start()

                #Initialize RGB camera
                self.rgb_camera = RGBCamera()
                self.rgb_camera.rgb_camera_frame_ready.connect(self.update_rgb_frame)
                self.rgb_camera.start()
            except Exception as e:
                print(f"Error initializing cameras: {e}")
                self.thermal_camera = None
                self.rgb_camera = None

        self.printer_status = PrinterStatus()  # Create an instance of the PrinterStatus model
        self.process_automation_controller = ProcessAutomationController(self)  # Initialize ProcessAutomationController

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)
        
        # Initialize HeaterBoard and ChamberTemperatureController if not in development mode
        if not Config.DEVELOPMENT_MODE:
            self.chamber_temp_controller = ChamberTemperatureController(self.printer_status)
        else:
            self.chamber_temp_controller = None

        # Initialize MoonrakerAPI if not in development mode
        if not Config.DEVELOPMENT_MODE:
            self.moonraker_api = MoonrakerAPI('http://192.168.0.231/')
        else:
            self.moonraker_api = MockMoonrakerAPI()

        # Initialize Scancard
        self.scancard = Scancard(self) if not Config.DEVELOPMENT_MODE else MockScancard(self)

        # Set up a QTimer to periodically check the Scancard status
        self.scancard_timer = QTimer(self)
        self.scancard_timer.timeout.connect(self.handle_scancard_status_change)
        self.scancard_timer.start(4000)  #  unit -> milliseconds  ### IMPORTANT - DON'T CHANGE 

        # Load sub UIs based on configuration
        self.load_loading_screen()
        self.load_tab_screen()
        self.switch_screen(self.loading_screen)
        self.layer_count = 0
        self.file = None
        self.current_layer = 0
        self.file_template = ""
        # Persistent process mode and input directory (used for DXF automation)
        self.process_mode = getattr(self, "process_mode", "DXF")
        self.input_dir = None

        # Adjust the size of the main window to fit its contents
        # self.adjustSize()

        self.process_automation_controller.progress_update_signal.connect(self.update_progress_bar)

    def update_progress_bar(self, value):
        self.home_screen.printProgressBar.setValue(value)
        self.control_screen.recoaterProgressBar.setValue(value)

    def load_loading_screen(self):
        self.loading_screen = LoadingScreen(self)
        self.stacked_widget.addWidget(self.loading_screen)
 
    def load_tab_screen(self):
        self.tab_screen = TabScreen(self)
        self.stacked_widget.addWidget(self.tab_screen)

    def switch_screen(self, widget):
        print(f"Switching to screen: {widget}")
        self.stacked_widget.setCurrentWidget(widget)
        self.adjustSize()  # Adjust size after switching screens

    def switch_to_tab_screen(self):
        self.switch_screen(self.tab_screen)

    def update_frame(self, frame, chamberTemperatures):
        if frame is not None and chamberTemperatures is not None:
            # Convert temps values to regular float
            converted_temps = {key: float(value) for key, value in chamberTemperatures.items()}
            self.printer_status.updateTemperatures(frame, converted_temps)

    def update_max_temp(self, max_temp):
        self.printer_status.updateMaxTemp(max_temp)

    def update_rgb_frame(self, frame):
        if frame is not None:
            self.printer_status.updateRGBFrame(frame)

######## -------- Scancard functions -------- ########




    # Add methods to interact with Scancard
    def start_scancard_mark(self):
        self.scancard.start_mark()

    def stop_scancard_mark(self):
        self.scancard.stop_mark()
        
    @run_async
    def handle_scancard_status_change(self):
        future = self.scancard.get_working_status()
        future.add_done_callback(self.update_scancard_status)

    def update_scancard_status(self, future):
        try:
            status = future.result()
                # print(status)
            self.printer_status.updateScancardStatus(status)
            self.control_screen.scanCardStatusLabel.setText("Status: " + self.printer_status.scancard_status)
        except Exception as e:
            print(f"Failed to update Scancard status: {e}")

    def open_scancard_file(self, file_path: str):
        close_future = self.scancard.close_file()
        close_future.add_done_callback(lambda f: self._handle_close_file_result_and_open(f, file_path))

    def set_file(self,file_path):
        try:
            self.file = file_path
            print(f"File: {self.file} has been selected")
            if ".emd" not in self.file:
                raise e
        except Exception as e:
            print("Invalid file format given - file is not a .emd file")
        


######## --------- Loading input directory function --------- ########

    def get_input_directory(self, dirName):
        print(f"Selected directory: {dirName}")
        self.input_dir = dirName
        # Branch by mode: EMD (API) vs DXF (Automation)
        if self.process_mode == "DXF":
            try:
                # Only count DXFs that match the intended naming scheme (e.g., img_01.dxf)
                files = [
                    f for f in os.listdir(dirName)
                    if os.path.isfile(os.path.join(dirName, f))
                    and f.lower().endswith('.dxf')
                    and f.lower().startswith('img_')
                ]
                files.sort()
                self.layer_count = len(files)
                print(f"[DXF] Found {self.layer_count} DXF files for printing (img_*.dxf).")
                QMessageBox.information(self, "DXF Files Loaded", f"Found {self.layer_count} DXF files for printing. Press play to start.")
                # Reset layer index for controller loop
                self.current_layer = 0
            except Exception as e:
                print(f"[DXF] Failed to enumerate DXF files: {e}")
                self.layer_count = 0
        else:
            # Legacy EMD flow
            self.layer_count = 0
            filenames = sorted(os.listdir(dirName))
            for filename in filenames:
                try:
                    file_path = os.path.join(dirName, filename)
                    if os.path.isfile(file_path):
                        print(f"Processing file {file_path}...")
                        if "emd" in filename:
                            self.layer_count += 1
                            if "_1." in filename:
                                print("Got the first layer file")
                                self.current_layer = 1
                                self.set_file(file_path)
                                self.open_file()
                                print(f"Loaded file {file_path}...")
                                self.process_automation_controller.file_loaded = True
                                self.file_template = self.file[:-5]
                                self.current_layer += 1
                        else:
                            print(f"Invalid file format: {file_path}...")
                except Exception as e:
                    print(f"Error: {e}...")
            print(f"Total number of layers: {self.layer_count}")
            import time
            time.sleep(2)



    def _handle_close_file_result_and_open(self, future, file_path: str):
        try:
            result = future.result()
            if result is None:
                raise ValueError("No result returned from close_file command")
            meaning = self._get_scancard_return_meaning(result.get("ret_value"))
            print(f"Close file result: {result} - {meaning}")
        except Exception as e:
            print(f"Failed to close Scancard file: {e}")
        finally:
            print("Executing finally block")

            self._open_scancard_file(file_path)

    def _open_scancard_file(self, file_path: str):
        print(f"Opening Scancard file: {file_path}")
        future = self.scancard.open_file(file_path)
        future.add_done_callback(lambda f: self._handle_open_file_result(f, file_path))

    def _handle_open_file_result(self, future, file_path: str):
        try:
            result = future.result()
            if result is None:
                raise ValueError("No result returned from open_file command")
            meaning = self._get_scancard_return_meaning(result.get("ret_value"))
            print(f"Open file result: {result} - {meaning}")
            self.update_file_info_label(file_path)
        except Exception as e:
            print(f"Failed to open Scancard file: {e}")

    def _get_scancard_return_meaning(self, ret_value):
        meanings = {
            1: "Execution successful",
            0: "Not executed",
            -1: "Failed to open",
            -2: "File does not exist"
        }
        return meanings.get(ret_value, "Unknown return value")

    def update_file_info_label(self, file_path: str):
        self.home_screen.fileInfoLabel.setText(file_path)

    def open_file(self):
        print(f"Opening file {self.file} in scancard")
        self.open_scancard_file(self.file)

    @run_async
    def pick_current_file(self):
        # take layer number to be printed
        print("LOADING NEXT LAYER FILE")  
        print(f"Loading file for layer {self.current_layer}")
       
    
        filename = self.file_template + str(int(self.current_layer)) + ".emd"
         
        # print(filename)
        self.set_file(filename)
        # print(f"Opening file {filename}")
        self.open_file()
        self.current_layer += 1

        self.file_loaded_signal.emit(True)

    def closeEvent(self, event):
        """Handle cleanup when the window is closed"""
        try:
            if self.thermal_camera is not None:
                self.thermal_camera.stop()
                self.thermal_camera.wait()
            if self.rgb_camera is not None:
                self.rgb_camera.stop()
                self.rgb_camera.wait()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        super().closeEvent(event)

class MockMoonrakerAPI:
    def __init__(self):
        print("MockMoonrakerAPI initialized")

    def send_gcode(self, cmd):
        time.sleep(1)
        print(f"MockMoonrakerAPI.send_gcode called with cmd: {cmd}")

    def query_status(self):
        print("MockMoonrakerAPI.query_status called")
        return {"status": "mock_status"}

    def query_temperatures(self):
        print("MockMoonrakerAPI.query_temperatures called")
        return {"temperatures": "mock_temperatures"}

class MockScancard:
    def __init__(self, main_window):
        print("MockScancard initialized")

    def start_mark(self):
        print("MockScancard.start_mark called")
        time.sleep(2)
        return MockFuture()

    def stop_mark(self):
        print("MockScancard.stop_mark called")

    def get_working_status(self):
        # print("MockScancard.get_working_status called")
        return MockFuture()

    def open_file(self, file_path):
        time.sleep(2)
        return MockFuture()

    def close_file(self):
        print("MockScancard.close_file called")
        return MockFuture()

class MockFuture:
    def add_done_callback(self, callback):
        # print("MockFuture.add_done_callback called")
        callback(self)

    def result(self):
        # print("MockFuture.result called")
        return {"ret_value": 1}  # Simulated response


