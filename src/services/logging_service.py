"""
Command Execution Logging Service for Jarvis
Provides centralized logging of all command executions and tool usage
"""

import os
import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

class LoggingService:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'jarvis_logs.db')
        self.ensure_data_directory()
        self.init_database()
    
    def ensure_data_directory(self):
        """Ensure the data directory exists"""
        data_dir = os.path.dirname(self.db_path)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def init_database(self):
        """Initialize the SQLite database with required tables"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS command_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    command TEXT NOT NULL,
                    tool_name TEXT,
                    status TEXT NOT NULL,
                    output TEXT,
                    error_message TEXT,
                    duration_ms INTEGER,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost_estimate REAL,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better query performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON command_logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON command_logs(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tool_name ON command_logs(tool_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON command_logs(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON command_logs(session_id)')
            
            conn.commit()
    
    @contextmanager
    def get_db_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def log_command_execution(self, 
                            command: str,
                            tool_name: str = None,
                            status: str = 'success',
                            output: str = None,
                            error_message: str = None,
                            duration_ms: int = None,
                            user_id: str = None,
                            session_id: str = None,
                            input_tokens: int = None,
                            output_tokens: int = None,
                            cost_estimate: float = None,
                            metadata: Dict[str, Any] = None) -> int:
        """
        Log a command execution
        
        Returns:
            int: The ID of the created log entry
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            metadata_json = json.dumps(metadata) if metadata else None
            
            # Truncate output if too long (keep first 1000 chars for summary)
            output_summary = output[:1000] + '...' if output and len(output) > 1000 else output
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO command_logs 
                    (timestamp, user_id, session_id, command, tool_name, status, 
                     output, error_message, duration_ms, input_tokens, output_tokens, 
                     cost_estimate, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp, user_id, session_id, command, tool_name, status,
                    output_summary, error_message, duration_ms, input_tokens, 
                    output_tokens, cost_estimate, metadata_json
                ))
                
                log_id = cursor.lastrowid
                conn.commit()
                return log_id
                
        except Exception as e:
            print(f"Error logging command execution: {e}")
            return None
    
    def get_logs(self, 
                 limit: int = 100,
                 offset: int = 0,
                 user_id: str = None,
                 session_id: str = None,
                 tool_name: str = None,
                 status: str = None,
                 start_date: str = None,
                 end_date: str = None,
                 search_query: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve logs with filtering options
        
        Args:
            limit: Maximum number of logs to return
            offset: Number of logs to skip
            user_id: Filter by user ID
            session_id: Filter by session ID
            tool_name: Filter by tool name
            status: Filter by status (success/error)
            start_date: Filter logs after this date (ISO format)
            end_date: Filter logs before this date (ISO format)
            search_query: Search in command and output text
        
        Returns:
            List of log entries as dictionaries
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with filters
                query = "SELECT * FROM command_logs WHERE 1=1"
                params = []
                
                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)
                
                if session_id:
                    query += " AND session_id = ?"
                    params.append(session_id)
                
                if tool_name:
                    query += " AND tool_name = ?"
                    params.append(tool_name)
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date)
                
                if search_query:
                    query += " AND (command LIKE ? OR output LIKE ?)"
                    search_pattern = f"%{search_query}%"
                    params.extend([search_pattern, search_pattern])
                
                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                logs = []
                for row in rows:
                    log_entry = dict(row)
                    
                    # Parse metadata if present
                    if log_entry['metadata']:
                        try:
                            log_entry['metadata'] = json.loads(log_entry['metadata'])
                        except json.JSONDecodeError:
                            log_entry['metadata'] = {}
                    
                    logs.append(log_entry)
                
                return logs
                
        except Exception as e:
            print(f"Error retrieving logs: {e}")
            return []
    
    def get_log_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific log entry by ID with full output"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM command_logs WHERE id = ?", (log_id,))
                row = cursor.fetchone()
                
                if row:
                    log_entry = dict(row)
                    
                    # Parse metadata if present
                    if log_entry['metadata']:
                        try:
                            log_entry['metadata'] = json.loads(log_entry['metadata'])
                        except json.JSONDecodeError:
                            log_entry['metadata'] = {}
                    
                    return log_entry
                
                return None
                
        except Exception as e:
            print(f"Error retrieving log by ID: {e}")
            return None
    
    def get_log_statistics(self, 
                          start_date: str = None,
                          end_date: str = None) -> Dict[str, Any]:
        """Get statistics about logged commands"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Base query conditions
                where_clause = "WHERE 1=1"
                params = []
                
                if start_date:
                    where_clause += " AND timestamp >= ?"
                    params.append(start_date)
                
                if end_date:
                    where_clause += " AND timestamp <= ?"
                    params.append(end_date)
                
                # Total commands
                cursor.execute(f"SELECT COUNT(*) FROM command_logs {where_clause}", params)
                total_commands = cursor.fetchone()[0]
                
                # Success rate
                cursor.execute(f"SELECT COUNT(*) FROM command_logs {where_clause} AND status = 'success'", params)
                successful_commands = cursor.fetchone()[0]
                
                # Most used tools
                cursor.execute(f"""
                    SELECT tool_name, COUNT(*) as count 
                    FROM command_logs {where_clause} AND tool_name IS NOT NULL
                    GROUP BY tool_name 
                    ORDER BY count DESC 
                    LIMIT 10
                """, params)
                top_tools = [{'tool': row[0], 'count': row[1]} for row in cursor.fetchall()]
                
                # Average duration
                cursor.execute(f"""
                    SELECT AVG(duration_ms) 
                    FROM command_logs {where_clause} AND duration_ms IS NOT NULL
                """, params)
                avg_duration = cursor.fetchone()[0] or 0
                
                # Commands by status
                cursor.execute(f"""
                    SELECT status, COUNT(*) as count 
                    FROM command_logs {where_clause}
                    GROUP BY status
                """, params)
                status_breakdown = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Token usage
                cursor.execute(f"""
                    SELECT SUM(input_tokens), SUM(output_tokens), SUM(cost_estimate)
                    FROM command_logs {where_clause}
                """, params)
                token_stats = cursor.fetchone()
                
                return {
                    'total_commands': total_commands,
                    'successful_commands': successful_commands,
                    'success_rate': (successful_commands / total_commands * 100) if total_commands > 0 else 0,
                    'top_tools': top_tools,
                    'average_duration_ms': round(avg_duration, 2),
                    'status_breakdown': status_breakdown,
                    'total_input_tokens': token_stats[0] or 0,
                    'total_output_tokens': token_stats[1] or 0,
                    'total_cost_estimate': round(token_stats[2] or 0, 4)
                }
                
        except Exception as e:
            print(f"Error getting log statistics: {e}")
            return {}
    
    def delete_old_logs(self, days_to_keep: int = 30) -> int:
        """Delete logs older than specified days"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            cutoff_iso = cutoff_date.isoformat()
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM command_logs WHERE timestamp < ?", (cutoff_iso,))
                deleted_count = cursor.rowcount
                conn.commit()
                
                return deleted_count
                
        except Exception as e:
            print(f"Error deleting old logs: {e}")
            return 0
    
    def export_logs_to_csv(self, 
                          filename: str,
                          start_date: str = None,
                          end_date: str = None) -> bool:
        """Export logs to CSV file"""
        try:
            import csv
            
            logs = self.get_logs(
                limit=10000,  # Large limit for export
                start_date=start_date,
                end_date=end_date
            )
            
            if not logs:
                return False
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'id', 'timestamp', 'user_id', 'session_id', 'command',
                    'tool_name', 'status', 'output', 'error_message',
                    'duration_ms', 'input_tokens', 'output_tokens', 'cost_estimate'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for log in logs:
                    # Remove metadata for CSV export (too complex)
                    log_copy = {k: v for k, v in log.items() if k != 'metadata'}
                    writer.writerow(log_copy)
            
            return True
            
        except Exception as e:
            print(f"Error exporting logs to CSV: {e}")
            return False

# Global logging service instance
logging_service = LoggingService()

def log_command(command: str, **kwargs) -> int:
    """Convenience function to log a command execution"""
    return logging_service.log_command_execution(command, **kwargs)

def log_tool_execution(tool_name: str, command: str, **kwargs) -> int:
    """Convenience function to log a tool execution"""
    return logging_service.log_command_execution(
        command=command,
        tool_name=tool_name,
        **kwargs
    )

