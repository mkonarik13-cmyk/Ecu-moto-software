"""
Connection dialog for ECU communication setup
Provides intuitive interface for configuring and testing ECU connections
"""

from typing import Optional, Dict, Any, List
import time

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QGroupBox,
    QProgressBar, QTextEdit, QCheckBox, QSpinBox, QFrame,
    QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont

from src.ecu.connection import ECUConnection, ConnectionStatus, ConnectionConfig
from src.maps.types import ProtocolType
from src.utils.logger import get_gui_logger


class ConnectionDialog(QDialog):
    """Dialog for configuring and establishing ECU connection"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_gui_logger()
        self.ecu_connection: Optional[ECUConnection] = None
        self.connection_config: Optional[ConnectionConfig] = None
        self.test_thread: Optional[ConnectionTestThread] = None

        self.setWindowTitle("ECU Connection Configuration")
        self.setModal(True)
        self.resize(600, 500)

        self.setup_ui()
        self.setup_connections()
        self.refresh_ports()

    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)

        # Connection settings group
        settings_group = QGroupBox("Connection Settings")
        settings_layout = QFormLayout(settings_group)

        # Port selection
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setMinimumWidth(300)
        settings_layout.addRow("Port:", self.port_combo)

        # Refresh ports button
        refresh_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Ports")
        refresh_layout.addWidget(self.refresh_button)
        refresh_layout.addStretch()
        settings_layout.addRow("", refresh_layout)

        # Baud rate selection
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["10400", "9600", "38400", "57600", "115200"])
        self.baudrate_combo.setCurrentText("10400")  # 28M4G standard
        self.baudrate_combo.setEditable(True)
        settings_layout.addRow("Baud Rate:", self.baudrate_combo)

        # Protocol selection
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["Auto Detect", "KWP2000", "UDS"])
        self.protocol_combo.setCurrentText("Auto Detect")
        settings_layout.addRow("Protocol:", self.protocol_combo)

        # Advanced settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QGridLayout(advanced_group)

        # Timeout
        advanced_layout.addWidget(QLabel("Timeout (seconds):"), 0, 0)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 30)
        self.timeout_spin.setValue(5)
        advanced_layout.addWidget(self.timeout_spin, 0, 1)

        # Retry count
        advanced_layout.addWidget(QLabel("Retry Count:"), 0, 2)
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(3)
        advanced_layout.addWidget(self.retry_spin, 0, 3)

        # Auto-detect checkbox
        self.auto_detect_checkbox = QCheckBox("Auto-detect settings")
        self.auto_detect_checkbox.setChecked(True)
        advanced_layout.addWidget(self.auto_detect_checkbox, 1, 0, 1, 2)

        # Test connection section
        test_group = QGroupBox("Connection Test")
        test_layout = QVBoxLayout(test_group)

        # Test button
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        test_layout.addWidget(self.test_button)

        # Progress bar
        self.test_progress = QProgressBar()
        self.test_progress.setVisible(False)
        test_layout.addWidget(self.test_progress)

        # Test results
        self.test_results = QTextEdit()
        self.test_results.setReadOnly(True)
        self.test_results.setMaximumHeight(150)
        self.test_results.setFont(QFont("Consolas", 9))
        test_layout.addWidget(self.test_results)

        # Add groups to main layout
        layout.addWidget(settings_group)
        layout.addWidget(advanced_group)
        layout.addWidget(test_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept_connection)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def setup_connections(self):
        """Setup signal connections"""
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.port_combo.currentTextChanged.connect(self.on_port_changed)
        self.auto_detect_checkbox.toggled.connect(self.on_auto_detect_changed)

    def refresh_ports(self):
        """Refresh available serial ports"""
        self.logger.info("Refreshing serial ports")
        self.port_combo.clear()

        try:
            # Create temporary ECU connection to scan ports
            temp_connection = ECUConnection()
            ports = temp_connection.get_available_ports()

            if ports:
                for port in ports:
                    display_text = f"{port['device']} - {port['description']}"
                    self.port_combo.addItem(display_text, port['device'])
                    self.logger.debug(f"Found port: {display_text}")
            else:
                self.port_combo.addItem("No ports found", "")
                self.logger.warning("No serial ports found")

        except Exception as e:
            self.logger.error(f"Failed to refresh ports: {e}")
            self.port_combo.addItem("Error scanning ports", "")

    def on_port_changed(self, port_text: str):
        """Handle port selection change"""
        # Clear test results when port changes
        self.test_results.clear()

    def on_auto_detect_changed(self, enabled: bool):
        """Handle auto-detect checkbox change"""
        # Enable/disable manual settings based on auto-detect
        self.protocol_combo.setEnabled(not enabled)
        self.baudrate_combo.setEnabled(not enabled)

    def test_connection(self):
        """Test ECU connection with current settings"""
        if self.test_thread and self.test_thread.isRunning():
            self.logger.warning("Connection test already in progress")
            return

        # Get connection settings
        config = self.get_connection_config()
        if not config:
            QMessageBox.warning(self, "Invalid Settings", "Please select a valid port")
            return

        # Setup test UI
        self.test_button.setEnabled(False)
        self.test_progress.setVisible(True)
        self.test_progress.setRange(0, 0)  # Indeterminate progress
        self.test_results.clear()
        self.test_results.append("Starting connection test...")
        self.test_results.append(f"Port: {config.port}")
        self.test_results.append(f"Baud Rate: {config.baudrate}")
        self.test_results.append(f"Protocol: {config.protocol.value}")
        self.test_results.append("")

        # Start test thread
        self.test_thread = ConnectionTestThread(config)
        self.test_thread.test_update.connect(self.on_test_update)
        self.test_thread.test_completed.connect(self.on_test_completed)
        self.test_thread.start()

    def on_test_update(self, message: str):
        """Handle test progress update"""
        self.test_results.append(f"[{time.strftime('%H:%M:%S')}] {message}")

    def on_test_completed(self, success: bool, ecu_info: Optional[Any], error: str):
        """Handle test completion"""
        self.test_button.setEnabled(True)
        self.test_progress.setVisible(False)

        if success:
            self.test_results.append("")
            self.test_results.append("✓ Connection test successful!")
            if ecu_info:
                self.test_results.append(f"ECU VIN: {ecu_info.vin}")
                self.test_results.append(f"Hardware: {ecu_info.hardware_version}")
                self.test_results.append(f"Software: {ecu_info.software_version}")
                self.test_results.append(f"Engine: {ecu_info.engine_type.value}")
        else:
            self.test_results.append("")
            self.test_results.append("✗ Connection test failed!")
            self.test_results.append(f"Error: {error}")

        # Scroll to bottom
        self.test_results.verticalScrollBar().setValue(
            self.test_results.verticalScrollBar().maximum()
        )

    def get_connection_config(self) -> Optional[ConnectionConfig]:
        """Get connection configuration from dialog"""
        port_data = self.port_combo.currentData()
        if not port_data:
            return None

        try:
            baudrate = int(self.baudrate_combo.currentText())
        except ValueError:
            baudrate = 10400  # Default

        # Determine protocol
        protocol_text = self.protocol_combo.currentText()
        if protocol_text == "Auto Detect":
            protocol = ProtocolType.KWP2000  # Default, will auto-detect
            auto_detect = True
        else:
            protocol = ProtocolType.KWP2000 if protocol_text == "KWP2000" else ProtocolType.UDS
            auto_detect = False

        return ConnectionConfig(
            port=port_data,
            baudrate=baudrate,
            protocol=protocol,
            timeout=self.timeout_spin.value(),
            retry_count=self.retry_spin.value(),
            auto_detect=auto_detect
        )

    def accept_connection(self):
        """Handle dialog acceptance"""
        config = self.get_connection_config()
        if not config:
            QMessageBox.warning(self, "Invalid Settings", "Please select a valid port")
            return

        self.connection_config = config
        self.accept()

    def reject(self):
        """Handle dialog rejection"""
        # Stop any running test
        if self.test_thread and self.test_thread.isRunning():
            self.test_thread.stop()
            self.test_thread.wait()

        super().reject()


class ConnectionTestThread(QThread):
    """Worker thread for testing ECU connection"""

    test_update = Signal(str)  # Progress update message
    test_completed = Signal(bool, object, str)  # success, ecu_info, error

    def __init__(self, config: ConnectionConfig):
        super().__init__()
        self.config = config
        self._stopped = False

    def run(self):
        """Run connection test"""
        try:
            self.test_update.emit("Creating ECU connection...")
            ecu_connection = ECUConnection(self.config)

            self.test_update.emit("Attempting to connect...")
            success = ecu_connection.connect()

            if self._stopped:
                return

            if success:
                self.test_update.emit("Connection established!")
                self.test_update.emit("Getting ECU information...")

                ecu_info = ecu_connection.get_ecu_info()
                if ecu_info:
                    self.test_update.emit("ECU identification successful!")
                    self.test_update.emit("Testing connection quality...")

                    quality = ecu_connection.test_connection_quality()
                    self.test_update.emit(
                        f"Connection quality: {quality['quality']:.1f}% "
                        f"(Latency: {quality['latency_ms']:.1f}ms)"
                    )

                    ecu_connection.disconnect()
                    self.test_completed.emit(True, ecu_info, "")
                else:
                    ecu_connection.disconnect()
                    self.test_completed.emit(False, None, "Failed to identify ECU")
            else:
                self.test_completed.emit(False, None, "Connection failed")

        except Exception as e:
            self.test_update.emit(f"Test error: {str(e)}")
            self.test_completed.emit(False, None, str(e))

    def stop(self):
        """Stop the test thread"""
        self._stopped = True
        self.terminate()
        self.wait()