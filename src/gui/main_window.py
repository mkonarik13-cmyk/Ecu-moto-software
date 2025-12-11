from PySide6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                               QMessageBox, QToolBar, QFileDialog, QProgressDialog)
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtCore import Qt
from .dashboard import DashboardWidget
from .map_editor import MapEditorWidget
from ..kwp2000 import KWP2000Client
from ..firmware_manager import FirmwareManager

class MainWindow(QMainWindow):
    def __init__(self, protocol, logger):
        super().__init__()
        self.protocol = protocol
        self.logger = logger
        self.kwp_client = KWP2000Client("TEST_PORT") # Placeholder port
        self.fw_manager = FirmwareManager(self.kwp_client)
        
        self.setWindowTitle("Moto ECU Tuner (Magneti Marelli 28M4G)")
        self.resize(1000, 700)
        
        self.setup_theme()
        self.setup_ui()
        self.setup_toolbar()

    def setup_theme(self):
        # Dark Theme
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)

    def setup_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Dashboard Tab
        self.dashboard = DashboardWidget(self.logger)
        self.tabs.addTab(self.dashboard, "Dashboard")
        
        # Map Editor Tab
        self.map_editor = MapEditorWidget(self.protocol, self.logger)
        self.tabs.addTab(self.map_editor, "Map Editor")

    def setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Connect Action
        connect_action = QAction("Connect", self)
        connect_action.triggered.connect(self.connect_ecu)
        toolbar.addAction(connect_action)
        
        toolbar.addSeparator()
        
        # Start Logging Action
        start_log_action = QAction("Start Logging", self)
        start_log_action.triggered.connect(self.start_logging)
        toolbar.addAction(start_log_action)
        
        # Stop Logging Action
        stop_log_action = QAction("Stop Logging", self)
        stop_log_action.triggered.connect(self.stop_logging)
        toolbar.addAction(stop_log_action)
        
        toolbar.addSeparator()
        
        # Read Firmware
        read_fw_action = QAction("Read Firmware", self)
        read_fw_action.triggered.connect(self.read_firmware)
        toolbar.addAction(read_fw_action)
        
        # Write Firmware
        write_fw_action = QAction("Write Firmware", self)
        write_fw_action.triggered.connect(self.write_firmware)
        toolbar.addAction(write_fw_action)

    def connect_ecu(self):
        try:
            # Try KWP2000 connection first
            # In real usage, we'd ask user for COM port
            if self.kwp_client.connect():
                QMessageBox.information(self, "Success", "Connected to 28M4G ECU via KWP2000")
            else:
                # Fallback to Mock for demo
                self.logger.connect()
                QMessageBox.information(self, "Success", "Connected to ECU (Mock Mode)")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection failed: {e}")

    def start_logging(self):
        try:
            params = ["RPM", "TPS", "ECT"]
            self.logger.start_logging(params)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start logging: {e}")

    def stop_logging(self):
        self.logger.stop_logging()

    def read_firmware(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Save Firmware", "", "Binary Files (*.bin)")
        if fname:
            progress = QProgressDialog("Reading Firmware...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            
            def update_progress(val):
                progress.setValue(int(val))
                
            try:
                self.fw_manager.download_firmware(fname, update_progress)
                QMessageBox.information(self, "Success", "Firmware downloaded successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Download failed: {e}")

    def write_firmware(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Firmware", "", "Binary Files (*.bin)")
        if fname:
            reply = QMessageBox.warning(self, "Warning",
                                      "Flashing firmware carries risks. Ensure battery is charged.\nContinue?",
                                      QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                progress = QProgressDialog("Writing Firmware...", "Cancel", 0, 100, self)
                progress.setWindowModality(Qt.WindowModal)
                
                def update_progress(val):
                    progress.setValue(int(val))
                    
                try:
                    self.fw_manager.upload_firmware(fname, update_progress)
                    QMessageBox.information(self, "Success", "Firmware uploaded successfully!")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Upload failed: {e}")