"""
Authentication Middleware for Jarvis
Provides decorators and utilities for protecting routes and validating authentication
"""

import time
from functools import wraps
from flask import request, jsonify, g
from typing import Dict, Any, Optional, Callable
from ..services.google_auth import google_auth

# Rate limiting storage (in production, use Redis)
rate_limit_storage = {}

def extract_token_from_request() -> Optional[str]:
    """Extract authentication token from request"""
    # Try Authorization header first
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Try cookie
    token = request.cookies.get('jarvis_session')
    if token:
        return token
    
    # Try query parameter (for testing)
    token = request.args.get('auth_token')
    if token:
        return token
    
    return None

def require_auth(f: Callable) -> Callable:
    """Decorator to require authentication for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = extract_token_from_request()
        
        if not token:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        # Validate token
        user_data = google_auth.validate_session_token(token)
        if not user_data:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired token',
                'code': 'INVALID_TOKEN'
            }), 401
        
        # Store user data in Flask's g object for use in the route
        g.current_user = user_data
        g.auth_token = token
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_admin(f: Callable) -> Callable:
    """Decorator to require admin role for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check authentication
        token = extract_token_from_request()
        
        if not token:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        user_data = google_auth.validate_session_token(token)
        if not user_data:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired token',
                'code': 'INVALID_TOKEN'
            }), 401
        
        # Check admin role
        if not google_auth.is_admin(user_data):
            return jsonify({
                'status': 'error',
                'message': 'Admin access required',
                'code': 'INSUFFICIENT_PERMISSIONS'
            }), 403
        
        g.current_user = user_data
        g.auth_token = token
        
        return f(*args, **kwargs)
    
    return decorated_function

def optional_auth(f: Callable) -> Callable:
    """Decorator for optional authentication (sets user data if available)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = extract_token_from_request()
        
        if token:
            user_data = google_auth.validate_session_token(token)
            if user_data:
                g.current_user = user_data
                g.auth_token = token
            else:
                g.current_user = None
                g.auth_token = None
        else:
            g.current_user = None
            g.auth_token = None
        
        return f(*args, **kwargs)
    
    return decorated_function

def rate_limit(max_requests: int = 60, window_seconds: int = 60):
    """Rate limiting decorator"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            user_id = getattr(g, 'current_user', {}).get('user_id', 'anonymous')
            client_key = f"{client_ip}:{user_id}:{f.__name__}"
            
            current_time = time.time()
            
            # Clean up old entries
            cleanup_rate_limit_storage(current_time, window_seconds)
            
            # Check rate limit
            if client_key in rate_limit_storage:
                requests_data = rate_limit_storage[client_key]
                
                # Filter requests within the window
                recent_requests = [
                    req_time for req_time in requests_data['requests']
                    if current_time - req_time < window_seconds
                ]
                
                if len(recent_requests) >= max_requests:
                    return jsonify({
                        'status': 'error',
                        'message': 'Rate limit exceeded',
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'retry_after': window_seconds
                    }), 429
                
                # Update requests list
                recent_requests.append(current_time)
                rate_limit_storage[client_key] = {
                    'requests': recent_requests,
                    'last_request': current_time
                }
            else:
                # First request from this client
                rate_limit_storage[client_key] = {
                    'requests': [current_time],
                    'last_request': current_time
                }
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def cleanup_rate_limit_storage(current_time: float, window_seconds: int):
    """Clean up old rate limit entries"""
    keys_to_remove = []
    
    for key, data in rate_limit_storage.items():
        if current_time - data['last_request'] > window_seconds * 2:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del rate_limit_storage[key]

def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current authenticated user from Flask's g object"""
    return getattr(g, 'current_user', None)

def get_current_token() -> Optional[str]:
    """Get current authentication token from Flask's g object"""
    return getattr(g, 'auth_token', None)

def is_authenticated() -> bool:
    """Check if current request is authenticated"""
    return get_current_user() is not None

def is_admin() -> bool:
    """Check if current user has admin role"""
    user = get_current_user()
    return user and google_auth.is_admin(user)

def check_permission(permission: str) -> bool:
    """Check if current user has a specific permission"""
    user = get_current_user()
    if not user:
        return False
    
    # Admin has all permissions
    if google_auth.is_admin(user):
        return True
    
    # Define permission mappings
    user_permissions = {
        'chat': True,
        'file_upload': True,
        'basic_tools': True
    }
    
    admin_permissions = {
        'system_diagnostics': True,
        'plugin_management': True,
        'user_management': True,
        'logs_access': True,
        'advanced_tools': True
    }
    
    if user.get('role') == 'admin':
        return permission in {**user_permissions, **admin_permissions}
    else:
        return permission in user_permissions

def create_auth_response(user_data: Dict[str, Any], token: str) -> Dict[str, Any]:
    """Create standardized authentication response"""
    return {
        'status': 'success',
        'user': {
            'id': user_data.get('user_id'),
            'email': user_data.get('email'),
            'name': user_data.get('name'),
            'picture': user_data.get('picture'),
            'role': user_data.get('role')
        },
        'token': token,
        'expires_at': user_data.get('exp'),
        'permissions': get_user_permissions(user_data)
    }

def get_user_permissions(user_data: Dict[str, Any]) -> Dict[str, bool]:
    """Get user permissions based on role"""
    base_permissions = {
        'chat': True,
        'file_upload': True,
        'basic_tools': True,
        'system_diagnostics': False,
        'plugin_management': False,
        'user_management': False,
        'logs_access': False,
        'advanced_tools': False
    }
    
    if google_auth.is_admin(user_data):
        # Admin gets all permissions
        return {key: True for key in base_permissions.keys()}
    
    return base_permissions

def validate_auth_config() -> Dict[str, Any]:
    """Validate authentication configuration"""
    status = google_auth.get_auth_status()
    
    issues = []
    if not status['configured']:
        issues.append('Google OAuth not configured')
    if status['admin_emails_count'] == 0:
        issues.append('No admin emails configured')
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'status': status
    }

