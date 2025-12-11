#!/usr/bin/env python3
"""
Test script to check for import problems
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_import(module_name, description=""):
    """Test if a module can be imported"""
    try:
        __import__(module_name)
        print(f"✓ {description or module_name}")
        return True
    except ImportError as e:
        print(f"✗ {description or module_name}: {e}")
        return False
    except Exception as e:
        print(f"✗ {description or module_name}: {e}")
        return False

def main():
    print("Testing ECU Tuner Imports")
    print("=" * 40)

    # Test core modules
    core_modules = [
        ('src.maps.types', 'Types module'),
        ('src.ecu.connection', 'ECU connection'),
        ('src.ecu.protocols.kwp2000', 'KWP2000 protocol'),
        ('src.ecu.protocols.uds', 'UDS protocol'),
        ('src.utils.logger', 'Logger'),
        ('src.maps.parser', 'Firmware parser')
    ]

    all_good = True
    for module, desc in core_modules:
        if not test_import(module, desc):
            all_good = False

    # Test GUI modules (skip if PySide6 not available)
    try:
        import PySide6
        print("\n✓ PySide6 available - testing GUI modules")

        gui_modules = [
            ('src.gui.main_window', 'Main window'),
            ('src.gui.dashboard', 'Dashboard'),
            ('src.gui.flash_tools', 'Flash tools'),
            ('src.gui.map_editor', 'Map editor'),
            ('src.gui.fan_settings', 'Fan settings'),
            ('src.gui.widgets.connection_dialog', 'Connection dialog')
        ]

        for module, desc in gui_modules:
            if not test_import(module, desc):
                all_good = False

    except ImportError:
        print("\n⚠ PySide6 not available - skipping GUI tests")

    print("\n" + "=" * 40)
    if all_good:
        print("✓ All imports successful!")
    else:
        print("✗ Some imports failed - check above for details")

    return all_good

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)