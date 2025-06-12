#!/usr/bin/env python3
"""
Diagnostic script to investigate UUID overlap between storage systems.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_ingestion.pipeline.pipeline_manager import PipelineManager
from app.config.configuration import SystemConfig

async def diagnose_uuid_overlap():
    """Diagnose UUID overlap between storage systems."""
    print("🔍 DIAGNOSING UUID OVERLAP BETWEEN STORAGE SYSTEMS")
    print("="*60)
    
    # Initialize pipeline
    config = SystemConfig.from_yaml("config/data_sources_config.yaml")
    pipeline = PipelineManager(config)
    await pipeline.initialize()
    
    try:
        # Test query
        test_query = "privacy sandbox analysis tool"
        
        print(f"\n📋 Testing with query: '{test_query}'")
        print(f"📅 Current time: {datetime.now()}")
        
        # Get recent data from all systems
        print("\n1. VECTOR STORE DATA:")
        vector_results = await pipeline.vector_store_manager.retriever.retrieve(test_query, top_k=20)
        print(f"   Found {len(vector_results)} vector results")
        vector_uuids = []
        for i, result in enumerate(vector_results[:5]):
            print(f"   [{i+1}] UUID: {result.chunk_uuid} | Similarity: {result.similarity_score:.3f}")
            vector_uuids.append(str(result.chunk_uuid))
        
        # Get recent chunks from database 
        print("\n2. DATABASE DATA:")
        # Get recent chunks (last 2 hours)
        recent_time = datetime.now() - timedelta(hours=2)
        
        # Use database manager to search for github_repo chunks
        db_results = await pipeline.database_manager.search_chunks(source_type="github_repo", limit=20)
        print(f"   Found {len(db_results)} database results (github_repo)")
        db_uuids = []
        for i, result in enumerate(db_results[:5]):
            print(f"   [{i+1}] UUID: {result.chunk_uuid} | Source: {result.source_identifier}")
            print(f"        Timestamp: {result.ingestion_timestamp}")
            db_uuids.append(str(result.chunk_uuid))
        
        print("\n3. KNOWLEDGE GRAPH DATA:")
        kg_entities = await pipeline.knowledge_graph_manager.retriever.get_entities_by_query(test_query, limit=20)
        print(f"   Found {len(kg_entities)} knowledge graph entities")
        kg_chunk_uuids = set()
        for i, entity in enumerate(kg_entities[:5]):
            print(f"   [{i+1}] Entity: {entity.name} | Type: {entity.entity_type}")
            print(f"        Source chunks: {len(entity.source_chunks)} chunks")
            if entity.source_chunks:
                for chunk_uuid in entity.source_chunks[:2]:  # Show first 2
                    print(f"          - {chunk_uuid}")
                    kg_chunk_uuids.add(str(chunk_uuid))
        
        # Analyze overlap
        print("\n4. UUID OVERLAP ANALYSIS:")
        vector_set = set(vector_uuids)
        db_set = set(db_uuids)
        kg_set = kg_chunk_uuids
        
        print(f"   Vector UUIDs sample: {len(vector_set)} unique")
        print(f"   Database UUIDs sample: {len(db_set)} unique") 
        print(f"   Knowledge Graph UUIDs sample: {len(kg_set)} unique")
        
        # Check intersections
        vector_db_intersection = vector_set.intersection(db_set)
        vector_kg_intersection = vector_set.intersection(kg_set)
        db_kg_intersection = db_set.intersection(kg_set)
        
        print(f"\n   Vector ∩ Database: {len(vector_db_intersection)} common UUIDs")
        if vector_db_intersection:
            print(f"      Common UUIDs: {list(vector_db_intersection)[:3]}")
        
        print(f"   Vector ∩ Knowledge Graph: {len(vector_kg_intersection)} common UUIDs")
        if vector_kg_intersection:
            print(f"      Common UUIDs: {list(vector_kg_intersection)[:3]}")
            
        print(f"   Database ∩ Knowledge Graph: {len(db_kg_intersection)} common UUIDs")
        if db_kg_intersection:
            print(f"      Common UUIDs: {list(db_kg_intersection)[:3]}")
        
        # Check if it's a timing issue - look for very recent data
        print("\n5. TIMING ANALYSIS:")
        print("   Checking for very recent ingestions...")
        
        # Get most recent database entries
        recent_db_results = await pipeline.database_manager.search_chunks(limit=10)
        print(f"   Most recent DB entries: {len(recent_db_results)}")
        for result in recent_db_results[:3]:
            time_diff = datetime.now() - result.ingestion_timestamp
            print(f"      UUID: {str(result.chunk_uuid)[:8]}... | Age: {time_diff}")
        
        # Check if recent UUIDs appear in vector store
        if recent_db_results:
            recent_uuid = str(recent_db_results[0].chunk_uuid)
            print(f"\n   Checking if most recent DB UUID appears in vector results...")
            in_vector = recent_uuid in [str(r.chunk_uuid) for r in vector_results]
            print(f"   Recent UUID {recent_uuid[:8]}... in vector results: {in_vector}")
        
    finally:
        # Note: We'll fix the close() method next
        print(f"\n✅ Diagnostic complete")

if __name__ == "__main__":
    asyncio.run(diagnose_uuid_overlap()) 