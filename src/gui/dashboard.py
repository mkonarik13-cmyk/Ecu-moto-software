from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                               QGroupBox, QLabel, QProgressBar)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

class DashboardWidget(QWidget):
    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.setup_ui()
        
        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(100)  # 10Hz update

    def setup_ui(self):
        layout = QGridLayout(self)
        
        # RPM Gauge (Simulated with Progress Bar)
        rpm_group = QGroupBox("Engine Speed")
        rpm_layout = QVBoxLayout(rpm_group)
        self.rpm_label = QLabel("0 RPM")
        self.rpm_label.setAlignment(Qt.AlignCenter)
        self.rpm_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.rpm_bar = QProgressBar()
        self.rpm_bar.setRange(0, 12000)
        self.rpm_bar.setTextVisible(False)
        rpm_layout.addWidget(self.rpm_label)
        rpm_layout.addWidget(self.rpm_bar)
        layout.addWidget(rpm_group, 0, 0)

        # TPS Gauge
        tps_group = QGroupBox("Throttle Position")
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

        # Temperature
        temp_group = QGroupBox("Coolant Temp")
        temp_layout = QVBoxLayout(temp_group)
        self.temp_label = QLabel("0 °C")
        self.temp_label.setAlignment(Qt.AlignCenter)
        self.temp_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.temp_bar = QProgressBar()
        self.temp_bar.setRange(0, 120)
        self.temp_bar.setTextVisible(False)
        temp_layout.addWidget(self.temp_label)
        temp_layout.addWidget(self.temp_bar)
        layout.addWidget(temp_group, 1, 0)

        # Status
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_group, 1, 1)

    def update_data(self):
        data = self.logger.get_latest_data()
        if data:
            rpm = data.get('Engine Speed', 0)
            tps = data.get('Throttle Position', 0)
            temp = data.get('Coolant Temp', 0)

            self.rpm_label.setText(f"{rpm:.0f} RPM")
            self.rpm_bar.setValue(int(rpm))

            self.tps_label.setText(f"{tps:.1f} %")
            self.tps_bar.setValue(int(tps))

            self.temp_label.setText(f"{temp:.0f} °C")
            self.temp_bar.setValue(int(temp))
            
            self.status_label.setText(f"Logging: {self.logger.is_logging}")