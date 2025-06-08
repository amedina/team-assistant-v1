"""
Database Manager for PostgreSQL operations.
Handles document chunks metadata, source mapping, and ingestion tracking.
"""

import uuid
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncpg
from contextlib import asynccontextmanager
from google.cloud.sql.connector import Connector

from config.configuration import DatabaseConfig

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Document chunk data structure for database operations."""
    chunk_uuid: str
    source_type: str
    source_identifier: str
    chunk_text_summary: Optional[str] = None
    chunk_metadata: Optional[Dict[str, Any]] = None
    ingestion_timestamp: Optional[datetime] = None
    source_last_modified_at: Optional[datetime] = None
    source_content_hash: Optional[str] = None
    last_indexed_at: Optional[datetime] = None
    ingestion_status: Optional[str] = "pending"

@dataclass
class ChunkSearchResult:
    """Result from chunk search in database."""
    chunk_uuid: str
    source_type: str
    source_identifier: str
    chunk_text_summary: Optional[str]
    chunk_metadata: Dict[str, Any]
    ingestion_timestamp: datetime
    source_last_modified_at: Optional[datetime] = None
    source_content_hash: Optional[str] = None
    last_indexed_at: Optional[datetime] = None
    ingestion_status: Optional[str] = None

class DatabaseManager:
    """
    Manager for PostgreSQL database operations.
    
    Responsibilities:
    - Managing document chunks metadata
    - Source identifier mapping
    - Ingestion tracking and statistics
    - Database schema management
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._connector: Optional[Connector] = None
        
    async def initialize(self):
        """Initialize database connection pool and schema using Cloud SQL Connector."""
        try:
            # Initialize Cloud SQL Connector
            self._connector = Connector()
            
            # Test connection first
            test_conn = await self._connector.connect_async(
                instance_connection_string=self.config.instance_connection_name,
                driver="asyncpg",
                user=self.config.db_user,
                password=self.config.db_pass,
                db=self.config.db_name,
            )
            await test_conn.close()
            
            self.logger.info("Cloud SQL connection test successful")
            
            # Note: We'll create connections on-demand rather than using a pool
            # This is simpler with the Cloud SQL Connector and works well for our use case
            
            # Initialize schema
            await self._initialize_schema()
            
            self.logger.info("Database manager initialized successfully with Cloud SQL Connector")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database manager: {e}")
            raise
    
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
            ingestion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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
    
    async def insert_chunk(self, chunk: DocumentChunk) -> bool:
        """
        Insert a single document chunk.
        
        Args:
            chunk: DocumentChunk to insert
            
        Returns:
            True if successful
        """
        try:
            import json
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO document_chunks 
                    (chunk_uuid, source_type, source_identifier, chunk_text_summary, chunk_metadata, 
                     ingestion_timestamp, source_last_modified_at, source_content_hash, 
                     last_indexed_at, ingestion_status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (chunk_uuid) DO UPDATE SET
                        source_type = EXCLUDED.source_type,
                        source_identifier = EXCLUDED.source_identifier,
                        chunk_text_summary = EXCLUDED.chunk_text_summary,
                        chunk_metadata = EXCLUDED.chunk_metadata,
                        ingestion_timestamp = EXCLUDED.ingestion_timestamp,
                        source_last_modified_at = EXCLUDED.source_last_modified_at,
                        source_content_hash = EXCLUDED.source_content_hash,
                        last_indexed_at = EXCLUDED.last_indexed_at,
                        ingestion_status = EXCLUDED.ingestion_status
                """, 
                chunk.chunk_uuid,
                chunk.source_type,
                chunk.source_identifier,
                chunk.chunk_text_summary,
                json.dumps(chunk.chunk_metadata) if chunk.chunk_metadata else None,
                chunk.ingestion_timestamp or datetime.now(),
                chunk.source_last_modified_at,
                chunk.source_content_hash,
                chunk.last_indexed_at or datetime.now(),
                chunk.ingestion_status or "completed"
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to insert chunk {chunk.chunk_uuid}: {e}")
            return False
    
    async def batch_insert_chunks(self, chunks: List[DocumentChunk]) -> Tuple[int, int]:
        """
        Batch insert document chunks.
        
        Args:
            chunks: List of DocumentChunk objects
            
        Returns:
            Tuple of (successful_count, total_count)
        """
        successful_count = 0
        
        try:
            import json
            async with self.get_connection() as conn:
                # Prepare and validate data for batch insert
                values = []
                for i, chunk in enumerate(chunks):
                    try:
                        # Validate UUID format
                        uuid.UUID(chunk.chunk_uuid)
                        
                        # Validate text summary length (database column limits)
                        text_summary = chunk.chunk_text_summary
                        if text_summary and len(text_summary) > 10000:  # Reasonable limit
                            text_summary = text_summary[:10000] + "..."
                            self.logger.warning(f"Truncated text_summary for chunk {chunk.chunk_uuid}")
                        
                        # Validate and clean source fields
                        source_type = chunk.source_type[:50] if chunk.source_type else ""
                        source_identifier = chunk.source_identifier[:512] if chunk.source_identifier else ""
                        
                        # Validate JSON metadata
                        metadata_json = None
                        if chunk.chunk_metadata:
                            try:
                                metadata_json = json.dumps(chunk.chunk_metadata)
                                # Test JSON deserialization
                                json.loads(metadata_json)
                            except (TypeError, ValueError) as json_error:
                                self.logger.error(f"Invalid JSON metadata for chunk {chunk.chunk_uuid}: {json_error}")
                                metadata_json = json.dumps({"error": "Invalid metadata", "original_type": str(type(chunk.chunk_metadata))})
                        
                        values.append((
                            chunk.chunk_uuid,
                            source_type,
                            source_identifier,
                            text_summary,
                            metadata_json,
                            chunk.ingestion_timestamp or datetime.now(),
                            chunk.source_last_modified_at,
                            chunk.source_content_hash,
                            chunk.last_indexed_at or datetime.now(),
                            chunk.ingestion_status or "completed"
                        ))
                        
                    except ValueError as uuid_error:
                        self.logger.error(f"Invalid UUID format for chunk {i}: {chunk.chunk_uuid} - {uuid_error}")
                        continue
                    except Exception as chunk_error:
                        self.logger.error(f"Error preparing chunk {i} for batch insert: {chunk_error}")
                        continue
                
                if not values:
                    self.logger.error("No valid chunks to insert after validation")
                    return 0, len(chunks)
                
                # Execute batch insert
                await conn.executemany("""
                    INSERT INTO document_chunks 
                    (chunk_uuid, source_type, source_identifier, chunk_text_summary, chunk_metadata, 
                     ingestion_timestamp, source_last_modified_at, source_content_hash, 
                     last_indexed_at, ingestion_status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (chunk_uuid) DO UPDATE SET
                        source_type = EXCLUDED.source_type,
                        source_identifier = EXCLUDED.source_identifier,
                        chunk_text_summary = EXCLUDED.chunk_text_summary,
                        chunk_metadata = EXCLUDED.chunk_metadata,
                        ingestion_timestamp = EXCLUDED.ingestion_timestamp,
                        source_last_modified_at = EXCLUDED.source_last_modified_at,
                        source_content_hash = EXCLUDED.source_content_hash,
                        last_indexed_at = EXCLUDED.last_indexed_at,
                        ingestion_status = EXCLUDED.ingestion_status
                """, values)
                
                successful_count = len(values)
                self.logger.info(f"Batch inserted {successful_count} chunks")
                
        except Exception as e:
            self.logger.error(f"Batch insert failed with detailed error: {type(e).__name__}: {e}")
            if hasattr(e, 'args') and e.args:
                self.logger.error(f"Error details: {e.args}")
            
            # Log first few problematic chunks for debugging
            if len(chunks) > 0:
                sample_chunk = chunks[0]
                self.logger.error(f"Sample chunk data - UUID: {sample_chunk.chunk_uuid}, "
                                f"Source: {sample_chunk.source_type}, "
                                f"Summary length: {len(sample_chunk.chunk_text_summary) if sample_chunk.chunk_text_summary else 0}, "
                                f"Metadata type: {type(sample_chunk.chunk_metadata)}")
            
            # Fallback to individual inserts
            self.logger.info("Falling back to individual chunk inserts...")
            for chunk in chunks:
                if await self.insert_chunk(chunk):
                    successful_count += 1
        
        return successful_count, len(chunks)
    
    async def get_chunk_by_uuid(self, chunk_uuid: str) -> Optional[ChunkSearchResult]:
        """
        Get chunk by UUID.
        
        Args:
            chunk_uuid: UUID of the chunk
            
        Returns:
            ChunkSearchResult or None if not found
        """
        try:
            async with self.get_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT chunk_uuid, source_type, source_identifier, 
                           chunk_text_summary, chunk_metadata, ingestion_timestamp,
                           source_last_modified_at, source_content_hash, 
                           last_indexed_at, ingestion_status
                    FROM document_chunks 
                    WHERE chunk_uuid = $1
                """, chunk_uuid)
                
                if row:
                    return ChunkSearchResult(
                        chunk_uuid=str(row['chunk_uuid']),
                        source_type=row['source_type'],
                        source_identifier=row['source_identifier'],
                        chunk_text_summary=row['chunk_text_summary'],
                        chunk_metadata=row['chunk_metadata'] or {},
                        ingestion_timestamp=row['ingestion_timestamp'],
                        source_last_modified_at=row['source_last_modified_at'],
                        source_content_hash=row['source_content_hash'],
                        last_indexed_at=row['last_indexed_at'],
                        ingestion_status=row['ingestion_status']
                    )
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get chunk {chunk_uuid}: {e}")
            return None
    
    async def get_chunks_by_uuids(self, chunk_uuids: List[str]) -> List[ChunkSearchResult]:
        """
        Get multiple chunks by UUIDs.
        
        Args:
            chunk_uuids: List of chunk UUIDs
            
        Returns:
            List of ChunkSearchResult objects
        """
        if not chunk_uuids:
            return []
        
        try:
            async with self.get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT chunk_uuid, source_type, source_identifier, 
                           chunk_text_summary, chunk_metadata, ingestion_timestamp,
                           source_last_modified_at, source_content_hash, 
                           last_indexed_at, ingestion_status
                    FROM document_chunks 
                    WHERE chunk_uuid = ANY($1::uuid[])
                """, chunk_uuids)
                
                results = []
                for row in rows:
                    result = ChunkSearchResult(
                        chunk_uuid=str(row['chunk_uuid']),
                        source_type=row['source_type'],
                        source_identifier=row['source_identifier'],
                        chunk_text_summary=row['chunk_text_summary'],
                        chunk_metadata=row['chunk_metadata'] or {},
                        ingestion_timestamp=row['ingestion_timestamp'],
                        source_last_modified_at=row['source_last_modified_at'],
                        source_content_hash=row['source_content_hash'],
                        last_indexed_at=row['last_indexed_at'],
                        ingestion_status=row['ingestion_status']
                    )
                    results.append(result)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Failed to get chunks by UUIDs: {e}")
            return []
    
    async def search_chunks(self, 
                          source_type: Optional[str] = None,
                          source_identifier: Optional[str] = None,
                          metadata_filter: Optional[Dict[str, Any]] = None,
                          limit: int = 100,
                          offset: int = 0) -> List[ChunkSearchResult]:
        """
        Search chunks with filters.
        
        Args:
            source_type: Filter by source type
            source_identifier: Filter by source identifier
            metadata_filter: Filter by metadata fields
            limit: Maximum results to return
            offset: Offset for pagination
            
        Returns:
            List of ChunkSearchResult objects
        """
        try:
            conditions = []
            params = []
            param_count = 0
            
            # Build WHERE conditions
            if source_type:
                param_count += 1
                conditions.append(f"source_type = ${param_count}")
                params.append(source_type)
            
            if source_identifier:
                param_count += 1
                conditions.append(f"source_identifier = ${param_count}")
                params.append(source_identifier)
            
            if metadata_filter:
                for key, value in metadata_filter.items():
                    param_count += 1
                    conditions.append(f"chunk_metadata->>'{key}' = ${param_count}")
                    params.append(str(value))
            
            # Build query
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            param_count += 1
            limit_clause = f"LIMIT ${param_count}"
            params.append(limit)
            
            param_count += 1
            offset_clause = f"OFFSET ${param_count}"
            params.append(offset)
            
            query = f"""
                SELECT chunk_uuid, source_type, source_identifier, 
                       chunk_text_summary, chunk_metadata, ingestion_timestamp,
                       source_last_modified_at, source_content_hash, 
                       last_indexed_at, ingestion_status
                FROM document_chunks 
                {where_clause}
                ORDER BY ingestion_timestamp DESC
                {limit_clause} {offset_clause}
            """
            
            async with self.get_connection() as conn:
                rows = await conn.fetch(query, *params)
                
                results = []
                for row in rows:
                    result = ChunkSearchResult(
                        chunk_uuid=str(row['chunk_uuid']),
                        source_type=row['source_type'],
                        source_identifier=row['source_identifier'],
                        chunk_text_summary=row['chunk_text_summary'],
                        chunk_metadata=row['chunk_metadata'] or {},
                        ingestion_timestamp=row['ingestion_timestamp'],
                        source_last_modified_at=row['source_last_modified_at'],
                        source_content_hash=row['source_content_hash'],
                        last_indexed_at=row['last_indexed_at'],
                        ingestion_status=row['ingestion_status']
                    )
                    results.append(result)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Failed to search chunks: {e}")
            return []
    
    async def delete_chunks_by_source(self, source_identifier: str) -> int:
        """
        Delete all chunks for a specific source.
        
        Args:
            source_identifier: Source identifier to delete
            
        Returns:
            Number of chunks deleted
        """
        try:
            async with self.get_connection() as conn:
                result = await conn.execute("""
                    DELETE FROM document_chunks 
                    WHERE source_identifier = $1
                """, source_identifier)
                
                # Extract count from result string like "DELETE 5"
                deleted_count = int(result.split()[-1])
                self.logger.info(f"Deleted {deleted_count} chunks for source {source_identifier}")
                
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to delete chunks for source {source_identifier}: {e}")
            return 0
    
    async def get_source_stats(self) -> Dict[str, Any]:
        """Get statistics about sources and chunks."""
        try:
            async with self.get_connection() as conn:
                stats = {}
                
                # Total chunks
                total_chunks = await conn.fetchval("SELECT COUNT(*) FROM document_chunks")
                stats['total_chunks'] = total_chunks
                
                # Chunks by source type
                source_type_stats = await conn.fetch("""
                    SELECT source_type, COUNT(*) as count 
                    FROM document_chunks 
                    GROUP BY source_type
                """)
                stats['by_source_type'] = {row['source_type']: row['count'] for row in source_type_stats}
                
                # Recent ingestion activity
                recent_activity = await conn.fetch("""
                    SELECT DATE(ingestion_timestamp) as date, COUNT(*) as count
                    FROM document_chunks 
                    WHERE ingestion_timestamp >= NOW() - INTERVAL '7 days'
                    GROUP BY DATE(ingestion_timestamp)
                    ORDER BY date DESC
                """)
                stats['recent_activity'] = [
                    {'date': row['date'].isoformat(), 'count': row['count']} 
                    for row in recent_activity
                ]
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get source stats: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.get_connection() as conn:
                # Simple query to check connectivity
                result = await conn.fetchval("SELECT 1")
                return result == 1
                
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self):
        """Close database connections and connector."""
        if self._connector:
            await self._connector.close_async()
            self._connector = None
            self.logger.info("Database connector closed") 