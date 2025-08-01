"""
Google OAuth Authentication Service for Jarvis
Handles Google OAuth 2.0 flow, token management, and user authentication
"""

import os
import jwt
import time
import json
import secrets
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode, parse_qs, urlparse
from flask import current_app

class GoogleAuthService:
    """Google OAuth 2.0 authentication service"""
    
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.session_secret = os.getenv('SESSION_SECRET', 'jarvis-default-secret-2024')
        self.redirect_uri = None  # Will be set dynamically based on request
        
        # OAuth endpoints
        self.auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
        self.token_url = 'https://oauth2.googleapis.com/token'
        self.userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        
        # OAuth scopes
        self.scopes = [
            'openid',
            'email',
            'profile'
        ]
        
        # Admin emails (configurable via environment)
        admin_emails = os.getenv('ADMIN_EMAILS', '')
        self.admin_emails = [email.strip() for email in admin_emails.split(',') if email.strip()]
        
        # Session storage (in production, use Redis or database)
        self.active_sessions = {}
        
        # Validate configuration
        if not self.client_id or not self.client_secret:
            print("Warning: Google OAuth credentials not configured")
    
    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured"""
        return bool(self.client_id and self.client_secret)
    
    def set_redirect_uri(self, base_url: str):
        """Set the redirect URI based on the current request"""
        self.redirect_uri = f"{base_url.rstrip('/')}/auth/callback"
    
    def generate_auth_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL"""
        if not self.is_configured():
            raise ValueError("Google OAuth not configured")
        
        if not self.redirect_uri:
            raise ValueError("Redirect URI not set")
        
        # Generate state parameter for CSRF protection
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state
        }
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        if not self.is_configured():
            raise ValueError("Google OAuth not configured")
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to exchange code for token: {str(e)}")
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google API"""
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(self.userinfo_url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to get user info: {str(e)}")
    
    def create_session_token(self, user_info: Dict[str, Any]) -> str:
        """Create a JWT session token for the user"""
        now = datetime.utcnow()
        
        # Determine user role
        role = 'admin' if user_info.get('email') in self.admin_emails else 'user'
        
        payload = {
            'user_id': user_info.get('id'),
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'picture': user_info.get('picture'),
            'role': role,
            'iat': now,
            'exp': now + timedelta(days=7),  # Token expires in 7 days
            'iss': 'jarvis-auth',
            'aud': 'jarvis-app'
        }
        
        token = jwt.encode(payload, self.session_secret, algorithm='HS256')
        
        # Store session info
        session_id = secrets.token_urlsafe(32)
        self.active_sessions[session_id] = {
            'user_id': user_info.get('id'),
            'email': user_info.get('email'),
            'role': role,
            'created_at': now.isoformat(),
            'last_activity': now.isoformat(),
            'token': token
        }
        
        return token
    
    def validate_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a JWT session token"""
        try:
            payload = jwt.decode(token, self.session_secret, algorithms=['HS256'])
            
            # Check if token is expired
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                return None
            
            # Update last activity for active sessions
            for session_id, session_data in self.active_sessions.items():
                if session_data.get('token') == token:
                    session_data['last_activity'] = datetime.utcnow().isoformat()
                    break
            
            return payload
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            print(f"Token validation error: {str(e)}")
            return None
    
    def revoke_session(self, token: str) -> bool:
        """Revoke a session token"""
        try:
            # Remove from active sessions
            sessions_to_remove = []
            for session_id, session_data in self.active_sessions.items():
                if session_data.get('token') == token:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.active_sessions[session_id]
            
            return True
        except Exception as e:
            print(f"Session revocation error: {str(e)}")
            return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session_data in self.active_sessions.items():
            try:
                token = session_data.get('token')
                if token:
                    payload = jwt.decode(token, self.session_secret, algorithms=['HS256'])
                    if now > datetime.fromtimestamp(payload['exp']):
                        expired_sessions.append(session_id)
            except jwt.InvalidTokenError:
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
                'last_activity': session_data.get('last_activity')
            })
        
        return {
            'total_sessions': len(sessions_info),
            'sessions': sessions_info
        }
    
    def authenticate_user(self, code: str, state: str = None) -> Tuple[str, Dict[str, Any]]:
        """Complete authentication flow"""
        try:
            # Exchange code for token
            token_data = self.exchange_code_for_token(code)
            access_token = token_data.get('access_token')
            
            if not access_token:
                raise Exception("No access token received")
            
            # Get user information
            user_info = self.get_user_info(access_token)
            
            # Create session token
            session_token = self.create_session_token(user_info)
            
            return session_token, user_info
            
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")
    
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
            'configured': self.is_configured(),
            'client_id': self.client_id[:10] + '...' if self.client_id else None,
            'admin_emails_count': len(self.admin_emails),
            'active_sessions': len(self.active_sessions),
            'scopes': self.scopes
        }

# Global instance
google_auth = GoogleAuthService()

