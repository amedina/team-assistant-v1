#!/usr/bin/env python3
"""
Vector Store Isolation Test - Direct testing of vector store insertion and retrieval.

This test isolates the vector store functionality to determine if the core
embedding generation, storage, and retrieval operations are working correctly.
"""

import asyncio
import sys
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.configuration import get_system_config
from data_ingestion.managers.vector_store_manager import VectorStoreManager
from data_ingestion.models import EmbeddingData


class VectorStoreIsolationTest:
    """Standalone test for vector store insertion and retrieval operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.vector_manager = None
        self.test_data = []
        self.test_results = {
            "initialization": False,
            "embedding_generation": False,
            "vector_insertion": False,
            "vector_retrieval": False,
            "cleanup": False,
            "errors": []
        }
    
    async def setup(self) -> bool:
        """Initialize the vector store manager."""
        try:
            print("🔧 VECTOR STORE ISOLATION TEST SETUP")
            print("=" * 50)
            
            # Load configuration
            print("   📋 Loading configuration...")
            config = get_system_config()
            
            if not config.pipeline_config.vector_search:
                raise ValueError("Vector search configuration not found")
            
            # Initialize Vector Store Manager
            print("   🚀 Initializing VectorStoreManager...")
            self.vector_manager = VectorStoreManager(config.pipeline_config.vector_search)
            
            success = await self.vector_manager.initialize()
            if not success:
                raise RuntimeError("Vector store manager initialization failed")
            
            print("   ✅ Vector store manager initialized successfully")
            self.test_results["initialization"] = True
            return True
            
        except Exception as e:
            error_msg = f"Setup failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    def generate_test_data(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate sample test data for vector store testing."""
        print(f"\n📝 GENERATING TEST DATA ({count} samples)")
        print("=" * 50)
        
        test_samples = [
            {
                "text": "Python is a high-level programming language with dynamic semantics and elegant syntax.",
                "metadata": {"source_type": "documentation", "topic": "python", "category": "programming"}
            },
            {
                "text": "Machine learning enables computers to learn patterns from data without explicit programming.",
                "metadata": {"source_type": "article", "topic": "machine_learning", "category": "AI"}
            },
            {
                "text": "Google Cloud Platform provides scalable cloud computing services and infrastructure.",
                "metadata": {"source_type": "marketing", "topic": "cloud", "category": "infrastructure"}
            },
            {
                "text": "Vector databases store high-dimensional embeddings for semantic search and retrieval.",
                "metadata": {"source_type": "technical", "topic": "vectors", "category": "database"}
            },
            {
                "text": "Natural language processing transforms human language into machine-readable formats.",
                "metadata": {"source_type": "research", "topic": "NLP", "category": "AI"}
            }
        ]
        
        # Take only the requested count
        selected_samples = test_samples[:count]
        
        # Generate UUIDs and prepare test data
        for i, sample in enumerate(selected_samples):
            test_uuid = str(uuid.uuid4())
            self.test_data.append({
                "uuid": test_uuid,
                "text": sample["text"],
                "metadata": {
                    **sample["metadata"],
                    "test_index": i,
                    "test_timestamp": datetime.now().isoformat(),
                    "source_identifier": f"test_document_{i}"
                }
            })
            print(f"   📄 Sample {i+1}: {sample['text'][:50]}... (UUID: {test_uuid[:8]}...)")
        
        print(f"   ✅ Generated {len(self.test_data)} test samples")
        return self.test_data
    
    async def test_embedding_generation(self) -> bool:
        """Test embedding generation from text using manager API."""
        try:
            print(f"\n🧠 TESTING EMBEDDING GENERATION")
            print("=" * 50)
            
            # Extract texts from test data
            texts = [item["text"] for item in self.test_data]
            chunk_uuids = [item["uuid"] for item in self.test_data]
            metadata_list = [item["metadata"] for item in self.test_data]
            
            print(f"   🔄 Generating and inserting embeddings for {len(texts)} texts...")
            start_time = datetime.now()
            
            # Generate embeddings and insert using the manager's coordinated API
            result = await self.vector_manager.generate_and_ingest(texts, chunk_uuids, metadata_list)
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            print(f"   📊 Generation and insertion result:")
            print(f"      - Total: {result.total_count}")
            print(f"      - Successful: {result.successful_count}")
            print(f"      - Failed: {result.total_count - result.successful_count}")
            print(f"      - Success rate: {(result.successful_count / result.total_count * 100):.1f}%")
            print(f"   ⏱️  Generation and insertion time: {generation_time:.2f}s")
            
            if result.successful_count == 0:
                raise ValueError("No embeddings were successfully generated and inserted")
            
            if result.error_messages:
                print(f"   ⚠️  Errors during generation:")
                for error in result.error_messages[:3]:  # Show first 3 errors
                    print(f"      - {error}")
            
            print(f"   ✅ Successfully generated and inserted {result.successful_count}/{result.total_count} embeddings")
            
            self.test_results["embedding_generation"] = True
            return True
            
        except Exception as e:
            error_msg = f"Embedding generation failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def test_vector_insertion(self) -> bool:
        """Test separate vector insertion using pre-computed embeddings."""
        try:
            print(f"\n📤 TESTING SEPARATE VECTOR INSERTION")
            print("=" * 50)
            
            # Generate a few additional test vectors to test separate insertion
            additional_texts = [
                "Additional test vector for separate insertion workflow",
                "Another sample text for testing batch vector insertion"
            ]
            
            additional_data = []
            for i, text in enumerate(additional_texts):
                test_uuid = str(uuid.uuid4())
                additional_data.append({
                    "uuid": test_uuid,
                    "text": text,
                    "metadata": {
                        "source_type": "test",
                        "topic": "additional",
                        "category": "insertion_test",
                        "test_index": len(self.test_data) + i
                    }
                })
            
            # Use the manager's embedding generation via ingestor (for testing purposes)
            texts = [item["text"] for item in additional_data]
            print(f"   🔄 Generating embeddings for {len(texts)} additional texts...")
            
            embeddings = await self.vector_manager.ingestor.generate_embeddings(texts)
            
            # Prepare EmbeddingData objects
            embedding_data = []
            for i, item in enumerate(additional_data):
                embedding_data.append(EmbeddingData(
                    chunk_uuid=item["uuid"],
                    embedding=embeddings[i],
                    metadata=item["metadata"]
                ))
            
            print(f"   🔄 Inserting {len(embedding_data)} pre-computed vectors...")
            start_time = datetime.now()
            
            # Insert vectors using the manager's coordinated API
            result = await self.vector_manager.ingest_embeddings(embedding_data)
            
            insertion_time = (datetime.now() - start_time).total_seconds()
            
            print(f"   📊 Insertion result:")
            print(f"      - Total: {result.total_count}")
            print(f"      - Successful: {result.successful_count}")
            print(f"      - Failed: {result.total_count - result.successful_count}")
            print(f"      - Success rate: {(result.successful_count / result.total_count * 100):.1f}%")
            print(f"   ⏱️  Insertion time: {insertion_time:.2f}s")
            
            if result.successful_count == 0:
                raise ValueError("No vectors were successfully inserted")
            
            if result.error_messages:
                print(f"   ⚠️  Errors during insertion:")
                for error in result.error_messages[:3]:  # Show first 3 errors
                    print(f"      - {error}")
            
            print(f"   ✅ Successfully inserted {result.successful_count}/{result.total_count} vectors")
            
            # Add additional data to test data for later retrieval testing
            self.test_data.extend(additional_data)
            
            self.test_results["vector_insertion"] = True
            return True
            
        except Exception as e:
            error_msg = f"Vector insertion failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def test_vector_retrieval(self) -> bool:
        """Test retrieval and search of vectors from the vector store."""
        try:
            print(f"\n📥 TESTING VECTOR RETRIEVAL")
            print("=" * 50)
            
            # Wait a moment for indexing (vector stores have eventual consistency)
            print("   ⏳ Waiting for indexing to complete...")
            await asyncio.sleep(3)
            
            # Test various search queries
            search_queries = [
                "Python programming language",
                "machine learning artificial intelligence",
                "cloud computing services",
                "vector database search",
                "natural language processing"
            ]
            
            successful_searches = 0
            total_results = 0
            
            for i, query in enumerate(search_queries):
                print(f"\n   🔍 Search {i+1}: '{query}'")
                
                try:
                    start_time = datetime.now()
                    
                    # Perform search using manager's coordinated API
                    results = await self.vector_manager.search(
                        query=query,
                        top_k=3,
                        min_similarity=0.0  # Accept any similarity for testing
                    )
                    
                    search_time = (datetime.now() - start_time).total_seconds()
                    
                    print(f"      📊 Found {len(results)} results in {search_time:.3f}s")
                    
                    if results:
                        successful_searches += 1
                        total_results += len(results)
                        
                        # Show top result details
                        top_result = results[0]
                        print(f"      🥇 Top result:")
                        print(f"         - UUID: {str(top_result.chunk_uuid)[:8]}...")
                        print(f"         - Similarity: {top_result.similarity_score:.3f}")
                        
                        # Check if we can find our test UUIDs
                        test_uuids = {item["uuid"] for item in self.test_data}
                        found_test_uuids = {str(r.chunk_uuid) for r in results if str(r.chunk_uuid) in test_uuids}
                        
                        if found_test_uuids:
                            print(f"         - ✅ Found test UUIDs: {len(found_test_uuids)}")
                        else:
                            print(f"         - ⚠️  No test UUIDs found in results")
                    else:
                        print(f"      📭 No results found")
                
                except Exception as search_error:
                    print(f"      ❌ Search failed: {search_error}")
            
            print(f"\n   📊 RETRIEVAL SUMMARY:")
            print(f"      - Successful searches: {successful_searches}/{len(search_queries)}")
            print(f"      - Total results found: {total_results}")
            print(f"      - Average results per search: {total_results/len(search_queries):.1f}")
            
            if successful_searches == 0:
                raise ValueError("No searches returned results")
            
            # Test batch search functionality
            print(f"\n   🔍 Testing batch search...")
            try:
                batch_queries = search_queries[:3]  # Use first 3 queries for batch test
                batch_start = datetime.now()
                
                batch_results = await self.vector_manager.batch_search(
                    queries=batch_queries,
                    top_k=2,
                    min_similarity=0.0
                )
                
                batch_time = (datetime.now() - batch_start).total_seconds()
                
                print(f"      📊 Batch search for {len(batch_queries)} queries completed in {batch_time:.3f}s")
                print(f"      📊 Results per query:")
                
                for query, results in batch_results.items():
                    print(f"         - '{query[:30]}...': {len(results)} results")
                
            except Exception as batch_error:
                print(f"      ⚠️  Batch search test failed: {batch_error}")
            
            # Test specific UUID lookup if possible
            print(f"\n   🎯 Testing specific UUID lookup...")
            try:
                test_uuid = self.test_data[0]["uuid"]
                test_text = self.test_data[0]["text"]
                
                # Search using the exact text content
                uuid_results = await self.vector_manager.search(
                    query=test_text,
                    top_k=5,
                    min_similarity=0.0
                )
                
                found_target = any(str(r.chunk_uuid) == test_uuid for r in uuid_results)
                print(f"      {'✅' if found_target else '❌'} Target UUID {'found' if found_target else 'not found'}")
                
            except Exception as lookup_error:
                print(f"      ⚠️  UUID lookup test failed: {lookup_error}")
            
            self.test_results["vector_retrieval"] = True
            return True
            
        except Exception as e:
            error_msg = f"Vector retrieval failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def cleanup(self) -> bool:
        """Clean up test resources."""
        try:
            print(f"\n🧹 CLEANUP")
            print("=" * 50)
            
            if self.vector_manager:
                print("   🔄 Closing vector store manager...")
                await self.vector_manager.close()
                print("   ✅ Vector store manager closed")
            
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
        print(f"\n📊 VECTOR STORE ISOLATION TEST RESULTS")
        print("=" * 50)
        
        # Calculate overall success
        critical_tests = ["initialization", "embedding_generation", "vector_insertion", "vector_retrieval"]
        passed_tests = sum(1 for test in critical_tests if self.test_results.get(test, False))
        total_tests = len(critical_tests)
        
        success_rate = (passed_tests / total_tests) * 100
        overall_success = success_rate >= 75  # At least 3/4 critical tests must pass
        
        print(f"🎯 OVERALL RESULT: {'✅ PASS' if overall_success else '❌ FAIL'}")
        print(f"📈 Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests} critical tests)")
        
        print(f"\n📋 TEST BREAKDOWN:")
        test_names = {
            "initialization": "Vector Store Initialization",
            "embedding_generation": "Embedding Generation", 
            "vector_insertion": "Vector Insertion",
            "vector_retrieval": "Vector Retrieval",
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
            print("   - Check vector store configuration and credentials")
            print("   - Verify Google Cloud project and permissions")
        elif not self.test_results.get("embedding_generation", False):
            print("   - Check embedding model availability and API access")
            print("   - Verify Vertex AI Text Embedding API is enabled")
        elif not self.test_results.get("vector_insertion", False):
            print("   - Check vector index write permissions")
            print("   - Verify vector index is properly deployed")
            print("   - Check for API rate limiting or quota issues")
        elif not self.test_results.get("vector_retrieval", False):
            print("   - Vector insertion succeeded but retrieval failed")
            print("   - Check for indexing delays (vectors may need time to be searchable)")
            print("   - Verify deployed index configuration")
            print("   - Consider waiting longer for eventual consistency")
        else:
            print("   - All critical vector store operations are working correctly!")
            print("   - The issue may be in the coordination between systems")


async def main():
    """Main function to run the vector store isolation test."""
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
    
    print("Vector Store Isolation Test")
    print("=" * 50)
    
    test = VectorStoreIsolationTest()
    
    try:
        # Run the complete test sequence
        if not await test.setup():
            return False
        
        # Generate test data
        test.generate_test_data(count=5)
        
        # Run ALL tests regardless of individual failures
        # This ensures we get complete diagnostic information
        
        test_results = []
        
        # Run embedding generation test
        test_results.append(await test.test_embedding_generation())
        
        # Run vector insertion test
        test_results.append(await test.test_vector_insertion())
        
        # Run vector retrieval test
        test_results.append(await test.test_vector_retrieval())
        
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
            await asyncio.sleep(0.5)
            import gc
            gc.collect()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1) 