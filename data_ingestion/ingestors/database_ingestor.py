"""
Database Ingestor - specialized for PostgreSQL chunk metadata ingestion.

This component handles:
- Document chunk metadata storage
- Batch insert operations
- Data validation and cleaning
- Ingestion statistics tracking
"""

import uuid
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncpg
from contextlib import asynccontextmanager

from config.configuration import DatabaseConfig
from ..models import ChunkData, BatchOperationResult, IngestionStatus

logger = logging.getLogger(__name__)


class DatabaseIngestor:
    """
    Specialized component for database ingestion operations.
    
    This class focuses purely on write operations:
    - Storing document chunk metadata
    - Batch processing for efficiency
    - Data validation and cleaning
    - Transaction management
    - Ingestion monitoring
    """
    
    def __init__(self, 
                 config: DatabaseConfig,
                 connector):
        """
        Initialize DatabaseIngestor with shared database resources.
        
        Args:
            config: Database configuration
            connector: Shared Cloud SQL connector instance
        """
        self.config = config
        self.connector = connector
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Ingestion statistics
        self._total_processed = 0
        self._total_successful = 0
        self._total_failed = 0
        self._current_batch_size = 100
    
    async def initialize(self) -> bool:
        """
        Initialize ingestor and validate database connectivity.
        
        Returns:
            True if initialization successful
        """
        try:
            # Test database connection
            async with self._get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                if result != 1:
                    raise RuntimeError("Database connectivity test failed")
            
            self.logger.info("DatabaseIngestor initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DatabaseIngestor: {e}")
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
    
    async def store_chunk(self, chunk: ChunkData) -> bool:
        """
        Store a single document chunk.
        
        Args:
            chunk: ChunkData object to store
            
        Returns:
            True if successful
        """
        try:
            # Validate chunk data
            validated_chunk = self._validate_and_clean_chunk(chunk)
            if not validated_chunk:
                return False
            
            # Serialize metadata to JSON string for PostgreSQL
            import json
            metadata_json = json.dumps(validated_chunk.chunk_metadata) if validated_chunk.chunk_metadata else "{}"
            
            async with self._get_connection() as conn:
                await conn.execute("""
                    INSERT INTO document_chunks 
                    (chunk_uuid, source_type, source_identifier, chunk_text_summary, 
                     chunk_metadata, ingestion_timestamp, source_last_modified_at, 
                     source_content_hash, last_indexed_at, ingestion_status)
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
                str(validated_chunk.chunk_uuid),
                validated_chunk.source_type.value,
                validated_chunk.source_identifier,
                validated_chunk.chunk_text_summary,
                metadata_json,
                validated_chunk.ingestion_timestamp,
                validated_chunk.source_last_modified_at,
                validated_chunk.source_content_hash,
                validated_chunk.last_indexed_at,
                validated_chunk.ingestion_status.value
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store chunk {chunk.chunk_uuid}: {e}")
            return False
    
    async def batch_store_chunks(self, chunks: List[ChunkData]) -> BatchOperationResult:
        """
        Store multiple document chunks in batch.
        
        Args:
            chunks: List of ChunkData objects to store
            
        Returns:
            BatchOperationResult with operation statistics
        """
        start_time = datetime.now()
        
        if not chunks:
            return BatchOperationResult(
                successful_count=0,
                total_count=0,
                processing_time_ms=0.0
            )
        
        try:
            self.logger.info(f"Starting batch storage of {len(chunks)} chunks")
            
            # Validate and clean all chunks
            valid_chunks = []
            validation_errors = []
            
            for i, chunk in enumerate(chunks):
                try:
                    validated_chunk = self._validate_and_clean_chunk(chunk)
                    if validated_chunk:
                        valid_chunks.append(validated_chunk)
                    else:
                        validation_errors.append(f"Chunk {i}: Validation failed")
                except Exception as e:
                    validation_errors.append(f"Chunk {i}: {str(e)}")
            
            if not valid_chunks:
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                return BatchOperationResult(
                    successful_count=0,
                    total_count=len(chunks),
                    processing_time_ms=processing_time,
                    error_messages=validation_errors
                )
            
            # Perform batch insert
            successful_count = await self._batch_insert(valid_chunks)
            
            # Update statistics
            self._total_processed += len(chunks)
            self._total_successful += successful_count
            self._total_failed += len(chunks) - successful_count
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = BatchOperationResult(
                successful_count=successful_count,
                total_count=len(chunks),
                failed_items=[f"Chunk {i}" for i in range(len(chunks)) if i >= successful_count],
                processing_time_ms=processing_time,
                error_messages=validation_errors if validation_errors else []
            )
            
            self.logger.info(f"Batch storage completed: {successful_count}/{len(chunks)} successful")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Batch storage failed: {e}")
            
            return BatchOperationResult(
                successful_count=0,
                total_count=len(chunks),
                processing_time_ms=processing_time,
                error_messages=[str(e)]
            )
    
    def _validate_and_clean_chunk(self, chunk: ChunkData) -> Optional[ChunkData]:
        """
        Validate and clean chunk data for database storage.
        
        Args:
            chunk: ChunkData to validate
            
        Returns:
            Cleaned ChunkData or None if validation fails
        """
        try:
            # Validate UUID format
            uuid.UUID(str(chunk.chunk_uuid))
            
            # Clean and validate text summary
            text_summary = chunk.chunk_text_summary
            if text_summary and len(text_summary) > 10000:
                text_summary = text_summary[:9997] + "..."
                self.logger.warning(f"Truncated text_summary for chunk {chunk.chunk_uuid}")
            
            # Validate and clean source fields
            source_type = chunk.source_type
            source_identifier = chunk.source_identifier[:512] if chunk.source_identifier else ""
            
            # Validate and clean JSON metadata
            chunk_metadata = self._clean_metadata_for_json(chunk.chunk_metadata or {})
            
            # Create cleaned chunk
            return ChunkData(
                chunk_uuid=chunk.chunk_uuid,
                source_type=source_type,
                source_identifier=source_identifier,
                chunk_text_summary=text_summary,
                chunk_metadata=chunk_metadata,
                ingestion_timestamp=chunk.ingestion_timestamp or datetime.now(),
                source_last_modified_at=chunk.source_last_modified_at,
                source_content_hash=chunk.source_content_hash,
                last_indexed_at=chunk.last_indexed_at or datetime.now(),
                ingestion_status=chunk.ingestion_status or IngestionStatus.COMPLETED
            )
            
        except Exception as e:
            self.logger.error(f"Validation failed for chunk {chunk.chunk_uuid}: {e}")
            return None
    
    def _clean_metadata_for_json(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean metadata dictionary to ensure JSON serialization compatibility.
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Cleaned metadata dictionary safe for JSON storage
        """
        import json
        from uuid import UUID
        from datetime import datetime
        
        def clean_value(value):
            """Recursively clean values for JSON compatibility."""
            if isinstance(value, (str, int, float, bool)) or value is None:
                return value
            elif isinstance(value, UUID):
                return str(value)
            elif isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, dict):
                return {k: clean_value(v) for k, v in value.items()}
            elif isinstance(value, (list, tuple)):
                return [clean_value(item) for item in value]
            else:
                # Convert any other object to string
                return str(value)
        
        try:
            cleaned_metadata = clean_value(metadata)
            
            # Validate that it can actually be JSON serialized
            json.dumps(cleaned_metadata)
            
            return cleaned_metadata
            
        except Exception as e:
            self.logger.warning(f"Failed to clean metadata, using empty dict: {e}")
            return {}
    
    async def _batch_insert(self, chunks: List[ChunkData]) -> int:
        """
        Perform optimized batch insert operation.
        
        Args:
            chunks: List of validated ChunkData objects
            
        Returns:
            Number of successfully inserted chunks
        """
        if not chunks:
            return 0
        
        try:
            # Prepare values for batch insert
            import json
            values = []
            for chunk in chunks:
                # Serialize metadata to JSON string for PostgreSQL
                metadata_json = json.dumps(chunk.chunk_metadata) if chunk.chunk_metadata else "{}"
                values.append((
                    str(chunk.chunk_uuid),
                    chunk.source_type.value,
                    chunk.source_identifier,
                    chunk.chunk_text_summary,
                    metadata_json,
                    chunk.ingestion_timestamp,
                    chunk.source_last_modified_at,
                    chunk.source_content_hash,
                    chunk.last_indexed_at,
                    chunk.ingestion_status.value
                ))
            
            async with self._get_connection() as conn:
                # Use executemany for efficient batch insert
                await conn.executemany("""
                    INSERT INTO document_chunks 
                    (chunk_uuid, source_type, source_identifier, chunk_text_summary, 
                     chunk_metadata, ingestion_timestamp, source_last_modified_at, 
                     source_content_hash, last_indexed_at, ingestion_status)
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
            
            self.logger.info(f"Successfully batch inserted {len(chunks)} chunks")
            return len(chunks)
            
        except Exception as e:
            self.logger.error(f"Batch insert failed: {e}")
            
            # Fallback to individual inserts
            self.logger.info("Falling back to individual chunk inserts...")
            successful_count = 0
            for chunk in chunks:
                if await self.store_chunk(chunk):
                    successful_count += 1
            
            return successful_count
    
    async def update_ingestion_status(self, 
                                    chunk_uuids: List[str], 
                                    status: IngestionStatus) -> int:
        """
        Update ingestion status for multiple chunks.
        
        Args:
            chunk_uuids: List of chunk UUIDs to update
            status: New ingestion status
            
        Returns:
            Number of chunks updated
        """
        if not chunk_uuids:
            return 0
        
        try:
            async with self._get_connection() as conn:
                result = await conn.execute("""
                    UPDATE document_chunks 
                    SET ingestion_status = $1, last_indexed_at = $2
                    WHERE chunk_uuid = ANY($3::uuid[])
                """, status.value, datetime.now(), chunk_uuids)
                
                # Extract number from result string like "UPDATE 5"
                updated_count = int(result.split()[-1]) if result.startswith("UPDATE") else 0
                
                self.logger.info(f"Updated ingestion status for {updated_count} chunks to {status.value}")
                return updated_count
                
        except Exception as e:
            self.logger.error(f"Failed to update ingestion status: {e}")
            return 0
    
    async def delete_chunks_by_source(self, source_identifier: str) -> int:
        """
        Delete all chunks for a specific source.
        
        Args:
            source_identifier: Source identifier to delete
            
        Returns:
            Number of chunks deleted
        """
        try:
            async with self._get_connection() as conn:
                result = await conn.execute("""
                    DELETE FROM document_chunks 
                    WHERE source_identifier = $1
                """, source_identifier)
                
                deleted_count = int(result.split()[-1]) if result.startswith("DELETE") else 0
                
                self.logger.info(f"Deleted {deleted_count} chunks for source: {source_identifier}")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to delete chunks for source {source_identifier}: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get ingestion statistics.
        
        Returns:
            Dictionary with ingestion statistics
        """
        return {
            "total_processed": self._total_processed,
            "total_successful": self._total_successful,
            "total_failed": self._total_failed,
            "success_rate": (self._total_successful / self._total_processed * 100) if self._total_processed > 0 else 0.0,
            "current_batch_size": self._current_batch_size
        }
    
    async def close(self):
        """Close ingestor and clean up resources."""
        self.logger.info(f"DatabaseIngestor closed. Final stats: {self.get_statistics()}") 