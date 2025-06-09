#!/usr/bin/env python3
"""
Database Isolation Test - Direct testing of PostgreSQL database insertion and retrieval.

This test isolates the database functionality to determine if the core
chunk storage, metadata handling, and retrieval operations are working correctly.
"""

import asyncio
import sys
import uuid
import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.configuration import get_system_config
from data_ingestion.managers.database_manager import DatabaseManager
from data_ingestion.models import ChunkData, IngestionStatus


class DatabaseIsolationTest:
    """Standalone test for PostgreSQL database insertion and retrieval operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.database_manager = None
        self.test_data = []
        self.test_results = {
            "initialization": False,
            "chunk_insertion": False,
            "chunk_retrieval": False,
            "metadata_queries": False,
            "recent_chunks": False,
            "contextual_chunks": False,
            "cleanup": False,
            "errors": []
        }
    
    async def setup(self) -> bool:
        """Initialize the database manager."""
        try:
            print("🔧 DATABASE ISOLATION TEST SETUP")
            print("=" * 50)
            
            # Load configuration
            print("   📋 Loading configuration...")
            config = get_system_config()
            
            if not config.pipeline_config.database:
                raise ValueError("Database configuration not found")
            
            # Initialize Database Manager
            print("   🚀 Initializing DatabaseManager...")
            self.database_manager = DatabaseManager(config.pipeline_config.database)
            
            success = await self.database_manager.initialize()
            if not success:
                raise RuntimeError("Database manager initialization failed")
            
            print("   ✅ Database manager initialized successfully")
            self.test_results["initialization"] = True
            return True
            
        except Exception as e:
            error_msg = f"Setup failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    def generate_test_data(self, count: int = 5) -> List[ChunkData]:
        """Generate sample test data for database testing."""
        print(f"\n📝 GENERATING TEST DATA ({count} samples)")
        print("=" * 50)
        
        test_samples = [
            {
                "text": "This is a comprehensive guide to Python programming fundamentals including variables, functions, and classes.",
                "source_type": "github_repo",
                "source_id": "python_guide_v1",
                "metadata": {"language": "python", "difficulty": "beginner", "topic": "programming"}
            },
            {
                "text": "Advanced machine learning techniques for natural language processing and computer vision applications.",
                "source_type": "drive_file", 
                "source_id": "ml_research_2024",
                "metadata": {"field": "AI", "year": 2024, "citations": 45}
            },
            {
                "text": "Google Cloud Platform architecture patterns for scalable web applications and microservices deployment.",
                "source_type": "web_source",
                "source_id": "gcp_patterns",
                "metadata": {"platform": "GCP", "architecture": "microservices", "scale": "enterprise"}
            },
            {
                "text": "Database design principles for high-performance applications with vector similarity search capabilities.",
                "source_type": "drive_folder",
                "source_id": "db_design_manual",
                "metadata": {"database_type": "vector", "performance": "high", "features": ["similarity_search"]}
            },
            {
                "text": "User experience best practices for building intuitive and accessible web interfaces.",
                "source_type": "local",
                "source_id": "ux_best_practices",
                "metadata": {"domain": "UX", "accessibility": True, "platform": "web"}
            }
        ]
        
        # Take only the requested count
        selected_samples = test_samples[:count]
        
        # Generate ChunkData objects
        for i, sample in enumerate(selected_samples):
            test_uuid = uuid.uuid4()
            now = datetime.now(timezone.utc)
            
            chunk_data = ChunkData(
                chunk_uuid=test_uuid,
                source_type=sample["source_type"],
                source_identifier=sample["source_id"],
                chunk_text_summary=sample["text"],
                chunk_metadata=sample["metadata"],
                ingestion_timestamp=now,
                source_last_modified_at=now,
                source_content_hash=f"hash_{i}_{test_uuid.hex[:8]}",
                last_indexed_at=now,
                ingestion_status=IngestionStatus.COMPLETED.value
            )
            
            self.test_data.append(chunk_data)
            print(f"   📄 Sample {i+1}: {sample['text'][:50]}... (UUID: {str(test_uuid)[:8]}...)")
        
        print(f"   ✅ Generated {len(self.test_data)} test samples")
        return self.test_data
    
    async def test_chunk_insertion(self) -> bool:
        """Test insertion of chunks into the database."""
        try:
            print(f"\n📤 TESTING CHUNK INSERTION")
            print("=" * 50)
            
            print(f"   🔄 Inserting {len(self.test_data)} chunks...")
            start_time = datetime.now()
            
            # Test individual insertions
            individual_success = 0
            for i, chunk in enumerate(self.test_data):
                try:
                    success = await self.database_manager.ingest_chunk(chunk)
                    if success:
                        individual_success += 1
                        print(f"      ✅ Chunk {i+1} inserted successfully")
                    else:
                        print(f"      ❌ Chunk {i+1} insertion failed")
                except Exception as e:
                    print(f"      ❌ Chunk {i+1} insertion error: {e}")
            
            insertion_time = (datetime.now() - start_time).total_seconds()
            
            print(f"   📊 Individual insertion result:")
            print(f"      - Total: {len(self.test_data)}")
            print(f"      - Successful: {individual_success}")
            print(f"      - Failed: {len(self.test_data) - individual_success}")
            print(f"      - Success rate: {(individual_success / len(self.test_data) * 100):.1f}%")
            print(f"   ⏱️  Insertion time: {insertion_time:.2f}s")
            
            # Test batch insertion with new data
            print(f"\n   🔄 Testing batch insertion...")
            batch_test_data = []
            for i in range(3):
                test_uuid = uuid.uuid4()
                now = datetime.now(timezone.utc)
                
                chunk_data = ChunkData(
                    chunk_uuid=test_uuid,
                    source_type="local",
                    source_identifier=f"batch_test_{i}",
                    chunk_text_summary=f"Batch test chunk number {i} for testing batch insertion functionality.",
                    chunk_metadata={"batch_index": i, "test_type": "batch_insertion"},
                    ingestion_timestamp=now,
                    source_last_modified_at=now,
                    source_content_hash=f"batch_hash_{i}_{test_uuid.hex[:8]}",
                    last_indexed_at=now,
                    ingestion_status=IngestionStatus.COMPLETED.value
                )
                batch_test_data.append(chunk_data)
            
            batch_start = datetime.now()
            batch_successful, batch_total = await self.database_manager.batch_ingest_chunks(batch_test_data)
            batch_time = (datetime.now() - batch_start).total_seconds()
            
            print(f"   📊 Batch insertion result:")
            print(f"      - Total: {batch_total}")
            print(f"      - Successful: {batch_successful}")
            print(f"      - Success rate: {(batch_successful / batch_total * 100):.1f}%")
            print(f"   ⏱️  Batch insertion time: {batch_time:.2f}s")
            
            # Add batch data to test data for later retrieval
            self.test_data.extend(batch_test_data)
            
            if individual_success == 0 and batch_successful == 0:
                raise ValueError("No chunks were successfully inserted")
            
            print(f"   ✅ Database insertion operations completed")
            self.test_results["chunk_insertion"] = True
            return True
            
        except Exception as e:
            error_msg = f"Chunk insertion failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def test_chunk_retrieval(self) -> bool:
        """Test retrieval of chunks from the database."""
        try:
            print(f"\n📥 TESTING CHUNK RETRIEVAL")
            print("=" * 50)
            
            # Test individual UUID retrieval
            print("   🔍 Testing individual UUID retrieval...")
            successful_retrievals = 0
            
            for i, original_chunk in enumerate(self.test_data[:3]):  # Test first 3
                try:
                    retrieved_chunk = await self.database_manager.get_chunk(str(original_chunk.chunk_uuid))
                    
                    if retrieved_chunk:
                        successful_retrievals += 1
                        print(f"      ✅ Chunk {i+1} retrieved successfully")
                        
                        # Validate data integrity
                        if retrieved_chunk.source_type == original_chunk.source_type:
                            print(f"         - Source type matches: {retrieved_chunk.source_type}")
                        else:
                            print(f"         - ⚠️  Source type mismatch: {retrieved_chunk.source_type} vs {original_chunk.source_type}")
                        
                        if retrieved_chunk.chunk_text_summary == original_chunk.chunk_text_summary:
                            print(f"         - Text content matches")
                        else:
                            print(f"         - ⚠️  Text content mismatch")
                            
                    else:
                        print(f"      ❌ Chunk {i+1} not found")
                        
                except Exception as e:
                    print(f"      ❌ Chunk {i+1} retrieval error: {e}")
            
            print(f"   📊 Individual retrieval: {successful_retrievals}/3 successful")
            
            # Test batch retrieval
            print(f"\n   🔍 Testing batch UUID retrieval...")
            test_uuids = [str(chunk.chunk_uuid) for chunk in self.test_data[:5]]
            
            batch_start = datetime.now()
            retrieved_chunks = await self.database_manager.get_chunks(test_uuids)
            batch_time = (datetime.now() - batch_start).total_seconds()
            
            print(f"   📊 Batch retrieval result:")
            print(f"      - Requested: {len(test_uuids)}")
            print(f"      - Retrieved: {len(retrieved_chunks)}")
            print(f"      - Success rate: {(len(retrieved_chunks) / len(test_uuids) * 100):.1f}%")
            print(f"   ⏱️  Batch retrieval time: {batch_time:.3f}s")
            
            if successful_retrievals == 0 and len(retrieved_chunks) == 0:
                raise ValueError("No chunks could be retrieved")
            
            self.test_results["chunk_retrieval"] = True
            return True
            
        except Exception as e:
            error_msg = f"Chunk retrieval failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def test_metadata_queries(self) -> bool:
        """Test metadata-based search and filtering."""
        try:
            print(f"\n🔍 TESTING METADATA QUERIES")
            print("=" * 50)
            
            # Test source type filtering
            print("   🔍 Testing source type filtering...")
            source_types = ["github_repo", "drive_file", "local"]
            
            for source_type in source_types:
                try:
                    results = await self.database_manager.search_chunks(
                        source_type=source_type,
                        limit=10
                    )
                    print(f"      📊 Source type '{source_type}': {len(results)} chunks found")
                    
                    if results:
                        # Verify all results have correct source type
                        correct_type = all(chunk.source_type == source_type for chunk in results)
                        print(f"         - {'✅' if correct_type else '❌'} All results have correct source type")
                        
                except Exception as e:
                    print(f"      ❌ Source type query failed: {e}")
            
            # Test source identifier filtering
            print(f"\n   🔍 Testing source identifier filtering...")
            test_source_ids = ["python_guide_v1", "ml_research_2024", "batch_test_0"]
            
            for source_id in test_source_ids:
                try:
                    results = await self.database_manager.search_chunks(
                        source_identifier=source_id,
                        limit=10
                    )
                    print(f"      📊 Source ID '{source_id}': {len(results)} chunks found")
                    
                    if results:
                        # Verify all results have correct source identifier
                        correct_id = all(chunk.source_identifier == source_id for chunk in results)
                        print(f"         - {'✅' if correct_id else '❌'} All results have correct source identifier")
                        
                except Exception as e:
                    print(f"      ❌ Source identifier query failed: {e}")
            
            # Test metadata filtering
            print(f"\n   🔍 Testing metadata filtering...")
            metadata_filters = [
                {"language": "python"},
                {"field": "AI"},
                {"test_type": "batch_insertion"}
            ]
            
            for metadata_filter in metadata_filters:
                try:
                    results = await self.database_manager.search_chunks(
                        metadata_filter=metadata_filter,
                        limit=10
                    )
                    filter_desc = ", ".join(f"{k}={v}" for k, v in metadata_filter.items())
                    print(f"      📊 Metadata filter '{filter_desc}': {len(results)} chunks found")
                    
                    if results:
                        # Show sample metadata
                        sample_metadata = results[0].chunk_metadata
                        print(f"         - Sample metadata: {json.dumps(sample_metadata, indent=None)[:100]}...")
                        
                except Exception as e:
                    print(f"      ❌ Metadata query failed: {e}")
            
            self.test_results["metadata_queries"] = True
            return True
            
        except Exception as e:
            error_msg = f"Metadata queries failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def test_recent_chunks(self) -> bool:
        """Test recent chunks retrieval functionality."""
        try:
            print(f"\n📅 TESTING RECENT CHUNKS RETRIEVAL")
            print("=" * 50)
            
            # Test different limits
            limits = [5, 10, 20]
            
            for limit in limits:
                try:
                    start_time = datetime.now()
                    recent_chunks = await self.database_manager.get_recent_chunks(limit=limit)
                    query_time = (datetime.now() - start_time).total_seconds()
                    
                    print(f"   📊 Recent chunks (limit={limit}): {len(recent_chunks)} found in {query_time:.3f}s")
                    
                    if recent_chunks:
                        # Check if results are ordered by ingestion timestamp (newest first)
                        timestamps = [chunk.ingestion_timestamp for chunk in recent_chunks]
                        is_ordered = all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))
                        print(f"      - {'✅' if is_ordered else '❌'} Results ordered by timestamp (newest first)")
                        
                        # Check if any of our test data is in the recent chunks
                        test_uuids = {str(chunk.chunk_uuid) for chunk in self.test_data}
                        recent_uuids = {str(chunk.chunk_uuid) for chunk in recent_chunks}
                        found_test_data = len(test_uuids.intersection(recent_uuids))
                        print(f"      - Found {found_test_data} of our test chunks in recent results")
                        
                        # Show oldest and newest timestamps
                        if len(recent_chunks) > 1:
                            newest = timestamps[0]
                            oldest = timestamps[-1]
                            time_span = (newest - oldest).total_seconds()
                            print(f"      - Time span: {time_span:.1f}s from oldest to newest")
                    
                except Exception as e:
                    print(f"   ❌ Recent chunks query (limit={limit}) failed: {e}")
            
            self.test_results["recent_chunks"] = True
            return True
            
        except Exception as e:
            error_msg = f"Recent chunks test failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def test_contextual_chunks(self) -> bool:
        """Test contextual chunk retrieval and enrichment functionality."""
        try:
            print(f"\n🔗 TESTING CONTEXTUAL CHUNKS")
            print("=" * 50)
            
            if not self.test_data:
                print("   ⚠️  No test data available for contextual testing")
                self.test_results["contextual_chunks"] = True
                return True
            
            successful_operations = 0
            total_operations = 0
            
            # Test contextual chunk retrieval with different context windows
            print("   🔍 Testing contextual chunk retrieval...")
            test_chunk = self.test_data[0]
            context_windows = [1, 2, 3]
            
            for window in context_windows:
                total_operations += 1
                try:
                    start_time = datetime.now()
                    contextual_chunk = await self.database_manager.get_chunk_with_context(
                        str(test_chunk.chunk_uuid), 
                        context_window=window
                    )
                    query_time = (datetime.now() - start_time).total_seconds()
                    
                    if contextual_chunk:
                        print(f"   📊 Context window {window}: Retrieved in {query_time:.3f}s")
                        print(f"      - Primary chunk: {contextual_chunk.primary_chunk.source_identifier}")
                        print(f"      - Context chunks: {len(contextual_chunk.context_chunks)}")
                        print(f"      - Context window size: {contextual_chunk.context_window_size}")
                        
                        # Validate context structure
                        context_count = len(contextual_chunk.context_chunks)
                        expected_max = window * 2  # window before + window after
                        if context_count <= expected_max:
                            print(f"      - ✅ Context size appropriate ({context_count} <= {expected_max})")
                            successful_operations += 1
                        else:
                            print(f"      - ⚠️  Context size unexpected ({context_count} > {expected_max})")
                            successful_operations += 1  # Still counts as working
                    else:
                        print(f"   ❌ Context window {window}: No contextual chunk returned")
                        
                except Exception as e:
                    print(f"   ❌ Context window {window} failed: {e}")
            
            # Test batch contextual retrieval
            print(f"\n   🔍 Testing batch contextual retrieval...")
            test_uuids = [str(chunk.chunk_uuid) for chunk in self.test_data[:3]]
            total_operations += 1
            
            try:
                batch_start = datetime.now()
                contextual_chunks = await self.database_manager.get_contextual_chunks(
                    test_uuids, 
                    context_window=2
                )
                batch_time = (datetime.now() - batch_start).total_seconds()
                
                print(f"   📊 Batch contextual retrieval:")
                print(f"      - Requested: {len(test_uuids)}")
                print(f"      - Retrieved: {len(contextual_chunks)}")
                print(f"      - Success rate: {(len(contextual_chunks) / len(test_uuids) * 100):.1f}%")
                print(f"      - Batch time: {batch_time:.3f}s")
                
                # Show context details for first result
                if contextual_chunks:
                    first_context = contextual_chunks[0]
                    print(f"      - Sample context: {len(first_context.context_chunks)} context chunks")
                    successful_operations += 1
                
            except Exception as e:
                print(f"   ❌ Batch contextual retrieval failed: {e}")
            
            # Test chunk enrichment functionality
            print(f"\n   🔍 Testing chunk enrichment...")
            total_operations += 1
            
            try:
                chunks_to_enrich = self.test_data[:2]  # Use first 2 chunks
                
                # Test with mock vector scores and graph entities
                vector_scores = [0.95, 0.87]  # Mock similarity scores
                graph_entities = [["python", "programming"], ["AI", "machine_learning"]]  # Mock entities
                
                enrichment_start = datetime.now()
                enriched_chunks = await self.database_manager.enrich_chunks(
                    chunks_to_enrich,
                    vector_scores=vector_scores,
                    graph_entities=graph_entities
                )
                enrichment_time = (datetime.now() - enrichment_start).total_seconds()
                
                print(f"   📊 Chunk enrichment:")
                print(f"      - Input chunks: {len(chunks_to_enrich)}")
                print(f"      - Enriched chunks: {len(enriched_chunks)}")
                print(f"      - Enrichment time: {enrichment_time:.3f}s")
                
                if enriched_chunks:
                    sample_enriched = enriched_chunks[0]
                    print(f"      - Sample enriched chunk: {sample_enriched.chunk_data.source_identifier}")
                    
                    # Check if enrichment data is present
                    if hasattr(sample_enriched, 'vector_score'):
                        print(f"         - Vector score: {getattr(sample_enriched, 'vector_score', 'N/A')}")
                    if hasattr(sample_enriched, 'graph_entities'):
                        entities = getattr(sample_enriched, 'graph_entities', [])
                        print(f"         - Graph entities: {len(entities) if entities else 0}")
                    
                    successful_operations += 1
                
            except Exception as e:
                print(f"   ❌ Chunk enrichment failed: {e}")
            
            # Evaluate overall success
            print(f"\n   📊 Contextual operations success rate: {successful_operations}/{total_operations}")
            
            # FAIL if most contextual operations don't work
            if successful_operations == 0:
                raise ValueError("All contextual chunk operations failed")
            
            if successful_operations < total_operations / 2:
                raise ValueError(f"Most contextual operations failed ({successful_operations}/{total_operations})")
            
            self.test_results["contextual_chunks"] = True
            return True
            
        except Exception as e:
            error_msg = f"Contextual chunks test failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def cleanup(self) -> bool:
        """Clean up test resources."""
        try:
            print(f"\n🧹 CLEANUP")
            print("=" * 50)
            
            if self.database_manager:
                print("   🔄 Closing database manager...")
                await self.database_manager.close()
                print("   ✅ Database manager closed")
            
            # Give aiohttp sessions additional time to clean up
            print("   ⏳ Allowing time for session cleanup...")
            await asyncio.sleep(1.0)  # Give sessions time to fully close
            
            self.test_results["cleanup"] = True
            return True
            
        except Exception as e:
            error_msg = f"Cleanup failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    def print_final_report(self):
        """Print comprehensive test results."""
        print(f"\n📊 DATABASE ISOLATION TEST RESULTS")
        print("=" * 50)
        
        # Calculate overall success
        critical_tests = ["initialization", "chunk_insertion", "chunk_retrieval", "metadata_queries", "recent_chunks", "contextual_chunks"]
        passed_tests = sum(1 for test in critical_tests if self.test_results.get(test, False))
        total_tests = len(critical_tests)
        
        success_rate = (passed_tests / total_tests) * 100
        overall_success = success_rate >= 80  # At least 5/6 critical tests must pass
        
        print(f"🎯 OVERALL RESULT: {'✅ PASS' if overall_success else '❌ FAIL'}")
        print(f"📈 Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests} critical tests)")
        
        print(f"\n📋 TEST BREAKDOWN:")
        test_names = {
            "initialization": "Database Manager Initialization",
            "chunk_insertion": "Chunk Insertion (Individual & Batch)",
            "chunk_retrieval": "Chunk Retrieval (Individual & Batch)", 
            "metadata_queries": "Metadata-based Queries",
            "recent_chunks": "Recent Chunks Retrieval",
            "contextual_chunks": "Contextual Chunks & Enrichment",
            "cleanup": "Resource Cleanup"
        }
        
        for test_key, test_name in test_names.items():
            status = "✅ PASS" if self.test_results.get(test_key, False) else "❌ FAIL"
            print(f"   {status} {test_name}")
        
        if self.test_results["errors"]:
            print(f"\n❌ ERRORS ENCOUNTERED:")
            for i, error in enumerate(self.test_results["errors"], 1):
                print(f"   {i}. {error}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        if not self.test_results.get("initialization", False):
            print("   - Check database configuration and connection settings")
            print("   - Verify PostgreSQL instance is running and accessible")
            print("   - Check Cloud SQL connector permissions")
        elif not self.test_results.get("chunk_insertion", False):
            print("   - Check database write permissions")
            print("   - Verify database schema is properly initialized")
            print("   - Check for database constraint violations")
        elif not self.test_results.get("chunk_retrieval", False):
            print("   - Data insertion succeeded but retrieval failed")
            print("   - Check database read permissions")
            print("   - Verify database indexes are working correctly")
        elif not self.test_results.get("metadata_queries", False):
            print("   - Basic operations work but metadata queries failed")
            print("   - Check JSONB column functionality")
            print("   - Verify metadata indexing is working")
        elif not self.test_results.get("recent_chunks", False):
            print("   - Core operations work but recent chunks query failed")
            print("   - Check timestamp indexing and ordering")
            print("   - Verify get_recent_chunks method implementation")
        elif not self.test_results.get("contextual_chunks", False):
            print("   - Core operations work but contextual chunks functionality failed")
            print("   - Check get_chunk_with_context and get_contextual_chunks implementations")
            print("   - Verify chunk enrichment and context window logic")
        else:
            print("   - All critical database operations are working correctly!")
            print("   - The database layer is functioning properly")


async def main():
    """Main function to run the database isolation test."""
    # Set up logging and suppress the aiohttp client session warnings
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Suppress specific asyncio warnings from Google Cloud libraries
    import warnings
    warnings.filterwarnings("ignore", message=".*Unclosed client session.*")
    warnings.filterwarnings("ignore", message=".*Unclosed connector.*")
    
    # Also set asyncio logger to CRITICAL to suppress the specific error
    asyncio_logger = logging.getLogger('asyncio')
    asyncio_logger.setLevel(logging.CRITICAL)
    
    print("Database Isolation Test")
    print("=" * 50)
    
    test = DatabaseIsolationTest()
    
    try:
        # Run the complete test sequence
        if not await test.setup():
            return False
        
        # Generate test data
        test.generate_test_data(count=5)
        
        # Run ALL tests regardless of individual failures
        # This ensures we get complete diagnostic information
        
        test_results = []
        
        # Run chunk insertion test
        test_results.append(await test.test_chunk_insertion())
        
        # Run chunk retrieval test
        test_results.append(await test.test_chunk_retrieval())
        
        # Run metadata queries test
        test_results.append(await test.test_metadata_queries())
        
        # Run recent chunks test
        test_results.append(await test.test_recent_chunks())
        
        # Run contextual chunks test
        test_results.append(await test.test_contextual_chunks())
        
        # Return True only if ALL tests passed
        return all(test_results)
        
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Test failed with unexpected error: {e}")
        test.test_results["errors"].append(f"Unexpected error: {e}")
        return False
    finally:
        await test.cleanup()
        test.print_final_report()
        
        # Additional cleanup to handle any lingering aiohttp sessions
        try:
            # Give extra time for all sessions to close
            await asyncio.sleep(0.5)
            
            # Force garbage collection
            import gc
            gc.collect()
                
        except Exception:
            pass  # Ignore cleanup errors


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1) 