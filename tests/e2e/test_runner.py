#!/usr/bin/env python3
"""
E2E Test Runner

Main orchestration script for the comprehensive End-to-End testing framework.
Provides command-line interface with flexible execution options and strict
failure reporting.
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.fixtures import (
    E2ETestResults, setup_test_logging, perform_system_health_check
)
from tests.e2e.test_scenarios import (
    get_scenario, get_all_scenarios, get_scenario_names,
    TestPhase, ComponentType, StorageTarget,
    get_scenarios_for_phase, get_scenarios_for_components, get_scenarios_for_storage_targets
)
from config.configuration import get_system_config

# Import test modules
import pytest

logger = logging.getLogger(__name__)

class E2ETestRunner:
    """Main E2E test runner with comprehensive execution control."""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.test_results = E2ETestResults()
        self.start_time = datetime.now()
        
        # Setup logging
        setup_test_logging(verbose=args.verbose)
        
        # Configuration
        self.strict_validation = args.strict_validation
        self.fail_fast = args.fail_fast
        
        logger.info(f"E2E Test Runner initialized with args: {vars(args)}")
    
    async def run_tests(self) -> bool:
        """
        Run the E2E test suite based on command-line arguments.
        
        Returns:
            True if all tests pass, False otherwise
        """
        try:
            print("🚀 TEAM ASSISTANT E2E TEST SUITE")
            print("=" * 60)
            print(f"📅 Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🎯 Configuration: {self._get_test_configuration_summary()}")
            print("=" * 60)
            
            # Step 1: System health check
            if not await self._perform_initial_health_check():
                if self.fail_fast:
                    return False
            
            # Step 2: Determine test scope
            test_scope = self._determine_test_scope()
            
            # Step 3: Execute tests based on scope
            success = await self._execute_test_scope(test_scope)
            
            # Step 4: Generate final report
            self._generate_final_report()
            
            return success
            
        except Exception as e:
            logger.error(f"Test runner failed: {e}")
            self.test_results.add_error(f"Test runner error: {e}")
            return False
    
    def _get_test_configuration_summary(self) -> str:
        """Get a summary of test configuration."""
        config_items = []
        
        if self.args.scenario:
            config_items.append(f"Scenario: {self.args.scenario}")
        
        if self.args.targets:
            config_items.append(f"Targets: {','.join(self.args.targets)}")
        
        if self.args.components:
            config_items.append(f"Components: {','.join(self.args.components)}")
        
        if self.args.phase:
            config_items.append(f"Phase: {self.args.phase}")
        
        config_items.append(f"Strict: {self.strict_validation}")
        config_items.append(f"FailFast: {self.fail_fast}")
        
        return " | ".join(config_items)
    
    async def _perform_initial_health_check(self) -> bool:
        """Perform initial system health check."""
        print("\n🏥 INITIAL SYSTEM HEALTH CHECK")
        print("-" * 40)
        
        try:
            # Load system configuration
            config = get_system_config()
            
            # Initialize managers for health check
            from data_ingestion.managers.vector_store_manager import VectorStoreManager
            from data_ingestion.managers.database_manager import DatabaseManager
            from data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager
            
            vector_manager = VectorStoreManager(config.pipeline_config.vector_search)
            database_manager = DatabaseManager(config.pipeline_config.database)
            # Use neo4j config if available, otherwise create minimal config
            if hasattr(config.pipeline_config, 'neo4j') and config.pipeline_config.neo4j:
                kg_config = config.pipeline_config.neo4j
            else:
                import os
                kg_config = type('KGConfig', (), {
                    'uri': 'neo4j://nyx.gagan.pro',
                    'user': 'neo4j', 
                    'password': os.getenv('NEO4J_PASSWORD'),
                    'database': 'neo4j'
                })()
            kg_manager = KnowledgeGraphManager(kg_config)
            
            # Initialize managers
            init_results = await asyncio.gather(
                vector_manager.initialize(),
                database_manager.initialize(),
                kg_manager.initialize(),
                return_exceptions=True
            )
            
            # Check initialization results
            vector_init = init_results[0] if not isinstance(init_results[0], Exception) else False
            db_init = init_results[1] if not isinstance(init_results[1], Exception) else False
            kg_init = init_results[2] if not isinstance(init_results[2], Exception) else False
            
            print(f"   📊 Vector Store: {'✅ Ready' if vector_init else '❌ Failed'}")
            print(f"   📊 Database: {'✅ Ready' if db_init else '❌ Failed'}")
            print(f"   📊 Knowledge Graph: {'✅ Ready' if kg_init else '❌ Failed'}")
            
            # Perform health checks
            if vector_init and db_init and kg_init:
                system_health = await perform_system_health_check(
                    vector_manager, database_manager, kg_manager
                )
                
                overall_healthy = system_health.overall_healthy
                print(f"   🎯 Overall System: {'✅ Healthy' if overall_healthy else '❌ Unhealthy'}")
                
                # Cleanup managers
                await asyncio.gather(
                    vector_manager.close(),
                    database_manager.close(),
                    kg_manager.close(),
                    return_exceptions=True
                )
                
                if not overall_healthy and self.strict_validation:
                    self.test_results.add_error("System health check failed")
                    return False
            else:
                print("   ⚠️  Initialization failed - tests may be limited")
                if self.strict_validation:
                    self.test_results.add_error("Manager initialization failed")
                    return False
            
            print("   ✅ Health check completed")
            return True
            
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            self.test_results.add_error(f"Health check error: {e}")
            return not self.strict_validation
    
    def _determine_test_scope(self) -> Dict[str, Any]:
        """Determine which tests to run based on arguments."""
        scope = {
            "scenarios": {},
            "test_modules": [],
            "pytest_args": []
        }
        
        # Determine scenarios
        if self.args.scenario:
            scenario = get_scenario(self.args.scenario)
            scope["scenarios"][self.args.scenario] = scenario
        else:
            scope["scenarios"] = get_all_scenarios()
        
        # Filter by phase
        if self.args.phase:
            phase = TestPhase(self.args.phase)
            scope["scenarios"] = get_scenarios_for_phase(phase)
            
            if phase == TestPhase.INGESTION:
                scope["test_modules"].extend(["test_components.py", "test_storage.py"])
            elif phase == TestPhase.RETRIEVAL:
                scope["test_modules"].extend(["test_storage.py", "test_integration.py"])
            else:  # FULL
                scope["test_modules"].extend(["test_components.py", "test_storage.py", "test_integration.py"])
        else:
            scope["test_modules"] = ["test_components.py", "test_storage.py", "test_integration.py"]
        
        # Filter by components
        if self.args.components:
            components = [ComponentType(c) for c in self.args.components]
            component_modules = {
                ComponentType.MODELS: "test_components.py::TestModels",
                ComponentType.PROCESSORS: "test_components.py::TestTextProcessor",
                ComponentType.CONNECTORS: "test_components.py::TestConnectors",
                ComponentType.TEXT_PROCESSING: "test_components.py::TestTextProcessor",
                ComponentType.STORAGE: "test_storage.py",
                ComponentType.RETRIEVAL: "test_integration.py::TestContextManager"
            }
            
            scope["test_modules"] = []
            for component in components:
                if component in component_modules:
                    scope["test_modules"].append(component_modules[component])
        
        # Filter by storage targets
        if self.args.targets:
            targets = [StorageTarget(t) for t in self.args.targets]
            target_modules = {
                StorageTarget.VECTOR: "test_storage.py::TestVectorStore",
                StorageTarget.DATABASE: "test_storage.py::TestDatabase",
                StorageTarget.KNOWLEDGE_GRAPH: "test_storage.py::TestKnowledgeGraph"
            }
            
            if scope["test_modules"] == ["test_components.py", "test_storage.py", "test_integration.py"]:
                scope["test_modules"] = []
            
            for target in targets:
                if target in target_modules:
                    scope["test_modules"].append(target_modules[target])
        
        # Setup pytest arguments
        scope["pytest_args"] = [
            "-v" if self.args.verbose else "-q",
            "--tb=short" if not self.args.verbose else "--tb=long",
            "--strict-markers",
            "--strict-config"
        ]
        
        if self.fail_fast:
            scope["pytest_args"].append("-x")
        
        return scope
    
    async def _execute_test_scope(self, test_scope: Dict[str, Any]) -> bool:
        """Execute tests based on determined scope."""
        print("\n🧪 EXECUTING TEST SUITE")
        print("-" * 40)
        
        success = True
        
        try:
            # Prepare test files
            test_dir = Path(__file__).parent
            test_files = []
            
            if test_scope["test_modules"]:
                for module in test_scope["test_modules"]:
                    if "::" in module:
                        # Specific test class/method
                        file_part, class_part = module.split("::", 1)
                        test_files.append(str(test_dir / file_part) + "::" + class_part)
                    else:
                        # Entire module
                        test_files.append(str(test_dir / module))
            else:
                # All test files
                test_files = [
                    str(test_dir / "test_components.py"),
                    str(test_dir / "test_storage.py"),
                    str(test_dir / "test_integration.py")
                ]
            
            # Add scenario-specific parameters if needed
            pytest_args = test_scope["pytest_args"] + test_files
            
            # Add quiet flag for integration with our custom reporting
            if not self.args.verbose:
                pytest_args.append("--quiet")
            
            print(f"   🎯 Running pytest with: {' '.join(pytest_args)}")
            
            # Run pytest
            exit_code = pytest.main(pytest_args)
            
            if exit_code == 0:
                print("   ✅ All tests passed")
                success = True
            else:
                print(f"   ❌ Tests failed with exit code: {exit_code}")
                success = False
                self.test_results.add_error(f"Pytest execution failed with code {exit_code}")
            
        except Exception as e:
            print(f"   ❌ Test execution failed: {e}")
            success = False
            self.test_results.add_error(f"Test execution error: {e}")
        
        return success
    
    def _generate_final_report(self):
        """Generate comprehensive final test report."""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        print("\n📊 FINAL TEST REPORT")
        print("=" * 60)
        print(f"⏱️  Total Duration: {total_duration:.2f}s")
        print(f"📅 Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Determine overall success
        overall_success = len(self.test_results.errors) == 0
        
        print(f"\n🎯 OVERALL RESULT: {'✅ SUCCESS' if overall_success else '❌ FAILURE'}")
        
        if self.test_results.errors:
            print(f"\n❌ ERRORS ENCOUNTERED ({len(self.test_results.errors)}):")
            for i, error in enumerate(self.test_results.errors, 1):
                print(f"   {i}. {error}")
        
        # Configuration summary
        print(f"\n⚙️  TEST CONFIGURATION:")
        print(f"   - Scenario: {self.args.scenario or 'All'}")
        print(f"   - Phase: {self.args.phase or 'Full'}")
        print(f"   - Components: {','.join(self.args.components) if self.args.components else 'All'}")
        print(f"   - Storage Targets: {','.join(self.args.targets) if self.args.targets else 'All'}")
        print(f"   - Strict Validation: {self.strict_validation}")
        print(f"   - Fail Fast: {self.fail_fast}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if overall_success:
            print("   ✅ All E2E tests completed successfully!")
            print("   ✅ The Team Assistant data ingestion system is functioning correctly.")
            print("   ✅ All storage layers and components are working as expected.")
        else:
            print("   ❌ Some tests failed or encountered errors.")
            print("   🔍 Review the error messages above for specific issues.")
            print("   🔧 Check system configuration and service health.")
            print("   📋 Consider running individual test modules for debugging.")
        
        print("=" * 60)

def create_argument_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Team Assistant E2E Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner.py --scenario github
  python test_runner.py --scenario drive --targets vector,database
  python test_runner.py --components models,processors --verbose
  python test_runner.py --phase ingestion --fail-fast
  python test_runner.py --strict-validation --verbose
        """
    )
    
    # Scenario selection
    parser.add_argument(
        "--scenario",
        choices=get_scenario_names(),
        help="Test specific scenario"
    )
    
    # Storage targets
    def validate_targets(value):
        targets = value.split(',')
        valid_choices = ["vector", "database", "knowledge_graph"]
        for target in targets:
            if target not in valid_choices:
                raise argparse.ArgumentTypeError(f"invalid choice: '{target}' (choose from {', '.join(valid_choices)})")
        return targets
    
    parser.add_argument(
        "--targets",
        type=validate_targets,
        help="Test specific storage targets (comma-separated)"
    )
    
    # Component selection
    def validate_components(value):
        components = value.split(',')
        valid_choices = ["models", "processors", "connectors", "text_processing", "retrieval", "storage"]
        for component in components:
            if component not in valid_choices:
                raise argparse.ArgumentTypeError(f"invalid choice: '{component}' (choose from {', '.join(valid_choices)})")
        return components
    
    parser.add_argument(
        "--components",
        type=validate_components,
        help="Test specific components (comma-separated)"
    )
    
    # Test phase
    parser.add_argument(
        "--phase",
        choices=["ingestion", "retrieval", "full"],
        default="full",
        help="Test phase to execute"
    )
    
    # Execution control
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed output"
    )
    
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--strict-validation",
        action="store_true",
        help="Enable all validation checks"
    )
    
    return parser

async def main():
    """Main entry point for the E2E test runner."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Handle conflicting flags
    if args.quiet and args.verbose:
        print("Error: --quiet and --verbose are mutually exclusive")
        sys.exit(1)
    
    # Set default verbosity
    if args.quiet:
        args.verbose = False
    
    # Create and run test suite
    runner = E2ETestRunner(args)
    success = await runner.run_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 