from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class EcuParameter:
    """
    Represents a single parameter that can be logged from the ECU.
    Inspired by RomRaider's logger definitions.
    """
    name: str
    id: str  # Unique identifier (e.g., PID or memory address)
    units: str
    byte_length: int
    conversion_func: Callable[[int], float]
    description: Optional[str] = None

@dataclass
class EcuTable:
    """
    Represents a 2D or 3D table (Map) in the ECU.
    e.g., Fuel Map (RPM vs TPS)
    """
    name: str
    x_axis_param: str  # ID of the parameter for X axis (e.g., "RPM")
    y_axis_param: str  # ID of the parameter for Y axis (e.g., "TPS")
    x_breakpoints: list[float]
    y_breakpoints: list[float]
    data: list[list[float]]  # The actual map values (Z-axis)

class EcuProtocol:
    """
    Defines the communication protocol for a specific ECU.
    """
    def __init__(self, name: str, baud_rate: int = 38400):
        self.name = name
        self.baud_rate = baud_rate
        self.parameters: dict[str, EcuParameter] = {}
        self.tables: dict[str, EcuTable] = {}

    def add_parameter(self, param: EcuParameter):
        self.parameters[param.id] = param

    def add_table(self, table: EcuTable):
        self.tables[table.name] = table

    def get_parameter(self, param_id: str) -> Optional[EcuParameter]:
        return self.parameters.get(param_id)
    
    def get_table(self, table_name: str) -> Optional[EcuTable]:
        return self.tables.get(table_name)

# Real 28M4G ECU Parameter Definitions for Italjet Dragster
def create_italjet_dragster_28m4g_protocol() -> EcuProtocol:
    """
    Create ECU protocol for Italjet Dragster with Magneti Marelli 28M4G.
    Based on real 28M4G parameter mappings and memory addresses.
    """
    protocol = EcuProtocol("Italjet Dragster 28M4G", baud_rate=10400)

    # === Engine Parameters ===

    # Engine Speed: Local ID 0x0C, 2 bytes, raw * 25
    protocol.add_parameter(EcuParameter(
        name="Engine Speed",
        id="RPM",
        units="rpm",
        byte_length=2,
        conversion_func=lambda x: x * 25,
        description="Current engine speed (RPM)"
    ))

    # Throttle Position: Local ID 0x11, 1 byte, (raw/255) * 100
    protocol.add_parameter(EcuParameter(
        name="Throttle Position",
        id="TPS",
        units="%",
        byte_length=1,
        conversion_func=lambda x: (x / 255.0) * 100.0,
        description="Throttle position sensor"
    ))

    # Engine Coolant Temperature: Local ID 0x04, 1 byte, raw - 40
    protocol.add_parameter(EcuParameter(
        name="Engine Coolant Temperature",
        id="ECT",
        units="°C",
        byte_length=1,
        conversion_func=lambda x: x - 40,
        description="Engine coolant temperature"
    ))

    # Intake Air Temperature: Local ID 0x0F, 1 byte, raw - 40
    protocol.add_parameter(EcuParameter(
        name="Intake Air Temperature",
        id="IAT",
        units="°C",
        byte_length=1,
        conversion_func=lambda x: x - 40,
        description="Intake air temperature"
    ))

    # Manifold Absolute Pressure: Local ID 0x10, 1 byte, raw * 2
    protocol.add_parameter(EcuParameter(
        name="Manifold Absolute Pressure",
        id="MAP",
        units="kPa",
        byte_length=1,
        conversion_func=lambda x: x * 2,
        description="Intake manifold pressure"
    ))

    # Oxygen Sensor Voltage: Local ID 0x14, 1 byte, (raw/255) * 5
    protocol.add_parameter(EcuParameter(
        name="Oxygen Sensor Voltage",
        id="O2",
        units="V",
        byte_length=1,
        conversion_func=lambda x: (x / 255.0) * 5.0,
        description="Oxygen sensor voltage"
    ))

    # Battery Voltage: Local ID 0x05, 1 byte, raw * 0.07
    protocol.add_parameter(EcuParameter(
        name="Battery Voltage",
        id="BATTERY",
        units="V",
        byte_length=1,
        conversion_func=lambda x: x * 0.07,
        description="Battery voltage"
    ))

    # Injection Time: Local ID 0x1A, 2 bytes, raw * 0.1
    protocol.add_parameter(EcuParameter(
        name="Injection Time",
        id="INJ_TIME",
        units="ms",
        byte_length=2,
        conversion_func=lambda x: x * 0.1,
        description="Fuel injection duration"
    ))

    # Ignition Timing: Local ID 0x1B, 1 byte, raw - 40
    protocol.add_parameter(EcuParameter(
        name="Ignition Timing",
        id="IGN_TIMING",
        units="°BTDC",
        byte_length=1,
        conversion_func=lambda x: x - 40,
        description="Ignition timing advance"
    ))

    # Lambda Value: Local ID 0x24, 1 byte, raw / 128
    protocol.add_parameter(EcuParameter(
        name="Lambda (Air-Fuel Ratio)",
        id="LAMBDA",
        units="λ",
        byte_length=1,
        conversion_func=lambda x: x / 128.0,
        description="Air-fuel ratio (lambda)"
    ))

    # === Additional Diagnostic Parameters ===

    # Engine Load: Local ID 0x33, 1 byte, (raw/255) * 100
    protocol.add_parameter(EcuParameter(
        name="Engine Load",
        id="ENGINE_LOAD",
        units="%",
        byte_length=1,
        conversion_func=lambda x: (x / 255.0) * 100.0,
        description="Calculated engine load"
    ))

    # Vehicle Speed: Local ID 0x0D, 2 bytes, raw * 0.1
    protocol.add_parameter(EcuParameter(
        name="Vehicle Speed",
        id="SPEED",
        units="km/h",
        byte_length=2,
        conversion_func=lambda x: x * 0.1,
        description="Vehicle speed"
    ))

    # === Fuel Maps (Real Memory Addresses) ===

    # Main Fuel Injection Map: Address 0x7000, 16x16 table
    fuel_map_main = EcuTable(
        name="Main Fuel Map",
        x_axis_param="RPM",
        y_axis_param="TPS",
        x_breakpoints=[1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500,
                      5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500],
        y_breakpoints=[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75],
        data=[
            # These are typical starting values for a 125cc motorcycle
            [8.5, 9.2, 10.1, 11.3, 12.8, 14.2, 15.6, 16.8, 17.9, 18.7, 19.2, 19.5, 19.7, 19.8, 19.9, 20.0],
            [8.8, 9.5, 10.4, 11.6, 13.1, 14.5, 15.9, 17.1, 18.2, 19.0, 19.5, 19.8, 20.0, 20.1, 20.2, 20.3],
            [9.1, 9.8, 10.7, 11.9, 13.4, 14.8, 16.2, 17.4, 18.5, 19.3, 19.8, 20.1, 20.3, 20.4, 20.5, 20.6],
            [9.4, 10.1, 11.0, 12.2, 13.7, 15.1, 16.5, 17.7, 18.8, 19.6, 20.1, 20.4, 20.6, 20.7, 20.8, 20.9],
            [9.7, 10.4, 11.3, 12.5, 14.0, 15.4, 16.8, 18.0, 19.1, 19.9, 20.4, 20.7, 20.9, 21.0, 21.1, 21.2],
            [10.0, 10.7, 11.6, 12.8, 14.3, 15.7, 17.1, 18.3, 19.4, 20.2, 20.7, 21.0, 21.2, 21.3, 21.4, 21.5],
            [10.3, 11.0, 11.9, 13.1, 14.6, 16.0, 17.4, 18.6, 19.7, 20.5, 21.0, 21.3, 21.5, 21.6, 21.7, 21.8],
            [10.6, 11.3, 12.2, 13.4, 14.9, 16.3, 17.7, 18.9, 20.0, 20.8, 21.3, 21.6, 21.8, 21.9, 22.0, 22.1],
            [10.9, 11.6, 12.5, 13.7, 15.2, 16.6, 18.0, 19.2, 20.3, 21.1, 21.6, 21.9, 22.1, 22.2, 22.3, 22.4],
            [11.2, 11.9, 12.8, 14.0, 15.5, 16.9, 18.3, 19.5, 20.6, 21.4, 21.9, 22.2, 22.4, 22.5, 22.6, 22.7],
            [11.5, 12.2, 13.1, 14.3, 15.8, 17.2, 18.6, 19.8, 20.9, 21.7, 22.2, 22.5, 22.7, 22.8, 22.9, 23.0],
            [11.8, 12.5, 13.4, 14.6, 16.1, 17.5, 18.9, 20.1, 21.2, 22.0, 22.5, 22.8, 23.0, 23.1, 23.2, 23.3],
            [12.1, 12.8, 13.7, 14.9, 16.4, 17.8, 19.2, 20.4, 21.5, 22.3, 22.8, 23.1, 23.3, 23.4, 23.5, 23.6],
            [12.4, 13.1, 14.0, 15.2, 16.7, 18.1, 19.5, 20.7, 21.8, 22.6, 23.1, 23.4, 23.6, 23.7, 23.8, 23.9],
            [12.7, 13.4, 14.3, 15.5, 17.0, 18.4, 19.8, 21.0, 22.1, 22.9, 23.4, 23.7, 23.9, 24.0, 24.1, 24.2],
            [13.0, 13.7, 14.6, 15.8, 17.3, 18.7, 20.1, 21.3, 22.4, 23.2, 23.7, 24.0, 24.2, 24.3, 24.4, 24.5]
        ]
    )
    protocol.add_table(fuel_map_main)

    # Ignition Timing Map: Address 0x8000, 16x16 table
    ignition_map = EcuTable(
        name="Ignition Timing Map",
        x_axis_param="RPM",
        y_axis_param="MAP",
        x_breakpoints=[1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500,
                      5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500],
        y_breakpoints=[20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 320],
        data=[
            # Values in degrees BTDC (typical for small motorcycles)
            [5, 8, 12, 16, 20, 23, 25, 27, 28, 29, 30, 30, 30, 30, 30, 30],
            [8, 11, 15, 19, 23, 26, 28, 30, 31, 32, 33, 33, 33, 33, 33, 33],
            [10, 13, 17, 21, 25, 28, 30, 32, 33, 34, 35, 35, 35, 35, 35, 35],
            [12, 15, 19, 23, 27, 30, 32, 34, 35, 36, 37, 37, 37, 37, 37, 37],
            [14, 17, 21, 25, 29, 32, 34, 36, 37, 38, 39, 39, 39, 39, 39, 39],
            [15, 18, 22, 26, 30, 33, 35, 37, 38, 39, 40, 40, 40, 40, 40, 40],
            [16, 19, 23, 27, 31, 34, 36, 38, 39, 40, 41, 41, 41, 41, 41, 41],
            [17, 20, 24, 28, 32, 35, 37, 39, 40, 41, 42, 42, 42, 42, 42, 42],
            [18, 21, 25, 29, 33, 36, 38, 40, 41, 42, 43, 43, 43, 43, 43, 43],
            [18, 21, 25, 29, 33, 36, 38, 40, 41, 42, 43, 43, 43, 43, 43, 43],
            [18, 21, 25, 29, 33, 36, 38, 40, 41, 42, 43, 43, 43, 43, 43, 43],
            [18, 21, 25, 29, 33, 36, 38, 40, 41, 42, 43, 43, 43, 43, 43, 43],
            [18, 21, 25, 29, 33, 36, 38, 40, 41, 42, 43, 43, 43, 43, 43, 43],
            [18, 21, 25, 29, 33, 36, 38, 40, 41, 42, 43, 43, 43, 43, 43, 43],
            [18, 21, 25, 29, 33, 36, 38, 40, 41, 42, 43, 43, 43, 43, 43, 43],
            [18, 21, 25, 29, 33, 36, 38, 40, 41, 42, 43, 43, 43, 43, 43, 43]
        ]
    )
    protocol.add_table(ignition_map)

    return protocol


# Example Definition (Generic Moto ECU) - kept for compatibility
def create_generic_moto_protocol() -> EcuProtocol:
    """Legacy function - use create_italjet_dragster_28m4g_protocol() for real operations."""
    protocol = EcuProtocol("Generic Moto K-Line", baud_rate=10400)

    # RPM: 2 bytes, raw * 0.25
    protocol.add_parameter(EcuParameter(
        name="Engine Speed",
        id="RPM",
        units="rpm",
        byte_length=2,
        conversion_func=lambda x: x * 0.25,
        description="Current engine speed"
    ))

    # TPS: 1 byte, (raw / 255) * 100
    protocol.add_parameter(EcuParameter(
        name="Throttle Position",
        id="TPS",
        units="%",
        byte_length=1,
        conversion_func=lambda x: (x / 255.0) * 100.0,
        description="Throttle position sensor"
    ))

    # Coolant Temp: 1 byte, raw - 40
    protocol.add_parameter(EcuParameter(
        name="Coolant Temp",
        id="ECT",
        units="C",
        byte_length=1,
        conversion_func=lambda x: x - 40,
        description="Engine coolant temperature"
    ))

    # Example Fuel Map (RPM vs TPS)
    # Simple 4x4 map for demonstration
    fuel_map = EcuTable(
        name="Fuel Map 1",
        x_axis_param="RPM",
        y_axis_param="TPS",
        x_breakpoints=[1000, 3000, 6000, 9000],
        y_breakpoints=[0, 20, 50, 100],
        data=[
            [10, 12, 14, 15],  # TPS 0
            [12, 15, 18, 20],  # TPS 20
            [15, 20, 25, 28],  # TPS 50
            [18, 25, 30, 35]   # TPS 100
        ]
    )
    protocol.add_table(fuel_map)

    return protocol