# Moto ECU Tuner (Magneti Marelli 28M4G)

A professional ECU tuning tool designed for **Italjet Dragster (125/200/300)** motorcycles equipped with the **Magneti Marelli 28M4G ECU**.

## Features

*   **ECU Flashing**: Read and Write full firmware binaries (`.bin`) via OBDII/K-Line.
*   **Live Dashboard**: Real-time gauges for RPM, TPS, and Temperature.
*   **Map Tracing**: Visualizes the active cell in the fuel map while the engine is running.
*   **Data Logging**: Records ECU parameters to CSV for analysis.
*   **Protocol Support**: Implements **KWP2000** with 28M4G-specific wake-up sequences.

## Hardware Requirements

*   **OBDII Interface**: A K-Line compatible OBDII adapter (e.g., VAG-COM KKL 409.1 with FTDI chip).
*   **Adapter Cable**: 3-pin Fiat/Alfa/Lancia to OBDII adapter (for the diagnostic port on the bike).

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

### Flashing Firmware
1.  Connect your OBDII adapter to the bike and PC.
2.  Turn the ignition **ON** (engine off).
3.  Click **Connect** in the app.
4.  Click **Read Firmware** to backup your current map.
5.  Click **Write Firmware** to upload a modified `.bin` file.

### Live Tuning
1.  Start the engine.
2.  Click **Start Logging**.
3.  Use the **Dashboard** and **Map Editor** tabs to monitor performance.

## Project Structure

*   `src/kwp2000.py`: KWP2000 protocol implementation.
*   `src/firmware_manager.py`: Logic for reading/writing flash memory.
*   `src/gui/`: UI components (PySide6).
*   `src/logger.py`: Live data logging engine.