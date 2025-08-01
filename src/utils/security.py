import os
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

class SecurityManager:
    def __init__(self):
        self.rate_limits = {}  # IP -> {count, reset_time}
        self.failed_attempts = {}  # IP -> {count, last_attempt}
        self.max_requests_per_minute = 10
        self.max_failed_attempts = 5
        self.lockout_duration = 300  # 5 minutes
        
    def generate_secure_token(self, length=32):
        """Generate a cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def hash_token(self, token):
        """Hash a token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def verify_token(self, provided_token, stored_hash=None):
        """Verify a token against stored hash or environment variable"""
        if stored_hash:
            return self.hash_token(provided_token) == stored_hash
        
        # Fallback to environment variable
        expected_token = os.getenv('COMMAND_AUTH_TOKEN', 'jarvis-secure-token-2024')
        return provided_token == expected_token
    
    def check_rate_limit(self, client_ip):
        """Check if client is within rate limits"""
        current_time = time.time()
        
        if client_ip in self.rate_limits:
            rate_data = self.rate_limits[client_ip]
            
            # Reset counter if minute has passed
            if current_time > rate_data['reset_time']:
                rate_data['count'] = 0
                rate_data['reset_time'] = current_time + 60
            
            # Check if limit exceeded
            if rate_data['count'] >= self.max_requests_per_minute:
                return False, f"Rate limit exceeded. Try again in {int(rate_data['reset_time'] - current_time)} seconds."
            
            # Increment counter
            rate_data['count'] += 1
        else:
            # First request from this IP
            self.rate_limits[client_ip] = {
                'count': 1,
                'reset_time': current_time + 60
            }
        
        return True, None
    
    def check_failed_attempts(self, client_ip):
        """Check if client is locked out due to failed attempts"""
        current_time = time.time()
        
        if client_ip in self.failed_attempts:
            failed_data = self.failed_attempts[client_ip]
            
            # Check if lockout period has expired
            if current_time > failed_data['last_attempt'] + self.lockout_duration:
                # Reset failed attempts
                del self.failed_attempts[client_ip]
                return True, None
            
            # Check if max attempts exceeded
            if failed_data['count'] >= self.max_failed_attempts:
                remaining_time = int((failed_data['last_attempt'] + self.lockout_duration) - current_time)
                return False, f"Too many failed attempts. Try again in {remaining_time} seconds."
        
        return True, None
    
    def record_failed_attempt(self, client_ip):
        """Record a failed authentication attempt"""
        current_time = time.time()
        
        if client_ip in self.failed_attempts:
            self.failed_attempts[client_ip]['count'] += 1
            self.failed_attempts[client_ip]['last_attempt'] = current_time
        else:
            self.failed_attempts[client_ip] = {
                'count': 1,
                'last_attempt': current_time
            }
    
    def is_safe_command(self, command, parameters):
        """Check if a command is safe to execute"""
        # Blacklisted commands that could be dangerous
        dangerous_commands = [
            'rm', 'delete', 'format', 'shutdown', 'reboot',
            'sudo', 'su', 'chmod', 'chown', 'passwd'
        ]
        
        # Check if command contains dangerous keywords
        command_lower = command.lower()
        for dangerous in dangerous_commands:
            if dangerous in command_lower:
                return False, f"Command '{command}' contains potentially dangerous operation: {dangerous}"
        
        # Check parameters for dangerous content
        if isinstance(parameters, dict):
            for key, value in parameters.items():
                if isinstance(value, str):
                    value_lower = value.lower()
                    for dangerous in dangerous_commands:
                        if dangerous in value_lower:
                            return False, f"Parameter '{key}' contains potentially dangerous content: {dangerous}"
        
        return True, None
    
    def sanitize_input(self, input_string):
        """Sanitize input to prevent injection attacks"""
        if not isinstance(input_string, str):
            return input_string
        
        # Remove potentially dangerous characters
        dangerous_chars = [';', '|', '&', '$', '`', '(', ')', '{', '}', '[', ']']
        sanitized = input_string
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized.strip()

# Global security manager instance
security_manager = SecurityManager()

def require_auth(f):
    """Decorator to require authentication for command endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Check rate limiting
        rate_ok, rate_msg = security_manager.check_rate_limit(client_ip)
        if not rate_ok:
            return jsonify({
                "status": "error",
                "message": rate_msg
            }), 429
        
        # Check failed attempts lockout
        lockout_ok, lockout_msg = security_manager.check_failed_attempts(client_ip)
        if not lockout_ok:
            return jsonify({
                "status": "error",
                "message": lockout_msg
            }), 429
        
        # Verify authentication token
        auth_token = request.headers.get('X-Command-Auth') or request.args.get('auth_token')
        
        if not auth_token:
            security_manager.record_failed_attempt(client_ip)
            return jsonify({
                "status": "error",
                "message": "Authentication token required"
            }), 401
        
        if not security_manager.verify_token(auth_token):
            security_manager.record_failed_attempt(client_ip)
            return jsonify({
                "status": "error",
                "message": "Invalid authentication token"
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

def validate_command(f):
    """Decorator to validate command safety"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.json or {}
        command = data.get("command", "")
        parameters = data.get("parameters", {})
        
        # Check if command is safe
        safe, safety_msg = security_manager.is_safe_command(command, parameters)
        if not safe:
            return jsonify({
                "status": "error",
                "message": f"Command rejected for security reasons: {safety_msg}"
            }), 400
        
        # Sanitize parameters
        if isinstance(parameters, dict):
            sanitized_params = {}
            for key, value in parameters.items():
                if isinstance(value, str):
                    sanitized_params[key] = security_manager.sanitize_input(value)
                else:
                    sanitized_params[key] = value
            
            # Update request data with sanitized parameters
            data["parameters"] = sanitized_params
            request.json = data
        
        return f(*args, **kwargs)
    
    return decorated_function

def log_security_event(event_type, client_ip, details):
    """Log security-related events"""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] SECURITY {event_type}: IP={client_ip}, Details={details}\n"
    
    try:
        log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'security.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to log security event: {e}")

def get_security_stats():
    """Get current security statistics"""
    return {
        "rate_limits": len(security_manager.rate_limits),
        "failed_attempts": len(security_manager.failed_attempts),
        "max_requests_per_minute": security_manager.max_requests_per_minute,
        "lockout_duration": security_manager.lockout_duration
    }

def verify_auth_token(request):
    """Verify authentication token from request"""
    auth_token = request.headers.get('X-Command-Auth') or request.args.get('auth_token')
    
    if not auth_token:
        return False
    
    return security_manager.verify_token(auth_token)

def rate_limit_check(client_ip):
    """Check rate limit for client IP"""
    return security_manager.check_rate_limit(client_ip)

