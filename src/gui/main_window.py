from PySide6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                               QMessageBox, QToolBar, QFileDialog, QProgressDialog)
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtCore import Qt
from .dashboard import DashboardWidget
from .map_editor import MapEditorWidget
from .scanner_dialog import ScannerDialog
from ..kwp2000 import KWP2000Client
from ..firmware_manager import FirmwareManager

class MainWindow(QMainWindow):
    def __init__(self, protocol, logger, kwp_client):
        super().__init__()
        self.protocol = protocol
        self.logger = logger
        self.kwp_client = kwp_client
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
        # Pass kwp_client as protocol for scanning
        self.dashboard = DashboardWidget(self.logger, self.kwp_client)
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
        
        toolbar.addSeparator()
        
        # Scan IDs
        scan_action = QAction("Scan Live Data IDs", self)
        scan_action.triggered.connect(self.open_scanner)
        toolbar.addAction(scan_action)

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
            # Ensure connection first
            if not self.kwp_client.ser and not self.kwp_client.simulation_mode:
                if not self.kwp_client.connect():
                    QMessageBox.critical(self, "Error", "Not connected to ECU!")
                    return

            progress = QProgressDialog("Reading Firmware from ECU...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            
            def update_progress(val):
                progress.setValue(int(val))
                if progress.wasCanceled():
                    return False
                return True
                
            try:
                success = self.fw_manager.download_firmware(fname, update_progress)
                if success:
                    QMessageBox.information(self, "Success", f"Firmware downloaded successfully!\nSaved to: {fname}")
                else:
                    QMessageBox.critical(self, "Error", "Download failed or was cancelled.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Download failed: {e}")

    def write_firmware(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Firmware", "", "Binary Files (*.bin)")
        if fname:
            # Check Voltage First
            voltage = self.kwp_client.get_battery_voltage()
            if voltage < 12.0:
                QMessageBox.critical(self, "Low Voltage", f"Battery voltage is too low ({voltage:.1f}V). Connect a charger before flashing.")
                return

            reply = QMessageBox.warning(self, "Warning",
                                      f"Flashing firmware carries risks.\nBattery Voltage: {voltage:.1f}V\n\nAn automatic backup will be created before writing.\n\nContinue?",
                                      QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                progress = QProgressDialog("Writing Firmware (Backup -> Flash)...", "Cancel", 0, 100, self)
                progress.setWindowModality(Qt.WindowModal)
                
                def update_progress(val):
                    progress.setValue(int(val))
                    
                try:
                    success = self.fw_manager.upload_firmware(fname, update_progress)
                    if success:
                        QMessageBox.information(self, "Success", "Firmware uploaded successfully!")
                    else:
                        QMessageBox.critical(self, "Error", "Upload failed. Check console for details.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Upload failed: {e}")

    def open_scanner(self):
        # Ensure connection first
        if not self.kwp_client.ser and not self.kwp_client.simulation_mode:
            if not self.kwp_client.connect():
                QMessageBox.critical(self, "Error", "Not connected to ECU!")
                return

        dialog = ScannerDialog(self.kwp_client, self)
        dialog.exec()

    def set_status(self, message):
        """Set status message for the main window."""
        self.setWindowTitle(f"Moto ECU Tuner (Magneti Marelli 28M4G) - {message}")