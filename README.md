# Moto ECU Tuner

A modern, open-source ECU tuning and logging tool inspired by RomRaider. It features a full graphical user interface for real-time data logging and map tracing.

## Features

*   **Modern GUI**: Built with PySide6 (Qt) for a professional look and feel.
*   **Live Dashboard**: Real-time gauges for RPM, TPS, and Temperature.
*   **Map Tracing**: Visualizes the active cell in the fuel map while the engine is running.
*   **Data Logging**: Records ECU parameters to CSV for analysis.
*   **Extensible**: Easy to define new protocols and maps in Python.

## Installation

1.  Install Python 3.8 or higher.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the application:

```bash
python main.py
```

### Quick Start Guide
1.  Click **Connect** in the toolbar (simulates connection in Mock mode).
2.  Click **Start Logging** to begin the data stream.
3.  Switch to the **Dashboard** tab to see live gauges.
4.  Switch to the **Map Editor** tab to see the "Map Tracing" in action (blue highlight moves as RPM/TPS change).

## Project Structure

*   `src/gui/`: UI components (Dashboard, Map Editor, Main Window).
*   `src/logger.py`: Core logging engine.
*   `src/ecu_definition.py`: ECU parameter and map definitions.
*   `main.py`: Application entry point.