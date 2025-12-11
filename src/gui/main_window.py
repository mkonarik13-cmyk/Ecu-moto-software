from PySide6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                               QMessageBox, QToolBar)
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtCore import Qt
from .dashboard import DashboardWidget
from .map_editor import MapEditorWidget

class MainWindow(QMainWindow):
    def __init__(self, protocol, logger):
        super().__init__()
        self.protocol = protocol
        self.logger = logger
        
        self.setWindowTitle("Moto ECU Tuner (RomRaider Inspired)")
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
        
        # Start Logging Action
        start_log_action = QAction("Start Logging", self)
        start_log_action.triggered.connect(self.start_logging)
        toolbar.addAction(start_log_action)
        
        # Stop Logging Action
        stop_log_action = QAction("Stop Logging", self)
        stop_log_action.triggered.connect(self.stop_logging)
        toolbar.addAction(stop_log_action)

    def connect_ecu(self):
        try:
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