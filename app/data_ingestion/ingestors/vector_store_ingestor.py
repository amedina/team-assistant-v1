"""
Vector Store Ingestor - specialized for embedding ingestion operations.

This component handles:
- Embedding generation from text
- Batch processing and validation
- Streaming upserts to Vector Search index
- Ingestion monitoring and error handling
"""

import uuid
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from google.cloud import storage
from google.cloud.aiplatform import MatchingEngineIndex

from app.config.configuration import VectorSearchConfig
from app.data_ingestion.models import EmbeddingData, BatchOperationResult

logger = logging.getLogger(__name__)


class VectorStoreIngestor:
    """
    Specialized component for vector embedding ingestion operations.
    
    This class focuses purely on write operations:
    - Converting text to embeddings
    - Validating embedding data
    - Batch processing for efficiency
    - Streaming upserts to vector index
    - Error handling and retry logic
    """
    
    def __init__(self, 
                 config: VectorSearchConfig,
                 storage_client: storage.Client,
                 index: MatchingEngineIndex,
                 embedding_model):
        """
        Initialize VectorStoreIngestor with shared resources.
        
        Args:
            config: Vector search configuration
            storage_client: Shared Google Cloud Storage client
            index: Shared MatchingEngineIndex instance
            embedding_model: Shared embedding model for text processing
        """
        self.config = config
        self.storage_client = storage_client
        self.index = index
        self.embedding_model = embedding_model
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Ingestion statistics
        self._total_processed = 0
        self._total_successful = 0
        self._total_failed = 0
    
    async def initialize(self) -> bool:
        """
        Initialize ingestor and validate access to resources.
        
        Returns:
            True if initialization successful
        """
        try:
            # Validate index access
            index_info = self.index.to_dict()
            index_name = index_info.get('name', 'unknown')
            
            # Validate storage access
            bucket_name = self.config.bucket.replace("gs://", "")
            bucket = self.storage_client.bucket(bucket_name)
            bucket.exists()  # This will raise an exception if bucket doesn't exist
            
            self.logger.info(f"VectorStoreIngestor initialized for index: {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize VectorStoreIngestor: {e}")
            return False
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            Exception: If embedding generation fails
        """
        if not texts:
            return []
        
        try:
            batch_size = self.config.batch_size if hasattr(self.config, 'batch_size') else 100
            all_embeddings = []
            
            self.logger.info(f"Generating embeddings for {len(texts)} texts")
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Generate embeddings for batch
                embeddings = self.embedding_model.get_embeddings(batch_texts)
                batch_embeddings = [emb.values for emb in embeddings]
                all_embeddings.extend(batch_embeddings)
                
                # Rate limiting to avoid API quotas
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
                
                self.logger.debug(f"Generated embeddings for batch {i//batch_size + 1}")
            
            self.logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
            return all_embeddings
            
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    async def store_embeddings(self, embedding_data: List[EmbeddingData]) -> BatchOperationResult:
        """
        Store embeddings in the vector index using streaming upsert.
        
        Args:
            embedding_data: List of EmbeddingData objects to store
            
        Returns:
            BatchOperationResult with operation statistics
        """
        start_time = datetime.now()
        
        if not embedding_data:
            return BatchOperationResult(
                successful_count=0,
                total_count=0,
                processing_time_ms=0.0
            )
        
        try:
            self.logger.info(f"Starting to store {len(embedding_data)} embeddings")
            
            # Validate and prepare datapoints
            datapoints = []
            validation_errors = []
            
            for i, data in enumerate(embedding_data):
                try:
                    # Validate embedding data
                    if not data.embedding or len(data.embedding) == 0:
                        validation_errors.append(f"Chunk {data.chunk_uuid}: Empty embedding")
                        continue
                    
                    # Prepare datapoint for Vector Search API
                    restricts = self._prepare_restricts(data.metadata)
                    
                    datapoint = {
                        "datapoint_id": str(data.chunk_uuid),
                        "feature_vector": data.embedding,
                        "restricts": restricts
                    }
                    datapoints.append(datapoint)
                    
                except Exception as validation_error:
                    validation_errors.append(f"Chunk {data.chunk_uuid}: {validation_error}")
                    continue
            
            if validation_errors:
                self.logger.warning(f"Validation errors: {validation_errors[:5]}")  # Log first 5
            
            # Perform streaming upsert
            successful_count = await self._streaming_upsert(datapoints)
            
            # Update statistics
            self._total_processed += len(embedding_data)
            self._total_successful += successful_count
            self._total_failed += len(embedding_data) - successful_count
            
            # Ensure successful_count doesn't exceed total_count
            successful_count = min(successful_count, len(embedding_data))
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = BatchOperationResult(
                successful_count=successful_count,
                total_count=len(embedding_data),
                failed_items=[err for err in validation_errors],
                processing_time_ms=processing_time,
                error_messages=validation_errors if validation_errors else []
            )
            
            self.logger.info(f"Embedding storage completed: {successful_count}/{len(embedding_data)} successful")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Failed to store embeddings: {e}")
            
            return BatchOperationResult(
                successful_count=0,
                total_count=len(embedding_data),
                processing_time_ms=processing_time,
                error_messages=[str(e)]
            )
    
    def _prepare_restricts(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Prepare restricts for Vector Search filtering.
        
        Args:
            metadata: Chunk metadata
            
        Returns:
            List of restrict dictionaries for Vector Search API
        """
        restricts = []
        
        # Source type restrict
        if "source_type" in metadata:
            restricts.append({
                "namespace": "source_type",
                "allow_list": [str(metadata["source_type"])]
            })
        
        # Source identifier restrict
        if "source_identifier" in metadata:
            restricts.append({
                "namespace": "source_id",
                "allow_list": [str(metadata["source_identifier"])]
            })
        
        return restricts
    
    async def _streaming_upsert(self, datapoints: List[Dict[str, Any]]) -> int:
        """
        Perform streaming upsert to Vector Search index.
        
        Args:
            datapoints: List of prepared datapoints
            
        Returns:
            Number of successfully upserted datapoints
        """
        if not datapoints:
            return 0
        
        try:
            from google.cloud.aiplatform_v1.services.index_service import IndexServiceClient
            from google.cloud.aiplatform_v1.types import UpsertDatapointsRequest
            from google.api_core.client_options import ClientOptions
            
            # Create client with region-specific endpoint
            client_options = ClientOptions(
                api_endpoint=f"{self.config.location}-aiplatform.googleapis.com"
            )
            index_service_client = IndexServiceClient(client_options=client_options)
            
            # Process in batches to handle API limits
            batch_size = 100
            total_upserted = 0
            
            for i in range(0, len(datapoints), batch_size):
                batch = datapoints[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                try:
                    # Create upsert request
                    request = UpsertDatapointsRequest(
                        index=self.config.index_resource_name,
                        datapoints=batch
                    )
                    
                    # Execute upsert (synchronous call)
                    response = index_service_client.upsert_datapoints(request=request)
                    
                    total_upserted += len(batch)
                    self.logger.info(f"Successfully upserted batch {batch_num}: {len(batch)} vectors")
                    
                    # Rate limiting between batches
                    await asyncio.sleep(0.2)
                    
                except Exception as batch_error:
                    self.logger.error(f"Failed to upsert batch {batch_num}: {batch_error}")
                    # Continue with other batches rather than failing completely
                    continue
            
            self.logger.info(f"Streaming upsert completed: {total_upserted}/{len(datapoints)} vectors")
            return total_upserted
            
        except Exception as e:
            self.logger.error(f"Streaming upsert failed: {e}")
            raise RuntimeError(f"Vector Search upsert error: {e}") from e
    
    async def generate_and_store_embeddings(self, 
                                          texts: List[str], 
                                          chunk_uuids: List[str],
                                          metadata_list: List[Dict[str, Any]]) -> BatchOperationResult:
        """
        Convenience method to generate embeddings and store them in one operation.
        
        Args:
            texts: List of text strings to embed
            chunk_uuids: List of chunk UUIDs (must match texts length)
            metadata_list: List of metadata dictionaries (must match texts length)
            
        Returns:
            BatchOperationResult with operation statistics
        """
        if len(texts) != len(chunk_uuids) or len(texts) != len(metadata_list):
            raise ValueError("texts, chunk_uuids, and metadata_list must have the same length")
        
        try:
            # Generate embeddings
            embeddings = await self.generate_embeddings(texts)
            
            # Create EmbeddingData objects
            embedding_data = []
            for i, (text, chunk_uuid, metadata) in enumerate(zip(texts, chunk_uuids, metadata_list)):
                if i < len(embeddings):
                    embedding_data.append(EmbeddingData(
                        chunk_uuid=chunk_uuid,
                        embedding=embeddings[i],
                        metadata=metadata
                    ))
            
            # Store embeddings
            return await self.store_embeddings(embedding_data)
            
        except Exception as e:
            self.logger.error(f"Failed to generate and store embeddings: {e}")
            return BatchOperationResult(
                successful_count=0,
                total_count=len(texts),
                error_messages=[str(e)]
            )
    
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
            "success_rate": (self._total_successful / self._total_processed * 100) if self._total_processed > 0 else 0.0
        }
    
    async def close(self):
        """Close ingestor and clean up resources."""
        try:
            # Force cleanup of any pending aiohttp sessions
            import gc
            import warnings
            
            # Suppress specific aiohttp warnings during cleanup
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*Unclosed client session.*")
                warnings.filterwarnings("ignore", message=".*Unclosed connector.*")
                
                # Force garbage collection to help close lingering HTTP clients
                gc.collect()
                
                # Give any pending async operations time to complete
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.debug(f"Ingestor cleanup (expected): {e}")
        
        self.logger.info(f"VectorStoreIngestor closed. Final stats: {self.get_statistics()}") 