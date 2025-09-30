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
        # Optimized parameters for thermal systems based on SLS research
        # Lower Kp for smoother response, higher Ki for steady-state accuracy, moderate Kd for stability
        self.pid_bottom = PID(50, 0.1, 5.0, setpoint=0)
        self.pid_right = PID(50, 0.1, 5.0, setpoint=0)
        self.pid_top = PID(50, 0.1, 5.0, setpoint=0)
        self.pid_left = PID(50, 0.1, 5.0, setpoint=0)

        # Set output limits for the PID controllers to clamp the integral factor
        self.pid_bottom.output_limits = (1, 99)
        self.pid_right.output_limits = (1, 99)
        self.pid_top.output_limits = (1, 99)
        self.pid_left.output_limits = (1, 99)

        # Set sample time for consistent control intervals (important for thermal systems)
        sample_time = 1.0  # 1 second sampling time for thermal stability
        self.pid_bottom.sample_time = sample_time
        self.pid_right.sample_time = sample_time
        self.pid_top.sample_time = sample_time
        self.pid_left.sample_time = sample_time

        # Store the previous setpoint to detect changes
        self.previous_setpoint = self.printer_status.chamberTemperatureSetpoint
        
        # Add temperature ramping for SLS thermal management
        self.max_temp_rate = 2.0  # Max 2°C per control cycle to prevent thermal shock
        self.current_target = 0.0  # Current ramped target temperature

    def reset_pids(self):
        """Reset the PID controllers."""
        self.pid_bottom.reset()
        self.pid_right.reset()
        self.pid_top.reset()
        self.pid_left.reset()

    def update_pid_parameters(self, kp=None, ki=None, kd=None):
        """Update PID parameters for all controllers dynamically."""
        if kp is not None:
            self.pid_bottom.Kp = kp
            self.pid_right.Kp = kp
            self.pid_top.Kp = kp
            self.pid_left.Kp = kp
        
        if ki is not None:
            self.pid_bottom.Ki = ki
            self.pid_right.Ki = ki
            self.pid_top.Ki = ki
            self.pid_left.Ki = ki
        
        if kd is not None:
            self.pid_bottom.Kd = kd
            self.pid_right.Kd = kd
            self.pid_top.Kd = kd
            self.pid_left.Kd = kd
        
        print(f"PID parameters updated - Kp: {kp}, Ki: {ki}, Kd: {kd}")

    def set_temperature_ramp_rate(self, rate):
        """Set the maximum temperature ramp rate in °C per control cycle."""
        self.max_temp_rate = rate
        print(f"Temperature ramp rate set to {rate}°C per cycle")

    @pyqtSlot(np.ndarray, dict)
    def control_heater(self, frame, chamberTemperatures):
        """Control the heater power based on the setpoint and actual temperatures."""
        setpoint = self.printer_status.chamberTemperatureSetpoint

        # Check if the setpoint has changed
        if setpoint != self.previous_setpoint:
            print(f"Setpoint changed from {self.previous_setpoint} to {setpoint}. Resetting PIDs.")
            self.reset_pids()
            self.previous_setpoint = setpoint
            self.current_target = self.current_target or setpoint  # Initialize if not set

        # Implement temperature ramping for SLS thermal management
        if abs(setpoint - self.current_target) > self.max_temp_rate:
            if setpoint > self.current_target:
                self.current_target += self.max_temp_rate
            else:
                self.current_target -= self.max_temp_rate
        else:
            self.current_target = setpoint

        temps = chamberTemperatures
        bottom_temp = temps.get('bottom-center', 0)
        right_temp = temps.get('middle-right', 0)
        top_temp = temps.get('top-center', 0)
        left_temp = temps.get('middle-left', 0)
        middle_center_temp = temps.get('middle-center', 0)

        # Update setpoints for each PID controller with ramped target
        self.pid_bottom.setpoint = self.current_target
        self.pid_right.setpoint = self.current_target
        self.pid_top.setpoint = self.current_target
        self.pid_left.setpoint = self.current_target

        # Compute the control values
        control_bottom = int(self.pid_bottom(bottom_temp))
        control_right = int(self.pid_right(right_temp))
        control_top = int(self.pid_top(top_temp))
        control_left = int(self.pid_left(left_temp))

        # Enhanced safety logic for SLS thermal management
        # 1. Center temperature override (existing)
        if middle_center_temp > self.current_target + 5:  # 5°C tolerance
            reduction_factor = 0.5  # More aggressive reduction for safety
            control_bottom = int(control_bottom * reduction_factor)
            control_right = int(control_right * reduction_factor)
            control_top = int(control_top * reduction_factor)
            control_left = int(control_left * reduction_factor)
            print(f"Center overheat protection activated: {middle_center_temp}°C > {self.current_target + 5}°C")

        # 2. Temperature gradient control - prevent excessive differences between zones
        temps_list = [bottom_temp, right_temp, top_temp, left_temp]
        temp_range = max(temps_list) - min(temps_list)
        if temp_range > 10:  # If temperature difference > 10°C between zones
            # Reduce power to hottest zones, increase power to coldest zones
            avg_temp = sum(temps_list) / len(temps_list)
            if bottom_temp > avg_temp + 3:
                control_bottom = int(control_bottom * 0.8)
            if right_temp > avg_temp + 3:
                control_right = int(control_right * 0.8)
            if top_temp > avg_temp + 3:
                control_top = int(control_top * 0.8)
            if left_temp > avg_temp + 3:
                control_left = int(control_left * 0.8)

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
        self.heater_board.setHeaterPowers(control_right, control_right//3, control_top, control_top, control_left, control_left, control_bottom, control_bottom)
        # self.heater_board.setHeaterPowers(0, 0, control_top, control_top, 0, 0, control_bottom, control_bottom)  #// Set the heater powers ---CH8, CH7, CH6, CH5, CH4, CH3, CH2, CH1
        # self.heater_board.setHeaterPowers(control_left, control_left , control_top, control_top, control_right//2, control_right, control_bottom, control_bottom//2)  #// Set the heater powers ---CH8, CH7, CH6, CH5, CH4, CH3, CH2, CH1
        
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

        # Enhanced logging for thermal analysis and SLS monitoring
        temp_range = max([bottom_temp, right_temp, top_temp, left_temp]) - min([bottom_temp, right_temp, top_temp, left_temp])
        print(f"Thermal Control - Target: {self.current_target:.1f}°C, "
              f"Temps: B:{bottom_temp:.1f} R:{right_temp:.1f} T:{top_temp:.1f} L:{left_temp:.1f} C:{middle_center_temp:.1f}, "
              f"Range: {temp_range:.1f}°C, "
              f"Powers: B:{control_bottom} R:{control_right} T:{control_top} L:{control_left}")