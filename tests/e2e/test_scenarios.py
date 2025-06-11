"""
E2E Test Scenarios Configuration

This module defines the test scenarios and validation rules for comprehensive 
end-to-end testing of the Team Assistant data ingestion and retrieval system.
"""

from typing import Dict, Any, List
from enum import Enum

class TestPhase(str, Enum):
    """Test execution phases."""
    INGESTION = "ingestion"
    RETRIEVAL = "retrieval"
    FULL = "full"

class ComponentType(str, Enum):
    """Component types for targeted testing."""
    MODELS = "models"
    PROCESSORS = "processors"
    CONNECTORS = "connectors"
    TEXT_PROCESSING = "text_processing"
    RETRIEVAL = "retrieval"
    STORAGE = "storage"

class StorageTarget(str, Enum):
    """Storage targets for testing."""
    VECTOR = "vector"
    DATABASE = "database"
    KNOWLEDGE_GRAPH = "knowledge_graph"

# Predefined test scenarios with enhanced validation
TEST_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "github": {
        "test_id": "GITHUB-001",
        "source_type": "github_repo", 
        "source_identifier": "GoogleChromeLabs/ps-analysis-tool",
        "target_file": "README",
        "query": "privacy sandbox analysis tool",
        "expected_keywords": ["privacy", "sandbox", "analysis", "tool", "chrome"],
        "expected_entities": ["Privacy Sandbox", "Chrome", "analysis", "tool"],
        "expected_source_pattern": "github:GoogleChromeLabs/ps-analysis-tool",
        "min_chunks_expected": 3,
        "min_vector_similarity": 0.2,
        "max_response_time_ms": 5000,
        "description": "Enhanced GitHub repository file ingestion and retrieval validation",
        "ingestion_only": False,
        "text_processing_validation": {
            "min_extracted_text_length": 500,
            "required_chunk_overlap": True,
            "min_entities_extracted": 2,
            "required_metadata_fields": ["file_type", "repository", "branch", "commit_hash"]
        },
        "model_validation": {
            "connector_output_type": "GitHubDocumentModel",
            "processor_output_type": "ProcessedDocumentModel",
            "ingestor_input_type": "ProcessedDocumentModel",
            "retriever_output_type": "RetrievalResultModel"
        },
        "connector_config": {
            "repository": "GoogleChromeLabs/ps-analysis-tool",
            "branch": "main",
            "paths": ["README.md"],
            "exclude_patterns": [".git/", "node_modules/"],
            "file_extensions": [".md", ".txt", ".pdf"]
        }
    },
    "drive": {
        "test_id": "DRIVE-002",
        "source_type": "drive_folder",
        "source_identifier": "1ptFZLZApmOZw6NWpmxoEGEAKwBaBhIcm",
        "target_file": "DevRel Assistance Documents",
        "query": "N/A - ingestion only",
        "expected_keywords": ["N/A - ingestion only"],
        "expected_entities": ["N/A - ingestion only"],
        "expected_source_pattern": "drive:1ptFZLZApmOZw6NWpmxoEGEAKwBaBhIcm",
        "min_chunks_expected": 5,
        "min_vector_similarity": 0.0,
        "max_response_time_ms": 30000,
        "description": "Google Drive folder ingestion validation (ingestion-only test)",
        "ingestion_only": True,
        "text_processing_validation": {
            "min_extracted_text_length": 1000,
            "required_chunk_overlap": True,
            "min_entities_extracted": 3,
            "required_metadata_fields": ["file_type", "drive_id", "folder_path", "last_modified"]
        },
        "model_validation": {
            "connector_output_type": "DriveDocumentModel",
            "processor_output_type": "ProcessedDocumentModel",
            "ingestor_input_type": "ProcessedDocumentModel"
        },
        "connector_config": {
            "folder_id": "1ptFZLZApmOZw6NWpmxoEGEAKwBaBhIcm",
            "include_subfolders": True,
            "file_types": ["google_doc", "google_slide", "google_sheet", "pdf", "text"],
            "exclude_patterns": ["temp_*", "draft_*", "archive/"],
            "max_file_size_mb": 50
        }
    },
    "drive_file": {
        "test_id": "DRIVE-FILE-003",
        "source_type": "drive_file",
        "source_identifier": "1YFOl19kCN782a-cJF_1LQHcIppcpKzHhsy_y0rr4Ro4",
        "target_file": "Individual Drive File",
        "query": "DevRel guidance assistance development",
        "expected_keywords": ["devrel", "guidance", "documentation", "assistance", "development"],
        "expected_entities": ["DevRel", "assistance", "development"],
        "expected_source_pattern": "drive:1YFOl19kCN782a-cJF_1LQHcIppcpKzHhsy_y0rr4Ro4",
        "min_chunks_expected": 2,
        "min_vector_similarity": 0.15,
        "max_response_time_ms": 6000,
        "description": "Enhanced individual Google Drive file processing validation",
        "ingestion_only": False,
        "text_processing_validation": {
            "min_extracted_text_length": 300,
            "required_chunk_overlap": True,
            "min_entities_extracted": 2,
            "required_metadata_fields": ["file_type", "drive_id", "file_name", "last_modified"]
        },
        "model_validation": {
            "connector_output_type": "DriveDocumentModel",
            "processor_output_type": "ProcessedDocumentModel",
            "ingestor_input_type": "ProcessedDocumentModel",
            "retriever_output_type": "RetrievalResultModel"
        },
        "connector_config": {
            "file_id": "1YFOl19kCN782a-cJF_1LQHcIppcpKzHhsy_y0rr4Ro4",
            "file_types": ["google_doc", "pdf", "text"],
            "max_file_size_mb": 50
        }
    },
    "web": {
        "test_id": "WEB-004",
        "source_type": "web_source",
        "source_identifier": "https://docs.python.org/3/tutorial/introduction.html",
        "target_file": "Python Tutorial Introduction",
        "query": "python operator calculate powers",
        "expected_keywords": ["python", "operator", "calculate", "powers"],
        "expected_entities": ["Python", "operator", "calculate"],
        "expected_source_pattern": "web:https://docs.python.org/3/tutorial/introduction.html",
        "min_chunks_expected": 2,
        "min_vector_similarity": 0.15,
        "max_response_time_ms": 4000,
        "description": "Enhanced web page ingestion and retrieval validation",
        "ingestion_only": False,
        "text_processing_validation": {
            "min_extracted_text_length": 400,
            "required_chunk_overlap": True,
            "min_entities_extracted": 1,
            "required_metadata_fields": ["url", "title", "content_type", "scraped_at"]
        },
        "model_validation": {
            "connector_output_type": "WebDocumentModel",
            "processor_output_type": "ProcessedDocumentModel",
            "ingestor_input_type": "ProcessedDocumentModel",
            "retriever_output_type": "RetrievalResultModel"
        },
        "connector_config": {
            "urls": ["https://docs.python.org/3/tutorial/introduction.html"],
            "crawl_mode": "single_page",
            "delay_between_requests": 1.0,
            "selectors": {
                "content": "main .content, article",
                "title": "h1"
            },
            "exclude_selectors": ["nav", "aside", ".page-navigation"],
            "user_agent": "DevRel-Assistant/1.0 (Documentation Reader)"
        }
    }
}

def get_scenario(scenario_name: str) -> Dict[str, Any]:
    """Get a specific test scenario configuration."""
    if scenario_name not in TEST_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}. Available: {list(TEST_SCENARIOS.keys())}")
    return TEST_SCENARIOS[scenario_name]

def get_all_scenarios() -> Dict[str, Dict[str, Any]]:
    """Get all test scenarios."""
    return TEST_SCENARIOS

def get_scenario_names() -> List[str]:
    """Get list of available scenario names."""
    return list(TEST_SCENARIOS.keys())

def validate_scenario_config(scenario: Dict[str, Any]) -> List[str]:
    """
    Validate scenario configuration completeness.
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    required_fields = [
        "test_id", "source_type", "source_identifier", "target_file",
        "query", "expected_keywords", "expected_entities", 
        "expected_source_pattern", "min_chunks_expected", 
        "min_vector_similarity", "max_response_time_ms",
        "description", "ingestion_only", "text_processing_validation",
        "model_validation", "connector_config"
    ]
    
    for field in required_fields:
        if field not in scenario:
            errors.append(f"Missing required field: {field}")
    
    # Validate text processing validation structure
    if "text_processing_validation" in scenario:
        tpv = scenario["text_processing_validation"]
        required_tpv_fields = [
            "min_extracted_text_length", "required_chunk_overlap",
            "min_entities_extracted", "required_metadata_fields"
        ]
        for field in required_tpv_fields:
            if field not in tpv:
                errors.append(f"Missing text_processing_validation field: {field}")
    
    # Validate model validation structure
    if "model_validation" in scenario:
        mv = scenario["model_validation"]
        required_mv_fields = ["connector_output_type", "processor_output_type", "ingestor_input_type"]
        if not scenario.get("ingestion_only", False):
            required_mv_fields.append("retriever_output_type")
        
        for field in required_mv_fields:
            if field not in mv:
                errors.append(f"Missing model_validation field: {field}")
    
    return errors

def get_scenarios_for_phase(phase: TestPhase) -> Dict[str, Dict[str, Any]]:
    """Get scenarios appropriate for a specific test phase."""
    if phase == TestPhase.INGESTION:
        return TEST_SCENARIOS
    elif phase == TestPhase.RETRIEVAL:
        return {k: v for k, v in TEST_SCENARIOS.items() if not v.get("ingestion_only", False)}
    else:  # FULL
        return TEST_SCENARIOS

def get_scenarios_for_components(components: List[ComponentType]) -> Dict[str, Dict[str, Any]]:
    """Get scenarios appropriate for testing specific components."""
    # For component-specific testing, return all scenarios as they all test the specified components
    return TEST_SCENARIOS

def get_scenarios_for_storage_targets(targets: List[StorageTarget]) -> Dict[str, Dict[str, Any]]:
    """Get scenarios appropriate for testing specific storage targets."""
    # All scenarios test all storage targets, so return all
    return TEST_SCENARIOS 