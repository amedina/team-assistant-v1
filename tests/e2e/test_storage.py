"""
Storage Layer E2E Tests

This module contains comprehensive tests for the storage layer of the team assistant
data ingestion system, including vector store, database, and knowledge graph operations.
"""

import asyncio
from datetime import datetime
import os
import logging
import pytest
from typing import Dict, Any, List
import uuid

from .fixtures import (
    E2ETestResults,
    validate_chunk_data,
    validate_retrieval_results,
    create_test_document,
    get_manager_sync,
    perform_system_health_check
)

logger = logging.getLogger(__name__)

class TestVectorStore:
    """Test vector store operations."""
    
    def test_vector_store_initialization(self, system_config, test_results: E2ETestResults):
        """Test vector store manager initialization."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.managers.vector_store_manager import VectorStoreManager
                
                manager = VectorStoreManager(system_config.pipeline_config.vector_search)
                success = await manager.initialize()
                
                if not success:
                    return False, "Vector store initialization failed"
                
                # Test health check
                health = await manager.health_check()
                if not health.is_healthy:
                    return False, f"Vector store health check failed: {health.error_message}"
                
                await manager.close()
                return True, "Vector store initialized and health check passed"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("vector_store_init", success, details, execution_time)
        if not success:
            pytest.fail(f"Vector store initialization test failed: {details}")

    def test_vector_operations(self, system_config, test_results: E2ETestResults):
        """Test vector storage and retrieval operations."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.managers.vector_store_manager import VectorStoreManager
                from data_ingestion.models import ChunkData
                
                manager = VectorStoreManager(system_config.pipeline_config.vector_search)
                await manager.initialize()
                
                # Create test chunk data
                test_doc = create_test_document({
                    "source_identifier": "vector_test",
                    "target_file": "vector_test_doc.txt",
                    "description": "Vector store operation test",
                    "source_type": "test"
                })

                # 🔍 INSPECT TEST DOCUMENT
                print(f"\n📄 TEST DOCUMENT GENERATED:")
                print(f"   Document ID: {test_doc['document_id']}")
                print(f"   Source ID: {test_doc['source_id']}")
                print(f"   Title: {test_doc['title']}")
                print(f"   Content Length: {len(test_doc['content'])} chars")
                print(f"   Content Preview: {test_doc['content'][:100]}...")
                print(f"   Metadata: {test_doc['metadata']}")
                
                from data_ingestion.models import SourceType
                
                chunk = ChunkData(
                    chunk_uuid=uuid.UUID("12345678-1234-5678-9012-123456789012"),
                    source_type=SourceType.LOCAL,  # Use SourceType enum
                    source_identifier="vector_test",
                    chunk_text_summary="This is a test chunk for vector operations.",
                    chunk_metadata={
                        "source_type": "test",                    # ✅ Required for restricts
                        "source_identifier": "vector_test",      # ✅ Required for restricts  
                        "test": "vector_operations"              # ✅ Additional test metadata
                    },
                    ingestion_timestamp=datetime.now()
                )
                # 🔍 INSPECT CHUNK DATA  
                print(f"\n📦 CHUNK DATA BEING INDEXED:")
                print(f"   Chunk UUID: {chunk.chunk_uuid}")
                print(f"   Source Type: {chunk.source_type}")
                print(f"   Source Identifier: {chunk.source_identifier}")
                print(f"   Text Summary: '{chunk.chunk_text_summary}'")
                print(f"   Metadata: {chunk.chunk_metadata}")
                
                # Test storage (using generate_and_ingest for text + metadata)
                result = await manager.generate_and_ingest(
                    texts=[chunk.chunk_text_summary or "test text"],
                    chunk_uuids=[str(chunk.chunk_uuid)],
                    metadata_list=[chunk.chunk_metadata]
                )
                # 🔍 THOROUGH VALIDATION OF UPSERT SUCCESS
                print(f"\n📊 UPSERT VALIDATION:")
                print(f"   Total Count: {result.total_count}")
                print(f"   Successful Count: {result.successful_count}")
                print(f"   Success Rate: {result.success_rate}%")
                print(f"   Processing Time: {result.processing_time_ms}ms")
                
                if not result.successful_count > 0:
                    await manager.close()
                    return False, "Failed to store chunk in vector store"
                
                # Test retrieval (using correct method name)
                query = "test chunk vector"
                results = await manager.search(query, top_k=5)
                
                # 🔍 DEBUG: What results are we actually getting?
                print(f"\n🔍 SEARCH RESULTS DEBUG:")
                print(f"   Query: '{query}'")
                print(f"   Results Found: {len(results)}")
                
                for i, result in enumerate(results):
                    print(f"\n   Result {i+1}:")
                    print(f"     Chunk UUID: {result.chunk_uuid}")
                    print(f"     Similarity Score: {result.similarity_score}")
                    print(f"     Distance Metric: {result.distance_metric}")
                    print(f"     Metadata: {result.metadata}")
                    
                    # Check if this is our inserted chunk
                    is_our_chunk = str(result.chunk_uuid) == str(chunk.chunk_uuid)
                    print(f"     Is Our Chunk: {is_our_chunk}")
                
                if not results:
                    await manager.close()
                    return False, "No results returned from vector search"
                
                # ✅ PROPER VALIDATION: Check if our chunk was found
                our_chunk_found = False
                our_chunk_similarity = 0.0
                
                for result in results:
                    if str(result.chunk_uuid) == str(chunk.chunk_uuid):
                        our_chunk_found = True
                        our_chunk_similarity = result.similarity_score
                        print(f"✅ VERIFICATION SUCCESS: Found our chunk with similarity {result.similarity_score}")
                        break
                
                if not our_chunk_found:
                    await manager.close()
                    return False, f"Our indexed chunk {chunk.chunk_uuid} was not found in search results"
                
                # Validate we got some results
                if len(results) < 1:
                    await manager.close() 
                    return False, "No search results returned"
                
                await manager.close()
                return True, f"Vector operations completed: stored 1 chunk, retrieved {len(results)} results"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("vector_operations", success, details, execution_time)
        if not success:
            pytest.fail(f"Vector operations test failed: {details}")

class TestDatabase:
    """Test database operations."""
    
    def test_database_initialization(self, system_config, test_results: E2ETestResults):
        """Test database manager initialization."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.managers.database_manager import DatabaseManager
                
                manager = DatabaseManager(system_config.pipeline_config.database)
                success = await manager.initialize()
                
                if not success:
                    return False, "Database initialization failed"
                
                # Test health check
                health = await manager.health_check()
                if not health.is_healthy:
                    return False, f"Database health check failed: {health.error_message}"
                
                await manager.close()
                return True, "Database initialized and health check passed"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("database_init", success, details, execution_time)
        if not success:
            pytest.fail(f"Database initialization test failed: {details}")

    def test_database_operations(self, system_config, test_results: E2ETestResults):
        """Test database storage and retrieval operations."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.managers.database_manager import DatabaseManager
                from data_ingestion.models import ChunkData
                
                manager = DatabaseManager(system_config.pipeline_config.database)
                await manager.initialize()
                
                # Create test chunk data
                import uuid
                from data_ingestion.models import SourceType
                from datetime import datetime
                
                chunk_uuid = uuid.uuid4()
                chunk = ChunkData(
                    chunk_uuid=chunk_uuid,
                    source_type=SourceType.LOCAL,
                    source_identifier="db_test",
                    chunk_text_summary="This is a test chunk for database operations.",
                    chunk_metadata={"test": "database_operations"},
                    ingestion_timestamp=datetime.now()
                )
                
                # Test storage
                success = await manager.ingest_chunk(chunk)
                if not success:
                    await manager.close()
                    return False, "Failed to store chunk in database"
                
                # Test retrieval
                retrieved_chunk = await manager.get_chunk(str(chunk.chunk_uuid))
                if not retrieved_chunk:
                    await manager.close()
                    return False, "Failed to retrieve chunk from database"
                
                # Validate retrieved data
                if not retrieved_chunk.chunk_uuid == chunk.chunk_uuid:
                    await manager.close()
                    return False, "Retrieved chunk UUID doesn't match stored chunk"
                
                if not retrieved_chunk.chunk_text_summary == chunk.chunk_text_summary:
                    await manager.close()
                    return False, "Retrieved chunk text doesn't match stored chunk"
                
                await manager.close()
                return True, "Database operations completed: stored and retrieved chunk successfully"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("database_operations", success, details, execution_time)
        if not success:
            pytest.fail(f"Database operations test failed: {details}")

class TestKnowledgeGraph:
    """Test knowledge graph operations."""
    
    def test_knowledge_graph_initialization(self, system_config, test_results: E2ETestResults):
        """Test knowledge graph manager initialization."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager
                
                # Use neo4j config if available, otherwise create minimal config
                if hasattr(system_config.pipeline_config, 'knowledge_graph'):
                    kg_config = system_config.pipeline_config.knowledge_graph
                else:
                    # Create a minimal config if not available
                    kg_config = type('KGConfig', (), {
                        'uri': 'neo4j://nyx.gagan.pro',
                        'user': 'neo4j', 
                        'password': os.getenv('NEO4J_PASSWORD'),
                        'database': 'neo4j'
                    })()
                
                manager = KnowledgeGraphManager(kg_config)
                success = await manager.initialize()
                
                if not success:
                    return False, "Knowledge graph initialization failed"
                
                # Test health check
                health = await manager.health_check()
                if not health.is_healthy:
                    return False, f"Knowledge graph health check failed: {health.error_message}"
                
                await manager.close()
                return True, "Knowledge graph initialized and health check passed"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("knowledge_graph_init", success, details, execution_time)
        if not success:
            pytest.fail(f"Knowledge graph initialization test failed: {details}")

    def test_knowledge_graph_operations(self, system_config, test_results: E2ETestResults):
        """Test knowledge graph storage and retrieval operations."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager
                from data_ingestion.models import Entity, Relationship
                
                # Use neo4j config if available, otherwise create minimal config
                if hasattr(system_config.pipeline_config, 'knowledge_graph'):
                    kg_config = system_config.pipeline_config.knowledge_graph
                else:
                    kg_config = type('KGConfig', (), {
                        'uri': 'neo4j://nyx.gagan.pro',
                        'user': 'neo4j', 
                        'password': os.getenv('NEO4J_PASSWORD'),
                        'database': 'neo4j'
                    })()
                
                manager = KnowledgeGraphManager(kg_config)
                await manager.initialize()
                
                # Create test entities
                from data_ingestion.models import EntityType
                import uuid
                
                entity1 = Entity(
                    id="entity_test_001",
                    name="Test Entity 1",
                    entity_type=EntityType.PERSON,
                    properties={"test": "knowledge_graph_operations"},
                    source_chunks=[uuid.uuid4()]
                )
                
                entity2 = Entity(
                    id="entity_test_002",
                    name="Test Entity 2",
                    entity_type=EntityType.ORGANIZATION,
                    properties={"test": "knowledge_graph_operations"},
                    source_chunks=[uuid.uuid4()]
                )
                
                # Create test relationship
                relationship = Relationship(
                    from_entity=entity1.id,
                    to_entity=entity2.id,
                    relationship_type="works_for",
                    properties={"test": "relationship"},
                    source_chunks=[uuid.uuid4()]
                )
                
                # Test entity storage
                success1 = await manager.ingest_entity(entity1)
                success2 = await manager.ingest_entity(entity2)
                
                if not (success1 and success2):
                    await manager.close()
                    return False, "Failed to store entities in knowledge graph"
                
                # Test relationship storage
                success3 = await manager.ingest_relationship(relationship)
                if not success3:
                    await manager.close()
                    return False, "Failed to store relationship in knowledge graph"
                
                # Test retrieval
                retrieved_entity = await manager.get_entity(entity1.id)
                if not retrieved_entity:
                    await manager.close()
                    return False, "Failed to retrieve entity from knowledge graph"
                
                await manager.close()
                return True, "Knowledge graph operations completed: stored 2 entities and 1 relationship"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("knowledge_graph_operations", success, details, execution_time)
        if not success:
            pytest.fail(f"Knowledge graph operations test failed: {details}")

class TestStorageIntegration:
    """Test integration between storage layers."""
    
    def test_multi_storage_operations(self, system_config, test_results: E2ETestResults):
        """Test operations across multiple storage layers."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.managers.vector_store_manager import VectorStoreManager
                from data_ingestion.managers.database_manager import DatabaseManager
                from data_ingestion.models import ChunkData
                
                # Initialize managers
                vector_manager = VectorStoreManager(system_config.pipeline_config.vector_search)
                database_manager = DatabaseManager(system_config.pipeline_config.database)
                
                await vector_manager.initialize()
                await database_manager.initialize()
                
                # Create test data
                import uuid
                from data_ingestion.models import SourceType
                from datetime import datetime
                
                chunk_uuid = uuid.uuid4()
                chunk = ChunkData(
                    chunk_uuid=chunk_uuid,
                    source_type=SourceType.LOCAL,
                    source_identifier="multi_storage_test",
                    chunk_text_summary="This is a test chunk for multi-storage operations.",
                    chunk_metadata={"test": "multi_storage"},
                    ingestion_timestamp=datetime.now()
                )
                
                # Store in both vector store and database
                texts = [chunk.chunk_text_summary]
                chunk_uuids = [str(chunk.chunk_uuid)]
                metadata_list = [chunk.chunk_metadata]
                
                vector_result = await vector_manager.generate_and_ingest(texts, chunk_uuids, metadata_list)
                db_success = await database_manager.ingest_chunk(chunk)
                
                if not (vector_result.successful_count > 0 and db_success):
                    await vector_manager.close()
                    await database_manager.close()
                    return False, "Failed to store chunk in both storage layers"
                
                # Retrieve from both
                vector_results = await vector_manager.search("test chunk", top_k=5)
                db_chunk = await database_manager.get_chunk(str(chunk.chunk_uuid))
                
                if not vector_results or not db_chunk:
                    await vector_manager.close()
                    await database_manager.close()
                    return False, "Failed to retrieve from both storage layers"
                
                await vector_manager.close()
                await database_manager.close()
                return True, "Multi-storage operations completed successfully"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("multi_storage_operations", success, details, execution_time)
        if not success:
            pytest.fail(f"Multi-storage operations test failed: {details}")

    def test_storage_health_checks(self, system_config, test_results: E2ETestResults):
        """Test health checks across all storage layers."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.managers.vector_store_manager import VectorStoreManager
                from data_ingestion.managers.database_manager import DatabaseManager
                from data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager
                
                # Initialize managers
                vector_manager = VectorStoreManager(system_config.pipeline_config.vector_search)
                database_manager = DatabaseManager(system_config.pipeline_config.database)
                
                # Use neo4j config if available, otherwise create minimal config
                if hasattr(system_config.pipeline_config, 'knowledge_graph'):
                    kg_config = system_config.pipeline_config.knowledge_graph
                else:
                    kg_config = type('KGConfig', (), {
                        'uri': 'neo4j://localhost:7687',
                        'user': 'neo4j', 
                        'password': '',
                        'database': 'neo4j'
                    })()
                
                kg_manager = KnowledgeGraphManager(kg_config)
                
                await vector_manager.initialize()
                await database_manager.initialize()
                await kg_manager.initialize()
                
                # Perform system health check
                system_health = await perform_system_health_check(
                    vector_manager, database_manager, kg_manager
                )
                
                # Check individual component health
                healthy_components = 0
                if system_health.vector_store.is_healthy:
                    healthy_components += 1
                if system_health.database.is_healthy:
                    healthy_components += 1
                if system_health.knowledge_graph.is_healthy:
                    healthy_components += 1
                
                await vector_manager.close()
                await database_manager.close()
                await kg_manager.close()
                
                if healthy_components == 0:
                    return False, "No storage components are healthy"
                
                return True, f"Health check completed: {healthy_components}/3 components healthy"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("storage_health_checks", success, details, execution_time)
        if not success:
            pytest.fail(f"Storage health checks test failed: {details}")

class TestStoragePerformance:
    """Test storage layer performance and scalability."""
    
    def test_batch_operations(self, system_config, test_results: E2ETestResults):
        """Test batch storage operations."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.managers.vector_store_manager import VectorStoreManager
                from data_ingestion.models import ChunkData
                
                manager = VectorStoreManager(system_config.pipeline_config.vector_search)
                await manager.initialize()
                
                # Create multiple test chunks
                import uuid
                from data_ingestion.models import SourceType
                from datetime import datetime
                
                chunks = []
                texts = []
                chunk_uuids = []
                metadata_list = []
                
                for i in range(5):  # Small batch for testing
                    chunk_uuid = uuid.uuid4()
                    chunk_text = f"This is test chunk {i} for batch operations."
                    
                    chunk = ChunkData(
                        chunk_uuid=chunk_uuid,
                        source_type=SourceType.LOCAL,
                        source_identifier=f"batch_test_{i}",
                        chunk_text_summary=chunk_text,
                        chunk_metadata={"test": "batch_operations", "batch_index": i},
                        ingestion_timestamp=datetime.now()
                    )
                    chunks.append(chunk)
                    texts.append(chunk_text)
                    chunk_uuids.append(str(chunk_uuid))
                    metadata_list.append(chunk.chunk_metadata)
                
                # Test batch storage
                batch_result = await manager.generate_and_ingest(texts, chunk_uuids, metadata_list)
                
                if batch_result.successful_count != len(chunks):
                    await manager.close()
                    return False, f"Batch storage failed: {batch_result.successful_count}/{len(chunks)} successful"
                
                # Test batch retrieval
                search_results = await manager.search("test batch", top_k=10)
                
                if len(search_results) < batch_result.successful_count:
                    await manager.close()
                    return False, f"Batch retrieval incomplete: found {len(search_results)}, expected {batch_result.successful_count}"
                
                await manager.close()
                return True, f"Batch operations completed: stored {batch_result.successful_count} chunks, retrieved {len(search_results)} results"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("batch_operations", success, details, execution_time)
        if not success:
            pytest.fail(f"Batch operations test failed: {details}") 