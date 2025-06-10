#!/usr/bin/env python3
"""
End-to-End Data Pipeline Tests.

This module tests the complete data ingestion pipeline from connectors through
processors to storage systems (Vector Store, Database, Knowledge Graph).
Updated to use actual models and text processor for realistic testing.
"""

import pytest
import asyncio
import logging
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.configuration import SystemConfig, get_system_config
from data_ingestion.processors.text_processor import TextProcessor, ProcessedDocument
from data_ingestion.models import (
    ChunkData, EmbeddingData, Entity, Relationship, EntityType, SourceType,
    IngestionStatus, VectorRetrievalResult, RetrievalContext, ComponentHealth
)
from data_ingestion.connectors.base_connector import SourceDocument

# Import our E2E test modules
from .test_scenarios import TestScenario, get_test_scenario, get_all_scenarios, TestPhase
from .fixtures.configuration import *
from .fixtures.managers import *
from .fixtures.test_data import *
from .utils.assertions import *
from .utils.reporting import get_reporter, TestMetrics
from .fixtures.custom_assertions import assert_pipeline_health, assert_ingestion_success, assert_retrieval_quality
from .utils.e2e_reporter import E2ETestReporter

logger = logging.getLogger(__name__)


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.parametrize("test_scenario", ["github", "drive_folder", "drive_file", "web"], indirect=True)
class TestE2EDataPipeline:
    """
    End-to-end tests for the complete data processing pipeline.
    
    Tests cover:
    - Document ingestion from various sources
    - Text processing with actual TextProcessor
    - Entity and relationship extraction
    - Storage in Vector Store, Database, and Knowledge Graph
    - Data retrieval and validation using actual models
    - Pipeline health monitoring and error handling
    """
    
    async def test_full_pipeline_flow(
        self,
        test_scenario: TestScenario,
        text_processor: TextProcessor,
        processed_test_documents: List[ProcessedDocument],
        processed_test_chunks: List[ChunkData],
        extracted_entities: List[Entity],
        extracted_relationships: List[Relationship],
        vector_store_manager,
        database_manager,
        knowledge_graph_manager,
        test_isolation_id: str,
        e2e_reporter: E2ETestReporter
    ):
        """
        Test complete end-to-end pipeline flow with actual models and text processor.
        
        Pipeline Flow:
        1. Document processing with TextProcessor (chunking + entity extraction)
        2. Database storage of ChunkData models
        3. Vector Store embedding generation and storage
        4. Knowledge Graph entity and relationship storage
        5. Retrieval validation from all systems
        6. Data consistency validation
        """
        e2e_reporter.log_test_start("Full Pipeline Flow", test_scenario.test_id)
        
        try:
            # Validate processed test data using actual models
            assert len(processed_test_documents) > 0, f"No documents processed for scenario {test_scenario.test_id}"
            assert len(processed_test_chunks) >= test_scenario.min_chunks_expected, \
                f"Expected at least {test_scenario.min_chunks_expected} chunks, got {len(processed_test_chunks)}"
            
            # Validate chunk data structure using actual ChunkData model
            for chunk in processed_test_chunks:
                assert isinstance(chunk, ChunkData), f"Chunk data is not a proper ChunkData model: {type(chunk)}"
                assert chunk.chunk_uuid, "Chunk UUID is missing"
                assert chunk.source_type, "Source type is missing"
                assert chunk.chunk_text_summary, "Chunk text summary is missing"
                assert chunk.chunk_metadata, "Chunk metadata is missing"
                assert chunk.ingestion_status == IngestionStatus.COMPLETED, "Chunk status should be COMPLETED"
            
            logger.info(f"✓ Document processing validation passed: {len(processed_test_documents)} docs → {len(processed_test_chunks)} chunks")
            
            # === PHASE 1: Database Storage ===
            logger.info("Phase 1: Testing database storage...")
            database_successful_count, database_total_count = await database_manager.batch_ingest_chunks(processed_test_chunks)
            
            assert database_successful_count > 0, "No chunks were stored in database"
            assert database_successful_count == database_total_count, \
                f"Database storage failed: {database_successful_count}/{database_total_count} chunks stored"
            
            logger.info(f"✓ Database storage successful: {database_successful_count}/{database_total_count} chunks")
            
            # === PHASE 2: Vector Store Storage ===
            logger.info("Phase 2: Testing vector store storage...")
            
            # Extract text content for embedding generation
            texts = []
            chunk_uuids = []
            metadata_list = []
            
            for chunk in processed_test_chunks:
                # Get full text from processed documents
                full_text = None
                for doc in processed_test_documents:
                    for text_chunk in doc.chunks:
                        if text_chunk.chunk_uuid == str(chunk.chunk_uuid):
                            full_text = text_chunk.text
                            break
                    if full_text:
                        break
                
                if full_text:
                    texts.append(full_text)
                    chunk_uuids.append(str(chunk.chunk_uuid))
                    metadata_list.append(chunk.chunk_metadata)
            
            assert len(texts) > 0, "No text content available for embedding generation"
            
            # Generate and store embeddings using coordinator pattern
            vector_result = await vector_store_manager.generate_and_ingest(texts, chunk_uuids, metadata_list)
            
            assert vector_result.successful_count > 0, "No embeddings were stored in vector store"
            assert vector_result.successful_count == len(texts), \
                f"Vector store storage failed: {vector_result.successful_count}/{len(texts)} embeddings stored"
            
            logger.info(f"✓ Vector store storage successful: {vector_result.successful_count}/{len(texts)} embeddings")
            
            # === PHASE 3: Knowledge Graph Storage ===
            logger.info("Phase 3: Testing knowledge graph storage...")
            
            # Store entities if available
            entities_successful = 0
            if extracted_entities:
                # Validate entity data structure
                for entity in extracted_entities:
                    assert isinstance(entity, Entity), f"Entity is not a proper Entity model: {type(entity)}"
                    assert entity.id, "Entity ID is missing"
                    assert entity.entity_type, "Entity type is missing"
                    assert entity.name, "Entity name is missing"
                
                entity_result = await knowledge_graph_manager.batch_ingest_entities(extracted_entities)
                entities_successful = entity_result.successful_count
                
                assert entities_successful > 0, "No entities were stored in knowledge graph"
                logger.info(f"✓ Knowledge graph entity storage: {entities_successful}/{len(extracted_entities)} entities")
            else:
                logger.info("⚠ No entities extracted for knowledge graph storage")
            
            # Store relationships if available
            relationships_successful = 0
            if extracted_relationships:
                # Validate relationship data structure
                for relationship in extracted_relationships:
                    assert isinstance(relationship, Relationship), f"Relationship is not a proper Relationship model: {type(relationship)}"
                    assert relationship.from_entity, "From entity is missing"
                    assert relationship.to_entity, "To entity is missing"
                    assert relationship.relationship_type, "Relationship type is missing"
                
                relationship_result = await knowledge_graph_manager.batch_ingest_relationships(extracted_relationships)
                relationships_successful = relationship_result.successful_count
                
                assert relationships_successful > 0, "No relationships were stored in knowledge graph"
                logger.info(f"✓ Knowledge graph relationship storage: {relationships_successful}/{len(extracted_relationships)} relationships")
            else:
                logger.info("⚠ No relationships extracted for knowledge graph storage")
            
            # === PHASE 4: Retrieval Validation ===
            logger.info("Phase 4: Testing data retrieval...")
            
            # Test database retrieval
            stored_chunks = await database_manager.get_chunks_by_source(test_isolation_id, limit=50)
            assert len(stored_chunks) > 0, "No chunks retrieved from database"
            logger.info(f"✓ Database retrieval: {len(stored_chunks)} chunks retrieved")
            
            # Test vector store retrieval using content from processed documents
            if texts:
                search_query = texts[0][:100]  # Use first 100 chars as search query
                vector_results = await vector_store_manager.similarity_search(
                    query_text=search_query,
                    limit=5,
                    metadata_filter={"test_isolation_id": test_isolation_id}
                )
                
                assert len(vector_results) > 0, "No results from vector store similarity search"
                assert all(isinstance(result, VectorRetrievalResult) for result in vector_results), \
                    "Vector results are not proper VectorRetrievalResult models"
                logger.info(f"✓ Vector store retrieval: {len(vector_results)} similar chunks found")
            
            # Test knowledge graph retrieval
            if entities_successful > 0:
                # Get entities by type
                entity_types = list(set(entity.entity_type for entity in extracted_entities))
                if entity_types:
                    retrieved_entities = await knowledge_graph_manager.get_entities_by_type(
                        entity_type=entity_types[0],
                        limit=10
                    )
                    assert len(retrieved_entities) > 0, "No entities retrieved from knowledge graph"
                    logger.info(f"✓ Knowledge graph entity retrieval: {len(retrieved_entities)} entities")
            
            # === PHASE 5: Data Consistency Validation ===
            logger.info("Phase 5: Testing data consistency...")
            
            # Check chunk UUID consistency across systems
            stored_chunk_uuids = {str(chunk.chunk_uuid) for chunk in stored_chunks}
            processed_chunk_uuids = {str(chunk.chunk_uuid) for chunk in processed_test_chunks}
            
            missing_in_db = processed_chunk_uuids - stored_chunk_uuids
            assert len(missing_in_db) == 0, f"Chunks missing from database: {missing_in_db}"
            
            # Check metadata consistency
            for stored_chunk in stored_chunks:
                assert stored_chunk.chunk_metadata.get("test_isolation_id") == test_isolation_id, \
                    "Test isolation ID not preserved in stored chunk metadata"
            
            logger.info("✓ Data consistency validation passed")
            
            # === SUCCESS REPORTING ===
            pipeline_stats = {
                "documents_processed": len(processed_test_documents),
                "chunks_processed": len(processed_test_chunks),
                "database_chunks_stored": database_successful_count,
                "vector_embeddings_stored": vector_result.successful_count,
                "entities_stored": entities_successful,
                "relationships_stored": relationships_successful,
                "chunks_retrieved": len(stored_chunks),
                "vector_results_found": len(vector_results) if 'vector_results' in locals() else 0
            }
            
            e2e_reporter.log_pipeline_stats(pipeline_stats)
            e2e_reporter.log_test_success("Full Pipeline Flow", pipeline_stats)
            
            logger.info(f"🎉 Full pipeline flow test PASSED for scenario: {test_scenario.test_id}")
            logger.info(f"📊 Pipeline stats: {pipeline_stats}")
            
        except Exception as e:
            error_context = {
                "scenario": test_scenario.test_id,
                "processed_documents": len(processed_test_documents) if 'processed_test_documents' in locals() else 0,
                "processed_chunks": len(processed_test_chunks) if 'processed_test_chunks' in locals() else 0,
                "extracted_entities": len(extracted_entities) if 'extracted_entities' in locals() else 0,
                "extracted_relationships": len(extracted_relationships) if 'extracted_relationships' in locals() else 0
            }
            e2e_reporter.log_test_failure("Full Pipeline Flow", str(e), error_context)
            logger.error(f"💥 Full pipeline flow test FAILED for scenario {test_scenario.test_id}: {e}")
            raise
    
    async def test_text_processor_integration(
        self,
        test_scenario: TestScenario,
        text_processor: TextProcessor,
        processed_test_documents: List[ProcessedDocument],
        test_isolation_id: str,
        e2e_reporter: E2ETestReporter
    ):
        """
        Test TextProcessor integration and document processing capabilities.
        
        Tests:
        - Document processing with chunking
        - Entity extraction functionality
        - Relationship extraction functionality
        - Processing statistics and metadata
        """
        e2e_reporter.log_test_start("Text Processor Integration", test_scenario.test_id)
        
        try:
            # Validate TextProcessor configuration
            processor_stats = text_processor.get_processing_stats()
            assert processor_stats["chunk_size"] > 0, "TextProcessor chunk size not configured"
            assert processor_stats["chunk_overlap"] >= 0, "TextProcessor chunk overlap not configured"
            assert processor_stats["entity_extraction_enabled"], "Entity extraction should be enabled for E2E testing"
            
            logger.info(f"✓ TextProcessor configuration validated: {processor_stats}")
            
            # Validate processed documents
            assert len(processed_test_documents) > 0, "No documents were processed by TextProcessor"
            
            total_chunks = 0
            total_entities = 0
            total_relationships = 0
            
            for doc in processed_test_documents:
                assert isinstance(doc, ProcessedDocument), "Document is not a ProcessedDocument instance"
                assert doc.source_id, "ProcessedDocument missing source_id"
                assert doc.document_id, "ProcessedDocument missing document_id"
                assert doc.title, "ProcessedDocument missing title"
                assert doc.chunks, "ProcessedDocument has no chunks"
                assert doc.processing_stats, "ProcessedDocument missing processing stats"
                
                # Validate chunks within document
                for chunk in doc.chunks:
                    assert chunk.chunk_uuid, "Chunk missing UUID"
                    assert chunk.text, "Chunk missing text content"
                    assert chunk.chunk_index >= 0, "Chunk has invalid index"
                    assert chunk.metadata, "Chunk missing metadata"
                    assert chunk.metadata.get("test_isolation_id") == test_isolation_id, \
                        "Chunk metadata missing test isolation ID"
                    
                    total_chunks += 1
                    
                    # Count entities and relationships
                    if chunk.entities:
                        total_entities += len(chunk.entities)
                        # Validate entity structure
                        for entity in chunk.entities:
                            assert isinstance(entity, Entity), "Entity is not an Entity model instance"
                            assert entity.id, "Entity missing ID"
                            assert entity.entity_type, "Entity missing type"
                            assert entity.name, "Entity missing name"
                    
                    if chunk.relationships:
                        total_relationships += len(chunk.relationships)
                        # Validate relationship structure
                        for relationship in chunk.relationships:
                            assert isinstance(relationship, Relationship), "Relationship is not a Relationship model instance"
                            assert relationship.from_entity, "Relationship missing from_entity"
                            assert relationship.to_entity, "Relationship missing to_entity"
                            assert relationship.relationship_type, "Relationship missing type"
                
                # Validate processing statistics
                assert doc.processing_stats.get("processing_time", 0) >= 0, "Invalid processing time"
                assert doc.processing_stats.get("total_chunks", 0) == len(doc.chunks), "Chunk count mismatch in stats"
            
            processing_summary = {
                "documents_processed": len(processed_test_documents),
                "total_chunks": total_chunks,
                "total_entities": total_entities,
                "total_relationships": total_relationships,
                "min_chunks_expected": test_scenario.min_chunks_expected,
                "meets_expectations": total_chunks >= test_scenario.min_chunks_expected,
                "has_entities": total_entities > 0,
                "has_relationships": total_relationships > 0
            }
            
            # Validate minimum expectations
            assert total_chunks >= test_scenario.min_chunks_expected, \
                f"Expected at least {test_scenario.min_chunks_expected} chunks, got {total_chunks}"
            
            # Entity extraction should work for most content
            if not test_scenario.ingestion_only:
                assert total_entities > 0, "Entity extraction should have found some entities in the content"
            
            e2e_reporter.log_processing_summary(processing_summary)
            e2e_reporter.log_test_success("Text Processor Integration", processing_summary)
            
            logger.info(f"✓ TextProcessor integration test PASSED for scenario: {test_scenario.test_id}")
            logger.info(f"📊 Processing summary: {processing_summary}")
            
        except Exception as e:
            error_context = {
                "scenario": test_scenario.test_id,
                "processor_config": text_processor.get_processing_stats() if 'text_processor' in locals() else {},
                "documents_available": len(processed_test_documents) if 'processed_test_documents' in locals() else 0
            }
            e2e_reporter.log_test_failure("Text Processor Integration", str(e), error_context)
            logger.error(f"💥 TextProcessor integration test FAILED for scenario {test_scenario.test_id}: {e}")
            raise
    
    async def test_model_validation(
        self,
        test_scenario: TestScenario,
        processed_test_chunks: List[ChunkData],
        extracted_entities: List[Entity],
        extracted_relationships: List[Relationship],
        test_isolation_id: str,
        e2e_reporter: E2ETestReporter
    ):
        """
        Test data model validation and type safety.
        
        Tests:
        - ChunkData model validation
        - Entity model validation
        - Relationship model validation
        - Type constraints and data integrity
        """
        e2e_reporter.log_test_start("Model Validation", test_scenario.test_id)
        
        try:
            # === ChunkData Model Validation ===
            logger.info("Testing ChunkData model validation...")
            
            assert len(processed_test_chunks) > 0, "No ChunkData objects to validate"
            
            for chunk in processed_test_chunks:
                # Type validation
                assert isinstance(chunk, ChunkData), f"Expected ChunkData, got {type(chunk)}"
                
                # Required field validation
                assert isinstance(chunk.chunk_uuid, uuid.UUID), "chunk_uuid should be a UUID"
                assert isinstance(chunk.source_type, SourceType), "source_type should be a SourceType enum"
                assert isinstance(chunk.ingestion_status, IngestionStatus), "ingestion_status should be an IngestionStatus enum"
                
                # Data validation
                assert chunk.source_identifier, "source_identifier cannot be empty"
                assert chunk.chunk_text_summary, "chunk_text_summary cannot be empty"
                assert chunk.chunk_metadata, "chunk_metadata cannot be empty"
                assert chunk.ingestion_timestamp, "ingestion_timestamp is required"
                
                # Metadata validation
                metadata = chunk.chunk_metadata
                assert isinstance(metadata, dict), "chunk_metadata should be a dictionary"
                assert metadata.get("test_isolation_id") == test_isolation_id, "Test isolation ID not in metadata"
                assert "chunk_index" in metadata, "chunk_index missing from metadata"
                assert "chunk_length" in metadata, "chunk_length missing from metadata"
            
            logger.info(f"✓ ChunkData validation passed: {len(processed_test_chunks)} chunks")
            
            # === Entity Model Validation ===
            logger.info("Testing Entity model validation...")
            
            if extracted_entities:
                for entity in extracted_entities:
                    # Type validation
                    assert isinstance(entity, Entity), f"Expected Entity, got {type(entity)}"
                    
                    # Required field validation
                    assert entity.id, "Entity ID cannot be empty"
                    assert entity.name, "Entity name cannot be empty"
                    assert isinstance(entity.entity_type, EntityType), "entity_type should be an EntityType enum"
                    
                    # Optional field validation
                    if entity.properties:
                        assert isinstance(entity.properties, dict), "Entity properties should be a dictionary"
                    
                    if entity.source_chunks:
                        assert isinstance(entity.source_chunks, list), "source_chunks should be a list"
                        for chunk_uuid in entity.source_chunks:
                            assert isinstance(chunk_uuid, uuid.UUID), "source_chunks should contain UUIDs"
                
                logger.info(f"✓ Entity validation passed: {len(extracted_entities)} entities")
            else:
                logger.info("⚠ No entities to validate")
            
            # === Relationship Model Validation ===
            logger.info("Testing Relationship model validation...")
            
            if extracted_relationships:
                for relationship in extracted_relationships:
                    # Type validation
                    assert isinstance(relationship, Relationship), f"Expected Relationship, got {type(relationship)}"
                    
                    # Required field validation
                    assert relationship.from_entity, "from_entity cannot be empty"
                    assert relationship.to_entity, "to_entity cannot be empty"
                    assert relationship.relationship_type, "relationship_type cannot be empty"
                    
                    # Relationship integrity
                    assert relationship.from_entity != relationship.to_entity, \
                        "Relationship cannot be self-referencing"
                    
                    # Optional field validation
                    if relationship.properties:
                        assert isinstance(relationship.properties, dict), "Relationship properties should be a dictionary"
                    
                    if relationship.source_chunks:
                        assert isinstance(relationship.source_chunks, list), "source_chunks should be a list"
                        for chunk_uuid in relationship.source_chunks:
                            assert isinstance(chunk_uuid, uuid.UUID), "source_chunks should contain UUIDs"
                
                logger.info(f"✓ Relationship validation passed: {len(extracted_relationships)} relationships")
            else:
                logger.info("⚠ No relationships to validate")
            
            # === Cross-Model Validation ===
            logger.info("Testing cross-model validation...")
            
            # Validate entity-chunk relationships
            chunk_uuids = {chunk.chunk_uuid for chunk in processed_test_chunks}
            
            for entity in extracted_entities:
                if entity.source_chunks:
                    for source_chunk_uuid in entity.source_chunks:
                        assert source_chunk_uuid in chunk_uuids, \
                            f"Entity {entity.id} references non-existent chunk {source_chunk_uuid}"
            
            # Validate relationship-chunk relationships
            for relationship in extracted_relationships:
                if relationship.source_chunks:
                    for source_chunk_uuid in relationship.source_chunks:
                        assert source_chunk_uuid in chunk_uuids, \
                            f"Relationship {relationship.from_entity}->{relationship.to_entity} references non-existent chunk {source_chunk_uuid}"
            
            logger.info("✓ Cross-model validation passed")
            
            # === Success Reporting ===
            validation_summary = {
                "chunks_validated": len(processed_test_chunks),
                "entities_validated": len(extracted_entities),
                "relationships_validated": len(extracted_relationships),
                "model_types_validated": ["ChunkData", "Entity", "Relationship"],
                "all_validations_passed": True
            }
            
            e2e_reporter.log_test_success("Model Validation", validation_summary)
            
            logger.info(f"✓ Model validation test PASSED for scenario: {test_scenario.test_id}")
            logger.info(f"📊 Validation summary: {validation_summary}")
            
        except Exception as e:
            error_context = {
                "scenario": test_scenario.test_id,
                "chunks_available": len(processed_test_chunks) if 'processed_test_chunks' in locals() else 0,
                "entities_available": len(extracted_entities) if 'extracted_entities' in locals() else 0,
                "relationships_available": len(extracted_relationships) if 'extracted_relationships' in locals() else 0
            }
            e2e_reporter.log_test_failure("Model Validation", str(e), error_context)
            logger.error(f"💥 Model validation test FAILED for scenario {test_scenario.test_id}: {e}")
            raise


# Command-line execution support
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run E2E Data Pipeline Tests")
    parser.add_argument("--scenario", choices=["github", "drive", "drive_file", "web", "all"], 
                       default="all", help="Test scenario to run")
    parser.add_argument("--targets", help="Comma-separated storage targets (vector,database,knowledge_graph)")
    parser.add_argument("--phase", choices=["ingestion", "retrieval", "full"], 
                       default="full", help="Test phase to execute")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet output")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else (logging.WARNING if args.quiet else logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Suppress some verbose library logs
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Build pytest arguments
    pytest_args = [__file__, "-v"]
    
    if args.scenario != "all":
        pytest_args.extend(["-k", f"test_full_pipeline_scenario[{args.scenario}]"])
    
    if args.targets:
        # This would require custom pytest fixture parametrization
        # For now, we'll note the targets selection
        print(f"Note: Target filtering ({args.targets}) should be implemented via pytest fixtures")
    
    if args.phase == "ingestion":
        pytest_args.extend(["-k", "test_ingestion_only"])
    elif args.phase == "retrieval":
        pytest_args.extend(["-k", "test_retrieval_only"])
    
    # Run pytest
    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code) 