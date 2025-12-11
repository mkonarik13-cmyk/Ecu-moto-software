#!/usr/bin/env python3
"""
Simple test to verify the fixes for simulation mode and battery voltage.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_simulation_mode_fix():
    """Test that simulation mode is properly detected."""
    print("🧪 Testing Simulation Mode Fix...")

    # Mock serial to avoid import issues
    import unittest.mock
    with unittest.mock.patch.dict('sys.modules', {'serial': unittest.mock.MagicMock()}):
        from src.kwp2000 import KWP2000Client

        # Test explicit simulation port
        client = KWP2000Client("SIMULATION_PORT")
        assert client.simulation_mode == True, "Should detect SIMULATION_PORT as simulation mode"

        # Test test port
        client = KWP2000Client("TEST_PORT")
        assert client.simulation_mode == True, "Should detect TEST_PORT as simulation mode"

        # Test mock port
        client = KWP2000Client("MOCK_PORT")
        assert client.simulation_mode == True, "Should detect MOCK_PORT as simulation mode"

        # Test real-looking port
        client = KWP2000Client("/dev/ttyUSB0")
        assert client.simulation_mode == False, "Should not detect real port as simulation mode"

        print("✅ Simulation mode fix verified")
        return True

def test_battery_voltage_fix():
    """Test that battery voltage returns correct values in simulation mode."""
    print("🧪 Testing Battery Voltage Fix...")

    # Mock serial to avoid import issues
    import unittest.mock
    with unittest.mock.patch.dict('sys.modules', {'serial': unittest.mock.MagicMock()}):
        from src.kwp2000 import KWP2000Client

        client = KWP2000Client("SIMULATION_PORT")
        voltage = client.get_battery_voltage()

        # Should return realistic voltage range
        assert 12.0 <= voltage <= 15.0, f"Voltage {voltage} not in realistic range"
        print(f"✅ Battery voltage simulation: {voltage:.2f}V (realistic)")

        # Test multiple calls to ensure variability
        voltages = [client.get_battery_voltage() for _ in range(5)]
        assert all(12.0 <= v <= 15.0 for v in voltages), "All voltages should be realistic"
        print(f"✅ Multiple voltage readings: {[f'{v:.2f}V' for v in voltages]}")

        return True

def test_pid_simulation_responses():
    """Test that PID responses work correctly in simulation mode."""
    print("🧪 Testing PID Simulation Responses...")

    # Mock serial to avoid import issues
    import unittest.mock
    with unittest.mock.patch.dict('sys.modules', {'serial': unittest.mock.MagicMock()}):
        from src.kwp2000 import KWP2000Client

        client = KWP2000Client("SIMULATION_PORT")

        # Test battery voltage PID response
        response = client.send_request(0x21, [0x05])  # Battery voltage PID
        assert response is not None, "Should return response for battery voltage PID"
        assert len(response) >= 2, "Response should have at least 2 bytes"
        assert response[0] == 0x61, "Should return positive response for PID 0x05"
        assert response[1] == 0x05, "Should echo back the PID"
        assert 177 <= response[2] <= 189, "Raw voltage should be in realistic range"

        voltage = response[2] * 0.07
        print(f"✅ Battery voltage PID response: raw={response[2]}, voltage={voltage:.2f}V")

        # Test temperature PID response
        response = client.send_request(0x21, [0x04])  # Coolant temperature PID
        assert response is not None, "Should return response for temperature PID"
        assert response[0] == 0x61, "Should return positive response for PID 0x04"
        assert response[1] == 0x04, "Should echo back the PID"
        assert 80 <= response[2] <= 120, "Raw temperature should be in realistic range"

        temp = response[2] - 40
        print(f"✅ Temperature PID response: raw={response[2]}, temp={temp}°C")

        # Test unsupported PID
        response = client.send_request(0x21, [0x99])  # Unsupported PID
        assert response is None, "Should return None for unsupported PID"
        print("✅ Unsupported PID correctly returns None")

        return True

def test_communication_stability():
    """Test communication stability tracking in simulation mode."""
    print("🧪 Testing Communication Stability...")

    # Mock serial to avoid import issues
    import unittest.mock
    with unittest.mock.patch.dict('sys.modules', {'serial': unittest.mock.MagicMock()}):
        from src.kwp2000 import KWP2000Client

        client = KWP2000Client("SIMULATION_PORT")

        # Make some requests to populate stats
        for _ in range(10):
            client.send_request(0x21, [0x05])  # Battery voltage
            client.send_request(0x21, [0x04])  # Temperature

        stability = client.get_communication_stability()
        stats = client.communication_stats

        assert stability > 0.9, f"Stability should be >90% in simulation mode, got {stability}"
        assert stats['total_requests'] == 20, f"Should have 20 requests, got {stats['total_requests']}"
        assert stats['successful_requests'] == 20, f"Should have 20 successful requests, got {stats['successful_requests']}"
        assert stats['failed_requests'] == 0, f"Should have 0 failed requests, got {stats['failed_requests']}"

        print(f"✅ Communication stability: {stability:.1%}")
        print(f"✅ Communication stats: {stats['total_requests']} total, {stats['successful_requests']} successful")

        return True

def main():
    """Run all fix verification tests."""
    print("🔧 Testing Moto ECU Tuner Fixes")
    print("=" * 50)

    tests = [
        test_simulation_mode_fix,
        test_battery_voltage_fix,
        test_pid_simulation_responses,
        test_communication_stability
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

    print("\n" + "=" * 50)
    print(f"📊 Fix Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All fixes verified successfully!")
        print("\n✅ Fixed Issues:")
        print("   • Simulation mode auto-detection working")
        print("   • Battery voltage returning realistic values")
        print("   • PID responses with correct format")
        print("   • Communication stability tracking")
        return True
    else:
        print("⚠️  Some fixes need attention.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)