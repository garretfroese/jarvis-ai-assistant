"""
Modes API Routes for Jarvis
Handles mode switching and management endpoints
"""

from flask import Blueprint, request, jsonify
from ..services.mode_manager import ModeManager
from ..utils.security import require_auth

modes_bp = Blueprint('modes', __name__)
mode_manager = ModeManager()

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

@modes_bp.route('/api/modes', methods=['GET'])
@require_auth
def get_modes():
    """Get all available modes"""
    try:
        modes = mode_manager.get_all_modes()
        return jsonify({
            'status': 'success',
            'modes': modes
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@modes_bp.route('/api/modes/<mode_name>', methods=['GET'])
@require_auth
def get_mode(mode_name):
    """Get specific mode details"""
    try:
        mode = mode_manager.get_mode(mode_name)
        if not mode:
            return jsonify({
                'status': 'error',
                'message': 'Mode not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'mode': mode
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@modes_bp.route('/api/modes', methods=['POST'])
@require_auth
@validate_input(['name', 'prompt'])
def create_mode():
    """Create a new mode"""
    try:
        data = request.get_json()
        name = data.get('name')
        prompt = data.get('prompt')
        description = data.get('description', '')
        tools_enabled = data.get('tools_enabled', ['all'])
        
        success = mode_manager.add_mode(name, prompt, description, tools_enabled)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Mode "{name}" created successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to create mode'
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@modes_bp.route('/api/modes/<mode_name>', methods=['PUT'])
@require_auth
def update_mode(mode_name):
    """Update an existing mode"""
    try:
        data = request.get_json()
        
        success = mode_manager.update_mode(mode_name, **data)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Mode "{mode_name}" updated successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Mode not found or update failed'
            }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@modes_bp.route('/api/modes/<mode_name>', methods=['DELETE'])
@require_auth
def delete_mode(mode_name):
    """Delete a mode"""
    try:
        success = mode_manager.delete_mode(mode_name)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Mode "{mode_name}" deleted successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Cannot delete mode (not found or protected)'
            }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@modes_bp.route('/api/sessions/<session_id>/mode', methods=['GET'])
@require_auth
def get_session_mode(session_id):
    """Get current mode for a session"""
    try:
        mode_name = mode_manager.get_session_mode(session_id)
        mode = mode_manager.get_mode(mode_name)
        
        return jsonify({
            'status': 'success',
            'current_mode': mode_name,
            'mode_details': mode
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@modes_bp.route('/api/sessions/<session_id>/mode', methods=['POST'])
@require_auth
@validate_input(['mode'])
def set_session_mode(session_id):
    """Set mode for a session"""
    try:
        data = request.get_json()
        mode_name = data.get('mode')
        
        success = mode_manager.set_session_mode(session_id, mode_name)
        
        if success:
            mode = mode_manager.get_mode(mode_name)
            return jsonify({
                'status': 'success',
                'message': f'Session mode set to "{mode_name}"',
                'mode_details': mode
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Invalid mode or failed to set session mode'
            }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@modes_bp.route('/api/modes/parse-command', methods=['POST'])
@require_auth
@validate_input(['message'])
def parse_mode_command():
    """Parse a message for mode switching commands"""
    try:
        data = request.get_json()
        message = data.get('message')
        
        mode_name = mode_manager.parse_mode_command(message)
        
        if mode_name:
            mode = mode_manager.get_mode(mode_name)
            return jsonify({
                'status': 'success',
                'mode_detected': mode_name,
                'mode_details': mode
            })
        else:
            return jsonify({
                'status': 'success',
                'mode_detected': None
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@modes_bp.route('/api/sessions/<session_id>/prompt', methods=['GET'])
@require_auth
def get_session_prompt(session_id):
    """Get the current system prompt for a session"""
    try:
        prompt = mode_manager.get_mode_prompt(session_id)
        mode_name = mode_manager.get_session_mode(session_id)
        
        return jsonify({
            'status': 'success',
            'prompt': prompt,
            'mode': mode_name
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@modes_bp.route('/api/sessions/<session_id>/tools', methods=['GET'])
@require_auth
def get_session_tools(session_id):
    """Get enabled tools for a session"""
    try:
        enabled_tools = mode_manager.get_enabled_tools(session_id)
        mode_name = mode_manager.get_session_mode(session_id)
        
        return jsonify({
            'status': 'success',
            'enabled_tools': enabled_tools,
            'mode': mode_name
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

