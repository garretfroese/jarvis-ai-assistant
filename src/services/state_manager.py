"""
System State Manager for Jarvis AI Assistant
Handles system state export and persistent plugin cache management.
"""

import os
import json
import time
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from .logging_service import logging_service
from .memory_loader import memory_loader

class StateManager:
    """System State Export and Plugin Cache Manager"""
    
    def __init__(self, state_dir: str = None):
        self.state_dir = state_dir or os.path.join(os.path.dirname(__file__), '../../state')
        self.plugin_cache_file = os.path.join(self.state_dir, 'plugin_cache.json')
        self.system_state_file = os.path.join(self.state_dir, 'system_state.json')
        
        # Plugin cache refresh settings
        self.cache_refresh_interval = 600  # 10 minutes
        self.last_cache_refresh = None
        self.plugin_cache = {}
        
        # System state tracking
        self.current_state = {}
        
        # Ensure state directory exists
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Load existing plugin cache
        self._load_plugin_cache()
        
        # Start background cache refresh
        self._start_cache_refresh_thread()
        
        print("✅ State manager initialized")
    
    def _start_cache_refresh_thread(self):
        """Start background thread for plugin cache refresh"""
        def refresh_loop():
            while True:
                try:
                    time.sleep(self.cache_refresh_interval)
                    self.refresh_plugin_cache()
                except Exception as e:
                    print(f"❌ Plugin cache refresh error: {e}")
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
        print("🔄 Plugin cache refresh thread started")
    
    def export_system_state(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Export complete system state"""
        
        try:
            # Get current system state
            state = {
                "timestamp": datetime.now().isoformat(),
                "version": "12.0.0",  # Phase 6 version
                "system_info": self._get_system_info(),
                "current_mode": self._get_current_mode(),
                "active_user": self._get_active_user(include_sensitive),
                "plugins_loaded": self._get_plugins_status(),
                "tools_active": self._get_tools_status(),
                "memory_status": self._get_memory_status(),
                "workflow_execution_status": self._get_workflow_status(),
                "security_status": self._get_security_status(),
                "performance_metrics": self._get_performance_metrics(),
                "health_status": self._get_health_status()
            }
            
            # Save state to file
            self._save_system_state(state)
            
            # Log state export
            if logging_service:
                logging_service.log_activity(
                    'system',
                    'state_exported',
                    {
                        'include_sensitive': include_sensitive,
                        'state_size': len(json.dumps(state))
                    }
                )
            
            return state
            
        except Exception as e:
            print(f"❌ Failed to export system state: {e}")
            
            # Log export failure
            if logging_service:
                logging_service.log_activity(
                    'system',
                    'state_export_failed',
                    {'error': str(e)}
                )
            
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        try:
            import psutil
            
            return {
                "platform": os.name,
                "python_version": os.sys.version,
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_total": psutil.disk_usage('/').total,
                "uptime": time.time() - psutil.boot_time(),
                "environment": os.getenv('FLASK_ENV', 'production')
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_current_mode(self) -> Dict[str, Any]:
        """Get current operating mode"""
        try:
            # This would integrate with your mode switching system
            # For now, return default mode
            return {
                "mode": "default",
                "description": "Default AI Assistant Mode",
                "capabilities": ["chat", "tools", "files", "workflows"],
                "restrictions": []
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_active_user(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Get active user information"""
        try:
            # This would integrate with your user service
            # For now, return system user
            user_info = {
                "user_type": "system",
                "role": "admin",
                "permissions": ["full_access"],
                "session_count": 1,
                "last_activity": datetime.now().isoformat()
            }
            
            if include_sensitive:
                user_info.update({
                    "user_id": "system_admin",
                    "email": "system@jarvis.ai"
                })
            
            return user_info
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_plugins_status(self) -> Dict[str, Any]:
        """Get plugins loading status"""
        try:
            # Get from plugin cache
            plugins_status = {
                "total_plugins": len(self.plugin_cache),
                "active_plugins": [],
                "failed_plugins": [],
                "plugin_details": {}
            }
            
            for plugin_name, plugin_data in self.plugin_cache.items():
                if plugin_data.get('status') == 'active':
                    plugins_status["active_plugins"].append(plugin_name)
                else:
                    plugins_status["failed_plugins"].append(plugin_name)
                
                plugins_status["plugin_details"][plugin_name] = {
                    "status": plugin_data.get('status', 'unknown'),
                    "last_used": plugin_data.get('last_used'),
                    "usage_count": plugin_data.get('usage_count', 0),
                    "health": plugin_data.get('health', 'unknown')
                }
            
            return plugins_status
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_tools_status(self) -> Dict[str, Any]:
        """Get tools status"""
        try:
            # This would integrate with your tool routing system
            tools_status = {
                "total_tools": 7,
                "active_tools": [
                    "weather_lookup",
                    "text_analyzer", 
                    "url_shortener",
                    "web_search",
                    "web_scraper",
                    "url_summarizer",
                    "command_executor"
                ],
                "tool_usage": {
                    "weather_lookup": {"usage_count": 0, "last_used": None},
                    "text_analyzer": {"usage_count": 0, "last_used": None},
                    "url_shortener": {"usage_count": 0, "last_used": None},
                    "web_search": {"usage_count": 0, "last_used": None},
                    "web_scraper": {"usage_count": 0, "last_used": None},
                    "url_summarizer": {"usage_count": 0, "last_used": None},
                    "command_executor": {"usage_count": 0, "last_used": None}
                }
            }
            
            return tools_status
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_memory_status(self) -> Dict[str, Any]:
        """Get memory system status"""
        try:
            if memory_loader:
                return memory_loader.get_memory_status()
            else:
                return {"error": "Memory loader not available"}
        except Exception as e:
            return {"error": str(e)}
    
    def _get_workflow_status(self) -> Dict[str, Any]:
        """Get workflow execution status"""
        try:
            # This would integrate with your workflow engine
            workflow_status = {
                "total_workflows": 3,
                "active_executions": 0,
                "completed_executions": 0,
                "failed_executions": 0,
                "workflow_templates": [
                    "send_followup_email",
                    "daily_summary", 
                    "notify_overdue"
                ],
                "last_execution": None
            }
            
            return workflow_status
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_security_status(self) -> Dict[str, Any]:
        """Get security system status"""
        try:
            # This would integrate with your security systems
            security_status = {
                "authentication_enabled": True,
                "rbac_enabled": True,
                "risk_filter_enabled": True,
                "plugin_sandbox_enabled": True,
                "audit_logging_enabled": True,
                "recent_security_events": 0,
                "blocked_commands": 0,
                "security_level": "high"
            }
            
            return security_status
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            import psutil
            
            return {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                "network_io": {
                    "bytes_sent": psutil.net_io_counters().bytes_sent,
                    "bytes_recv": psutil.net_io_counters().bytes_recv
                },
                "process_count": len(psutil.pids()),
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        try:
            # This would integrate with your watchdog agent
            from .watchdog_agent import watchdog_agent
            
            if watchdog_agent:
                return watchdog_agent.get_health_status()
            else:
                return {"status": "unknown", "message": "Watchdog not available"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _save_system_state(self, state: Dict[str, Any]):
        """Save system state to file"""
        try:
            with open(self.system_state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            print(f"✅ System state saved to {self.system_state_file}")
            
        except Exception as e:
            print(f"❌ Failed to save system state: {e}")
    
    def refresh_plugin_cache(self) -> bool:
        """Refresh plugin cache from active plugin state"""
        try:
            print("🔄 Refreshing plugin cache...")
            
            # Get current plugin states (this would integrate with your plugin system)
            current_plugins = self._get_current_plugin_states()
            
            # Update cache
            for plugin_name, plugin_data in current_plugins.items():
                if plugin_name not in self.plugin_cache:
                    self.plugin_cache[plugin_name] = {}
                
                self.plugin_cache[plugin_name].update({
                    "status": plugin_data.get("status", "unknown"),
                    "health": plugin_data.get("health", "unknown"),
                    "last_updated": datetime.now().isoformat(),
                    "metadata": plugin_data.get("metadata", {}),
                    "usage_count": plugin_data.get("usage_count", 0),
                    "last_used": plugin_data.get("last_used")
                })
            
            # Save cache to disk
            self._save_plugin_cache()
            
            self.last_cache_refresh = datetime.now()
            
            print(f"✅ Plugin cache refreshed ({len(self.plugin_cache)} plugins)")
            
            # Log cache refresh
            if logging_service:
                logging_service.log_activity(
                    'system',
                    'plugin_cache_refreshed',
                    {'plugin_count': len(self.plugin_cache)}
                )
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to refresh plugin cache: {e}")
            
            # Log cache refresh failure
            if logging_service:
                logging_service.log_activity(
                    'system',
                    'plugin_cache_refresh_failed',
                    {'error': str(e)}
                )
            
            return False
    
    def _get_current_plugin_states(self) -> Dict[str, Any]:
        """Get current plugin states from plugin system"""
        # This would integrate with your actual plugin system
        # For now, return default plugin states
        
        return {
            "calculator": {
                "status": "active",
                "health": "healthy",
                "metadata": {
                    "version": "1.0.0",
                    "description": "Mathematical expression calculator",
                    "language": "python"
                },
                "usage_count": 0,
                "last_used": None
            },
            "text_processor": {
                "status": "active", 
                "health": "healthy",
                "metadata": {
                    "version": "1.0.0",
                    "description": "Text manipulation utilities",
                    "language": "python"
                },
                "usage_count": 0,
                "last_used": None
            },
            "web_scraper": {
                "status": "active",
                "health": "healthy", 
                "metadata": {
                    "version": "1.0.0",
                    "description": "Web content extraction",
                    "language": "python"
                },
                "usage_count": 0,
                "last_used": None
            }
        }
    
    def _load_plugin_cache(self):
        """Load plugin cache from disk"""
        try:
            if os.path.exists(self.plugin_cache_file):
                with open(self.plugin_cache_file, 'r') as f:
                    self.plugin_cache = json.load(f)
                
                print(f"✅ Loaded plugin cache ({len(self.plugin_cache)} plugins)")
            else:
                # Initialize with default cache
                self.plugin_cache = {}
                self.refresh_plugin_cache()
                
        except Exception as e:
            print(f"❌ Failed to load plugin cache: {e}")
            self.plugin_cache = {}
    
    def _save_plugin_cache(self):
        """Save plugin cache to disk"""
        try:
            # Create backup
            if os.path.exists(self.plugin_cache_file):
                backup_file = f"{self.plugin_cache_file}.backup"
                os.rename(self.plugin_cache_file, backup_file)
            
            # Save new cache
            with open(self.plugin_cache_file, 'w') as f:
                json.dump(self.plugin_cache, f, indent=2)
            
            print(f"✅ Plugin cache saved to {self.plugin_cache_file}")
            
        except Exception as e:
            print(f"❌ Failed to save plugin cache: {e}")
            
            # Restore backup if save failed
            backup_file = f"{self.plugin_cache_file}.backup"
            if os.path.exists(backup_file):
                os.rename(backup_file, self.plugin_cache_file)
    
    def get_plugin_cache_status(self) -> Dict[str, Any]:
        """Get plugin cache status"""
        return {
            "cache_file": self.plugin_cache_file,
            "total_plugins": len(self.plugin_cache),
            "last_refresh": self.last_cache_refresh.isoformat() if self.last_cache_refresh else None,
            "refresh_interval": self.cache_refresh_interval,
            "cache_size": len(json.dumps(self.plugin_cache)),
            "plugins": list(self.plugin_cache.keys())
        }
    
    def reload_failed_plugins(self) -> Dict[str, Any]:
        """Reload plugins that failed to load on startup"""
        try:
            failed_plugins = []
            reloaded_plugins = []
            
            for plugin_name, plugin_data in self.plugin_cache.items():
                if plugin_data.get('status') != 'active':
                    failed_plugins.append(plugin_name)
                    
                    # Attempt to reload (this would integrate with your plugin system)
                    if self._attempt_plugin_reload(plugin_name):
                        reloaded_plugins.append(plugin_name)
            
            # Log reload attempt
            if logging_service:
                logging_service.log_activity(
                    'system',
                    'plugin_reload_attempted',
                    {
                        'failed_plugins': failed_plugins,
                        'reloaded_plugins': reloaded_plugins
                    }
                )
            
            return {
                "failed_plugins": failed_plugins,
                "reloaded_plugins": reloaded_plugins,
                "success_rate": len(reloaded_plugins) / len(failed_plugins) if failed_plugins else 1.0
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _attempt_plugin_reload(self, plugin_name: str) -> bool:
        """Attempt to reload a specific plugin"""
        try:
            # This would integrate with your actual plugin loading system
            # For now, simulate successful reload
            
            self.plugin_cache[plugin_name]["status"] = "active"
            self.plugin_cache[plugin_name]["health"] = "healthy"
            self.plugin_cache[plugin_name]["last_reload"] = datetime.now().isoformat()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to reload plugin {plugin_name}: {e}")
            return False
    
    def get_state_files_info(self) -> Dict[str, Any]:
        """Get information about state files"""
        files_info = {}
        
        for filename in ['plugin_cache.json', 'system_state.json']:
            filepath = os.path.join(self.state_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    stat = os.stat(filepath)
                    files_info[filename] = {
                        "exists": True,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "readable": os.access(filepath, os.R_OK),
                        "writable": os.access(filepath, os.W_OK)
                    }
                except Exception as e:
                    files_info[filename] = {
                        "exists": True,
                        "error": str(e)
                    }
            else:
                files_info[filename] = {
                    "exists": False
                }
        
        return {
            "state_directory": self.state_dir,
            "files": files_info,
            "total_files": len([f for f in files_info.values() if f.get('exists')])
        }

# Global instance
state_manager = StateManager()

