from flask import Blueprint, request, jsonify
import json
import datetime
import os
from functools import wraps
from src.services.webhook_manager import webhook_manager

chatrelay_bp = Blueprint('chatrelay', __name__)

# In-memory storage for webhook messages (in production, use Redis or database)
webhook_messages = []

def require_auth(f):
    """Optional authentication decorator for webhook security"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if authentication is enabled
        webhook_token = os.getenv('WEBHOOK_AUTH_TOKEN')
        if webhook_token:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            
            token = auth_header.split(' ')[1]
            if token != webhook_token:
                return jsonify({"error": "Invalid authentication token"}), 401
        
        return f(*args, **kwargs)
    return decorated_function

@chatrelay_bp.route('/relay_message', methods=['POST'])
@require_auth
def relay_message():
    """
    Webhook endpoint to receive external messages and inject them into chat
    
    Expected payload:
    {
        "message": "string",      // The actual text Jarvis should say
        "author": "string"        // Optional, for tagging/logging
    }
    """
    try:
        # Check if webhook is enabled
        if not webhook_manager.is_webhook_enabled():
            return jsonify({"error": "Webhook functionality is disabled"}), 503
        
        # Check source IP if restrictions are configured
        if not webhook_manager.is_source_allowed(request.remote_addr):
            return jsonify({"error": "Source IP not allowed"}), 403
        
        # Parse JSON payload
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        
        # Validate message using webhook manager
        is_valid, validation_message = webhook_manager.validate_message(data)
        if not is_valid:
            return jsonify({"error": validation_message}), 400
        
        # Process message using webhook manager
        source_info = {
            "ip": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', 'Unknown')
        }
        
        webhook_message = webhook_manager.process_webhook_message(data, source_info)
        
        # Store the message
        webhook_messages.append(webhook_message)
        
        # Log the webhook call
        log_webhook_call(webhook_message)
        
        # Return success response
        return jsonify({
            "status": "ok",
            "message_id": webhook_message["id"],
            "timestamp": webhook_message["timestamp"]
        }), 200
        
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON payload"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@chatrelay_bp.route('/webhook_messages', methods=['GET'])
def get_webhook_messages():
    """Get all webhook messages for the frontend to consume"""
    try:
        # Optional: Add pagination
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get messages with pagination
        paginated_messages = webhook_messages[offset:offset + limit]
        
        return jsonify({
            "status": "ok",
            "messages": paginated_messages,
            "total": len(webhook_messages),
            "limit": limit,
            "offset": offset
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@chatrelay_bp.route('/webhook_messages/<message_id>', methods=['DELETE'])
@require_auth
def delete_webhook_message(message_id):
    """Delete a specific webhook message"""
    try:
        global webhook_messages
        
        # Find and remove the message
        webhook_messages = [msg for msg in webhook_messages if msg['id'] != message_id]
        
        return jsonify({
            "status": "ok",
            "message": f"Message {message_id} deleted"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@chatrelay_bp.route('/webhook_messages', methods=['DELETE'])
@require_auth
def clear_webhook_messages():
    """Clear all webhook messages"""
    try:
        global webhook_messages
        webhook_messages = []
        
        return jsonify({
            "status": "ok",
            "message": "All webhook messages cleared"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@chatrelay_bp.route('/webhook_status', methods=['GET'])
def webhook_status():
    """Get webhook system status and configuration"""
    try:
        webhook_token = os.getenv('WEBHOOK_AUTH_TOKEN')
        
        return jsonify({
            "status": "ok",
            "webhook_enabled": True,
            "authentication_enabled": bool(webhook_token),
            "total_messages": len(webhook_messages),
            "endpoint": "/api/relay_message",
            "methods": ["POST"],
            "last_message": webhook_messages[-1] if webhook_messages else None
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

def log_webhook_call(webhook_message):
    """Log webhook calls for auditing and debugging"""
    try:
        log_entry = {
            "timestamp": webhook_message["timestamp"],
            "message_id": webhook_message["id"],
            "author": webhook_message["author"],
            "message_length": len(webhook_message["message"]),
            "source_ip": webhook_message["source_ip"],
            "user_agent": webhook_message["user_agent"]
        }
        
        # In production, write to proper logging system
        print(f"[WEBHOOK] {json.dumps(log_entry)}")
        
        # Optional: Write to log file
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'webhook_calls.log')
        with open(log_file, 'a') as f:
            f.write(f"{json.dumps(log_entry)}\n")
            
    except Exception as e:
        print(f"[WEBHOOK ERROR] Failed to log webhook call: {str(e)}")

# Test endpoint for development
@chatrelay_bp.route('/test_webhook', methods=['POST'])
def test_webhook():
    """Test endpoint to verify webhook functionality"""
    try:
        test_message = {
            "message": "This is a test message from the webhook system!",
            "author": "Webhook Test"
        }
        
        # Simulate the webhook call
        response = relay_message.__wrapped__()  # Call without auth decorator
        
        return jsonify({
            "status": "ok",
            "message": "Webhook test completed",
            "test_payload": test_message
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Test failed: {str(e)}"}), 500


@chatrelay_bp.route('/webhook_config', methods=['GET'])
def get_webhook_config():
    """Get current webhook configuration"""
    try:
        config = webhook_manager.get_full_configuration()
        return jsonify({
            "status": "ok",
            "configuration": config
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get configuration: {str(e)}"}), 500

@chatrelay_bp.route('/webhook_config', methods=['PUT'])
@require_auth
def update_webhook_config():
    """Update webhook configuration"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        updates = request.get_json()
        if not updates:
            return jsonify({"error": "No configuration updates provided"}), 400
        
        success = webhook_manager.update_configuration(updates)
        if success:
            return jsonify({
                "status": "ok",
                "message": "Configuration updated successfully"
            }), 200
        else:
            return jsonify({"error": "Failed to update configuration"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Configuration update error: {str(e)}"}), 500

@chatrelay_bp.route('/webhook_config/reset', methods=['POST'])
@require_auth
def reset_webhook_config():
    """Reset webhook configuration to defaults"""
    try:
        success = webhook_manager.reset_to_defaults()
        if success:
            return jsonify({
                "status": "ok",
                "message": "Configuration reset to defaults"
            }), 200
        else:
            return jsonify({"error": "Failed to reset configuration"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Configuration reset error: {str(e)}"}), 500

@chatrelay_bp.route('/webhook_stats', methods=['GET'])
def get_webhook_stats():
    """Get webhook usage statistics"""
    try:
        stats = webhook_manager.get_webhook_statistics()
        return jsonify({
            "status": "ok",
            "statistics": stats
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get statistics: {str(e)}"}), 500

