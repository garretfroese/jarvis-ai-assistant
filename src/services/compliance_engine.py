"""
Compliance Engine for Jarvis AI Assistant
Provides enterprise-grade compliance features for GDPR, CCPA, HIPAA, and SOC 2.
"""

import os
import json
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from .logging_service import logging_service, LogLevel, LogCategory

class ComplianceFramework(Enum):
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOC2 = "soc2"

class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class DataSubjectRight(Enum):
    ACCESS = "access"
    DELETION = "deletion"
    PORTABILITY = "portability"
    RECTIFICATION = "rectification"
    RESTRICTION = "restriction"
    OBJECTION = "objection"

@dataclass
class DataSubjectRequest:
    request_id: str
    user_id: str
    request_type: DataSubjectRight
    framework: ComplianceFramework
    submitted_at: datetime
    status: str  # pending, processing, completed, rejected
    completed_at: Optional[datetime] = None
    verification_method: Optional[str] = None
    data_exported: Optional[str] = None
    deletion_confirmed: bool = False
    notes: Optional[str] = None

@dataclass
class ConsentRecord:
    consent_id: str
    user_id: str
    purpose: str
    consent_given: bool
    consent_date: datetime
    withdrawal_date: Optional[datetime] = None
    legal_basis: str = "consent"
    data_categories: List[str] = None
    retention_period: Optional[int] = None  # days

@dataclass
class DataProcessingActivity:
    activity_id: str
    name: str
    purpose: str
    legal_basis: str
    data_categories: List[str]
    data_subjects: List[str]
    recipients: List[str]
    retention_period: int  # days
    security_measures: List[str]
    cross_border_transfers: bool = False
    created_at: datetime = None

@dataclass
class ComplianceViolation:
    violation_id: str
    framework: ComplianceFramework
    severity: str  # low, medium, high, critical
    description: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    affected_users: List[str] = None
    remediation_actions: List[str] = None

class ComplianceEngine:
    """Enterprise compliance engine for regulatory compliance"""
    
    def __init__(self):
        self.enabled = os.getenv('COMPLIANCE_ENABLED', 'True').lower() == 'true'
        self.data_dir = os.path.join(os.path.dirname(__file__), '../../compliance')
        
        # Compliance configuration
        self.gdpr_enabled = os.getenv('GDPR_ENABLED', 'True').lower() == 'true'
        self.ccpa_enabled = os.getenv('CCPA_ENABLED', 'True').lower() == 'true'
        self.hipaa_enabled = os.getenv('HIPAA_ENABLED', 'False').lower() == 'true'
        self.soc2_enabled = os.getenv('SOC2_ENABLED', 'True').lower() == 'true'
        
        # Data retention settings
        self.default_retention_days = int(os.getenv('DATA_RETENTION_DAYS', '2555'))  # 7 years
        self.log_retention_days = int(os.getenv('LOG_RETENTION_DAYS', '2555'))  # 7 years
        self.backup_retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '2555'))  # 7 years
        
        # Storage
        self.requests: Dict[str, DataSubjectRequest] = {}
        self.consents: Dict[str, ConsentRecord] = {}
        self.activities: Dict[str, DataProcessingActivity] = {}
        self.violations: Dict[str, ComplianceViolation] = {}
        
        # Initialize storage
        os.makedirs(self.data_dir, exist_ok=True)
        self._load_compliance_data()
        
        print("✅ Compliance engine initialized")
    
    def _load_compliance_data(self):
        """Load compliance data from storage"""
        try:
            # Load data subject requests
            requests_file = os.path.join(self.data_dir, 'data_subject_requests.json')
            if os.path.exists(requests_file):
                with open(requests_file, 'r') as f:
                    data = json.load(f)
                    for req_data in data.get('requests', []):
                        request = DataSubjectRequest(
                            request_id=req_data['request_id'],
                            user_id=req_data['user_id'],
                            request_type=DataSubjectRight(req_data['request_type']),
                            framework=ComplianceFramework(req_data['framework']),
                            submitted_at=datetime.fromisoformat(req_data['submitted_at']),
                            status=req_data['status'],
                            completed_at=datetime.fromisoformat(req_data['completed_at']) if req_data.get('completed_at') else None,
                            verification_method=req_data.get('verification_method'),
                            data_exported=req_data.get('data_exported'),
                            deletion_confirmed=req_data.get('deletion_confirmed', False),
                            notes=req_data.get('notes')
                        )
                        self.requests[request.request_id] = request
            
            # Load consent records
            consents_file = os.path.join(self.data_dir, 'consent_records.json')
            if os.path.exists(consents_file):
                with open(consents_file, 'r') as f:
                    data = json.load(f)
                    for consent_data in data.get('consents', []):
                        consent = ConsentRecord(
                            consent_id=consent_data['consent_id'],
                            user_id=consent_data['user_id'],
                            purpose=consent_data['purpose'],
                            consent_given=consent_data['consent_given'],
                            consent_date=datetime.fromisoformat(consent_data['consent_date']),
                            withdrawal_date=datetime.fromisoformat(consent_data['withdrawal_date']) if consent_data.get('withdrawal_date') else None,
                            legal_basis=consent_data.get('legal_basis', 'consent'),
                            data_categories=consent_data.get('data_categories', []),
                            retention_period=consent_data.get('retention_period')
                        )
                        self.consents[consent.consent_id] = consent
            
            print(f"✅ Loaded {len(self.requests)} data subject requests and {len(self.consents)} consent records")
            
        except Exception as e:
            print(f"❌ Failed to load compliance data: {e}")
    
    def _save_compliance_data(self):
        """Save compliance data to storage"""
        try:
            # Save data subject requests
            requests_data = {
                "requests": [
                    {
                        **asdict(request),
                        "request_type": request.request_type.value,
                        "framework": request.framework.value,
                        "submitted_at": request.submitted_at.isoformat(),
                        "completed_at": request.completed_at.isoformat() if request.completed_at else None
                    }
                    for request in self.requests.values()
                ]
            }
            
            requests_file = os.path.join(self.data_dir, 'data_subject_requests.json')
            with open(requests_file, 'w') as f:
                json.dump(requests_data, f, indent=2)
            
            # Save consent records
            consents_data = {
                "consents": [
                    {
                        **asdict(consent),
                        "consent_date": consent.consent_date.isoformat(),
                        "withdrawal_date": consent.withdrawal_date.isoformat() if consent.withdrawal_date else None
                    }
                    for consent in self.consents.values()
                ]
            }
            
            consents_file = os.path.join(self.data_dir, 'consent_records.json')
            with open(consents_file, 'w') as f:
                json.dump(consents_data, f, indent=2)
            
            print(f"✅ Saved compliance data")
            
        except Exception as e:
            print(f"❌ Failed to save compliance data: {e}")
    
    # ===== GDPR COMPLIANCE =====
    
    def submit_gdpr_request(self, user_id: str, request_type: DataSubjectRight,
                           verification_method: str = "email") -> str:
        """Submit GDPR data subject request"""
        
        if not self.gdpr_enabled:
            raise ValueError("GDPR compliance is not enabled")
        
        request_id = str(uuid.uuid4())
        
        request = DataSubjectRequest(
            request_id=request_id,
            user_id=user_id,
            request_type=request_type,
            framework=ComplianceFramework.GDPR,
            submitted_at=datetime.now(),
            status="pending",
            verification_method=verification_method
        )
        
        self.requests[request_id] = request
        self._save_compliance_data()
        
        # Log the request
        if logging_service:
            logging_service.log(
                LogLevel.INFO,
                LogCategory.AUTH,
                'gdpr_request_submitted',
                user_id=user_id,
                details={
                    'request_id': request_id,
                    'request_type': request_type.value,
                    'verification_method': verification_method
                }
            )
        
        return request_id
    
    def process_gdpr_request(self, request_id: str) -> Dict[str, Any]:
        """Process GDPR data subject request"""
        
        if request_id not in self.requests:
            raise ValueError("Request not found")
        
        request = self.requests[request_id]
        
        if request.framework != ComplianceFramework.GDPR:
            raise ValueError("Not a GDPR request")
        
        request.status = "processing"
        
        try:
            if request.request_type == DataSubjectRight.ACCESS:
                # Export user data
                data_export = self._export_user_data(request.user_id)
                request.data_exported = data_export
                request.status = "completed"
                
            elif request.request_type == DataSubjectRight.DELETION:
                # Delete user data
                deletion_result = self._delete_user_data(request.user_id)
                request.deletion_confirmed = deletion_result
                request.status = "completed"
                
            elif request.request_type == DataSubjectRight.PORTABILITY:
                # Export data in machine-readable format
                data_export = self._export_user_data(request.user_id, portable=True)
                request.data_exported = data_export
                request.status = "completed"
                
            else:
                request.status = "completed"
                request.notes = f"Request type {request.request_type.value} processed"
            
            request.completed_at = datetime.now()
            self._save_compliance_data()
            
            # Log completion
            if logging_service:
                logging_service.log(
                    LogLevel.INFO,
                    LogCategory.AUTH,
                    'gdpr_request_completed',
                    user_id=request.user_id,
                    details={
                        'request_id': request_id,
                        'request_type': request.request_type.value,
                        'status': request.status
                    }
                )
            
            return {
                "request_id": request_id,
                "status": request.status,
                "completed_at": request.completed_at.isoformat(),
                "data_exported": request.data_exported,
                "deletion_confirmed": request.deletion_confirmed
            }
            
        except Exception as e:
            request.status = "failed"
            request.notes = f"Processing failed: {str(e)}"
            self._save_compliance_data()
            raise
    
    # ===== CCPA COMPLIANCE =====
    
    def submit_ccpa_request(self, user_id: str, request_type: DataSubjectRight) -> str:
        """Submit CCPA consumer request"""
        
        if not self.ccpa_enabled:
            raise ValueError("CCPA compliance is not enabled")
        
        request_id = str(uuid.uuid4())
        
        request = DataSubjectRequest(
            request_id=request_id,
            user_id=user_id,
            request_type=request_type,
            framework=ComplianceFramework.CCPA,
            submitted_at=datetime.now(),
            status="pending"
        )
        
        self.requests[request_id] = request
        self._save_compliance_data()
        
        # Log the request
        if logging_service:
            logging_service.log(
                LogLevel.INFO,
                LogCategory.AUTH,
                'ccpa_request_submitted',
                user_id=user_id,
                details={
                    'request_id': request_id,
                    'request_type': request_type.value
                }
            )
        
        return request_id
    
    # ===== CONSENT MANAGEMENT =====
    
    def record_consent(self, user_id: str, purpose: str, consent_given: bool,
                      legal_basis: str = "consent", data_categories: List[str] = None,
                      retention_period: int = None) -> str:
        """Record user consent"""
        
        consent_id = str(uuid.uuid4())
        
        consent = ConsentRecord(
            consent_id=consent_id,
            user_id=user_id,
            purpose=purpose,
            consent_given=consent_given,
            consent_date=datetime.now(),
            legal_basis=legal_basis,
            data_categories=data_categories or [],
            retention_period=retention_period or self.default_retention_days
        )
        
        self.consents[consent_id] = consent
        self._save_compliance_data()
        
        # Log consent
        if logging_service:
            logging_service.log(
                LogLevel.INFO,
                LogCategory.AUTH,
                'consent_recorded',
                user_id=user_id,
                details={
                    'consent_id': consent_id,
                    'purpose': purpose,
                    'consent_given': consent_given,
                    'legal_basis': legal_basis
                }
            )
        
        return consent_id
    
    def withdraw_consent(self, consent_id: str, user_id: str) -> bool:
        """Withdraw user consent"""
        
        if consent_id not in self.consents:
            return False
        
        consent = self.consents[consent_id]
        
        if consent.user_id != user_id:
            return False
        
        consent.consent_given = False
        consent.withdrawal_date = datetime.now()
        
        self._save_compliance_data()
        
        # Log withdrawal
        if logging_service:
            logging_service.log(
                LogLevel.INFO,
                LogCategory.AUTH,
                'consent_withdrawn',
                user_id=user_id,
                details={
                    'consent_id': consent_id,
                    'purpose': consent.purpose
                }
            )
        
        return True
    
    def get_user_consents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all consents for a user"""
        
        user_consents = []
        for consent in self.consents.values():
            if consent.user_id == user_id:
                consent_data = asdict(consent)
                consent_data['consent_date'] = consent.consent_date.isoformat()
                consent_data['withdrawal_date'] = consent.withdrawal_date.isoformat() if consent.withdrawal_date else None
                user_consents.append(consent_data)
        
        return user_consents
    
    # ===== DATA MANAGEMENT =====
    
    def _export_user_data(self, user_id: str, portable: bool = False) -> str:
        """Export all user data"""
        
        try:
            # This would integrate with all data sources
            user_data = {
                "user_id": user_id,
                "export_date": datetime.now().isoformat(),
                "export_type": "portable" if portable else "standard",
                "data": {
                    "profile": self._get_user_profile(user_id),
                    "conversations": self._get_user_conversations(user_id),
                    "files": self._get_user_files(user_id),
                    "preferences": self._get_user_preferences(user_id),
                    "consents": self.get_user_consents(user_id),
                    "activity_logs": self._get_user_activity_logs(user_id)
                }
            }
            
            # Save export file
            export_filename = f"user_data_export_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            export_path = os.path.join(self.data_dir, 'exports', export_filename)
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            with open(export_path, 'w') as f:
                json.dump(user_data, f, indent=2)
            
            return export_path
            
        except Exception as e:
            print(f"❌ Failed to export user data: {e}")
            return None
    
    def _delete_user_data(self, user_id: str) -> bool:
        """Delete all user data"""
        
        try:
            # This would integrate with all data sources to delete user data
            
            # Delete user profile
            self._delete_user_profile(user_id)
            
            # Delete conversations
            self._delete_user_conversations(user_id)
            
            # Delete files
            self._delete_user_files(user_id)
            
            # Delete preferences
            self._delete_user_preferences(user_id)
            
            # Mark consents as withdrawn
            for consent in self.consents.values():
                if consent.user_id == user_id and consent.consent_given:
                    consent.consent_given = False
                    consent.withdrawal_date = datetime.now()
            
            # Anonymize activity logs (keep for audit but remove PII)
            self._anonymize_user_activity_logs(user_id)
            
            self._save_compliance_data()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to delete user data: {e}")
            return False
    
    def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile data"""
        # This would integrate with user service
        return {"user_id": user_id, "profile": "placeholder"}
    
    def _get_user_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user conversation data"""
        # This would integrate with session manager
        return []
    
    def _get_user_files(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user file data"""
        # This would integrate with file processor
        return []
    
    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences"""
        # This would integrate with memory loader
        return {}
    
    def _get_user_activity_logs(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user activity logs"""
        # This would integrate with logging service
        return []
    
    def _delete_user_profile(self, user_id: str):
        """Delete user profile"""
        # This would integrate with user service
        pass
    
    def _delete_user_conversations(self, user_id: str):
        """Delete user conversations"""
        # This would integrate with session manager
        pass
    
    def _delete_user_files(self, user_id: str):
        """Delete user files"""
        # This would integrate with file processor
        pass
    
    def _delete_user_preferences(self, user_id: str):
        """Delete user preferences"""
        # This would integrate with memory loader
        pass
    
    def _anonymize_user_activity_logs(self, user_id: str):
        """Anonymize user activity logs"""
        # This would integrate with logging service
        pass
    
    # ===== COMPLIANCE REPORTING =====
    
    def get_compliance_status(self) -> Dict[str, Any]:
        """Get overall compliance status"""
        
        now = datetime.now()
        
        # Count pending requests
        pending_requests = sum(1 for req in self.requests.values() if req.status == "pending")
        
        # Count active consents
        active_consents = sum(1 for consent in self.consents.values() if consent.consent_given)
        
        # Check for overdue requests (30 days for GDPR)
        overdue_requests = 0
        for req in self.requests.values():
            if req.status == "pending" and req.framework == ComplianceFramework.GDPR:
                days_pending = (now - req.submitted_at).days
                if days_pending > 30:
                    overdue_requests += 1
        
        return {
            "compliance_enabled": self.enabled,
            "frameworks": {
                "gdpr": self.gdpr_enabled,
                "ccpa": self.ccpa_enabled,
                "hipaa": self.hipaa_enabled,
                "soc2": self.soc2_enabled
            },
            "data_subject_requests": {
                "total": len(self.requests),
                "pending": pending_requests,
                "overdue": overdue_requests
            },
            "consent_management": {
                "total_consents": len(self.consents),
                "active_consents": active_consents
            },
            "data_retention": {
                "default_retention_days": self.default_retention_days,
                "log_retention_days": self.log_retention_days,
                "backup_retention_days": self.backup_retention_days
            },
            "last_updated": now.isoformat()
        }
    
    def generate_compliance_report(self, framework: ComplianceFramework,
                                 start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate compliance report for a specific framework"""
        
        # Filter requests by framework and date range
        framework_requests = [
            req for req in self.requests.values()
            if req.framework == framework and start_date <= req.submitted_at <= end_date
        ]
        
        # Calculate metrics
        total_requests = len(framework_requests)
        completed_requests = sum(1 for req in framework_requests if req.status == "completed")
        pending_requests = sum(1 for req in framework_requests if req.status == "pending")
        
        # Average processing time
        completed_with_times = [
            req for req in framework_requests 
            if req.status == "completed" and req.completed_at
        ]
        
        avg_processing_time = 0
        if completed_with_times:
            total_time = sum(
                (req.completed_at - req.submitted_at).total_seconds() 
                for req in completed_with_times
            )
            avg_processing_time = total_time / len(completed_with_times) / 86400  # days
        
        return {
            "framework": framework.value,
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "metrics": {
                "total_requests": total_requests,
                "completed_requests": completed_requests,
                "pending_requests": pending_requests,
                "completion_rate": completed_requests / total_requests if total_requests > 0 else 0,
                "average_processing_time_days": round(avg_processing_time, 2)
            },
            "request_types": {
                req_type.value: sum(1 for req in framework_requests if req.request_type == req_type)
                for req_type in DataSubjectRight
            },
            "generated_at": datetime.now().isoformat()
        }

# Global instance
compliance_engine = ComplianceEngine()

