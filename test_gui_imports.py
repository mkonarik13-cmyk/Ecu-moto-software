#!/usr/bin/env python3
"""
Test PySide6 imports to verify GUI fixes.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_pyside6_imports():
    """Test that all PySide6 imports work correctly."""
    print("🧪 Testing PySide6 GUI Imports...")

    try:
        # Test main PySide6 imports
        from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
        from PySide6.QtCore import Qt, QTimer, Signal
        from PySide6.QtGui import QAction, QPalette, QColor
        print("✅ Basic PySide6 imports successful")

        # Test signal import specifically
        signal = Signal(str)
        print("✅ Signal import successful")

        # Test GUI components imports
        from src.gui.dashboard import DashboardWidget
        print("✅ DashboardWidget import successful")

        from src.gui.main_window import MainWindow
        print("✅ MainWindow import successful")

        # Test that MainWindow has the required methods
        # We'll just test the class definition, not instantiation (since we don't have GUI)
        assert hasattr(MainWindow, 'set_status'), "MainWindow should have set_status method"
        assert hasattr(MainWindow, 'connect_ecu'), "MainWindow should have connect_ecu method"
        assert hasattr(MainWindow, 'read_firmware'), "MainWindow should have read_firmware method"
        assert hasattr(MainWindow, 'write_firmware'), "MainWindow should have write_firmware method"
        print("✅ MainWindow methods available")

        # Test DashboardWidget has the required signal
        assert hasattr(DashboardWidget, 'status_updated'), "DashboardWidget should have status_updated signal"
        print("✅ DashboardWidget signal available")

        print("✅ All PySide6 GUI imports working correctly!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_components_without_gui():
    """Test that components can be imported without starting GUI."""
    print("\n🧪 Testing Components Without GUI...")

    try:
        from src.ecu_definition import create_italjet_dragster_28m4g_protocol
        from src.safety import safety_manager
        from src.backup_manager import backup_manager
        from src.kwp2000 import KWP2000Client

        # Test basic functionality without GUI
        protocol = create_italjet_dragster_28m4g_protocol()
        print(f"✅ Protocol created: {protocol.name}")

        client = KWP2000Client("SIMULATION_PORT")
        print(f"✅ KWP client created: simulation={client.simulation_mode}")

        voltage_check = safety_manager.check_battery_voltage(12.6)
        print(f"✅ Safety check: {voltage_check.message}")

        print("✅ All components work without GUI!")
        return True

    except Exception as e:
        print(f"❌ Component test error: {e}")
        return False

def main():
    """Run all GUI import tests."""
    print("🔧 Testing PySide6 GUI Fixes")
    print("=" * 40)

    tests = [
        test_pyside6_imports,
        test_components_without_gui
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

    print("\n" + "=" * 40)
    print(f"📊 GUI Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All GUI fixes verified successfully!")
        print("\n✅ Fixed Issues:")
        print("   • pyqtSignal → Signal import fixed")
        print("   • MainWindow.set_status() method added")
        print("   • All PySide6 imports working correctly")
        print("\n🚀 Ready to run: python main.py")
        return True
    else:
        print("⚠️  Some GUI issues remain.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)