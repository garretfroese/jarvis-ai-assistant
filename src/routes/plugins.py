"""
Plugin Management API Routes for Jarvis
Handles plugin loading, execution, and management endpoints
"""

from flask import Blueprint, request, jsonify
import os
from ..services.plugin_loader import plugin_loader
from ..utils.security import require_auth
from ..utils.log_decorator import log_tool_execution_decorator

plugins_bp = Blueprint('plugins', __name__)

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

@plugins_bp.route('/api/plugins', methods=['GET'])
@require_auth
def get_plugins():
    """Get list of all available plugins"""
    try:
        plugins = plugin_loader.get_plugin_list()
        failed_plugins = plugin_loader.get_failed_plugins()
        
        return jsonify({
            'status': 'success',
            'plugins': plugins,
            'failed_plugins': failed_plugins,
            'total_loaded': len(plugins),
            'total_failed': len(failed_plugins)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve plugins: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/<plugin_name>', methods=['GET'])
@require_auth
def get_plugin_info(plugin_name):
    """Get detailed information about a specific plugin"""
    try:
        plugin_info = plugin_loader.get_plugin_info(plugin_name)
        
        if not plugin_info:
            return jsonify({
                'status': 'error',
                'message': f'Plugin "{plugin_name}" not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'plugin': plugin_info
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve plugin info: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/<plugin_name>/execute', methods=['POST'])
@require_auth
@log_tool_execution_decorator('plugin_execution')
@validate_input(['input'])
def execute_plugin(plugin_name):
    """Execute a specific plugin"""
    try:
        data = request.get_json()
        input_data = data.get('input')
        kwargs = data.get('kwargs', {})
        
        # Check if plugin is available
        if not plugin_loader.is_plugin_available(plugin_name):
            return jsonify({
                'status': 'error',
                'message': f'Plugin "{plugin_name}" is not available or disabled'
            }), 400
        
        # Execute the plugin
        result = plugin_loader.execute_plugin(plugin_name, input_data, **kwargs)
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'result': result['output'],
                'execution_time_ms': result.get('duration_ms'),
                'executed_at': result.get('executed_at')
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result['error'],
                'traceback': result.get('traceback')
            }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to execute plugin: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/<plugin_name>/enable', methods=['POST'])
@require_auth
def enable_plugin(plugin_name):
    """Enable a plugin"""
    try:
        success = plugin_loader.enable_plugin(plugin_name)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Plugin "{plugin_name}" enabled successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Plugin "{plugin_name}" not found'
            }), 404
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to enable plugin: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/<plugin_name>/disable', methods=['POST'])
@require_auth
def disable_plugin(plugin_name):
    """Disable a plugin"""
    try:
        success = plugin_loader.disable_plugin(plugin_name)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Plugin "{plugin_name}" disabled successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Plugin "{plugin_name}" not found'
            }), 404
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to disable plugin: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/<plugin_name>/reload', methods=['POST'])
@require_auth
def reload_plugin(plugin_name):
    """Reload a plugin"""
    try:
        success = plugin_loader.reload_plugin(plugin_name)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Plugin "{plugin_name}" reloaded successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to reload plugin "{plugin_name}". Check the plugin file for errors.'
            }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to reload plugin: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/reload-all', methods=['POST'])
@require_auth
def reload_all_plugins():
    """Reload all plugins"""
    try:
        plugin_loader.load_all_plugins()
        
        plugins = plugin_loader.get_plugin_list()
        failed_plugins = plugin_loader.get_failed_plugins()
        
        return jsonify({
            'status': 'success',
            'message': 'All plugins reloaded',
            'loaded_count': len(plugins),
            'failed_count': len(failed_plugins),
            'failed_plugins': failed_plugins
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to reload plugins: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/create', methods=['POST'])
@require_auth
@validate_input(['name'])
def create_plugin():
    """Create a new plugin from template"""
    try:
        data = request.get_json()
        plugin_name = data.get('name')
        description = data.get('description', '')
        
        # Validate plugin name
        if not plugin_name.replace('_', '').isalnum():
            return jsonify({
                'status': 'error',
                'message': 'Plugin name must contain only letters, numbers, and underscores'
            }), 400
        
        # Check if plugin already exists
        plugin_path = os.path.join(plugin_loader.tools_dir, f"{plugin_name}.py")
        if os.path.exists(plugin_path):
            return jsonify({
                'status': 'error',
                'message': f'Plugin "{plugin_name}" already exists'
            }), 400
        
        # Create plugin template
        created_path = plugin_loader.create_plugin_template(plugin_name, description)
        
        # Load the new plugin
        success = plugin_loader.load_plugin(plugin_name)
        
        return jsonify({
            'status': 'success',
            'message': f'Plugin "{plugin_name}" created successfully',
            'file_path': created_path,
            'loaded': success
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to create plugin: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/<plugin_name>/source', methods=['GET'])
@require_auth
def get_plugin_source(plugin_name):
    """Get the source code of a plugin"""
    try:
        plugin_info = plugin_loader.get_plugin_info(plugin_name)
        
        if not plugin_info:
            return jsonify({
                'status': 'error',
                'message': f'Plugin "{plugin_name}" not found'
            }), 404
        
        file_path = plugin_info['file_path']
        
        if not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': f'Plugin source file not found: {file_path}'
            }), 404
        
        with open(file_path, 'r') as f:
            source_code = f.read()
        
        return jsonify({
            'status': 'success',
            'source_code': source_code,
            'file_path': file_path
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve plugin source: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/<plugin_name>/source', methods=['PUT'])
@require_auth
@validate_input(['source_code'])
def update_plugin_source(plugin_name):
    """Update the source code of a plugin"""
    try:
        data = request.get_json()
        source_code = data.get('source_code')
        
        plugin_info = plugin_loader.get_plugin_info(plugin_name)
        
        if not plugin_info:
            return jsonify({
                'status': 'error',
                'message': f'Plugin "{plugin_name}" not found'
            }), 404
        
        file_path = plugin_info['file_path']
        
        # Backup original file
        backup_path = f"{file_path}.backup"
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                backup_content = f.read()
            with open(backup_path, 'w') as f:
                f.write(backup_content)
        
        # Write new source code
        with open(file_path, 'w') as f:
            f.write(source_code)
        
        # Try to reload the plugin
        success = plugin_loader.reload_plugin(plugin_name)
        
        if success:
            # Remove backup if successful
            if os.path.exists(backup_path):
                os.remove(backup_path)
            
            return jsonify({
                'status': 'success',
                'message': f'Plugin "{plugin_name}" updated and reloaded successfully'
            })
        else:
            # Restore backup if reload failed
            if os.path.exists(backup_path):
                with open(backup_path, 'r') as f:
                    backup_content = f.read()
                with open(file_path, 'w') as f:
                    f.write(backup_content)
                os.remove(backup_path)
                plugin_loader.reload_plugin(plugin_name)  # Reload original
            
            failed_plugins = plugin_loader.get_failed_plugins()
            error_msg = failed_plugins.get(plugin_name, 'Unknown error')
            
            return jsonify({
                'status': 'error',
                'message': f'Plugin update failed and was reverted. Error: {error_msg}'
            }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to update plugin: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/<plugin_name>', methods=['DELETE'])
@require_auth
def delete_plugin(plugin_name):
    """Delete a plugin"""
    try:
        plugin_info = plugin_loader.get_plugin_info(plugin_name)
        
        if not plugin_info:
            return jsonify({
                'status': 'error',
                'message': f'Plugin "{plugin_name}" not found'
            }), 404
        
        file_path = plugin_info['file_path']
        
        # Remove from registry
        if plugin_name in plugin_loader.plugin_registry:
            del plugin_loader.plugin_registry[plugin_name]
        if plugin_name in plugin_loader.plugin_metadata:
            del plugin_loader.plugin_metadata[plugin_name]
        if plugin_name in plugin_loader.loaded_plugins:
            plugin_loader.loaded_plugins.remove(plugin_name)
        
        # Delete file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return jsonify({
            'status': 'success',
            'message': f'Plugin "{plugin_name}" deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete plugin: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/categories', methods=['GET'])
@require_auth
def get_plugin_categories():
    """Get list of plugin categories"""
    try:
        plugins = plugin_loader.get_plugin_list()
        categories = set()
        
        for plugin in plugins:
            categories.add(plugin.get('category', 'general'))
        
        return jsonify({
            'status': 'success',
            'categories': sorted(list(categories))
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve categories: {str(e)}'
        }), 500

@plugins_bp.route('/api/plugins/search', methods=['POST'])
@require_auth
@validate_input(['query'])
def search_plugins():
    """Search plugins by name, description, or tags"""
    try:
        data = request.get_json()
        query = data.get('query', '').lower()
        category = data.get('category')
        enabled_only = data.get('enabled_only', False)
        
        plugins = plugin_loader.get_plugin_list()
        
        # Filter plugins
        filtered_plugins = []
        for plugin in plugins:
            # Category filter
            if category and plugin.get('category') != category:
                continue
            
            # Enabled filter
            if enabled_only and not plugin.get('enabled', True):
                continue
            
            # Search query
            if query:
                searchable_text = f"{plugin.get('name', '')} {plugin.get('description', '')} {' '.join(plugin.get('tags', []))}".lower()
                if query not in searchable_text:
                    continue
            
            filtered_plugins.append(plugin)
        
        return jsonify({
            'status': 'success',
            'plugins': filtered_plugins,
            'query': query,
            'category': category,
            'result_count': len(filtered_plugins)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Search failed: {str(e)}'
        }), 500

