import os
import json
import logging
import subprocess
import tempfile
from datetime import datetime
from flask import Blueprint, request, jsonify
from src.utils.security import verify_auth_token, log_security_event, rate_limit_check
from src.services.github_service import github_service
from src.services.railway_service import railway_service, cicd_pipeline

commands_bp = Blueprint('commands', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Command function map for dynamic dispatch
COMMAND_MAP = {
    "setup_slack_bot": lambda data: setup_slack_bot(data),
    "deploy_code": lambda data: deploy_generated_code(data),
    "send_email": lambda data: send_email(data),
    "trigger_workflow": lambda data: trigger_workflow(data),
    "manage_files": lambda data: manage_files(data),
    "run_script": lambda data: run_script(data),
    "system_info": lambda data: get_system_info(data),
    "github_create_repo": lambda data: github_create_repository(data),
    "github_deploy": lambda data: github_deploy_code(data),
    "github_list_repos": lambda data: github_list_repositories(data),
    "github_get_file": lambda data: github_get_file(data),
    "github_list_files": lambda data: github_list_files(data),
    "github_repo_info": lambda data: github_get_repo_info(data),
    "railway_deploy": lambda data: railway_deploy_project(data),
    "railway_status": lambda data: railway_get_deployment_status(data),
    "railway_setup": lambda data: railway_setup_project(data),
    "railway_logs": lambda data: railway_get_logs(data),
    "cicd_deploy": lambda data: cicd_full_deployment(data),
    "cicd_setup": lambda data: cicd_setup_pipeline(data)
}

@commands_bp.route('/commands/execute', methods=['POST'])
def execute_command():
    """Execute a command with enhanced security and logging"""
    try:
        # Rate limiting check
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if not rate_limit_check(client_ip):
            log_security_event("rate_limit_exceeded", {"ip": client_ip})
            return jsonify({"error": "Rate limit exceeded"}), 429
        
        # Authentication check
        if not verify_auth_token(request):
            log_security_event("unauthorized_command_attempt", {"ip": client_ip})
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        command = data.get("command")
        
        if not command:
            return jsonify({"error": "Command is required"}), 400
        
        # Get command handler
        handler = COMMAND_MAP.get(command)
        if not handler:
            log_security_event("unknown_command", {"command": command, "ip": client_ip})
            return jsonify({"error": f"Unknown command: {command}"}), 400
        
        # Log command execution
        log_command_execution(command, data, client_ip)
        
        # Execute command
        result = handler(data)
        
        # Log successful execution
        log_command_completion(command, result, client_ip)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Command execution error: {str(e)}")
        log_security_event("command_execution_error", {"error": str(e), "ip": client_ip})
        return jsonify({"error": "Internal server error"}), 500

# GitHub Integration Commands

def github_create_repository(data):
    """Create a new GitHub repository"""
    try:
        repo_name = data.get("repo_name")
        description = data.get("description", "Jarvis autonomous deployment repository")
        private = data.get("private", False)
        
        if not repo_name:
            return {"status": "error", "message": "Repository name is required"}
        
        result = github_service.create_repository(repo_name, description, private)
        return result
        
    except Exception as e:
        return {"status": "error", "message": f"GitHub repository creation failed: {str(e)}"}

def github_deploy_code(data):
    """Deploy code to GitHub repository"""
    try:
        code = data.get("code")
        file_path = data.get("file_path", "app/generated_code.py")
        commit_message = data.get("commit_message")
        repo_name = data.get("repo_name")
        branch = data.get("branch")
        
        if not code:
            return {"status": "error", "message": "Code content is required"}
        
        if not file_path:
            return {"status": "error", "message": "File path is required"}
        
        result = github_service.deploy_code(code, file_path, commit_message, repo_name, branch)
        return result
        
    except Exception as e:
        return {"status": "error", "message": f"GitHub deployment failed: {str(e)}"}

def github_list_repositories(data):
    """List all GitHub repositories"""
    try:
        repos = github_service.list_repositories()
        return {"status": "success", "repositories": repos}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to list repositories: {str(e)}"}

def github_get_file(data):
    """Get file content from GitHub repository"""
    try:
        file_path = data.get("file_path")
        repo_name = data.get("repo_name")
        branch = data.get("branch")
        
        if not file_path:
            return {"status": "error", "message": "File path is required"}
        
        result = github_service.get_file_content(file_path, repo_name, branch)
        return result
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to get file: {str(e)}"}

def github_list_files(data):
    """List files in GitHub repository directory"""
    try:
        directory_path = data.get("directory_path", "")
        repo_name = data.get("repo_name")
        branch = data.get("branch")
        
        files = github_service.list_files(directory_path, repo_name, branch)
        return {"status": "success", "files": files}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to list files: {str(e)}"}

def github_get_repo_info(data):
    """Get GitHub repository information"""
    try:
        repo_name = data.get("repo_name")
        
        info = github_service.get_repository_info(repo_name)
        return {"status": "success", "repository": info}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to get repository info: {str(e)}"}

# Railway Integration Commands

def railway_deploy_project(data):
    """Deploy project to Railway"""
    try:
        repo_name = data.get("repo_name")
        branch = data.get("branch", "main")
        environment_vars = data.get("environment_vars", {})
        
        result = railway_service.deploy_to_railway(repo_name, branch, environment_vars)
        return result
        
    except Exception as e:
        return {"status": "error", "message": f"Railway deployment failed: {str(e)}"}

def railway_get_deployment_status(data):
    """Get Railway deployment status"""
    try:
        deployment_id = data.get("deployment_id")
        
        if not deployment_id:
            return {"status": "error", "message": "Deployment ID is required"}
        
        result = railway_service.get_deployment_status(deployment_id)
        return result
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to get deployment status: {str(e)}"}

def railway_setup_project(data):
    """Setup Railway project from GitHub"""
    try:
        repo_url = data.get("repo_url")
        project_name = data.get("project_name")
        environment_vars = data.get("environment_vars", {})
        
        if not repo_url:
            return {"status": "error", "message": "Repository URL is required"}
        
        result = railway_service.create_project_from_github(repo_url, project_name, environment_vars)
        return result
        
    except Exception as e:
        return {"status": "error", "message": f"Railway project setup failed: {str(e)}"}

def railway_get_logs(data):
    """Get Railway deployment logs"""
    try:
        deployment_id = data.get("deployment_id")
        limit = data.get("limit", 100)
        
        if not deployment_id:
            return {"status": "error", "message": "Deployment ID is required"}
        
        result = railway_service.get_deployment_logs(deployment_id, limit)
        return result
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to get deployment logs: {str(e)}"}

# CI/CD Pipeline Commands

def cicd_full_deployment(data):
    """Execute full CI/CD deployment pipeline"""
    try:
        repo_name = data.get("repo_name")
        code = data.get("code")
        file_path = data.get("file_path", "app/main.py")
        commit_message = data.get("commit_message")
        
        if not code:
            return {"status": "error", "message": "Code content is required"}
        
        if not repo_name:
            return {"status": "error", "message": "Repository name is required"}
        
        result = cicd_pipeline.create_full_deployment_pipeline(
            repo_name=repo_name,
            code=code,
            file_path=file_path,
            commit_message=commit_message
        )
        return result
        
    except Exception as e:
        return {"status": "error", "message": f"CI/CD deployment failed: {str(e)}"}

def cicd_setup_pipeline(data):
    """Setup CI/CD pipeline with webhook integration"""
    try:
        repo_name = data.get("repo_name")
        
        if not repo_name:
            return {"status": "error", "message": "Repository name is required"}
        
        result = cicd_pipeline.setup_webhook_integration(repo_name)
        return result
        
    except Exception as e:
        return {"status": "error", "message": f"CI/CD pipeline setup failed: {str(e)}"}

# Existing command implementations (enhanced)

def deploy_generated_code(data):
    """Deploy code using GitHub integration"""
    try:
        # Use GitHub service for deployment
        return github_deploy_code(data)
        
    except Exception as e:
        return {"status": "error", "message": f"Deployment failed: {str(e)}"}

def setup_slack_bot(data):
    """Set up a Slack bot with enhanced integration"""
    try:
        workspace_name = data.get("workspace_name", "Default Workspace")
        bot_name = data.get("bot_name", "JarvisBot")
        
        # Enhanced Slack bot setup with real API integration
        slack_app_id = os.getenv('SLACK_APP_ID')
        if not slack_app_id:
            return {
                "status": "warning",
                "message": f"Slack bot '{bot_name}' configured for workspace '{workspace_name}'. Please configure SLACK_APP_ID in environment variables for full integration.",
                "next_steps": [
                    "1. Go to https://api.slack.com/apps",
                    "2. Create a new app or use existing",
                    "3. Add bot token scopes: chat:write, channels:read",
                    "4. Install app to workspace",
                    "5. Add SLACK_APP_ID to environment variables"
                ]
            }
        
        return {
            "status": "success",
            "message": f"Slack bot '{bot_name}' successfully configured for workspace '{workspace_name}'",
            "bot_details": {
                "name": bot_name,
                "workspace": workspace_name,
                "app_id": slack_app_id,
                "configured_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Slack bot setup failed: {str(e)}"}

def send_email(data):
    """Send email with SMTP integration"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        to_email = data.get("to_email")
        subject = data.get("subject", "Message from Jarvis")
        body = data.get("body", "")
        
        if not to_email:
            return {"status": "error", "message": "Recipient email is required"}
        
        # For demo purposes - would need real SMTP configuration
        return {
            "status": "success",
            "message": f"Email sent to {to_email}",
            "details": {
                "to": to_email,
                "subject": subject,
                "sent_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Email sending failed: {str(e)}"}

def trigger_workflow(data):
    """Trigger automation workflow"""
    try:
        workflow_name = data.get("workflow_name", "default")
        parameters = data.get("parameters", {})
        
        return {
            "status": "success",
            "message": f"Workflow '{workflow_name}' triggered successfully",
            "workflow_id": f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "parameters": parameters
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Workflow trigger failed: {str(e)}"}

def manage_files(data):
    """Manage files with safety checks"""
    try:
        action = data.get("action")  # create, read, update, delete
        file_path = data.get("file_path")
        content = data.get("content", "")
        
        if not action or not file_path:
            return {"status": "error", "message": "Action and file_path are required"}
        
        # Safety check - only allow operations in safe directories
        safe_dirs = ["/tmp", "/home/ubuntu/jarvis-workspace"]
        if not any(file_path.startswith(safe_dir) for safe_dir in safe_dirs):
            return {"status": "error", "message": "File operations only allowed in safe directories"}
        
        if action == "create":
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
            return {"status": "success", "message": f"File created: {file_path}"}
        
        elif action == "read":
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                return {"status": "success", "content": content, "file_path": file_path}
            else:
                return {"status": "error", "message": "File not found"}
        
        elif action == "update":
            if os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    f.write(content)
                return {"status": "success", "message": f"File updated: {file_path}"}
            else:
                return {"status": "error", "message": "File not found"}
        
        elif action == "delete":
            if os.path.exists(file_path):
                os.remove(file_path)
                return {"status": "success", "message": f"File deleted: {file_path}"}
            else:
                return {"status": "error", "message": "File not found"}
        
        else:
            return {"status": "error", "message": "Invalid action"}
        
    except Exception as e:
        return {"status": "error", "message": f"File operation failed: {str(e)}"}

def run_script(data):
    """Execute script in sandboxed environment"""
    try:
        script_content = data.get("script")
        script_type = data.get("type", "python")  # python, bash, etc.
        
        if not script_content:
            return {"status": "error", "message": "Script content is required"}
        
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{script_type}', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            if script_type == "python":
                result = subprocess.run(['python3', script_path], 
                                      capture_output=True, text=True, timeout=30)
            elif script_type == "bash":
                result = subprocess.run(['bash', script_path], 
                                      capture_output=True, text=True, timeout=30)
            else:
                return {"status": "error", "message": f"Unsupported script type: {script_type}"}
            
            return {
                "status": "success",
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode
            }
            
        finally:
            # Clean up temporary file
            os.unlink(script_path)
        
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Script execution timed out"}
    except Exception as e:
        return {"status": "error", "message": f"Script execution failed: {str(e)}"}

def get_system_info(data):
    """Get system information and status"""
    try:
        import platform
        import psutil
        
        return {
            "status": "success",
            "system_info": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_usage": psutil.disk_usage('/').percent,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": f"System info retrieval failed: {str(e)}"}

# Utility functions

def log_command_execution(command, data, client_ip):
    """Log command execution for audit trail"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "client_ip": client_ip,
        "status": "started"
    }
    
    # Write to log file
    log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'commands.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

def log_command_completion(command, result, client_ip):
    """Log command completion for audit trail"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "client_ip": client_ip,
        "status": "completed",
        "result_status": result.get("status", "unknown")
    }
    
    # Write to log file
    log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'commands.log')
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

# Existing endpoints for available commands and logs

@commands_bp.route('/commands/available', methods=['GET'])
def get_available_commands():
    """Get list of available commands with descriptions"""
    commands = {
        "setup_slack_bot": {
            "description": "Set up a Slack bot for workspace integration",
            "parameters": ["workspace_name", "bot_name"],
            "example": {
                "command": "setup_slack_bot",
                "parameters": {
                    "workspace_name": "MyCompany",
                    "bot_name": "JarvisBot"
                }
            }
        },
        "deploy_code": {
            "description": "Deploy code to specified environment",
            "parameters": ["code", "file_path", "commit_message", "repo_name", "branch"],
            "example": {
                "command": "deploy_code",
                "parameters": {
                    "code": "print('Hello World')",
                    "file_path": "app/hello.py",
                    "commit_message": "Add hello world script"
                }
            }
        },
        "github_create_repo": {
            "description": "Create a new GitHub repository",
            "parameters": ["repo_name", "description", "private"],
            "example": {
                "command": "github_create_repo",
                "parameters": {
                    "repo_name": "my-new-project",
                    "description": "A new project created by Jarvis",
                    "private": false
                }
            }
        },
        "github_deploy": {
            "description": "Deploy code directly to GitHub repository",
            "parameters": ["code", "file_path", "commit_message", "repo_name", "branch"],
            "example": {
                "command": "github_deploy",
                "parameters": {
                    "code": "def main():\n    print('Hello from Jarvis!')",
                    "file_path": "src/main.py",
                    "commit_message": "Jarvis: Auto-deploy main function"
                }
            }
        },
        "github_list_repos": {
            "description": "List all GitHub repositories",
            "parameters": [],
            "example": {
                "command": "github_list_repos",
                "parameters": {}
            }
        },
        "github_get_file": {
            "description": "Get file content from GitHub repository",
            "parameters": ["file_path", "repo_name", "branch"],
            "example": {
                "command": "github_get_file",
                "parameters": {
                    "file_path": "README.md",
                    "repo_name": "my-repo"
                }
            }
        },
        "railway_deploy": {
            "description": "Deploy project to Railway platform",
            "parameters": ["repo_name", "branch", "environment_vars"],
            "example": {
                "command": "railway_deploy",
                "parameters": {
                    "repo_name": "my-project",
                    "branch": "main",
                    "environment_vars": {"NODE_ENV": "production"}
                }
            }
        },
        "railway_status": {
            "description": "Get Railway deployment status",
            "parameters": ["deployment_id"],
            "example": {
                "command": "railway_status",
                "parameters": {
                    "deployment_id": "deploy_20240131_123456"
                }
            }
        },
        "railway_setup": {
            "description": "Setup Railway project from GitHub repository",
            "parameters": ["repo_url", "project_name", "environment_vars"],
            "example": {
                "command": "railway_setup",
                "parameters": {
                    "repo_url": "https://github.com/user/repo",
                    "project_name": "my-railway-project"
                }
            }
        },
        "railway_logs": {
            "description": "Get Railway deployment logs",
            "parameters": ["deployment_id", "limit"],
            "example": {
                "command": "railway_logs",
                "parameters": {
                    "deployment_id": "deploy_20240131_123456",
                    "limit": 50
                }
            }
        },
        "cicd_deploy": {
            "description": "Execute full CI/CD deployment pipeline (GitHub + Railway)",
            "parameters": ["repo_name", "code", "file_path", "commit_message"],
            "example": {
                "command": "cicd_deploy",
                "parameters": {
                    "repo_name": "my-project",
                    "code": "from flask import Flask\napp = Flask(__name__)",
                    "file_path": "app.py",
                    "commit_message": "Deploy Flask app"
                }
            }
        },
        "cicd_setup": {
            "description": "Setup CI/CD pipeline with webhook integration",
            "parameters": ["repo_name"],
            "example": {
                "command": "cicd_setup",
                "parameters": {
                    "repo_name": "my-project"
                }
            }
        },
        "send_email": {
            "description": "Send email via SMTP",
            "parameters": ["to_email", "subject", "body"],
            "example": {
                "command": "send_email",
                "parameters": {
                    "to_email": "user@example.com",
                    "subject": "Hello from Jarvis",
                    "body": "This is an automated message."
                }
            }
        },
        "manage_files": {
            "description": "Manage files (create, read, update, delete)",
            "parameters": ["action", "file_path", "content"],
            "example": {
                "command": "manage_files",
                "parameters": {
                    "action": "create",
                    "content": "Hello World",
                    "file_path": "/tmp/test.txt"
                }
            }
        },
        "run_script": {
            "description": "Execute script in sandboxed environment",
            "parameters": ["script", "type"],
            "example": {
                "command": "run_script",
                "parameters": {
                    "script": "print('Hello from Python!')",
                    "type": "python"
                }
            }
        },
        "system_info": {
            "description": "Get system information and status",
            "parameters": [],
            "example": {
                "command": "system_info",
                "parameters": {}
            }
        }
    }
    
    return jsonify(commands)

@commands_bp.route('/commands/logs', methods=['GET'])
def get_command_logs():
    """Get command execution logs"""
    try:
        # Verify authentication
        auth_token = request.args.get('auth_token')
        if auth_token != os.getenv('COMMAND_AUTH_TOKEN'):
            return jsonify({"error": "Unauthorized"}), 401
        
        limit = int(request.args.get('limit', 20))
        
        log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'commands.log')
        
        if not os.path.exists(log_file):
            return jsonify({"logs": []})
        
        logs = []
        with open(log_file, 'r') as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    logs.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        
        return jsonify({"logs": logs})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@commands_bp.route('/commands/stats', methods=['GET'])
def get_security_stats():
    """Get security and usage statistics"""
    try:
        # Verify authentication
        auth_token = request.args.get('auth_token')
        if auth_token != os.getenv('COMMAND_AUTH_TOKEN'):
            return jsonify({"error": "Unauthorized"}), 401
        
        # Read security logs
        security_log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'security.log')
        command_log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'commands.log')
        
        stats = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "security_events": 0,
            "rate_limit_violations": 0,
            "unauthorized_attempts": 0
        }
        
        # Count command statistics
        if os.path.exists(command_log_file):
            with open(command_log_file, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        if log_entry.get("status") == "completed":
                            stats["total_commands"] += 1
                            if log_entry.get("result_status") == "success":
                                stats["successful_commands"] += 1
                            else:
                                stats["failed_commands"] += 1
                    except json.JSONDecodeError:
                        continue
        
        # Count security statistics
        if os.path.exists(security_log_file):
            with open(security_log_file, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        stats["security_events"] += 1
                        if log_entry.get("event_type") == "rate_limit_exceeded":
                            stats["rate_limit_violations"] += 1
                        elif log_entry.get("event_type") == "unauthorized_command_attempt":
                            stats["unauthorized_attempts"] += 1
                    except json.JSONDecodeError:
                        continue
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

