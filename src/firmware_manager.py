import time
import os
from .kwp2000 import KWP2000Client
from .safety import safety_manager, SafetyLevel
from .backup_manager import backup_manager

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
        Includes retry logic for reliability.
        """
        print(f"Starting firmware download to {filename}...")
        try:
            with open(filename, "wb") as f:
                current_addr = self.flash_start
                end_addr = self.flash_start + self.flash_size
                
                while current_addr < end_addr:
                    # Calculate chunk size (don't go past end)
                    size = min(self.chunk_size, end_addr - current_addr)
                    
                    # Read from ECU with Retry
                    data = self._read_chunk_with_retry(current_addr, size)
                    
                    if data:
                        f.write(data)
                        current_addr += len(data)
                        
                        # Update progress
                        if progress_callback:
                            percent = ((current_addr - self.flash_start) / self.flash_size) * 100
                            progress_callback(percent)
                    else:
                        print(f"Critical Error reading at {hex(current_addr)}. Aborting.")
                        return False
                        
            print(f"Download complete. Saved to {filename}")
            return True
        except Exception as e:
            print(f"File error: {e}")
            return False

    def _read_chunk_with_retry(self, address, size, retries=3):
        for i in range(retries):
            data = self.protocol.read_memory(address, size)
            if data:
                return data
            print(f"Retry {i+1}/{retries} reading {hex(address)}")
            time.sleep(0.1)
        return None

    def upload_firmware(self, filename, progress_callback=None, enable_real_write=False):
        """
        Uploads a .bin file to the ECU flash memory with comprehensive safety checks.
        WARNING: Real flashing is only enabled when enable_real_write=True
        """
        # 1. Comprehensive Safety Validation
        print("Performing comprehensive safety checks...")

        # Check battery voltage
        voltage = self.protocol.get_battery_voltage()
        voltage_check = safety_manager.check_battery_voltage(voltage)

        if not voltage_check.can_proceed:
            safety_manager.log_safety_event("BATTERY_CHECK_FAILED", voltage_check.message, SafetyLevel.DANGER)
            print(f"SAFETY BLOCK: {voltage_check.message}")
            print(f"Recommendation: {voltage_check.recommendation}")
            return False

        # Check communication stability
        comm_stability = self.protocol.get_communication_stability()
        comm_check = safety_manager.check_communication_stability(comm_stability,
                                                                 self.protocol.communication_stats['total_requests'])

        if not comm_check.can_proceed:
            safety_manager.log_safety_event("COMMUNICATION_UNSTABLE", comm_check.message, SafetyLevel.DANGER)
            print(f"SAFETY BLOCK: {comm_check.message}")
            print(f"Recommendation: {comm_check.recommendation}")
            return False

        print(f"Safety checks passed: Battery {voltage:.1f}V, Communication {comm_stability:.1%}")

        # 2. Load and Validate Firmware File
        print(f"Loading firmware file: {filename}")
        try:
            with open(filename, "rb") as f:
                firmware_data = bytearray(f.read())
        except Exception as e:
            safety_manager.log_safety_event("FIRMWARE_LOAD_ERROR", str(e), SafetyLevel.CRITICAL)
            print(f"Error loading firmware file: {e}")
            return False

        # Validate firmware content
        firmware_check = safety_manager.validate_firmware_for_flashing(firmware_data, self.flash_size)
        if not firmware_check.can_proceed:
            safety_manager.log_safety_event("FIRMWARE_INVALID", firmware_check.message, SafetyLevel.CRITICAL)
            print(f"SAFETY BLOCK: {firmware_check.message}")
            return False

        # 3. Create Automatic Backup
        print("Creating automatic backup before flashing...")
        try:
            backup_metadata = backup_manager.create_backup(
                firmware_data=b"",  # We'll fill this with actual ECU data
                ecu_type="28M4G",
                description=f"Pre-flash backup before uploading {os.path.basename(filename)}"
            )

            # Download current firmware as backup
            backup_filename = backup_metadata.filename
            if not self.download_firmware(backup_manager.backup_directory / backup_filename, progress_callback):
                safety_manager.log_safety_event("BACKUP_FAILED", "Failed to create pre-flash backup", SafetyLevel.CRITICAL)
                print("CRITICAL: Backup creation failed. Aborting flash operation.")
                return False

            print(f"Backup created: {backup_filename}")

        except Exception as e:
            safety_manager.log_safety_event("BACKUP_ERROR", str(e), SafetyLevel.CRITICAL)
            print(f"Error creating backup: {e}")
            return False

        # 4. Comprehensive Flash Safety Check
        overall_safety_level, safety_checks = safety_manager.check_flash_operation_safety(
            battery_voltage=voltage,
            comm_stability=comm_stability,
            firmware_valid=True
        )

        if overall_safety_level in [SafetyLevel.DANGER, SafetyLevel.CRITICAL]:
            print("CRITICAL SAFETY WARNINGS DETECTED:")
            for check in safety_checks:
                if check.level in [SafetyLevel.DANGER, SafetyLevel.CRITICAL]:
                    print(f"  ⚠️  {check.message}")
                    if check.recommendation:
                        print(f"     💡 {check.recommendation}")

            # Get user confirmation for dangerous operations
            warnings = [check.message for check in safety_checks if not check.can_proceed]
            if not safety_manager.get_user_confirmation_for_critical_operation("FIRMWARE FLASH", warnings):
                print("Operation cancelled by user.")
                return False

        # 5. Security Access
        print("Obtaining security access...")
        if not self.protocol.security_access():
            safety_manager.log_safety_event("SECURITY_ACCESS_FAILED", "Unable to unlock ECU", SafetyLevel.CRITICAL)
            print("CRITICAL: Security access failed. Cannot flash firmware.")
            return False

        # 6. Prepare Firmware Data
        print("Preparing firmware data...")
        self._correct_checksum(firmware_data)

        # 7. Flash Operation
        if enable_real_write:
            print("WARNING: REAL FLASHING ENABLED - This will modify ECU firmware")
            return self._write_firmware_safe(firmware_data, progress_callback)
        else:
            print("FLASH SIMULATION MODE - No actual writing to ECU")
            return self._simulate_firmware_write(firmware_data, progress_callback)

    def _write_firmware_safe(self, firmware_data: bytearray, progress_callback=None) -> bool:
        """
        Actually write firmware to ECU with comprehensive safety checks.
        ONLY call this method when enable_real_write=True and all safety checks pass.
        """
        total_bytes = len(firmware_data)
        write_errors = []

        try:
            # Write in small chunks with verification
            for offset in range(0, total_bytes, self.chunk_size):
                chunk = firmware_data[offset:offset + self.chunk_size]
                current_addr = self.flash_start + offset

                # Write chunk
                write_success = self.protocol.write_memory(current_addr, chunk)
                if not write_success:
                    error_msg = f"Write failed at offset {hex(offset)}"
                    write_errors.append(error_msg)
                    safety_manager.log_safety_event("FLASH_WRITE_ERROR", error_msg, SafetyLevel.CRITICAL)
                    break

                # Verify chunk by reading back
                time.sleep(0.01)  # Small delay for ECU to process
                verification_data = self.protocol.read_memory(current_addr, len(chunk))

                if verification_data != bytes(chunk):
                    error_msg = f"Verification failed at offset {hex(offset)}"
                    write_errors.append(error_msg)
                    safety_manager.log_safety_event("FLASH_VERIFY_ERROR", error_msg, SafetyLevel.CRITICAL)
                    break

                # Update progress
                if progress_callback:
                    percent = ((offset + len(chunk)) / total_bytes) * 100
                    progress_callback(percent)

            if write_errors:
                print(f"Flash operation failed with {len(write_errors)} errors:")
                for error in write_errors:
                    print(f"  ❌ {error}")

                # Attempt rollback from backup
                print("Attempting rollback from backup...")
                latest_backup = backup_manager.get_latest_backup()
                if latest_backup:
                    try:
                        backup_data = backup_manager.restore_backup(latest_backup.filename)
                        if self._write_firmware_safe(backup_data, None):
                            print("✅ Rollback successful")
                        else:
                            print("❌ Rollback failed - ECU may be in unstable state")
                    except Exception as e:
                        print(f"❌ Rollback failed: {e}")

                return False
            else:
                safety_manager.log_safety_event("FLASH_SUCCESS", "Firmware written successfully", SafetyLevel.SAFE)
                print("✅ Flash operation completed successfully")
                return True

        except Exception as e:
            error_msg = f"Unexpected error during flash operation: {e}"
            safety_manager.log_safety_event("FLASH_ERROR", error_msg, SafetyLevel.CRITICAL)
            print(f"❌ {error_msg}")
            return False

    def _simulate_firmware_write(self, firmware_data: bytearray, progress_callback=None) -> bool:
        """
        Simulate firmware write operation for testing purposes.
        """
        print("Simulating flash write operation...")
        total_bytes = len(firmware_data)

        for i in range(0, total_bytes, self.chunk_size):
            # Simulate write time
            time.sleep(0.001)

            # Simulate occasional write failure for testing
            import random
            if random.random() < 0.001:  # 0.1% chance of simulated failure
                print(f"Simulated write failure at offset {hex(i)}")
                return False

            # Update progress
            if progress_callback:
                percent = ((i + self.chunk_size) / total_bytes) * 100
                progress_callback(min(percent, 100.0))

        print("✅ Flash simulation completed successfully")
        return True

    def _correct_checksum(self, data):
        """
        Calculates and updates the checksum in the firmware buffer.
        Magneti Marelli often uses a simple additive checksum or CRC.
        """
        # Placeholder: Calculate simple sum and store at end
        checksum = sum(data[:-4]) & 0xFFFFFFFF
        # In reality, we'd write this to a specific address
        print(f"Calculated Checksum: {hex(checksum)}")