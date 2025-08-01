"""
Database configuration and models for Jarvis
Supports both local development and production deployment
"""
import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any

class DatabaseManager:
    """Simple database manager for Jarvis using SQLite for production compatibility"""
    
    def __init__(self):
        # Use environment variable for database path, default to local storage
        db_path = os.getenv('DATABASE_PATH', '/tmp/jarvis.db')
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE NOT NULL,
                        name TEXT,
                        google_id TEXT UNIQUE,
                        role TEXT DEFAULT 'user',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # Sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        user_id INTEGER,
                        data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Conversations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        user_id INTEGER,
                        title TEXT,
                        messages TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Command logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS command_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        command TEXT NOT NULL,
                        input_data TEXT,
                        output_data TEXT,
                        status TEXT DEFAULT 'success',
                        execution_time REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # File uploads table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS file_uploads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        filename TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_size INTEGER,
                        mime_type TEXT,
                        analysis_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                conn.commit()
                print(f"Database initialized at {self.db_path}")
                
        except Exception as e:
            print(f"Database initialization error: {e}")
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def create_user(self, email: str, name: str = None, google_id: str = None) -> Optional[int]:
        """Create a new user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (email, name, google_id)
                    VALUES (?, ?, ?)
                ''', (email, name, google_id))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def update_user_login(self, user_id: int):
        """Update user last login timestamp"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
        except Exception as e:
            print(f"Error updating user login: {e}")
    
    def save_conversation(self, conversation_id: str, user_id: int, title: str, messages: List[Dict]):
        """Save conversation to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO conversations 
                    (id, user_id, title, messages, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (conversation_id, user_id, title, json.dumps(messages)))
                conn.commit()
        except Exception as e:
            print(f"Error saving conversation: {e}")
    
    def get_user_conversations(self, user_id: int) -> List[Dict]:
        """Get user conversations"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, title, created_at, updated_at
                    FROM conversations 
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                ''', (user_id,))
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"Error getting conversations: {e}")
            return []
    
    def log_command(self, user_id: int, command: str, input_data: Any = None, 
                   output_data: Any = None, status: str = 'success', execution_time: float = 0):
        """Log command execution"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO command_logs 
                    (user_id, command, input_data, output_data, status, execution_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, command, 
                     json.dumps(input_data) if input_data else None,
                     json.dumps(output_data) if output_data else None,
                     status, execution_time))
                conn.commit()
        except Exception as e:
            print(f"Error logging command: {e}")
    
    def get_command_logs(self, user_id: int = None, limit: int = 100) -> List[Dict]:
        """Get command logs"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute('''
                        SELECT * FROM command_logs 
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    ''', (user_id, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM command_logs 
                        ORDER BY created_at DESC
                        LIMIT ?
                    ''', (limit,))
                
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"Error getting command logs: {e}")
            return []

# Global database instance
db = DatabaseManager()

def get_db():
    """Get database instance"""
    return db

