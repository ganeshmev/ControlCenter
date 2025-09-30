from PyQt5.QtCore import QObject, pyqtSignal
from utils.helpers import run_async
import time
from config import Config
# TBD clean play pause process. use printer printing status to diferentiate between control and main printing sequence

class ProcessAutomationController(QObject):
    progress_update_signal = pyqtSignal(int)

    def __init__(self, main_window):
        super(ProcessAutomationController, self).__init__()
        self.main_window = main_window
        self.process_running = False
        self.worker_signals = None
        self.file_loaded = False
        self.main_window.file_loaded_signal.connect(self.check_file_loaded)

        # Connect the progress update signal to the slot
        self.progress_update_signal.connect(self.update_progress_bar)

    def update_progress_bar(self, value):
        """Slot to update the progress bar value."""
        self.main_window.home_screen.printProgressBar.setValue(value)

    def check_file_loaded(self, value):
        self.file_loaded = True # sets flag to true on completion of file loading



    def initialLevellingRecoat(self):
        """Perform the initial levelling recoat."""
        self.set_motion_control_buttons_enabled(False)
        
        layerHeight = self.main_window.printer_status.layerHeight
        
        if Config.DEVELOPMENT_MODE:
            layerHeight = 0.1

        initialLevellingHeight = self.main_window.printer_status.initialLevellingHeight
        
        if Config.DEVELOPMENT_MODE:
            initialLevellingHeight = 0.5


        recoatCount = int(initialLevellingHeight / layerHeight)
        sequence = self.main_window.printer_status.initialLevellingRecoatingSequence

        for i in range(recoatCount):
            if not self.process_running:
                break

            # Pause handling
            while not self.main_window.home_screen.playPauseButton.isChecked():
                if not self.process_running:
                    break
                time.sleep(1)  # Sleep for a short duration to avoid busy waiting

            if not self.process_running:
                break

            # Perform recoat operation
            sequence_replaced = replace_placeholders(sequence, self.main_window.printer_status)
            for line in sequence_replaced.split('\n'):
                self.main_window.moonraker_api.send_gcode(line)

        self.set_motion_control_buttons_enabled(True)

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
                #setpoint = setpoint - 2 # changed 
                temps = self.main_window.printer_status.chamberTemperatures
                if all(temps.get(pos, 0) >= setpoint for pos in ['middle-center']):
                    time.sleep(2) #wait 20 secs atleast for layer to heat
                    break
                if not self.process_running:
                    self.progress_update_signal.emit(0)
                    break
                time.sleep(1)  # Sleep for a short duration to avoid busy waiting

            # Pause handling
            while not self.main_window.home_screen.playPauseButton.isChecked():
                if not self.process_running:
                    break
                time.sleep(1)  # Sleep for a short duration to avoid busy waiting

            if not self.process_running:
                break

            # Perform recoat operation
            sequence_replaced = replace_placeholders(sequence, self.main_window.printer_status)
            for line in sequence_replaced.split('\n'):
                self.main_window.moonraker_api.send_gcode(line)

        self.set_motion_control_buttons_enabled(True)

    def dose_recoat_layer(self):
        """Perform a single recoat using the layer height from the parameters screen."""
        self.set_motion_control_buttons_enabled(False)  # Disable motion control buttons
        sequence = self.main_window.printer_status.printingRecoatingSequence
        sequence_replaced = replace_placeholders(sequence, self.main_window.printer_status)
        for line in sequence_replaced.split('\n'):
            self.main_window.moonraker_api.send_gcode(line)
        self.progress_update_signal.emit(100)
        self.set_motion_control_buttons_enabled(True)  # Re-enable motion control buttons

    def prepare_powder_loading(self):
        """Prepare for powder loading."""
        self.set_motion_control_buttons_enabled(False)
        sequence = self.main_window.printer_status.powderLoadingSequence
        sequence_replaced = replace_placeholders(sequence, self.main_window.printer_status)
        for line in sequence_replaced.split('\n'):
            self.main_window.moonraker_api.send_gcode(line)
        self.set_motion_control_buttons_enabled(True)

    def move_to_starting_sequence(self):
        """Execute the move to starting sequence."""
        self.set_motion_control_buttons_enabled(False)
        sequence = self.main_window.printer_status.moveToStartingSequence
        sequence_replaced = replace_placeholders(sequence, self.main_window.printer_status)
        for line in sequence_replaced.split('\n'):
            self.main_window.moonraker_api.send_gcode(line)
        self.set_motion_control_buttons_enabled(True)

    def prepare_for_part_removal_sequence(self):
        """Execute the prepare for part removal sequence."""
        self.set_motion_control_buttons_enabled(False)
        sequence = self.main_window.printer_status.prepareForPartRemovalSequence
        sequence_replaced = replace_placeholders(sequence, self.main_window.printer_status)
        for line in sequence_replaced.split('\n'):
            self.main_window.moonraker_api.send_gcode(line)
        self.set_motion_control_buttons_enabled(True)

    @run_async
    def start_printing_sequence(self, layer_count):
        """Start the main printing sequence."""
        self.set_motion_control_buttons_enabled(False)
        self.progress_update_signal.emit(0)
        # Step 1: Initial Levelling Recoat
        self.initialLevellingRecoat()
        self.progress_update_signal.emit(10)
        print("Initial Levelling Recoat done")

        # Step 2: Heated Buffer Recoat
        self.heatedBufferRecoat()
        self.progress_update_signal.emit(20)
        print("Heated Buffer Recoat done")

        ###### ---- Actual Printing Process ------- ######


        # Step 3 and 4: Mark laser and dose recoat layer until all layers are done
        
        for i in range(layer_count):
            if not self.process_running:
                self.progress_update_signal.emit(0)
                break

            # Pause handling
            while not self.main_window.home_screen.playPauseButton.isChecked():
                if not self.process_running:
                    self.progress_update_signal.emit(0)
                    break
                time.sleep(1)  # Sleep for a short duration to avoid busy waiting

            while True:

                # Wait for the chamber to reach the setpoint temperature

                setpoint = self.main_window.printer_status.chamberTemperatureSetpoint
                temps = self.main_window.printer_status.chamberTemperatures
                #setpoint = setpoint - 2 # changed
                if all(temps.get(pos, 0) >= setpoint for pos in ['middle-center']):
                    time.sleep(2) #wait 20 secs atleast for layer to heat
                    break
                if not self.process_running:
                    self.progress_update_signal.emit(0)
                    break
                time.sleep(1)  # Sleep for a short duration to avoid busy waiting

            if not self.process_running:
                self.progress_update_signal.emit(0)
                break


            #### Marking starts ###### 
            print("-------------------------------------------")

            print("Marking layer number: ", i+1)
            print(f"Marking for file: {self.main_window.file}")


            while not self.file_loaded:
                time.sleep(0.5)  # wait for file to be loaded onto scancard
                print("Waiting for file to get loaded...")

            print("ENTRY 1 - After file loaded")

            # Actual marking starts
            print("ENTRY 2 - About to send marking command")
            future = self.main_window.scancard.start_mark()
            print("ENTRY 3 - After sending marking command")
            response = future.result()
            time.sleep(5)  # Sleep for a short duration to avoid busy waiting \\ to ensure we get latest status
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

            print("ENTRY 6 - Beofre loading file at end of marking")
            if i!=layer_count-1:    
                self.main_window.pick_current_file()

            print("ENTRY 7 - After loading file at end of marking")

            # Dose recoat layer after marking one layer
            print("After Laser Recoating...")
            self.dose_recoat_layer()
            progress = int((i + 1) / layer_count * 60) + 20
            self.progress_update_signal.emit(progress)
          

        print("******************************")
        # Step 5: Final Heated Buffer Recoat --- make this optional
        self.heatedBufferRecoat()
        self.progress_update_signal.emit(100)

        self.set_motion_control_buttons_enabled(True)

        print("########### PRINTING DONE #############")

    def stop_process(self):
        """Stop the recoat process."""
        self.process_running = False
        self.main_window.home_screen.playPauseButton.setChecked(False)
        self.progress_update_signal.emit(0)

    def set_motion_control_buttons_enabled(self, enabled):
        """Enable or disable motion control buttons."""
        for button in self.main_window.control_screen.motion_control_buttons:
            button.setEnabled(enabled)

def replace_placeholders(sequence: str, printer_status) -> str:
        """Replace placeholders in the sequence with actual values from the printer_status model."""
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
            "{dosingHeight}": printer_status.dosingHeight  # Add dosingHeight
        }
        for placeholder, value in placeholders.items():
            sequence = sequence.replace(placeholder, str(value))
        return sequence