"""
AI-Powered Risk Filter for Jarvis AI Assistant
Safety interceptor layer that analyzes commands for potential security risks.
"""

import re
import json
import openai
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import hashlib

from .logging_service import logging_service

class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskCategory(Enum):
    DELETION = "deletion"
    OVERWRITE = "overwrite"
    EXTERNAL_TRANSMISSION = "external_transmission"
    FINANCIAL = "financial"
    SYSTEM_ACCESS = "system_access"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    MALICIOUS_CODE = "malicious_code"
    SUSPICIOUS_FILE = "suspicious_file"
    UNAUTHORIZED_ACCESS = "unauthorized_access"

@dataclass
class RiskAssessment:
    """Result of risk assessment"""
    risk_level: RiskLevel
    risk_categories: List[RiskCategory]
    confidence: float
    reasoning: str
    blocked: bool
    recommendations: List[str]
    metadata: Dict[str, Any]

@dataclass
class SecurityEvent:
    """Security event for logging"""
    timestamp: datetime
    user_id: str
    command: str
    risk_assessment: RiskAssessment
    action_taken: str
    ip_address: Optional[str] = None

class RiskFilter:
    """AI-powered safety interceptor for command analysis"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI()
        self.security_events: List[SecurityEvent] = []
        self.risk_patterns = self._initialize_risk_patterns()
        self.blocked_commands_cache = set()
        
        print("✅ Risk filter initialized")
    
    def _initialize_risk_patterns(self) -> Dict[RiskCategory, List[str]]:
        """Initialize risk detection patterns"""
        return {
            RiskCategory.DELETION: [
                r'\b(?:delete|remove|rm|del|erase|wipe|destroy)\b',
                r'\b(?:drop|truncate|clear)\s+(?:table|database|collection)\b',
                r'--force\b',
                r'\brm\s+-rf\b'
            ],
            
            RiskCategory.OVERWRITE: [
                r'\b(?:overwrite|replace|update|modify)\b.*\b(?:all|everything|entire)\b',
                r'>\s*[^>]',  # Shell redirection
                r'\bmv\b.*\b(?:replace|overwrite)\b'
            ],
            
            RiskCategory.EXTERNAL_TRANSMISSION: [
                r'\b(?:send|email|upload|post|transmit|export)\b.*\b(?:to|@)\b',
                r'\bcurl\b.*\b(?:POST|PUT)\b',
                r'\bwget\b.*\b(?:--post|--upload)\b',
                r'\b(?:ftp|sftp|scp)\b.*\b(?:put|upload)\b'
            ],
            
            RiskCategory.FINANCIAL: [
                r'\b(?:payment|charge|bill|invoice|transaction|transfer)\b',
                r'\b(?:credit|debit|bank|account)\s+(?:card|number)\b',
                r'\b(?:stripe|paypal|venmo|cashapp)\b',
                r'\$\d+(?:\.\d{2})?'
            ],
            
            RiskCategory.SYSTEM_ACCESS: [
                r'\b(?:sudo|su|admin|root|administrator)\b',
                r'\b(?:passwd|password|credentials|auth)\b',
                r'\b(?:ssh|telnet|rdp|vnc)\b',
                r'\b(?:chmod|chown|chgrp)\b.*\b(?:777|666)\b'
            ],
            
            RiskCategory.DATA_EXFILTRATION: [
                r'\b(?:dump|export|backup|copy)\b.*\b(?:database|db|data)\b',
                r'\b(?:select|extract)\b.*\b(?:password|secret|key|token)\b',
                r'\bbase64\b.*\b(?:encode|decode)\b',
                r'\b(?:zip|tar|compress)\b.*\b(?:sensitive|confidential)\b'
            ],
            
            RiskCategory.PRIVILEGE_ESCALATION: [
                r'\b(?:escalate|elevate|privilege|permission)\b',
                r'\b(?:setuid|setgid|sticky)\b',
                r'\b(?:exploit|vulnerability|CVE)\b'
            ],
            
            RiskCategory.MALICIOUS_CODE: [
                r'\b(?:eval|exec|system|shell_exec)\b',
                r'\b(?:injection|xss|csrf|sqli)\b',
                r'\b(?:malware|virus|trojan|backdoor)\b',
                r'<script[^>]*>.*</script>',
                r'\b(?:buffer\s+overflow|heap\s+spray)\b'
            ],
            
            RiskCategory.SUSPICIOUS_FILE: [
                r'\b(?:\.exe|\.bat|\.cmd|\.scr|\.pif|\.com)\b',
                r'\b(?:\.sh|\.bash|\.zsh|\.fish)\b',
                r'\b(?:\.ps1|\.psm1|\.psd1)\b',
                r'\b(?:\.jar|\.war|\.ear)\b'
            ],
            
            RiskCategory.UNAUTHORIZED_ACCESS: [
                r'\b(?:hack|crack|break|bypass|circumvent)\b',
                r'\b(?:brute\s+force|dictionary\s+attack)\b',
                r'\b(?:unauthorized|illegal|forbidden)\b'
            ]
        }
    
    def assess_risk(self, command: str, user_id: str, context: Dict[str, Any] = None, ip_address: str = None) -> RiskAssessment:
        """Assess the risk level of a command"""
        try:
            # Quick pattern-based assessment
            pattern_assessment = self._pattern_based_assessment(command)
            
            # AI-powered deep assessment for medium+ risk
            if pattern_assessment.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]:
                ai_assessment = self._ai_risk_assessment(command, context or {})
                # Use the higher risk assessment
                if ai_assessment.risk_level.value > pattern_assessment.risk_level.value:
                    final_assessment = ai_assessment
                else:
                    final_assessment = pattern_assessment
            else:
                final_assessment = pattern_assessment
            
            # Determine if command should be blocked
            final_assessment.blocked = self._should_block_command(final_assessment, user_id)
            
            # Log security event
            security_event = SecurityEvent(
                timestamp=datetime.now(),
                user_id=user_id,
                command=command[:200],  # Truncate for logging
                risk_assessment=final_assessment,
                action_taken="blocked" if final_assessment.blocked else "allowed",
                ip_address=ip_address
            )
            
            self._log_security_event(security_event)
            
            # Send admin notification for high-risk events
            if final_assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                self._send_admin_notification(security_event)
            
            return final_assessment
            
        except Exception as e:
            # On error, default to safe but log the issue
            return RiskAssessment(
                risk_level=RiskLevel.SAFE,
                risk_categories=[],
                confidence=0.0,
                reasoning=f"Risk assessment failed: {str(e)}",
                blocked=False,
                recommendations=["Manual review recommended due to assessment error"],
                metadata={"error": str(e)}
            )
    
    def _pattern_based_assessment(self, command: str) -> RiskAssessment:
        """Perform pattern-based risk assessment"""
        command_lower = command.lower()
        detected_categories = []
        risk_scores = []
        
        for category, patterns in self.risk_patterns.items():
            category_score = 0
            for pattern in patterns:
                if re.search(pattern, command_lower, re.IGNORECASE):
                    category_score += 1
            
            if category_score > 0:
                detected_categories.append(category)
                # Normalize score (max 1.0 per category)
                risk_scores.append(min(category_score / len(patterns), 1.0))
        
        # Calculate overall risk level
        if not detected_categories:
            risk_level = RiskLevel.SAFE
            confidence = 0.9
        else:
            avg_score = sum(risk_scores) / len(risk_scores)
            if avg_score >= 0.8:
                risk_level = RiskLevel.CRITICAL
            elif avg_score >= 0.6:
                risk_level = RiskLevel.HIGH
            elif avg_score >= 0.4:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            confidence = min(avg_score + 0.1, 1.0)
        
        recommendations = self._generate_recommendations(detected_categories)
        
        return RiskAssessment(
            risk_level=risk_level,
            risk_categories=detected_categories,
            confidence=confidence,
            reasoning=f"Pattern-based assessment detected {len(detected_categories)} risk categories",
            blocked=False,  # Will be determined later
            recommendations=recommendations,
            metadata={"method": "pattern_based", "scores": risk_scores}
        )
    
    def _ai_risk_assessment(self, command: str, context: Dict[str, Any]) -> RiskAssessment:
        """Perform AI-powered risk assessment"""
        try:
            system_prompt = """You are a cybersecurity expert analyzing commands for potential risks.
            
            Assess the security risk of the given command and classify it into these categories:
            - DELETION: Commands that delete or remove data/files
            - OVERWRITE: Commands that overwrite existing data
            - EXTERNAL_TRANSMISSION: Commands that send data externally
            - FINANCIAL: Commands involving financial transactions
            - SYSTEM_ACCESS: Commands accessing system-level functions
            - DATA_EXFILTRATION: Commands that extract sensitive data
            - PRIVILEGE_ESCALATION: Commands that escalate privileges
            - MALICIOUS_CODE: Commands containing potentially malicious code
            - SUSPICIOUS_FILE: Commands involving suspicious file types
            - UNAUTHORIZED_ACCESS: Commands attempting unauthorized access
            
            Risk levels: SAFE, LOW, MEDIUM, HIGH, CRITICAL
            
            Respond with JSON:
            {
                "risk_level": "SAFE|LOW|MEDIUM|HIGH|CRITICAL",
                "risk_categories": ["CATEGORY1", "CATEGORY2"],
                "confidence": 0.0-1.0,
                "reasoning": "Detailed explanation",
                "recommendations": ["recommendation1", "recommendation2"]
            }"""
            
            user_prompt = f"""Analyze this command for security risks:
            
            Command: {command}
            Context: {json.dumps(context, indent=2)}
            
            Consider the intent, potential impact, and security implications."""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return RiskAssessment(
                risk_level=RiskLevel(result["risk_level"].lower()),
                risk_categories=[RiskCategory(cat.lower()) for cat in result["risk_categories"]],
                confidence=result["confidence"],
                reasoning=f"AI assessment: {result['reasoning']}",
                blocked=False,  # Will be determined later
                recommendations=result["recommendations"],
                metadata={"method": "ai_powered", "model": "gpt-4o-mini"}
            )
            
        except Exception as e:
            # Fallback to medium risk on AI failure
            return RiskAssessment(
                risk_level=RiskLevel.MEDIUM,
                risk_categories=[],
                confidence=0.5,
                reasoning=f"AI assessment failed, using conservative estimate: {str(e)}",
                blocked=False,
                recommendations=["Manual review recommended due to AI assessment failure"],
                metadata={"method": "ai_fallback", "error": str(e)}
            )
    
    def _should_block_command(self, assessment: RiskAssessment, user_id: str) -> bool:
        """Determine if a command should be blocked"""
        # Always block critical risk
        if assessment.risk_level == RiskLevel.CRITICAL:
            return True
        
        # Block high risk unless user has admin privileges
        if assessment.risk_level == RiskLevel.HIGH:
            try:
                from .user_service import user_service
                user = user_service.get_user(user_id)
                if user and user.get('role') == 'admin':
                    return False  # Allow admins to execute high-risk commands
                return True
            except:
                return True  # Block if can't verify admin status
        
        # Check for specific dangerous categories
        dangerous_categories = [
            RiskCategory.DELETION,
            RiskCategory.EXTERNAL_TRANSMISSION,
            RiskCategory.FINANCIAL,
            RiskCategory.MALICIOUS_CODE
        ]
        
        if any(cat in assessment.risk_categories for cat in dangerous_categories):
            if assessment.confidence > 0.8:
                return True
        
        return False
    
    def _generate_recommendations(self, risk_categories: List[RiskCategory]) -> List[str]:
        """Generate security recommendations based on detected risks"""
        recommendations = []
        
        if RiskCategory.DELETION in risk_categories:
            recommendations.append("Consider using backup or version control before deletion")
            recommendations.append("Verify deletion targets are correct")
        
        if RiskCategory.EXTERNAL_TRANSMISSION in risk_categories:
            recommendations.append("Ensure data is encrypted before external transmission")
            recommendations.append("Verify recipient authorization")
        
        if RiskCategory.FINANCIAL in risk_categories:
            recommendations.append("Require additional authentication for financial operations")
            recommendations.append("Implement transaction limits and monitoring")
        
        if RiskCategory.SYSTEM_ACCESS in risk_categories:
            recommendations.append("Use principle of least privilege")
            recommendations.append("Log all system access attempts")
        
        if RiskCategory.MALICIOUS_CODE in risk_categories:
            recommendations.append("Scan for malicious patterns")
            recommendations.append("Execute in isolated environment")
        
        if not recommendations:
            recommendations.append("Monitor command execution")
        
        return recommendations
    
    def _log_security_event(self, event: SecurityEvent):
        """Log security event"""
        self.security_events.append(event)
        
        # Keep only last 1000 events
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
        
        # Log to main logging service
        if logging_service:
            logging_service.log_activity(
                event.user_id,
                'security_event',
                {
                    'command': event.command,
                    'risk_level': event.risk_assessment.risk_level.value,
                    'risk_categories': [cat.value for cat in event.risk_assessment.risk_categories],
                    'confidence': event.risk_assessment.confidence,
                    'blocked': event.risk_assessment.blocked,
                    'action_taken': event.action_taken,
                    'ip_address': event.ip_address
                }
            )
    
    def _send_admin_notification(self, event: SecurityEvent):
        """Send notification to administrators for high-risk events"""
        try:
            # This would integrate with notification systems (Slack, email, etc.)
            notification_data = {
                "type": "security_alert",
                "severity": event.risk_assessment.risk_level.value,
                "user_id": event.user_id,
                "command": event.command,
                "risk_categories": [cat.value for cat in event.risk_assessment.risk_categories],
                "reasoning": event.risk_assessment.reasoning,
                "timestamp": event.timestamp.isoformat(),
                "action_taken": event.action_taken
            }
            
            # Log the notification attempt
            if logging_service:
                logging_service.log_activity(
                    'system',
                    'admin_notification_sent',
                    notification_data
                )
            
            print(f"🚨 SECURITY ALERT: {event.risk_assessment.risk_level.value} risk command from {event.user_id}")
            
        except Exception as e:
            print(f"Failed to send admin notification: {e}")
    
    def get_security_events(self, user_id: str = None, risk_level: RiskLevel = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get security events with optional filtering"""
        events = self.security_events
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if risk_level:
            events = [e for e in events if e.risk_assessment.risk_level == risk_level]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Convert to dict format
        return [
            {
                "timestamp": event.timestamp.isoformat(),
                "user_id": event.user_id,
                "command": event.command,
                "risk_level": event.risk_assessment.risk_level.value,
                "risk_categories": [cat.value for cat in event.risk_assessment.risk_categories],
                "confidence": event.risk_assessment.confidence,
                "reasoning": event.risk_assessment.reasoning,
                "blocked": event.risk_assessment.blocked,
                "action_taken": event.action_taken,
                "ip_address": event.ip_address
            }
            for event in events[:limit]
        ]
    
    def get_security_statistics(self) -> Dict[str, Any]:
        """Get security statistics"""
        if not self.security_events:
            return {
                "total_events": 0,
                "risk_distribution": {},
                "blocked_commands": 0,
                "top_risk_categories": []
            }
        
        # Risk level distribution
        risk_distribution = {}
        for event in self.security_events:
            level = event.risk_assessment.risk_level.value
            risk_distribution[level] = risk_distribution.get(level, 0) + 1
        
        # Blocked commands count
        blocked_count = sum(1 for e in self.security_events if e.risk_assessment.blocked)
        
        # Top risk categories
        category_counts = {}
        for event in self.security_events:
            for category in event.risk_assessment.risk_categories:
                cat_name = category.value
                category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
        
        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_events": len(self.security_events),
            "risk_distribution": risk_distribution,
            "blocked_commands": blocked_count,
            "block_rate": (blocked_count / len(self.security_events)) * 100,
            "top_risk_categories": top_categories,
            "recent_events_24h": len([
                e for e in self.security_events
                if (datetime.now() - e.timestamp).total_seconds() < 86400
            ])
        }
    
    def is_command_safe(self, command: str, user_id: str, context: Dict[str, Any] = None) -> bool:
        """Quick safety check for a command"""
        assessment = self.assess_risk(command, user_id, context)
        return not assessment.blocked

# Global instance
risk_filter = RiskFilter()

