"""
Enhanced Role-Based Access Control (RBAC) Manager for Jarvis AI Assistant
Comprehensive permission management with Google OAuth integration and granular access control.
"""

import os
import json
import jwt
import requests
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .user_service import user_service
from .logging_service import logging_service

class Permission(Enum):
    # Basic permissions
    CHAT = "chat"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    
    # Tool permissions
    TOOL_USAGE = "tool_usage"
    WEB_SEARCH = "web_search"
    WEATHER_LOOKUP = "weather_lookup"
    URL_SCRAPING = "url_scraping"
    COMMAND_EXECUTION = "command_execution"
    
    # Workflow permissions
    WORKFLOW_VIEW = "workflow_view"
    WORKFLOW_EXECUTION = "workflow_execution"
    WORKFLOW_CREATION = "workflow_creation"
    WORKFLOW_MANAGEMENT = "workflow_management"
    
    # Plugin permissions
    PLUGIN_VIEW = "plugin_view"
    PLUGIN_EXECUTION = "plugin_execution"
    PLUGIN_MANAGEMENT = "plugin_management"
    PLUGIN_DEVELOPMENT = "plugin_development"
    
    # System permissions
    SYSTEM_ACCESS = "system_access"
    SYSTEM_DIAGNOSTICS = "system_diagnostics"
    SYSTEM_CONFIGURATION = "system_configuration"
    
    # User management permissions
    USER_VIEW = "user_view"
    USER_MANAGEMENT = "user_management"
    ROLE_MANAGEMENT = "role_management"
    
    # Security permissions
    SECURITY_VIEW = "security_view"
    SECURITY_MANAGEMENT = "security_management"
    AUDIT_LOGS = "audit_logs"
    
    # Administrative permissions
    ADMIN_PANEL = "admin_panel"
    FULL_ACCESS = "full_access"

class Role(Enum):
    GUEST = "guest"
    USER = "user"
    DEVELOPER = "developer"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

@dataclass
class RoleDefinition:
    """Role definition with permissions"""
    name: str
    display_name: str
    description: str
    permissions: Set[Permission]
    inherits_from: Optional['RoleDefinition'] = None

@dataclass
class UserPermissions:
    """User permissions with context"""
    user_id: str
    role: Role
    permissions: Set[Permission]
    custom_permissions: Set[Permission]
    restrictions: Set[Permission]
    expires_at: Optional[datetime] = None

class RBACManager:
    """Enhanced Role-Based Access Control Manager"""
    
    def __init__(self):
        self.role_definitions = self._initialize_role_definitions()
        self.user_permissions_cache: Dict[str, UserPermissions] = {}
        self.google_oauth_config = self._load_oauth_config()
        
        print("✅ RBAC manager initialized")
    
    def _initialize_role_definitions(self) -> Dict[Role, RoleDefinition]:
        """Initialize role definitions with permissions"""
        
        # Guest role - minimal permissions
        guest_permissions = {
            Permission.CHAT
        }
        
        # User role - standard user permissions
        user_permissions = {
            Permission.CHAT,
            Permission.FILE_UPLOAD,
            Permission.FILE_DOWNLOAD,
            Permission.TOOL_USAGE,
            Permission.WEB_SEARCH,
            Permission.WEATHER_LOOKUP,
            Permission.URL_SCRAPING,
            Permission.WORKFLOW_VIEW,
            Permission.WORKFLOW_EXECUTION,
            Permission.PLUGIN_VIEW,
            Permission.PLUGIN_EXECUTION
        }
        
        # Developer role - development permissions
        developer_permissions = user_permissions | {
            Permission.COMMAND_EXECUTION,
            Permission.WORKFLOW_CREATION,
            Permission.PLUGIN_DEVELOPMENT,
            Permission.SYSTEM_DIAGNOSTICS,
            Permission.SECURITY_VIEW,
            Permission.AUDIT_LOGS
        }
        
        # Admin role - administrative permissions
        admin_permissions = developer_permissions | {
            Permission.WORKFLOW_MANAGEMENT,
            Permission.PLUGIN_MANAGEMENT,
            Permission.SYSTEM_ACCESS,
            Permission.SYSTEM_CONFIGURATION,
            Permission.USER_VIEW,
            Permission.USER_MANAGEMENT,
            Permission.SECURITY_MANAGEMENT,
            Permission.ADMIN_PANEL
        }
        
        # Super Admin role - full access
        super_admin_permissions = admin_permissions | {
            Permission.ROLE_MANAGEMENT,
            Permission.FULL_ACCESS
        }
        
        return {
            Role.GUEST: RoleDefinition(
                name="guest",
                display_name="Guest",
                description="Limited access for unauthenticated users",
                permissions=guest_permissions
            ),
            Role.USER: RoleDefinition(
                name="user",
                display_name="User",
                description="Standard user with basic functionality",
                permissions=user_permissions
            ),
            Role.DEVELOPER: RoleDefinition(
                name="developer",
                display_name="Developer",
                description="Developer with advanced tools and workflow access",
                permissions=developer_permissions
            ),
            Role.ADMIN: RoleDefinition(
                name="admin",
                display_name="Administrator",
                description="Administrator with system management capabilities",
                permissions=admin_permissions
            ),
            Role.SUPER_ADMIN: RoleDefinition(
                name="super_admin",
                display_name="Super Administrator",
                description="Full system access and control",
                permissions=super_admin_permissions
            )
        }
    
    def _load_oauth_config(self) -> Dict[str, str]:
        """Load Google OAuth configuration"""
        return {
            "client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", ""),
            "redirect_uri": os.getenv("GOOGLE_OAUTH_REDIRECT_URI", ""),
            "scope": "openid email profile"
        }
    
    def extract_role_from_oauth(self, oauth_token: str) -> Optional[Role]:
        """Extract user role from Google OAuth token"""
        try:
            # Verify and decode the OAuth token
            user_info = self._verify_oauth_token(oauth_token)
            
            if not user_info:
                return Role.GUEST
            
            email = user_info.get('email', '').lower()
            domain = email.split('@')[-1] if '@' in email else ''
            
            # Role assignment based on email domain or specific users
            admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
            developer_emails = os.getenv("DEVELOPER_EMAILS", "").split(",")
            admin_domains = os.getenv("ADMIN_DOMAINS", "").split(",")
            
            # Check for super admin
            if email in [e.strip().lower() for e in admin_emails if e.strip()]:
                return Role.SUPER_ADMIN
            
            # Check for admin domain
            if domain in [d.strip().lower() for d in admin_domains if d.strip()]:
                return Role.ADMIN
            
            # Check for developer
            if email in [e.strip().lower() for e in developer_emails if e.strip()]:
                return Role.DEVELOPER
            
            # Default to user for authenticated users
            return Role.USER
            
        except Exception as e:
            print(f"Error extracting role from OAuth: {e}")
            return Role.GUEST
    
    def _verify_oauth_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify Google OAuth token and return user info"""
        try:
            # Verify token with Google
            response = requests.get(
                f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={token}",
                timeout=10
            )
            
            if response.status_code == 200:
                token_info = response.json()
                
                # Get user info
                user_response = requests.get(
                    f"https://www.googleapis.com/oauth2/v1/userinfo?access_token={token}",
                    timeout=10
                )
                
                if user_response.status_code == 200:
                    return user_response.json()
            
            return None
            
        except Exception as e:
            print(f"OAuth token verification failed: {e}")
            return None
    
    def get_user_permissions(self, user_id: str, force_refresh: bool = False) -> UserPermissions:
        """Get user permissions with caching"""
        
        # Check cache first
        if not force_refresh and user_id in self.user_permissions_cache:
            cached = self.user_permissions_cache[user_id]
            if not cached.expires_at or cached.expires_at > datetime.now():
                return cached
        
        # Get user from user service
        try:
            user = user_service.get_user(user_id)
            if not user:
                # Default to guest for unknown users
                role = Role.GUEST
            else:
                role = Role(user.get('role', 'user'))
        except:
            role = Role.GUEST
        
        # Get role permissions
        role_def = self.role_definitions[role]
        base_permissions = role_def.permissions.copy()
        
        # Add custom permissions (if any)
        custom_permissions = set()
        restrictions = set()
        
        # TODO: Load custom permissions and restrictions from database
        
        # Create user permissions object
        user_permissions = UserPermissions(
            user_id=user_id,
            role=role,
            permissions=base_permissions | custom_permissions - restrictions,
            custom_permissions=custom_permissions,
            restrictions=restrictions,
            expires_at=datetime.now() + timedelta(hours=1)  # Cache for 1 hour
        )
        
        # Cache the permissions
        self.user_permissions_cache[user_id] = user_permissions
        
        return user_permissions
    
    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has specific permission"""
        user_permissions = self.get_user_permissions(user_id)
        return permission in user_permissions.permissions
    
    def has_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions"""
        user_permissions = self.get_user_permissions(user_id)
        return any(perm in user_permissions.permissions for perm in permissions)
    
    def has_all_permissions(self, user_id: str, permissions: List[Permission]) -> bool:
        """Check if user has all specified permissions"""
        user_permissions = self.get_user_permissions(user_id)
        return all(perm in user_permissions.permissions for perm in permissions)
    
    def check_command_permission(self, user_id: str, command_type: str, command_data: Dict[str, Any] = None) -> bool:
        """Check if user has permission for specific command type"""
        
        permission_map = {
            'chat': [Permission.CHAT],
            'tool': [Permission.TOOL_USAGE],
            'file_operation': [Permission.FILE_UPLOAD],
            'workflow': [Permission.WORKFLOW_EXECUTION],
            'plugin': [Permission.PLUGIN_EXECUTION],
            'system': [Permission.SYSTEM_ACCESS]
        }
        
        required_permissions = permission_map.get(command_type, [])
        
        if not required_permissions:
            return True  # Allow unknown command types
        
        return self.has_any_permission(user_id, required_permissions)
    
    def get_accessible_tools(self, user_id: str) -> List[str]:
        """Get list of tools accessible to user"""
        user_permissions = self.get_user_permissions(user_id)
        accessible_tools = []
        
        if Permission.WEB_SEARCH in user_permissions.permissions:
            accessible_tools.append('web_search')
        
        if Permission.WEATHER_LOOKUP in user_permissions.permissions:
            accessible_tools.append('weather_lookup')
        
        if Permission.URL_SCRAPING in user_permissions.permissions:
            accessible_tools.extend(['web_scraper', 'url_summarizer'])
        
        if Permission.COMMAND_EXECUTION in user_permissions.permissions:
            accessible_tools.append('command_executor')
        
        return accessible_tools
    
    def get_accessible_workflows(self, user_id: str) -> List[str]:
        """Get list of workflows accessible to user"""
        user_permissions = self.get_user_permissions(user_id)
        
        if Permission.WORKFLOW_MANAGEMENT in user_permissions.permissions:
            return ['all']  # Admin can access all workflows
        elif Permission.WORKFLOW_EXECUTION in user_permissions.permissions:
            return ['send_followup_email', 'daily_summary']  # User workflows
        else:
            return []
    
    def get_accessible_plugins(self, user_id: str) -> List[str]:
        """Get list of plugins accessible to user"""
        user_permissions = self.get_user_permissions(user_id)
        
        if Permission.PLUGIN_MANAGEMENT in user_permissions.permissions:
            return ['all']  # Admin can access all plugins
        elif Permission.PLUGIN_EXECUTION in user_permissions.permissions:
            return ['calculator', 'text_processor']  # Safe plugins for users
        else:
            return []
    
    def grant_permission(self, user_id: str, permission: Permission, granted_by: str) -> bool:
        """Grant custom permission to user"""
        try:
            # Check if granter has permission to grant
            if not self.has_permission(granted_by, Permission.ROLE_MANAGEMENT):
                return False
            
            # Add to custom permissions (would be stored in database)
            user_permissions = self.get_user_permissions(user_id)
            user_permissions.custom_permissions.add(permission)
            user_permissions.permissions.add(permission)
            
            # Log the permission grant
            if logging_service:
                logging_service.log_activity(
                    granted_by,
                    'permission_granted',
                    {
                        'target_user': user_id,
                        'permission': permission.value,
                        'granted_by': granted_by
                    }
                )
            
            return True
            
        except Exception as e:
            print(f"Error granting permission: {e}")
            return False
    
    def revoke_permission(self, user_id: str, permission: Permission, revoked_by: str) -> bool:
        """Revoke custom permission from user"""
        try:
            # Check if revoker has permission to revoke
            if not self.has_permission(revoked_by, Permission.ROLE_MANAGEMENT):
                return False
            
            # Add to restrictions (would be stored in database)
            user_permissions = self.get_user_permissions(user_id)
            user_permissions.restrictions.add(permission)
            user_permissions.permissions.discard(permission)
            
            # Log the permission revocation
            if logging_service:
                logging_service.log_activity(
                    revoked_by,
                    'permission_revoked',
                    {
                        'target_user': user_id,
                        'permission': permission.value,
                        'revoked_by': revoked_by
                    }
                )
            
            return True
            
        except Exception as e:
            print(f"Error revoking permission: {e}")
            return False
    
    def change_user_role(self, user_id: str, new_role: Role, changed_by: str) -> bool:
        """Change user role"""
        try:
            # Check if changer has permission to change roles
            if not self.has_permission(changed_by, Permission.ROLE_MANAGEMENT):
                return False
            
            # Update user role in user service
            success = user_service.update_user(user_id, {'role': new_role.value})
            
            if success:
                # Clear permissions cache
                if user_id in self.user_permissions_cache:
                    del self.user_permissions_cache[user_id]
                
                # Log the role change
                if logging_service:
                    logging_service.log_activity(
                        changed_by,
                        'role_changed',
                        {
                            'target_user': user_id,
                            'new_role': new_role.value,
                            'changed_by': changed_by
                        }
                    )
            
            return success
            
        except Exception as e:
            print(f"Error changing user role: {e}")
            return False
    
    def get_role_info(self, role: Role) -> Dict[str, Any]:
        """Get role information"""
        role_def = self.role_definitions[role]
        
        return {
            "name": role_def.name,
            "display_name": role_def.display_name,
            "description": role_def.description,
            "permissions": [perm.value for perm in role_def.permissions],
            "permission_count": len(role_def.permissions)
        }
    
    def get_all_roles(self) -> List[Dict[str, Any]]:
        """Get all available roles"""
        return [self.get_role_info(role) for role in Role]
    
    def get_all_permissions(self) -> List[Dict[str, str]]:
        """Get all available permissions"""
        return [
            {
                "name": perm.value,
                "display_name": perm.value.replace('_', ' ').title(),
                "category": perm.value.split('_')[0].title()
            }
            for perm in Permission
        ]
    
    def get_user_role_summary(self, user_id: str) -> Dict[str, Any]:
        """Get user role and permissions summary"""
        user_permissions = self.get_user_permissions(user_id)
        role_info = self.get_role_info(user_permissions.role)
        
        return {
            "user_id": user_id,
            "role": role_info,
            "total_permissions": len(user_permissions.permissions),
            "custom_permissions": [perm.value for perm in user_permissions.custom_permissions],
            "restrictions": [perm.value for perm in user_permissions.restrictions],
            "accessible_tools": self.get_accessible_tools(user_id),
            "accessible_workflows": self.get_accessible_workflows(user_id),
            "accessible_plugins": self.get_accessible_plugins(user_id)
        }
    
    def clear_permissions_cache(self, user_id: str = None):
        """Clear permissions cache"""
        if user_id:
            if user_id in self.user_permissions_cache:
                del self.user_permissions_cache[user_id]
        else:
            self.user_permissions_cache.clear()
    
    def get_rbac_statistics(self) -> Dict[str, Any]:
        """Get RBAC statistics"""
        # Get user role distribution from user service
        try:
            users = user_service.get_all_users()
            role_distribution = {}
            
            for user in users:
                role = user.get('role', 'user')
                role_distribution[role] = role_distribution.get(role, 0) + 1
            
        except:
            role_distribution = {}
        
        return {
            "total_roles": len(Role),
            "total_permissions": len(Permission),
            "cached_users": len(self.user_permissions_cache),
            "role_distribution": role_distribution,
            "oauth_configured": bool(self.google_oauth_config.get("client_id"))
        }

# Global instance
rbac_manager = RBACManager()

