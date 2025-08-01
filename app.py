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
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# File upload configuration
UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'csv', 'json'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variables
conversations = {}
uploaded_files = {}
current_mode = 'default'

# OpenAI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_mode_prompt(mode):
    """Get system prompt based on current mode"""
    prompts = {
        'default': "You are Jarvis, a helpful AI assistant.",
        'ceo': "You are Jarvis in CEO mode. Provide executive-level strategic advice and business insights.",
        'wags': "You are Jarvis in WAGS mode. Focus on workplace guidance and support.",
        'legal': "You are Jarvis in Legal mode. Provide legal analysis and compliance guidance."
    }
    return prompts.get(mode, prompts['default'])

@app.route('/')
def health_check():
    return jsonify({
        "message": "Jarvis AI Assistant is running!",
        "status": "healthy", 
        "version": "4.0.0"
    })

@app.route('/diagnose')
def diagnose():
    return jsonify({
        "status": "healthy",
        "version": "4.0.0",
        "mode": current_mode,
        "conversations_count": len(conversations),
        "uploaded_files_count": len(uploaded_files),
        "openai_configured": bool(OPENAI_API_KEY)
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    global current_mode  # Global declaration at the top
    
    try:
        data = request.get_json()
        message = data.get('message', '')
        conversation_id = data.get('conversation_id', 'default')
        
        # Initialize conversation if it doesn't exist
        if conversation_id not in conversations:
            conversations[conversation_id] = {
                "id": conversation_id,
                "created_at": datetime.now().isoformat(),
                "messages": [],
                "mode": current_mode
            }
        
        # Check for mode switching commands
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
        user_message = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        conversations[conversation_id]["messages"].append(user_message)
        
        # Generate AI response
        if OPENAI_API_KEY:
            try:
                # Prepare messages for OpenAI
                openai_messages = [{"role": "system", "content": get_mode_prompt(current_mode)}]
                for msg in conversations[conversation_id]["messages"]:
                    openai_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                
                # Call OpenAI API
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
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    ai_response = response.json()["choices"][0]["message"]["content"]
                else:
                    ai_response = f"Sorry, I encountered an error: {response.status_code}"
                    
            except Exception as e:
                ai_response = f"Sorry, I'm having trouble connecting to my AI service: {str(e)}"
        else:
            ai_response = f"Hello! I'm Jarvis in {current_mode.upper()} mode. I'm currently running in demo mode. Please configure OpenAI API key for full functionality."
        
        # Add assistant message to conversation
        assistant_message = {
            "role": "assistant", 
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        }
        conversations[conversation_id]["messages"].append(assistant_message)
        
        return jsonify({
            "response": ai_response,
            "conversation_id": conversation_id,
            "mode": current_mode,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Chat error: {str(e)}",
            "status": "error"
        }), 500

# Conversation management endpoints
@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    return jsonify({
        "conversations": list(conversations.values()),
        "status": "success"
    })

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    if conversation_id in conversations:
        return jsonify({
            "conversation": conversations[conversation_id],
            "status": "success"
        })
    return jsonify({"error": "Conversation not found"}), 404

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    if conversation_id in conversations:
        del conversations[conversation_id]
        return jsonify({"status": "success", "message": "Conversation deleted"})
    return jsonify({"error": "Conversation not found"}), 404

@app.route('/api/conversations/clear', methods=['POST'])
def clear_conversations():
    conversations.clear()
    return jsonify({"status": "success", "message": "All conversations cleared"})

# Mode management endpoints
@app.route('/api/mode', methods=['GET'])
def get_mode():
    return jsonify({
        "mode": current_mode,
        "status": "success"
    })

@app.route('/api/mode', methods=['POST'])
def set_mode():
    global current_mode
    
    data = request.get_json()
    new_mode = data.get('mode', 'default')
    
    if new_mode in ['default', 'ceo', 'wags', 'legal']:
        current_mode = new_mode
        return jsonify({
            "mode": current_mode,
            "status": "success",
            "message": f"Mode set to {current_mode.upper()}"
        })
    
    return jsonify({
        "error": "Invalid mode",
        "status": "error"
    }), 400

# File upload endpoints
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        
        try:
            file.save(file_path)
            
            # Store file metadata
            uploaded_files[file_id] = {
                "id": file_id,
                "name": filename,
                "path": file_path,
                "size": os.path.getsize(file_path),
                "uploaded_at": datetime.now().isoformat()
            }
            
            return jsonify({
                "file_id": file_id,
                "filename": filename,
                "size": uploaded_files[file_id]["size"],
                "status": "success",
                "message": "File uploaded successfully"
            })
            
        except Exception as e:
            return jsonify({"error": f"Upload failed: {str(e)}"}), 500
    
    return jsonify({"error": "Invalid file type"}), 400

@app.route('/api/files', methods=['GET'])
def get_files():
    return jsonify({
        "files": list(uploaded_files.values()),
        "status": "success"
    })

@app.route('/api/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    if file_id in uploaded_files:
        try:
            # Delete physical file
            if os.path.exists(uploaded_files[file_id]["path"]):
                os.remove(uploaded_files[file_id]["path"])
            
            # Remove from metadata
            del uploaded_files[file_id]
            
            return jsonify({
                "status": "success",
                "message": "File deleted successfully"
            })
        except Exception as e:
            return jsonify({"error": f"Delete failed: {str(e)}"}), 500
    
    return jsonify({"error": "File not found"}), 404

@app.route('/api/files/<file_id>/analyze', methods=['POST'])
def analyze_file(file_id):
    if file_id not in uploaded_files:
        return jsonify({"error": "File not found"}), 404
    
    try:
        file_info = uploaded_files[file_id]
        file_path = file_info["path"]
        
        # Read file content (basic text analysis for now)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()[:2000]  # First 2000 characters
        
        # Generate analysis using AI if available
        if OPENAI_API_KEY:
            try:
                response = requests.post(
                    f"{OPENAI_API_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": "You are an AI assistant that analyzes files and provides insights."},
                            {"role": "user", "content": f"Please analyze this file content and provide insights:\n\nFilename: {file_info['name']}\nContent:\n{content}"}
                        ],
                        "max_tokens": 500,
                        "temperature": 0.7
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    analysis = response.json()["choices"][0]["message"]["content"]
                else:
                    analysis = f"Analysis failed with status {response.status_code}"
                    
            except Exception as e:
                analysis = f"Analysis error: {str(e)}"
        else:
            analysis = f"File analysis for {file_info['name']}:\n- Size: {file_info['size']} bytes\n- Content preview: {content[:200]}..."
        
        return jsonify({
            "analysis": analysis,
            "file_info": file_info,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

