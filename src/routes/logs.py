"""
Log Dashboard API Routes for Jarvis
Handles log retrieval, filtering, and management endpoints
"""

from flask import Blueprint, request, jsonify, send_file
import os
import tempfile
from datetime import datetime, timedelta
from ..services.logging_service import logging_service
from ..utils.security import require_auth

logs_bp = Blueprint('logs', __name__)

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

@logs_bp.route('/api/logs', methods=['GET'])
@require_auth
def get_logs():
    """Get logs with filtering and pagination"""
    try:
        # Extract query parameters
        limit = min(int(request.args.get('limit', 100)), 1000)  # Max 1000 logs
        offset = int(request.args.get('offset', 0))
        user_id = request.args.get('user_id')
        session_id = request.args.get('session_id')
        tool_name = request.args.get('tool_name')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        search_query = request.args.get('search')
        
        # Validate date formats if provided
        if start_date:
            try:
                datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'
                }), 400
        
        if end_date:
            try:
                datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'
                }), 400
        
        # Get logs from service
        logs = logging_service.get_logs(
            limit=limit,
            offset=offset,
            user_id=user_id,
            session_id=session_id,
            tool_name=tool_name,
            status=status,
            start_date=start_date,
            end_date=end_date,
            search_query=search_query
        )
        
        # Get total count for pagination
        total_logs = logging_service.get_logs(
            limit=10000,  # Large number to get total count
            user_id=user_id,
            session_id=session_id,
            tool_name=tool_name,
            status=status,
            start_date=start_date,
            end_date=end_date,
            search_query=search_query
        )
        
        return jsonify({
            'status': 'success',
            'logs': logs,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': len(total_logs),
                'has_more': len(total_logs) > offset + limit
            },
            'filters': {
                'user_id': user_id,
                'session_id': session_id,
                'tool_name': tool_name,
                'status': status,
                'start_date': start_date,
                'end_date': end_date,
                'search_query': search_query
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve logs: {str(e)}'
        }), 500

@logs_bp.route('/api/logs/<int:log_id>', methods=['GET'])
@require_auth
def get_log_details(log_id):
    """Get detailed information for a specific log entry"""
    try:
        log_entry = logging_service.get_log_by_id(log_id)
        
        if not log_entry:
            return jsonify({
                'status': 'error',
                'message': 'Log entry not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'log': log_entry
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve log details: {str(e)}'
        }), 500

@logs_bp.route('/api/logs/statistics', methods=['GET'])
@require_auth
def get_log_statistics():
    """Get statistics about logged commands"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Default to last 30 days if no dates provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).isoformat()
        
        stats = logging_service.get_log_statistics(
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            'status': 'success',
            'statistics': stats,
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve statistics: {str(e)}'
        }), 500

@logs_bp.route('/api/logs/export', methods=['POST'])
@require_auth
def export_logs():
    """Export logs to CSV file"""
    try:
        data = request.get_json() or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        format_type = data.get('format', 'csv').lower()
        
        if format_type != 'csv':
            return jsonify({
                'status': 'error',
                'message': 'Only CSV format is currently supported'
            }), 400
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.csv', 
            delete=False,
            prefix='jarvis_logs_'
        )
        temp_file.close()
        
        # Export logs
        success = logging_service.export_logs_to_csv(
            filename=temp_file.name,
            start_date=start_date,
            end_date=end_date
        )
        
        if not success:
            os.unlink(temp_file.name)
            return jsonify({
                'status': 'error',
                'message': 'Failed to export logs or no logs found'
            }), 500
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        download_filename = f'jarvis_logs_{timestamp}.csv'
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=download_filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to export logs: {str(e)}'
        }), 500

@logs_bp.route('/api/logs/cleanup', methods=['POST'])
@require_auth
def cleanup_old_logs():
    """Delete old log entries"""
    try:
        data = request.get_json() or {}
        days_to_keep = data.get('days_to_keep', 30)
        
        if days_to_keep < 1:
            return jsonify({
                'status': 'error',
                'message': 'days_to_keep must be at least 1'
            }), 400
        
        deleted_count = logging_service.delete_old_logs(days_to_keep)
        
        return jsonify({
            'status': 'success',
            'message': f'Deleted {deleted_count} old log entries',
            'deleted_count': deleted_count,
            'days_kept': days_to_keep
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to cleanup logs: {str(e)}'
        }), 500

@logs_bp.route('/api/logs/tools', methods=['GET'])
@require_auth
def get_available_tools():
    """Get list of tools that have been logged"""
    try:
        # Get unique tool names from logs
        logs = logging_service.get_logs(limit=10000)  # Get many logs to find all tools
        tools = set()
        
        for log in logs:
            if log.get('tool_name'):
                tools.add(log['tool_name'])
        
        return jsonify({
            'status': 'success',
            'tools': sorted(list(tools))
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve tools: {str(e)}'
        }), 500

@logs_bp.route('/api/logs/users', methods=['GET'])
@require_auth
def get_logged_users():
    """Get list of users that have been logged"""
    try:
        # Get unique user IDs from logs
        logs = logging_service.get_logs(limit=10000)  # Get many logs to find all users
        users = set()
        
        for log in logs:
            if log.get('user_id'):
                users.add(log['user_id'])
        
        return jsonify({
            'status': 'success',
            'users': sorted(list(users))
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve users: {str(e)}'
        }), 500

@logs_bp.route('/api/logs/replay/<int:log_id>', methods=['POST'])
@require_auth
def replay_command(log_id):
    """Replay a previous command (placeholder for future implementation)"""
    try:
        log_entry = logging_service.get_log_by_id(log_id)
        
        if not log_entry:
            return jsonify({
                'status': 'error',
                'message': 'Log entry not found'
            }), 404
        
        # For now, just return the command details
        # In the future, this could actually re-execute the command
        return jsonify({
            'status': 'success',
            'message': 'Replay functionality not yet implemented',
            'command': log_entry.get('command'),
            'tool_name': log_entry.get('tool_name'),
            'original_timestamp': log_entry.get('timestamp')
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to replay command: {str(e)}'
        }), 500

@logs_bp.route('/api/logs/search', methods=['POST'])
@require_auth
@validate_input(['query'])
def search_logs():
    """Advanced search in logs"""
    try:
        data = request.get_json()
        query = data.get('query')
        filters = data.get('filters', {})
        limit = min(int(data.get('limit', 100)), 1000)
        
        # Extract filters
        tool_name = filters.get('tool_name')
        status = filters.get('status')
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        user_id = filters.get('user_id')
        
        logs = logging_service.get_logs(
            limit=limit,
            tool_name=tool_name,
            status=status,
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            search_query=query
        )
        
        return jsonify({
            'status': 'success',
            'logs': logs,
            'query': query,
            'filters': filters,
            'result_count': len(logs)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Search failed: {str(e)}'
        }), 500

