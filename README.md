# Moto ECU Tuner (Magneti Marelli 28M4G)

A professional ECU tuning tool designed for **Italjet Dragster (125/200/300)** motorcycles equipped with the **Magneti Marelli 28M4G ECU**. Inspired by professional tools like IXI Personal Flasher.

## Features

*   **Professional Flashing**:
    *   **Automatic Security Access**: Handles Seed-Key exchange automatically.
    *   **Safety First**: Checks battery voltage before flashing to prevent bricking.
    *   **Auto-Backup**: Automatically backs up the original firmware before every write.
    *   **Checksum Correction**: Automatically calculates and fixes checksums.
    *   **Retry Logic**: Robust communication with automatic retries on failure.
*   **Live Dashboard**: Real-time gauges for RPM, TPS, and Temperature.
*   **Map Tracing**: Visualizes the active cell in the fuel map while the engine is running.
*   **Data Logging**: Records ECU parameters to CSV for analysis.

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
4.  Click **Write Firmware**. The app will:
    *   Check Battery Voltage (>12V required).
    *   Download a full backup of the current ECU state.
    *   Unlock the ECU (Security Access).
    *   Correct Checksums in your new file.
    *   Upload the new firmware.

### Live Tuning
1.  Start the engine.
2.  Click **Start Logging**.
3.  Use the **Dashboard** and **Map Editor** tabs to monitor performance.

## Project Structure

*   `src/kwp2000.py`: KWP2000 protocol with Security Access & Voltage Check.
*   `src/firmware_manager.py`: Robust flash manager with Backup & Checksum logic.
*   `src/gui/`: UI components (PySide6).
*   `src/logger.py`: Live data logging engine.