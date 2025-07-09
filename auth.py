"""
Authentication and Authorization Module for Banking Agents Demo

This module implements authentication mechanisms and authorization policies
to meet compliance control C9262 requirements.
"""

import os
import logging
import hashlib
import time
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from functools import wraps

# Configure security logging
security_logger = logging.getLogger('security_audit')
security_logger.setLevel(logging.INFO)

# Create console handler if none exists
if not security_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)


class UserRole(Enum):
    """User roles for role-based access control"""
    ADMIN = "admin"
    TELLER = "teller"
    CUSTOMER = "customer"


@dataclass
class User:
    """User data structure"""
    user_id: str
    username: str
    role: UserRole
    allowed_accounts: List[str] = None  # Accounts this user can access
    
    def __post_init__(self):
        if self.allowed_accounts is None:
            self.allowed_accounts = []


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class AuthorizationError(Exception):
    """Raised when authorization fails"""
    pass


class AuthManager:
    """
    Authentication and Authorization Manager
    
    Provides user authentication via API keys and role-based authorization.
    """
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, str] = {}  # api_key -> user_id
        self.session_tokens: Dict[str, Tuple[str, float]] = {}  # token -> (user_id, expires_at)
        self._load_users()
        
    def _load_users(self):
        """Load users from environment variables or defaults"""
        # Default admin user
        admin_key = os.getenv("ADMIN_API_KEY", "admin-key-12345")
        self.add_user("admin", "admin", UserRole.ADMIN, admin_key, [])
        
        # Default teller user
        teller_key = os.getenv("TELLER_API_KEY", "teller-key-12345")
        self.add_user("teller", "bank_teller", UserRole.TELLER, teller_key, ["1234", "5678", "9012"])
        
        # Default customer user
        customer_key = os.getenv("CUSTOMER_API_KEY", "customer-key-12345")
        self.add_user("customer", "john_doe", UserRole.CUSTOMER, customer_key, ["1234"])
        
        security_logger.info("User database initialized with default users")
    
    def add_user(self, user_id: str, username: str, role: UserRole, api_key: str, allowed_accounts: List[str]):
        """Add a user to the system"""
        user = User(user_id, username, role, allowed_accounts)
        self.users[user_id] = user
        
        # Hash the API key for storage
        hashed_key = self._hash_api_key(api_key)
        self.api_keys[hashed_key] = user_id
        
        security_logger.info(f"User added: {username} with role {role.value}")
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def authenticate_api_key(self, api_key: str) -> User:
        """Authenticate user by API key"""
        if not api_key:
            security_logger.warning("Authentication attempt with empty API key")
            raise AuthenticationError("API key is required")
        
        hashed_key = self._hash_api_key(api_key)
        user_id = self.api_keys.get(hashed_key)
        
        if not user_id:
            security_logger.warning(f"Authentication failed for API key: {api_key[:8]}...")
            raise AuthenticationError("Invalid API key")
        
        user = self.users.get(user_id)
        if not user:
            security_logger.error(f"User not found for authenticated API key: {user_id}")
            raise AuthenticationError("User not found")
        
        security_logger.info(f"User authenticated: {user.username} ({user.role.value})")
        return user
    
    def create_session_token(self, user: User, duration_hours: int = 1) -> str:
        """Create a session token for the user"""
        token = hashlib.sha256(f"{user.user_id}{time.time()}".encode()).hexdigest()
        expires_at = time.time() + (duration_hours * 3600)
        self.session_tokens[token] = (user.user_id, expires_at)
        
        security_logger.info(f"Session token created for user: {user.username}")
        return token
    
    def authenticate_session_token(self, token: str) -> User:
        """Authenticate user by session token"""
        if not token:
            raise AuthenticationError("Session token is required")
        
        session_data = self.session_tokens.get(token)
        if not session_data:
            security_logger.warning("Authentication failed: Invalid session token")
            raise AuthenticationError("Invalid session token")
        
        user_id, expires_at = session_data
        if time.time() > expires_at:
            del self.session_tokens[token]
            security_logger.warning(f"Authentication failed: Expired session token for user {user_id}")
            raise AuthenticationError("Session token expired")
        
        user = self.users.get(user_id)
        if not user:
            security_logger.error(f"User not found for valid session token: {user_id}")
            raise AuthenticationError("User not found")
        
        return user
    
    def authorize_account_access(self, user: User, account_id: str) -> bool:
        """Check if user is authorized to access the account"""
        # Admin can access all accounts
        if user.role == UserRole.ADMIN:
            return True
        
        # Teller can access assigned accounts
        if user.role == UserRole.TELLER and account_id in user.allowed_accounts:
            return True
        
        # Customer can only access their own accounts
        if user.role == UserRole.CUSTOMER and account_id in user.allowed_accounts:
            return True
        
        security_logger.warning(
            f"Authorization denied: User {user.username} ({user.role.value}) "
            f"attempted to access account {account_id}"
        )
        return False
    
    def authorize_role(self, user: User, required_roles: List[UserRole]) -> bool:
        """Check if user has required role"""
        if user.role in required_roles:
            return True
        
        security_logger.warning(
            f"Authorization denied: User {user.username} ({user.role.value}) "
            f"requires role(s): {[r.value for r in required_roles]}"
        )
        return False


# Global auth manager instance
auth_manager = AuthManager()


def require_auth(api_key_param: str = "api_key"):
    """
    Decorator to require authentication for functions
    
    Args:
        api_key_param: Parameter name that contains the API key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract API key from kwargs
            api_key = kwargs.get(api_key_param)
            if not api_key:
                raise AuthenticationError(f"Missing required parameter: {api_key_param}")
            
            # Authenticate user
            user = auth_manager.authenticate_api_key(api_key)
            
            # Remove API key from kwargs and add user
            kwargs.pop(api_key_param, None)
            kwargs['current_user'] = user
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_roles(*roles: UserRole):
    """
    Decorator to require specific roles for functions
    
    Args:
        roles: Required user roles
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise AuthenticationError("Authentication required")
            
            if not auth_manager.authorize_role(current_user, list(roles)):
                raise AuthorizationError(f"Requires role(s): {[r.value for r in roles]}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_account_access(account_param: str = "account_id"):
    """
    Decorator to require account access authorization
    
    Args:
        account_param: Parameter name that contains the account ID
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise AuthenticationError("Authentication required")
            
            account_id = kwargs.get(account_param)
            if not account_id:
                raise AuthorizationError(f"Missing required parameter: {account_param}")
            
            if not auth_manager.authorize_account_access(current_user, account_id):
                raise AuthorizationError(f"Access denied to account: {account_id}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_configuration():
    """Validate security configuration on startup"""
    errors = []
    
    # Check for secure API keys in production
    if os.getenv("ENVIRONMENT") == "production":
        default_keys = ["admin-key-12345", "teller-key-12345", "customer-key-12345"]
        for key_env in ["ADMIN_API_KEY", "TELLER_API_KEY", "CUSTOMER_API_KEY"]:
            key_value = os.getenv(key_env)
            if not key_value or key_value in default_keys:
                errors.append(f"Insecure default API key detected for {key_env}")
    
    # Check for required Azure OpenAI configuration
    required_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT"
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")
    
    if errors:
        error_msg = "Security configuration errors:\n" + "\n".join(f"- {e}" for e in errors)
        security_logger.error(error_msg)
        raise Exception(error_msg)
    
    security_logger.info("Security configuration validation passed")