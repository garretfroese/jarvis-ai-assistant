"""
Comprehensive Logging Service for Jarvis AI Assistant
Provides activity logging, audit trails, performance monitoring, and workflow tracking.
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from dataclasses import dataclass, asdict
from enum import Enum

class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class LogCategory(Enum):
    CHAT = "chat"
    TOOL = "tool"
    FILE = "file"
    SESSION = "session"
    AUTH = "auth"
    SYSTEM = "system"
    WORKFLOW = "workflow"
    ERROR = "error"

@dataclass
class LogEntry:
    id: str
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    user_id: str
    session_id: str
    action: str
    details: Dict[str, Any]
    duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class LoggingService:
    def __init__(self, log_dir: str = "logs", max_log_files: int = 100):
        self.log_dir = log_dir
        self.max_log_files = max_log_files
        self.logs: List[LogEntry] = []
        self.max_memory_logs = 1000  # Keep last 1000 logs in memory
        
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Load recent logs from files
        self._load_recent_logs()
    
    def _load_recent_logs(self):
        """Load recent logs from files into memory"""
        try:
            log_files = sorted([f for f in os.listdir(self.log_dir) if f.endswith('.json')])
            
            # Load from most recent files
            for log_file in log_files[-5:]:  # Load last 5 files
                file_path = os.path.join(self.log_dir, log_file)
                try:
                    with open(file_path, 'r') as f:
                        for line in f:
                            if line.strip():
                                log_data = json.loads(line)
                                log_entry = self._dict_to_log_entry(log_data)
                                self.logs.append(log_entry)
                except Exception as e:
                    print(f"Error loading log file {log_file}: {e}")
            
            # Keep only recent logs in memory
            self.logs = self.logs[-self.max_memory_logs:]
            
        except Exception as e:
            print(f"Error loading logs: {e}")
    
    def _dict_to_log_entry(self, data: Dict) -> LogEntry:
        """Convert dictionary to LogEntry object"""
        return LogEntry(
            id=data['id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            level=LogLevel(data['level']),
            category=LogCategory(data['category']),
            user_id=data['user_id'],
            session_id=data['session_id'],
            action=data['action'],
            details=data['details'],
            duration_ms=data.get('duration_ms'),
            success=data.get('success', True),
            error_message=data.get('error_message'),
            metadata=data.get('metadata')
        )
    
    def _log_entry_to_dict(self, entry: LogEntry) -> Dict:
        """Convert LogEntry to dictionary for serialization"""
        data = asdict(entry)
        data['timestamp'] = entry.timestamp.isoformat()
        data['level'] = entry.level.value
        data['category'] = entry.category.value
        return data
    
    def _write_to_file(self, entry: LogEntry):
        """Write log entry to file"""
        try:
            # Create filename based on date
            date_str = entry.timestamp.strftime("%Y-%m-%d")
            filename = f"jarvis_logs_{date_str}.json"
            filepath = os.path.join(self.log_dir, filename)
            
            # Append to file
            with open(filepath, 'a') as f:
                json.dump(self._log_entry_to_dict(entry), f)
                f.write('\n')
                
        except Exception as e:
            print(f"Error writing to log file: {e}")
    
    def log(self, 
            level: LogLevel,
            category: LogCategory,
            action: str,
            user_id: str = "default",
            session_id: str = "default",
            details: Optional[Dict[str, Any]] = None,
            duration_ms: Optional[int] = None,
            success: bool = True,
            error_message: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None):
        """Log an activity"""
        
        entry = LogEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            level=level,
            category=category,
            user_id=user_id,
            session_id=session_id,
            action=action,
            details=details or {},
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            metadata=metadata
        )
        
        # Add to memory
        self.logs.append(entry)
        
        # Keep memory logs limited
        if len(self.logs) > self.max_memory_logs:
            self.logs = self.logs[-self.max_memory_logs:]
        
        # Write to file
        self._write_to_file(entry)
        
        return entry.id
    
    def log_chat_message(self, user_id: str, session_id: str, message: str, 
                        response: str, tool_used: Optional[str] = None,
                        duration_ms: Optional[int] = None):
        """Log a chat interaction"""
        details = {
            "user_message": message,
            "ai_response": response,
            "tool_used": tool_used,
            "message_length": len(message),
            "response_length": len(response)
        }
        
        return self.log(
            level=LogLevel.INFO,
            category=LogCategory.CHAT,
            action="chat_interaction",
            user_id=user_id,
            session_id=session_id,
            details=details,
            duration_ms=duration_ms
        )
    
    def log_tool_execution(self, user_id: str, session_id: str, tool_name: str,
                          tool_input: Any, tool_output: Any, success: bool = True,
                          duration_ms: Optional[int] = None, error_message: Optional[str] = None):
        """Log tool execution"""
        details = {
            "tool_name": tool_name,
            "tool_input": str(tool_input)[:500],  # Limit input length
            "tool_output": str(tool_output)[:500],  # Limit output length
            "input_type": type(tool_input).__name__,
            "output_type": type(tool_output).__name__
        }
        
        return self.log(
            level=LogLevel.INFO if success else LogLevel.ERROR,
            category=LogCategory.TOOL,
            action="tool_execution",
            user_id=user_id,
            session_id=session_id,
            details=details,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message
        )
    
    def log_file_operation(self, user_id: str, session_id: str, operation: str,
                          filename: str, file_size: Optional[int] = None,
                          success: bool = True, duration_ms: Optional[int] = None,
                          error_message: Optional[str] = None):
        """Log file operations"""
        details = {
            "operation": operation,
            "filename": filename,
            "file_size": file_size
        }
        
        return self.log(
            level=LogLevel.INFO if success else LogLevel.ERROR,
            category=LogCategory.FILE,
            action="file_operation",
            user_id=user_id,
            session_id=session_id,
            details=details,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message
        )
    
    def log_session_event(self, user_id: str, session_id: str, event: str,
                         details: Optional[Dict[str, Any]] = None):
        """Log session events"""
        return self.log(
            level=LogLevel.INFO,
            category=LogCategory.SESSION,
            action=event,
            user_id=user_id,
            session_id=session_id,
            details=details or {}
        )
    
    def log_system_event(self, event: str, details: Optional[Dict[str, Any]] = None,
                        level: LogLevel = LogLevel.INFO):
        """Log system events"""
        return self.log(
            level=level,
            category=LogCategory.SYSTEM,
            action=event,
            user_id="system",
            session_id="system",
            details=details or {}
        )
    
    def log_error(self, error_type: str, error_message: str, user_id: str = "system",
                 session_id: str = "system", details: Optional[Dict[str, Any]] = None):
        """Log errors"""
        return self.log(
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            action=error_type,
            user_id=user_id,
            session_id=session_id,
            details=details or {},
            success=False,
            error_message=error_message
        )
    
    def get_logs(self, 
                user_id: Optional[str] = None,
                session_id: Optional[str] = None,
                category: Optional[LogCategory] = None,
                level: Optional[LogLevel] = None,
                start_time: Optional[datetime] = None,
                end_time: Optional[datetime] = None,
                limit: int = 100) -> List[LogEntry]:
        """Get filtered logs"""
        
        filtered_logs = self.logs
        
        # Apply filters
        if user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == user_id]
        
        if session_id:
            filtered_logs = [log for log in filtered_logs if log.session_id == session_id]
        
        if category:
            filtered_logs = [log for log in filtered_logs if log.category == category]
        
        if level:
            filtered_logs = [log for log in filtered_logs if log.level == level]
        
        if start_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start_time]
        
        if end_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_time]
        
        # Sort by timestamp (newest first) and limit
        filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_logs[:limit]
    
    def get_statistics(self, 
                      user_id: Optional[str] = None,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get usage statistics"""
        
        logs = self.get_logs(user_id=user_id, start_time=start_time, end_time=end_time, limit=10000)
        
        stats = {
            "total_logs": len(logs),
            "by_category": {},
            "by_level": {},
            "by_user": {},
            "by_session": {},
            "tool_usage": {},
            "error_rate": 0,
            "average_response_time": 0,
            "most_active_user": None,
            "most_used_tool": None
        }
        
        total_duration = 0
        duration_count = 0
        error_count = 0
        
        for log in logs:
            # Count by category
            category_key = log.category.value
            stats["by_category"][category_key] = stats["by_category"].get(category_key, 0) + 1
            
            # Count by level
            level_key = log.level.value
            stats["by_level"][level_key] = stats["by_level"].get(level_key, 0) + 1
            
            # Count by user
            stats["by_user"][log.user_id] = stats["by_user"].get(log.user_id, 0) + 1
            
            # Count by session
            stats["by_session"][log.session_id] = stats["by_session"].get(log.session_id, 0) + 1
            
            # Track tool usage
            if log.category == LogCategory.TOOL and "tool_name" in log.details:
                tool_name = log.details["tool_name"]
                stats["tool_usage"][tool_name] = stats["tool_usage"].get(tool_name, 0) + 1
            
            # Track errors
            if not log.success:
                error_count += 1
            
            # Track response times
            if log.duration_ms:
                total_duration += log.duration_ms
                duration_count += 1
        
        # Calculate derived stats
        if len(logs) > 0:
            stats["error_rate"] = (error_count / len(logs)) * 100
        
        if duration_count > 0:
            stats["average_response_time"] = total_duration / duration_count
        
        # Find most active user
        if stats["by_user"]:
            stats["most_active_user"] = max(stats["by_user"], key=stats["by_user"].get)
        
        # Find most used tool
        if stats["tool_usage"]:
            stats["most_used_tool"] = max(stats["tool_usage"], key=stats["tool_usage"].get)
        
        return stats
    
    def get_recent_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent activity for dashboard"""
        recent_logs = self.get_logs(limit=limit)
        
        activity = []
        for log in recent_logs:
            activity.append({
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "level": log.level.value,
                "category": log.category.value,
                "action": log.action,
                "user_id": log.user_id,
                "session_id": log.session_id,
                "success": log.success,
                "duration_ms": log.duration_ms,
                "details": log.details
            })
        
        return activity
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up old log files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for filename in os.listdir(self.log_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.log_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    
                    if file_time < cutoff_date:
                        os.remove(filepath)
                        print(f"Removed old log file: {filename}")
                        
        except Exception as e:
            print(f"Error cleaning up logs: {e}")

# Global logging service instance
logging_service = LoggingService()

