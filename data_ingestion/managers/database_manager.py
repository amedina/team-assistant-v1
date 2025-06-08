"""
Database Manager - Coordinator for PostgreSQL database operations.
Implements the Manager-as-Coordinator pattern with shared resource management.

This component acts as a facade that:
- Manages shared database connections and schema
- Coordinates between DatabaseIngestor and DatabaseRetriever
- Provides unified interface for database operations
- Handles connection lifecycle and health checks
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager
from datetime import datetime
from google.cloud.sql.connector import Connector

from config.configuration import DatabaseConfig
from ..models import (
    ChunkData, ContextualChunk, EnrichedChunk, BatchOperationResult,
    ComponentHealth, IngestionStatus
)
from ..ingestors.database_ingestor import DatabaseIngestor
from ..retrievers.database_retriever import DatabaseRetriever

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Coordinator/Facade for PostgreSQL database operations.
    
    Responsibilities:
    - Managing shared database connections and schema
    - Coordinating between ingestor and retriever components
    - Providing unified interface for database operations
    - Connection lifecycle management and health monitoring
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Shared resources
        self._connector: Optional[Connector] = None
        
        # Specialized components (initialized after shared resources)
        self.ingestor: Optional[DatabaseIngestor] = None
        self.retriever: Optional[DatabaseRetriever] = None
        
        # Manager state
        self._initialized = False
        
    async def initialize(self) -> bool:
        """
        Initialize shared database resources and component coordination.
        
        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing DatabaseManager and shared resources...")
            
            # Initialize shared resources
            await self._initialize_shared_resources()
            
            # Initialize specialized components with shared resources
            self.ingestor = DatabaseIngestor(
                config=self.config,
                connector=self._connector
            )
            
            self.retriever = DatabaseRetriever(
                config=self.config,
                connector=self._connector
            )
            
            # Initialize components
            ingestor_ready = await self.ingestor.initialize()
            retriever_ready = await self.retriever.initialize()
            
            self._initialized = ingestor_ready and retriever_ready
            
            if self._initialized:
                self.logger.info("DatabaseManager initialization completed successfully")
            else:
                self.logger.error("DatabaseManager initialization failed - components not ready")
            
            return self._initialized
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DatabaseManager: {e}")
            return False
    
    async def _initialize_shared_resources(self):
        """Initialize shared database connections and schema."""
        # Initialize Cloud SQL Connector
        self._connector = Connector()
        
        # Test connection
        test_conn = await self._connector.connect_async(
            instance_connection_string=self.config.instance_connection_name,
            driver="asyncpg",
            user=self.config.db_user,
            password=self.config.db_pass,
            db=self.config.db_name,
        )
        await test_conn.close()
        
        self.logger.info("Cloud SQL connection test successful")
        
        # Initialize schema
        await self._initialize_schema()
        
        self.logger.info("Shared database resources initialized successfully")
    
    async def _create_connection(self):
        """Create a new database connection using Cloud SQL Connector."""
        if self._connector is None:
            raise RuntimeError("Database manager not initialized. Call initialize() first.")
        
        return await self._connector.connect_async(
            instance_connection_string=self.config.instance_connection_name,
            driver="asyncpg",
            user=self.config.db_user,
            password=self.config.db_pass,
            db=self.config.db_name,
        )
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection using Cloud SQL Connector."""
        connection = await self._create_connection()
        try:
            yield connection
        finally:
            await connection.close()
    
    async def _initialize_schema(self):
        """Initialize database schema and indexes."""
        schema_sql = """
        -- Create document_chunks table
        CREATE TABLE IF NOT EXISTS document_chunks (
            chunk_uuid UUID PRIMARY KEY,
            source_type VARCHAR(50) NOT NULL,
            source_identifier VARCHAR(512) NOT NULL,
            chunk_text_summary TEXT,
            chunk_metadata JSONB,
            ingestion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            source_last_modified_at TIMESTAMP WITH TIME ZONE,
            source_content_hash VARCHAR(64),
            last_indexed_at TIMESTAMP WITH TIME ZONE,
            ingestion_status VARCHAR(20) DEFAULT 'completed'
        );
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_document_chunks_source_type 
            ON document_chunks(source_type);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_source_identifier 
            ON document_chunks(source_identifier);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_ingestion_timestamp 
            ON document_chunks(ingestion_timestamp);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata 
            ON document_chunks USING GIN(chunk_metadata);
        
        -- Create ingestion_stats table for tracking
        CREATE TABLE IF NOT EXISTS ingestion_stats (
            id SERIAL PRIMARY KEY,
            source_id VARCHAR(100) NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            chunks_processed INTEGER NOT NULL,
            chunks_successful INTEGER NOT NULL,
            start_time TIMESTAMP WITH TIME ZONE NOT NULL,
            end_time TIMESTAMP WITH TIME ZONE,
            status VARCHAR(20) NOT NULL DEFAULT 'running',
            error_message TEXT,
            metadata JSONB
        );
        
        CREATE INDEX IF NOT EXISTS idx_ingestion_stats_source_id 
            ON ingestion_stats(source_id);
        CREATE INDEX IF NOT EXISTS idx_ingestion_stats_start_time 
            ON ingestion_stats(start_time);
        """
        
        async with self.get_connection() as conn:
            await conn.execute(schema_sql)
            self.logger.info("Database schema initialized")
    
    # =================================================================
    # INGESTION COORDINATION METHODS
    # =================================================================
    
    async def ingest_chunk(self, chunk_data: ChunkData) -> bool:
        """
        Coordinate single chunk ingestion through the ingestor component.
        
        Args:
            chunk_data: ChunkData object to store
            
        Returns:
            True if successful
        """
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        return await self.ingestor.store_chunk(chunk_data)
    
    async def batch_ingest_chunks(self, chunks: List[ChunkData]) -> Tuple[int, int]:
        """
        Coordinate batch chunk ingestion through the ingestor component.
        
        Args:
            chunks: List of ChunkData objects to store
            
        Returns:
            Tuple of (successful_count, total_count)
        """
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        result = await self.ingestor.batch_store_chunks(chunks)
        return result.successful_count, result.total_count
    
    async def update_chunk_status(self, chunk_uuid: str, status: IngestionStatus) -> bool:
        """
        Coordinate chunk status update through the ingestor component.
        
        Args:
            chunk_uuid: UUID of chunk to update
            status: New ingestion status
            
        Returns:
            True if successful
        """
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        return await self.ingestor.update_ingestion_status(chunk_uuid, status)
    
    async def delete_chunks_by_source(self, source_identifier: str) -> int:
        """
        Coordinate chunk deletion by source through the ingestor component.
        
        Args:
            source_identifier: Source identifier to delete
            
        Returns:
            Number of chunks deleted
        """
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        return await self.ingestor.delete_chunks_by_source(source_identifier)
    
    # =================================================================
    # RETRIEVAL COORDINATION METHODS
    # =================================================================
    
    async def get_chunk(self, chunk_uuid: str) -> Optional[ChunkData]:
        """
        Coordinate single chunk retrieval through the retriever component.
        
        Args:
            chunk_uuid: UUID of the chunk to retrieve
            
        Returns:
            ChunkData object or None if not found
        """
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        # Use the batch method with a single UUID
        chunks = await self.retriever.get_chunks_by_uuids([chunk_uuid])
        return chunks[0] if chunks else None
    
    async def get_chunks(self, chunk_uuids: List[str]) -> List[ChunkData]:
        """
        Coordinate multiple chunk retrieval through the retriever component.
        
        Args:
            chunk_uuids: List of chunk UUIDs to retrieve
            
        Returns:
            List of ChunkData objects
        """
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        return await self.retriever.get_chunks_by_uuids(chunk_uuids)
    
    async def search_chunks(self, 
                          source_type: Optional[str] = None,
                          source_identifier: Optional[str] = None,
                          metadata_filter: Optional[Dict[str, Any]] = None,
                          limit: int = 100,
                          offset: int = 0) -> List[ChunkData]:
        """
        Coordinate chunk search through the retriever component.
        
        Args:
            source_type: Filter by source type
            source_identifier: Filter by source identifier
            metadata_filter: Filter by metadata fields
            limit: Maximum results to return
            offset: Offset for pagination
            
        Returns:
            List of ChunkData objects
        """
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        # Delegate to appropriate retriever method based on search criteria
        if source_identifier:
            # Use source-specific search
            return await self.retriever.search_chunks_by_source(source_identifier, limit)
        elif metadata_filter:
            # Use metadata-based search
            return await self.retriever.search_chunks_by_metadata(metadata_filter, limit)
        else:
            # For general search, use metadata search with source_type filter if provided
            search_filters = {}
            if source_type:
                search_filters['source_type'] = source_type
            
            if search_filters:
                return await self.retriever.search_chunks_by_metadata(search_filters, limit)
            else:
                # Return empty list if no search criteria provided
                self.logger.warning("No search criteria provided to search_chunks")
                return []
    
    async def get_chunk_with_context(self, 
                                   chunk_uuid: str, 
                                   context_window: int = 2) -> Optional[ContextualChunk]:
        """
        Coordinate single contextual chunk retrieval through the retriever component.
        
        Args:
            chunk_uuid: Primary chunk UUID
            context_window: Number of surrounding chunks to include
            
        Returns:
            ContextualChunk object with context or None if not found
        """
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        return await self.retriever.get_chunk_with_context(chunk_uuid, context_window)
    
    async def get_contextual_chunks(self, 
                                  chunk_uuids: List[str],
                                  context_window: int = 2) -> List[ContextualChunk]:
        """
        Coordinate contextual chunk retrieval through the retriever component.
        
        Args:
            chunk_uuids: List of primary chunk UUIDs
            context_window: Number of surrounding chunks to include
            
        Returns:
            List of ContextualChunk objects with context
        """
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        contextual_chunks = []
        for chunk_uuid in chunk_uuids:
            contextual_chunk = await self.retriever.get_chunk_with_context(chunk_uuid, context_window)
            if contextual_chunk:
                contextual_chunks.append(contextual_chunk)
        
        return contextual_chunks
    
    async def enrich_chunks(self, 
                          chunks: List[ChunkData],
                          vector_scores: Optional[List[float]] = None,
                          graph_entities: Optional[List[List[str]]] = None) -> List[EnrichedChunk]:
        """
        Coordinate chunk enrichment through the retriever component.
        
        Args:
            chunks: Base chunk data
            vector_scores: Optional vector similarity scores
            graph_entities: Optional graph entities per chunk
            
        Returns:
            List of EnrichedChunk objects
        """
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        chunk_uuids = [str(chunk.chunk_uuid) for chunk in chunks]
        return await self.retriever.enrich_chunks_with_metadata(chunk_uuids, vector_scores)
    
    # =================================================================
    # ANALYTICS AND MONITORING METHODS
    # =================================================================
    
    async def get_source_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive source statistics from retriever component.
        
        Returns:
            Dictionary with source statistics
        """
        if not self._initialized:
            return {"error": "Manager not initialized"}
        
        return self.retriever.get_statistics()
    
    async def get_ingestion_statistics(self) -> Dict[str, Any]:
        """
        Get ingestion statistics from ingestor component.
        
        Returns:
            Dictionary with ingestion statistics
        """
        if not self._initialized:
            return {"error": "Manager not initialized"}
        
        return self.ingestor.get_statistics()
    
    async def health_check(self) -> ComponentHealth:
        """
        Coordinate comprehensive health check of database system.
        
        Returns:
            ComponentHealth with overall system status
        """
        start_time = datetime.now()
        
        try:
            if not self._initialized:
                return ComponentHealth(
                    component_name="DatabaseManager",
                    is_healthy=False,
                    error_message="Manager not initialized"
                )
            
            # Check component health
            ingestor_health = await self.ingestor.health_check()
            retriever_health = await self.retriever.health_check()
            
            is_healthy = ingestor_health.is_healthy and retriever_health.is_healthy
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            additional_info = {
                "ingestor_healthy": ingestor_health.is_healthy,
                "retriever_healthy": retriever_health.is_healthy,
                "ingestor_stats": self.ingestor.get_statistics(),
                "retriever_stats": self.retriever.get_statistics()
            }
            
            return ComponentHealth(
                component_name="DatabaseManager",
                is_healthy=is_healthy,
                response_time_ms=response_time,
                additional_info=additional_info
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return ComponentHealth(
                component_name="DatabaseManager",
                is_healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics from all components.
        
        Returns:
            Dictionary with system statistics
        """
        if not self._initialized:
            return {"error": "Manager not initialized"}
        
        return {
            "manager_initialized": self._initialized,
            "ingestion_stats": self.ingestor.get_statistics(),
            "retrieval_stats": self.retriever.get_statistics(),
            "shared_resources": {
                "connector_initialized": self._connector is not None
            }
        }
    
    async def close(self):
        """Close manager and clean up database resources."""
        try:
            if self.ingestor:
                await self.ingestor.close()
            if self.retriever:
                await self.retriever.close()
            
            if self._connector:
                await self._connector.close()
            
            self._initialized = False
            self.logger.info("DatabaseManager closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during DatabaseManager cleanup: {e}") 