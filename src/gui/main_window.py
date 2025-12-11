"""
Main application window for ECU Tuner 28M4G
Central hub connecting all GUI modules with modern Material Design styling
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QMenuBar, QStatusBar, QToolBar, QSplitter, QFrame,
    QMessageBox, QProgressDialog, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, pyqtSignal
from PySide6.QtGui import QAction, QIcon, QPalette, QColor

# Import custom modules
from src.gui.dashboard import DashboardWidget
from src.gui.flash_tools import FlashToolsWidget
from src.gui.map_editor import MapEditorWidget
from src.gui.fan_settings import FanSettingsWidget
from src.gui.widgets.connection_dialog import ConnectionDialog
from src.ecu.connection import ECUConnection, ConnectionStatus
from src.maps.types import ECUInfo, ConnectionConfig
from src.utils.logger import get_gui_logger


class MainWindow(QMainWindow):
    """
    Main application window with Material Design styling
    Manages all GUI components and ECU connection state
    """

    # Signals for inter-component communication
    ecu_connected = pyqtSignal(object)  # ECUInfo
    ecu_disconnected = pyqtSignal()
    connection_status_changed = pyqtSignal(str)
    operation_progress = pyqtSignal(str, int)  # operation, percentage

    def __init__(self):
        super().__init__()
        self.logger = get_gui_logger()
        self.ecu_connection: Optional[ECUConnection] = None
        self.ecu_info: Optional[ECUInfo] = None

        # Setup UI
        self.setWindowTitle("ECU Tuner 28M4G - Italjet Dragster")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # Apply modern dark theme
        self.setup_theme()

        # Setup UI components
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        self.setup_toolbar()

        # Connect signals
        self.setup_connections()

        # Setup status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second

        self.logger.info("Main window initialized")

    def setup_theme(self):
        """Apply modern Material Design dark theme"""
        palette = QPalette()

        # Dark theme colors
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

        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #353535;
            }
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
            QStatusBar {
                background-color: #2d2d2d;
                color: white;
                border-top: 1px solid #555;
            }
            QToolBar {
                background-color: #404040;
                border: 1px solid #555;
                spacing: 3px;
            }
            QMenuBar {
                background-color: #404040;
                color: white;
                border-bottom: 1px solid #555;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
            }
            QMenuBar::item:selected {
                background-color: #0078d4;
            }
            QSplitter::handle {
                background-color: #555;
            }
            QSplitter::handle:horizontal {
                width: 2px;
            }
            QSplitter::handle:vertical {
                height: 2px;
            }
        """)

    def setup_ui(self):
        """Setup main UI layout"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Create splitter for resizable panels
        main_splitter = QSplitter(Qt.Horizontal)

        # Create tab widget for main modules
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(False)

        # Initialize tabs (will be created on demand)
        self.dashboard_tab = None
        self.flash_tools_tab = None
        self.map_editor_tab = None
        self.fan_settings_tab = None

        # Create initial dashboard tab
        self.create_dashboard_tab()

        # Add tab widget to splitter
        main_splitter.addWidget(self.tab_widget)

        # Set splitter proportions
        main_splitter.setSizes([1000])  # Give all space to tabs initially
        main_layout.addWidget(main_splitter)

    def setup_menu(self):
        """Setup application menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('&File')

        connect_action = QAction('&Connect ECU...', self)
        connect_action.setShortcut('Ctrl+C')
        connect_action.setStatusTip('Connect to ECU')
        connect_action.triggered.connect(self.show_connection_dialog)
        file_menu.addAction(connect_action)

        disconnect_action = QAction('&Disconnect ECU', self)
        disconnect_action.setShortcut('Ctrl+D')
        disconnect_action.setStatusTip('Disconnect from ECU')
        disconnect_action.triggered.connect(self.disconnect_ecu)
        file_menu.addAction(disconnect_action)

        file_menu.addSeparator()

        load_firmware_action = QAction('&Load Firmware...', self)
        load_firmware_action.setShortcut('Ctrl+L')
        load_firmware_action.setStatusTip('Load firmware file')
        load_firmware_action.triggered.connect(self.load_firmware_file)
        file_menu.addAction(load_firmware_action)

        save_firmware_action = QAction('&Save Firmware...', self)
        save_firmware_action.setShortcut('Ctrl+S')
        save_firmware_action.setStatusTip('Save firmware file')
        save_firmware_action.triggered.connect(self.save_firmware_file)
        file_menu.addAction(save_firmware_action)

        file_menu.addSeparator()

        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu('&Tools')

        read_firmware_action = QAction('&Read Firmware from ECU', self)
        read_firmware_action.setStatusTip('Read firmware from connected ECU')
        read_firmware_action.triggered.connect(self.read_firmware_from_ecu)
        tools_menu.addAction(read_firmware_action)

        tools_menu.addSeparator()

        diagnostics_action = QAction('&Run Diagnostics', self)
        diagnostics_action.setStatusTip('Run ECU diagnostic tests')
        diagnostics_action.triggered.connect(self.run_diagnostics)
        tools_menu.addAction(diagnostics_action)

        clear_dtcs_action = QAction('&Clear DTCs', self)
        clear_dtcs_action.setStatusTip('Clear diagnostic trouble codes')
        clear_dtcs_action.triggered.connect(self.clear_dtcs)
        tools_menu.addAction(clear_dtcs_action)

        # View menu
        view_menu = menubar.addMenu('&View')

        dashboard_action = QAction('&Dashboard', self)
        dashboard_action.setStatusTip('Show dashboard')
        dashboard_action.setCheckable(True)
        dashboard_action.setChecked(True)
        dashboard_action.triggered.connect(lambda: self.show_tab('dashboard'))
        view_menu.addAction(dashboard_action)

        flash_tools_action = QAction('&Flash Tools', self)
        flash_tools_action.setStatusTip('Show flash tools')
        flash_tools_action.setCheckable(True)
        flash_tools_action.triggered.connect(lambda: self.show_tab('flash_tools'))
        view_menu.addAction(flash_tools_action)

        map_editor_action = QAction('&Map Editor', self)
        map_editor_action.setStatusTip('Show map editor')
        map_editor_action.setCheckable(True)
        map_editor_action.triggered.connect(lambda: self.show_tab('map_editor'))
        view_menu.addAction(map_editor_action)

        fan_settings_action = QAction('Fan &Settings', self)
        fan_settings_action.setStatusTip('Show fan settings')
        fan_settings_action.setCheckable(True)
        fan_settings_action.triggered.connect(lambda: self.show_tab('fan_settings'))
        view_menu.addAction(fan_settings_action)

        # Help menu
        help_menu = menubar.addMenu('&Help')

        about_action = QAction('&About', self)
        about_action.setStatusTip('Show about dialog')
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def setup_status_bar(self):
        """Setup status bar with connection status and info"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Connection status label
        self.connection_status_label = "Disconnected"
        self.status_bar.showMessage("Ready - Not connected to ECU")

    def setup_toolbar(self):
        """Setup main toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Connect button
        connect_action = QAction('Connect', self)
        connect_action.setStatusTip('Connect to ECU')
        connect_action.triggered.connect(self.show_connection_dialog)
        toolbar.addAction(connect_action)

        # Disconnect button
        disconnect_action = QAction('Disconnect', self)
        disconnect_action.setStatusTip('Disconnect from ECU')
        disconnect_action.triggered.connect(self.disconnect_ecu)
        toolbar.addAction(disconnect_action)

        toolbar.addSeparator()

        # Read firmware button
        read_firmware_action = QAction('Read Firmware', self)
        read_firmware_action.setStatusTip('Read firmware from ECU')
        read_firmware_action.triggered.connect(self.read_firmware_from_ecu)
        toolbar.addAction(read_firmware_action)

    def setup_connections(self):
        """Setup signal connections"""
        self.ecu_connected.connect(self.on_ecu_connected)
        self.ecu_disconnected.connect(self.on_ecu_disconnected)
        self.connection_status_changed.connect(self.on_connection_status_changed)
        self.operation_progress.connect(self.on_operation_progress)

    def create_dashboard_tab(self):
        """Create and add dashboard tab"""
        if self.dashboard_tab is None:
            self.dashboard_tab = DashboardWidget()
            self.tab_widget.addTab(self.dashboard_tab, "Dashboard")

    def create_flash_tools_tab(self):
        """Create and add flash tools tab"""
        if self.flash_tools_tab is None:
            self.flash_tools_tab = FlashToolsWidget()
            self.tab_widget.addTab(self.flash_tools_tab, "Flash Tools")

    def create_map_editor_tab(self):
        """Create and add map editor tab"""
        if self.map_editor_tab is None:
            self.map_editor_tab = MapEditorWidget()
            self.tab_widget.addTab(self.map_editor_tab, "Map Editor")

    def create_fan_settings_tab(self):
        """Create and add fan settings tab"""
        if self.fan_settings_tab is None:
            self.fan_settings_tab = FanSettingsWidget()
            self.tab_widget.addTab(self.fan_settings_tab, "Fan Settings")

    def show_tab(self, tab_name: str):
        """Show specific tab"""
        if tab_name == 'dashboard':
            self.create_dashboard_tab()
            self.tab_widget.setCurrentWidget(self.dashboard_tab)
        elif tab_name == 'flash_tools':
            self.create_flash_tools_tab()
            self.tab_widget.setCurrentWidget(self.flash_tools_tab)
        elif tab_name == 'map_editor':
            self.create_map_editor_tab()
            self.tab_widget.setCurrentWidget(self.map_editor_tab)
        elif tab_name == 'fan_settings':
            self.create_fan_settings_tab()
            self.tab_widget.setCurrentWidget(self.fan_settings_tab)

    def show_connection_dialog(self):
        """Show ECU connection dialog"""
        dialog = ConnectionDialog(self)
        if dialog.exec_() == ConnectionDialog.Accepted:
            config = dialog.get_connection_config()
            if config:
                self.connect_to_ecu(config)

    def connect_to_ecu(self, config: ConnectionConfig):
        """Connect to ECU with given configuration"""
        try:
            self.status_bar.showMessage("Connecting to ECU...")
            QApplication.processEvents()  # Update UI

            # Create ECU connection
            self.ecu_connection = ECUConnection(config)

            # Connect in a thread to avoid UI freezing
            connection_thread = QThread()
            worker = ECUConnectionWorker(self.ecu_connection)
            worker.moveToThread(connection_thread)

            worker.connection_established.connect(self.on_connection_established)
            worker.connection_failed.connect(self.on_connection_failed)

            connection_thread.started.connect(worker.connect)
            worker.finished.connect(connection_thread.quit)
            worker.finished.connect(worker.deleteLater)
            connection_thread.finished.connect(connection_thread.deleteLater)

            connection_thread.start()

        except Exception as e:
            self.logger.error(f"Connection setup failed: {e}")
            self.show_error_message("Connection Error", f"Failed to setup connection: {e}")

    def disconnect_ecu(self):
        """Disconnect from ECU"""
        if self.ecu_connection:
            try:
                self.ecu_connection.disconnect()
                self.on_ecu_disconnected()
            except Exception as e:
                self.logger.error(f"Disconnect failed: {e}")

    def on_connection_established(self, ecu_info: ECUInfo):
        """Handle successful ECU connection"""
        self.ecu_info = ecu_info
        self.ecu_connected.emit(ecu_info)
        self.status_bar.showMessage(f"Connected to ECU - VIN: {ecu_info.vin}")

    def on_connection_failed(self, error_message: str):
        """Handle failed ECU connection"""
        self.status_bar.showMessage("Connection failed")
        self.show_error_message("Connection Failed", error_message)

    def on_ecu_connected(self, ecu_info: ECUInfo):
        """Handle ECU connected signal"""
        self.connection_status_label = f"Connected - {ecu_info.engine_type.value}"

        # Update all tabs with ECU info
        if self.dashboard_tab:
            self.dashboard_tab.set_ecu_info(ecu_info)
        if self.flash_tools_tab:
            self.flash_tools_tab.set_ecu_connection(self.ecu_connection)
        if self.map_editor_tab:
            self.map_editor_tab.set_ecu_connection(self.ecu_connection)
        if self.fan_settings_tab:
            self.fan_settings_tab.set_ecu_connection(self.ecu_connection)

    def on_ecu_disconnected(self):
        """Handle ECU disconnected signal"""
        self.connection_status_label = "Disconnected"
        self.ecu_info = None
        self.ecu_connection = None
        self.status_bar.showMessage("Disconnected from ECU")

        # Update all tabs
        if self.dashboard_tab:
            self.dashboard_tab.set_ecu_info(None)
        if self.flash_tools_tab:
            self.flash_tools_tab.set_ecu_connection(None)
        if self.map_editor_tab:
            self.map_editor_tab.set_ecu_connection(None)
        if self.fan_settings_tab:
            self.fan_settings_tab.set_ecu_connection(None)

    def on_connection_status_changed(self, status: str):
        """Handle connection status change"""
        self.status_bar.showMessage(f"Connection status: {status}")

    def on_operation_progress(self, operation: str, percentage: int):
        """Handle operation progress updates"""
        self.status_bar.showMessage(f"{operation}: {percentage}%")

    def update_status(self):
        """Periodic status update"""
        if self.ecu_connection and self.ecu_connection.is_connected():
            # Update connection quality
            quality = self.ecu_connection.test_connection_quality()
            if quality['quality'] < 50:
                self.status_bar.showMessage("Warning: Poor connection quality")

    def load_firmware_file(self):
        """Load firmware file"""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Firmware File",
            "",
            "Firmware Files (*.bin *.hex);;All Files (*.*)"
        )

        if file_path:
            # Load firmware and update map editor
            if self.map_editor_tab:
                self.map_editor_tab.load_firmware_file(file_path)

    def save_firmware_file(self):
        """Save firmware file"""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Firmware File",
            "",
            "Firmware Files (*.bin);;All Files (*.*)"
        )

        if file_path:
            # Save firmware from map editor
            if self.map_editor_tab:
                self.map_editor_tab.save_firmware_file(file_path)

    def read_firmware_from_ecu(self):
        """Read firmware from connected ECU"""
        if not self.ecu_connection or not self.ecu_connection.is_connected():
            self.show_error_message("Not Connected", "Please connect to ECU first")
            return

        # Show flash tools tab
        self.create_flash_tools_tab()
        self.tab_widget.setCurrentWidget(self.flash_tools_tab)

        # Start firmware read
        if self.flash_tools_tab:
            self.flash_tools_tab.read_firmware()

    def run_diagnostics(self):
        """Run ECU diagnostics"""
        if not self.ecu_connection or not self.ecu_connection.is_connected():
            self.show_error_message("Not Connected", "Please connect to ECU first")
            return

        # Implement diagnostic routine
        self.show_info_message("Diagnostics", "Diagnostic routine not yet implemented")

    def clear_dtcs(self):
        """Clear diagnostic trouble codes"""
        if not self.ecu_connection or not self.ecu_connection.is_connected():
            self.show_error_message("Not Connected", "Please connect to ECU first")
            return

        reply = QMessageBox.question(
            self, 'Clear DTCs',
            'Are you sure you want to clear all diagnostic trouble codes?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Clear DTCs using protocol
                if self.ecu_connection.protocol:
                    success = self.ecu_connection.protocol.clear_dtcs()
                    if success:
                        self.show_info_message("Success", "DTCs cleared successfully")
                    else:
                        self.show_error_message("Failed", "Failed to clear DTCs")
            except Exception as e:
                self.show_error_message("Error", f"Failed to clear DTCs: {e}")

    def show_about_dialog(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About ECU Tuner 28M4G",
            """<b>ECU Tuner 28M4G v1.0.0</b><br><br>
            Professional ECU tuning software for<br>
            Magneti Marelli 28M4G ECU<br>
            Used in Italjet Dragster motorcycles<br><br>
            <b>Features:</b><br>
            • K-Line and UDS protocol support<br>
            • Firmware read/write capabilities<br>
            • Interactive map editing<br>
            • Diagnostic tools<br>
            • Fan configuration<br><br>
            © 2024 ECU Tuner Software"""
        )

    def show_error_message(self, title: str, message: str):
        """Show error message dialog"""
        QMessageBox.critical(self, title, message)

    def show_info_message(self, title: str, message: str):
        """Show info message dialog"""
        QMessageBox.information(self, title, message)

    def closeEvent(self, event):
        """Handle application close event"""
        # Disconnect from ECU if connected
        if self.ecu_connection and self.ecu_connection.is_connected():
            try:
                self.ecu_connection.disconnect()
            except:
                pass

        # Save application settings if needed
        event.accept()


class ECUConnectionWorker(QThread):
    """Worker thread for ECU connection to avoid UI freezing"""

    connection_established = pyqtSignal(object)  # ECUInfo
    connection_failed = pyqtSignal(str)  # error message
    finished = pyqtSignal()

    def __init__(self, ecu_connection: ECUConnection):
        super().__init__()
        self.ecu_connection = ecu_connection

    def connect(self):
        """Connect to ECU"""
        try:
            success = self.ecu_connection.connect()
            if success:
                ecu_info = self.ecu_connection.get_ecu_info()
                if ecu_info:
                    self.connection_established.emit(ecu_info)
                else:
                    self.connection_failed.emit("Failed to get ECU information")
            else:
                self.connection_failed.emit("Failed to establish connection")
        except Exception as e:
            self.connection_failed.emit(f"Connection error: {e}")
        finally:
            self.finished.emit()