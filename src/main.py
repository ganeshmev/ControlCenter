import sys
import gc
import logging
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from ui.main_window import MainWindow

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.debug("Starting application")
    # Ensure relative paths (e.g., ui/...) resolve by setting CWD to this file's directory (src)
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        logging.debug(f"Changed working directory to {script_dir}")
    except Exception as e:
        logging.warning(f"Failed to change working directory: {e}")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    logging.debug("Main window shown")

    # Set up a QTimer to trigger garbage collection periodically
    gc_timer = QTimer()
    gc_timer.timeout.connect(gc.collect)
    gc_timer.start(60000)  # Trigger garbage collection every 60 seconds
    logging.debug("Garbage collection timer started")

    try:
        sys.exit(app.exec_())
    except Exception as e:
        logging.error("Exception occurred", exc_info=True)

if __name__ == "__main__":
    main ()


     