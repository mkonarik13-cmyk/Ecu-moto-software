"""
ECU diagnostics module for reading and managing diagnostic trouble codes
Provides comprehensive DTC functionality for 28M4G ECU
"""

from typing import List, Dict, Optional, Any
import time
from datetime import datetime

from src.ecu.connection import ECUConnection
from src.maps.types import DTC, DTCStatus
from src.utils.logger import get_ecu_logger


class DTCManager:
    """
    Diagnostic Trouble Code manager for 28M4G ECU
    Handles reading, clearing, and managing DTCs
    """

    def __init__(self, ecu_connection: ECUConnection):
        self.ecu_connection = ecu_connection
        self.logger = get_ecu_logger()

        # DTC code descriptions for common motorcycle issues
        self.DTC_DESCRIPTIONS = {
            # Fuel System
            'P0171': 'System Too Lean (Bank 1)',
            'P0172': 'System Too Rich (Bank 1)',
            'P0201': 'Injector Circuit Malfunction (Cylinder 1)',
            'P0202': 'Injector Circuit Malfunction (Cylinder 2)',

            # Ignition System
            'P0300': 'Random/Multiple Cylinder Misfire Detected',
            'P0301': 'Cylinder 1 Misfire Detected',
            'P0302': 'Cylinder 2 Misfire Detected',
            'P0350': 'Ignition Coil Primary/Secondary Circuit Malfunction',

            # Sensors
            'P0101': 'Mass Air Flow (MAF) Circuit Range/Performance',
            'P0110': 'Intake Air Temperature (IAT) Circuit Malfunction',
            'P0120': 'Throttle Position Sensor (TPS) Circuit Malfunction',
            'P0130': 'O2 Sensor Circuit Malfunction (Bank 1, Sensor 1)',
            'P0335': 'Crankshaft Position Sensor Circuit Malfunction',
            'P0340': 'Camshaft Position Sensor Circuit Malfunction',

            # Temperature/Cooling
            'P0115': 'Engine Coolant Temperature (ECT) Circuit Malfunction',
            'P0125': 'Insufficient Coolant Temperature for Closed Loop Fuel Control',
            'P0217': 'Engine Over Temperature Condition',

            # Electrical System
            'P0560': 'System Voltage Malfunction',
            'P0562': 'System Voltage Low',
            'P0563': 'System Voltage High',

            # Transmission/Clutch (if applicable)
            'P0700': 'Transmission Control System (MIL Request)',
            'P0705': 'Transmission Range Sensor Circuit Malfunction',

            # Immobilizer/Security
            'B1600': 'Immobilizer Antenna Coil malfunction',
            'B1601': 'Immobilizer No Signal or Incorrect Signal',
            'B1602': 'Immobilizer Incorrect Signal Received',

            # 28M4G Specific Codes
            'U1000': 'CAN Communication Bus Error',
            'U1010': 'Lost Communication with ECU',
            'U1100': 'ECU Internal Memory Error',
            'U1200': 'Fuel Map Corruption Detected',
            'U1300': 'Ignition Map Corruption Detected',

            # Motorcycle Specific
            'C0001': 'Side Stand Switch Malfunction',
            'C0002': 'Clutch Switch Malfunction',
            'C0003': 'Neutral Switch Malfunction',
            'C0100': 'Fan Control Circuit Malfunction',
            'C0101': 'Temperature Sensor Fault',
            'C0200': 'Fuel Pump Circuit Malfunction',
        }

        # DTC severity levels
        self.DTC_SEVERITY = {
            'P': 'Powertrain',      # Engine/Transmission
            'B': 'Body',           # Body/Accessories
            'C': 'Chassis',        # Chassis/Brakes/Suspension
            'U': 'Network'         # Communication/Network
        }

    def read_dtcs(self) -> List[DTC]:
        """
        Read all diagnostic trouble codes from ECU

        Returns:
            List of DTC objects
        """
        if not self.ecu_connection or not self.ecu_connection.is_connected():
            raise Exception("ECU not connected")

        try:
            self.logger.info("Reading DTCs from ECU")

            # Use protocol to read DTCs
            if self.ecu_connection.protocol:
                protocol_dtcs = self.ecu_connection.protocol.read_dtcs()

                # Enhance with descriptions and additional info
                enhanced_dtcs = []
                for dtc in protocol_dtcs:
                    enhanced_dtc = DTC(
                        code=dtc.code,
                        description=self.get_dtc_description(dtc.code),
                        status=dtc.status,
                        occurrence_count=dtc.occurrence_count,
                        first_occurrence=dtc.first_occurrence,
                        last_occurrence=dtc.last_occurrence
                    )
                    enhanced_dtcs.append(enhanced_dtc)

                self.logger.info(f"Read {len(enhanced_dtcs)} DTCs from ECU")
                return enhanced_dtcs
            else:
                raise Exception("No protocol available for DTC reading")

        except Exception as e:
            self.logger.error(f"Failed to read DTCs: {e}")
            raise

    def clear_dtcs(self, dtc_codes: List[str] = None) -> bool:
        """
        Clear diagnostic trouble codes

        Args:
            dtc_codes: List of specific DTC codes to clear (None = all)

        Returns:
            True if successful
        """
        if not self.ecu_connection or not self.ecu_connection.is_connected():
            raise Exception("ECU not connected")

        try:
            self.logger.info(f"Clearing DTCs: {dtc_codes or 'ALL'}")

            if self.ecu_connection.protocol:
                success = self.ecu_connection.protocol.clear_dtcs()
                if success:
                    self.logger.info("DTCs cleared successfully")
                    return True
                else:
                    self.logger.error("Failed to clear DTCs")
                    return False
            else:
                raise Exception("No protocol available for DTC clearing")

        except Exception as e:
            self.logger.error(f"Failed to clear DTCs: {e}")
            raise

    def get_dtc_description(self, dtc_code: str) -> str:
        """
        Get description for DTC code

        Args:
            dtc_code: DTC code (e.g., "P0171")

        Returns:
            Human-readable description
        """
        return self.DTC_DESCRIPTIONS.get(dtc_code, f"Unknown DTC: {dtc_code}")

    def get_dtc_severity(self, dtc_code: str) -> str:
        """
        Get severity category for DTC code

        Args:
            dtc_code: DTC code

        Returns:
            Severity category string
        """
        if dtc_code and len(dtc_code) > 0:
            prefix = dtc_code[0].upper()
            return self.DTC_SEVERITY.get(prefix, 'Unknown')
        return 'Unknown'

    def analyze_dtcs(self, dtcs: List[DTC]) -> Dict[str, Any]:
        """
        Analyze DTCs and provide recommendations

        Args:
            dtcs: List of DTC objects

        Returns:
            Analysis results with recommendations
        """
        analysis = {
            'total_count': len(dtcs),
            'active_count': len([dtc for dtc in dtcs if dtc.status == DTCStatus.ACTIVE]),
            'stored_count': len([dtc for dtc in dtcs if dtc.status == DTCStatus.STORED]),
            'severity_breakdown': {},
            'common_issues': [],
            'recommendations': []
        }

        # Categorize by severity
        for dtc in dtcs:
            severity = self.get_dtc_severity(dtc.code)
            analysis['severity_breakdown'][severity] = analysis['severity_breakdown'].get(severity, 0) + 1

        # Identify common patterns and provide recommendations
        active_dtcs = [dtc for dtc in dtcs if dtc.status == DTCStatus.ACTIVE]
        stored_dtcs = [dtc for dtc in dtcs if dtc.status == DTCStatus.STORED]

        # Analyze active DTCs
        for dtc in active_dtcs:
            code = dtc.code
            if code.startswith('P01'):  # Fuel/Air metering
                analysis['common_issues'].append('Fuel system imbalance detected')
                analysis['recommendations'].append('Check air filter, fuel filter, and vacuum leaks')
            elif code.startswith('P03'):  # Ignition system
                analysis['common_issues'].append('Ignition system malfunction')
                analysis['recommendations'].append('Check spark plugs, ignition coils, and wiring')
            elif code.startswith('P05'):  # Electrical system
                analysis['common_issues'].append('Electrical system issue')
                analysis['recommendations'].append('Check battery voltage, charging system, and grounds')
            elif code.startswith('C01'):  # Cooling system
                analysis['common_issues'].append('Cooling system malfunction')
                analysis['recommendations'].append('Check coolant level, thermostat, and cooling fan')
            elif code.startswith('U'):  # Network/Communication
                analysis['common_issues'].append('Communication error')
                analysis['recommendations'].append('Check wiring harness and ECU connections')

        # Add general recommendations
        if analysis['active_count'] == 0 and analysis['stored_count'] > 0:
            analysis['recommendations'].append('No active issues found, but monitor stored DTCs')

        if analysis['active_count'] > 5:
            analysis['recommendations'].append('Multiple active DTCs - consider professional diagnosis')

        return analysis

    def get_freeze_frame_data(self, dtc_code: str) -> Optional[Dict[str, Any]]:
        """
        Get freeze frame data for specific DTC (if available)

        Args:
            dtc_code: DTC code to get freeze frame for

        Returns:
            Freeze frame data or None if not available
        """
        # This would require specific protocol commands to read freeze frame data
        # For now, return None as placeholder
        self.logger.info(f"Freeze frame data not implemented for DTC: {dtc_code}")
        return None

    def get_dtc_history(self) -> List[Dict[str, Any]]:
        """
        Get DTC occurrence history

        Returns:
            List of historical DTC records
        """
        # This would require reading additional ECU memory for history
        # For now, return empty list as placeholder
        self.logger.info("DTC history not implemented")
        return []

    def monitor_dtcs(self, callback=None):
        """
        Start continuous DTC monitoring

        Args:
            callback: Function to call when DTC status changes
        """
        # This would implement continuous monitoring in a background thread
        # For now, just log the request
        self.logger.info("Continuous DTC monitoring not implemented")

    def get_dtc_statistics(self) -> Dict[str, Any]:
        """
        Get DTC statistics for the current session

        Returns:
            Statistics dictionary
        """
        return {
            'session_start': datetime.now(),
            'dtcs_cleared': 0,
            'dtcs_detected': 0,
            'last_check': None
        }


class DiagnosticReport:
    """Generate comprehensive diagnostic reports"""

    def __init__(self, dtc_manager: DTCManager):
        self.dtc_manager = dtc_manager
        self.logger = get_ecu_logger()

    def generate_report(self, dtcs: List[DTC], include_analysis: bool = True) -> str:
        """
        Generate comprehensive diagnostic report

        Args:
            dtcs: List of DTCs to include in report
            include_analysis: Whether to include analysis and recommendations

        Returns:
            Formatted report string
        """
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("ECU DIAGNOSTIC REPORT")
        report_lines.append("=" * 60)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Total DTCs: {len(dtcs)}")
        report_lines.append("")

        if not dtcs:
            report_lines.append("No diagnostic trouble codes found.")
            report_lines.append("")
            report_lines.append("ECU appears to be operating normally.")
            return "\n".join(report_lines)

        # Group DTCs by status
        active_dtcs = [dtc for dtc in dtcs if dtc.status == DTCStatus.ACTIVE]
        stored_dtcs = [dtc for dtc in dtcs if dtc.status == DTCStatus.STORED]

        # Active DTCs section
        if active_dtcs:
            report_lines.append("ACTIVE DIAGNOSTIC TROUBLE CODES")
            report_lines.append("-" * 40)
            for i, dtc in enumerate(active_dtcs, 1):
                severity = self.dtc_manager.get_dtc_severity(dtc.code)
                report_lines.append(f"{i}. {dtc.code} - {severity}")
                report_lines.append(f"   Description: {dtc.description}")
                report_lines.append(f"   Occurrences: {dtc.occurrence_count}")
                report_lines.append(f"   Last seen: {dtc.last_occurrence.strftime('%Y-%m-%d %H:%M:%S')}")
                report_lines.append("")

        # Stored DTCs section
        if stored_dtcs:
            report_lines.append("STORED DIAGNOSTIC TROUBLE CODES")
            report_lines.append("-" * 40)
            for i, dtc in enumerate(stored_dtcs, 1):
                severity = self.dtc_manager.get_dtc_severity(dtc.code)
                report_lines.append(f"{i}. {dtc.code} - {severity}")
                report_lines.append(f"   Description: {dtc.description}")
                report_lines.append(f"   First seen: {dtc.first_occurrence.strftime('%Y-%m-%d %H:%M:%S')}")
                report_lines.append("")

        # Analysis section
        if include_analysis:
            analysis = self.dtc_manager.analyze_dtcs(dtcs)
            report_lines.append("ANALYSIS AND RECOMMENDATIONS")
            report_lines.append("-" * 40)
            report_lines.append(f"Active DTCs: {analysis['active_count']}")
            report_lines.append(f"Stored DTCs: {analysis['stored_count']}")
            report_lines.append("")

            if analysis['severity_breakdown']:
                report_lines.append("Severity Breakdown:")
                for severity, count in analysis['severity_breakdown'].items():
                    report_lines.append(f"  {severity}: {count}")
                report_lines.append("")

            if analysis['common_issues']:
                report_lines.append("Identified Issues:")
                for issue in analysis['common_issues']:
                    report_lines.append(f"  • {issue}")
                report_lines.append("")

            if analysis['recommendations']:
                report_lines.append("Recommendations:")
                for rec in analysis['recommendations']:
                    report_lines.append(f"  • {rec}")
                report_lines.append("")

        # Footer
        report_lines.append("=" * 60)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 60)

        return "\n".join(report_lines)

    def save_report(self, dtcs: List[DTC], filename: str) -> bool:
        """
        Save diagnostic report to file

        Args:
            dtcs: List of DTCs to include
            filename: Output filename

        Returns:
            True if successful
        """
        try:
            report = self.generate_report(dtcs)

            with open(filename, 'w') as f:
                f.write(report)

            self.logger.info(f"Diagnostic report saved to: {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save diagnostic report: {e}")
            return False