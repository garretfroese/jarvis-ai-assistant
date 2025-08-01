"""
Advanced Workflow Management Service
Implements complex autonomous workflows, goal decomposition, and intelligent task orchestration
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from src.services.autonomy_service import autonomy_engine, memory_manager, job_scheduler
from src.services.github_service import github_service
from src.services.railway_service import railway_service, cicd_pipeline

class WorkflowEngine:
    """Advanced workflow engine for autonomous task orchestration"""
    
    def __init__(self):
        self.autonomy_engine = autonomy_engine
        self.memory_manager = memory_manager
        self.job_scheduler = job_scheduler
    
    def create_workflow(self, goal: str, context: Dict = None) -> str:
        """Create a new autonomous workflow"""
        try:
            workflow_id = f"workflow_{uuid.uuid4().hex[:12]}"
            
            # Decompose goal into steps
            steps = self.decompose_goal(goal, context or {})
            
            workflow = {
                'id': workflow_id,
                'goal': goal,
                'context': context or {},
                'steps': steps,
                'status': 'created',
                'current_step': 0,
                'progress': 0,
                'created_at': datetime.utcnow().isoformat(),
                'estimated_duration': self.estimate_duration(steps)
            }
            
            # Store workflow in memory
            self.memory_manager.store(f"workflow:{workflow_id}", workflow, category='workflows')
            
            # Create autonomy session
            session_id = self.autonomy_engine.create_autonomy_session(goal, {
                'workflow_id': workflow_id,
                'total_steps': len(steps)
            })
            
            workflow['session_id'] = session_id
            self.memory_manager.store(f"workflow:{workflow_id}", workflow, category='workflows')
            
            return workflow_id
            
        except Exception as e:
            print(f"Workflow creation error: {e}")
            return None
    
    def decompose_goal(self, goal: str, context: Dict) -> List[Dict]:
        """Decompose high-level goal into executable steps"""
        try:
            # Analyze goal to determine workflow type
            goal_lower = goal.lower()
            
            if 'deploy' in goal_lower and ('app' in goal_lower or 'code' in goal_lower):
                return self.create_deployment_workflow(goal, context)
            elif 'create' in goal_lower and ('project' in goal_lower or 'app' in goal_lower):
                return self.create_project_workflow(goal, context)
            elif 'analyze' in goal_lower or 'research' in goal_lower:
                return self.create_analysis_workflow(goal, context)
            elif 'automate' in goal_lower or 'schedule' in goal_lower:
                return self.create_automation_workflow(goal, context)
            else:
                return self.create_generic_workflow(goal, context)
                
        except Exception as e:
            print(f"Goal decomposition error: {e}")
            return self.create_generic_workflow(goal, context)
    
    def create_deployment_workflow(self, goal: str, context: Dict) -> List[Dict]:
        """Create deployment workflow steps"""
        return [
            {
                'id': 1,
                'name': 'Analyze Requirements',
                'command': 'analyze_deployment_requirements',
                'parameters': {'goal': goal, 'context': context},
                'estimated_duration': 60,
                'dependencies': []
            },
            {
                'id': 2,
                'name': 'Generate Code',
                'command': 'generate_application_code',
                'parameters': {'requirements': '${step_1_result}'},
                'estimated_duration': 180,
                'dependencies': [1]
            },
            {
                'id': 3,
                'name': 'Create Repository',
                'command': 'github_create_repo',
                'parameters': {
                    'repo_name': context.get('repo_name', 'jarvis-auto-deploy'),
                    'description': f'Auto-generated project: {goal}'
                },
                'estimated_duration': 30,
                'dependencies': []
            },
            {
                'id': 4,
                'name': 'Deploy to GitHub',
                'command': 'github_deploy',
                'parameters': {
                    'code': '${step_2_result}',
                    'file_path': 'app.py',
                    'commit_message': f'Jarvis: {goal}'
                },
                'estimated_duration': 45,
                'dependencies': [2, 3]
            },
            {
                'id': 5,
                'name': 'Deploy to Railway',
                'command': 'railway_deploy',
                'parameters': {
                    'repo_name': context.get('repo_name', 'jarvis-auto-deploy')
                },
                'estimated_duration': 120,
                'dependencies': [4]
            },
            {
                'id': 6,
                'name': 'Verify Deployment',
                'command': 'verify_deployment',
                'parameters': {'deployment_id': '${step_5_result.deployment_id}'},
                'estimated_duration': 60,
                'dependencies': [5]
            }
        ]
    
    def create_project_workflow(self, goal: str, context: Dict) -> List[Dict]:
        """Create project creation workflow steps"""
        return [
            {
                'id': 1,
                'name': 'Define Project Structure',
                'command': 'define_project_structure',
                'parameters': {'goal': goal, 'context': context},
                'estimated_duration': 90,
                'dependencies': []
            },
            {
                'id': 2,
                'name': 'Generate Core Files',
                'command': 'generate_project_files',
                'parameters': {'structure': '${step_1_result}'},
                'estimated_duration': 240,
                'dependencies': [1]
            },
            {
                'id': 3,
                'name': 'Create Documentation',
                'command': 'generate_documentation',
                'parameters': {'project_info': '${step_1_result}'},
                'estimated_duration': 120,
                'dependencies': [1]
            },
            {
                'id': 4,
                'name': 'Setup Repository',
                'command': 'setup_project_repository',
                'parameters': {
                    'files': '${step_2_result}',
                    'docs': '${step_3_result}'
                },
                'estimated_duration': 60,
                'dependencies': [2, 3]
            },
            {
                'id': 5,
                'name': 'Configure CI/CD',
                'command': 'setup_cicd_pipeline',
                'parameters': {'repo_name': '${step_4_result.repo_name}'},
                'estimated_duration': 90,
                'dependencies': [4]
            }
        ]
    
    def create_analysis_workflow(self, goal: str, context: Dict) -> List[Dict]:
        """Create analysis workflow steps"""
        return [
            {
                'id': 1,
                'name': 'Gather Data',
                'command': 'gather_analysis_data',
                'parameters': {'goal': goal, 'context': context},
                'estimated_duration': 120,
                'dependencies': []
            },
            {
                'id': 2,
                'name': 'Process Data',
                'command': 'process_analysis_data',
                'parameters': {'data': '${step_1_result}'},
                'estimated_duration': 180,
                'dependencies': [1]
            },
            {
                'id': 3,
                'name': 'Generate Insights',
                'command': 'generate_insights',
                'parameters': {'processed_data': '${step_2_result}'},
                'estimated_duration': 150,
                'dependencies': [2]
            },
            {
                'id': 4,
                'name': 'Create Report',
                'command': 'create_analysis_report',
                'parameters': {'insights': '${step_3_result}'},
                'estimated_duration': 120,
                'dependencies': [3]
            }
        ]
    
    def create_automation_workflow(self, goal: str, context: Dict) -> List[Dict]:
        """Create automation workflow steps"""
        return [
            {
                'id': 1,
                'name': 'Identify Automation Opportunities',
                'command': 'identify_automation_targets',
                'parameters': {'goal': goal, 'context': context},
                'estimated_duration': 90,
                'dependencies': []
            },
            {
                'id': 2,
                'name': 'Design Automation Logic',
                'command': 'design_automation_logic',
                'parameters': {'targets': '${step_1_result}'},
                'estimated_duration': 180,
                'dependencies': [1]
            },
            {
                'id': 3,
                'name': 'Implement Automation',
                'command': 'implement_automation',
                'parameters': {'logic': '${step_2_result}'},
                'estimated_duration': 240,
                'dependencies': [2]
            },
            {
                'id': 4,
                'name': 'Test Automation',
                'command': 'test_automation',
                'parameters': {'implementation': '${step_3_result}'},
                'estimated_duration': 120,
                'dependencies': [3]
            },
            {
                'id': 5,
                'name': 'Deploy Automation',
                'command': 'deploy_automation',
                'parameters': {'tested_automation': '${step_4_result}'},
                'estimated_duration': 90,
                'dependencies': [4]
            }
        ]
    
    def create_generic_workflow(self, goal: str, context: Dict) -> List[Dict]:
        """Create generic workflow for unknown goal types"""
        return [
            {
                'id': 1,
                'name': 'Analyze Goal',
                'command': 'analyze_goal',
                'parameters': {'goal': goal, 'context': context},
                'estimated_duration': 60,
                'dependencies': []
            },
            {
                'id': 2,
                'name': 'Plan Execution',
                'command': 'plan_execution',
                'parameters': {'analysis': '${step_1_result}'},
                'estimated_duration': 90,
                'dependencies': [1]
            },
            {
                'id': 3,
                'name': 'Execute Plan',
                'command': 'execute_plan',
                'parameters': {'plan': '${step_2_result}'},
                'estimated_duration': 180,
                'dependencies': [2]
            },
            {
                'id': 4,
                'name': 'Verify Results',
                'command': 'verify_results',
                'parameters': {'execution_result': '${step_3_result}'},
                'estimated_duration': 60,
                'dependencies': [3]
            }
        ]
    
    def estimate_duration(self, steps: List[Dict]) -> int:
        """Estimate total workflow duration in seconds"""
        return sum(step.get('estimated_duration', 60) for step in steps)
    
    def execute_workflow(self, workflow_id: str) -> bool:
        """Execute workflow autonomously"""
        try:
            workflow = self.memory_manager.retrieve(f"workflow:{workflow_id}")
            if not workflow:
                return False
            
            workflow['status'] = 'running'
            workflow['started_at'] = datetime.utcnow().isoformat()
            self.memory_manager.store(f"workflow:{workflow_id}", workflow, category='workflows')
            
            # Schedule first step
            first_steps = [step for step in workflow['steps'] if not step.get('dependencies')]
            for step in first_steps:
                self.schedule_workflow_step(workflow_id, step)
            
            return True
            
        except Exception as e:
            print(f"Workflow execution error: {e}")
            return False
    
    def schedule_workflow_step(self, workflow_id: str, step: Dict) -> str:
        """Schedule a workflow step for execution"""
        try:
            job_id = self.job_scheduler.schedule_job(
                command=step['command'],
                parameters={
                    **step['parameters'],
                    'workflow_id': workflow_id,
                    'step_id': step['id']
                },
                job_type='workflow_step',
                priority=2
            )
            
            # Store step execution info
            step_info = {
                'job_id': job_id,
                'status': 'scheduled',
                'scheduled_at': datetime.utcnow().isoformat()
            }
            
            self.memory_manager.store(
                f"workflow:{workflow_id}:step:{step['id']}", 
                step_info, 
                category='workflow_steps'
            )
            
            return job_id
            
        except Exception as e:
            print(f"Step scheduling error: {e}")
            return None
    
    def complete_workflow_step(self, workflow_id: str, step_id: int, result: Dict) -> bool:
        """Complete a workflow step and trigger dependent steps"""
        try:
            workflow = self.memory_manager.retrieve(f"workflow:{workflow_id}")
            if not workflow:
                return False
            
            # Update step status
            step_info = self.memory_manager.retrieve(f"workflow:{workflow_id}:step:{step_id}")
            step_info['status'] = 'completed'
            step_info['completed_at'] = datetime.utcnow().isoformat()
            step_info['result'] = result
            
            self.memory_manager.store(
                f"workflow:{workflow_id}:step:{step_id}", 
                step_info, 
                category='workflow_steps'
            )
            
            # Update workflow progress
            completed_steps = workflow['current_step'] + 1
            total_steps = len(workflow['steps'])
            progress = int((completed_steps / total_steps) * 100)
            
            workflow['current_step'] = completed_steps
            workflow['progress'] = progress
            
            if progress >= 100:
                workflow['status'] = 'completed'
                workflow['completed_at'] = datetime.utcnow().isoformat()
            
            self.memory_manager.store(f"workflow:{workflow_id}", workflow, category='workflows')
            
            # Update autonomy session
            if 'session_id' in workflow:
                self.autonomy_engine.update_session_progress(
                    workflow['session_id'], 
                    progress, 
                    f"Completed step {step_id}"
                )
            
            # Schedule dependent steps
            if progress < 100:
                self.schedule_dependent_steps(workflow_id, step_id)
            
            return True
            
        except Exception as e:
            print(f"Step completion error: {e}")
            return False
    
    def schedule_dependent_steps(self, workflow_id: str, completed_step_id: int) -> None:
        """Schedule steps that depend on the completed step"""
        try:
            workflow = self.memory_manager.retrieve(f"workflow:{workflow_id}")
            if not workflow:
                return
            
            # Find steps that depend on the completed step
            for step in workflow['steps']:
                dependencies = step.get('dependencies', [])
                if completed_step_id in dependencies:
                    # Check if all dependencies are completed
                    all_deps_completed = True
                    for dep_id in dependencies:
                        dep_info = self.memory_manager.retrieve(f"workflow:{workflow_id}:step:{dep_id}")
                        if not dep_info or dep_info.get('status') != 'completed':
                            all_deps_completed = False
                            break
                    
                    if all_deps_completed:
                        # Resolve parameter variables
                        resolved_params = self.resolve_step_parameters(workflow_id, step['parameters'])
                        step['parameters'] = resolved_params
                        
                        self.schedule_workflow_step(workflow_id, step)
            
        except Exception as e:
            print(f"Dependent step scheduling error: {e}")
    
    def resolve_step_parameters(self, workflow_id: str, parameters: Dict) -> Dict:
        """Resolve parameter variables from previous step results"""
        try:
            resolved = {}
            
            for key, value in parameters.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    # Extract variable reference
                    var_ref = value[2:-1]  # Remove ${ and }
                    
                    if var_ref.startswith('step_') and '_result' in var_ref:
                        # Extract step ID
                        step_id = int(var_ref.split('_')[1])
                        
                        # Get step result
                        step_info = self.memory_manager.retrieve(f"workflow:{workflow_id}:step:{step_id}")
                        if step_info and 'result' in step_info:
                            if '.' in var_ref:
                                # Handle nested property access
                                prop_path = var_ref.split('.', 1)[1]
                                resolved[key] = self.get_nested_property(step_info['result'], prop_path)
                            else:
                                resolved[key] = step_info['result']
                        else:
                            resolved[key] = None
                    else:
                        resolved[key] = value
                else:
                    resolved[key] = value
            
            return resolved
            
        except Exception as e:
            print(f"Parameter resolution error: {e}")
            return parameters
    
    def get_nested_property(self, obj: Any, path: str) -> Any:
        """Get nested property from object using dot notation"""
        try:
            keys = path.split('.')
            current = obj
            
            for key in keys:
                if isinstance(current, dict):
                    current = current.get(key)
                else:
                    return None
                
                if current is None:
                    return None
            
            return current
            
        except Exception:
            return None
    
    def get_workflow_status(self, workflow_id: str) -> Dict:
        """Get workflow status and progress"""
        try:
            workflow = self.memory_manager.retrieve(f"workflow:{workflow_id}")
            if not workflow:
                return {'error': 'Workflow not found'}
            
            # Get step statuses
            steps_status = []
            for step in workflow['steps']:
                step_info = self.memory_manager.retrieve(f"workflow:{workflow_id}:step:{step['id']}")
                steps_status.append({
                    'id': step['id'],
                    'name': step['name'],
                    'status': step_info.get('status', 'pending') if step_info else 'pending',
                    'result': step_info.get('result') if step_info else None
                })
            
            return {
                'workflow': workflow,
                'steps': steps_status
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        try:
            workflow = self.memory_manager.retrieve(f"workflow:{workflow_id}")
            if not workflow:
                return False
            
            workflow['status'] = 'cancelled'
            workflow['cancelled_at'] = datetime.utcnow().isoformat()
            
            self.memory_manager.store(f"workflow:{workflow_id}", workflow, category='workflows')
            
            return True
            
        except Exception as e:
            print(f"Workflow cancellation error: {e}")
            return False

class GoalDecomposer:
    """Advanced goal decomposition and planning"""
    
    @staticmethod
    def analyze_goal_complexity(goal: str) -> Dict:
        """Analyze goal complexity and requirements"""
        complexity_indicators = {
            'simple': ['get', 'show', 'list', 'check'],
            'medium': ['create', 'update', 'deploy', 'setup'],
            'complex': ['build', 'develop', 'analyze', 'optimize', 'automate']
        }
        
        goal_lower = goal.lower()
        complexity = 'simple'
        
        for level, indicators in complexity_indicators.items():
            if any(indicator in goal_lower for indicator in indicators):
                complexity = level
        
        return {
            'complexity': complexity,
            'estimated_steps': {'simple': 2, 'medium': 4, 'complex': 6}[complexity],
            'estimated_duration': {'simple': 300, 'medium': 900, 'complex': 1800}[complexity],
            'requires_external_apis': any(service in goal_lower for service in ['github', 'railway', 'slack', 'email']),
            'requires_code_generation': any(term in goal_lower for term in ['code', 'app', 'script', 'program']),
            'requires_deployment': any(term in goal_lower for term in ['deploy', 'publish', 'launch'])
        }

# Global instance
workflow_engine = WorkflowEngine()
goal_decomposer = GoalDecomposer()

