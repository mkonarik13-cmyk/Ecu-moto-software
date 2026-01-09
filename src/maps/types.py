"""
Core data structures for ECU maps and 28M4G specific motorcycle tuning
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime


class EngineType(Enum):
    """Engine displacement types for Italjet Dragster"""
    CC125 = "125cc"
    CC200 = "200cc"
    CC300 = "300cc"


class ProtocolType(Enum):
    """Supported communication protocols"""
    KWP2000 = "KWP2000"
    UDS = "UDS"


class DTCStatus(Enum):
    """Diagnostic Trouble Code status"""
    ACTIVE = "active"
    STORED = "stored"
    PENDING = "pending"


class SessionType(Enum):
    """UDS diagnostic session types"""
    DEFAULT = "default"
    PROGRAMMING = "programming"
    EXTENDED = "extended"


@dataclass
class ECUInfo:
    """ECU identification and configuration information"""
    vin: str
    hardware_version: str
    software_version: str
    protocol: ProtocolType
    flash_size: int
    supported_features: List[str]
    engine_type: EngineType
    calibration_number: Optional[str] = None
    manufacturing_date: Optional[datetime] = None


@dataclass
class FuelMap:
    """Fuel injection map for motorcycle tuning"""
    rpm_axis: List[int]  # RPM values (1000-18000 range for motorcycles)
    tps_axis: List[int]  # Throttle position values (0-100%)
    values: List[List[float]]  # 2D array of fuel values
    unit: str  # "ms" (milliseconds) or "mg/stroke"
    engine_type: EngineType  # 125/200/300 specific
    description: Optional[str] = None


@dataclass
class IgnitionMap:
    """Ignition timing map for motorcycle tuning"""
    rpm_axis: List[int]  # RPM values (1000-18000)
    tps_axis: List[int]  # Throttle position values (0-100%)
    values: List[List[float]]  # 2D array of ignition timing
    unit: str  # "degrees BTDC"
    multi_spark: bool  # Multi-spark capability
    gear_correction: Dict[int, float]  # Gear-specific adjustments
    description: Optional[str] = None


@dataclass
class FanSettings:
    """Cooling fan configuration for liquid-cooled engines"""
    on_temp: float  # Temperature to turn fan ON (°C)
    off_temp: float  # Temperature to turn fan OFF (°C)
    high_temp_boost: float  # High temperature boost setting
    variable_speed: bool  # Variable fan speed support
    dual_fan: bool  # Dual fan configuration
    track_mode: bool  # Track day mode (more aggressive cooling)


@dataclass
class IdleSettings:
    """Engine idle control settings"""
    target_rpm: int  # Target idle RPM
    cold_start_rpm: int  # Cold start idle RPM
    warm_up_time: int  # Time to reach normal idle (seconds)
    temperature_compensation: Dict[float, int]  # Temperature -> RPM compensation


@dataclass
class ColdStartSettings:
    """Cold start and warm-up settings"""
    enrichment_factor: float  # Fuel enrichment multiplier
    warm_up_duration: int  # Duration of warm-up phase (seconds)
    temperature_thresholds: List[float]  # Temperature thresholds for different phases


@dataclass
class MotorcycleMaps:
    """Complete set of motorcycle-specific maps and settings"""
    fuel_map: FuelMap
    ignition_map: IgnitionMap
    rev_limiter: int  # RPM limit
    fan_settings: FanSettings
    idle_control: IdleSettings
    cold_start: ColdStartSettings
    model_specific: Dict[str, Any]  # 125/200/300 specific features


@dataclass
class DTC:
    """Diagnostic Trouble Code"""
    code: str  # e.g., "P0171"
    description: str
    status: DTCStatus  # active, stored, pending
    occurrence_count: int
    first_occurrence: datetime
    last_occurrence: datetime


@dataclass
class FirmwareMap:
    """Complete firmware data with extracted maps"""
    raw_data: bytes
    size: int
    checksum: int
    ecu_info: ECUInfo
    maps: MotorcycleMaps
    dtcs: List[DTC]
    flash_addresses: Dict[str, int]  # Address ranges for different operations
    version_info: Dict[str, str]


@dataclass
class ConnectionConfig:
    """Connection configuration for ECU communication"""
    port: str
    baudrate: int
    protocol: ProtocolType
    timeout: float = 5.0
    retry_count: int = 3
    auto_detect: bool = True


@dataclass
class FlashProgress:
    """Progress information for flash operations"""
    operation: str  # "read" or "write"
    progress_percent: float
    bytes_processed: int
    total_bytes: int
    time_elapsed: float  # seconds
    time_remaining: float  # seconds
    current_address: int
    status: str  # "running", "completed", "error", "cancelled"


@dataclass
class SecurityKey:
    """Security access seed/key pair for 28M4G ECU"""
    level: int
    seed: Optional[bytes] = None
    key: Optional[bytes] = None
    algorithm: str = "unknown"  # Algorithm description for 28M4G


@dataclass
class MapModification:
    """Track changes made to maps"""
    map_type: str  # "fuel", "ignition", etc.
    coordinates: tuple  # (rpm_idx, tps_idx) or other relevant coordinates
    old_value: Union[float, int]
    new_value: Union[float, int]
    timestamp: datetime
    description: Optional[str] = None


# 28M4G specific constants and configurations
class ECU28M4GConstants:
    """28M4G ECU specific constants"""
    STANDARD_KLINE_BAUD = 10400  # Standard 28M4G K-Line baud rate
    ALTERNATIVE_KLINE_BAUD = 9600  # Alternative 28M4G baud rate

    # Memory map ranges (example addresses, need verification for 28M4G)
    FUEL_MAP_BASE = 0x8000
    IGNITION_MAP_BASE = 0x9000
    FAN_SETTINGS_BASE = 0xA000
    VIN_ADDRESS = 0xF000

    # 28M4G specific service IDs
    KWP_START_DIAGNOSTIC = 0x10
    KWP_SECURITY_ACCESS = 0x27
    KWP_READ_MEMORY = 0x23
    KWP_WRITE_MEMORY = 0x3D
    KWP_READ_DTC = 0x18
    KWP_CLEAR_DTC = 0x19

    # Motorcycle specific RPM ranges
    RPM_RANGES = {
        EngineType.CC125: (1000, 12000),
        EngineType.CC200: (1000, 14000),
        EngineType.CC300: (1000, 16000)
    }

    # Default temperature thresholds
    DEFAULT_FAN_ON = 95.0  # °C
    DEFAULT_FAN_OFF = 85.0  # °C
    MAX_SAFE_TEMP = 110.0  # °C