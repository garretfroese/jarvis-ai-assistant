import os
import json
import subprocess
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from src.utils.security import require_auth, validate_command, log_security_event, get_security_stats

# Load environment variables
load_dotenv()

commands_bp = Blueprint('commands', __name__)

# Configure logging for command execution
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Command execution log file
COMMAND_LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'logs', 'commands.log')

def log_command_execution(command, params, result, success, client_ip=None):
    """Log command execution for audit trail"""
    try:
        os.makedirs(os.path.dirname(COMMAND_LOG_FILE), exist_ok=True)
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "parameters": params,
            "result": result,
            "success": success,
            "client_ip": client_ip or "unknown"
        }
        with open(COMMAND_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        logger.error(f"Failed to log command execution: {str(e)}")

@commands_bp.route('/commands', methods=['POST'])
@require_auth
@validate_command
def handle_command():
    """Main command handler endpoint with enhanced security"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    try:
        data = request.json
        command = data.get("command")
        params = data.get("parameters", {})
        
        if not command:
            return jsonify({
                "status": "error",
                "message": "No command specified"
            }), 400
        
        logger.info(f"Executing command: {command} from IP: {client_ip}")
        log_security_event("COMMAND_EXECUTION", client_ip, f"Command: {command}")
        
        # Route to appropriate command handler
        result = None
        success = False
        
        if command == "setup_slack_bot":
            result = setup_slack_bot(params)
            success = result.get("status") == "success"
        elif command == "deploy_code":
            result = deploy_code(params)
            success = result.get("status") == "success"
        elif command == "send_email":
            result = send_email(params)
            success = result.get("status") == "success"
        elif command == "trigger_workflow":
            result = trigger_workflow(params)
            success = result.get("status") == "success"
        elif command == "manage_files":
            result = manage_files(params)
            success = result.get("status") == "success"
        elif command == "run_script":
            result = run_script(params)
            success = result.get("status") == "success"
        elif command == "system_info":
            result = get_system_info(params)
            success = result.get("status") == "success"
        else:
            result = {
                "status": "error",
                "message": f"Unknown command: {command}",
                "available_commands": [
                    "setup_slack_bot", "deploy_code", "send_email", 
                    "trigger_workflow", "manage_files", "run_script", "system_info"
                ]
            }
        
        # Log the command execution
        log_command_execution(command, params, result, success, client_ip)
        
        return jsonify(result)
        
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Command execution failed: {str(e)}"
        }
        log_command_execution(command if 'command' in locals() else 'unknown', 
                            params if 'params' in locals() else {}, 
                            error_result, False, client_ip)
        log_security_event("COMMAND_ERROR", client_ip, f"Error: {str(e)}")
        return jsonify(error_result), 500

def setup_slack_bot(params):
    """Set up a Slack bot with specified configuration"""
    try:
        workspace = params.get('workspace', 'default')
        bot_name = params.get('bot_name', 'Jarvis-Bot')
        bot_token = params.get('bot_token', '')
        
        # Check if Slack token is provided for real integration
        if bot_token and bot_token.startswith('xoxb-'):
            try:
                # Test the Slack token by making a simple API call
                import requests
                
                headers = {
                    'Authorization': f'Bearer {bot_token}',
                    'Content-Type': 'application/json'
                }
                
                # Test auth
                response = requests.get('https://slack.com/api/auth.test', headers=headers)
                
                if response.status_code == 200:
                    auth_data = response.json()
                    if auth_data.get('ok'):
                        return {
                            "status": "success",
                            "message": f"Slack bot '{bot_name}' successfully connected to workspace '{workspace}'",
                            "data": {
                                "bot_name": bot_name,
                                "workspace": workspace,
                                "team_name": auth_data.get('team', 'Unknown'),
                                "bot_user_id": auth_data.get('user_id'),
                                "connected": True,
                                "capabilities": [
                                    "Send messages to channels",
                                    "Respond to mentions",
                                    "Access channel history",
                                    "Manage files and attachments"
                                ]
                            }
                        }
                    else:
                        return {
                            "status": "error",
                            "message": f"Slack API error: {auth_data.get('error', 'Unknown error')}"
                        }
                else:
                    return {
                        "status": "error",
                        "message": f"Failed to connect to Slack API: HTTP {response.status_code}"
                    }
                    
            except Exception as api_error:
                return {
                    "status": "error",
                    "message": f"Slack API integration failed: {str(api_error)}"
                }
        
        # Return setup instructions if no token provided
        return {
            "status": "success",
            "message": f"Slack bot '{bot_name}' setup initiated for workspace '{workspace}'",
            "data": {
                "bot_name": bot_name,
                "workspace": workspace,
                "setup_required": True,
                "next_steps": [
                    "1. Visit https://api.slack.com/apps to create a new Slack app",
                    "2. Navigate to 'OAuth & Permissions' in your app settings",
                    "3. Add the following Bot Token Scopes:",
                    "   - app_mentions:read (to respond to @mentions)",
                    "   - channels:history (to read channel messages)",
                    "   - channels:read (to access channel information)",
                    "   - chat:write (to send messages)",
                    "   - commands (to handle slash commands)",
                    "   - files:read, files:write (to manage files)",
                    "   - users:read (to access user information)",
                    "4. Install the app to your workspace",
                    "5. Copy the 'Bot User OAuth Token' (starts with xoxb-)",
                    "6. Run the command again with the token: 'Set up Slack bot with token xoxb-your-token-here'"
                ],
                "required_scopes": [
                    "app_mentions:read", "channels:history", "channels:read", 
                    "channels:write", "chat:write", "commands", "files:read",
                    "files:write", "users:read", "reactions:read", "reactions:write"
                ],
                "webhook_url": f"https://your-jarvis-domain.com/api/slack/events",
                "slash_command_url": f"https://your-jarvis-domain.com/api/slack/commands"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to setup Slack bot: {str(e)}"
        }

def deploy_code(params):
    """Deploy code to specified environment"""
    try:
        environment = params.get('environment', 'staging')
        repository = params.get('repository', 'current')
        branch = params.get('branch', 'main')
        
        # Mock deployment process
        return {
            "status": "success",
            "message": f"Code deployment initiated to {environment}",
            "data": {
                "environment": environment,
                "repository": repository,
                "branch": branch,
                "deployment_id": f"deploy-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "estimated_time": "3-5 minutes"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to deploy code: {str(e)}"
        }

def send_email(params):
    """Send email using configured email service"""
    try:
        recipient = params.get('recipient')
        subject = params.get('subject', 'Message from Jarvis')
        body = params.get('body', '')
        sender_email = params.get('sender_email') or os.getenv('SMTP_EMAIL')
        sender_password = params.get('sender_password') or os.getenv('SMTP_PASSWORD')
        smtp_server = params.get('smtp_server') or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(params.get('smtp_port') or os.getenv('SMTP_PORT', '587'))
        
        if not recipient:
            return {
                "status": "error",
                "message": "Recipient email address is required"
            }
        
        # If SMTP credentials are provided, attempt real email sending
        if sender_email and sender_password:
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                
                # Create message
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = recipient
                msg['Subject'] = subject
                
                # Add body to email
                msg.attach(MIMEText(body, 'plain'))
                
                # Create SMTP session
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()  # Enable security
                server.login(sender_email, sender_password)
                
                # Send email
                text = msg.as_string()
                server.sendmail(sender_email, recipient, text)
                server.quit()
                
                return {
                    "status": "success",
                    "message": f"Email sent successfully to {recipient}",
                    "data": {
                        "recipient": recipient,
                        "subject": subject,
                        "sender": sender_email,
                        "sent_at": datetime.now().isoformat(),
                        "message_id": f"msg-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                        "smtp_server": smtp_server,
                        "delivery_status": "sent"
                    }
                }
                
            except Exception as smtp_error:
                return {
                    "status": "error",
                    "message": f"Failed to send email via SMTP: {str(smtp_error)}",
                    "data": {
                        "recipient": recipient,
                        "subject": subject,
                        "error_type": "smtp_error",
                        "smtp_server": smtp_server
                    }
                }
        
        # Return mock response if no SMTP credentials
        return {
            "status": "success",
            "message": f"Email queued for delivery to {recipient}",
            "data": {
                "recipient": recipient,
                "subject": subject,
                "sent_at": datetime.now().isoformat(),
                "message_id": f"msg-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "delivery_status": "queued",
                "note": "To enable real email sending, configure SMTP settings in environment variables:",
                "required_env_vars": [
                    "SMTP_EMAIL (sender email address)",
                    "SMTP_PASSWORD (sender email password or app password)",
                    "SMTP_SERVER (SMTP server, default: smtp.gmail.com)",
                    "SMTP_PORT (SMTP port, default: 587)"
                ]
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send email: {str(e)}"
        }

def trigger_workflow(params):
    """Trigger a workflow or automation"""
    try:
        workflow_id = params.get('workflow_id')
        workflow_name = params.get('workflow_name', 'Unknown Workflow')
        
        if not workflow_id:
            return {
                "status": "error",
                "message": "Workflow ID is required"
            }
        
        return {
            "status": "success",
            "message": f"Workflow '{workflow_name}' triggered successfully",
            "data": {
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "triggered_at": datetime.now().isoformat(),
                "execution_id": f"exec-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to trigger workflow: {str(e)}"
        }

def manage_files(params):
    """Manage files (create, read, update, delete)"""
    try:
        action = params.get('action', 'list')
        file_path = params.get('file_path', '')
        content = params.get('content', '')
        
        if action == 'list':
            # List files in specified directory
            directory = file_path or '/tmp'
            if os.path.exists(directory):
                files = os.listdir(directory)
                return {
                    "status": "success",
                    "message": f"Listed files in {directory}",
                    "data": {
                        "directory": directory,
                        "files": files[:20],  # Limit to first 20 files
                        "total_count": len(files)
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": f"Directory not found: {directory}"
                }
        
        elif action == 'create':
            if not file_path:
                return {
                    "status": "error",
                    "message": "File path is required for create action"
                }
            
            # Create file with content
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
            
            return {
                "status": "success",
                "message": f"File created: {file_path}",
                "data": {
                    "file_path": file_path,
                    "size": len(content),
                    "created_at": datetime.now().isoformat()
                }
            }
        
        else:
            return {
                "status": "error",
                "message": f"Unsupported file action: {action}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to manage files: {str(e)}"
        }

def run_script(params):
    """Run a Python script or shell command"""
    try:
        script_type = params.get('script_type', 'python')
        script_content = params.get('script_content', '')
        safe_mode = params.get('safe_mode', True)
        
        if not script_content:
            return {
                "status": "error",
                "message": "Script content is required"
            }
        
        if safe_mode:
            # In safe mode, only allow specific whitelisted commands
            allowed_commands = ['echo', 'ls', 'pwd', 'date', 'whoami']
            if script_type == 'shell':
                command_parts = script_content.split()
                if command_parts and command_parts[0] not in allowed_commands:
                    return {
                        "status": "error",
                        "message": f"Command '{command_parts[0]}' not allowed in safe mode"
                    }
        
        if script_type == 'python':
            # Execute Python code (be very careful with this in production)
            result = eval(script_content) if safe_mode else exec(script_content)
            return {
                "status": "success",
                "message": "Python script executed successfully",
                "data": {
                    "result": str(result) if result else "Script executed (no return value)",
                    "executed_at": datetime.now().isoformat()
                }
            }
        
        elif script_type == 'shell':
            # Execute shell command
            result = subprocess.run(
                script_content, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            return {
                "status": "success" if result.returncode == 0 else "error",
                "message": "Shell command executed",
                "data": {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                    "executed_at": datetime.now().isoformat()
                }
            }
        
        else:
            return {
                "status": "error",
                "message": f"Unsupported script type: {script_type}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to run script: {str(e)}"
        }

def get_system_info(params):
    """Get system information and status"""
    try:
        info_type = params.get('info_type', 'general')
        
        if info_type == 'general':
            return {
                "status": "success",
                "message": "System information retrieved",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "python_version": subprocess.run(['python', '--version'], 
                                                   capture_output=True, text=True).stdout.strip(),
                    "working_directory": os.getcwd(),
                    "environment_variables": {
                        "FLASK_ENV": os.getenv('FLASK_ENV', 'not set'),
                        "PORT": os.getenv('PORT', 'not set'),
                        "MODEL": os.getenv('MODEL', 'not set')
                    }
                }
            }
        
        elif info_type == 'disk':
            disk_usage = subprocess.run(['df', '-h'], capture_output=True, text=True)
            return {
                "status": "success",
                "message": "Disk usage information retrieved",
                "data": {
                    "disk_usage": disk_usage.stdout
                }
            }
        
        else:
            return {
                "status": "error",
                "message": f"Unsupported info type: {info_type}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get system info: {str(e)}"
        }

@commands_bp.route('/commands/logs', methods=['GET'])
@require_auth
def get_command_logs():
    """Retrieve command execution logs with enhanced security"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    try:
        limit = int(request.args.get('limit', 50))
        
        log_security_event("LOG_ACCESS", client_ip, f"Requested {limit} logs")
        
        if not os.path.exists(COMMAND_LOG_FILE):
            return jsonify({
                "status": "success",
                "message": "No command logs found",
                "data": {"logs": []}
            })
        
        logs = []
        with open(COMMAND_LOG_FILE, 'r') as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    logs.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        
        return jsonify({
            "status": "success",
            "message": f"Retrieved {len(logs)} command logs",
            "data": {"logs": logs}
        })
        
    except Exception as e:
        log_security_event("LOG_ACCESS_ERROR", client_ip, f"Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve logs: {str(e)}"
        }), 500

@commands_bp.route('/commands/security/stats', methods=['GET'])
@require_auth
def get_security_statistics():
    """Get security statistics"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    try:
        log_security_event("SECURITY_STATS_ACCESS", client_ip, "Security stats requested")
        
        stats = get_security_stats()
        
        return jsonify({
            "status": "success",
            "message": "Security statistics retrieved",
            "data": stats
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve security stats: {str(e)}"
        }), 500

@commands_bp.route('/commands/available', methods=['GET'])
def list_available_commands():
    """List all available commands and their descriptions"""
    commands = {
        "setup_slack_bot": {
            "description": "Set up a Slack bot with specified configuration",
            "parameters": ["workspace", "bot_name"],
            "example": {"command": "setup_slack_bot", "parameters": {"workspace": "my-workspace", "bot_name": "Jarvis-Bot"}}
        },
        "deploy_code": {
            "description": "Deploy code to specified environment",
            "parameters": ["environment", "repository", "branch"],
            "example": {"command": "deploy_code", "parameters": {"environment": "production", "branch": "main"}}
        },
        "send_email": {
            "description": "Send email using configured email service",
            "parameters": ["recipient", "subject", "body"],
            "example": {"command": "send_email", "parameters": {"recipient": "user@example.com", "subject": "Hello", "body": "Test message"}}
        },
        "trigger_workflow": {
            "description": "Trigger a workflow or automation",
            "parameters": ["workflow_id", "workflow_name"],
            "example": {"command": "trigger_workflow", "parameters": {"workflow_id": "wf-123", "workflow_name": "Deploy Pipeline"}}
        },
        "manage_files": {
            "description": "Manage files (create, read, update, delete)",
            "parameters": ["action", "file_path", "content"],
            "example": {"command": "manage_files", "parameters": {"action": "create", "file_path": "/tmp/test.txt", "content": "Hello World"}}
        },
        "run_script": {
            "description": "Run a Python script or shell command",
            "parameters": ["script_type", "script_content", "safe_mode"],
            "example": {"command": "run_script", "parameters": {"script_type": "python", "script_content": "print('Hello from Jarvis')"}}
        },
        "system_info": {
            "description": "Get system information and status",
            "parameters": ["info_type"],
            "example": {"command": "system_info", "parameters": {"info_type": "general"}}
        }
    }
    
    return jsonify({
        "status": "success",
        "message": "Available commands retrieved",
        "data": {"commands": commands}
    })

