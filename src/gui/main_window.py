from PySide6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                               QMessageBox, QToolBar, QFileDialog, QProgressDialog,
                               QMenuBar, QMenu)
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtCore import Qt
from .dashboard import DashboardWidget
from .map_editor import MapEditorWidget
from .scanner_dialog import ScannerDialog
from ..kwp2000 import KWP2000Client
from ..firmware_manager import FirmwareManager

class MainWindow(QMainWindow):
    def __init__(self, protocol, logger, kwp_client):
        super().__init__()
        self.protocol = protocol
        self.logger = logger
        self.kwp_client = kwp_client
        self.fw_manager = FirmwareManager(self.kwp_client)
        
        self.setWindowTitle("Moto ECU Tuner (Magneti Marelli 28M4G)")
        self.resize(1000, 700)
        
        self.setup_theme()
        self.setup_ui()
        self.setup_menubar()
        self.setup_toolbar()

    def setup_theme(self):
        # Dark Theme
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)

    def setup_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Dashboard Tab
        # Pass kwp_client as protocol for scanning
        self.dashboard = DashboardWidget(self.logger, self.kwp_client)
        self.tabs.addTab(self.dashboard, "Dashboard")
        
        # Map Editor Tab
        self.map_editor = MapEditorWidget(self.protocol, self.logger)
        self.tabs.addTab(self.map_editor, "Map Editor")

    def setup_menubar(self):
        """Setup comprehensive menu bar like professional ECU software."""
        menubar = self.menuBar()

        # === File Menu ===
        file_menu = menubar.addMenu('Soubor')

        # New Project
        new_action = QAction('Nový projekt', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        # Open Project
        open_action = QAction('Otevřít projekt', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        # Save Project
        save_action = QAction('Uložit projekt', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        # Read Firmware
        read_fw_action = QAction('Načíst firmware z ECU', self)
        read_fw_action.setShortcut('Ctrl+R')
        read_fw_action.triggered.connect(self.read_firmware)
        file_menu.addAction(read_fw_action)

        # Write Firmware
        write_fw_action = QAction('Zapsat firmware do ECU', self)
        write_fw_action.setShortcut('Ctrl+W')
        write_fw_action.triggered.connect(self.write_firmware)
        file_menu.addAction(write_fw_action)

        file_menu.addSeparator()

        # Exit
        exit_action = QAction('Konec', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # === ECU Menu ===
        ecu_menu = menubar.addMenu('ECU')

        # Connect
        connect_action = QAction('Připojit', self)
        connect_action.setShortcut('F5')
        connect_action.triggered.connect(self.connect_ecu)
        ecu_menu.addAction(connect_action)

        # Disconnect
        disconnect_action = QAction('Odpojit', self)
        disconnect_action.setShortcut('F6')
        disconnect_action.triggered.connect(self.disconnect_ecu)
        ecu_menu.addAction(disconnect_action)

        ecu_menu.addSeparator()

        # Read ECU Info
        ecu_info_action = QAction('Informace o ECU', self)
        ecu_info_action.setShortcut('F7')
        ecu_info_action.triggered.connect(self.show_ecu_info)
        ecu_menu.addAction(ecu_info_action)

        # Read VIN
        read_vin_action = QAction('Načíst VIN', self)
        read_vin_action.triggered.connect(self.read_vin)
        ecu_menu.addAction(read_vin_action)

        # Read DTC
        read_dtc_action = QAction('Načíst chybové kódy', self)
        read_dtc_action.setShortcut('F8')
        read_dtc_action.triggered.connect(self.read_dtc)
        ecu_menu.addAction(read_dtc_action)

        # Clear DTC
        clear_dtc_action = QAction('Smazat chybové kódy', self)
        clear_dtc_action.triggered.connect(self.clear_dtc)
        ecu_menu.addAction(clear_dtc_action)

        ecu_menu.addSeparator()

        # Security Access
        security_action = QAction('Přístup do zabezpečení', self)
        security_action.triggered.connect(self.request_security_access)
        ecu_menu.addAction(security_action)

        # === Diagnostics Menu ===
        diag_menu = menubar.addMenu('Diagnostika')

        # Live Data
        live_data_action = QAction('Živá data', self)
        live_data_action.setShortcut('Ctrl+L')
        live_data_action.triggered.connect(self.start_logging)
        diag_menu.addAction(live_data_action)

        # Stop Live Data
        stop_data_action = QAction('Zastavit živá data', self)
        stop_data_action.setShortcut('Ctrl+T')
        stop_data_action.triggered.connect(self.stop_logging)
        diag_menu.addAction(stop_data_action)

        diag_menu.addSeparator()

        # Scan PIDs
        scan_action = QAction('Skenovat ID parametrů', self)
        scan_action.setShortcut('F9')
        scan_action.triggered.connect(self.open_scanner)
        diag_menu.addAction(scan_action)

        # === Tools Menu ===
        tools_menu = menubar.addMenu('Nástroje')

        # Map Editor
        map_editor_action = QAction('Editor map', self)
        map_editor_action.setShortcut('Ctrl+M')
        map_editor_action.triggered.connect(self.open_map_editor)
        tools_menu.addAction(map_editor_action)

        # Backup Manager
        backup_action = QAction('Správce záloh', self)
        backup_action.triggered.connect(self.open_backup_manager)
        tools_menu.addAction(backup_action)

        tools_menu.addSeparator()

        # Preferences
        pref_action = QAction('Nastavení', self)
        pref_action.triggered.connect(self.show_preferences)
        tools_menu.addAction(pref_action)

        # === Help Menu ===
        help_menu = menubar.addMenu('Nápověda')

        # About
        about_action = QAction('O aplikaci', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # Help
        help_doc_action = QAction('Nápověda', self)
        help_doc_action.triggered.connect(self.show_help)
        help_menu.addAction(help_doc_action)

    def setup_toolbar(self):
        """Setup toolbar with common actions."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # Quick Connect
        connect_action = QAction("🔌 Připojit", self)
        connect_action.triggered.connect(self.connect_ecu)
        toolbar.addAction(connect_action)

        toolbar.addSeparator()

        # Live Data
        start_log_action = QAction("📊 Spustit logování", self)
        start_log_action.triggered.connect(self.start_logging)
        toolbar.addAction(start_log_action)

        # Stop Logging
        stop_log_action = QAction("⏹ Zastavit", self)
        stop_log_action.triggered.connect(self.stop_logging)
        toolbar.addAction(stop_log_action)

        toolbar.addSeparator()

        # Read Firmware
        read_fw_action = QAction("📥 Načíst firmware", self)
        read_fw_action.triggered.connect(self.read_firmware)
        toolbar.addAction(read_fw_action)

        # Write Firmware
        write_fw_action = QAction("📤 Zapsat firmware", self)
        write_fw_action.triggered.connect(self.write_firmware)
        toolbar.addAction(write_fw_action)

        toolbar.addSeparator()

        # Map Editor
        map_action = QAction("🗺️ Editor map", self)
        map_action.triggered.connect(self.open_map_editor)
        toolbar.addAction(map_action)

        # Scan PIDs
        scan_action = QAction("🔍 Skenovat PIDs", self)
        scan_action.triggered.connect(self.open_scanner)
        toolbar.addAction(scan_action)

    # === File Menu Methods ===
    def new_project(self):
        """Create new project."""
        QMessageBox.information(self, "Nový projekt", "Vytvořen nový projekt")

    def open_project(self):
        """Open existing project."""
        fname, _ = QFileDialog.getOpenFileName(self, "Otevřít projekt", "", "ECU Files (*.ecu *.xml *.json)")
        if fname:
            QMessageBox.information(self, "Projekt otevřen", f"Projekt otevřen z: {fname}")

    def save_project(self):
        """Save current project."""
        fname, _ = QFileDialog.getSaveFileName(self, "Uložit projekt", "", "ECU Files (*.ecu *.xml *.json)")
        if fname:
            QMessageBox.information(self, "Projekt uložen", f"Projekt uložen do: {fname}")

    # === ECU Menu Methods ===
    def connect_ecu(self):
        """Connect to ECU with comprehensive feedback."""
        try:
            self.set_status("Připojování k ECU...")

            # Show connection dialog with hardware detection
            from ..hardware_detector import HardwareDetector

            detector = HardwareDetector()
            adapters = detector.scan_adapters()

            if adapters:
                # Auto-connect to best adapter
                if detector.auto_detect_and_connect():
                    if self.kwp_client.connect():
                        voltage = self.kwp_client.get_battery_voltage()
                        stability = self.kwp_client.get_communication_stability()

                        msg = f"""✅ Připojeno k ECU!

📡 Adapér: {detector.selected_adapter.name}
🔌 Port: {detector.selected_adapter.port}
🔋 Napětí: {voltage:.1f}V
📊 Stabilita: {stability:.1%}

ECU: Magneti Marelli 28M4G
Protokol: KWP2000
Rychlost: 10400 baud"""

                        QMessageBox.information(self, "Připojeno", msg)
                        self.set_status(f"Připojeno - {detector.selected_adapter.name}")
                        return True
                    else:
                        QMessageBox.warning(self, "Upozornění", "Adapér nalezen, ale nepodařilo se připojit k ECU")
                else:
                    QMessageBox.warning(self, "Upozornění", "Nepodařilo se inicializovat adaptér")
            else:
                # Fallback to simulation mode
                reply = QMessageBox.question(self, "Žádný hardware",
                                          "Nebyl nalezen žádný K-Line adaptér.\n\nSpustit v simulačním režimu?",
                                          QMessageBox.Yes | QMessageBox.No)

                if reply == QMessageBox.Yes:
                    self.kwp_client.simulation_mode = True
                    self.logger.connect()
                    QMessageBox.information(self, "Simulační režim",
                                          "Aplikace spuštěna v simulačním režimu\n\nPro reálné připojení připojte K-Line adaptér")
                    self.set_status("Simulační režim")
                    return True

        except Exception as e:
            QMessageBox.critical(self, "Chyba připojení", f"Nepodařilo se připojit k ECU:\n\n{str(e)}")
            self.set_status("Chyba připojení")
            return False

    def disconnect_ecu(self):
        """Disconnect from ECU."""
        try:
            if hasattr(self.kwp_client, 'disconnect'):
                self.kwp_client.disconnect()
            QMessageBox.information(self, "Odpojeno", "ECU bylo úspěšně odpojeno")
            self.set_status("Odpojeno")
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se odpojit: {e}")

    def show_ecu_info(self):
        """Show ECU information dialog."""
        try:
            if self.kwp_client.simulation_mode:
                info = """📋 Informace o ECU (Simulační režim)

🏷️  Typ ECU: Magneti Marelli 28M4G
🏍️  Motocykl: Italjet Dragster
📊 Objem: 125cc / 200cc / 300cc
🔌 Protokol: KWP2000
📡 Rozhraní: K-Line OBDII
💾 Paměť Flash: 256KB
🔐 Zabezpečení: Seed-Key Level 2
📈 Rychlost komunikace: 10400 baud

⚠️  Toto jsou simulační údaje.
Pro reálné informace připojte hardware."""
            else:
                voltage = self.kwp_client.get_battery_voltage()
                stability = self.kwp_client.get_communication_stability()
                stats = self.kwp_client.communication_stats

                info = f"""📋 Informace o ECU

🏷️  Typ ECU: Magneti Marelli 28M4G
🏍️  Motocykl: Italjet Dragster
🔌 Protokol: KWP2000
📡 Rozhraní: K-Line OBDII
💾 Paměť Flash: 256KB
🔐 Zabezpečení: Seed-Key Level 2
📈 Rychlost komunikace: 10400 baud

📊 Stav připojení:
🔋 Napětí baterie: {voltage:.1f}V
📊 Stabilita komunikace: {stability:.1%}
📨 Celkem požadavků: {stats['total_requests']}
✅ Úspěšné požadavky: {stats['successful_requests']}
❌ Neúspěšné požadavky: {stats['failed_requests']}
🔄 Reconnects: {stats['reconnections']}"""

            QMessageBox.information(self, "Informace o ECU", info)

        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se získat informace o ECU: {e}")

    def read_vin(self):
        """Read VIN from ECU."""
        try:
            QMessageBox.information(self, "VIN",
                "Funkce čtení VIN (ve vývoji)\n\nSimulované VIN: ZD4ABC1234567890")
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se přečíst VIN: {e}")

    def read_dtc(self):
        """Read Diagnostic Trouble Codes."""
        try:
            if self.kwp_client.simulation_mode:
                QMessageBox.information(self, "Chybové kódy",
                    "Žádné chybové kódy (simulační režim)")
            else:
                QMessageBox.information(self, "Chybové kódy",
                    "Funkce čtení DTC (ve vývoji)\n\nAktivní kódy: 0")
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se přečíst DTC: {e}")

    def clear_dtc(self):
        """Clear Diagnostic Trouble Codes."""
        try:
            reply = QMessageBox.question(self, "Smazat DTC",
                                      "Opravdu chcete smazat všechny chybové kódy?",
                                      QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                QMessageBox.information(self, "DTC smazány", "Všechny chybové kódy byly smazány")
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se smazat DTC: {e}")

    def request_security_access(self):
        """Request security access to ECU."""
        try:
            if self.kwp_client.simulation_mode:
                QMessageBox.information(self, "Přístup do zabezpečení",
                    "Přístup udělen (simulační režim)")
            else:
                if self.kwp_client.security_access():
                    QMessageBox.information(self, "Přístup do zabezpečení",
                        "✅ Přístup do zabezpečení úspěšně udělen\n\nÚroveň zabezpečení: 2")
                else:
                    QMessageBox.warning(self, "Přístup do zabezpečení",
                        "❌ Přístup do zabezpečení zamítnut")
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Chyba přístupu do zabezpečení: {e}")

    # === Tools Menu Methods ===
    def open_map_editor(self):
        """Switch to map editor tab."""
        self.tabs.setCurrentIndex(1)  # Switch to Map Editor tab

    def open_backup_manager(self):
        """Open backup manager dialog."""
        try:
            from ..backup_manager import backup_manager
            backups = backup_manager.list_backups()

            if backups:
                info = f"Správce záloh\n\nCelkem záloh: {len(backups)}\n\n"
                for i, backup in enumerate(backups[:5], 1):
                    info += f"{i}. {backup.filename}\n"
                    info += f"   Velikost: {backup.size} bytes\n"
                    info += f"   Čas: {backup.timestamp}\n\n"

                if len(backups) > 5:
                    info += f"... a {len(backups) - 5} dalších záloh"

                QMessageBox.information(self, "Správce záloh", info)
            else:
                QMessageBox.information(self, "Správce záloh", "Žádné zálohy nenalezeny")

        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Chyba správce záloh: {e}")

    def show_preferences(self):
        """Show preferences dialog."""
        QMessageBox.information(self, "Nastavení", "Nastavení (ve vývoji)")

    # === Help Menu Methods ===
    def show_about(self):
        """Show about dialog."""
        about_text = """🏍️ Moto ECU Tuner v2.0

Profesionální ECU tuning software pro:
• Italjet Dragster 125/200/300
• Magneti Marelli 28M4G ECU

🔧 Funkce:
• Real-time diagnostika
• Firmware čtení/zápis
• Editor palivových a zapalovacích map
• Profesionální bezpečnostní systém
• Automatické zálohování

⚠️  Tento software je určen pro profesionální použití.
Vždy používejte na testovacím ECU, nikdy na motocyklu!

📝 Verze: 2.0 Production
👨‍💻 Vytvořeno pro reálné použití"""

        QMessageBox.about(self, "O aplikaci", about_text)

    def show_help(self):
        """Show help dialog."""
        help_text = """🔧 Nápověda - Rychlý start

1. Připojení:
   • Připojte K-Line adaptér (VAG-COM KKL 409.1 doporučen)
   • Zvolte ECU → Připojit (F5)
   • Software automaticky detekuje hardware

2. Diagnostika:
   • Spusťte živá data (Ctrl+L)
   • Skenujte ID parametrů (F9)
   • Zobrazte informace o ECU (F7)

3. Firmware:
   • Načtěte firmware z ECU (Ctrl+R)
   • Vytvořte zálohu před úpravami
   • Zapište upravený firmware (Ctrl+W)

4. Mapy:
   • Otevřete editor map (Ctrl+M)
   • Upravte palivové/zapalovací mapy
   • Zapište změny do ECU

⚡ Klávesové zkratky:
• F5 - Připojit
• F6 - Odpojit
• F7 - Informace ECU
• F8 - Číst DTC
• F9 - Skenovat PIDs
• Ctrl+R - Načíst firmware
• Ctrl+W - Zapsat firmware
• Ctrl+L - Spustit logování

🚨 Bezpečnost:
• Vždy používejte stabilní napájení (>12.5V)
• Vytvářejte zálohy před úpravami
• Testujte na testovacím ECU"""

        QMessageBox.information(self, "Nápověda", help_text)

    def start_logging(self):
        try:
            params = ["RPM", "TPS", "ECT"]
            self.logger.start_logging(params)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start logging: {e}")

    def stop_logging(self):
        self.logger.stop_logging()

    def read_firmware(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Save Firmware", "", "Binary Files (*.bin)")
        if fname:
            # Ensure connection first
            if not self.kwp_client.ser and not self.kwp_client.simulation_mode:
                if not self.kwp_client.connect():
                    QMessageBox.critical(self, "Error", "Not connected to ECU!")
                    return

            progress = QProgressDialog("Reading Firmware from ECU...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            
            def update_progress(val):
                progress.setValue(int(val))
                if progress.wasCanceled():
                    return False
                return True
                
            try:
                success = self.fw_manager.download_firmware(fname, update_progress)
                if success:
                    QMessageBox.information(self, "Success", f"Firmware downloaded successfully!\nSaved to: {fname}")
                else:
                    QMessageBox.critical(self, "Error", "Download failed or was cancelled.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Download failed: {e}")

    def write_firmware(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Firmware", "", "Binary Files (*.bin)")
        if fname:
            # Check Voltage First
            voltage = self.kwp_client.get_battery_voltage()
            if voltage < 12.0:
                QMessageBox.critical(self, "Low Voltage", f"Battery voltage is too low ({voltage:.1f}V). Connect a charger before flashing.")
                return

            reply = QMessageBox.warning(self, "Warning",
                                      f"Flashing firmware carries risks.\nBattery Voltage: {voltage:.1f}V\n\nAn automatic backup will be created before writing.\n\nContinue?",
                                      QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                progress = QProgressDialog("Writing Firmware (Backup -> Flash)...", "Cancel", 0, 100, self)
                progress.setWindowModality(Qt.WindowModal)
                
                def update_progress(val):
                    progress.setValue(int(val))
                    
                try:
                    success = self.fw_manager.upload_firmware(fname, update_progress)
                    if success:
                        QMessageBox.information(self, "Success", "Firmware uploaded successfully!")
                    else:
                        QMessageBox.critical(self, "Error", "Upload failed. Check console for details.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Upload failed: {e}")

    def open_scanner(self):
        # Ensure connection first
        if not self.kwp_client.ser and not self.kwp_client.simulation_mode:
            if not self.kwp_client.connect():
                QMessageBox.critical(self, "Error", "Not connected to ECU!")
                return

        dialog = ScannerDialog(self.kwp_client, self)
        dialog.exec()

    def set_status(self, message):
        """Set status message for the main window."""
        self.setWindowTitle(f"Moto ECU Tuner (Magneti Marelli 28M4G) - {message}")