"""
Storage utilities for Jarvis production deployment
Handles file storage, logs, and temporary data
"""
import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class StorageManager:
    """Manages file storage for Jarvis in production environment"""
    
    def __init__(self):
        # Use /tmp for ephemeral storage on Render
        self.base_path = Path(os.getenv('STORAGE_PATH', '/tmp/jarvis'))
        self.logs_path = self.base_path / 'logs'
        self.uploads_path = self.base_path / 'uploads'
        self.temp_path = self.base_path / 'temp'
        
        # Create directories
        self.init_storage()
    
    def init_storage(self):
        """Initialize storage directories"""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            self.logs_path.mkdir(parents=True, exist_ok=True)
            self.uploads_path.mkdir(parents=True, exist_ok=True)
            self.temp_path.mkdir(parents=True, exist_ok=True)
            print(f"Storage initialized at {self.base_path}")
        except Exception as e:
            print(f"Storage initialization error: {e}")
    
    def save_file(self, file_data: bytes, filename: str, category: str = 'uploads') -> Optional[str]:
        """Save file to storage"""
        try:
            if category == 'uploads':
                file_path = self.uploads_path / filename
            elif category == 'temp':
                file_path = self.temp_path / filename
            else:
                file_path = self.base_path / category / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            return str(file_path)
        except Exception as e:
            print(f"Error saving file: {e}")
            return None
    
    def read_file(self, file_path: str) -> Optional[bytes]:
        """Read file from storage"""
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    
    def save_log(self, log_data: Dict[str, Any], log_type: str = 'general') -> bool:
        """Save log entry"""
        try:
            timestamp = datetime.now().isoformat()
            log_file = self.logs_path / f"{log_type}_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            log_entry = {
                'timestamp': timestamp,
                **log_data
            }
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            return True
        except Exception as e:
            print(f"Error saving log: {e}")
            return False
    
    def read_logs(self, log_type: str = 'general', limit: int = 100) -> List[Dict]:
        """Read log entries"""
        try:
            log_file = self.logs_path / f"{log_type}_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            if not log_file.exists():
                return []
            
            logs = []
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Get last 'limit' lines
                for line in lines[-limit:]:
                    try:
                        logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
            
            return logs
        except Exception as e:
            print(f"Error reading logs: {e}")
            return []
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up temporary files older than max_age_hours"""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for file_path in self.temp_path.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        print(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            print(f"Error cleaning temp files: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stats = {
                'base_path': str(self.base_path),
                'total_files': 0,
                'total_size': 0,
                'categories': {}
            }
            
            for category_path in [self.logs_path, self.uploads_path, self.temp_path]:
                if category_path.exists():
                    category_files = list(category_path.rglob('*'))
                    category_size = sum(f.stat().st_size for f in category_files if f.is_file())
                    
                    stats['categories'][category_path.name] = {
                        'files': len([f for f in category_files if f.is_file()]),
                        'size': category_size
                    }
                    
                    stats['total_files'] += stats['categories'][category_path.name]['files']
                    stats['total_size'] += category_size
            
            return stats
        except Exception as e:
            print(f"Error getting storage stats: {e}")
            return {'error': str(e)}

# Global storage instance
storage = StorageManager()

def get_storage():
    """Get storage instance"""
    return storage

