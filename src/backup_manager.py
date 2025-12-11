"""
Professional backup management system for ECU firmware.
Provides comprehensive backup, restore, and version management.
"""
import os
import time
import shutil
import hashlib
import json
from typing import List, Optional, Dict
from dataclasses import dataclass
from pathlib import Path

@dataclass
class BackupMetadata:
    """Metadata for ECU firmware backup."""
    filename: str
    timestamp: float
    size: int
    checksum: str
    ecu_type: str
    original_filename: Optional[str] = None
    description: Optional[str] = None
    firmware_version: Optional[str] = None

class BackupManager:
    """Professional backup management for ECU firmware operations."""

    def __init__(self, backup_directory: str = "ecu_backups"):
        self.backup_directory = Path(backup_directory)
        self.backup_directory.mkdir(exist_ok=True)
        self.metadata_file = self.backup_directory / "backup_metadata.json"
        self.max_backups = 10  # Maximum number of backups to keep

    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum for firmware data."""
        return hashlib.sha256(data).hexdigest()

    def _load_metadata(self) -> Dict:
        """Load backup metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading metadata: {e}")
                return {}
        return {}

    def _save_metadata(self, metadata: Dict):
        """Save backup metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
        except IOError as e:
            print(f"Error saving metadata: {e}")

    def create_backup(self, firmware_data: bytes, ecu_type: str = "unknown",
                     description: str = "", original_filename: Optional[str] = None) -> BackupMetadata:
        """Create a new backup of ECU firmware."""
        timestamp = time.time()
        checksum = self._calculate_checksum(firmware_data)

        # Generate backup filename
        timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(timestamp))
        backup_filename = f"backup_{ecu_type}_{timestamp_str}.bin"
        backup_path = self.backup_directory / backup_filename

        # Save firmware data
        try:
            with open(backup_path, 'wb') as f:
                f.write(firmware_data)

            # Create metadata
            metadata = BackupMetadata(
                filename=backup_filename,
                timestamp=timestamp,
                size=len(firmware_data),
                checksum=checksum,
                ecu_type=ecu_type,
                original_filename=original_filename,
                description=description
            )

            # Load existing metadata and add new entry
            all_metadata = self._load_metadata()
            all_metadata[backup_filename] = {
                'timestamp': metadata.timestamp,
                'size': metadata.size,
                'checksum': metadata.checksum,
                'ecu_type': metadata.ecu_type,
                'original_filename': metadata.original_filename,
                'description': metadata.description
            }

            # Save updated metadata
            self._save_metadata(all_metadata)

            # Clean up old backups if needed
            self._cleanup_old_backups()

            print(f"Backup created: {backup_filename} ({metadata.size} bytes)")
            return metadata

        except IOError as e:
            print(f"Error creating backup: {e}")
            raise

    def restore_backup(self, backup_filename: str) -> bytes:
        """Restore firmware data from backup."""
        backup_path = self.backup_directory / backup_filename

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_filename}")

        try:
            with open(backup_path, 'rb') as f:
                data = f.read()

            # Verify checksum
            metadata = self.get_backup_metadata(backup_filename)
            if metadata:
                current_checksum = self._calculate_checksum(data)
                if current_checksum != metadata.checksum:
                    raise ValueError(f"Checksum mismatch for backup {backup_filename}")

            print(f"Backup restored: {backup_filename} ({len(data)} bytes)")
            return data

        except IOError as e:
            print(f"Error restoring backup: {e}")
            raise

    def get_backup_metadata(self, backup_filename: str) -> Optional[BackupMetadata]:
        """Get metadata for a specific backup."""
        all_metadata = self._load_metadata()
        backup_data = all_metadata.get(backup_filename)

        if backup_data:
            return BackupMetadata(
                filename=backup_filename,
                timestamp=backup_data['timestamp'],
                size=backup_data['size'],
                checksum=backup_data['checksum'],
                ecu_type=backup_data['ecu_type'],
                original_filename=backup_data.get('original_filename'),
                description=backup_data.get('description')
            )
        return None

    def list_backups(self) -> List[BackupMetadata]:
        """List all available backups."""
        backups = []
        all_metadata = self._load_metadata()

        for backup_filename, backup_data in all_metadata.items():
            backups.append(BackupMetadata(
                filename=backup_filename,
                timestamp=backup_data['timestamp'],
                size=backup_data['size'],
                checksum=backup_data['checksum'],
                ecu_type=backup_data['ecu_type'],
                original_filename=backup_data.get('original_filename'),
                description=backup_data.get('description')
            ))

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.timestamp, reverse=True)
        return backups

    def delete_backup(self, backup_filename: str) -> bool:
        """Delete a specific backup."""
        backup_path = self.backup_directory / backup_filename

        try:
            if backup_path.exists():
                backup_path.unlink()

            # Remove from metadata
            all_metadata = self._load_metadata()
            if backup_filename in all_metadata:
                del all_metadata[backup_filename]
                self._save_metadata(all_metadata)

            print(f"Backup deleted: {backup_filename}")
            return True

        except Exception as e:
            print(f"Error deleting backup: {e}")
            return False

    def _cleanup_old_backups(self):
        """Remove old backups if we exceed the maximum limit."""
        backups = self.list_backups()

        if len(backups) > self.max_backups:
            # Remove oldest backups
            backups_to_remove = backups[self.max_backups:]
            for backup in backups_to_remove:
                self.delete_backup(backup.filename)

    def verify_backup_integrity(self, backup_filename: str) -> bool:
        """Verify the integrity of a backup file."""
        try:
            metadata = self.get_backup_metadata(backup_filename)
            if not metadata:
                return False

            backup_path = self.backup_directory / backup_filename
            if not backup_path.exists():
                return False

            with open(backup_path, 'rb') as f:
                data = f.read()

            current_checksum = self._calculate_checksum(data)
            return current_checksum == metadata.checksum

        except Exception:
            return False

    def get_latest_backup(self, ecu_type: Optional[str] = None) -> Optional[BackupMetadata]:
        """Get the most recent backup, optionally filtered by ECU type."""
        backups = self.list_backups()

        if ecu_type:
            backups = [b for b in backups if b.ecu_type == ecu_type]

        return backups[0] if backups else None

    def export_backup(self, backup_filename: str, export_path: str) -> bool:
        """Export a backup to an external location."""
        backup_path = self.backup_directory / backup_filename
        export_path = Path(export_path)

        try:
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_filename}")

            # Create export directory if needed
            export_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy backup file
            shutil.copy2(backup_path, export_path)

            # Also copy metadata
            metadata = self.get_backup_metadata(backup_filename)
            if metadata:
                metadata_path = export_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump({
                        'filename': metadata.filename,
                        'timestamp': metadata.timestamp,
                        'size': metadata.size,
                        'checksum': metadata.checksum,
                        'ecu_type': metadata.ecu_type,
                        'original_filename': metadata.original_filename,
                        'description': metadata.description
                    }, f, indent=2, default=str)

            print(f"Backup exported: {export_path}")
            return True

        except Exception as e:
            print(f"Error exporting backup: {e}")
            return False

    def import_backup(self, import_path: str, ecu_type: Optional[str] = None) -> bool:
        """Import a backup from an external location."""
        import_path = Path(import_path)

        try:
            if not import_path.exists():
                raise FileNotFoundError(f"Import file not found: {import_path}")

            # Load firmware data
            with open(import_path, 'rb') as f:
                firmware_data = f.read()

            # Try to load metadata
            metadata_path = import_path.with_suffix('.json')
            description = ""
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    import_metadata = json.load(f)
                    description = import_metadata.get('description', '')
                    ecu_type = ecu_type or import_metadata.get('ecu_type', 'imported')

            # Create backup
            self.create_backup(
                firmware_data=firmware_data,
                ecu_type=ecu_type or 'imported',
                description=f"Imported: {description}" or "Imported backup",
                original_filename=import_path.name
            )

            print(f"Backup imported: {import_path}")
            return True

        except Exception as e:
            print(f"Error importing backup: {e}")
            return False

    def get_backup_statistics(self) -> Dict:
        """Get statistics about the backup collection."""
        backups = self.list_backups()

        if not backups:
            return {
                'total_backups': 0,
                'total_size': 0,
                'oldest_backup': None,
                'newest_backup': None,
                'ecu_types': []
            }

        total_size = sum(b.size for b in backups)
        ecu_types = list(set(b.ecu_type for b in backups))

        return {
            'total_backups': len(backups),
            'total_size': total_size,
            'oldest_backup': min(b.timestamp for b in backups),
            'newest_backup': max(b.timestamp for b in backups),
            'ecu_types': ecu_types
        }


# Global backup manager instance
backup_manager = BackupManager()


def create_ecu_backup(firmware_data: bytes, ecu_type: str = "28M4G",
                     description: str = "") -> Optional[BackupMetadata]:
    """Convenience function to create ECU backup."""
    try:
        return backup_manager.create_backup(firmware_data, ecu_type, description)
    except Exception as e:
        print(f"Failed to create backup: {e}")
        return None


def restore_ecu_backup(backup_filename: str) -> Optional[bytes]:
    """Convenience function to restore ECU backup."""
    try:
        return backup_manager.restore_backup(backup_filename)
    except Exception as e:
        print(f"Failed to restore backup: {e}")
        return None