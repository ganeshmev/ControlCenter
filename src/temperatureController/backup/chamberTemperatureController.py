from PyQt5.QtCore import QThread, pyqtSlot
import numpy as np
from simple_pid import PID
from .heaterBoard import HeaterBoard

class ChamberTemperatureController(QThread):
    def __init__(self, printer_status):
        super().__init__()
        self.heater_board = HeaterBoard()
        self.printer_status = printer_status

        # Connect the temperatures_updated signal to the control_heater slot
        self.printer_status.temperatures_updated.connect(self.control_heater)

        # Initialize PID controllers for each side
        # self.pid_bottom = PID(15, 0.000001, 0.001, setpoint=0)
        # self.pid_right = PID(15, 0.000001, 0.001, setpoint=0)
        # self.pid_top = PID(15, 0.000001, 0.001, setpoint=0)
        # self.pid_left = PID(15, 0.000001, 0.001, setpoint=0)

        self.pid_bottom = PID(500, 0.000001, 0.001, setpoint=0)
        self.pid_right = PID(500, 0.000001, 0.001, setpoint=0)
        self.pid_top = PID(500, 0.000001, 0.001, setpoint=0)
        self.pid_left = PID(500, 0.000001, 0.001, setpoint=0)

        # Set output limits for the PID controllers to clamp the integral factor
        self.pid_bottom.output_limits = (1, 99)
        self.pid_right.output_limits = (1, 99)
        self.pid_top.output_limits = (1, 99)
        self.pid_left.output_limits = (1, 99)

        # Store the previous setpoint to detect changes
        self.previous_setpoint = self.printer_status.chamberTemperatureSetpoint

    def reset_pids(self):
        """Reset the PID controllers."""
        self.pid_bottom.reset()
        self.pid_right.reset()
        self.pid_top.reset()
        self.pid_left.reset()

    @pyqtSlot(np.ndarray, dict)
    def control_heater(self, frame, chamberTemperatures):
        """Control the heater power based on the setpoint and actual temperatures."""
        setpoint = self.printer_status.chamberTemperatureSetpoint

        # Check if the setpoint has changed
        if setpoint != self.previous_setpoint:
            print(f"Setpoint changed from {self.previous_setpoint} to {setpoint}. Resetting PIDs.")
            self.reset_pids()
            self.previous_setpoint = setpoint

        temps = chamberTemperatures
        bottom_temp = temps.get('bottom-center', 0)
        right_temp = temps.get('middle-right', 0)
        top_temp = temps.get('top-center', 0)
        left_temp = temps.get('middle-left', 0)
        middle_center_temp = temps.get('middle-center', 0)

        # Update setpoints for each PID controller
        self.pid_bottom.setpoint = setpoint
        self.pid_right.setpoint = setpoint
        self.pid_top.setpoint = setpoint
        self.pid_left.setpoint = setpoint

        # Compute the control values
        control_bottom = int(self.pid_bottom(bottom_temp))
        control_right = int(self.pid_right(right_temp))
        control_top = int(self.pid_top(top_temp))
        control_left = int(self.pid_left(left_temp))

        # If middle-center temperature goes beyond the setpoint, reduce the output of other PIDs
        if middle_center_temp > setpoint:
            reduction_factor = 0.75
            control_bottom = int(control_bottom * reduction_factor)
            control_right = int(control_right * reduction_factor)
            control_top = int(control_top * reduction_factor)
            control_left = int(control_left * reduction_factor)

        # Clamp the control values between 1 and 99
        control_bottom = max(1, min(99, control_bottom))
        control_right = max(1, min(99, control_right))
        control_top = max(1, min(99, control_top))
        control_left = max(1, min(99, control_left))

        # Apply the control values to the heater board
        # self.heater_board.setHeaterPowers(control_bottom, control_bottom, control_right, control_right // 2, control_top, control_top, control_left, control_left // 2)
        # OLD LINE
        #self.heater_board.setHeaterPowers(control_left, control_left//2, control_top, control_top, control_right, control_right//2, control_bottom, control_bottom)  #// Set the heater powers ---CH8, CH7, CH6, CH5, CH4, CH3, CH2, CH1
        # NEW
        # Test
        # ###self.heater_board.setHeaterPowers(control_left, control_left, control_top, control_top, control_right, control_right, control_bottom, control_bottom)
        # self.heater_board.setHeaterPowers(0, 0, control_top, control_top, 0, 0, control_bottom, control_bottom)  #// Set the heater powers ---CH8-Left, CH7-Left, CH6-Back, CH5-Back, CH4-Right, CH3-Right, CH2-Front, CH1-Front
        # self.heater_board.setHeaterPowers(control_left, control_left , control_top, control_top, control_right//2, control_right, control_bottom, control_bottom//2)  #// Set the heater powers ---CH8, CH7, CH6, CH5, CH4, CH3, CH2, CH1
 
        self.heater_board.setHeaterPowers(control_left, control_left, control_top, control_top, control_right, control_right//1.5, control_bottom, control_bottom)
        # self.heater_board.setHeaterPowers(
        #     int(control_left // 1.15),
        #     int(control_left // 4.71),
        #     int(control_top // 1.15),
        #     int(control_top // 4.71),
        #     int(control_right // 1.15),
        #     int(control_right // 4.71),
        #     int(control_bottom // 1.15),
        #     int(control_bottom // 4.71)
        # )  #// Set the heater powers ---CH8, CH7, CH6, CH5, CH4, CH3, CH2, CH1

        # Log the control values for debugging
        # print(f"Control values - Bottom: {control_bottom}, Right: {control_right}, Top: {control_top}, Left: {control_left}")