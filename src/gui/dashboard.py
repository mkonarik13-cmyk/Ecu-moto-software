from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QGroupBox, QLabel, QProgressBar, QPushButton,
                               QFrame, QGridLayout)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPalette, QColor
from .scanner_dialog import ScannerDialog

class DashboardWidget(QWidget):
    """Enhanced dashboard with real 28M4G parameters and hardware status."""

    # Signal for status updates
    status_updated = Signal(str)

    def __init__(self, logger, protocol=None, kwp_client=None):
        super().__init__()
        self.logger = logger
        self.protocol = protocol
        self.kwp_client = kwp_client  # Add KWP client for hardware status
        self.setup_ui()

        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(100)  # 10Hz update

        # Hardware status timer (slower update)
        self.hw_timer = QTimer()
        self.hw_timer.timeout.connect(self.update_hardware_status)
        self.hw_timer.start(2000)  # Update every 2 seconds

    def setup_ui(self):
        layout = QGridLayout(self)

        # === Real Engine Parameters ===

        # RPM Gauge (Real 28M4G conversion)
        rpm_group = QGroupBox("Engine Speed (RPM)")
        rpm_layout = QVBoxLayout(rpm_group)
        self.rpm_label = QLabel("0 RPM")
        self.rpm_label.setAlignment(Qt.AlignCenter)
        self.rpm_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.rpm_bar = QProgressBar()
        self.rpm_bar.setRange(0, 12000)  # Typical range for 125cc motorcycles
        self.rpm_bar.setTextVisible(False)
        rpm_layout.addWidget(self.rpm_label)
        rpm_layout.addWidget(self.rpm_bar)
        layout.addWidget(rpm_group, 0, 0)

        # TPS Gauge (Real 28M4G conversion)
        tps_group = QGroupBox("Throttle Position (%)")
        tps_layout = QVBoxLayout(tps_group)
        self.tps_label = QLabel("0.0 %")
        self.tps_label.setAlignment(Qt.AlignCenter)
        self.tps_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.tps_bar = QProgressBar()
        self.tps_bar.setRange(0, 100)
        self.tps_bar.setTextVisible(False)
        tps_layout.addWidget(self.tps_label)
        tps_layout.addWidget(self.tps_bar)
        layout.addWidget(tps_group, 0, 1)

        # Engine Coolant Temperature (Real 28M4G conversion)
        ect_group = QGroupBox("Coolant Temperature (°C)")
        ect_layout = QVBoxLayout(ect_group)
        self.ect_label = QLabel("40 °C")  # Default ECT when engine off
        self.ect_label.setAlignment(Qt.AlignCenter)
        self.ect_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.ect_bar = QProgressBar()
        self.ect_bar.setRange(-40, 120)  # 28M4G temperature range
        self.ect_bar.setTextVisible(False)
        ect_layout.addWidget(self.ect_label)
        ect_layout.addWidget(self.ect_bar)
        layout.addWidget(ect_group, 1, 0)

        # Intake Air Temperature (New 28M4G parameter)
        iat_group = QGroupBox("Intake Air Temperature (°C)")
        iat_layout = QVBoxLayout(iat_group)
        self.iat_label = QLabel("20 °C")  # Default IAT
        self.iat_label.setAlignment(Qt.AlignCenter)
        self.iat_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.iat_bar = QProgressBar()
        self.iat_bar.setRange(-40, 120)
        self.iat_bar.setTextVisible(False)
        iat_layout.addWidget(self.iat_label)
        iat_layout.addWidget(self.iat_bar)
        layout.addWidget(iat_group, 1, 1)

        # === Additional 28M4G Parameters ===

        # Manifold Absolute Pressure
        map_group = QGroupBox("MAP (kPa)")
        map_layout = QVBoxLayout(map_group)
        self.map_label = QLabel("100 kPa")
        self.map_label.setAlignment(Qt.AlignCenter)
        self.map_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.map_bar = QProgressBar()
        self.map_bar.setRange(0, 300)  # Typical MAP range
        self.map_bar.setTextVisible(False)
        map_layout.addWidget(self.map_label)
        map_layout.addWidget(self.map_bar)
        layout.addWidget(map_group, 2, 0)

        # Battery Voltage (Critical for safety)
        battery_group = QGroupBox("Battery Voltage")
        battery_layout = QVBoxLayout(battery_group)
        self.battery_label = QLabel("12.5 V")
        self.battery_label.setAlignment(Qt.AlignCenter)
        self.battery_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.battery_bar = QProgressBar()
        self.battery_bar.setRange(0, 20)  # 0-20V range
        self.battery_bar.setTextVisible(False)
        # Color-code voltage levels
        self.battery_bar.setStyleSheet("""
            QProgressBar::chunk {
                background-color: #ff4444;
            }
        """)
        battery_layout.addWidget(self.battery_label)
        battery_layout.addWidget(self.battery_bar)
        layout.addWidget(battery_group, 2, 1)

        # === Hardware and Communication Status ===

        # Hardware Status Panel
        hw_group = QGroupBox("Hardware Status")
        hw_layout = QVBoxLayout(hw_group)

        # Connection Status
        self.connection_status = QLabel("🟡 No Connection")
        self.connection_status.setFont(QFont("Arial", 12, QFont.Bold))
        hw_layout.addWidget(self.connection_status)

        # Communication Stability
        self.comm_status = QLabel("Communication: --%")
        self.comm_status.setFont(QFont("Arial", 10))
        hw_layout.addWidget(self.comm_status)

        # Adapter Info
        self.adapter_info = QLabel("Adapter: None")
        self.adapter_info.setFont(QFont("Arial", 10))
        hw_layout.addWidget(self.adapter_info)

        layout.addWidget(hw_group, 3, 0)

        # Control Panel
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout(control_group)

        # Logging Status
        self.logging_status = QLabel("🔴 Logging: OFF")
        self.logging_status.setFont(QFont("Arial", 12, QFont.Bold))
        control_layout.addWidget(self.logging_status)

        # Scan Button
        self.scan_btn = QPushButton("🔍 Scan Live Data IDs")
        self.scan_btn.clicked.connect(self.open_scanner)
        control_layout.addWidget(self.scan_btn)

        layout.addWidget(control_group, 3, 1)

    def open_scanner(self):
        if not self.protocol:
            return
        dialog = ScannerDialog(self.protocol, self)
        dialog.exec()

    def update_data(self):
        """Update dashboard with real 28M4G parameter data."""
        data = self.logger.get_latest_data()
        if data:
            # Real 28M4G parameters with proper conversions
            rpm = data.get('RPM', 0)  # Already converted by EcuParameter
            tps = data.get('TPS', 0)  # Already converted to percentage
            ect = data.get('ECT', 40)  # Engine Coolant Temperature
            iat = data.get('IAT', 20)  # Intake Air Temperature
            map_pressure = data.get('MAP', 100)  # Manifold Absolute Pressure

            # Update RPM
            self.rpm_label.setText(f"{rpm:.0f} RPM")
            self.rpm_bar.setValue(int(min(rpm, 12000)))

            # Update TPS
            self.tps_label.setText(f"{tps:.1f} %")
            self.tps_bar.setValue(int(tps))

            # Update ECT (with temperature warning colors)
            self.ect_label.setText(f"{ect:.0f} °C")
            self.ect_bar.setValue(int(ect))
            if ect > 100:
                self.ect_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff4444; }")
            elif ect > 90:
                self.ect_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff8800; }")
            else:
                self.ect_bar.setStyleSheet("QProgressBar::chunk { background-color: #44ff44; }")

            # Update IAT
            self.iat_label.setText(f"{iat:.0f} °C")
            self.iat_bar.setValue(int(iat))

            # Update MAP
            self.map_label.setText(f"{map_pressure:.0f} kPa")
            self.map_bar.setValue(int(map_pressure))

            # Update logging status
            if self.logger.is_logging:
                self.logging_status.setText("🟢 Logging: ON")
            else:
                self.logging_status.setText("🔴 Logging: OFF")

    def update_hardware_status(self):
        """Update hardware and communication status indicators."""
        if not self.kwp_client:
            self.connection_status.setText("🟡 No KWP Client")
            self.comm_status.setText("Communication: N/A")
            self.adapter_info.setText("Adapter: None")
            return

        # Update connection status
        if self.kwp_client.simulation_mode:
            self.connection_status.setText("🟡 Simulation Mode")
            self.comm_status.setText("Communication: Simulated")
            self.adapter_info.setText("Adapter: Simulated")
        else:
            # Real hardware connection
            try:
                # Check battery voltage
                voltage = self.kwp_client.get_battery_voltage()
                self.battery_label.setText(f"{voltage:.1f} V")
                self.battery_bar.setValue(int(voltage * 10))  # Scale for progress bar

                # Color-code battery voltage
                if voltage >= 12.5:
                    color = "#44ff44"  # Green
                    status = "🟢"
                elif voltage >= 12.0:
                    color = "#ffaa00"  # Orange
                    status = "🟡"
                else:
                    color = "#ff4444"  # Red
                    status = "🔴"

                self.battery_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")
                self.connection_status.setText(f"{status} Connected ({voltage:.1f}V)")

                # Update communication stability
                stability = self.kwp_client.get_communication_stability()
                stats = self.kwp_client.communication_stats
                self.comm_status.setText(f"Communication: {stability:.1%} ({stats['total_requests']} requests)")

                # Update adapter info
                self.adapter_info.setText(f"Port: {self.kwp_client.port}")

            except Exception as e:
                self.connection_status.setText("🔴 Connection Error")
                self.comm_status.setText(f"Error: {str(e)[:30]}...")

    def set_status(self, status_text):
        """Public method to update dashboard status."""
        # This can be called from main window to update status
        self.adapter_info.setText(f"Status: {status_text}")

    def get_current_values(self) -> dict:
        """Get current dashboard values for other components."""
        return {
            'rpm': int(self.rpm_label.text().split()[0]),
            'tps': float(self.tps_label.text().split()[0]),
            'ect': int(self.ect_label.text().split()[0]),
            'iat': int(self.iat_label.text().split()[0]),
            'map': int(self.map_label.text().split()[0]),
            'battery': float(self.battery_label.text().split()[0])
        }