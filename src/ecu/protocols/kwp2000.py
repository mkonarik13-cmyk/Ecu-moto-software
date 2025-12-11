"""
KWP2000 Protocol implementation for Magneti Marelli 28M4G ECU
Keyword Protocol 2000 with ISO-TP transport layer
"""

import time
import struct
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from src.maps.types import ECUInfo, ProtocolType, DTC, DTCStatus, SecurityKey
from src.utils.logger import get_protocol_logger, log_ecu_communication


class KWP2000Service(Enum):
    """KWP2000 service identifiers"""
    START_DIAGNOSTIC = 0x10
    STOP_DIAGNOSTIC = 0x11
    SECURITY_ACCESS = 0x27
    READ_DATA_BY_IDENTIFIER = 0x21
    READ_MEMORY_BY_ADDRESS = 0x23
    WRITE_MEMORY_BY_ADDRESS = 0x3D
    TESTER_PRESENT = 0x3E
    READ_DTC = 0x18
    CLEAR_DTC = 0x19
    READ_SCALING_DATA = 0x19
    READ_DATA_BY_LOCAL_ID = 0x2F
    ECU_RESET = 0x11


class KWP2000Response(Enum):
    """KWP2000 response codes"""
    POSITIVE_RESPONSE = 0x00
    GENERAL_REJECT = 0x10
    SERVICE_NOT_SUPPORTED = 0x11
    SUB_FUNCTION_NOT_SUPPORTED = 0x12
    CONDITIONS_NOT_CORRECT = 0x22
    REQUEST_SEQUENCE_ERROR = 0x24
    SECURITY_ACCESS_DENIED = 0x33
    INVALID_KEY = 0x35
    EXCEEDED_NUMBER_OF_ATTEMPTS = 0x36
    REQUIRED_TIME_DELAY_NOT_EXPIRED = 0x37
    UPLOAD_DOWNLOAD_NOT_ACCEPTED = 0x70
    TRANSFER_DATA_SUSPENDED = 0x71
    GENERAL_PROGRAMMING_FAILURE = 0x72
    BLOCK_SEQUENCE_ERROR = 0x73


class KWP2000Protocol:
    """
    KWP2000 protocol implementation specifically for 28M4G ECU
    Includes 28M4G-specific wake-up sequences and address handling
    """

    def __init__(self, serial_port):
        self.serial_port = serial_port
        self.logger = get_protocol_logger()
        self.session_active = False
        self.security_level = 0
        self.target_addr = 0x01  # Default ECU address
        self.source_addr = 0xF1  # Default tester address

        # 28M4G specific constants
        self.WAKE_UP_PATTERN = bytes([0x81, 0x12, 0xF1, 0x81, 0x04])
        self.KWP_HEADER_FORMAT = ">BBB"  # fmt, target, source
        self.KWP_LENGTH_OFFSET = 3
        self.KWP_SERVICE_OFFSET = 4

    def initialize(self) -> bool:
        """
        Initialize KWP2000 communication with 28M4G specific wake-up

        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing KWP2000 protocol for 28M4G ECU")

            # Send 28M4G wake-up sequence
            if not self._send_28m4g_wake_up():
                self.logger.error("28M4G wake-up failed")
                return False

            # Try to start diagnostic session
            if not self.start_diagnostic_session():
                self.logger.error("Failed to start diagnostic session")
                return False

            self.logger.info("KWP2000 protocol initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"KWP2000 initialization failed: {e}")
            return False

    def _send_28m4g_wake_up(self) -> bool:
        """
        Send 28M4G specific wake-up sequence

        Returns:
            True if wake-up successful
        """
        try:
            self.logger.debug("Sending 28M4G wake-up sequence")

            # Clear buffers
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()

            # Send wake-up pattern multiple times
            for i in range(3):
                self.serial_port.write(self.WAKE_UP_PATTERN)
                self.serial_port.flush()
                time.sleep(0.1)

            # Wait for response
            time.sleep(0.5)
            response = self.serial_port.read(64)

            if len(response) > 0:
                self.logger.debug(f"28M4G wake-up response: {response.hex()}")
                return True

        except Exception as e:
            self.logger.error(f"28M4G wake-up failed: {e}")

        return False

    def _send_kwp_frame(self, service_id: int, data: bytes = b"") -> Optional[bytes]:
        """
        Send KWP2000 frame with proper formatting

        Args:
            service_id: KWP2000 service ID
            data: Additional data payload

        Returns:
            Response if successful, None otherwise
        """
        try:
            # Build KWP2000 frame
            length = len(data) + 1  # +1 for service ID
            frame = struct.pack(self.KWP_HEADER_FORMAT, 0x80, self.target_addr, self.source_addr)
            frame += bytes([length, service_id]) + data

            # Add checksum (simple sum modulo 256)
            checksum = sum(frame) & 0xFF
            frame += bytes([checksum])

            # Log transmission
            log_ecu_communication("KWP2000", "TX", frame)

            # Send frame
            self.serial_port.write(frame)
            self.serial_port.flush()

            # Wait for response
            response = self.serial_port.read(256)
            if response:
                log_ecu_communication("KWP2000", "RX", response)
                return self._validate_kwp_response(response, service_id)

            return None

        except Exception as e:
            self.logger.error(f"KWP2000 frame send failed: {e}")
            return None

    def _validate_kwp_response(self, response: bytes, expected_service: int) -> Optional[bytes]:
        """
        Validate KWP2000 response and extract data

        Args:
            response: Raw response bytes
            expected_service: Expected service ID for positive response

        Returns:
            Response data if valid, None otherwise
        """
        if len(response) < 5:
            self.logger.warning("KWP2000 response too short")
            return None

        # Check frame format
        fmt, target, source = struct.unpack(self.KWP_HEADER_FORMAT, response[:3])
        if fmt != 0x80 or source != self.target_addr or target != self.source_addr:
            self.logger.warning("Invalid KWP2000 response header")
            return None

        # Check length
        length = response[3]
        if len(response) < length + 5:  # +5 for header and checksum
            self.logger.warning("KWP2000 response length mismatch")
            return None

        # Validate checksum
        checksum = response[-1]
        calculated_checksum = sum(response[:-1]) & 0xFF
        if checksum != calculated_checksum:
            self.logger.warning("KWP2000 checksum error")
            return None

        # Extract service ID and data
        service_id = response[4]
        data = response[5:5+length-1] if length > 1 else b""

        # Check response type
        if service_id == expected_service + 0x40:  # Positive response
            return data
        elif service_id == 0x7F:  # Negative response
            if len(data) >= 1:
                error_code = KWP2000Response(data[0])
                self.logger.warning(f"KWP2000 negative response: {error_code}")
            return None

        self.logger.warning(f"Unexpected KWP2000 service ID: {service_id}")
        return None

    def start_diagnostic_session(self) -> bool:
        """
        Start diagnostic session with ECU

        Returns:
            True if session started successfully
        """
        try:
            self.logger.info("Starting KWP2000 diagnostic session")

            # Try different diagnostic session types
            session_types = [
                0x81,  # Extended diagnostic session
                0x85,  # Development diagnostic session
                0x89   # Programming session (28M4G specific)
            ]

            for session_type in session_types:
                response = self._send_kwp_frame(
                    KWP2000Service.START_DIAGNOSTIC.value,
                    bytes([session_type])
                )

                if response is not None:
                    self.session_active = True
                    self.logger.info(f"Diagnostic session started with type: 0x{session_type:02X}")
                    return True

            self.logger.error("Failed to start any diagnostic session")
            return False

        except Exception as e:
            self.logger.error(f"Start diagnostic session failed: {e}")
            return False

    def stop_diagnostic_session(self) -> bool:
        """
        Stop diagnostic session

        Returns:
            True if session stopped successfully
        """
        try:
            response = self._send_kwp_frame(KWP2000Service.STOP_DIAGNOSTIC.value)
            if response is not None:
                self.session_active = False
                self.logger.info("Diagnostic session stopped")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Stop diagnostic session failed: {e}")
            return False

    def security_access(self, level: int, key: Optional[bytes] = None) -> bool:
        """
        Perform security access (seed/key authentication)

        Args:
            level: Security level
            key: Key for seed validation (None for seed request)

        Returns:
            True if security access successful

        Note: This is a placeholder for 28M4G security access
              Real implementation requires 28M4G specific algorithm
        """
        try:
            self.logger.info(f"Security access attempt - Level: {level}")

            # Request seed (odd sub-function)
            if key is None:
                response = self._send_kwp_frame(
                    KWP2000Service.SECURITY_ACCESS.value,
                    bytes([level * 2 - 1])  # Request seed
                )

                if response:
                    seed = response
                    self.logger.warning(f"Security seed received: {seed.hex()}")
                    self.logger.warning("TODO: Implement 28M4G seed/key algorithm")
                    return False

            # Send key (even sub-function)
            else:
                response = self._send_kwp_frame(
                    KWP2000Service.SECURITY_ACCESS.value,
                    bytes([level * 2]) + key
                )

                if response is not None:
                    self.security_level = level
                    self.logger.info(f"Security access granted - Level: {level}")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Security access failed: {e}")
            return False

    def read_memory_by_address(self, address: int, length: int) -> Optional[bytes]:
        """
        Read memory from ECU by address

        Args:
            address: Memory address
            length: Number of bytes to read

        Returns:
            Data if successful, None otherwise
        """
        try:
            self.logger.debug(f"Reading memory - Address: 0x{address:08X}, Length: {length}")

            # KWP2000 uses 24-bit address and 16-bit length
            address_bytes = struct.pack(">L", address)[1:]  # Use upper 3 bytes
            length_bytes = struct.pack(">H", length)

            data = address_bytes + length_bytes
            response = self._send_kwp_frame(KWP2000Service.READ_MEMORY_BY_ADDRESS.value, data)

            if response:
                self.logger.debug(f"Memory read successful: {len(response)} bytes")
                return response

            return None

        except Exception as e:
            self.logger.error(f"Read memory by address failed: {e}")
            return None

    def write_memory_by_address(self, address: int, data: bytes) -> bool:
        """
        Write memory to ECU by address

        Args:
            address: Memory address
            data: Data to write

        Returns:
            True if write successful
        """
        try:
            self.logger.debug(f"Writing memory - Address: 0x{address:08X}, Length: {len(data)}")

            # KWP2000 uses 24-bit address and 16-bit length
            address_bytes = struct.pack(">L", address)[1:]  # Use upper 3 bytes
            length_bytes = struct.pack(">H", len(data))

            request_data = address_bytes + length_bytes + data
            response = self._send_kwp_frame(KWP2000Service.WRITE_MEMORY_BY_ADDRESS.value, request_data)

            if response is not None:
                self.logger.debug(f"Memory write successful: {len(data)} bytes")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Write memory by address failed: {e}")
            return False

    def read_dtcs(self) -> List[DTC]:
        """
        Read diagnostic trouble codes

        Returns:
            List of DTCs
        """
        try:
            self.logger.info("Reading DTCs")

            dtcs = []
            response = self._send_kwp_frame(KWP2000Service.READ_DTC.value)

            if response:
                # Parse DTCs from response (format depends on ECU)
                # This is a simplified parser
                for i in range(0, len(response), 3):
                    if i + 2 < len(response):
                        dtc_code = f"P{response[i]:02X}{response[i+1]:02X}"
                        status_byte = response[i+2]

                        # Map status byte to DTC status
                        if status_byte & 0x01:
                            status = DTCStatus.ACTIVE
                        elif status_byte & 0x08:
                            status = DTCStatus.STORED
                        else:
                            status = DTCStatus.PENDING

                        dtc = DTC(
                            code=dtc_code,
                            description=f"DTC {dtc_code}",  # TODO: Add description mapping
                            status=status,
                            occurrence_count=1,
                            first_occurrence=time.time(),
                            last_occurrence=time.time()
                        )
                        dtcs.append(dtc)

            self.logger.info(f"Read {len(dtcs)} DTCs")
            return dtcs

        except Exception as e:
            self.logger.error(f"Read DTCs failed: {e}")
            return []

    def clear_dtcs(self) -> bool:
        """
        Clear diagnostic trouble codes

        Returns:
            True if clear successful
        """
        try:
            self.logger.info("Clearing DTCs")

            response = self._send_kwp_frame(KWP2000Service.CLEAR_DTC.value)
            if response is not None:
                self.logger.info("DTCs cleared successfully")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Clear DTCs failed: {e}")
            return False

    def get_ecu_info(self) -> Optional[ECUInfo]:
        """
        Get ECU identification information

        Returns:
            ECUInfo object if successful
        """
        try:
            self.logger.info("Getting ECU identification")

            # 28M4G specific identifiers
            identifiers = {
                0xF180: "VIN",  # Vehicle Identification Number
                0xF181: "Hardware Version",
                0xF182: "Software Version",
                0xF183: "Calibration Number"
            }

            ecu_data = {}

            for identifier, name in identifiers.items():
                id_bytes = struct.pack(">H", identifier)
                response = self._send_kwp_frame(
                    KWP2000Service.READ_DATA_BY_IDENTIFIER.value,
                    id_bytes
                )

                if response:
                    # Convert bytes to string, stripping null terminators
                    value = response.rstrip(b'\x00').decode('utf-8', errors='ignore')
                    ecu_data[name] = value
                    self.logger.debug(f"ECU {name}: {value}")

            # Build ECUInfo object
            if all(key in ecu_data for key in ["VIN", "Hardware Version", "Software Version"]):
                from src.maps.types import EngineType
                # Detect engine type from hardware version or calibration
                engine_type = EngineType.CC125  # Default, should be detected from ECU

                return ECUInfo(
                    vin=ecu_data["VIN"],
                    hardware_version=ecu_data["Hardware Version"],
                    software_version=ecu_data["Software Version"],
                    protocol=ProtocolType.KWP2000,
                    flash_size=256 * 1024,  # 28M4G typical size
                    supported_features=["KWP2000", "Memory Read/Write", "DTC"],
                    engine_type=engine_type,
                    calibration_number=ecu_data.get("Calibration Number")
                )

            return None

        except Exception as e:
            self.logger.error(f"Get ECU info failed: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Test if connection is still active

        Returns:
            True if connection test successful
        """
        try:
            # Send tester present command
            response = self._send_kwp_frame(KWP2000Service.TESTER_PRESENT.value)
            return response is not None

        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def read_live_data(self) -> Dict[str, Any]:
        """
        Read live data parameters (RPM, Temp, etc.)
        
        Returns:
            Dictionary with parameter names and values
        """
        try:
            # TODO: These are example Local IDs.
            # Real IDs for 28M4G need to be verified (often 0x01, 0x02, etc.)
            # or read via memory address if PIDs are not standard.
            
            live_data = {}
            
            # Example: Read RPM (assuming Local ID 0x10 returns 2 bytes)
            # response = self._send_kwp_frame(KWP2000Service.READ_DATA_BY_LOCAL_ID.value, bytes([0x10]))
            # if response:
            #     raw_rpm = struct.unpack(">H", response)[0]
            #     live_data['rpm'] = raw_rpm * 50  # Example scaling
            
            # Example: Read Coolant Temp (assuming Local ID 0x11 returns 1 byte)
            # response = self._send_kwp_frame(KWP2000Service.READ_DATA_BY_LOCAL_ID.value, bytes([0x11]))
            # if response:
            #     raw_temp = response[0]
            #     live_data['temperature'] = raw_temp - 40  # Example scaling
            
            # For now, return empty dict as we don't have real IDs
            # The dashboard will handle missing keys by keeping previous values or showing defaults
            return live_data

        except Exception as e:
            self.logger.error(f"Read live data failed: {e}")
            return {}

    def close_session(self):
        """Close the diagnostic session"""
        if self.session_active:
            self.stop_diagnostic_session()