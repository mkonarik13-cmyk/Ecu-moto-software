"""
Fan settings widget for configuring motorcycle cooling fan behavior
Provides temperature threshold settings and fan control options
"""

from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QSlider, QCheckBox, QSpinBox, QComboBox,
    QMessageBox, QProgressBar, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from src.ecu.connection import ECUConnection
from src.maps.types import FanSettings, EngineType
from src.utils.logger import get_gui_logger


class TemperatureGauge(QWidget):
    """Custom temperature gauge for visual feedback"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_temp = 75.0
        self.fan_on_temp = 95.0
        self.fan_off_temp = 85.0
        self.setMinimumWidth(60)
        self.setMinimumHeight(200)

    def set_temperature(self, temp: float):
        self.current_temp = temp
        self.update()

    def set_thresholds(self, on_temp: float, off_temp: float):
        self.fan_on_temp = on_temp
        self.fan_off_temp = off_temp
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient
        from PySide6.QtCore import QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        margin = 10

        # Draw temperature scale background
        gauge_rect = QRectF(margin, margin, width - 2*margin, height - 2*margin)

        # Temperature range (0-120°C)
        temp_range = 120
        current_ratio = self.current_temp / temp_range
        on_ratio = self.fan_on_temp / temp_range
        off_ratio = self.fan_off_temp / temp_range

        # Draw background
        painter.fillRect(gauge_rect, QColor(40, 40, 40))

        # Draw color zones
        zone_height = gauge_rect.height() / temp_range

        # Blue zone (safe)
        blue_height = off_ratio * gauge_rect.height()
        blue_rect = QRectF(gauge_rect.left(),
                          gauge_rect.bottom() - blue_height,
                          gauge_rect.width(), blue_height)
        painter.fillRect(blue_rect, QColor(33, 150, 243))

        # Yellow zone (warning)
        yellow_height = (on_ratio - off_ratio) * gauge_rect.height()
        yellow_rect = QRectF(gauge_rect.left(),
                           gauge_rect.bottom() - blue_height - yellow_height,
                           gauge_rect.width(), yellow_height)
        painter.fillRect(yellow_rect, QColor(255, 193, 7))

        # Red zone (danger)
        red_height = (1.0 - on_ratio) * gauge_rect.height()
        red_rect = QRectF(gauge_rect.left(),
                        gauge_rect.top(),
                        gauge_rect.width(), red_height)
        painter.fillRect(red_rect, QColor(244, 67, 54))

        # Draw current temperature indicator
        current_y = gauge_rect.bottom() - (current_ratio * gauge_rect.height())
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.drawLine(gauge_rect.left() - 5, current_y,
                        gauge_rect.right() + 5, current_y)

        # Draw temperature text
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        font = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font)
        temp_text = f"{self.current_temp:.0f}°C"
        painter.drawText(gauge_rect, Qt.AlignCenter, temp_text)

        # Draw thresholds
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        font = QFont("Arial", 8)
        painter.setFont(font)

        # Fan ON threshold
        on_y = gauge_rect.bottom() - (on_ratio * gauge_rect.height())
        painter.drawLine(gauge_rect.left(), on_y, gauge_rect.right(), on_y)
        painter.drawText(gauge_rect.left(), on_y - 5, f"ON: {self.fan_on_temp:.0f}°")

        # Fan OFF threshold
        off_y = gauge_rect.bottom() - (off_ratio * gauge_rect.height())
        painter.drawLine(gauge_rect.left(), off_y, gauge_rect.right(), off_y)
        painter.drawText(gauge_rect.left(), off_y - 5, f"OFF: {self.fan_off_temp:.0f}°")


class FanSettingsWidget(QWidget):
    """Fan settings widget for motorcycle cooling configuration"""

    def __init__(self):
        super().__init__()
        self.logger = get_gui_logger()
        self.ecu_connection: Optional[ECUConnection] = None
        self.current_fan_settings: Optional[FanSettings] = None
        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self.update_simulation)

        self.setup_ui()
        self.setup_style()
        self.load_default_settings()

    def setup_ui(self):
        """Setup fan settings UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Temperature Thresholds Section
        thresholds_group = self.create_thresholds_section()
        content_layout.addWidget(thresholds_group)

        # Fan Control Section
        control_group = self.create_control_section()
        content_layout.addWidget(control_group)

        # Mode Settings Section
        mode_group = self.create_mode_section()
        content_layout.addWidget(mode_group)

        # Live Monitoring Section
        monitoring_group = self.create_monitoring_section()
        content_layout.addWidget(monitoring_group)

        # Testing Section
        testing_group = self.create_testing_section()
        content_layout.addWidget(testing_group)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def create_thresholds_section(self) -> QGroupBox:
        """Create temperature thresholds section"""
        group = QGroupBox("Temperature Thresholds")
        layout = QGridLayout(group)

        # Fan ON temperature
        layout.addWidget(QLabel("Fan ON Temperature:"), 0, 0)
        self.fan_on_slider = QSlider(Qt.Horizontal)
        self.fan_on_slider.setRange(70, 105)
        self.fan_on_slider.setValue(95)
        self.fan_on_slider.valueChanged.connect(self.on_threshold_changed)
        layout.addWidget(self.fan_on_slider, 0, 1)

        self.fan_on_spin = QSpinBox()
        self.fan_on_spin.setRange(70, 105)
        self.fan_on_spin.setValue(95)
        self.fan_on_spin.setSuffix(" °C")
        self.fan_on_spin.valueChanged.connect(self.on_spin_threshold_changed)
        layout.addWidget(self.fan_on_spin, 0, 2)

        # Fan OFF temperature
        layout.addWidget(QLabel("Fan OFF Temperature:"), 1, 0)
        self.fan_off_slider = QSlider(Qt.Horizontal)
        self.fan_off_slider.setRange(60, 95)
        self.fan_off_slider.setValue(85)
        self.fan_off_slider.valueChanged.connect(self.on_threshold_changed)
        layout.addWidget(self.fan_off_slider, 1, 1)

        self.fan_off_spin = QSpinBox()
        self.fan_off_spin.setRange(60, 95)
        self.fan_off_spin.setValue(85)
        self.fan_off_spin.setSuffix(" °C")
        self.fan_off_spin.valueChanged.connect(self.on_spin_threshold_changed)
        layout.addWidget(self.fan_off_spin, 1, 2)

        # Hysteresis display
        layout.addWidget(QLabel("Hysteresis:"), 2, 0)
        self.hysteresis_label = QLabel("10 °C")
        layout.addWidget(self.hysteresis_label, 2, 1)

        # Temperature gauge
        self.temp_gauge = TemperatureGauge()
        layout.addWidget(self.temp_gauge, 0, 3, 3, 1)

        return group

    def create_control_section(self) -> QGroupBox:
        """Create fan control options section"""
        group = QGroupBox("Fan Control Options")
        layout = QVBoxLayout(group)

        # Variable speed control
        self.variable_speed_checkbox = QCheckBox("Enable Variable Speed Control")
        self.variable_speed_checkbox.setChecked(False)
        layout.addWidget(self.variable_speed_checkbox)

        # Dual fan configuration
        self.dual_fan_checkbox = QCheckBox("Dual Fan Configuration")
        self.dual_fan_checkbox.setChecked(False)
        self.dual_fan_checkbox.toggled.connect(self.on_dual_fan_toggled)
        layout.addWidget(self.dual_fan_checkbox)

        # High temperature boost
        boost_layout = QHBoxLayout()
        boost_layout.addWidget(QLabel("High Temp Boost:"))

        self.boost_combo = QComboBox()
        self.boost_combo.addItems(["Off", "Low (+10%)", "Medium (+20%)", "High (+30%)"])
        self.boost_combo.setCurrentText("Medium (+20%)")
        boost_layout.addWidget(self.boost_combo)

        boost_layout.addStretch()
        layout.addLayout(boost_layout)

        # Minimum fan speed (if variable speed)
        min_speed_layout = QHBoxLayout()
        min_speed_layout.addWidget(QLabel("Minimum Speed:"))

        self.min_speed_spin = QSpinBox()
        self.min_speed_spin.setRange(30, 100)
        self.min_speed_spin.setValue(40)
        self.min_speed_spin.setSuffix(" %")
        min_speed_layout.addWidget(self.min_speed_spin)

        min_speed_layout.addStretch()
        layout.addLayout(min_speed_layout)

        # Maximum fan speed
        max_speed_layout = QHBoxLayout()
        max_speed_layout.addWidget(QLabel("Maximum Speed:"))

        self.max_speed_spin = QSpinBox()
        self.max_speed_spin.setRange(50, 100)
        self.max_speed_spin.setValue(100)
        self.max_speed_spin.setSuffix(" %")
        max_speed_layout.addWidget(self.max_speed_spin)

        max_speed_layout.addStretch()
        layout.addLayout(max_speed_layout)

        return group

    def create_mode_section(self) -> QGroupBox:
        """Create riding mode settings section"""
        group = QGroupBox("Riding Mode Settings")
        layout = QGridLayout(group)

        # Track mode
        layout.addWidget(QLabel("Track Day Mode:"), 0, 0)
        self.track_mode_checkbox = QCheckBox("Enable Aggressive Cooling")
        self.track_mode_checkbox.setChecked(False)
        self.track_mode_checkbox.toggled.connect(self.on_track_mode_toggled)
        layout.addWidget(self.track_mode_checkbox, 0, 1)

        # Track mode settings
        self.track_on_temp_spin = QSpinBox()
        self.track_on_temp_spin.setRange(80, 100)
        self.track_on_temp_spin.setValue(90)
        self.track_on_temp_spin.setSuffix(" °C")
        layout.addWidget(QLabel("Track Fan ON:"), 1, 0)
        layout.addWidget(self.track_on_temp_spin, 1, 1)

        # Traffic mode
        layout.addWidget(QLabel("Traffic Jam Mode:"), 2, 0)
        self.traffic_mode_checkbox = QCheckBox("Enable Enhanced Low-Speed Cooling")
        self.traffic_mode_checkbox.setChecked(False)
        layout.addWidget(self.traffic_mode_checkbox, 2, 1)

        # Traffic mode settings
        self.traffic_on_temp_spin = QSpinBox()
        self.traffic_on_temp_spin.setRange(70, 90)
        self.traffic_on_temp_spin.setValue(80)
        self.traffic_on_temp_spin.setSuffix(" °C")
        layout.addWidget(QLabel("Traffic Fan ON:"), 3, 0)
        layout.addWidget(self.traffic_on_temp_spin, 3, 1)

        return group

    def create_monitoring_section(self) -> QGroupBox:
        """Create live monitoring section"""
        group = QGroupBox("Live Monitoring")
        layout = QGridLayout(group)

        # Current temperature
        layout.addWidget(QLabel("Current Temperature:"), 0, 0)
        self.current_temp_label = QLabel("--.- °C")
        self.current_temp_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4caf50;")
        layout.addWidget(self.current_temp_label, 0, 1)

        # Fan status
        layout.addWidget(QLabel("Fan Status:"), 1, 0)
        self.fan_status_label = QLabel("Unknown")
        self.fan_status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.fan_status_label, 1, 1)

        # Fan speed (if variable speed)
        layout.addWidget(QLabel("Fan Speed:"), 2, 0)
        self.fan_speed_label = QLabel("-- %")
        layout.addWidget(self.fan_speed_label, 2, 1)

        # Fan speed progress bar
        self.fan_speed_progress = QProgressBar()
        self.fan_speed_progress.setRange(0, 100)
        layout.addWidget(self.fan_speed_progress, 3, 0, 1, 2)

        # Last activation
        layout.addWidget(QLabel("Last Activation:"), 4, 0)
        self.last_activation_label = QLabel("Never")
        layout.addWidget(self.last_activation_label, 4, 1)

        return group

    def create_testing_section(self) -> QGroupBox:
        """Create fan testing section"""
        group = QGroupBox("Fan Testing")
        layout = QVBoxLayout(group)

        # Test controls
        test_layout = QHBoxLayout()

        self.test_fan_button = QPushButton("Test Fan Operation")
        self.test_fan_button.clicked.connect(self.test_fan)
        test_layout.addWidget(self.test_fan_button)

        self.stop_test_button = QPushButton("Stop Test")
        self.stop_test_button.clicked.connect(self.stop_fan_test)
        self.stop_test_button.setEnabled(False)
        test_layout.addWidget(self.stop_test_button)

        test_layout.addStretch()
        layout.addLayout(test_layout)

        # Test status
        self.test_status_label = QLabel("Ready for testing")
        layout.addWidget(self.test_status_label)

        # Test results
        test_results_layout = QGridLayout()

        test_results_layout.addWidget(QLabel("Response Time:"), 0, 0)
        self.response_time_label = QLabel("-- ms")
        test_results_layout.addWidget(self.response_time_label, 0, 1)

        test_results_layout.addWidget(QLabel("Current Draw:"), 1, 0)
        self.current_draw_label = QLabel("-- A")
        test_results_layout.addWidget(self.current_draw_label, 1, 1)

        layout.addLayout(test_results_layout)

        return group

    def setup_style(self):
        """Setup widget styling"""
        try:
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
                    color: #ddd;
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
                QSlider::groove:horizontal {
                    border: 1px solid #555;
                    height: 8px;
                    background: #404040;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #0078d4;
                    border: 1px solid #555;
                    width: 18px;
                    margin: -5px 0;
                    border-radius: 9px;
                }
                QCheckBox {
                    color: #ddd;
                }
                QComboBox {
                    background-color: #404040;
                    border: 1px solid #555;
                    padding: 5px;
                    border-radius: 4px;
                    color: #ddd;
                }
                QSpinBox {
                    background-color: #404040;
                    border: 1px solid #555;
                    padding: 5px;
                    border-radius: 4px;
                    color: #ddd;
                }
                QProgressBar {
                    border: 1px solid #555;
                    border-radius: 4px;
                    text-align: center;
                    color: #ddd;
                }
                QProgressBar::chunk {
                    background-color: #0078d4;
                    border-radius: 3px;
                }
            """)
        except Exception as e:
            self.logger.error(f"Failed to set style: {e}")
            # Fallback - minimal styling
            self.setStyleSheet("""
                QWidget {
                    background-color: #2d2d2d;
                    color: #ddd;
                }
            """)

    def set_ecu_connection(self, ecu_connection: Optional[ECUConnection]):
        """Set ECU connection reference"""
        self.ecu_connection = ecu_connection

        if ecu_connection and ecu_connection.is_connected():
            self.start_simulation()
        else:
            self.stop_simulation()

    def load_default_settings(self):
        """Load default fan settings"""
        self.current_fan_settings = FanSettings(
            on_temp=95.0,
            off_temp=85.0,
            high_temp_boost=20.0,
            variable_speed=False,
            dual_fan=False,
            track_mode=False
        )

        # Update UI with default values
        self.fan_on_slider.setValue(95)
        self.fan_off_slider.setValue(85)
        self.variable_speed_checkbox.setChecked(False)
        self.dual_fan_checkbox.setChecked(False)

    def on_threshold_changed(self):
        """Handle threshold slider changes"""
        on_temp = self.fan_on_slider.value()
        off_temp = self.fan_off_slider.value()

        # Ensure ON temperature is always higher than OFF temperature
        if on_temp <= off_temp:
            on_temp = off_temp + 1
            self.fan_on_slider.setValue(on_temp)

        # Update spinboxes
        self.fan_on_spin.setValue(on_temp)
        self.fan_off_spin.setValue(off_temp)

        # Update hysteresis
        hysteresis = on_temp - off_temp
        self.hysteresis_label.setText(f"{hysteresis} °C")

        # Update temperature gauge
        self.temp_gauge.set_thresholds(on_temp, off_temp)

        # Update current settings
        if self.current_fan_settings:
            self.current_fan_settings.on_temp = on_temp
            self.current_fan_settings.off_temp = off_temp

    def on_spin_threshold_changed(self):
        """Handle threshold spinbox changes"""
        on_temp = self.fan_on_spin.value()
        off_temp = self.fan_off_spin.value()

        # Ensure ON temperature is always higher than OFF temperature
        if on_temp <= off_temp:
            on_temp = off_temp + 1
            self.fan_on_spin.setValue(on_temp)

        # Update sliders
        self.fan_on_slider.setValue(on_temp)
        self.fan_off_slider.setValue(off_temp)

        # Update hysteresis
        hysteresis = on_temp - off_temp
        self.hysteresis_label.setText(f"{hysteresis} °C")

        # Update temperature gauge
        self.temp_gauge.set_thresholds(on_temp, off_temp)

    def on_dual_fan_toggled(self, enabled: bool):
        """Handle dual fan toggle"""
        if self.current_fan_settings:
            self.current_fan_settings.dual_fan = enabled

        # Show/hide dual fan specific options
        if enabled:
            # Could show additional dual fan controls here
            self.logger.info("Dual fan mode enabled")
        else:
            self.logger.info("Single fan mode")

    def on_track_mode_toggled(self, enabled: bool):
        """Handle track mode toggle"""
        if self.current_fan_settings:
            self.current_fan_settings.track_mode = enabled

        if enabled:
            # Enable track mode settings
            self.track_on_temp_spin.setEnabled(True)
            self.logger.info(f"Track mode enabled - Fan ON at {self.track_on_temp_spin.value()}°C")
        else:
            # Disable track mode settings
            self.track_on_temp_spin.setEnabled(False)
            self.logger.info("Track mode disabled")

    def test_fan(self):
        """Test fan operation"""
        if not self.ecu_connection or not self.ecu_connection.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to ECU first")
            return

        reply = QMessageBox.question(
            self, 'Fan Test',
            'This will activate the cooling fan for testing.\n\n'
            'Ensure the motorcycle is in a safe location.\n\n'
            'Continue with fan test?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.test_status_label.setText("Testing fan...")
            self.test_fan_button.setEnabled(False)
            self.stop_test_button.setEnabled(True)

            # Start test (placeholder - would send actual command to ECU)
            self.logger.info("Starting fan test")

            # Simulate test results
            import random
            response_time = random.randint(200, 500)
            current_draw = random.uniform(2.5, 4.5)

            self.response_time_label.setText(f"{response_time} ms")
            self.current_draw_label.setText(f"{current_draw:.1f} A")

            self.test_status_label.setText("Fan test running...")

    def stop_fan_test(self):
        """Stop fan test"""
        self.test_status_label.setText("Test stopped")
        self.test_fan_button.setEnabled(True)
        self.stop_test_button.setEnabled(False)

        # Stop test (placeholder - would send actual command to ECU)
        self.logger.info("Fan test stopped")

    def start_simulation(self):
        """Start temperature simulation"""
        self.simulation_timer.start(2000)  # Update every 2 seconds

    def stop_simulation(self):
        """Stop temperature simulation"""
        self.simulation_timer.stop()
        self.reset_monitoring_display()

    def reset_monitoring_display(self):
        """Reset monitoring display to default state"""
        self.current_temp_label.setText("--.- °C")
        self.fan_status_label.setText("Unknown")
        self.fan_status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #888;")
        self.fan_speed_label.setText("-- %")
        self.fan_speed_progress.setValue(0)
        self.last_activation_label.setText("Never")

    def update_simulation(self):
        """Update simulated temperature and fan status"""
        import random
        import time

        # Simulate temperature changes
        current_temp = getattr(self, '_sim_temp', 75.0)
        temp_change = random.uniform(-3, 4)
        current_temp = max(60, min(110, current_temp + temp_change))
        self._sim_temp = current_temp

        # Update temperature display
        self.current_temp_label.setText(f"{current_temp:.1f} °C")
        self.temp_gauge.set_temperature(current_temp)

        # Determine fan status based on thresholds
        on_temp = self.fan_on_slider.value()
        off_temp = self.fan_off_slider.value()

        # Get track mode setting
        track_mode = self.track_mode_checkbox.isChecked()
        if track_mode:
            on_temp = min(on_temp, self.track_on_temp_spin.value())

        if current_temp >= on_temp:
            fan_status = "ON"
            color = "#4caf50"  # Green
            fan_speed = 100
        elif current_temp <= off_temp:
            fan_status = "OFF"
            color = "#2196f3"  # Blue
            fan_speed = 0
        else:
            fan_status = "INTERMITTENT"
            color = "#ff9800"  # Orange
            # Variable speed in hysteresis zone
            if self.variable_speed_checkbox.isChecked():
                speed_range = (current_temp - off_temp) / (on_temp - off_temp)
                fan_speed = int(self.min_speed_spin.value() +
                               speed_range * (self.max_speed_spin.value() - self.min_speed_spin.value()))
            else:
                fan_speed = 100

        self.fan_status_label.setText(fan_status)
        self.fan_status_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
        self.fan_speed_label.setText(f"{fan_speed} %")
        self.fan_speed_progress.setValue(fan_speed)

        # Update last activation time
        if fan_status == "ON":
            self.last_activation_label.setText(time.strftime("%H:%M:%S"))

    def save_settings(self):
        """Save current fan settings to ECU"""
        if not self.ecu_connection or not self.ecu_connection.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to ECU first")
            return

        try:
            # Build fan settings object
            fan_settings = FanSettings(
                on_temp=float(self.fan_on_slider.value()),
                off_temp=float(self.fan_off_slider.value()),
                high_temp_boost=float(self.boost_combo.currentText().split('+')[1].split('%')[0]),
                variable_speed=self.variable_speed_checkbox.isChecked(),
                dual_fan=self.dual_fan_checkbox.isChecked(),
                track_mode=self.track_mode_checkbox.isChecked()
            )

            # Send settings to ECU (placeholder - would use actual protocol commands)
            self.logger.info(f"Saving fan settings: {fan_settings}")

            QMessageBox.information(self, "Settings Saved",
                                  "Fan settings have been saved to ECU successfully")

        except Exception as e:
            self.logger.error(f"Failed to save fan settings: {e}")
            QMessageBox.critical(self, "Save Failed",
                               f"Failed to save fan settings:\n{str(e)}")

    def load_settings(self):
        """Load fan settings from ECU"""
        if not self.ecu_connection or not self.ecu_connection.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to ECU first")
            return

        try:
            # Load settings from ECU (placeholder - would use actual protocol commands)
            self.logger.info("Loading fan settings from ECU")

            # Update UI with loaded settings (using current values as demo)
            QMessageBox.information(self, "Settings Loaded",
                                  "Fan settings have been loaded from ECU successfully")

        except Exception as e:
            self.logger.error(f"Failed to load fan settings: {e}")
            QMessageBox.critical(self, "Load Failed",
                               f"Failed to load fan settings:\n{str(e)}")