"""
Simple Authentication Routes for Jarvis
Basic authentication without Google OAuth for deployment testing
"""

import os
import secrets
from flask import Blueprint, request, jsonify, make_response
from ..services.simple_auth import simple_auth

simple_auth_bp = Blueprint('simple_auth', __name__)

@simple_auth_bp.route('/auth/simple-login', methods=['POST'])
def simple_login():
    """Simple login for testing (development only)"""
    try:
        data = request.get_json() or {}
        email = data.get('email')
        name = data.get('name', email)
        
        if not email:
            return jsonify({
                'status': 'error',
                'message': 'Email is required'
            }), 400
        
        # Create user info
        user_info = {
            'id': email,
            'email': email,
            'name': name,
            'picture': f'https://ui-avatars.com/api/?name={name}&background=random'
        }
        
        # Create session token
        token = simple_auth.create_session_token(user_info)
        
        # Get user data
        user_data = simple_auth.validate_session_token(token)
        
        # Create response
        response_data = {
            'status': 'success',
            'user': {
                'id': user_data.get('user_id'),
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'picture': user_data.get('picture'),
                'role': user_data.get('role')
            },
            'token': token
        }
        
        response = make_response(jsonify(response_data))
        
        # Set secure HTTP-only cookie
        response.set_cookie(
            'jarvis_session',
            token,
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,
            secure=request.is_secure,
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Login failed: {str(e)}'
        }), 500

@simple_auth_bp.route('/auth/status', methods=['GET'])
def auth_status():
    """Get current authentication status"""
    try:
        # Get token from cookie or header
        token = request.cookies.get('jarvis_session')
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        if token:
            user_data = simple_auth.validate_session_token(token)
            if user_data:
                return jsonify({
                    'status': 'success',
                    'authenticated': True,
                    'user': {
                        'id': user_data.get('user_id'),
                        'email': user_data.get('email'),
                        'name': user_data.get('name'),
                        'picture': user_data.get('picture'),
                        'role': user_data.get('role')
                    }
                })
        
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

@simple_auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user and revoke session"""
    try:
        # Get token
        token = request.cookies.get('jarvis_session')
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        # Revoke session
        if token:
            simple_auth.revoke_session(token)
        
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

@simple_auth_bp.route('/auth/sessions', methods=['GET'])
def get_sessions():
    """Get active sessions"""
    try:
        sessions_data = simple_auth.get_active_sessions()
        return jsonify({
            'status': 'success',
            'sessions': sessions_data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get sessions: {str(e)}'
        }), 500

