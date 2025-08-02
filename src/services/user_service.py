"""
User Management Service for Jarvis
Handles user profiles, roles, permissions, and activity tracking
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import uuid

# Import authentication service
from .user_auth import auth_service

class UserService:
    """User management and profile service"""
    
    def __init__(self):
        # User storage (in production, use database)
        self.users_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.json')
        self.activity_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'user_activity.json')
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        
        # Load existing data
        self.users = self._load_users()
        self.activity_log = self._load_activity()
        
        # Role definitions
        self.roles = {
            'admin': {
                'name': 'Administrator',
                'description': 'Full system access and management',
                'permissions': [
                    'chat', 'file_upload', 'basic_tools', 'advanced_tools',
                    'system_diagnostics', 'plugin_management', 'user_management',
                    'logs_access', 'webhook_management', 'mode_switching'
                ]
            },
            'agent': {
                'name': 'Agent',
                'description': 'Advanced user with tool access',
                'permissions': [
                    'chat', 'file_upload', 'basic_tools', 'advanced_tools',
                    'mode_switching', 'logs_access'
                ]
            },
            'user': {
                'name': 'User',
                'description': 'Standard user access',
                'permissions': [
                    'chat', 'file_upload', 'basic_tools', 'mode_switching'
                ]
            },
            'guest': {
                'name': 'Guest',
                'description': 'Limited access',
                'permissions': ['chat']
            }
        }
        
        # Create default admin user if none exists
        self._ensure_admin_user()
    
    def _ensure_admin_user(self):
        """Ensure at least one admin user exists"""
        admin_users = [user for user in self.users.values() if user.get('role') == 'admin']
        
        if not admin_users:
            # Create default admin user
            admin_id = str(uuid.uuid4())
            admin_user = {
                'id': admin_id,
                'username': 'admin',
                'email': 'admin@jarvis.local',
                'password_hash': auth_service.hash_password('admin123'),
                'role': 'admin',
                'status': 'active',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'last_login': None,
                'login_count': 0,
                'preferences': {
                    'theme': 'dark',
                    'language': 'en',
                    'notifications': True
                },
                'permissions': self.get_user_permissions('admin')
            }
            
            self.users[admin_id] = admin_user
            self._save_users()
            print("✅ Default admin user created (username: admin, password: admin123)")
    
    def create_user(self, username: str, email: str, password: str, role: str = 'user') -> Optional[Dict[str, Any]]:
        """Create a new user"""
        # Validate role
        if role not in self.roles:
            return None
        
        # Check if username or email already exists
        for user in self.users.values():
            if user.get('username') == username or user.get('email') == email:
                return None
        
        # Create user
        user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        user = {
            'id': user_id,
            'username': username,
            'email': email,
            'password_hash': auth_service.hash_password(password),
            'role': role,
            'status': 'active',
            'created_at': now,
            'updated_at': now,
            'last_login': None,
            'login_count': 0,
            'preferences': {
                'theme': 'dark',
                'language': 'en',
                'notifications': True
            },
            'permissions': self.get_user_permissions(role)
        }
        
        self.users[user_id] = user
        self._save_users()
        
        # Log activity
        self.log_activity(user_id, 'user_created', {
            'username': username,
            'email': email,
            'role': role
        })
        
        # Return user without password hash
        user_copy = user.copy()
        del user_copy['password_hash']
        return user_copy
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user data with token"""
        # Find user by username or email
        user = None
        for u in self.users.values():
            if u.get('username') == username or u.get('email') == username:
                user = u
                break
        
        if not user:
            return None
        
        # Check password
        if not auth_service.verify_password(password, user['password_hash']):
            return None
        
        # Check if user is active
        if user.get('status') != 'active':
            return None
        
        # Update login info
        user['last_login'] = datetime.utcnow().isoformat()
        user['login_count'] = user.get('login_count', 0) + 1
        self._save_users()
        
        # Generate token
        user_data = {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role']
        }
        
        token = auth_service.generate_token(user_data)
        
        # Log activity
        self.log_activity(user['id'], 'user_login', {
            'username': username
        })
        
        # Return user without password hash
        user_copy = user.copy()
        del user_copy['password_hash']
        
        return {
            'success': True,
            'user': user_copy,
            'token': token
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user data"""
        token_data = auth_service.verify_token(token)
        if not token_data:
            return None
        
        # Get full user data
        user = self.users.get(token_data['id'])
        if not user or user.get('status') != 'active':
            return None
        
        # Return user without password hash
        user_copy = user.copy()
        del user_copy['password_hash']
        return user_copy
    
    def logout_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Logout user and blacklist token"""
        token_data = auth_service.verify_token(token)
        if not token_data:
            return None
        
        # Blacklist token
        success = auth_service.blacklist_token(token)
        
        if success:
            # Log activity
            self.log_activity(token_data['id'], 'user_logout', {})
            
            return {
                'success': True,
                'user_id': token_data['id']
            }
        
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        user = self.users.get(user_id)
        if user:
            user_copy = user.copy()
            del user_copy['password_hash']
            return user_copy
        return None
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (without password hashes)"""
        users = []
        for user in self.users.values():
            user_copy = user.copy()
            del user_copy['password_hash']
            users.append(user_copy)
        return users
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user data"""
        user = self.users.get(user_id)
        if not user:
            return None
        
        # Fields that can be updated
        updatable_fields = ['email', 'role', 'status', 'preferences']
        
        for field in updatable_fields:
            if field in update_data:
                if field == 'role' and update_data[field] not in self.roles:
                    continue  # Skip invalid roles
                
                user[field] = update_data[field]
                
                # Update permissions if role changed
                if field == 'role':
                    user['permissions'] = self.get_role_permissions(update_data[field])
        
        # Handle password update separately
        if 'password' in update_data:
            user['password_hash'] = auth_service.hash_password(update_data['password'])
        
        user['updated_at'] = datetime.utcnow().isoformat()
        self._save_users()
        
        # Log activity
        self.log_activity(user_id, 'user_updated', {
            'fields': list(update_data.keys())
        })
        
        # Return user without password hash
        user_copy = user.copy()
        del user_copy['password_hash']
        return user_copy
    
    def get_user_permissions(self, role: str) -> List[str]:
        """Get permissions for a role"""
        return self.roles.get(role, {}).get('permissions', [])
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics"""
        total_users = len(self.users)
        active_users = len([u for u in self.users.values() if u.get('status') == 'active'])
        
        role_counts = {}
        for user in self.users.values():
            role = user.get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1
        
        recent_logins = len([
            u for u in self.users.values()
            if u.get('last_login') and 
            datetime.fromisoformat(u['last_login']) > datetime.utcnow() - timedelta(days=7)
        ])
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'role_distribution': role_counts,
            'recent_logins_7d': recent_logins,
            'total_activity_logs': len(self.activity_log)
        }
    
    def _load_users(self) -> Dict[str, Any]:
        """Load users from storage"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading users: {e}")
        return {}
    
    def _save_users(self):
        """Save users to storage"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving users: {e}")
    
    def _load_activity(self) -> List[Dict[str, Any]]:
        """Load activity log from storage"""
        try:
            if os.path.exists(self.activity_file):
                with open(self.activity_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading activity: {e}")
        return []
    
    def _save_activity(self):
        """Save activity log to storage"""
        try:
            # Keep only last 1000 activity entries
            if len(self.activity_log) > 1000:
                self.activity_log = self.activity_log[-1000:]
            
            with open(self.activity_file, 'w') as f:
                json.dump(self.activity_log, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving activity: {e}")
    
    def log_activity(self, user_id: str, action: str, details: Dict[str, Any] = None):
        """Log user activity"""
        activity_entry = {
            'user_id': user_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': None  # Could be added from request context
        }
        
        self.activity_log.append(activity_entry)
        self._save_activity()
    
    def get_user_activity(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user activity history"""
        user_activities = [
            activity for activity in self.activity_log
            if activity.get('user_id') == user_id
        ]
        
        # Sort by timestamp (newest first)
        user_activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return user_activities[:limit] if limit else user_activities
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data"""
        if user_id not in self.users:
            return False
        
        # Remove user
        del self.users[user_id]
        
        # Remove user activity
        self.activity_log = [
            activity for activity in self.activity_log
            if activity.get('user_id') != user_id
        ]
        
        # Save changes
        self._save_users()
        self._save_activity()
        
        return True

# Global instance
user_service = UserService()

