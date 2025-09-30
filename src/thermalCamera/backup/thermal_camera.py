import sys
import os
import csv
import datetime
import signal
import logging
import threading
import numpy as np
import cv2 as cv
from PyQt5.QtCore import QThread, pyqtSignal
from .mi48 import MI48, format_header, format_framestats  # Connects and communicates with the MI48 thermal camera
from .utils import data_to_frame, remap, cv_filter, RollingAverageFilter, connect_senxor


def replace_dead_pixels(frame, min_val=0, max_val=220):
    """Replace dead pixels with the average of surrounding 48 pixels."""
    for i in range(3, frame.shape[0] - 3):
        for j in range(3, frame.shape[1] - 3):
            if frame[i, j] < min_val or frame[i, j] > max_val:
                surrounding_pixels = [
                    frame[i-3, j-3], frame[i-3, j-2], frame[i-3, j-1], frame[i-3, j], frame[i-3, j+1], frame[i-3, j+2], frame[i-3, j+3],  # top row
                    frame[i-2, j-3], frame[i-2, j-2], frame[i-2, j-1], frame[i-2, j], frame[i-2, j+1], frame[i-2, j+2], frame[i-2, j+3],  # second row
                    frame[i-1, j-3], frame[i-1, j-2], frame[i-1, j-1], frame[i-1, j], frame[i-1, j+1], frame[i-1, j+2], frame[i-1, j+3],  # third row
                    frame[i, j-3], frame[i, j-2], frame[i, j-1], frame[i, j+1], frame[i, j+2], frame[i, j+3],  # middle row (excluding center)
                    frame[i+1, j-3], frame[i+1, j-2], frame[i+1, j-1], frame[i+1, j], frame[i+1, j+1], frame[i+1, j+2], frame[i+1, j+3],  # fifth row
                    frame[i+2, j-3], frame[i+2, j-2], frame[i+2, j-1], frame[i+2, j], frame[i+2, j+1], frame[i+2, j+2], frame[i+2, j+3],  # sixth row
                    frame[i+3, j-3], frame[i+3, j-2], frame[i+3, j-1], frame[i+3, j], frame[i+3, j+1], frame[i+3, j+2], frame[i+3, j+3]   # bottom row
                ]
                frame[i, j] = np.mean(surrounding_pixels)
    return frame

class ThermalCamera(QThread):
    thermal_camera_frame_ready = pyqtSignal(np.ndarray, dict)
    max_temp_signal = pyqtSignal(float)  # Add a new signal for the maximum temperature
    chip_temp_signal = pyqtSignal(float)  # new signal for die temperature


    def __init__(self, roi=(0, 0, 80, 80), com_port=None):
        """
        Initializes the thermal camera with a given ROI and optional COM port.
        Runs in a separate thread.
        """
        super().__init__()
        self.roi = roi    # (x1, y1, x2, y2) cam FOV crop
        self.com_port = com_port #cam com
        self.running = True
        self.latest_frame = None
        self.lock = threading.Lock()

        self.temps = {f"Section {i}": 0 for i in range(1, 37)}
        
        # Connect to the MI48 camera. detects automatically 
        self.mi48, self.connected_port, _ = connect_senxor(src=self.com_port) if self.com_port else connect_senxor()

        # Set camera parameters
        self.mi48.set_fps(10)                                                   # Set Frames Per Second (FPS)  15-->25
        self.mi48.disable_filter(f1=True, f2=True, f3=True)                     # Disable all filters
        self.mi48.set_filter_1(85)                                              # Set internal filter sett 1 to 85
        self.mi48.enable_filter(f1=True, f2=False, f3=False, f3_ks_5=False)
        self.mi48.set_offset_corr(0.0)                                          # Set offset correction to 0.0
        self.mi48.set_sens_factor(100)       # Set sensitivity factor to 100
        
        # Start streaming                                 
        self.mi48.start(stream=True, with_header=True)

        self.dminav = RollingAverageFilter(N=10)
        self.dmaxav = RollingAverageFilter(N=10)
               
        # ----------- BEGIN: Temperature Grid Logging Setup -----------raju
        self.log_interval = 1.0  # seconds between log entries; change if you want different interval
        self._last_log_time = 0
    
        log_dir = r"C:\Users\SLS Machine\Desktop\thermal_logs"  # <--- PUT YOUR FOLDER PATH HERE
        os.makedirs(log_dir, exist_ok=True)   # <--- Creates folder if not present
        today = datetime.datetime.now().strftime('%Y%m%d')
        log_base = os.path.join(log_dir, f"thermal_grid_log_{today}")
        idx = 1
        while os.path.exists(f"{log_base}_{idx}.csv"):
            idx += 1
        self.log_filename = f"{log_base}_{idx}.csv"

        self.section_order = [f"Section {i}" for i in range(1, 37)]

        with open(self.log_filename, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp'] + self.section_order)
        # ----------- END: Temperature Grid Logging Setup -----------raju


    def run(self):
        """Runs the camera processing loop asynchronously."""
        while self.running:
            self.process_frame()

    def process_frame(self):
        """Processes a frame: crops ROI, calculates temperatures, overlays grid and text."""
       
        try:
            data, header = self.mi48.read()
            if data is None:
                return
            
            # ---- update: for getting die temperature
            if header and 'senxor_temperature' in header:
                chip_temp = header['senxor_temperature']
                self.chip_temp_signal.emit(chip_temp)

            # Calculate min/max temperatures
            min_temp = self.dminav(data.min())
            max_temp = self.dmaxav(data.max())

            # Convert raw data to an image frame
            frame = data_to_frame(data, (80, 62), hflip=True)

            # Replace dead pixels
            frame = replace_dead_pixels(frame)

            # Clip the frame to the min/max temperatures
            frame = np.clip(frame, min_temp, max_temp)

            # Vertical flip and rotate
            #frame = cv.flip(frame, 1)
            frame = cv.rotate(frame, cv.ROTATE_90_CLOCKWISE)
            frame_height, frame_width = frame.shape[:2]  # After rotation


            # Apply filters
            filt_frame = cv_filter(remap(frame), {'blur_ks': 3, 'd': 5, 'sigmaColor': 27, 'sigmaSpace': 27},  #Remaps temperature values for visualization
                                use_median=True, use_bilat=True, use_nlm=False)                            #Applies smoothing filters to reduce noise.

           # Crop to ROI
            x1, y1, x2, y2 = self.roi

            # Ensure width and height are divisible by 6 to avoid region overflow
            # Clip x2/y2 to not exceed actual frame size
            x2 = min(x2, frame_width)
            y2 = min(y2, frame_height)

            # Ensure divisible by 6
            roi_width = x2 - x1 - ((x2 - x1) % 6)
            roi_height = y2 - y1 - ((y2 - y1) % 6)
            x2 = x1 + roi_width
            y2 = y1 + roi_height


            roi_frame = filt_frame[y1:y2, x1:x2]


            # Apply thermal color mapping
            roi_frame = cv.applyColorMap(roi_frame, cv.COLORMAP_INFERNO)

            # Resize the frame to make it larger
            roi_frame = cv.resize(roi_frame, (600, 600), interpolation=cv.INTER_LINEAR)

            # Draw the 3×3 grid
            self.draw_grid(roi_frame)
            
            frame = frame[y1:y2, x1:x2]  # Crop thermal data same as ROI
            x1, y1, x2, y2 = 0, 0, roi_width, roi_height  # Reset coords for calc

            # Calculate section temperatures
            temps = self.calculate_temperatures(frame, x1, y1, x2, y2)

            # Overlay text on the image
            self.overlay_text(roi_frame, temps)

            # Draw a white rectangle around the point of maximum temperature
            max_temp_loc = np.unravel_index(np.argmax(frame, axis=None), frame.shape)
            max_temp_loc = (max_temp_loc[1] - x1, max_temp_loc[0] - y1)  # Adjust for ROI
            max_temp_loc = (max_temp_loc[0] * 600 // (x2 - x1), max_temp_loc[1] * 600 // (y2 - y1))  # Scale to resized frame
            cv.rectangle(roi_frame, (max_temp_loc[0] - 5, max_temp_loc[1] - 5), (max_temp_loc[0] + 5, max_temp_loc[1] + 5), (255, 255, 255), 1)

            # Emit the maximum temperature after dead pixel correction
            self.max_temp_signal.emit(frame.max())

            # Store the latest frame for streaming
            with self.lock:
                self.latest_frame = roi_frame
                       
            # ----------- BEGIN: Temperature Grid Logging -----------raju
            now = datetime.datetime.now()
            now_ts = now.timestamp()
            if now_ts - self._last_log_time >= self.log_interval:
                self._last_log_time = now_ts
                row = [now.strftime('%Y-%m-%d %H:%M:%S')] + [temps.get(sec, 0) for sec in self.section_order]
                with open(self.log_filename, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(row)
            # ----------- END: Temperature Grid Logging -----------raju

            self.thermal_camera_frame_ready.emit(roi_frame, temps)  # Emit the frame for display
            if DEVELOPMENT_MODE: # type: ignore
                cv.imshow("Thermal Grid (Thermogram)", roi_frame)
                if cv.waitKey(1) & 0xFF == ord('q'):
                    self.stop()

        except Exception as e:
            logging.error(f"Error processing frame: {e}")

    def draw_grid(self, frame):
        """Draws a 3×3 grid overlay on the thermal feed."""
        try:
            h, w = frame.shape[:2]     # Get frame dimensions
            step_w, step_h = w // 6, h // 6    # Divide width and height into 3 sections to get 3x3 grid

            # Draw vertical lines
            for i in range(1, 6):
                x = i * step_w
                cv.line(frame, (x, 0), (x, h), (255, 255, 255), 1)

            # Draw horizontal lines
            for i in range(1, 6):
                y = i * step_h
                cv.line(frame, (0, y), (w, y), (255, 255, 255), 1)
        except Exception as e:
            logging.error(f"Error drawing grid: {e}")

    def calculate_temperatures(self, frame, x1, y1, x2, y2):
        """Calculates average temperatures for a 6×6 grid."""
        try:
            w, h = x2 - x1, y2 - y1
            section_w, section_h = w // 6, h // 6

            temps = {}
            count = 1

            for row in range(6):
                for col in range(6):
                    x_start = x1 + col * section_w
                    x_end = x1 + (col + 1) * section_w if col < 5 else x2  # use exact x2 on last column

                    y_start = y1 + row * section_h
                    y_end = y1 + (row + 1) * section_h if row < 5 else y2  # use exact y2 on last row

                    region = frame[y_start:y_end, x_start:x_end]
                    avg = float(np.mean(region)) if region.size > 0 else 0.0

                    if np.isnan(avg):
                        avg = 0.0

                    temps[f"Section {count}"] = avg
                    count += 1

                 # ⬇️ Add compatibility mapping for old 3×3 heater controller names
            compat_map = {
                'top-left': (
                        temps.get('Section 1', 0) + temps.get('Section 2', 0) +
                        temps.get('Section 7', 0) + temps.get('Section 8', 0)
                    ) / 4,

                    'top-center': (
                        temps.get('Section 3', 0) + temps.get('Section 4', 0) +
                        temps.get('Section 9', 0) + temps.get('Section 10', 0)
                    ) / 4,

                    'top-right': (
                        temps.get('Section 5', 0) + temps.get('Section 6', 0) +
                        temps.get('Section 11', 0) + temps.get('Section 12', 0)
                    ) / 4,

                    'middle-left': (
                        temps.get('Section 13', 0) + temps.get('Section 14', 0) +
                        temps.get('Section 19', 0) + temps.get('Section 20', 0)
                    ) / 4,

                    'middle-center': (
                        temps.get('Section 15', 0) + temps.get('Section 16', 0) +
                        temps.get('Section 21', 0) + temps.get('Section 22', 0)
                    ) / 4,

                    'middle-right': (
                        temps.get('Section 17', 0) + temps.get('Section 18', 0) +
                        temps.get('Section 23', 0) + temps.get('Section 24', 0)
                    ) / 4,

                    'bottom-left': (
                        temps.get('Section 25', 0) + temps.get('Section 26', 0) +
                        temps.get('Section 31', 0) + temps.get('Section 32', 0)
                    ) / 4,

                    'bottom-center': (
                        temps.get('Section 27', 0) + temps.get('Section 28', 0) +
                        temps.get('Section 33', 0) + temps.get('Section 34', 0)
                    ) / 4,

                    'bottom-right': (
                        temps.get('Section 29', 0) + temps.get('Section 30', 0) +
                        temps.get('Section 35', 0) + temps.get('Section 36', 0)
                    ) / 4,
                    
}
            temps.update(compat_map)

            self.temps = temps
            return self.temps

        except Exception as e:
            logging.error(f"Error calculating temperatures: {e}")
            return self.temps

    
    def overlay_text(self, frame, temps):
        """Overlays temperature values on the image for a 6×6 grid."""
        try:
            h, w = frame.shape[:2]
            section_w, section_h = w // 6, h // 6  # Updated for 6×6 grid

            font = cv.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            color = (255, 255, 255)
            thickness = 1

            count = 1
            for row in range(6):
                for col in range(6):
                    x = col * section_w + section_w // 4
                    y = row * section_h + section_h // 2
                    temp_val = temps.get(f"Section {count}", 0)
                    cv.putText(frame, f"{temp_val:.1f}°C", (x, y), font, font_scale, color, thickness)
                    cv.putText(frame, f"{count}", (col * section_w + 5, row * section_h + 15), font, 0.4, (0, 255, 0), 1)
                    count += 1
        except Exception as e:
            logging.error(f"Error overlaying text: {e}")


    def stop(self):
        """Stops the camera."""
        self.running = False
        self.mi48.stop()
        cv.destroyAllWindows()

