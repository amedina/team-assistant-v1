#!/usr/bin/env python3
"""
Team Assistant E2E Test Suite - Main Entry Point

Simple entry point for running the comprehensive End-to-End testing framework
for the Team Assistant data ingestion and retrieval system.

This script provides the command-line interface specified in the framework
requirements with flexible execution options and strict failure reporting.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path for absolute imports (go up two levels from tests/e2e/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the test runner
from tests.e2e.test_runner import main

if __name__ == "__main__":
    """
    Main entry point for E2E testing.
    
    Usage examples:
    
    # Test specific scenario
    python e2e_test.py --scenario github
    
    # Test specific storage targets  
    python e2e_test.py --scenario github --targets vector,database
    python e2e_test.py --scenario drive --targets knowledge_graph
    
    # Test specific components
    python e2e_test.py --scenario web --components models,processors,connectors
    python e2e_test.py --scenario drive_file --components text_processing,retrieval
    
    # Verbosity control
    python e2e_test.py --verbose
    python e2e_test.py --quiet
    
    # Test phase control
    python e2e_test.py --scenario web --phase ingestion
    python e2e_test.py --scenario drive_file --phase retrieval  
    python e2e_test.py --scenario github --phase full  # default
    
    # Failure modes
    python e2e_test.py --fail-fast  # Stop on first failure
    python e2e_test.py --strict-validation  # Enable all validation checks
    """
    asyncio.run(main()) 