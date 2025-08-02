"""
Memory Reload Engine for Jarvis AI Assistant
Handles loading, caching, and managing system memory including prompt templates,
chat history, plugin states, and user preferences.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from .logging_service import logging_service, LogLevel, LogCategory

class MemoryType:
    """Memory type constants"""
    ALL = "all"
    PROMPT = "prompt"
    PLUGINS = "plugins"
    HISTORY = "history"
    PREFERENCES = "preferences"
    WORKFLOWS = "workflows"

class MemoryLoader:
    """Memory Reload Engine for system state management"""
    
    def __init__(self, memory_dir: str = None):
        self.memory_dir = memory_dir or os.path.join(os.path.dirname(__file__), '../../memory')
        self.cache: Dict[str, Any] = {}
        self.load_timestamps: Dict[str, datetime] = {}
        self.auto_load_enabled = os.getenv('AUTO_LOAD_MEMORY', 'True').lower() == 'true'
        
        # Ensure memory directory exists
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # Initialize default memory files if they don't exist
        self._initialize_default_memory()
        
        print("✅ Memory loader initialized")
        
        # Auto-load memory on startup if enabled
        if self.auto_load_enabled:
            self.load_memory(MemoryType.ALL)
    
    def _initialize_default_memory(self):
        """Initialize default memory files if they don't exist"""
        
        default_memories = {
            'prompt_templates.json': {
                "system_prompts": {
                    "default": "You are Jarvis, an intelligent AI assistant. Be helpful, accurate, and concise.",
                    "ceo": "You are Jarvis, acting as a CEO advisor. Focus on strategic thinking, leadership, and business decisions.",
                    "wags": "You are Jarvis, acting as a WAGS (Wives and Girlfriends) advisor. Be supportive, understanding, and lifestyle-focused.",
                    "legal": "You are Jarvis, acting as a legal advisor. Be precise, thorough, and focus on legal implications."
                },
                "response_templates": {
                    "greeting": "Hello! I'm Jarvis, your AI assistant. How can I help you today?",
                    "error": "I apologize, but I encountered an error. Let me try to help you in a different way.",
                    "clarification": "Could you please provide more details so I can better assist you?"
                },
                "tool_prompts": {
                    "web_search": "I'll search the web for information about: {query}",
                    "weather": "Let me get the current weather information for: {location}",
                    "file_analysis": "I'll analyze this file for you: {filename}"
                }
            },
            'chat_history.json': {
                "sessions": {},
                "global_context": {
                    "user_preferences": {},
                    "conversation_themes": [],
                    "frequently_asked": []
                },
                "statistics": {
                    "total_conversations": 0,
                    "total_messages": 0,
                    "average_session_length": 0
                }
            },
            'plugin_states.json': {
                "active_plugins": {
                    "calculator": {
                        "enabled": True,
                        "last_used": None,
                        "usage_count": 0,
                        "configuration": {}
                    },
                    "text_processor": {
                        "enabled": True,
                        "last_used": None,
                        "usage_count": 0,
                        "configuration": {}
                    },
                    "web_scraper": {
                        "enabled": True,
                        "last_used": None,
                        "usage_count": 0,
                        "configuration": {
                            "timeout": 30,
                            "max_content_length": 100000
                        }
                    }
                },
                "plugin_cache": {},
                "execution_history": []
            },
            'user_preferences.json': {
                "default_settings": {
                    "theme": "light",
                    "language": "en",
                    "response_style": "balanced",
                    "auto_save": True,
                    "notifications": True
                },
                "user_specific": {},
                "global_preferences": {
                    "max_response_length": 2000,
                    "enable_file_upload": True,
                    "enable_tool_usage": True,
                    "enable_workflows": True
                }
            },
            'workflow_states.json': {
                "active_workflows": {},
                "workflow_templates": {
                    "send_followup_email": {
                        "enabled": True,
                        "last_executed": None,
                        "execution_count": 0
                    },
                    "daily_summary": {
                        "enabled": True,
                        "last_executed": None,
                        "execution_count": 0
                    },
                    "notify_overdue": {
                        "enabled": True,
                        "last_executed": None,
                        "execution_count": 0
                    }
                },
                "execution_history": []
            }
        }
        
        for filename, content in default_memories.items():
            filepath = os.path.join(self.memory_dir, filename)
            if not os.path.exists(filepath):
                try:
                    with open(filepath, 'w') as f:
                        json.dump(content, f, indent=2)
                    print(f"✅ Created default memory file: {filename}")
                except Exception as e:
                    print(f"⚠️ Failed to create {filename}: {e}")
    
    def load_memory(self, memory_type: str = MemoryType.ALL) -> Dict[str, Any]:
        """Load memory from disk into cache"""
        
        try:
            if memory_type == MemoryType.ALL:
                # Load all memory types
                result = {}
                for mem_type in [MemoryType.PROMPT, MemoryType.PLUGINS, MemoryType.HISTORY, 
                               MemoryType.PREFERENCES, MemoryType.WORKFLOWS]:
                    result[mem_type] = self._load_memory_type(mem_type)
                
                # Log successful load
                if logging_service:
                    logging_service.log(
                        LogLevel.INFO,
                        LogCategory.SYSTEM,
                        'memory_loaded',
                        details={'type': 'all', 'files_loaded': len(result)}
                    )
                
                return result
            else:
                # Load specific memory type
                result = self._load_memory_type(memory_type)
                
                # Log successful load
                if logging_service:
                    logging_service.log(
                        LogLevel.INFO,
                        LogCategory.SYSTEM,
                        'memory_loaded',
                        details={'type': memory_type, 'success': True}
                    )
                
                return {memory_type: result}
                
        except Exception as e:
            print(f"❌ Failed to load memory ({memory_type}): {e}")
            
            # Log failed load
            if logging_service:
                logging_service.log(
                    LogLevel.ERROR,
                    LogCategory.SYSTEM,
                    'memory_load_failed',
                    details={'type': memory_type, 'error': str(e)},
                    success=False,
                    error_message=str(e)
                )
            
            return {}
    
    def _load_memory_type(self, memory_type: str) -> Dict[str, Any]:
        """Load specific memory type from disk"""
        
        file_mapping = {
            MemoryType.PROMPT: 'prompt_templates.json',
            MemoryType.PLUGINS: 'plugin_states.json',
            MemoryType.HISTORY: 'chat_history.json',
            MemoryType.PREFERENCES: 'user_preferences.json',
            MemoryType.WORKFLOWS: 'workflow_states.json'
        }
        
        filename = file_mapping.get(memory_type)
        if not filename:
            raise ValueError(f"Unknown memory type: {memory_type}")
        
        filepath = os.path.join(self.memory_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"⚠️ Memory file not found: {filename}")
            return {}
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Cache the data
            self.cache[memory_type] = data
            self.load_timestamps[memory_type] = datetime.now()
            
            print(f"✅ Loaded memory: {filename}")
            return data
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {filename}: {e}")
            return {}
        except Exception as e:
            print(f"❌ Failed to load {filename}: {e}")
            return {}
    
    def save_memory(self, memory_type: str, data: Dict[str, Any]) -> bool:
        """Save memory data to disk"""
        
        file_mapping = {
            MemoryType.PROMPT: 'prompt_templates.json',
            MemoryType.PLUGINS: 'plugin_states.json',
            MemoryType.HISTORY: 'chat_history.json',
            MemoryType.PREFERENCES: 'user_preferences.json',
            MemoryType.WORKFLOWS: 'workflow_states.json'
        }
        
        filename = file_mapping.get(memory_type)
        if not filename:
            print(f"❌ Unknown memory type: {memory_type}")
            return False
        
        filepath = os.path.join(self.memory_dir, filename)
        
        try:
            # Backup existing file
            if os.path.exists(filepath):
                backup_path = f"{filepath}.backup"
                os.rename(filepath, backup_path)
            
            # Save new data
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Update cache
            self.cache[memory_type] = data
            self.load_timestamps[memory_type] = datetime.now()
            
            print(f"✅ Saved memory: {filename}")
            
            # Log successful save
            if logging_service:
                logging_service.log(
                    LogLevel.INFO,
                    LogCategory.SYSTEM,
                    'memory_saved',
                    details={'type': memory_type, 'file': filename}
                )
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to save {filename}: {e}")
            
            # Restore backup if save failed
            backup_path = f"{filepath}.backup"
            if os.path.exists(backup_path):
                os.rename(backup_path, filepath)
            
            # Log failed save
            if logging_service:
                logging_service.log(
                    LogLevel.ERROR,
                    LogCategory.SYSTEM,
                    'memory_save_failed',
                    details={'type': memory_type, 'error': str(e)},
                    success=False,
                    error_message=str(e)
                )
            
            return False
    
    def get_cached_memory(self, memory_type: str) -> Optional[Dict[str, Any]]:
        """Get memory from cache (fast access)"""
        return self.cache.get(memory_type)
    
    def get_memory_status(self) -> Dict[str, Any]:
        """Get memory loading status and statistics"""
        
        status = {
            "auto_load_enabled": self.auto_load_enabled,
            "memory_directory": self.memory_dir,
            "cached_types": list(self.cache.keys()),
            "load_timestamps": {
                k: v.isoformat() if v else None 
                for k, v in self.load_timestamps.items()
            },
            "memory_files": {},
            "total_cache_size": 0
        }
        
        # Check memory files on disk
        for memory_type in [MemoryType.PROMPT, MemoryType.PLUGINS, MemoryType.HISTORY, 
                           MemoryType.PREFERENCES, MemoryType.WORKFLOWS]:
            file_mapping = {
                MemoryType.PROMPT: 'prompt_templates.json',
                MemoryType.PLUGINS: 'plugin_states.json',
                MemoryType.HISTORY: 'chat_history.json',
                MemoryType.PREFERENCES: 'user_preferences.json',
                MemoryType.WORKFLOWS: 'workflow_states.json'
            }
            
            filename = file_mapping[memory_type]
            filepath = os.path.join(self.memory_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    stat = os.stat(filepath)
                    status["memory_files"][memory_type] = {
                        "filename": filename,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "cached": memory_type in self.cache
                    }
                    
                    if memory_type in self.cache:
                        # Estimate cache size (rough approximation)
                        cache_size = len(json.dumps(self.cache[memory_type]))
                        status["memory_files"][memory_type]["cache_size"] = cache_size
                        status["total_cache_size"] += cache_size
                        
                except Exception as e:
                    status["memory_files"][memory_type] = {
                        "filename": filename,
                        "error": str(e)
                    }
            else:
                status["memory_files"][memory_type] = {
                    "filename": filename,
                    "exists": False
                }
        
        return status
    
    def reload_memory(self, memory_type: str = MemoryType.ALL, force: bool = False) -> Dict[str, Any]:
        """Reload memory from disk, optionally forcing reload even if cached"""
        
        if force or memory_type not in self.cache:
            return self.load_memory(memory_type)
        else:
            print(f"Memory {memory_type} already cached, use force=True to reload")
            return {memory_type: self.cache.get(memory_type, {})}
    
    def clear_cache(self, memory_type: str = None):
        """Clear memory cache"""
        
        if memory_type:
            if memory_type in self.cache:
                del self.cache[memory_type]
            if memory_type in self.load_timestamps:
                del self.load_timestamps[memory_type]
            print(f"✅ Cleared cache for: {memory_type}")
        else:
            self.cache.clear()
            self.load_timestamps.clear()
            print("✅ Cleared all memory cache")
    
    def get_prompt_template(self, template_type: str, template_name: str) -> Optional[str]:
        """Get specific prompt template from memory"""
        
        prompt_memory = self.get_cached_memory(MemoryType.PROMPT)
        if not prompt_memory:
            prompt_memory = self.load_memory(MemoryType.PROMPT).get(MemoryType.PROMPT, {})
        
        return prompt_memory.get(template_type, {}).get(template_name)
    
    def update_plugin_state(self, plugin_name: str, state_data: Dict[str, Any]) -> bool:
        """Update plugin state in memory"""
        
        plugin_memory = self.get_cached_memory(MemoryType.PLUGINS)
        if not plugin_memory:
            plugin_memory = self.load_memory(MemoryType.PLUGINS).get(MemoryType.PLUGINS, {})
        
        if "active_plugins" not in plugin_memory:
            plugin_memory["active_plugins"] = {}
        
        plugin_memory["active_plugins"][plugin_name] = {
            **plugin_memory["active_plugins"].get(plugin_name, {}),
            **state_data,
            "last_updated": datetime.now().isoformat()
        }
        
        return self.save_memory(MemoryType.PLUGINS, plugin_memory)
    
    def add_chat_history(self, session_id: str, message_data: Dict[str, Any]) -> bool:
        """Add chat message to history memory"""
        
        history_memory = self.get_cached_memory(MemoryType.HISTORY)
        if not history_memory:
            history_memory = self.load_memory(MemoryType.HISTORY).get(MemoryType.HISTORY, {})
        
        if "sessions" not in history_memory:
            history_memory["sessions"] = {}
        
        if session_id not in history_memory["sessions"]:
            history_memory["sessions"][session_id] = {
                "created": datetime.now().isoformat(),
                "messages": []
            }
        
        history_memory["sessions"][session_id]["messages"].append({
            **message_data,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update statistics
        if "statistics" not in history_memory:
            history_memory["statistics"] = {
                "total_conversations": 0,
                "total_messages": 0
            }
        
        history_memory["statistics"]["total_messages"] += 1
        history_memory["statistics"]["total_conversations"] = len(history_memory["sessions"])
        
        return self.save_memory(MemoryType.HISTORY, history_memory)
    
    def get_user_preferences(self, user_id: str = None) -> Dict[str, Any]:
        """Get user preferences from memory"""
        
        pref_memory = self.get_cached_memory(MemoryType.PREFERENCES)
        if not pref_memory:
            pref_memory = self.load_memory(MemoryType.PREFERENCES).get(MemoryType.PREFERENCES, {})
        
        if user_id and "user_specific" in pref_memory:
            return pref_memory["user_specific"].get(user_id, pref_memory.get("default_settings", {}))
        else:
            return pref_memory.get("default_settings", {})
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences in memory"""
        
        pref_memory = self.get_cached_memory(MemoryType.PREFERENCES)
        if not pref_memory:
            pref_memory = self.load_memory(MemoryType.PREFERENCES).get(MemoryType.PREFERENCES, {})
        
        if "user_specific" not in pref_memory:
            pref_memory["user_specific"] = {}
        
        pref_memory["user_specific"][user_id] = {
            **pref_memory["user_specific"].get(user_id, {}),
            **preferences,
            "last_updated": datetime.now().isoformat()
        }
        
        return self.save_memory(MemoryType.PREFERENCES, pref_memory)

# Global instance
memory_loader = MemoryLoader()

