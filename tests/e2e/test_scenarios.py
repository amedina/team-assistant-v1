#!/usr/bin/env python3
"""
Test Scenarios for E2E Data Pipeline Testing.

This module defines test scenarios with their configurations, expected outcomes,
and validation criteria for comprehensive E2E testing of the Team Assistant
data ingestion and retrieval system.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class TestPhase(Enum):
    """Test execution phases."""
    INGESTION = "ingestion"
    RETRIEVAL = "retrieval"
    FULL = "full"


@dataclass
class TestScenario:
    """Configuration for a single E2E test scenario."""
    test_id: str
    source_type: str
    source_identifier: str
    target_file: str
    query: str
    expected_keywords: List[str]
    expected_entities: List[str]
    expected_source_pattern: str
    min_chunks_expected: int
    min_vector_similarity: float
    max_response_time_ms: int
    description: str
    ingestion_only: bool = False
    
    @property
    def scenario_name(self) -> str:
        """Get the scenario name from test_id."""
        return self.test_id.split('-')[0].lower()


# Predefined test scenarios as specified in the requirements
TEST_SCENARIOS: Dict[str, TestScenario] = {
    "github": TestScenario(
        test_id="GITHUB-001",
        source_type="github_repo",
        source_identifier="GoogleChromeLabs/ps-analysis-tool",
        target_file="README",
        query="privacy sandbox analysis tool",
        expected_keywords=["privacy", "sandbox", "analysis", "tool", "chrome"],
        expected_entities=["Privacy Sandbox", "Chrome", "analysis", "tool"],
        expected_source_pattern="github:GoogleChromeLabs/ps-analysis-tool",
        min_chunks_expected=3,
        min_vector_similarity=0.2,
        max_response_time_ms=5000,
        description="Enhanced GitHub repository file ingestion and retrieval validation",
        ingestion_only=False
    ),
    
    "drive": TestScenario(
        test_id="DRIVE-002",
        source_type="drive_folder",
        source_identifier="1ptFZLZApmOZw6NWpmxoEGEAKwBaBhIcm",
        target_file="DevRel Assistance Documents",
        query="N/A - ingestion only",
        expected_keywords=["N/A - ingestion only"],
        expected_entities=["N/A - ingestion only"],
        expected_source_pattern="drive:1ptFZLZApmOZw6NWpmxoEGEAKwBaBhIcm",
        min_chunks_expected=5,
        min_vector_similarity=0.0,
        max_response_time_ms=30000,
        description="Google Drive folder ingestion validation (ingestion-only test)",
        ingestion_only=True
    ),
    
    "drive_file": TestScenario(
        test_id="DRIVE-FILE-003",
        source_type="drive_file",
        source_identifier="1YFOl19kCN782a-cJF_1LQHcIppcpKzHhsy_y0rr4Ro4",
        target_file="Individual Drive File",
        query="DevRel guidance assistance development",
        expected_keywords=["devrel", "guidance", "documentation", "assistance", "development"],
        expected_entities=["DevRel", "assistance", "development"],
        expected_source_pattern="drive:1YFOl19kCN782a-cJF_1LQHcIppcpKzHhsy_y0rr4Ro4",
        min_chunks_expected=2,
        min_vector_similarity=0.15,
        max_response_time_ms=6000,
        description="Enhanced individual Google Drive file processing validation",
        ingestion_only=False
    ),
    
    "web": TestScenario(
        test_id="WEB-004",
        source_type="web_source",
        source_identifier="https://docs.python.org/3/tutorial/introduction.html",
        target_file="Python Tutorial Introduction",
        query="python operator calculate powers",
        expected_keywords=["python", "operator", "calculate", "powers"],
        expected_entities=["Python", "operator", "calculate"],
        expected_source_pattern="web:https://docs.python.org/3/tutorial/introduction.html",
        min_chunks_expected=2,
        min_vector_similarity=0.15,
        max_response_time_ms=4000,
        description="Enhanced web page ingestion and retrieval validation",
        ingestion_only=False
    )
}


def get_test_scenario(scenario_name: str) -> Optional[TestScenario]:
    """
    Get test scenario by name.
    
    Args:
        scenario_name: Name of the scenario
        
    Returns:
        TestScenario object or None if not found
    """
    return TEST_SCENARIOS.get(scenario_name.lower())


def get_all_scenarios() -> List[TestScenario]:
    """
    Get all available test scenarios.
    
    Returns:
        List of all TestScenario objects
    """
    return list(TEST_SCENARIOS.values())


def get_ingestion_scenarios() -> List[TestScenario]:
    """
    Get scenarios that include ingestion testing.
    
    Returns:
        List of TestScenario objects that test ingestion
    """
    return list(TEST_SCENARIOS.values())


def get_retrieval_scenarios() -> List[TestScenario]:
    """
    Get scenarios that include retrieval testing.
    
    Returns:
        List of TestScenario objects that test retrieval
    """
    return [scenario for scenario in TEST_SCENARIOS.values() if not scenario.ingestion_only]


def create_data_source_config(scenario: TestScenario) -> Dict[str, Any]:
    """
    Create a data source configuration for testing based on the scenario.
    
    Args:
        scenario: Test scenario to create config for
        
    Returns:
        Data source configuration dictionary
    """
    base_config = {
        "source_id": f"test-{scenario.scenario_name}",
        "source_type": scenario.source_type,
        "access_level": "global",
        "description": scenario.description,
        "enabled": True,
        "config": {}
    }
    
    # Add source-specific configuration
    if scenario.source_type == "github_repo":
        repository_parts = scenario.source_identifier.split("/")
        if len(repository_parts) >= 2:
            base_config["config"] = {
                "repository": scenario.source_identifier,
                "branch": "main",
                "paths": ["README.md"] if "README" in scenario.target_file else [],
                "exclude_patterns": [".git/", "node_modules/"],
                "file_extensions": [".md", ".txt", ".pdf"],
                "access_token": "projects/ps-agent-sandbox/secrets/github-token/versions/latest"
            }
    
    elif scenario.source_type == "drive_folder":
        base_config["config"] = {
            "folder_id": scenario.source_identifier,
            "include_subfolders": True,
            "file_types": ["google_doc", "google_slide", "google_sheet", "pdf", "text"],
            "exclude_patterns": ["temp_*", "draft_*", "archive/"],
            "max_file_size_mb": 50
        }
    
    elif scenario.source_type == "drive_file":
        base_config["config"] = {
            "file_id": scenario.source_identifier,
            "file_types": ["google_doc", "pdf", "text"],
            "max_file_size_mb": 50
        }
    
    elif scenario.source_type == "web_source":
        base_config["config"] = {
            "urls": [scenario.source_identifier],
            "crawl_mode": "single_page",
            "delay_between_requests": 1.0,
            "selectors": {
                "content": "main, .content, article",
                "title": "h1, title"
            },
            "exclude_selectors": ["nav", "footer", ".sidebar"],
            "user_agent": "DevRel-Assistant/1.0 (E2E Test)"
        }
    
    return base_config


class ScenarioValidator:
    """Validator for test scenario results."""
    
    @staticmethod
    def validate_scenario_config(scenario: TestScenario) -> List[str]:
        """
        Validate scenario configuration.
        
        Args:
            scenario: Scenario to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not scenario.test_id:
            errors.append("test_id is required")
        
        if not scenario.source_type:
            errors.append("source_type is required")
        
        if not scenario.source_identifier:
            errors.append("source_identifier is required")
        
        if scenario.min_chunks_expected < 0:
            errors.append("min_chunks_expected must be non-negative")
        
        if not (0.0 <= scenario.min_vector_similarity <= 1.0):
            errors.append("min_vector_similarity must be between 0.0 and 1.0")
        
        if scenario.max_response_time_ms <= 0:
            errors.append("max_response_time_ms must be positive")
        
        return errors
    
    @staticmethod
    def validate_all_scenarios() -> Dict[str, List[str]]:
        """
        Validate all test scenarios.
        
        Returns:
            Dictionary mapping scenario names to validation errors
        """
        validation_results = {}
        for name, scenario in TEST_SCENARIOS.items():
            errors = ScenarioValidator.validate_scenario_config(scenario)
            if errors:
                validation_results[name] = errors
        
        return validation_results 