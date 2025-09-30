# chamberTemperatureController.py  — updated for CH2..CH5 control (no CH1)
from PyQt5.QtCore import QThread, pyqtSlot
import numpy as np
from simple_pid import PID
from .heaterBoard import HeaterBoard

class ChamberTemperatureController(QThread):
    def __init__(self, printer_status):
        super().__init__()
        self.heater_board = HeaterBoard()
        self.printer_status = printer_status

        # Listen to your existing signal (frame, temperatures_dict)
        self.printer_status.temperatures_updated.connect(self.control_heater)
        # fix (assuming you pass the ThermalCamera instance as printer_status)
        # self.printer_status.thermal_camera_frame_ready.connect(self.control_heater)

        # ---------------- PID per logical channel ----------------
        # Mapping (from your 6x6->3x3 keys):
        #   CH2 -> avg(bottom-left, bottom-center, bottom-right)      (bottom row)
        #   CH3 -> avg(top-right, middle-right, bottom-right)         (right column)
        #   CH4 -> avg(top-left, top-center, top-right)               (top row)
        #   CH5 -> avg(top-left, middle-left, bottom-left)            (left column)
        #
        # # sane starter gains; adjust if needed
        # self.pid_bottom = PID(8.0, 0.03, 0.8, setpoint=0)   # CH2
        # self.pid_right  = PID(8.0, 0.03, 0.8, setpoint=0)   # CH3
        # self.pid_top    = PID(8.0, 0.03, 0.8, setpoint=0)   # CH4
        # self.pid_left   = PID(8.0, 0.03, 0.8, setpoint=0)   # CH5

        self.pid_bottom = PID(500, 0.05, 0.8, setpoint=0)
        self.pid_right = PID(500, 0.05, 0.8, setpoint=0)
        self.pid_top = PID(500, 0.05, 0.8, setpoint=0)
        self.pid_left = PID(500, 0.05, 0.8, setpoint=0)

        for pid in (self.pid_bottom, self.pid_right, self.pid_top, self.pid_left):
            pid.output_limits = (0, 99)     # MCU 0..99 + anti-windup
            pid.sample_time = None          # compute on each signal

        # Slew-limit to avoid sudden jumps on SSR/relays
        self._last_out = {"ch2": 0, "ch3": 0, "ch4": 0, "ch5": 0}
        self._slew_step = 10  # max change per control tick

        # Light EWMA smoothing on temps + spike clamp
        self._filt = {"ch2": None, "ch3": None, "ch4": None, "ch5": None}
        self._alpha = 0.30      # 0..1  (lower = smoother)
        self._max_step_c = 3.0  # clamp per-frame ΔT (°C)

        # Keep last setpoint to reset PIDs on change
        self.previous_setpoint = getattr(self.printer_status, "chamberTemperatureSetpoint", 0)

    # ---------- helpers ----------
    def _ewma(self, key, new_val):
        prev = self._filt[key]
        if prev is not None:
            lo, hi = prev - self._max_step_c, prev + self._max_step_c
            new_val = min(hi, max(lo, new_val))
        a = self._alpha
        sm = (1 - a) * (prev if prev is not None else new_val) + a * new_val
        self._filt[key] = sm
        return sm

    def _slew(self, key, target_out):
        last = self._last_out[key]
        step = self._slew_step
        delta = max(-step, min(step, target_out - last))
        out = int(round(last + delta))
        self._last_out[key] = out
        return out

    def reset_pids(self):
        self.pid_bottom.reset()
        self.pid_right.reset()
        self.pid_top.reset()
        self.pid_left.reset()

    # ---------- main control ----------
    @pyqtSlot(np.ndarray, dict)
    def control_heater(self, _frame, chamberTemperatures):
        """Closed-loop control using CH2..CH5. No CH1 is driven."""
        setpoint = getattr(self.printer_status, "chamberTemperatureSetpoint", 90.0)
        self.printer_status.chamberTemperatureSetpoint = setpoint

        # Reset PIDs if setpoint changed
        if setpoint != self.previous_setpoint:
            print(f"[Chamber] Setpoint changed {self.previous_setpoint} -> {setpoint}. Resetting PIDs.")
            self.reset_pids()
            self.previous_setpoint = setpoint

        t = chamberTemperatures  # 3×3 compatibility keys emitted by your 6×6 camera code

        # -------- FEEDBACK (exact mapping) --------
        # CH2 (bottom row)
        ch2_meas = np.mean([
            t.get('bottom-left', 0.0),
            t.get('bottom-center', 0.0),
            t.get('bottom-right', 0.0),
        ])

        # CH3 (right column)
        ch3_meas = np.mean([
            t.get('top-right', 0.0),
            t.get('middle-right', 0.0),
            t.get('bottom-right', 0.0),
        ])

        # CH4 (top row)
        ch4_meas = np.mean([
            t.get('top-left', 0.0),
            t.get('top-center', 0.0),
            t.get('top-right', 0.0),
        ])

        # CH5 (left column)
        ch5_meas = np.mean([
            t.get('top-left', 0.0),
            t.get('middle-left', 0.0),
            t.get('bottom-left', 0.0),
        ])

        # Update setpoints
        self.pid_bottom.setpoint = setpoint
        self.pid_right.setpoint  = setpoint
        self.pid_top.setpoint    = setpoint
        self.pid_left.setpoint   = setpoint

        # Smooth measurements
        ch2_f = self._ewma("ch2", float(ch2_meas))
        ch3_f = self._ewma("ch3", float(ch3_meas))
        ch4_f = self._ewma("ch4", float(ch4_meas))
        ch5_f = self._ewma("ch5", float(ch5_meas))

        # PID outputs
        o2 = float(self.pid_bottom(ch2_f))
        o3 = float(self.pid_right(ch3_f))
        o4 = float(self.pid_top(ch4_f))
        o5 = float(self.pid_left(ch5_f))

        # Central over-temp moderation (your idea)
        middle_center_temp = t.get('middle-center', 0.0)
        if middle_center_temp > setpoint:
            factor = 0.75
            o2 *= factor; o3 *= factor; o4 *= factor; o5 *= factor

        # Clamp + slew-limit
        clamp_int = lambda v: int(max(0, min(99, round(v))))
        ch2 = self._slew("ch2", clamp_int(o2))
        ch3 = self._slew("ch3", clamp_int(o3))
        ch4 = self._slew("ch4", clamp_int(o4))
        ch5 = self._slew("ch5", clamp_int(o5))

        # -------- SEND TO BOARD --------
        # Preferred: your 4-arg API (order here is CH2,CH3,CH4,CH5).
        # If your board is still on the old 8-arg API, we fall back and keep CH1=0 (unused).
        try:
            self.heater_board.setHeaterPowers(ch5, ch4, ch3, ch2)
        except TypeError:
            # Legacy 8-arg order [CH8, CH7, CH6, CH5, CH4, CH3, CH2, CH1]
            # Duplicate pairs if your old hardware used two outputs per side; CH1=0 as requested.
            self.heater_board.setHeaterPowers(
                ch5, ch5,   # CH8, CH7  (left)
                ch4, ch4,   # CH6, CH5  (top)
                ch3, ch3,   # CH4, CH3  (right)
                ch2, 0      # CH2, CH1  (bottom, CH1 unused)
            )

        # Optional debug:
        # print(f"SP={setpoint:.1f} | CH2(btm)={ch2_f:.1f}->{ch2}  CH3(rgt)={ch3_f:.1f}->{ch3}  CH4(top)={ch4_f:.1f}->{ch4}  CH5(lft)={ch5_f:.1f}->{ch5}")
