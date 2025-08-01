"""
User Management API Routes for Jarvis
Handles user profiles, roles, permissions, and administration
"""

from flask import Blueprint, request, jsonify
from ..services.user_service import user_service
from ..utils.auth_middleware import (
    require_auth, require_admin, get_current_user, rate_limit
)

users_bp = Blueprint('users', __name__)

def validate_input(required_fields):
    """Simple input validation decorator"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            data = request.get_json() or {}
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

@users_bp.route('/api/users/profile', methods=['GET'])
@require_auth
def get_current_user_profile():
    """Get current user's profile"""
    try:
        current_user = get_current_user()
        user_id = current_user.get('user_id')
        
        # Get or create user profile
        user_profile = user_service.get_user(user_id)
        if not user_profile:
            # Create profile from auth data
            user_profile = user_service.create_or_update_user(current_user)
        
        return jsonify({
            'status': 'success',
            'profile': user_profile
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get profile: {str(e)}'
        }), 500

@users_bp.route('/api/users/profile', methods=['PUT'])
@require_auth
@validate_input(['preferences'])
def update_current_user_profile():
    """Update current user's profile"""
    try:
        current_user = get_current_user()
        user_id = current_user.get('user_id')
        data = request.get_json()
        
        # Update preferences
        preferences = data.get('preferences', {})
        success = user_service.update_user_preferences(user_id, preferences)
        
        if success:
            updated_profile = user_service.get_user(user_id)
            return jsonify({
                'status': 'success',
                'message': 'Profile updated successfully',
                'profile': updated_profile
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update profile'
            }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to update profile: {str(e)}'
        }), 500

@users_bp.route('/api/users/activity', methods=['GET'])
@require_auth
def get_current_user_activity():
    """Get current user's activity history"""
    try:
        current_user = get_current_user()
        user_id = current_user.get('user_id')
        
        limit = request.args.get('limit', 50, type=int)
        activity = user_service.get_user_activity(user_id, limit)
        
        return jsonify({
            'status': 'success',
            'activity': activity,
            'count': len(activity)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get activity: {str(e)}'
        }), 500

@users_bp.route('/api/users', methods=['GET'])
@require_admin
def get_all_users():
    """Get all users (admin only)"""
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        users = user_service.get_all_users(include_inactive)
        
        return jsonify({
            'status': 'success',
            'users': users,
            'count': len(users)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get users: {str(e)}'
        }), 500

@users_bp.route('/api/users/<user_id>', methods=['GET'])
@require_admin
def get_user_by_id(user_id):
    """Get user by ID (admin only)"""
    try:
        user = user_service.get_user(user_id)
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'user': user
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get user: {str(e)}'
        }), 500

@users_bp.route('/api/users/<user_id>/role', methods=['PUT'])
@require_admin
@validate_input(['role'])
def update_user_role(user_id):
    """Update user role (admin only)"""
    try:
        data = request.get_json()
        new_role = data.get('role')
        
        success = user_service.update_user_role(user_id, new_role)
        
        if success:
            updated_user = user_service.get_user(user_id)
            return jsonify({
                'status': 'success',
                'message': f'User role updated to {new_role}',
                'user': updated_user
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update user role'
            }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to update role: {str(e)}'
        }), 500

@users_bp.route('/api/users/<user_id>/status', methods=['PUT'])
@require_admin
@validate_input(['status'])
def update_user_status(user_id):
    """Update user status (admin only)"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        success = user_service.update_user_status(user_id, new_status)
        
        if success:
            updated_user = user_service.get_user(user_id)
            return jsonify({
                'status': 'success',
                'message': f'User status updated to {new_status}',
                'user': updated_user
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update user status'
            }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to update status: {str(e)}'
        }), 500

@users_bp.route('/api/users/<user_id>/activity', methods=['GET'])
@require_admin
def get_user_activity(user_id):
    """Get user activity history (admin only)"""
    try:
        limit = request.args.get('limit', 50, type=int)
        activity = user_service.get_user_activity(user_id, limit)
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'activity': activity,
            'count': len(activity)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get user activity: {str(e)}'
        }), 500

@users_bp.route('/api/users/roles', methods=['GET'])
@require_admin
def get_available_roles():
    """Get available roles and their permissions (admin only)"""
    try:
        return jsonify({
            'status': 'success',
            'roles': user_service.roles
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get roles: {str(e)}'
        }), 500

@users_bp.route('/api/users/stats', methods=['GET'])
@require_admin
def get_user_stats():
    """Get user statistics (admin only)"""
    try:
        stats = user_service.get_user_stats()
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get stats: {str(e)}'
        }), 500

@users_bp.route('/api/users/by-role/<role>', methods=['GET'])
@require_admin
def get_users_by_role(role):
    """Get users by role (admin only)"""
    try:
        users = user_service.get_users_by_role(role)
        
        return jsonify({
            'status': 'success',
            'role': role,
            'users': users,
            'count': len(users)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get users by role: {str(e)}'
        }), 500

@users_bp.route('/api/users/<user_id>/export', methods=['GET'])
@require_admin
def export_user_data(user_id):
    """Export user data (admin only)"""
    try:
        user_data = user_service.export_user_data(user_id)
        
        if not user_data:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': user_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to export user data: {str(e)}'
        }), 500

@users_bp.route('/api/users/<user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    """Delete user (admin only)"""
    try:
        current_user = get_current_user()
        
        # Prevent self-deletion
        if current_user.get('user_id') == user_id:
            return jsonify({
                'status': 'error',
                'message': 'Cannot delete your own account'
            }), 400
        
        success = user_service.delete_user(user_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'User deleted successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete user: {str(e)}'
        }), 500

@users_bp.route('/api/users/activity/cleanup', methods=['POST'])
@require_admin
def cleanup_user_activity():
    """Clean up old user activity (admin only)"""
    try:
        days = request.args.get('days', 30, type=int)
        cleaned_count = user_service.cleanup_old_activity(days)
        
        return jsonify({
            'status': 'success',
            'message': f'Cleaned up {cleaned_count} old activity records',
            'cleaned_count': cleaned_count,
            'days': days
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to cleanup activity: {str(e)}'
        }), 500

@users_bp.route('/api/users/permissions/check', methods=['POST'])
@require_auth
@validate_input(['permission'])
def check_user_permission():
    """Check if current user has a specific permission"""
    try:
        current_user = get_current_user()
        user_id = current_user.get('user_id')
        data = request.get_json()
        permission = data.get('permission')
        
        has_permission = user_service.has_permission(user_id, permission)
        
        return jsonify({
            'status': 'success',
            'permission': permission,
            'has_permission': has_permission
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to check permission: {str(e)}'
        }), 500

@users_bp.route('/api/users/search', methods=['POST'])
@require_admin
@validate_input(['query'])
def search_users():
    """Search users by email or name (admin only)"""
    try:
        data = request.get_json()
        query = data.get('query', '').lower()
        
        all_users = user_service.get_all_users(include_inactive=True)
        
        # Filter users based on query
        matching_users = []
        for user in all_users:
            email = user.get('email', '').lower()
            name = user.get('name', '').lower()
            
            if query in email or query in name:
                matching_users.append(user)
        
        return jsonify({
            'status': 'success',
            'query': query,
            'users': matching_users,
            'count': len(matching_users)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Search failed: {str(e)}'
        }), 500

