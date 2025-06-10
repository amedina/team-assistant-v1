#!/usr/bin/env python3
"""
Main E2E Test Entry Point.

This script provides a command-line interface for running E2E tests for the
Team Assistant data ingestion and retrieval system.

Usage:
    python tests/e2e/e2e_test.py --scenario github
    python tests/e2e/e2e_test.py --scenario github --targets vector,database
    python tests/e2e/e2e_test.py --verbose
    python tests/e2e/e2e_test.py --scenario web --phase ingestion
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def setup_logging(verbose: bool = False, quiet: bool = False):
    """Set up logging configuration."""
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Suppress verbose logs from external libraries
    if not verbose:
        logging.getLogger('google').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)


def validate_arguments(args):
    """Validate command-line arguments."""
    errors = []
    
    # Validate scenario
    valid_scenarios = ["github", "drive", "drive_file", "web", "all"]
    if args.scenario not in valid_scenarios:
        errors.append(f"Invalid scenario '{args.scenario}'. Valid options: {valid_scenarios}")
    
    # Validate targets
    if args.targets:
        valid_targets = ["vector", "database", "knowledge_graph"]
        target_list = [t.strip() for t in args.targets.split(",")]
        invalid_targets = [t for t in target_list if t not in valid_targets]
        
        if invalid_targets:
            errors.append(f"Invalid targets: {invalid_targets}. Valid options: {valid_targets}")
    
    # Validate phase
    valid_phases = ["ingestion", "retrieval", "full"]
    if args.phase not in valid_phases:
        errors.append(f"Invalid phase '{args.phase}'. Valid options: {valid_phases}")
    
    # Validate phase-scenario compatibility
    if args.phase == "retrieval" and args.scenario == "drive":
        errors.append("Drive folder scenario only supports ingestion testing")
    
    return errors


def build_pytest_args(args):
    """Build pytest arguments based on command-line arguments."""
    pytest_args = []
    
    # Base test files to run
    e2e_dir = project_root / "tests" / "e2e"
    
    if args.phase == "full":
        pytest_args.extend([
            str(e2e_dir / "test_e2e_data_pipeline.py"),
            str(e2e_dir / "test_context_manager.py")
        ])
    elif args.phase == "ingestion":
        pytest_args.append(str(e2e_dir / "test_e2e_data_pipeline.py"))
        # Filter to ingestion-related tests
        pytest_args.extend(["-k", "test_full_pipeline_flow or test_text_processor_integration or test_model_validation"])
    elif args.phase == "retrieval":
        pytest_args.extend([
            str(e2e_dir / "test_e2e_data_pipeline.py"),
            str(e2e_dir / "test_context_manager.py")
        ])
        # Filter to retrieval-related tests
        pytest_args.extend(["-k", "test_full_pipeline_flow or test_complete_context_flow or test_llm_retrieval_context"])
    
    # Add verbosity
    if args.verbose:
        pytest_args.append("-vv")
    elif not args.quiet:
        pytest_args.append("-v")
    
    # Add scenario filtering
    if args.scenario != "all":
        # Combine with existing -k filter if it exists
        scenario_filter = f"[{args.scenario}]"
        existing_k_filters = [pytest_args[i+1] for i, arg in enumerate(pytest_args) if arg == "-k"]
        if existing_k_filters:
            # Replace existing -k filter with combined filter
            k_index = pytest_args.index("-k")
            pytest_args[k_index + 1] = f"({existing_k_filters[0]}) and {scenario_filter}"
        else:
            pytest_args.extend(["-k", scenario_filter])
    
    # Add pytest options for better output
    pytest_args.extend([
        "--tb=short",  # Shorter traceback format
        "--no-header",  # Remove pytest header
        "--disable-warnings"  # Reduce warning noise
    ])
    
    # Add target filtering (this would need custom fixture support)
    if args.targets:
        target_list = [t.strip() for t in args.targets.split(",")]
        print(f"📝 Note: Target filtering for {target_list} requires custom fixture configuration")
        print(f"    The tests will run with all available targets and filter results accordingly")
    
    return pytest_args


def print_test_info(args):
    """Print test execution information."""
    print("🧪 Team Assistant E2E Test Suite")
    print("=" * 50)
    print(f"📋 Scenario: {args.scenario}")
    print(f"🎯 Phase: {args.phase}")
    
    if args.targets:
        print(f"🎪 Targets: {args.targets}")
    else:
        print(f"🎪 Targets: all available")
    
    if args.verbose:
        print(f"📢 Verbosity: verbose")
    elif args.quiet:
        print(f"📢 Verbosity: quiet")
    else:
        print(f"📢 Verbosity: normal")
    
    print()


def check_prerequisites():
    """Check if prerequisites are available."""
    errors = []
    
    # Check if configuration file exists
    config_file = project_root / "config" / "data_sources_config.yaml"
    if not config_file.exists():
        errors.append(f"Configuration file not found: {config_file}")
    
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        errors.append("pytest is not installed. Please run: pip install pytest pytest-asyncio")
    
    # Check if core dependencies are available
    try:
        from config.configuration import get_system_config
    except ImportError as e:
        errors.append(f"Core dependencies not available: {e}")
    
    return errors


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run E2E tests for Team Assistant data pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/e2e/e2e_test.py --scenario github
  python tests/e2e/e2e_test.py --scenario github --targets vector,database
  python tests/e2e/e2e_test.py --scenario drive --phase ingestion
  python tests/e2e/e2e_test.py --verbose
  python tests/e2e/e2e_test.py --quiet
        """
    )
    
    parser.add_argument(
        "--scenario",
        choices=["github", "drive", "drive_file", "web", "all"],
        default="all",
        help="Test scenario to run (default: all)"
    )
    
    parser.add_argument(
        "--targets",
        help="Comma-separated storage targets: vector,database,knowledge_graph"
    )
    
    parser.add_argument(
        "--phase",
        choices=["ingestion", "retrieval", "full"],
        default="full",
        help="Test phase to execute (default: full)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet output (warnings and errors only)"
    )
    
    args = parser.parse_args()
    
    # Set up logging first
    setup_logging(args.verbose, args.quiet)
    
    # Validate arguments
    validation_errors = validate_arguments(args)
    if validation_errors:
        print("❌ Argument validation errors:")
        for error in validation_errors:
            print(f"   - {error}")
        sys.exit(1)
    
    # Check prerequisites
    prerequisite_errors = check_prerequisites()
    if prerequisite_errors:
        print("❌ Prerequisite check failed:")
        for error in prerequisite_errors:
            print(f"   - {error}")
        sys.exit(1)
    
    # Print test information
    print_test_info(args)
    
    # Build pytest arguments
    pytest_args = build_pytest_args(args)
    
    if args.verbose:
        print(f"🔧 Running pytest with args: {' '.join(pytest_args)}")
        print()
    
    # Import and run pytest
    try:
        import pytest
        exit_code = pytest.main(pytest_args)
        
        # Print final status
        print()
        if exit_code == 0:
            print("✅ E2E tests completed successfully!")
        else:
            print("❌ E2E tests completed with failures")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 