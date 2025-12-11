"""
Hardware detection and K-Line adapter management for ECU tuning software.
Detects compatible K-Line OBDII adapters and provides hardware validation.
"""
import serial
import serial.tools.list_ports
from typing import List, Optional, Dict
from dataclasses import dataclass

@dataclass
class KLineAdapter:
    """Represents a detected K-Line adapter."""
    port: str
    name: str
    vid: int
    pid: int
    description: str

class HardwareDetector:
    """Detects and validates K-Line adapters for ECU communication."""

    # Known K-Line adapter VID/PID combinations
    COMPATIBLE_ADAPTERS = {
        # FTDI USB Serial adapters (common for K-Line)
        (0x0403, 0x6001): "FTDI USB Serial (VAG-COM compatible)",
        (0x0403, 0x6001): "FTDI USB-Serial Converter",
        (0x0403, 0x8A28): "FTDI USB-Serial Cable",

        # Prolific adapters (less common for K-Line)
        (0x067B, 0x2303): "Prolific PL2303 Serial Adapter",

        # Silicon Labs adapters
        (0x10C4, 0xEA60): "Silicon Labs CP210x UART",

        # CH340 adapters (common with cheap cables)
        (0x1A86, 0x7523): "CH340 USB to Serial",

        # Custom automotive adapters
        (0x0403, 0xC630): "VAG-COM KKL 409.1",
        (0x0403, 0xC631): "VAG-COM KKL 409.2",
    }

    def __init__(self):
        self.detected_adapters: List[KLineAdapter] = []
        self.selected_adapter: Optional[KLineAdapter] = None

    def scan_adapters(self) -> List[KLineAdapter]:
        """Scan for all compatible K-Line adapters on the system."""
        self.detected_adapters = []
        ports = serial.tools.list_ports.comports()

        for port in ports:
            # Check if this port matches known K-Line adapters
            adapter_key = (port.vid, port.pid) if port.vid and port.pid else None

            if adapter_key in self.COMPATIBLE_ADAPTERS:
                adapter_name = self.COMPATIBLE_ADAPTERS[adapter_key]
                adapter = KLineAdapter(
                    port=port.device,
                    name=adapter_name,
                    vid=port.vid,
                    pid=port.pid,
                    description=port.description or f"{adapter_name} on {port.device}"
                )
                self.detected_adapters.append(adapter)
            else:
                # Include potential serial adapters with manufacturer info
                if port.description and any(keyword in port.description.lower()
                    for keyword in ['k-line', 'obd', 'diagnostic', 'ecu', 'vag']):
                    adapter = KLineAdapter(
                        port=port.device,
                        name=f"Unknown Adapter: {port.description}",
                        vid=port.vid or 0,
                        pid=port.pid or 0,
                        description=port.description
                    )
                    self.detected_adapters.append(adapter)

        return self.detected_adapters

    def get_best_adapter(self) -> Optional[KLineAdapter]:
        """Select the most suitable adapter from detected devices."""
        if not self.detected_adapters:
            return None

        # Prioritize known VAG-COM adapters
        for adapter in self.detected_adapters:
            if "VAG-COM" in adapter.name:
                return adapter

        # Then prioritize FTDI adapters
        for adapter in self.detected_adapters:
            if adapter.vid == 0x0403:  # FTDI
                return adapter

        # Return first available adapter
        return self.detected_adapters[0]

    def test_connection(self, adapter: KLineAdapter, baudrate: int = 10400) -> bool:
        """Test if we can open a connection to the adapter."""
        try:
            with serial.Serial(adapter.port, baudrate, timeout=2.0) as ser:
                # Test if we can write to the port
                ser.write(bytes([0x00]))
                return True
        except (serial.SerialException, serial.SerialTimeoutException):
            return False
        except Exception:
            return False

    def select_adapter(self, adapter: KLineAdapter) -> bool:
        """Select an adapter for ECU communication."""
        if self.test_connection(adapter):
            self.selected_adapter = adapter
            return True
        return False

    def get_adapter_info(self) -> Dict[str, str]:
        """Get information about the selected adapter."""
        if not self.selected_adapter:
            return {"status": "No adapter selected"}

        return {
            "status": "Connected",
            "port": self.selected_adapter.port,
            "name": self.selected_adapter.name,
            "description": self.selected_adapter.description,
            "vid": f"0x{self.selected_adapter.vid:04X}",
            "pid": f"0x{self.selected_adapter.pid:04X}"
        }

    def auto_detect_and_connect(self) -> bool:
        """Automatically detect and connect to the best available adapter."""
        adapters = self.scan_adapters()

        if not adapters:
            print("No K-Line adapters found.")
            return False

        best_adapter = self.get_best_adapter()
        if best_adapter:
            success = self.select_adapter(best_adapter)
            if success:
                print(f"Auto-connected to {best_adapter.name} on {best_adapter.port}")
                return True
            else:
                print(f"Failed to connect to {best_adapter.name}")

        return False

    def validate_hardware_setup(self) -> tuple[bool, str]:
        """Validate that the hardware setup is suitable for ECU communication."""
        if not self.selected_adapter:
            return False, "No K-Line adapter selected"

        if not self.test_connection(self.selected_adapter):
            return False, f"Cannot communicate with adapter on {self.selected_adapter.port}"

        # Additional validation could include checking adapter capabilities
        # but basic connectivity is the most important check

        return True, f"Hardware OK: {self.selected_adapter.name} on {self.selected_adapter.port}"


def detect_kline_adapters() -> List[KLineAdapter]:
    """Convenience function to detect K-Line adapters."""
    detector = HardwareDetector()
    return detector.scan_adapters()


def auto_connect_adapter() -> Optional[KLineAdapter]:
    """Convenience function to auto-detect and connect to best adapter."""
    detector = HardwareDetector()
    if detector.auto_detect_and_connect():
        return detector.selected_adapter
    return None