import time
import sys
import os
from src.ecu_definition import create_generic_moto_protocol
from src.logger import EcuLogger
from src.map_tracer import MapTracer

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    print("=== Moto ECU Logger (RomRaider Inspired) ===")
    
    # 1. Load ECU Definition
    protocol = create_generic_moto_protocol()
    print(f"Loaded Protocol: {protocol.name}")
    print(f"Available Parameters: {', '.join(protocol.parameters.keys())}")
    print(f"Available Maps: {', '.join(protocol.tables.keys())}")
    
    # 2. Initialize Logger (using Mock mode for demo)
    # In real usage, you would pass the actual serial port, e.g., '/dev/ttyUSB0' or 'COM3'
    logger = EcuLogger(protocol, port="TEST_PORT", use_mock=True)
    
    try:
        logger.connect()
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)
        
    # 3. Select Parameters to Log
    params_to_log = ["RPM", "TPS", "ECT"]
    print(f"Logging parameters: {params_to_log}")
    
    # 4. Start Logging
    logger.start_logging(params_to_log, interval=0.2)
    
    # 5. Simulate a running session (display live data)
    print("\n--- Live Data (Press Ctrl+C to stop) ---")
    
    # Get the Fuel Map for tracing
    fuel_map = protocol.get_table("Fuel Map 1")
    
    try:
        for _ in range(50): # Run for ~10 seconds
            data = logger.get_latest_data()
            if data:
                clear_screen()
                print("=== LIVE DASHBOARD ===")
                
                # 1. Display Sensor Data
                rpm = data.get('Engine Speed', 0)
                tps = data.get('Throttle Position', 0)
                temp = data.get('Coolant Temp', 0)
                
                print(f"Time: {data['timestamp']:.2f}s")
                print(f"RPM:  {rpm:.0f}")
                print(f"TPS:  {tps:.1f}%")
                print(f"Temp: {temp:.0f}C")
                print("-" * 30)
                
                # 2. Display Map Trace
                if fuel_map:
                    row, col = MapTracer.get_active_cell(fuel_map, rpm, tps)
                    print(MapTracer.format_trace_output(fuel_map, row, col))
                
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        # 6. Stop and Save
        logger.stop_logging()
        logger.save_to_csv("datalog_session.csv")
        print("Session complete.")

if __name__ == "__main__":
    main()