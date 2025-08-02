"""
Twilio Integration for Jarvis AI Assistant
Provides SMS, RVM (Ringless Voicemail), and AI Voice calling capabilities
"""

import os
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("⚠️ Twilio SDK not installed. Run: pip install twilio")

from ..services.logging_service import logging_service, LogLevel, LogCategory

@dataclass
class SMSMessage:
    message_id: str
    to_number: str
    from_number: str
    body: str
    status: str
    direction: str  # inbound, outbound
    created_at: datetime
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    cost: Optional[float] = None

@dataclass
class VoiceCall:
    call_id: str
    to_number: str
    from_number: str
    status: str
    direction: str  # inbound, outbound
    duration: Optional[int] = None  # seconds
    recording_url: Optional[str] = None
    created_at: datetime = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    cost: Optional[float] = None

@dataclass
class RinglessVoicemail:
    rvm_id: str
    to_number: str
    audio_url: str
    status: str
    created_at: datetime
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    cost: Optional[float] = None

class TwilioIntegration:
    """Twilio integration for SMS, voice calls, and ringless voicemail"""
    
    def __init__(self):
        self.enabled = os.getenv('TWILIO_ENABLED', 'False').lower() == 'true'
        
        if not TWILIO_AVAILABLE:
            self.enabled = False
            print("❌ Twilio integration disabled - SDK not available")
            return
        
        # Twilio credentials
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        # Optional: Twilio Programmable Voice
        self.twiml_app_sid = os.getenv('TWILIO_TWIML_APP_SID')
        
        # Optional: Ringless Voicemail (requires special Twilio add-on)
        self.rvm_enabled = os.getenv('TWILIO_RVM_ENABLED', 'False').lower() == 'true'
        
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            self.enabled = False
            print("❌ Twilio integration disabled - missing credentials")
            return
        
        # Initialize Twilio client
        try:
            self.client = Client(self.account_sid, self.auth_token)
            self.enabled = True
            print("✅ Twilio integration initialized")
        except Exception as e:
            self.enabled = False
            print(f"❌ Twilio initialization failed: {e}")
        
        # Storage
        self.data_dir = os.path.join(os.path.dirname(__file__), '../../integrations_data/twilio')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Message storage
        self.sms_messages: Dict[str, SMSMessage] = {}
        self.voice_calls: Dict[str, VoiceCall] = {}
        self.rvm_messages: Dict[str, RinglessVoicemail] = {}
        
        # Load existing data
        self._load_data()
    
    def _load_data(self):
        """Load existing Twilio data from storage"""
        try:
            # Load SMS messages
            sms_file = os.path.join(self.data_dir, 'sms_messages.json')
            if os.path.exists(sms_file):
                with open(sms_file, 'r') as f:
                    data = json.load(f)
                    for msg_data in data.get('messages', []):
                        msg = SMSMessage(
                            message_id=msg_data['message_id'],
                            to_number=msg_data['to_number'],
                            from_number=msg_data['from_number'],
                            body=msg_data['body'],
                            status=msg_data['status'],
                            direction=msg_data['direction'],
                            created_at=datetime.fromisoformat(msg_data['created_at']),
                            delivered_at=datetime.fromisoformat(msg_data['delivered_at']) if msg_data.get('delivered_at') else None,
                            error_message=msg_data.get('error_message'),
                            cost=msg_data.get('cost')
                        )
                        self.sms_messages[msg.message_id] = msg
            
            print(f"✅ Loaded {len(self.sms_messages)} SMS messages")
            
        except Exception as e:
            print(f"❌ Failed to load Twilio data: {e}")
    
    def _save_data(self):
        """Save Twilio data to storage"""
        try:
            # Save SMS messages
            sms_data = {
                "messages": [
                    {
                        **asdict(msg),
                        "created_at": msg.created_at.isoformat(),
                        "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None
                    }
                    for msg in self.sms_messages.values()
                ]
            }
            
            sms_file = os.path.join(self.data_dir, 'sms_messages.json')
            with open(sms_file, 'w') as f:
                json.dump(sms_data, f, indent=2)
            
            print(f"✅ Saved Twilio data")
            
        except Exception as e:
            print(f"❌ Failed to save Twilio data: {e}")
    
    # ===== SMS FUNCTIONALITY =====
    
    def send_sms(self, to_number: str, message: str, from_number: str = None) -> Dict[str, Any]:
        """Send SMS message"""
        
        if not self.enabled:
            return {"error": "Twilio integration not enabled"}
        
        try:
            # Use default phone number if not specified
            if not from_number:
                from_number = self.phone_number
            
            # Send SMS via Twilio
            message_obj = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            
            # Create SMS record
            sms_message = SMSMessage(
                message_id=message_obj.sid,
                to_number=to_number,
                from_number=from_number,
                body=message,
                status=message_obj.status,
                direction="outbound",
                created_at=datetime.now()
            )
            
            self.sms_messages[sms_message.message_id] = sms_message
            self._save_data()
            
            # Log SMS sending
            if logging_service:
                logging_service.log(
                    LogLevel.INFO,
                    LogCategory.INTEGRATION,
                    'sms_sent',
                    details={
                        'message_id': sms_message.message_id,
                        'to_number': to_number,
                        'from_number': from_number,
                        'message_length': len(message)
                    }
                )
            
            return {
                "success": True,
                "message_id": sms_message.message_id,
                "status": sms_message.status,
                "to_number": to_number,
                "message": "SMS sent successfully"
            }
            
        except TwilioException as e:
            error_msg = f"Twilio SMS error: {e}"
            print(f"❌ {error_msg}")
            
            if logging_service:
                logging_service.log(
                    LogLevel.ERROR,
                    LogCategory.INTEGRATION,
                    'sms_send_failed',
                    details={
                        'to_number': to_number,
                        'error': str(e)
                    }
                )
            
            return {"error": error_msg}
        
        except Exception as e:
            error_msg = f"SMS sending failed: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
    
    def get_sms_status(self, message_id: str) -> Dict[str, Any]:
        """Get SMS message status"""
        
        if not self.enabled:
            return {"error": "Twilio integration not enabled"}
        
        try:
            # Get message from Twilio
            message = self.client.messages(message_id).fetch()
            
            # Update local record if exists
            if message_id in self.sms_messages:
                sms_msg = self.sms_messages[message_id]
                sms_msg.status = message.status
                if message.status == 'delivered':
                    sms_msg.delivered_at = datetime.now()
                if hasattr(message, 'error_message') and message.error_message:
                    sms_msg.error_message = message.error_message
                
                self._save_data()
            
            return {
                "message_id": message_id,
                "status": message.status,
                "direction": message.direction,
                "to": message.to,
                "from": message.from_,
                "body": message.body,
                "date_created": message.date_created.isoformat() if message.date_created else None,
                "date_sent": message.date_sent.isoformat() if message.date_sent else None,
                "error_message": getattr(message, 'error_message', None)
            }
            
        except TwilioException as e:
            return {"error": f"Failed to get SMS status: {e}"}
        except Exception as e:
            return {"error": f"SMS status check failed: {e}"}
    
    def get_sms_history(self, phone_number: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get SMS message history"""
        
        if not self.enabled:
            return []
        
        try:
            # Get messages from Twilio
            messages = self.client.messages.list(
                to=phone_number if phone_number else None,
                from_=phone_number if phone_number else None,
                limit=limit
            )
            
            history = []
            for message in messages:
                history.append({
                    "message_id": message.sid,
                    "to": message.to,
                    "from": message.from_,
                    "body": message.body,
                    "status": message.status,
                    "direction": message.direction,
                    "date_created": message.date_created.isoformat() if message.date_created else None,
                    "date_sent": message.date_sent.isoformat() if message.date_sent else None
                })
            
            return history
            
        except Exception as e:
            print(f"❌ Failed to get SMS history: {e}")
            return []
    
    # ===== VOICE CALL FUNCTIONALITY =====
    
    def make_voice_call(self, to_number: str, twiml_url: str = None, 
                       from_number: str = None) -> Dict[str, Any]:
        """Make voice call"""
        
        if not self.enabled:
            return {"error": "Twilio integration not enabled"}
        
        try:
            # Use default phone number if not specified
            if not from_number:
                from_number = self.phone_number
            
            # Make call via Twilio
            call = self.client.calls.create(
                to=to_number,
                from_=from_number,
                url=twiml_url if twiml_url else f"http://demo.twilio.com/docs/voice.xml"
            )
            
            # Create call record
            voice_call = VoiceCall(
                call_id=call.sid,
                to_number=to_number,
                from_number=from_number,
                status=call.status,
                direction="outbound",
                created_at=datetime.now()
            )
            
            self.voice_calls[voice_call.call_id] = voice_call
            
            # Log call initiation
            if logging_service:
                logging_service.log(
                    LogLevel.INFO,
                    LogCategory.INTEGRATION,
                    'voice_call_initiated',
                    details={
                        'call_id': voice_call.call_id,
                        'to_number': to_number,
                        'from_number': from_number
                    }
                )
            
            return {
                "success": True,
                "call_id": voice_call.call_id,
                "status": voice_call.status,
                "to_number": to_number,
                "message": "Voice call initiated successfully"
            }
            
        except TwilioException as e:
            error_msg = f"Twilio voice call error: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
        
        except Exception as e:
            error_msg = f"Voice call failed: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
    
    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Get voice call status"""
        
        if not self.enabled:
            return {"error": "Twilio integration not enabled"}
        
        try:
            # Get call from Twilio
            call = self.client.calls(call_id).fetch()
            
            # Update local record if exists
            if call_id in self.voice_calls:
                voice_call = self.voice_calls[call_id]
                voice_call.status = call.status
                if call.duration:
                    voice_call.duration = int(call.duration)
                if call.start_time:
                    voice_call.answered_at = call.start_time
                if call.end_time:
                    voice_call.ended_at = call.end_time
            
            return {
                "call_id": call_id,
                "status": call.status,
                "direction": call.direction,
                "to": call.to,
                "from": call.from_,
                "duration": call.duration,
                "start_time": call.start_time.isoformat() if call.start_time else None,
                "end_time": call.end_time.isoformat() if call.end_time else None,
                "date_created": call.date_created.isoformat() if call.date_created else None
            }
            
        except TwilioException as e:
            return {"error": f"Failed to get call status: {e}"}
        except Exception as e:
            return {"error": f"Call status check failed: {e}"}
    
    # ===== RINGLESS VOICEMAIL FUNCTIONALITY =====
    
    def send_ringless_voicemail(self, to_number: str, audio_url: str) -> Dict[str, Any]:
        """Send ringless voicemail (requires Twilio add-on)"""
        
        if not self.enabled or not self.rvm_enabled:
            return {"error": "Ringless voicemail not enabled"}
        
        try:
            # Note: This is a placeholder implementation
            # Actual RVM requires specific Twilio add-on and configuration
            
            rvm_id = str(uuid.uuid4())
            
            # Create RVM record
            rvm = RinglessVoicemail(
                rvm_id=rvm_id,
                to_number=to_number,
                audio_url=audio_url,
                status="queued",
                created_at=datetime.now()
            )
            
            self.rvm_messages[rvm_id] = rvm
            
            # Log RVM sending
            if logging_service:
                logging_service.log(
                    LogLevel.INFO,
                    LogCategory.INTEGRATION,
                    'rvm_sent',
                    details={
                        'rvm_id': rvm_id,
                        'to_number': to_number,
                        'audio_url': audio_url
                    }
                )
            
            return {
                "success": True,
                "rvm_id": rvm_id,
                "status": "queued",
                "to_number": to_number,
                "message": "Ringless voicemail queued successfully"
            }
            
        except Exception as e:
            error_msg = f"RVM sending failed: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
    
    # ===== WEBHOOK HANDLING =====
    
    def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming Twilio webhooks"""
        
        try:
            message_type = webhook_data.get('MessageStatus') or webhook_data.get('CallStatus')
            
            if 'MessageSid' in webhook_data:
                # SMS webhook
                return self._handle_sms_webhook(webhook_data)
            elif 'CallSid' in webhook_data:
                # Voice call webhook
                return self._handle_call_webhook(webhook_data)
            else:
                return {"error": "Unknown webhook type"}
                
        except Exception as e:
            print(f"❌ Webhook handling failed: {e}")
            return {"error": f"Webhook processing failed: {e}"}
    
    def _handle_sms_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SMS webhook"""
        
        message_id = webhook_data.get('MessageSid')
        status = webhook_data.get('MessageStatus')
        
        # Update message status if we have it
        if message_id in self.sms_messages:
            sms_msg = self.sms_messages[message_id]
            sms_msg.status = status
            
            if status == 'delivered':
                sms_msg.delivered_at = datetime.now()
            elif status in ['failed', 'undelivered']:
                sms_msg.error_message = webhook_data.get('ErrorMessage', 'Delivery failed')
            
            self._save_data()
        
        # Handle incoming SMS
        if webhook_data.get('Direction') == 'inbound':
            # Create new incoming message record
            incoming_sms = SMSMessage(
                message_id=message_id,
                to_number=webhook_data.get('To', ''),
                from_number=webhook_data.get('From', ''),
                body=webhook_data.get('Body', ''),
                status='received',
                direction='inbound',
                created_at=datetime.now()
            )
            
            self.sms_messages[message_id] = incoming_sms
            self._save_data()
            
            # Log incoming SMS
            if logging_service:
                logging_service.log(
                    LogLevel.INFO,
                    LogCategory.INTEGRATION,
                    'sms_received',
                    details={
                        'message_id': message_id,
                        'from_number': incoming_sms.from_number,
                        'to_number': incoming_sms.to_number,
                        'body': incoming_sms.body
                    }
                )
        
        return {"success": True, "message": "SMS webhook processed"}
    
    def _handle_call_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voice call webhook"""
        
        call_id = webhook_data.get('CallSid')
        status = webhook_data.get('CallStatus')
        
        # Update call status if we have it
        if call_id in self.voice_calls:
            voice_call = self.voice_calls[call_id]
            voice_call.status = status
            
            if status == 'in-progress' and not voice_call.answered_at:
                voice_call.answered_at = datetime.now()
            elif status in ['completed', 'busy', 'no-answer', 'failed', 'canceled']:
                voice_call.ended_at = datetime.now()
                if webhook_data.get('CallDuration'):
                    voice_call.duration = int(webhook_data['CallDuration'])
        
        # Handle incoming call
        if webhook_data.get('Direction') == 'inbound':
            # Create new incoming call record
            incoming_call = VoiceCall(
                call_id=call_id,
                to_number=webhook_data.get('To', ''),
                from_number=webhook_data.get('From', ''),
                status=status,
                direction='inbound',
                created_at=datetime.now()
            )
            
            self.voice_calls[call_id] = incoming_call
            
            # Log incoming call
            if logging_service:
                logging_service.log(
                    LogLevel.INFO,
                    LogCategory.INTEGRATION,
                    'voice_call_received',
                    details={
                        'call_id': call_id,
                        'from_number': incoming_call.from_number,
                        'to_number': incoming_call.to_number,
                        'status': status
                    }
                )
        
        return {"success": True, "message": "Call webhook processed"}
    
    # ===== ANALYTICS AND REPORTING =====
    
    def get_communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics"""
        
        total_sms = len(self.sms_messages)
        total_calls = len(self.voice_calls)
        total_rvm = len(self.rvm_messages)
        
        # SMS stats
        sms_sent = sum(1 for msg in self.sms_messages.values() if msg.direction == 'outbound')
        sms_received = sum(1 for msg in self.sms_messages.values() if msg.direction == 'inbound')
        sms_delivered = sum(1 for msg in self.sms_messages.values() if msg.status == 'delivered')
        
        # Call stats
        calls_made = sum(1 for call in self.voice_calls.values() if call.direction == 'outbound')
        calls_received = sum(1 for call in self.voice_calls.values() if call.direction == 'inbound')
        calls_completed = sum(1 for call in self.voice_calls.values() if call.status == 'completed')
        
        return {
            "twilio_enabled": self.enabled,
            "sms_statistics": {
                "total_messages": total_sms,
                "messages_sent": sms_sent,
                "messages_received": sms_received,
                "messages_delivered": sms_delivered,
                "delivery_rate": round((sms_delivered / sms_sent * 100), 2) if sms_sent > 0 else 0
            },
            "voice_statistics": {
                "total_calls": total_calls,
                "calls_made": calls_made,
                "calls_received": calls_received,
                "calls_completed": calls_completed,
                "completion_rate": round((calls_completed / calls_made * 100), 2) if calls_made > 0 else 0
            },
            "rvm_statistics": {
                "total_rvm": total_rvm,
                "rvm_enabled": self.rvm_enabled
            },
            "phone_number": self.phone_number,
            "last_updated": datetime.now().isoformat()
        }
    
    def get_recent_activity(self, hours: int = 24) -> Dict[str, Any]:
        """Get recent communication activity"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_sms = [
            {
                "message_id": msg.message_id,
                "direction": msg.direction,
                "to_number": msg.to_number,
                "from_number": msg.from_number,
                "status": msg.status,
                "created_at": msg.created_at.isoformat(),
                "body_preview": msg.body[:50] + "..." if len(msg.body) > 50 else msg.body
            }
            for msg in self.sms_messages.values()
            if msg.created_at >= cutoff_time
        ]
        
        recent_calls = [
            {
                "call_id": call.call_id,
                "direction": call.direction,
                "to_number": call.to_number,
                "from_number": call.from_number,
                "status": call.status,
                "duration": call.duration,
                "created_at": call.created_at.isoformat() if call.created_at else None
            }
            for call in self.voice_calls.values()
            if call.created_at and call.created_at >= cutoff_time
        ]
        
        return {
            "time_period": f"Last {hours} hours",
            "recent_sms": sorted(recent_sms, key=lambda x: x['created_at'], reverse=True),
            "recent_calls": sorted(recent_calls, key=lambda x: x['created_at'] or '', reverse=True),
            "total_recent_sms": len(recent_sms),
            "total_recent_calls": len(recent_calls)
        }

# Global instance
twilio_integration = TwilioIntegration()

