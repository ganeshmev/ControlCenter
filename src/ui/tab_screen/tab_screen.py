from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from ui.home_screen.home_screen import HomeScreen
from ui.control_screen.control_screen import ControlScreen


class TabScreen(QWidget):
    def __init__(self, main_window):
        super(TabScreen, self).__init__()
        self.main_window = main_window
        # Load the .ui file for tab screen
        try:
            uic.loadUi('ui/tab_screen/tab_screen.ui', self)
            print("TabScreen UI loaded successfully")
        except Exception as e:
            print(f"Failed to load TabScreen UI: {e}")

        # Find the QTabWidget
        self.tabWidget = self.findChild(QTabWidget, 'tabWidget')

        # Populate the tabs using the existing containers in the UI file
        self.load_home_tab()
        self.load_parameters_tab()
        self.load_control_tab()

    def load_home_tab(self):
        # Find the existing home tab
        home_tab = self.findChild(QWidget, 'home_tab')
        if home_tab:
            self.home_screen = HomeScreen(self.main_window)
            self.main_window.home_screen = self.home_screen  # Store reference in main_window
            # Now that HomeScreen exists, connect automation log signal to its handler
            try:
                self.main_window.process_automation_controller.automation_log_signal.connect(
                    self.home_screen.append_automation_log
                )
            except Exception as e:
                print(f"Failed to connect automation log signal: {e}")
            layout = QVBoxLayout(home_tab)
            layout.addWidget(self.home_screen)
            home_tab.setLayout(layout)
        else:
            print("Home tab not found in TabScreen UI")

    def load_parameters_tab(self):
        # Locate the existing parameters tab container (set objectName to "parameters_tab" in Qt Designer)
        parameters_tab = self.findChild(QWidget, 'parameters_tab')
        if parameters_tab:
            from ui.parameters_screen.parameters_screen import ParametersScreen
            self.parameters_screen = ParametersScreen(self.main_window)
            layout = QVBoxLayout(parameters_tab)
            layout.addWidget(self.parameters_screen)
            parameters_tab.setLayout(layout)
        else:
            print("Parameters tab not found in TabScreen UI")

    def load_control_tab(self):
        # Find the existing control tab by its object name as set in Qt Designer (e.g., "controlTab")
        control_tab = self.findChild(QWidget, 'control_tab')
        if control_tab:
            # Import ControlScreen only when needed
            self.control_screen = ControlScreen(self.main_window)
            self.main_window.control_screen = self.control_screen  # Store reference in main_window
            layout = QVBoxLayout(control_tab)
            layout.addWidget(self.control_screen)
            control_tab.setLayout(layout)
        else:
            print("Control tab not found in TabScreen UI")