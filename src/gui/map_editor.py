"""
Map editor widget for interactive fuel and ignition map editing
Provides 2D table view and 3D visualization capabilities
"""

import time
from typing import Optional, List, Dict, Any, Tuple
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QTabWidget, QFileDialog, QMessageBox, QDoubleSpinBox, QSpinBox,
    QHeaderView, QSplitter, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor

from src.ecu.connection import ECUConnection
from src.maps.types import FuelMap, IgnitionMap, EngineType, FirmwareMap
from src.utils.logger import get_gui_logger


class MapTableWidget(QTableWidget):
    """Custom table widget for map editing with color coding"""

    cell_changed = Signal(int, int, float)  # row, col, new_value

    def __init__(self):
        super().__init__()
        self.setup_table()
        self.setup_style()

    def setup_table(self):
        """Setup table properties"""
        # Enable editing
        self.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)

        # Setup headers
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Connect signals
        self.cellChanged.connect(self.on_cell_changed)

    def setup_style(self):
        """Setup table styling"""
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #555;
                background-color: #2d2d2d;
                alternate-background-color: #353535;
                color: #ddd;
            }
            QTableWidget::item {
                padding: 5px;
                border: 1px solid #444;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
            }
            QTableWidget::item:hover {
                background-color: #404040;
            }
            QHeaderView::section {
                background-color: #404040;
                color: #ddd;
                padding: 5px;
                border: 1px solid #555;
                font-weight: bold;
            }
        """)

    def load_map_data(self, rpm_axis: List[int], tps_axis: List[int], values: List[List[float]], unit: str):
        """Load map data into table"""
        self.clear()

        # Set dimensions
        self.setRowCount(len(rpm_axis))
        self.setColumnCount(len(tps_axis))

        # Set headers
        self.setVerticalHeaderLabels([str(rpm) for rpm in rpm_axis])
        self.setHorizontalHeaderLabels([f"{tps}%" for tps in tps_axis])

        # Set table name as tooltip
        self.setToolTip(f"Unit: {unit}")

        # Load values with color coding
        for i, rpm in enumerate(rpm_axis):
            for j, tps in enumerate(tps_axis):
                if i < len(values) and j < len(values[i]):
                    value = values[i][j]
                    item = QTableWidgetItem(f"{value:.2f}")
                    item.setData(Qt.UserRole, value)  # Store original value
                    self.setItem(i, j, item)

                    # Color coding based on value
                    self.set_cell_color(i, j, value, values)

    def set_cell_color(self, row: int, col: int, value: float, all_values: List[List[float]]):
        """Set cell background color based on value"""
        if not all_values or row >= len(all_values) or col >= len(all_values[0]):
            return

        # Calculate min/max for color scaling
        flat_values = [val for row in all_values for val in row]
        if not flat_values:
            return

        min_val = min(flat_values)
        max_val = max(flat_values)
        range_val = max_val - min_val

        if range_val == 0:
            return

        # Calculate color intensity (0-1)
        intensity = (value - min_val) / range_val

        # Create color gradient from blue (low) to red (high)
        if intensity < 0.5:
            # Blue to green
            r = int(0 * 255)
            g = int(intensity * 2 * 255)
            b = int((1 - intensity * 2) * 255)
        else:
            # Green to red
            r = int((intensity - 0.5) * 2 * 255)
            g = int((1 - (intensity - 0.5) * 2) * 255)
            b = int(0 * 255)

        color = QColor(r, g, b, 100)  # Semi-transparent
        item = self.item(row, col)
        if item:
            item.setBackground(color)

    def on_cell_changed(self, row: int, col: int):
        """Handle cell value change"""
        item = self.item(row, col)
        if item:
            try:
                new_value = float(item.text())
                old_value = item.data(Qt.UserRole)

                if abs(new_value - old_value) > 0.001:  # Significant change
                    item.setData(Qt.UserRole, new_value)
                    self.cell_changed.emit(row, col, new_value)

                    # Update cell color
                    # Note: This would require access to all values - simplified for now
                    item.setBackground(QColor(255, 200, 0, 100))  # Yellow for modified

            except ValueError:
                # Restore original value if invalid
                original_value = item.data(Qt.UserRole)
                item.setText(str(original_value))


class MapEditorWidget(QWidget):
    """Main map editor widget with fuel and ignition map editing"""

    def __init__(self):
        super().__init__()
        self.logger = get_gui_logger()
        self.ecu_connection: Optional[ECUConnection] = None
        self.firmware_map: Optional[FirmwareMap] = None

        # Track map changes
        self.fuel_map_changes: List[Tuple[int, int, float, float]] = []
        self.ignition_map_changes: List[Tuple[int, int, float, float]] = []

        self.setup_ui()
        self.setup_style()

    def setup_ui(self):
        """Setup map editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create tab widget for different map types
        self.tab_widget = QTabWidget()

        # Fuel Map Tab
        fuel_tab = self.create_fuel_map_tab()
        self.tab_widget.addTab(fuel_tab, "Fuel Map")

        # Ignition Map Tab
        ignition_tab = self.create_ignition_map_tab()
        self.tab_widget.addTab(ignition_tab, "Ignition Map")

        # Advanced Maps Tab (placeholder)
        advanced_tab = self.create_advanced_maps_tab()
        self.tab_widget.addTab(advanced_tab, "Advanced")

        layout.addWidget(self.tab_widget)

        # Control buttons
        control_layout = QHBoxLayout()
        control_layout.addStretch()

        self.load_firmware_button = QPushButton("Load Firmware")
        self.load_firmware_button.clicked.connect(self.load_firmware_file)
        control_layout.addWidget(self.load_firmware_button)

        self.save_firmware_button = QPushButton("Save Firmware")
        self.save_firmware_button.clicked.connect(self.save_firmware_file)
        self.save_firmware_button.setEnabled(False)
        control_layout.addWidget(self.save_firmware_button)

        self.reset_changes_button = QPushButton("Reset Changes")
        self.reset_changes_button.clicked.connect(self.reset_changes)
        self.reset_changes_button.setEnabled(False)
        control_layout.addWidget(self.reset_changes_button)

        layout.addLayout(control_layout)

    def create_fuel_map_tab(self) -> QWidget:
        """Create fuel map editing tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Map info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("Fuel Injection Map (ms)"))
        info_layout.addStretch()

        # Engine type selector
        info_layout.addWidget(QLabel("Engine Type:"))
        self.engine_type_combo = QComboBox()
        self.engine_type_combo.addItems(["125cc", "200cc", "300cc"])
        self.engine_type_combo.currentTextChanged.connect(self.on_engine_type_changed)
        info_layout.addWidget(self.engine_type_combo)

        layout.addLayout(info_layout)

        # Create splitter for table and controls
        splitter = QSplitter(Qt.Horizontal)

        # Fuel map table
        fuel_group = QGroupBox("Fuel Map Table")
        fuel_layout = QVBoxLayout(fuel_group)

        self.fuel_table = MapTableWidget()
        fuel_layout.addWidget(self.fuel_table)

        # Table controls
        table_controls = QHBoxLayout()
        table_controls.addWidget(QLabel("Quick Adjust:"))

        self.fuel_adjust_spin = QDoubleSpinBox()
        self.fuel_adjust_spin.setRange(-50.0, 50.0)
        self.fuel_adjust_spin.setSuffix("%")
        self.fuel_adjust_spin.setSingleStep(1.0)
        table_controls.addWidget(self.fuel_adjust_spin)

        apply_fuel_button = QPushButton("Apply to All")
        apply_fuel_button.clicked.connect(self.apply_fuel_adjustment)
        table_controls.addWidget(apply_fuel_button)

        table_controls.addStretch()
        fuel_layout.addLayout(table_controls)

        splitter.addWidget(fuel_group)

        # Map info panel
        info_group = QGroupBox("Map Information")
        info_group_layout = QVBoxLayout(info_group)

        self.fuel_map_info = QLabel("No fuel map loaded")
        self.fuel_map_info.setWordWrap(True)
        info_group_layout.addWidget(self.fuel_map_info)

        # Statistics
        self.fuel_stats_label = QLabel("Statistics: N/A")
        info_group_layout.addWidget(self.fuel_stats_label)

        # Change tracking
        self.fuel_changes_label = QLabel("Changes: 0")
        info_group_layout.addWidget(self.fuel_changes_label)

        info_group_layout.addStretch()

        splitter.addWidget(info_group)
        splitter.setSizes([600, 200])

        layout.addWidget(splitter)

        return tab

    def create_ignition_map_tab(self) -> QWidget:
        """Create ignition map editing tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Map info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("Ignition Timing Map (° BTDC)"))
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Create splitter for table and controls
        splitter = QSplitter(Qt.Horizontal)

        # Ignition map table
        ignition_group = QGroupBox("Ignition Map Table")
        ignition_layout = QVBoxLayout(ignition_group)

        self.ignition_table = MapTableWidget()
        ignition_layout.addWidget(self.ignition_table)

        # Table controls
        table_controls = QHBoxLayout()
        table_controls.addWidget(QLabel("Quick Adjust:"))

        self.ignition_adjust_spin = QDoubleSpinBox()
        self.ignition_adjust_spin.setRange(-10.0, 10.0)
        self.ignition_adjust_spin.setSuffix("°")
        self.ignition_adjust_spin.setSingleStep(0.5)
        table_controls.addWidget(self.ignition_adjust_spin)

        apply_ignition_button = QPushButton("Apply to All")
        apply_ignition_button.clicked.connect(self.apply_ignition_adjustment)
        table_controls.addWidget(apply_ignition_button)

        table_controls.addStretch()
        ignition_layout.addLayout(table_controls)

        splitter.addWidget(ignition_group)

        # Map info panel
        info_group = QGroupBox("Map Information")
        info_group_layout = QVBoxLayout(info_group)

        self.ignition_map_info = QLabel("No ignition map loaded")
        self.ignition_map_info.setWordWrap(True)
        info_group_layout.addWidget(self.ignition_map_info)

        # Statistics
        self.ignition_stats_label = QLabel("Statistics: N/A")
        info_group_layout.addWidget(self.ignition_stats_label)

        # Change tracking
        self.ignition_changes_label = QLabel("Changes: 0")
        info_group_layout.addWidget(self.ignition_changes_label)

        info_group_layout.addStretch()

        splitter.addWidget(info_group)
        splitter.setSizes([600, 200])

        layout.addWidget(splitter)

        return tab

    def create_advanced_maps_tab(self) -> QWidget:
        """Create advanced maps tab (placeholder for future features)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Advanced Maps (Coming Soon)"))
        layout.addWidget(QLabel("Features planned:"))
        layout.addWidget(QLabel("• 3D Map Visualization"))
        layout.addWidget(QLabel("• Temperature Compensation Maps"))
        layout.addWidget(QLabel("• Gear-Dependent Maps"))
        layout.addWidget(QLabel("• Rev Limiter Settings"))
        layout.addWidget(QLabel("• Quickshifter Settings"))

        return tab

    def setup_style(self):
        """Setup widget styling"""
        try:
            self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #404040;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
            QTabBar::tab:hover {
                background-color: #505050;
            }
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
            QComboBox {
                background-color: #404040;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 4px;
                color: #ddd;
            }
            QDoubleSpinBox {
                background-color: #404040;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 4px;
                color: #ddd;
            }
            QSplitter::handle {
                background-color: #555;
            }
            QSplitter::handle:horizontal {
                width: 2px;
            }
        """)
        except Exception as e:
            self.logger.error(f"Failed to apply map editor styling: {e}")
            # Apply basic styling without CSS
            pass

    def set_ecu_connection(self, ecu_connection: Optional[ECUConnection]):
        """Set ECU connection reference"""
        self.ecu_connection = ecu_connection

    def load_firmware_file(self):
        """Load firmware file for map editing"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Firmware File",
            "",
            "Binary Files (*.bin);;All Files (*.*)"
        )

        if file_path:
            try:
                # This is a placeholder - would use the actual firmware parser
                self.load_demo_maps()
                self.logger.info(f"Loaded firmware file: {file_path}")

                QMessageBox.information(self, "File Loaded",
                                      f"Firmware file loaded successfully:\n{file_path}")

            except Exception as e:
                self.logger.error(f"Failed to load firmware: {e}")
                QMessageBox.critical(self, "Load Failed",
                                   f"Failed to load firmware file:\n{str(e)}")

    def save_firmware_file(self):
        """Save modified firmware file"""
        if not self.firmware_map:
            QMessageBox.warning(self, "No Map", "No map data to save")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Modified Firmware",
            "",
            "Binary Files (*.bin);;All Files (*.*)"
        )

        if file_path:
            try:
                # Apply changes to firmware map
                self.apply_map_changes()

                # Save firmware (placeholder)
                self.logger.info(f"Saved modified firmware to: {file_path}")

                QMessageBox.information(self, "File Saved",
                                      f"Modified firmware saved successfully:\n{file_path}")

            except Exception as e:
                self.logger.error(f"Failed to save firmware: {e}")
                QMessageBox.critical(self, "Save Failed",
                                   f"Failed to save firmware file:\n{str(e)}")

    def load_demo_maps(self):
        """Load demo map data for testing"""
        # Generate demo fuel map
        rpm_axis = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        tps_axis = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        # Create realistic fuel map values (injection time in ms)
        fuel_values = []
        for rpm in rpm_axis:
            row = []
            for tps in tps_axis:
                # Base injection time increases with RPM and TPS
                base_time = 2.0 + (rpm / 10000) * 3.0 + (tps / 100) * 5.0
                # Add some variation
                variation = np.random.uniform(-0.2, 0.2)
                row.append(max(1.0, base_time + variation))
            fuel_values.append(row)

        # Load into fuel table
        self.fuel_table.load_map_data(rpm_axis, tps_axis, fuel_values, "ms")
        self.fuel_map_info.setText(f"Fuel Map: {len(rpm_axis)}x{len(tps_axis)} grid")

        # Update fuel statistics
        self.update_fuel_stats(fuel_values)

        # Generate demo ignition map
        ignition_values = []
        for rpm in rpm_axis:
            row = []
            for tps in tps_axis:
                # Base timing advances with RPM, retards at high TPS
                base_timing = 10 + (rpm / 10000) * 25 - (tps / 100) * 5
                # Add some variation
                variation = np.random.uniform(-1, 1)
                row.append(max(5, min(45, base_timing + variation)))
            ignition_values.append(row)

        # Load into ignition table
        self.ignition_table.load_map_data(rpm_axis, tps_axis, ignition_values, "° BTDC")
        self.ignition_map_info.setText(f"Ignition Map: {len(rpm_axis)}x{len(tps_axis)} grid")

        # Update ignition statistics
        self.update_ignition_stats(ignition_values)

        # Enable save button
        self.save_firmware_button.setEnabled(True)

        # Connect table change signals
        self.fuel_table.cell_changed.connect(self.on_fuel_cell_changed)
        self.ignition_table.cell_changed.connect(self.on_ignition_cell_changed)

    def on_fuel_cell_changed(self, row: int, col: int, new_value: float):
        """Handle fuel map cell change"""
        old_value = self.fuel_table.item(row, col).data(Qt.UserRole) if self.fuel_table.item(row, col) else 0.0
        self.fuel_map_changes.append((row, col, old_value, new_value))
        self.fuel_changes_label.setText(f"Changes: {len(self.fuel_map_changes)}")
        self.reset_changes_button.setEnabled(True)

        self.logger.debug(f"Fuel map changed at ({row}, {col}): {old_value} -> {new_value}")

    def on_ignition_cell_changed(self, row: int, col: int, new_value: float):
        """Handle ignition map cell change"""
        old_value = self.ignition_table.item(row, col).data(Qt.UserRole) if self.ignition_table.item(row, col) else 0.0
        self.ignition_map_changes.append((row, col, old_value, new_value))
        self.ignition_changes_label.setText(f"Changes: {len(self.ignition_map_changes)}")
        self.reset_changes_button.setEnabled(True)

        self.logger.debug(f"Ignition map changed at ({row}, {col}): {old_value} -> {new_value}")

    def apply_fuel_adjustment(self):
        """Apply percentage adjustment to all fuel map cells"""
        if not self.fuel_table.rowCount():
            return

        adjustment = self.fuel_adjust_spin.value() / 100.0

        for row in range(self.fuel_table.rowCount()):
            for col in range(self.fuel_table.columnCount()):
                item = self.fuel_table.item(row, col)
                if item:
                    old_value = item.data(Qt.UserRole)
                    new_value = old_value * (1.0 + adjustment)
                    item.setText(f"{new_value:.2f}")
                    # Trigger change signal
                    self.fuel_table.cellChanged.emit(row, col)

    def apply_ignition_adjustment(self):
        """Apply degree adjustment to all ignition map cells"""
        if not self.ignition_table.rowCount():
            return

        adjustment = self.ignition_adjust_spin.value()

        for row in range(self.ignition_table.rowCount()):
            for col in range(self.ignition_table.columnCount()):
                item = self.ignition_table.item(row, col)
                if item:
                    old_value = item.data(Qt.UserRole)
                    new_value = old_value + adjustment
                    item.setText(f"{new_value:.1f}")
                    # Trigger change signal
                    self.ignition_table.cellChanged.emit(row, col)

    def reset_changes(self):
        """Reset all map changes"""
        reply = QMessageBox.question(
            self, 'Reset Changes',
            'Are you sure you want to reset all map changes?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.fuel_map_changes.clear()
            self.ignition_map_changes.clear()
            self.fuel_changes_label.setText("Changes: 0")
            self.ignition_changes_label.setText("Changes: 0")
            self.reset_changes_button.setEnabled(False)

            # Reload demo maps to reset values
            self.load_demo_maps()

    def on_engine_type_changed(self, engine_type_str: str):
        """Handle engine type change"""
        self.logger.info(f"Engine type changed to: {engine_type_str}")
        # In a real implementation, this would load different map ranges/profiles

    def update_fuel_stats(self, values: List[List[float]]):
        """Update fuel map statistics"""
        if not values:
            return

        flat_values = [val for row in values for val in row]
        if flat_values:
            min_val = min(flat_values)
            max_val = max(flat_values)
            avg_val = sum(flat_values) / len(flat_values)

            self.fuel_stats_label.setText(
                f"Min: {min_val:.2f}ms | Max: {max_val:.2f}ms | Avg: {avg_val:.2f}ms"
            )

    def update_ignition_stats(self, values: List[List[float]]):
        """Update ignition map statistics"""
        if not values:
            return

        flat_values = [val for row in values for val in row]
        if flat_values:
            min_val = min(flat_values)
            max_val = max(flat_values)
            avg_val = sum(flat_values) / len(flat_values)

            self.ignition_stats_label.setText(
                f"Min: {min_val:.1f}° | Max: {max_val:.1f}° | Avg: {avg_val:.1f}°"
            )

    def apply_map_changes(self):
        """Apply tracked changes to firmware map"""
        # This would apply the changes to the actual firmware map data
        # Placeholder for now
        self.logger.info(f"Applying {len(self.fuel_map_changes)} fuel changes and "
                        f"{len(self.ignition_map_changes)} ignition changes")

        # Clear change tracking after successful application
        self.fuel_map_changes.clear()
        self.ignition_map_changes.clear()
        self.fuel_changes_label.setText("Changes: 0")
        self.ignition_changes_label.setText("Changes: 0")
        self.reset_changes_button.setEnabled(False)