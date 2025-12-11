from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QLabel, QGroupBox, QHBoxLayout)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from ..map_tracer import MapTracer

class MapEditorWidget(QWidget):
    def __init__(self, protocol, logger):
        super().__init__()
        self.protocol = protocol
        self.logger = logger
        self.current_table = None
        
        self.setup_ui()
        
        # Update timer for map tracing
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_trace)
        self.timer.start(100)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Map Selection (Simplified: just load the first one for now)
        self.map_label = QLabel("Fuel Map 1")
        layout.addWidget(self.map_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers) # Read-only for now
        layout.addWidget(self.table)
        
        # Load initial map
        self.load_map("Fuel Map 1")

    def load_map(self, map_name):
        self.current_table = self.protocol.get_table(map_name)
        if not self.current_table:
            return
            
        # Setup dimensions
        rows = len(self.current_table.y_breakpoints)
        cols = len(self.current_table.x_breakpoints)
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        
        # Headers
        self.table.setHorizontalHeaderLabels([str(x) for x in self.current_table.x_breakpoints])
        self.table.setVerticalHeaderLabels([str(y) for y in self.current_table.y_breakpoints])
        
        # Fill data
        for r in range(rows):
            for c in range(cols):
                val = self.current_table.data[r][c]
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)

    def update_trace(self):
        if not self.current_table:
            return
            
        data = self.logger.get_latest_data()
        if not data:
            return
            
        # Get current operating point
        x_val = data.get(self.current_table.x_axis_param, 0)
        y_val = data.get(self.current_table.y_axis_param, 0)
        
        # Find active cell
        row, col = MapTracer.get_active_cell(self.current_table, x_val, y_val)
        
        # Highlight active cell
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if r == row and c == col:
                    item.setBackground(QColor(0, 120, 215)) # Blue highlight
                    item.setForeground(Qt.white)
                else:
                    item.setBackground(Qt.transparent) # Reset
                    item.setForeground(Qt.white) # Keep text visible in dark mode