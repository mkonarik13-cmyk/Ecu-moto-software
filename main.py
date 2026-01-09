#!/usr/bin/env python3
"""
ECU Tuner for Magneti Marelli 28M4G - Italjet Dragster
Main entry point for the application

This application provides comprehensive ECU tuning, diagnostics, and flashing
capabilities for the Magneti Marelli 28M4G ECU used in Italjet Dragster motorcycles.
"""

import sys
import os
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QLocale
from PySide6.QtGui import QIcon
from src.gui.main_window import MainWindow
from src.utils.logger import setup_logging


def setup_application():
    """Configure QApplication with basic settings"""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("ECU Tuner 28M4G")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ECU Tuner Software")
    app.setOrganizationDomain("ecu-tuner.com")

    # Set application icon (if available)
    icon_path = Path(__file__).parent / "src" / "gui" / "resources" / "icons" / "app.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Setup translation (Czech/English support)
    translator = QTranslator()
    locale = QLocale.system().name()

    # Try to load Czech translation first
    if translator.load(f"translations/ecu_tuner_{locale}", ":/"):
        app.installTranslator(translator)
    else:
        # Fall back to English
        if translator.load("translations/ecu_tuner_en", ":/"):
            app.installTranslator(translator)

    return app


def main():
    """Main application entry point"""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Starting ECU Tuner 28M4G application")

        # Create Qt application
        qt_app = setup_application()

        # Create and show main window
        main_window = MainWindow()
        main_window.show()

        logger.info("Main window displayed, starting event loop")

        # Start the Qt event loop
        return qt_app.exec()

    except Exception as e:
        logging.getLogger(__name__).error(f"Application startup failed: {e}")
        print(f"Failed to start application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())