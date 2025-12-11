"""
UDS (Unified Diagnostic Services) Protocol implementation for newer 28M4G ECU variants
ISO 14229 standard with extended features
"""

import time
import struct
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from src.maps.types import (
    ECUInfo, ProtocolType, DTC, DTCStatus, SecurityKey, SessionType
)
from src.utils.logger import get_protocol_logger, log_ecu_communication


class UDSService(Enum):
    """UDS service identifiers"""
    DIAGNOSTIC_SESSION_CONTROL = 0x10
    ECU_RESET = 0x11
    SECURITY_ACCESS = 0x27
    COMMUNICATION_CONTROL = 0x28
    TESTER_PRESENT = 0x3E
    READ_DATA_BY_IDENTIFIER = 0x22
    READ_MEMORY_BY_ADDRESS = 0x23
    WRITE_DATA_BY_IDENTIFIER = 0x2E
    WRITE_MEMORY_BY_ADDRESS = 0x3D
    CLEAR_DIAGNOSTIC_INFORMATION = 0x14
    READ_DTC = 0x19
    ROUTINE_CONTROL = 0x31
    REQUEST_DOWNLOAD = 0x34
    REQUEST_UPLOAD = 0x35
    TRANSFER_DATA = 0x36
    REQUEST_TRANSFER_EXIT = 0x37


class UDSResponse(Enum):
    """UDS negative response codes"""
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


class UDSSession:
    """UDS session types"""
    DEFAULT = 0x01
    PROGRAMMING = 0x02
    EXTENDED_DIAGNOSTIC = 0x03
    SAFETY_SYSTEM_DIAGNOSTIC = 0x04


class UDSProtocol:
    """
    UDS protocol implementation for newer 28M4G ECU variants
    Includes 28M4G specific extended features and session handling
    """

    def __init__(self, serial_port):
        self.serial_port = serial_port
        self.logger = get_protocol_logger()
        self.session_active = False
        self.current_session = SessionType.DEFAULT
        self.security_level = 0
        self.target_addr = 0x7E0  # UDS standard ECU address
        self.source_addr = 0x7E8  # UDS standard tester address
        self.block_sequence_counter = 0

        # UDS specific constants
        self.UDS_CAN_ID_FORMAT = ">HH"
        self.UDS_HEADER_FORMAT = ">BBH"  # length, type, address
        self.MAX_BLOCK_SIZE = 4096  # Max bytes per transfer block

    def initialize(self) -> bool:
        """
        Initialize UDS communication with 28M4G ECU

        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing UDS protocol for 28M4G ECU")

            # Clear any existing communication
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()

            # Try to establish communication with tester present
            if self.tester_present():
                # Start extended diagnostic session
                if self.diagnostic_session_control(SessionType.EXTENDED):
                    self.logger.info("UDS protocol initialized successfully")
                    return True

            self.logger.error("UDS initialization failed")
            return False

        except Exception as e:
            self.logger.error(f"UDS initialization failed: {e}")
            return False

    def _send_uds_frame(self, service_id: int, data: bytes = b"") -> Optional[bytes]:
        """
        Send UDS frame with ISO-TP transport layer

        Args:
            service_id: UDS service ID
            data: Additional data payload

        Returns:
            Response if successful, None otherwise
        """
        try:
            # Build UDS frame
            length = 1 + len(data)  # +1 for service ID
            frame = bytes([length, service_id]) + data

            # Log transmission
            log_ecu_communication("UDS", "TX", frame)

            # Send frame
            self.serial_port.write(frame)
            self.serial_port.flush()

            # Wait for response
            response = self.serial_port.read(4096)
            if response:
                log_ecu_communication("UDS", "RX", response)
                return self._validate_uds_response(response, service_id)

            return None

        except Exception as e:
            self.logger.error(f"UDS frame send failed: {e}")
            return None

    def _validate_uds_response(self, response: bytes, expected_service: int) -> Optional[bytes]:
        """
        Validate UDS response and extract data

        Args:
            response: Raw response bytes
            expected_service: Expected service ID for positive response

        Returns:
            Response data if valid, None otherwise
        """
        if len(response) < 2:
            self.logger.warning("UDS response too short")
            return None

        # Check length byte
        length = response[0]
        if len(response) < length + 1:
            self.logger.warning("UDS response length mismatch")
            return None

        # Extract service ID and data
        service_id = response[1]
        data = response[2:2+length-1] if length > 1 else b""

        # Check response type
        if service_id == expected_service + 0x40:  # Positive response
            return data
        elif service_id == 0x7F:  # Negative response
            if len(data) >= 2:
                error_service = data[0]
                error_code = UDSResponse(data[1])
                self.logger.warning(f"UDS negative response: {error_code} for service 0x{error_service:02X}")
            return None

        self.logger.warning(f"Unexpected UDS service ID: {service_id}")
        return None

    def diagnostic_session_control(self, session_type: SessionType) -> bool:
        """
        Control diagnostic session type

        Args:
            session_type: Type of session to start

        Returns:
            True if session control successful
        """
        try:
            self.logger.info(f"Starting {session_type.value} session")

            session_byte = {
                SessionType.DEFAULT: UDSSession.DEFAULT,
                SessionType.PROGRAMMING: UDSSession.PROGRAMMING,
                SessionType.EXTENDED: UDSSession.EXTENDED_DIAGNOSTIC
            }.get(session_type, UDSSession.DEFAULT)

            response = self._send_uds_frame(
                UDSService.DIAGNOSTIC_SESSION_CONTROL.value,
                bytes([session_byte])
            )

            if response is not None:
                self.session_active = True
                self.current_session = session_type
                self.logger.info(f"{session_type.value} session started")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Diagnostic session control failed: {e}")
            return False

    def security_access(self, level: int, key: Optional[bytes] = None) -> bool:
        """
        Perform UDS security access (seed/key authentication)

        Args:
            level: Security level
            key: Key for seed validation (None for seed request)

        Returns:
            True if security access successful

        Note: This is a placeholder for 28M4G UDS security access
              Real implementation requires 28M4G specific algorithm
        """
        try:
            self.logger.info(f"UDS security access - Level: {level}")

            # Request seed (odd sub-function)
            if key is None:
                response = self._send_uds_frame(
                    UDSService.SECURITY_ACCESS.value,
                    bytes([level * 2 - 1])  # Request seed
                )

                if response:
                    seed = response
                    self.logger.warning(f"Security seed received: {seed.hex()}")
                    self.logger.warning("TODO: Implement 28M4G UDS seed/key algorithm")
                    return False

            # Send key (even sub-function)
            else:
                response = self._send_uds_frame(
                    UDSService.SECURITY_ACCESS.value,
                    bytes([level * 2]) + key
                )

                if response is not None:
                    self.security_level = level
                    self.logger.info(f"UDS security access granted - Level: {level}")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"UDS security access failed: {e}")
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
            self.logger.debug(f"UDS read memory - Address: 0x{address:08X}, Length: {length}")

            # UDS uses addressAndLength format
            address_bytes = struct.pack(">L", address)
            length_bytes = struct.pack(">H", length)

            # Build addressAndLength identifier
            # Format: memorySize, memoryAddress
            address_length_format = bytes([0x44]) + length_bytes + address_bytes

            response = self._send_uds_frame(
                UDSService.READ_MEMORY_BY_ADDRESS.value,
                address_length_format
            )

            if response:
                self.logger.debug(f"UDS memory read successful: {len(response)} bytes")
                return response

            return None

        except Exception as e:
            self.logger.error(f"UDS read memory failed: {e}")
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
            self.logger.debug(f"UDS write memory - Address: 0x{address:08X}, Length: {len(data)}")

            # UDS uses addressAndLength format
            address_bytes = struct.pack(">L", address)
            length_bytes = struct.pack(">H", len(data))

            # Build addressAndLength identifier
            address_length_format = bytes([0x44]) + length_bytes + address_bytes

            request_data = address_length_format + data
            response = self._send_uds_frame(
                UDSService.WRITE_MEMORY_BY_ADDRESS.value,
                request_data
            )

            if response is not None:
                self.logger.debug(f"UDS memory write successful: {len(data)} bytes")
                return True

            return False

        except Exception as e:
            self.logger.error(f"UDS write memory failed: {e}")
            return False

    def request_download(self, address: int, length: int) -> bool:
        """
        Request download operation (for programming)

        Args:
            address: Memory address
            length: Data length

        Returns:
            True if request successful
        """
        try:
            self.logger.debug(f"UDS request download - Address: 0x{address:08X}, Length: {length}")

            # UDS requestDownload format
            data_format = bytes([0x44])  # memorySize, memoryAddress format
            address_bytes = struct.pack(">L", address)
            length_bytes = struct.pack(">L", length)  # Use 32-bit for UDS

            request_data = data_format + length_bytes + address_bytes
            response = self._send_uds_frame(
                UDSService.REQUEST_DOWNLOAD.value,
                request_data
            )

            if response is not None:
                self.logger.info("UDS download request accepted")
                return True

            return False

        except Exception as e:
            self.logger.error(f"UDS request download failed: {e}")
            return False

    def transfer_data(self, block_number: int, data: bytes) -> bool:
        """
        Transfer data block

        Args:
            block_number: Block sequence number
            data: Data block

        Returns:
            True if transfer successful
        """
        try:
            self.logger.debug(f"UDS transfer data - Block: {block_number}, Size: {len(data)}")

            # Block number for UDS
            block_bytes = struct.pack(">H", block_number)
            request_data = block_bytes + data

            response = self._send_uds_frame(
                UDSService.TRANSFER_DATA.value,
                request_data
            )

            if response is not None:
                self.logger.debug(f"UDS data transfer successful - Block {block_number}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"UDS transfer data failed: {e}")
            return False

    def tester_present(self) -> bool:
        """
        Send tester present to keep session alive

        Returns:
            True if tester present successful
        """
        try:
            response = self._send_uds_frame(UDSService.TESTER_PRESENT.value)
            return response is not None

        except Exception as e:
            self.logger.error(f"UDS tester present failed: {e}")
            return False

    def read_dtcs(self) -> List[DTC]:
        """
        Read diagnostic trouble codes

        Returns:
            List of DTCs
        """
        try:
            self.logger.info("Reading UDS DTCs")

            dtcs = []
            # Read all DTCs with status
            response = self._send_uds_frame(
                UDSService.READ_DTC.value,
                bytes([0x02, 0xFF, 0xFF])  # Report all DTCs with status
            )

            if response:
                # Parse DTCs from UDS response
                # UDS DTC format: 3 bytes per DTC + 1 byte status
                for i in range(0, len(response), 4):
                    if i + 3 < len(response):
                        dtc_bytes = response[i:i+3]
                        status_byte = response[i+3]

                        # Convert DTC bytes to readable format
                        dtc_code = self._format_dtc_code(dtc_bytes)

                        # Map status byte to DTC status
                        if status_byte & 0x01:
                            status = DTCStatus.ACTIVE
                        elif status_byte & 0x08:
                            status = DTCStatus.STORED
                        else:
                            status = DTCStatus.PENDING

                        dtc = DTC(
                            code=dtc_code,
                            description=f"UDS DTC {dtc_code}",  # TODO: Add description mapping
                            status=status,
                            occurrence_count=1,
                            first_occurrence=time.time(),
                            last_occurrence=time.time()
                        )
                        dtcs.append(dtc)

            self.logger.info(f"Read {len(dtcs)} UDS DTCs")
            return dtcs

        except Exception as e:
            self.logger.error(f"UDS read DTCs failed: {e}")
            return []

    def clear_dtcs(self) -> bool:
        """
        Clear diagnostic trouble codes

        Returns:
            True if clear successful
        """
        try:
            self.logger.info("Clearing UDS DTCs")

            # Clear all DTCs
            response = self._send_uds_frame(
                UDSService.CLEAR_DIAGNOSTIC_INFORMATION.value,
                bytes([0xFFFFFF])  # Clear all DTCs
            )

            if response is not None:
                self.logger.info("UDS DTCs cleared successfully")
                return True

            return False

        except Exception as e:
            self.logger.error(f"UDS clear DTCs failed: {e}")
            return False

    def get_ecu_info(self) -> Optional[ECUInfo]:
        """
        Get ECU identification information using UDS

        Returns:
            ECUInfo object if successful
        """
        try:
            self.logger.info("Getting UDS ECU identification")

            # UDS standard identifiers
            identifiers = {
                0xF190: "VIN",  # Vehicle Identification Number
                0xF18C: "Hardware Version",
                0xF18D: "Software Version",
                0xF18E: "Calibration Number"
            }

            ecu_data = {}

            for identifier, name in identifiers.items():
                id_bytes = struct.pack(">H", identifier)
                response = self._send_uds_frame(
                    UDSService.READ_DATA_BY_IDENTIFIER.value,
                    id_bytes
                )

                if response:
                    # Convert bytes to string, stripping null terminators
                    value = response.rstrip(b'\x00').decode('utf-8', errors='ignore')
                    ecu_data[name] = value
                    self.logger.debug(f"UDS ECU {name}: {value}")

            # Build ECUInfo object
            if all(key in ecu_data for key in ["VIN", "Hardware Version", "Software Version"]):
                from src.maps.types import EngineType
                # Detect engine type from hardware version or calibration
                engine_type = EngineType.CC125  # Default, should be detected from ECU

                return ECUInfo(
                    vin=ecu_data["VIN"],
                    hardware_version=ecu_data["Hardware Version"],
                    software_version=ecu_data["Software Version"],
                    protocol=ProtocolType.UDS,
                    flash_size=512 * 1024,  # UDS 28M4G typical size
                    supported_features=["UDS", "Memory Read/Write", "DTC", "Programming"],
                    engine_type=engine_type,
                    calibration_number=ecu_data.get("Calibration Number")
                )

            return None

        except Exception as e:
            self.logger.error(f"UDS get ECU info failed: {e}")
            return None

    def identify_28m4g_uds_features(self) -> List[str]:
        """
        Identify 28M4G specific UDS features

        Returns:
            List of supported features
        """
        try:
            self.logger.info("Identifying 28M4G UDS features")

            features = []

            # Test for programming support
            if self.diagnostic_session_control(SessionType.PROGRAMMING):
                features.append("Programming Mode")
                # Return to extended session
                self.diagnostic_session_control(SessionType.EXTENDED)

            # Test for extended memory access
            test_address = 0x8000  # Common memory area
            if self.read_memory_by_address(test_address, 1):
                features.append("Extended Memory Access")

            # Add standard UDS features
            features.extend(["DTC Management", "Security Access", "Tester Present"])

            self.logger.info(f"28M4G UDS features: {features}")
            return features

        except Exception as e:
            self.logger.error(f"28M4G UDS feature identification failed: {e}")
            return []

    def test_connection(self) -> bool:
        """
        Test if UDS connection is still active

        Returns:
            True if connection test successful
        """
        try:
            return self.tester_present()

        except Exception as e:
            self.logger.error(f"UDS connection test failed: {e}")
            return False

    def read_live_data(self) -> Dict[str, Any]:
        """
        Read live data parameters (RPM, Temp, etc.)
        
        Returns:
            Dictionary with parameter names and values
        """
        try:
            # TODO: These are example Data Identifiers (DIDs).
            # Real DIDs for 28M4G need to be verified.
            
            live_data = {}
            
            # Example: Read Engine Speed (DID 0xF40C)
            # response = self._send_uds_frame(UDSService.READ_DATA_BY_IDENTIFIER.value, b'\xF4\x0C')
            # if response:
            #     raw_rpm = struct.unpack(">H", response)[0]
            #     live_data['rpm'] = raw_rpm / 4  # Example scaling
            
            # Example: Read Coolant Temp (DID 0xF405)
            # response = self._send_uds_frame(UDSService.READ_DATA_BY_IDENTIFIER.value, b'\xF4\x05')
            # if response:
            #     raw_temp = response[0]
            #     live_data['temperature'] = raw_temp - 40
            
            return live_data

        except Exception as e:
            self.logger.error(f"Read live data failed: {e}")
            return {}

    def close_session(self):
        """Close the UDS diagnostic session"""
        if self.session_active:
            # Return to default session
            self.diagnostic_session_control(SessionType.DEFAULT)
            self.session_active = False

    def _format_dtc_code(self, dtc_bytes: bytes) -> str:
        """
        Convert UDS DTC bytes to readable format

        Args:
            dtc_bytes: 3-byte DTC representation

        Returns:
            Formatted DTC code string
        """
        if len(dtc_bytes) != 3:
            return "UNKNOWN"

        # UDS DTC format conversion
        first_byte = dtc_bytes[0]
        second_byte = dtc_bytes[1]
        third_byte = dtc_bytes[2]

        # Extract standard and type
        dtc_type = (first_byte >> 6) & 0x03
        dtc_second = first_byte & 0x3F

        # Type mapping
        type_map = {
            0: "P",  # Powertrain
            1: "C",  # Chassis
            2: "B",  # Body
            3: "U"   # Network/Communication
        }

        prefix = type_map.get(dtc_type, "X")
        code = f"{prefix}{dtc_second:02X}{second_byte:02X}{third_byte:02X}"

        return code