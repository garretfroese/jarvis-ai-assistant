"""
Intelligent Tool Router for Jarvis
Routes user queries to the most appropriate tool based on confidence scoring
"""

import os
import sys
import importlib.util
from typing import Dict, List, Tuple, Optional
import re

# Add the tools directory to the path
tools_dir = os.path.join(os.path.dirname(__file__), '..', 'tools')
if tools_dir not in sys.path:
    sys.path.append(tools_dir)

class ToolRouter:
    def __init__(self):
        self.tools = {}
        self.confidence_functions = {}
        self.load_tools()
    
    def load_tools(self):
        """Load all available tools and their confidence functions"""
        tools_directory = os.path.join(os.path.dirname(__file__), '..', 'tools')
        
        if not os.path.exists(tools_directory):
            print(f"Tools directory not found: {tools_directory}")
            return
        
        # Load each tool
        for filename in os.listdir(tools_directory):
            if filename.endswith('.py') and not filename.startswith('__'):
                tool_name = filename[:-3]  # Remove .py extension
                self.load_tool(tool_name, tools_directory)
    
    def load_tool(self, tool_name: str, tools_directory: str):
        """Load a specific tool and its confidence function"""
        try:
            tool_path = os.path.join(tools_directory, f"{tool_name}.py")
            
            # Load the module
            spec = importlib.util.spec_from_file_location(tool_name, tool_path)
            if spec is None or spec.loader is None:
                print(f"Failed to load tool: {tool_name}")
                return
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Store the tool
            self.tools[tool_name] = {
                'module': module,
                'run': getattr(module, 'run', None),
                'manifest': getattr(module, 'manifest', {}),
                'enabled': getattr(module, 'manifest', {}).get('enabled', True)
            }
            
            # Look for confidence function
            confidence_func_name = f"get_{tool_name.replace('_', '')}_confidence"
            if hasattr(module, confidence_func_name):
                self.confidence_functions[tool_name] = getattr(module, confidence_func_name)
            elif hasattr(module, 'get_confidence'):
                self.confidence_functions[tool_name] = getattr(module, 'get_confidence')
            else:
                # Create a default confidence function
                self.confidence_functions[tool_name] = self.create_default_confidence_function(tool_name)
            
            print(f"Loaded tool: {tool_name}")
            
        except Exception as e:
            print(f"Error loading tool {tool_name}: {str(e)}")
    
    def create_default_confidence_function(self, tool_name: str):
        """Create a default confidence function based on tool name"""
        def default_confidence(input_text: str) -> float:
            # Simple keyword matching based on tool name
            keywords = tool_name.replace('_', ' ').split()
            input_lower = input_text.lower()
            
            confidence = 0.0
            for keyword in keywords:
                if keyword in input_lower:
                    confidence += 0.3
            
            return min(confidence, 1.0)
        
        return default_confidence
    
    def route_query(self, input_text: str, threshold: float = 0.3) -> Tuple[Optional[str], float, Dict]:
        """
        Route a query to the most appropriate tool
        
        Args:
            input_text (str): User input to route
            threshold (float): Minimum confidence threshold
            
        Returns:
            Tuple of (tool_name, confidence, routing_info)
        """
        if not input_text.strip():
            return None, 0.0, {'error': 'Empty input'}
        
        # Calculate confidence for each tool
        tool_scores = {}
        
        for tool_name, tool_info in self.tools.items():
            if not tool_info.get('enabled', True):
                continue
            
            if tool_name in self.confidence_functions:
                try:
                    confidence = self.confidence_functions[tool_name](input_text)
                    tool_scores[tool_name] = confidence
                except Exception as e:
                    print(f"Error calculating confidence for {tool_name}: {str(e)}")
                    tool_scores[tool_name] = 0.0
        
        # Find the best tool
        if not tool_scores:
            return None, 0.0, {'error': 'No tools available'}
        
        best_tool = max(tool_scores.items(), key=lambda x: x[1])
        best_tool_name, best_confidence = best_tool
        
        # Check if confidence meets threshold
        if best_confidence < threshold:
            return None, best_confidence, {
                'reason': 'No tool meets confidence threshold',
                'threshold': threshold,
                'best_tool': best_tool_name,
                'best_confidence': best_confidence,
                'all_scores': tool_scores
            }
        
        return best_tool_name, best_confidence, {
            'all_scores': tool_scores,
            'threshold': threshold
        }
    
    def execute_tool(self, tool_name: str, input_text: str, **kwargs) -> Dict:
        """
        Execute a specific tool
        
        Args:
            tool_name (str): Name of the tool to execute
            input_text (str): Input for the tool
            **kwargs: Additional arguments
            
        Returns:
            Dict with execution result
        """
        if tool_name not in self.tools:
            return {
                'success': False,
                'error': f"Tool '{tool_name}' not found",
                'output': None
            }
        
        tool_info = self.tools[tool_name]
        
        if not tool_info.get('enabled', True):
            return {
                'success': False,
                'error': f"Tool '{tool_name}' is disabled",
                'output': None
            }
        
        run_function = tool_info.get('run')
        if not run_function:
            return {
                'success': False,
                'error': f"Tool '{tool_name}' has no run function",
                'output': None
            }
        
        try:
            start_time = datetime.now()
            result = run_function(input_text, **kwargs)
            end_time = datetime.now()
            
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                'success': True,
                'error': None,
                'output': str(result) if result is not None else None,
                'tool_name': tool_name,
                'duration_ms': duration_ms,
                'executed_at': end_time.isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error executing tool '{tool_name}': {str(e)}",
                'output': None,
                'tool_name': tool_name
            }
    
    def route_and_execute(self, input_text: str, threshold: float = 0.3, **kwargs) -> Dict:
        """
        Route a query and execute the best tool
        
        Args:
            input_text (str): User input
            threshold (float): Confidence threshold
            **kwargs: Additional arguments for tool execution
            
        Returns:
            Dict with routing and execution results
        """
        # Route the query
        tool_name, confidence, routing_info = self.route_query(input_text, threshold)
        
        result = {
            'routed_to_tool': tool_name is not None,
            'tool_name': tool_name,
            'confidence': confidence,
            'routing_info': routing_info
        }
        
        # Execute if we found a suitable tool
        if tool_name:
            execution_result = self.execute_tool(tool_name, input_text, **kwargs)
            result.update(execution_result)
        else:
            result.update({
                'success': False,
                'error': 'No suitable tool found',
                'output': None,
                'fallback_to_gpt': True
            })
        
        return result
    
    def get_available_tools(self) -> List[Dict]:
        """Get list of available tools"""
        tools_list = []
        
        for tool_name, tool_info in self.tools.items():
            manifest = tool_info.get('manifest', {})
            tools_list.append({
                'name': tool_name,
                'display_name': manifest.get('name', tool_name),
                'description': manifest.get('description', ''),
                'category': manifest.get('category', 'general'),
                'tags': manifest.get('tags', []),
                'enabled': tool_info.get('enabled', True),
                'requires_auth': manifest.get('requires_auth', False)
            })
        
        return tools_list
    
    def enable_tool(self, tool_name: str) -> bool:
        """Enable a tool"""
        if tool_name in self.tools:
            self.tools[tool_name]['enabled'] = True
            return True
        return False
    
    def disable_tool(self, tool_name: str) -> bool:
        """Disable a tool"""
        if tool_name in self.tools:
            self.tools[tool_name]['enabled'] = False
            return True
        return False
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict]:
        """Get information about a specific tool"""
        if tool_name not in self.tools:
            return None
        
        tool_info = self.tools[tool_name]
        manifest = tool_info.get('manifest', {})
        
        return {
            'name': tool_name,
            'display_name': manifest.get('name', tool_name),
            'description': manifest.get('description', ''),
            'version': manifest.get('version', '1.0.0'),
            'author': manifest.get('author', 'Unknown'),
            'category': manifest.get('category', 'general'),
            'tags': manifest.get('tags', []),
            'enabled': tool_info.get('enabled', True),
            'requires_auth': manifest.get('requires_auth', False)
        }

# Global tool router instance
tool_router = ToolRouter()

# Convenience functions
def route_query(input_text: str, threshold: float = 0.3):
    """Route a query to the best tool"""
    return tool_router.route_query(input_text, threshold)

def execute_tool(tool_name: str, input_text: str, **kwargs):
    """Execute a specific tool"""
    return tool_router.execute_tool(tool_name, input_text, **kwargs)

def route_and_execute(input_text: str, threshold: float = 0.3, **kwargs):
    """Route and execute in one call"""
    return tool_router.route_and_execute(input_text, threshold, **kwargs)

def get_available_tools():
    """Get available tools"""
    return tool_router.get_available_tools()

