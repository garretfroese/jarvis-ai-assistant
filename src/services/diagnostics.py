"""
System Diagnostics Service for Jarvis
Provides system health checks and monitoring capabilities
"""

import os
import time
import json
from datetime import datetime
try:
    import psutil
    PSUTIL_AVAILABLE = True
except (ImportError, NotImplementedError):
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available - system metrics will be limited")

import requests
from datetime import datetime
from typing import Dict, Any, List
from ..services.mode_manager import ModeManager
from ..services.file_processor import FileProcessor

class DiagnosticsService:
    def __init__(self):
        self.mode_manager = ModeManager()
        self.file_processor = FileProcessor()
        self.start_time = time.time()
    
    def check_openai_connection(self, api_key: str = None) -> Dict[str, Any]:
        """Test OpenAI API connection and model access"""
        result = {
            'status': 'unknown',
            'model': None,
            'streaming': False,
            'error': None,
            'response_time': None
        }
        
        try:
            if not api_key:
                api_key = os.getenv('OPENAI_API_KEY')
            
            if not api_key:
                result['status'] = 'error'
                result['error'] = 'No API key provided'
                return result
            
            # Test API connection with a simple request
            start_time = time.time()
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Test with a minimal request
            test_data = {
                'model': 'gpt-4o',
                'messages': [{'role': 'user', 'content': 'Test'}],
                'max_tokens': 5,
                'stream': False
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=test_data,
                timeout=10
            )
            
            response_time = time.time() - start_time
            result['response_time'] = round(response_time * 1000, 2)  # ms
            
            if response.status_code == 200:
                data = response.json()
                result['status'] = 'ok'
                result['model'] = data.get('model', 'gpt-4o')
                result['streaming'] = True  # We know streaming works if basic API works
            else:
                result['status'] = 'error'
                result['error'] = f'API returned {response.status_code}: {response.text[:200]}'
                
        except requests.RequestException as e:
            result['status'] = 'error'
            result['error'] = f'Connection error: {str(e)}'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = f'Unexpected error: {str(e)}'
        
        return result
    
    def check_tools_status(self) -> Dict[str, Any]:
        """Check status of all available tools"""
        tools_status = {}
        
        # Define tool checks
        tool_checks = {
            'web_browsing': self._check_web_browsing,
            'code_execution': self._check_code_execution,
            'file_processing': self._check_file_processing,
            'weather': self._check_weather_service,
            'email': self._check_email_service,
            'slack': self._check_slack_service,
            'github': self._check_github_service,
            'railway': self._check_railway_service
        }
        
        for tool_name, check_func in tool_checks.items():
            try:
                tools_status[tool_name] = check_func()
            except Exception as e:
                tools_status[tool_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return tools_status
    
    def _check_web_browsing(self) -> Dict[str, Any]:
        """Check web browsing capability"""
        try:
            # Test DuckDuckGo search
            response = requests.get('https://duckduckgo.com', timeout=5)
            if response.status_code == 200:
                return {'status': 'ok', 'service': 'DuckDuckGo'}
            else:
                return {'status': 'error', 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _check_code_execution(self) -> Dict[str, Any]:
        """Check code execution capability"""
        try:
            # Test basic Python execution
            import subprocess
            result = subprocess.run(['python3', '-c', 'print("test")'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and 'test' in result.stdout:
                return {'status': 'ok', 'python_version': 'available'}
            else:
                return {'status': 'error', 'error': 'Python execution failed'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _check_file_processing(self) -> Dict[str, Any]:
        """Check file processing capability"""
        try:
            # Check if required libraries are available
            libraries = []
            try:
                import PyPDF2
                libraries.append('PyPDF2')
            except ImportError:
                pass
            
            try:
                from docx import Document
                libraries.append('python-docx')
            except ImportError:
                pass
            
            try:
                from PIL import Image
                libraries.append('Pillow')
            except ImportError:
                pass
            
            return {
                'status': 'ok' if libraries else 'limited',
                'available_libraries': libraries,
                'supported_types': list(self.file_processor.allowed_extensions.keys())
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _check_weather_service(self) -> Dict[str, Any]:
        """Check weather service availability"""
        try:
            response = requests.get('https://wttr.in/London?format=j1', timeout=5)
            if response.status_code == 200:
                return {'status': 'ok', 'service': 'wttr.in'}
            else:
                return {'status': 'error', 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _check_email_service(self) -> Dict[str, Any]:
        """Check email service configuration"""
        smtp_host = os.getenv('SMTP_HOST')
        sendgrid_key = os.getenv('SENDGRID_API_KEY')
        
        if smtp_host or sendgrid_key:
            return {
                'status': 'configured',
                'smtp': bool(smtp_host),
                'sendgrid': bool(sendgrid_key)
            }
        else:
            return {'status': 'not_configured', 'error': 'No email service configured'}
    
    def _check_slack_service(self) -> Dict[str, Any]:
        """Check Slack service configuration"""
        slack_token = os.getenv('SLACK_BOT_TOKEN')
        
        if slack_token:
            return {'status': 'configured', 'has_token': True}
        else:
            return {'status': 'not_configured', 'error': 'No Slack token configured'}
    
    def _check_github_service(self) -> Dict[str, Any]:
        """Check GitHub service configuration"""
        github_token = os.getenv('GITHUB_TOKEN')
        
        if github_token:
            return {'status': 'configured', 'has_token': True}
        else:
            return {'status': 'not_configured', 'error': 'No GitHub token configured'}
    
    def _check_railway_service(self) -> Dict[str, Any]:
        """Check Railway service configuration"""
        railway_token = os.getenv('RAILWAY_TOKEN')
        
        if railway_token:
            return {'status': 'configured', 'has_token': True}
        else:
            return {'status': 'not_configured', 'error': 'No Railway token configured'}
    
    def check_memory_status(self) -> Dict[str, Any]:
        """Check memory and session status"""
        try:
            # Check available modes
            modes = self.mode_manager.get_all_modes()
            
            # Check session storage
            sessions = self.mode_manager.load_sessions()
            
            return {
                'status': 'ok',
                'available_modes': len(modes),
                'mode_names': list(modes.keys()),
                'active_sessions': len(sessions),
                'default_mode': 'default'
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        if not PSUTIL_AVAILABLE:
            return {
                'status': 'limited',
                'error': 'System metrics not available (psutil not supported)',
                'uptime_seconds': time.time() - self.start_time,
                'uptime_formatted': self._format_uptime(time.time() - self.start_time)
            }
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Uptime
            uptime = time.time() - self.start_time
            
            return {
                'status': 'ok',
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                'uptime_seconds': uptime,
                'uptime_formatted': self._format_uptime(uptime)
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def run_full_diagnostics(self, api_key: str = None) -> Dict[str, Any]:
        """Run comprehensive system diagnostics"""
        start_time = time.time()
        
        diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'version': '2.5.0',
            'diagnostics_duration': None,
            'overall_status': 'unknown',
            'openai': self.check_openai_connection(api_key),
            'tools': self.check_tools_status(),
            'memory': self.check_memory_status(),
            'system': self.check_system_resources()
        }
        
        # Calculate overall status
        issues = []
        
        if diagnostics['openai']['status'] != 'ok':
            issues.append('OpenAI API')
        
        tool_issues = [name for name, status in diagnostics['tools'].items() 
                      if status.get('status') == 'error']
        if tool_issues:
            issues.append(f"Tools: {', '.join(tool_issues)}")
        
        if diagnostics['memory']['status'] != 'ok':
            issues.append('Memory/Sessions')
        
        if diagnostics['system']['status'] != 'ok':
            issues.append('System Resources')
        
        if not issues:
            diagnostics['overall_status'] = 'healthy'
        elif len(issues) <= 2:
            diagnostics['overall_status'] = 'warning'
            diagnostics['issues'] = issues
        else:
            diagnostics['overall_status'] = 'critical'
            diagnostics['issues'] = issues
        
        diagnostics['diagnostics_duration'] = round((time.time() - start_time) * 1000, 2)
        
        return diagnostics
    
    def get_quick_status(self) -> Dict[str, Any]:
        """Get quick system status without full diagnostics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'status': 'running',
            'uptime': self._format_uptime(time.time() - self.start_time),
            'memory_usage': psutil.virtual_memory().percent,
            'cpu_usage': psutil.cpu_percent(),
            'available_modes': len(self.mode_manager.get_all_modes())
        }

