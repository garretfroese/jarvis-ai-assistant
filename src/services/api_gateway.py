"""
API Gateway Service for Jarvis AI Assistant
Enables external systems to access Jarvis via secure API endpoints.
"""

import os
import json
import time
import uuid
import hashlib
import secrets
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

from .logging_service import logging_service, LogLevel, LogCategory

class APIKeyPermission:
    """API key permission constants"""
    CHAT = "chat"
    EXECUTE = "execute"
    UPLOAD = "upload"
    STATUS = "status"
    MODE = "mode"
    ADMIN = "admin"

class RateLimit:
    """Rate limiting configuration"""
    def __init__(self, requests_per_minute: int = 100, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

class APIKey:
    """API key data structure"""
    def __init__(self, key_id: str, key_hash: str, name: str, permissions: List[str], 
                 rate_limit: RateLimit, created_by: str, expires_at: Optional[datetime] = None,
                 ip_whitelist: Optional[List[str]] = None):
        self.key_id = key_id
        self.key_hash = key_hash
        self.name = name
        self.permissions = permissions
        self.rate_limit = rate_limit
        self.created_by = created_by
        self.created_at = datetime.now()
        self.expires_at = expires_at
        self.ip_whitelist = ip_whitelist or []
        self.last_used = None
        self.usage_count = 0
        self.is_active = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "key_id": self.key_id,
            "name": self.name,
            "permissions": self.permissions,
            "rate_limit": {
                "requests_per_minute": self.rate_limit.requests_per_minute,
                "requests_per_hour": self.rate_limit.requests_per_hour
            },
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "ip_whitelist": self.ip_whitelist,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count": self.usage_count,
            "is_active": self.is_active
        }

class APIGateway:
    """API Gateway for external access to Jarvis"""
    
    def __init__(self):
        self.enabled = os.getenv('API_GATEWAY_ENABLED', 'True').lower() == 'true'
        self.api_keys: Dict[str, APIKey] = {}
        self.rate_limit_cache: Dict[str, Dict[str, List[float]]] = {}
        self.api_keys_file = os.path.join(os.path.dirname(__file__), '../../state/api_keys.json')
        
        # Default rate limits
        self.default_rate_limit = RateLimit(
            requests_per_minute=int(os.getenv('API_DEFAULT_RPM', '100')),
            requests_per_hour=int(os.getenv('API_DEFAULT_RPH', '1000'))
        )
        
        # Load existing API keys
        self._load_api_keys()
        
        print("✅ API Gateway initialized")
    
    def _load_api_keys(self):
        """Load API keys from storage"""
        try:
            if os.path.exists(self.api_keys_file):
                with open(self.api_keys_file, 'r') as f:
                    data = json.load(f)
                
                for key_data in data.get('api_keys', []):
                    api_key = APIKey(
                        key_id=key_data['key_id'],
                        key_hash=key_data['key_hash'],
                        name=key_data['name'],
                        permissions=key_data['permissions'],
                        rate_limit=RateLimit(
                            key_data['rate_limit']['requests_per_minute'],
                            key_data['rate_limit']['requests_per_hour']
                        ),
                        created_by=key_data['created_by'],
                        expires_at=datetime.fromisoformat(key_data['expires_at']) if key_data.get('expires_at') else None,
                        ip_whitelist=key_data.get('ip_whitelist', [])
                    )
                    api_key.created_at = datetime.fromisoformat(key_data['created_at'])
                    api_key.last_used = datetime.fromisoformat(key_data['last_used']) if key_data.get('last_used') else None
                    api_key.usage_count = key_data.get('usage_count', 0)
                    api_key.is_active = key_data.get('is_active', True)
                    
                    self.api_keys[api_key.key_id] = api_key
                
                print(f"✅ Loaded {len(self.api_keys)} API keys")
            else:
                # Create default admin API key if none exist
                self._create_default_admin_key()
                
        except Exception as e:
            print(f"❌ Failed to load API keys: {e}")
            self._create_default_admin_key()
    
    def _save_api_keys(self):
        """Save API keys to storage"""
        try:
            os.makedirs(os.path.dirname(self.api_keys_file), exist_ok=True)
            
            data = {
                "api_keys": [
                    {
                        **api_key.to_dict(),
                        "key_hash": api_key.key_hash
                    }
                    for api_key in self.api_keys.values()
                ]
            }
            
            with open(self.api_keys_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✅ Saved {len(self.api_keys)} API keys")
            
        except Exception as e:
            print(f"❌ Failed to save API keys: {e}")
    
    def _create_default_admin_key(self):
        """Create default admin API key"""
        try:
            admin_key = self.create_api_key(
                name="Default Admin Key",
                permissions=[
                    APIKeyPermission.CHAT,
                    APIKeyPermission.EXECUTE,
                    APIKeyPermission.UPLOAD,
                    APIKeyPermission.STATUS,
                    APIKeyPermission.MODE,
                    APIKeyPermission.ADMIN
                ],
                created_by="system",
                rate_limit=RateLimit(1000, 10000)  # Higher limits for admin
            )
            
            print(f"✅ Created default admin API key: {admin_key['api_key']}")
            print("⚠️ Save this API key securely - it won't be shown again!")
            
        except Exception as e:
            print(f"❌ Failed to create default admin key: {e}")
    
    def create_api_key(self, name: str, permissions: List[str], created_by: str,
                      rate_limit: Optional[RateLimit] = None, expires_days: Optional[int] = None,
                      ip_whitelist: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new API key"""
        
        # Generate secure API key
        api_key = f"jarvis_{secrets.token_urlsafe(32)}"
        key_id = str(uuid.uuid4())
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Set expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        # Create API key object
        api_key_obj = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            permissions=permissions,
            rate_limit=rate_limit or self.default_rate_limit,
            created_by=created_by,
            expires_at=expires_at,
            ip_whitelist=ip_whitelist
        )
        
        # Store API key
        self.api_keys[key_id] = api_key_obj
        self._save_api_keys()
        
        # Log API key creation
        if logging_service:
            logging_service.log(
                LogLevel.INFO,
                LogCategory.AUTH,
                'api_key_created',
                user_id=created_by,
                details={
                    'key_id': key_id,
                    'name': name,
                    'permissions': permissions
                }
            )
        
        return {
            "api_key": api_key,  # Only returned once
            "key_id": key_id,
            "name": name,
            "permissions": permissions,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_at": api_key_obj.created_at.isoformat()
        }
    
    def validate_api_key(self, api_key: str, required_permission: str = None,
                        client_ip: str = None) -> Tuple[bool, Optional[APIKey], Optional[str]]:
        """Validate API key and check permissions"""
        
        if not api_key:
            return False, None, "API key required"
        
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Find matching API key
        api_key_obj = None
        for key_obj in self.api_keys.values():
            if key_obj.key_hash == key_hash:
                api_key_obj = key_obj
                break
        
        if not api_key_obj:
            return False, None, "Invalid API key"
        
        # Check if key is active
        if not api_key_obj.is_active:
            return False, None, "API key is disabled"
        
        # Check expiration
        if api_key_obj.expires_at and datetime.now() > api_key_obj.expires_at:
            return False, None, "API key has expired"
        
        # Check IP whitelist
        if api_key_obj.ip_whitelist and client_ip:
            if client_ip not in api_key_obj.ip_whitelist:
                return False, None, "IP address not whitelisted"
        
        # Check permissions
        if required_permission and required_permission not in api_key_obj.permissions:
            return False, None, f"Permission '{required_permission}' not granted"
        
        # Check rate limits
        if not self._check_rate_limit(api_key_obj, client_ip):
            return False, None, "Rate limit exceeded"
        
        # Update usage statistics
        api_key_obj.last_used = datetime.now()
        api_key_obj.usage_count += 1
        
        return True, api_key_obj, None
    
    def _check_rate_limit(self, api_key: APIKey, client_ip: str) -> bool:
        """Check if request is within rate limits"""
        
        now = time.time()
        cache_key = f"{api_key.key_id}:{client_ip}"
        
        if cache_key not in self.rate_limit_cache:
            self.rate_limit_cache[cache_key] = {
                'minute': [],
                'hour': []
            }
        
        cache = self.rate_limit_cache[cache_key]
        
        # Clean old entries
        minute_ago = now - 60
        hour_ago = now - 3600
        
        cache['minute'] = [t for t in cache['minute'] if t > minute_ago]
        cache['hour'] = [t for t in cache['hour'] if t > hour_ago]
        
        # Check limits
        if len(cache['minute']) >= api_key.rate_limit.requests_per_minute:
            return False
        
        if len(cache['hour']) >= api_key.rate_limit.requests_per_hour:
            return False
        
        # Add current request
        cache['minute'].append(now)
        cache['hour'].append(now)
        
        return True
    
    def revoke_api_key(self, key_id: str, revoked_by: str) -> bool:
        """Revoke an API key"""
        
        if key_id not in self.api_keys:
            return False
        
        api_key = self.api_keys[key_id]
        api_key.is_active = False
        
        self._save_api_keys()
        
        # Log API key revocation
        if logging_service:
            logging_service.log(
                LogLevel.INFO,
                LogCategory.AUTH,
                'api_key_revoked',
                user_id=revoked_by,
                details={
                    'key_id': key_id,
                    'name': api_key.name
                }
            )
        
        return True
    
    def list_api_keys(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """List all API keys (without the actual key values)"""
        
        keys = []
        for api_key in self.api_keys.values():
            if not include_inactive and not api_key.is_active:
                continue
            
            key_info = api_key.to_dict()
            # Remove sensitive information
            key_info.pop('key_hash', None)
            keys.append(key_info)
        
        return keys
    
    def get_api_key_stats(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get usage statistics for an API key"""
        
        if key_id not in self.api_keys:
            return None
        
        api_key = self.api_keys[key_id]
        
        return {
            "key_id": key_id,
            "name": api_key.name,
            "usage_count": api_key.usage_count,
            "last_used": api_key.last_used.isoformat() if api_key.last_used else None,
            "created_at": api_key.created_at.isoformat(),
            "is_active": api_key.is_active,
            "permissions": api_key.permissions
        }
    
    def log_api_request(self, api_key: APIKey, endpoint: str, client_ip: str, 
                       user_agent: str, success: bool, response_time_ms: int = None,
                       error_message: str = None):
        """Log API request for audit trail"""
        
        if logging_service:
            logging_service.log(
                LogLevel.INFO if success else LogLevel.ERROR,
                LogCategory.SYSTEM,
                'external_api_request',
                user_id=api_key.name,
                details={
                    'key_id': api_key.key_id,
                    'endpoint': endpoint,
                    'client_ip': client_ip,
                    'user_agent': user_agent,
                    'success': success,
                    'error_message': error_message
                },
                duration_ms=response_time_ms,
                success=success,
                error_message=error_message
            )
    
    def get_gateway_stats(self) -> Dict[str, Any]:
        """Get API gateway statistics"""
        
        active_keys = sum(1 for key in self.api_keys.values() if key.is_active)
        total_requests = sum(key.usage_count for key in self.api_keys.values())
        
        # Get recent usage (last 24 hours)
        recent_usage = 0
        day_ago = datetime.now() - timedelta(days=1)
        
        for key in self.api_keys.values():
            if key.last_used and key.last_used > day_ago:
                recent_usage += 1
        
        return {
            "enabled": self.enabled,
            "total_api_keys": len(self.api_keys),
            "active_api_keys": active_keys,
            "total_requests": total_requests,
            "recent_usage_24h": recent_usage,
            "default_rate_limit": {
                "requests_per_minute": self.default_rate_limit.requests_per_minute,
                "requests_per_hour": self.default_rate_limit.requests_per_hour
            }
        }

# Decorator for API key authentication
def require_api_key(permission: str = None):
    """Decorator to require API key authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not api_gateway.enabled:
                return jsonify({"error": "API Gateway is disabled"}), 503
            
            # Get API key from Authorization header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({"error": "Authorization header required (Bearer <api_key>)"}), 401
            
            api_key = auth_header[7:]  # Remove 'Bearer ' prefix
            client_ip = request.remote_addr
            
            # Validate API key
            valid, api_key_obj, error_msg = api_gateway.validate_api_key(
                api_key, permission, client_ip
            )
            
            if not valid:
                return jsonify({"error": error_msg}), 401
            
            # Add API key info to request context
            request.api_key = api_key_obj
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Global instance
api_gateway = APIGateway()

