#!/usr/bin/env python3
"""
Automated build script for ECU Tuner 28M4G Windows executable
Creates standalone .exe file with PyInstaller
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import PyInstaller.__main__
except ImportError:
    print("Error: PyInstaller not found. Please install with: pip install PyInstaller")
    sys.exit(1)


def create_app_icon():
    """Create a simple app icon if one doesn't exist"""
    icon_dir = project_root / "src" / "gui" / "resources" / "icons"
    icon_dir.mkdir(parents=True, exist_ok=True)

    icon_path = icon_dir / "app.ico"
    if not icon_path.exists():
        print("Note: No app.ico found. You may want to add a custom icon.")
        # Could create a simple icon here using PIL if needed
        return None
    return str(icon_path)


def clean_build_dirs():
    """Clean previous build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']

    for dir_name in dirs_to_clean:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"Cleaning {dir_path}...")
            shutil.rmtree(dir_path, ignore_errors=True)


def create_version_info():
    """Create version info file for Windows executable"""
    version_info_content = '''
# Version information for Windows executable
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'ECU Tuner Software'),
        StringStruct(u'FileDescription', u'ECU Tuner 28M4G - Italjet Dragster'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'InternalName', u'ecu_tuner_28m4g'),
        StringStruct(u'LegalCopyright', u'Copyright © 2024'),
        StringStruct(u'OriginalFilename', u'ECU_Tuner_28M4G.exe'),
        StringStruct(u'ProductName', u'ECU Tuner 28M4G'),
        StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

    version_file = project_root / "build_scripts" / "version_info.txt"
    with open(version_file, 'w') as f:
        f.write(version_info_content)

    return str(version_file)


def create_spec_file():
    """Create PyInstaller spec file with custom configuration"""
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['{project_root}'],
    binaries=[],
    datas=[
        ('src/gui/resources', 'resources'),
        ('build_scripts/version_info.txt', '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'matplotlib.backends.backend_qt5agg',
        'numpy',
        'pycryptodome',
        'colorlog',
        'retrying'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'test',
        'doctest',
        'pdb',
        'distutils'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ECU_Tuner_28M4G',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='build_scripts/version_info.txt',
    icon='src/gui/resources/icons/app.ico' if Path('src/gui/resources/icons/app.ico').exists() else None
)
'''

    spec_file = project_root / "build_scripts" / "ecu_tuner.spec"
    with open(spec_file, 'w') as f:
        f.write(spec_content)

    return str(spec_file)


def build_executable():
    """Build the executable using PyInstaller"""
    print("Starting PyInstaller build...")

    # Change to project directory
    os.chdir(project_root)

    # Create spec file
    spec_file = create_spec_file()
    print(f"Created spec file: {spec_file}")

    # Build arguments
    build_args = [
        str(spec_file),
        '--clean',
        '--noconfirm'
    ]

    # Run PyInstaller
    try:
        print("Running PyInstaller...")
        PyInstaller.__main__.run(build_args)

        # Check if executable was created
        exe_path = project_root / "dist" / "ECU_Tuner_28M4G.exe"
        if exe_path.exists():
            file_size = exe_path.stat().st_size / (1024 * 1024)  # Convert to MB
            print(f"Build successful!")
            print(f"Executable: {exe_path}")
            print(f"File size: {file_size:.1f} MB")
            return True
        else:
            print("Error: Executable not found after build")
            return False

    except Exception as e:
        print(f"Build failed with error: {e}")
        return False


def create_distribution_package():
    """Create distribution package with documentation"""
    dist_dir = project_root / "dist"

    if not dist_dir.exists():
        print("Error: dist directory not found")
        return False

    # Create package directory
    package_dir = dist_dir / "ECU_Tuner_28M4G_Package"
    if package_dir.exists():
        shutil.rmtree(package_dir)

    package_dir.mkdir()

    # Copy executable
    exe_source = dist_dir / "ECU_Tuner_28M4G.exe"
    exe_dest = package_dir / "ECU_Tuner_28M4G.exe"
    if exe_source.exists():
        shutil.copy2(exe_source, exe_dest)
        print(f"Copied executable to package")
    else:
        print("Error: Executable not found")
        return False

    # Create documentation
    readme_content = '''# ECU Tuner 28M4G - Installation Guide

## Overview
Professional ECU tuning software for Magneti Marelli 28M4G ECU
Used in Italjet Dragster motorcycles (125cc, 200cc, 300cc)

## System Requirements
- Windows 10 or later (64-bit)
- 4GB RAM minimum
- 100MB free disk space
- USB port for OBD-II adapter

## Installation
1. Extract all files to a folder
2. Run "ECU_Tuner_28M4G.exe"
3. No installation required - portable application

## Hardware Requirements
- OBD-II to K-Line USB adapter (recommended: VAG-COM compatible)
- Compatible with:
  * VAG-COM K-Line adapters
  * Generic K-Line USB adapters
  * Dedicated motorcycle tuning interfaces

## Quick Start
1. Connect OBD-II adapter to motorcycle
2. Connect USB cable to computer
3. Launch application
4. Click "Connect ECU"
5. Select port and click "Auto Detect"
6. Start tuning!

## Features
- KWP2000 and UDS protocol support
- Firmware read/write capabilities
- Interactive fuel and ignition map editing
- Real-time dashboard with gauges
- Cooling fan configuration
- Diagnostic trouble code management
- Professional logging system

## Support
For technical support and documentation, visit:
https://github.com/username/Ecu-moto-software

## Safety Warning
This software modifies ECU firmware. Incorrect use can damage
your motorcycle engine. Always backup original firmware before
making changes.

© 2024 ECU Tuner Software
'''

    readme_path = package_dir / "README.txt"
    with open(readme_path, 'w') as f:
        f.write(readme_content)

    # Create driver info
    driver_info = '''# OBD-II Adapter Driver Installation

## Windows Driver Installation

Most modern Windows systems will automatically install drivers
for USB OBD-II adapters. If drivers are not found:

### VAG-COM/K-Line Adapters
1. Download FTDI drivers from: https://ftdichip.com/drivers/
2. Install drivers before connecting adapter
3. Connect adapter when prompted

### Generic USB Adapters
1. Check manufacturer website for drivers
2. Use Windows Update to find drivers
3. May require manual driver selection

### Testing Connection
- Check Device Manager for COM port assignment
- Verify adapter appears under "Ports (COM & LPT)"
- Test with ECU Tuner application

## Troubleshooting
- Try different USB ports
- Disable power saving on USB ports
- Use shorter USB cables
- Try different baud rates in connection settings
'''

    driver_path = package_dir / "DRIVERS.txt"
    with open(driver_path, 'w') as f:
        f.write(driver_info)

    # Create profiles directory with example files
    profiles_dir = package_dir / "profiles"
    profiles_dir.mkdir()

    # Create example tuning profiles
    profiles = {
        "Stock_125cc.txt": "Stock fuel and ignition map for 125cc model",
        "Sport_200cc.txt": "Performance map for 200cc model (increased fuel, advanced timing)",
        "Economy_300cc.txt": "Economy map for 300cc model (reduced fuel, retarded timing)",
        "Track_Day.txt": "Track day settings (max performance, aggressive cooling)"
    }

    for profile_name, description in profiles.items():
        profile_path = profiles_dir / profile_name
        with open(profile_path, 'w') as f:
            f.write(f"# {description}\\n# Load via Map Editor -> Load Profile\\n")

    print("Created distribution package with documentation")

    # Calculate package size
    total_size = sum(f.stat().st_size for f in package_dir.rglob('*') if f.is_file())
    total_size_mb = total_size / (1024 * 1024)

    print(f"Package size: {total_size_mb:.1f} MB")
    print(f"Package location: {package_dir}")

    return True


def main():
    """Main build function"""
    print("=" * 60)
    print("ECU Tuner 28M4G - Build Script")
    print("=" * 60)

    # Check if we're in the right directory
    if not (project_root / "main.py").exists():
        print("Error: main.py not found. Please run from project directory.")
        return False

    # Create version info
    version_file = create_version_info()
    print(f"Created version info: {version_file}")

    # Clean previous builds
    clean_build_dirs()

    # Build executable
    if build_executable():
        print("\\nBuild completed successfully!")

        # Create distribution package
        if create_distribution_package():
            print("\\nDistribution package created!")

            # Final instructions
            print("\\n" + "=" * 60)
            print("BUILD COMPLETE")
            print("=" * 60)
            print(f"Executable: dist/ECU_Tuner_28M4G.exe")
            print(f"Package: dist/ECU_Tuner_28M4G_Package/")
            print("\\nReady for distribution!")

            return True
        else:
            print("Error: Failed to create distribution package")
            return False
    else:
        print("Error: Build failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)