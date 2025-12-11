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

# Example Definition (Generic Moto ECU)
def create_generic_moto_protocol() -> EcuProtocol:
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