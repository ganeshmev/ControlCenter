from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QLineEdit, QPushButton, QPlainTextEdit
import yaml

class ParametersScreen(QWidget):
    def __init__(self, main_window):
        super(ParametersScreen, self).__init__()
        self.main_window = main_window
        self.printer_status = main_window.printer_status  # Assuming main_window has a printer_status attribute

        try:
            uic.loadUi('ui/parameters_screen/parameters_screen.ui', self)
            print("ParametersScreen UI loaded successfully")
        except Exception as e:
            print(f"Failed to load ParametersScreen UI: {e}")

        # Initialize all QLineEdit widgets
        self.layerHeightLineEdit = self.findChild(QLineEdit, "layerHeightLineEdit")
        self.initialLevellingHeightLineEdit = self.findChild(QLineEdit, "initialLevellingHeightLineEdit")
        self.heatedBufferHeightLineEdit = self.findChild(QLineEdit, "heatedBufferHeightLineEdit")
        self.powderLoadingExtraHeightGapLineEdit = self.findChild(QLineEdit, "powderLoadingExtraHeightGapLineEdit")
        self.bedTemperatureLineEdit = self.findChild(QLineEdit, "bedTemperatureLineEdit")
        self.volumeTemberatureLineEdit = self.findChild(QLineEdit, "volumeTemberatureLineEdit")
        self.chamberTemperatureLineEdit = self.findChild(QLineEdit, "chamberTemperatureLineEdit")
        self.pLineEdit = self.findChild(QLineEdit, "pLineEdit")
        self.iLineEdit = self.findChild(QLineEdit, "iLineEdit")
        self.dLineEdit = self.findChild(QLineEdit, "dLineEdit")
        self.partHeightLineEdit = self.findChild(QLineEdit, "partHeightLineEdit")
        self.dosingHeightLineEdit = self.findChild(QLineEdit, "dosingHeightLineEdit")  # Add dosingHeightLineEdit

        # Initialize all QPlainTextEdit widgets
        self.powderLoadingSequenceText = self.findChild(QPlainTextEdit, "powderLoadingSequenceText")
        self.moveToStartingSequenceText = self.findChild(QPlainTextEdit, "moveToStartingSequenceText")
        self.prepareForPartRemovalSequenceText = self.findChild(QPlainTextEdit, "prepareForPartRemovalSequenceText")
        self.initialLevellingRecoatingSequenceText = self.findChild(QPlainTextEdit, "initialLevellingRecoatingSequenceText")
        self.heatedBufferRecoatingSequenceText = self.findChild(QPlainTextEdit, "heatedBufferRecoatingSequenceText")
        self.printingRecoatingSequenceText = self.findChild(QPlainTextEdit, "printingRecoatingSequenceText")

        # Initialize buttons
        self.saveChangesButton = self.findChild(QPushButton, "saveChangesButton")
        self.revertChangesButton = self.findChild(QPushButton, "revertChangesButton")

        # Store initial values
        self.initial_values = {
            "layerHeight": self.printer_status.layerHeight,
            "initialLevellingHeight": self.printer_status.initialLevellingHeight,
            "heatedBufferHeight": self.printer_status.heatedBufferHeight,
            "powderLoadingExtraHeightGap": self.printer_status.powderLoadingExtraHeightGap,
            "bedTemperature": self.printer_status.bedTemperature,
            "volumeTemperature": self.printer_status.volumeTemperature,
            "chamberTemperature": self.printer_status.chamberTemperature,
            "p": self.printer_status.p,
            "i": self.printer_status.i,
            "d": self.printer_status.d,
            "powderLoadingSequence": self.printer_status.powderLoadingSequence,
            "moveToStartingSequence": self.printer_status.moveToStartingSequence,
            "prepareForPartRemovalSequence": self.printer_status.prepareForPartRemovalSequence,
            "initialLevellingRecoatingSequence": self.printer_status.initialLevellingRecoatingSequence,
            "heatedBufferRecoatingSequence": self.printer_status.heatedBufferRecoatingSequence,
            "printingRecoatingSequence": self.printer_status.printingRecoatingSequence,
            "partHeight": self.printer_status.partHeight,
            "dosingHeight": self.printer_status.dosingHeight  # Add dosingHeight
        }

        # Connect buttons to methods
        self.saveChangesButton.clicked.connect(self.save_changes)
        self.revertChangesButton.clicked.connect(self.revert_changes)

        # Load parameters from YAML file
        self.load_parameters()

    def load_parameters(self):
        try:
            with open('parameters.yaml', 'r') as file:
                parameters = yaml.safe_load(file)
                self.printer_status.setLayerHeight(float(parameters["layerHeight"]))
                self.printer_status.setInitialLevellingHeight(float(parameters["initialLevellingHeight"]))
                self.printer_status.setHeatedBufferHeight(float(parameters["heatedBufferHeight"]))
                self.printer_status.setPowderLoadingExtraHeightGap(float(parameters["powderLoadingExtraHeightGap"]))
                self.printer_status.setBedTemperature(float(parameters["bedTemperature"]))
                self.printer_status.setVolumeTemperature(float(parameters["volumeTemperature"]))
                self.printer_status.setChamberTemperature(float(parameters["chamberTemperature"]))
                self.printer_status.setP(float(parameters["p"]))
                self.printer_status.setI(float(parameters["i"]))
                self.printer_status.setD(float(parameters["d"]))
                self.printer_status.setPartHeight(float(parameters["partHeight"]))
                self.printer_status.setDosingHeight(float(parameters["dosingHeight"]))  # Add dosingHeight
                self.printer_status.setPowderLoadingSequence(parameters["powderLoadingSequence"])
                self.printer_status.setMoveToStartingSequence(parameters["moveToStartingSequence"])
                self.printer_status.setPrepareForPartRemovalSequence(parameters["prepareForPartRemovalSequence"])
                self.printer_status.setInitialLevellingRecoatingSequence(parameters["initialLevellingRecoatingSequence"])
                self.printer_status.setHeatedBufferRecoatingSequence(parameters["heatedBufferRecoatingSequence"])
                self.printer_status.setPrintingRecoatingSequence(parameters["printingRecoatingSequence"])

                # Set values to QLineEdit and QPlainTextEdit widgets
                self.layerHeightLineEdit.setText(parameters["layerHeight"])
                self.initialLevellingHeightLineEdit.setText(parameters["initialLevellingHeight"])
                self.heatedBufferHeightLineEdit.setText(parameters["heatedBufferHeight"])
                self.powderLoadingExtraHeightGapLineEdit.setText(parameters["powderLoadingExtraHeightGap"])
                self.bedTemperatureLineEdit.setText(parameters["bedTemperature"])
                self.volumeTemberatureLineEdit.setText(parameters["volumeTemperature"])
                self.chamberTemperatureLineEdit.setText(parameters["chamberTemperature"])
                self.pLineEdit.setText(parameters["p"])
                self.iLineEdit.setText(parameters["i"])
                self.dLineEdit.setText(parameters["d"])
                self.partHeightLineEdit.setText(parameters["partHeight"])
                self.dosingHeightLineEdit.setText(parameters["dosingHeight"])  # Add dosingHeight
                self.powderLoadingSequenceText.setPlainText(parameters["powderLoadingSequence"])
                self.moveToStartingSequenceText.setPlainText(parameters["moveToStartingSequence"])
                self.prepareForPartRemovalSequenceText.setPlainText(parameters["prepareForPartRemovalSequence"])
                self.initialLevellingRecoatingSequenceText.setPlainText(parameters["initialLevellingRecoatingSequence"])
                self.heatedBufferRecoatingSequenceText.setPlainText(parameters["heatedBufferRecoatingSequence"])
                self.printingRecoatingSequenceText.setPlainText(parameters["printingRecoatingSequence"])
        except FileNotFoundError:
            print("parameters.yaml file not found. Using initial values.")

    def save_changes(self):
        self.printer_status.setLayerHeight(float(self.layerHeightLineEdit.text()))
        self.printer_status.setInitialLevellingHeight(float(self.initialLevellingHeightLineEdit.text()))
        self.printer_status.setHeatedBufferHeight(float(self.heatedBufferHeightLineEdit.text()))
        self.printer_status.setPowderLoadingExtraHeightGap(float(self.powderLoadingExtraHeightGapLineEdit.text()))
        self.printer_status.setBedTemperature(float(self.bedTemperatureLineEdit.text()))
        self.printer_status.setVolumeTemperature(float(self.volumeTemberatureLineEdit.text()))
        self.printer_status.setChamberTemperature(float(self.chamberTemperatureLineEdit.text()))
        self.printer_status.setP(float(self.pLineEdit.text()))
        self.printer_status.setI(float(self.iLineEdit.text()))
        self.printer_status.setD(float(self.dLineEdit.text()))
        self.printer_status.setPartHeight(float(self.partHeightLineEdit.text()))
        self.printer_status.setDosingHeight(float(self.dosingHeightLineEdit.text()))  # Add dosingHeight

        self.printer_status.setPowderLoadingSequence(self.powderLoadingSequenceText.toPlainText())
        self.printer_status.setMoveToStartingSequence(self.moveToStartingSequenceText.toPlainText())
        self.printer_status.setPrepareForPartRemovalSequence(self.prepareForPartRemovalSequenceText.toPlainText())
        self.printer_status.setInitialLevellingRecoatingSequence(self.initialLevellingRecoatingSequenceText.toPlainText())
        self.printer_status.setHeatedBufferRecoatingSequence(self.heatedBufferRecoatingSequenceText.toPlainText())
        self.printer_status.setPrintingRecoatingSequence(self.printingRecoatingSequenceText.toPlainText())

        # Save to YAML file
        parameters = {
            "layerHeight": self.layerHeightLineEdit.text(),
            "initialLevellingHeight": self.initialLevellingHeightLineEdit.text(),
            "heatedBufferHeight": self.heatedBufferHeightLineEdit.text(),
            "powderLoadingExtraHeightGap": self.powderLoadingExtraHeightGapLineEdit.text(),
            "bedTemperature": self.bedTemperatureLineEdit.text(),
            "volumeTemperature": self.volumeTemberatureLineEdit.text(),
            "chamberTemperature": self.chamberTemperatureLineEdit.text(),
            "p": self.pLineEdit.text(),
            "i": self.iLineEdit.text(),
            "d": self.dLineEdit.text(),
            "powderLoadingSequence": self.powderLoadingSequenceText.toPlainText(),
            "moveToStartingSequence": self.moveToStartingSequenceText.toPlainText(),
            "prepareForPartRemovalSequence": self.prepareForPartRemovalSequenceText.toPlainText(),
            "initialLevellingRecoatingSequence": self.initialLevellingRecoatingSequenceText.toPlainText(),
            "heatedBufferRecoatingSequence": self.heatedBufferRecoatingSequenceText.toPlainText(),
            "printingRecoatingSequence": self.printingRecoatingSequenceText.toPlainText(),
            "partHeight": self.partHeightLineEdit.text(),
            "dosingHeight": self.dosingHeightLineEdit.text()  # Add dosingHeight
        }
        with open('parameters.yaml', 'w') as file:
            yaml.dump(parameters, file)

    def revert_changes(self):
        # Load from YAML file
        try:
            with open('parameters.yaml', 'r') as file:
                parameters = yaml.safe_load(file)
                self.layerHeightLineEdit.setText(parameters["layerHeight"])
                self.initialLevellingHeightLineEdit.setText(parameters["initialLevellingHeight"])
                self.heatedBufferHeightLineEdit.setText(parameters["heatedBufferHeight"])
                self.powderLoadingExtraHeightGapLineEdit.setText(parameters["powderLoadingExtraHeightGap"])
                self.bedTemperatureLineEdit.setText(parameters["bedTemperature"])
                self.volumeTemberatureLineEdit.setText(parameters["volumeTemperature"])
                self.chamberTemperatureLineEdit.setText(parameters["chamberTemperature"])
                self.pLineEdit.setText(parameters["p"])
                self.iLineEdit.setText(parameters["i"])
                self.dLineEdit.setText(parameters["d"])
                self.partHeightLineEdit.setText(parameters["partHeight"])
                self.dosingHeightLineEdit.setText(parameters["dosingHeight"])  # Add dosingHeight
                self.powderLoadingSequenceText.setPlainText(parameters["powderLoadingSequence"])
                self.moveToStartingSequenceText.setPlainText(parameters["moveToStartingSequence"])
                self.prepareForPartRemovalSequenceText.setPlainText(parameters["prepareForPartRemovalSequence"])
                self.initialLevellingRecoatingSequenceText.setPlainText(parameters["initialLevellingRecoatingSequence"])
                self.heatedBufferRecoatingSequenceText.setPlainText(parameters["heatedBufferRecoatingSequence"])
                self.printingRecoatingSequenceText.setPlainText(parameters["printingRecoatingSequence"])
        except FileNotFoundError:
            print("parameters.yaml file not found. Reverting to initial values.")
            self.layerHeightLineEdit.setText(str(self.initial_values["layerHeight"]))
            self.initialLevellingHeightLineEdit.setText(str(self.initial_values["initialLevellingHeight"]))
            self.heatedBufferHeightLineEdit.setText(str(self.initial_values["heatedBufferHeight"]))
            self.powderLoadingExtraHeightGapLineEdit.setText(str(self.initial_values["powderLoadingExtraHeightGap"]))
            self.bedTemperatureLineEdit.setText(str(self.initial_values["bedTemperature"]))
            self.volumeTemberatureLineEdit.setText(str(self.initial_values["volumeTemperature"]))
            self.chamberTemperatureLineEdit.setText(str(self.initial_values["chamberTemperature"]))
            self.pLineEdit.setText(str(self.initial_values["p"]))
            self.iLineEdit.setText(str(self.initial_values["i"]))
            self.dLineEdit.setText(str(self.initial_values["d"]))
            self.partHeightLineEdit.setText(str(self.initial_values["partHeight"]))
            self.dosingHeightLineEdit.setText(str(self.initial_values["dosingHeight"]))  # Add dosingHeight
            self.powderLoadingSequenceText.setPlainText(self.initial_values["powderLoadingSequence"])
            self.moveToStartingSequenceText.setPlainText(self.initial_values["moveToStartingSequence"])
            self.prepareForPartRemovalSequenceText.setPlainText(self.initial_values["prepareForPartRemovalSequence"])
            self.initialLevellingRecoatingSequenceText.setPlainText(self.initial_values["initialLevellingRecoatingSequence"])
            self.heatedBufferRecoatingSequenceText.setPlainText(self.initial_values["heatedBufferRecoatingSequence"])
            self.printingRecoatingSequenceText.setPlainText(self.initial_values["printingRecoatingSequence"])