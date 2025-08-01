"""
Autonomy Service for Jarvis
Implements autonomous decision-making, memory management, and self-extension capabilities
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet
from src.models.database import db, Memory, CommandLog, SecurityEvent, JobQueue, Secret, WebhookEvent, AutonomySession

class MemoryManager:
    """Memory management for autonomous operations"""
    
    @staticmethod
    def store(key: str, value: Any, category: str = 'general', expires_in_hours: int = None) -> bool:
        """Store data in memory"""
        try:
            # Check if key exists
            memory = Memory.query.filter_by(key=key).first()
            
            if memory:
                # Update existing
                memory.set_value(value)
                memory.category = category
                memory.updated_at = datetime.utcnow()
            else:
                # Create new
                memory = Memory(key=key, category=category)
                memory.set_value(value)
                db.session.add(memory)
            
            # Set expiration if specified
            if expires_in_hours:
                memory.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Memory store error: {e}")
            return False
    
    @staticmethod
    def retrieve(key: str) -> Optional[Any]:
        """Retrieve data from memory"""
        try:
            memory = Memory.query.filter_by(key=key).first()
            
            if not memory:
                return None
            
            # Check expiration
            if memory.expires_at and memory.expires_at < datetime.utcnow():
                db.session.delete(memory)
                db.session.commit()
                return None
            
            return memory.get_parsed_value()
            
        except Exception as e:
            print(f"Memory retrieve error: {e}")
            return None
    
    @staticmethod
    def search(category: str = None, pattern: str = None) -> List[Dict]:
        """Search memory entries"""
        try:
            query = Memory.query
            
            if category:
                query = query.filter_by(category=category)
            
            if pattern:
                query = query.filter(Memory.key.like(f'%{pattern}%'))
            
            memories = query.all()
            return [memory.to_dict() for memory in memories]
            
        except Exception as e:
            print(f"Memory search error: {e}")
            return []
    
    @staticmethod
    def delete(key: str) -> bool:
        """Delete memory entry"""
        try:
            memory = Memory.query.filter_by(key=key).first()
            if memory:
                db.session.delete(memory)
                db.session.commit()
                return True
            return False
            
        except Exception as e:
            db.session.rollback()
            print(f"Memory delete error: {e}")
            return False
    
    @staticmethod
    def cleanup_expired() -> int:
        """Clean up expired memory entries"""
        try:
            expired = Memory.query.filter(Memory.expires_at < datetime.utcnow()).all()
            count = len(expired)
            
            for memory in expired:
                db.session.delete(memory)
            
            db.session.commit()
            return count
            
        except Exception as e:
            db.session.rollback()
            print(f"Memory cleanup error: {e}")
            return 0

class SecretManager:
    """Secure secret management"""
    
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key"""
        key_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'secret.key')
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(key)
            return key
    
    def store_secret(self, key: str, value: str, description: str = None, category: str = 'general') -> bool:
        """Store encrypted secret"""
        try:
            encrypted_value = self.cipher.encrypt(value.encode()).decode()
            
            # Check if secret exists
            secret = Secret.query.filter_by(key=key).first()
            
            if secret:
                # Update existing
                secret.encrypted_value = encrypted_value
                secret.description = description
                secret.category = category
                secret.updated_at = datetime.utcnow()
            else:
                # Create new
                secret = Secret(
                    key=key,
                    encrypted_value=encrypted_value,
                    description=description,
                    category=category
                )
                db.session.add(secret)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Secret store error: {e}")
            return False
    
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve and decrypt secret"""
        try:
            secret = Secret.query.filter_by(key=key).first()
            
            if not secret:
                return None
            
            # Update access tracking
            secret.last_accessed = datetime.utcnow()
            secret.access_count += 1
            db.session.commit()
            
            # Decrypt and return
            decrypted_value = self.cipher.decrypt(secret.encrypted_value.encode()).decode()
            return decrypted_value
            
        except Exception as e:
            print(f"Secret retrieve error: {e}")
            return None
    
    def list_secrets(self, category: str = None) -> List[Dict]:
        """List secrets (without values)"""
        try:
            query = Secret.query
            
            if category:
                query = query.filter_by(category=category)
            
            secrets = query.all()
            return [secret.to_dict(include_value=False) for secret in secrets]
            
        except Exception as e:
            print(f"Secret list error: {e}")
            return []
    
    def delete_secret(self, key: str) -> bool:
        """Delete secret"""
        try:
            secret = Secret.query.filter_by(key=key).first()
            if secret:
                db.session.delete(secret)
                db.session.commit()
                return True
            return False
            
        except Exception as e:
            db.session.rollback()
            print(f"Secret delete error: {e}")
            return False

class JobScheduler:
    """Job scheduling and queue management"""
    
    @staticmethod
    def schedule_job(command: str, parameters: Dict, job_type: str = 'command', 
                    priority: int = 5, delay_minutes: int = 0, max_retries: int = 3) -> str:
        """Schedule a job for execution"""
        try:
            job_id = f"job_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"
            scheduled_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
            
            job = JobQueue(
                job_id=job_id,
                job_type=job_type,
                command=command,
                parameters=json.dumps(parameters),
                priority=priority,
                scheduled_at=scheduled_at,
                max_retries=max_retries
            )
            
            db.session.add(job)
            db.session.commit()
            
            return job_id
            
        except Exception as e:
            db.session.rollback()
            print(f"Job schedule error: {e}")
            return None
    
    @staticmethod
    def get_pending_jobs(limit: int = 10) -> List[Dict]:
        """Get pending jobs for execution"""
        try:
            jobs = JobQueue.query.filter(
                JobQueue.status == 'pending',
                JobQueue.scheduled_at <= datetime.utcnow()
            ).order_by(JobQueue.priority.asc(), JobQueue.scheduled_at.asc()).limit(limit).all()
            
            return [job.to_dict() for job in jobs]
            
        except Exception as e:
            print(f"Get pending jobs error: {e}")
            return []
    
    @staticmethod
    def update_job_status(job_id: str, status: str, result: Dict = None, error_message: str = None) -> bool:
        """Update job status"""
        try:
            job = JobQueue.query.filter_by(job_id=job_id).first()
            
            if not job:
                return False
            
            job.status = status
            
            if status == 'running':
                job.started_at = datetime.utcnow()
            elif status in ['completed', 'failed']:
                job.completed_at = datetime.utcnow()
                
                if result:
                    job.result = json.dumps(result)
                
                if error_message:
                    job.error_message = error_message
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Job status update error: {e}")
            return False
    
    @staticmethod
    def retry_failed_job(job_id: str) -> bool:
        """Retry a failed job"""
        try:
            job = JobQueue.query.filter_by(job_id=job_id).first()
            
            if not job or job.retry_count >= job.max_retries:
                return False
            
            job.status = 'pending'
            job.retry_count += 1
            job.scheduled_at = datetime.utcnow() + timedelta(minutes=job.retry_count * 5)  # Exponential backoff
            job.error_message = None
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Job retry error: {e}")
            return False

class WebhookProcessor:
    """Webhook event processing"""
    
    @staticmethod
    def store_webhook(event_id: str, source: str, event_type: str, payload: Dict, headers: Dict = None) -> bool:
        """Store webhook event"""
        try:
            webhook = WebhookEvent(
                event_id=event_id,
                source=source,
                event_type=event_type,
                payload=json.dumps(payload),
                headers=json.dumps(headers or {})
            )
            
            db.session.add(webhook)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Webhook store error: {e}")
            return False
    
    @staticmethod
    def get_unprocessed_webhooks(source: str = None, limit: int = 10) -> List[Dict]:
        """Get unprocessed webhook events"""
        try:
            query = WebhookEvent.query.filter_by(processed=False)
            
            if source:
                query = query.filter_by(source=source)
            
            webhooks = query.order_by(WebhookEvent.created_at.asc()).limit(limit).all()
            return [webhook.to_dict() for webhook in webhooks]
            
        except Exception as e:
            print(f"Get unprocessed webhooks error: {e}")
            return []
    
    @staticmethod
    def mark_webhook_processed(event_id: str, result: Dict = None) -> bool:
        """Mark webhook as processed"""
        try:
            webhook = WebhookEvent.query.filter_by(event_id=event_id).first()
            
            if not webhook:
                return False
            
            webhook.processed = True
            webhook.processed_at = datetime.utcnow()
            
            if result:
                webhook.processing_result = json.dumps(result)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Webhook mark processed error: {e}")
            return False

class AutonomyEngine:
    """Main autonomy engine for decision-making and self-extension"""
    
    def __init__(self):
        self.memory = MemoryManager()
        self.secrets = SecretManager()
        self.scheduler = JobScheduler()
        self.webhook_processor = WebhookProcessor()
    
    def create_autonomy_session(self, goal: str, metadata: Dict = None) -> str:
        """Create new autonomy session"""
        try:
            session_id = f"session_{uuid.uuid4().hex[:12]}"
            
            session = AutonomySession(
                session_id=session_id,
                goal=goal,
                session_metadata=json.dumps(metadata or {})
            )
            
            db.session.add(session)
            db.session.commit()
            
            # Store in memory for quick access
            self.memory.store(f"session:{session_id}", {
                'goal': goal,
                'status': 'active',
                'created_at': datetime.utcnow().isoformat()
            }, category='sessions')
            
            return session_id
            
        except Exception as e:
            db.session.rollback()
            print(f"Autonomy session creation error: {e}")
            return None
    
    def update_session_progress(self, session_id: str, progress: int, current_step: str = None) -> bool:
        """Update session progress"""
        try:
            session = AutonomySession.query.filter_by(session_id=session_id).first()
            
            if not session:
                return False
            
            session.progress = progress
            if current_step:
                session.current_step = current_step
            
            session.updated_at = datetime.utcnow()
            
            if progress >= 100:
                session.status = 'completed'
                session.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            # Update memory
            self.memory.store(f"session:{session_id}:progress", progress, category='sessions')
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Session progress update error: {e}")
            return False
    
    def make_autonomous_decision(self, context: Dict, options: List[Dict]) -> Dict:
        """Make autonomous decision based on context and options"""
        try:
            # Simple decision-making logic (can be enhanced with ML)
            decision_factors = {
                'priority': 0.4,
                'success_rate': 0.3,
                'resource_cost': 0.2,
                'risk_level': 0.1
            }
            
            best_option = None
            best_score = -1
            
            for option in options:
                score = 0
                
                # Calculate weighted score
                for factor, weight in decision_factors.items():
                    if factor in option:
                        score += option[factor] * weight
                
                if score > best_score:
                    best_score = score
                    best_option = option
            
            decision = {
                'selected_option': best_option,
                'confidence': best_score,
                'reasoning': f"Selected based on weighted scoring: {decision_factors}",
                'context': context,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store decision in memory
            decision_id = f"decision_{uuid.uuid4().hex[:8]}"
            self.memory.store(f"decision:{decision_id}", decision, category='decisions')
            
            return decision
            
        except Exception as e:
            print(f"Autonomous decision error: {e}")
            return {'error': str(e)}
    
    def self_extend_capability(self, capability_name: str, implementation: str, description: str = None) -> bool:
        """Self-extend capabilities by adding new functions"""
        try:
            # Store new capability
            capability = {
                'name': capability_name,
                'implementation': implementation,
                'description': description or f"Auto-generated capability: {capability_name}",
                'created_at': datetime.utcnow().isoformat(),
                'version': '1.0'
            }
            
            self.memory.store(f"capability:{capability_name}", capability, category='capabilities')
            
            # Schedule capability integration job
            job_id = self.scheduler.schedule_job(
                command='integrate_capability',
                parameters={
                    'capability_name': capability_name,
                    'implementation': implementation
                },
                job_type='self_extension',
                priority=3
            )
            
            return job_id is not None
            
        except Exception as e:
            print(f"Self-extend capability error: {e}")
            return False
    
    def analyze_performance(self) -> Dict:
        """Analyze system performance and suggest improvements"""
        try:
            # Get recent command logs
            recent_logs = CommandLog.query.filter(
                CommandLog.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).all()
            
            # Calculate metrics
            total_commands = len(recent_logs)
            successful_commands = len([log for log in recent_logs if log.status == 'success'])
            failed_commands = total_commands - successful_commands
            
            success_rate = (successful_commands / total_commands * 100) if total_commands > 0 else 0
            
            # Get average execution time
            execution_times = [log.execution_time for log in recent_logs if log.execution_time]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            # Analyze common failures
            failed_logs = [log for log in recent_logs if log.status != 'success']
            common_failures = {}
            for log in failed_logs:
                command = log.command
                common_failures[command] = common_failures.get(command, 0) + 1
            
            analysis = {
                'period': '24 hours',
                'total_commands': total_commands,
                'successful_commands': successful_commands,
                'failed_commands': failed_commands,
                'success_rate': round(success_rate, 2),
                'average_execution_time': round(avg_execution_time, 3),
                'common_failures': common_failures,
                'recommendations': self._generate_recommendations(success_rate, common_failures),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store analysis
            self.memory.store('performance_analysis', analysis, category='analytics', expires_in_hours=24)
            
            return analysis
            
        except Exception as e:
            print(f"Performance analysis error: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, success_rate: float, common_failures: Dict) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        if success_rate < 80:
            recommendations.append("Success rate is below 80%. Consider improving error handling and validation.")
        
        if common_failures:
            most_common = max(common_failures, key=common_failures.get)
            recommendations.append(f"Most common failure: {most_common}. Consider optimizing this command.")
        
        if success_rate > 95:
            recommendations.append("Excellent performance! Consider expanding capabilities or increasing complexity.")
        
        return recommendations

# Global instances
autonomy_engine = AutonomyEngine()
memory_manager = MemoryManager()
secret_manager = SecretManager()
job_scheduler = JobScheduler()
webhook_processor = WebhookProcessor()

