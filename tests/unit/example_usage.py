#!/usr/bin/env python3
"""
Example usage of the data processing and retrieval system.
Demonstrates the complete pipeline from configuration to data ingestion and retrieval.
"""

import asyncio
import logging
from pathlib import Path

from app.config.configuration import get_system_config
from data_ingestion.pipeline.pipeline_manager import PipelineManager, SyncMode
from data_ingestion.managers.vector_store_manager import VectorStoreManager
from data_ingestion.managers.database_manager import DatabaseManager
from data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main example demonstrating the data processing pipeline."""
    
    try:
        logger.info("Starting data processing pipeline example")
        
        # 1. Load Configuration
        logger.info("Loading system configuration...")
        config = get_system_config()
        
        # Validate configuration
        from config.configuration import get_config_manager
        config_manager = get_config_manager()
        issues = config_manager.validate_config()
        
        if issues:
            logger.warning("Configuration issues found:")
            for issue in issues:
                logger.warning(f"  - {issue}")
        
        # 2. Initialize Pipeline Manager
        logger.info("Initializing pipeline manager...")
        pipeline = PipelineManager(config)
        await pipeline.initialize()
        
        # 3. Perform Health Check
        logger.info("Performing system health check...")
        health_result = await pipeline.health_check()
        
        if health_result.overall_status:
            logger.info("✅ All systems healthy")
        else:
            logger.warning("⚠️  Some systems are unhealthy:")
            for issue in health_result.issues:
                logger.warning(f"  - {issue}")
        
        # 4. Run Pipeline for Specific Sources (optional)
        logger.info("Running pipeline for all enabled sources...")
        
        # You can specify specific sources if needed:
        # specific_sources = ["ps-analysis-tool", "devrel-assistance-folder"]
        # stats = await pipeline.run_pipeline(source_ids=specific_sources, sync_mode=SyncMode.FULL_SYNC)
        
        stats = await pipeline.run_pipeline(sync_mode=SyncMode.SMART_SYNC)
        
        # 5. Display Results
        logger.info("Pipeline execution completed!")
        logger.info(f"Processing time: {stats.processing_time:.2f} seconds")
        logger.info(f"Documents processed: {stats.successful_documents}/{stats.total_documents}")
        logger.info(f"Chunks created: {stats.successful_chunks}/{stats.total_chunks}")
        
        if stats.errors:
            logger.warning("Errors encountered:")
            for error in stats.errors[:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")
        
        # 6. Get Pipeline Statistics
        logger.info("Getting pipeline statistics...")
        pipeline_stats = await pipeline.get_pipeline_stats()
        
        logger.info("System Statistics:")
        logger.info(f"  - Enabled sources: {pipeline_stats['enabled_sources']}")
        logger.info(f"  - Components active: {sum(1 for v in pipeline_stats['components'].values() if v)}")
        
        if 'database_stats' in pipeline_stats:
            db_stats = pipeline_stats['database_stats']
            logger.info(f"  - Total chunks in database: {db_stats.get('total_chunks', 0)}")
        
        if 'knowledge_graph_stats' in pipeline_stats:
            kg_stats = pipeline_stats['knowledge_graph_stats']
            logger.info(f"  - Entities in knowledge graph: {kg_stats.get('total_entities', 0)}")
        
        # 7. Example: Query the System
        await demonstrate_retrieval(pipeline)
        
        # 8. Cleanup
        await pipeline.cleanup()
        logger.info("Example completed successfully!")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise

async def demonstrate_retrieval(pipeline: PipelineManager):
    """Demonstrate data retrieval capabilities."""
    logger.info("Demonstrating retrieval capabilities...")
    
    try:
        # Example 1: Database Queries
        if pipeline.database_manager:
            logger.info("Querying database for recent chunks...")
            
            # Search for chunks from a specific source
            chunks = await pipeline.database_manager.search_chunks(
                source_type="github_repo",
                limit=5
            )
            
            logger.info(f"Found {len(chunks)} chunks from GitHub sources")
            for chunk in chunks[:3]:  # Show first 3
                logger.info(f"  - {chunk.chunk_uuid}: {chunk.chunk_text_summary[:100]}...")
        
        # Example 2: Vector Search (if configured)
        if pipeline.vector_store_manager:
            logger.info("Demonstrating vector search...")
            
            # Generate embedding for query
            query_text = "What is Privacy Sandbox?"
            query_embeddings = await pipeline.vector_store_manager.generate_embeddings([query_text])
            
            if query_embeddings:
                # Perform similarity search
                results = await pipeline.vector_store_manager.search_similar(
                    query_embedding=query_embeddings[0],
                    num_neighbors=5
                )
                
                logger.info(f"Found {len(results)} similar chunks for query: '{query_text}'")
                for result in results[:3]:
                    logger.info(f"  - {result.chunk_uuid} (score: {result.similarity_score:.3f})")
        
        # Example 3: Knowledge Graph Queries (if enabled)
        if pipeline.knowledge_graph_manager:
            logger.info("Querying knowledge graph...")
            
            # Find entities of specific types
            entities = await pipeline.knowledge_graph_manager.find_entities(
                entity_type="ORG",  # Organizations
                limit=10
            )
            
            logger.info(f"Found {len(entities)} organization entities")
            for entity in entities[:3]:
                logger.info(f"  - {entity.name} (ID: {entity.id})")
    
    except Exception as e:
        logger.warning(f"Retrieval demonstration failed: {e}")

async def demonstrate_individual_components():
    """Demonstrate using individual components separately."""
    logger.info("Demonstrating individual component usage...")
    
    # Example: Using TextProcessor standalone
    from data_ingestion.processors.text_processor import TextProcessor
    
    processor = TextProcessor(chunk_size=500, chunk_overlap=50)
    
    sample_document = {
        'content': """
        Privacy Sandbox is Google's initiative to develop web technologies that protect user privacy 
        while enabling digital businesses to build and sustain their business models. The Privacy Sandbox 
        aims to phase out support for third-party cookies and limit covert tracking, while developing 
        new tools to deliver relevant ads and measure their effectiveness.
        
        Key technologies include:
        - Topics API for interest-based advertising
        - FLEDGE for remarketing and custom audiences  
        - Trust Tokens for fraud prevention
        - Attribution Reporting API for conversion measurement
        """,
        'title': 'Privacy Sandbox Overview',
        'source_id': 'example-source',
        'document_id': 'example-doc-1',
        'metadata': {'type': 'documentation', 'category': 'privacy'}
    }
    
    processed = await processor.process_document(sample_document)
    
    logger.info(f"Text processor created {processed.total_chunks} chunks")
    logger.info(f"Processing took {processed.processing_stats['processing_time']:.3f} seconds")
    
    for i, chunk in enumerate(processed.chunks[:2]):  # Show first 2 chunks
        logger.info(f"  Chunk {i+1}: {chunk.text[:100]}...")
        if chunk.entities:
            logger.info(f"    Entities found: {[e.name for e in chunk.entities[:3]]}")

if __name__ == "__main__":
    # You can run either the full pipeline example or individual components
    
    print("Data Processing Pipeline Example")
    print("================================")
    print()
    print("This example demonstrates:")
    print("1. Loading configuration from config/data_sources_config.yaml")
    print("2. Initializing all pipeline components")
    print("3. Running health checks")
    print("4. Processing documents from configured sources")
    print("5. Storing data in Vector Search, PostgreSQL, and Neo4j")
    print("6. Demonstrating retrieval capabilities")
    print()
    
    choice = input("Run [F]ull pipeline example or [I]ndividual components demo? (F/I): ").upper()
    
    if choice == "I":
        asyncio.run(demonstrate_individual_components())
    else:
        asyncio.run(main()) 