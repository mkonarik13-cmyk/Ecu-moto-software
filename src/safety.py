"""
Safety module for ECU tuning operations.
Provides comprehensive safety checks and interlocks for critical operations.
"""
import time
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

class SafetyLevel(Enum):
    """Safety level for operations."""
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"

@dataclass
class SafetyCheck:
    """Result of a safety check."""
    level: SafetyLevel
    message: str
    recommendation: Optional[str] = None
    can_proceed: bool = True

class SafetyManager:
    """Manages safety checks and interlocks for ECU operations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.safety_log: List[dict] = []
        self.min_battery_voltage = 12.5  # Minimum voltage for flashing
        self.max_battery_voltage = 15.0  # Maximum safe voltage

    def log_safety_event(self, event_type: str, message: str, level: SafetyLevel = SafetyLevel.SAFE):
        """Log a safety-related event."""
        timestamp = time.time()
        log_entry = {
            "timestamp": timestamp,
            "type": event_type,
            "message": message,
            "level": level.value
        }
        self.safety_log.append(log_entry)

        # Also log to standard logger
        if level == SafetyLevel.CRITICAL:
            self.logger.critical(f"[{event_type}] {message}")
        elif level == SafetyLevel.DANGER:
            self.logger.error(f"[{event_type}] {message}")
        elif level == SafetyLevel.WARNING:
            self.logger.warning(f"[{event_type}] {message}")
        else:
            self.logger.info(f"[{event_type}] {message}")

    def check_battery_voltage(self, voltage: float) -> SafetyCheck:
        """Check if battery voltage is safe for operations."""
        if voltage < 11.0:
            return SafetyCheck(
                level=SafetyLevel.CRITICAL,
                message=f"Battery critically low: {voltage:.1f}V",
                recommendation="Connect battery charger immediately. Operation blocked.",
                can_proceed=False
            )
        elif voltage < self.min_battery_voltage:
            return SafetyCheck(
                level=SafetyLevel.DANGER,
                message=f"Battery voltage too low: {voltage:.1f}V (minimum {self.min_battery_voltage}V)",
                recommendation="Connect battery charger before proceeding.",
                can_proceed=False
            )
        elif voltage > 16.0:
            return SafetyCheck(
                level=SafetyLevel.CRITICAL,
                message=f"Battery voltage dangerously high: {voltage:.1f}V",
                recommendation="Check charging system. Risk of ECU damage.",
                can_proceed=False
            )
        elif voltage > self.max_battery_voltage:
            return SafetyCheck(
                level=SafetyLevel.WARNING,
                message=f"Battery voltage high: {voltage:.1f}V",
                recommendation="Monitor voltage. Avoid flashing if voltage increases.",
                can_proceed=True
            )
        else:
            return SafetyCheck(
                level=SafetyLevel.SAFE,
                message=f"Battery voltage OK: {voltage:.1f}V",
                can_proceed=True
            )

    def check_communication_stability(self, success_rate: float, total_attempts: int) -> SafetyCheck:
        """Check if communication with ECU is stable enough for operations."""
        if total_attempts < 10:
            return SafetyCheck(
                level=SafetyLevel.WARNING,
                message=f"Insufficient communication data: {total_attempts} attempts",
                recommendation="Establish stable communication before proceeding.",
                can_proceed=False
            )

        if success_rate < 0.8:
            return SafetyCheck(
                level=SafetyLevel.CRITICAL,
                message=f"Poor communication stability: {success_rate:.1%} success rate",
                recommendation="Check connections and try again. Operation blocked.",
                can_proceed=False
            )
        elif success_rate < 0.95:
            return SafetyCheck(
                level=SafetyLevel.WARNING,
                message=f"Unstable communication: {success_rate:.1%} success rate",
                recommendation="Communication may be unreliable. Proceed with caution.",
                can_proceed=True
            )
        else:
            return SafetyCheck(
                level=SafetyLevel.SAFE,
                message=f"Communication stable: {success_rate:.1%} success rate",
                can_proceed=True
            )

    def validate_firmware_for_flashing(self, firmware_data: bytes, expected_size: int) -> SafetyCheck:
        """Validate firmware data before flashing."""
        if not firmware_data:
            return SafetyCheck(
                level=SafetyLevel.CRITICAL,
                message="No firmware data provided",
                can_proceed=False
            )

        if len(firmware_data) != expected_size:
            size_diff = len(firmware_data) - expected_size
            return SafetyCheck(
                level=SafetyLevel.DANGER,
                message=f"Firmware size mismatch: {len(firmware_data)} bytes (expected {expected_size})",
                recommendation=f"Size differs by {size_diff} bytes. Verify correct firmware file.",
                can_proceed=False
            )

        # Check for obviously invalid firmware (all zeros or all ones)
        if all(b == 0x00 for b in firmware_data[:100]):
            return SafetyCheck(
                level=SafetyLevel.CRITICAL,
                message="Firmware appears to be all zeros (erased)",
                can_proceed=False
            )

        if all(b == 0xFF for b in firmware_data[:100]):
            return SafetyCheck(
                level=SafetyLevel.DANGER,
                message="Firmware appears to be erased (all 0xFF)",
                recommendation="Verify firmware file is not corrupted",
                can_proceed=False
            )

        return SafetyCheck(
            level=SafetyLevel.SAFE,
            message=f"Firmware validated: {len(firmware_data)} bytes",
            can_proceed=True
        )

    def check_flash_operation_safety(self, battery_voltage: float, comm_stability: float,
                                   firmware_valid: bool) -> Tuple[SafetyLevel, List[SafetyCheck]]:
        """Comprehensive safety check before flash operations."""
        checks = []

        # Battery voltage check
        voltage_check = self.check_battery_voltage(battery_voltage)
        checks.append(voltage_check)

        # Communication stability check
        comm_check = self.check_communication_stability(comm_stability, 10)
        checks.append(comm_check)

        # Firmware validation
        if not firmware_valid:
            checks.append(SafetyCheck(
                level=SafetyLevel.CRITICAL,
                message="Firmware validation failed",
                can_proceed=False
            ))

        # Determine overall safety level
        worst_level = SafetyLevel.SAFE
        for check in checks:
            if not check.can_proceed:
                worst_level = SafetyLevel.CRITICAL
                break
            elif check.level.value == "critical":
                worst_level = SafetyLevel.CRITICAL
            elif check.level.value == "danger" and worst_level != SafetyLevel.CRITICAL:
                worst_level = SafetyLevel.DANGER
            elif check.level.value == "warning" and worst_level == SafetyLevel.SAFE:
                worst_level = SafetyLevel.WARNING

        return worst_level, checks

    def create_backup_confirmation(self, backup_file: str) -> SafetyCheck:
        """Confirm that a backup has been created successfully."""
        import os

        if not os.path.exists(backup_file):
            return SafetyCheck(
                level=SafetyLevel.CRITICAL,
                message=f"Backup file not found: {backup_file}",
                recommendation="Create backup before proceeding with any modifications.",
                can_proceed=False
            )

        if os.path.getsize(backup_file) == 0:
            return SafetyCheck(
                level=SafetyLevel.CRITICAL,
                message=f"Backup file is empty: {backup_file}",
                recommendation="Backup failed. Create new backup before proceeding.",
                can_proceed=False
            )

        return SafetyCheck(
            level=SafetyLevel.SAFE,
            message=f"Backup confirmed: {backup_file} ({os.path.getsize(backup_file)} bytes)",
            can_proceed=True
        )

    def get_user_confirmation_for_critical_operation(self, operation: str, warnings: List[str]) -> bool:
        """Get user confirmation for critical operations (for interactive use)."""
        print(f"\n{'='*60}")
        print(f"CRITICAL OPERATION: {operation}")
        print(f"{'='*60}")

        for warning in warnings:
            print(f"⚠️  {warning}")

        print(f"\n{'='*60}")

        # This would be replaced with GUI confirmation in the actual application
        try:
            confirmation = input("\nType 'CONFIRM' to proceed with this operation: ").strip().upper()
            return confirmation == "CONFIRM"
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return False

    def log_critical_operation(self, operation: str, user: str = "unknown",
                             details: Optional[dict] = None):
        """Log a critical operation for audit trail."""
        log_entry = {
            "timestamp": time.time(),
            "operation": operation,
            "user": user,
            "details": details or {}
        }
        self.safety_log.append(log_entry)

        self.logger.info(f"Critical operation logged: {operation} by {user}")

    def get_safety_report(self) -> dict:
        """Get a summary of safety checks and recent events."""
        recent_events = self.safety_log[-10:]  # Last 10 events

        return {
            "total_safety_events": len(self.safety_log),
            "recent_events": recent_events,
            "safety_settings": {
                "min_battery_voltage": self.min_battery_voltage,
                "max_battery_voltage": self.max_battery_voltage
            }
        }


# Global safety manager instance
safety_manager = SafetyManager()


def check_battery_safety(voltage: float) -> SafetyCheck:
    """Convenience function for battery safety check."""
    return safety_manager.check_battery_voltage(voltage)


def validate_flash_safety(battery_voltage: float, comm_stability: float,
                        firmware_valid: bool) -> Tuple[SafetyLevel, List[SafetyCheck]]:
    """Convenience function for comprehensive flash safety check."""
    return safety_manager.check_flash_operation_safety(battery_voltage, comm_stability, firmware_valid)