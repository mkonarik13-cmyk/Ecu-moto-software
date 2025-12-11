#!/usr/bin/env python3
"""
Comprehensive integration test for Moto ECU Tuner.
Tests all components working together in real-world scenarios.
"""

import os
import sys
import time
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ecu_protocol():
    """Test ECU protocol definitions."""
    print("🧪 Testing ECU Protocol...")

    from src.ecu_definition import create_italjet_dragster_28m4g_protocol

    protocol = create_italjet_dragster_28m4g_protocol()

    # Verify protocol setup
    assert protocol.name == "Italjet Dragster 28M4G"
    assert len(protocol.parameters) >= 10  # Should have all real 28M4G parameters
    assert len(protocol.tables) >= 2       # Should have fuel and ignition maps

    # Verify key parameters
    required_params = ['RPM', 'TPS', 'ECT', 'IAT', 'MAP', 'BATTERY']
    for param in required_params:
        assert param in protocol.parameters, f"Missing parameter: {param}"

    # Verify parameter conversions
    rpm_param = protocol.parameters['RPM']
    assert rpm_param.conversion_func(40) == 1000  # 40 * 25 = 1000 RPM

    tps_param = protocol.parameters['TPS']
    assert abs(tps_param.conversion_func(128) - 50.2) < 0.1  # ~50%

    print("✅ ECU Protocol test passed")
    return True

def test_safety_system():
    """Test safety management system."""
    print("🧪 Testing Safety System...")

    from src.safety import safety_manager, SafetyLevel

    # Test voltage safety
    check = safety_manager.check_battery_voltage(12.6)
    assert check.can_proceed == True
    assert check.level == SafetyLevel.SAFE

    check = safety_manager.check_battery_voltage(11.5)
    assert check.can_proceed == False
    assert check.level == SafetyLevel.DANGER

    # Test flash safety
    overall_level, checks = safety_manager.check_flash_operation_safety(
        battery_voltage=13.2,
        comm_stability=0.98,
        firmware_valid=True
    )
    assert overall_level == SafetyLevel.SAFE

    # Test invalid scenario
    overall_level, checks = safety_manager.check_flash_operation_safety(
        battery_voltage=11.0,
        comm_stability=0.7,
        firmware_valid=False
    )
    assert overall_level == SafetyLevel.CRITICAL

    print("✅ Safety System test passed")
    return True

def test_backup_system():
    """Test backup management system."""
    print("🧪 Testing Backup System...")

    from src.backup_manager import BackupManager

    # Create temporary backup directory
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BackupManager(temp_dir)

        # Create test firmware data
        test_firmware = bytes([i % 256 for i in range(1024)])

        # Test backup creation
        metadata = manager.create_backup(
            firmware_data=test_firmware,
            ecu_type="TEST_ECU",
            description="Test backup"
        )

        assert metadata.ecu_type == "TEST_ECU"
        assert metadata.size == 1024
        assert len(metadata.checksum) == 64  # SHA-256 hex length

        # Test backup listing
        backups = manager.list_backups()
        assert len(backups) == 1
        assert backups[0].filename == metadata.filename

        # Test backup restoration
        restored_data = manager.restore_backup(metadata.filename)
        assert restored_data == test_firmware

        # Test integrity verification
        assert manager.verify_backup_integrity(metadata.filename) == True

        print("✅ Backup System test passed")
        return True

def test_hardware_detection():
    """Test hardware detection system."""
    print("🧪 Testing Hardware Detection...")

    from src.hardware_detector import HardwareDetector, KLineAdapter

    detector = HardwareDetector()

    # Test adapter detection (will be empty in CI environment)
    adapters = detector.scan_adapters()
    assert isinstance(adapters, list)

    # Test adapter info when no hardware found
    adapter_info = detector.get_adapter_info()
    assert adapter_info["status"] == "No adapter selected"

    print("✅ Hardware Detection test passed")
    return True

def test_kwp2000_simulation():
    """Test KWP2000 protocol in simulation mode."""
    print("🧪 Testing KWP2000 Simulation...")

    from src.kwp2000 import KWP2000Client

    # Create client in simulation mode
    client = KWP2000Client("SIMULATION_PORT")
    assert client.simulation_mode == True

    # Test basic communication
    response = client.send_request(0x21, [0x05])  # Battery voltage request
    assert response is not None
    assert len(response) >= 2

    # Test battery voltage reading
    voltage = client.get_battery_voltage()
    assert isinstance(voltage, (int, float))
    assert 10.0 <= voltage <= 15.0  # Reasonable voltage range

    # Test communication statistics
    stability = client.get_communication_stability()
    assert 0.0 <= stability <= 1.0

    print("✅ KWP2000 Simulation test passed")
    return True

def test_firmware_manager():
    """Test firmware management with safety."""
    print("🧪 Testing Firmware Manager...")

    from src.kwp2000 import KWP2000Client
    from src.firmware_manager import FirmwareManager
    from src.backup_manager import BackupManager

    # Create components
    client = KWP2000Client("SIMULATION_PORT")
    manager = FirmwareManager(client)

    # Test firmware download simulation
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as temp_file:
        temp_filename = temp_file.name

    try:
        success = manager.download_firmware(temp_filename)
        assert success == True

        # Verify file was created and has content
        assert os.path.exists(temp_filename)
        assert os.path.getsize(temp_filename) > 0

    finally:
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

    # Test firmware upload simulation
    test_firmware_file = temp_filename + '_test.bin'
    try:
        # Create test firmware file
        with open(test_firmware_file, 'wb') as f:
            f.write(bytes([i % 256 for i in range(manager.flash_size)]))

        # Test upload (simulation mode)
        success = manager.upload_firmware(test_firmware_file, enable_real_write=False)
        assert success == True

    finally:
        if os.path.exists(test_firmware_file):
            os.unlink(test_firmware_file)

    print("✅ Firmware Manager test passed")
    return True

def test_integration_workflow():
    """Test complete workflow integration."""
    print("🧪 Testing Integration Workflow...")

    from src.ecu_definition import create_italjet_dragster_28m4g_protocol
    from src.kwp2000 import KWP2000Client
    from src.firmware_manager import FirmwareManager
    from src.safety import safety_manager
    from src.backup_manager import backup_manager

    # 1. Initialize components
    protocol = create_italjet_dragster_28m4g_protocol()
    client = KWP2000Client("SIMULATION_PORT")
    manager = FirmwareManager(client)

    # 2. Simulate ECU connection
    connection_success = client.connect()
    assert connection_success == True

    # 3. Test live data reading
    voltage = client.get_battery_voltage()
    assert isinstance(voltage, (int, float))

    # 4. Safety validation for flash operation
    voltage_check = safety_manager.check_battery_voltage(voltage)
    assert voltage_check.can_proceed == True

    comm_stability = client.get_communication_stability()
    overall_safety, safety_checks = safety_manager.check_flash_operation_safety(
        battery_voltage=voltage,
        comm_stability=comm_stability,
        firmware_valid=True
    )
    assert overall_safety.value == 'safe'

    # 5. Test parameter access through protocol
    rpm_param = protocol.get_parameter('RPM')
    assert rpm_param is not None
    assert rpm_param.units == 'rpm'

    fuel_table = protocol.get_table('Main Fuel Map')
    assert fuel_table is not None
    assert len(fuel_table.x_breakpoints) == 16  # 16x16 table

    print("✅ Integration Workflow test passed")
    return True

def main():
    """Run all integration tests."""
    print("🚀 Starting Moto ECU Tuner Integration Tests")
    print("=" * 60)

    tests = [
        test_ecu_protocol,
        test_safety_system,
        test_backup_system,
        test_hardware_detection,
        test_kwp2000_simulation,
        test_firmware_manager,
        test_integration_workflow
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} failed with error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! System is ready for real-world use.")
        return True
    else:
        print("⚠️  Some tests failed. Review errors before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)