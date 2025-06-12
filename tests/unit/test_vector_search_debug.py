#!/usr/bin/env python3
import asyncio
from app.data_ingestion.pipeline.pipeline_manager import PipelineManager
from app.config.configuration import SystemConfig

async def debug_vector_search():
    """Debug why vector search returns wrong content for Drive file query."""
    
    # Initialize pipeline manager and get vector manager from it
    config = SystemConfig.from_yaml('config/data_sources_config.yaml')
    pipeline_manager = PipelineManager(config)
    await pipeline_manager.initialize()
    
    vector_manager = pipeline_manager.vector_store_manager
    db_manager = pipeline_manager.database_manager
    
    print("🔍 Debugging Vector Search for Drive File Content")
    print("=" * 60)
    
    # Test the exact query used in the test
    query = "DevRel guidance assistance development"
    print(f"Query: '{query}'")
    print()
    
    # Get vector search results
    vector_results = await vector_manager.search(query, top_k=5)
    
    print(f"Vector Search returned {len(vector_results)} results:")
    print("-" * 40)
    
    for i, result in enumerate(vector_results):
        print(f"Result {i+1}:")
        print(f"  UUID: {result.chunk_uuid}")
        print(f"  Similarity: {result.similarity_score:.3f}")
        
        # Get the actual chunk data
        chunk_data = await db_manager.get_chunk(str(result.chunk_uuid))
        
        if chunk_data:
            print(f"  Source Type: {chunk_data.source_type.value}")
            print(f"  Source ID: {chunk_data.source_identifier}")
            content = chunk_data.chunk_text_summary[:150] if chunk_data.chunk_text_summary else "No content"
            print(f"  Content: {content}...")
            
            # Check if this is the Drive file we expect
            if chunk_data.source_type.value == 'drive_file':
                print("  🎯 THIS IS THE DRIVE FILE!")
            else:
                print(f"  ❌ Wrong source type: {chunk_data.source_type.value}")
        else:
            print("  ❌ Could not retrieve chunk data")
        
        print()
    
    # Check if any Drive file content appears in top results
    drive_file_found = False
    for result in vector_results:
        chunk_data = await db_manager.get_chunk(str(result.chunk_uuid))
        if chunk_data and chunk_data.source_type.value == 'drive_file':
            drive_file_found = True
            break
    
    if not drive_file_found:
        print("🚨 ISSUE IDENTIFIED: Drive file content NOT in top 5 vector search results!")
        print()
        print("Possible causes:")
        print("1. Vector indexing delay - new content not yet indexed")
        print("2. Poor vector embedding similarity")
        print("3. Vector store sync issues")
        print()
        
        # Check if vector store has indexed recent content
        print("Checking if vector store is up to date...")
        # This would require checking vector store directly, which might be complex
    else:
        print("✅ Drive file content found in vector search results!")
    
    await pipeline_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(debug_vector_search()) 