import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QProgressBar, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QFileDialog, QMessageBox, QLabel)
from PySide6.QtCore import Qt, QThread, Signal

class ScanThread(QThread):
    # Define signals properly for PySide6
    progress = Signal(int)
    finished = Signal(list)

    def __init__(self, protocol):
        super().__init__()
        self.protocol = protocol

    def run(self):
        results = self.protocol.scan_local_ids(self.update_progress)
        self.finished.emit(results)

    def update_progress(self, val):
        self.progress.emit(val)

class ScannerDialog(QDialog):
    def __init__(self, protocol, parent=None):
        super().__init__(parent)
        self.protocol = protocol
        self.results = []
        
        self.setWindowTitle("Live Data ID Scanner")
        self.resize(500, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Info Label
        layout.addWidget(QLabel("Scans for supported KWP2000 Local IDs (0x21 Service)."))
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 255)
        layout.addWidget(self.progress_bar)
        
        # Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["PID (Hex)", "Raw Response", "Possible Type"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.clicked.connect(self.start_scan)
        btn_layout.addWidget(self.scan_btn)
        
        self.export_btn = QPushButton("Export JSON")
        self.export_btn.clicked.connect(self.export_json)
        self.export_btn.setEnabled(False)
        btn_layout.addWidget(self.export_btn)
        
        layout.addLayout(btn_layout)

    def start_scan(self):
        self.scan_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.table.setRowCount(0)
        self.results = []
        
        self.thread = ScanThread(self.protocol)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.finished.connect(self.scan_finished)
        self.thread.start()

    def scan_finished(self, results):
        self.results = results
        self.scan_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.progress_bar.setValue(255)
        
        self.table.setRowCount(len(results))
        for i, item in enumerate(results):
            self.table.setItem(i, 0, QTableWidgetItem(item['id']))
            self.table.setItem(i, 1, QTableWidgetItem(item['raw']))
            
            # Heuristic Detection
            raw_bytes = bytes.fromhex(item['raw'])
            guess = self.detect_parameter_type(raw_bytes)
            self.table.setItem(i, 2, QTableWidgetItem(guess))
            
        QMessageBox.information(self, "Scan Complete", f"Found {len(results)} supported IDs.")

    def detect_parameter_type(self, data):
        """
        Simple heuristic to guess parameter type based on value.
        """
        if len(data) == 1:
            val = data[0]
            # Temp is often offset by 40 (0 = -40C)
            temp_c = val - 40
            if 10 <= temp_c <= 110:
                return f"Temp? ({temp_c}C)"
            # Voltage (byte * 0.07 approx)
            volts = val * 0.07
            if 11.0 <= volts <= 15.0:
                return f"Voltage? ({volts:.1f}V)"
                
        elif len(data) == 2:
            val = int.from_bytes(data, 'big')
            # RPM is often raw / 4 or raw
            rpm = val // 4
            if 600 <= rpm <= 16000:
                return f"RPM? ({rpm})"
                
        return "Unknown"

    def export_json(self):
        if not self.results:
            return
            
        fname, _ = QFileDialog.getSaveFileName(self, "Export Results", "supported_ids.json", "JSON Files (*.json)")
        if fname:
            try:
                data = {"supported_local_ids": self.results}
                with open(fname, 'w') as f:
                    json.dump(data, f, indent=2)
                QMessageBox.information(self, "Success", f"Saved to {fname}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")