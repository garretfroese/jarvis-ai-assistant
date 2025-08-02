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

# Import logging service
try:
    from src.services.logging_service import logging_service, LogLevel, LogCategory
    LOGGING_ENABLED = True
    print("✅ Logging service loaded successfully")
except ImportError as e:
    print(f"⚠️ Logging service not available: {e}")
    LOGGING_ENABLED = False

# Import user service
try:
    from src.services.user_service import user_service
    from src.services.workflow_engine import workflow_engine
    from src.services.webhook_service import webhook_service
    from src.services.command_router import command_router
    from src.services.risk_filter import risk_filter
    from src.plugins.plugin_sandbox import plugin_sandbox
    from src.services.rbac_manager import rbac_manager
    from src.services.memory_loader import memory_loader
    from src.services.watchdog_agent import watchdog_agent
    from src.services.state_manager import state_manager
    USER_SERVICE_ENABLED = True
    WORKFLOW_ENGINE_ENABLED = True
    WEBHOOK_SERVICE_ENABLED = True
    COMMAND_ROUTER_ENABLED = True
    RISK_FILTER_ENABLED = True
    RBAC_MANAGER_ENABLED = True
    PLUGIN_SANDBOX_ENABLED = True
    MEMORY_LOADER_ENABLED = True
    WATCHDOG_AGENT_ENABLED = True
    STATE_MANAGER_ENABLED = True
    print("✅ User service loaded successfully")
    print("✅ Workflow engine loaded successfully")
    print("✅ Webhook service loaded successfully")
    print("✅ Command router loaded successfully")
    print("✅ Risk filter loaded successfully")
    print("✅ RBAC manager loaded successfully")
    print("✅ Plugin sandbox loaded successfully")
    print("✅ Memory loader loaded successfully")
    print("✅ Watchdog agent loaded successfully")
    print("✅ State manager loaded successfully")
except ImportError as e:
    print(f"⚠️ Services not available: {e}")
    USER_SERVICE_ENABLED = False
    WORKFLOW_ENGINE_ENABLED = False
    WEBHOOK_SERVICE_ENABLED = False
    COMMAND_ROUTER_ENABLED = False
    RISK_FILTER_ENABLED = False
    RBAC_MANAGER_ENABLED = False
    PLUGIN_SANDBOX_ENABLED = False

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
    start_time = datetime.now()
    
    try:
        data = request.get_json()
        message = data.get('message', '')
        conversation_id = data.get('conversation_id', 'default')
        user_id = data.get('user_id', 'default')
        
        # Log incoming chat request
        if LOGGING_ENABLED:
            logging_service.log_session_event(
                user_id=user_id,
                session_id=conversation_id,
                event="chat_request_received",
                details={"message_length": len(message), "mode": current_mode}
            )
        
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
                
                # Log mode switch
                if LOGGING_ENABLED:
                    logging_service.log_session_event(
                        user_id=user_id,
                        session_id=conversation_id,
                        event="mode_switch",
                        details={"from_mode": old_mode, "to_mode": current_mode}
                    )
                
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
        tool_start_time = datetime.now()
        
        if TOOL_ROUTING_ENABLED:
            try:
                tool_result = route_and_execute(message, threshold=0.3)
                tool_duration = (datetime.now() - tool_start_time).total_seconds() * 1000
                
                if tool_result.get('routed_to_tool') and tool_result.get('success'):
                    ai_response = f"🔧 **Tool Used:** {tool_result['tool_name']}\n\n{tool_result['output']}"
                    
                    # Log successful tool execution
                    if LOGGING_ENABLED:
                        logging_service.log_tool_execution(
                            user_id=user_id,
                            session_id=conversation_id,
                            tool_name=tool_result['tool_name'],
                            tool_input=message,
                            tool_output=tool_result['output'],
                            success=True,
                            duration_ms=int(tool_duration)
                        )
                    
                    # Add tool usage info to conversation
                    conversations[conversation_id]["messages"].append({
                        "role": "system",
                        "content": f"Used tool: {tool_result['tool_name']} (confidence: {tool_result['confidence']:.2f})",
                        "timestamp": datetime.now().isoformat(),
                        "tool_info": tool_result
                    })
                else:
                    # Log tool routing attempt but no execution
                    if LOGGING_ENABLED and tool_result.get('routed_to_tool'):
                        logging_service.log_tool_execution(
                            user_id=user_id,
                            session_id=conversation_id,
                            tool_name=tool_result.get('tool_name', 'unknown'),
                            tool_input=message,
                            tool_output=tool_result.get('output', 'No output'),
                            success=False,
                            duration_ms=int(tool_duration),
                            error_message=tool_result.get('error', 'Tool execution failed')
                        )
                    
            except Exception as e:
                tool_duration = (datetime.now() - tool_start_time).total_seconds() * 1000
                print(f"Tool routing error: {str(e)}")
                
                # Log tool routing error
                if LOGGING_ENABLED:
                    logging_service.log_error(
                        error_type="tool_routing_error",
                        error_message=str(e),
                        user_id=user_id,
                        session_id=conversation_id,
                        details={"message": message, "duration_ms": int(tool_duration)}
                    )
        
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
        
        # Log successful chat completion
        if LOGGING_ENABLED:
            total_duration = (datetime.now() - start_time).total_seconds() * 1000
            tool_name = tool_result.get('tool_name') if tool_result and tool_result.get('routed_to_tool') else None
            
            logging_service.log_chat_message(
                user_id=user_id,
                session_id=conversation_id,
                message=message,
                response=ai_response,
                tool_used=tool_name,
                duration_ms=int(total_duration)
            )
        
        return jsonify(response_data)
        
    except Exception as e:
        # Log chat error
        if LOGGING_ENABLED:
            total_duration = (datetime.now() - start_time).total_seconds() * 1000
            logging_service.log_error(
                error_type="chat_error",
                error_message=str(e),
                user_id=data.get('user_id', 'unknown') if 'data' in locals() else 'unknown',
                session_id=data.get('conversation_id', 'unknown') if 'data' in locals() else 'unknown',
                details={"duration_ms": int(total_duration)}
            )
        
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
    start_time = datetime.now()
    
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
        
        # Log file upload start
        if LOGGING_ENABLED:
            logging_service.log_file_operation(
                user_id=user_id,
                session_id=session_id or 'default',
                operation="upload_start",
                filename=file.filename,
                file_size=len(file.read())
            )
            file.seek(0)  # Reset file pointer after reading for size
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4()}_{filename}")
        file.save(temp_path)
        
        # Process with advanced file processor
        result = file_processor.upload_file(temp_path, filename, user_id, session_id)
        
        # Log successful upload
        if LOGGING_ENABLED:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logging_service.log_file_operation(
                user_id=user_id,
                session_id=session_id or 'default',
                operation="upload_complete",
                filename=filename,
                file_size=result.get('file_size'),
                success=True,
                duration_ms=int(duration)
            )
        
        return jsonify(result)
        
    except Exception as e:
        # Log upload error
        if LOGGING_ENABLED:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logging_service.log_file_operation(
                user_id=user_id if 'user_id' in locals() else 'unknown',
                session_id=session_id if 'session_id' in locals() else 'unknown',
                operation="upload_failed",
                filename=file.filename if 'file' in locals() else 'unknown',
                success=False,
                duration_ms=int(duration),
                error_message=str(e)
            )
        
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

# Logging and Analytics Endpoints
@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get filtered logs for dashboard"""
    if not LOGGING_ENABLED:
        return jsonify({"error": "Logging service not available"}), 503
    
    try:
        # Get query parameters
        user_id = request.args.get('user_id')
        session_id = request.args.get('session_id')
        category = request.args.get('category')
        level = request.args.get('level')
        limit = int(request.args.get('limit', 100))
        
        # Convert string parameters to enums if provided
        category_enum = None
        if category:
            try:
                category_enum = LogCategory(category)
            except ValueError:
                return jsonify({"error": f"Invalid category: {category}"}), 400
        
        level_enum = None
        if level:
            try:
                level_enum = LogLevel(level)
            except ValueError:
                return jsonify({"error": f"Invalid level: {level}"}), 400
        
        # Get filtered logs
        logs = logging_service.get_logs(
            user_id=user_id,
            session_id=session_id,
            category=category_enum,
            level=level_enum,
            limit=limit
        )
        
        # Convert to JSON-serializable format
        logs_data = []
        for log in logs:
            logs_data.append({
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "level": log.level.value,
                "category": log.category.value,
                "user_id": log.user_id,
                "session_id": log.session_id,
                "action": log.action,
                "details": log.details,
                "duration_ms": log.duration_ms,
                "success": log.success,
                "error_message": log.error_message,
                "metadata": log.metadata
            })
        
        return jsonify({
            "logs": logs_data,
            "total": len(logs_data),
            "filters": {
                "user_id": user_id,
                "session_id": session_id,
                "category": category,
                "level": level,
                "limit": limit
            },
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get logs: {str(e)}"}), 500

@app.route('/api/logs/statistics', methods=['GET'])
def get_log_statistics():
    """Get usage statistics and analytics"""
    if not LOGGING_ENABLED:
        return jsonify({"error": "Logging service not available"}), 503
    
    try:
        user_id = request.args.get('user_id')
        stats = logging_service.get_statistics(user_id=user_id)
        
        return jsonify({
            "statistics": stats,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get statistics: {str(e)}"}), 500

@app.route('/api/logs/activity', methods=['GET'])
def get_recent_activity():
    """Get recent activity for dashboard"""
    if not LOGGING_ENABLED:
        return jsonify({"error": "Logging service not available"}), 503
    
    try:
        limit = int(request.args.get('limit', 50))
        activity = logging_service.get_recent_activity(limit=limit)
        
        return jsonify({
            "activity": activity,
            "total": len(activity),
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get activity: {str(e)}"}), 500

@app.route('/api/logs/cleanup', methods=['POST'])
def cleanup_logs():
    """Clean up old log files"""
    if not LOGGING_ENABLED:
        return jsonify({"error": "Logging service not available"}), 503
    
    try:
        data = request.get_json() or {}
        days_to_keep = data.get('days_to_keep', 30)
        
        logging_service.cleanup_old_logs(days_to_keep=days_to_keep)
        
        return jsonify({
            "message": f"Cleaned up logs older than {days_to_keep} days",
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to cleanup logs: {str(e)}"}), 500

# ===== USER MANAGEMENT ENDPOINTS =====

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """Register a new user"""
    if not USER_SERVICE_ENABLED:
        return jsonify({"error": "User service not available"}), 503
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'user')
        
        if not all([username, email, password]):
            return jsonify({"error": "Username, email, and password are required"}), 400
        
        # Create user
        user = user_service.create_user(
            username=username,
            email=email,
            password=password,
            role=role
        )
        
        if user:
            # Log user registration
            if LOGGING_ENABLED:
                logging_service.log_auth_event(
                    user_id=user['id'],
                    event_type="user_registration",
                    details={"username": username, "email": email, "role": role}
                )
            
            return jsonify({
                "message": "User registered successfully",
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user['email'],
                    "role": user['role']
                },
                "status": "success"
            })
        else:
            return jsonify({"error": "Failed to create user"}), 400
        
    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    """Login user and return JWT token"""
    if not USER_SERVICE_ENABLED:
        return jsonify({"error": "User service not available"}), 503
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not all([username, password]):
            return jsonify({"error": "Username and password are required"}), 400
        
        # Authenticate user
        result = user_service.authenticate_user(username, password)
        
        if result and result.get('success'):
            user = result['user']
            token = result['token']
            
            # Log successful login
            if LOGGING_ENABLED:
                logging_service.log_auth_event(
                    user_id=user['id'],
                    event_type="user_login",
                    details={"username": username}
                )
            
            return jsonify({
                "message": "Login successful",
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user['email'],
                    "role": user['role'],
                    "permissions": user_service.get_user_permissions(user['role'])
                },
                "token": token,
                "status": "success"
            })
        else:
            # Log failed login
            if LOGGING_ENABLED:
                logging_service.log_auth_event(
                    user_id="unknown",
                    event_type="login_failed",
                    details={"username": username}
                )
            
            return jsonify({"error": "Invalid username or password"}), 401
        
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout_user():
    """Logout user and invalidate token"""
    if not USER_SERVICE_ENABLED:
        return jsonify({"error": "User service not available"}), 503
    
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "No valid token provided"}), 401
        
        token = auth_header.split(' ')[1]
        
        # Verify and invalidate token
        result = user_service.logout_user(token)
        
        if result and result.get('success'):
            user_id = result.get('user_id')
            
            # Log logout
            if LOGGING_ENABLED:
                logging_service.log_auth_event(
                    user_id=user_id,
                    event_type="user_logout",
                    details={}
                )
            
            return jsonify({
                "message": "Logout successful",
                "status": "success"
            })
        else:
            return jsonify({"error": "Invalid token"}), 401
        
    except Exception as e:
        return jsonify({"error": f"Logout failed: {str(e)}"}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users (admin only)"""
    if not USER_SERVICE_ENABLED:
        return jsonify({"error": "User service not available"}), 503
    
    try:
        # Check authentication and permissions
        auth_result = check_auth_and_permissions(['user_management'])
        if not auth_result['success']:
            return jsonify({"error": auth_result['error']}), auth_result['status_code']
        
        users = user_service.get_all_users()
        
        return jsonify({
            "users": users,
            "total": len(users),
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get users: {str(e)}"}), 500

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get specific user details"""
    if not USER_SERVICE_ENABLED:
        return jsonify({"error": "User service not available"}), 503
    
    try:
        # Check authentication
        auth_result = check_auth_and_permissions([])
        if not auth_result['success']:
            return jsonify({"error": auth_result['error']}), auth_result['status_code']
        
        # Users can only view their own profile unless they're admin
        current_user = auth_result['user']
        if current_user['id'] != user_id and 'user_management' not in user_service.get_user_permissions(current_user['role']):
            return jsonify({"error": "Permission denied"}), 403
        
        user = user_service.get_user_by_id(user_id)
        
        if user:
            return jsonify({
                "user": user,
                "status": "success"
            })
        else:
            return jsonify({"error": "User not found"}), 404
        
    except Exception as e:
        return jsonify({"error": f"Failed to get user: {str(e)}"}), 500

@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user details"""
    if not USER_SERVICE_ENABLED:
        return jsonify({"error": "User service not available"}), 503
    
    try:
        # Check authentication
        auth_result = check_auth_and_permissions([])
        if not auth_result['success']:
            return jsonify({"error": auth_result['error']}), auth_result['status_code']
        
        # Users can only update their own profile unless they're admin
        current_user = auth_result['user']
        if current_user['id'] != user_id and 'user_management' not in user_service.get_user_permissions(current_user['role']):
            return jsonify({"error": "Permission denied"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Update user
        updated_user = user_service.update_user(user_id, data)
        
        if updated_user:
            # Log user update
            if LOGGING_ENABLED:
                logging_service.log_auth_event(
                    user_id=user_id,
                    event_type="user_updated",
                    details={"updated_by": current_user['id'], "fields": list(data.keys())}
                )
            
            return jsonify({
                "message": "User updated successfully",
                "user": updated_user,
                "status": "success"
            })
        else:
            return jsonify({"error": "Failed to update user"}), 400
        
    except Exception as e:
        return jsonify({"error": f"Failed to update user: {str(e)}"}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete user (admin only)"""
    if not USER_SERVICE_ENABLED:
        return jsonify({"error": "User service not available"}), 503
    
    try:
        # Check authentication and permissions
        auth_result = check_auth_and_permissions(['user_management'])
        if not auth_result['success']:
            return jsonify({"error": auth_result['error']}), auth_result['status_code']
        
        current_user = auth_result['user']
        
        # Prevent self-deletion
        if current_user['id'] == user_id:
            return jsonify({"error": "Cannot delete your own account"}), 400
        
        # Delete user
        success = user_service.delete_user(user_id)
        
        if success:
            # Log user deletion
            if LOGGING_ENABLED:
                logging_service.log_auth_event(
                    user_id=user_id,
                    event_type="user_deleted",
                    details={"deleted_by": current_user['id']}
                )
            
            return jsonify({
                "message": "User deleted successfully",
                "status": "success"
            })
        else:
            return jsonify({"error": "Failed to delete user"}), 400
        
    except Exception as e:
        return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500

@app.route('/api/users/statistics', methods=['GET'])
def get_user_statistics():
    """Get user statistics (admin only)"""
    if not USER_SERVICE_ENABLED:
        return jsonify({"error": "User service not available"}), 503
    
    try:
        # Check authentication and permissions
        auth_result = check_auth_and_permissions(['user_management'])
        if not auth_result['success']:
            return jsonify({"error": auth_result['error']}), auth_result['status_code']
        
        stats = user_service.get_user_statistics()
        
        return jsonify({
            "statistics": stats,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get user statistics: {str(e)}"}), 500

def check_auth_and_permissions(required_permissions=None):
    """Helper function to check authentication and permissions"""
    if not USER_SERVICE_ENABLED:
        return {"success": False, "error": "User service not available", "status_code": 503}
    
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return {"success": False, "error": "No valid token provided", "status_code": 401}
        
        token = auth_header.split(' ')[1]
        
        # Verify token
        user = user_service.verify_token(token)
        if not user:
            return {"success": False, "error": "Invalid or expired token", "status_code": 401}
        
        # Check permissions if required
        if required_permissions:
            user_permissions = user_service.get_user_permissions(user['role'])
            for permission in required_permissions:
                if permission not in user_permissions:
                    return {"success": False, "error": f"Permission denied: {permission}", "status_code": 403}
        
        return {"success": True, "user": user}
        
    except Exception as e:
        return {"success": False, "error": f"Authentication failed: {str(e)}", "status_code": 500}

# Workflow API Endpoints
@app.route('/api/workflows', methods=['GET'])
def get_workflows():
    """Get all available workflows"""
    try:
        if not WORKFLOW_ENGINE_ENABLED:
            return jsonify({"error": "Workflow engine not available"}), 503
        
        workflows = workflow_engine.get_workflow_definitions()
        
        return jsonify({
            "workflows": workflows,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get workflows: {str(e)}"}), 500

@app.route('/api/workflows/execute/<workflow_id>', methods=['POST'])
def execute_workflow(workflow_id):
    """Execute a workflow"""
    try:
        if not WORKFLOW_ENGINE_ENABLED:
            return jsonify({"error": "Workflow engine not available"}), 503
        
        data = request.get_json() or {}
        context = data.get('context', {})
        user_id = data.get('user_id')
        
        # Execute workflow asynchronously
        execution_id = workflow_engine.execute_workflow(workflow_id, context, user_id)
        
        return jsonify({
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": "started",
            "message": "Workflow execution started"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to execute workflow: {str(e)}"}), 500

@app.route('/api/workflows/executions/<execution_id>', methods=['GET'])
def get_workflow_execution(execution_id):
    """Get workflow execution status"""
    try:
        if not WORKFLOW_ENGINE_ENABLED:
            return jsonify({"error": "Workflow engine not available"}), 503
        
        execution = workflow_engine.get_execution_status(execution_id)
        
        if not execution:
            return jsonify({"error": "Execution not found"}), 404
        
        return jsonify({
            "execution": execution,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get execution: {str(e)}"}), 500

@app.route('/api/workflows/executions/<execution_id>/results', methods=['GET'])
def get_workflow_results(execution_id):
    """Get workflow execution results"""
    try:
        if not WORKFLOW_ENGINE_ENABLED:
            return jsonify({"error": "Workflow engine not available"}), 503
        
        results = workflow_engine.get_execution_results(execution_id)
        
        if not results:
            return jsonify({"error": "Execution not found"}), 404
        
        return jsonify({
            "results": results,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get results: {str(e)}"}), 500

# Webhook API Endpoints
@app.route('/webhook/<source>', methods=['POST'])
def receive_webhook(source):
    """Receive webhook from external source"""
    try:
        if not WEBHOOK_SERVICE_ENABLED:
            return jsonify({"error": "Webhook service not available"}), 503
        
        # Get request data
        headers = dict(request.headers)
        payload = request.get_json() or {}
        ip_address = request.remote_addr
        
        # Process webhook
        result = webhook_service.process_webhook(source, headers, payload, ip_address)
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Webhook processing failed: {str(e)}"
        }), 500

@app.route('/api/webhooks/logs', methods=['GET'])
def get_webhook_logs():
    """Get webhook logs"""
    try:
        if not WEBHOOK_SERVICE_ENABLED:
            return jsonify({"error": "Webhook service not available"}), 503
        
        source = request.args.get('source')
        limit = int(request.args.get('limit', 100))
        
        logs = webhook_service.get_webhook_logs(source, limit)
        
        return jsonify({
            "logs": logs,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get webhook logs: {str(e)}"}), 500

@app.route('/api/webhooks/sources', methods=['GET'])
def get_webhook_sources():
    """Get configured webhook sources"""
    try:
        if not WEBHOOK_SERVICE_ENABLED:
            return jsonify({"error": "Webhook service not available"}), 503
        
        sources = webhook_service.get_webhook_sources()
        
        return jsonify({
            "sources": sources,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get webhook sources: {str(e)}"}), 500

@app.route('/api/webhooks/statistics', methods=['GET'])
def get_webhook_statistics():
    """Get webhook statistics"""
    try:
        if not WEBHOOK_SERVICE_ENABLED:
            return jsonify({"error": "Webhook service not available"}), 503
        
        stats = webhook_service.get_webhook_statistics()
        
        return jsonify({
            "statistics": stats,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get webhook statistics: {str(e)}"}), 500

# Phase 5: Command Router API Endpoints
@app.route('/api/route', methods=['POST'])
def route_command():
    """Intelligent command routing"""
    try:
        if not COMMAND_ROUTER_ENABLED:
            return jsonify({"error": "Command router not available"}), 503
        
        data = request.get_json() or {}
        message = data.get('message', '')
        user_id = data.get('user_id')
        context = data.get('context', {})
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        # Route the command
        classification = command_router.route_command(message, user_id, context)
        
        return jsonify({
            "classification": {
                "command_type": classification.command_type.value,
                "handler": classification.handler,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
                "parameters": classification.parameters
            },
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Command routing failed: {str(e)}"}), 500

@app.route('/api/command', methods=['POST'])
def execute_command():
    """Secure command execution with risk assessment"""
    try:
        if not COMMAND_ROUTER_ENABLED or not RISK_FILTER_ENABLED:
            return jsonify({"error": "Command execution services not available"}), 503
        
        data = request.get_json() or {}
        message = data.get('message', '')
        user_id = data.get('user_id')
        context = data.get('context', {})
        ip_address = request.remote_addr
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        # Risk assessment
        risk_assessment = risk_filter.assess_risk(message, user_id or 'anonymous', context, ip_address)
        
        if risk_assessment.blocked:
            return jsonify({
                "status": "blocked",
                "risk_assessment": {
                    "risk_level": risk_assessment.risk_level.value,
                    "reasoning": risk_assessment.reasoning,
                    "recommendations": risk_assessment.recommendations
                },
                "message": "Command blocked due to security risk"
            }), 403
        
        # Route and execute command
        classification = command_router.route_command(message, user_id, context)
        result = command_router.execute_command(classification, user_id, context)
        
        return jsonify({
            "status": "executed",
            "classification": {
                "command_type": classification.command_type.value,
                "handler": classification.handler,
                "confidence": classification.confidence
            },
            "risk_assessment": {
                "risk_level": risk_assessment.risk_level.value,
                "confidence": risk_assessment.confidence
            },
            "result": result
        })
        
    except Exception as e:
        return jsonify({"error": f"Command execution failed: {str(e)}"}), 500

# Plugin API Endpoints
@app.route('/api/plugins', methods=['GET'])
def get_plugins():
    """Get available plugins"""
    try:
        if not PLUGIN_SANDBOX_ENABLED:
            return jsonify({"error": "Plugin sandbox not available"}), 503
        
        plugins = plugin_sandbox.list_plugins()
        
        return jsonify({
            "plugins": plugins,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get plugins: {str(e)}"}), 500

@app.route('/api/plugins/execute', methods=['POST'])
def execute_plugin():
    """Execute plugin in sandbox"""
    try:
        if not PLUGIN_SANDBOX_ENABLED:
            return jsonify({"error": "Plugin sandbox not available"}), 503
        
        data = request.get_json() or {}
        plugin_name = data.get('plugin_name')
        input_data = data.get('input_data', {})
        user_id = data.get('user_id')
        timeout = data.get('timeout')
        
        if not plugin_name:
            return jsonify({"error": "No plugin name provided"}), 400
        
        # Check permissions
        if RBAC_MANAGER_ENABLED and user_id:
            from src.services.rbac_manager import Permission
            if not rbac_manager.has_permission(user_id, Permission.PLUGIN_EXECUTION):
                return jsonify({"error": "Insufficient permissions for plugin execution"}), 403
        
        # Execute plugin
        execution_id = plugin_sandbox.execute_plugin(plugin_name, input_data, user_id or 'anonymous', timeout)
        
        return jsonify({
            "execution_id": execution_id,
            "plugin_name": plugin_name,
            "status": "started",
            "message": "Plugin execution started"
        })
        
    except Exception as e:
        return jsonify({"error": f"Plugin execution failed: {str(e)}"}), 500

@app.route('/api/plugins/executions/<execution_id>', methods=['GET'])
def get_plugin_execution(execution_id):
    """Get plugin execution status"""
    try:
        if not PLUGIN_SANDBOX_ENABLED:
            return jsonify({"error": "Plugin sandbox not available"}), 503
        
        execution = plugin_sandbox.get_execution_status(execution_id)
        
        if not execution:
            return jsonify({"error": "Execution not found"}), 404
        
        return jsonify({
            "execution": execution,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get execution: {str(e)}"}), 500

@app.route('/api/plugins/executions/<execution_id>/results', methods=['GET'])
def get_plugin_results(execution_id):
    """Get plugin execution results"""
    try:
        if not PLUGIN_SANDBOX_ENABLED:
            return jsonify({"error": "Plugin sandbox not available"}), 503
        
        result = plugin_sandbox.get_execution_result(execution_id)
        
        if not result:
            return jsonify({"error": "Execution not found"}), 404
        
        return jsonify({
            "result": result,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get results: {str(e)}"}), 500

@app.route('/api/plugins/executions/<execution_id>/kill', methods=['POST'])
def kill_plugin_execution(execution_id):
    """Kill running plugin execution"""
    try:
        if not PLUGIN_SANDBOX_ENABLED:
            return jsonify({"error": "Plugin sandbox not available"}), 503
        
        success = plugin_sandbox.kill_execution(execution_id)
        
        return jsonify({
            "success": success,
            "message": "Execution killed" if success else "Failed to kill execution"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to kill execution: {str(e)}"}), 500

# RBAC API Endpoints
@app.route('/api/permissions', methods=['GET'])
def get_user_permissions():
    """Get user permissions"""
    try:
        if not RBAC_MANAGER_ENABLED:
            return jsonify({"error": "RBAC manager not available"}), 503
        
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "No user_id provided"}), 400
        
        permissions = rbac_manager.get_user_role_summary(user_id)
        
        return jsonify({
            "permissions": permissions,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get permissions: {str(e)}"}), 500

@app.route('/api/permissions/check', methods=['POST'])
def check_permission():
    """Check specific permission"""
    try:
        if not RBAC_MANAGER_ENABLED:
            return jsonify({"error": "RBAC manager not available"}), 503
        
        data = request.get_json() or {}
        user_id = data.get('user_id')
        permission = data.get('permission')
        
        if not user_id or not permission:
            return jsonify({"error": "user_id and permission required"}), 400
        
        from src.services.rbac_manager import Permission as PermissionEnum
        try:
            perm_enum = PermissionEnum(permission)
            has_permission = rbac_manager.has_permission(user_id, perm_enum)
        except ValueError:
            return jsonify({"error": f"Invalid permission: {permission}"}), 400
        
        return jsonify({
            "user_id": user_id,
            "permission": permission,
            "has_permission": has_permission,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Permission check failed: {str(e)}"}), 500

@app.route('/api/roles', methods=['GET'])
def get_roles():
    """Get all available roles"""
    try:
        if not RBAC_MANAGER_ENABLED:
            return jsonify({"error": "RBAC manager not available"}), 503
        
        roles = rbac_manager.get_all_roles()
        
        return jsonify({
            "roles": roles,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get roles: {str(e)}"}), 500

@app.route('/api/permissions/all', methods=['GET'])
def get_all_permissions():
    """Get all available permissions"""
    try:
        if not RBAC_MANAGER_ENABLED:
            return jsonify({"error": "RBAC manager not available"}), 503
        
        permissions = rbac_manager.get_all_permissions()
        
        return jsonify({
            "permissions": permissions,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get permissions: {str(e)}"}), 500

# Security API Endpoints
@app.route('/api/security/events', methods=['GET'])
def get_security_events():
    """Get security events"""
    try:
        if not RISK_FILTER_ENABLED:
            return jsonify({"error": "Risk filter not available"}), 503
        
        user_id = request.args.get('user_id')
        risk_level = request.args.get('risk_level')
        limit = int(request.args.get('limit', 100))
        
        from src.services.risk_filter import RiskLevel
        risk_level_enum = None
        if risk_level:
            try:
                risk_level_enum = RiskLevel(risk_level.lower())
            except ValueError:
                return jsonify({"error": f"Invalid risk level: {risk_level}"}), 400
        
        events = risk_filter.get_security_events(user_id, risk_level_enum, limit)
        
        return jsonify({
            "events": events,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get security events: {str(e)}"}), 500

@app.route('/api/security/statistics', methods=['GET'])
def get_security_statistics():
    """Get security statistics"""
    try:
        if not RISK_FILTER_ENABLED:
            return jsonify({"error": "Risk filter not available"}), 503
        
        stats = risk_filter.get_security_statistics()
        
        return jsonify({
            "statistics": stats,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get security statistics: {str(e)}"}), 500

# ===== PHASE 6: MEMORY & SELF-HEALING API ENDPOINTS =====

@app.route('/api/memory/status', methods=['GET'])
def get_memory_status():
    """Get memory system status"""
    try:
        if not MEMORY_LOADER_ENABLED:
            return jsonify({"error": "Memory loader not available"}), 503
        
        status = memory_loader.get_memory_status()
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({"error": f"Failed to get memory status: {str(e)}"}), 500

@app.route('/api/memory/load', methods=['GET'])
def load_memory():
    """Load memory from disk"""
    try:
        if not MEMORY_LOADER_ENABLED:
            return jsonify({"error": "Memory loader not available"}), 503
        
        memory_type = request.args.get('type', 'all')
        
        result = memory_loader.load_memory(memory_type)
        
        return jsonify({
            "memory": result,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to load memory: {str(e)}"}), 500

@app.route('/api/memory/reload', methods=['POST'])
def reload_memory():
    """Force reload memory from disk"""
    try:
        if not MEMORY_LOADER_ENABLED:
            return jsonify({"error": "Memory loader not available"}), 503
        
        data = request.get_json() or {}
        memory_type = data.get('type', 'all')
        force = data.get('force', False)
        
        result = memory_loader.reload_memory(memory_type, force)
        
        return jsonify({
            "memory": result,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to reload memory: {str(e)}"}), 500

@app.route('/api/watchdog/status', methods=['GET'])
def get_watchdog_status():
    """Get watchdog health status"""
    try:
        if not WATCHDOG_AGENT_ENABLED:
            return jsonify({"error": "Watchdog agent not available"}), 503
        
        status = watchdog_agent.get_health_status()
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({"error": f"Failed to get watchdog status: {str(e)}"}), 500

@app.route('/api/watchdog/check', methods=['POST'])
def force_health_check():
    """Force immediate health check"""
    try:
        if not WATCHDOG_AGENT_ENABLED:
            return jsonify({"error": "Watchdog agent not available"}), 503
        
        result = watchdog_agent.force_health_check()
        
        return jsonify({
            "health_check": result,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to force health check: {str(e)}"}), 500

@app.route('/api/watchdog/history', methods=['GET'])
def get_health_history():
    """Get health check history"""
    try:
        if not WATCHDOG_AGENT_ENABLED:
            return jsonify({"error": "Watchdog agent not available"}), 503
        
        limit = int(request.args.get('limit', 50))
        history = watchdog_agent.get_health_history(limit)
        
        return jsonify({
            "history": history,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get health history: {str(e)}"}), 500

@app.route('/api/state/export', methods=['GET'])
def export_system_state():
    """Export complete system state"""
    try:
        if not STATE_MANAGER_ENABLED:
            return jsonify({"error": "State manager not available"}), 503
        
        include_sensitive = request.args.get('include_sensitive', 'false').lower() == 'true'
        
        state = state_manager.export_system_state(include_sensitive)
        
        return jsonify(state)
        
    except Exception as e:
        return jsonify({"error": f"Failed to export system state: {str(e)}"}), 500

@app.route('/api/state/plugin-cache', methods=['GET'])
def get_plugin_cache_status():
    """Get plugin cache status"""
    try:
        if not STATE_MANAGER_ENABLED:
            return jsonify({"error": "State manager not available"}), 503
        
        status = state_manager.get_plugin_cache_status()
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({"error": f"Failed to get plugin cache status: {str(e)}"}), 500

@app.route('/api/state/plugin-cache/refresh', methods=['POST'])
def refresh_plugin_cache():
    """Refresh plugin cache"""
    try:
        if not STATE_MANAGER_ENABLED:
            return jsonify({"error": "State manager not available"}), 503
        
        success = state_manager.refresh_plugin_cache()
        
        return jsonify({
            "success": success,
            "status": "success" if success else "failed"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to refresh plugin cache: {str(e)}"}), 500

@app.route('/api/state/files', methods=['GET'])
def get_state_files_info():
    """Get state files information"""
    try:
        if not STATE_MANAGER_ENABLED:
            return jsonify({"error": "State manager not available"}), 503
        
        info = state_manager.get_state_files_info()
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({"error": f"Failed to get state files info: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

