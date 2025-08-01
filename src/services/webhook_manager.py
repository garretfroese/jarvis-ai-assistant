import json
import datetime
import os
from typing import List, Dict, Optional

class WebhookManager:
    """Service for managing webhook configurations and message processing"""
    
    def __init__(self):
        self.config_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'webhook_config.json')
        self.ensure_config_directory()
        self.load_configuration()
    
    def ensure_config_directory(self):
        """Ensure the config directory exists"""
        config_dir = os.path.dirname(self.config_file)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
    
    def load_configuration(self):
        """Load webhook configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = self.get_default_config()
                self.save_configuration()
        except Exception as e:
            print(f"Error loading webhook config: {e}")
            self.config = self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """Get default webhook configuration"""
        return {
            "enabled": True,
            "authentication_required": True,
            "rate_limit": {
                "enabled": True,
                "requests_per_minute": 60,
                "requests_per_hour": 1000
            },
            "allowed_sources": [],  # Empty means all sources allowed
            "message_retention": {
                "enabled": True,
                "max_messages": 1000,
                "retention_days": 30
            },
            "logging": {
                "enabled": True,
                "log_level": "INFO",
                "log_file": "webhook.log"
            },
            "notifications": {
                "enabled": False,
                "email": None,
                "slack_webhook": None
            },
            "created_at": datetime.datetime.utcnow().isoformat(),
            "updated_at": datetime.datetime.utcnow().isoformat()
        }
    
    def save_configuration(self):
        """Save current configuration to file"""
        try:
            self.config["updated_at"] = datetime.datetime.utcnow().isoformat()
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving webhook config: {e}")
    
    def update_configuration(self, updates: Dict) -> bool:
        """Update webhook configuration"""
        try:
            self.config.update(updates)
            self.save_configuration()
            return True
        except Exception as e:
            print(f"Error updating webhook config: {e}")
            return False
    
    def is_webhook_enabled(self) -> bool:
        """Check if webhook is enabled"""
        return self.config.get("enabled", True)
    
    def is_authentication_required(self) -> bool:
        """Check if authentication is required"""
        return self.config.get("authentication_required", True)
    
    def is_source_allowed(self, source_ip: str) -> bool:
        """Check if source IP is allowed"""
        allowed_sources = self.config.get("allowed_sources", [])
        if not allowed_sources:  # Empty list means all sources allowed
            return True
        return source_ip in allowed_sources
    
    def get_rate_limits(self) -> Dict:
        """Get rate limit configuration"""
        return self.config.get("rate_limit", {
            "enabled": True,
            "requests_per_minute": 60,
            "requests_per_hour": 1000
        })
    
    def get_message_retention_config(self) -> Dict:
        """Get message retention configuration"""
        return self.config.get("message_retention", {
            "enabled": True,
            "max_messages": 1000,
            "retention_days": 30
        })
    
    def get_logging_config(self) -> Dict:
        """Get logging configuration"""
        return self.config.get("logging", {
            "enabled": True,
            "log_level": "INFO",
            "log_file": "webhook.log"
        })
    
    def get_full_configuration(self) -> Dict:
        """Get complete webhook configuration"""
        return self.config.copy()
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        try:
            self.config = self.get_default_config()
            self.save_configuration()
            return True
        except Exception as e:
            print(f"Error resetting webhook config: {e}")
            return False
    
    def validate_message(self, message_data: Dict) -> tuple[bool, str]:
        """Validate incoming webhook message"""
        try:
            # Check required fields
            if 'message' not in message_data:
                return False, "Missing required field: message"
            
            message = message_data.get('message', '').strip()
            if not message:
                return False, "Message cannot be empty"
            
            # Check message length
            max_length = self.config.get('max_message_length', 10000)
            if len(message) > max_length:
                return False, f"Message too long (max {max_length} characters)"
            
            # Validate author field if present
            author = message_data.get('author', '')
            if author and len(author) > 100:
                return False, "Author name too long (max 100 characters)"
            
            return True, "Valid message"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def process_webhook_message(self, message_data: Dict, source_info: Dict) -> Dict:
        """Process and enrich webhook message"""
        try:
            # Validate message
            is_valid, validation_message = self.validate_message(message_data)
            if not is_valid:
                raise ValueError(validation_message)
            
            # Create processed message
            processed_message = {
                "id": f"webhook_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
                "message": message_data.get('message', '').strip(),
                "author": message_data.get('author', 'External System'),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "type": "webhook",
                "source_ip": source_info.get('ip', 'unknown'),
                "user_agent": source_info.get('user_agent', 'unknown'),
                "processed_at": datetime.datetime.utcnow().isoformat(),
                "status": "processed"
            }
            
            return processed_message
            
        except Exception as e:
            raise Exception(f"Message processing error: {str(e)}")
    
    def get_webhook_statistics(self) -> Dict:
        """Get webhook usage statistics"""
        try:
            # In a real implementation, this would query a database
            # For now, return basic stats
            return {
                "webhook_enabled": self.is_webhook_enabled(),
                "authentication_enabled": self.is_authentication_required(),
                "total_messages_processed": 0,  # Would be from database
                "messages_today": 0,  # Would be from database
                "last_message_time": None,  # Would be from database
                "error_rate": 0.0,  # Would be calculated from logs
                "average_response_time": 0.0,  # Would be from performance logs
                "configuration_last_updated": self.config.get("updated_at"),
                "uptime": "100%"  # Would be calculated from monitoring
            }
        except Exception as e:
            return {"error": f"Failed to get statistics: {str(e)}"}

# Global webhook manager instance
webhook_manager = WebhookManager()

