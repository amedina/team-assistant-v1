"""
Database Retriever - specialized for PostgreSQL chunk retrieval and enrichment.

This component handles:
- Chunk retrieval by UUIDs
- Context window assembly (surrounding chunks)
- Metadata enrichment and filtering
- Source document aggregation
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from uuid import UUID

from config.configuration import DatabaseConfig
from ..models import ChunkData, ContextualChunk, EnrichedChunk, ComponentHealth, SourceType

logger = logging.getLogger(__name__)


class DatabaseRetriever:
    """
    Specialized component for database retrieval operations.
    
    This class focuses purely on read operations:
    - Retrieving chunks by UUIDs
    - Assembling contextual chunks with surrounding content
    - Enriching chunks with metadata
    - Filtering and searching chunk collections
    - Source document information aggregation
    """
    
    def __init__(self, 
                 config: DatabaseConfig,
                 connector):
        """
        Initialize DatabaseRetriever with shared database resources.
        
        Args:
            config: Database configuration
            connector: Shared Cloud SQL connector instance
        """
        self.config = config
        self.connector = connector
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Retrieval statistics
        self._total_queries = 0
        self._total_chunks_retrieved = 0
        self._average_response_time_ms = 0.0
        self._cache_hits = 0  # For future caching implementation
    
    async def initialize(self) -> bool:
        """
        Initialize retriever and validate database connectivity.
        
        Returns:
            True if initialization successful
        """
        try:
            async with self._get_connection() as conn:
                result = await conn.fetchval("SELECT COUNT(*) FROM document_chunks")
                self.logger.info(f"DatabaseRetriever initialized. Found {result} chunks.")
                return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False
    
    @asynccontextmanager
    async def _get_connection(self):
        """Get database connection using shared connector."""
        connection = await self.connector.connect_async(
            instance_connection_string=self.config.instance_connection_name,
            driver="asyncpg",
            user=self.config.db_user,
            password=self.config.db_pass,
            db=self.config.db_name,
        )
        try:
            yield connection
        finally:
            await connection.close()
    
    async def get_chunks_by_uuids(self, chunk_uuids: List[str]) -> List[ChunkData]:
        """
        Retrieve chunks by their UUIDs.
        
        Args:
            chunk_uuids: List of chunk UUID strings
            
        Returns:
            List of ChunkData objects
        """
        if not chunk_uuids:
            return []
        
        try:
            async with self._get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT chunk_uuid, source_type, source_identifier, 
                           chunk_text_summary, chunk_metadata, ingestion_timestamp
                    FROM document_chunks 
                    WHERE chunk_uuid = ANY($1::uuid[])
                """, chunk_uuids)
                
                chunks = []
                for row in rows:
                    chunk = ChunkData(
                        chunk_uuid=UUID(str(row['chunk_uuid'])),
                        source_type=row['source_type'],
                        source_identifier=row['source_identifier'],
                        chunk_text_summary=row['chunk_text_summary'],
                        chunk_metadata=json.loads(row['chunk_metadata']) if row['chunk_metadata'] else {},
                        ingestion_timestamp=row['ingestion_timestamp']
                    )
                    chunks.append(chunk)
                
                return chunks
        except Exception as e:
            self.logger.error(f"Failed to retrieve chunks: {e}")
            return []
    
    async def get_chunk_with_context(self, 
                                   chunk_uuid: str, 
                                   context_window: int = 2) -> Optional[ContextualChunk]:
        """
        Retrieve a chunk with surrounding context chunks.
        
        Args:
            chunk_uuid: UUID of the primary chunk
            context_window: Number of chunks before and after to include
            
        Returns:
            ContextualChunk with primary chunk and context, or None if not found
        """
        if context_window < 0 or context_window > 10:
            raise ValueError("context_window must be between 0 and 10")
        
        try:
            # First, get the primary chunk
            primary_chunks = await self.get_chunks_by_uuids([chunk_uuid])
            if not primary_chunks:
                return None
            
            primary_chunk = primary_chunks[0]
            
            # If no context window needed, return just the primary chunk
            if context_window == 0:
                return ContextualChunk(
                    primary_chunk=primary_chunk,
                    context_chunks=[],
                    context_window_size=0,
                    source_document_info=await self._get_source_document_info(primary_chunk.source_identifier)
                )
            
            # Get context chunks from the same source
            context_chunks = await self._get_context_chunks(
                primary_chunk.source_identifier, 
                primary_chunk.chunk_uuid, 
                context_window
            )
            
            # Get source document information
            source_info = await self._get_source_document_info(primary_chunk.source_identifier)
            
            return ContextualChunk(
                primary_chunk=primary_chunk,
                context_chunks=context_chunks,
                context_window_size=context_window,
                source_document_info=source_info
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get chunk with context for {chunk_uuid}: {e}")
            return None
    
    async def _get_context_chunks(self, 
                                source_identifier: str, 
                                primary_chunk_uuid: UUID, 
                                context_window: int) -> List[ChunkData]:
        """Get surrounding chunks from the same source."""
        try:
            async with self._get_connection() as conn:
                # Get chunks from the same source, ordered by metadata (if it contains chunk index)
                rows = await conn.fetch("""
                    SELECT chunk_uuid, source_type, source_identifier, 
                           chunk_text_summary, chunk_metadata, ingestion_timestamp,
                           source_last_modified_at, source_content_hash, 
                           last_indexed_at, ingestion_status
                    FROM document_chunks 
                    WHERE source_identifier = $1 
                      AND chunk_uuid != $2
                    ORDER BY 
                        COALESCE((chunk_metadata->>'chunk_index')::int, 0),
                        ingestion_timestamp
                    LIMIT $3
                """, source_identifier, str(primary_chunk_uuid), context_window * 2)
                
                context_chunks = []
                for row in rows:
                    chunk = ChunkData(
                        chunk_uuid=UUID(str(row['chunk_uuid'])),
                        source_type=SourceType(row['source_type']),
                        source_identifier=row['source_identifier'],
                        chunk_text_summary=row['chunk_text_summary'],
                        chunk_metadata=json.loads(row['chunk_metadata']) if row['chunk_metadata'] else {},
                        ingestion_timestamp=row['ingestion_timestamp'],
                        source_last_modified_at=row['source_last_modified_at'],
                        source_content_hash=row['source_content_hash'],
                        last_indexed_at=row['last_indexed_at'],
                        ingestion_status=row['ingestion_status']
                    )
                    context_chunks.append(chunk)
                
                return context_chunks[:context_window * 2]  # Limit to requested window
                
        except Exception as e:
            self.logger.error(f"Failed to get context chunks: {e}")
            return []
    
    async def _get_source_document_info(self, source_identifier: str) -> Dict[str, Any]:
        """Get aggregated information about a source document."""
        try:
            async with self._get_connection() as conn:
                # Get document statistics
                result = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_chunks,
                        MAX(ingestion_timestamp) as last_updated,
                        source_type,
                        source_content_hash
                    FROM document_chunks 
                    WHERE source_identifier = $1
                    GROUP BY source_type, source_content_hash
                """, source_identifier)
                
                if result:
                    return {
                        "source_identifier": source_identifier,
                        "source_type": result['source_type'],
                        "total_chunks": result['total_chunks'],
                        "last_updated": result['last_updated'],
                        "content_hash": result['source_content_hash']
                    }
                else:
                    return {"source_identifier": source_identifier}
                    
        except Exception as e:
            self.logger.error(f"Failed to get source document info: {e}")
            return {"source_identifier": source_identifier}
    
    async def enrich_chunks_with_metadata(self, 
                                        chunk_uuids: List[str],
                                        vector_scores: Optional[List[float]] = None) -> List[EnrichedChunk]:
        """
        Enrich chunks with additional metadata and scores.
        
        Args:
            chunk_uuids: List of chunk UUIDs
            vector_scores: Optional vector similarity scores (must match chunk_uuids length)
            
        Returns:
            List of EnrichedChunk objects
        """
        if vector_scores and len(vector_scores) != len(chunk_uuids):
            raise ValueError("vector_scores length must match chunk_uuids length")
        
        try:
            # Retrieve base chunk data
            chunks = await self.get_chunks_by_uuids(chunk_uuids)
            
            # Create enriched chunks
            enriched_chunks = []
            chunk_uuid_to_chunk = {str(chunk.chunk_uuid): chunk for chunk in chunks}
            
            for i, chunk_uuid in enumerate(chunk_uuids):
                chunk = chunk_uuid_to_chunk.get(chunk_uuid)
                if not chunk:
                    continue
                
                # Get related chunks from same source
                related_chunks = await self._get_related_chunk_uuids(chunk.source_identifier, chunk.chunk_uuid)
                
                enriched_chunk = EnrichedChunk(
                    chunk_data=chunk,
                    vector_score=vector_scores[i] if vector_scores else None,
                    graph_entities=[],  # To be populated by knowledge graph retriever
                    related_chunks=related_chunks,
                    relevance_score=vector_scores[i] if vector_scores else None,
                    ranking_position=i + 1
                )
                enriched_chunks.append(enriched_chunk)
            
            return enriched_chunks
            
        except Exception as e:
            self.logger.error(f"Failed to enrich chunks with metadata: {e}")
            return []
    
    async def _get_related_chunk_uuids(self, source_identifier: str, exclude_uuid: UUID) -> List[UUID]:
        """Get UUIDs of chunks from the same source."""
        try:
            async with self._get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT chunk_uuid 
                    FROM document_chunks 
                    WHERE source_identifier = $1 
                      AND chunk_uuid != $2
                    ORDER BY 
                        COALESCE((chunk_metadata->>'chunk_index')::int, 0),
                        ingestion_timestamp
                    LIMIT 5
                """, source_identifier, str(exclude_uuid))
                
                return [UUID(str(row['chunk_uuid'])) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to get related chunk UUIDs: {e}")
            return []
    
    async def search_chunks_by_source(self, 
                                    source_identifier: str,
                                    limit: int = 100) -> List[ChunkData]:
        """
        Get all chunks for a specific source.
        
        Args:
            source_identifier: Source identifier to search
            limit: Maximum number of chunks to return
            
        Returns:
            List of ChunkData objects
        """
        try:
            async with self._get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT chunk_uuid, source_type, source_identifier, 
                           chunk_text_summary, chunk_metadata, ingestion_timestamp,
                           source_last_modified_at, source_content_hash, 
                           last_indexed_at, ingestion_status
                    FROM document_chunks 
                    WHERE source_identifier = $1
                    ORDER BY 
                        COALESCE((chunk_metadata->>'chunk_index')::int, 0),
                        ingestion_timestamp
                    LIMIT $2
                """, source_identifier, limit)
                
                chunks = []
                for row in rows:
                    chunk = ChunkData(
                        chunk_uuid=UUID(str(row['chunk_uuid'])),
                        source_type=SourceType(row['source_type']),
                        source_identifier=row['source_identifier'],
                        chunk_text_summary=row['chunk_text_summary'],
                        chunk_metadata=json.loads(row['chunk_metadata']) if row['chunk_metadata'] else {},
                        ingestion_timestamp=row['ingestion_timestamp'],
                        source_last_modified_at=row['source_last_modified_at'],
                        source_content_hash=row['source_content_hash'],
                        last_indexed_at=row['last_indexed_at'],
                        ingestion_status=row['ingestion_status']
                    )
                    chunks.append(chunk)
                
                return chunks
                
        except Exception as e:
            self.logger.error(f"Failed to search chunks by source: {e}")
            return []
    
    async def search_chunks_by_metadata(self, 
                                      metadata_filters: Dict[str, Any],
                                      limit: int = 100) -> List[ChunkData]:
        """
        Search chunks by metadata fields.
        
        Args:
            metadata_filters: Dictionary of metadata field filters
            limit: Maximum number of chunks to return
            
        Returns:
            List of ChunkData objects
        """
        if not metadata_filters:
            return []
        
        try:
            # Build dynamic WHERE clause for JSONB queries
            conditions = []
            params = []
            param_count = 0
            
            for key, value in metadata_filters.items():
                param_count += 1
                conditions.append(f"chunk_metadata->>'{key}' = ${param_count}")
                params.append(str(value))
            
            where_clause = " AND ".join(conditions)
            
            param_count += 1
            limit_clause = f"LIMIT ${param_count}"
            params.append(limit)
            
            query = f"""
                SELECT chunk_uuid, source_type, source_identifier, 
                       chunk_text_summary, chunk_metadata, ingestion_timestamp,
                       source_last_modified_at, source_content_hash, 
                       last_indexed_at, ingestion_status
                FROM document_chunks 
                WHERE {where_clause}
                ORDER BY ingestion_timestamp DESC
                {limit_clause}
            """
            
            async with self._get_connection() as conn:
                rows = await conn.fetch(query, *params)
                
                chunks = []
                for row in rows:
                    chunk = ChunkData(
                        chunk_uuid=UUID(str(row['chunk_uuid'])),
                        source_type=SourceType(row['source_type']),
                        source_identifier=row['source_identifier'],
                        chunk_text_summary=row['chunk_text_summary'],
                        chunk_metadata=json.loads(row['chunk_metadata']) if row['chunk_metadata'] else {},
                        ingestion_timestamp=row['ingestion_timestamp'],
                        source_last_modified_at=row['source_last_modified_at'],
                        source_content_hash=row['source_content_hash'],
                        last_indexed_at=row['last_indexed_at'],
                        ingestion_status=row['ingestion_status']
                    )
                    chunks.append(chunk)
                
                return chunks
                
        except Exception as e:
            self.logger.error(f"Failed to search chunks by metadata: {e}")
            return []
    
    def _update_average_response_time(self, response_time_ms: float):
        """Update the running average response time."""
        if self._total_queries == 1:
            self._average_response_time_ms = response_time_ms
        else:
            alpha = 0.1
            self._average_response_time_ms = (
                alpha * response_time_ms + 
                (1 - alpha) * self._average_response_time_ms
            )
    
    async def health_check(self) -> ComponentHealth:
        """
        Check retriever health and performance.
        
        Returns:
            ComponentHealth with retriever status
        """
        start_time = datetime.now()
        
        try:
            # Test database connectivity and performance
            async with self._get_connection() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM document_chunks LIMIT 1")
                
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ComponentHealth(
                component_name="DatabaseRetriever",
                is_healthy=True,
                response_time_ms=response_time,
                additional_info={
                    "total_queries": self._total_queries,
                    "average_response_time_ms": self._average_response_time_ms,
                    "total_chunks_retrieved": self._total_chunks_retrieved,
                    "cache_hits": self._cache_hits
                }
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return ComponentHealth(
                component_name="DatabaseRetriever",
                is_healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {
            "total_queries": self._total_queries,
            "total_chunks_retrieved": self._total_chunks_retrieved,
            "average_response_time_ms": self._average_response_time_ms,
            "average_chunks_per_query": (
                self._total_chunks_retrieved / self._total_queries 
                if self._total_queries > 0 else 0.0
            ),
            "cache_hits": self._cache_hits
        }
    
    async def close(self):
        """Close retriever and clean up resources."""
        self.logger.info(f"DatabaseRetriever closed. Final stats: {self.get_statistics()}") 