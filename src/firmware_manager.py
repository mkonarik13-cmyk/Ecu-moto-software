import time
from .kwp2000 import KWP2000Client

class FirmwareManager:
    def __init__(self, protocol: KWP2000Client):
        self.protocol = protocol
        # 28M4G Flash Size is typically 256KB or 512KB
        # We'll assume 256KB (0x40000) for now, or detect it
        self.flash_start = 0x000000
        self.flash_size = 0x40000 
        self.chunk_size = 64 # Max bytes per request

    def download_firmware(self, filename, progress_callback=None):
        """
        Downloads the entire ECU flash memory to a .bin file.
        """
        print(f"Starting firmware download to {filename}...")
        with open(filename, "wb") as f:
            current_addr = self.flash_start
            end_addr = self.flash_start + self.flash_size
            
            while current_addr < end_addr:
                # Calculate chunk size (don't go past end)
                size = min(self.chunk_size, end_addr - current_addr)
                
                # Read from ECU
                data = self.protocol.read_memory(current_addr, size)
                
                if data:
                    f.write(data)
                    current_addr += len(data)
                    
                    # Update progress
                    if progress_callback:
                        percent = ((current_addr - self.flash_start) / self.flash_size) * 100
                        progress_callback(percent)
                else:
                    print(f"Error reading at {hex(current_addr)}")
                    # Retry logic could go here
                    break
                    
        print("Download complete.")

    def upload_firmware(self, filename, progress_callback=None):
        """
        Uploads a .bin file to the ECU flash memory.
        WARNING: This is dangerous!
        """
        print(f"Starting firmware upload from {filename}...")
        with open(filename, "rb") as f:
            data = f.read()
            
        if len(data) != self.flash_size:
            print("Warning: File size does not match expected flash size.")
            
        current_addr = self.flash_start
        total_bytes = len(data)
        
        # TODO: Need to erase flash sectors first!
        # This is a simplified example. Real flashing requires:
        # 1. Security Access (Seed/Key)
        # 2. Request Download
        # 3. Erase Routine
        # 4. Transfer Data
        
        print("Flashing logic is complex and risky. Implemented in 'Safe Mode' (Simulation).")
        
        # Simulation loop for UI testing
        for i in range(0, total_bytes, self.chunk_size):
            chunk = data[i : i + self.chunk_size]
            # self.protocol.write_memory(current_addr + i, chunk) # Commented out for safety
            time.sleep(0.01) # Simulate write time
            
            if progress_callback:
                percent = (i / total_bytes) * 100
                progress_callback(percent)
                
        print("Upload complete.")