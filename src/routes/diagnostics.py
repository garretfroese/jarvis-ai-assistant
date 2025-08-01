"""
Diagnostics API Routes for Jarvis
Handles system diagnostics and health check endpoints
"""

from flask import Blueprint, request, jsonify
from ..services.diagnostics import DiagnosticsService
from ..utils.security import require_auth

diagnostics_bp = Blueprint('diagnostics', __name__)
diagnostics_service = DiagnosticsService()

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

@diagnostics_bp.route('/api/diagnose', methods=['GET', 'POST'])
@require_auth
def run_diagnostics():
    """Run comprehensive system diagnostics"""
    try:
        # Get API key from request if provided
        api_key = None
        if request.method == 'POST':
            data = request.get_json() or {}
            api_key = data.get('api_key')
        elif request.method == 'GET':
            api_key = request.args.get('api_key')
        
        # Run full diagnostics
        result = diagnostics_service.run_full_diagnostics(api_key)
        
        return jsonify({
            'status': 'success',
            'diagnostics': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Diagnostics failed: {str(e)}'
        }), 500

@diagnostics_bp.route('/api/status', methods=['GET'])
def get_quick_status():
    """Get quick system status (no auth required for health checks)"""
    try:
        status = diagnostics_service.get_quick_status()
        return jsonify({
            'status': 'success',
            'system_status': status
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@diagnostics_bp.route('/api/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': diagnostics_service.get_quick_status()['timestamp'],
        'service': 'jarvis-api'
    })

@diagnostics_bp.route('/api/diagnose/openai', methods=['POST'])
@require_auth
def test_openai():
    """Test OpenAI API connection specifically"""
    try:
        data = request.get_json() or {}
        api_key = data.get('api_key')
        
        result = diagnostics_service.check_openai_connection(api_key)
        
        return jsonify({
            'status': 'success',
            'openai_test': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@diagnostics_bp.route('/api/diagnose/tools', methods=['GET'])
@require_auth
def test_tools():
    """Test all tools status"""
    try:
        result = diagnostics_service.check_tools_status()
        
        return jsonify({
            'status': 'success',
            'tools_status': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@diagnostics_bp.route('/api/diagnose/memory', methods=['GET'])
@require_auth
def test_memory():
    """Test memory and session status"""
    try:
        result = diagnostics_service.check_memory_status()
        
        return jsonify({
            'status': 'success',
            'memory_status': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@diagnostics_bp.route('/api/diagnose/system', methods=['GET'])
@require_auth
def test_system():
    """Test system resources"""
    try:
        result = diagnostics_service.check_system_resources()
        
        return jsonify({
            'status': 'success',
            'system_status': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@diagnostics_bp.route('/api/diagnose/command', methods=['POST'])
@require_auth
def handle_diagnose_command():
    """Handle /diagnose command from chat"""
    try:
        data = request.get_json() or {}
        message = data.get('message', '').lower()
        api_key = data.get('api_key')
        
        # Parse command options
        if 'quick' in message:
            result = diagnostics_service.get_quick_status()
            response_type = 'quick'
        elif 'openai' in message:
            result = diagnostics_service.check_openai_connection(api_key)
            response_type = 'openai'
        elif 'tools' in message:
            result = diagnostics_service.check_tools_status()
            response_type = 'tools'
        elif 'memory' in message:
            result = diagnostics_service.check_memory_status()
            response_type = 'memory'
        elif 'system' in message:
            result = diagnostics_service.check_system_resources()
            response_type = 'system'
        else:
            # Full diagnostics
            result = diagnostics_service.run_full_diagnostics(api_key)
            response_type = 'full'
        
        # Format response for chat
        formatted_response = format_diagnostics_for_chat(result, response_type)
        
        return jsonify({
            'status': 'success',
            'response_type': response_type,
            'raw_data': result,
            'formatted_response': formatted_response,
            'is_command_response': True
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'formatted_response': f"❌ Diagnostics failed: {str(e)}"
        }), 500

def format_diagnostics_for_chat(data, response_type):
    """Format diagnostics data for chat display"""
    
    if response_type == 'quick':
        return f"""🔍 **Quick System Status**
        
✅ Status: {data['status']}
⏱️ Uptime: {data['uptime']}
💾 Memory Usage: {data['memory_usage']:.1f}%
🖥️ CPU Usage: {data['cpu_usage']:.1f}%
🎭 Available Modes: {data['available_modes']}"""
    
    elif response_type == 'openai':
        status_emoji = "✅" if data['status'] == 'ok' else "❌"
        response = f"{status_emoji} **OpenAI API Status: {data['status'].upper()}**\n"
        
        if data['status'] == 'ok':
            response += f"🤖 Model: {data['model']}\n"
            response += f"⚡ Streaming: {'Yes' if data['streaming'] else 'No'}\n"
            response += f"⏱️ Response Time: {data['response_time']}ms"
        else:
            response += f"❌ Error: {data['error']}"
        
        return response
    
    elif response_type == 'tools':
        response = "🛠️ **Tools Status**\n\n"
        
        for tool_name, status in data.items():
            status_emoji = "✅" if status['status'] == 'ok' else "⚠️" if status['status'] == 'configured' else "❌"
            response += f"{status_emoji} {tool_name.replace('_', ' ').title()}: {status['status']}\n"
            
            if 'error' in status:
                response += f"   └─ {status['error']}\n"
        
        return response
    
    elif response_type == 'memory':
        status_emoji = "✅" if data['status'] == 'ok' else "❌"
        return f"""{status_emoji} **Memory & Sessions Status**

🎭 Available Modes: {data['available_modes']}
📝 Mode Names: {', '.join(data['mode_names'])}
👥 Active Sessions: {data['active_sessions']}
🏠 Default Mode: {data['default_mode']}"""
    
    elif response_type == 'system':
        status_emoji = "✅" if data['status'] == 'ok' else "❌"
        return f"""{status_emoji} **System Resources**

🖥️ CPU Usage: {data['cpu_percent']:.1f}%
💾 Memory: {data['memory']['percent']:.1f}% used
💿 Disk: {data['disk']['percent']:.1f}% used
⏱️ Uptime: {data['uptime_formatted']}"""
    
    elif response_type == 'full':
        overall_emoji = "✅" if data['overall_status'] == 'healthy' else "⚠️" if data['overall_status'] == 'warning' else "❌"
        
        response = f"""{overall_emoji} **Full System Diagnostics**

**Overall Status: {data['overall_status'].upper()}**
🕐 Scan Duration: {data['diagnostics_duration']}ms

**🤖 OpenAI API:** {data['openai']['status']}"""
        
        if data['openai']['status'] == 'ok':
            response += f" ({data['openai']['model']})"
        
        response += f"\n**🛠️ Tools:** "
        tool_statuses = [status['status'] for status in data['tools'].values()]
        ok_count = tool_statuses.count('ok')
        total_count = len(tool_statuses)
        response += f"{ok_count}/{total_count} operational"
        
        response += f"\n**💾 Memory:** {data['memory']['status']} ({data['memory']['available_modes']} modes)"
        response += f"\n**🖥️ System:** {data['system']['status']} (CPU: {data['system']['cpu_percent']:.1f}%, RAM: {data['system']['memory']['percent']:.1f}%)"
        
        if 'issues' in data:
            response += f"\n\n⚠️ **Issues Found:** {', '.join(data['issues'])}"
        
        return response
    
    return str(data)

