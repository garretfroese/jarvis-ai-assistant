import os
import json
from flask import Blueprint, request, jsonify, Response, stream_template
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

chat_bp = Blueprint('chat', __name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# In-memory conversation storage (for demo purposes)
conversations = {}

@chat_bp.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        messages = data.get('messages', [])
        conversation_id = data.get('conversation_id', 'default')
        stream = data.get('stream', True)
        
        # Get API key from request or environment
        api_key = data.get('apiKey') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            return jsonify({"error": "OpenAI API key is required"}), 400
        
        # Initialize OpenAI client with the provided API key
        client_instance = OpenAI(api_key=api_key)
        
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
        
        # Get model from request or environment
        model = data.get('model') or os.getenv('MODEL', 'gpt-4')
        
        if stream:
            return Response(
                stream_chat_response(full_messages, model, conversation_id, client_instance),
                mimetype='text/plain'
            )
        else:
            # Non-streaming response
            response = client_instance.chat.completions.create(
                model=model,
                messages=full_messages,
                stream=False
            )
            
            assistant_message = response.choices[0].message.content
            
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

def stream_chat_response(messages, model, conversation_id, client_instance):
    """Generator function for streaming chat responses"""
    try:
        response = client_instance.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        
        full_response = ""
        
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                
                # Send chunk as JSON
                yield f"data: {json.dumps({'content': content, 'type': 'chunk'})}\n\n"
        
        # Store conversation if memory is enabled
        if os.getenv('SESSION_MEMORY_ENABLED', 'true').lower() == 'true':
            if conversation_id not in conversations:
                conversations[conversation_id] = []
            
            # Add user messages and assistant response
            user_messages = [msg for msg in messages if msg.get('role') == 'user']
            conversations[conversation_id].extend(user_messages)
            conversations[conversation_id].append({
                "role": "assistant", 
                "content": full_response
            })
        
        # Send completion signal
        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"

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

