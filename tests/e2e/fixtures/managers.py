"""
Manager fixtures for E2E testing.

This module provides pytest fixtures for initializing and managing the lifecycle
of the three core managers: VectorStoreManager, DatabaseManager, and KnowledgeGraphManager.
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from config.configuration import SystemConfig
from data_ingestion.managers.vector_store_manager import VectorStoreManager
from data_ingestion.managers.database_manager import DatabaseManager
from data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager
from .configuration import validate_storage_target_config, ConfigurationError

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
async def vector_store_manager(system_config: SystemConfig) -> AsyncGenerator[Optional[VectorStoreManager], None]:
    """
    Provide initialized VectorStoreManager for the test session.
    
    Args:
        system_config: System configuration
        
    Yields:
        VectorStoreManager instance or None if not configured
    """
    if not system_config.pipeline_config.vector_search:
        logger.warning("Vector Search not configured - skipping VectorStoreManager")
        yield None
        return
    
    try:
        # Validate configuration
        validate_storage_target_config(system_config, "vector")
        
        # Initialize manager
        manager = VectorStoreManager(system_config.pipeline_config.vector_search)
        
        logger.info("Initializing VectorStoreManager...")
        success = await manager.initialize()
        
        if not success:
            raise RuntimeError("VectorStoreManager initialization failed")
        
        logger.info("VectorStoreManager initialized successfully")
        yield manager
        
    except Exception as e:
        logger.error(f"Failed to initialize VectorStoreManager: {e}")
        yield None
    finally:
        # Cleanup
        if 'manager' in locals():
            try:
                logger.info("Closing VectorStoreManager...")
                await manager.close()
                logger.info("VectorStoreManager closed successfully")
                
                # Allow time for cleanup
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Error during VectorStoreManager cleanup: {e}")


@pytest.fixture(scope="session")
async def database_manager(system_config: SystemConfig) -> AsyncGenerator[Optional[DatabaseManager], None]:
    """
    Provide initialized DatabaseManager for the test session.
    
    Args:
        system_config: System configuration
        
    Yields:
        DatabaseManager instance or None if not configured
    """
    if not system_config.pipeline_config.database:
        logger.warning("Database not configured - skipping DatabaseManager")
        yield None
        return
    
    try:
        # Validate configuration
        validate_storage_target_config(system_config, "database")
        
        # Initialize manager
        manager = DatabaseManager(system_config.pipeline_config.database)
        
        logger.info("Initializing DatabaseManager...")
        success = await manager.initialize()
        
        if not success:
            raise RuntimeError("DatabaseManager initialization failed")
        
        logger.info("DatabaseManager initialized successfully")
        yield manager
        
    except Exception as e:
        logger.error(f"Failed to initialize DatabaseManager: {e}")
        yield None
    finally:
        # Cleanup
        if 'manager' in locals():
            try:
                logger.info("Closing DatabaseManager...")
                await manager.close()
                logger.info("DatabaseManager closed successfully")
                
                # Allow time for cleanup
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Error during DatabaseManager cleanup: {e}")


@pytest.fixture(scope="session")
async def knowledge_graph_manager(system_config: SystemConfig) -> AsyncGenerator[Optional[KnowledgeGraphManager], None]:
    """
    Provide initialized KnowledgeGraphManager for the test session.
    
    Args:
        system_config: System configuration
        
    Yields:
        KnowledgeGraphManager instance or None if not configured
    """
    if not system_config.pipeline_config.enable_knowledge_graph or not system_config.pipeline_config.neo4j:
        logger.warning("Knowledge Graph not configured - skipping KnowledgeGraphManager")
        yield None
        return
    
    try:
        # Validate configuration
        validate_storage_target_config(system_config, "knowledge_graph")
        
        # Initialize manager
        manager = KnowledgeGraphManager(system_config.pipeline_config.neo4j)
        
        logger.info("Initializing KnowledgeGraphManager...")
        success = await manager.initialize()
        
        if not success:
            raise RuntimeError("KnowledgeGraphManager initialization failed")
        
        logger.info("KnowledgeGraphManager initialized successfully")
        yield manager
        
    except Exception as e:
        logger.error(f"Failed to initialize KnowledgeGraphManager: {e}")
        yield None
    finally:
        # Cleanup
        if 'manager' in locals():
            try:
                logger.info("Closing KnowledgeGraphManager...")
                await manager.close()
                logger.info("KnowledgeGraphManager closed successfully")
                
                # Allow time for cleanup
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Error during KnowledgeGraphManager cleanup: {e}")


@pytest.fixture
async def managers(
    vector_store_manager: Optional[VectorStoreManager],
    database_manager: Optional[DatabaseManager],
    knowledge_graph_manager: Optional[KnowledgeGraphManager]
) -> Dict[str, Any]:
    """
    Provide all managers in a single fixture for convenience.
    
    Args:
        vector_store_manager: VectorStoreManager instance
        database_manager: DatabaseManager instance
        knowledge_graph_manager: KnowledgeGraphManager instance
        
    Returns:
        Dictionary mapping manager names to instances
    """
    managers_dict = {
        "vector": vector_store_manager,
        "database": database_manager,
        "knowledge_graph": knowledge_graph_manager
    }
    
    # Log available managers
    available_managers = [name for name, manager in managers_dict.items() if manager is not None]
    logger.info(f"Available managers: {available_managers}")
    
    return managers_dict


@pytest.fixture
async def active_managers(managers: Dict[str, Any], configured_storage_targets: Dict[str, bool]) -> Dict[str, Any]:
    """
    Provide only the managers that are both configured and requested for testing.
    
    Args:
        managers: All available managers
        configured_storage_targets: Configured storage targets
        
    Returns:
        Dictionary of active managers for the test
    """
    active = {}
    
    for target_name, is_configured in configured_storage_targets.items():
        if is_configured and managers.get(target_name):
            active[target_name] = managers[target_name]
            logger.debug(f"Manager '{target_name}' is active for this test")
        else:
            logger.debug(f"Manager '{target_name}' is not active (configured: {is_configured}, available: {bool(managers.get(target_name))})")
    
    logger.info(f"Active managers for test: {list(active.keys())}")
    return active


@pytest.fixture
async def manager_health_check(active_managers: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Perform health checks on all active managers.
    
    Args:
        active_managers: Dictionary of active managers
        
    Returns:
        Dictionary mapping manager names to health check results
    """
    health_results = {}
    
    for manager_name, manager in active_managers.items():
        if manager is None:
            health_results[manager_name] = {
                "is_healthy": False,
                "error_message": "Manager is None"
            }
            continue
        
        try:
            logger.debug(f"Performing health check for {manager_name} manager...")
            health = await manager.health_check()
            
            health_results[manager_name] = {
                "is_healthy": health.is_healthy,
                "response_time_ms": getattr(health, 'response_time_ms', None),
                "error_message": getattr(health, 'error_message', None),
                "additional_info": getattr(health, 'additional_info', None)
            }
            
            logger.info(f"{manager_name} manager health: {'✓' if health.is_healthy else '✗'}")
            
        except Exception as e:
            logger.error(f"Health check failed for {manager_name} manager: {e}")
            health_results[manager_name] = {
                "is_healthy": False,
                "error_message": str(e)
            }
    
    # Log overall health status
    healthy_managers = [name for name, result in health_results.items() if result["is_healthy"]]
    unhealthy_managers = [name for name, result in health_results.items() if not result["is_healthy"]]
    
    logger.info(f"Manager health summary - Healthy: {healthy_managers}, Unhealthy: {unhealthy_managers}")
    
    return health_results


@pytest.fixture
async def verify_manager_readiness(manager_health_check: Dict[str, Dict[str, Any]]) -> None:
    """
    Verify that all required managers are healthy and ready for testing.
    
    Args:
        manager_health_check: Health check results
        
    Raises:
        pytest.skip: If managers are not ready but tests can be skipped
        pytest.fail: If managers are critically unhealthy
    """
    unhealthy_managers = []
    critical_errors = []
    
    for manager_name, health in manager_health_check.items():
        if not health["is_healthy"]:
            unhealthy_managers.append(manager_name)
            
            error_msg = health.get("error_message", "Unknown error")
            
            # Determine if this is a critical error or can be skipped
            if "not initialized" in error_msg.lower() or "connection" in error_msg.lower():
                critical_errors.append(f"{manager_name}: {error_msg}")
            else:
                logger.warning(f"Manager {manager_name} is unhealthy but may be recoverable: {error_msg}")
    
    if critical_errors:
        error_msg = "Critical manager errors prevent testing:\n" + "\n".join(f"  - {error}" for error in critical_errors)
        logger.error(error_msg)
        pytest.fail(error_msg)
    
    if unhealthy_managers:
        warning_msg = f"Some managers are unhealthy but tests can proceed: {unhealthy_managers}"
        logger.warning(warning_msg)
    
    logger.info("Manager readiness verification passed")


class ManagerError(Exception):
    """Raised when manager operations fail."""
    pass


@asynccontextmanager
async def managed_manager_lifecycle(*managers):
    """
    Context manager for ensuring proper lifecycle management of multiple managers.
    
    Args:
        *managers: Variable number of manager instances
        
    Yields:
        Tuple of manager instances
    """
    initialized_managers = []
    
    try:
        # Initialize all managers
        for manager in managers:
            if manager is not None:
                if hasattr(manager, 'initialize'):
                    success = await manager.initialize()
                    if not success:
                        raise ManagerError(f"Failed to initialize {type(manager).__name__}")
                initialized_managers.append(manager)
        
        yield tuple(initialized_managers)
        
    finally:
        # Clean up all managers in reverse order
        for manager in reversed(initialized_managers):
            try:
                if hasattr(manager, 'close'):
                    await manager.close()
                    # Small delay for cleanup
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"Error closing {type(manager).__name__}: {e}")


@pytest.fixture
def manager_statistics(active_managers: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Get statistics from all active managers.
    
    Args:
        active_managers: Dictionary of active managers
        
    Returns:
        Dictionary mapping manager names to their statistics
    """
    stats = {}
    
    for manager_name, manager in active_managers.items():
        if manager is None:
            stats[manager_name] = {"error": "Manager is None"}
            continue
        
        try:
            if hasattr(manager, 'get_statistics'):
                stats[manager_name] = manager.get_statistics()
            else:
                stats[manager_name] = {"error": "Statistics not available"}
                
        except Exception as e:
            logger.warning(f"Failed to get statistics for {manager_name}: {e}")
            stats[manager_name] = {"error": str(e)}
    
    return stats


@pytest.fixture
async def reset_test_data(active_managers: Dict[str, Any], test_isolation_id: str) -> None:
    """
    Reset/clean test data from all storage systems before test execution.
    
    Args:
        active_managers: Dictionary of active managers
        test_isolation_id: Test isolation ID for cleanup
    """
    logger.info(f"Resetting test data for isolation ID: {test_isolation_id}")
    
    # Note: This is a placeholder for test data cleanup
    # In a real implementation, you would add cleanup logic for each storage system
    # based on the test isolation ID or other cleanup criteria
    
    for manager_name, manager in active_managers.items():
        if manager is None:
            continue
        
        try:
            # Add manager-specific cleanup logic here
            if manager_name == "database" and hasattr(manager, 'delete_chunks_by_source'):
                # Clean up test chunks from database
                test_source_pattern = f"test_{test_isolation_id}%"
                logger.debug(f"Cleaning up database test data matching: {test_source_pattern}")
                # await manager.delete_chunks_by_source(test_source_pattern)
            
            elif manager_name == "knowledge_graph":
                # Clean up test entities and relationships from Neo4j
                logger.debug(f"Cleaning up knowledge graph test data for: {test_isolation_id}")
                # Add Neo4j cleanup logic here
            
            elif manager_name == "vector":
                # Note: Vector store cleanup is more complex due to immutable nature
                # Typically handled by using unique IDs and batch deletion
                logger.debug(f"Vector store cleanup noted for: {test_isolation_id}")
            
        except Exception as e:
            logger.warning(f"Error during test data reset for {manager_name}: {e}")
    
    logger.info("Test data reset completed") 