import sys
from PySide6.QtWidgets import QApplication
from src.ecu_definition import create_generic_moto_protocol
from src.logger import EcuLogger
from src.gui.main_window import MainWindow
from src.kwp2000 import KWP2000Client

def main():
    # 1. Setup Core Logic
    protocol = create_generic_moto_protocol()
    
    # Create shared KWP Client
    kwp_client = KWP2000Client("TEST_PORT")
    
    # Initialize Logger with the shared client
    logger = EcuLogger(protocol, kwp_client)
    
    # 2. Setup GUI
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Good cross-platform style
    
    # Pass shared client to MainWindow (it will pass it to widgets)
    window = MainWindow(protocol, logger, kwp_client)
    window.show()
    
    # 3. Run Event Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()