"""
Logging Decorator for Jarvis
Provides decorators to automatically log command executions
"""

import time
import functools
from typing import Any, Callable
from flask import request, g
from ..services.logging_service import logging_service

def log_execution(tool_name: str = None, 
                 extract_command: Callable = None,
                 extract_user_id: Callable = None,
                 extract_session_id: Callable = None):
    """
    Decorator to automatically log command executions
    
    Args:
        tool_name: Name of the tool being executed
        extract_command: Function to extract command from request/args
        extract_user_id: Function to extract user ID from request
        extract_session_id: Function to extract session ID from request
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Extract information for logging
            command = None
            user_id = None
            session_id = None
            
            try:
                # Extract command
                if extract_command:
                    command = extract_command(request, *args, **kwargs)
                elif hasattr(request, 'json') and request.json:
                    command = request.json.get('message') or request.json.get('command') or str(request.json)
                elif hasattr(request, 'args'):
                    command = request.args.get('q') or request.args.get('query') or str(dict(request.args))
                else:
                    command = f"{func.__name__}({args}, {kwargs})"
                
                # Extract user ID
                if extract_user_id:
                    user_id = extract_user_id(request, *args, **kwargs)
                elif hasattr(request, 'json') and request.json:
                    user_id = request.json.get('user_id') or request.json.get('userId')
                elif hasattr(request, 'headers'):
                    user_id = request.headers.get('X-User-ID')
                
                # Extract session ID
                if extract_session_id:
                    session_id = extract_session_id(request, *args, **kwargs)
                elif hasattr(request, 'json') and request.json:
                    session_id = request.json.get('session_id') or request.json.get('sessionId')
                elif hasattr(request, 'headers'):
                    session_id = request.headers.get('X-Session-ID')
                
            except Exception as e:
                print(f"Error extracting logging information: {e}")
                command = f"{func.__name__} execution"
            
            # Execute the function
            try:
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Extract output and status from result
                output = None
                status = 'success'
                error_message = None
                
                if isinstance(result, tuple) and len(result) == 2:
                    # Flask response tuple (response, status_code)
                    response_data, status_code = result
                    if status_code >= 400:
                        status = 'error'
                        if hasattr(response_data, 'get_json'):
                            json_data = response_data.get_json()
                            error_message = json_data.get('message') if json_data else None
                    else:
                        if hasattr(response_data, 'get_json'):
                            json_data = response_data.get_json()
                            output = str(json_data) if json_data else None
                elif hasattr(result, 'status_code'):
                    # Flask Response object
                    if result.status_code >= 400:
                        status = 'error'
                        try:
                            json_data = result.get_json()
                            error_message = json_data.get('message') if json_data else None
                        except:
                            error_message = "Unknown error"
                    else:
                        try:
                            json_data = result.get_json()
                            output = str(json_data) if json_data else None
                        except:
                            output = str(result.data) if hasattr(result, 'data') else None
                else:
                    # Regular return value
                    output = str(result) if result is not None else None
                
                # Log the execution
                logging_service.log_command_execution(
                    command=command,
                    tool_name=tool_name or func.__name__,
                    status=status,
                    output=output,
                    error_message=error_message,
                    duration_ms=duration_ms,
                    user_id=user_id,
                    session_id=session_id
                )
                
                return result
                
            except Exception as e:
                # Calculate duration for failed execution
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log the error
                logging_service.log_command_execution(
                    command=command,
                    tool_name=tool_name or func.__name__,
                    status='error',
                    output=None,
                    error_message=str(e),
                    duration_ms=duration_ms,
                    user_id=user_id,
                    session_id=session_id
                )
                
                # Re-raise the exception
                raise e
        
        return wrapper
    return decorator

def log_chat_execution(func):
    """Specialized decorator for chat endpoints"""
    return log_execution(
        tool_name='chat',
        extract_command=lambda req, *args, **kwargs: req.json.get('message') if req.json else None,
        extract_user_id=lambda req, *args, **kwargs: req.json.get('user_id') if req.json else None,
        extract_session_id=lambda req, *args, **kwargs: req.json.get('session_id') if req.json else None
    )(func)

def log_tool_execution_decorator(tool_name: str):
    """Specialized decorator for tool endpoints"""
    return log_execution(
        tool_name=tool_name,
        extract_command=lambda req, *args, **kwargs: req.json.get('command') or req.json.get('input') if req.json else None,
        extract_user_id=lambda req, *args, **kwargs: req.json.get('user_id') if req.json else None,
        extract_session_id=lambda req, *args, **kwargs: req.json.get('session_id') if req.json else None
    )

def log_file_operation(func):
    """Specialized decorator for file operations"""
    return log_execution(
        tool_name='file_processing',
        extract_command=lambda req, *args, **kwargs: f"File upload: {req.files.get('file').filename if req.files and 'file' in req.files else 'unknown'}",
        extract_user_id=lambda req, *args, **kwargs: req.form.get('user_id') or (req.json.get('user_id') if req.json else None),
        extract_session_id=lambda req, *args, **kwargs: req.form.get('session_id') or (req.json.get('session_id') if req.json else None)
    )(func)

def log_mode_operation(func):
    """Specialized decorator for mode operations"""
    return log_execution(
        tool_name='mode_management',
        extract_command=lambda req, *args, **kwargs: f"Mode operation: {req.json.get('mode') if req.json else kwargs.get('mode_name', 'unknown')}",
        extract_user_id=lambda req, *args, **kwargs: req.json.get('user_id') if req.json else None,
        extract_session_id=lambda req, *args, **kwargs: kwargs.get('session_id') or (req.json.get('session_id') if req.json else None)
    )(func)

class LoggingContext:
    """Context manager for manual logging"""
    
    def __init__(self, command: str, tool_name: str = None, user_id: str = None, session_id: str = None):
        self.command = command
        self.tool_name = tool_name
        self.user_id = user_id
        self.session_id = session_id
        self.start_time = None
        self.log_id = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.time() - self.start_time) * 1000)
        
        if exc_type is None:
            # Success
            self.log_id = logging_service.log_command_execution(
                command=self.command,
                tool_name=self.tool_name,
                status='success',
                duration_ms=duration_ms,
                user_id=self.user_id,
                session_id=self.session_id
            )
        else:
            # Error
            self.log_id = logging_service.log_command_execution(
                command=self.command,
                tool_name=self.tool_name,
                status='error',
                error_message=str(exc_val),
                duration_ms=duration_ms,
                user_id=self.user_id,
                session_id=self.session_id
            )
    
    def update_output(self, output: str):
        """Update the log entry with output after successful execution"""
        if self.log_id:
            # Note: This would require an update method in logging_service
            pass

def manual_log(command: str, tool_name: str = None, **kwargs):
    """Manual logging function for custom scenarios"""
    return logging_service.log_command_execution(
        command=command,
        tool_name=tool_name,
        **kwargs
    )

