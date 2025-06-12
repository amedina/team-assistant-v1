"""
Pipeline Manager - Central control unit for data processing pipeline.
Orchestrates data flow from connectors through processors to storage systems.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.config.configuration import SystemConfig, get_system_config
from app.data_ingestion.managers.vector_store_manager import VectorStoreManager
from app.data_ingestion.managers.database_manager import DatabaseManager
from app.data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager
from app.data_ingestion.processors.text_processor import TextProcessor
from app.data_ingestion.connectors.base_connector import BaseConnector, SourceDocument
from app.data_ingestion.models import (
    EmbeddingData, ChunkData, Entity, Relationship, 
    ComponentHealth, SystemHealth, IngestionStatus
)

logger = logging.getLogger(__name__)

class SyncMode(Enum):
    """Pipeline sync modes."""
    FULL_SYNC = "full_sync"
    INCREMENTAL_SYNC = "incremental_sync"
    SMART_SYNC = "smart_sync"

@dataclass
class PipelineStats:
    """Pipeline execution statistics."""
    start_time: datetime
    end_time: Optional[datetime]
    total_documents: int
    successful_documents: int
    failed_documents: int
    total_chunks: int
    successful_chunks: int
    errors: List[str]
    processing_time: float = 0.0
    sources_processed: List[str] = None
    total_entities: int = 0
    total_relationships: int = 0
    processing_times: Dict[str, float] = None
    
    def __post_init__(self):
        if self.sources_processed is None:
            self.sources_processed = []
        if self.processing_times is None:
            self.processing_times = {}
    
    @property
    def duration(self) -> float:
        """Calculate duration from start and end time."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

class PipelineManager:
    """
    Central control unit for the data processing pipeline.
    
    Responsibilities:
    - Orchestrating end-to-end pipeline execution
    - Managing configuration and component initialization
    - Handling different sync modes
    - Providing health checks and statistics
    - Managing concurrent processing with rate limiting
    """
    
    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or get_system_config()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize managers
        self.vector_store_manager: Optional[VectorStoreManager] = None
        self.database_manager: Optional[DatabaseManager] = None
        self.knowledge_graph_manager: Optional[KnowledgeGraphManager] = None
        self.text_processor: Optional[TextProcessor] = None
        
        # Pipeline state
        self._initialized = False
        self._running = False
        
    async def initialize(self):
        """Initialize all pipeline components."""
        try:
            self.logger.info("Initializing pipeline components...")
            
            # Initialize text processor
            self.text_processor = TextProcessor(
                chunk_size=self.config.pipeline_config.chunk_size,
                chunk_overlap=self.config.pipeline_config.chunk_overlap,
                enable_entity_extraction=self.config.pipeline_config.enable_knowledge_graph
            )
            
            # Initialize vector store manager with coordinator pattern
            if self.config.pipeline_config.vector_search:
                self.vector_store_manager = VectorStoreManager(
                    self.config.pipeline_config.vector_search
                )
                await self.vector_store_manager.initialize()
            
            # Initialize database manager with coordinator pattern
            if self.config.pipeline_config.database:
                self.database_manager = DatabaseManager(
                    self.config.pipeline_config.database
                )
                await self.database_manager.initialize()
            
            # Initialize knowledge graph manager with coordinator pattern
            if (self.config.pipeline_config.enable_knowledge_graph and 
                self.config.pipeline_config.neo4j):
                self.knowledge_graph_manager = KnowledgeGraphManager(
                    self.config.pipeline_config.neo4j
                )
                await self.knowledge_graph_manager.initialize()
            
            self._initialized = True
            self.logger.info("Pipeline components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize pipeline: {e}")
            raise
    
    async def run_pipeline(self, 
                         source_ids: Optional[List[str]] = None,
                         sync_mode: SyncMode = SyncMode.SMART_SYNC,
                         limit: Optional[int] = None) -> PipelineStats:
        """
        Run the complete data processing pipeline.
        
        Args:
            source_ids: List of source IDs to process (None for all enabled sources)
            sync_mode: Synchronization mode to use
            limit: Maximum number of documents to process (None for no limit)
            
        Returns:
            Pipeline execution statistics
        """
        if not self._initialized:
            await self.initialize()
        
        self._running = True
        stats = PipelineStats(
            start_time=datetime.now(),
            end_time=None,
            total_documents=0,
            successful_documents=0,
            failed_documents=0,
            total_chunks=0,
            successful_chunks=0,
            errors=[]
        )
        
        try:
            # Clean progress message (shows even in quiet mode)
            print(f"🚀 Starting pipeline execution with mode: {sync_mode.value}")
            self.logger.info(f"Starting pipeline execution with mode: {sync_mode.value}")
            
            # Get data sources to process
            sources_to_process = self._get_sources_to_process(source_ids)
            
            if not sources_to_process:
                print("⚠️  No data sources to process")
                self.logger.warning("No data sources to process")
                return stats
            
            print(f"📊 Processing {len(sources_to_process)} data source(s)...")
            
            # Process each data source
            semaphore = asyncio.Semaphore(self.config.pipeline_config.max_concurrent_jobs)
            
            tasks = []
            for source_config in sources_to_process:
                task = self._process_data_source(source_config, sync_mode, stats, semaphore, limit)
                tasks.append(task)
            
            # Execute all source processing tasks concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
            
            stats.end_time = datetime.now()
            stats.processing_time = (stats.end_time - stats.start_time).total_seconds()
            
            # Clean completion message (shows even in quiet mode)
            print(f"✅ Pipeline execution completed in {stats.processing_time:.1f}s")
            self.logger.info(
                f"Pipeline execution completed: "
                f"{stats.successful_documents}/{stats.total_documents} documents, "
                f"{stats.successful_chunks} chunks in {stats.processing_time:.2f}s"
            )
            
        except Exception as e:
            error_msg = f"Pipeline execution failed: {e}"
            self.logger.error(error_msg)
            stats.errors.append(error_msg)
        
        finally:
            self._running = False
        
        return stats
    
    def _get_sources_to_process(self, source_ids: Optional[List[str]]) -> List:
        """Get list of data source configurations to process."""
        enabled_sources = self.config.get_enabled_sources()
        
        if source_ids:
            # Filter by specified source IDs
            return [
                source for source in enabled_sources 
                if source.source_id in source_ids
            ]
        else:
            # Process all enabled sources
            return enabled_sources
    
    async def _process_data_source(self, 
                                 source_config,
                                 sync_mode: SyncMode,
                                 stats: PipelineStats,
                                 semaphore: asyncio.Semaphore,
                                 limit: Optional[int] = None):
        """Process documents from a single data source."""
        async with semaphore:
            try:
                # Clean progress message (shows even in quiet mode)
                print(f"  📁 Processing: {source_config.source_id}")
                self.logger.info(f"Processing data source: {source_config.source_id}")
                
                # Create connector for this source
                connector = await self._create_connector(source_config)
                if not connector:
                    error_msg = f"Failed to create connector for {source_config.source_id}"
                    print(f"    ❌ {error_msg}")
                    stats.errors.append(error_msg)
                    return
                
                # Connect to data source
                await connector.connect()
                
                # Determine last sync time based on sync mode
                last_sync = await self._get_last_sync_time(source_config.source_id, sync_mode)
                
                # Fetch and process documents
                document_count = 0
                async for document in connector.fetch_documents(last_sync=last_sync):
                    # Check if we've reached the limit
                    if limit and document_count >= limit:
                        print(f"    📊 Reached document limit ({limit}) for {source_config.source_id}")
                        self.logger.info(f"Reached document limit ({limit}) for source {source_config.source_id}")
                        break
                        
                    document_count += 1
                    stats.total_documents += 1
                    
                    try:
                        # Process document
                        processed_doc = await self.text_processor.process_document(
                            document.to_dict()
                        )
                        
                        if processed_doc.chunks:
                            # Store processed chunks
                            await self._store_processed_document(processed_doc, stats)
                            stats.successful_documents += 1
                        else:
                            self.logger.warning(f"No chunks created for document {document.document_id}")
                            stats.failed_documents += 1
                            
                    except Exception as e:
                        error_msg = f"Failed to process document {document.document_id}: {e}"
                        self.logger.error(error_msg)
                        stats.errors.append(error_msg)
                        stats.failed_documents += 1
                
                await connector.disconnect()
                print(f"    ✅ Completed: {document_count} documents from {source_config.source_id}")
                self.logger.info(f"Completed processing {document_count} documents from {source_config.source_id}")
                
            except Exception as e:
                error_msg = f"Failed to process data source {source_config.source_id}: {e}"
                print(f"    ❌ Error: {error_msg}")
                self.logger.error(error_msg)
                stats.errors.append(error_msg)
    
    async def _create_connector(self, source_config) -> Optional[BaseConnector]:
        """Create appropriate connector for the data source."""
        try:
            if source_config.source_type == "github_repo":
                from app.data_ingestion.connectors.github_connector import GitHubConnector
                return GitHubConnector(source_config.__dict__)
            elif source_config.source_type == "drive_folder":
                from data_ingestion.connectors.drive_connector import DriveConnector
                return DriveConnector(source_config.__dict__)
            elif source_config.source_type == "drive_file":
                from data_ingestion.connectors.drive_connector import DriveConnector
                return DriveConnector(source_config.__dict__)
            elif source_config.source_type == "web_source":
                from data_ingestion.connectors.web_connector import WebConnector
                return WebConnector(source_config.__dict__)
            else:
                self.logger.error(f"Unknown source type: {source_config.source_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create connector for {source_config.source_id}: {e}")
            return None
    
    async def _get_last_sync_time(self, source_id: str, sync_mode: SyncMode) -> Optional[datetime]:
        """Get last sync time based on sync mode."""
        if sync_mode == SyncMode.FULL_SYNC:
            return None
        elif sync_mode == SyncMode.INCREMENTAL_SYNC:
            # Query database for last successful sync
            # Placeholder implementation
            return None
        elif sync_mode == SyncMode.SMART_SYNC:
            # Smart logic to determine optimal sync point
            # Placeholder implementation
            return None
        return None
    
    async def _store_processed_document(self, processed_doc, stats: PipelineStats):
        """Store processed document chunks in all configured storage systems using coordinator pattern."""
        try:
            # Prepare data for storage using centralized models
            chunk_data_list = []
            embedding_data = []
            entities = []
            relationships = []
            
            for chunk in processed_doc.chunks:
                stats.total_chunks += 1
                
                # Prepare ChunkData using centralized model
                chunk_data = ChunkData(
                    chunk_uuid=chunk.chunk_uuid,
                    source_type=chunk.metadata.get('source_type', ''),
                    source_identifier=chunk.metadata.get('source_identifier', ''),
                    chunk_text_summary=chunk.metadata.get('text_summary', ''),
                    chunk_metadata=chunk.metadata,
                    ingestion_timestamp=datetime.now(),
                    source_last_modified_at=chunk.metadata.get('last_modified'),
                    source_content_hash=chunk.metadata.get('content_hash'),
                    last_indexed_at=datetime.now(),
                    ingestion_status=IngestionStatus.COMPLETED
                )
                chunk_data_list.append(chunk_data)
                
                # Collect entities and relationships for knowledge graph
                if chunk.entities:
                    entities.extend(chunk.entities)
                if chunk.relationships:
                    relationships.extend(chunk.relationships)
            
            # Track success for each storage system
            database_success_count = 0
            vector_store_success = True
            knowledge_graph_success = True
            
            # Store in database using coordinator pattern
            if self.database_manager and chunk_data_list:
                database_success_count, total_count = await self.database_manager.batch_ingest_chunks(chunk_data_list)
                
                # Track database failures as errors
                failed_count = total_count - database_success_count
                if failed_count > 0:
                    error_msg = f"Failed to store {failed_count}/{total_count} chunks in database"
                    self.logger.error(error_msg)
                    stats.errors.append(error_msg)
            else:
                # If no database manager, assume all chunks "succeed" for database
                database_success_count = len(processed_doc.chunks)
            
            # Generate and store embeddings using coordinator pattern
            if self.vector_store_manager and chunk_data_list:
                try:
                    # Extract text for embedding generation
                    texts = [chunk.text for chunk in processed_doc.chunks]
                    chunk_uuids = [str(chunk.chunk_uuid) for chunk in processed_doc.chunks]
                    metadata_list = [chunk.chunk_metadata for chunk in chunk_data_list]
                    
                    # Use coordinator method for generation and storage
                    result = await self.vector_store_manager.generate_and_ingest(texts, chunk_uuids, metadata_list)
                    
                    if result.successful_count != len(texts):
                        vector_store_success = False
                        failed_count = len(texts) - result.successful_count
                        error_msg = f"Failed to store {failed_count}/{len(texts)} embeddings in vector store"
                        self.logger.error(error_msg)
                        stats.errors.append(error_msg)
                        
                except Exception as e:
                    vector_store_success = False
                    error_msg = f"Vector store operation failed: {e}"
                    self.logger.error(error_msg)
                    stats.errors.append(error_msg)
            
            # Store in knowledge graph using coordinator pattern
            if (self.knowledge_graph_manager and 
                self.config.pipeline_config.enable_knowledge_graph and
                (entities or relationships)):
                
                try:
                    if entities:
                        result = await self.knowledge_graph_manager.batch_ingest_entities(entities)
                        # Update entity statistics
                        stats.total_entities += result.successful_count
                        
                        failed_entities = result.total_count - result.successful_count
                        if failed_entities > 0:
                            knowledge_graph_success = False
                            error_msg = f"Failed to store {failed_entities}/{result.total_count} entities in knowledge graph"
                            self.logger.error(error_msg)
                            stats.errors.append(error_msg)
                    
                    if relationships:
                        result = await self.knowledge_graph_manager.batch_ingest_relationships(relationships)
                        # Update relationship statistics
                        stats.total_relationships += result.successful_count
                        
                        failed_relationships = result.total_count - result.successful_count
                        if failed_relationships > 0:
                            knowledge_graph_success = False
                            error_msg = f"Failed to store {failed_relationships}/{result.total_count} relationships in knowledge graph"
                            self.logger.error(error_msg)
                            stats.errors.append(error_msg)
                        
                except Exception as e:
                    knowledge_graph_success = False
                    error_msg = f"Knowledge graph operation failed: {e}"
                    self.logger.error(error_msg)
                    stats.errors.append(error_msg)
            
            # Only count chunks as successful if ALL required storage systems succeeded
            if (database_success_count > 0 and vector_store_success and knowledge_graph_success):
                # All systems succeeded - count the minimum success across systems
                stats.successful_chunks += min(database_success_count, len(processed_doc.chunks))
            elif database_success_count > 0 and not self.vector_store_manager:
                # No vector store required, just database + KG
                if knowledge_graph_success:
                    stats.successful_chunks += database_success_count
            elif database_success_count > 0 and not self.config.pipeline_config.enable_knowledge_graph:
                # No KG required, just database + vector store
                if vector_store_success:
                    stats.successful_chunks += database_success_count
            # If any required system failed, successful_chunks remains unchanged (0 added)
            
        except Exception as e:
            error_msg = f"Failed to store processed document {processed_doc.document_id}: {e}"
            self.logger.error(error_msg)
            stats.errors.append(error_msg)
    
    async def health_check(self) -> SystemHealth:
        """Perform comprehensive health check of all components using coordinator pattern."""
        # Individual component health checks
        vector_store_health = ComponentHealth(component_name="VectorStore", is_healthy=True)
        database_health = ComponentHealth(component_name="Database", is_healthy=True)
        knowledge_graph_health = ComponentHealth(component_name="KnowledgeGraph", is_healthy=True)
        
        try:
            # Check vector store using coordinator pattern
            if self.vector_store_manager:
                vector_store_health = await self.vector_store_manager.health_check()
            
            # Check database using coordinator pattern
            if self.database_manager:
                database_health = await self.database_manager.health_check()
            
            # Check knowledge graph using coordinator pattern
            if self.knowledge_graph_manager:
                knowledge_graph_health = await self.knowledge_graph_manager.health_check()
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
        
        # Create SystemHealth using centralized model
        system_health = SystemHealth(
            vector_store=vector_store_health,
            database=database_health,
            knowledge_graph=knowledge_graph_health
        )
        
        return system_health
    
    async def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics."""
        stats = {
            'pipeline_status': 'running' if self._running else 'idle',
            'initialized': self._initialized,
            'configuration': {
                'chunk_size': self.config.pipeline_config.chunk_size,
                'chunk_overlap': self.config.pipeline_config.chunk_overlap,
                'max_concurrent_jobs': self.config.pipeline_config.max_concurrent_jobs,
                'enable_knowledge_graph': self.config.pipeline_config.enable_knowledge_graph
            },
            'enabled_sources': len(self.config.get_enabled_sources()),
            'component_stats': {}
        }
        
        # Get component statistics using coordinator pattern
        if self.vector_store_manager:
            stats['component_stats']['vector_store'] = self.vector_store_manager.get_statistics()
        
        if self.database_manager:
            stats['component_stats']['database'] = self.database_manager.get_statistics()
        
        if self.knowledge_graph_manager:
            stats['component_stats']['knowledge_graph'] = self.knowledge_graph_manager.get_statistics()
        
        return stats
    
    async def close(self):
        """Close pipeline and clean up all resources using coordinator pattern."""
        try:
            if self.vector_store_manager:
                await self.vector_store_manager.close()
            
            if self.database_manager:
                await self.database_manager.close()
            
            if self.knowledge_graph_manager:
                await self.knowledge_graph_manager.close()
            
            self._initialized = False
            self.logger.info("Pipeline cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during pipeline cleanup: {e}")
    
    async def cleanup(self):
        """Clean up pipeline resources using coordinator pattern. (Alias for close())"""
        await self.close() 