# ECU Tuner 28M4G - Italjet Dragster

Professional ECU tuning software for the Magneti Marelli 28M4G ECU used in Italjet Dragster motorcycles (125cc, 200cc, 300cc).

![ECU Tuner Logo](docs/images/logo.png)

## 🏍️ Features

### 🔧 ECU Communication
- **Auto-detection**: Automatically detects ECU and communication protocol
- **KWP2000 Protocol**: Primary protocol for 28M4G ECU
- **UDS Protocol**: Support for newer 28M4G firmware variants
- **K-Line Communication**: Optimized for motorcycle K-Line adapters
- **Connection Testing**: Real-time connection quality monitoring

### 📊 Real-time Dashboard
- **Custom Tachometer**: Motorcycle-specific RPM display (up to 18,000 RPM)
- **Temperature Monitoring**: Engine temperature with visual warnings
- **Connection Status**: Live connection quality and communication stats
- **Quick Actions**: One-click firmware reading and diagnostics

### 💾 Firmware Operations
- **Read Firmware**: Backup original ECU firmware to .bin files
- **Write Firmware**: Flash modified firmware with safety checks
- **Checksum Validation**: Automatic verification of firmware integrity
- **Progress Tracking**: Real-time progress with time estimation
- **Backup Creation**: Automatic timestamped backups before modifications

### 🗺️ Map Editing
- **Fuel Maps**: Interactive 2D table editing with color coding
- **Ignition Maps**: Spark advance timing adjustment
- **Engine-Specific Profiles**: Different maps for 125cc/200cc/300cc models
- **3D Visualization**: Visual representation of map surfaces (planned)
- **Undo/Redo**: Complete change tracking and rollback capability

### 🌡️ Cooling Management
- **Fan Configuration**: Adjustable temperature thresholds
- **Variable Speed Control**: Support for variable speed fans
- **Dual Fan Support**: Configure dual fan systems
- **Riding Modes**: Track day and traffic jam presets
- **Real-time Monitoring**: Live temperature and fan status

### 🔍 Diagnostics
- **DTC Reading**: Read and clear diagnostic trouble codes
- **Code Descriptions**: Detailed explanations of all DTCs
- **Freeze Frame**: Capture conditions when DTCs occurred
- **Analysis**: Automatic issue identification and recommendations
- **Report Generation**: Comprehensive diagnostic reports

## 🚀 Quick Start

### Prerequisites
- Windows 10 or later (64-bit)
- 4GB RAM minimum
- USB OBD-II to K-Line adapter
- Italjet Dragster with 28M4G ECU

### Installation
1. **Download the latest release** from the [Releases](https://github.com/username/Ecu-moto-software/releases) page
2. **Extract the ZIP file** to a folder
3. **Run `ECU_Tuner_28M4G.exe`** - no installation required!
4. **Connect your OBD-II adapter** to the motorcycle and computer

### First Connection
1. Launch the application
2. Click **"Connect ECU"** button
3. Select your USB port (or use Auto Detect)
4. Click **"Connect"** and wait for detection
5. Verify ECU information appears on the dashboard

## 📋 Hardware Compatibility

### Recommended Adapters
- **VAG-COM K-Line** (409.1 or newer)
- **Dedicated motorcycle tuning interfaces**
- **Generic K-Line USB adapters** with FTDI chips

### Supported Models
- **Italjet Dragster 125** (28M4G ECU)
- **Italjet Dragster 200** (28M4G ECU)
- **Italjet Dragster 300** (28M4G ECU)

## 🛠️ Development

### Environment Setup
```bash
# Clone repository
git clone https://github.com/username/Ecu-moto-software.git
cd Ecu-moto-software

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run application (development mode)
python main.py
```

### Project Structure
```
Ecu-moto-software/
├── src/                          # Source code
│   ├── gui/                      # User interface
│   │   ├── main_window.py        # Main application window
│   │   ├── dashboard.py          # Dashboard with gauges
│   │   ├── flash_tools.py        # Firmware read/write tools
│   │   ├── map_editor.py         # Map editing interface
│   │   ├── fan_settings.py       # Cooling fan configuration
│   │   └── widgets/              # Custom UI widgets
│   ├── ecu/                      # ECU communication
│   │   ├── connection.py         # ECU connection management
│   │   ├── protocols/            # Communication protocols
│   │   │   ├── kwp2000.py        # KWP2000 implementation
│   │   │   └── uds.py            # UDS implementation
│   │   └── diagnostics.py        # DTC management
│   ├── maps/                     # Map handling
│   │   ├── parser.py             # Firmware parsing
│   │   ├── editor.py             # Map modification
│   │   └── types.py              # Data structures
│   └── utils/                    # Utilities
│       ├── logger.py             # Logging system
│       └── crypto.py             # Security functions
├── build_scripts/                # Build and packaging
├── requirements.txt              # Python dependencies
├── main.py                       # Application entry point
└── README.md                     # This file
```

### Building Executable
```bash
# Install PyInstaller
pip install pyinstaller

# Run build script
python build_scripts/build_exe.py

# Or use PyInstaller directly
pyinstaller build_scripts/ecu_tuner.spec
```

## ⚙️ Configuration

### Connection Settings
- **Port**: USB COM port of your OBD-II adapter
- **Baud Rate**: 10400 (standard for 28M4G) or 9600
- **Protocol**: Auto-detect or specify KWP2000/UDS
- **Timeout**: 5 seconds (adjustable)
- **Retry Count**: 3 attempts (adjustable)

### Map Settings
- **Fuel Map Unit**: Milliseconds (injection time)
- **Ignition Map Unit**: Degrees BTDC (before top dead center)
- **RPM Range**: 1000-18000 RPM (engine dependent)
- **TPS Range**: 0-100% throttle position

### Fan Settings
- **ON Temperature**: 85-105°C (adjustable)
- **OFF Temperature**: 75-95°C (adjustable)
- **Hysteresis**: Automatic calculation (ON - OFF)

## 🔒 Safety Features

### Firmware Protection
- **Automatic Backups**: Creates backup before any modifications
- **Checksum Validation**: Verifies firmware integrity
- **File Size Validation**: Checks against ECU flash size
- **Abort on Error**: Stops operations on communication failures

### User Warnings
- **Multiple Confirmation Dialogs**: Prevents accidental modifications
- **Risk Warnings**: Clear explanations of potential risks
- **Rollback Capability**: Undo all map changes
- **Recovery Procedures**: Emergency recovery documentation

## 📖 Troubleshooting

### Connection Issues
**Problem**: Cannot connect to ECU
1. Check USB cable and adapter
2. Try different USB port
3. Verify driver installation
4. Try different baud rates (10400, 9600)
5. Check motorcycle ignition (must be ON)

**Problem**: Adapter not detected
1. Install FTDI drivers (for VAG-COM adapters)
2. Check Device Manager for COM port
3. Try different USB cable
4. Restart computer

### Firmware Issues
**Problem**: Read operation fails
1. Check connection quality
2. Increase timeout settings
3. Ensure motorcycle battery is charged
4. Try again with engine running

**Problem**: Write operation fails
1. Verify firmware file compatibility
2. Check available disk space
3. Ensure stable connection
4. Try with smaller file size

### Map Editing Issues
**Problem**: Cannot load map file
1. Verify file format (.bin or .hex)
2. Check file size (should match ECU)
3. Try reading firmware from ECU first
4. Check for file corruption

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Style
- Follow PEP 8 Python style guidelines
- Use Black for code formatting
- Include docstrings for all functions
- Add type hints where appropriate
- Write unit tests for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**IMPORTANT WARNING**: This software modifies your motorcycle's ECU firmware. Incorrect use can:
- Cause engine damage
- Void your warranty
- Create unsafe operating conditions
- Violate local regulations

**Always**:
- Backup your original firmware
- Test in a safe environment
- Consult professional tuners if unsure
- Follow local laws and regulations

## 🙏 Acknowledgments

- **Magneti Marelli** for the 28M4G ECU documentation
- **Italjet** for motorcycle specifications
- **Open Source Community** for various libraries and tools
- **Beta Testers** for valuable feedback and testing

## 📞 Support

- **Documentation**: [Wiki](https://github.com/username/Ecu-moto-software/wiki)
- **Issues**: [GitHub Issues](https://github.com/username/Ecu-moto-software/issues)
- **Discussions**: [GitHub Discussions](https://github.com/username/Ecu-moto-software/discussions)
- **Email**: support@ecu-tuner.com

---

**ECU Tuner 28M4G** - Professional tuning for Italjet Dragster motorcycles

*Built with ❤️ for motorcycle enthusiasts*