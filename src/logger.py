import time
import threading
import pandas as pd
from typing import List, Dict, Optional
from .ecu_definition import EcuProtocol, EcuParameter
from .kwp2000 import KWP2000Client

class EcuLogger:
    def __init__(self, protocol: EcuProtocol, kwp_client: KWP2000Client):
        self.protocol = protocol
        self.kwp_client = kwp_client
        self.is_logging = False
        self.log_data: List[Dict] = []
        self.selected_params: List[str] = []
        self._thread: Optional[threading.Thread] = None

    def connect(self):
        """Establishes connection to the ECU via KWP Client."""
        # Connection is handled by KWP client externally or here
        if not self.kwp_client.ser and not self.kwp_client.simulation_mode:
            return self.kwp_client.connect()
        return True

    def start_logging(self, param_ids: List[str], interval: float = 0.1):
        """Starts the logging loop in a separate thread."""
        # Check if connected (either real or simulation)
        if not self.kwp_client.ser and not self.kwp_client.simulation_mode:
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
            
            for pid_name in self.selected_params:
                param = self.protocol.get_parameter(pid_name)
                if not param:
                    continue
                
                # Map parameter ID (e.g., "RPM") to KWP2000 Local ID (e.g., 0x0C)
                # For now, we'll assume the ID in definition is the Local ID if it's hex-like
                # Or we need a mapping. Let's assume param.id is the Local ID for KWP2000
                try:
                    # If param.id is "RPM", we need a mapping.
                    # For this fix, let's assume we use a hardcoded mapping or update definition later.
                    # Using a simple mapping for demo:
                    local_id = 0x00
                    if param.id == "RPM": local_id = 0x0C
                    elif param.id == "TPS": local_id = 0x11
                    elif param.id == "ECT": local_id = 0x04
                    
                    # Send KWP2000 Request (Service 0x21)
                    response = self.kwp_client.send_request(0x21, [local_id])
                    
                    if response and response[0] == 0x61:
                        raw_bytes = bytes(response[2:]) # Skip Service(61) + PID
                        if raw_bytes:
                            raw_val = int.from_bytes(raw_bytes, byteorder='big')
                            phys_val = param.conversion_func(raw_val)
                            row[param.name] = phys_val
                        else:
                            row[param.name] = None
                    else:
                        row[param.name] = None
                except Exception as e:
                    print(f"Error logging {param.name}: {e}")
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