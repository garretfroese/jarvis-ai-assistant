"""
Modular Plugin Loader for Jarvis
Dynamically loads and manages tool plugins from the /tools/ directory
"""

import os
import sys
import json
import importlib.util
import inspect
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import traceback

class PluginLoader:
    def __init__(self):
        self.tools_dir = os.path.join(os.path.dirname(__file__), '..', 'tools')
        self.plugin_registry = {}
        self.plugin_metadata = {}
        self.loaded_plugins = set()
        self.failed_plugins = {}
        self.ensure_tools_directory()
        self.load_all_plugins()
    
    def ensure_tools_directory(self):
        """Ensure the tools directory exists"""
        if not os.path.exists(self.tools_dir):
            os.makedirs(self.tools_dir)
            
        # Create __init__.py if it doesn't exist
        init_file = os.path.join(self.tools_dir, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('# Jarvis Tools Directory\n')
    
    def load_all_plugins(self):
        """Load all plugins from the tools directory"""
        if not os.path.exists(self.tools_dir):
            print(f"Tools directory not found: {self.tools_dir}")
            return
        
        # Clear existing plugins
        self.plugin_registry.clear()
        self.plugin_metadata.clear()
        self.loaded_plugins.clear()
        self.failed_plugins.clear()
        
        # Scan for Python files
        for filename in os.listdir(self.tools_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                plugin_name = filename[:-3]  # Remove .py extension
                self.load_plugin(plugin_name)
    
    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a specific plugin by name
        
        Args:
            plugin_name: Name of the plugin file (without .py extension)
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        plugin_path = os.path.join(self.tools_dir, f"{plugin_name}.py")
        
        if not os.path.exists(plugin_path):
            self.failed_plugins[plugin_name] = f"Plugin file not found: {plugin_path}"
            return False
        
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None or spec.loader is None:
                self.failed_plugins[plugin_name] = "Failed to create module spec"
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Validate plugin structure
            validation_result = self.validate_plugin(module, plugin_name)
            if not validation_result['valid']:
                self.failed_plugins[plugin_name] = validation_result['error']
                return False
            
            # Extract plugin information
            manifest = getattr(module, 'manifest', {})
            run_function = getattr(module, 'run')
            
            # Register the plugin
            self.plugin_registry[plugin_name] = {
                'module': module,
                'run': run_function,
                'manifest': manifest,
                'loaded_at': datetime.now().isoformat()
            }
            
            # Store metadata
            self.plugin_metadata[plugin_name] = {
                'name': manifest.get('name', plugin_name),
                'description': manifest.get('description', 'No description provided'),
                'version': manifest.get('version', '1.0.0'),
                'author': manifest.get('author', 'Unknown'),
                'category': manifest.get('category', 'general'),
                'tags': manifest.get('tags', []),
                'requires_auth': manifest.get('requires_auth', True),
                'enabled': manifest.get('enabled', True),
                'file_path': plugin_path,
                'loaded_at': datetime.now().isoformat()
            }
            
            self.loaded_plugins.add(plugin_name)
            print(f"Successfully loaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            error_msg = f"Error loading plugin {plugin_name}: {str(e)}\n{traceback.format_exc()}"
            self.failed_plugins[plugin_name] = error_msg
            print(error_msg)
            return False
    
    def validate_plugin(self, module, plugin_name: str) -> Dict[str, Any]:
        """
        Validate that a plugin has the required structure
        
        Args:
            module: The loaded Python module
            plugin_name: Name of the plugin
            
        Returns:
            Dict with 'valid' boolean and 'error' message if invalid
        """
        # Check for required 'run' function
        if not hasattr(module, 'run'):
            return {
                'valid': False,
                'error': "Plugin must have a 'run' function"
            }
        
        run_function = getattr(module, 'run')
        if not callable(run_function):
            return {
                'valid': False,
                'error': "'run' must be a callable function"
            }
        
        # Check function signature
        try:
            sig = inspect.signature(run_function)
            params = list(sig.parameters.keys())
            
            # Must accept at least one parameter (input)
            if len(params) < 1:
                return {
                    'valid': False,
                    'error': "'run' function must accept at least one parameter (input)"
                }
        except Exception as e:
            return {
                'valid': False,
                'error': f"Error inspecting 'run' function signature: {str(e)}"
            }
        
        # Check for manifest (optional but recommended)
        if hasattr(module, 'manifest'):
            manifest = getattr(module, 'manifest')
            if not isinstance(manifest, dict):
                return {
                    'valid': False,
                    'error': "'manifest' must be a dictionary"
                }
        
        # Security validation
        security_check = self.validate_plugin_security(module, plugin_name)
        if not security_check['valid']:
            return security_check
        
        return {'valid': True, 'error': None}
    
    def validate_plugin_security(self, module, plugin_name: str) -> Dict[str, Any]:
        """
        Perform basic security validation on a plugin
        
        Args:
            module: The loaded Python module
            plugin_name: Name of the plugin
            
        Returns:
            Dict with 'valid' boolean and 'error' message if invalid
        """
        # Get the source code for analysis
        try:
            source_file = inspect.getfile(module)
            with open(source_file, 'r') as f:
                source_code = f.read()
        except Exception:
            # If we can't read the source, allow it but log a warning
            print(f"Warning: Could not read source code for security validation of {plugin_name}")
            return {'valid': True, 'error': None}
        
        # List of potentially dangerous operations
        dangerous_patterns = [
            'os.system(',
            'subprocess.call(',
            'subprocess.run(',
            'subprocess.Popen(',
            'eval(',
            'exec(',
            '__import__(',
            'open(',  # File operations should be controlled
            'file(',
            'input(',  # User input should be controlled
            'raw_input(',
        ]
        
        # Check for dangerous patterns
        for pattern in dangerous_patterns:
            if pattern in source_code:
                return {
                    'valid': False,
                    'error': f"Plugin contains potentially dangerous operation: {pattern}"
                }
        
        return {'valid': True, 'error': None}
    
    def execute_plugin(self, plugin_name: str, input_data: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a plugin with the given input
        
        Args:
            plugin_name: Name of the plugin to execute
            input_data: Input string to pass to the plugin
            **kwargs: Additional keyword arguments
            
        Returns:
            Dict with execution result
        """
        if plugin_name not in self.plugin_registry:
            return {
                'success': False,
                'error': f"Plugin '{plugin_name}' not found or not loaded",
                'output': None
            }
        
        plugin = self.plugin_registry[plugin_name]
        
        # Check if plugin is enabled
        if not self.plugin_metadata[plugin_name].get('enabled', True):
            return {
                'success': False,
                'error': f"Plugin '{plugin_name}' is disabled",
                'output': None
            }
        
        try:
            # Execute the plugin
            start_time = datetime.now()
            
            # Get the run function
            run_function = plugin['run']
            
            # Prepare arguments based on function signature
            sig = inspect.signature(run_function)
            params = list(sig.parameters.keys())
            
            # Call with appropriate arguments
            if len(params) == 1:
                result = run_function(input_data)
            else:
                # Pass additional kwargs if function accepts them
                result = run_function(input_data, **kwargs)
            
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                'success': True,
                'error': None,
                'output': str(result) if result is not None else None,
                'duration_ms': duration_ms,
                'executed_at': end_time.isoformat()
            }
            
        except Exception as e:
            error_msg = f"Error executing plugin '{plugin_name}': {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'output': None,
                'traceback': traceback.format_exc()
            }
    
    def get_plugin_list(self) -> List[Dict[str, Any]]:
        """Get list of all loaded plugins with their metadata"""
        plugins = []
        
        for plugin_name in self.loaded_plugins:
            metadata = self.plugin_metadata.get(plugin_name, {})
            plugins.append({
                'name': plugin_name,
                'display_name': metadata.get('name', plugin_name),
                'description': metadata.get('description', ''),
                'version': metadata.get('version', '1.0.0'),
                'author': metadata.get('author', 'Unknown'),
                'category': metadata.get('category', 'general'),
                'tags': metadata.get('tags', []),
                'enabled': metadata.get('enabled', True),
                'requires_auth': metadata.get('requires_auth', True),
                'loaded_at': metadata.get('loaded_at', '')
            })
        
        return plugins
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific plugin"""
        if plugin_name not in self.plugin_registry:
            return None
        
        plugin = self.plugin_registry[plugin_name]
        metadata = self.plugin_metadata[plugin_name]
        
        # Get function signature
        run_function = plugin['run']
        sig = inspect.signature(run_function)
        
        return {
            'name': plugin_name,
            'metadata': metadata,
            'manifest': plugin['manifest'],
            'function_signature': str(sig),
            'loaded_at': plugin['loaded_at'],
            'file_path': metadata.get('file_path', ''),
            'status': 'loaded'
        }
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin"""
        if plugin_name in self.plugin_metadata:
            self.plugin_metadata[plugin_name]['enabled'] = True
            return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin"""
        if plugin_name in self.plugin_metadata:
            self.plugin_metadata[plugin_name]['enabled'] = False
            return True
        return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a specific plugin"""
        # Remove from registry if exists
        if plugin_name in self.plugin_registry:
            del self.plugin_registry[plugin_name]
        if plugin_name in self.plugin_metadata:
            del self.plugin_metadata[plugin_name]
        if plugin_name in self.loaded_plugins:
            self.loaded_plugins.remove(plugin_name)
        if plugin_name in self.failed_plugins:
            del self.failed_plugins[plugin_name]
        
        # Reload
        return self.load_plugin(plugin_name)
    
    def get_failed_plugins(self) -> Dict[str, str]:
        """Get list of plugins that failed to load"""
        return self.failed_plugins.copy()
    
    def is_plugin_available(self, plugin_name: str) -> bool:
        """Check if a plugin is available and enabled"""
        return (plugin_name in self.plugin_registry and 
                self.plugin_metadata.get(plugin_name, {}).get('enabled', True))
    
    def create_plugin_template(self, plugin_name: str, description: str = "") -> str:
        """Create a template plugin file"""
        template = f'''"""
{plugin_name.title()} Plugin for Jarvis
{description}
"""

# Plugin manifest - metadata about this plugin
manifest = {{
    "name": "{plugin_name.title()}",
    "description": "{description or f'A plugin for {plugin_name}'}",
    "version": "1.0.0",
    "author": "Jarvis User",
    "category": "general",
    "tags": ["{plugin_name}"],
    "requires_auth": True,
    "enabled": True
}}

def run(input_text: str) -> str:
    """
    Main plugin function - this is called when the plugin is executed
    
    Args:
        input_text (str): The input text/command from the user
        
    Returns:
        str: The result/output of the plugin execution
    """
    # TODO: Implement your plugin logic here
    
    # Example implementation:
    return f"Hello from {{manifest['name']}}! You said: {{input_text}}"

# Optional: Add any helper functions below
def helper_function():
    """Example helper function"""
    pass
'''
        
        plugin_path = os.path.join(self.tools_dir, f"{plugin_name}.py")
        
        try:
            with open(plugin_path, 'w') as f:
                f.write(template)
            return plugin_path
        except Exception as e:
            raise Exception(f"Failed to create plugin template: {str(e)}")

# Global plugin loader instance
plugin_loader = PluginLoader()

def get_available_plugins() -> List[Dict[str, Any]]:
    """Convenience function to get available plugins"""
    return plugin_loader.get_plugin_list()

def execute_plugin(plugin_name: str, input_data: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to execute a plugin"""
    return plugin_loader.execute_plugin(plugin_name, input_data, **kwargs)

def is_plugin_available(plugin_name: str) -> bool:
    """Convenience function to check plugin availability"""
    return plugin_loader.is_plugin_available(plugin_name)

