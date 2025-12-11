"""
Firmware parser for extracting 28M4G map data from binary files
Analyzes Magneti Marelli 28M4G firmware structure to extract fuel and ignition maps
"""

import struct
import binascii
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from src.maps.types import (
    FuelMap, IgnitionMap, FanSettings, MotorcycleMaps, FirmwareMap,
    EngineType, IdleSettings, ColdStartSettings, ECUInfo, ProtocolType
)
from src.utils.logger import get_maps_logger


class FirmwareParseError(Exception):
    """Custom exception for firmware parsing errors"""
    pass


class FirmwareParser:
    """
    Parser for 28M4G ECU firmware binary files
    Extracts fuel maps, ignition maps, and configuration data
    """

    def __init__(self):
        self.logger = get_maps_logger()

        # 28M4G specific signatures and patterns
        self.SIGNATURES = {
            '28M4G_125': b'\x28\x4D\x34\x47\x31\x32\x35',  # 28M4G125
            '28M4G_200': b'\x28\x4D\x34\x47\x32\x30\x30',  # 28M4G200
            '28M4G_300': b'\x28\x4D\x34\x47\x33\x30\x30',  # 28M4G300
        }

        # Known map locations (these are example offsets - real ones would need research)
        self.MAP_OFFSETS = {
            EngineType.CC125: {
                'fuel_map': 0x10000,
                'ignition_map': 0x14000,
                'fan_settings': 0x18000,
                'idle_settings': 0x1A000,
                'calibration': 0x1F000
            },
            EngineType.CC200: {
                'fuel_map': 0x12000,
                'ignition_map': 0x16000,
                'fan_settings': 0x1A000,
                'idle_settings': 0x1C000,
                'calibration': 0x21000
            },
            EngineType.CC300: {
                'fuel_map': 0x14000,
                'ignition_map': 0x18000,
                'fan_settings': 0x1C000,
                'idle_settings': 0x1E000,
                'calibration': 0x23000
            }
        }

        # Map dimensions for different engine types
        self.MAP_DIMENSIONS = {
            EngineType.CC125: {
                'rpm_points': 10,  # 1000-12000 RPM
                'tps_points': 11   # 0-100% TPS
            },
            EngineType.CC200: {
                'rpm_points': 12,  # 1000-14000 RPM
                'tps_points': 11   # 0-100% TPS
            },
            EngineType.CC300: {
                'rpm_points': 14,  # 1000-16000 RPM
                'tps_points': 11   # 0-100% TPS
            }
        }

    def parse_firmware(self, firmware_data: bytes) -> FirmwareMap:
        """
        Parse firmware binary data and extract all maps

        Args:
            firmware_data: Raw firmware binary data

        Returns:
            FirmwareMap object with extracted data

        Raises:
            FirmwareParseError: If parsing fails
        """
        try:
            self.logger.info(f"Starting firmware parse - Size: {len(firmware_data):,} bytes")

            # Validate firmware file
            self._validate_firmware(firmware_data)

            # Identify engine type
            engine_type = self.identify_engine_type(firmware_data)
            self.logger.info(f"Detected engine type: {engine_type.value}")

            # Extract ECU information
            ecu_info = self.extract_ecu_info(firmware_data, engine_type)

            # Extract fuel map
            fuel_map = self.extract_fuel_map(firmware_data, engine_type)

            # Extract ignition map
            ignition_map = self.extract_ignition_map(firmware_data, engine_type)

            # Extract fan settings
            fan_settings = self.extract_fan_settings(firmware_data, engine_type)

            # Extract idle settings
            idle_settings = self.extract_idle_settings(firmware_data, engine_type)

            # Extract cold start settings
            cold_start = self.extract_cold_start_settings(firmware_data, engine_type)

            # Create motorcycle maps object
            motorcycle_maps = MotorcycleMaps(
                fuel_map=fuel_map,
                ignition_map=ignition_map,
                rev_limiter=self._extract_rev_limiter(firmware_data, engine_type),
                fan_settings=fan_settings,
                idle_control=idle_settings,
                cold_start=cold_start,
                model_specific=self._extract_model_specific(firmware_data, engine_type)
            )

            # Calculate checksum
            checksum = self.calculate_checksum(firmware_data)

            # Create firmware map object
            firmware_map = FirmwareMap(
                raw_data=firmware_data,
                size=len(firmware_data),
                checksum=checksum,
                ecu_info=ecu_info,
                maps=motorcycle_maps,
                dtcs=[],  # DTCs would be read from ECU, not firmware
                flash_addresses=self._get_flash_addresses(engine_type),
                version_info=self._get_version_info(firmware_data)
            )

            self.logger.info(f"Successfully parsed firmware for {engine_type.value}")
            return firmware_map

        except Exception as e:
            self.logger.error(f"Firmware parse failed: {e}")
            raise FirmwareParseError(f"Failed to parse firmware: {e}")

    def _validate_firmware(self, firmware_data: bytes):
        """Validate firmware file format and integrity"""
        if not firmware_data:
            raise FirmwareParseError("Empty firmware data")

        # Check minimum size
        if len(firmware_data) < 0x1000:  # At least 4KB
            raise FirmwareParseError("Firmware file too small")

        # Look for 28M4G signature
        found_signature = False
        for name, signature in self.SIGNATURES.items():
            if signature in firmware_data:
                found_signature = True
                self.logger.debug(f"Found signature: {name}")
                break

        if not found_signature:
            # Try to find any 28M4G pattern
            if b'28M4G' not in firmware_data:
                raise FirmwareParseError("No 28M4G signature found in firmware")
            else:
                self.logger.warning("Found 28M4G pattern but specific signature not recognized")

    def identify_engine_type(self, firmware_data: bytes) -> EngineType:
        """
        Identify engine displacement from firmware

        Args:
            firmware_data: Raw firmware binary data

        Returns:
            Detected engine type
        """
        # Check for specific signatures
        for name, signature in self.SIGNATURES.items():
            if signature in firmware_data:
                if '125' in name:
                    return EngineType.CC125
                elif '200' in name:
                    return EngineType.CC200
                elif '300' in name:
                    return EngineType.CC300

        # Fallback: try to identify from calibration data or map size
        # This is a simplified approach - real identification would be more complex
        firmware_size = len(firmware_data)

        if firmware_size < 200 * 1024:  # Less than 200KB
            return EngineType.CC125
        elif firmware_size < 400 * 1024:  # Less than 400KB
            return EngineType.CC200
        else:
            return EngineType.CC300

    def extract_ecu_info(self, firmware_data: bytes, engine_type: EngineType) -> ECUInfo:
        """
        Extract ECU identification information from firmware

        Args:
            firmware_data: Raw firmware binary data
            engine_type: Detected engine type

        Returns:
            ECUInfo object
        """
        try:
            # Look for VIN (placeholder - would need actual location)
            vin = self._extract_vin(firmware_data)

            # Extract version information
            hw_version = self._extract_string_at_offset(firmware_data, 0xFF00, 16)
            sw_version = self._extract_string_at_offset(firmware_data, 0xFF20, 16)
            calibration = self._extract_string_at_offset(firmware_data, 0xFF40, 32)

            # Determine flash size
            flash_size = self._determine_flash_size(firmware_data)

            # Determine supported features
            features = [
                "KWP2000",
                "Fuel Map Editing",
                "Ignition Map Editing",
                "Fan Control",
                "DTC Reading"
            ]

            # Check for UDS support in newer firmware
            if b'UDS' in firmware_data or b'0x22' in firmware_data:
                features.append("UDS Protocol")

            return ECUInfo(
                vin=vin or "UNKNOWN",
                hardware_version=hw_version or f"28M4G-{engine_type.value}",
                software_version=sw_version or f"FW-{engine_type.value}",
                protocol=ProtocolType.KWP2000,  # Default, could be detected
                flash_size=flash_size,
                supported_features=features,
                engine_type=engine_type,
                calibration_number=calibration or None
            )

        except Exception as e:
            self.logger.error(f"Failed to extract ECU info: {e}")
            # Return minimal ECU info
            return ECUInfo(
                vin="UNKNOWN",
                hardware_version=f"28M4G-{engine_type.value}",
                software_version="UNKNOWN",
                protocol=ProtocolType.KWP2000,
                flash_size=256 * 1024,  # Default size
                supported_features=["KWP2000"],
                engine_type=engine_type
            )

    def extract_fuel_map(self, firmware_data: bytes, engine_type: EngineType) -> FuelMap:
        """
        Extract fuel injection map from firmware

        Args:
            firmware_data: Raw firmware binary data
            engine_type: Detected engine type

        Returns:
            FuelMap object
        """
        try:
            offsets = self.MAP_OFFSETS[engine_type]
            dimensions = self.MAP_DIMENSIONS[engine_type]

            # Generate RPM axis for engine type
            rpm_axis = self._generate_rpm_axis(engine_type)
            tps_axis = [i * 10 for i in range(dimensions['tps_points'])]  # 0, 10, 20...100%

            # Extract fuel map values
            fuel_offset = offsets['fuel_map']
            fuel_values = []

            for i in range(dimensions['rpm_points']):
                row = []
                for j in range(dimensions['tps_points']):
                    # Calculate position in firmware
                    pos = fuel_offset + (i * dimensions['tps_points'] + j) * 2  # 2 bytes per value

                    if pos + 1 < len(firmware_data):
                        # Read 16-bit value (assuming little-endian)
                        raw_value = struct.unpack('<H', firmware_data[pos:pos+2])[0]
                        # Convert to injection time in milliseconds
                        fuel_time = raw_value / 1000.0  # Convert from microseconds
                        row.append(fuel_time)
                    else:
                        # Use default value if out of bounds
                        row.append(2.5)  # Default 2.5ms

                fuel_values.append(row)

            return FuelMap(
                rpm_axis=rpm_axis,
                tps_axis=tps_axis,
                values=fuel_values,
                unit="ms",
                engine_type=engine_type,
                description=f"Fuel injection map for {engine_type.value} engine"
            )

        except Exception as e:
            self.logger.error(f"Failed to extract fuel map: {e}")
            # Return default fuel map
            return self._create_default_fuel_map(engine_type)

    def extract_ignition_map(self, firmware_data: bytes, engine_type: EngineType) -> IgnitionMap:
        """
        Extract ignition timing map from firmware

        Args:
            firmware_data: Raw firmware binary data
            engine_type: Detected engine type

        Returns:
            IgnitionMap object
        """
        try:
            offsets = self.MAP_OFFSETS[engine_type]
            dimensions = self.MAP_DIMENSIONS[engine_type]

            # Generate RPM axis for engine type
            rpm_axis = self._generate_rpm_axis(engine_type)
            tps_axis = [i * 10 for i in range(dimensions['tps_points'])]

            # Extract ignition map values
            ignition_offset = offsets['ignition_map']
            ignition_values = []

            for i in range(dimensions['rpm_points']):
                row = []
                for j in range(dimensions['tps_points']):
                    # Calculate position in firmware
                    pos = ignition_offset + (i * dimensions['tps_points'] + j) * 1  # 1 byte per value

                    if pos < len(firmware_data):
                        # Read 8-bit value
                        raw_value = firmware_data[pos]
                        # Convert to degrees BTDC (typically 5-45 degrees)
                        timing = raw_value / 2.0  # Scale to degrees
                        timing = max(5, min(45, timing))  # Clamp to reasonable range
                        row.append(timing)
                    else:
                        # Use default value
                        row.append(25.0)  # Default 25° BTDC

                ignition_values.append(row)

            return IgnitionMap(
                rpm_axis=rpm_axis,
                tps_axis=tps_axis,
                values=ignition_values,
                unit="degrees BTDC",
                multi_spark=engine_type != EngineType.CC125,  # Multi-spark on larger engines
                gear_correction={},  # Would be extracted separately
                description=f"Ignition timing map for {engine_type.value} engine"
            )

        except Exception as e:
            self.logger.error(f"Failed to extract ignition map: {e}")
            # Return default ignition map
            return self._create_default_ignition_map(engine_type)

    def extract_fan_settings(self, firmware_data: bytes, engine_type: EngineType) -> FanSettings:
        """
        Extract cooling fan settings from firmware

        Args:
            firmware_data: Raw firmware binary data
            engine_type: Detected engine type

        Returns:
            FanSettings object
        """
        try:
            offsets = self.MAP_OFFSETS[engine_type]
            fan_offset = offsets['fan_settings']

            # Read fan settings
            if fan_offset + 8 < len(firmware_data):
                fan_data = firmware_data[fan_offset:fan_offset+8]

                # Parse fan settings (example format)
                on_temp = fan_data[0] + 60  # Byte 0: ON temperature offset
                off_temp = fan_data[1] + 70  # Byte 1: OFF temperature offset
                boost = fan_data[2] * 10     # Byte 2: Boost percentage
                flags = fan_data[3]          # Byte 3: Feature flags

                variable_speed = bool(flags & 0x01)
                dual_fan = bool(flags & 0x02)

                return FanSettings(
                    on_temp=float(on_temp),
                    off_temp=float(off_temp),
                    high_temp_boost=float(boost),
                    variable_speed=variable_speed,
                    dual_fan=dual_fan,
                    track_mode=False  # Would be determined from other settings
                )
            else:
                # Return default fan settings
                return FanSettings(
                    on_temp=95.0,
                    off_temp=85.0,
                    high_temp_boost=20.0,
                    variable_speed=False,
                    dual_fan=False,
                    track_mode=False
                )

        except Exception as e:
            self.logger.error(f"Failed to extract fan settings: {e}")
            # Return default fan settings
            return FanSettings(
                on_temp=95.0,
                off_temp=85.0,
                high_temp_boost=20.0,
                variable_speed=False,
                dual_fan=False,
                track_mode=False
            )

    def extract_idle_settings(self, firmware_data: bytes, engine_type: EngineType) -> IdleSettings:
        """Extract idle control settings"""
        # Placeholder implementation
        base_idle = {
            EngineType.CC125: 1400,
            EngineType.CC200: 1300,
            EngineType.CC300: 1200
        }.get(engine_type, 1300)

        return IdleSettings(
            target_rpm=base_idle,
            cold_start_rpm=base_idle + 200,
            warm_up_time=120,
            temperature_compensation={-10.0: 300, 0.0: 200, 20.0: 0, 40.0: -100}
        )

    def extract_cold_start_settings(self, firmware_data: bytes, engine_type: EngineType) -> ColdStartSettings:
        """Extract cold start settings"""
        # Placeholder implementation
        return ColdStartSettings(
            enrichment_factor=1.2,
            warm_up_duration=180,
            temperature_thresholds=[0.0, 20.0, 40.0]
        )

    def _extract_vin(self, firmware_data: bytes) -> Optional[str]:
        """Extract VIN from firmware (placeholder)"""
        # Look for VIN pattern (17 characters)
        vin_pattern = rb'([A-HJ-NPR-Z0-9]{17})'
        import re
        match = re.search(vin_pattern, firmware_data)
        if match:
            return match.group(1).decode('ascii', errors='ignore')
        return None

    def _extract_string_at_offset(self, firmware_data: bytes, offset: int, max_length: int) -> Optional[str]:
        """Extract null-terminated string from firmware"""
        if offset >= len(firmware_data):
            return None

        end_offset = firmware_data.find(b'\x00', offset, offset + max_length)
        if end_offset == -1:
            end_offset = min(offset + max_length, len(firmware_data))

        string_data = firmware_data[offset:end_offset]
        return string_data.decode('ascii', errors='ignore').strip()

    def _determine_flash_size(self, firmware_data: bytes) -> int:
        """Determine flash size from firmware"""
        size = len(firmware_data)

        # Round up to nearest power of 2
        if size <= 64 * 1024:
            return 64 * 1024
        elif size <= 128 * 1024:
            return 128 * 1024
        elif size <= 256 * 1024:
            return 256 * 1024
        elif size <= 512 * 1024:
            return 512 * 1024
        else:
            return 1024 * 1024

    def _generate_rpm_axis(self, engine_type: EngineType) -> List[int]:
        """Generate RPM axis points for engine type"""
        rpm_ranges = {
            EngineType.CC125: (1000, 12000),
            EngineType.CC200: (1000, 14000),
            EngineType.CC300: (1000, 16000)
        }

        dimensions = self.MAP_DIMENSIONS[engine_type]
        min_rpm, max_rpm = rpm_ranges[engine_type]
        step = (max_rpm - min_rpm) // (dimensions['rpm_points'] - 1)

        return [min_rpm + i * step for i in range(dimensions['rpm_points'])]

    def _extract_rev_limiter(self, firmware_data: bytes, engine_type: EngineType) -> int:
        """Extract rev limiter setting"""
        # Placeholder - would read from specific firmware location
        default_limits = {
            EngineType.CC125: 11500,
            EngineType.CC200: 13500,
            EngineType.CC300: 15500
        }
        return default_limits.get(engine_type, 12000)

    def _extract_model_specific(self, firmware_data: bytes, engine_type: EngineType) -> Dict[str, Any]:
        """Extract model-specific features"""
        return {
            'quickshifter_supported': engine_type in [EngineType.CC200, EngineType.CC300],
            'traction_control_supported': engine_type == EngineType.CC300,
            'ride_by_wire_supported': False,  # Not in these models
            'abs_supported': False
        }

    def _get_flash_addresses(self, engine_type: EngineType) -> Dict[str, int]:
        """Get flash address ranges for operations"""
        return {
            'fuel_map': self.MAP_OFFSETS[engine_type]['fuel_map'],
            'ignition_map': self.MAP_OFFSETS[engine_type]['ignition_map'],
            'fan_settings': self.MAP_OFFSETS[engine_type]['fan_settings'],
            'configuration': 0xF000,
            'calibration': self.MAP_OFFSETS[engine_type]['calibration']
        }

    def _get_version_info(self, firmware_data: bytes) -> Dict[str, str]:
        """Extract version information"""
        return {
            'build_date': self._extract_string_at_offset(firmware_data, 0xFF80, 11) or "Unknown",
            'version': self._extract_string_at_offset(firmware_data, 0xFF90, 8) or "Unknown",
            'checksum': f"0x{self.calculate_checksum(firmware_data):08X}"
        }

    def _create_default_fuel_map(self, engine_type: EngineType) -> FuelMap:
        """Create default fuel map for engine type"""
        dimensions = self.MAP_DIMENSIONS[engine_type]
        rpm_axis = self._generate_rpm_axis(engine_type)
        tps_axis = [i * 10 for i in range(dimensions['tps_points'])]

        # Create realistic default fuel map
        fuel_values = []
        for rpm in rpm_axis:
            row = []
            for tps in tps_axis:
                # Base fuel calculation
                base_fuel = 2.0 + (rpm / 10000) * 2.0 + (tps / 100) * 4.0
                row.append(base_fuel)
            fuel_values.append(row)

        return FuelMap(
            rpm_axis=rpm_axis,
            tps_axis=tps_axis,
            values=fuel_values,
            unit="ms",
            engine_type=engine_type,
            description=f"Default fuel map for {engine_type.value}"
        )

    def _create_default_ignition_map(self, engine_type: EngineType) -> IgnitionMap:
        """Create default ignition map for engine type"""
        dimensions = self.MAP_DIMENSIONS[engine_type]
        rpm_axis = self._generate_rpm_axis(engine_type)
        tps_axis = [i * 10 for i in range(dimensions['tps_points'])]

        # Create realistic default ignition map
        ignition_values = []
        for rpm in rpm_axis:
            row = []
            for tps in tps_axis:
                # Base timing calculation
                base_timing = 10 + (rpm / 10000) * 20 - (tps / 100) * 3
                base_timing = max(5, min(40, base_timing))
                row.append(base_timing)
            ignition_values.append(row)

        return IgnitionMap(
            rpm_axis=rpm_axis,
            tps_axis=tps_axis,
            values=ignition_values,
            unit="degrees BTDC",
            multi_spark=engine_type != EngineType.CC125,
            gear_correction={},
            description=f"Default ignition map for {engine_type.value}"
        )

    def calculate_checksum(self, firmware_data: bytes) -> int:
        """
        Calculate firmware checksum

        Args:
            firmware_data: Raw firmware binary data

        Returns:
            Checksum value
        """
        return sum(firmware_data) & 0xFFFFFFFF

    def validate_checksum(self, firmware_data: bytes, expected_checksum: int) -> bool:
        """
        Validate firmware checksum

        Args:
            firmware_data: Raw firmware binary data
            expected_checksum: Expected checksum value

        Returns:
            True if checksum is valid
        """
        calculated = self.calculate_checksum(firmware_data)
        return calculated == expected_checksum