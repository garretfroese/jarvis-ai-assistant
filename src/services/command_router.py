"""
Command Routing Engine for Jarvis AI Assistant
Intelligently classifies and routes user messages to appropriate handlers.
"""

import re
import json
import openai
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

# Import existing services
from .tool_router import tool_router
from .workflow_engine import workflow_engine
from .logging_service import logging_service

class CommandType(Enum):
    CHAT = "chat"
    TOOL = "tool"
    FILE_OPERATION = "file_operation"
    WORKFLOW = "workflow"
    WEBHOOK = "webhook"
    PLUGIN = "plugin"
    SYSTEM = "system"

@dataclass
class CommandClassification:
    """Result of command classification"""
    command_type: CommandType
    confidence: float
    handler: str
    parameters: Dict[str, Any]
    reasoning: str

@dataclass
class RoutingRule:
    """Command routing rule definition"""
    keywords: List[str]
    patterns: List[str]
    command_type: CommandType
    handler: str
    priority: int
    requires_auth: bool = True
    required_permissions: List[str] = None

class CommandRouter:
    """Intelligent command routing engine"""
    
    def __init__(self):
        self.routing_rules = self._initialize_routing_rules()
        self.classification_cache = {}
        self.openai_client = openai.OpenAI()
        
        print("✅ Command router initialized")
    
    def _initialize_routing_rules(self) -> List[RoutingRule]:
        """Initialize command routing rules"""
        return [
            # File Operations
            RoutingRule(
                keywords=["upload", "file", "document", "pdf", "analyze file", "process file"],
                patterns=[r"upload.*file", r"analyze.*document", r"process.*pdf"],
                command_type=CommandType.FILE_OPERATION,
                handler="file_processor",
                priority=9,
                required_permissions=["file_upload"]
            ),
            
            # Workflow Operations
            RoutingRule(
                keywords=["workflow", "execute workflow", "run workflow", "start workflow"],
                patterns=[r"execute.*workflow", r"run.*workflow", r"start.*workflow"],
                command_type=CommandType.WORKFLOW,
                handler="workflow_engine",
                priority=8,
                required_permissions=["workflow_execution"]
            ),
            
            # Tool Operations
            RoutingRule(
                keywords=["search", "weather", "scrape", "summarize", "command", "execute"],
                patterns=[r"search.*web", r"get.*weather", r"scrape.*url", r"summarize.*url"],
                command_type=CommandType.TOOL,
                handler="tool_router",
                priority=7,
                required_permissions=["tool_usage"]
            ),
            
            # System Operations
            RoutingRule(
                keywords=["system", "status", "health", "diagnostics", "logs", "users"],
                patterns=[r"system.*status", r"show.*logs", r"user.*management"],
                command_type=CommandType.SYSTEM,
                handler="system_handler",
                priority=6,
                required_permissions=["system_access"]
            ),
            
            # Plugin Operations
            RoutingRule(
                keywords=["plugin", "run plugin", "execute plugin"],
                patterns=[r"run.*plugin", r"execute.*plugin"],
                command_type=CommandType.PLUGIN,
                handler="plugin_sandbox",
                priority=5,
                required_permissions=["plugin_execution"]
            ),
            
            # Default Chat (lowest priority)
            RoutingRule(
                keywords=[],
                patterns=[],
                command_type=CommandType.CHAT,
                handler="chat_handler",
                priority=1,
                requires_auth=False
            )
        ]
    
    def route_command(self, message: str, user_id: str = None, context: Dict[str, Any] = None) -> CommandClassification:
        """Route a command to the appropriate handler"""
        try:
            # Check cache first
            cache_key = f"{message}:{user_id}"
            if cache_key in self.classification_cache:
                return self.classification_cache[cache_key]
            
            # Classify the command
            classification = self._classify_command(message, context or {})
            
            # Validate permissions if user provided
            if user_id and classification.command_type != CommandType.CHAT:
                if not self._check_permissions(user_id, classification):
                    # Fallback to chat if no permissions
                    classification = CommandClassification(
                        command_type=CommandType.CHAT,
                        confidence=1.0,
                        handler="chat_handler",
                        parameters={"original_message": message},
                        reasoning="Insufficient permissions for requested operation"
                    )
            
            # Cache the result
            self.classification_cache[cache_key] = classification
            
            # Log the routing decision
            if logging_service:
                logging_service.log_activity(
                    user_id or 'anonymous',
                    'command_routed',
                    {
                        'message': message[:100],  # Truncate for logging
                        'command_type': classification.command_type.value,
                        'handler': classification.handler,
                        'confidence': classification.confidence,
                        'reasoning': classification.reasoning
                    }
                )
            
            return classification
            
        except Exception as e:
            # Fallback to chat on any error
            return CommandClassification(
                command_type=CommandType.CHAT,
                confidence=1.0,
                handler="chat_handler",
                parameters={"original_message": message, "error": str(e)},
                reasoning=f"Error in routing: {str(e)}"
            )
    
    def _classify_command(self, message: str, context: Dict[str, Any]) -> CommandClassification:
        """Classify a command using keyword matching and LLM fallback"""
        message_lower = message.lower()
        
        # First, try keyword and pattern matching
        for rule in sorted(self.routing_rules, key=lambda x: x.priority, reverse=True):
            confidence = self._calculate_rule_confidence(message_lower, rule)
            
            if confidence > 0.7:  # High confidence threshold
                return CommandClassification(
                    command_type=rule.command_type,
                    confidence=confidence,
                    handler=rule.handler,
                    parameters=self._extract_parameters(message, rule),
                    reasoning=f"Keyword/pattern match with {confidence:.2f} confidence"
                )
        
        # If no high-confidence match, use LLM classification
        return self._llm_classify_command(message, context)
    
    def _calculate_rule_confidence(self, message: str, rule: RoutingRule) -> float:
        """Calculate confidence score for a routing rule"""
        if rule.command_type == CommandType.CHAT and not rule.keywords:
            return 0.1  # Default chat has low confidence
        
        keyword_score = 0.0
        pattern_score = 0.0
        
        # Check keywords
        if rule.keywords:
            keyword_matches = sum(1 for keyword in rule.keywords if keyword.lower() in message)
            keyword_score = keyword_matches / len(rule.keywords)
        
        # Check patterns
        if rule.patterns:
            pattern_matches = sum(1 for pattern in rule.patterns if re.search(pattern, message, re.IGNORECASE))
            pattern_score = pattern_matches / len(rule.patterns)
        
        # Combine scores
        if rule.keywords and rule.patterns:
            return (keyword_score + pattern_score) / 2
        elif rule.keywords:
            return keyword_score
        elif rule.patterns:
            return pattern_score
        else:
            return 0.0
    
    def _llm_classify_command(self, message: str, context: Dict[str, Any]) -> CommandClassification:
        """Use LLM to classify ambiguous commands"""
        try:
            system_prompt = """You are a command classifier for the Jarvis AI Assistant. 
            Classify the user's message into one of these categories:
            
            1. CHAT - General conversation, questions, or requests that should be handled by GPT
            2. TOOL - Requests to use specific tools (web search, weather, scraping, etc.)
            3. FILE_OPERATION - File uploads, document analysis, or file processing
            4. WORKFLOW - Workflow execution or automation requests
            5. SYSTEM - System status, diagnostics, user management, or administrative tasks
            6. PLUGIN - Plugin execution or custom functionality requests
            
            Respond with JSON in this format:
            {
                "command_type": "CHAT|TOOL|FILE_OPERATION|WORKFLOW|SYSTEM|PLUGIN",
                "confidence": 0.0-1.0,
                "reasoning": "Brief explanation of classification",
                "parameters": {"key": "value"}
            }
            
            If uncertain, default to CHAT with lower confidence."""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Classify this message: {message}"}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return CommandClassification(
                command_type=CommandType(result["command_type"].lower()),
                confidence=result["confidence"],
                handler=self._get_handler_for_type(CommandType(result["command_type"].lower())),
                parameters=result.get("parameters", {}),
                reasoning=f"LLM classification: {result['reasoning']}"
            )
            
        except Exception as e:
            # Fallback to chat on LLM error
            return CommandClassification(
                command_type=CommandType.CHAT,
                confidence=0.9,
                handler="chat_handler",
                parameters={"original_message": message},
                reasoning=f"LLM classification failed, defaulting to chat: {str(e)}"
            )
    
    def _get_handler_for_type(self, command_type: CommandType) -> str:
        """Get the appropriate handler for a command type"""
        handler_map = {
            CommandType.CHAT: "chat_handler",
            CommandType.TOOL: "tool_router",
            CommandType.FILE_OPERATION: "file_processor",
            CommandType.WORKFLOW: "workflow_engine",
            CommandType.WEBHOOK: "webhook_service",
            CommandType.PLUGIN: "plugin_sandbox",
            CommandType.SYSTEM: "system_handler"
        }
        return handler_map.get(command_type, "chat_handler")
    
    def _extract_parameters(self, message: str, rule: RoutingRule) -> Dict[str, Any]:
        """Extract parameters from message based on routing rule"""
        parameters = {"original_message": message}
        
        if rule.command_type == CommandType.TOOL:
            # Extract tool-specific parameters
            if "weather" in message.lower():
                # Extract location for weather
                location_match = re.search(r"weather.*?(?:in|for|at)\s+([^.!?]+)", message, re.IGNORECASE)
                if location_match:
                    parameters["location"] = location_match.group(1).strip()
            
            elif "search" in message.lower():
                # Extract search query
                search_match = re.search(r"search.*?(?:for|about)\s+([^.!?]+)", message, re.IGNORECASE)
                if search_match:
                    parameters["query"] = search_match.group(1).strip()
        
        elif rule.command_type == CommandType.WORKFLOW:
            # Extract workflow name
            workflow_match = re.search(r"(?:execute|run|start)\s+(?:workflow\s+)?([^.!?]+)", message, re.IGNORECASE)
            if workflow_match:
                parameters["workflow_name"] = workflow_match.group(1).strip()
        
        return parameters
    
    def _check_permissions(self, user_id: str, classification: CommandClassification) -> bool:
        """Check if user has permissions for the classified command"""
        try:
            # Find the routing rule for this classification
            rule = None
            for r in self.routing_rules:
                if r.command_type == classification.command_type and r.handler == classification.handler:
                    rule = r
                    break
            
            if not rule or not rule.requires_auth:
                return True
            
            # Check with user service if available
            try:
                from .user_service import user_service
                
                if rule.required_permissions:
                    for permission in rule.required_permissions:
                        if not user_service.has_permission(user_id, permission):
                            return False
                
                return True
                
            except ImportError:
                # If user service not available, allow all operations
                return True
                
        except Exception as e:
            print(f"Permission check error: {e}")
            return False
    
    def execute_command(self, classification: CommandClassification, user_id: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a classified command"""
        try:
            handler = classification.handler
            parameters = classification.parameters
            
            if handler == "chat_handler":
                return self._execute_chat(parameters, user_id, context)
            elif handler == "tool_router":
                return self._execute_tool(parameters, user_id, context)
            elif handler == "file_processor":
                return self._execute_file_operation(parameters, user_id, context)
            elif handler == "workflow_engine":
                return self._execute_workflow(parameters, user_id, context)
            elif handler == "system_handler":
                return self._execute_system_command(parameters, user_id, context)
            elif handler == "plugin_sandbox":
                return self._execute_plugin(parameters, user_id, context)
            else:
                return {
                    "success": False,
                    "error": f"Unknown handler: {handler}",
                    "fallback": "chat"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Command execution failed: {str(e)}",
                "fallback": "chat"
            }
    
    def _execute_chat(self, parameters: Dict[str, Any], user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute chat command (fallback to existing chat handler)"""
        return {
            "success": True,
            "type": "chat",
            "message": parameters.get("original_message", ""),
            "handler": "chat_handler"
        }
    
    def _execute_tool(self, parameters: Dict[str, Any], user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool command"""
        try:
            message = parameters.get("original_message", "")
            result = tool_router.route_query(message, user_id)
            
            return {
                "success": True,
                "type": "tool",
                "result": result,
                "handler": "tool_router"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "handler": "tool_router"
            }
    
    def _execute_file_operation(self, parameters: Dict[str, Any], user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file operation command"""
        return {
            "success": True,
            "type": "file_operation",
            "message": "File operations should be handled through the upload endpoint",
            "handler": "file_processor"
        }
    
    def _execute_workflow(self, parameters: Dict[str, Any], user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow command"""
        try:
            workflow_name = parameters.get("workflow_name")
            if not workflow_name:
                return {
                    "success": False,
                    "error": "No workflow name specified",
                    "handler": "workflow_engine"
                }
            
            # Execute workflow
            execution_id = workflow_engine.execute_workflow(workflow_name, context or {}, user_id)
            
            return {
                "success": True,
                "type": "workflow",
                "execution_id": execution_id,
                "workflow_name": workflow_name,
                "handler": "workflow_engine"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Workflow execution failed: {str(e)}",
                "handler": "workflow_engine"
            }
    
    def _execute_system_command(self, parameters: Dict[str, Any], user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute system command"""
        return {
            "success": True,
            "type": "system",
            "message": "System commands should be handled through specific API endpoints",
            "handler": "system_handler"
        }
    
    def _execute_plugin(self, parameters: Dict[str, Any], user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin command"""
        return {
            "success": True,
            "type": "plugin",
            "message": "Plugin execution not yet implemented",
            "handler": "plugin_sandbox"
        }
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get command routing statistics"""
        # Count classifications by type
        type_counts = {}
        for classification in self.classification_cache.values():
            command_type = classification.command_type.value
            type_counts[command_type] = type_counts.get(command_type, 0) + 1
        
        return {
            "total_classifications": len(self.classification_cache),
            "type_distribution": type_counts,
            "routing_rules": len(self.routing_rules),
            "cache_size": len(self.classification_cache)
        }
    
    def clear_cache(self):
        """Clear the classification cache"""
        self.classification_cache.clear()
    
    def add_routing_rule(self, rule: RoutingRule):
        """Add a new routing rule"""
        self.routing_rules.append(rule)
        self.routing_rules.sort(key=lambda x: x.priority, reverse=True)
    
    def remove_routing_rule(self, command_type: CommandType, handler: str):
        """Remove a routing rule"""
        self.routing_rules = [
            rule for rule in self.routing_rules
            if not (rule.command_type == command_type and rule.handler == handler)
        ]

# Global instance
command_router = CommandRouter()

