"""
Workflow Engine Service for Jarvis AI Assistant
Handles multi-step workflow execution with tool integration, decision branching, and external API calls.
"""

import os
import json
import yaml
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

# Import existing services
from .tool_router import tool_router
from .logging_service import logging_service
from .user_service import user_service

class WorkflowStepType(Enum):
    TOOL = "tool"
    API_CALL = "api_call"
    DECISION = "decision"
    FILE_OPERATION = "file_operation"
    PLUGIN = "plugin"
    DELAY = "delay"
    NOTIFICATION = "notification"

class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class WorkflowStep:
    """Individual workflow step definition"""
    id: str
    type: WorkflowStepType
    name: str
    config: Dict[str, Any]
    next_step: Optional[str] = None
    error_step: Optional[str] = None
    condition: Optional[str] = None

@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    id: str
    name: str
    description: str
    version: str
    steps: List[WorkflowStep]
    triggers: List[str]
    metadata: Dict[str, Any]

@dataclass
class WorkflowExecution:
    """Workflow execution instance"""
    id: str
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime]
    current_step: Optional[str]
    context: Dict[str, Any]
    results: Dict[str, Any]
    error_message: Optional[str]
    user_id: Optional[str]

class WorkflowEngine:
    """Main workflow engine for executing multi-step workflows"""
    
    def __init__(self):
        self.workflows_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'workflows')
        self.templates_dir = os.path.join(self.workflows_dir, 'templates')
        self.active_dir = os.path.join(self.workflows_dir, 'active')
        self.logs_dir = os.path.join(self.workflows_dir, 'logs')
        
        # Ensure directories exist
        os.makedirs(self.workflows_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.active_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # In-memory storage for active executions
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        
        # Load existing workflows
        self._load_workflows()
        
        print("✅ Workflow engine initialized")
    
    def _load_workflows(self):
        """Load workflow definitions from files"""
        try:
            # Load templates
            for filename in os.listdir(self.templates_dir):
                if filename.endswith(('.yaml', '.yml', '.json')):
                    filepath = os.path.join(self.templates_dir, filename)
                    workflow = self._load_workflow_file(filepath)
                    if workflow:
                        self.workflow_definitions[workflow.id] = workflow
            
            # Load active workflows
            for filename in os.listdir(self.active_dir):
                if filename.endswith(('.yaml', '.yml', '.json')):
                    filepath = os.path.join(self.active_dir, filename)
                    workflow = self._load_workflow_file(filepath)
                    if workflow:
                        self.workflow_definitions[workflow.id] = workflow
                        
            print(f"✅ Loaded {len(self.workflow_definitions)} workflow definitions")
        except Exception as e:
            print(f"Error loading workflows: {e}")
    
    def _load_workflow_file(self, filepath: str) -> Optional[WorkflowDefinition]:
        """Load a single workflow file"""
        try:
            with open(filepath, 'r') as f:
                if filepath.endswith('.json'):
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)
            
            return self._parse_workflow_definition(data)
        except Exception as e:
            print(f"Error loading workflow file {filepath}: {e}")
            return None
    
    def _parse_workflow_definition(self, data: Dict[str, Any]) -> WorkflowDefinition:
        """Parse workflow definition from data"""
        steps = []
        for step_data in data.get('steps', []):
            step = WorkflowStep(
                id=step_data['id'],
                type=WorkflowStepType(step_data['type']),
                name=step_data['name'],
                config=step_data.get('config', {}),
                next_step=step_data.get('next_step'),
                error_step=step_data.get('error_step'),
                condition=step_data.get('condition')
            )
            steps.append(step)
        
        return WorkflowDefinition(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            steps=steps,
            triggers=data.get('triggers', []),
            metadata=data.get('metadata', {})
        )
    
    async def execute_workflow(self, workflow_id: str, context: Dict[str, Any] = None, user_id: str = None) -> str:
        """Execute a workflow and return execution ID"""
        if workflow_id not in self.workflow_definitions:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflow_definitions[workflow_id]
        execution_id = f"{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING,
            started_at=datetime.now(),
            completed_at=None,
            current_step=workflow.steps[0].id if workflow.steps else None,
            context=context or {},
            results={},
            error_message=None,
            user_id=user_id
        )
        
        self.active_executions[execution_id] = execution
        
        # Log workflow start
        logging_service.log_activity(
            user_id or 'system',
            'workflow_started',
            {
                'workflow_id': workflow_id,
                'execution_id': execution_id,
                'workflow_name': workflow.name
            }
        )
        
        # Start execution asynchronously
        asyncio.create_task(self._execute_workflow_async(execution))
        
        return execution_id
    
    async def _execute_workflow_async(self, execution: WorkflowExecution):
        """Execute workflow steps asynchronously"""
        try:
            execution.status = WorkflowStatus.RUNNING
            workflow = self.workflow_definitions[execution.workflow_id]
            
            current_step_id = execution.current_step
            
            while current_step_id:
                step = self._find_step(workflow, current_step_id)
                if not step:
                    raise ValueError(f"Step {current_step_id} not found")
                
                execution.current_step = current_step_id
                
                try:
                    # Execute the step
                    result = await self._execute_step(step, execution)
                    execution.results[step.id] = result
                    
                    # Determine next step
                    if step.condition and not self._evaluate_condition(step.condition, execution.context, result):
                        current_step_id = step.error_step
                    else:
                        current_step_id = step.next_step
                        
                except Exception as step_error:
                    execution.results[step.id] = {'error': str(step_error)}
                    current_step_id = step.error_step
                    
                    if not current_step_id:
                        raise step_error
            
            # Workflow completed successfully
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now()
            
            # Log completion
            logging_service.log_activity(
                execution.user_id or 'system',
                'workflow_completed',
                {
                    'workflow_id': execution.workflow_id,
                    'execution_id': execution.id,
                    'duration_seconds': (execution.completed_at - execution.started_at).total_seconds(),
                    'steps_executed': len(execution.results)
                }
            )
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            
            # Log failure
            logging_service.log_activity(
                execution.user_id or 'system',
                'workflow_failed',
                {
                    'workflow_id': execution.workflow_id,
                    'execution_id': execution.id,
                    'error': str(e),
                    'current_step': execution.current_step
                }
            )
        
        # Save execution log
        self._save_execution_log(execution)
    
    def _find_step(self, workflow: WorkflowDefinition, step_id: str) -> Optional[WorkflowStep]:
        """Find a step by ID in the workflow"""
        for step in workflow.steps:
            if step.id == step_id:
                return step
        return None
    
    async def _execute_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a single workflow step"""
        if step.type == WorkflowStepType.TOOL:
            return await self._execute_tool_step(step, execution)
        elif step.type == WorkflowStepType.API_CALL:
            return await self._execute_api_step(step, execution)
        elif step.type == WorkflowStepType.DECISION:
            return await self._execute_decision_step(step, execution)
        elif step.type == WorkflowStepType.FILE_OPERATION:
            return await self._execute_file_step(step, execution)
        elif step.type == WorkflowStepType.PLUGIN:
            return await self._execute_plugin_step(step, execution)
        elif step.type == WorkflowStepType.DELAY:
            return await self._execute_delay_step(step, execution)
        elif step.type == WorkflowStepType.NOTIFICATION:
            return await self._execute_notification_step(step, execution)
        else:
            raise ValueError(f"Unknown step type: {step.type}")
    
    async def _execute_tool_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a tool step using the existing tool router"""
        tool_name = step.config.get('tool_name')
        query = step.config.get('query', '')
        
        # Replace variables in query
        query = self._replace_variables(query, execution.context, execution.results)
        
        # Use tool router to execute
        result = tool_router.route_query(query, execution.user_id)
        
        return {
            'tool_name': tool_name,
            'query': query,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _execute_api_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute an API call step"""
        url = self._replace_variables(step.config.get('url', ''), execution.context, execution.results)
        method = step.config.get('method', 'GET').upper()
        headers = step.config.get('headers', {})
        payload = step.config.get('payload', {})
        
        # Replace variables in headers and payload
        headers = self._replace_variables_in_dict(headers, execution.context, execution.results)
        payload = self._replace_variables_in_dict(payload, execution.context, execution.results)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=payload, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=payload, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            return {
                'url': url,
                'method': method,
                'status_code': response.status_code,
                'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'url': url,
                'method': method,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _execute_decision_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a decision step"""
        condition = step.config.get('condition', '')
        result = self._evaluate_condition(condition, execution.context, execution.results)
        
        return {
            'condition': condition,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _execute_file_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a file operation step"""
        operation = step.config.get('operation', 'read')
        filepath = self._replace_variables(step.config.get('filepath', ''), execution.context, execution.results)
        
        try:
            if operation == 'read':
                with open(filepath, 'r') as f:
                    content = f.read()
                return {
                    'operation': operation,
                    'filepath': filepath,
                    'content': content,
                    'timestamp': datetime.now().isoformat()
                }
            elif operation == 'write':
                content = self._replace_variables(step.config.get('content', ''), execution.context, execution.results)
                with open(filepath, 'w') as f:
                    f.write(content)
                return {
                    'operation': operation,
                    'filepath': filepath,
                    'bytes_written': len(content),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                raise ValueError(f"Unsupported file operation: {operation}")
                
        except Exception as e:
            return {
                'operation': operation,
                'filepath': filepath,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _execute_plugin_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a plugin step"""
        plugin_name = step.config.get('plugin_name')
        plugin_args = step.config.get('args', {})
        
        # Replace variables in plugin args
        plugin_args = self._replace_variables_in_dict(plugin_args, execution.context, execution.results)
        
        # TODO: Implement plugin execution system
        return {
            'plugin_name': plugin_name,
            'args': plugin_args,
            'result': 'Plugin execution not yet implemented',
            'timestamp': datetime.now().isoformat()
        }
    
    async def _execute_delay_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a delay step"""
        delay_seconds = step.config.get('seconds', 1)
        await asyncio.sleep(delay_seconds)
        
        return {
            'delay_seconds': delay_seconds,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _execute_notification_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a notification step"""
        message = self._replace_variables(step.config.get('message', ''), execution.context, execution.results)
        notification_type = step.config.get('type', 'log')
        
        if notification_type == 'log':
            logging_service.log_activity(
                execution.user_id or 'system',
                'workflow_notification',
                {'message': message, 'workflow_id': execution.workflow_id}
            )
        
        return {
            'type': notification_type,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any], results: Dict[str, Any]) -> bool:
        """Evaluate a condition string"""
        try:
            # Simple condition evaluation - can be enhanced
            condition = self._replace_variables(condition, context, results)
            
            # Basic condition parsing
            if 'contains' in condition:
                parts = condition.split('contains')
                if len(parts) == 2:
                    value = parts[0].strip().strip('"\'')
                    search_term = parts[1].strip().strip('"\'')
                    return search_term in value
            
            # Add more condition types as needed
            return eval(condition)  # Use with caution in production
            
        except Exception:
            return False
    
    def _replace_variables(self, text: str, context: Dict[str, Any], results: Dict[str, Any]) -> str:
        """Replace variables in text with values from context and results"""
        if not isinstance(text, str):
            return text
        
        # Replace context variables
        for key, value in context.items():
            text = text.replace(f"{{context.{key}}}", str(value))
        
        # Replace result variables
        for step_id, result in results.items():
            if isinstance(result, dict):
                for key, value in result.items():
                    text = text.replace(f"{{results.{step_id}.{key}}}", str(value))
        
        return text
    
    def _replace_variables_in_dict(self, data: Dict[str, Any], context: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """Replace variables in dictionary values"""
        if not isinstance(data, dict):
            return data
        
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._replace_variables(value, context, results)
            elif isinstance(value, dict):
                result[key] = self._replace_variables_in_dict(value, context, results)
            else:
                result[key] = value
        
        return result
    
    def _save_execution_log(self, execution: WorkflowExecution):
        """Save execution log to file"""
        try:
            log_file = os.path.join(self.logs_dir, f"{execution.id}.json")
            log_data = {
                'id': execution.id,
                'workflow_id': execution.workflow_id,
                'status': execution.status.value,
                'started_at': execution.started_at.isoformat(),
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'context': execution.context,
                'results': execution.results,
                'error_message': execution.error_message,
                'user_id': execution.user_id
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving execution log: {e}")
    
    def get_workflow_definitions(self) -> List[Dict[str, Any]]:
        """Get all workflow definitions"""
        return [
            {
                'id': workflow.id,
                'name': workflow.name,
                'description': workflow.description,
                'version': workflow.version,
                'steps_count': len(workflow.steps),
                'triggers': workflow.triggers,
                'metadata': workflow.metadata
            }
            for workflow in self.workflow_definitions.values()
        ]
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status"""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return None
        
        return {
            'id': execution.id,
            'workflow_id': execution.workflow_id,
            'status': execution.status.value,
            'started_at': execution.started_at.isoformat(),
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'current_step': execution.current_step,
            'progress': len(execution.results),
            'error_message': execution.error_message
        }
    
    def get_execution_results(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution results"""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return None
        
        return {
            'id': execution.id,
            'workflow_id': execution.workflow_id,
            'status': execution.status.value,
            'results': execution.results,
            'context': execution.context
        }

# Global instance
workflow_engine = WorkflowEngine()

