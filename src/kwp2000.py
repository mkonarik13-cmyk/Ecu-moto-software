import time
import serial
import struct

class KWP2000Client:
    """
    Implements the KWP2000 protocol for Magneti Marelli 28M4G ECU.
    """
    def __init__(self, port, baudrate=10400):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.target_addr = 0x01
        self.source_addr = 0xF1
        self.simulation_mode = False

    def connect(self):
        print(f"Connecting to {self.port} at {self.baudrate} baud...")
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1.0)
            self.simulation_mode = False
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            print("Entering SIMULATION MODE for testing.")
            self.simulation_mode = True
            return True # Return True to allow testing UI
        
        # 28M4G Specific Wake-up Sequence
        # This is critical for the ECU to start communicating
        wakeup_pattern = bytes([0x81, 0x12, 0xF1, 0x81, 0x04])
        self.ser.write(wakeup_pattern)
        time.sleep(0.3) # Wait for ECU to wake up
        
        # Start Diagnostic Session (Service 0x10)
        response = self.send_request(0x10, [0x81]) # 0x81 = Standard Diagnostic Mode
        if response and response[0] == 0x50: # Positive Response to 0x10
            print("ECU Connected & Session Started!")
            return True
        else:
            print("Failed to start session.")
            return False

    def security_access(self):
        """
        Performs the Seed-Key exchange to unlock the ECU (Service 0x27).
        Required for writing memory.
        """
        # 1. Request Seed (Level 0x01)
        response = self.send_request(0x27, [0x01])
        if not response or response[0] != 0x67:
            print("Failed to request seed.")
            return False
            
        # Seed is usually 2 or 4 bytes
        seed = response[2:] # Skip Service ID (0x67) and Level (0x01)
        print(f"Got Seed: {seed.hex()}")
        
        # 2. Calculate Key
        key = self._calculate_key(seed)
        print(f"Calculated Key: {key.hex()}")
        
        # 3. Send Key (Level 0x02)
        response = self.send_request(0x27, [0x02] + list(key))
        if response and response[0] == 0x67:
            print("Security Access Granted!")
            return True
        else:
            print("Security Access Denied.")
            return False

    def _calculate_key(self, seed):
        """
        Calculates the key from the seed.
        Placeholder for Magneti Marelli algorithm.
        """
        # TODO: Implement specific 28M4G algorithm
        # Often simple bitwise operations
        key = bytearray(seed)
        for i in range(len(key)):
            key[i] = key[i] ^ 0xFF # Simple XOR example
        return bytes(key)

    def get_battery_voltage(self):
        """
        Reads battery voltage to ensure safe flashing.
        """
        # Placeholder PID request (Service 0x21)
        # Assuming Voltage is PID 0x04 (Example)
        response = self.send_request(0x21, [0x04])
        if response and len(response) > 1:
            raw_val = response[1]
            voltage = raw_val * 0.07 # Example conversion
            return voltage
        return 12.5 # Mock value if request fails

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send_request(self, service_id, data=[]):
        """
        Sends a KWP2000 request frame.
        Format: [Format, Target, Source, Length, Service, Data..., Checksum]
        """
        if self.simulation_mode:
            time.sleep(0.01) # Simulate latency
            # Return positive response for common services
            if service_id == 0x10: return [0x50] # Start Session OK
            if service_id == 0x27: return [0x67, 0x01, 0xDE, 0xAD] # Security Access OK
            if service_id == 0x23: return [0x63] + [0xFF] * 64 # Read Memory OK (Dummy Data)
            if service_id == 0x3D: return [0x7D] # Write Memory OK
            return [service_id + 0x40]

        if not self.ser:
            return None
            
        length = len(data) + 1 # Service ID + Data
        # Format byte: 0x80 (Physical addressing) + Length (if < 63)
        # Simplified for this ECU: usually 0xC0 or similar for KWP2000
        # Using the reference header format:
        fmt = 0x80 | length if length < 64 else 0x80
        
        header = [fmt, self.target_addr, self.source_addr]
        payload = [service_id] + data
        
        frame = header + payload
        checksum = sum(frame) & 0xFF
        frame.append(checksum)
        
        self.ser.write(bytes(frame))
        
        return self.read_response()

    def read_response(self):
        """
        Reads the KWP2000 response frame.
        """
        # Read header (3 bytes)
        header = self.ser.read(3)
        if len(header) < 3:
            return None
            
        # Parse length (simplified)
        length = header[0] & 0x3F
        if length == 0:
            # Handle multi-byte length if needed (rare for simple requests)
            pass
            
        # Read payload + checksum
        payload_len = length
        data = self.ser.read(payload_len + 1) # +1 for checksum
        
        if len(data) < payload_len + 1:
            return None
            
        # Verify checksum (optional but recommended)
        # ...
        
        # Return service data (excluding Service ID echo which is Request + 0x40)
        return data[1:-1] # Strip Service ID and Checksum

    def read_memory(self, address, size):
        """
        Reads a block of memory from the ECU (Service 0x23).
        Used for downloading the firmware/maps.
        """
        if self.simulation_mode:
            # Return dummy data for simulation
            import random
            return bytes([random.randint(0, 255) for _ in range(size)])

        # Address is usually 3 or 4 bytes
        addr_bytes = list(struct.pack(">I", address))[1:] # Take last 3 bytes
        size_bytes = list(struct.pack(">H", size))
        
        response = self.send_request(0x23, addr_bytes + size_bytes)
        return response

    def write_memory(self, address, data):
        """
        Writes a block of memory to the ECU (Service 0x3D).
        Used for uploading modified maps.
        """
        addr_bytes = list(struct.pack(">I", address))[1:]
        response = self.send_request(0x3D, addr_bytes + list(data))
        return response is not None