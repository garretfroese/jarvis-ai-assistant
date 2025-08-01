"""
Command Executor Plugin for Jarvis
Executes system commands and shell operations (with security restrictions)
"""

import subprocess
import os
import re
from typing import List

# Plugin manifest - metadata about this plugin
manifest = {
    "name": "Command Executor",
    "description": "Execute safe system commands and shell operations",
    "version": "1.0.0",
    "author": "Jarvis Team",
    "category": "system",
    "tags": ["command", "shell", "system", "execution"],
    "requires_auth": True,
    "enabled": True
}

# Security: List of allowed commands (whitelist approach)
ALLOWED_COMMANDS = [
    'ls', 'dir', 'pwd', 'whoami', 'date', 'uptime', 'df', 'free',
    'ps', 'top', 'htop', 'cat', 'head', 'tail', 'wc', 'grep',
    'find', 'which', 'whereis', 'file', 'stat', 'du', 'tree',
    'git', 'npm', 'pip', 'python', 'node', 'curl', 'wget'
]

# Security: List of dangerous patterns to block
BLOCKED_PATTERNS = [
    r'rm\s+-rf',  # Dangerous delete operations
    r'sudo\s+rm',  # Sudo delete operations
    r'>\s*/dev/',  # Writing to device files
    r'mkfs\.',  # Filesystem creation
    r'fdisk',  # Disk partitioning
    r'dd\s+',  # Disk operations
    r'chmod\s+777',  # Dangerous permissions
    r'chown\s+root',  # Ownership changes
    r'passwd',  # Password changes
    r'su\s+',  # User switching
    r'sudo\s+su',  # Sudo user switching
]

def run(input_text: str) -> str:
    """
    Execute a system command with security restrictions
    
    Args:
        input_text (str): Command to execute
        
    Returns:
        str: Command output or error message
    """
    try:
        # Extract command from input
        command = extract_command(input_text)
        if not command:
            return "Please provide a command to execute. Example: 'run ls -la' or 'execute pwd'"
        
        # Security validation
        security_check = validate_command_security(command)
        if not security_check['safe']:
            return f"Command blocked for security reasons: {security_check['reason']}"
        
        # Execute the command
        result = execute_safe_command(command)
        
        return format_command_result(command, result)
        
    except Exception as e:
        return f"Error executing command: {str(e)}"

def extract_command(input_text: str) -> str:
    """Extract command from user input"""
    # Remove common command-related words
    words_to_remove = ['run', 'execute', 'command', 'shell', 'bash']
    words = input_text.split()
    
    # Find where the actual command starts
    command_words = []
    found_command = False
    
    for word in words:
        if word.lower() in words_to_remove and not found_command:
            found_command = True
            continue
        if found_command or word.lower() not in words_to_remove:
            command_words.append(word)
            found_command = True
    
    return ' '.join(command_words) if command_words else input_text.strip()

def validate_command_security(command: str) -> dict:
    """
    Validate command for security risks
    
    Args:
        command (str): Command to validate
        
    Returns:
        dict: Security validation result
    """
    # Check for blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return {
                'safe': False,
                'reason': f"Command contains blocked pattern: {pattern}"
            }
    
    # Extract the base command
    base_command = command.split()[0] if command.split() else ""
    
    # Check if base command is in allowed list
    if base_command not in ALLOWED_COMMANDS:
        return {
            'safe': False,
            'reason': f"Command '{base_command}' is not in the allowed commands list"
        }
    
    # Additional security checks
    dangerous_chars = ['|', '&', ';', '$(', '`', '>', '>>', '<']
    for char in dangerous_chars:
        if char in command:
            return {
                'safe': False,
                'reason': f"Command contains potentially dangerous character: {char}"
            }
    
    return {'safe': True, 'reason': None}

def execute_safe_command(command: str) -> dict:
    """
    Execute a command safely with timeout and output limits
    
    Args:
        command (str): Command to execute
        
    Returns:
        dict: Execution result
    """
    try:
        # Execute with timeout and capture output
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
            cwd=os.getcwd()
        )
        
        # Limit output size to prevent overwhelming responses
        stdout = result.stdout[:2000] if result.stdout else ""
        stderr = result.stderr[:1000] if result.stderr else ""
        
        if len(result.stdout) > 2000:
            stdout += "\n... (output truncated)"
        
        return {
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': stdout,
            'stderr': stderr,
            'command': command
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Command timed out (30 second limit)',
            'command': command
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'command': command
        }

def format_command_result(command: str, result: dict) -> str:
    """Format command execution result"""
    response = f"💻 Executed: `{command}`\n\n"
    
    if result.get('success'):
        response += "**Status:** ✅ Success\n"
        if result.get('stdout'):
            response += f"**Output:**\n```\n{result['stdout']}\n```\n"
        else:
            response += "**Output:** (no output)\n"
    else:
        response += "**Status:** ❌ Failed\n"
        if result.get('returncode'):
            response += f"**Return Code:** {result['returncode']}\n"
        if result.get('stderr'):
            response += f"**Error:**\n```\n{result['stderr']}\n```\n"
        if result.get('error'):
            response += f"**Error:** {result['error']}\n"
    
    return response

def get_command_confidence(input_text: str) -> float:
    """
    Calculate confidence that this input is a command execution request
    
    Args:
        input_text (str): User input
        
    Returns:
        float: Confidence score between 0.0 and 1.0
    """
    command_keywords = [
        'run', 'execute', 'command', 'shell', 'bash', 'terminal',
        'ls', 'pwd', 'whoami', 'ps', 'top', 'git', 'npm', 'pip'
    ]
    
    input_lower = input_text.lower()
    confidence = 0.0
    
    # Check for command keywords
    for keyword in command_keywords:
        if keyword in input_lower:
            confidence += 0.3
    
    # Check if it starts with common command patterns
    if input_lower.startswith(('run ', 'execute ', 'command ')):
        confidence += 0.5
    
    # Check for command-like structure
    words = input_text.split()
    if words and words[0] in ALLOWED_COMMANDS:
        confidence += 0.6
    
    # Cap at 1.0
    return min(confidence, 1.0)

def get_allowed_commands() -> List[str]:
    """Get list of allowed commands"""
    return ALLOWED_COMMANDS.copy()

def is_command_allowed(command: str) -> bool:
    """Check if a command is allowed"""
    base_command = command.split()[0] if command.split() else ""
    return base_command in ALLOWED_COMMANDS

