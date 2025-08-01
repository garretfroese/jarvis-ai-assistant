"""
Enhanced Jarvis AI Assistant with OpenAI Integration
"""

import os
import json
import uuid
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

@app.route('/')
def home():
    return jsonify({
        "message": "Jarvis AI Assistant is running!",
        "status": "healthy",
        "version": "2.0.0"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "jarvis-ai-assistant"
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        stream = data.get('stream', False)
        
        if not message:
            return jsonify({
                "error": "Message is required",
                "status": "error"
            }), 400
        
        # Initialize conversation if not exists
        if conversation_id not in conversations:
            conversations[conversation_id] = []
        
        # Add user message to conversation
        conversations[conversation_id].append({
            "role": "user",
            "content": message
        })
        
        if stream:
            return Response(
                stream_with_context(generate_streaming_response(conversation_id)),
                mimetype='text/plain'
            )
        else:
            response = generate_response(conversation_id)
            return jsonify({
                "response": response,
                "conversation_id": conversation_id,
                "status": "success"
            })
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

def generate_response(conversation_id):
    """Generate a non-streaming response"""
    try:
        if not OPENAI_API_KEY:
            # Fallback response if no OpenAI key
            return "I'm a demo version of Jarvis. Please configure OpenAI API key for full functionality."
        
        messages = conversations[conversation_id]
        
        # Add system message
        system_message = {
            "role": "system",
            "content": "You are Jarvis, an intelligent AI assistant. Be helpful, concise, and friendly."
        }
        
        response = requests.post(
            f"{OPENAI_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": [system_message] + messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            assistant_message = result['choices'][0]['message']['content']
            
            # Add assistant response to conversation
            conversations[conversation_id].append({
                "role": "assistant",
                "content": assistant_message
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
        
        messages = conversations[conversation_id]
        
        # Add system message
        system_message = {
            "role": "system",
            "content": "You are Jarvis, an intelligent AI assistant. Be helpful, concise, and friendly."
        }
        
        response = requests.post(
            f"{OPENAI_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": [system_message] + messages,
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
        conversations[conversation_id].append({
            "role": "assistant",
            "content": full_response
        })
        
        yield f"data: {json.dumps({'done': True})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get list of conversations"""
    return jsonify({
        "conversations": list(conversations.keys()),
        "status": "success"
    })

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get specific conversation"""
    if conversation_id in conversations:
        return jsonify({
            "conversation": conversations[conversation_id],
            "conversation_id": conversation_id,
            "status": "success"
        })
    else:
        return jsonify({
            "error": "Conversation not found",
            "status": "error"
        }), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

