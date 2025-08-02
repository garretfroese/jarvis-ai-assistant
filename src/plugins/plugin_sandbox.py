"""
Plugin Execution Sandbox for Jarvis AI Assistant
Secure, isolated environment for executing plugins with comprehensive monitoring.
"""

import os
import sys
import subprocess
import threading
import time
import json
import tempfile
import shutil
import signal
import resource
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import uuid

from ..services.logging_service import logging_service

@dataclass
class PluginExecution:
    """Plugin execution tracking"""
    execution_id: str
    plugin_name: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str  # running, completed, failed, timeout, killed
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    resource_usage: Dict[str, Any]
    sandbox_path: str

@dataclass
class PluginConfig:
    """Plugin configuration"""
    name: str
    version: str
    description: str
    author: str
    entry_point: str
    language: str  # python, javascript, shell
    timeout: int  # seconds
    memory_limit: int  # MB
    cpu_limit: float  # percentage
    network_access: bool
    file_access: List[str]  # allowed paths
    required_permissions: List[str]

class PluginSandbox:
    """Secure plugin execution sandbox"""
    
    def __init__(self):
        self.executions: Dict[str, PluginExecution] = {}
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.plugins: Dict[str, PluginConfig] = {}
        self.sandbox_base_path = "/tmp/jarvis_plugin_sandbox"
        
        # Create sandbox directory
        os.makedirs(self.sandbox_base_path, exist_ok=True)
        
        # Load built-in plugins
        self._load_builtin_plugins()
        
        print("✅ Plugin sandbox initialized")
    
    def _load_builtin_plugins(self):
        """Load built-in plugins"""
        # Example calculator plugin
        self.plugins['calculator'] = PluginConfig(
            name='calculator',
            version='1.0.0',
            description='Simple calculator plugin',
            author='Jarvis AI',
            entry_point='calculator.py',
            language='python',
            timeout=10,
            memory_limit=50,
            cpu_limit=10.0,
            network_access=False,
            file_access=[],
            required_permissions=['basic_computation']
        )
        
        # Example text processor plugin
        self.plugins['text_processor'] = PluginConfig(
            name='text_processor',
            version='1.0.0',
            description='Text processing utilities',
            author='Jarvis AI',
            entry_point='text_processor.py',
            language='python',
            timeout=30,
            memory_limit=100,
            cpu_limit=20.0,
            network_access=False,
            file_access=['/tmp'],
            required_permissions=['text_processing']
        )
        
        # Example web scraper plugin
        self.plugins['web_scraper'] = PluginConfig(
            name='web_scraper',
            version='1.0.0',
            description='Web scraping plugin',
            author='Jarvis AI',
            entry_point='web_scraper.py',
            language='python',
            timeout=60,
            memory_limit=200,
            cpu_limit=30.0,
            network_access=True,
            file_access=['/tmp'],
            required_permissions=['web_access', 'file_write']
        )
    
    def execute_plugin(self, plugin_name: str, input_data: Dict[str, Any], user_id: str, 
                      timeout: Optional[int] = None) -> str:
        """Execute a plugin and return execution ID"""
        
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin '{plugin_name}' not found")
        
        plugin_config = self.plugins[plugin_name]
        execution_id = str(uuid.uuid4())
        
        # Create execution record
        execution = PluginExecution(
            execution_id=execution_id,
            plugin_name=plugin_name,
            user_id=user_id,
            start_time=datetime.now(),
            end_time=None,
            status='running',
            input_data=input_data,
            output_data=None,
            error_message=None,
            resource_usage={},
            sandbox_path=os.path.join(self.sandbox_base_path, execution_id)
        )
        
        self.executions[execution_id] = execution
        
        # Start execution in background thread
        thread = threading.Thread(
            target=self._execute_plugin_async,
            args=(execution_id, plugin_config, input_data, timeout or plugin_config.timeout)
        )
        thread.daemon = True
        thread.start()
        
        # Log execution start
        if logging_service:
            logging_service.log_activity(
                user_id,
                'plugin_execution_started',
                {
                    'execution_id': execution_id,
                    'plugin_name': plugin_name,
                    'input_size': len(json.dumps(input_data))
                }
            )
        
        return execution_id
    
    def _execute_plugin_async(self, execution_id: str, plugin_config: PluginConfig, 
                             input_data: Dict[str, Any], timeout: int):
        """Execute plugin asynchronously"""
        execution = self.executions[execution_id]
        
        try:
            # Create sandbox environment
            sandbox_path = execution.sandbox_path
            os.makedirs(sandbox_path, exist_ok=True)
            
            # Create plugin script
            script_path = self._create_plugin_script(sandbox_path, plugin_config, input_data)
            
            # Execute plugin with resource limits
            result = self._execute_with_limits(
                script_path, plugin_config, timeout, sandbox_path
            )
            
            # Update execution record
            execution.end_time = datetime.now()
            execution.output_data = result.get('output')
            execution.error_message = result.get('error')
            execution.status = result.get('status', 'completed')
            execution.resource_usage = result.get('resource_usage', {})
            
            # Log execution completion
            if logging_service:
                logging_service.log_activity(
                    execution.user_id,
                    'plugin_execution_completed',
                    {
                        'execution_id': execution_id,
                        'plugin_name': plugin_config.name,
                        'status': execution.status,
                        'duration_ms': int((execution.end_time - execution.start_time).total_seconds() * 1000),
                        'output_size': len(json.dumps(execution.output_data)) if execution.output_data else 0
                    }
                )
            
        except Exception as e:
            # Handle execution error
            execution.end_time = datetime.now()
            execution.status = 'failed'
            execution.error_message = str(e)
            
            # Log execution error
            if logging_service:
                logging_service.log_activity(
                    execution.user_id,
                    'plugin_execution_failed',
                    {
                        'execution_id': execution_id,
                        'plugin_name': plugin_config.name,
                        'error': str(e)
                    }
                )
        
        finally:
            # Cleanup sandbox
            try:
                shutil.rmtree(sandbox_path, ignore_errors=True)
            except:
                pass
            
            # Remove from active processes
            if execution_id in self.active_processes:
                del self.active_processes[execution_id]
    
    def _create_plugin_script(self, sandbox_path: str, plugin_config: PluginConfig, 
                             input_data: Dict[str, Any]) -> str:
        """Create plugin script in sandbox"""
        
        if plugin_config.language == 'python':
            return self._create_python_script(sandbox_path, plugin_config, input_data)
        elif plugin_config.language == 'javascript':
            return self._create_javascript_script(sandbox_path, plugin_config, input_data)
        elif plugin_config.language == 'shell':
            return self._create_shell_script(sandbox_path, plugin_config, input_data)
        else:
            raise ValueError(f"Unsupported plugin language: {plugin_config.language}")
    
    def _create_python_script(self, sandbox_path: str, plugin_config: PluginConfig, 
                             input_data: Dict[str, Any]) -> str:
        """Create Python plugin script"""
        
        # Write input data to file
        input_file = os.path.join(sandbox_path, 'input.json')
        with open(input_file, 'w') as f:
            json.dump(input_data, f)
        
        # Create plugin script based on plugin name
        script_content = self._get_plugin_script_content(plugin_config.name, 'python')
        
        script_path = os.path.join(sandbox_path, plugin_config.entry_point)
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        return script_path
    
    def _create_javascript_script(self, sandbox_path: str, plugin_config: PluginConfig, 
                                 input_data: Dict[str, Any]) -> str:
        """Create JavaScript plugin script"""
        
        # Write input data to file
        input_file = os.path.join(sandbox_path, 'input.json')
        with open(input_file, 'w') as f:
            json.dump(input_data, f)
        
        # Create plugin script
        script_content = self._get_plugin_script_content(plugin_config.name, 'javascript')
        
        script_path = os.path.join(sandbox_path, plugin_config.entry_point)
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        return script_path
    
    def _create_shell_script(self, sandbox_path: str, plugin_config: PluginConfig, 
                            input_data: Dict[str, Any]) -> str:
        """Create shell plugin script"""
        
        # Write input data to file
        input_file = os.path.join(sandbox_path, 'input.json')
        with open(input_file, 'w') as f:
            json.dump(input_data, f)
        
        # Create plugin script
        script_content = self._get_plugin_script_content(plugin_config.name, 'shell')
        
        script_path = os.path.join(sandbox_path, plugin_config.entry_point)
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        return script_path
    
    def _get_plugin_script_content(self, plugin_name: str, language: str) -> str:
        """Get plugin script content based on plugin name and language"""
        
        if plugin_name == 'calculator' and language == 'python':
            return '''
import json
import sys
import os

def main():
    try:
        # Read input
        with open('input.json', 'r') as f:
            data = json.load(f)
        
        expression = data.get('expression', '')
        if not expression:
            raise ValueError("No expression provided")
        
        # Simple calculator - only allow basic operations
        allowed_chars = set('0123456789+-*/()., ')
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Invalid characters in expression")
        
        # Evaluate expression safely
        result = eval(expression)
        
        # Write output
        output = {
            "result": result,
            "expression": expression,
            "status": "success"
        }
        
        with open('output.json', 'w') as f:
            json.dump(output, f)
        
        print(json.dumps(output))
        
    except Exception as e:
        error_output = {
            "error": str(e),
            "status": "error"
        }
        
        with open('output.json', 'w') as f:
            json.dump(error_output, f)
        
        print(json.dumps(error_output))
        sys.exit(1)

if __name__ == '__main__':
    main()
'''
        
        elif plugin_name == 'text_processor' and language == 'python':
            return '''
import json
import sys
import re

def main():
    try:
        # Read input
        with open('input.json', 'r') as f:
            data = json.load(f)
        
        text = data.get('text', '')
        operation = data.get('operation', 'word_count')
        
        if operation == 'word_count':
            result = len(text.split())
        elif operation == 'char_count':
            result = len(text)
        elif operation == 'uppercase':
            result = text.upper()
        elif operation == 'lowercase':
            result = text.lower()
        elif operation == 'reverse':
            result = text[::-1]
        elif operation == 'remove_spaces':
            result = re.sub(r'\\s+', '', text)
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Write output
        output = {
            "result": result,
            "operation": operation,
            "original_text": text,
            "status": "success"
        }
        
        with open('output.json', 'w') as f:
            json.dump(output, f)
        
        print(json.dumps(output))
        
    except Exception as e:
        error_output = {
            "error": str(e),
            "status": "error"
        }
        
        with open('output.json', 'w') as f:
            json.dump(error_output, f)
        
        print(json.dumps(error_output))
        sys.exit(1)

if __name__ == '__main__':
    main()
'''
        
        elif plugin_name == 'web_scraper' and language == 'python':
            return '''
import json
import sys
import requests
from urllib.parse import urlparse

def main():
    try:
        # Read input
        with open('input.json', 'r') as f:
            data = json.load(f)
        
        url = data.get('url', '')
        if not url:
            raise ValueError("No URL provided")
        
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        
        # Make request with timeout
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Jarvis AI Assistant Plugin'
        })
        response.raise_for_status()
        
        # Extract basic information
        content = response.text
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "No title found"
        
        # Write output
        output = {
            "url": url,
            "title": title,
            "status_code": response.status_code,
            "content_length": len(content),
            "content_type": response.headers.get('content-type', 'unknown'),
            "status": "success"
        }
        
        with open('output.json', 'w') as f:
            json.dump(output, f)
        
        print(json.dumps(output))
        
    except Exception as e:
        error_output = {
            "error": str(e),
            "status": "error"
        }
        
        with open('output.json', 'w') as f:
            json.dump(error_output, f)
        
        print(json.dumps(error_output))
        sys.exit(1)

if __name__ == '__main__':
    main()
'''
        
        else:
            # Default plugin template
            return f'''
import json
import sys

def main():
    try:
        # Read input
        with open('input.json', 'r') as f:
            data = json.load(f)
        
        # Plugin logic here
        result = f"Plugin {plugin_name} executed with data: {{data}}"
        
        # Write output
        output = {{
            "result": result,
            "plugin": "{plugin_name}",
            "status": "success"
        }}
        
        with open('output.json', 'w') as f:
            json.dump(output, f)
        
        print(json.dumps(output))
        
    except Exception as e:
        error_output = {{
            "error": str(e),
            "status": "error"
        }}
        
        with open('output.json', 'w') as f:
            json.dump(error_output, f)
        
        print(json.dumps(error_output))
        sys.exit(1)

if __name__ == '__main__':
    main()
'''
    
    def _execute_with_limits(self, script_path: str, plugin_config: PluginConfig, 
                            timeout: int, sandbox_path: str) -> Dict[str, Any]:
        """Execute plugin with resource limits"""
        
        try:
            # Prepare command based on language
            if plugin_config.language == 'python':
                cmd = [sys.executable, script_path]
            elif plugin_config.language == 'javascript':
                cmd = ['node', script_path]
            elif plugin_config.language == 'shell':
                cmd = ['/bin/bash', script_path]
            else:
                raise ValueError(f"Unsupported language: {plugin_config.language}")
            
            # Set resource limits
            def set_limits():
                # Memory limit (in bytes)
                memory_limit = plugin_config.memory_limit * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
                
                # CPU time limit
                resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout))
                
                # File size limit (100MB)
                file_limit = 100 * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
                
                # Number of processes limit
                resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
            
            # Execute process
            start_time = time.time()
            
            process = subprocess.Popen(
                cmd,
                cwd=sandbox_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=set_limits,
                text=True
            )
            
            # Store process for potential termination
            execution_id = os.path.basename(sandbox_path)
            self.active_processes[execution_id] = process
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                end_time = time.time()
                
                # Read output file if exists
                output_file = os.path.join(sandbox_path, 'output.json')
                output_data = None
                
                if os.path.exists(output_file):
                    try:
                        with open(output_file, 'r') as f:
                            output_data = json.load(f)
                    except:
                        pass
                
                # If no output file, try to parse stdout
                if not output_data and stdout:
                    try:
                        output_data = json.loads(stdout)
                    except:
                        output_data = {"result": stdout, "status": "success"}
                
                return {
                    "status": "completed" if process.returncode == 0 else "failed",
                    "output": output_data,
                    "error": stderr if stderr else None,
                    "resource_usage": {
                        "execution_time": end_time - start_time,
                        "return_code": process.returncode
                    }
                }
                
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                return {
                    "status": "timeout",
                    "output": None,
                    "error": f"Plugin execution timed out after {timeout} seconds",
                    "resource_usage": {
                        "execution_time": timeout,
                        "return_code": -1
                    }
                }
            
        except Exception as e:
            return {
                "status": "failed",
                "output": None,
                "error": str(e),
                "resource_usage": {}
            }
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status"""
        if execution_id not in self.executions:
            return None
        
        execution = self.executions[execution_id]
        
        return {
            "execution_id": execution_id,
            "plugin_name": execution.plugin_name,
            "user_id": execution.user_id,
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "status": execution.status,
            "input_data": execution.input_data,
            "output_data": execution.output_data,
            "error_message": execution.error_message,
            "resource_usage": execution.resource_usage
        }
    
    def get_execution_result(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution result"""
        if execution_id not in self.executions:
            return None
        
        execution = self.executions[execution_id]
        
        if execution.status == 'running':
            return {
                "status": "running",
                "message": "Execution still in progress"
            }
        
        return {
            "status": execution.status,
            "output": execution.output_data,
            "error": execution.error_message,
            "resource_usage": execution.resource_usage
        }
    
    def kill_execution(self, execution_id: str) -> bool:
        """Kill a running execution"""
        if execution_id in self.active_processes:
            try:
                process = self.active_processes[execution_id]
                process.kill()
                process.wait()
                
                # Update execution record
                if execution_id in self.executions:
                    execution = self.executions[execution_id]
                    execution.end_time = datetime.now()
                    execution.status = 'killed'
                    execution.error_message = 'Execution killed by user'
                
                return True
            except:
                return False
        
        return False
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List available plugins"""
        return [
            {
                "name": config.name,
                "version": config.version,
                "description": config.description,
                "author": config.author,
                "language": config.language,
                "timeout": config.timeout,
                "memory_limit": config.memory_limit,
                "network_access": config.network_access,
                "required_permissions": config.required_permissions
            }
            for config in self.plugins.values()
        ]
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get plugin information"""
        if plugin_name not in self.plugins:
            return None
        
        config = self.plugins[plugin_name]
        return {
            "name": config.name,
            "version": config.version,
            "description": config.description,
            "author": config.author,
            "language": config.language,
            "timeout": config.timeout,
            "memory_limit": config.memory_limit,
            "cpu_limit": config.cpu_limit,
            "network_access": config.network_access,
            "file_access": config.file_access,
            "required_permissions": config.required_permissions
        }
    
    def get_execution_history(self, user_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history"""
        executions = list(self.executions.values())
        
        if user_id:
            executions = [e for e in executions if e.user_id == user_id]
        
        # Sort by start time (newest first)
        executions.sort(key=lambda x: x.start_time, reverse=True)
        
        return [
            {
                "execution_id": e.execution_id,
                "plugin_name": e.plugin_name,
                "user_id": e.user_id,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat() if e.end_time else None,
                "status": e.status,
                "duration": (e.end_time - e.start_time).total_seconds() if e.end_time else None
            }
            for e in executions[:limit]
        ]
    
    def get_sandbox_statistics(self) -> Dict[str, Any]:
        """Get sandbox statistics"""
        total_executions = len(self.executions)
        running_executions = len([e for e in self.executions.values() if e.status == 'running'])
        
        # Status distribution
        status_counts = {}
        for execution in self.executions.values():
            status = execution.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Plugin usage
        plugin_counts = {}
        for execution in self.executions.values():
            plugin = execution.plugin_name
            plugin_counts[plugin] = plugin_counts.get(plugin, 0) + 1
        
        return {
            "total_executions": total_executions,
            "running_executions": running_executions,
            "available_plugins": len(self.plugins),
            "status_distribution": status_counts,
            "plugin_usage": plugin_counts,
            "active_processes": len(self.active_processes)
        }

# Global instance
plugin_sandbox = PluginSandbox()

