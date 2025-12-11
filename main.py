import sys
from PySide6.QtWidgets import QApplication
from src.ecu_definition import create_generic_moto_protocol
from src.logger import EcuLogger
from src.gui.main_window import MainWindow

def main():
    # 1. Setup Core Logic
    protocol = create_generic_moto_protocol()
    # Use Mock mode by default for demonstration
    logger = EcuLogger(protocol, port="TEST_PORT", use_mock=True)
    
    # 2. Setup GUI
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Good cross-platform style
    
    window = MainWindow(protocol, logger)
    window.show()
    
    # 3. Run Event Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()