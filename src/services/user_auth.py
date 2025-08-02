"""
Authentication Service for Jarvis
Handles JWT tokens, password hashing, and user authentication
"""

import os
import jwt
import bcrypt
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class AuthService:
    """Authentication service with JWT support"""
    
    def __init__(self):
        # JWT configuration
        self.jwt_secret = os.getenv('JWT_SECRET', 'jarvis-secret-key-change-in-production')
        self.jwt_algorithm = 'HS256'
        self.token_expiry_hours = 24
        
        # Token blacklist (in production, use Redis or database)
        self.blacklisted_tokens = set()
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    def generate_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT token for user"""
        payload = {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'email': user_data['email'],
            'role': user_data['role'],
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            'jti': str(uuid.uuid4())  # JWT ID for token tracking
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user data"""
        try:
            # Check if token is blacklisted
            if token in self.blacklisted_tokens:
                return None
            
            # Decode token
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Check expiration
            exp = payload.get('exp')
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                return None
            
            return {
                'id': payload.get('user_id'),
                'username': payload.get('username'),
                'email': payload.get('email'),
                'role': payload.get('role'),
                'token_id': payload.get('jti')
            }
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None
    
    def blacklist_token(self, token: str) -> bool:
        """Add token to blacklist (logout)"""
        try:
            # Verify token first to get JTI
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            jti = payload.get('jti')
            
            if jti:
                self.blacklisted_tokens.add(token)
                return True
            
            return False
            
        except Exception:
            return False
    
    def cleanup_blacklist(self):
        """Clean up expired tokens from blacklist"""
        valid_tokens = set()
        
        for token in self.blacklisted_tokens:
            try:
                payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
                exp = payload.get('exp')
                
                # Keep token if not expired
                if exp and datetime.fromtimestamp(exp) >= datetime.utcnow():
                    valid_tokens.add(token)
                    
            except Exception:
                # Remove invalid tokens
                continue
        
        self.blacklisted_tokens = valid_tokens
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get detailed token information"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            return {
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'email': payload.get('email'),
                'role': payload.get('role'),
                'issued_at': datetime.fromtimestamp(payload.get('iat')).isoformat() if payload.get('iat') else None,
                'expires_at': datetime.fromtimestamp(payload.get('exp')).isoformat() if payload.get('exp') else None,
                'token_id': payload.get('jti'),
                'is_blacklisted': token in self.blacklisted_tokens
            }
            
        except Exception:
            return None

# Global instance
auth_service = AuthService()

