"""
Logging configuration for the ECU Tuner application
Provides comprehensive logging with different levels and file handling
"""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime
import colorlog
from typing import Optional


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    Setup logging configuration for the application

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, creates default log file
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Create default log file name if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"ecu_tuner_{timestamp}.log"
    else:
        log_file = Path(log_file)

    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatter for file logs
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )

    # Create colored formatter for console output
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s - %(message)s',
        datefmt='%H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    # Setup file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Log the setup
    logging.info(f"Logging initialized - Level: {log_level}, File: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class ECUOperationLogger:
    """Specialized logger for ECU operations with detailed tracking"""

    def __init__(self, operation: str):
        self.operation = operation
        self.logger = logging.getLogger(f"ecu_operations.{operation}")
        self.start_time = None

    def start(self, details: str = ""):
        """Log operation start"""
        self.start_time = datetime.now()
        self.logger.info(f"Starting {self.operation} - {details}")

    def progress(self, message: str, data: dict = None):
        """Log operation progress"""
        self.logger.debug(f"{self.operation} progress: {message}")
        if data:
            self.logger.debug(f"Operation data: {data}")

    def success(self, details: str = ""):
        """Log successful operation completion"""
        duration = datetime.now() - self.start_time if self.start_time else None
        duration_str = f" (Duration: {duration})" if duration else ""
        self.logger.info(f"{self.operation} completed successfully{duration_str} - {details}")

    def error(self, error_msg: str, exception: Exception = None):
        """Log operation error"""
        self.logger.error(f"{self.operation} failed: {error_msg}")
        if exception:
            self.logger.exception(f"Exception details: {exception}")

    def warning(self, warning_msg: str):
        """Log operation warning"""
        self.logger.warning(f"{self.operation} warning: {warning_msg}")


def log_ecu_communication(port: str, direction: str, data: bytes, success: bool = True):
    """
    Log raw ECU communication data

    Args:
        port: Serial port name
        direction: "TX" (transmit) or "RX" (receive)
        data: Raw bytes sent/received
        success: Whether communication was successful
    """
    comm_logger = logging.getLogger("ecu_communication")

    # Create hex representation of data
    hex_data = ' '.join(f'{b:02X}' for b in data)

    if success:
        comm_logger.debug(f"{port} {direction}: {hex_data}")
    else:
        comm_logger.error(f"{port} {direction} FAILED: {hex_data}")


def log_firmware_operation(operation: str, file_path: str, size: int, checksum: int):
    """
    Log firmware read/write operations

    Args:
        operation: "read" or "write"
        file_path: File path used
        size: Size of firmware in bytes
        checksum: Firmware checksum
    """
    firmware_logger = logging.getLogger("firmware_operations")
    firmware_logger.info(
        f"Firmware {operation}: {file_path} "
        f"(Size: {size:,} bytes, Checksum: 0x{checksum:08X})"
    )


def log_map_editing(map_type: str, coordinates: str, old_value: float, new_value: float):
    """
    Log map editing operations for audit trail

    Args:
        map_type: Type of map being edited
        coordinates: Location of change (e.g., "RPM=3000,TPS=50%")
        old_value: Previous value
        new_value: New value
    """
    editing_logger = logging.getLogger("map_editing")
    editing_logger.info(
        f"Map edit - {map_type} at {coordinates}: "
        f"{old_value} -> {new_value}"
    )


# Pre-configured loggers for different components
def get_ecu_logger() -> logging.Logger:
    """Get logger for ECU communication module"""
    return logging.getLogger("ecu")


def get_gui_logger() -> logging.Logger:
    """Get logger for GUI components"""
    return logging.getLogger("gui")


def get_maps_logger() -> logging.Logger:
    """Get logger for map operations"""
    return logging.getLogger("maps")


def get_protocol_logger() -> logging.Logger:
    """Get logger for protocol implementations"""
    return logging.getLogger("protocols")