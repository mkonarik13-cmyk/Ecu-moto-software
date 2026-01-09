"""
ECU communication module for Magneti Marelli 28M4G
Handles low-level communication with K-Line and UDS protocols
"""

import serial
import time
from typing import Optional, List, Dict, Any
from enum import Enum
import serial.tools.list_ports
from serial import SerialException

from src.maps.types import ECUInfo, ProtocolType, ConnectionConfig, ECU28M4GConstants
from src.utils.logger import get_ecu_logger, log_ecu_communication
from src.ecu.protocols.kwp2000 import KWP2000Protocol
from src.ecu.protocols.uds import UDSProtocol


class ConnectionStatus(Enum):
    """ECU connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    AUTO_DETECTING = "auto_detecting"


class ECUConnectionError(Exception):
    """Custom exception for ECU connection errors"""
    pass


class ECUConnection:
    """
    Main ECU communication handler with auto-detection capabilities
    Specifically designed for Magneti Marelli 28M4G ECU in Italjet Dragster
    """

    def __init__(self, config: Optional[ConnectionConfig] = None):
        self.config = config or ConnectionConfig("", 0, ProtocolType.KWP2000)
        self.serial_port: Optional[serial.Serial] = None
        self.protocol: Optional[Any] = None
        self.status = ConnectionStatus.DISCONNECTED
        self.logger = get_ecu_logger()
        self.ecu_info: Optional[ECUInfo] = None

    def get_available_ports(self) -> List[Dict[str, str]]:
        """
        Scan for available serial ports

        Returns:
            List of dictionaries with port information
        """
        ports = []
        for port in serial.tools.list_ports.comports():
            port_info = {
                'device': port.device,
                'name': port.name,
                'description': port.description,
                'manufacturer': port.manufacturer or 'Unknown',
                'vid': port.vid,
                'pid': port.pid
            }
            ports.append(port_info)
            self.logger.debug(f"Found port: {port_info}")

        return ports

    def connect(self, port: str = None, baudrate: int = None, auto_detect: bool = True) -> bool:
        """
        Connect to ECU with auto-detection

        Args:
            port: Serial port to use (if None, auto-detect)
            baudrate: Baud rate (if None, try standard rates)
            auto_detect: Whether to auto-detect protocol and settings

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.status = ConnectionStatus.CONNECTING
            self.logger.info(f"Attempting ECU connection - Port: {port}, Auto-detect: {auto_detect}")

            if auto_detect:
                return self._auto_connect(port, baudrate)
            else:
                return self._direct_connect(port or self.config.port, baudrate or self.config.baudrate)

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.status = ConnectionStatus.ERROR
            raise ECUConnectionError(f"Failed to connect to ECU: {e}")

    def _auto_connect(self, port: str = None, baudrate: int = None) -> bool:
        """
        Auto-detect and connect to ECU

        Returns:
            True if successful connection and detection
        """
        self.status = ConnectionStatus.AUTO_DETECTING
        available_ports = self.get_available_ports()

        # Filter ports if specific port provided
        if port:
            available_ports = [p for p in available_ports if p['device'] == port]

        if not available_ports:
            raise ECUConnectionError("No suitable serial ports found")

        # Try each port with different baud rates
        for port_info in available_ports:
            port_device = port_info['device']

            # Try standard 28M4G baud rates
            baud_rates = [baudrate] if baudrate else [
                ECU28M4GConstants.STANDARD_KLINE_BAUD,
                ECU28M4GConstants.ALTERNATIVE_KLINE_BAUD,
                38400, 57600, 115200  # Fallback rates
            ]

            for rate in baud_rates:
                try:
                    self.logger.debug(f"Trying {port_device} at {rate} baud")

                    if self._try_connection(port_device, rate):
                        self.logger.info(f"Successfully connected to ECU on {port_device} at {rate}")
                        self.config.port = port_device
                        self.config.baudrate = rate
                        return True

                except (serial.SerialException, ECUConnectionError) as e:
                    self.logger.debug(f"Failed to connect on {port_device} at {rate}: {e}")
                    self.disconnect()  # Clean up partial connection
                    continue

        raise ECUConnectionError("Could not establish connection with ECU")

    def _direct_connect(self, port: str, baudrate: int) -> bool:
        """
        Direct connection without auto-detection

        Args:
            port: Serial port device
            baudrate: Communication baud rate

        Returns:
            True if connection successful
        """
        return self._try_connection(port, baudrate)

    def _try_connection(self, port: str, baudrate: int) -> bool:
        """
        Attempt to establish connection with specific port and baud rate

        Args:
            port: Serial port device
            baudrate: Communication baud rate

        Returns:
            True if successful connection and ECU identification

        Raises:
            ECUConnectionError: If connection fails
        """
        # Open serial port
        self.serial_port = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )

        # Clear any pending data
        self.serial_port.reset_input_buffer()
        self.serial_port.reset_output_buffer()

        # Small delay for port to stabilize
        time.sleep(0.1)

        # Try to detect and initialize protocol
        protocol = self._detect_protocol()
        if not protocol:
            raise ECUConnectionError("Could not detect ECU protocol")

        self.protocol = protocol
        self.status = ConnectionStatus.CONNECTED

        # Get ECU information
        self.ecu_info = self.get_ecu_info()
        if not self.ecu_info:
            raise ECUConnectionError("Could not identify ECU")

        self.logger.info(f"Connected to ECU: {self.ecu_info}")
        return True

    def _detect_protocol(self) -> Optional[Any]:
        """
        Detect which protocol the ECU supports

        Returns:
            Protocol instance if detection successful, None otherwise
        """
        # Try KWP2000 first (most common for 28M4G)
        try:
            self.logger.debug("Attempting KWP2000 protocol detection")
            kwp_protocol = KWP2000Protocol(self.serial_port)
            if kwp_protocol.initialize():
                self.config.protocol = ProtocolType.KWP2000
                self.logger.info("KWP2000 protocol detected and initialized")
                return kwp_protocol
        except Exception as e:
            self.logger.debug(f"KWP2000 detection failed: {e}")

        # Try UDS protocol (newer 28M4G variants)
        try:
            self.logger.debug("Attempting UDS protocol detection")
            uds_protocol = UDSProtocol(self.serial_port)
            if uds_protocol.initialize():
                self.config.protocol = ProtocolType.UDS
                self.logger.info("UDS protocol detected and initialized")
                return uds_protocol
        except Exception as e:
            self.logger.debug(f"UDS detection failed: {e}")

        self.logger.warning("No compatible protocol detected")
        return None

    def disconnect(self):
        """Disconnect from ECU"""
        try:
            if self.protocol:
                # Close diagnostic session if active
                try:
                    self.protocol.close_session()
                except:
                    pass  # Ignore errors during cleanup

            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.logger.info("ECU connection closed")

        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
        finally:
            self.serial_port = None
            self.protocol = None
            self.status = ConnectionStatus.DISCONNECTED
            self.ecu_info = None

    def is_connected(self) -> bool:
        """Check if ECU is connected and responsive"""
        if not self.serial_port or not self.serial_port.is_open:
            return False

        if self.status != ConnectionStatus.CONNECTED:
            return False

        # Try a simple test command
        try:
            if self.protocol:
                return self.protocol.test_connection()
        except:
            return False

        return False

    def get_ecu_info(self) -> Optional[ECUInfo]:
        """
        Get ECU identification information

        Returns:
            ECUInfo object if successful, None otherwise
        """
        if not self.protocol:
            return None

        try:
            return self.protocol.get_ecu_info()
        except Exception as e:
            self.logger.error(f"Failed to get ECU info: {e}")
            return None

    def read_live_data(self) -> Dict[str, Any]:
        """
        Read live data parameters from ECU
        
        Returns:
            Dictionary with parameter names and values
        """
        if not self.is_connected() or not self.protocol:
            return {}
            
        try:
            if hasattr(self.protocol, 'read_live_data'):
                return self.protocol.read_live_data()
            return {}
        except Exception as e:
            self.logger.error(f"Failed to read live data: {e}")
            return {}

    def send_raw_command(self, command: bytes) -> Optional[bytes]:
        """
        Send raw command to ECU (for advanced use)

        Args:
            command: Raw command bytes

        Returns:
            Response bytes if successful, None otherwise
        """
        if not self.is_connected():
            raise ECUConnectionError("ECU not connected")

        try:
            # Log the command
            log_ecu_communication(self.config.port, "TX", command)

            # Send command
            self.serial_port.write(command)
            self.serial_port.flush()

            # Wait for response
            response = self.serial_port.read(1024)

            # Log response
            log_ecu_communication(self.config.port, "RX", response, len(response) > 0)

            return response if response else None

        except Exception as e:
            self.logger.error(f"Raw command failed: {e}")
            return None

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status

        Returns:
            Dictionary with connection information
        """
        return {
            'status': self.status.value,
            'port': self.config.port if self.serial_port else None,
            'baudrate': self.config.baudrate,
            'protocol': self.config.protocol.value if self.config.protocol else None,
            'ecu_info': self.ecu_info,
            'is_responsive': self.is_connected()
        }

    def test_connection_quality(self) -> Dict[str, float]:
        """
        Test connection quality and latency

        Returns:
            Dictionary with quality metrics
        """
        if not self.is_connected():
            return {'quality': 0.0, 'latency_ms': 0.0, 'success_rate': 0.0}

        try:
            # Send multiple test commands
            test_times = []
            successful_tests = 0
            total_tests = 5

            for i in range(total_tests):
                start_time = time.time()
                if self.protocol.test_connection():
                    end_time = time.time()
                    test_times.append((end_time - start_time) * 1000)  # Convert to ms
                    successful_tests += 1
                time.sleep(0.1)  # Small delay between tests

            # Calculate metrics
            avg_latency = sum(test_times) / len(test_times) if test_times else 0
            success_rate = successful_tests / total_tests
            quality = success_rate * 100  # Simple quality metric

            return {
                'quality': quality,
                'latency_ms': avg_latency,
                'success_rate': success_rate,
                'tests_successful': successful_tests,
                'tests_total': total_tests
            }

        except Exception as e:
            self.logger.error(f"Connection quality test failed: {e}")
            return {'quality': 0.0, 'latency_ms': 0.0, 'success_rate': 0.0}