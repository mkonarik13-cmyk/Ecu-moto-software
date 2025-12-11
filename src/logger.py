import time
import serial
import threading
import random
import pandas as pd
from typing import List, Dict, Optional
from .ecu_definition import EcuProtocol, EcuParameter

class MockSerial:
    """Simulates a serial connection for testing without an ECU."""
    def __init__(self):
        self.is_open = True
        
    def write(self, data):
        pass  # Simulate sending request
        
    def read(self, size):
        # Return random bytes to simulate ECU response
        return bytes([random.randint(0, 255) for _ in range(size)])
        
    def close(self):
        self.is_open = False

class EcuLogger:
    def __init__(self, protocol: EcuProtocol, port: str = "COM1", use_mock: bool = False):
        self.protocol = protocol
        self.port = port
        self.use_mock = use_mock
        self.serial: Optional[serial.Serial] = None
        self.is_logging = False
        self.log_data: List[Dict] = []
        self.selected_params: List[str] = []
        self._thread: Optional[threading.Thread] = None

    def connect(self):
        """Establishes connection to the ECU."""
        if self.use_mock:
            print(f"Connecting to MOCK ECU on {self.port}...")
            self.serial = MockSerial()
        else:
            print(f"Connecting to ECU on {self.port} at {self.protocol.baud_rate} baud...")
            try:
                self.serial = serial.Serial(
                    self.port, 
                    self.protocol.baud_rate, 
                    timeout=0.1
                )
            except serial.SerialException as e:
                print(f"Connection failed: {e}")
                raise

    def start_logging(self, param_ids: List[str], interval: float = 0.1):
        """Starts the logging loop in a separate thread."""
        if not self.serial:
            raise Exception("Not connected to ECU")
            
        self.selected_params = param_ids
        self.is_logging = True
        self.log_data = []
        
        self._thread = threading.Thread(target=self._logging_loop, args=(interval,))
        self._thread.daemon = True
        self._thread.start()
        print("Logging started...")

    def stop_logging(self):
        """Stops the logging loop."""
        self.is_logging = False
        if self._thread:
            self._thread.join()
        print("Logging stopped.")

    def _logging_loop(self, interval: float):
        """Main loop that queries the ECU and records data."""
        start_time = time.time()
        
        while self.is_logging:
            loop_start = time.time()
            timestamp = loop_start - start_time
            
            row = {"timestamp": timestamp}
            
            # In a real K-Line/CAN scenario, you might construct a single request packet
            # containing all PIDs, or request them sequentially.
            # Here we simulate sequential requests for simplicity.
            
            for pid in self.selected_params:
                param = self.protocol.get_parameter(pid)
                if not param:
                    continue
                
                # 1. Send Request (Implementation depends on specific protocol, e.g., KWP2000, ISO9141)
                # self.serial.write(build_request(param.id))
                
                # 2. Read Response
                raw_bytes = self.serial.read(param.byte_length)
                
                if len(raw_bytes) == param.byte_length:
                    # Convert bytes to integer
                    raw_val = int.from_bytes(raw_bytes, byteorder='big')
                    # Apply conversion formula
                    phys_val = param.conversion_func(raw_val)
                    row[param.name] = phys_val
                else:
                    row[param.name] = None

            self.log_data.append(row)
            
            # Maintain sampling rate
            elapsed = time.time() - loop_start
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)

    def save_to_csv(self, filename: str):
        """Saves the recorded session to a CSV file."""
        if not self.log_data:
            print("No data to save.")
            return
            
        df = pd.DataFrame(self.log_data)
        df.to_csv(filename, index=False)
        print(f"Log saved to {filename}")
        
    def get_latest_data(self) -> Optional[Dict]:
        """Returns the most recent data point for UI display."""
        if self.log_data:
            return self.log_data[-1]
        return None