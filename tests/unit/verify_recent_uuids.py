#!/usr/bin/env python3
"""
Script to verify recent UUID generation and vector store indexing.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_ingestion.pipeline.pipeline_manager import PipelineManager
from app.config.configuration import SystemConfig

async def verify_recent_uuids():
    """Verify that recent chunks have proper UUIDs and check vector indexing."""
    print("🔍 VERIFYING RECENT UUID GENERATION AND VECTOR INDEXING")
    print("="*70)
    
    # Initialize pipeline
    config = SystemConfig.from_yaml("config/data_sources_config.yaml")
    pipeline = PipelineManager(config)
    await pipeline.initialize()
    
    try:
        # Get most recent database chunks (last 1 hour)
        print("\n1. CHECKING RECENT DATABASE CHUNKS:")
        recent_time = datetime.now() - timedelta(hours=1)
        
        # Search for very recent github_repo chunks
        recent_chunks = await pipeline.database_manager.search_chunks(
            source_type="github_repo", 
            limit=10
        )
        
        print(f"   Found {len(recent_chunks)} recent github_repo chunks")
        
        recent_uuids = []
        for i, chunk in enumerate(recent_chunks[:5]):
            # Handle timezone-aware datetime
            now = datetime.now(chunk.ingestion_timestamp.tzinfo) if chunk.ingestion_timestamp.tzinfo else datetime.now()
            age = now - chunk.ingestion_timestamp
            print(f"   [{i+1}] UUID: {chunk.chunk_uuid}")
            print(f"       Age: {age}")
            print(f"       Source: {chunk.source_identifier}")
            
            # Validate UUID format
            try:
                from uuid import UUID
                UUID(str(chunk.chunk_uuid))
                print(f"       ✅ Valid UUID format")
                recent_uuids.append(str(chunk.chunk_uuid))
            except ValueError:
                print(f"       ❌ Invalid UUID format")
        
        # Check if these UUIDs appear in vector search results
        if recent_uuids:
            print(f"\n2. CHECKING IF RECENT UUIDs APPEAR IN VECTOR SEARCH:")
            vector_results = await pipeline.vector_store_manager.retriever.retrieve(
                "privacy sandbox analysis tool", 
                top_k=20
            )
            
            print(f"   Vector search returned {len(vector_results)} results")
            vector_uuids = [str(r.chunk_uuid) for r in vector_results if hasattr(r, 'chunk_uuid')]
            
            print(f"   Sample vector UUIDs:")
            for i, uuid_str in enumerate(vector_uuids[:5]):
                try:
                    from uuid import UUID
                    UUID(uuid_str)
                    print(f"   [{i+1}] {uuid_str} ✅")
                except ValueError:
                    print(f"   [{i+1}] {uuid_str} ❌ (malformed)")
            
            # Check overlap
            recent_set = set(recent_uuids)
            vector_set = set(vector_uuids)
            overlap = recent_set.intersection(vector_set)
            
            print(f"\n3. UUID OVERLAP ANALYSIS:")
            print(f"   Recent DB UUIDs: {len(recent_set)}")
            print(f"   Vector UUIDs: {len(vector_set)}")
            print(f"   Overlap: {len(overlap)} UUIDs")
            
            if overlap:
                print(f"   ✅ Found overlap! Recent chunks are in vector store:")
                for uuid_str in list(overlap)[:3]:
                    print(f"      - {uuid_str}")
            else:
                print(f"   ❌ No overlap - recent chunks not in vector search results")
                print(f"   This suggests vector indexing delay or different search terms")
        
        # Check vector index info
        print(f"\n4. VECTOR INDEX INFORMATION:")
        index_info = await pipeline.vector_store_manager.get_index_info()
        print(f"   Vectors count: {index_info.get('vectors_count', 'unknown')}")
        print(f"   Is deployed: {index_info.get('is_deployed', False)}")
        print(f"   Last updated: {index_info.get('updated_time', 'unknown')}")
        
    finally:
        try:
            await pipeline.close()
        except Exception as e:
            print(f"⚠️  Warning during cleanup: {e}")
        print(f"\n✅ Verification complete")

if __name__ == "__main__":
    asyncio.run(verify_recent_uuids()) 