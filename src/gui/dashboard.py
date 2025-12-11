"""
Dashboard widget for displaying ECU information and real-time data
Motorcycle-specific dashboard with tachometer, temperature, and system status
"""

from typing import Optional, Dict, Any
import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QFrame, QProgressBar, QScrollArea,
    QGridLayout, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QFont, QPalette, QColor, QPainter, QPen, QBrush, QRadialGradient,
    QPixmap, QPainterPath
)

from src.maps.types import ECUInfo, ConnectionStatus, EngineType
from src.utils.logger import get_gui_logger


class TachometerWidget(QWidget):
    """Custom tachometer widget for motorcycle RPM display"""

    def __init__(self):
        super().__init__()
        self.current_rpm = 0
        self.max_rpm = 16000  # Typical sportbike range
        self.redline = 14000
        self.setMinimumSize(250, 250)

    def set_rpm(self, rpm: int):
        """Set current RPM value"""
        self.current_rpm = max(0, min(rpm, self.max_rpm))
        self.update()

    def paintEvent(self, event):
        """Paint the tachometer"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate dimensions
        width = self.width()
        height = self.height()
        radius = min(width, height) // 2 - 10
        center_x = width // 2
        center_y = height // 2

        # Draw outer circle
        gradient = QRadialGradient(center_x, center_y, radius)
        gradient.setColorAt(0, QColor(50, 50, 50))
        gradient.setColorAt(1, QColor(30, 30, 30))

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)

        # Draw RPM markings
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        font = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font)

        for i in range(0, self.max_rpm + 1, 2000):
            angle = -225 + (i / self.max_rpm) * 270  # -225° to 45°
            angle_rad = angle * 3.14159 / 180

            # Draw tick mark
            x1 = center_x + (radius - 10) * -angle_rad
            y1 = center_y + (radius - 10) * -angle_rad
            x2 = center_x + (radius - 20) * -angle_rad
            y2 = center_y + (radius - 20) * -angle_rad

            painter.drawLine(x1, y1, x2, y2)

            # Draw number
            text_x = center_x + (radius - 35) * -angle_rad
            text_y = center_y + (radius - 35) * -angle_rad
            painter.drawText(text_x - 15, text_y, str(i // 1000))

        # Draw redline
        redline_start = -225 + (self.redline / self.max_rpm) * 270
        redline_start_rad = redline_start * 3.14159 / 180
        redline_end_rad = -45 * 3.14159 / 180

        painter.setPen(QPen(QColor(255, 0, 0), 4))
        painter.drawArc(
            center_x - radius + 5, center_y - radius + 5,
            (radius - 5) * 2, (radius - 5) * 2,
            int(redline_start * 16), int((redline_end_rad - redline_start_rad) * 16 / 3.14159)
        )

        # Draw needle
        needle_angle = -225 + (self.current_rpm / self.max_rpm) * 270
        needle_angle_rad = needle_angle * 3.14159 / 180

        painter.setPen(QPen(QColor(255, 0, 0), 3))
        painter.drawLine(
            center_x, center_y,
            center_x + (radius - 30) * -needle_angle_rad,
            center_y + (radius - 30) * -needle_angle_rad
        )

        # Draw center cap
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawEllipse(center_x - 8, center_y - 8, 16, 16)

        # Draw current RPM text
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        font = QFont("Arial", 14, QFont.Bold)
        painter.setFont(font)
        rpm_text = str(self.current_rpm)
        painter.drawText(center_x - 25, center_y + 40, f"{rpm_text} RPM")


class TemperatureGauge(QWidget):
    """Custom temperature gauge for engine temperature"""

    def __init__(self):
        super().__init__()
        self.current_temp = 20.0
        self.max_temp = 120.0
        self.warning_temp = 100.0
        self.setMinimumSize(150, 150)

    def set_temperature(self, temp: float):
        """Set current temperature"""
        self.current_temp = max(0, min(temp, self.max_temp))
        self.update()

    def paintEvent(self, event):
        """Paint the temperature gauge"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        radius = min(width, height) // 2 - 10
        center_x = width // 2
        center_y = height // 2

        # Background circle
        gradient = QRadialGradient(center_x, center_y, radius)
        gradient.setColorAt(0, QColor(50, 50, 50))
        gradient.setColorAt(1, QColor(30, 30, 30))

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)

        # Temperature arc
        temp_ratio = self.current_temp / self.max_temp
        temp_angle = int(temp_ratio * 270)

        # Choose color based on temperature
        if self.current_temp < 80:
            color = QColor(0, 200, 0)  # Green
        elif self.current_temp < self.warning_temp:
            color = QColor(255, 200, 0)  # Orange
        else:
            color = QColor(255, 0, 0)  # Red

        painter.setPen(QPen(color, 8))
        painter.drawArc(
            center_x - radius + 5, center_y - radius + 5,
            (radius - 5) * 2, (radius - 5) * 2,
            90 * 16, -temp_angle * 16
        )

        # Temperature text
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        font = QFont("Arial", 12, QFont.Bold)
        painter.setFont(font)
        temp_text = f"{self.current_temp:.0f}°C"
        painter.drawText(center_x - 25, center_y + 5, temp_text)


class DashboardWidget(QWidget):
    """Main dashboard widget with ECU information and gauges"""

    # Signals
    connect_request = Signal()
    disconnect_request = Signal()
    read_firmware_request = Signal()

    def __init__(self):
        super().__init__()
        self.logger = get_gui_logger()
        self.ecu_info: Optional[ECUInfo] = None
        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self.update_simulation)

        self.setup_ui()
        self.setup_style()

    def setup_ui(self):
        """Setup dashboard UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create scroll area for responsive layout
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Main content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # ECU Information Section
        ecu_info_group = self.create_ecu_info_section()
        content_layout.addWidget(ecu_info_group)

        # Gauges Section
        gauges_layout = QHBoxLayout()

        # Tachometer
        tachometer_group = QGroupBox("Tachometer")
        tachometer_layout = QVBoxLayout(tachometer_group)
        self.tachometer = TachometerWidget()
        tachometer_layout.addWidget(self.tachometer)
        tachometer_layout.addWidget(QLabel("Engine RPM"))
        gauges_layout.addWidget(tachometer_group)

        # Temperature Gauge
        temp_group = QGroupBox("Engine Temperature")
        temp_layout = QVBoxLayout(temp_group)
        self.temperature_gauge = TemperatureGauge()
        temp_layout.addWidget(self.temperature_gauge)
        temp_layout.addWidget(QLabel("Coolant Temperature"))
        gauges_layout.addWidget(temp_group)

        # System Status
        status_group = self.create_status_section()
        gauges_layout.addWidget(status_group)

        content_layout.addLayout(gauges_layout)

        # Quick Actions Section
        actions_group = self.create_actions_section()
        content_layout.addWidget(actions_group)

        # Connection Status
        connection_group = self.create_connection_section()
        content_layout.addWidget(connection_group)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def create_ecu_info_section(self) -> QGroupBox:
        """Create ECU information display section"""
        group = QGroupBox("ECU Information")
        layout = QGridLayout(group)

        # VIN
        layout.addWidget(QLabel("VIN:"), 0, 0)
        self.vin_label = QLabel("Not Connected")
        self.vin_label.setStyleSheet("color: #888;")
        layout.addWidget(self.vin_label, 0, 1)

        # Hardware Version
        layout.addWidget(QLabel("Hardware:"), 0, 2)
        self.hw_version_label = QLabel("-")
        self.hw_version_label.setStyleSheet("color: #888;")
        layout.addWidget(self.hw_version_label, 0, 3)

        # Software Version
        layout.addWidget(QLabel("Software:"), 1, 0)
        self.sw_version_label = QLabel("-")
        self.sw_version_label.setStyleSheet("color: #888;")
        layout.addWidget(self.sw_version_label, 1, 1)

        # Engine Type
        layout.addWidget(QLabel("Engine:"), 1, 2)
        self.engine_type_label = QLabel("-")
        self.engine_type_label.setStyleSheet("color: #888;")
        layout.addWidget(self.engine_type_label, 1, 3)

        # Calibration Number
        layout.addWidget(QLabel("Calibration:"), 2, 0)
        self.calibration_label = QLabel("-")
        self.calibration_label.setStyleSheet("color: #888;")
        layout.addWidget(self.calibration_label, 2, 1)

        # Flash Size
        layout.addWidget(QLabel("Flash Size:"), 2, 2)
        self.flash_size_label = QLabel("-")
        self.flash_size_label.setStyleSheet("color: #888;")
        layout.addWidget(self.flash_size_label, 2, 3)

        return group

    def create_status_section(self) -> QGroupBox:
        """Create system status section"""
        group = QGroupBox("System Status")
        layout = QVBoxLayout(group)

        # Connection Quality
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Connection Quality:"))
        self.quality_progress = QProgressBar()
        self.quality_progress.setRange(0, 100)
        quality_layout.addWidget(self.quality_progress)
        self.quality_label = QLabel("N/A")
        quality_layout.addWidget(self.quality_label)
        layout.addLayout(quality_layout)

        # Battery Voltage
        voltage_layout = QHBoxLayout()
        voltage_layout.addWidget(QLabel("Battery Voltage:"))
        self.voltage_label = QLabel("--.- V")
        voltage_layout.addWidget(self.voltage_label)
        voltage_layout.addStretch()
        layout.addLayout(voltage_layout)

        # Fan Status
        fan_layout = QHBoxLayout()
        fan_layout.addWidget(QLabel("Cooling Fan:"))
        self.fan_status_label = QLabel("Unknown")
        fan_layout.addWidget(self.fan_status_label)
        fan_layout.addStretch()
        layout.addLayout(fan_layout)

        # DTC Count
        dtc_layout = QHBoxLayout()
        dtc_layout.addWidget(QLabel("DTC Count:"))
        self.dtc_count_label = QLabel("0")
        dtc_layout.addWidget(self.dtc_count_label)
        dtc_layout.addStretch()
        layout.addLayout(dtc_layout)

        return group

    def create_actions_section(self) -> QGroupBox:
        """Create quick actions section"""
        group = QGroupBox("Quick Actions")
        layout = QGridLayout(group)

        # Connect/Disconnect
        self.connect_button = QPushButton("Connect ECU")
        self.connect_button.clicked.connect(self.connect_request.emit)
        layout.addWidget(self.connect_button, 0, 0)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_request.emit)
        self.disconnect_button.setEnabled(False)
        layout.addWidget(self.disconnect_button, 0, 1)

        # Read Firmware
        self.read_firmware_button = QPushButton("Read Firmware")
        self.read_firmware_button.clicked.connect(self.read_firmware_request.emit)
        self.read_firmware_button.setEnabled(False)
        layout.addWidget(self.read_firmware_button, 1, 0)

        # Diagnostics
        self.diagnostics_button = QPushButton("Run Diagnostics")
        self.diagnostics_button.setEnabled(False)
        layout.addWidget(self.diagnostics_button, 1, 1)

        # Performance Mode
        self.performance_combo = QComboBox()
        self.performance_combo.addItems(["Street Mode", "Sport Mode", "Track Mode"])
        self.performance_combo.setEnabled(False)
        layout.addWidget(QLabel("Performance Mode:"), 2, 0)
        layout.addWidget(self.performance_combo, 2, 1)

        return group

    def create_connection_section(self) -> QGroupBox:
        """Create connection status section"""
        group = QGroupBox("Connection Details")
        layout = QGridLayout(group)

        # Protocol
        layout.addWidget(QLabel("Protocol:"), 0, 0)
        self.protocol_label = QLabel("Disconnected")
        self.protocol_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        layout.addWidget(self.protocol_label, 0, 1)

        # Port
        layout.addWidget(QLabel("Port:"), 0, 2)
        self.port_label = QLabel("-")
        layout.addWidget(self.port_label, 0, 3)

        # Baud Rate
        layout.addWidget(QLabel("Baud Rate:"), 1, 0)
        self.baudrate_label = QLabel("-")
        layout.addWidget(self.baudrate_label, 1, 1)

        # Last Update
        layout.addWidget(QLabel("Last Update:"), 1, 2)
        self.last_update_label = QLabel("Never")
        layout.addWidget(self.last_update_label, 1, 3)

        return group

    def setup_style(self):
        """Setup widget styling"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin: 3px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                color: #ddd;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #555;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666;
            }
            QComboBox {
                background-color: #404040;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 4px;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)

    def set_ecu_info(self, ecu_info: Optional[ECUInfo]):
        """Update ECU information display"""
        self.ecu_info = ecu_info

        if ecu_info:
            # Update ECU information
            self.vin_label.setText(ecu_info.vin)
            self.vin_label.setStyleSheet("color: #4caf50; font-weight: bold;")

            self.hw_version_label.setText(ecu_info.hardware_version)
            self.hw_version_label.setStyleSheet("color: #4caf50;")

            self.sw_version_label.setText(ecu_info.software_version)
            self.sw_version_label.setStyleSheet("color: #4caf50;")

            self.engine_type_label.setText(ecu_info.engine_type.value)
            self.engine_type_label.setStyleSheet("color: #4caf50;")

            self.calibration_label.setText(ecu_info.calibration_number or "Unknown")
            self.calibration_label.setStyleSheet("color: #4caf50;")

            flash_size_kb = ecu_info.flash_size // 1024
            self.flash_size_label.setText(f"{flash_size_kb} KB")
            self.flash_size_label.setStyleSheet("color: #4caf50;")

            # Update connection details
            self.protocol_label.setText(ecu_info.protocol.value)
            self.protocol_label.setStyleSheet("color: #4caf50; font-weight: bold;")

            # Enable controls
            self.disconnect_button.setEnabled(True)
            self.read_firmware_button.setEnabled(True)
            self.diagnostics_button.setEnabled(True)
            self.performance_combo.setEnabled(True)
            self.connect_button.setEnabled(False)

            # Start simulation (for demo purposes)
            self.simulation_timer.start(2000)  # Update every 2 seconds

            # Update last update time
            self.last_update_label.setText(time.strftime("%H:%M:%S"))

            self.logger.info(f"Dashboard updated with ECU info: {ecu_info.vin}")

        else:
            # Clear ECU information
            self.vin_label.setText("Not Connected")
            self.vin_label.setStyleSheet("color: #888;")
            self.hw_version_label.setText("-")
            self.hw_version_label.setStyleSheet("color: #888;")
            self.sw_version_label.setText("-")
            self.sw_version_label.setStyleSheet("color: #888;")
            self.engine_type_label.setText("-")
            self.engine_type_label.setStyleSheet("color: #888;")
            self.calibration_label.setText("-")
            self.calibration_label.setStyleSheet("color: #888;")
            self.flash_size_label.setText("-")
            self.flash_size_label.setStyleSheet("color: #888;")

            # Update connection details
            self.protocol_label.setText("Disconnected")
            self.protocol_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
            self.port_label.setText("-")
            self.baudrate_label.setText("-")
            self.last_update_label.setText("Never")

            # Disable controls
            self.disconnect_button.setEnabled(False)
            self.read_firmware_button.setEnabled(False)
            self.diagnostics_button.setEnabled(False)
            self.performance_combo.setEnabled(False)
            self.connect_button.setEnabled(True)

            # Stop simulation
            self.simulation_timer.stop()
            self.reset_gauges()

            # Reset status displays
            self.quality_progress.setValue(0)
            self.quality_label.setText("N/A")
            self.voltage_label.setText("--.- V")
            self.fan_status_label.setText("Unknown")
            self.dtc_count_label.setText("0")

    def update_simulation(self):
        """Update simulated dashboard data (for demo purposes)"""
        import random

        # Simulate RPM changes
        if self.ecu_info:
            # Different RPM ranges based on engine type
            if self.ecu_info.engine_type == EngineType.CC125:
                max_rpm = 12000
            elif self.ecu_info.engine_type == EngineType.CC200:
                max_rpm = 14000
            else:  # CC300
                max_rpm = 16000

            # Simulate idle to varying RPM
            current_rpm = self.tachometer.current_rpm
            if current_rpm < 1500:  # Starting from idle
                new_rpm = random.randint(800, 1200)
            else:
                # Random variation around current RPM
                change = random.randint(-500, 800)
                new_rpm = max(800, min(current_rpm + change, max_rpm))

            self.tachometer.set_rpm(new_rpm)

            # Simulate temperature changes
            current_temp = self.temperature_gauge.current_temp
            temp_change = random.uniform(-2, 3)
            new_temp = max(20, min(current_temp + temp_change, 105))
            self.temperature_gauge.set_temperature(new_temp)

            # Update fan status based on temperature
            if new_temp > 95:
                self.fan_status_label.setText("ON")
                self.fan_status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            elif new_temp > 85:
                self.fan_status_label.setText("Intermittent")
                self.fan_status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            else:
                self.fan_status_label.setText("OFF")
                self.fan_status_label.setStyleSheet("color: #2196f3;")

            # Simulate battery voltage
            voltage = 12.6 + random.uniform(-0.3, 0.3)
            self.voltage_label.setText(f"{voltage:.1f} V")
            if voltage < 12.0:
                self.voltage_label.setStyleSheet("color: #f44336;")
            elif voltage < 12.3:
                self.voltage_label.setStyleSheet("color: #ff9800;")
            else:
                self.voltage_label.setStyleSheet("color: #4caf50;")

            # Simulate connection quality
            quality = random.randint(75, 100)
            self.quality_progress.setValue(quality)
            self.quality_label.setText(f"{quality}%")
            if quality >= 90:
                self.quality_label.setStyleSheet("color: #4caf50;")
            elif quality >= 70:
                self.quality_label.setStyleSheet("color: #ff9800;")
            else:
                self.quality_label.setStyleSheet("color: #f44336;")

            # Update last update time
            self.last_update_label.setText(time.strftime("%H:%M:%S"))

    def reset_gauges(self):
        """Reset all gauges to default values"""
        self.tachometer.set_rpm(0)
        self.temperature_gauge.set_temperature(20.0)

    def update_connection_details(self, port: str, baudrate: int):
        """Update connection port and baud rate display"""
        self.port_label.setText(port)
        self.baudrate_label.setText(str(baudrate))