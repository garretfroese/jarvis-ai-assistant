"""
Enhanced Jarvis AI Assistant with OpenAI Integration and Advanced Features
"""

import os
import json
import uuid
from datetime import datetime
from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# OpenAI configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_API_BASE = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com/v1')

# In-memory conversation storage (for demo purposes)
conversations = {}
current_mode = "default"

@app.route('/')
def home():
    return jsonify({
        "message": "Jarvis AI Assistant is running!",
        "status": "healthy",
        "version": "3.0.0",
        "features": ["chat", "streaming", "conversations", "modes", "diagnostics"]
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "jarvis-ai-assistant",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/chat', methods=['POST'])
@app.route('/api/chat', methods=['POST'])
def chat():
    """Enhanced chat endpoint with conversation management"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        conversation_id = data.get('conversation_id', 'default')
        stream = data.get('stream', False)
        
        if not message:
            return jsonify({
                "error": "Message is required",
                "status": "error"
            }), 400
        
        # Initialize conversation if not exists
        if conversation_id not in conversations:
            conversations[conversation_id] = {
                "id": conversation_id,
                "created_at": datetime.now().isoformat(),
                "messages": [],
                "mode": current_mode
            }
        
        # Check for mode switching commands
        global current_mode
        if message.startswith('!'):
            mode_command = message.split()[0][1:].lower()
            if mode_command in ['ceo', 'wags', 'legal', 'default']:
                current_mode = mode_command
                conversations[conversation_id]["mode"] = current_mode
                return jsonify({
                    "response": f"Mode switched to: {current_mode.upper()}",
                    "conversation_id": conversation_id,
                    "mode": current_mode,
                    "status": "success"
                })
        
        # Add user message to conversation
        conversations[conversation_id]["messages"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        if stream:
            return Response(
                stream_with_context(generate_streaming_response(conversation_id)),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*'
                }
            )
        else:
            response = generate_response(conversation_id)
            return jsonify({
                "response": response,
                "conversation_id": conversation_id,
                "mode": current_mode,
                "status": "success"
            })
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

def get_system_message(mode):
    """Get system message based on current mode"""
    mode_prompts = {
        "default": "You are Jarvis, an intelligent AI assistant. Be helpful, concise, and friendly.",
        "ceo": "You are Jarvis in CEO mode. Provide strategic, executive-level insights with a focus on business leadership, decision-making, and high-level planning.",
        "wags": "You are Jarvis in WAGS mode. Be sophisticated, elegant, and provide advice on lifestyle, relationships, and social situations with grace and wisdom.",
        "legal": "You are Jarvis in Legal mode. Provide careful, precise legal-style analysis and advice. Always remind users to consult with qualified legal professionals for actual legal matters."
    }
    return mode_prompts.get(mode, mode_prompts["default"])

def generate_response(conversation_id):
    """Generate a non-streaming response"""
    try:
        if not OPENAI_API_KEY:
            # Fallback response if no OpenAI key
            return "I'm a demo version of Jarvis. Please configure OpenAI API key for full functionality."
        
        conversation = conversations[conversation_id]
        messages = conversation["messages"]
        mode = conversation.get("mode", "default")
        
        # Add system message based on mode
        system_message = {
            "role": "system",
            "content": get_system_message(mode)
        }
        
        # Format messages for OpenAI
        openai_messages = [system_message] + [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in messages
        ]
        
        response = requests.post(
            f"{OPENAI_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": openai_messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            assistant_message = result['choices'][0]['message']['content']
            
            # Add assistant response to conversation
            conversations[conversation_id]["messages"].append({
                "role": "assistant",
                "content": assistant_message,
                "timestamp": datetime.now().isoformat()
            })
            
            return assistant_message
        else:
            return f"Error from OpenAI API: {response.status_code}"
            
    except Exception as e:
        return f"Error generating response: {str(e)}"

def generate_streaming_response(conversation_id):
    """Generate a streaming response"""
    try:
        if not OPENAI_API_KEY:
            # Fallback streaming response
            demo_response = "I'm a demo version of Jarvis. Please configure OpenAI API key for full functionality."
            for char in demo_response:
                yield f"data: {json.dumps({'content': char})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            return
        
        conversation = conversations[conversation_id]
        messages = conversation["messages"]
        mode = conversation.get("mode", "default")
        
        # Add system message based on mode
        system_message = {
            "role": "system",
            "content": get_system_message(mode)
        }
        
        # Format messages for OpenAI
        openai_messages = [system_message] + [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in messages
        ]
        
        response = requests.post(
            f"{OPENAI_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": openai_messages,
                "max_tokens": 1000,
                "temperature": 0.7,
                "stream": True
            },
            stream=True
        )
        
        full_response = ""
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                content = delta['content']
                                full_response += content
                                yield f"data: {json.dumps({'content': content})}\n\n"
                    except json.JSONDecodeError:
                        continue
        
        # Add complete response to conversation
        conversations[conversation_id]["messages"].append({
            "role": "assistant",
            "content": full_response,
            "timestamp": datetime.now().isoformat()
        })
        
        yield f"data: {json.dumps({'done': True})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get list of conversations"""
    conversation_list = []
    for conv_id, conv_data in conversations.items():
        conversation_list.append({
            "id": conv_id,
            "created_at": conv_data.get("created_at"),
            "mode": conv_data.get("mode", "default"),
            "message_count": len(conv_data.get("messages", []))
        })
    
    return jsonify({
        "conversations": conversation_list,
        "status": "success"
    })

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get specific conversation"""
    if conversation_id in conversations:
        return jsonify({
            "conversation": conversations[conversation_id],
            "status": "success"
        })
    else:
        return jsonify({
            "error": "Conversation not found",
            "status": "error"
        }), 404

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete specific conversation"""
    if conversation_id in conversations:
        del conversations[conversation_id]
        return jsonify({
            "message": f"Conversation {conversation_id} deleted",
            "status": "success"
        })
    else:
        return jsonify({
            "error": "Conversation not found",
            "status": "error"
        }), 404

@app.route('/api/conversations/clear', methods=['POST'])
def clear_conversations():
    """Clear all conversations"""
    global conversations
    conversations = {}
    return jsonify({
        "message": "All conversations cleared",
        "status": "success"
    })

@app.route('/api/mode', methods=['GET'])
def get_mode():
    """Get current mode"""
    return jsonify({
        "mode": current_mode,
        "status": "success"
    })

@app.route('/api/mode', methods=['POST'])
def set_mode():
    """Set current mode"""
    global current_mode
    data = request.get_json()
    mode = data.get('mode', 'default')
    
    if mode in ['default', 'ceo', 'wags', 'legal']:
        current_mode = mode
        return jsonify({
            "mode": current_mode,
            "message": f"Mode set to {current_mode}",
            "status": "success"
        })
    else:
        return jsonify({
            "error": "Invalid mode. Available modes: default, ceo, wags, legal",
            "status": "error"
        }), 400

@app.route('/diagnose', methods=['GET'])
@app.route('/api/diagnose', methods=['GET'])
def diagnose():
    """System health and diagnostic information"""
    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "components": {
            "openai": {
                "status": "✅" if OPENAI_API_KEY else "❌",
                "configured": bool(OPENAI_API_KEY)
            },
            "conversations": {
                "status": "✅",
                "count": len(conversations),
                "active_mode": current_mode
            },
            "memory": {
                "status": "✅",
                "conversations_stored": len(conversations)
            },
            "api": {
                "status": "✅",
                "endpoints": ["chat", "conversations", "mode", "diagnose"]
            }
        },
        "version": "3.0.0",
        "features": ["streaming", "modes", "conversation_management", "diagnostics"]
    }
    
    return jsonify(diagnostics)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

