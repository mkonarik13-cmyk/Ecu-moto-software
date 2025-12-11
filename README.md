# Moto ECU Logger & Map Tracer

This project is a modern ECU tuning tool inspired by **RomRaider**, designed to replace older tools like TunerPro. It focuses on high-speed data logging and real-time map tracing.

## Features

*   **Real-time Data Logging**: Logs ECU parameters (RPM, TPS, Temp, etc.) via Serial/K-Line.
*   **Map Tracing**: Visualizes exactly which cell of the fuel/ignition map is currently active while the engine is running.
*   **CSV Export**: Automatically saves log sessions to CSV for analysis in MegaLogViewer or Excel.
*   **Extensible Definitions**: Easy to add new parameters and maps in `src/ecu_definition.py`.

## Installation

1.  Install Python 3.8 or higher.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To run the simulation (Mock Mode):

```bash
python main.py
```

This will start a live dashboard in your terminal, simulating an engine running and showing the active cell in the Fuel Map.

## Configuration

*   **Edit `src/ecu_definition.py`** to define your specific ECU's protocol, parameters, and maps.
*   **Edit `main.py`** to change the serial port (e.g., `COM3` or `/dev/ttyUSB0`) when connecting to a real bike.

## Project Structure

*   `src/logger.py`: Core logging engine.
*   `src/map_tracer.py`: Logic for map cell highlighting.
*   `src/ecu_definition.py`: Definitions for ECU parameters and tables.
*   `main.py`: Entry point and CLI dashboard.