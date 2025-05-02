import os
import shutil
from datetime import datetime
import logging
from models import db, Detection
from flask import current_app
import json

logger = logging.getLogger(__name__)

class BackupSystem:
    def __init__(self, backup_dir='backups'):
        self.backup_dir = backup_dir
        self.detections_dir = 'detections'
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_backup(self):
        """Create a backup of all detections and database"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(self.backup_dir, f'backup_{timestamp}')
            
            # Create backup directory
            os.makedirs(backup_path, exist_ok=True)
            
            # Backup detections directory
            if os.path.exists(self.detections_dir):
                detections_backup = os.path.join(backup_path, 'detections')
                shutil.copytree(self.detections_dir, detections_backup)
                logger.info(f"Backed up detections to {detections_backup}")
            
            # Backup database
            db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if os.path.exists(db_path):
                shutil.copy2(db_path, os.path.join(backup_path, 'database.db'))
                logger.info(f"Backed up database to {backup_path}")
            
            # Create backup manifest
            manifest = {
                'timestamp': timestamp,
                'detection_count': Detection.query.count(),
                'files': {
                    'detections': len(os.listdir(self.detections_dir)) if os.path.exists(self.detections_dir) else 0,
                    'database': os.path.getsize(db_path) if os.path.exists(db_path) else 0
                }
            }
            
            with open(os.path.join(backup_path, 'manifest.json'), 'w') as f:
                json.dump(manifest, f, indent=2)
            
            logger.info(f"Created backup {timestamp} with {manifest['detection_count']} detections")
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return False
    
    def restore_backup(self, backup_name):
        """Restore from a specific backup"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_name)
            if not os.path.exists(backup_path):
                logger.error(f"Backup {backup_name} not found")
                return False
            
            # Restore detections
            detections_backup = os.path.join(backup_path, 'detections')
            if os.path.exists(detections_backup):
                if os.path.exists(self.detections_dir):
                    shutil.rmtree(self.detections_dir)
                shutil.copytree(detections_backup, self.detections_dir)
                logger.info(f"Restored detections from {detections_backup}")
            
            # Restore database
            db_backup = os.path.join(backup_path, 'database.db')
            if os.path.exists(db_backup):
                db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
                shutil.copy2(db_backup, db_path)
                logger.info(f"Restored database from {db_backup}")
            
            logger.info(f"Successfully restored backup {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            return False
    
    def list_backups(self):
        """List all available backups"""
        try:
            backups = []
            for backup in os.listdir(self.backup_dir):
                if backup.startswith('backup_'):
                    manifest_path = os.path.join(self.backup_dir, backup, 'manifest.json')
                    if os.path.exists(manifest_path):
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                            backups.append({
                                'name': backup,
                                'timestamp': manifest['timestamp'],
                                'detection_count': manifest['detection_count']
                            })
            return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
        except Exception as e:
            logger.error(f"Error listing backups: {str(e)}")
            return []
    
    def cleanup_old_backups(self, keep_last=5):
        """Remove old backups, keeping only the specified number of most recent ones"""
        try:
            backups = self.list_backups()
            if len(backups) <= keep_last:
                return
            
            for backup in backups[keep_last:]:
                backup_path = os.path.join(self.backup_dir, backup['name'])
                shutil.rmtree(backup_path)
                logger.info(f"Removed old backup {backup['name']}")
            
            return True
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {str(e)}")
            return False

# Create global instance
backup_system = BackupSystem() 