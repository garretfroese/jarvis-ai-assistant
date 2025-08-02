"""
Webhook Service for Jarvis AI Assistant
Handles incoming webhooks from external systems and triggers corresponding workflows.
"""

import os
import json
import hmac
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from flask import request
import ipaddress

from .workflow_engine import workflow_engine
from .logging_service import logging_service

@dataclass
class WebhookSource:
    """Webhook source configuration"""
    name: str
    secret_token: Optional[str]
    trusted_ips: List[str]
    signature_header: Optional[str]
    signature_prefix: Optional[str]
    rate_limit: int  # requests per minute
    workflow_mapping: Dict[str, str]  # event -> workflow_id

@dataclass
class WebhookRequest:
    """Incoming webhook request data"""
    source: str
    headers: Dict[str, str]
    payload: Dict[str, Any]
    ip_address: str
    timestamp: datetime
    signature: Optional[str]

class WebhookService:
    """Service for handling incoming webhooks and triggering workflows"""
    
    def __init__(self):
        self.webhook_sources: Dict[str, WebhookSource] = {}
        self.rate_limit_tracker: Dict[str, List[datetime]] = {}
        self.webhook_logs: List[Dict[str, Any]] = []
        
        # Initialize default webhook sources
        self._initialize_default_sources()
        
        print("✅ Webhook service initialized")
    
    def _initialize_default_sources(self):
        """Initialize default webhook source configurations"""
        
        # Slack webhook configuration
        self.webhook_sources['slack'] = WebhookSource(
            name='Slack',
            secret_token=os.getenv('SLACK_WEBHOOK_SECRET'),
            trusted_ips=['0.0.0.0/0'],  # Slack uses various IPs
            signature_header='X-Slack-Signature',
            signature_prefix='v0=',
            rate_limit=60,  # 60 requests per minute
            workflow_mapping={
                'message': 'slack_message_handler',
                'app_mention': 'slack_mention_handler',
                'reaction_added': 'slack_reaction_handler'
            }
        )
        
        # Calendly webhook configuration
        self.webhook_sources['calendly'] = WebhookSource(
            name='Calendly',
            secret_token=os.getenv('CALENDLY_WEBHOOK_SECRET'),
            trusted_ips=['0.0.0.0/0'],  # Calendly uses various IPs
            signature_header='Calendly-Webhook-Signature',
            signature_prefix='',
            rate_limit=30,  # 30 requests per minute
            workflow_mapping={
                'invitee.created': 'send_followup_email',
                'invitee.canceled': 'handle_cancellation',
                'invitee.rescheduled': 'handle_reschedule'
            }
        )
        
        # Stripe webhook configuration
        self.webhook_sources['stripe'] = WebhookSource(
            name='Stripe',
            secret_token=os.getenv('STRIPE_WEBHOOK_SECRET'),
            trusted_ips=['0.0.0.0/0'],  # Stripe uses various IPs
            signature_header='Stripe-Signature',
            signature_prefix='',
            rate_limit=100,  # 100 requests per minute
            workflow_mapping={
                'payment_intent.succeeded': 'handle_payment_success',
                'payment_intent.payment_failed': 'handle_payment_failure',
                'customer.subscription.created': 'handle_new_subscription'
            }
        )
        
        # GitHub webhook configuration
        self.webhook_sources['github'] = WebhookSource(
            name='GitHub',
            secret_token=os.getenv('GITHUB_WEBHOOK_SECRET'),
            trusted_ips=['140.82.112.0/20', '185.199.108.0/22', '192.30.252.0/22'],
            signature_header='X-Hub-Signature-256',
            signature_prefix='sha256=',
            rate_limit=120,  # 120 requests per minute
            workflow_mapping={
                'push': 'handle_code_push',
                'pull_request': 'handle_pull_request',
                'issues': 'handle_issue_event'
            }
        )
        
        # Generic webhook configuration
        self.webhook_sources['generic'] = WebhookSource(
            name='Generic',
            secret_token=os.getenv('GENERIC_WEBHOOK_SECRET'),
            trusted_ips=['0.0.0.0/0'],
            signature_header=None,
            signature_prefix='',
            rate_limit=60,
            workflow_mapping={
                'trigger': 'generic_webhook_handler'
            }
        )
    
    def process_webhook(self, source: str, headers: Dict[str, str], payload: Dict[str, Any], ip_address: str) -> Dict[str, Any]:
        """Process incoming webhook request"""
        
        webhook_request = WebhookRequest(
            source=source,
            headers=headers,
            payload=payload,
            ip_address=ip_address,
            timestamp=datetime.now(),
            signature=headers.get('X-Hub-Signature-256') or headers.get('X-Slack-Signature') or headers.get('Calendly-Webhook-Signature') or headers.get('Stripe-Signature')
        )
        
        try:
            # Validate webhook source
            if source not in self.webhook_sources:
                raise ValueError(f"Unknown webhook source: {source}")
            
            webhook_source = self.webhook_sources[source]
            
            # Check rate limiting
            if not self._check_rate_limit(source, webhook_source.rate_limit):
                raise ValueError(f"Rate limit exceeded for source: {source}")
            
            # Validate IP address
            if not self._validate_ip_address(ip_address, webhook_source.trusted_ips):
                raise ValueError(f"Untrusted IP address: {ip_address}")
            
            # Validate signature
            if webhook_source.secret_token and not self._validate_signature(webhook_request, webhook_source):
                raise ValueError("Invalid webhook signature")
            
            # Determine event type and workflow
            event_type = self._extract_event_type(webhook_request, webhook_source)
            workflow_id = webhook_source.workflow_mapping.get(event_type)
            
            if not workflow_id:
                raise ValueError(f"No workflow mapping for event type: {event_type}")
            
            # Prepare workflow context
            context = {
                'webhook_source': source,
                'event_type': event_type,
                'payload': payload,
                'headers': headers,
                'ip_address': ip_address,
                'timestamp': webhook_request.timestamp.isoformat()
            }
            
            # Execute workflow
            execution_id = workflow_engine.execute_workflow(workflow_id, context)
            
            # Log successful webhook processing
            self._log_webhook_event(webhook_request, 'success', {
                'event_type': event_type,
                'workflow_id': workflow_id,
                'execution_id': execution_id
            })
            
            return {
                'status': 'success',
                'message': 'Webhook processed successfully',
                'event_type': event_type,
                'workflow_id': workflow_id,
                'execution_id': execution_id
            }
            
        except Exception as e:
            # Log failed webhook processing
            self._log_webhook_event(webhook_request, 'error', {
                'error': str(e)
            })
            
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': webhook_request.timestamp.isoformat()
            }
    
    def _check_rate_limit(self, source: str, limit: int) -> bool:
        """Check if request is within rate limit"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Initialize tracking for source if not exists
        if source not in self.rate_limit_tracker:
            self.rate_limit_tracker[source] = []
        
        # Remove old requests
        self.rate_limit_tracker[source] = [
            timestamp for timestamp in self.rate_limit_tracker[source]
            if timestamp > minute_ago
        ]
        
        # Check if under limit
        if len(self.rate_limit_tracker[source]) >= limit:
            return False
        
        # Add current request
        self.rate_limit_tracker[source].append(now)
        return True
    
    def _validate_ip_address(self, ip_address: str, trusted_ips: List[str]) -> bool:
        """Validate if IP address is in trusted list"""
        if not trusted_ips or '0.0.0.0/0' in trusted_ips:
            return True
        
        try:
            ip = ipaddress.ip_address(ip_address)
            for trusted_ip in trusted_ips:
                if '/' in trusted_ip:
                    # CIDR notation
                    if ip in ipaddress.ip_network(trusted_ip, strict=False):
                        return True
                else:
                    # Single IP
                    if ip == ipaddress.ip_address(trusted_ip):
                        return True
            return False
        except Exception:
            return False
    
    def _validate_signature(self, webhook_request: WebhookRequest, webhook_source: WebhookSource) -> bool:
        """Validate webhook signature"""
        if not webhook_source.secret_token or not webhook_source.signature_header:
            return True
        
        signature = webhook_request.headers.get(webhook_source.signature_header)
        if not signature:
            return False
        
        # Remove prefix if present
        if webhook_source.signature_prefix and signature.startswith(webhook_source.signature_prefix):
            signature = signature[len(webhook_source.signature_prefix):]
        
        # Calculate expected signature
        payload_bytes = json.dumps(webhook_request.payload, separators=(',', ':')).encode('utf-8')
        
        if webhook_source.name == 'Slack':
            # Slack uses timestamp + body
            timestamp = webhook_request.headers.get('X-Slack-Request-Timestamp', '')
            sig_basestring = f"v0:{timestamp}:{payload_bytes.decode('utf-8')}"
            expected_signature = hmac.new(
                webhook_source.secret_token.encode('utf-8'),
                sig_basestring.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
        elif webhook_source.name == 'GitHub':
            # GitHub uses SHA256 HMAC
            expected_signature = hmac.new(
                webhook_source.secret_token.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
        elif webhook_source.name == 'Stripe':
            # Stripe uses SHA256 HMAC with timestamp
            timestamp = webhook_request.headers.get('X-Stripe-Timestamp', '')
            sig_basestring = f"{timestamp}.{payload_bytes.decode('utf-8')}"
            expected_signature = hmac.new(
                webhook_source.secret_token.encode('utf-8'),
                sig_basestring.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
        else:
            # Generic HMAC SHA256
            expected_signature = hmac.new(
                webhook_source.secret_token.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _extract_event_type(self, webhook_request: WebhookRequest, webhook_source: WebhookSource) -> str:
        """Extract event type from webhook payload"""
        payload = webhook_request.payload
        
        if webhook_source.name == 'Slack':
            return payload.get('type', 'unknown')
        elif webhook_source.name == 'Calendly':
            return payload.get('event', 'unknown')
        elif webhook_source.name == 'Stripe':
            return payload.get('type', 'unknown')
        elif webhook_source.name == 'GitHub':
            return webhook_request.headers.get('X-GitHub-Event', 'unknown')
        else:
            return payload.get('event_type', payload.get('type', 'trigger'))
    
    def _log_webhook_event(self, webhook_request: WebhookRequest, status: str, details: Dict[str, Any]):
        """Log webhook event"""
        log_entry = {
            'timestamp': webhook_request.timestamp.isoformat(),
            'source': webhook_request.source,
            'ip_address': webhook_request.ip_address,
            'status': status,
            'details': details,
            'payload_size': len(json.dumps(webhook_request.payload))
        }
        
        self.webhook_logs.append(log_entry)
        
        # Keep only last 1000 webhook logs
        if len(self.webhook_logs) > 1000:
            self.webhook_logs = self.webhook_logs[-1000:]
        
        # Log to main logging service
        logging_service.log_activity(
            'system',
            'webhook_received',
            {
                'source': webhook_request.source,
                'status': status,
                'ip_address': webhook_request.ip_address,
                **details
            }
        )
    
    def get_webhook_logs(self, source: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get webhook logs"""
        logs = self.webhook_logs
        
        if source:
            logs = [log for log in logs if log['source'] == source]
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return logs[:limit] if limit else logs
    
    def get_webhook_sources(self) -> List[Dict[str, Any]]:
        """Get configured webhook sources"""
        return [
            {
                'name': source.name,
                'id': source_id,
                'rate_limit': source.rate_limit,
                'trusted_ips': source.trusted_ips,
                'has_secret': bool(source.secret_token),
                'workflow_mappings': source.workflow_mapping
            }
            for source_id, source in self.webhook_sources.items()
        ]
    
    def add_webhook_source(self, source_id: str, config: Dict[str, Any]) -> bool:
        """Add a new webhook source configuration"""
        try:
            webhook_source = WebhookSource(
                name=config['name'],
                secret_token=config.get('secret_token'),
                trusted_ips=config.get('trusted_ips', ['0.0.0.0/0']),
                signature_header=config.get('signature_header'),
                signature_prefix=config.get('signature_prefix', ''),
                rate_limit=config.get('rate_limit', 60),
                workflow_mapping=config.get('workflow_mapping', {})
            )
            
            self.webhook_sources[source_id] = webhook_source
            return True
            
        except Exception as e:
            print(f"Error adding webhook source: {e}")
            return False
    
    def update_webhook_source(self, source_id: str, config: Dict[str, Any]) -> bool:
        """Update webhook source configuration"""
        if source_id not in self.webhook_sources:
            return False
        
        try:
            source = self.webhook_sources[source_id]
            
            if 'name' in config:
                source.name = config['name']
            if 'secret_token' in config:
                source.secret_token = config['secret_token']
            if 'trusted_ips' in config:
                source.trusted_ips = config['trusted_ips']
            if 'signature_header' in config:
                source.signature_header = config['signature_header']
            if 'signature_prefix' in config:
                source.signature_prefix = config['signature_prefix']
            if 'rate_limit' in config:
                source.rate_limit = config['rate_limit']
            if 'workflow_mapping' in config:
                source.workflow_mapping = config['workflow_mapping']
            
            return True
            
        except Exception as e:
            print(f"Error updating webhook source: {e}")
            return False
    
    def delete_webhook_source(self, source_id: str) -> bool:
        """Delete webhook source configuration"""
        if source_id in self.webhook_sources:
            del self.webhook_sources[source_id]
            return True
        return False
    
    def get_webhook_statistics(self) -> Dict[str, Any]:
        """Get webhook statistics"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        recent_logs = [log for log in self.webhook_logs if datetime.fromisoformat(log['timestamp']) > hour_ago]
        daily_logs = [log for log in self.webhook_logs if datetime.fromisoformat(log['timestamp']) > day_ago]
        
        # Count by source
        source_counts = {}
        for log in daily_logs:
            source = log['source']
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Count by status
        status_counts = {}
        for log in daily_logs:
            status = log['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'total_webhooks_24h': len(daily_logs),
            'total_webhooks_1h': len(recent_logs),
            'success_rate_24h': (status_counts.get('success', 0) / len(daily_logs) * 100) if daily_logs else 0,
            'source_distribution': source_counts,
            'status_distribution': status_counts,
            'configured_sources': len(self.webhook_sources),
            'rate_limit_status': {
                source_id: len(timestamps) for source_id, timestamps in self.rate_limit_tracker.items()
            }
        }

# Global instance
webhook_service = WebhookService()

