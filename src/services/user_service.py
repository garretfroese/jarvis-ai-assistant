"""
User Management Service for Jarvis
Handles user profiles, roles, permissions, and activity tracking
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from ..services.google_auth import google_auth

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
                    'chat', 'file_upload', 'basic_tools'
                ]
            },
            'viewer': {
                'name': 'Viewer',
                'description': 'Read-only access',
                'permissions': [
                    'chat'
                ]
            }
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
    
    def create_or_update_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update user profile"""
        user_id = user_data.get('user_id') or user_data.get('id')
        email = user_data.get('email')
        
        if not user_id or not email:
            raise ValueError("User ID and email are required")
        
        now = datetime.utcnow().isoformat()
        
        # Check if user exists
        existing_user = self.users.get(user_id)
        
        if existing_user:
            # Update existing user
            existing_user.update({
                'name': user_data.get('name', existing_user.get('name')),
                'picture': user_data.get('picture', existing_user.get('picture')),
                'last_login': now,
                'login_count': existing_user.get('login_count', 0) + 1,
                'updated_at': now
            })
            user_profile = existing_user
        else:
            # Create new user
            # Determine initial role
            role = google_auth.get_user_role(email)
            
            user_profile = {
                'user_id': user_id,
                'email': email,
                'name': user_data.get('name'),
                'picture': user_data.get('picture'),
                'role': role,
                'status': 'active',
                'created_at': now,
                'updated_at': now,
                'last_login': now,
                'login_count': 1,
                'preferences': {
                    'theme': 'dark',
                    'language': 'en',
                    'notifications': True
                },
                'permissions': self.get_role_permissions(role)
            }
            
            self.users[user_id] = user_profile
        
        # Log activity
        self.log_activity(user_id, 'login', {
            'email': email,
            'name': user_data.get('name')
        })
        
        # Save to storage
        self._save_users()
        
        return user_profile
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        for user in self.users.values():
            if user.get('email') == email:
                return user
        return None
    
    def update_user_role(self, user_id: str, new_role: str) -> bool:
        """Update user role"""
        if new_role not in self.roles:
            return False
        
        user = self.users.get(user_id)
        if not user:
            return False
        
        old_role = user.get('role')
        user['role'] = new_role
        user['permissions'] = self.get_role_permissions(new_role)
        user['updated_at'] = datetime.utcnow().isoformat()
        
        # Log activity
        self.log_activity(user_id, 'role_change', {
            'old_role': old_role,
            'new_role': new_role
        })
        
        self._save_users()
        return True
    
    def update_user_status(self, user_id: str, status: str) -> bool:
        """Update user status (active, suspended, disabled)"""
        valid_statuses = ['active', 'suspended', 'disabled']
        if status not in valid_statuses:
            return False
        
        user = self.users.get(user_id)
        if not user:
            return False
        
        old_status = user.get('status')
        user['status'] = status
        user['updated_at'] = datetime.utcnow().isoformat()
        
        # Log activity
        self.log_activity(user_id, 'status_change', {
            'old_status': old_status,
            'new_status': status
        })
        
        self._save_users()
        return True
    
    def get_role_permissions(self, role: str) -> List[str]:
        """Get permissions for a role"""
        return self.roles.get(role, {}).get('permissions', [])
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        if user.get('status') != 'active':
            return False
        
        permissions = user.get('permissions', [])
        return permission in permissions
    
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
        
        return user_activities[:limit]
    
    def get_all_users(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get all users"""
        users = list(self.users.values())
        
        if not include_inactive:
            users = [user for user in users if user.get('status') == 'active']
        
        # Sort by last login (newest first)
        users.sort(key=lambda x: x.get('last_login', ''), reverse=True)
        
        return users
    
    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Get users by role"""
        return [
            user for user in self.users.values()
            if user.get('role') == role and user.get('status') == 'active'
        ]
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        current_prefs = user.get('preferences', {})
        current_prefs.update(preferences)
        user['preferences'] = current_prefs
        user['updated_at'] = datetime.utcnow().isoformat()
        
        self._save_users()
        return True
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        total_users = len(self.users)
        active_users = len([u for u in self.users.values() if u.get('status') == 'active'])
        
        # Count by role
        role_counts = {}
        for role in self.roles.keys():
            role_counts[role] = len(self.get_users_by_role(role))
        
        # Recent activity (last 24 hours)
        recent_cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        recent_activity = len([
            activity for activity in self.activity_log
            if activity.get('timestamp', '') > recent_cutoff
        ])
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'role_distribution': role_counts,
            'recent_activity_24h': recent_activity,
            'available_roles': list(self.roles.keys())
        }
    
    def cleanup_old_activity(self, days: int = 30):
        """Clean up old activity logs"""
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        original_count = len(self.activity_log)
        self.activity_log = [
            activity for activity in self.activity_log
            if activity.get('timestamp', '') > cutoff_date
        ]
        
        cleaned_count = original_count - len(self.activity_log)
        
        if cleaned_count > 0:
            self._save_activity()
        
        return cleaned_count
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export all data for a specific user"""
        user = self.users.get(user_id)
        if not user:
            return None
        
        user_activity = self.get_user_activity(user_id, limit=None)
        
        return {
            'profile': user,
            'activity': user_activity,
            'export_timestamp': datetime.utcnow().isoformat()
        }
    
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

