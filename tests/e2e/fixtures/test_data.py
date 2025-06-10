"""
Test data fixtures for E2E testing.

This module provides pytest fixtures for generating test documents, managing test data
lifecycle, and creating connector instances for data ingestion testing. Updated to use
the actual models and text processor for realistic document processing.
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from pathlib import Path
import uuid

from config.configuration import SystemConfig, DataSourceConfig
from data_ingestion.connectors.base_connector import SourceDocument, BaseConnector
from data_ingestion.processors.text_processor import TextProcessor, ProcessedDocument
from data_ingestion.models import (
    ChunkData, EmbeddingData, Entity, Relationship, EntityType, SourceType,
    IngestionStatus, ChunkMetadata
)
from ..test_scenarios import TestScenario

logger = logging.getLogger(__name__)


@pytest.fixture
def test_scenario(request) -> TestScenario:
    """
    Provide test scenario based on pytest parameter.
    
    Args:
        request: Pytest request object
        
    Returns:
        TestScenario object for the current test
    """
    scenario_name = getattr(request, 'param', 'github')
    
    # Import scenarios here to avoid circular imports
    from ..test_scenarios import get_test_scenario
    
    scenario = get_test_scenario(scenario_name)
    if not scenario:
        pytest.fail(f"Unknown test scenario: {scenario_name}")
    
    logger.info(f"Using test scenario: {scenario.test_id} - {scenario.description}")
    return scenario


@pytest.fixture
async def text_processor() -> TextProcessor:
    """
    Provide initialized TextProcessor for document processing.
    
    Returns:
        Configured TextProcessor instance
    """
    processor = TextProcessor(
        chunk_size=800,  # Smaller chunks for testing
        chunk_overlap=100,
        enable_entity_extraction=True
    )
    
    logger.info("Initialized TextProcessor for E2E testing")
    return processor


@pytest.fixture
async def connector_instance(test_scenario: TestScenario, connector_config_override: Dict[str, Any]) -> AsyncGenerator[Optional[BaseConnector], None]:
    """
    Create and initialize a connector instance for the test scenario.
    
    Args:
        test_scenario: Test scenario configuration
        connector_config_override: Connector configuration override
        
    Yields:
        Initialized connector instance or None if creation failed
    """
    connector = None
    
    try:
        # Create connector based on source type
        if test_scenario.source_type == "github_repo":
            from data_ingestion.connectors.github_connector import GitHubConnector
            connector = GitHubConnector(connector_config_override)
        elif test_scenario.source_type == "drive_folder":
            try:
                # Try to import drive connector
                from data_ingestion.connectors.drive_connector import DriveConnector
                connector = DriveConnector(connector_config_override)
            except ImportError:
                logger.warning("DriveConnector not available - skipping drive test")
                yield None
                return
        elif test_scenario.source_type == "drive_file":
            try:
                # Try to import drive connector
                from data_ingestion.connectors.drive_connector import DriveConnector
                connector = DriveConnector(connector_config_override)
            except ImportError:
                logger.warning("DriveConnector not available - skipping drive file test")
                yield None
                return
        elif test_scenario.source_type == "web_source":
            try:
                # Try to import web connector
                from data_ingestion.connectors.web_connector import WebConnector
                connector = WebConnector(connector_config_override)
            except ImportError:
                logger.warning("WebConnector not available - skipping web test")
                yield None
                return
        else:
            logger.error(f"Unknown connector type: {test_scenario.source_type}")
            yield None
            return
        
        # Initialize the connector
        logger.info(f"Initializing {test_scenario.source_type} connector...")
        success = await connector.connect()
        
        if not success:
            logger.error(f"Failed to initialize {test_scenario.source_type} connector")
            yield None
            return
        
        logger.info(f"{test_scenario.source_type} connector initialized successfully")
        yield connector
        
    except Exception as e:
        logger.error(f"Error creating {test_scenario.source_type} connector: {e}")
        yield None
    finally:
        # Cleanup
        if connector:
            try:
                logger.info(f"Closing {test_scenario.source_type} connector...")
                await connector.disconnect()
                logger.info(f"{test_scenario.source_type} connector closed successfully")
            except Exception as e:
                logger.warning(f"Error closing connector: {e}")


@pytest.fixture
async def test_documents(connector_instance: Optional[BaseConnector], test_scenario: TestScenario) -> List[SourceDocument]:
    """
    Fetch test documents from the connector.
    
    Args:
        connector_instance: Initialized connector instance
        test_scenario: Test scenario configuration
        
    Returns:
        List of SourceDocument objects fetched from the source
    """
    if not connector_instance:
        logger.warning("No connector instance available - returning empty document list")
        return []
    
    try:
        logger.info(f"Fetching documents from {test_scenario.source_type} source...")
        
        documents = []
        limit = min(test_scenario.min_chunks_expected * 2, 10)  # Reasonable limit for testing
        
        # Fetch documents with timeout
        async for doc in connector_instance.fetch_documents(limit=limit):
            documents.append(doc)
            logger.debug(f"Fetched document: {doc.title[:50]}...")
            
            # Safety limit
            if len(documents) >= limit:
                break
        
        logger.info(f"Fetched {len(documents)} documents from {test_scenario.source_type}")
        
        # Validate minimum document count
        if len(documents) == 0:
            logger.warning(f"No documents fetched from {test_scenario.source_type}")
        elif len(documents) < test_scenario.min_chunks_expected:
            logger.warning(f"Fetched {len(documents)} documents, but expected at least {test_scenario.min_chunks_expected}")
        
        return documents
        
    except asyncio.TimeoutError:
        logger.error(f"Timeout while fetching documents from {test_scenario.source_type}")
        return []
    except Exception as e:
        logger.error(f"Error fetching documents from {test_scenario.source_type}: {e}")
        return []


@pytest.fixture
async def processed_test_documents(
    test_documents: List[SourceDocument], 
    text_processor: TextProcessor,
    test_isolation_id: str
) -> List[ProcessedDocument]:
    """
    Process test documents using the actual TextProcessor.
    
    Args:
        test_documents: List of source documents
        text_processor: Configured TextProcessor instance
        test_isolation_id: Test isolation ID
        
    Returns:
        List of ProcessedDocument objects with chunks, entities, and relationships
    """
    if not test_documents:
        logger.warning("No test documents to process")
        return []
    
    processed_documents = []
    
    for doc in test_documents:
        try:
            # Convert SourceDocument to dict format expected by text processor
            doc_dict = {
                'content': doc.content,
                'title': doc.title,
                'source_id': doc.source_id,
                'document_id': doc.document_id,
                'metadata': {
                    **doc.metadata,
                    'test_isolation_id': test_isolation_id,
                    'source_type': doc.source_id,  # Map to source_type for compatibility
                    'url': doc.url,
                    'content_type': doc.content_type,
                    'last_modified': doc.last_modified.isoformat() if doc.last_modified else None
                }
            }
            
            # Process document using actual TextProcessor
            processed_doc = await text_processor.process_document(doc_dict, extract_entities=True)
            
            if processed_doc.chunks:
                processed_documents.append(processed_doc)
                logger.info(f"Processed document '{doc.title}': {len(processed_doc.chunks)} chunks, "
                          f"{sum(len(chunk.entities or []) for chunk in processed_doc.chunks)} entities, "
                          f"{sum(len(chunk.relationships or []) for chunk in processed_doc.chunks)} relationships")
            else:
                logger.warning(f"No chunks created for document: {doc.title}")
        
        except Exception as e:
            logger.error(f"Error processing document {doc.title}: {e}")
            continue
    
    logger.info(f"Successfully processed {len(processed_documents)} documents with TextProcessor")
    return processed_documents


@pytest.fixture
def processed_test_chunks(processed_test_documents: List[ProcessedDocument]) -> List[ChunkData]:
    """
    Convert processed documents to ChunkData objects using the actual models.
    
    Args:
        processed_test_documents: List of ProcessedDocument objects
        
    Returns:
        List of ChunkData objects ready for storage
    """
    if not processed_test_documents:
        logger.warning("No processed documents to convert to chunks")
        return []
    
    chunk_data_list = []
    
    for processed_doc in processed_test_documents:
        for text_chunk in processed_doc.chunks:
            try:
                # Create ChunkData using the actual model
                chunk_data = ChunkData(
                    chunk_uuid=uuid.UUID(text_chunk.chunk_uuid),
                    source_type=SourceType(text_chunk.metadata.get('source_type', 'github_repo')),
                    source_identifier=text_chunk.metadata.get('document_id', processed_doc.document_id),
                    chunk_text_summary=text_chunk.metadata.get('text_summary', text_chunk.text[:200]),
                    chunk_metadata=text_chunk.metadata,
                    ingestion_timestamp=datetime.now(),
                    source_last_modified_at=datetime.fromisoformat(text_chunk.metadata['last_modified']) if text_chunk.metadata.get('last_modified') else None,
                    source_content_hash=text_chunk.metadata.get('content_hash'),
                    last_indexed_at=datetime.now(),
                    ingestion_status=IngestionStatus.COMPLETED
                )
                
                chunk_data_list.append(chunk_data)
                
            except Exception as e:
                logger.error(f"Error creating ChunkData for chunk {text_chunk.chunk_uuid}: {e}")
                continue
    
    logger.info(f"Converted {len(chunk_data_list)} chunks to ChunkData objects")
    return chunk_data_list


@pytest.fixture
def extracted_entities(processed_test_documents: List[ProcessedDocument]) -> List[Entity]:
    """
    Extract entities from processed documents.
    
    Args:
        processed_test_documents: List of ProcessedDocument objects
        
    Returns:
        List of Entity objects extracted from the documents
    """
    entities = []
    
    for processed_doc in processed_test_documents:
        for text_chunk in processed_doc.chunks:
            if text_chunk.entities:
                entities.extend(text_chunk.entities)
    
    logger.info(f"Extracted {len(entities)} entities from processed documents")
    return entities


@pytest.fixture
def extracted_relationships(processed_test_documents: List[ProcessedDocument]) -> List[Relationship]:
    """
    Extract relationships from processed documents.
    
    Args:
        processed_test_documents: List of ProcessedDocument objects
        
    Returns:
        List of Relationship objects extracted from the documents
    """
    relationships = []
    
    for processed_doc in processed_test_documents:
        for text_chunk in processed_doc.chunks:
            if text_chunk.relationships:
                relationships.extend(text_chunk.relationships)
    
    logger.info(f"Extracted {len(relationships)} relationships from processed documents")
    return relationships


@pytest.fixture
def mock_test_documents(test_scenario: TestScenario, test_isolation_id: str) -> List[SourceDocument]:
    """
    Generate mock test documents when real connectors are not available.
    
    Args:
        test_scenario: Test scenario configuration
        test_isolation_id: Test isolation ID
        
    Returns:
        List of mock SourceDocument objects
    """
    logger.info(f"Generating mock documents for scenario: {test_scenario.test_id}")
    
    documents = []
    
    # Generate documents based on scenario
    if test_scenario.source_type == "github_repo":
        documents = [
            SourceDocument(
                source_id=f"test-{test_scenario.scenario_name}",
                document_id=f"{test_scenario.source_identifier}/README.md",
                title="README.md",
                content=f"""# Privacy Sandbox Analysis Tool

This is a Chrome extension that helps developers analyze Privacy Sandbox features and APIs. The tool provides comprehensive analysis capabilities for understanding how Privacy Sandbox technologies work.

## Features
- Analysis of Chrome Privacy Sandbox APIs including Topics API, FLEDGE, Trust Tokens
- Developer tools integration for real-time analysis
- Comprehensive reporting and analytics dashboard
- Cookie and tracking analysis tools

## Installation
The Privacy Sandbox Analysis Tool can be installed from the Chrome Web Store. It integrates directly with Chrome DevTools to provide real-time analysis of Privacy Sandbox API usage.

## Usage
The tool provides insights into privacy sandbox analysis capabilities and helps developers understand how their websites interact with Privacy Sandbox APIs. It includes features for analyzing Topics API classifications, FLEDGE auction mechanics, and Trust Token operations.

## Contributing
We welcome contributions to improve the Privacy Sandbox Analysis Tool. Please see our contributing guidelines for more information about how to get involved in the development process.
""",
                metadata={
                    "source": "github",
                    "repository": test_scenario.source_identifier,
                    "file_path": "README.md",
                    "test_isolation_id": test_isolation_id,
                    "file_size": 1200,
                    "language": "en"
                },
                content_type="text",
                url=f"https://github.com/{test_scenario.source_identifier}/blob/main/README.md",
                last_modified=datetime.now()
            )
        ]
    
    elif test_scenario.source_type in ["drive_folder", "drive_file"]:
        documents = [
            SourceDocument(
                source_id=f"test-{test_scenario.scenario_name}",
                document_id=test_scenario.source_identifier,
                title="DevRel Assistance Guide",
                content="""# DevRel Assistance and Development Guidelines

This document provides comprehensive guidance for developer relations assistance and development processes. It covers best practices for community engagement, technical documentation, and developer experience optimization.

## DevRel Best Practices
- Comprehensive documentation that helps developers understand complex technical concepts
- Developer-focused assistance programs that provide direct support
- Community engagement strategies that build strong developer relationships
- Technical guidance and mentorship programs
- Developer experience optimization through feedback and iteration

## Assistance Framework
The assistance framework helps development teams create better developer experiences through:
- Structured support processes
- Technical documentation standards
- Community building initiatives
- Developer feedback integration
- Continuous improvement methodologies

## Development Process
Our development process emphasizes collaboration, quality, and developer-centric design. We focus on creating tools and resources that genuinely help developers succeed in their projects and contribute to the broader development community.

## Community Engagement
Effective community engagement requires authentic relationships, valuable content, and responsive support. We prioritize understanding developer needs and providing practical assistance that makes a real difference in their daily work.
""",
                metadata={
                    "source": "drive",
                    "file_id": test_scenario.source_identifier,
                    "file_type": "google_doc",
                    "test_isolation_id": test_isolation_id,
                    "file_size": 1500,
                    "language": "en"
                },
                content_type="text",
                url=f"https://docs.google.com/document/d/{test_scenario.source_identifier}",
                last_modified=datetime.now()
            )
        ]
    
    elif test_scenario.source_type == "web_source":
        documents = [
            SourceDocument(
                source_id=f"test-{test_scenario.scenario_name}",
                document_id=test_scenario.source_identifier,
                title="Python Tutorial Introduction",
                content="""# An Informal Introduction to Python

Python is a high-level programming language with elegant syntax and powerful capabilities. This tutorial introduces the basic concepts and features of Python programming.

## Numbers and Operators
Python provides powerful mathematical operators for performing calculations:
- Use the ** operator to calculate powers: 2 ** 3 equals 8
- Use the * operator for multiplication: 5 * 4 equals 20
- Use the + operator for addition: 10 + 5 equals 15
- Use the - operator for subtraction: 10 - 3 equals 7
- Use the / operator for division: 15 / 3 equals 5.0

## Working with Powers
The power operator (**) is particularly useful for mathematical calculations. For example:
- Calculate squares: x ** 2
- Calculate cubes: x ** 3
- Calculate square roots: x ** 0.5

## Operator Precedence
Python follows standard mathematical operator precedence rules. Powers are calculated before multiplication and division, which are calculated before addition and subtraction. You can use parentheses to override the default precedence.

## Variables and Expressions
Python allows you to store values in variables and use them in mathematical expressions. The language provides intuitive operator precedence for mathematical calculations, making it easy to write complex mathematical expressions.
""",
                metadata={
                    "source": "web",
                    "url": test_scenario.source_identifier,
                    "title": "Python Tutorial Introduction",
                    "test_isolation_id": test_isolation_id,
                    "file_size": 1300,
                    "language": "en"
                },
                content_type="text",
                url=test_scenario.source_identifier,
                last_modified=datetime.now()
            )
        ]
    
    logger.info(f"Generated {len(documents)} mock documents with realistic content")
    return documents


@pytest.fixture
def fallback_test_data(test_documents: List[SourceDocument], mock_test_documents: List[SourceDocument]) -> List[SourceDocument]:
    """
    Provide fallback test data using mock documents if real documents are not available.
    
    Args:
        test_documents: Real test documents from connectors
        mock_test_documents: Mock test documents
        
    Returns:
        List of SourceDocument objects (real or mock)
    """
    if test_documents:
        logger.info(f"Using {len(test_documents)} real test documents")
        return test_documents
    else:
        logger.info(f"Using {len(mock_test_documents)} mock test documents as fallback")
        return mock_test_documents


@pytest.fixture
async def test_data_validation(
    processed_test_documents: List[ProcessedDocument],
    processed_test_chunks: List[ChunkData],
    extracted_entities: List[Entity],
    extracted_relationships: List[Relationship],
    test_scenario: TestScenario
) -> Dict[str, Any]:
    """
    Validate processed test data against scenario requirements using actual models.
    
    Args:
        processed_test_documents: Processed documents
        processed_test_chunks: Processed chunks
        extracted_entities: Extracted entities
        extracted_relationships: Extracted relationships
        test_scenario: Test scenario configuration
        
    Returns:
        Validation results dictionary
    """
    validation_results = {
        "documents_processed": len(processed_test_documents),
        "chunks_count": len(processed_test_chunks),
        "entities_count": len(extracted_entities),
        "relationships_count": len(extracted_relationships),
        "meets_minimum_chunks": len(processed_test_chunks) >= test_scenario.min_chunks_expected,
        "has_entities": len(extracted_entities) > 0,
        "has_relationships": len(extracted_relationships) > 0,
        "chunks_have_content": all(chunk.chunk_text_summary and chunk.chunk_text_summary.strip() for chunk in processed_test_chunks),
        "chunks_have_metadata": all(chunk.chunk_metadata for chunk in processed_test_chunks),
        "chunks_have_valid_uuids": all(chunk.chunk_uuid for chunk in processed_test_chunks),
        "validation_errors": []
    }
    
    # Detailed validation
    if validation_results["documents_processed"] == 0:
        validation_results["validation_errors"].append("No documents were processed")
    
    if validation_results["chunks_count"] == 0:
        validation_results["validation_errors"].append("No test chunks available")
    
    if not validation_results["meets_minimum_chunks"]:
        validation_results["validation_errors"].append(
            f"Only {len(processed_test_chunks)} chunks, expected at least {test_scenario.min_chunks_expected}"
        )
    
    if not validation_results["chunks_have_content"]:
        validation_results["validation_errors"].append("Some chunks have empty content")
    
    if not validation_results["chunks_have_metadata"]:
        validation_results["validation_errors"].append("Some chunks are missing metadata")
    
    if not validation_results["chunks_have_valid_uuids"]:
        validation_results["validation_errors"].append("Some chunks have invalid UUIDs")
    
    # Check for expected keywords in content (if not ingestion-only)
    if processed_test_chunks and not test_scenario.ingestion_only:
        all_content = " ".join(chunk.chunk_text_summary or "" for chunk in processed_test_chunks).lower()
        
        found_keywords = []
        missing_keywords = []
        
        for keyword in test_scenario.expected_keywords:
            if keyword != "N/A - ingestion only" and keyword.lower() in all_content:
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        validation_results["keywords_found"] = found_keywords
        validation_results["keywords_missing"] = missing_keywords
        validation_results["has_expected_keywords"] = len(found_keywords) > 0
        
        if not validation_results["has_expected_keywords"] and not test_scenario.ingestion_only:
            validation_results["validation_errors"].append(f"No expected keywords found in content: {test_scenario.expected_keywords}")
    
    # Validate entity types
    entity_types = [entity.entity_type for entity in extracted_entities]
    validation_results["entity_types_found"] = list(set(entity_types))
    
    # Validate relationship types
    relationship_types = [rel.relationship_type for rel in extracted_relationships]
    validation_results["relationship_types_found"] = list(set(relationship_types))
    
    # Log validation results
    if validation_results["validation_errors"]:
        logger.warning(f"Test data validation issues: {validation_results['validation_errors']}")
    else:
        logger.info("Test data validation passed")
    
    logger.info(f"Processing summary: {validation_results['documents_processed']} docs → "
               f"{validation_results['chunks_count']} chunks → "
               f"{validation_results['entities_count']} entities → "
               f"{validation_results['relationships_count']} relationships")
    
    return validation_results


class TestDataError(Exception):
    """Raised when test data is invalid or unavailable."""
    pass 