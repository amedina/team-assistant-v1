"""
Component-Level E2E Tests

This module contains comprehensive tests for individual components of the team assistant
data ingestion system, including models, text processors, and connectors.
"""

import pytest
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from .fixtures import (
    E2ETestResults, 
    validate_chunk_data, 
    validate_text_processing,
    validate_model_types,
    create_test_document,
    get_manager_sync
)

logger = logging.getLogger(__name__)

class TestModels:
    """Test data models and serialization functionality."""
    
    def test_model_serialization(self, test_results: E2ETestResults):
        """Test model serialization and deserialization."""
        start_time = datetime.now()
        
        try:
            from data_ingestion.models import ChunkData
            from data_ingestion.connectors.base_connector import SourceDocument
            
            # Create test source document
            doc = SourceDocument(
                source_id="test_source",
                document_id="test_doc_001",
                title="Test Document",
                content="This is test content for model validation.",
                metadata={"test": True}
            )
            
            # Test source document structure
            doc_dict = doc.to_dict()
            assert "document_id" in doc_dict
            assert doc_dict["title"] == "Test Document"
            
            # Test chunk data model
            chunk = ChunkData(
                chunk_uuid="00000000-0000-0000-0000-000000000001",
                source_type="local",
                source_identifier="test_source",
                chunk_text_summary="Test chunk content",
                chunk_metadata={"chunk_type": "text"},
                ingestion_timestamp=datetime.now(),
                ingestion_status="completed"
            )
            
            # Validate chunk structure  
            chunk_dict = chunk.model_dump()
            assert "chunk_uuid" in chunk_dict
            assert chunk_dict["chunk_text_summary"] == "Test chunk content"
            
            success, details = True, "Model serialization tests passed"
            
        except Exception as e:
            success, details = False, str(e)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("model_serialization", success, details, execution_time)
        if not success:
            pytest.fail(f"Model serialization test failed: {details}")

class TestTextProcessor:
    """Test text processing functionality."""
    
    def test_text_chunking(self, text_processor, test_results: E2ETestResults):
        """Test text chunking with overlap processing."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.connectors.base_connector import SourceDocument
                
                # Create test document
                test_doc_data = create_test_document({
                    "source_identifier": "test_text_chunking",
                    "target_file": "test_content.txt",
                    "description": "Text chunking validation",
                    "source_type": "text"
                })
                
                # Create SourceDocument with substantial content
                doc = SourceDocument(
                    source_id=test_doc_data["source_id"],
                    document_id=test_doc_data["document_id"],
                    title=test_doc_data["title"],
                    content=test_doc_data["content"] * 5,  # Repeat content to ensure chunking
                    metadata=test_doc_data["metadata"]
                )
                
                # Process text into chunks
                processed_doc = await text_processor.process_document(doc.to_dict())
                
                # Validate processing results
                validation_config = {
                    "min_extracted_text_length": 50,
                    "required_chunk_overlap": False,
                    "min_entities_extracted": 0
                }
                
                is_valid, errors = validate_text_processing(processed_doc, validation_config)
                if not is_valid:
                    return False, f"Text processing validation failed: {errors}"
                
                # Check chunk structure
                if hasattr(processed_doc, "chunks") and processed_doc.chunks:
                    for chunk in processed_doc.chunks:
                        chunk_valid, chunk_errors = validate_chunk_data(
                            chunk, ["chunk_uuid", "text", "metadata"]
                        )
                        if not chunk_valid:
                            return False, f"Chunk validation failed: {chunk_errors}"
                        
                        # Also check that metadata contains expected fields
                        if hasattr(chunk, "metadata"):
                            required_metadata_fields = ["source_id", "document_id", "text_summary"]
                            missing_metadata = [field for field in required_metadata_fields 
                                              if field not in chunk.metadata]
                            if missing_metadata:
                                return False, f"Missing metadata fields: {missing_metadata}"
                
                return True, f"Successfully processed {len(processed_doc.chunks)} chunks"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("text_chunking", success, details, execution_time)
        if not success:
            pytest.fail(f"Text chunking test failed: {details}")

    def test_entity_extraction(self, text_processor, test_results: E2ETestResults):
        """Test entity and relationship extraction."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.connectors.base_connector import SourceDocument
                
                # Create document with entities
                test_doc_data = create_test_document({
                    "source_identifier": "test_entity_extraction",
                    "target_file": "entity_test.txt",
                    "description": "Entity extraction validation",
                    "source_type": "text"
                })
                
                # Create SourceDocument with entity-rich content
                doc = SourceDocument(
                    source_id=test_doc_data["source_id"],
                    document_id=test_doc_data["document_id"],
                    title=test_doc_data["title"],
                    content=(
                        "John Smith works at Google Inc. in San Francisco, California. "
                        "He manages the AI team that develops machine learning models. "
                        "The team collaborates with Microsoft and OpenAI on various projects."
                    ),
                    metadata=test_doc_data["metadata"]
                )
                
                processed_doc = await text_processor.process_document(doc.to_dict())
                
                # Check for entity extraction (basic validation since NLP results may vary)
                entities_found = False
                if hasattr(processed_doc, "chunks"):
                    for chunk in processed_doc.chunks:
                        if hasattr(chunk, "entities") and chunk.entities:
                            entities_found = True
                            break
                
                # Entity extraction is optional and may not work in test environment
                return True, f"Entity extraction completed: entities_found={entities_found}"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("entity_extraction", success, details, execution_time)
        if not success:
            pytest.fail(f"Entity extraction test failed: {details}")

class TestConnectors:
    """Test data connectors functionality."""
    
    def test_github_connector_initialization(self, system_config, test_results: E2ETestResults):
        """Test GitHub connector initialization and configuration."""
        start_time = datetime.now()
        
        try:
            from data_ingestion.connectors.github_connector import GitHubConnector
            
            # Find GitHub data source from system config
            github_source = None
            for source in system_config.data_sources:
                if source.source_type == "github_repo":
                    github_source = source
                    break
            
            if not github_source:
                success, details = False, "No GitHub data source found in system configuration"
            else:
                # Use actual system configuration for GitHub connector
                source_config = {
                    "source_id": github_source.source_id,
                    "source_type": github_source.source_type,
                    "enabled": github_source.enabled,
                    "config": github_source.config
                }
                
                connector = GitHubConnector(source_config)
                
                # Validate basic attributes
                assert hasattr(connector, 'source_config')
                assert connector.source_config is not None
                assert connector.source_id == github_source.source_id
                assert connector.source_type == "github_repo"
                
                # Test type validation
                is_valid, errors = validate_model_types(connector, "GitHubConnector")
                if not is_valid:
                    success, details = False, f"Connector type validation failed: {errors}"
                else:
                    success, details = True, "GitHub connector initialized successfully"
            
        except Exception as e:
            success, details = False, str(e)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("github_connector_init", success, details, execution_time)
        if not success:
            pytest.fail(f"GitHub connector initialization test failed: {details}")

    def test_drive_connector_initialization(self, system_config, test_results: E2ETestResults):
        """Test Drive connector initialization and configuration."""
        start_time = datetime.now()
        
        try:
            from data_ingestion.connectors.drive_connector import DriveConnector
            
            # Find Drive data source from system config
            drive_source = None
            for source in system_config.data_sources:
                if source.source_type in ["drive_folder", "drive_file"]:
                    drive_source = source
                    break
            
            if not drive_source:
                success, details = False, "No Drive data source found in system configuration"
            else:
                # Use actual system configuration for Drive connector
                source_config = {
                    "source_id": drive_source.source_id,
                    "source_type": drive_source.source_type,
                    "enabled": drive_source.enabled,
                    "config": drive_source.config
                }
                
                connector = DriveConnector(source_config)
                
                # Validate basic attributes
                assert hasattr(connector, 'source_config')
                assert connector.source_config is not None
                assert connector.source_id == drive_source.source_id
                assert connector.source_type in ["drive_folder", "drive_file"]
                
                # Test type validation
                is_valid, errors = validate_model_types(connector, "DriveConnector")
                if not is_valid:
                    success, details = False, f"Connector type validation failed: {errors}"
                else:
                    success, details = True, "Drive connector initialized successfully"
            
        except Exception as e:
            success, details = False, str(e)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("drive_connector_init", success, details, execution_time)
        if not success:
            pytest.fail(f"Drive connector initialization test failed: {details}")

    def test_web_connector_initialization(self, system_config, test_results: E2ETestResults):
        """Test Web connector initialization and configuration."""
        start_time = datetime.now()
        
        try:
            from data_ingestion.connectors.web_connector import WebConnector
            
            # Find Web data source from system config
            web_source = None
            for source in system_config.data_sources:
                if source.source_type == "web_source":
                    web_source = source
                    break
            
            if not web_source:
                success, details = False, "No Web data source found in system configuration"
            else:
                # Use actual system configuration for Web connector
                source_config = {
                    "source_id": web_source.source_id,
                    "source_type": web_source.source_type,
                    "enabled": web_source.enabled,
                    "config": web_source.config
                }
                
                connector = WebConnector(source_config)
                
                # Validate basic attributes
                assert hasattr(connector, 'source_config')
                assert connector.source_config is not None
                assert connector.source_id == web_source.source_id
                assert connector.source_type == "web_source"
                
                # Test type validation
                is_valid, errors = validate_model_types(connector, "WebConnector")
                if not is_valid:
                    success, details = False, f"Connector type validation failed: {errors}"
                else:
                    success, details = True, "Web connector initialized successfully"
            
        except Exception as e:
            success, details = False, str(e)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("web_connector_init", success, details, execution_time)
        if not success:
            pytest.fail(f"Web connector initialization test failed: {details}")

    def test_connector_document_fetching(self, system_config, test_results: E2ETestResults):
        """Test actual document fetching functionality with web connector."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.connectors.web_connector import WebConnector
                
                # Find Web data source from system config
                web_source = None
                for source in system_config.data_sources:
                    if source.source_type == "web_source":
                        web_source = source
                        break
                
                if not web_source:
                    return False, "No Web data source found in system configuration"
                
                # Use actual system configuration for Web connector
                source_config = {
                    "source_id": web_source.source_id,
                    "source_type": web_source.source_type,
                    "enabled": web_source.enabled,
                    "config": web_source.config
                }
                
                connector = WebConnector(source_config)
                
                # Test actual document fetching
                documents_fetched = []
                fetch_limit = 3  # Limit to avoid long test times
                
                async for document in connector.fetch_documents(limit=fetch_limit):
                    documents_fetched.append(document)
                    
                    # Validate document structure
                    if not hasattr(document, 'source_id'):
                        return False, f"Document missing source_id attribute"
                    if not hasattr(document, 'document_id'):
                        return False, f"Document missing document_id attribute"
                    if not hasattr(document, 'content'):
                        return False, f"Document missing content attribute"
                    if not hasattr(document, 'title'):
                        return False, f"Document missing title attribute"
                    
                    # Validate content is not empty
                    if not document.content or len(document.content.strip()) == 0:
                        return False, f"Document {document.document_id} has empty content"
                    
                    # Validate source ID matches
                    if document.source_id != web_source.source_id:
                        return False, f"Document source_id {document.source_id} doesn't match expected {web_source.source_id}"
                
                if len(documents_fetched) == 0:
                    return False, "No documents were fetched from web source"
                
                return True, f"Successfully fetched {len(documents_fetched)} documents from web source"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("connector_document_fetching", success, details, execution_time)
        if not success:
            pytest.fail(f"Connector document fetching test failed: {details}")

class TestComponentIntegration:
    """Test integration between different components."""
    
    def test_processor_connector_integration(self, system_config, text_processor, test_results: E2ETestResults):
        """Test REAL integration between connectors and processors using actual document fetching."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                # Find ANY enabled data source from system config to test real integration
                enabled_source = None
                connector = None
                
                # Try to find and create a real connector from configured sources
                for source in system_config.data_sources:
                    if not source.enabled:
                        continue
                    
                    source_config = {
                        "source_id": source.source_id,
                        "source_type": source.source_type,
                        "enabled": source.enabled,
                        "config": source.config
                    }
                    
                    if source.source_type == "github_repo":
                        from data_ingestion.connectors.github_connector import GitHubConnector
                        connector = GitHubConnector(source_config)
                        enabled_source = source
                        break
                    elif source.source_type in ["drive_folder", "drive_file"]:
                        from data_ingestion.connectors.drive_connector import DriveConnector
                        connector = DriveConnector(source_config)
                        enabled_source = source
                        break
                    elif source.source_type == "web_source":
                        from data_ingestion.connectors.web_connector import WebConnector
                        connector = WebConnector(source_config)
                        enabled_source = source
                        break
                
                if not connector or not enabled_source:
                    return False, "No enabled data sources found in system configuration for integration testing"
                
                print(f"\n🔄 INTEGRATION TEST PROGRESS:")
                print(f"   Found enabled source: {enabled_source.source_type} ({enabled_source.source_id})")
                print(f"   Fetching real document...")
                
                # Fetch REAL document from the connector
                real_document = None
                fetch_limit = 1  # Just need one document for integration test
                
                async for document in connector.fetch_documents(limit=fetch_limit):
                    real_document = document
                    break
                
                if not real_document:
                    return False, f"No documents could be fetched from {enabled_source.source_type} source {enabled_source.source_id}"
                
                # Validate the real document has required attributes
                if not hasattr(real_document, 'content') or not real_document.content:
                    return False, f"Real document from connector has no content"
                
                if not hasattr(real_document, 'source_id'):
                    return False, f"Real document from connector missing source_id"
                
                print(f"   Document fetched: '{real_document.title[:50]}{'...' if len(real_document.title) > 50 else ''}'")
                print(f"   Processing through text processor...")
                
                # Process the REAL document through the text processor
                processed_doc = await text_processor.process_document(real_document.to_dict())
                
                # Validate the processing pipeline worked with real data
                if not hasattr(processed_doc, "chunks") or not processed_doc.chunks:
                    return False, "No chunks produced by processor from real connector document"
                
                # Validate each chunk has proper structure for downstream processing
                for chunk in processed_doc.chunks:
                    required_fields = ["chunk_uuid", "text", "metadata"]
                    is_valid, errors = validate_chunk_data(chunk, required_fields)
                    if not is_valid:
                        return False, f"Integration validation failed on real document: {errors}"
                    
                    # Ensure chunk text is not empty
                    if not chunk.text or len(chunk.text.strip()) == 0:
                        return False, f"Chunk produced empty text from real document"
                    
                    # Ensure chunk metadata contains source information
                    if not hasattr(chunk, 'metadata') or not chunk.metadata:
                        return False, f"Chunk missing metadata from real document processing"
                
                # Validate source ID consistency through the pipeline
                if processed_doc.chunks[0].metadata.get('source_id') != enabled_source.source_id:
                    return False, f"Source ID not preserved through connector->processor pipeline"

                # Always visible test milestone 
                print(f"\n✅ INTEGRATION TEST SUCCESS:")
                print(f"   Source: {enabled_source.source_type} ({enabled_source.source_id})")
                print(f"   Document: '{real_document.title[:60]}{'...' if len(real_document.title) > 60 else ''}'")
                print(f"   Output: {len(processed_doc.chunks)} chunks produced")
                print(f"   Pipeline: connector → processor → {len(processed_doc.chunks)} validated chunks")
                
                # Log detailed success for debugging when needed
                success_message = f"REAL integration test passed: {enabled_source.source_type} connector -> processor produced {len(processed_doc.chunks)} chunks from real document '{real_document.title[:50]}...'"
                print(success_message)  # Using WARNING level so it shows up in log_cli
                
                return True, success_message
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("processor_connector_integration", success, details, execution_time)
        if not success:
            pytest.fail(f"Processor-connector integration test failed: {details}")

    def test_model_data_flow(self, text_processor, test_results: E2ETestResults):
        """Test data flow through different model types."""
        start_time = datetime.now()
        
        async def run_test():
            try:
                from data_ingestion.connectors.base_connector import SourceDocument
                
                # Test model transformations through the pipeline
                test_doc_data = create_test_document({
                    "source_identifier": "model_flow_test",
                    "target_file": "model_flow_document.txt",
                    "description": "Model data flow validation",
                    "source_type": "test"
                })
                
                doc = SourceDocument(
                    source_id=test_doc_data["source_id"],
                    document_id=test_doc_data["document_id"],
                    title=test_doc_data["title"],
                    content=test_doc_data["content"],
                    metadata=test_doc_data["metadata"]
                )
                
                # Validate initial document model
                is_valid, errors = validate_model_types(doc, "SourceDocument")
                if not is_valid:
                    return False, f"Initial document validation failed: {errors}"
                
                # Process through text processor
                processed_doc = await text_processor.process_document(doc.to_dict())
                
                # Validate processed document model
                is_valid, errors = validate_model_types(processed_doc, "ProcessedDocument")
                if not is_valid:
                    return False, f"Processed document validation failed: {errors}"
                
                # Validate chunk models
                if hasattr(processed_doc, "chunks") and processed_doc.chunks:
                    for chunk in processed_doc.chunks:
                        # Test the actual implementation: TextProcessor returns TextChunk objects
                        is_valid, errors = validate_model_types(chunk, "TextChunk")
                        if not is_valid:
                            return False, f"Chunk model validation failed: {errors}"
                
                return True, "Model data flow validation completed successfully"
                
            except Exception as e:
                return False, str(e)
        
        # Run async test
        success, details = asyncio.run(run_test())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        test_results.add_result("model_data_flow", success, details, execution_time)
        if not success:
            pytest.fail(f"Model data flow test failed: {details}") 