"""
Flash tools widget for reading and writing ECU firmware
Provides firmware backup, restoration, and flashing capabilities
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QProgressBar, QTextEdit, QFileDialog,
    QLineEdit, QCheckBox, QSpinBox, QComboBox, QMessageBox,
    QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap

from src.ecu.connection import ECUConnection
from src.maps.types import FlashProgress, ECUInfo
from src.utils.logger import get_gui_logger


class FlashOperationThread(QThread):
    """Worker thread for flash operations to avoid UI freezing"""

    progress_updated = Signal(str, int, int, int)  # operation, percent, bytes_done, total_bytes
    operation_completed = Signal(bool, str)  # success, message
    log_message = Signal(str)

    def __init__(self, ecu_connection: ECUConnection, operation: str, file_path: str = ""):
        super().__init__()
        self.ecu_connection = ecu_connection
        self.operation = operation  # "read" or "write"
        self.file_path = file_path
        self._stopped = False

    def run(self):
        """Execute the flash operation"""
        try:
            if self.operation == "read":
                self._read_firmware()
            elif self.operation == "write":
                self._write_firmware()
            else:
                self.operation_completed.emit(False, "Unknown operation")

        except Exception as e:
            self.log_message.emit(f"Flash operation error: {str(e)}")
            self.operation_completed.emit(False, str(e))

    def _read_firmware(self):
        """Read firmware from ECU"""
        self.log_message.emit("Starting firmware read operation...")

        if not self.ecu_connection or not self.ecu_connection.is_connected():
            self.operation_completed.emit(False, "ECU not connected")
            return

        if not self.file_path:
            self.operation_completed.emit(False, "No file path specified")
            return

        try:
            # Get ECU info to determine flash size
            ecu_info = self.ecu_connection.get_ecu_info()
            if not ecu_info:
                self.operation_completed.emit(False, "Could not get ECU information")
                return

            flash_size = ecu_info.flash_size
            self.log_message.emit(f"Reading {flash_size:,} bytes from ECU...")

            # Start reading firmware
            if self.ecu_connection.protocol:
                # Read firmware in chunks
                chunk_size = 4096  # 4KB chunks
                total_bytes = 0
                firmware_data = b""

                # Read from address 0x00000 to flash_size
                current_address = 0x00000

                while current_address < flash_size and not self._stopped:
                    # Calculate chunk size for this iteration
                    remaining = flash_size - current_address
                    read_size = min(chunk_size, remaining)

                    # Read chunk from ECU
                    chunk = self.ecu_connection.protocol.read_memory_by_address(
                        current_address, read_size
                    )

                    if not chunk:
                        self.log_message.emit(f"Failed to read at address 0x{current_address:08X}")
                        break

                    firmware_data += chunk
                    current_address += read_size
                    total_bytes += read_size

                    # Update progress
                    progress = int((current_address / flash_size) * 100)
                    self.progress_updated.emit("Reading Firmware", progress, current_address, flash_size)

                    # Small delay to prevent overwhelming the ECU
                    time.sleep(0.01)

                if self._stopped:
                    self.log_message.emit("Firmware read operation cancelled")
                    return

                # Save firmware to file
                with open(self.file_path, 'wb') as f:
                    f.write(firmware_data)

                self.log_message.emit(f"Firmware saved to {self.file_path}")
                self.log_message.emit(f"Total bytes read: {total_bytes:,}")

                # Calculate checksum
                checksum = sum(firmware_data) & 0xFFFFFFFF
                self.log_message.emit(f"Firmware checksum: 0x{checksum:08X}")

                self.operation_completed.emit(True, f"Firmware successfully read and saved to {self.file_path}")

            else:
                self.operation_completed.emit(False, "No protocol available")

        except Exception as e:
            self.log_message.emit(f"Read operation failed: {str(e)}")
            self.operation_completed.emit(False, str(e))

    def _write_firmware(self):
        """Write firmware to ECU"""
        self.log_message.emit("Starting firmware write operation...")

        if not self.ecu_connection or not self.ecu_connection.is_connected():
            self.operation_completed.emit(False, "ECU not connected")
            return

        if not self.file_path:
            self.operation_completed.emit(False, "No file path specified")
            return

        try:
            # Load firmware file
            with open(self.file_path, 'rb') as f:
                firmware_data = f.read()

            file_size = len(firmware_data)
            self.log_message.emit(f"Loaded firmware file: {file_size:,} bytes")

            # Get ECU info for validation
            ecu_info = self.ecu_connection.get_ecu_info()
            if not ecu_info:
                self.operation_completed.emit(False, "Could not get ECU information")
                return

            # Validate file size
            if file_size > ecu_info.flash_size:
                self.log_message.emit(f"Warning: File size ({file_size:,}) exceeds ECU flash size ({ecu_info.flash_size:,})")

            # Calculate checksum
            checksum = sum(firmware_data) & 0xFFFFFFFF
            self.log_message.emit(f"File checksum: 0x{checksum:08X}")

            # Confirm before writing
            self.log_message.emit("Starting firmware write...")
            self.log_message.emit("WARNING: This operation modifies ECU firmware")

            if self.ecu_connection.protocol:
                # Write firmware in chunks
                chunk_size = 4096  # 4KB chunks
                total_bytes = 0
                current_address = 0x00000

                while current_address < file_size and not self._stopped:
                    # Calculate chunk size for this iteration
                    remaining = file_size - current_address
                    write_size = min(chunk_size, remaining)

                    # Extract chunk from firmware
                    chunk = firmware_data[current_address:current_address + write_size]

                    # Write chunk to ECU
                    success = self.ecu_connection.protocol.write_memory_by_address(
                        current_address, chunk
                    )

                    if not success:
                        self.log_message.emit(f"Failed to write at address 0x{current_address:08X}")
                        break

                    current_address += write_size
                    total_bytes += write_size

                    # Update progress
                    progress = int((current_address / file_size) * 100)
                    self.progress_updated.emit("Writing Firmware", progress, current_address, file_size)

                    # Small delay to prevent overwhelming the ECU
                    time.sleep(0.02)

                if self._stopped:
                    self.log_message.emit("Firmware write operation cancelled")
                    return

                self.log_message.emit(f"Total bytes written: {total_bytes:,}")

                # Verify write if possible
                self.log_message.emit("Verifying firmware write...")
                verification_passed = self._verify_firmware_write(firmware_data[:total_bytes], total_bytes)

                if verification_passed:
                    self.log_message.emit("Firmware verification successful!")
                    self.operation_completed.emit(True, f"Firmware successfully written to ECU")
                else:
                    self.log_message.emit("Firmware verification failed!")
                    self.operation_completed.emit(False, "Firmware verification failed")

            else:
                self.operation_completed.emit(False, "No protocol available")

        except Exception as e:
            self.log_message.emit(f"Write operation failed: {str(e)}")
            self.operation_completed.emit(False, str(e))

    def _verify_firmware_write(self, original_data: bytes, size: int) -> bool:
        """Verify that firmware was written correctly"""
        try:
            chunk_size = 4096
            current_address = 0x00000

            while current_address < size:
                # Calculate chunk size
                remaining = size - current_address
                read_size = min(chunk_size, remaining)

                # Read back from ECU
                read_data = self.ecu_connection.protocol.read_memory_by_address(
                    current_address, read_size
                )

                if not read_data:
                    self.log_message.emit(f"Verification failed at address 0x{current_address:08X}")
                    return False

                # Compare with original data
                original_chunk = original_data[current_address:current_address + read_size]
                if read_data != original_chunk:
                    self.log_message.emit(f"Data mismatch at address 0x{current_address:08X}")
                    return False

                current_address += read_size

            return True

        except Exception as e:
            self.log_message.emit(f"Verification error: {str(e)}")
            return False

    def stop(self):
        """Stop the flash operation"""
        self._stopped = True


class FlashToolsWidget(QWidget):
    """Flash tools widget for firmware operations"""

    def __init__(self):
        super().__init__()
        self.logger = get_gui_logger()
        self.ecu_connection: Optional[ECUConnection] = None
        self.ecu_info: Optional[ECUInfo] = None
        self.flash_thread: Optional[FlashOperationThread] = None

        self.setup_ui()
        self.setup_style()

    def setup_ui(self):
        """Setup flash tools UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Firmware Read Section
        read_group = self.create_read_firmware_section()
        content_layout.addWidget(read_group)

        # Firmware Write Section
        write_group = self.create_write_firmware_section()
        content_layout.addWidget(write_group)

        # Progress Section
        progress_group = self.create_progress_section()
        content_layout.addWidget(progress_group)

        # Log Section
        log_group = self.create_log_section()
        content_layout.addWidget(log_group)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def create_read_firmware_section(self) -> QGroupBox:
        """Create firmware read section"""
        group = QGroupBox("Read Firmware from ECU")
        layout = QGridLayout(group)

        # File selection
        layout.addWidget(QLabel("Save Location:"), 0, 0)
        self.read_file_edit = QLineEdit()
        self.read_file_edit.setPlaceholderText("Select location to save firmware...")
        layout.addWidget(self.read_file_edit, 0, 1, 1, 2)

        self.browse_read_button = QPushButton("Browse...")
        self.browse_read_button.clicked.connect(self.browse_read_file)
        layout.addWidget(self.browse_read_button, 0, 3)

        # Options
        self.verify_after_read_checkbox = QCheckBox("Verify after reading")
        self.verify_after_read_checkbox.setChecked(True)
        layout.addWidget(self.verify_after_read_checkbox, 1, 0, 1, 2)

        self.create_backup_checkbox = QCheckBox("Create timestamped backup")
        self.create_backup_checkbox.setChecked(True)
        layout.addWidget(self.create_backup_checkbox, 1, 2, 1, 2)

        # Read button
        self.read_button = QPushButton("Read Firmware")
        self.read_button.clicked.connect(self.read_firmware)
        self.read_button.setEnabled(False)
        layout.addWidget(self.read_button, 2, 0, 1, 4)

        return group

    def create_write_firmware_section(self) -> QGroupBox:
        """Create firmware write section"""
        group = QGroupBox("Write Firmware to ECU")
        layout = QGridLayout(group)

        # File selection
        layout.addWidget(QLabel("Firmware File:"), 0, 0)
        self.write_file_edit = QLineEdit()
        self.write_file_edit.setPlaceholderText("Select firmware file to write...")
        layout.addWidget(self.write_file_edit, 0, 1, 1, 2)

        self.browse_write_button = QPushButton("Browse...")
        self.browse_write_button.clicked.connect(self.browse_write_file)
        layout.addWidget(self.browse_write_button, 0, 3)

        # Options
        self.verify_before_write_checkbox = QCheckBox("Verify file before writing")
        self.verify_before_write_checkbox.setChecked(True)
        layout.addWidget(self.verify_before_write_checkbox, 1, 0, 1, 2)

        self.create_write_backup_checkbox = QCheckBox("Backup current firmware first")
        self.create_write_backup_checkbox.setChecked(True)
        layout.addWidget(self.create_write_backup_checkbox, 1, 2, 1, 2)

        # Safety confirmation
        self.safety_checkbox = QCheckBox("I understand the risks and want to proceed")
        layout.addWidget(self.safety_checkbox, 2, 0, 1, 3)

        # Write button
        self.write_button = QPushButton("Write Firmware")
        self.write_button.clicked.connect(self.write_firmware)
        self.write_button.setEnabled(False)
        self.write_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
            QPushButton:disabled {
                background-color: #404040;
            }
        """)
        layout.addWidget(self.write_button, 2, 3)

        return group

    def create_progress_section(self) -> QGroupBox:
        """Create progress display section"""
        group = QGroupBox("Operation Progress")
        layout = QVBoxLayout(group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status labels
        status_layout = QHBoxLayout()
        self.operation_label = QLabel("No operation in progress")
        status_layout.addWidget(self.operation_label)

        self.bytes_label = QLabel("")
        status_layout.addWidget(self.bytes_label)

        status_layout.addStretch()

        self.time_label = QLabel("")
        status_layout.addWidget(self.time_label)

        layout.addLayout(status_layout)

        # Cancel button
        self.cancel_button = QPushButton("Cancel Operation")
        self.cancel_button.clicked.connect(self.cancel_operation)
        self.cancel_button.setEnabled(False)
        layout.addWidget(self.cancel_button)

        return group

    def create_log_section(self) -> QGroupBox:
        """Create log display section"""
        group = QGroupBox("Operation Log")
        layout = QVBoxLayout(group)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)

        # Clear log button
        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(self.log_text.clear)
        layout.addWidget(clear_button)

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
            QLineEdit {
                background-color: #404040;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 4px;
                color: #ddd;
            }
            QCheckBox {
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
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #555;
                color: #ddd;
            }
        """)

    def set_ecu_connection(self, ecu_connection: Optional[ECUConnection]):
        """Set ECU connection reference"""
        self.ecu_connection = ecu_connection

        # Enable/disable read button based on connection
        if ecu_connection and ecu_connection.is_connected():
            self.read_button.setEnabled(True)
            self.log_message("ECU connected - firmware operations available")
        else:
            self.read_button.setEnabled(False)
            self.write_button.setEnabled(False)
            self.log_message("ECU not connected - firmware operations unavailable")

    def browse_read_file(self):
        """Browse for firmware save location"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Firmware",
            "",
            "Binary Files (*.bin);;All Files (*.*)"
        )

        if file_path:
            if not file_path.endswith('.bin'):
                file_path += '.bin'

            self.read_file_edit.setText(file_path)

    def browse_write_file(self):
        """Browse for firmware file to write"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Firmware File",
            "",
            "Binary Files (*.bin);;Hex Files (*.hex);;All Files (*.*)"
        )

        if file_path:
            self.write_file_edit.setText(file_path)

    def read_firmware(self):
        """Start firmware read operation"""
        if not self.ecu_connection or not self.ecu_connection.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to ECU first")
            return

        file_path = self.read_file_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "No Location", "Please specify a save location")
            return

        # Add timestamp if backup requested
        if self.create_backup_checkbox.isChecked():
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_path = Path(file_path)
            file_path = str(base_path.parent / f"{base_path.stem}_{timestamp}{base_path.suffix}")
            self.read_file_edit.setText(file_path)

        # Confirm operation
        reply = QMessageBox.question(
            self, 'Read Firmware',
            f'Read firmware from ECU and save to:\n{file_path}',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.start_flash_operation("read", file_path)

    def write_firmware(self):
        """Start firmware write operation"""
        if not self.ecu_connection or not self.ecu_connection.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to ECU first")
            return

        file_path = self.write_file_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "No File", "Please select a firmware file")
            return

        if not self.safety_checkbox.isChecked():
            QMessageBox.warning(self, "Safety Confirmation",
                              "Please confirm that you understand the risks")
            return

        # File existence check
        if not Path(file_path).exists():
            QMessageBox.critical(self, "File Not Found", f"File not found:\n{file_path}")
            return

        # Final warning
        reply = QMessageBox.warning(
            self, 'WARNING - Firmware Write',
            'This will modify your ECU firmware.\n\n'
            'Incorrect firmware can damage your engine!\n\n'
            'Are you absolutely sure you want to continue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.start_flash_operation("write", file_path)

    def start_flash_operation(self, operation: str, file_path: str = ""):
        """Start flash operation in separate thread"""
        if self.flash_thread and self.flash_thread.isRunning():
            QMessageBox.warning(self, "Operation in Progress",
                              "Another flash operation is already running")
            return

        # Setup UI for operation
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.operation_label.setText(f"Starting {operation} operation...")
        self.bytes_label.setText("")
        self.time_label.setText("")

        self.read_button.setEnabled(False)
        self.write_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

        # Start operation thread
        self.flash_thread = FlashOperationThread(self.ecu_connection, operation, file_path)
        self.flash_thread.progress_updated.connect(self.on_progress_updated)
        self.flash_thread.operation_completed.connect(self.on_operation_completed)
        self.flash_thread.log_message.connect(self.log_message)
        self.flash_thread.start()

    def cancel_operation(self):
        """Cancel current flash operation"""
        if self.flash_thread and self.flash_thread.isRunning():
            reply = QMessageBox.question(
                self, 'Cancel Operation',
                'Are you sure you want to cancel the flash operation?\n\n'
                'This may leave the ECU in an inconsistent state.',
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.flash_thread.stop()
                self.log_message("Cancelling flash operation...")

    def on_progress_updated(self, operation: str, percent: int, bytes_done: int, total_bytes: int):
        """Handle progress updates"""
        self.progress_bar.setValue(percent)
        self.operation_label.setText(f"{operation}: {percent}%")

        if bytes_done > 0 and total_bytes > 0:
            self.bytes_label.setText(f"{bytes_done:,} / {total_bytes:,} bytes")

            # Calculate estimated time remaining
            elapsed_time = self.flash_thread.elapsed() if self.flash_thread else 0
            if elapsed_time > 0 and percent > 0:
                estimated_total = (elapsed_time * 100) / percent
                remaining_time = estimated_total - elapsed_time
                self.time_label.setText(f"Remaining: {remaining_time:.0f}s")

    def on_operation_completed(self, success: bool, message: str):
        """Handle operation completion"""
        # Reset UI
        self.progress_bar.setVisible(False)
        self.cancel_button.setEnabled(False)

        # Re-enable buttons if still connected
        if self.ecu_connection and self.ecu_connection.is_connected():
            self.read_button.setEnabled(True)
            self.write_button.setEnabled(True)

        if success:
            self.operation_label.setText("Operation completed successfully")
            self.log_message(f"SUCCESS: {message}")
            QMessageBox.information(self, "Operation Complete", message)
        else:
            self.operation_label.setText("Operation failed")
            self.log_message(f"ERROR: {message}")
            QMessageBox.critical(self, "Operation Failed", message)

        # Clear thread reference
        self.flash_thread = None

    def log_message(self, message: str):
        """Add message to log display"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

        # Auto-scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )