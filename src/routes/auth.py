"""
Authentication Routes for Jarvis
Handles Google OAuth login, logout, and session management
"""

import os
import secrets
from flask import Blueprint, request, jsonify, redirect, make_response, url_for
from ..services.google_auth import google_auth
from ..utils.auth_middleware import (
    require_auth, require_admin, optional_auth, rate_limit,
    get_current_user, create_auth_response, validate_auth_config
)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/auth/config', methods=['GET'])
def get_auth_config():
    """Get authentication configuration status"""
    try:
        config_status = validate_auth_config()
        return jsonify(config_status)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get auth config: {str(e)}'
        }), 500

@auth_bp.route('/login', methods=['GET'])
@rate_limit(max_requests=10, window_seconds=60)
def login():
    """Initiate Google OAuth login"""
    try:
        if not google_auth.is_configured():
            return jsonify({
                'status': 'error',
                'message': 'Google OAuth not configured',
                'code': 'AUTH_NOT_CONFIGURED'
            }), 500
        
        # Set redirect URI based on current request
        base_url = request.url_root.rstrip('/')
        google_auth.set_redirect_uri(base_url)
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state in session (in production, use secure session storage)
        # For now, we'll validate it in the callback
        
        # Generate authorization URL
        auth_url = google_auth.generate_auth_url(state)
        
        # Return redirect URL for frontend to handle
        return jsonify({
            'status': 'success',
            'auth_url': auth_url,
            'state': state
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Login initiation failed: {str(e)}',
            'code': 'LOGIN_FAILED'
        }), 500

@auth_bp.route('/auth/callback', methods=['GET'])
@rate_limit(max_requests=10, window_seconds=60)
def auth_callback():
    """Handle Google OAuth callback"""
    try:
        # Get authorization code and state
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            return jsonify({
                'status': 'error',
                'message': f'OAuth error: {error}',
                'code': 'OAUTH_ERROR'
            }), 400
        
        if not code:
            return jsonify({
                'status': 'error',
                'message': 'No authorization code received',
                'code': 'NO_AUTH_CODE'
            }), 400
        
        # Set redirect URI
        base_url = request.url_root.rstrip('/')
        google_auth.set_redirect_uri(base_url)
        
        # Authenticate user
        token, user_info = google_auth.authenticate_user(code, state)
        
        # Create response
        response_data = create_auth_response(
            google_auth.validate_session_token(token), 
            token
        )
        
        # Create response with secure cookie
        response = make_response(jsonify(response_data))
        
        # Set secure HTTP-only cookie
        response.set_cookie(
            'jarvis_session',
            token,
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,
            secure=request.is_secure,  # HTTPS only in production
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Authentication failed: {str(e)}',
            'code': 'AUTH_FAILED'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@optional_auth
@rate_limit(max_requests=10, window_seconds=60)
def logout():
    """Logout user and revoke session"""
    try:
        user = get_current_user()
        
        if user:
            # Get token from request
            token = request.cookies.get('jarvis_session')
            if not token:
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header[7:]
            
            # Revoke session
            if token:
                google_auth.revoke_session(token)
        
        # Create response
        response = make_response(jsonify({
            'status': 'success',
            'message': 'Logged out successfully'
        }))
        
        # Clear cookie
        response.set_cookie(
            'jarvis_session',
            '',
            expires=0,
            httponly=True,
            secure=request.is_secure,
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Logout failed: {str(e)}'
        }), 500

@auth_bp.route('/auth/status', methods=['GET'])
@optional_auth
def auth_status():
    """Get current authentication status"""
    try:
        user = get_current_user()
        
        if user:
            return jsonify({
                'status': 'success',
                'authenticated': True,
                'user': {
                    'id': user.get('user_id'),
                    'email': user.get('email'),
                    'name': user.get('name'),
                    'picture': user.get('picture'),
                    'role': user.get('role')
                },
                'expires_at': user.get('exp')
            })
        else:
            return jsonify({
                'status': 'success',
                'authenticated': False,
                'user': None
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get auth status: {str(e)}'
        }), 500

@auth_bp.route('/auth/refresh', methods=['POST'])
@require_auth
@rate_limit(max_requests=10, window_seconds=60)
def refresh_token():
    """Refresh authentication token"""
    try:
        user = get_current_user()
        
        # Create new token
        new_token = google_auth.create_session_token({
            'id': user.get('user_id'),
            'email': user.get('email'),
            'name': user.get('name'),
            'picture': user.get('picture')
        })
        
        # Create response
        response_data = create_auth_response(
            google_auth.validate_session_token(new_token),
            new_token
        )
        
        response = make_response(jsonify(response_data))
        
        # Update cookie
        response.set_cookie(
            'jarvis_session',
            new_token,
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,
            secure=request.is_secure,
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Token refresh failed: {str(e)}'
        }), 500

@auth_bp.route('/auth/sessions', methods=['GET'])
@require_admin
def get_active_sessions():
    """Get active sessions (admin only)"""
    try:
        sessions_data = google_auth.get_active_sessions()
        return jsonify({
            'status': 'success',
            'sessions': sessions_data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get sessions: {str(e)}'
        }), 500

@auth_bp.route('/auth/sessions/cleanup', methods=['POST'])
@require_admin
def cleanup_sessions():
    """Clean up expired sessions (admin only)"""
    try:
        cleaned_count = google_auth.cleanup_expired_sessions()
        return jsonify({
            'status': 'success',
            'message': f'Cleaned up {cleaned_count} expired sessions',
            'cleaned_count': cleaned_count
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Session cleanup failed: {str(e)}'
        }), 500

@auth_bp.route('/auth/test', methods=['GET'])
@require_auth
def test_auth():
    """Test authentication (protected endpoint)"""
    user = get_current_user()
    return jsonify({
        'status': 'success',
        'message': 'Authentication working',
        'user': {
            'email': user.get('email'),
            'role': user.get('role')
        },
        'timestamp': user.get('iat')
    })

@auth_bp.route('/auth/admin-test', methods=['GET'])
@require_admin
def test_admin():
    """Test admin authentication (admin only)"""
    user = get_current_user()
    return jsonify({
        'status': 'success',
        'message': 'Admin authentication working',
        'user': {
            'email': user.get('email'),
            'role': user.get('role')
        }
    })

# Error handlers
@auth_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'status': 'error',
        'message': 'Authentication required',
        'code': 'UNAUTHORIZED'
    }), 401

@auth_bp.errorhandler(403)
def forbidden(error):
    return jsonify({
        'status': 'error',
        'message': 'Insufficient permissions',
        'code': 'FORBIDDEN'
    }), 403

@auth_bp.errorhandler(429)
def rate_limited(error):
    return jsonify({
        'status': 'error',
        'message': 'Rate limit exceeded',
        'code': 'RATE_LIMITED'
    }), 429

