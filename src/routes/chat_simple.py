import os
import json
import requests
from flask import Blueprint, request, jsonify, Response
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

chat_bp = Blueprint('chat', __name__)

# In-memory conversation storage (for demo purposes)
conversations = {}

@chat_bp.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        messages = data.get('messages', [])
        conversation_id = data.get('conversation_id', 'default')
        
        # Get API key from request or environment
        api_key = data.get('apiKey') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            return jsonify({"error": "OpenAI API key is required"}), 400
            
        # Validate API key format
        if not api_key.startswith('sk-'):
            return jsonify({"error": "Invalid OpenAI API key format"}), 400
        
        # Get system prompt from request or environment
        system_prompt = data.get('systemPrompt') or os.getenv('DEFAULT_SYSTEM_PROMPT', 
                                 'You are Jarvis, Garret\'s AI assistant. You are helpful, knowledgeable, and ready to assist with any questions or tasks.')
        
        # Prepare messages with system prompt
        full_messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if memory is enabled
        if os.getenv('SESSION_MEMORY_ENABLED', 'true').lower() == 'true':
            if conversation_id in conversations:
                full_messages.extend(conversations[conversation_id])
        
        # Add current messages
        full_messages.extend(messages)
        
        # Get model from request or use GPT-4o as default
        model = data.get('model') or 'gpt-4o'
        
        # Validate model is a real OpenAI model
        valid_models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo']
        if model not in valid_models:
            model = 'gpt-4o'  # Default to GPT-4o if invalid model is provided
        
        # Make request to OpenAI API using requests
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model,
            'messages': full_messages,
            'stream': False
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            error_detail = "Unknown error"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_detail = error_data['error'].get('message', 'Unknown error')
            except:
                error_detail = response.text
            
            return jsonify({
                "error": f"OpenAI API error: {error_detail}",
                "status_code": response.status_code
            }), response.status_code
        
        response_data = response.json()
        assistant_message = response_data['choices'][0]['message']['content']
        
        # Store conversation if memory is enabled
        if os.getenv('SESSION_MEMORY_ENABLED', 'true').lower() == 'true':
            if conversation_id not in conversations:
                conversations[conversation_id] = []
            conversations[conversation_id].extend(messages)
            conversations[conversation_id].append({
                "role": "assistant", 
                "content": assistant_message
            })
        
        return jsonify({
            "message": assistant_message,
            "conversation_id": conversation_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get conversation history"""
    if conversation_id in conversations:
        return jsonify({
            "conversation_id": conversation_id,
            "messages": conversations[conversation_id]
        })
    else:
        return jsonify({
            "conversation_id": conversation_id,
            "messages": []
        })

@chat_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
def clear_conversation(conversation_id):
    """Clear conversation history"""
    if conversation_id in conversations:
        del conversations[conversation_id]
    return jsonify({"message": "Conversation cleared"})

@chat_bp.route('/conversations', methods=['GET'])
def list_conversations():
    """List all conversation IDs"""
    return jsonify({
        "conversations": list(conversations.keys())
    })

@chat_bp.route('/system-prompt', methods=['GET'])
def get_system_prompt():
    """Get current system prompt"""
    return jsonify({
        "system_prompt": os.getenv('DEFAULT_SYSTEM_PROMPT', 
                                  'You are Jarvis, Garret\'s AI assistant. You are helpful, knowledgeable, and ready to assist with any questions or tasks.')
    })

@chat_bp.route('/system-prompt', methods=['POST'])
def update_system_prompt():
    """Update system prompt (runtime only, not persistent)"""
    data = request.json
    new_prompt = data.get('system_prompt', '')
    
    # Note: This only updates the runtime environment variable
    # For persistent changes, the .env file would need to be updated
    os.environ['DEFAULT_SYSTEM_PROMPT'] = new_prompt
    
    return jsonify({
        "message": "System prompt updated",
        "system_prompt": new_prompt
    })



@chat_bp.route('/models', methods=['GET'])
def get_available_models():
    """Get list of available OpenAI models"""
    return jsonify({
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o", "description": "Most advanced GPT-4 model"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "description": "Faster, cost-effective GPT-4 model"},
            {"id": "gpt-4", "name": "GPT-4", "description": "Original GPT-4 model"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "description": "Enhanced GPT-4 with larger context"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "description": "Fast and efficient model"}
        ]
    })

@chat_bp.route('/test-api', methods=['POST'])
def test_api_key():
    """Test if API key is valid"""
    try:
        data = request.json
        api_key = data.get('apiKey') or os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            return jsonify({"valid": False, "error": "No API key provided"}), 400
            
        if not api_key.startswith('sk-'):
            return jsonify({"valid": False, "error": "Invalid API key format"}), 400
        
        # Test with a simple request
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'gpt-4o',
            'messages': [{"role": "user", "content": "Test"}],
            'max_tokens': 5
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({"valid": True, "message": "API key is valid"})
        else:
            error_detail = "Unknown error"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_detail = error_data['error'].get('message', 'Unknown error')
            except:
                error_detail = response.text
            
            return jsonify({
                "valid": False, 
                "error": error_detail,
                "status_code": response.status_code
            }), 400
        
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 500

