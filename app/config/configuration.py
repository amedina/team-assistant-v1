"""
Configuration management for the data processing and retrieval system.
Handles loading from YAML files and provides strongly-typed configuration classes.
"""

import os
import yaml
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

# Import SecretManager for secure secret resolution
from app.utils.secret_manager import get_secret_manager, SecretConfig

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file from current directory or parent directories
except ImportError:
    pass

logger = logging.getLogger(__name__)

@dataclass
class VectorSearchConfig:
    """Configuration for Vertex AI Vector Search."""
    index_id: str
    endpoint: str
    bucket: str
    embedding_model: str = "text-embedding-005"
    location: str = "us-west1"
    project_id: Optional[str] = None
    
    @property
    def endpoint_id(self) -> str:
        """Extract endpoint ID from the full endpoint path."""
        return self.endpoint.split('/')[-1]
    
    @property
    def index_resource_name(self) -> str:
        """Get the full index resource name."""
        if not self.project_id:
            raise ValueError("project_id is required for index resource name")
        return f"projects/{self.project_id}/locations/{self.location}/indexes/{self.index_id}"
    
    @property
    def endpoint_resource_name(self) -> str:
        """Get the full endpoint resource name."""
        return self.endpoint

@dataclass
class DatabaseConfig:
    """Configuration for PostgreSQL database."""
    instance_connection_name: str
    db_name: str
    db_user: str
    db_pass: str
    
    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string for Cloud SQL Connector."""
        # This will be used with the Cloud SQL Connector, not direct connection
        return f"postgresql://{self.db_user}:{self.db_pass}@/{self.db_name}"

@dataclass
class Neo4jConfig:
    """Configuration for Neo4j Knowledge Graph."""
    uri: str
    user: str
    password: str
    database: str = "neo4j"
    batch_size: int = 100

@dataclass
class PipelineConfig:
    """Configuration for pipeline processing."""
    chunk_size: int = 1500
    chunk_overlap: int = 200
    embedding_model: str = "text-embedding-005"
    batch_size: int = 100
    enable_knowledge_graph: bool = True
    enable_change_detection: bool = True
    default_strategy: str = "smart_sync"
    batch_window_minutes: int = 5
    max_concurrent_jobs: int = 3
    retry_attempts: int = 3
    
    # Google Cloud configuration
    google_cloud_project: Optional[str] = None
    google_cloud_location: str = "us-west1"
    
    # Vector Search configuration
    vector_search: Optional[VectorSearchConfig] = None
    database: Optional[DatabaseConfig] = None
    neo4j: Optional[Neo4jConfig] = None

@dataclass
class DataSourceConfig:
    """Configuration for a data source."""
    source_id: str
    source_type: str
    access_level: str
    description: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProjectConfig:
    """Project-level configuration."""
    google_cloud_project: str
    google_cloud_location: str = "us-west1"

@dataclass
class SystemConfig:
    """Complete system configuration."""
    version: str
    project_config: ProjectConfig
    pipeline_config: PipelineConfig
    data_sources: List[DataSourceConfig]
    
    @classmethod
    def from_yaml(cls, config_path: str, config_manager: Optional['ConfigurationManager'] = None) -> 'SystemConfig':
        """Load configuration from YAML file."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            
            logger.info(f"Loaded configuration from {config_path}")
            return cls._from_dict(data, config_manager)
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            raise
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any], config_manager: Optional['ConfigurationManager'] = None) -> 'SystemConfig':
        """Create SystemConfig from dictionary."""
        # Parse project config
        project_data = data.get('project_config', {})
        project_config = ProjectConfig(**project_data)
        
        # Parse pipeline config
        pipeline_data = data.get('pipeline_config', {})
        
        # Create vector search config
        vector_config = None
        if all(key in pipeline_data for key in ['vector_search_index', 'vector_search_endpoint', 'vector_search_bucket']):
            vector_config = VectorSearchConfig(
                index_id=pipeline_data['vector_search_index'],
                endpoint=pipeline_data['vector_search_endpoint'],
                bucket=pipeline_data['vector_search_bucket'],
                embedding_model=pipeline_data.get('embedding_model', 'text-embedding-005'),
                location=project_config.google_cloud_location,
                project_id=project_config.google_cloud_project
            )
        
        # Create database config
        db_config = None
        if all(key in pipeline_data for key in ['instance-connection-name', 'db_name', 'db_user']):
            # Use secret resolution if config_manager is available
            if config_manager:
                db_pass = config_manager.resolve_secret('db_pass')
            else:
                db_pass = os.environ.get('DB_PASS', '')
            db_config = DatabaseConfig(
                instance_connection_name=pipeline_data['instance-connection-name'],
                db_name=pipeline_data['db_name'],
                db_user=pipeline_data['db_user'],
                db_pass=db_pass
            )
        
        # Create Neo4j config
        neo4j_config = None
        if all(key in pipeline_data for key in ['neo4j_uri', 'neo4j_user']):
            # Use secret resolution if config_manager is available
            if config_manager:
                neo4j_password = config_manager.resolve_secret('neo4j_password')
            else:
                neo4j_password = os.environ.get('NEO4J_PASSWORD', '')
            neo4j_config = Neo4jConfig(
                uri=pipeline_data['neo4j_uri'],
                user=pipeline_data['neo4j_user'],
                password=neo4j_password,
                database=pipeline_data.get('database', 'neo4j'),
                batch_size=pipeline_data.get('batch_size', 100)
            )
        
        # Create pipeline config
        pipeline_config = PipelineConfig(
            chunk_size=pipeline_data.get('chunk_size', 1500),
            chunk_overlap=pipeline_data.get('chunk_overlap', 200),
            embedding_model=pipeline_data.get('embedding_model', 'text-embedding-005'),
            batch_size=pipeline_data.get('batch_size', 100),
            enable_knowledge_graph=pipeline_data.get('enable_knowledge_graph', True),
            enable_change_detection=pipeline_data.get('enable_change_detection', True),
            default_strategy=pipeline_data.get('default_strategy', 'smart_sync'),
            batch_window_minutes=pipeline_data.get('batch_window_minutes', 5),
            max_concurrent_jobs=pipeline_data.get('max_concurrent_jobs', 3),
            retry_attempts=pipeline_data.get('retry_attempts', 3),
            google_cloud_project=project_config.google_cloud_project,
            google_cloud_location=project_config.google_cloud_location,
            vector_search=vector_config,
            database=db_config,
            neo4j=neo4j_config
        )
        
        # Parse data sources
        data_sources = []
        for source_data in data.get('data_sources', []):
            data_source = DataSourceConfig(
                source_id=source_data['source_id'],
                source_type=source_data['source_type'],
                access_level=source_data['access_level'],
                description=source_data['description'],
                enabled=source_data.get('enabled', True),
                config=source_data.get('config', {})
            )
            data_sources.append(data_source)
        
        return cls(
            version=data.get('version', '1.0'),
            project_config=project_config,
            pipeline_config=pipeline_config,
            data_sources=data_sources
        )
    
    def get_enabled_sources(self) -> List[DataSourceConfig]:
        """Get list of enabled data sources."""
        return [source for source in self.data_sources if source.enabled]
    
    def get_source_by_id(self, source_id: str) -> Optional[DataSourceConfig]:
        """Get data source configuration by ID."""
        for source in self.data_sources:
            if source.source_id == source_id:
                return source
        return None
    
    def get_sources_by_type(self, source_type: str) -> List[DataSourceConfig]:
        """Get data sources by type."""
        return [source for source in self.data_sources if source.source_type == source_type]

class ConfigurationManager:
    """Manager for system configuration with secret resolution support."""
    
    def __init__(self, config_path: Optional[str] = None, secret_config: Optional[SecretConfig] = None):
        self.config_path = config_path or self._find_config_file()
        self._secret_manager = get_secret_manager(secret_config)
        self._config: Optional[SystemConfig] = None
    
    def resolve_secret(self,
                      secret_key: str,
                      env_key: Optional[str] = None,
                      default_value: str = '') -> str:
        """
        Resolve secret value with secure fallback chain:
        1. Secret Manager (primary)
        2. Environment Variable (fallback)
        3. Default Value (if provided)

        Args:
            secret_key: Key to look up in Secret Manager
            env_key: Environment variable key (defaults to secret_key.upper())
            default_value: Default value if all sources fail

        Returns:
            Resolved secret value
        """
        # 1. Try Secret Manager first
        try:
            return self._secret_manager.get_secret(secret_key)
        except Exception as e:
            logger.debug(f"Could not retrieve '{secret_key}' from Secret Manager: {e}")

        # 2. Try environment variable
        env_key = env_key or secret_key.upper().replace('-', '_')
        env_value = os.environ.get(env_key)
        if env_value:
            logger.info(f"Using environment variable '{env_key}' for secret '{secret_key}'")
            return env_value

        # 3. Use default value
        if default_value:
            logger.warning(f"Using default value for secret '{secret_key}'")
            return default_value

        # If no default provided, raise an error
        raise ValueError(f"Could not resolve secret '{secret_key}' from any source (Secret Manager, {env_key})")

    def _find_config_file(self) -> str:
        """Find configuration file in common locations."""
        possible_paths = ["app/config/data_sources_config.yaml"]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found config file at {path}")
                return path
        
        raise FileNotFoundError("Could not find data_sources_config.yaml file")
    
    @property
    def config(self) -> SystemConfig:
        """Get system configuration, loading if necessary."""
        if self._config is None:
            self._config = SystemConfig.from_yaml(self.config_path, self)
        return self._config
    
    def reload_config(self) -> SystemConfig:
        """Reload configuration from file."""
        self._config = None
        return self.config
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        try:
            config = self.config
            
            # Check required components
            if not config.pipeline_config.vector_search:
                issues.append("Vector Search configuration is missing")
            
            if not config.pipeline_config.database:
                issues.append("Database configuration is missing")
            
            if config.pipeline_config.enable_knowledge_graph and not config.pipeline_config.neo4j:
                issues.append("Knowledge Graph is enabled but Neo4j configuration is missing")
            
            # Check data sources
            enabled_sources = config.get_enabled_sources()
            if not enabled_sources:
                issues.append("No enabled data sources found")
            
            # Validate each data source
            for source in enabled_sources:
                source_issues = self._validate_data_source(source)
                issues.extend(source_issues)
            
        except Exception as e:
            issues.append(f"Configuration validation failed: {e}")
        
        return issues
    
    def _validate_data_source(self, source: DataSourceConfig) -> List[str]:
        """Validate individual data source configuration."""
        issues = []
        
        # Check required fields
        if not source.source_id:
            issues.append(f"Data source missing source_id")
        
        if not source.source_type:
            issues.append(f"Data source {source.source_id} missing source_type")
        
        # Type-specific validation
        if source.source_type == "github_repo":
            if not source.config.get("repository"):
                issues.append(f"GitHub source {source.source_id} missing repository")
            if not source.config.get("access_token"):
                issues.append(f"GitHub source {source.source_id} missing access_token")
        
        elif source.source_type == "drive_folder":
            if not source.config.get("folder_id"):
                issues.append(f"Drive source {source.source_id} missing folder_id")
        
        elif source.source_type == "drive_file":
            if not source.config.get("file_id"):
                issues.append(f"Drive file source {source.source_id} missing file_id")
        
        elif source.source_type == "web_source":
            if not source.config.get("urls"):
                issues.append(f"Web source {source.source_id} missing urls")
        
        return issues

# Global configuration manager instance
_config_manager = None

def get_config_manager(config_path: Optional[str] = None, secret_config: Optional[SecretConfig] = None) -> ConfigurationManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager(config_path, secret_config)
    return _config_manager

def get_system_config() -> SystemConfig:
    """Get system configuration."""
    return get_config_manager().config 