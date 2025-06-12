"""
E2E Test Fixtures and Utilities

This module provides simplified test fixtures, configuration loading, and utility functions
for the comprehensive E2E testing framework without pytest-asyncio dependencies.
"""

import os
import pytest
import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.configuration import get_system_config, SystemConfig

logger = logging.getLogger(__name__)

class E2ETestResults:
    """Container for test results and metrics."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.results: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.timing_metrics: Dict[str, float] = {}
        self.component_health: Dict[str, Any] = {}
        
    def add_result(self, test_name: str, success: bool, details: Any = None, execution_time: float = 0.0):
        """Add a test result."""
        self.results[test_name] = {
            "success": success,
            "details": details,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }
        self.timing_metrics[test_name] = execution_time
        
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(f"[{datetime.now().isoformat()}] {error}")
        
    def get_success_rate(self) -> float:
        """Calculate overall success rate."""
        if not self.results:
            return 0.0
        successful = sum(1 for r in self.results.values() if r["success"])
        return (successful / len(self.results)) * 100.0
        
    def is_overall_success(self, min_success_rate: float = 80.0) -> bool:
        """Check if overall test run is successful."""
        return self.get_success_rate() >= min_success_rate and len(self.errors) == 0
        
    def get_total_execution_time(self) -> float:
        """Get total execution time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

@pytest.fixture(scope="session")
def system_config() -> SystemConfig:
    """Load system configuration for tests."""
    return get_system_config()

@pytest.fixture(scope="session")
def test_results() -> E2ETestResults:
    """Test results container for collecting metrics."""
    return E2ETestResults()

@pytest.fixture(scope="session")
def text_processor():
    """Initialize and provide text processor."""
    from data_ingestion.processors.text_processor import TextProcessor
    return TextProcessor(
        chunk_size=800,
        chunk_overlap=100,
        enable_entity_extraction=True
    )

# Utility functions for test validation

def validate_chunk_data(chunk_data: Any, expected_fields: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate chunk data structure and required fields.
    
    Args:
        chunk_data: Chunk data to validate
        expected_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    if not hasattr(chunk_data, '__dict__') and not isinstance(chunk_data, dict):
        errors.append("Chunk data is not a valid object or dictionary")
        return False, errors
    
    # Get attributes as dict
    if hasattr(chunk_data, '__dict__'):
        data_dict = chunk_data.__dict__
    else:
        data_dict = chunk_data
    
    # Check required fields
    for field in expected_fields:
        if field not in data_dict:
            errors.append(f"Missing required field: {field}")
    
    return len(errors) == 0, errors

def validate_text_processing(processed_doc: Any, validation_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate text processing results against configuration.
    
    Args:
        processed_doc: Processed document result
        validation_config: Validation configuration from scenario
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check minimum text length
    min_length = validation_config.get("min_extracted_text_length", 0)
    if hasattr(processed_doc, "chunks") and processed_doc.chunks:
        total_text_length = sum(len(chunk.text) for chunk in processed_doc.chunks)
        if total_text_length < min_length:
            errors.append(f"Total extracted text length {total_text_length} < {min_length}")
    else:
        errors.append("No chunks found in processed document")
    
    # Check chunk overlap if required
    if validation_config.get("required_chunk_overlap", False):
        if hasattr(processed_doc, "chunks") and len(processed_doc.chunks) > 1:
            # This is a simplified check - in practice you'd verify actual overlap
            if not any(hasattr(chunk, "metadata") and 
                      chunk.metadata.get("chunk_index", 0) > 0 
                      for chunk in processed_doc.chunks):
                errors.append("Chunk overlap validation failed - no multi-chunk processing detected")
    
    # Check minimum entities extracted
    min_entities = validation_config.get("min_entities_extracted", 0)
    if hasattr(processed_doc, "chunks"):
        total_entities = sum(
            len(chunk.entities) if hasattr(chunk, "entities") and chunk.entities else 0
            for chunk in processed_doc.chunks
        )
        if total_entities < min_entities:
            errors.append(f"Total entities extracted {total_entities} < {min_entities}")
    
    # Check required metadata fields
    required_fields = validation_config.get("required_metadata_fields", [])
    if hasattr(processed_doc, "chunks") and processed_doc.chunks:
        for chunk in processed_doc.chunks:
            if hasattr(chunk, "metadata"):
                for field in required_fields:
                    if field not in chunk.metadata:
                        errors.append(f"Missing required metadata field: {field}")
                        break  # Only report once per chunk type
    
    return len(errors) == 0, errors

def validate_retrieval_results(results: List[Any], scenario_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate retrieval results against scenario expectations.
    
    Args:
        results: List of retrieval results
        scenario_config: Scenario configuration
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check minimum number of results
    min_chunks = scenario_config.get("min_chunks_expected", 0)
    if len(results) < min_chunks:
        errors.append(f"Found {len(results)} results, expected at least {min_chunks}")
    
    # Check minimum similarity scores
    min_similarity = scenario_config.get("min_vector_similarity", 0.0)
    if results and hasattr(results[0], "similarity_score"):
        low_similarity_count = sum(
            1 for result in results 
            if hasattr(result, "similarity_score") and result.similarity_score < min_similarity
        )
        if low_similarity_count > 0:
            errors.append(f"{low_similarity_count} results below minimum similarity {min_similarity}")
    
    # Check for expected keywords in results (simplified check)
    expected_keywords = scenario_config.get("expected_keywords", [])
    if expected_keywords and results:
        # This is a simplified implementation - you might want more sophisticated keyword matching
        found_keywords = set()
        for result in results:
            if hasattr(result, "metadata") and "text_summary" in result.metadata:
                text = result.metadata["text_summary"].lower()
                for keyword in expected_keywords:
                    if keyword.lower() in text:
                        found_keywords.add(keyword.lower())
        
        missing_keywords = set(k.lower() for k in expected_keywords) - found_keywords
        if missing_keywords:
            errors.append(f"Missing expected keywords: {list(missing_keywords)}")
    
    return len(errors) == 0, errors

def validate_model_types(data: Any, expected_type_name: str) -> Tuple[bool, List[str]]:
    """
    Validate that data matches expected model type.
    
    Args:
        data: Data object to validate
        expected_type_name: Expected type name
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    if data is None:
        errors.append(f"Data is None, expected {expected_type_name}")
        return False, errors
    
    # Check class name (simplified type checking)
    actual_type = type(data).__name__
    if expected_type_name not in actual_type and actual_type not in expected_type_name:
        errors.append(f"Type mismatch: expected {expected_type_name}, got {actual_type}")
    
    return len(errors) == 0, errors

def generate_test_uuid() -> str:
    """Generate a unique test UUID."""
    return str(uuid.uuid4())

def create_test_document(scenario_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a test document based on scenario configuration.
    
    Args:
        scenario_config: Scenario configuration
        
    Returns:
        Test document dictionary
    """
    # Provide default values for missing fields
    test_id = scenario_config.get("test_id", f"TEST-{generate_test_uuid()[:8]}")
    
    return {
        "document_id": generate_test_uuid(),
        "source_id": scenario_config["source_identifier"],
        "title": scenario_config["target_file"],
        "content": f"Test content for {scenario_config['description']}. " * 10,  # Repeat for sufficient length
        "metadata": {
            "source_type": scenario_config["source_type"],
            "test_scenario": test_id,
            "created_at": datetime.now().isoformat()
        }
    }

def setup_test_logging(verbose: bool = False):
    """Setup logging configuration for tests."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.getLogger().handlers.clear()

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler('test_logs.log')
        ]
    )
    
    # Suppress noisy loggers unless in verbose mode
    if not verbose:
        logging.getLogger('google').setLevel(logging.WARNING)
        logging.getLogger('google.cloud').setLevel(logging.WARNING)
        logging.getLogger('vertexai').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)

# Helper functions for async operations
async def init_vector_store_manager(config):
    """Initialize vector store manager."""
    from data_ingestion.managers.vector_store_manager import VectorStoreManager
    manager = VectorStoreManager(config.pipeline_config.vector_search)
    await manager.initialize()
    return manager

async def init_database_manager(config):
    """Initialize database manager."""
    from data_ingestion.managers.database_manager import DatabaseManager
    manager = DatabaseManager(config.pipeline_config.database)
    await manager.initialize()
    return manager

async def init_knowledge_graph_manager(config):
    """Initialize knowledge graph manager."""
    from data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager
    # Use neo4j config if available, otherwise create minimal config
    if hasattr(config.pipeline_config, 'neo4j') and config.pipeline_config.neo4j:
        kg_config = config.pipeline_config.neo4j
    else:
        # Create a minimal config if not available
        kg_config = type('KGConfig', (), {
            'uri': 'neo4j://nyx.gagan.pro',
            'user': 'neo4j', 
            'password': os.getenv('NEO4J_PASSWORD'),
            'database': 'neo4j'
        })()
    
    manager = KnowledgeGraphManager(kg_config)
    await manager.initialize()
    return manager

async def cleanup_aiohttp_sessions():
    """Force cleanup of any lingering aiohttp sessions."""
    try:
        import gc
        import asyncio
        import warnings
        
        # Suppress aiohttp warnings during cleanup
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*Unclosed client session.*")
            warnings.filterwarnings("ignore", message=".*Unclosed connector.*")
            
            # Force garbage collection
            gc.collect()
            
            # Give sessions time to close
            await asyncio.sleep(0.2)
            
            # Try to close any active sessions
            try:
                import aiohttp
                for obj in gc.get_objects():
                    if isinstance(obj, aiohttp.ClientSession) and not obj.closed:
                        try:
                            await obj.close()
                        except:
                            pass
            except ImportError:
                pass
            except Exception:
                pass
            
            # Final cleanup delay
            await asyncio.sleep(0.1)
    except Exception:
        # Ignore all cleanup errors
        pass

# Manager fixtures for E2E tests
@pytest.fixture(scope="function")
def vector_store_manager(system_config):
    """Initialize and provide vector store manager for tests."""
    import asyncio
    
    async def _init_and_run():
        manager = await init_vector_store_manager(system_config)
        return manager
    
    # Get or create event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    manager = loop.run_until_complete(_init_and_run())
    yield manager
    
    async def _cleanup():
        await manager.close()
        await cleanup_aiohttp_sessions()
    
    loop.run_until_complete(_cleanup())

@pytest.fixture(scope="function") 
def database_manager(system_config):
    """Initialize and provide database manager for tests."""
    import asyncio
    
    async def _init_and_run():
        manager = await init_database_manager(system_config)
        return manager
    
    # Get or create event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    manager = loop.run_until_complete(_init_and_run())
    yield manager
    
    async def _cleanup():
        await manager.close()
        await cleanup_aiohttp_sessions()
    
    loop.run_until_complete(_cleanup())

@pytest.fixture(scope="function")
def knowledge_graph_manager(system_config):
    """Initialize and provide knowledge graph manager for tests."""
    import asyncio
    
    async def _init_and_run():
        manager = await init_knowledge_graph_manager(system_config)
        return manager
    
    # Get or create event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    manager = loop.run_until_complete(_init_and_run())
    yield manager
    
    async def _cleanup():
        await manager.close()
        await cleanup_aiohttp_sessions()
    
    loop.run_until_complete(_cleanup())

def get_manager_sync(manager_type: str, config):
    """Get manager synchronously using asyncio.run()."""
    if manager_type == "vector":
        return asyncio.run(init_vector_store_manager(config))
    elif manager_type == "database":
        return asyncio.run(init_database_manager(config))
    elif manager_type == "knowledge_graph":
        return asyncio.run(init_knowledge_graph_manager(config))
    else:
        raise ValueError(f"Unknown manager type: {manager_type}")

async def perform_system_health_check(vector_manager, database_manager, knowledge_graph_manager):
    """
    Perform comprehensive system health check.
    
    Args:
        vector_manager: Vector store manager
        database_manager: Database manager
        knowledge_graph_manager: Knowledge graph manager
        
    Returns:
        SystemHealth object with component statuses
    """
    from data_ingestion.models import ComponentHealth, SystemHealth
    
    # Perform health checks in parallel
    health_checks = await asyncio.gather(
        vector_manager.health_check(),
        database_manager.health_check(),
        knowledge_graph_manager.health_check(),
        return_exceptions=True
    )
    
    # Extract results or create error health objects
    vector_health = health_checks[0] if isinstance(health_checks[0], ComponentHealth) else ComponentHealth(
        component_name="VectorStore",
        is_healthy=False,
        error_message=str(health_checks[0])
    )
    
    database_health = health_checks[1] if isinstance(health_checks[1], ComponentHealth) else ComponentHealth(
        component_name="Database",
        is_healthy=False,
        error_message=str(health_checks[1])
    )
    
    kg_health = health_checks[2] if isinstance(health_checks[2], ComponentHealth) else ComponentHealth(
        component_name="KnowledgeGraph",
        is_healthy=False,
        error_message=str(health_checks[2])
    )
    
    return SystemHealth(
        vector_store=vector_health,
        database=database_health,
        knowledge_graph=kg_health
    ) 