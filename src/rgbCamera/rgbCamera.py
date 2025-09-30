import sys
import cv2
import time
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np

class RGBCamera(QThread):
    rgb_camera_frame_ready = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)  # Ensure the correct camera index
        if not self.cap.isOpened():
            print("Error: Could not open the IR camera.")
            exit()
    def run(self):
        """Runs the camera processing loop asynchronously."""
        self.running = True
        while self.running:
            start_time = time.time()
            self.update_frame()
            elapsed_time = time.time() - start_time
            sleep_time = max(0, (1/30) - elapsed_time)
            time.sleep(sleep_time)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            print("Error: Failed to capture an image.")
            time.sleep(0.5)  # Add a small delay before retrying
            return
        zoom_factor = 0.8

        # Define the region of interest (ROI) for cropping
        height, width, _ = frame.shape
        roi_size = int(min(height, width) * zoom_factor)   # Define the size of the inner square (half of the smaller dimension)
        x_center, y_center = width // 2, height // 2  # Center of the frame
        x1, y1 = x_center - roi_size // 2, y_center - roi_size // 2
        x2, y2 = x_center + roi_size // 2, y_center + roi_size // 2

        # Crop the frame to the ROI
        cropped_frame = frame[y1:y2, x1:x2]

        # Resize the cropped frame to the original frame size to achieve zoom effect
        zoomed_frame = cv2.resize(cropped_frame, (width, height))
        self.rgb_camera_frame_ready.emit(zoomed_frame)  # Emit the frame for display


