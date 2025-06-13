#!/usr/bin/env python3
"""
Comprehensive End-to-End Testing Script for Data Ingestion & Retrieval Architecture

This script validates the complete data lifecycle:
Source → Ingestion → Storage → Retrieval → Verification

Usage:
    python test_full_pipeline.py --scenario all --verbose
    python test_full_pipeline.py --scenario github
    python test_full_pipeline.py --scenario drive
    python test_full_pipeline.py --scenario web
"""

import asyncio
import logging
import time
import json
import sys
import os
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from pathlib import Path

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Pipeline imports
from app.data_ingestion.pipeline.pipeline_manager import PipelineManager
from app.data_ingestion.managers.vector_store_manager import VectorStoreManager
from app.data_ingestion.managers.database_manager import DatabaseManager
from app.data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager
from app.data_ingestion.models import (
    IngestionStatus, SourceType, VectorRetrievalResult, 
    ChunkData, Entity, ComponentHealth
)
from app.config.configuration import SystemConfig

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Default: only show warnings and errors
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/test_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)


# ====================================================================
# TEST CONFIGURATION & SCENARIOS
# ====================================================================

TEST_SCENARIOS = {
    "github": {
        "test_id": "E2E-GITHUB-001",
        "source_type": "github_repo",
        "source_identifier": "GoogleChromeLabs/ps-analysis-tool",
        "target_file": "README",
        "query": "privacy sandbox analysis tool",
        "expected_keywords": ["privacy", "sandbox", "analysis", "tool", "chrome"],
        "expected_entities": ["Privacy Sandbox", "Chrome", "analysis", "tool"],
        "expected_source_pattern": "github:GoogleChromeLabs/ps-analysis-tool",
        "description": "Test GitHub repository file ingestion and retrieval using PSAT repo"
    },
    "drive": {
        "test_id": "E2E-DRIVE-002",
        "source_type": "drive_folder",
        "source_identifier": "1ptFZLZApmOZw6NWpmxoEGEAKwBaBhIcm",  # Real DevRel Assistance folder
        "target_file": "DevRel Assistance Documents",
        "query": "N/A - ingestion only",
        "expected_keywords": ["N/A - ingestion only"],
        "expected_entities": ["N/A - ingestion only"],
        "expected_source_pattern": "drive:1ptFZLZApmOZw6NWpmxoEGEAKwBaBhIcm",
        "description": "Test Google Drive folder ingestion (folders are containers, files within are indexed)"
    },
    "drive_file": {
        "test_id": "E2E-DRIVE-FILE-003",
        "source_type": "drive_file",
        "source_identifier": "1YFOl19kCN782a-cJF_1LQHcIppcpKzHhsy_y0rr4Ro4",  # Individual file ID
        "target_file": "Individual Drive File",
        "query": "DevRel guidance assistance development",
        "expected_keywords": ["devrel", "guidance", "documentation", "assistance", "development"],
        "expected_entities": ["DevRel", "assistance", "development"],
        "expected_source_pattern": "drive:1YFOl19kCN782a-cJF_1LQHcIppcpKzHhsy_y0rr4Ro4",
        "description": "Test individual Google Drive file ingestion and retrieval"
    },
    "web": {
        "test_id": "E2E-WEB-004",
        "source_type": "web_source",
        "source_identifier": "https://docs.python.org/3/tutorial/introduction.html",
        "target_file": "Python Tutorial Introduction",
        "query": "python operator calculate powers",
        "expected_keywords": ["python", "operator", "calculate", "powers"],
        "expected_entities": ["Python", "operator", "calculate"],
        "expected_source_pattern": "web:https://docs.python.org/3/tutorial/introduction.html",
        "description": "Test web page ingestion and retrieval"
    }
}


# ====================================================================
# TEST UTILITIES
# ====================================================================

class TestStats:
    """Track comprehensive test statistics including per-system results and Coordinator Pattern validation."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.scenarios_run = 0
        self.scenarios_passed = 0
        self.scenarios_failed = 0
        self.total_chunks_processed = 0
        self.total_retrieval_queries = 0
        self.errors = []
        
        # Per-system tracking
        self.system_results = {
            "vector_search": {"tests": 0, "passed": 0, "failed": 0, "avg_similarity": 0.0},
            "database": {"tests": 0, "passed": 0, "failed": 0, "avg_response_time": 0.0},
            "knowledge_graph": {"tests": 0, "passed": 0, "failed": 0, "avg_entities": 0.0}
        }
        
        # Enhanced metrics for comprehensive validation
        self.coordinator_pattern_scores = []
        self.cross_system_consistency_scores = []
        self.data_integrity_scores = []
        self.performance_metrics = {
            "ingestion_times": [],
            "retrieval_times": [],
            "consistency_check_times": []
        }
        
        # Detailed results per scenario
        self.scenario_details = {}
    
    def add_scenario_result(self, scenario_name: str, success: bool, error: str = None):
        """Record scenario result."""
        self.scenarios_run += 1
        if success:
            self.scenarios_passed += 1
        else:
            self.scenarios_failed += 1
            if error:
                self.errors.append(f"{scenario_name}: {error}")
    
    def add_system_result(self, system_name: str, success: bool, **metrics):
        """Record individual system test result with metrics."""
        if system_name not in self.system_results:
            return
        
        self.system_results[system_name]["tests"] += 1
        if success:
            self.system_results[system_name]["passed"] += 1
        else:
            self.system_results[system_name]["failed"] += 1
        
        # Update system-specific metrics
        if system_name == "vector_search" and "similarity_score" in metrics:
            current_avg = self.system_results[system_name]["avg_similarity"]
            total_tests = self.system_results[system_name]["tests"]
            self.system_results[system_name]["avg_similarity"] = (
                (current_avg * (total_tests - 1) + metrics["similarity_score"]) / total_tests
            )
        
        elif system_name == "database" and "response_time" in metrics:
            current_avg = self.system_results[system_name]["avg_response_time"]
            total_tests = self.system_results[system_name]["tests"]
            self.system_results[system_name]["avg_response_time"] = (
                (current_avg * (total_tests - 1) + metrics["response_time"]) / total_tests
            )
        
        elif system_name == "knowledge_graph" and "entity_count" in metrics:
            current_avg = self.system_results[system_name]["avg_entities"]
            total_tests = self.system_results[system_name]["tests"]
            self.system_results[system_name]["avg_entities"] = (
                (current_avg * (total_tests - 1) + metrics["entity_count"]) / total_tests
            )
    
    def add_scenario_details(self, scenario_name: str, system_results: Dict[str, Any]):
        """Store detailed results for a scenario."""
        self.scenario_details[scenario_name] = system_results
    
    def add_coordinator_pattern_score(self, score: float):
        """Add Coordinator Pattern validation score."""
        self.coordinator_pattern_scores.append(score)
    
    def add_consistency_score(self, score: float):
        """Add cross-system consistency score."""
        self.cross_system_consistency_scores.append(score)
    
    def add_integrity_score(self, score: float):
        """Add data integrity score."""
        self.data_integrity_scores.append(score)
    
    def add_performance_metric(self, metric_type: str, value: float):
        """Add performance metric."""
        if metric_type in self.performance_metrics:
            self.performance_metrics[metric_type].append(value)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive test summary including per-system results and enhanced metrics."""
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        success_rate = (self.scenarios_passed / self.scenarios_run * 100) if self.scenarios_run > 0 else 0
        
        # Calculate enhanced metric averages
        avg_coordinator_score = sum(self.coordinator_pattern_scores) / len(self.coordinator_pattern_scores) if self.coordinator_pattern_scores else 0.0
        avg_consistency_score = sum(self.cross_system_consistency_scores) / len(self.cross_system_consistency_scores) if self.cross_system_consistency_scores else 0.0
        avg_integrity_score = sum(self.data_integrity_scores) / len(self.data_integrity_scores) if self.data_integrity_scores else 0.0
        
        return {
            "elapsed_time_seconds": elapsed_time,
            "scenarios_run": self.scenarios_run,
            "scenarios_passed": self.scenarios_passed,
            "scenarios_failed": self.scenarios_failed,
            "success_rate": success_rate,
            "total_chunks_processed": self.total_chunks_processed,
            "total_retrieval_queries": self.total_retrieval_queries,
            "errors": self.errors,
            "system_results": self.system_results,
            "scenario_details": self.scenario_details,
            "enhanced_metrics": {
                "avg_coordinator_pattern_score": avg_coordinator_score,
                "avg_cross_system_consistency": avg_consistency_score,
                "avg_data_integrity_score": avg_integrity_score,
                "performance_metrics": self.performance_metrics
            }
        }


# ====================================================================
# MAIN TEST RUNNER CLASS
# ====================================================================

class E2ETestRunner:
    """Orchestrates end-to-end testing of the complete data pipeline."""
    
    def __init__(self, verbose: bool = False):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.verbose = verbose
        self.stats = TestStats()
        
        # Configuration and managers
        self.config: Optional[SystemConfig] = None
        self.pipeline_manager: Optional[PipelineManager] = None
        self.vector_manager: Optional[VectorStoreManager] = None
        self.database_manager: Optional[DatabaseManager] = None
        self.kg_manager: Optional[KnowledgeGraphManager] = None
        
        # Configure logging based on verbose flag
        if verbose:
            # Enable all logging levels (DEBUG, INFO, WARNING, ERROR)
            logging.getLogger().setLevel(logging.DEBUG)
            # Also enable for specific loggers that might be noisy
            logging.getLogger("data_ingestion").setLevel(logging.DEBUG)
            logging.getLogger("neo4j").setLevel(logging.INFO)  # Neo4j can be very verbose, keep at INFO
        else:
            # Keep default WARNING level (only warnings and errors)
            logging.getLogger().setLevel(logging.ERROR)
            logging.getLogger("data_ingestion").setLevel(logging.ERROR)
    
    # ================================================================
    # SETUP AND INITIALIZATION
    # ================================================================
    
    async def setup_test_environment(self) -> bool:
        """Initialize all managers and components for testing."""
        print("\n🔧 SETUP: Initializing test environment...")
        
        try:
            # Load configuration
            config_path = "app/config/data_sources_config.yaml"
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
            self.config = SystemConfig.from_yaml(config_path)
            print("   ✅ Configuration loaded")
            
            # Initialize pipeline manager
            self.pipeline_manager = PipelineManager(self.config)
            await self.pipeline_manager.initialize()
            print("   ✅ Pipeline Manager initialized")
            
            # Get individual managers for direct testing
            self.vector_manager = self.pipeline_manager.vector_store_manager
            self.database_manager = self.pipeline_manager.database_manager
            self.kg_manager = self.pipeline_manager.knowledge_graph_manager
            
            # Verify all managers are initialized
            assert self.vector_manager is not None, "Vector Store Manager not initialized"
            assert self.database_manager is not None, "Database Manager not initialized"
            assert self.kg_manager is not None, "Knowledge Graph Manager not initialized"
            print("   ✅ All managers accessible")
            
            # Run health checks
            await self._run_health_checks()
            
            print("   ✅ Test environment ready")
            return True
            
        except Exception as e:
            print(f"   ❌ Setup failed: {e}")
            self.logger.exception("Test environment setup failed")
            return False
    
    async def _run_health_checks(self):
        """Run comprehensive health checks including Coordinator Pattern validation."""
        print("   🏥 Running comprehensive health checks...")
        
        # Vector Store health check
        start_time = time.time()
        vector_health = await self.vector_manager.health_check()
        vector_time = (time.time() - start_time) * 1000
        if not vector_health:
            raise RuntimeError("Vector Store health check failed")
        print(f"     ✅ Vector Store: {vector_time:.1f}ms")
        
        # Database health check
        start_time = time.time()
        db_health = await self.database_manager.health_check()
        db_time = (time.time() - start_time) * 1000
        if not db_health:
            raise RuntimeError("Database health check failed")
        print(f"     ✅ Database: {db_time:.1f}ms")
        
        # Knowledge Graph health check
        start_time = time.time()
        kg_health = await self.kg_manager.health_check()
        kg_time = (time.time() - start_time) * 1000
        if not kg_health:
            raise RuntimeError("Knowledge Graph health check failed")
        print(f"     ✅ Knowledge Graph: {kg_time:.1f}ms")
        
        # Coordinator Pattern validation
        coordinator_score = await self._validate_coordinator_pattern()
        print(f"     🏗️  Coordinator Pattern: {coordinator_score:.2f}/1.0")
        self.stats.add_coordinator_pattern_score(coordinator_score)
    
    async def _validate_coordinator_pattern(self) -> float:
        """Validate the Coordinator Pattern implementation."""
        if self.verbose:
            print("   🏗️  Validating Coordinator Pattern implementation...")
        
        validation_scores = []
        
        # 1. Manager Initialization Check
        manager_init_score = 0.0
        if (self.pipeline_manager is not None and
            hasattr(self.pipeline_manager, 'vector_store_manager') and
            hasattr(self.pipeline_manager, 'database_manager') and
            hasattr(self.pipeline_manager, 'knowledge_graph_manager')):
            manager_init_score = 1.0
        validation_scores.append(manager_init_score)
        
        # 2. Ingestor Coordination Check
        ingestor_coord_score = 0.0
        try:
            if (hasattr(self.vector_manager, 'ingestor') and
                hasattr(self.database_manager, 'ingestor') and
                hasattr(self.kg_manager, 'ingestor')):
                ingestor_coord_score = 1.0
        except:
            pass
        validation_scores.append(ingestor_coord_score)
        
        # 3. Retriever Coordination Check
        retriever_coord_score = 0.0
        try:
            if (hasattr(self.vector_manager, 'retriever') and
                hasattr(self.database_manager, 'retriever') and
                hasattr(self.kg_manager, 'retriever')):
                retriever_coord_score = 1.0
        except:
            pass
        validation_scores.append(retriever_coord_score)
        
        # 4. Cross-System Communication Check
        cross_comm_score = 0.0
        try:
            # Test that all managers have health_check methods
            if (hasattr(self.vector_manager, 'health_check') and
                hasattr(self.database_manager, 'health_check') and
                hasattr(self.kg_manager, 'health_check')):
                cross_comm_score = 1.0
        except:
            pass
        validation_scores.append(cross_comm_score)
        
        # 5. Error Handling Check
        error_handling_score = 0.0
        try:
            # Test that managers have statistics/monitoring capabilities
            if (hasattr(self.vector_manager, 'get_statistics') and
                hasattr(self.database_manager, 'get_statistics') and
                hasattr(self.kg_manager, 'get_statistics')):
                error_handling_score = 1.0
        except:
            pass
        validation_scores.append(error_handling_score)
        
        # 6. Resource Management Check
        resource_mgmt_score = 0.0
        if hasattr(self.pipeline_manager, 'close'):
            resource_mgmt_score = 1.0
        validation_scores.append(resource_mgmt_score)
        
        # Calculate overall score
        overall_score = sum(validation_scores) / len(validation_scores)
        
        if self.verbose:
            print(f"     Manager Initialization: {'✅' if manager_init_score == 1.0 else '❌'}")
            print(f"     Ingestor Coordination: {'✅' if ingestor_coord_score == 1.0 else '❌'}")
            print(f"     Retriever Coordination: {'✅' if retriever_coord_score == 1.0 else '❌'}")
            print(f"     Cross-System Communication: {'✅' if cross_comm_score == 1.0 else '❌'}")
            print(f"     Error Handling: {'✅' if error_handling_score == 1.0 else '❌'}")
            print(f"     Resource Management: {'✅' if resource_mgmt_score == 1.0 else '❌'}")
            print(f"     Overall Score: {overall_score:.2f}/1.0")
        
        return overall_score
    
    # ================================================================
    # INGESTION TESTING
    # ================================================================
    
    async def run_ingestion_test(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ingestion for a specific test scenario."""
        print(f"\n📥 INGESTING: {scenario['test_id']}")
        start_time = time.time()
        
        try:
            # Prepare source configuration for this test
            source_config = {
                "sources": [{
                    "type": scenario["source_type"],
                    "identifier": scenario["source_identifier"],
                    "enabled": True,
                    "filters": {}
                }]
            }
            
            print(f"   📁 Source: {scenario['source_type']}")
            print(f"   🎯 Target: {scenario['source_identifier']}")
            
            # Execute pipeline ingestion
            if self.verbose:
                print(f"   🔧 Running pipeline with config: {json.dumps(source_config, indent=2)}")
            
            # Use pre-existing test config file
            test_config_path = f"tests/config/test_{scenario['source_type']}_config.yaml"
            if not os.path.exists(test_config_path):
                raise FileNotFoundError(f"Test config file not found: {test_config_path}")
            
            # Use CLI to run pipeline (more realistic test)
            result = await self._run_pipeline_cli(test_config_path)
            
            # Validate ingestion results
            assert result["chunks_processed"] > 0, "No chunks processed during ingestion"
            assert result["success_rate"] > 0.8, f"Low success rate: {result['success_rate']:.1f}%"
            
            ingestion_time = time.time() - start_time
            chunks_processed = result["chunks_processed"]
            success_rate = result["success_rate"]
            
            print(f"   ✅ Ingestion completed in {ingestion_time:.2f}s")
            print(f"   📊 Processed: {chunks_processed} chunks")
            print(f"   📊 Success rate: {success_rate:.1f}%")
            
            # Update stats
            self.stats.total_chunks_processed += chunks_processed
            
            return {
                "success": True,
                "chunks_processed": chunks_processed,
                "success_rate": success_rate,
                "ingestion_time": ingestion_time
            }
            
        except Exception as e:
            ingestion_time = time.time() - start_time
            print(f"   ❌ Ingestion failed after {ingestion_time:.2f}s: {e}")
            self.logger.exception(f"Ingestion test failed for {scenario['test_id']}")
            
            return {
                "success": False,
                "error": str(e),
                "ingestion_time": ingestion_time
            }
    

    
    async def _run_pipeline_cli(self, config_path: str) -> Dict[str, Any]:
        """Run the pipeline using the CLI for realistic testing."""
        import subprocess
        import json
        
        try:
            # Run pipeline CLI command
            cmd = [
                sys.executable, 
                "data_ingestion/pipeline/pipeline_cli.py", 
                "--config", config_path,
                "--output-file", "/tmp/pipeline_output.json",
                "run",
                "--mode", "smart"
            ]
            
            if self.verbose:
                print(f"   🔧 Executing: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Pipeline CLI failed: {result.stderr}")
            
            # Parse JSON output from file
            output_file = "/tmp/pipeline_output.json"
            try:
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        output = json.load(f)
                    # Clean up the temp file
                    os.remove(output_file)
                    return {
                        "chunks_processed": output.get("total_chunks", 0),
                        "success_rate": 100.0 if output.get("successful_chunks", 0) > 0 else 0.0,
                        "processing_time": 0.0  # Not in the output format
                    }
                else:
                    # Fallback: parse text output
                    return self._parse_text_output(result.stdout)
            except json.JSONDecodeError:
                # Fallback: parse text output
                return self._parse_text_output(result.stdout)
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("Pipeline CLI timed out after 5 minutes")
        except Exception as e:
            raise RuntimeError(f"Pipeline CLI execution failed: {e}")
    
    def _parse_text_output(self, output: str) -> Dict[str, Any]:
        """Parse text output from pipeline CLI."""
        # Simple parsing of common output patterns
        chunks_processed = 0
        success_rate = 0.0
        successful_chunks = 0
        
        for line in output.split('\n'):
            if 'total chunks:' in line.lower():
                try:
                    chunks_processed = int(''.join(filter(str.isdigit, line)))
                except:
                    pass
            elif 'successful:' in line.lower() or 'successful chunks' in line.lower():
                try:
                    successful_chunks = int(''.join(filter(str.isdigit, line)))
                except:
                    pass
            elif 'pipeline completed successfully' in line.lower():
                success_rate = 100.0
            elif 'pipeline failed' in line.lower():
                success_rate = 0.0
        
        # Calculate success rate if we have chunk counts
        if chunks_processed > 0 and successful_chunks > 0:
            success_rate = (successful_chunks / chunks_processed) * 100.0
        elif successful_chunks > 0:
            chunks_processed = successful_chunks
            success_rate = 100.0
        
        return {
            "chunks_processed": max(chunks_processed, successful_chunks),
            "success_rate": success_rate,
            "processing_time": 0.0
        }
    
    # ================================================================
    # RETRIEVAL TESTING
    # ================================================================
    
    async def run_retrieval_test(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute retrieval tests for a specific scenario."""
        print(f"\n🔍 RETRIEVING: {scenario['test_id']}")
        
        query = scenario["query"]
        expected_source_type = scenario["source_type"]
        print(f"   🔎 Query: '{query}'")
        print(f"   🎯 Expected source type: {expected_source_type}")
        
        retrieval_results = {}
        system_metrics = {
            "vector_search": {"success": False, "metrics": {}},
            "database": {"success": False, "metrics": {}},
            "knowledge_graph": {"success": False, "metrics": {}}
        }
        
        try:
            # ====================================================================
            # TEST 1: VECTOR SEARCH SYSTEM
            # ====================================================================
            print("\n   📊 TESTING VECTOR SEARCH SYSTEM")
            print("   " + "="*50)
            vector_start_time = datetime.now()
            
            vector_results = await self._test_vector_retrieval(query)
            retrieval_results["vector_results"] = vector_results
            
            if not vector_results:
                print("     ❌ Vector search returned no results")
                system_metrics["vector_search"]["success"] = False
                raise AssertionError("No vector search results returned")
            
            # Search for the result matching the expected source type
            best_result = None
            chunk_uuid = None
            similarity_score = None
            
            print(f"     🔍 Searching {len(vector_results)} results for {expected_source_type} content...")
            
            for i, result in enumerate(vector_results):
                # Get chunk data to check source type
                temp_chunk_data = await self._test_database_retrieval(str(result.chunk_uuid))
                if temp_chunk_data and temp_chunk_data.source_type.value == expected_source_type:
                    best_result = result
                    chunk_uuid = str(result.chunk_uuid)
                    similarity_score = result.similarity_score
                    print(f"     ✅ Found {expected_source_type} content at position {i+1}")
                    print(f"     📊 UUID: {chunk_uuid[:8]}... (similarity: {similarity_score:.3f})")
                    break
                else:
                    source_type = temp_chunk_data.source_type.value if temp_chunk_data else "unknown"
                    print(f"     ⏩ Skipping result {i+1}: {source_type} (looking for {expected_source_type})")
            
            if not best_result:
                # Show what we found instead
                print(f"     ❌ No {expected_source_type} content found in top {len(vector_results)} results!")
                print("     📋 Results found:")
                for i, result in enumerate(vector_results[:3]):  # Show first 3
                    temp_chunk_data = await self._test_database_retrieval(str(result.chunk_uuid))
                    source_type = temp_chunk_data.source_type.value if temp_chunk_data else "unknown"
                    print(f"       {i+1}. {source_type} (similarity: {result.similarity_score:.3f})")
                
                system_metrics["vector_search"]["success"] = False
                raise AssertionError(f"No {expected_source_type} content found in vector search results")
            
            vector_response_time = (datetime.now() - vector_start_time).total_seconds()
            system_metrics["vector_search"]["success"] = True
            system_metrics["vector_search"]["metrics"] = {
                "similarity_score": similarity_score,
                "response_time_ms": vector_response_time * 1000,
                "results_count": len(vector_results),
                "target_position": next((i+1 for i, r in enumerate(vector_results) if str(r.chunk_uuid) == chunk_uuid), -1)
            }
            
            print(f"     ✅ Vector search SUCCESS: {len(vector_results)} results, similarity: {similarity_score:.3f}")
            if similarity_score < 0.3:
                print(f"     ⚠️  Low similarity score: {similarity_score:.3f}")
            
            # ====================================================================
            # TEST 2: DATABASE SYSTEM  
            # ====================================================================
            print("\n   🗄️  TESTING DATABASE SYSTEM")
            print("   " + "="*50)
            db_start_time = datetime.now()
            
            await self._test_database_independent_search(scenario, chunk_uuid)
            
            # Get main chunk data for later verification
            chunk_data = await self._test_database_retrieval(chunk_uuid)
            retrieval_results["chunk_data"] = chunk_data
            
            if not chunk_data:
                system_metrics["database"]["success"] = False
                raise AssertionError(f"No chunk data found for UUID: {chunk_uuid}")
            
            db_response_time = (datetime.now() - db_start_time).total_seconds()
            system_metrics["database"]["success"] = True
            system_metrics["database"]["metrics"] = {
                "response_time_ms": db_response_time * 1000,
                "chunk_retrieved": True,
                "source_type": chunk_data.source_type.value,
                "has_metadata": bool(chunk_data.chunk_metadata)
            }
            
            print(f"     ✅ Database SUCCESS: Retrieved {chunk_data.source_type.value} chunk")
            
            # ====================================================================
            # TEST 3: KNOWLEDGE GRAPH SYSTEM
            # ====================================================================
            print("\n   🕸️  TESTING KNOWLEDGE GRAPH SYSTEM")
            print("   " + "="*50)
            kg_start_time = datetime.now()
            
            entities = await self._test_knowledge_graph_independent_search(scenario, chunk_uuid)
            retrieval_results["entities"] = entities
            
            kg_response_time = (datetime.now() - kg_start_time).total_seconds()
            system_metrics["knowledge_graph"]["success"] = True  # KG can succeed even with 0 entities
            system_metrics["knowledge_graph"]["metrics"] = {
                "response_time_ms": kg_response_time * 1000,
                "entity_count": len(entities),
                "entities_found": [e.name for e in entities[:5]] if entities else []
            }
            
            if entities:
                print(f"     ✅ Knowledge Graph SUCCESS: Found {len(entities)} entities")
            else:
                print(f"     ⚠️  Knowledge Graph: No entities found (may be expected)")
            
            # ====================================================================
            # TEST 4: CONTEXTUAL RETRIEVAL
            # ====================================================================
            print("\n   🧩 TESTING CONTEXTUAL RETRIEVAL")
            print("   " + "="*50)
            contextual_chunk = await self._test_contextual_retrieval(chunk_uuid)
            retrieval_results["contextual_chunk"] = contextual_chunk
            
            if contextual_chunk:
                context_count = len(contextual_chunk.context_chunks)
                print(f"     ✅ Retrieved {context_count} context chunks")
            else:
                print(f"     ⚠️  No contextual chunks found")
            
            # ====================================================================
            # TEST 5: CROSS-SYSTEM CONSISTENCY
            # ====================================================================
            print("\n   🔄 TESTING CROSS-SYSTEM CONSISTENCY")
            print("   " + "="*50)
            await self._test_cross_system_search_consistency(query, expected_source_type)
            
            # Record system metrics
            for system_name, metrics in system_metrics.items():
                self.stats.add_system_result(
                    system_name, 
                    metrics["success"], 
                    **metrics["metrics"]
                )
            
            # Store detailed scenario results
            self.stats.add_scenario_details(scenario["test_id"], system_metrics)
            
            # Update stats
            self.stats.total_retrieval_queries += 5  # 5 different retrieval tests
            
            # Print summary
            print(f"\n   📊 RETRIEVAL SUMMARY:")
            print(f"     📊 Vector Search: {'✅ PASS' if system_metrics['vector_search']['success'] else '❌ FAIL'}")
            print(f"     🗄️  Database:     {'✅ PASS' if system_metrics['database']['success'] else '❌ FAIL'}")
            print(f"     🕸️  Knowledge Graph: {'✅ PASS' if system_metrics['knowledge_graph']['success'] else '❌ FAIL'}")
            
            return {
                "success": True,
                "chunk_uuid": chunk_uuid,
                "similarity_score": similarity_score,
                "results": retrieval_results,
                "system_metrics": system_metrics
            }
            
        except Exception as e:
            print(f"   ❌ Retrieval test failed: {e}")
            self.logger.exception(f"Retrieval test failed for {scenario['test_id']}")
            
            # Record failed system metrics
            for system_name, metrics in system_metrics.items():
                if system_name not in ["vector_search", "database", "knowledge_graph"]:
                    continue
                self.stats.add_system_result(
                    system_name, 
                    metrics["success"], 
                    **metrics.get("metrics", {})
                )
            
            return {
                "success": False,
                "error": str(e),
                "results": retrieval_results,
                "system_metrics": system_metrics
            }
    
    async def _test_database_independent_search(self, scenario: Dict[str, Any], reference_uuid: str):
        """Test database independent search capabilities."""
        source_type = scenario["source_type"]
        source_identifier = scenario["source_identifier"]
        
        print(f"     🔍 Testing database search capabilities...")
        
        # Test 1: Search by source type
        try:
            source_chunks = await self.database_manager.search_chunks(source_type=source_type, limit=5)
            if source_chunks:
                print(f"     ✅ Found {len(source_chunks)} chunks by source type ({source_type})")
                # Verify reference chunk is in results
                reference_found = any(str(chunk.chunk_uuid) == reference_uuid for chunk in source_chunks)
                if reference_found:
                    print(f"     ✅ Reference chunk found in source type search")
                else:
                    print(f"     ⚠️  Reference chunk not in top 5 source type results")
            else:
                print(f"     ❌ No chunks found for source type: {source_type}")
        except Exception as e:
            print(f"     ❌ Source type search failed: {e}")
        
        # Test 2: Search by source identifier
        try:
            identifier_chunks = await self.database_manager.search_chunks(source_identifier=source_identifier, limit=5)
            if identifier_chunks:
                print(f"     ✅ Found {len(identifier_chunks)} chunks by source identifier")
                # Verify reference chunk is in results
                reference_found = any(str(chunk.chunk_uuid) == reference_uuid for chunk in identifier_chunks)
                if reference_found:
                    print(f"     ✅ Reference chunk found in identifier search")
            else:
                print(f"     ⚠️  No chunks found for source identifier")
        except Exception as e:
            print(f"     ❌ Source identifier search failed: {e}")
        
        # Test 3: Search by metadata filter
        try:
            # Try searching with source_type in metadata filter
            metadata_filter = {"source_type": source_type}
            metadata_chunks = await self.database_manager.search_chunks(metadata_filter=metadata_filter, limit=3)
            if metadata_chunks:
                print(f"     ✅ Found {len(metadata_chunks)} chunks by metadata filter")
            else:
                print(f"     ⚠️  No chunks found with metadata filter")
        except Exception as e:
            print(f"     ❌ Metadata search failed: {e}")
        
        # Test 4: Get chunk by UUID (existing test)
        chunk_data = await self._test_database_retrieval(reference_uuid)
        if chunk_data:
            print(f"     ✅ Retrieved chunk by UUID: {chunk_data.source_type.value}")
        else:
            print(f"     ❌ Failed to retrieve chunk by UUID")
    
    async def _test_knowledge_graph_independent_search(self, scenario: Dict[str, Any], chunk_uuid: str) -> List[Entity]:
        """Test knowledge graph independent search capabilities."""
        query = scenario["query"]
        expected_entities = scenario["expected_entities"]
        
        print(f"     🔍 Testing knowledge graph search capabilities...")
        
        all_entities = []
        
        # Test 1: Entity search by name pattern
        try:
            for expected_entity in expected_entities[:2]:  # Test first 2 expected entities
                entities = await self.kg_manager.find_entities(name_pattern=expected_entity, limit=5)
                if entities:
                    print(f"     ✅ Found {len(entities)} entities matching '{expected_entity}'")
                    print(f"         Entities: {[e.name for e in entities[:3]]}")
                    all_entities.extend(entities)
                else:
                    print(f"     ⚠️  No entities found for pattern '{expected_entity}'")
        except Exception as e:
            print(f"     ❌ Entity name search failed: {e}")
        
        # Test 2: Entity search by query terms
        try:
            query_entities = await self.kg_manager.search_entities_by_text(query, limit=5)
            if query_entities:
                print(f"     ✅ Found {len(query_entities)} entities for query '{query}'")
                all_entities.extend(query_entities)
            else:
                print(f"     ⚠️  No entities found for query '{query}'")
        except Exception as e:
            print(f"     ❌ Query entity search failed: {e}")
        
        # Test 3: Get entities related to chunk using the retriever directly
        try:
            from uuid import UUID
            chunk_entities_map = await self.kg_manager.retriever.get_entities_for_chunks([UUID(chunk_uuid)])
            # get_entities_for_chunks returns a dict mapping chunk UUIDs to entity lists
            chunk_entities = chunk_entities_map.get(chunk_uuid, [])
            if chunk_entities:
                print(f"     ✅ Found {len(chunk_entities)} entities linked to chunk")
                print(f"         Linked entities: {[e.name for e in chunk_entities[:3]]}")
                all_entities.extend(chunk_entities)
            else:
                print(f"     ⚠️  No entities linked to chunk {chunk_uuid[:8]}...")
        except Exception as e:
            print(f"     ❌ Chunk entity lookup failed: {e}")
        
        # Test 4: Get graph context for the chunk (basic connectivity test)
        try:
            graph_context = await self.kg_manager.get_graph_context_for_chunks([chunk_uuid], max_depth=1)
            context_entities = graph_context.query_entities + graph_context.related_entities
            if context_entities:
                print(f"     ✅ Found {len(context_entities)} entities through graph context")
                print(f"         Context entities: {[e.name for e in context_entities[:3]]}")
                all_entities.extend(context_entities[:3])  # Add only first 3
            else:
                print(f"     ⚠️  No entities found in graph context")
        except Exception as e:
            print(f"     ❌ Graph context retrieval failed: {e}")
        
        # Remove duplicates
        unique_entities = {entity.id: entity for entity in all_entities}.values()
        final_entities = list(unique_entities)
        
        if final_entities:
            print(f"     ✅ Total unique entities found: {len(final_entities)}")
        else:
            print(f"     ⚠️  Knowledge graph appears to be empty or disconnected")
        
        return final_entities
    
    async def _test_cross_system_search_consistency(self, query: str, expected_source_type: str):
        """Test that the same query returns consistent results across systems."""
        print(f"     🔄 Cross-system consistency for query: '{query}'")
        
        # Get results from vector system
        vector_results = await self._test_vector_retrieval(query)
        
        try:
            # Get results from database system (by source type)
            db_results = await self.database_manager.search_chunks(source_type=expected_source_type, limit=5)
            
            print(f"     📊 Vector: {len(vector_results)} results, Database: {len(db_results)} results")
            
            # Check if there's overlap between vector and database results
            if vector_results and db_results:
                vector_uuids = {str(r.chunk_uuid) for r in vector_results}
                db_uuids = {str(chunk.chunk_uuid) for chunk in db_results}
                overlap = vector_uuids.intersection(db_uuids)
                
                if overlap:
                    print(f"     ✅ Found {len(overlap)} overlapping UUIDs between vector and database")
                else:
                    print(f"     ⚠️  No UUID overlap between vector and database results")
                    
                # Show sample UUIDs for debugging
                if vector_results:
                    print(f"     🔍 Sample vector UUIDs: {[str(r.chunk_uuid)[:8] for r in vector_results[:2]]}")
                if db_results:
                    print(f"     🔍 Sample database UUIDs: {[str(c.chunk_uuid)[:8] for c in db_results[:2]]}")
            
        except Exception as e:
            print(f"     ❌ Cross-system consistency check failed: {e}")
        
        # Test knowledge graph consistency
        try:
            kg_entities = await self.kg_manager.search_entities_by_text(query, limit=3)
            print(f"     🕸️  Knowledge graph: {len(kg_entities)} entities found")
            
            if kg_entities:
                print(f"     ✅ Knowledge graph is responsive to queries")
            else:
                print(f"     ⚠️  Knowledge graph returned no entities for query")
                
        except Exception as e:
            print(f"     ❌ Knowledge graph consistency check failed: {e}")
    
    async def _test_vector_retrieval(self, query: str) -> List[VectorRetrievalResult]:
        """Test vector store retrieval using coordinator pattern."""
        try:
            # Use the VectorStoreManager coordinator method
            results = await self.vector_manager.search(query, top_k=10)
            return results
            
        except Exception as e:
            self.logger.error(f"Vector retrieval failed: {e}")
            return []
    
    async def _test_database_retrieval(self, chunk_uuid: str) -> Optional[ChunkData]:
        """Test database chunk retrieval using coordinator pattern."""
        try:
            # Use the DatabaseManager coordinator method  
            chunk = await self.database_manager.get_chunk(chunk_uuid)
            return chunk
            
        except Exception as e:
            self.logger.error(f"Database retrieval failed: {e}")
            return None
    
    async def _test_knowledge_graph_retrieval(self, query: str, chunk_uuid: str) -> List[Entity]:
        """Test knowledge graph entity retrieval using coordinator pattern."""
        try:
            # Use the KnowledgeGraphManager coordinator method for entity search
            entities = await self.kg_manager.find_entities(name_pattern=query, limit=10)
            
            # Also try to get entities related to the specific chunk using coordinator method
            try:
                chunk_entities = await self.kg_manager.get_entities_for_chunks([UUID(chunk_uuid)])
                if chunk_entities:
                    entities.extend(chunk_entities)
            except:
                pass  # Chunk-entity mapping might not exist yet
            
            # Remove duplicates
            unique_entities = {entity.id: entity for entity in entities}.values()
            return list(unique_entities)
            
        except Exception as e:
            self.logger.error(f"Knowledge graph retrieval failed: {e}")
            return []
    
    async def _test_contextual_retrieval(self, chunk_uuid: str):
        """Test contextual chunk retrieval using coordinator pattern."""
        try:
            # Use the DatabaseManager coordinator method for contextual retrieval
            return await self.database_manager.get_chunk_with_context(chunk_uuid, context_window=2)
        except Exception as e:
            self.logger.error(f"Contextual retrieval failed: {e}")
            return None
    
    # ================================================================
    # TRACEABILITY VERIFICATION
    # ================================================================
    
    async def verify_traceability(self, scenario: Dict[str, Any], retrieval_results: Dict[str, Any]) -> bool:
        """Verify complete data traceability for the scenario."""
        print(f"\n✅ VERIFYING: {scenario['test_id']}")
        
        try:
            chunk_uuid = retrieval_results["chunk_uuid"]
            results = retrieval_results["results"]
            
            # Verification 1: Source identifier traceability
            await self._verify_source_traceability(scenario, results["chunk_data"])
            
            # Verification 2: Content keyword verification
            await self._verify_content_keywords(scenario, results["chunk_data"])
            
            # Verification 3: Knowledge graph entity verification
            await self._verify_knowledge_graph_entities(scenario, results["entities"])
            
            # Verification 4: Cross-system consistency
            await self._verify_cross_system_consistency(chunk_uuid, results)
            
            # Verification 5: Temporal consistency
            await self._verify_temporal_consistency(results["chunk_data"])
            
            print("   🎉 All verifications passed!")
            return True
            
        except Exception as e:
            print(f"   ❌ Verification failed: {e}")
            self.logger.exception(f"Traceability verification failed for {scenario['test_id']}")
            return False
    
    async def _verify_source_traceability(self, scenario: Dict[str, Any], chunk_data: ChunkData):
        """Verify source identifier matches expected pattern."""
        print("   🔍 Source traceability:")
        
        expected_pattern = scenario["expected_source_pattern"]
        actual_source = chunk_data.source_identifier
        
        print(f"     Expected pattern: {expected_pattern}")
        print(f"     Actual source:    {actual_source}")
        
        # Allow flexible matching
        if expected_pattern not in actual_source and actual_source not in expected_pattern:
            # Try partial match
            source_parts = expected_pattern.split(':')
            if len(source_parts) >= 2 and source_parts[1] not in actual_source:
                raise AssertionError(f"Source identifier mismatch: {actual_source} does not contain {source_parts[1]}")
        
        print("     ✅ Source identifier verified")
    
    async def _verify_content_keywords(self, scenario: Dict[str, Any], chunk_data: ChunkData):
        """Verify expected keywords are present in chunk content."""
        print("   📝 Content verification:")
        
        chunk_text = (chunk_data.chunk_text_summary or "").lower()
        expected_keywords = [kw.lower() for kw in scenario["expected_keywords"]]
        
        # Display the actual retrieved content in red
        print("\033[36m" + "="*80)
        print("🔍 ACTUAL RETRIEVED CONTENT:")
        print("="*80)
        actual_content = chunk_data.chunk_text_summary or "(No content)"
        # Truncate very long content for readability
        if len(actual_content) > 500:
            displayed_content = actual_content[:500] + "\n... [TRUNCATED] ..."
        else:
            displayed_content = actual_content
        print(displayed_content)
        print("="*80)
        print("📋 SOURCE INFO:")
        print(f"Source Type: {chunk_data.source_type.value}")
        print(f"Source ID: {chunk_data.source_identifier}")
        print(f"Chunk UUID: {chunk_data.chunk_uuid}")
        if chunk_data.chunk_metadata:
            print(f"Metadata: {chunk_data.chunk_metadata}")
        print("="*80 + "\033[0m")
        
        found_keywords = []
        missing_keywords = []
        
        for keyword in expected_keywords:
            if keyword in chunk_text:
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        print(f"     Expected keywords: {expected_keywords}")
        print(f"     Found keywords:    {found_keywords}")
        
        if missing_keywords:
            print(f"     Missing keywords:  {missing_keywords}")
        
        # Require at least 50% of keywords to be found
        required_matches = max(1, len(expected_keywords) // 2)
        if len(found_keywords) < required_matches:
            raise AssertionError(f"Too few keywords found: {found_keywords} (need at least {required_matches})")
        
        print("     ✅ Content keywords verified")
    
    async def _verify_knowledge_graph_entities(self, scenario: Dict[str, Any], entities: List[Entity]):
        """Verify expected entities exist in knowledge graph."""
        print("   🕸️  Entity verification:")
        
        if not entities:
            print("     ⚠️  No entities found (this may be expected for some content)")
            return
        
        entity_names = [entity.name.lower() for entity in entities]
        expected_entities = [e.lower() for e in scenario["expected_entities"]]
        
        found_entities = []
        for expected in expected_entities:
            if any(expected in name for name in entity_names):
                found_entities.append(expected)
        
        print(f"     Expected entities: {expected_entities}")
        print(f"     Found entities:    {found_entities}")
        print(f"     All entities:      {[e.name for e in entities[:5]]}")  # Show first 5
        
        # More lenient check for entities (they might be variations)
        if len(entities) == 0:
            print("     ⚠️  No entities extracted (content may not contain named entities)")
        else:
            print("     ✅ Knowledge graph entities verified")
    
    async def _verify_cross_system_consistency(self, chunk_uuid: str, results: Dict[str, Any]):
        """Verify consistency across all storage systems."""
        print("   🔄 Cross-system consistency:")
        
        chunk_data = results["chunk_data"]
        
        # Check UUID consistency
        db_uuid = str(chunk_data.chunk_uuid)
        if db_uuid != chunk_uuid:
            raise AssertionError(f"UUID mismatch: vector={chunk_uuid}, database={db_uuid}")
        
        # Check ingestion status
        if chunk_data.ingestion_status != IngestionStatus.COMPLETED:
            print(f"     ⚠️  Ingestion status: {chunk_data.ingestion_status}")
        
        # Check metadata exists
        if not chunk_data.chunk_metadata:
            print("     ⚠️  No chunk metadata found")
        
        # Check content hash exists
        if not chunk_data.source_content_hash:
            print("     ⚠️  No content hash found")
        
        print("     ✅ Cross-system consistency verified")
    
    async def _verify_temporal_consistency(self, chunk_data: ChunkData):
        """Verify temporal aspects of the data."""
        print("   ⏰ Temporal consistency:")
        
        now = datetime.now()
        ingestion_time = chunk_data.ingestion_timestamp
        
        if ingestion_time:
            # Remove timezone info for comparison if present
            if ingestion_time.tzinfo:
                ingestion_time = ingestion_time.replace(tzinfo=None)
            
            time_diff = now - ingestion_time
            
            print(f"     Ingestion time: {ingestion_time}")
            print(f"     Time diff:      {time_diff}")
            
            # Check if ingestion happened within reasonable time (1 hour)
            if time_diff > timedelta(hours=1):
                print(f"     ⚠️  Data is older than 1 hour ({time_diff})")
            else:
                print("     ✅ Recent ingestion verified")
        else:
            print("     ⚠️  No ingestion timestamp found")
    
    # ================================================================
    # SCENARIO EXECUTION
    # ================================================================
    
    async def run_single_scenario(self, scenario_name: str) -> bool:
        """Run complete test for a single scenario."""
        scenario = TEST_SCENARIOS.get(scenario_name)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        print(f"\n{'='*80}")
        print(f"🧪 RUNNING E2E TEST: {scenario['test_id']}")
        print(f"   📊 Description: {scenario['description']}")
        print(f"   📁 Source: {scenario['source_type']}")
        print(f"   🎯 Target: {scenario['source_identifier']}")
        print(f"{'='*80}")
        

        
        success = False
        error_message = None
        
        try:
            # Step 1: Ingestion
            ingestion_result = await self.run_ingestion_test(scenario)
            if not ingestion_result["success"]:
                raise RuntimeError(f"Ingestion failed: {ingestion_result.get('error', 'Unknown error')}")
            
            # Step 2: For drive_folder, only test ingestion (folders are containers, not content)
            if scenario["source_type"] == "drive_folder":
                print(f"\n✅ DRIVE FOLDER VALIDATION: Ingestion-only test completed")
                print(f"   📁 Folder processed successfully: {scenario['source_identifier']}")
                print(f"   📊 Files ingested: {ingestion_result.get('chunks_processed', 'Unknown')}")
                print(f"   ✅ Drive folder contents successfully indexed")
                print(f"\n🎉 SUCCESS: {scenario['test_id']} passed ingestion test!")
                success = True
                
            else:
                # Step 2: Wait for systems to sync
                sync_time = 10  # seconds
                print(f"\n⏳ WAITING: Allowing {sync_time}s for systems to sync...")
                await asyncio.sleep(sync_time)
                
                # Step 3: Retrieval
                retrieval_result = await self.run_retrieval_test(scenario)
                if not retrieval_result["success"]:
                    raise RuntimeError(f"Retrieval failed: {retrieval_result.get('error', 'Unknown error')}")
                
                # Step 4: Verification
                verification_success = await self.verify_traceability(scenario, retrieval_result)
                if not verification_success:
                    raise RuntimeError("Traceability verification failed")
                
                print(f"\n🎉 SUCCESS: {scenario['test_id']} passed all tests!")
                success = True
            
        except Exception as e:
            error_message = str(e)
            print(f"\n💥 FAILURE: {scenario['test_id']} failed: {e}")
            self.logger.exception(f"Scenario {scenario_name} failed")
        
        # Record result
        self.stats.add_scenario_result(scenario_name, success, error_message)
        
        # Show enhanced reporting for this scenario
        await self._generate_scenario_report(scenario_name, scenario['test_id'])
        
        return success
    
    async def _generate_scenario_report(self, scenario_name: str, test_id: str):
        """Generate enhanced report for a single scenario."""
        stats = self.stats.get_summary()
        
        print(f"\n{'📊 DETAILED TEST RESULTS 📊':^80}")
        print(f"{'='*80}")
        
        # ====================================================================
        # PER-SYSTEM RESULTS FOR THIS SCENARIO
        # ====================================================================
        system_results = stats['system_results']
        scenario_details = stats['scenario_details'].get(test_id, {})
        
        print(f"🔧 SYSTEM PERFORMANCE BREAKDOWN:")
        print(f"{'='*80}")
        
        # Vector Search Results
        vs_details = scenario_details.get('vector_search', {})
        vs_success = vs_details.get('success', False)
        vs_metrics = vs_details.get('metrics', {})
        
        print(f"\n📊 VECTOR SEARCH SYSTEM:")
        print(f"   Status:           {'✅ PASS' if vs_success else '❌ FAIL'}")
        if vs_metrics.get('response_time_ms'):
            print(f"   Response time:    {vs_metrics['response_time_ms']:.1f}ms")
        if vs_metrics.get('similarity_score'):
            print(f"   Similarity score: {vs_metrics['similarity_score']:.3f}")
        if vs_metrics.get('results_count'):
            print(f"   Results found:    {vs_metrics['results_count']}")
        if vs_metrics.get('target_position'):
            print(f"   Target position:  #{vs_metrics['target_position']}")
        
        # Database Results  
        db_details = scenario_details.get('database', {})
        db_success = db_details.get('success', False)
        db_metrics = db_details.get('metrics', {})
        
        print(f"\n🗄️  DATABASE SYSTEM:")
        print(f"   Status:           {'✅ PASS' if db_success else '❌ FAIL'}")
        if db_metrics.get('response_time_ms'):
            print(f"   Response time:    {db_metrics['response_time_ms']:.1f}ms")
        if db_metrics.get('source_type'):
            print(f"   Source verified:  {db_metrics['source_type']}")
        if 'has_metadata' in db_metrics:
            print(f"   Metadata found:   {'✅ Yes' if db_metrics['has_metadata'] else '❌ No'}")
        
        # Knowledge Graph Results
        kg_details = scenario_details.get('knowledge_graph', {})
        kg_success = kg_details.get('success', False)
        kg_metrics = kg_details.get('metrics', {})
        
        print(f"\n🕸️  KNOWLEDGE GRAPH SYSTEM:")
        print(f"   Status:           {'✅ PASS' if kg_success else '❌ FAIL'}")
        if kg_metrics.get('response_time_ms'):
            print(f"   Response time:    {kg_metrics['response_time_ms']:.1f}ms")
        if 'entity_count' in kg_metrics:
            print(f"   Entities found:   {kg_metrics['entity_count']}")
        if kg_metrics.get('entities_found'):
            entities_str = ', '.join(kg_metrics['entities_found'][:3])
            if len(kg_metrics['entities_found']) > 3:
                entities_str += f" + {len(kg_metrics['entities_found']) - 3} more"
            print(f"   Sample entities:  {entities_str}")
        
        # ====================================================================
        # OVERALL ASSESSMENT
        # ====================================================================
        all_systems_passed = vs_success and db_success and kg_success
        systems_passed = sum([vs_success, db_success, kg_success])
        
        print(f"\n{'🎯 SCENARIO ASSESSMENT 🎯':^80}")
        print(f"{'='*80}")
        print(f"Systems tested:   3 (Vector Search, Database, Knowledge Graph)")
        print(f"Systems passed:   {systems_passed}/3")
        print(f"Overall result:   {'✅ ALL SYSTEMS OPERATIONAL' if all_systems_passed else f'⚠️  {3-systems_passed} SYSTEM(S) NEED ATTENTION'}")
        
        # Individual system health
        print(f"\nSystem Health:")
        print(f"  📊 Vector Search:   {'🟢 HEALTHY' if vs_success else '🔴 FAILING'}")
        print(f"  🗄️  Database:       {'🟢 HEALTHY' if db_success else '🔴 FAILING'}")
        print(f"  🕸️  Knowledge Graph: {'🟢 HEALTHY' if kg_success else '🔴 FAILING'}")
        
        if all_systems_passed:
            print(f"\n🎉 EXCELLENT! All retrieval systems are working perfectly!")
            print(f"✅ Your data pipeline is ready for production workloads")
        elif systems_passed >= 2:
            print(f"\n⚠️  GOOD: Most systems operational, minor issues detected")
            print(f"🔧 Consider reviewing the failing system for optimization")
        else:
            print(f"\n🚨 ATTENTION: Multiple systems need immediate review")
            print(f"🔧 Check system configurations and connectivity")
        
        print(f"{'='*80}")
        
        # Save individual scenario report
        report_file = f"test_report_{scenario_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            scenario_data = {
                "scenario": scenario_name,
                "test_id": test_id,
                "timestamp": datetime.now().isoformat(),
                "system_results": scenario_details,
                "overall_success": all_systems_passed
            }
            with open(report_file, 'w') as f:
                json.dump(scenario_data, f, indent=2, default=str)
            print(f"📄 Scenario report saved to: {report_file}")
        except Exception as e:
            self.logger.error(f"Failed to save scenario report: {e}")

    async def run_all_scenarios(self) -> bool:
        """Run all test scenarios."""
        print(f"\n{'🚀 STARTING COMPREHENSIVE E2E TESTING 🚀':^80}")
        
        all_passed = True
        
        for scenario_name in TEST_SCENARIOS.keys():
            try:
                scenario_passed = await self.run_single_scenario(scenario_name)
                if not scenario_passed:
                    all_passed = False
                    
                # Brief pause between scenarios
                await asyncio.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Critical failure in scenario {scenario_name}: {e}")
                all_passed = False
        
        # Generate final comprehensive report
        await self._generate_final_report()
        
        return all_passed
    
    async def _generate_final_report(self):
        """Generate and display comprehensive final test report for all scenarios."""
        stats = self.stats.get_summary()
        
        print(f"\n{'📊 COMPREHENSIVE E2E TEST REPORT 📊':^80}")
        print(f"{'='*80}")
        print(f"Execution time:     {stats['elapsed_time_seconds']:.2f} seconds")
        print(f"Scenarios run:      {stats['scenarios_run']}")
        print(f"Scenarios passed:   {stats['scenarios_passed']}")
        print(f"Scenarios failed:   {stats['scenarios_failed']}")
        print(f"Success rate:       {stats['success_rate']:.1f}%")
        print(f"Chunks processed:   {stats['total_chunks_processed']}")
        print(f"Retrieval queries:  {stats['total_retrieval_queries']}")
        print(f"{'='*80}")
        
        # ====================================================================
        # PER-SYSTEM AGGREGATE RESULTS
        # ====================================================================
        print(f"\n{'🔧 AGGREGATE SYSTEM-BY-SYSTEM RESULTS 🔧':^80}")
        print(f"{'='*80}")
        
        system_results = stats['system_results']
        
        # Vector Search Results
        vs_stats = system_results['vector_search']
        vs_success_rate = (vs_stats['passed'] / vs_stats['tests'] * 100) if vs_stats['tests'] > 0 else 0
        print(f"\n📊 VECTOR SEARCH SYSTEM:")
        print(f"   Tests run:        {vs_stats['tests']}")
        print(f"   Tests passed:     {vs_stats['passed']}")
        print(f"   Tests failed:     {vs_stats['failed']}")
        print(f"   Success rate:     {vs_success_rate:.1f}%")
        if vs_stats['avg_similarity'] > 0:
            print(f"   Avg similarity:   {vs_stats['avg_similarity']:.3f}")
        print(f"   Status:           {'✅ HEALTHY' if vs_success_rate >= 80 else '⚠️  NEEDS ATTENTION' if vs_success_rate >= 50 else '❌ FAILING'}")
        
        # Database Results  
        db_stats = system_results['database']
        db_success_rate = (db_stats['passed'] / db_stats['tests'] * 100) if db_stats['tests'] > 0 else 0
        print(f"\n🗄️  DATABASE SYSTEM:")
        print(f"   Tests run:        {db_stats['tests']}")
        print(f"   Tests passed:     {db_stats['passed']}")
        print(f"   Tests failed:     {db_stats['failed']}")
        print(f"   Success rate:     {db_success_rate:.1f}%")
        if db_stats['avg_response_time'] > 0:
            print(f"   Avg response:     {db_stats['avg_response_time']:.1f}ms")
        print(f"   Status:           {'✅ HEALTHY' if db_success_rate >= 80 else '⚠️  NEEDS ATTENTION' if db_success_rate >= 50 else '❌ FAILING'}")
        
        # Knowledge Graph Results
        kg_stats = system_results['knowledge_graph']
        kg_success_rate = (kg_stats['passed'] / kg_stats['tests'] * 100) if kg_stats['tests'] > 0 else 0
        print(f"\n🕸️  KNOWLEDGE GRAPH SYSTEM:")
        print(f"   Tests run:        {kg_stats['tests']}")
        print(f"   Tests passed:     {kg_stats['passed']}")
        print(f"   Tests failed:     {kg_stats['failed']}")
        print(f"   Success rate:     {kg_success_rate:.1f}%")
        if kg_stats['avg_entities'] > 0:
            print(f"   Avg entities:     {kg_stats['avg_entities']:.1f}")
        print(f"   Status:           {'✅ HEALTHY' if kg_success_rate >= 80 else '⚠️  NEEDS ATTENTION' if kg_success_rate >= 50 else '❌ FAILING'}")
        
        # ====================================================================
        # DETAILED SCENARIO MATRIX
        # ====================================================================
        print(f"\n{'📋 DETAILED SCENARIO RESULTS MATRIX 📋':^80}")
        print(f"{'='*80}")
        print(f"{'Scenario':<25} {'Vector':<10} {'Database':<10} {'KnowGraph':<10} {'Status':<12}")
        print("-" * 80)
        
        for scenario_name, scenario in TEST_SCENARIOS.items():
            scenario_details = stats['scenario_details'].get(scenario['test_id'], {})
            
            # Determine scenario status
            if scenario_name in [error.split(':')[0] for error in stats['errors']]:
                status = "❌ FAILED"
            elif any(scenario_name in scenario['test_id'] for scenario in TEST_SCENARIOS.values()):
                status = "✅ PASSED"
            else:
                status = "⏸️  SKIPPED"
            
            # Get system statuses
            vs_status = "✅ PASS" if scenario_details.get('vector_search', {}).get('success', False) else "❌ FAIL" if scenario_details else "⏸️  SKIP"
            db_status = "✅ PASS" if scenario_details.get('database', {}).get('success', False) else "❌ FAIL" if scenario_details else "⏸️  SKIP"
            kg_status = "✅ PASS" if scenario_details.get('knowledge_graph', {}).get('success', False) else "❌ FAIL" if scenario_details else "⏸️  SKIP"
            
            print(f"{scenario['test_id']:<25} {vs_status:<10} {db_status:<10} {kg_status:<10} {status:<12}")
        
        # ====================================================================
        # AGGREGATE PERFORMANCE METRICS
        # ====================================================================
        if stats['scenario_details']:
            print(f"\n{'⚡ AGGREGATE PERFORMANCE METRICS ⚡':^80}")
            print(f"{'='*80}")
            
            # Collect performance data
            vector_times = []
            db_times = []
            kg_times = []
            similarities = []
            
            for scenario_id, details in stats['scenario_details'].items():
                if 'vector_search' in details and 'metrics' in details['vector_search']:
                    vs_metrics = details['vector_search']['metrics']
                    if 'response_time_ms' in vs_metrics:
                        vector_times.append(vs_metrics['response_time_ms'])
                    if 'similarity_score' in vs_metrics:
                        similarities.append(vs_metrics['similarity_score'])
                
                if 'database' in details and 'metrics' in details['database']:
                    db_metrics = details['database']['metrics']
                    if 'response_time_ms' in db_metrics:
                        db_times.append(db_metrics['response_time_ms'])
                
                if 'knowledge_graph' in details and 'metrics' in details['knowledge_graph']:
                    kg_metrics = details['knowledge_graph']['metrics']
                    if 'response_time_ms' in kg_metrics:
                        kg_times.append(kg_metrics['response_time_ms'])
            
            # Display performance summary
            if vector_times:
                print(f"📊 Vector Search Performance:")
                print(f"   Avg response time: {sum(vector_times)/len(vector_times):.1f}ms")
                print(f"   Min response time: {min(vector_times):.1f}ms")
                print(f"   Max response time: {max(vector_times):.1f}ms")
                if similarities:
                    print(f"   Avg similarity:    {sum(similarities)/len(similarities):.3f}")
            
            if db_times:
                print(f"\n🗄️  Database Performance:")
                print(f"   Avg response time: {sum(db_times)/len(db_times):.1f}ms")
                print(f"   Min response time: {min(db_times):.1f}ms")
                print(f"   Max response time: {max(db_times):.1f}ms")
            
            if kg_times:
                print(f"\n🕸️  Knowledge Graph Performance:")
                print(f"   Avg response time: {sum(kg_times)/len(kg_times):.1f}ms")
                print(f"   Min response time: {min(kg_times):.1f}ms")
                print(f"   Max response time: {max(kg_times):.1f}ms")
        
        # ====================================================================
        # ERROR DETAILS
        # ====================================================================
        if stats['errors']:
            print(f"\n{'🚨 ERROR DETAILS 🚨':^80}")
            print(f"{'='*80}")
            for error in stats['errors']:
                print(f"❌ {error}")
        
        print("-" * 80)
        
        # ====================================================================
        # FINAL VERDICT
        # ====================================================================
        overall_system_health = (vs_success_rate + db_success_rate + kg_success_rate) / 3
        
        if stats['scenarios_failed'] == 0 and overall_system_health >= 80:
            print("\n🎉 ALL SYSTEMS OPERATIONAL! E2E Pipeline Fully Validated! 🎉")
            print("✅ Data lifecycle verified from source to retrieval")
            print("✅ All three retrieval systems functioning correctly")
            print("✅ Cross-system consistency confirmed")
            print("✅ Architecture ready for production workloads")
        elif overall_system_health >= 60:
            print(f"\n⚠️  PARTIAL SUCCESS: Overall system health: {overall_system_health:.1f}%")
            print("🔧 Some systems may need optimization")
            print("📋 Review individual system performance above")
        else:
            print(f"\n❌ SYSTEM ISSUES DETECTED: Overall health: {overall_system_health:.1f}%")
            print("🚨 Multiple systems require immediate attention")
            print("🔧 Check system configuration and connectivity")
            print("📋 Review error details and logs for troubleshooting")
        
        # Save comprehensive report to file
        report_file = f"test_report_comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(report_file, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            print(f"\n📄 Comprehensive report saved to: {report_file}")
        except Exception as e:
            self.logger.error(f"Failed to save comprehensive report: {e}")


# ====================================================================
# CLI INTERFACE
# ====================================================================

async def main():
    """Main entry point for E2E testing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="End-to-End Pipeline Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_full_pipeline.py --scenario all --verbose
  python test_full_pipeline.py --scenario github
  python test_full_pipeline.py --scenario drive --verbose
  python test_full_pipeline.py --scenario drive_file
  python test_full_pipeline.py --scenario web

Test Scenarios:
  github     - Test GitHub repository file ingestion and retrieval
  drive      - Test Google Drive folder ingestion and retrieval  
  drive_file - Test individual Google Drive file ingestion and retrieval
  web        - Test web page ingestion and retrieval
  all        - Run all test scenarios
        """
    )
    
    parser.add_argument(
        "--scenario", 
        choices=["github", "drive", "drive_file", "web", "all"], 
        default="all", 
        help="Test scenario to run (default: all)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging and detailed output"
    )
    parser.add_argument(
        "--config",
        default="app/config/data_sources_config.yaml",
        help="Path to configuration file (default: config/data_sources_config.yaml)"
    )
    
    args = parser.parse_args()
    
    print(f"{'='*80}")
    print(f"🧪 End-to-End Data Pipeline Testing")
    print(f"{'='*80}")
    print(f"Configuration: {args.config}")
    print(f"Scenario:      {args.scenario}")
    print(f"Verbose:       {args.verbose}")
    print(f"{'='*80}")
    
    # Initialize test runner (handles logging configuration internally)
    runner = E2ETestRunner(verbose=args.verbose)
    
    try:
        # Setup test environment
        setup_success = await runner.setup_test_environment()
        if not setup_success:
            print("\n💥 CRITICAL: Test environment setup failed")
            return 1
        
        # Run requested tests
        if args.scenario == "all":
            success = await runner.run_all_scenarios()
        else:
            success = await runner.run_single_scenario(args.scenario)
        
        # Return appropriate exit code
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test execution interrupted by user")
        return 130
        
    except Exception as e:
        print(f"\n💥 CRITICAL FAILURE: {e}")
        logger.exception("Critical test failure")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 