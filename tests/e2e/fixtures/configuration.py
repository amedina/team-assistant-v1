"""
Configuration fixtures for E2E testing.

This module provides pytest fixtures for system configuration management,
ensuring proper initialization and cleanup of configuration resources.
"""

import pytest
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from config.configuration import SystemConfig, get_system_config, get_config_manager
from tests.e2e.test_scenarios import TestScenario, create_data_source_config

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def system_config() -> SystemConfig:
    """
    Provide system configuration for the entire test session.
    
    Returns:
        SystemConfig object loaded from configuration file
    """
    try:
        config = get_system_config()
        logger.info(f"Loaded system configuration with {len(config.data_sources)} data sources")
        return config
    except Exception as e:
        logger.error(f"Failed to load system configuration: {e}")
        pytest.fail(f"Cannot run E2E tests without valid configuration: {e}")


@pytest.fixture
def test_config(system_config: SystemConfig) -> SystemConfig:
    """
    Provide a clean system configuration for each test.
    
    Args:
        system_config: Session-scoped system configuration
        
    Returns:
        Fresh SystemConfig object for the test
    """
    return system_config


@pytest.fixture
def scenario_data_config(test_scenario: TestScenario) -> Dict[str, Any]:
    """
    Create data source configuration for a test scenario.
    
    Args:
        test_scenario: Test scenario to create config for
        
    Returns:
        Data source configuration dictionary
    """
    return create_data_source_config(test_scenario)


@pytest.fixture
def validate_configuration(system_config: SystemConfig) -> None:
    """
    Validate that the system configuration is complete and valid for E2E testing.
    
    Args:
        system_config: System configuration to validate
        
    Raises:
        pytest.skip: If configuration is invalid but tests can be skipped
        pytest.fail: If configuration is critically invalid
    """
    errors = []
    
    # Check vector search configuration
    if not system_config.pipeline_config.vector_search:
        errors.append("Vector Search configuration is missing")
    else:
        vector_config = system_config.pipeline_config.vector_search
        if not vector_config.index_id:
            errors.append("Vector Search index_id is missing")
        if not vector_config.endpoint:
            errors.append("Vector Search endpoint is missing")
        if not vector_config.bucket:
            errors.append("Vector Search bucket is missing")
        if not vector_config.project_id:
            errors.append("Vector Search project_id is missing")
    
    # Check database configuration
    if not system_config.pipeline_config.database:
        errors.append("Database configuration is missing")
    else:
        db_config = system_config.pipeline_config.database
        if not db_config.instance_connection_name:
            errors.append("Database instance_connection_name is missing")
        if not db_config.db_name:
            errors.append("Database db_name is missing")
        if not db_config.db_user:
            errors.append("Database db_user is missing")
        if not db_config.db_pass:
            errors.append("Database db_pass is missing")
    
    # Check Neo4j configuration (if knowledge graph is enabled)
    if system_config.pipeline_config.enable_knowledge_graph:
        if not system_config.pipeline_config.neo4j:
            errors.append("Knowledge Graph is enabled but Neo4j configuration is missing")
        else:
            neo4j_config = system_config.pipeline_config.neo4j
            if not neo4j_config.uri:
                errors.append("Neo4j uri is missing")
            if not neo4j_config.user:
                errors.append("Neo4j user is missing")
            # Password can be empty for some configurations
    
    # Check for enabled data sources
    enabled_sources = system_config.get_enabled_sources()
    if not enabled_sources:
        errors.append("No enabled data sources found")
    
    # Log configuration status
    logger.info(f"Configuration validation:")
    logger.info(f"  - Vector Search: {'✓' if system_config.pipeline_config.vector_search else '✗'}")
    logger.info(f"  - Database: {'✓' if system_config.pipeline_config.database else '✗'}")
    logger.info(f"  - Knowledge Graph: {'✓' if system_config.pipeline_config.neo4j else '✗'}")
    logger.info(f"  - Enabled Sources: {len(enabled_sources)}")
    
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
        logger.error(error_msg)
        pytest.fail(error_msg)
    
    logger.info("Configuration validation passed")


@pytest.fixture(scope="session")
def storage_targets(system_config: SystemConfig) -> Dict[str, bool]:
    """
    Determine which storage targets are available for testing.
    
    Args:
        system_config: System configuration
        
    Returns:
        Dictionary indicating which storage targets are available
    """
    targets = {
        "vector": bool(system_config.pipeline_config.vector_search),
        "database": bool(system_config.pipeline_config.database),
        "knowledge_graph": bool(
            system_config.pipeline_config.enable_knowledge_graph and
            system_config.pipeline_config.neo4j
        )
    }
    
    logger.info(f"Available storage targets: {targets}")
    return targets


@pytest.fixture
def test_isolation_id() -> str:
    """
    Generate a unique isolation ID for test data to avoid conflicts.
    
    Returns:
        Unique isolation ID string
    """
    import uuid
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    isolation_id = f"e2e_test_{timestamp}_{unique_id}"
    
    logger.debug(f"Generated test isolation ID: {isolation_id}")
    return isolation_id


@pytest.fixture
def connector_config_override(test_scenario: TestScenario, test_isolation_id: str) -> Dict[str, Any]:
    """
    Create connector configuration override for testing.
    
    Args:
        test_scenario: Test scenario configuration
        test_isolation_id: Unique test isolation ID
        
    Returns:
        Configuration override dictionary
    """
    base_config = create_data_source_config(test_scenario)
    
    # Add test-specific overrides
    base_config["source_id"] = f"{base_config['source_id']}_{test_isolation_id}"
    base_config["config"]["test_mode"] = True
    base_config["config"]["test_isolation_id"] = test_isolation_id
    
    # Add test-specific metadata
    if "metadata" not in base_config["config"]:
        base_config["config"]["metadata"] = {}
    
    base_config["config"]["metadata"].update({
        "test_scenario": test_scenario.test_id,
        "test_description": test_scenario.description,
        "test_isolation_id": test_isolation_id
    })
    
    logger.debug(f"Created connector config override for {test_scenario.test_id}")
    return base_config


class ConfigurationError(Exception):
    """Raised when configuration is invalid for testing."""
    pass


def validate_storage_target_config(config: SystemConfig, target: str) -> None:
    """
    Validate configuration for a specific storage target.
    
    Args:
        config: System configuration
        target: Storage target ("vector", "database", "knowledge_graph")
        
    Raises:
        ConfigurationError: If target configuration is invalid
    """
    if target == "vector":
        if not config.pipeline_config.vector_search:
            raise ConfigurationError("Vector Search configuration is required")
        
        vector_config = config.pipeline_config.vector_search
        required_fields = ["index_id", "endpoint", "bucket", "project_id"]
        missing_fields = [field for field in required_fields 
                         if not getattr(vector_config, field, None)]
        
        if missing_fields:
            raise ConfigurationError(f"Vector Search missing fields: {missing_fields}")
    
    elif target == "database":
        if not config.pipeline_config.database:
            raise ConfigurationError("Database configuration is required")
        
        db_config = config.pipeline_config.database
        required_fields = ["instance_connection_name", "db_name", "db_user", "db_pass"]
        missing_fields = [field for field in required_fields 
                         if not getattr(db_config, field, None)]
        
        if missing_fields:
            raise ConfigurationError(f"Database missing fields: {missing_fields}")
    
    elif target == "knowledge_graph":
        if not config.pipeline_config.enable_knowledge_graph:
            raise ConfigurationError("Knowledge Graph is not enabled")
        
        if not config.pipeline_config.neo4j:
            raise ConfigurationError("Neo4j configuration is required")
        
        neo4j_config = config.pipeline_config.neo4j
        required_fields = ["uri", "user"]
        missing_fields = [field for field in required_fields 
                         if not getattr(neo4j_config, field, None)]
        
        if missing_fields:
            raise ConfigurationError(f"Neo4j missing fields: {missing_fields}")
    
    else:
        raise ConfigurationError(f"Unknown storage target: {target}")


@pytest.fixture
def configured_storage_targets(system_config: SystemConfig, request) -> Dict[str, bool]:
    """
    Provide storage targets configuration based on test parameters.
    
    Args:
        system_config: System configuration
        request: Pytest request object
        
    Returns:
        Dictionary of configured storage targets
    """
    # Get target filters from test parameters
    target_filter = getattr(request, 'param', None)
    if isinstance(target_filter, str):
        target_filter = [target_filter]
    
    # Default to all available targets
    all_targets = {
        "vector": bool(system_config.pipeline_config.vector_search),
        "database": bool(system_config.pipeline_config.database),
        "knowledge_graph": bool(
            system_config.pipeline_config.enable_knowledge_graph and
            system_config.pipeline_config.neo4j
        )
    }
    
    # Apply filter if specified
    if target_filter:
        filtered_targets = {
            target: (target in target_filter and all_targets[target])
            for target in all_targets
        }
        return filtered_targets
    
    return all_targets 