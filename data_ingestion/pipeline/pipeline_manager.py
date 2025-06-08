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

from config.configuration import SystemConfig, get_system_config
from data_ingestion.managers.vector_store_manager import VectorStoreManager, EmbeddingData
from data_ingestion.managers.database_manager import DatabaseManager, DocumentChunk
from data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager
from data_ingestion.processors.text_processor import TextProcessor
from data_ingestion.connectors.base_connector import BaseConnector, SourceDocument

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

@dataclass
class HealthCheckResult:
    """System health check result."""
    overall_status: bool
    vector_store_healthy: bool
    database_healthy: bool
    knowledge_graph_healthy: bool
    issues: List[str]

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
            
            # Initialize vector store manager
            if self.config.pipeline_config.vector_search:
                self.vector_store_manager = VectorStoreManager(
                    self.config.pipeline_config.vector_search
                )
            
            # Initialize database manager
            if self.config.pipeline_config.database:
                self.database_manager = DatabaseManager(
                    self.config.pipeline_config.database
                )
                await self.database_manager.initialize()
            
            # Initialize knowledge graph manager (if enabled)
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
                from data_ingestion.connectors.github_connector import GitHubConnector
                return GitHubConnector(source_config.__dict__)
            elif source_config.source_type == "drive_folder":
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
        """Store processed document chunks in all configured storage systems."""
        try:
            # Prepare data for storage
            database_chunks = []
            embedding_data = []
            entities = []
            relationships = []
            
            for chunk in processed_doc.chunks:
                stats.total_chunks += 1
                
                # Prepare database chunk
                db_chunk = DocumentChunk(
                    chunk_uuid=chunk.chunk_uuid,
                    source_type=chunk.metadata.get('source_type', ''),
                    source_identifier=chunk.metadata.get('source_identifier', ''),
                    chunk_text_summary=chunk.metadata.get('text_summary', ''),
                    chunk_metadata=chunk.metadata,
                    ingestion_timestamp=datetime.now(),
                    source_last_modified_at=chunk.metadata.get('last_modified'),
                    source_content_hash=chunk.metadata.get('content_hash'),
                    last_indexed_at=datetime.now(),
                    ingestion_status="completed"
                )
                database_chunks.append(db_chunk)
                
                # Collect entities and relationships for knowledge graph
                if chunk.entities:
                    entities.extend(chunk.entities)
                if chunk.relationships:
                    relationships.extend(chunk.relationships)
            
            # Track success for each storage system
            database_success_count = 0
            vector_store_success = True
            knowledge_graph_success = True
            
            # Store in database
            if self.database_manager and database_chunks:
                database_success_count, total_count = await self.database_manager.batch_insert_chunks(database_chunks)
                
                # Track database failures as errors
                failed_count = total_count - database_success_count
                if failed_count > 0:
                    error_msg = f"Failed to store {failed_count}/{total_count} chunks in database"
                    self.logger.error(error_msg)
                    stats.errors.append(error_msg)
            else:
                # If no database manager, assume all chunks "succeed" for database
                database_success_count = len(processed_doc.chunks)
            
            # Generate and store embeddings
            if self.vector_store_manager and database_chunks:
                try:
                    # Extract text for embedding generation
                    texts = [chunk.text for chunk in processed_doc.chunks]
                    embeddings = await self.vector_store_manager.generate_embeddings(texts)
                    
                    # Prepare embedding data
                    for i, (chunk, embedding) in enumerate(zip(processed_doc.chunks, embeddings)):
                        emb_data = EmbeddingData(
                            chunk_uuid=chunk.chunk_uuid,
                            embedding=embedding,
                            metadata=chunk.metadata
                        )
                        embedding_data.append(emb_data)
                    
                    # Store embeddings
                    vector_store_success = await self.vector_store_manager.batch_upsert(embedding_data)
                    if not vector_store_success:
                        error_msg = f"Failed to store {len(embedding_data)} embeddings in vector store"
                        self.logger.error(error_msg)
                        stats.errors.append(error_msg)
                        
                except Exception as e:
                    vector_store_success = False
                    error_msg = f"Vector store operation failed: {e}"
                    self.logger.error(error_msg)
                    stats.errors.append(error_msg)
            
            # Store in knowledge graph
            if (self.knowledge_graph_manager and 
                self.config.pipeline_config.enable_knowledge_graph and
                (entities or relationships)):
                
                try:
                    if entities:
                        kg_success_count, kg_total_count = await self.knowledge_graph_manager.batch_upsert_entities(entities)
                        # Update entity statistics
                        stats.total_entities += kg_success_count
                        
                        failed_entities = kg_total_count - kg_success_count
                        if failed_entities > 0:
                            knowledge_graph_success = False
                            error_msg = f"Failed to store {failed_entities}/{kg_total_count} entities in knowledge graph"
                            self.logger.error(error_msg)
                            stats.errors.append(error_msg)
                    
                    if relationships:
                        # Note: Currently relationships are stored as part of entities
                        # But we should track them separately if the KG manager supports it
                        stats.total_relationships += len(relationships)
                        
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
    
    async def health_check(self) -> HealthCheckResult:
        """Perform comprehensive health check of all components."""
        result = HealthCheckResult(
            overall_status=True,
            vector_store_healthy=True,
            database_healthy=True,
            knowledge_graph_healthy=True,
            issues=[]
        )
        
        try:
            # Check vector store
            if self.vector_store_manager:
                result.vector_store_healthy = await self.vector_store_manager.health_check()
                if not result.vector_store_healthy:
                    result.issues.append("Vector store is unhealthy")
            
            # Check database
            if self.database_manager:
                result.database_healthy = await self.database_manager.health_check()
                if not result.database_healthy:
                    result.issues.append("Database is unhealthy")
            
            # Check knowledge graph
            if self.knowledge_graph_manager:
                result.knowledge_graph_healthy = await self.knowledge_graph_manager.health_check()
                if not result.knowledge_graph_healthy:
                    result.issues.append("Knowledge graph is unhealthy")
            
            # Overall status
            result.overall_status = (
                result.vector_store_healthy and 
                result.database_healthy and 
                result.knowledge_graph_healthy
            )
            
        except Exception as e:
            result.overall_status = False
            result.issues.append(f"Health check failed: {e}")
        
        return result
    
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
            'components': {
                'vector_store': self.vector_store_manager is not None,
                'database': self.database_manager is not None,
                'knowledge_graph': self.knowledge_graph_manager is not None,
                'text_processor': self.text_processor is not None
            }
        }
        
        # Add component-specific stats
        try:
            if self.database_manager:
                db_stats = await self.database_manager.get_source_stats()
                stats['database_stats'] = db_stats
            
            if self.knowledge_graph_manager:
                kg_stats = await self.knowledge_graph_manager.get_graph_stats()
                stats['knowledge_graph_stats'] = kg_stats
                
            if self.vector_store_manager:
                vs_stats = await self.vector_store_manager.get_index_stats()
                stats['vector_store_stats'] = vs_stats
                
        except Exception as e:
            self.logger.warning(f"Failed to get component stats: {e}")
        
        return stats
    
    async def cleanup(self):
        """Clean up resources and close connections."""
        try:
            if self.database_manager:
                await self.database_manager.close()
            
            if self.knowledge_graph_manager:
                await self.knowledge_graph_manager.close()
            
            self.logger.info("Pipeline cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Pipeline cleanup failed: {e}") 