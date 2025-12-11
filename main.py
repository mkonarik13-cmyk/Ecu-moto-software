import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer
from src.ecu_definition import create_italjet_dragster_28m4g_protocol, create_generic_moto_protocol
from src.logger import EcuLogger
from src.gui.main_window import MainWindow
from src.kwp2000 import KWP2000Client
from src.hardware_detector import HardwareDetector, auto_connect_adapter
from src.safety import safety_manager

def main():
    """
    Main application entry point with real hardware integration.
    Supports both real ECU communication and simulation mode.
    """
    print("🏍️  Moto ECU Tuner - Starting up...")

    # 1. Hardware Detection and Setup
    print("🔌 Detecting K-Line adapters...")
    detector = HardwareDetector()
    adapters = detector.scan_adapters()

    kwp_client = None
    use_real_hardware = False

    if adapters:
        print(f"✅ Found {len(adapters)} compatible adapter(s):")
        for adapter in adapters:
            print(f"   - {adapter.name} on {adapter.port}")

        # Try to auto-connect to the best adapter
        if detector.auto_detect_and_connect():
            kwp_client = KWP2000Client(detector.selected_adapter.port)
            use_real_hardware = True
            print(f"🔗 Connected to: {detector.selected_adapter.name}")
        else:
            print("❌ Failed to connect to any adapter")
    else:
        print("⚠️  No K-Line adapters found - using simulation mode")

    # 2. Fallback to simulation if no hardware
    if not use_real_hardware:
        print("🎮 Starting in SIMULATION MODE")
        kwp_client = KWP2000Client("SIMULATION_PORT")

    # 3. ECU Protocol Setup
    try:
        print("📋 Loading ECU protocol definitions...")
        if use_real_hardware:
            # Use real 28M4G protocol for actual hardware
            protocol = create_italjet_dragster_28m4g_protocol()
            print("✅ Loaded Italjet Dragster 28M4G protocol")
        else:
            # Use generic protocol for simulation
            protocol = create_generic_moto_protocol()
            print("✅ Loaded generic protocol for simulation")
    except Exception as e:
        print(f"❌ Error loading ECU protocol: {e}")
        QMessageBox.critical(None, "Error", f"Failed to load ECU protocol: {e}")
        return 1

    # 4. Initialize Logger with shared client
    try:
        logger = EcuLogger(protocol, kwp_client)
        print("✅ Logger initialized")
    except Exception as e:
        print(f"❌ Error initializing logger: {e}")
        QMessageBox.critical(None, "Error", f"Failed to initialize logger: {e}")
        return 1

    # 5. Establish ECU Communication (if using real hardware)
    if use_real_hardware:
        print("🚀 Establishing ECU communication...")
        try:
            if kwp_client.connect():
                print("✅ ECU communication established")

                # Test basic communication
                voltage = kwp_client.get_battery_voltage()
                print(f"🔋 Battery voltage: {voltage:.1f}V")

                # Log successful connection
                safety_manager.log_safety_event("ECU_CONNECTED",
                                             f"ECU communication established, voltage: {voltage:.1f}V")
            else:
                print("❌ Failed to establish ECU communication")
                use_real_hardware = False
                print("🔄 Switching to simulation mode")
        except Exception as e:
            print(f"❌ Error connecting to ECU: {e}")
            print("🔄 Switching to simulation mode")
            use_real_hardware = False

    # 6. GUI Setup
    print("🖥️  Initializing GUI...")
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")  # Good cross-platform style

        # Set application properties
        app.setApplicationName("Moto ECU Tuner")
        app.setApplicationVersion("2.0")
        app.setOrganizationName("ECU Tuning Solutions")

        # Create main window
        window = MainWindow(protocol, logger, kwp_client)
        window.show()

        print("✅ GUI initialized")

        # 7. Status Updates
        if use_real_hardware:
            status_msg = f"Connected to {detector.selected_adapter.name if detector.selected_adapter else 'ECU'}"
            window.set_status(f"🟢 {status_msg}")
        else:
            window.set_status("🟡 Simulation Mode - No hardware detected")

        # 8. Setup periodic status updates
        def update_status():
            if use_real_hardware and kwp_client:
                try:
                    voltage = kwp_client.get_battery_voltage()
                    stability = kwp_client.get_communication_stability()
                    window.set_status(f"🟢 Connected | Battery: {voltage:.1f}V | Stability: {stability:.1%}")
                except:
                    window.set_status("🟠 Connection issues detected")

        status_timer = QTimer()
        status_timer.timeout.connect(update_status)
        status_timer.start(5000)  # Update every 5 seconds

        print("🎉 Application ready!")

        # 9. Run Event Loop
        return app.exec()

    except Exception as e:
        print(f"❌ Error initializing GUI: {e}")
        QMessageBox.critical(None, "Error", f"Failed to initialize GUI: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Application terminated by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)