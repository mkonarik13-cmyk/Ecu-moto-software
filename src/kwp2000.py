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

    def connect(self):
        print(f"Connecting to {self.port} at {self.baudrate} baud...")
        self.ser = serial.Serial(self.port, self.baudrate, timeout=1.0)
        
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

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send_request(self, service_id, data=[]):
        """
        Sends a KWP2000 request frame.
        Format: [Format, Target, Source, Length, Service, Data..., Checksum]
        """
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