"""
Data Governance Framework for Jarvis AI Assistant
Provides enterprise-grade data governance, classification, and lifecycle management.
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

class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class DataLifecycleStage(Enum):
    CREATION = "creation"
    PROCESSING = "processing"
    STORAGE = "storage"
    ARCHIVAL = "archival"
    DELETION = "deletion"

class DataQualityMetric(Enum):
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"

@dataclass
class DataAsset:
    asset_id: str
    name: str
    description: str
    classification: DataClassification
    owner: str
    steward: str
    created_at: datetime
    last_updated: datetime
    retention_period: int  # days
    data_sources: List[str]
    data_consumers: List[str]
    quality_score: float
    compliance_tags: List[str]
    lineage_upstream: List[str]
    lineage_downstream: List[str]

@dataclass
class DataPolicy:
    policy_id: str
    name: str
    description: str
    policy_type: str  # retention, access, quality, security
    classification_scope: List[DataClassification]
    rules: List[Dict[str, Any]]
    enforcement_level: str  # advisory, warning, blocking
    created_by: str
    created_at: datetime
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    is_active: bool = True

@dataclass
class DataQualityRule:
    rule_id: str
    name: str
    description: str
    metric: DataQualityMetric
    threshold: float
    asset_scope: List[str]  # asset IDs
    validation_query: str
    remediation_action: str
    severity: str  # low, medium, high, critical
    is_active: bool = True

@dataclass
class DataLineageRecord:
    lineage_id: str
    source_asset: str
    target_asset: str
    transformation: str
    transformation_type: str  # copy, aggregate, join, filter, etc.
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class DataAccessRequest:
    request_id: str
    requester: str
    asset_id: str
    access_type: str  # read, write, delete
    justification: str
    requested_at: datetime
    status: str  # pending, approved, denied, expired
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    expiry_date: Optional[datetime] = None

class GovernanceFramework:
    """Enterprise data governance framework"""
    
    def __init__(self):
        self.enabled = os.getenv('GOVERNANCE_ENABLED', 'True').lower() == 'true'
        self.data_dir = os.path.join(os.path.dirname(__file__), '../../governance')
        
        # Configuration
        self.auto_classification = os.getenv('AUTO_CLASSIFICATION', 'True').lower() == 'true'
        self.quality_monitoring = os.getenv('QUALITY_MONITORING', 'True').lower() == 'true'
        self.lineage_tracking = os.getenv('LINEAGE_TRACKING', 'True').lower() == 'true'
        
        # Default retention periods by classification
        self.retention_policies = {
            DataClassification.PUBLIC: int(os.getenv('PUBLIC_RETENTION_DAYS', '1095')),  # 3 years
            DataClassification.INTERNAL: int(os.getenv('INTERNAL_RETENTION_DAYS', '2555')),  # 7 years
            DataClassification.CONFIDENTIAL: int(os.getenv('CONFIDENTIAL_RETENTION_DAYS', '2555')),  # 7 years
            DataClassification.RESTRICTED: int(os.getenv('RESTRICTED_RETENTION_DAYS', '3650'))  # 10 years
        }
        
        # Storage
        self.assets: Dict[str, DataAsset] = {}
        self.policies: Dict[str, DataPolicy] = {}
        self.quality_rules: Dict[str, DataQualityRule] = {}
        self.lineage_records: Dict[str, DataLineageRecord] = {}
        self.access_requests: Dict[str, DataAccessRequest] = {}
        
        # Initialize storage
        os.makedirs(self.data_dir, exist_ok=True)
        self._load_governance_data()
        self._initialize_default_policies()
        
        print("✅ Data governance framework initialized")
    
    def _load_governance_data(self):
        """Load governance data from storage"""
        try:
            # Load data assets
            assets_file = os.path.join(self.data_dir, 'data_assets.json')
            if os.path.exists(assets_file):
                with open(assets_file, 'r') as f:
                    data = json.load(f)
                    for asset_data in data.get('assets', []):
                        asset = DataAsset(
                            asset_id=asset_data['asset_id'],
                            name=asset_data['name'],
                            description=asset_data['description'],
                            classification=DataClassification(asset_data['classification']),
                            owner=asset_data['owner'],
                            steward=asset_data['steward'],
                            created_at=datetime.fromisoformat(asset_data['created_at']),
                            last_updated=datetime.fromisoformat(asset_data['last_updated']),
                            retention_period=asset_data['retention_period'],
                            data_sources=asset_data['data_sources'],
                            data_consumers=asset_data['data_consumers'],
                            quality_score=asset_data['quality_score'],
                            compliance_tags=asset_data['compliance_tags'],
                            lineage_upstream=asset_data['lineage_upstream'],
                            lineage_downstream=asset_data['lineage_downstream']
                        )
                        self.assets[asset.asset_id] = asset
            
            print(f"✅ Loaded {len(self.assets)} data assets")
            
        except Exception as e:
            print(f"❌ Failed to load governance data: {e}")
    
    def _save_governance_data(self):
        """Save governance data to storage"""
        try:
            # Save data assets
            assets_data = {
                "assets": [
                    {
                        **asdict(asset),
                        "classification": asset.classification.value,
                        "created_at": asset.created_at.isoformat(),
                        "last_updated": asset.last_updated.isoformat()
                    }
                    for asset in self.assets.values()
                ]
            }
            
            assets_file = os.path.join(self.data_dir, 'data_assets.json')
            with open(assets_file, 'w') as f:
                json.dump(assets_data, f, indent=2)
            
            print(f"✅ Saved governance data")
            
        except Exception as e:
            print(f"❌ Failed to save governance data: {e}")
    
    def _initialize_default_policies(self):
        """Initialize default data governance policies"""
        
        # Data retention policy
        retention_policy = DataPolicy(
            policy_id="retention_001",
            name="Data Retention Policy",
            description="Automatic data retention based on classification",
            policy_type="retention",
            classification_scope=list(DataClassification),
            rules=[
                {
                    "classification": "public",
                    "retention_days": self.retention_policies[DataClassification.PUBLIC],
                    "action": "delete"
                },
                {
                    "classification": "internal",
                    "retention_days": self.retention_policies[DataClassification.INTERNAL],
                    "action": "archive"
                },
                {
                    "classification": "confidential",
                    "retention_days": self.retention_policies[DataClassification.CONFIDENTIAL],
                    "action": "secure_delete"
                },
                {
                    "classification": "restricted",
                    "retention_days": self.retention_policies[DataClassification.RESTRICTED],
                    "action": "secure_delete"
                }
            ],
            enforcement_level="blocking",
            created_by="system",
            created_at=datetime.now(),
            effective_date=datetime.now()
        )
        
        self.policies[retention_policy.policy_id] = retention_policy
        
        # Data access policy
        access_policy = DataPolicy(
            policy_id="access_001",
            name="Data Access Control Policy",
            description="Role-based access control for classified data",
            policy_type="access",
            classification_scope=list(DataClassification),
            rules=[
                {
                    "classification": "public",
                    "required_roles": ["guest", "user", "admin"],
                    "approval_required": False
                },
                {
                    "classification": "internal",
                    "required_roles": ["user", "admin"],
                    "approval_required": False
                },
                {
                    "classification": "confidential",
                    "required_roles": ["admin"],
                    "approval_required": True
                },
                {
                    "classification": "restricted",
                    "required_roles": ["admin"],
                    "approval_required": True,
                    "additional_verification": True
                }
            ],
            enforcement_level="blocking",
            created_by="system",
            created_at=datetime.now(),
            effective_date=datetime.now()
        )
        
        self.policies[access_policy.policy_id] = access_policy
    
    # ===== DATA ASSET MANAGEMENT =====
    
    def register_data_asset(self, name: str, description: str, owner: str,
                           steward: str, data_sources: List[str] = None,
                           classification: DataClassification = None) -> str:
        """Register a new data asset"""
        
        asset_id = str(uuid.uuid4())
        
        # Auto-classify if not provided
        if classification is None and self.auto_classification:
            classification = self._auto_classify_asset(name, description)
        elif classification is None:
            classification = DataClassification.INTERNAL  # Default
        
        asset = DataAsset(
            asset_id=asset_id,
            name=name,
            description=description,
            classification=classification,
            owner=owner,
            steward=steward,
            created_at=datetime.now(),
            last_updated=datetime.now(),
            retention_period=self.retention_policies[classification],
            data_sources=data_sources or [],
            data_consumers=[],
            quality_score=0.0,
            compliance_tags=[],
            lineage_upstream=[],
            lineage_downstream=[]
        )
        
        self.assets[asset_id] = asset
        self._save_governance_data()
        
        # Log asset registration
        if logging_service:
            logging_service.log(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                'data_asset_registered',
                details={
                    'asset_id': asset_id,
                    'name': name,
                    'classification': classification.value,
                    'owner': owner
                }
            )
        
        return asset_id
    
    def _auto_classify_asset(self, name: str, description: str) -> DataClassification:
        """Automatically classify data asset based on content"""
        
        content = f"{name} {description}".lower()
        
        # Restricted data indicators
        restricted_keywords = [
            'password', 'secret', 'key', 'token', 'credential',
            'ssn', 'social security', 'credit card', 'payment',
            'medical', 'health', 'diagnosis', 'treatment',
            'legal', 'attorney', 'privileged', 'confidential'
        ]
        
        # Confidential data indicators
        confidential_keywords = [
            'personal', 'private', 'internal', 'proprietary',
            'financial', 'revenue', 'profit', 'strategy',
            'employee', 'salary', 'performance', 'review'
        ]
        
        # Check for restricted content
        if any(keyword in content for keyword in restricted_keywords):
            return DataClassification.RESTRICTED
        
        # Check for confidential content
        if any(keyword in content for keyword in confidential_keywords):
            return DataClassification.CONFIDENTIAL
        
        # Default to internal
        return DataClassification.INTERNAL
    
    def update_asset_classification(self, asset_id: str, new_classification: DataClassification,
                                  justification: str, updated_by: str) -> bool:
        """Update data asset classification"""
        
        if asset_id not in self.assets:
            return False
        
        asset = self.assets[asset_id]
        old_classification = asset.classification
        
        asset.classification = new_classification
        asset.retention_period = self.retention_policies[new_classification]
        asset.last_updated = datetime.now()
        
        self._save_governance_data()
        
        # Log classification change
        if logging_service:
            logging_service.log(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                'asset_classification_updated',
                details={
                    'asset_id': asset_id,
                    'old_classification': old_classification.value,
                    'new_classification': new_classification.value,
                    'justification': justification,
                    'updated_by': updated_by
                }
            )
        
        return True
    
    # ===== DATA LINEAGE TRACKING =====
    
    def record_data_lineage(self, source_asset: str, target_asset: str,
                           transformation: str, transformation_type: str,
                           metadata: Dict[str, Any] = None) -> str:
        """Record data lineage relationship"""
        
        lineage_id = str(uuid.uuid4())
        
        lineage = DataLineageRecord(
            lineage_id=lineage_id,
            source_asset=source_asset,
            target_asset=target_asset,
            transformation=transformation,
            transformation_type=transformation_type,
            created_at=datetime.now(),
            metadata=metadata or {}
        )
        
        self.lineage_records[lineage_id] = lineage
        
        # Update asset lineage references
        if source_asset in self.assets:
            self.assets[source_asset].lineage_downstream.append(target_asset)
        
        if target_asset in self.assets:
            self.assets[target_asset].lineage_upstream.append(source_asset)
        
        self._save_governance_data()
        
        return lineage_id
    
    def get_data_lineage(self, asset_id: str, direction: str = "both") -> Dict[str, Any]:
        """Get data lineage for an asset"""
        
        if asset_id not in self.assets:
            return {}
        
        asset = self.assets[asset_id]
        
        lineage = {
            "asset_id": asset_id,
            "asset_name": asset.name
        }
        
        if direction in ["upstream", "both"]:
            lineage["upstream"] = []
            for upstream_id in asset.lineage_upstream:
                if upstream_id in self.assets:
                    upstream_asset = self.assets[upstream_id]
                    lineage["upstream"].append({
                        "asset_id": upstream_id,
                        "name": upstream_asset.name,
                        "classification": upstream_asset.classification.value
                    })
        
        if direction in ["downstream", "both"]:
            lineage["downstream"] = []
            for downstream_id in asset.lineage_downstream:
                if downstream_id in self.assets:
                    downstream_asset = self.assets[downstream_id]
                    lineage["downstream"].append({
                        "asset_id": downstream_id,
                        "name": downstream_asset.name,
                        "classification": downstream_asset.classification.value
                    })
        
        return lineage
    
    # ===== DATA QUALITY MONITORING =====
    
    def create_quality_rule(self, name: str, description: str, metric: DataQualityMetric,
                           threshold: float, asset_scope: List[str],
                           validation_query: str, remediation_action: str,
                           severity: str = "medium") -> str:
        """Create data quality rule"""
        
        rule_id = str(uuid.uuid4())
        
        rule = DataQualityRule(
            rule_id=rule_id,
            name=name,
            description=description,
            metric=metric,
            threshold=threshold,
            asset_scope=asset_scope,
            validation_query=validation_query,
            remediation_action=remediation_action,
            severity=severity
        )
        
        self.quality_rules[rule_id] = rule
        
        return rule_id
    
    def evaluate_data_quality(self, asset_id: str) -> Dict[str, Any]:
        """Evaluate data quality for an asset"""
        
        if asset_id not in self.assets:
            return {}
        
        asset = self.assets[asset_id]
        
        # Find applicable quality rules
        applicable_rules = [
            rule for rule in self.quality_rules.values()
            if asset_id in rule.asset_scope and rule.is_active
        ]
        
        quality_results = {
            "asset_id": asset_id,
            "asset_name": asset.name,
            "evaluation_date": datetime.now().isoformat(),
            "overall_score": 0.0,
            "metric_scores": {},
            "rule_results": []
        }
        
        total_score = 0.0
        metric_scores = {}
        
        for rule in applicable_rules:
            # Simulate quality evaluation (would integrate with actual data validation)
            score = self._simulate_quality_check(rule)
            
            metric_scores[rule.metric.value] = score
            total_score += score
            
            quality_results["rule_results"].append({
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "metric": rule.metric.value,
                "score": score,
                "threshold": rule.threshold,
                "passed": score >= rule.threshold,
                "severity": rule.severity
            })
        
        if applicable_rules:
            quality_results["overall_score"] = total_score / len(applicable_rules)
            quality_results["metric_scores"] = metric_scores
            
            # Update asset quality score
            asset.quality_score = quality_results["overall_score"]
            asset.last_updated = datetime.now()
            self._save_governance_data()
        
        return quality_results
    
    def _simulate_quality_check(self, rule: DataQualityRule) -> float:
        """Simulate data quality check (placeholder)"""
        # This would integrate with actual data validation logic
        import random
        return random.uniform(0.7, 1.0)  # Simulate good quality scores
    
    # ===== DATA ACCESS MANAGEMENT =====
    
    def request_data_access(self, requester: str, asset_id: str, access_type: str,
                           justification: str) -> str:
        """Request access to a data asset"""
        
        if asset_id not in self.assets:
            raise ValueError("Asset not found")
        
        request_id = str(uuid.uuid4())
        
        access_request = DataAccessRequest(
            request_id=request_id,
            requester=requester,
            asset_id=asset_id,
            access_type=access_type,
            justification=justification,
            requested_at=datetime.now(),
            status="pending"
        )
        
        self.access_requests[request_id] = access_request
        
        # Check if auto-approval is possible
        asset = self.assets[asset_id]
        if self._can_auto_approve_access(asset, access_type, requester):
            self._approve_access_request(request_id, "system")
        
        return request_id
    
    def _can_auto_approve_access(self, asset: DataAsset, access_type: str, requester: str) -> bool:
        """Check if access request can be auto-approved"""
        
        # Find applicable access policy
        access_policy = None
        for policy in self.policies.values():
            if (policy.policy_type == "access" and 
                asset.classification in policy.classification_scope):
                access_policy = policy
                break
        
        if not access_policy:
            return False
        
        # Check rules for this classification
        for rule in access_policy.rules:
            if rule["classification"] == asset.classification.value:
                return not rule.get("approval_required", True)
        
        return False
    
    def _approve_access_request(self, request_id: str, approved_by: str) -> bool:
        """Approve data access request"""
        
        if request_id not in self.access_requests:
            return False
        
        request = self.access_requests[request_id]
        request.status = "approved"
        request.approved_by = approved_by
        request.approved_at = datetime.now()
        request.expiry_date = datetime.now() + timedelta(days=30)  # 30-day access
        
        # Log access approval
        if logging_service:
            logging_service.log(
                LogLevel.INFO,
                LogCategory.AUTH,
                'data_access_approved',
                user_id=request.requester,
                details={
                    'request_id': request_id,
                    'asset_id': request.asset_id,
                    'access_type': request.access_type,
                    'approved_by': approved_by
                }
            )
        
        return True
    
    # ===== GOVERNANCE REPORTING =====
    
    def get_governance_dashboard(self) -> Dict[str, Any]:
        """Get governance dashboard data"""
        
        now = datetime.now()
        
        # Asset statistics
        total_assets = len(self.assets)
        classification_counts = {}
        for classification in DataClassification:
            classification_counts[classification.value] = sum(
                1 for asset in self.assets.values() 
                if asset.classification == classification
            )
        
        # Quality statistics
        quality_scores = [asset.quality_score for asset in self.assets.values()]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Access request statistics
        pending_requests = sum(1 for req in self.access_requests.values() if req.status == "pending")
        
        # Policy compliance
        active_policies = sum(1 for policy in self.policies.values() if policy.is_active)
        
        return {
            "governance_enabled": self.enabled,
            "data_assets": {
                "total": total_assets,
                "by_classification": classification_counts,
                "average_quality_score": round(avg_quality, 2)
            },
            "data_policies": {
                "total": len(self.policies),
                "active": active_policies
            },
            "data_quality": {
                "total_rules": len(self.quality_rules),
                "monitoring_enabled": self.quality_monitoring
            },
            "data_lineage": {
                "total_records": len(self.lineage_records),
                "tracking_enabled": self.lineage_tracking
            },
            "access_management": {
                "total_requests": len(self.access_requests),
                "pending_requests": pending_requests
            },
            "retention_policies": {
                classification.value: days 
                for classification, days in self.retention_policies.items()
            },
            "last_updated": now.isoformat()
        }
    
    def generate_governance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate comprehensive governance report"""
        
        # Filter data by date range
        period_assets = [
            asset for asset in self.assets.values()
            if start_date <= asset.created_at <= end_date
        ]
        
        period_requests = [
            req for req in self.access_requests.values()
            if start_date <= req.requested_at <= end_date
        ]
        
        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "asset_metrics": {
                "new_assets": len(period_assets),
                "total_assets": len(self.assets),
                "classification_distribution": {
                    classification.value: sum(
                        1 for asset in period_assets 
                        if asset.classification == classification
                    )
                    for classification in DataClassification
                }
            },
            "access_metrics": {
                "total_requests": len(period_requests),
                "approved_requests": sum(1 for req in period_requests if req.status == "approved"),
                "denied_requests": sum(1 for req in period_requests if req.status == "denied"),
                "pending_requests": sum(1 for req in period_requests if req.status == "pending")
            },
            "quality_metrics": {
                "average_quality_score": round(
                    sum(asset.quality_score for asset in self.assets.values()) / len(self.assets), 2
                ) if self.assets else 0,
                "assets_below_threshold": sum(
                    1 for asset in self.assets.values() if asset.quality_score < 0.8
                )
            },
            "lineage_metrics": {
                "total_lineage_records": len(self.lineage_records),
                "assets_with_lineage": sum(
                    1 for asset in self.assets.values()
                    if asset.lineage_upstream or asset.lineage_downstream
                )
            },
            "generated_at": datetime.now().isoformat()
        }

# Global instance
governance_framework = GovernanceFramework()

