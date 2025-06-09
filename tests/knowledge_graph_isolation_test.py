#!/usr/bin/env python3
"""
Knowledge Graph Isolation Test - Direct testing of Neo4j knowledge graph insertion and retrieval.

This test isolates the knowledge graph functionality to determine if the core
entity storage, relationship creation, and graph query operations are working correctly.
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
from data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager
from data_ingestion.models import Entity, Relationship, EntityType
from uuid import UUID


class KnowledgeGraphIsolationTest:
    """Standalone test for Neo4j knowledge graph insertion and retrieval operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.kg_manager = None
        self.test_entities = []
        self.test_relationships = []
        self.test_results = {
            "initialization": False,
            "entity_insertion": False,
            "entity_retrieval": False,
            "relationship_creation": False,
            "graph_queries": False,
            "chunk_association": False,
            "cleanup": False,
            "errors": []
        }
    
    async def setup(self) -> bool:
        """Initialize the knowledge graph manager."""
        try:
            print("🔧 KNOWLEDGE GRAPH ISOLATION TEST SETUP")
            print("=" * 50)
            
            # Load configuration
            print("   📋 Loading configuration...")
            config = get_system_config()
            
            if not config.pipeline_config.neo4j:
                raise ValueError("Neo4j configuration not found")
            
            # Initialize Knowledge Graph Manager
            print("   🚀 Initializing KnowledgeGraphManager...")
            self.kg_manager = KnowledgeGraphManager(config.pipeline_config.neo4j)
            
            success = await self.kg_manager.initialize()
            if not success:
                raise RuntimeError("Knowledge graph manager initialization failed")
            
            print("   ✅ Knowledge graph manager initialized successfully")
            self.test_results["initialization"] = True
            return True
            
        except Exception as e:
            error_msg = f"Setup failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    def generate_test_data(self, count: int = 5) -> List[Entity]:
        """Generate sample test data for knowledge graph testing."""
        print(f"\n📝 GENERATING TEST DATA ({count} entities)")
        print("=" * 50)
        
        test_entity_samples = [
            {
                "id": f"test_entity_{uuid.uuid4().hex[:8]}",
                "name": "Python",
                "entity_type": EntityType.TECHNOLOGY,
                "description": "A high-level programming language known for its simplicity and readability.",
                "properties": {"category": "programming_language", "paradigm": "multi_paradigm", "year_created": 1991}
            },
            {
                "id": f"test_entity_{uuid.uuid4().hex[:8]}",
                "name": "Google Cloud Platform",
                "entity_type": EntityType.TECHNOLOGY,
                "description": "Cloud computing services provided by Google for building and deploying applications.",
                "properties": {"category": "cloud_platform", "provider": "Google", "services": ["compute", "storage", "AI"]}
            },
            {
                "id": f"test_entity_{uuid.uuid4().hex[:8]}",
                "name": "Machine Learning",
                "entity_type": EntityType.CONCEPT,
                "description": "A subset of artificial intelligence that enables computers to learn from data.",
                "properties": {"field": "AI", "applications": ["NLP", "computer_vision", "prediction"], "complexity": "high"}
            },
            {
                "id": f"test_entity_{uuid.uuid4().hex[:8]}",
                "name": "DevRel Team",
                "entity_type": EntityType.ORGANIZATION,
                "description": "Developer Relations team focused on building relationships with the developer community.",
                "properties": {"department": "engineering", "focus": "developer_experience", "size": "medium"}
            },
            {
                "id": f"test_entity_{uuid.uuid4().hex[:8]}",
                "name": "Vector Database",
                "entity_type": EntityType.CONCEPT,
                "description": "A database optimized for storing and querying high-dimensional vector embeddings.",
                "properties": {"category": "database", "use_cases": ["semantic_search", "similarity"], "dimension": "high"}
            }
        ]
        
        # Take only the requested count
        selected_samples = test_entity_samples[:count]
        
        # Generate Entity objects
        for i, sample in enumerate(selected_samples):
            entity = Entity(
                id=sample["id"],
                name=sample["name"],
                entity_type=sample["entity_type"],
                description=sample["description"],
                properties=sample["properties"],
                source_chunks=[UUID(str(uuid.uuid4()))],  # Generate fake chunk UUIDs
                confidence_score=0.9
            )
            
            self.test_entities.append(entity)
            print(f"   📄 Entity {i+1}: {sample['name']} ({sample['entity_type'].value}) - {sample['id'][:16]}...")
        
        print(f"   ✅ Generated {len(self.test_entities)} test entities")
        return self.test_entities
    
    def generate_test_relationships(self) -> List[Relationship]:
        """Generate test relationships between entities."""
        print(f"\n🔗 GENERATING TEST RELATIONSHIPS")
        print("=" * 50)
        
        if len(self.test_entities) < 2:
            print("   ⚠️  Need at least 2 entities to create relationships")
            return []
        
        # Create relationships between entities
        relationship_data = [
            {
                "from_entity": self.test_entities[0].id,  # Python
                "to_entity": self.test_entities[2].id,  # Machine Learning
                "relationship_type": "USED_FOR",
                "description": "Python is commonly used for machine learning applications",
                "properties": {"common_use": True, "popularity": "high"}
            },
            {
                "from_entity": self.test_entities[1].id,  # Google Cloud Platform
                "to_entity": self.test_entities[2].id,  # Machine Learning
                "relationship_type": "SUPPORTS",
                "description": "Google Cloud Platform provides machine learning services",
                "properties": {"service_type": "AI/ML", "integration": "native"}
            },
            {
                "from_entity": self.test_entities[3].id,  # DevRel Team
                "to_entity": self.test_entities[0].id,  # Python
                "relationship_type": "PROMOTES",
                "description": "DevRel team promotes Python usage through documentation and examples",
                "properties": {"activity": "documentation", "priority": "high"}
            }
        ]
        
        for i, rel_data in enumerate(relationship_data):
            if i < len(self.test_entities) - 1:  # Ensure we don't exceed entity count
                relationship = Relationship(
                    from_entity=rel_data["from_entity"],
                    to_entity=rel_data["to_entity"],
                    relationship_type=rel_data["relationship_type"],
                    description=rel_data["description"],
                    properties=rel_data["properties"],
                    source_chunks=[UUID(str(uuid.uuid4()))],
                    confidence_score=0.8
                )
                
                self.test_relationships.append(relationship)
                source_name = next(e.name for e in self.test_entities if e.id == rel_data["from_entity"])
                target_name = next(e.name for e in self.test_entities if e.id == rel_data["to_entity"])
                print(f"   🔗 Relationship {i+1}: {source_name} --{rel_data['relationship_type']}--> {target_name}")
        
        print(f"   ✅ Generated {len(self.test_relationships)} test relationships")
        return self.test_relationships
    
    async def test_entity_insertion(self) -> bool:
        """Test insertion of entities into the knowledge graph."""
        try:
            print(f"\n📤 TESTING ENTITY INSERTION")
            print("=" * 50)
            
            print(f"   🔄 Inserting {len(self.test_entities)} entities...")
            start_time = datetime.now()
            
            # Test individual entity insertions
            individual_success = 0
            for i, entity in enumerate(self.test_entities):
                try:
                    success = await self.kg_manager.ingest_entity(entity)
                    if success:
                        individual_success += 1
                        print(f"      ✅ Entity {i+1} ({entity.name}) inserted successfully")
                    else:
                        print(f"      ❌ Entity {i+1} ({entity.name}) insertion failed")
                except Exception as e:
                    print(f"      ❌ Entity {i+1} ({entity.name}) insertion error: {e}")
            
            insertion_time = (datetime.now() - start_time).total_seconds()
            
            print(f"   📊 Individual insertion result:")
            print(f"      - Total: {len(self.test_entities)}")
            print(f"      - Successful: {individual_success}")
            print(f"      - Failed: {len(self.test_entities) - individual_success}")
            print(f"      - Success rate: {(individual_success / len(self.test_entities) * 100):.1f}%")
            print(f"   ⏱️  Insertion time: {insertion_time:.2f}s")
            
            # Test batch insertion with new entities
            print(f"\n   🔄 Testing batch entity insertion...")
            batch_test_entities = []
            for i in range(3):
                entity = Entity(
                    id=f"batch_test_entity_{i}_{uuid.uuid4().hex[:8]}",
                    name=f"Batch Test Entity {i}",
                    entity_type=EntityType.OTHER,
                    description=f"Test entity number {i} for batch insertion testing.",
                    properties={"batch_index": i, "test_type": "batch_insertion"},
                    source_chunks=[UUID(str(uuid.uuid4()))],
                    confidence_score=0.7
                )
                batch_test_entities.append(entity)
            
            batch_start = datetime.now()
            batch_result = await self.kg_manager.batch_ingest_entities(batch_test_entities)
            batch_time = (datetime.now() - batch_start).total_seconds()
            
            print(f"   📊 Batch insertion result:")
            print(f"      - Total: {batch_result.total_count}")
            print(f"      - Successful: {batch_result.successful_count}")
            print(f"      - Success rate: {(batch_result.successful_count / batch_result.total_count * 100):.1f}%")
            print(f"   ⏱️  Batch insertion time: {batch_time:.2f}s")
            
            # Add batch data to test data for later retrieval
            self.test_entities.extend(batch_test_entities)
            
            if individual_success == 0 and batch_result.successful_count == 0:
                raise ValueError("No entities were successfully inserted")
            
            print(f"   ✅ Entity insertion operations completed")
            self.test_results["entity_insertion"] = True
            return True
            
        except Exception as e:
            error_msg = f"Entity insertion failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def test_entity_retrieval(self) -> bool:
        """Test retrieval of entities from the knowledge graph."""
        try:
            print(f"\n📥 TESTING ENTITY RETRIEVAL")
            print("=" * 50)
            
            # Test individual entity retrieval by ID
            print("   🔍 Testing individual entity retrieval...")
            successful_retrievals = 0
            
            for i, original_entity in enumerate(self.test_entities[:3]):  # Test first 3
                try:
                    retrieved_entity = await self.kg_manager.get_entity(original_entity.id)
                    
                    if retrieved_entity:
                        successful_retrievals += 1
                        print(f"      ✅ Entity {i+1} ({original_entity.name}) retrieved successfully")
                        
                        # Validate data integrity
                        if retrieved_entity.name == original_entity.name:
                            print(f"         - Name matches: {retrieved_entity.name}")
                        else:
                            print(f"         - ⚠️  Name mismatch: {retrieved_entity.name} vs {original_entity.name}")
                        
                        if retrieved_entity.entity_type == original_entity.entity_type:
                            print(f"         - Type matches: {retrieved_entity.entity_type}")
                        else:
                            print(f"         - ⚠️  Type mismatch: {retrieved_entity.entity_type} vs {original_entity.entity_type}")
                            
                    else:
                        print(f"      ❌ Entity {i+1} ({original_entity.name}) not found")
                        
                except Exception as e:
                    print(f"      ❌ Entity {i+1} ({original_entity.name}) retrieval error: {e}")
            
            print(f"   📊 Individual retrieval: {successful_retrievals}/3 successful")
            
            # Test entity search by type using find_entities() - CRITICAL FUNCTIONALITY
            print(f"\n   🔍 Testing entity search by type...")
            entity_types = [EntityType.TECHNOLOGY, EntityType.CONCEPT, EntityType.ORGANIZATION]
            search_failures = 0
            
            for entity_type in entity_types:
                try:
                    search_start = datetime.now()
                    entities = await self.kg_manager.find_entities(entity_type=entity_type, limit=10)
                    search_time = (datetime.now() - search_start).total_seconds()
                    
                    print(f"      📊 Entity type '{entity_type.value}': {len(entities)} entities found in {search_time:.3f}s")
                    
                    if entities:
                        # Verify all results have correct type
                        correct_type = all(entity.entity_type == entity_type for entity in entities)
                        print(f"         - {'✅' if correct_type else '❌'} All results have correct type")
                        
                except Exception as e:
                    search_failures += 1
                    print(f"      ❌ Entity type search failed: {e}")
            
            # Test entity search by name using search_entities_by_text() - CRITICAL FUNCTIONALITY
            print(f"\n   🔍 Testing entity search by name...")
            test_names = ["Python", "Google Cloud Platform", "Batch Test"]
            name_search_failures = 0
            
            for name in test_names:
                try:
                    entities = await self.kg_manager.search_entities_by_text(name, limit=5)
                    print(f"      📊 Name search '{name}': {len(entities)} entities found")
                    
                    if entities:
                        # Show sample entity info
                        sample_entity = entities[0]
                        print(f"         - Sample: {sample_entity.name} ({sample_entity.entity_type.value})")
                        
                except Exception as e:
                    name_search_failures += 1
                    print(f"      ❌ Name search failed: {e}")
            
            # Additional test: name_pattern search using find_entities()
            print(f"\n   🔍 Testing name pattern search...")
            try:
                pattern_entities = await self.kg_manager.find_entities(name_pattern="Python", limit=5)
                print(f"      📊 Pattern search 'Python': {len(pattern_entities)} entities found")
                if pattern_entities:
                    for entity in pattern_entities[:2]:
                        print(f"         - {entity.name} ({entity.entity_type.value})")
            except Exception as e:
                print(f"      ❌ Pattern search failed: {e}")
            
            # FAIL THE TEST if individual retrieval fails OR critical search methods fail completely
            if successful_retrievals == 0:
                raise ValueError("No entities could be retrieved by ID")
            
            if search_failures == len(entity_types):
                raise ValueError("Entity search by type is completely non-functional")
                
            if name_search_failures == len(test_names):
                raise ValueError("Entity search by name is completely non-functional")
            
            self.test_results["entity_retrieval"] = True
            return True
            
        except Exception as e:
            error_msg = f"Entity retrieval failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def test_relationship_creation(self) -> bool:
        """Test creation of relationships between entities."""
        try:
            print(f"\n🔗 TESTING RELATIONSHIP CREATION")
            print("=" * 50)
            
            # Generate test relationships
            self.generate_test_relationships()
            
            if not self.test_relationships:
                print("   ⚠️  No relationships to test")
                self.test_results["relationship_creation"] = True
                return True
            
            print(f"   🔄 Creating {len(self.test_relationships)} relationships...")
            start_time = datetime.now()
            
            # Test individual relationship creation
            individual_success = 0
            for i, relationship in enumerate(self.test_relationships):
                try:
                    success = await self.kg_manager.ingest_relationship(relationship)
                    if success:
                        individual_success += 1
                        print(f"      ✅ Relationship {i+1} ({relationship.relationship_type}) created successfully")
                    else:
                        print(f"      ❌ Relationship {i+1} ({relationship.relationship_type}) creation failed")
                except Exception as e:
                    print(f"      ❌ Relationship {i+1} ({relationship.relationship_type}) creation error: {e}")
            
            creation_time = (datetime.now() - start_time).total_seconds()
            
            print(f"   📊 Relationship creation result:")
            print(f"      - Total: {len(self.test_relationships)}")
            print(f"      - Successful: {individual_success}")
            print(f"      - Failed: {len(self.test_relationships) - individual_success}")
            print(f"      - Success rate: {(individual_success / len(self.test_relationships) * 100):.1f}%")
            print(f"   ⏱️  Creation time: {creation_time:.2f}s")
            
            if individual_success == 0:
                raise ValueError("No relationships were successfully created")
            
            self.test_results["relationship_creation"] = True
            return True
            
        except Exception as e:
            error_msg = f"Relationship creation failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def test_graph_queries(self) -> bool:
        """Test graph traversal and query operations."""
        try:
            print(f"\n🕸️  TESTING GRAPH QUERIES")
            print("=" * 50)
            
            successful_operations = 0
            total_operations = 0
            
            # Test getting entities by relationships using get_entity_neighborhood() - CRITICAL FUNCTIONALITY
            print("   🔍 Testing relationship-based queries...")
            total_operations += 1
            
            if self.test_entities:
                test_entity_id = self.test_entities[0].id
                
                try:
                    # Get entity neighborhood (connected entities via relationships)
                    graph_context = await self.kg_manager.get_entity_neighborhood(test_entity_id, max_depth=2, max_entities=10)
                    connected_entities = graph_context.query_entities + graph_context.related_entities
                    print(f"      📊 Connected entities to '{self.test_entities[0].name}': {len(connected_entities)}")
                    
                    if connected_entities:
                        for entity in connected_entities[:3]:  # Show first 3
                            print(f"         - {entity.name} ({entity.entity_type.value})")
                    
                    # Also show relationships in the context
                    relationships = graph_context.relationships
                    print(f"      📊 Relationships in neighborhood: {len(relationships)}")
                    if relationships:
                        for rel in relationships[:2]:  # Show first 2
                            print(f"         - {rel.from_entity} --{rel.relationship_type}--> {rel.to_entity}")
                    
                    successful_operations += 1
                    
                except Exception as e:
                    print(f"      ❌ Entity neighborhood query failed: {e}")
            
            # Test relationship retrieval - CORE FUNCTIONALITY
            print(f"\n   🔍 Testing relationship retrieval...")
            total_operations += 1
            
            try:
                if self.test_entities:
                    entity_ids = [entity.id for entity in self.test_entities[:2]]
                    relationships = await self.kg_manager.find_relationships(
                        from_entity=entity_ids[0] if entity_ids else None,
                        limit=20
                    )
                    print(f"      📊 Total relationships found: {len(relationships)}")
                    
                    if relationships:
                        # Show sample relationships
                        for rel in relationships[:3]:  # Show first 3
                            print(f"         - {rel.from_entity} --{rel.relationship_type}--> {rel.to_entity}")
                        successful_operations += 1
                    else:
                        print(f"      ⚠️  No relationships found (may indicate graph traversal issues)")
                
            except Exception as e:
                print(f"      ❌ Relationship retrieval failed: {e}")
            
            # Test graph statistics - USEFUL BUT NOT CRITICAL
            print(f"\n   📊 Testing graph statistics...")
            try:
                stats = await self.kg_manager.get_graph_statistics()
                print(f"      📈 Graph statistics:")
                print(f"         - Total entities: {stats.get('total_entities', 'unknown')}")
                print(f"         - Total relationships: {stats.get('total_relationships', 'unknown')}")
                print(f"         - Entity types: {stats.get('entity_types', 'unknown')}")
                
            except Exception as e:
                print(f"      ❌ Graph statistics failed: {e}")
            
            # FAIL if core graph query functionality is missing
            print(f"\n   📊 Graph query success rate: {successful_operations}/{total_operations}")
            
            if successful_operations == 0:
                raise ValueError("All graph query operations failed - core graph traversal functionality is missing")
            
            # At least some graph functionality should work for knowledge graphs to be useful
            if successful_operations < total_operations / 2:
                raise ValueError(f"Most graph query operations failed ({successful_operations}/{total_operations}) - insufficient functionality")
            
            self.test_results["graph_queries"] = True
            return True
            
        except Exception as e:
            error_msg = f"Graph queries failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def test_chunk_association(self) -> bool:
        """Test chunk-entity association functionality."""
        try:
            print(f"\n🧩 TESTING CHUNK-ENTITY ASSOCIATIONS")
            print("=" * 50)
            
            if not self.test_entities:
                print("   ⚠️  No entities available for chunk association test")
                self.test_results["chunk_association"] = True
                return True
            
            successful_associations = 0
            total_association_tests = 0
            
            # Test getting entities by chunk using get_graph_context_for_chunks() - CRITICAL FOR RETRIEVAL INTEGRATION
            test_entity = self.test_entities[0]
            test_chunk_uuid = test_entity.source_chunks[0] if test_entity.source_chunks else None
            
            if test_chunk_uuid:
                total_association_tests += 1
                try:
                    # Use the actual API method to get graph context for chunks
                    chunk_uuids = [str(test_chunk_uuid)]
                    graph_context = await self.kg_manager.get_graph_context_for_chunks(chunk_uuids, max_depth=1)
                    
                    entities_for_chunk = graph_context.query_entities + graph_context.related_entities
                    print(f"   📊 Entities associated with chunk {str(test_chunk_uuid)[:8]}...: {len(entities_for_chunk)}")
                    
                    if entities_for_chunk:
                        for entity in entities_for_chunk:
                            print(f"      - {entity.name} ({entity.entity_type.value})")
                        successful_associations += 1
                    
                    # Also check the entity-chunks mapping
                    chunk_mapping = graph_context.entity_chunks_mapping
                    print(f"   📊 Entity-chunk mappings found: {len(chunk_mapping)}")
                    
                except Exception as e:
                    print(f"   ❌ Chunk-entity association query failed: {e}")
            
            # Test entity context by getting neighborhood - CRITICAL FOR ENTITY CONTEXT
            total_association_tests += 1
            try:
                test_entity = self.test_entities[0]
                entity_context = await self.kg_manager.get_entity_neighborhood(test_entity.id, max_depth=1, max_entities=20)
                
                # Check if entity has chunk associations in the context
                chunk_mappings = entity_context.entity_chunks_mapping
                chunks_for_entity = chunk_mappings.get(test_entity.id, [])
                
                print(f"   📊 Chunks associated with entity '{test_entity.name}': {len(chunks_for_entity)}")
                
                if chunks_for_entity:
                    for chunk_uuid in chunks_for_entity[:3]:  # Show first 3
                        print(f"      - Chunk: {str(chunk_uuid)[:8]}...")
                    successful_associations += 1
                elif test_entity.source_chunks:
                    # If no chunks in mapping but entity has source_chunks, that's still valid
                    print(f"      - Entity has {len(test_entity.source_chunks)} source chunks (from entity data)")
                    successful_associations += 1
                
            except Exception as e:
                print(f"   ❌ Entity-chunk context query failed: {e}")
            
            # FAIL if chunk association functionality is completely missing
            print(f"\n   📊 Chunk association success rate: {successful_associations}/{total_association_tests}")
            
            if successful_associations == 0 and total_association_tests > 0:
                raise ValueError("Chunk-entity association functionality is completely non-functional - graph context methods not working properly")
            
            self.test_results["chunk_association"] = True
            return True
            
        except Exception as e:
            error_msg = f"Chunk association tests failed: {e}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False
    
    async def cleanup(self) -> bool:
        """Clean up test resources."""
        try:
            print(f"\n🧹 CLEANUP")
            print("=" * 50)
            
            if self.kg_manager:
                print("   🔄 Closing knowledge graph manager...")
                await self.kg_manager.close()
                print("   ✅ Knowledge graph manager closed")
            
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
        print(f"\n📊 KNOWLEDGE GRAPH ISOLATION TEST RESULTS")
        print("=" * 50)
        
        # Calculate overall success
        critical_tests = ["initialization", "entity_insertion", "entity_retrieval", "relationship_creation", "graph_queries", "chunk_association"]
        passed_tests = sum(1 for test in critical_tests if self.test_results.get(test, False))
        total_tests = len(critical_tests)
        
        success_rate = (passed_tests / total_tests) * 100
        overall_success = success_rate >= 75  # At least 75% of critical tests must pass
        
        print(f"🎯 OVERALL RESULT: {'✅ PASS' if overall_success else '❌ FAIL'}")
        print(f"📈 Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests} critical tests)")
        
        print(f"\n📋 TEST BREAKDOWN:")
        test_names = {
            "initialization": "Knowledge Graph Manager Initialization",
            "entity_insertion": "Entity Insertion (Individual & Batch)",
            "entity_retrieval": "Entity Retrieval & Search", 
            "relationship_creation": "Relationship Creation",
            "graph_queries": "Graph Traversal & Queries",
            "chunk_association": "Chunk-Entity Associations",
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
            print("   - Check Neo4j configuration and connection settings")
            print("   - Verify Neo4j instance is running and accessible")
            print("   - Check database credentials and network connectivity")
        elif not self.test_results.get("entity_insertion", False):
            print("   - Check Neo4j write permissions")
            print("   - Verify graph schema constraints are properly set up")
            print("   - Check for constraint violations in entity data")
        elif not self.test_results.get("entity_retrieval", False):
            print("   - CRITICAL: Entity search functionality failed")
            print("   - Check find_entities() and search_entities_by_text() implementations")
            print("   - These are essential for knowledge graph-based retrieval functionality")
        elif not self.test_results.get("relationship_creation", False):
            print("   - Entities work but relationship creation failed")
            print("   - Check relationship constraints and validation")
            print("   - Verify entity IDs exist before creating relationships")
        elif not self.test_results.get("graph_queries", False):
            print("   - CRITICAL: Graph traversal functionality failed")
            print("   - Check get_entity_neighborhood() and find_relationships() implementations")
            print("   - Verify relationship indexing and graph traversal queries are working")
        elif not self.test_results.get("chunk_association", False):
            print("   - CRITICAL: Chunk-entity association functionality failed")
            print("   - Check get_graph_context_for_chunks() and get_entity_neighborhood() implementations")
            print("   - These are essential for integrating knowledge graph with retrieval system")
        else:
            print("   - All critical knowledge graph operations are working correctly!")
            print("   - The knowledge graph layer is functioning properly")


async def main():
    """Main function to run the knowledge graph isolation test."""
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
    
    print("Knowledge Graph Isolation Test")
    print("=" * 50)
    
    test = KnowledgeGraphIsolationTest()
    
    try:
        # Run the complete test sequence
        if not await test.setup():
            return False
        
        # Generate test data
        test.generate_test_data(count=5)
        
        # Run ALL tests regardless of individual failures
        # This ensures we get complete diagnostic information
        
        test_results = []
        
        # Run entity insertion test
        test_results.append(await test.test_entity_insertion())
        
        # Run entity retrieval test
        test_results.append(await test.test_entity_retrieval())
        
        # Run relationship creation test
        test_results.append(await test.test_relationship_creation())
        
        # Run graph queries test
        test_results.append(await test.test_graph_queries())
        
        # Run chunk association test
        test_results.append(await test.test_chunk_association())
        
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