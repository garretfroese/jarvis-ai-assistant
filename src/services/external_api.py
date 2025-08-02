"""
External API Endpoints for Jarvis AI Assistant
Provides secure external access to Jarvis functionality via REST API.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from flask import request, jsonify, send_file
import tempfile

from .api_gateway import api_gateway, require_api_key, APIKeyPermission
from .logging_service import logging_service, LogLevel, LogCategory

class ExternalAPI:
    """External API endpoints for Jarvis"""
    
    def __init__(self):
        self.enabled = api_gateway.enabled
        self.max_file_size = int(os.getenv('API_MAX_FILE_SIZE', '10485760'))  # 10MB default
        self.max_prompt_length = int(os.getenv('API_MAX_PROMPT_LENGTH', '10000'))  # 10k chars
        
        print("✅ External API initialized")
    
    def register_routes(self, app):
        """Register external API routes with Flask app"""
        
        # External chat endpoint
        @app.route('/api/external/chat', methods=['POST'])
        @require_api_key(APIKeyPermission.CHAT)
        def external_chat():
            """External chat interface"""
            start_time = time.time()
            
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "JSON data required"}), 400
                
                prompt = data.get('prompt', '').strip()
                if not prompt:
                    return jsonify({"error": "Prompt is required"}), 400
                
                if len(prompt) > self.max_prompt_length:
                    return jsonify({"error": f"Prompt too long (max {self.max_prompt_length} characters)"}), 400
                
                # Optional parameters
                mode = data.get('mode', 'default')
                session_id = data.get('session_id', 'external')
                user_id = data.get('user_id', 'external')
                
                # Process chat request
                response = self._process_chat_request(prompt, mode, session_id, user_id)
                
                # Log successful request
                response_time = int((time.time() - start_time) * 1000)
                api_gateway.log_api_request(
                    request.api_key,
                    '/api/external/chat',
                    request.remote_addr,
                    request.headers.get('User-Agent', ''),
                    True,
                    response_time
                )
                
                return jsonify({
                    "response": response,
                    "mode": mode,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "status": "success"
                })
                
            except Exception as e:
                # Log failed request
                response_time = int((time.time() - start_time) * 1000)
                api_gateway.log_api_request(
                    request.api_key,
                    '/api/external/chat',
                    request.remote_addr,
                    request.headers.get('User-Agent', ''),
                    False,
                    response_time,
                    str(e)
                )
                
                return jsonify({"error": f"Chat processing failed: {str(e)}"}), 500
        
        # External execute endpoint
        @app.route('/api/external/execute', methods=['POST'])
        @require_api_key(APIKeyPermission.EXECUTE)
        def external_execute():
            """Execute tool/workflow/plugin"""
            start_time = time.time()
            
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "JSON data required"}), 400
                
                action_type = data.get('type', '').lower()  # tool, workflow, plugin
                action_name = data.get('name', '').strip()
                parameters = data.get('parameters', {})
                
                if not action_type or not action_name:
                    return jsonify({"error": "Type and name are required"}), 400
                
                if action_type not in ['tool', 'workflow', 'plugin']:
                    return jsonify({"error": "Type must be 'tool', 'workflow', or 'plugin'"}), 400
                
                # Execute the requested action
                result = self._execute_action(action_type, action_name, parameters)
                
                # Log successful request
                response_time = int((time.time() - start_time) * 1000)
                api_gateway.log_api_request(
                    request.api_key,
                    '/api/external/execute',
                    request.remote_addr,
                    request.headers.get('User-Agent', ''),
                    True,
                    response_time
                )
                
                return jsonify({
                    "result": result,
                    "type": action_type,
                    "name": action_name,
                    "timestamp": datetime.now().isoformat(),
                    "status": "success"
                })
                
            except Exception as e:
                # Log failed request
                response_time = int((time.time() - start_time) * 1000)
                api_gateway.log_api_request(
                    request.api_key,
                    '/api/external/execute',
                    request.remote_addr,
                    request.headers.get('User-Agent', ''),
                    False,
                    response_time,
                    str(e)
                )
                
                return jsonify({"error": f"Execution failed: {str(e)}"}), 500
        
        # External status endpoint
        @app.route('/api/external/status', methods=['GET'])
        @require_api_key(APIKeyPermission.STATUS)
        def external_status():
            """Get system status"""
            start_time = time.time()
            
            try:
                status = self._get_system_status()
                
                # Log successful request
                response_time = int((time.time() - start_time) * 1000)
                api_gateway.log_api_request(
                    request.api_key,
                    '/api/external/status',
                    request.remote_addr,
                    request.headers.get('User-Agent', ''),
                    True,
                    response_time
                )
                
                return jsonify(status)
                
            except Exception as e:
                # Log failed request
                response_time = int((time.time() - start_time) * 1000)
                api_gateway.log_api_request(
                    request.api_key,
                    '/api/external/status',
                    request.remote_addr,
                    request.headers.get('User-Agent', ''),
                    False,
                    response_time,
                    str(e)
                )
                
                return jsonify({"error": f"Status check failed: {str(e)}"}), 500
        
        # External upload endpoint
        @app.route('/api/external/upload', methods=['POST'])
        @require_api_key(APIKeyPermission.UPLOAD)
        def external_upload():
            """Upload and analyze file"""
            start_time = time.time()
            
            try:
                if 'file' not in request.files:
                    return jsonify({"error": "File is required"}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({"error": "No file selected"}), 400
                
                # Check file size
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Reset to beginning
                
                if file_size > self.max_file_size:
                    return jsonify({"error": f"File too large (max {self.max_file_size} bytes)"}), 400
                
                # Optional analysis parameters
                analysis_type = request.form.get('analysis_type', 'summary')
                include_insights = request.form.get('include_insights', 'true').lower() == 'true'
                
                # Process file upload
                result = self._process_file_upload(file, analysis_type, include_insights)
                
                # Log successful request
                response_time = int((time.time() - start_time) * 1000)
                api_gateway.log_api_request(
                    request.api_key,
                    '/api/external/upload',
                    request.remote_addr,
                    request.headers.get('User-Agent', ''),
                    True,
                    response_time
                )
                
                return jsonify({
                    "analysis": result,
                    "filename": file.filename,
                    "file_size": file_size,
                    "analysis_type": analysis_type,
                    "timestamp": datetime.now().isoformat(),
                    "status": "success"
                })
                
            except Exception as e:
                # Log failed request
                response_time = int((time.time() - start_time) * 1000)
                api_gateway.log_api_request(
                    request.api_key,
                    '/api/external/upload',
                    request.remote_addr,
                    request.headers.get('User-Agent', ''),
                    False,
                    response_time,
                    str(e)
                )
                
                return jsonify({"error": f"File upload failed: {str(e)}"}), 500
        
        # External mode endpoint
        @app.route('/api/external/mode', methods=['GET', 'POST'])
        @require_api_key(APIKeyPermission.MODE)
        def external_mode():
            """Get or set operating mode"""
            start_time = time.time()
            
            try:
                if request.method == 'GET':
                    # Get current mode
                    mode_info = self._get_current_mode()
                    
                    # Log successful request
                    response_time = int((time.time() - start_time) * 1000)
                    api_gateway.log_api_request(
                        request.api_key,
                        '/api/external/mode',
                        request.remote_addr,
                        request.headers.get('User-Agent', ''),
                        True,
                        response_time
                    )
                    
                    return jsonify(mode_info)
                
                else:  # POST
                    data = request.get_json()
                    if not data:
                        return jsonify({"error": "JSON data required"}), 400
                    
                    new_mode = data.get('mode', '').strip()
                    if not new_mode:
                        return jsonify({"error": "Mode is required"}), 400
                    
                    # Set new mode
                    result = self._set_mode(new_mode)
                    
                    # Log successful request
                    response_time = int((time.time() - start_time) * 1000)
                    api_gateway.log_api_request(
                        request.api_key,
                        '/api/external/mode',
                        request.remote_addr,
                        request.headers.get('User-Agent', ''),
                        True,
                        response_time
                    )
                    
                    return jsonify({
                        "previous_mode": result['previous_mode'],
                        "current_mode": result['current_mode'],
                        "timestamp": datetime.now().isoformat(),
                        "status": "success"
                    })
                
            except Exception as e:
                # Log failed request
                response_time = int((time.time() - start_time) * 1000)
                api_gateway.log_api_request(
                    request.api_key,
                    '/api/external/mode',
                    request.remote_addr,
                    request.headers.get('User-Agent', ''),
                    False,
                    response_time,
                    str(e)
                )
                
                return jsonify({"error": f"Mode operation failed: {str(e)}"}), 500
        
        # API documentation endpoint
        @app.route('/api/external/docs', methods=['GET'])
        def external_docs():
            """API documentation"""
            try:
                docs = self._generate_api_docs()
                return jsonify(docs)
            except Exception as e:
                return jsonify({"error": f"Documentation generation failed: {str(e)}"}), 500
    
    def _process_chat_request(self, prompt: str, mode: str, session_id: str, user_id: str) -> str:
        """Process external chat request"""
        try:
            # Import chat processing components
            from .command_router import command_router
            from .session_manager import session_manager
            
            # Set session context
            session_manager.set_current_session(session_id)
            session_manager.set_current_user(user_id)
            
            # Route and process the command
            result = command_router.route_command(prompt, user_id, session_id)
            
            if result.get('success'):
                return result.get('response', 'Command executed successfully')
            else:
                return f"Error: {result.get('error', 'Unknown error occurred')}"
                
        except Exception as e:
            return f"Chat processing error: {str(e)}"
    
    def _execute_action(self, action_type: str, action_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool, workflow, or plugin"""
        try:
            if action_type == 'tool':
                from .tool_router import tool_router
                return tool_router.execute_tool(action_name, parameters)
            
            elif action_type == 'workflow':
                from .workflow_engine import workflow_engine
                return workflow_engine.execute_workflow(action_name, parameters)
            
            elif action_type == 'plugin':
                from ..plugins.plugin_sandbox import plugin_sandbox
                return plugin_sandbox.execute_plugin(action_name, parameters)
            
            else:
                return {"error": f"Unknown action type: {action_type}"}
                
        except Exception as e:
            return {"error": f"Execution failed: {str(e)}"}
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "status": "healthy",
                    "version": "12.0.0",
                    "uptime": self._get_uptime()
                },
                "services": {
                    "api_gateway": api_gateway.enabled,
                    "chat": True,
                    "tools": True,
                    "workflows": True,
                    "plugins": True,
                    "file_processing": True
                },
                "current_mode": "default",
                "available_modes": [
                    "default", "ceo", "legal", "technical", "creative", "analyst"
                ],
                "tools": self._get_available_tools(),
                "workflows": self._get_available_workflows(),
                "plugins": self._get_available_plugins()
            }
            
            return status
            
        except Exception as e:
            return {"error": f"Status check failed: {str(e)}"}
    
    def _process_file_upload(self, file, analysis_type: str, include_insights: bool) -> Dict[str, Any]:
        """Process uploaded file and return analysis"""
        try:
            # Save file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name
            
            try:
                # Process file based on type
                from .advanced_file_processor import file_processor
                
                result = file_processor.process_file(
                    temp_path,
                    analysis_type=analysis_type,
                    include_insights=include_insights
                )
                
                return result
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            return {"error": f"File processing failed: {str(e)}"}
    
    def _get_current_mode(self) -> Dict[str, Any]:
        """Get current operating mode"""
        try:
            # This would integrate with the mode management system
            return {
                "current_mode": "default",
                "available_modes": [
                    "default", "ceo", "legal", "technical", "creative", "analyst"
                ],
                "mode_description": "Default conversational mode",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": f"Mode check failed: {str(e)}"}
    
    def _set_mode(self, new_mode: str) -> Dict[str, Any]:
        """Set new operating mode"""
        try:
            # This would integrate with the mode management system
            previous_mode = "default"
            
            # Validate mode
            valid_modes = ["default", "ceo", "legal", "technical", "creative", "analyst"]
            if new_mode not in valid_modes:
                raise ValueError(f"Invalid mode. Valid modes: {valid_modes}")
            
            return {
                "previous_mode": previous_mode,
                "current_mode": new_mode,
                "success": True
            }
        except Exception as e:
            return {"error": f"Mode change failed: {str(e)}"}
    
    def _get_uptime(self) -> str:
        """Get system uptime"""
        try:
            import psutil
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            return f"{days}d {hours}h {minutes}m"
        except:
            return "unknown"
    
    def _get_available_tools(self) -> List[str]:
        """Get list of available tools"""
        try:
            from .tool_router import tool_router
            return list(tool_router.tools.keys())
        except:
            return ["weather_lookup", "web_search", "web_scraper", "url_summarizer", "command_executor"]
    
    def _get_available_workflows(self) -> List[str]:
        """Get list of available workflows"""
        try:
            from .workflow_engine import workflow_engine
            return list(workflow_engine.workflows.keys())
        except:
            return ["send_followup_email", "daily_summary", "notify_overdue"]
    
    def _get_available_plugins(self) -> List[str]:
        """Get list of available plugins"""
        try:
            from ..plugins.plugin_sandbox import plugin_sandbox
            return list(plugin_sandbox.plugins.keys())
        except:
            return ["calculator", "text_processor", "web_scraper"]
    
    def _generate_api_docs(self) -> Dict[str, Any]:
        """Generate API documentation"""
        return {
            "title": "Jarvis AI Assistant External API",
            "version": "1.0.0",
            "description": "External API for accessing Jarvis AI Assistant functionality",
            "base_url": "/api/external",
            "authentication": {
                "type": "Bearer Token",
                "header": "Authorization: Bearer <api_key>",
                "description": "API key required for all endpoints"
            },
            "endpoints": {
                "/chat": {
                    "method": "POST",
                    "permission": "chat",
                    "description": "Send chat message to Jarvis",
                    "parameters": {
                        "prompt": "string (required) - Chat message",
                        "mode": "string (optional) - Operating mode",
                        "session_id": "string (optional) - Session identifier",
                        "user_id": "string (optional) - User identifier"
                    },
                    "example": {
                        "prompt": "What's the weather like today?",
                        "mode": "default",
                        "session_id": "external_session_1"
                    }
                },
                "/execute": {
                    "method": "POST",
                    "permission": "execute",
                    "description": "Execute tool, workflow, or plugin",
                    "parameters": {
                        "type": "string (required) - 'tool', 'workflow', or 'plugin'",
                        "name": "string (required) - Name of action to execute",
                        "parameters": "object (optional) - Parameters for execution"
                    },
                    "example": {
                        "type": "tool",
                        "name": "weather_lookup",
                        "parameters": {"location": "New York"}
                    }
                },
                "/status": {
                    "method": "GET",
                    "permission": "status",
                    "description": "Get system status and available features",
                    "parameters": {},
                    "example": {}
                },
                "/upload": {
                    "method": "POST",
                    "permission": "upload",
                    "description": "Upload file for analysis",
                    "parameters": {
                        "file": "file (required) - File to upload",
                        "analysis_type": "string (optional) - Type of analysis",
                        "include_insights": "boolean (optional) - Include AI insights"
                    },
                    "example": "multipart/form-data with file field"
                },
                "/mode": {
                    "method": "GET/POST",
                    "permission": "mode",
                    "description": "Get or set operating mode",
                    "parameters": {
                        "mode": "string (POST only) - New mode to set"
                    },
                    "example": {
                        "mode": "ceo"
                    }
                }
            },
            "rate_limits": {
                "default": "100 requests/minute, 1000 requests/hour",
                "admin": "1000 requests/minute, 10000 requests/hour"
            },
            "error_codes": {
                "400": "Bad Request - Invalid parameters",
                "401": "Unauthorized - Invalid or missing API key",
                "403": "Forbidden - Insufficient permissions",
                "429": "Too Many Requests - Rate limit exceeded",
                "500": "Internal Server Error - Server error"
            }
        }

# Global instance
external_api = ExternalAPI()

