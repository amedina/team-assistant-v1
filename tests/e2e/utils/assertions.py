"""
Custom assertions for E2E testing.

This module provides specialized assertion functions for validating data consistency
across storage systems and testing complex scenarios in the Team Assistant system.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from data_ingestion.models import VectorRetrievalResult, ChunkData, Entity, Relationship
from ..test_scenarios import TestScenario

logger = logging.getLogger(__name__)


class E2EAssertionError(AssertionError):
    """Custom assertion error for E2E tests."""
    pass


def assert_ingestion_success(
    results: Dict[str, Any],
    scenario: TestScenario,
    min_success_rate: float = 0.8
) -> None:
    """
    Assert that ingestion was successful across all storage targets.
    
    Args:
        results: Ingestion results from all storage systems
        scenario: Test scenario configuration
        min_success_rate: Minimum success rate required (0.0 to 1.0)
        
    Raises:
        E2EAssertionError: If ingestion did not meet success criteria
    """
    errors = []
    
    for storage_type, result in results.items():
        if result is None:
            errors.append(f"{storage_type} ingestion returned None")
            continue
        
        # Check if result has success metrics
        if hasattr(result, 'successful_count') and hasattr(result, 'total_count'):
            if result.total_count == 0:
                errors.append(f"{storage_type} ingestion processed 0 items")
                continue
            
            success_rate = result.successful_count / result.total_count
            if success_rate < min_success_rate:
                errors.append(
                    f"{storage_type} ingestion success rate {success_rate:.2f} "
                    f"is below minimum {min_success_rate:.2f} "
                    f"({result.successful_count}/{result.total_count})"
                )
        
        # Check for error messages
        if hasattr(result, 'error_messages') and result.error_messages:
            error_summary = f"{len(result.error_messages)} errors"
            if result.error_messages:
                # Show first error as example
                error_summary += f" (e.g., {result.error_messages[0]})"
            errors.append(f"{storage_type} ingestion had {error_summary}")
    
    if errors:
        error_msg = f"Ingestion assertion failed for scenario {scenario.test_id}:\n" + \
                   "\n".join(f"  - {error}" for error in errors)
        logger.error(error_msg)
        raise E2EAssertionError(error_msg)
    
    logger.info(f"Ingestion success assertion passed for scenario {scenario.test_id}")


def assert_retrieval_results(
    vector_results: List[VectorRetrievalResult],
    scenario: TestScenario,
    min_results: Optional[int] = None
) -> None:
    """
    Assert that retrieval results meet scenario expectations.
    
    Args:
        vector_results: Vector search results
        scenario: Test scenario configuration
        min_results: Minimum number of results expected (defaults to scenario min_chunks_expected)
        
    Raises:
        E2EAssertionError: If retrieval results don't meet expectations
    """
    if min_results is None:
        min_results = scenario.min_chunks_expected
    
    errors = []
    
    # Check minimum result count
    if len(vector_results) < min_results:
        errors.append(
            f"Got {len(vector_results)} results, expected at least {min_results}"
        )
    
    # Check similarity scores
    if vector_results:
        top_similarity = vector_results[0].similarity_score
        if top_similarity < scenario.min_vector_similarity:
            errors.append(
                f"Top similarity score {top_similarity:.3f} is below minimum {scenario.min_vector_similarity:.3f}"
            )
    
    # Check for expected source pattern
    if vector_results and scenario.expected_source_pattern:
        source_found = False
        for result in vector_results:
            if hasattr(result, 'metadata') and result.metadata:
                # Check various possible source identifiers
                metadata = result.metadata
                source_fields = ['source_identifier', 'source_id', 'source', 'repository', 'url']
                
                for field in source_fields:
                    if field in metadata:
                        source_value = str(metadata[field])
                        if scenario.expected_source_pattern.lower() in source_value.lower():
                            source_found = True
                            break
                
                if source_found:
                    break
        
        if not source_found:
            errors.append(
                f"Expected source pattern '{scenario.expected_source_pattern}' not found in results"
            )
    
    if errors:
        error_msg = f"Retrieval assertion failed for scenario {scenario.test_id}:\n" + \
                   "\n".join(f"  - {error}" for error in errors)
        logger.error(error_msg)
        raise E2EAssertionError(error_msg)
    
    logger.info(f"Retrieval results assertion passed for scenario {scenario.test_id}")


def assert_data_consistency(
    vector_results: List[VectorRetrievalResult],
    database_chunks: List[ChunkData],
    graph_entities: List[Entity],
    test_isolation_id: str
) -> None:
    """
    Assert data consistency across all three storage systems.
    
    Args:
        vector_results: Results from vector search
        database_chunks: Chunks from database
        graph_entities: Entities from knowledge graph
        test_isolation_id: Test isolation ID for validation
        
    Raises:
        E2EAssertionError: If data is inconsistent across systems
    """
    errors = []
    
    # Extract UUIDs from each system
    vector_uuids = {str(result.chunk_uuid) for result in vector_results}
    database_uuids = {str(chunk.chunk_uuid) for chunk in database_chunks}
    
    # Check UUID consistency between vector and database
    if vector_uuids and database_uuids:
        vector_only = vector_uuids - database_uuids
        database_only = database_uuids - vector_uuids
        
        if vector_only:
            errors.append(f"UUIDs in vector store but not database: {list(vector_only)[:5]}")
        
        if database_only:
            errors.append(f"UUIDs in database but not vector store: {list(database_only)[:5]}")
    
    # Check test isolation ID consistency
    test_related_db_chunks = [
        chunk for chunk in database_chunks 
        if chunk.chunk_metadata and 
        chunk.chunk_metadata.get('test_isolation_id') == test_isolation_id
    ]
    
    if database_chunks and not test_related_db_chunks:
        errors.append(f"No database chunks found with test isolation ID: {test_isolation_id}")
    
    # Check graph entities have source chunks that exist in other systems
    if graph_entities:
        entity_source_uuids = set()
        for entity in graph_entities:
            if hasattr(entity, 'source_chunks') and entity.source_chunks:
                entity_source_uuids.update(str(uuid) for uuid in entity.source_chunks)
        
        if entity_source_uuids:
            # Check if entity source chunks exist in database
            missing_in_db = entity_source_uuids - database_uuids
            if missing_in_db and len(missing_in_db) == len(entity_source_uuids):
                # All entity source chunks are missing from database
                errors.append(f"Graph entities reference chunks not found in database: {list(missing_in_db)[:5]}")
    
    # Check metadata consistency
    for vector_result in vector_results[:5]:  # Check first 5 for performance
        uuid_str = str(vector_result.chunk_uuid)
        matching_db_chunks = [chunk for chunk in database_chunks if str(chunk.chunk_uuid) == uuid_str]
        
        if matching_db_chunks:
            db_chunk = matching_db_chunks[0]
            
            # Check basic metadata consistency
            if hasattr(vector_result, 'metadata') and vector_result.metadata:
                vector_metadata = vector_result.metadata
                db_metadata = db_chunk.chunk_metadata or {}
                
                # Check for test isolation ID consistency
                vector_test_id = vector_metadata.get('test_isolation_id')
                db_test_id = db_metadata.get('test_isolation_id')
                
                if vector_test_id and db_test_id and vector_test_id != db_test_id:
                    errors.append(f"Test isolation ID mismatch for {uuid_str}: vector={vector_test_id}, db={db_test_id}")
    
    if errors:
        error_msg = f"Data consistency assertion failed:\n" + \
                   "\n".join(f"  - {error}" for error in errors)
        logger.error(error_msg)
        raise E2EAssertionError(error_msg)
    
    logger.info("Data consistency assertion passed")


def assert_context_manager_flow(
    context_result: Dict[str, Any],
    scenario: TestScenario,
    required_components: Optional[List[str]] = None
) -> None:
    """
    Assert that Context Manager flow returned expected structured output.
    
    Args:
        context_result: Result from Context Manager flow
        scenario: Test scenario configuration
        required_components: Required components in context result
        
    Raises:
        E2EAssertionError: If Context Manager flow didn't produce expected output
    """
    if required_components is None:
        required_components = ['vector_results', 'database_metadata', 'graph_context']
    
    errors = []
    
    # Check that result is a dictionary
    if not isinstance(context_result, dict):
        errors.append(f"Context result is not a dictionary: {type(context_result)}")
        return
    
    # Check required components
    for component in required_components:
        if component not in context_result:
            errors.append(f"Missing required component: {component}")
    
    # Check vector results
    if 'vector_results' in context_result:
        vector_results = context_result['vector_results']
        if not isinstance(vector_results, list):
            errors.append(f"vector_results is not a list: {type(vector_results)}")
        elif len(vector_results) == 0 and not scenario.ingestion_only:
            errors.append("vector_results is empty for non-ingestion-only scenario")
    
    # Check database metadata
    if 'database_metadata' in context_result:
        db_metadata = context_result['database_metadata']
        if not isinstance(db_metadata, list):
            errors.append(f"database_metadata is not a list: {type(db_metadata)}")
    
    # Check graph context
    if 'graph_context' in context_result:
        graph_context = context_result['graph_context']
        if not isinstance(graph_context, dict):
            errors.append(f"graph_context is not a dictionary: {type(graph_context)}")
        else:
            # Check for expected graph context structure
            expected_graph_keys = ['query_entities', 'related_entities', 'relationships']
            for key in expected_graph_keys:
                if key not in graph_context:
                    errors.append(f"Missing graph context key: {key}")
    
    # Check response time if provided
    if 'response_time_ms' in context_result:
        response_time = context_result['response_time_ms']
        if response_time > scenario.max_response_time_ms:
            errors.append(
                f"Response time {response_time}ms exceeds maximum {scenario.max_response_time_ms}ms"
            )
    
    if errors:
        error_msg = f"Context Manager flow assertion failed for scenario {scenario.test_id}:\n" + \
                   "\n".join(f"  - {error}" for error in errors)
        logger.error(error_msg)
        raise E2EAssertionError(error_msg)
    
    logger.info(f"Context Manager flow assertion passed for scenario {scenario.test_id}")


def assert_performance_metrics(
    timing_data: Dict[str, float],
    scenario: TestScenario,
    max_total_time_ms: Optional[float] = None
) -> None:
    """
    Assert that performance metrics meet scenario requirements.
    
    Args:
        timing_data: Dictionary of operation names to timing in milliseconds
        scenario: Test scenario configuration
        max_total_time_ms: Maximum total time allowed (defaults to scenario max_response_time_ms)
        
    Raises:
        E2EAssertionError: If performance metrics don't meet requirements
    """
    if max_total_time_ms is None:
        max_total_time_ms = scenario.max_response_time_ms
    
    errors = []
    
    # Calculate total time
    total_time = sum(timing_data.values())
    
    if total_time > max_total_time_ms:
        errors.append(
            f"Total time {total_time:.2f}ms exceeds maximum {max_total_time_ms:.2f}ms"
        )
    
    # Check individual operation times (optional detailed checks)
    for operation, time_ms in timing_data.items():
        if time_ms < 0:
            errors.append(f"Invalid negative time for {operation}: {time_ms}ms")
        
        # Add operation-specific timing checks if needed
        if operation == "vector_search" and time_ms > scenario.max_response_time_ms * 0.7:
            # Vector search shouldn't take more than 70% of total allowed time
            errors.append(f"Vector search time {time_ms:.2f}ms is too high")
    
    if errors:
        error_msg = f"Performance metrics assertion failed for scenario {scenario.test_id}:\n" + \
                   "\n".join(f"  - {error}" for error in errors)
        logger.error(error_msg)
        raise E2EAssertionError(error_msg)
    
    logger.info(f"Performance metrics assertion passed for scenario {scenario.test_id}")


def assert_keyword_presence(
    content_sources: List[str],
    expected_keywords: List[str],
    min_keyword_matches: int = 1
) -> None:
    """
    Assert that expected keywords are present in content.
    
    Args:
        content_sources: List of content strings to search
        expected_keywords: List of keywords to find
        min_keyword_matches: Minimum number of keywords that must be found
        
    Raises:
        E2EAssertionError: If insufficient keywords are found
    """
    if not content_sources:
        raise E2EAssertionError("No content sources provided for keyword assertion")
    
    # Combine all content and normalize
    all_content = " ".join(content_sources).lower()
    
    # Filter out placeholder keywords
    valid_keywords = [kw for kw in expected_keywords if kw != "N/A - ingestion only"]
    
    if not valid_keywords:
        logger.info("No valid keywords to check - skipping keyword assertion")
        return
    
    # Find matching keywords
    found_keywords = []
    
    for keyword in valid_keywords:
        if keyword.lower() in all_content:
            found_keywords.append(keyword)
    
    if len(found_keywords) < min_keyword_matches:
        missing_keywords = [kw for kw in valid_keywords if kw not in found_keywords]
        error_msg = f"Found {len(found_keywords)} keywords, expected at least {min_keyword_matches}. " \
                   f"Missing: {missing_keywords}"
        logger.error(error_msg)
        raise E2EAssertionError(error_msg)
    
    logger.info(f"Keyword assertion passed: found {found_keywords}")


def assert_no_duplicate_data(
    all_chunk_uuids: List[str],
    isolation_id: str
) -> None:
    """
    Assert that there are no duplicate chunks in the system.
    
    Args:
        all_chunk_uuids: List of all chunk UUIDs from all systems
        isolation_id: Test isolation ID for context
        
    Raises:
        E2EAssertionError: If duplicate UUIDs are found
    """
    uuid_counts = {}
    for uuid in all_chunk_uuids:
        uuid_counts[uuid] = uuid_counts.get(uuid, 0) + 1
    
    duplicates = {uuid: count for uuid, count in uuid_counts.items() if count > 1}
    
    if duplicates:
        error_msg = f"Duplicate UUIDs found in test {isolation_id}: {duplicates}"
        logger.error(error_msg)
        raise E2EAssertionError(error_msg)
    
    logger.info(f"No duplicate data assertion passed for test {isolation_id}")


def soft_assert(condition: bool, message: str, warnings: List[str]) -> None:
    """
    Perform a soft assertion that accumulates warnings instead of failing immediately.
    
    Args:
        condition: Condition to check
        message: Warning message if condition is False
        warnings: List to accumulate warnings
    """
    if not condition:
        warnings.append(message)
        logger.warning(f"Soft assertion failed: {message}")


def assert_soft_warnings(warnings: List[str], max_warnings: int = 5) -> None:
    """
    Assert that accumulated soft warnings don't exceed a threshold.
    
    Args:
        warnings: List of accumulated warnings
        max_warnings: Maximum number of warnings allowed
        
    Raises:
        E2EAssertionError: If too many warnings accumulated
    """
    if len(warnings) > max_warnings:
        error_msg = f"Too many soft assertion warnings ({len(warnings)} > {max_warnings}):\n" + \
                   "\n".join(f"  - {warning}" for warning in warnings)
        logger.error(error_msg)
        raise E2EAssertionError(error_msg)
    
    if warnings:
        logger.info(f"Soft warnings within acceptable range: {len(warnings)}/{max_warnings}")
    else:
        logger.info("No soft assertion warnings") 