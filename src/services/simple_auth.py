"""
Simple Authentication Service for Jarvis (without JWT)
Basic session management using secure tokens
"""

import os
import time
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class SimpleAuthService:
    """Simple authentication service without JWT dependency"""
    
    def __init__(self):
        self.session_secret = os.getenv('SESSION_SECRET', 'jarvis-default-secret-2024')
        self.admin_emails = []
        
        # Admin emails (configurable via environment)
        admin_emails = os.getenv('ADMIN_EMAILS', '')
        if admin_emails:
            self.admin_emails = [email.strip() for email in admin_emails.split(',') if email.strip()]
        
        # Session storage (in production, use Redis or database)
        self.active_sessions = {}
        
        print(f"Simple auth initialized with {len(self.admin_emails)} admin emails")
    
    def is_configured(self) -> bool:
        """Check if authentication is configured"""
        return True  # Simple auth is always available
    
    def create_session_token(self, user_info: Dict[str, Any]) -> str:
        """Create a simple session token"""
        now = datetime.utcnow()
        
        # Determine user role
        role = 'admin' if user_info.get('email') in self.admin_emails else 'user'
        
        # Create session ID
        session_id = secrets.token_urlsafe(32)
        
        # Create token data
        token_data = {
            'session_id': session_id,
            'user_id': user_info.get('id', user_info.get('email')),
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'picture': user_info.get('picture'),
            'role': role,
            'created_at': now.isoformat(),
            'expires_at': (now + timedelta(days=7)).isoformat()
        }
        
        # Store session
        self.active_sessions[session_id] = token_data
        
        return session_id
    
    def validate_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a session token"""
        session_data = self.active_sessions.get(token)
        
        if not session_data:
            return None
        
        # Check if expired
        expires_at = datetime.fromisoformat(session_data['expires_at'])
        if datetime.utcnow() > expires_at:
            # Remove expired session
            del self.active_sessions[token]
            return None
        
        return session_data
    
    def revoke_session(self, token: str) -> bool:
        """Revoke a session token"""
        if token in self.active_sessions:
            del self.active_sessions[token]
            return True
        return False
    
    def get_user_role(self, email: str) -> str:
        """Get user role based on email"""
        if email in self.admin_emails:
            return 'admin'
        return 'user'
    
    def is_admin(self, user_data: Dict[str, Any]) -> bool:
        """Check if user has admin role"""
        return user_data.get('role') == 'admin'
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication service status"""
        return {
            'configured': True,
            'provider': 'simple',
            'admin_emails_count': len(self.admin_emails),
            'active_sessions': len(self.active_sessions)
        }
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session_data in self.active_sessions.items():
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            if now > expires_at:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        return len(expired_sessions)
    
    def get_active_sessions(self) -> Dict[str, Any]:
        """Get information about active sessions"""
        self.cleanup_expired_sessions()
        
        sessions_info = []
        for session_id, session_data in self.active_sessions.items():
            sessions_info.append({
                'session_id': session_id,
                'email': session_data.get('email'),
                'role': session_data.get('role'),
                'created_at': session_data.get('created_at'),
                'expires_at': session_data.get('expires_at')
            })
        
        return {
            'total_sessions': len(sessions_info),
            'sessions': sessions_info
        }

# Global instance
simple_auth = SimpleAuthService()

