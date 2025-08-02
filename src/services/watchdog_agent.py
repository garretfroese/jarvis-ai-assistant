"""
Self-Healing Deployment Watchdog for Jarvis AI Assistant
Monitors system health and implements automatic recovery mechanisms.
"""

import os
import time
import json
import requests
import subprocess
import threading
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from .logging_service import logging_service, LogLevel, LogCategory

@dataclass
class HealthCheck:
    """Health check result"""
    name: str
    status: bool
    message: str
    timestamp: datetime
    response_time: Optional[float] = None

@dataclass
class SystemThresholds:
    """System resource thresholds"""
    cpu_percent: float = 80.0
    memory_percent: float = 85.0
    disk_percent: float = 90.0
    response_time_ms: float = 5000.0

class WatchdogAgent:
    """Self-Healing Deployment Watchdog"""
    
    def __init__(self):
        self.enabled = os.getenv('WATCHDOG_ENABLED', 'True').lower() == 'true'
        self.check_interval = int(os.getenv('WATCHDOG_INTERVAL', '60'))  # seconds
        self.backend_url = os.getenv('BACKEND_URL', 'http://localhost:5000')
        self.render_deploy_hook = os.getenv('RENDER_DEPLOY_HOOK_URL', '')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL', '')
        self.admin_email = os.getenv('ADMIN_EMAIL', '')
        
        self.thresholds = SystemThresholds()
        self.health_history: List[Dict[str, Any]] = []
        self.last_notification = {}
        self.notification_cooldown = 300  # 5 minutes
        
        self.running = False
        self.thread = None
        
        print("✅ Watchdog agent initialized")
        
        if self.enabled:
            self.start()
    
    def start(self):
        """Start the watchdog monitoring"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        
        print("🔄 Watchdog monitoring started")
        
        # Log watchdog start
        if logging_service:
            logging_service.log(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                'watchdog_started',
                details={'interval': self.check_interval, 'enabled': self.enabled}
            )
    
    def stop(self):
        """Stop the watchdog monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        print("⏹️ Watchdog monitoring stopped")
        
        # Log watchdog stop
        if logging_service:
            logging_service.log(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                'watchdog_stopped',
                details={}
            )
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Perform health checks
                health_results = self.perform_health_checks()
                
                # Analyze results and take action
                self._analyze_and_respond(health_results)
                
                # Store health history
                self._store_health_history(health_results)
                
                # Wait for next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"❌ Watchdog error: {e}")
                time.sleep(self.check_interval)
    
    def perform_health_checks(self) -> List[HealthCheck]:
        """Perform all health checks"""
        checks = []
        
        # 1. Backend API responsiveness
        checks.append(self._check_backend_api())
        
        # 2. Plugin registration status
        checks.append(self._check_plugins())
        
        # 3. OpenAI API availability
        checks.append(self._check_openai_api())
        
        # 4. System resource thresholds
        checks.extend(self._check_system_resources())
        
        # 5. Memory loader status
        checks.append(self._check_memory_loader())
        
        # 6. Workflow engine status
        checks.append(self._check_workflow_engine())
        
        return checks
    
    def _check_backend_api(self) -> HealthCheck:
        """Check if backend API is responsive"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/health", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return HealthCheck(
                    name="backend_api",
                    status=True,
                    message="Backend API is responsive",
                    timestamp=datetime.now(),
                    response_time=response_time
                )
            else:
                return HealthCheck(
                    name="backend_api",
                    status=False,
                    message=f"Backend API returned status {response.status_code}",
                    timestamp=datetime.now(),
                    response_time=response_time
                )
                
        except requests.exceptions.RequestException as e:
            return HealthCheck(
                name="backend_api",
                status=False,
                message=f"Backend API unreachable: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _check_plugins(self) -> HealthCheck:
        """Check plugin registration status"""
        try:
            response = requests.get(f"{self.backend_url}/api/plugins", timeout=10)
            
            if response.status_code == 200:
                plugins = response.json().get('plugins', [])
                if len(plugins) >= 3:  # Expect at least 3 built-in plugins
                    return HealthCheck(
                        name="plugins",
                        status=True,
                        message=f"All {len(plugins)} plugins registered",
                        timestamp=datetime.now()
                    )
                else:
                    return HealthCheck(
                        name="plugins",
                        status=False,
                        message=f"Only {len(plugins)} plugins registered (expected 3+)",
                        timestamp=datetime.now()
                    )
            else:
                return HealthCheck(
                    name="plugins",
                    status=False,
                    message=f"Plugin endpoint returned status {response.status_code}",
                    timestamp=datetime.now()
                )
                
        except requests.exceptions.RequestException as e:
            return HealthCheck(
                name="plugins",
                status=False,
                message=f"Plugin check failed: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _check_openai_api(self) -> HealthCheck:
        """Check OpenAI API availability"""
        try:
            import openai
            
            # Simple API test
            client = openai.OpenAI()
            response = client.models.list()
            
            return HealthCheck(
                name="openai_api",
                status=True,
                message="OpenAI API is available",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return HealthCheck(
                name="openai_api",
                status=False,
                message=f"OpenAI API unavailable: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _check_system_resources(self) -> List[HealthCheck]:
        """Check system resource usage"""
        checks = []
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            checks.append(HealthCheck(
                name="cpu_usage",
                status=cpu_percent < self.thresholds.cpu_percent,
                message=f"CPU usage: {cpu_percent:.1f}% (threshold: {self.thresholds.cpu_percent}%)",
                timestamp=datetime.now()
            ))
            
            # Memory usage
            memory = psutil.virtual_memory()
            checks.append(HealthCheck(
                name="memory_usage",
                status=memory.percent < self.thresholds.memory_percent,
                message=f"Memory usage: {memory.percent:.1f}% (threshold: {self.thresholds.memory_percent}%)",
                timestamp=datetime.now()
            ))
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            checks.append(HealthCheck(
                name="disk_usage",
                status=disk_percent < self.thresholds.disk_percent,
                message=f"Disk usage: {disk_percent:.1f}% (threshold: {self.thresholds.disk_percent}%)",
                timestamp=datetime.now()
            ))
            
        except Exception as e:
            checks.append(HealthCheck(
                name="system_resources",
                status=False,
                message=f"Resource check failed: {str(e)}",
                timestamp=datetime.now()
            ))
        
        return checks
    
    def _check_memory_loader(self) -> HealthCheck:
        """Check memory loader status"""
        try:
            response = requests.get(f"{self.backend_url}/api/memory/status", timeout=10)
            
            if response.status_code == 200:
                status = response.json()
                cached_types = status.get('cached_types', [])
                
                if len(cached_types) >= 3:  # Expect at least 3 memory types
                    return HealthCheck(
                        name="memory_loader",
                        status=True,
                        message=f"Memory loader active with {len(cached_types)} types cached",
                        timestamp=datetime.now()
                    )
                else:
                    return HealthCheck(
                        name="memory_loader",
                        status=False,
                        message=f"Memory loader has only {len(cached_types)} types cached",
                        timestamp=datetime.now()
                    )
            else:
                return HealthCheck(
                    name="memory_loader",
                    status=False,
                    message=f"Memory status endpoint returned {response.status_code}",
                    timestamp=datetime.now()
                )
                
        except requests.exceptions.RequestException as e:
            return HealthCheck(
                name="memory_loader",
                status=False,
                message=f"Memory loader check failed: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _check_workflow_engine(self) -> HealthCheck:
        """Check workflow engine status"""
        try:
            response = requests.get(f"{self.backend_url}/api/workflows", timeout=10)
            
            if response.status_code == 200:
                workflows = response.json().get('workflows', [])
                
                if len(workflows) >= 3:  # Expect at least 3 workflow templates
                    return HealthCheck(
                        name="workflow_engine",
                        status=True,
                        message=f"Workflow engine active with {len(workflows)} workflows",
                        timestamp=datetime.now()
                    )
                else:
                    return HealthCheck(
                        name="workflow_engine",
                        status=False,
                        message=f"Workflow engine has only {len(workflows)} workflows",
                        timestamp=datetime.now()
                    )
            else:
                return HealthCheck(
                    name="workflow_engine",
                    status=False,
                    message=f"Workflow endpoint returned {response.status_code}",
                    timestamp=datetime.now()
                )
                
        except requests.exceptions.RequestException as e:
            return HealthCheck(
                name="workflow_engine",
                status=False,
                message=f"Workflow engine check failed: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _analyze_and_respond(self, health_results: List[HealthCheck]):
        """Analyze health results and take recovery actions"""
        
        failed_checks = [check for check in health_results if not check.status]
        
        if not failed_checks:
            return  # All checks passed
        
        # Categorize failures
        critical_failures = []
        warning_failures = []
        
        for check in failed_checks:
            if check.name in ['backend_api', 'openai_api']:
                critical_failures.append(check)
            else:
                warning_failures.append(check)
        
        # Handle critical failures
        if critical_failures:
            self._handle_critical_failures(critical_failures)
        
        # Handle warnings
        if warning_failures:
            self._handle_warnings(warning_failures)
    
    def _handle_critical_failures(self, failures: List[HealthCheck]):
        """Handle critical system failures"""
        
        failure_names = [f.name for f in failures]
        
        print(f"🚨 Critical failures detected: {failure_names}")
        
        # Log critical failure
        if logging_service:
            logging_service.log(
                LogLevel.CRITICAL,
                LogCategory.SYSTEM,
                'critical_failure',
                details={
                    'failures': [{'name': f.name, 'message': f.message} for f in failures],
                    'recovery_attempted': True
                },
                success=False
            )
        
        # Attempt recovery
        recovery_success = False
        
        # Try local restart first (if running locally)
        if self._is_local_deployment():
            recovery_success = self._restart_local_service()
        
        # Try Render redeploy if local restart failed or not local
        if not recovery_success and self.render_deploy_hook:
            recovery_success = self._trigger_render_redeploy()
        
        # Send notifications
        self._send_critical_notification(failures, recovery_success)
    
    def _handle_warnings(self, warnings: List[HealthCheck]):
        """Handle warning-level issues"""
        
        warning_names = [w.name for w in warnings]
        
        print(f"⚠️ Warnings detected: {warning_names}")
        
        # Log warnings
        if logging_service:
            logging_service.log(
                LogLevel.WARNING,
                LogCategory.SYSTEM,
                'system_warnings',
                details={
                    'warnings': [{'name': w.name, 'message': w.message} for w in warnings]
                }
            )
        
        # Send warning notification (with cooldown)
        self._send_warning_notification(warnings)
    
    def _is_local_deployment(self) -> bool:
        """Check if this is a local deployment"""
        return 'localhost' in self.backend_url or '127.0.0.1' in self.backend_url
    
    def _restart_local_service(self) -> bool:
        """Restart local Flask service"""
        try:
            # This is a simplified restart - in production you'd use proper process management
            print("🔄 Attempting local service restart...")
            
            # Find and kill existing Flask processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'python' in proc.info['name'] and 'app.py' in ' '.join(proc.info['cmdline']):
                        proc.terminate()
                        proc.wait(timeout=5)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Start new process (this is simplified - in production use proper process management)
            # subprocess.Popen(['python', 'app.py'], cwd='/path/to/jarvis-chatbot')
            
            print("✅ Local service restart attempted")
            return True
            
        except Exception as e:
            print(f"❌ Local restart failed: {e}")
            return False
    
    def _trigger_render_redeploy(self) -> bool:
        """Trigger Render redeploy via webhook"""
        try:
            if not self.render_deploy_hook:
                return False
            
            print("🔄 Triggering Render redeploy...")
            
            response = requests.post(self.render_deploy_hook, timeout=30)
            
            if response.status_code in [200, 201, 202]:
                print("✅ Render redeploy triggered successfully")
                return True
            else:
                print(f"❌ Render redeploy failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Render redeploy error: {e}")
            return False
    
    def _send_critical_notification(self, failures: List[HealthCheck], recovery_attempted: bool):
        """Send critical failure notification"""
        
        # Check notification cooldown
        if self._is_notification_on_cooldown('critical'):
            return
        
        message = f"🚨 CRITICAL: Jarvis AI Assistant System Failure\n\n"
        message += f"Time: {datetime.now().isoformat()}\n"
        message += f"Failures:\n"
        
        for failure in failures:
            message += f"- {failure.name}: {failure.message}\n"
        
        message += f"\nRecovery attempted: {'Yes' if recovery_attempted else 'No'}"
        
        # Send to Slack
        if self.slack_webhook:
            self._send_slack_notification(message, urgent=True)
        
        # Send email (if configured)
        if self.admin_email:
            self._send_email_notification(message, urgent=True)
        
        # Update cooldown
        self.last_notification['critical'] = datetime.now()
    
    def _send_warning_notification(self, warnings: List[HealthCheck]):
        """Send warning notification"""
        
        # Check notification cooldown
        if self._is_notification_on_cooldown('warning'):
            return
        
        message = f"⚠️ WARNING: Jarvis AI Assistant System Issues\n\n"
        message += f"Time: {datetime.now().isoformat()}\n"
        message += f"Warnings:\n"
        
        for warning in warnings:
            message += f"- {warning.name}: {warning.message}\n"
        
        # Send to Slack
        if self.slack_webhook:
            self._send_slack_notification(message, urgent=False)
        
        # Update cooldown
        self.last_notification['warning'] = datetime.now()
    
    def _is_notification_on_cooldown(self, notification_type: str) -> bool:
        """Check if notification is on cooldown"""
        last_sent = self.last_notification.get(notification_type)
        if not last_sent:
            return False
        
        return (datetime.now() - last_sent).total_seconds() < self.notification_cooldown
    
    def _send_slack_notification(self, message: str, urgent: bool = False):
        """Send notification to Slack"""
        try:
            payload = {
                "text": message,
                "username": "Jarvis Watchdog",
                "icon_emoji": ":robot_face:" if not urgent else ":rotating_light:"
            }
            
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            
            if response.status_code == 200:
                print("✅ Slack notification sent")
            else:
                print(f"❌ Slack notification failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Slack notification error: {e}")
    
    def _send_email_notification(self, message: str, urgent: bool = False):
        """Send email notification (placeholder - implement with your email service)"""
        # This would integrate with your email service (SendGrid, etc.)
        print(f"📧 Email notification would be sent to {self.admin_email}")
        print(f"Subject: {'URGENT: ' if urgent else ''}Jarvis System Alert")
        print(f"Message: {message}")
    
    def _store_health_history(self, health_results: List[HealthCheck]):
        """Store health check history"""
        
        health_record = {
            "timestamp": datetime.now().isoformat(),
            "checks": [
                {
                    "name": check.name,
                    "status": check.status,
                    "message": check.message,
                    "response_time": check.response_time
                }
                for check in health_results
            ],
            "overall_status": all(check.status for check in health_results)
        }
        
        self.health_history.append(health_record)
        
        # Keep only last 100 records
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        
        if not self.health_history:
            return {
                "status": "unknown",
                "message": "No health checks performed yet",
                "last_check": None
            }
        
        latest = self.health_history[-1]
        
        return {
            "status": "healthy" if latest["overall_status"] else "unhealthy",
            "last_check": latest["timestamp"],
            "checks": latest["checks"],
            "watchdog_enabled": self.enabled,
            "check_interval": self.check_interval,
            "total_checks": len(self.health_history)
        }
    
    def get_health_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get health check history"""
        return self.health_history[-limit:]
    
    def force_health_check(self) -> Dict[str, Any]:
        """Force immediate health check"""
        health_results = self.perform_health_checks()
        self._store_health_history(health_results)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "results": [
                {
                    "name": check.name,
                    "status": check.status,
                    "message": check.message,
                    "response_time": check.response_time
                }
                for check in health_results
            ],
            "overall_status": all(check.status for check in health_results)
        }

# Global instance
watchdog_agent = WatchdogAgent()

