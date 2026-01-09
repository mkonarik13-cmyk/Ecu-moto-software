#!/usr/bin/env python3
"""
Simple build script for ECU Tuner 28M4G
Minimal PyInstaller build with better error handling
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("Simple ECU Tuner Build Script")
    print("=" * 50)

    # Check dependencies
    try:
        import PySide6
        print(f"✓ PySide6 {PySide6.__version__} found")
    except ImportError:
        print("✗ PySide6 not found - install with: pip install PySide6")
        return False

    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("✗ main.py not found - run from project root directory")
        return False

    print("✓ Found main.py")

    # Clean previous builds
    print("Cleaning previous builds...")
    for dir_name in ["build", "dist"]:
        if Path(dir_name).exists():
            import shutil
            shutil.rmtree(dir_name, ignore_errors=True)
            print(f"  ✓ Cleaned {dir_name}")

    # Simple PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "main.py",
        "--name=ECU_Tuner_28M4G",
        "--windowed",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--exclude-module=tkinter",
        "--exclude-module=unittest",
        "--exclude-module=test"
    ]

    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)

    try:
        # Run PyInstaller
        result = subprocess.run(cmd, capture_output=False, text=True)

        if result.returncode == 0:
            print("-" * 50)
            print("✓ Build completed successfully!")

            # Check for executable
            exe_path = Path("dist") / "ECU_Tuner_28M4G.exe"
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"✓ Executable created: {exe_path}")
                print(f"✓ File size: {size_mb:.1f} MB")
                print(f"✓ Location: {exe_path.absolute()}")
                return True
            else:
                print("✗ Executable not found")
                return False
        else:
            print("✗ PyInstaller failed")
            return False

    except Exception as e:
        print(f"✗ Error during build: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)