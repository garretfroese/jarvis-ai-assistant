"""
Enhanced Jarvis AI Assistant with OpenAI Integration and Advanced Features
"""

import os
import sys
import json
import uuid
from datetime import datetime
from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
import requests
from werkzeug.utils import secure_filename

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import tool routing system
try:
    from src.services.tool_router import tool_router, route_and_execute
    TOOL_ROUTING_ENABLED = True
    print("✅ Tool routing system loaded successfully")
except ImportError as e:
    print(f"⚠️ Tool routing system not available: {e}")
    TOOL_ROUTING_ENABLED = False

# Import enhanced session manager
try:
    from src.services.session_manager import session_manager, get_session_context, switch_mode as session_switch_mode
    SESSION_MANAGER_ENABLED = True
    print("✅ Enhanced session manager loaded successfully")
except ImportError as e:
    print(f"⚠️ Enhanced session manager not available: {e}")
    SESSION_MANAGER_ENABLED = False

# Import advanced file processor
try:
    from src.services.advanced_file_processor import initialize_file_processor, get_file_processor
    ADVANCED_FILE_PROCESSING = True
    print("✅ Advanced file processor loaded successfully")
except ImportError as e:
    print(f"⚠️ Advanced file processor not available: {e}")
    ADVANCED_FILE_PROCESSING = False

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

# Initialize advanced file processor
if ADVANCED_FILE_PROCESSING:
    file_processor = initialize_file_processor(
        openai_api_key=OPENAI_API_KEY,
        openai_api_base=OPENAI_API_BASE
    )
    print("✅ Advanced file processor initialized")
else:
    file_processor = None

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
        "version": "7.0.0"
    })

@app.route('/diagnose')
def diagnose():
    # Get enhanced file statistics if available
    file_stats = {}
    if ADVANCED_FILE_PROCESSING and file_processor:
        try:
            file_stats = file_processor.get_file_statistics()
        except:
            file_stats = {"error": "Failed to get file statistics"}
    
    return jsonify({
        "status": "healthy",
        "version": "7.0.0",
        "mode": current_mode,
        "conversations_count": len(conversations),
        "uploaded_files_count": len(uploaded_files),
        "ai_enabled": OPENAI_API_KEY is not None,
        "tool_routing_enabled": TOOL_ROUTING_ENABLED,
        "session_manager_enabled": SESSION_MANAGER_ENABLED,
        "advanced_file_processing": ADVANCED_FILE_PROCESSING,
        "file_statistics": file_stats,
        "features": {
            "chat": True,
            "file_upload": True,
            "mode_switching": True,
            "tool_routing": TOOL_ROUTING_ENABLED,
            "enhanced_sessions": SESSION_MANAGER_ENABLED,
            "advanced_files": ADVANCED_FILE_PROCESSING
        }
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    global current_mode  # Global declaration at the top
    
    try:
        data = request.get_json()
        message = data.get('message', '')
        conversation_id = data.get('conversation_id', 'default')
        user_id = data.get('user_id', 'default')
        
        # Enhanced session management
        if SESSION_MANAGER_ENABLED:
            # Get or create session
            session = session_manager.get_session(conversation_id)
            if not session:
                conversation_id = session_manager.create_session(user_id, current_mode)
                session = session_manager.get_session(conversation_id)
            
            # Update current mode from session
            current_mode = session.get("mode", current_mode)
        else:
            # Fallback to old conversation management
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
                old_mode = current_mode
                current_mode = mode_command
                
                # Enhanced mode switching
                if SESSION_MANAGER_ENABLED:
                    session_switch_mode(conversation_id, current_mode)
                else:
                    conversations[conversation_id]["mode"] = current_mode
                
                return jsonify({
                    "response": f"🔄 Mode switched from {old_mode.upper()} to {current_mode.upper()}\n\nI'm now operating in {current_mode.upper()} mode with enhanced context awareness.",
                    "conversation_id": conversation_id,
                    "mode": current_mode,
                    "mode_switch": {
                        "from": old_mode,
                        "to": current_mode
                    },
                    "status": "success"
                })
        
        # Create user message with enhanced metadata
        user_message = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "session_id": conversation_id
        }
        
        # Add to enhanced session or fallback
        if SESSION_MANAGER_ENABLED:
            session_manager.add_message(conversation_id, user_message)
            # Get enhanced context for AI
            session_context = get_session_context(conversation_id)
        else:
            conversations[conversation_id]["messages"].append(user_message)
            session_context = {}
        conversations[conversation_id]["messages"].append(user_message)
        
        # Try tool routing first
        tool_result = None
        ai_response = None
        
        if TOOL_ROUTING_ENABLED:
            try:
                tool_result = route_and_execute(message, threshold=0.3)
                
                if tool_result.get('routed_to_tool') and tool_result.get('success'):
                    ai_response = f"🔧 **Tool Used:** {tool_result['tool_name']}\n\n{tool_result['output']}"
                    
                    # Add tool usage info to conversation
                    conversations[conversation_id]["messages"].append({
                        "role": "system",
                        "content": f"Used tool: {tool_result['tool_name']} (confidence: {tool_result['confidence']:.2f})",
                        "timestamp": datetime.now().isoformat(),
                        "tool_info": tool_result
                    })
                    
            except Exception as e:
                print(f"Tool routing error: {str(e)}")
        
        # Fallback to GPT-4o if no tool was used or tool failed
        if not ai_response:
            if OPENAI_API_KEY:
                try:
                    # Prepare enhanced system prompt with session context
                    system_prompt = get_mode_prompt(current_mode)
                    
                    if SESSION_MANAGER_ENABLED and session_context:
                        # Add context-aware information to system prompt
                        context_info = []
                        
                        if session_context.get("topics_discussed"):
                            context_info.append(f"Recent topics: {', '.join(session_context['topics_discussed'][-3:])}")
                        
                        if session_context.get("tools_used"):
                            recent_tools = [tool["tool"] for tool in session_context["tools_used"][-2:]]
                            context_info.append(f"Recently used tools: {', '.join(recent_tools)}")
                        
                        if session_context.get("preferences"):
                            context_info.append("User preferences available in session memory")
                        
                        if context_info:
                            system_prompt += f"\n\nSession Context: {' | '.join(context_info)}"
                    
                    # Prepare messages for OpenAI with enhanced context
                    openai_messages = [{"role": "system", "content": system_prompt}]
                    
                    # Get messages from enhanced session or fallback
                    if SESSION_MANAGER_ENABLED:
                        session = session_manager.get_session(conversation_id)
                        messages_to_send = session.get("messages", [])
                    else:
                        messages_to_send = conversations[conversation_id]["messages"]
                    
                    for msg in messages_to_send:
                        if msg["role"] != "system":  # Skip tool usage messages for OpenAI
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
                        
                        # Add fallback info if tool routing was attempted
                        if tool_result and not tool_result.get('success'):
                            ai_response = f"🤖 **AI Response** (tool routing failed):\n\n{ai_response}"
                    else:
                        ai_response = f"Sorry, I encountered an error: {response.status_code}"
                        
                except Exception as e:
                    ai_response = f"Sorry, I'm having trouble connecting to my AI service: {str(e)}"
            else:
                ai_response = f"Hello! I'm Jarvis in {current_mode.upper()} mode. I'm currently running in demo mode. Please configure OpenAI API key for full functionality."
        
        # Create enhanced assistant message
        assistant_message = {
            "role": "assistant", 
            "content": ai_response,
            "timestamp": datetime.now().isoformat(),
            "mode": current_mode,
            "session_id": conversation_id
        }
        
        # Add tool information if tool was used
        if tool_result and tool_result.get('routed_to_tool'):
            assistant_message["tool_info"] = tool_result
        
        # Add to enhanced session or fallback
        if SESSION_MANAGER_ENABLED:
            session_manager.add_message(conversation_id, assistant_message)
            # Get updated session statistics
            session_stats = session_manager.get_session_statistics()
        else:
            conversations[conversation_id]["messages"].append(assistant_message)
            session_stats = {}
        
        # Prepare enhanced response
        response_data = {
            "response": ai_response,
            "conversation_id": conversation_id,
            "mode": current_mode,
            "status": "success"
        }
        
        # Add enhanced session information
        if SESSION_MANAGER_ENABLED and session_context:
            response_data["session_info"] = {
                "topics_discussed": len(session_context.get("topics_discussed", [])),
                "tools_used_count": len(session_context.get("tools_used", [])),
                "session_mode": session_context.get("current_mode", current_mode),
                "has_preferences": bool(session_context.get("preferences")),
                "memory_items": len(session_context.get("relevant_long_term", []))
            }
        
        # Add tool routing information
        if tool_result:
            response_data["tool_info"] = {
                "routed_to_tool": tool_result.get("routed_to_tool", False),
                "tool_name": tool_result.get("tool_name"),
                "confidence": tool_result.get("confidence", 0),
                "success": tool_result.get("success", False)
            }
        
        return jsonify(response_data)
        
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

# Advanced File Upload Endpoints
@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Advanced file upload with intelligent processing"""
    if not ADVANCED_FILE_PROCESSING:
        return jsonify({"error": "Advanced file processing not available"}), 503
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    try:
        # Get additional parameters
        user_id = request.form.get('user_id', 'default')
        session_id = request.form.get('session_id', None)
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4()}_{filename}")
        file.save(temp_path)
        
        # Process with advanced file processor
        result = file_processor.upload_file(temp_path, filename, user_id, session_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@app.route('/api/files', methods=['GET'])
def get_files():
    """Get files with advanced filtering and search"""
    if not ADVANCED_FILE_PROCESSING:
        # Fallback to basic file list
        return jsonify({
            "files": list(uploaded_files.values()),
            "status": "success",
            "enhanced_features": False
        })
    
    try:
        user_id = request.args.get('user_id', 'default')
        session_id = request.args.get('session_id', None)
        search_query = request.args.get('search', None)
        
        if search_query:
            # Search files
            results = file_processor.search_files(search_query, user_id)
            files = [result["metadata"] for result in results]
        elif session_id:
            # Get session files
            files = file_processor.get_session_files(session_id)
        else:
            # Get all user files
            files = file_processor.get_user_files(user_id)
        
        return jsonify({
            "files": files,
            "total": len(files),
            "enhanced_features": True,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get files: {str(e)}"}), 500

@app.route('/api/files/<file_id>', methods=['GET'])
def get_file_details(file_id):
    """Get detailed file information"""
    if not ADVANCED_FILE_PROCESSING:
        # Fallback
        if file_id in uploaded_files:
            return jsonify({"file": uploaded_files[file_id], "status": "success"})
        else:
            return jsonify({"error": "File not found"}), 404
    
    try:
        metadata = file_processor.get_file_metadata(file_id)
        if metadata:
            return jsonify({
                "file": metadata,
                "enhanced_features": True,
                "status": "success"
            })
        else:
            return jsonify({"error": "File not found"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Failed to get file details: {str(e)}"}), 500

@app.route('/api/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Delete file with advanced cleanup"""
    if not ADVANCED_FILE_PROCESSING:
        # Fallback to basic deletion
        if file_id in uploaded_files:
            try:
                if os.path.exists(uploaded_files[file_id]["path"]):
                    os.remove(uploaded_files[file_id]["path"])
                del uploaded_files[file_id]
                return jsonify({"status": "success", "message": "File deleted successfully"})
            except Exception as e:
                return jsonify({"error": f"Delete failed: {str(e)}"}), 500
        else:
            return jsonify({"error": "File not found"}), 404
    
    try:
        success = file_processor.delete_file(file_id)
        if success:
            return jsonify({
                "status": "success",
                "message": "File deleted successfully"
            })
        else:
            return jsonify({"error": "File not found"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Delete failed: {str(e)}"}), 500

@app.route('/api/files/<file_id>/analyze', methods=['POST'])
def analyze_file(file_id):
    """Analyze file with AI insights"""
    if not ADVANCED_FILE_PROCESSING:
        # Fallback to basic analysis
        if file_id not in uploaded_files:
            return jsonify({"error": "File not found"}), 404
        
        try:
            file_info = uploaded_files[file_id]
            file_path = file_info["path"]
            
            # Basic text analysis
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()[:2000]
            
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
                analysis = "AI analysis not available - OpenAI API key not configured"
            
            return jsonify({
                "file_id": file_id,
                "analysis": analysis,
                "enhanced_features": False,
                "status": "success"
            })
            
        except Exception as e:
            return jsonify({"error": f"Analysis failed: {str(e)}"}), 500
    
    try:
        metadata = file_processor.get_file_metadata(file_id)
        if not metadata:
            return jsonify({"error": "File not found"}), 404
        
        # Check if already analyzed
        if metadata.get("ai_analyzed"):
            return jsonify({
                "file_id": file_id,
                "analysis": metadata.get("summary", ""),
                "insights": metadata.get("insights", []),
                "actions": metadata.get("actions", []),
                "tags": metadata.get("tags", []),
                "enhanced_features": True,
                "status": "success",
                "cached": True
            })
        
        # Trigger analysis if not done
        success = file_processor.process_file(file_id)
        if success:
            updated_metadata = file_processor.get_file_metadata(file_id)
            return jsonify({
                "file_id": file_id,
                "analysis": updated_metadata.get("summary", ""),
                "insights": updated_metadata.get("insights", []),
                "actions": updated_metadata.get("actions", []),
                "tags": updated_metadata.get("tags", []),
                "enhanced_features": True,
                "status": "success",
                "cached": False
            })
        else:
            return jsonify({"error": "Analysis failed"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

@app.route('/api/files/search', methods=['POST'])
def search_files():
    """Search files by content, tags, or metadata"""
    if not ADVANCED_FILE_PROCESSING:
        return jsonify({"error": "Advanced search not available"}), 503
    
    try:
        data = request.get_json()
        query = data.get('query', '')
        user_id = data.get('user_id', 'default')
        
        if not query:
            return jsonify({"error": "Search query is required"}), 400
        
        results = file_processor.search_files(query, user_id)
        
        return jsonify({
            "results": results,
            "total": len(results),
            "query": query,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500

@app.route('/api/files/statistics', methods=['GET'])
def get_file_statistics():
    """Get file processing statistics"""
    if not ADVANCED_FILE_PROCESSING:
        # Basic statistics
        total_files = len(uploaded_files)
        return jsonify({
            "statistics": {
                "total_files": total_files,
                "enhanced_features": False
            },
            "status": "success"
        })
    
    try:
        stats = file_processor.get_file_statistics()
        return jsonify({
            "statistics": stats,
            "enhanced_features": True,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get statistics: {str(e)}"}), 500

@app.route('/api/files/batch-upload', methods=['POST'])
def batch_upload_files():
    """Upload multiple files at once"""
    if not ADVANCED_FILE_PROCESSING:
        return jsonify({"error": "Batch upload not available"}), 503
    
    try:
        files = request.files.getlist('files')
        user_id = request.form.get('user_id', 'default')
        session_id = request.form.get('session_id', None)
        
        if not files:
            return jsonify({"error": "No files provided"}), 400
        
        results = []
        for file in files:
            if file.filename != '':
                try:
                    filename = secure_filename(file.filename)
                    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4()}_{filename}")
                    file.save(temp_path)
                    
                    result = file_processor.upload_file(temp_path, filename, user_id, session_id)
                    results.append(result)
                    
                except Exception as e:
                    results.append({
                        "filename": file.filename,
                        "status": "error",
                        "message": f"Upload failed: {str(e)}"
                    })
        
        successful_uploads = len([r for r in results if r.get("status") == "uploaded"])
        
        return jsonify({
            "results": results,
            "total_files": len(files),
            "successful_uploads": successful_uploads,
            "failed_uploads": len(files) - successful_uploads,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Batch upload failed: {str(e)}"}), 500

# Tools management endpoints
@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get list of available tools"""
    if not TOOL_ROUTING_ENABLED:
        return jsonify({
            "error": "Tool routing system not available",
            "tools": []
        })
    
    try:
        tools = tool_router.get_available_tools()
        return jsonify({
            "tools": tools,
            "count": len(tools),
            "status": "success"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get tools: {str(e)}"}), 500

@app.route('/api/tools/<tool_name>', methods=['GET'])
def get_tool_info(tool_name):
    """Get information about a specific tool"""
    if not TOOL_ROUTING_ENABLED:
        return jsonify({"error": "Tool routing system not available"})
    
    try:
        tool_info = tool_router.get_tool_info(tool_name)
        if tool_info:
            return jsonify(tool_info)
        else:
            return jsonify({"error": f"Tool '{tool_name}' not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to get tool info: {str(e)}"}), 500

@app.route('/api/tools/<tool_name>/execute', methods=['POST'])
def execute_tool_endpoint(tool_name):
    """Execute a specific tool"""
    if not TOOL_ROUTING_ENABLED:
        return jsonify({"error": "Tool routing system not available"})
    
    try:
        data = request.get_json()
        input_text = data.get('input', '')
        
        if not input_text:
            return jsonify({"error": "Input text is required"}), 400
        
        result = tool_router.execute_tool(tool_name, input_text)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Tool execution failed: {str(e)}"}), 500

@app.route('/api/tools/<tool_name>/enable', methods=['POST'])
def enable_tool(tool_name):
    """Enable a tool"""
    if not TOOL_ROUTING_ENABLED:
        return jsonify({"error": "Tool routing system not available"})
    
    try:
        success = tool_router.enable_tool(tool_name)
        if success:
            return jsonify({"message": f"Tool '{tool_name}' enabled", "status": "success"})
        else:
            return jsonify({"error": f"Tool '{tool_name}' not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to enable tool: {str(e)}"}), 500

@app.route('/api/tools/<tool_name>/disable', methods=['POST'])
def disable_tool(tool_name):
    """Disable a tool"""
    if not TOOL_ROUTING_ENABLED:
        return jsonify({"error": "Tool routing system not available"})
    
    try:
        success = tool_router.disable_tool(tool_name)
        if success:
            return jsonify({"message": f"Tool '{tool_name}' disabled", "status": "success"})
        else:
            return jsonify({"error": f"Tool '{tool_name}' not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to disable tool: {str(e)}"}), 500

@app.route('/api/route', methods=['POST'])
def route_query_endpoint():
    """Route a query to the best tool without executing"""
    if not TOOL_ROUTING_ENABLED:
        return jsonify({"error": "Tool routing system not available"})
    
    try:
        data = request.get_json()
        input_text = data.get('input', '')
        threshold = data.get('threshold', 0.3)
        
        if not input_text:
            return jsonify({"error": "Input text is required"}), 400
        
        tool_name, confidence, routing_info = tool_router.route_query(input_text, threshold)
        
        return jsonify({
            "routed_to_tool": tool_name is not None,
            "tool_name": tool_name,
            "confidence": confidence,
            "routing_info": routing_info,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Routing failed: {str(e)}"}), 500

# Session Management Endpoints
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all sessions for a user"""
    try:
        user_id = request.args.get('user_id', 'default')
        
        if SESSION_MANAGER_ENABLED:
            sessions = session_manager.get_user_sessions(user_id)
            return jsonify({
                "sessions": sessions,
                "total": len(sessions),
                "status": "success"
            })
        else:
            # Fallback to old conversation system
            user_conversations = []
            for conv_id, conv_data in conversations.items():
                user_conversations.append({
                    "session_id": conv_id,
                    "mode": conv_data.get("mode", "default"),
                    "created_at": conv_data.get("created_at"),
                    "last_activity": conv_data.get("created_at"),
                    "message_count": len(conv_data.get("messages", []))
                })
            
            return jsonify({
                "sessions": user_conversations,
                "total": len(user_conversations),
                "status": "success"
            })
            
    except Exception as e:
        return jsonify({"error": f"Failed to get sessions: {str(e)}", "status": "error"}), 500

@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session_details(session_id):
    """Get detailed session information"""
    try:
        if SESSION_MANAGER_ENABLED:
            session = session_manager.get_session(session_id)
            if session:
                context = get_session_context(session_id)
                return jsonify({
                    "session": session,
                    "context": context,
                    "status": "success"
                })
            else:
                return jsonify({"error": "Session not found", "status": "error"}), 404
        else:
            # Fallback
            if session_id in conversations:
                return jsonify({
                    "session": conversations[session_id],
                    "context": {},
                    "status": "success"
                })
            else:
                return jsonify({"error": "Session not found", "status": "error"}), 404
                
    except Exception as e:
        return jsonify({"error": f"Failed to get session: {str(e)}", "status": "error"}), 500

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session"""
    try:
        if SESSION_MANAGER_ENABLED:
            success = session_manager.delete_session(session_id)
            if success:
                return jsonify({"message": "Session deleted successfully", "status": "success"})
            else:
                return jsonify({"error": "Session not found", "status": "error"}), 404
        else:
            # Fallback
            if session_id in conversations:
                del conversations[session_id]
                return jsonify({"message": "Session deleted successfully", "status": "success"})
            else:
                return jsonify({"error": "Session not found", "status": "error"}), 404
                
    except Exception as e:
        return jsonify({"error": f"Failed to delete session: {str(e)}", "status": "error"}), 500

@app.route('/api/sessions/statistics', methods=['GET'])
def get_session_statistics():
    """Get overall session statistics"""
    try:
        if SESSION_MANAGER_ENABLED:
            stats = session_manager.get_session_statistics()
            return jsonify({
                "statistics": stats,
                "enhanced_features": True,
                "status": "success"
            })
        else:
            # Basic statistics from conversations
            total_conversations = len(conversations)
            total_messages = sum(len(conv.get("messages", [])) for conv in conversations.values())
            
            return jsonify({
                "statistics": {
                    "total_sessions": total_conversations,
                    "total_messages": total_messages,
                    "average_messages_per_session": total_messages / total_conversations if total_conversations > 0 else 0
                },
                "enhanced_features": False,
                "status": "success"
            })
            
    except Exception as e:
        return jsonify({"error": f"Failed to get statistics: {str(e)}", "status": "error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

