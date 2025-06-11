"""
Pytest configuration for E2E tests.

This file configures pytest fixtures and settings for the E2E test suite.
"""

import pytest
import logging
from pathlib import Path
import sys

# Add project root to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.fixtures import (
    system_config,
    test_results,
    text_processor,
    setup_test_logging,
    vector_store_manager,
    database_manager,
    knowledge_graph_manager
)

# Configure logging for tests
def pytest_configure(config):
    """Configure pytest with global logging control."""
    
    # Get the verbosity and quiet options from pytest command line
    # Use getvalue() which is the correct method for option values
    verbose_level = config.option.verbose if hasattr(config.option, 'verbose') else 0
    quiet = config.option.quiet if hasattr(config.option, 'quiet') else False
    
    # Debug what we're getting
    print(f"🔍 PYTEST OPTIONS: verbose={verbose_level}, quiet={quiet}")
    
    # Determine global logging level based on pytest flags
    if quiet:
        log_level = logging.CRITICAL  # Only show critical errors
    elif verbose_level >= 2:
        log_level = logging.DEBUG     # Show everything in very verbose mode (-vv)
    elif verbose_level >= 1:
        log_level = logging.INFO      # Show info and above in verbose mode (-v)
    else:
        log_level = logging.WARNING   # Default: only warnings and errors
    
    # Store the desired level globally so we can reapply it later
    import builtins
    builtins._pytest_log_level = log_level
    
    # Configure logging globally - more aggressive approach
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True  # Override any existing configuration
    )
    
    # Set the root logger level (affects all child loggers by default)
    logging.getLogger().setLevel(log_level)
    
    # Ensure all existing handlers respect our level
    for handler in logging.getLogger().handlers:
        handler.setLevel(log_level)
    

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and organize tests."""
    for item in items:
        # Add markers based on test file location
        if "test_components.py" in str(item.fspath):
            item.add_marker(pytest.mark.component)
        elif "test_storage.py" in str(item.fspath):
            item.add_marker(pytest.mark.storage)
        elif "test_integration.py" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "test_scenarios.py" in str(item.fspath):
            item.add_marker(pytest.mark.scenario)

def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--scenario",
        action="store",
        default=None,
        help="Run specific scenario test (github, drive, drive_file, web)"
    )
    parser.addoption(
        "--component",
        action="store",
        default=None,
        help="Run specific component tests (models, processors, connectors, etc.)"
    )
    parser.addoption(
        "--storage-target",
        action="store", 
        default=None,
        help="Run tests for specific storage target (vector, database, knowledge_graph)"
    )

def pytest_runtest_setup(item):
    """Setup for each test run."""
    
    # Reapply logging configuration before each test
    # This is crucial because application code may reconfigure logging during imports
    import builtins
    desired_level = getattr(builtins, '_pytest_log_level', logging.WARNING)
    
    # Aggressively reset all logging
    root_logger = logging.getLogger()
    root_logger.setLevel(desired_level)
    
    # Clear any existing handlers and recreate with our level
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add a console handler with our desired level
    import sys
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(desired_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Set all existing loggers to our level
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        logger.setLevel(desired_level)
    
    # Filter tests based on command line options
    scenario_filter = item.config.getoption("--scenario")
    if scenario_filter and "scenario" in item.keywords:
        if scenario_filter not in item.name.lower():
            pytest.skip(f"Test skipped: not matching scenario filter '{scenario_filter}'")
    
    component_filter = item.config.getoption("--component")
    if component_filter and "component" in item.keywords:
        if component_filter not in item.name.lower():
            pytest.skip(f"Test skipped: not matching component filter '{component_filter}'")
    
    storage_filter = item.config.getoption("--storage-target")
    if storage_filter and "storage" in item.keywords:
        if storage_filter not in item.name.lower():
            pytest.skip(f"Test skipped: not matching storage filter '{storage_filter}'")

@pytest.fixture(scope="function", autouse=True)
def global_logging_control():
    """Auto-applied fixture for global logging control (runs before each test)."""
    
    # Get the desired level from our global storage
    import builtins
    desired_level = getattr(builtins, '_pytest_log_level', logging.WARNING)
    
    # Reapply the logging configuration before each test
    # This ensures any application code that reconfigures logging gets overridden
    logging.basicConfig(
        level=desired_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )
    
    # Set root logger level
    logging.getLogger().setLevel(desired_level)
    
    # Apply this level to ALL existing loggers (including ones created by app code)
    for name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(name)
        logger.setLevel(desired_level)
        
        # Also set all handlers on each logger
        for handler in logger.handlers:
            handler.setLevel(desired_level)

    # Suppress Neo4j notifications and other verbose logging
    logging.getLogger('neo4j.pool').setLevel(logging.WARNING)
    logging.getLogger('neo4j.io').setLevel(logging.WARNING)
    logging.getLogger('neo4j.notifications').setLevel(logging.WARNING)
    logging.getLogger('neo4j').setLevel(logging.WARNING)
    
    # Set all root logger handlers
    for handler in logging.getLogger().handlers:
        handler.setLevel(desired_level)