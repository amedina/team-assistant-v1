"""
Secret Manager utility for secure and centralized access to sensitive information.
Provides caching, fallbacks, and convenient methods for common configurations.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from google.cloud import secretmanager
from google.auth import default
import threading

logger = logging.getLogger(__name__)

@dataclass
class SecretConfig:
    """Configuration for secret management."""
    project_id: Optional[str] = None
    cache_ttl_minutes: int = 5
    enable_fallback_env: bool = True
    default_version: str = "latest"
    
    def __post_init__(self):
        if not self.project_id:
            self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

@dataclass 
class CachedSecret:
    """Cached secret with expiration."""
    value: str
    expires_at: datetime
    
    def is_expired(self) -> bool:
        return datetime.now() >= self.expires_at

class SecretManager:
    """
    Secure and centralized secret management with caching and fallbacks.
    
    Features:
    - Google Cloud Secret Manager integration
    - In-memory cache with TTL
    - Environment variable fallbacks
    - JSON secret parsing
    - Thread-safe operations
    """
    
    def __init__(self, config: Optional[SecretConfig] = None):
        self.config = config or SecretConfig()
        self._client: Optional[secretmanager.SecretManagerServiceClient] = None
        self._cache: Dict[str, CachedSecret] = {}
        self._lock = threading.Lock()
        
    @property
    def client(self) -> secretmanager.SecretManagerServiceClient:
        """Lazy initialization of Secret Manager client."""
        if self._client is None:
            try:
                credentials, project = default()
                self._client = secretmanager.SecretManagerServiceClient(credentials=credentials)
                logger.info(f"Initialized Secret Manager client for project: {self.config.project_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Secret Manager client: {e}")
                raise
        return self._client
    
    def get_secret(self, 
                   secret_id: str, 
                   project_id: Optional[str] = None,
                   version: str = "latest",
                   parse_json: bool = False) -> Union[str, Dict[str, Any]]:
        """
        Retrieve a secret with caching and fallback support.
        
        Args:
            secret_id: Secret identifier
            project_id: GCP project ID (uses config default if None)
            version: Secret version (default: "latest")
            parse_json: Whether to parse secret as JSON
            
        Returns:
            Secret value as string or parsed JSON dict
        """
        project_id = project_id or self.config.project_id
        cache_key = f"{project_id}/{secret_id}/{version}"
        
        with self._lock:
            # Check cache first
            if cache_key in self._cache and not self._cache[cache_key].is_expired():
                logger.debug(f"Retrieved secret '{secret_id}' from cache")
                value = self._cache[cache_key].value
                return json.loads(value) if parse_json else value
            
            # Try to get from Secret Manager
            try:
                secret_value = self._get_from_secret_manager(secret_id, project_id, version)
                if secret_value:
                    # Cache the secret
                    expires_at = datetime.now() + timedelta(minutes=self.config.cache_ttl_minutes)
                    self._cache[cache_key] = CachedSecret(secret_value, expires_at)
                    logger.info(f"Retrieved and cached secret '{secret_id}' from Secret Manager")
                    return json.loads(secret_value) if parse_json else secret_value
            except Exception as e:
                logger.warning(f"Failed to get secret '{secret_id}' from Secret Manager: {e}")
            
            # Fallback to environment variable
            if self.config.enable_fallback_env:
                env_value = os.getenv(secret_id.upper().replace('-', '_'))
                if env_value:
                    logger.warning(f"Using fallback environment variable for secret '{secret_id}'")
                    return json.loads(env_value) if parse_json else env_value
            
            raise ValueError(f"Could not retrieve secret '{secret_id}' from any source")
    
    def _get_from_secret_manager(self, secret_id: str, project_id: str, version: str) -> str:
        """Get secret value from Google Cloud Secret Manager."""
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
        response = self.client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration from secrets."""
        try:
            # Try to get complete database config as JSON
            return self.get_secret("database-config", parse_json=True)
        except:
            # Fallback to individual secrets
            return {
                "host": self.get_secret("db-host"),
                "port": int(self.get_secret("db-port", "5432")),
                "database": self.get_secret("db-name"),
                "user": self.get_secret("db-user"),
                "password": self.get_secret("db-password")
            }
    
    def get_neo4j_config(self) -> Dict[str, Any]:
        """Get Neo4j configuration from secrets."""
        try:
            return self.get_secret("neo4j-config", parse_json=True)
        except:
            return {
                "uri": self.get_secret("neo4j-uri"),
                "user": self.get_secret("neo4j-user"),
                "password": self.get_secret("neo4j-password"),
                "database": self.get_secret("neo4j-database", "neo4j")
            }
    
    def get_api_keys(self) -> Dict[str, str]:
        """Get API keys for various services."""
        keys = {}
        api_key_mappings = {
            "github-token": "github",
            "openai-api-key": "openai",
            "google-api-key": "google"
        }
        
        for secret_id, key_name in api_key_mappings.items():
            try:
                keys[key_name] = self.get_secret(secret_id)
            except:
                logger.warning(f"Could not retrieve API key for {key_name}")
        
        return keys
    
    def clear_cache(self):
        """Clear the secret cache."""
        with self._lock:
            self._cache.clear()
            logger.info("Secret cache cleared")

# Global instance for convenience
_secret_manager = None

def get_secret_manager(config: Optional[SecretConfig] = None) -> SecretManager:
    """Get global SecretManager instance."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager(config)
    return _secret_manager

def get_secret_value(secret_id: str, 
                    project_id: Optional[str] = None,
                    version: str = "latest") -> str:
    """Convenience function to get a secret value."""
    return get_secret_manager().get_secret(secret_id, project_id, version) 