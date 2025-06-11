"""
Team Assistant E2E Test Suite

Comprehensive End-to-End testing framework for validating the complete
data ingestion and retrieval pipeline across all storage systems.

This package implements a modular test architecture with strict failure
reporting and comprehensive validation capabilities.
"""

__version__ = "1.0.0"
__author__ = "Team Assistant E2E Test Framework"
__description__ = "Comprehensive E2E testing for Team Assistant data ingestion system"

# Import key components for external access
from .test_scenarios import (
    TEST_SCENARIOS,
    get_scenario,
    get_all_scenarios,
    get_scenario_names,
    TestPhase,
    ComponentType,
    StorageTarget
)

from .fixtures import (
    E2ETestResults,
    validate_chunk_data,
    validate_text_processing,
    validate_retrieval_results,
    validate_model_types,
    generate_test_uuid,
    create_test_document,
    perform_system_health_check
)

__all__ = [
    "TEST_SCENARIOS",
    "get_scenario",
    "get_all_scenarios", 
    "get_scenario_names",
    "TestPhase",
    "ComponentType",
    "StorageTarget",
    "E2ETestResults",
    "validate_chunk_data",
    "validate_text_processing",
    "validate_retrieval_results",
    "validate_model_types",
    "generate_test_uuid",
    "create_test_document",
    "perform_system_health_check"
] 