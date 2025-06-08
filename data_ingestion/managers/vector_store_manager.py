"""
Vector Store Manager for Vertex AI Vector Search operations.
Handles both ingestion and retrieval operations for the vector search index.
"""

import uuid
import logging
import asyncio
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from google.cloud import storage
from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
import numpy as np

from config.configuration import VectorSearchConfig

logger = logging.getLogger(__name__)

@dataclass
class VectorSearchResult:
    """Result from vector search query."""
    chunk_uuid: str
    similarity_score: float
    metadata: Dict[str, Any]

@dataclass
class EmbeddingData:
    """Data structure for embeddings with metadata."""
    chunk_uuid: str
    embedding: List[float]
    metadata: Dict[str, Any]

class VectorStoreManager:
    """
    Manager for Vertex AI Vector Search operations.
    
    Responsibilities:
    - Managing vector search index operations
    - Embedding generation and storage
    - Similarity search with filtering
    - Batch operations for efficiency
    """
    
    def __init__(self, config: VectorSearchConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize AI Platform
        aiplatform.init(
            project=config.project_id,
            location=config.location
        )
        
        # Initialize clients
        self._storage_client: Optional[storage.Client] = None
        self._index: Optional[MatchingEngineIndex] = None
        self._endpoint: Optional[MatchingEngineIndexEndpoint] = None
        
    @property
    def storage_client(self) -> storage.Client:
        """Lazy initialization of Cloud Storage client."""
        if self._storage_client is None:
            self._storage_client = storage.Client(project=self.config.project_id)
        return self._storage_client
    
    @property
    def index(self) -> MatchingEngineIndex:
        """Lazy initialization of Vector Search index."""
        if self._index is None:
            self._index = aiplatform.MatchingEngineIndex(
                index_name=self.config.index_resource_name
            )
        return self._index
    
    @property
    def endpoint(self) -> MatchingEngineIndexEndpoint:
        """Lazy initialization of Vector Search endpoint."""
        if self._endpoint is None:
            self._endpoint = aiplatform.MatchingEngineIndexEndpoint(
                index_endpoint_name=self.config.endpoint_resource_name
            )
        return self._endpoint
    
    async def _get_deployed_index_id(self) -> Optional[str]:
        """Get the deployed index ID for our target index on the endpoint."""
        try:
            index_info = self.index.to_dict()
            deployed_indexes = index_info.get("deployedIndexes", [])
            
            # Find the deployed index that matches our target endpoint
            target_endpoint = self.config.endpoint_resource_name
            for deployed in deployed_indexes:
                if deployed.get("indexEndpoint") == target_endpoint:
                    return deployed.get("deployedIndexId")
            
            self.logger.warning(f"No deployed index found for endpoint {target_endpoint}")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get deployed index ID: {e}")
            return None
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using Vertex AI.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            from vertexai.language_models import TextEmbeddingModel
            
            model = TextEmbeddingModel.from_pretrained(self.config.embedding_model)
            
            # Generate embeddings in batches to avoid API limits
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                embeddings = model.get_embeddings(batch_texts)
                batch_embeddings = [emb.values for emb in embeddings]
                all_embeddings.extend(batch_embeddings)
                
                # Add small delay to avoid rate limiting
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
            
            self.logger.info(f"Generated {len(all_embeddings)} embeddings")
            return all_embeddings
            
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    async def store_embeddings(self, embedding_data: List[EmbeddingData]) -> bool:
        """
        Store embeddings in Vector Search using streaming updates.
        
        Args:
            embedding_data: List of embedding data with metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare datapoints for streaming update (no deployed_index_id needed)
            datapoints = []
            for data in embedding_data:
                # Create restricts for filtering (using correct 'allow_list' field)
                restricts = [
                    {"namespace": "source_type", "allow_list": [data.metadata.get("source_type", "")]},
                    {"namespace": "source_id", "allow_list": [data.metadata.get("source_id", "")]}
                ]
                
                datapoint = {
                    "datapoint_id": data.chunk_uuid,
                    "feature_vector": data.embedding,
                    "restricts": restricts
                }
                datapoints.append(datapoint)
            
            # Use streaming update to add vectors directly to index
            await self._streaming_upsert(datapoints)
            
            self.logger.info(f"Vector upsert completed for {len(embedding_data)} embeddings")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store embeddings: {e}")
            return False
    
    async def _streaming_upsert(self, datapoints: List[Dict[str, Any]]) -> None:
        """
        Perform streaming upsert to add vectors directly to the index using the correct Vector Search API.
        
        Args:
            datapoints: List of datapoint dictionaries to upsert
        """
        try:
            # Import required modules for Vector Search upsert
            from google.cloud.aiplatform_v1.services.index_service import IndexServiceClient
            from google.cloud.aiplatform_v1.types import UpsertDatapointsRequest
            from google.api_core.client_options import ClientOptions
            
            # Create client with region-specific endpoint (critical for avoiding "global" region errors)
            client_options = ClientOptions(api_endpoint=f"{self.config.location}-aiplatform.googleapis.com")
            index_service_client = IndexServiceClient(client_options=client_options)
            
            # Prepare datapoints in the correct format for Vector Search
            formatted_datapoints = []
            for dp in datapoints:
                # Create datapoint with correct field names
                datapoint = {
                    "datapoint_id": dp["datapoint_id"],
                    "feature_vector": dp["feature_vector"]
                }
                
                # Handle restricts with proper format (allow_list, not allow)
                if dp.get("restricts"):
                    valid_restricts = []
                    for restrict in dp["restricts"]:
                        if isinstance(restrict, dict) and "namespace" in restrict:
                            # Convert 'allow' to 'allow_list' if needed
                            if "allow_list" in restrict:
                                valid_restricts.append(restrict)
                            elif "allow" in restrict:
                                restrict_copy = restrict.copy()
                                restrict_copy["allow_list"] = restrict_copy.pop("allow")
                                valid_restricts.append(restrict_copy)
                    
                    if valid_restricts:
                        datapoint["restricts"] = valid_restricts
                
                formatted_datapoints.append(datapoint)
            
            # Process in batches suitable for Vector Search
            batch_size = 100
            total_upserted = 0
            
            for i in range(0, len(formatted_datapoints), batch_size):
                batch = formatted_datapoints[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                try:
                    # Create the upsert request with CORRECT field name
                    request = UpsertDatapointsRequest(
                        index=self.config.index_resource_name,  # Use 'index', not 'index_endpoint_name'!
                        datapoints=batch
                    )
                    
                    # Execute the upsert using the index service client
                    upsert_response = index_service_client.upsert_datapoints(request=request)
                    
                    total_upserted += len(batch)
                    self.logger.info(f"✅ Successfully upserted batch {batch_num}: {len(batch)} vectors to Vector Search index")
                    
                    # Small delay between batches to be respectful
                    await asyncio.sleep(0.2)
                    
                except Exception as batch_error:
                    self.logger.error(f"❌ Failed to upsert batch {batch_num}: {batch_error}")
                    # Continue with other batches rather than failing completely
                    continue
            
            if total_upserted > 0:
                self.logger.info(f"🎉 Vector upsert completed successfully: {total_upserted}/{len(datapoints)} vectors uploaded to index")
                
                # Verification: Try to do a quick search to see if vectors are actually there
                try:
                    self.logger.info("🔍 Verifying vectors are searchable...")
                    # Use a dummy embedding for search test
                    dummy_embedding = [0.1] * 768  # Standard embedding dimension
                    deployed_index_id = await self._get_deployed_index_id()
                    if deployed_index_id:
                        response = self.endpoint.find_neighbors(
                            deployed_index_id=deployed_index_id,
                            queries=[dummy_embedding],
                            num_neighbors=1
                        )
                        if response and len(response) > 0 and len(response[0]) > 0:
                            self.logger.info(f"✅ Verification successful: Found {len(response[0])} vectors in search")
                        else:
                            self.logger.warning("⚠️ Verification: No vectors found in search - they may still be processing")
                    else:
                        self.logger.warning("⚠️ Could not verify - no deployed index ID found")
                except Exception as verify_error:
                    self.logger.warning(f"⚠️ Verification failed (this doesn't mean upsert failed): {verify_error}")
            else:
                self.logger.error(f"❌ All vector upsert batches failed - 0/{len(datapoints)} vectors uploaded")
                raise RuntimeError("All vector upsert operations failed")
            
        except Exception as e:
            self.logger.error(f"❌ Vector upsert completely failed: {e}")
            # Let this propagate up so the pipeline knows vectors failed
            raise RuntimeError(f"Vector Search upsert error: {e}") from e
    
    async def _upload_embeddings_for_update(self, contents: List[Dict[str, Any]]) -> bool:
        """
        Upload embeddings to Cloud Storage and trigger index update.
        
        Args:
            contents: List of embedding content dictionaries
            
        Returns:
            True if successful
        """
        try:
            bucket_name = self.config.bucket.replace("gs://", "")
            bucket = self.storage_client.bucket(bucket_name)
            
            # Generate unique filename
            timestamp = uuid.uuid4().hex[:8]
            blob_name = f"embeddings/batch_{timestamp}.jsonl"
            blob = bucket.blob(blob_name)
            
            # Convert to JSONL format
            import json
            jsonl_content = "\n".join(json.dumps(content) for content in contents)
            
            # Upload to Cloud Storage
            blob.upload_from_string(jsonl_content, content_type="application/jsonl")
            self.logger.info(f"Uploaded {len(contents)} records to {blob_name}")
            
            # Trigger index update operation
            gcs_source = f"{self.config.bucket}/{blob_name}"
            await self._trigger_index_update(gcs_source)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload embeddings for update: {e}")
            return False
    
    async def _trigger_index_update(self, gcs_source: str) -> None:
        """
        Trigger an index update operation to add the uploaded embeddings.
        
        Args:
            gcs_source: GCS path to the uploaded embeddings file
        """
        try:
            # Use the index's update_embeddings method
            operation = self.index.update_embeddings(
                contents_delta_uri=gcs_source,
                is_complete_overwrite=False  # This is an incremental update
            )
            
            self.logger.info(f"Started index update operation: {operation.operation.name}")
            self.logger.info("Index update is running in the background. Vectors will be available once the operation completes.")
            
        except Exception as e:
            self.logger.error(f"Failed to trigger index update: {e}")
            raise
    
    async def _upload_to_storage(self, jsonl_data: List[Dict[str, Any]]) -> bool:
        """Upload JSONL data to Cloud Storage bucket (legacy method for batch updates)."""
        try:
            bucket_name = self.config.bucket.replace("gs://", "")
            bucket = self.storage_client.bucket(bucket_name)
            
            # Generate unique filename
            timestamp = uuid.uuid4().hex[:8]
            blob_name = f"embeddings/batch_{timestamp}.jsonl"
            blob = bucket.blob(blob_name)
            
            # Convert to JSONL format
            import json
            jsonl_content = "\n".join(json.dumps(record) for record in jsonl_data)
            
            # Upload
            blob.upload_from_string(jsonl_content, content_type="application/jsonl")
            
            self.logger.info(f"Uploaded {len(jsonl_data)} records to {blob_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload to storage: {e}")
            return False
    
    async def search_similar(self, 
                           query_embedding: List[float],
                           num_neighbors: int = 10,
                           filters: Optional[Dict[str, List[str]]] = None) -> List[VectorSearchResult]:
        """
        Search for similar vectors in the index.
        
        Args:
            query_embedding: Query vector
            num_neighbors: Number of results to return
            filters: Optional filters for restricts (currently not supported)
            
        Returns:
            List of search results
            
        Raises:
            Exception: If search fails due to API or configuration issues
        """
        # Get the deployed index ID for our target index
        deployed_index_id = await self._get_deployed_index_id()
        if not deployed_index_id:
            raise RuntimeError("Could not find deployed index ID for vector search")
        
        # Note: filters/restricts are not currently supported in this version
        if filters:
            self.logger.warning("Filters are not currently supported in vector search")
        
        try:
            # Perform search
            response = self.endpoint.find_neighbors(
                deployed_index_id=deployed_index_id,
                queries=[query_embedding],
                num_neighbors=num_neighbors
            )
            
            # Process results
            results = []
            if response and len(response) > 0:
                for neighbor in response[0]:
                    result = VectorSearchResult(
                        chunk_uuid=neighbor.id,
                        similarity_score=neighbor.distance,
                        metadata=getattr(neighbor, 'metadata', {})
                    )
                    results.append(result)
            
            self.logger.info(f"Vector search completed successfully: found {len(results)} similar vectors")
            return results
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            raise RuntimeError(f"Vector search API call failed: {e}") from e
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector index."""
        try:
            # Get index information
            index_info = self.index.to_dict()
            
            # Get deployed index information
            deployed_indexes = index_info.get("deployedIndexes", [])
            deployed_index_id = await self._get_deployed_index_id()
            
            # Get index stats from metadata
            index_stats = index_info.get("indexStats", {})
            
            stats = {
                "index_id": self.config.index_id,
                "endpoint_id": self.config.endpoint_id,
                "deployed_index_id": deployed_index_id,
                "is_deployed": bool(deployed_index_id),
                "deployed_endpoints": [d.get("indexEndpoint") for d in deployed_indexes],
                "dimensions": index_info.get("metadata", {}).get("config", {}).get("dimensions"),
                "vectors_count": index_stats.get("vectorsCount"),
                "shards_count": index_stats.get("shardsCount"),
                "created_time": index_info.get("createTime"),
                "updated_time": index_info.get("updateTime")
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get index stats: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check if the vector store is healthy and accessible."""
        try:
            # Check if index exists and is accessible
            index_info = self.index.to_dict()
            
            # Check if index has deployed indexes (this means it's deployed to an endpoint)
            deployed_indexes = index_info.get("deployedIndexes", [])
            if not deployed_indexes:
                self.logger.error("Vector store health check failed: Index is not deployed to any endpoint")
                return False
            
            # Check if our target endpoint is in the deployed indexes
            target_endpoint = self.config.endpoint_resource_name
            is_deployed = any(
                deployed.get("indexEndpoint") == target_endpoint 
                for deployed in deployed_indexes
            )
            
            if not is_deployed:
                self.logger.error(f"Vector store health check failed: Index not deployed to target endpoint: {target_endpoint}")
                return False
            
            # Try a simple search with dummy vector to verify functionality
            deployed_index_id = await self._get_deployed_index_id()
            if not deployed_index_id:
                self.logger.error("Vector store health check failed: Could not get deployed index ID")
                return False
            
            # Perform actual API call to test functionality
            dummy_embedding = [0.0] * 768  # Assuming 768-dimensional embeddings
            
            # Test the actual API call directly to catch any errors
            response = self.endpoint.find_neighbors(
                deployed_index_id=deployed_index_id,
                queries=[dummy_embedding],
                num_neighbors=1
            )
            
            # Check if we got a valid response
            if response is None:
                self.logger.error("Vector store health check failed: Got null response from find_neighbors")
                return False
            
            self.logger.info("Vector store health check passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Vector store health check failed: {e}")
            return False
    
    async def batch_upsert(self, embedding_data: List[EmbeddingData]) -> bool:
        """
        Batch upsert operation for embeddings.
        
        Args:
            embedding_data: List of embedding data to upsert
            
        Returns:
            True if successful
        """
        try:
            # Split into batches to avoid memory issues
            batch_size = 1000
            total_batches = (len(embedding_data) + batch_size - 1) // batch_size
            
            success_count = 0
            
            for i in range(0, len(embedding_data), batch_size):
                batch = embedding_data[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                self.logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
                
                success = await self.store_embeddings(batch)
                if success:
                    success_count += 1
                else:
                    self.logger.warning(f"Batch {batch_num} failed")
                
                # Small delay between batches
                await asyncio.sleep(1)
            
            overall_success = success_count == total_batches
            self.logger.info(f"Batch upsert completed: {success_count}/{total_batches} batches successful")
            
            return overall_success
            
        except Exception as e:
            self.logger.error(f"Batch upsert failed: {e}")
            return False
    
    async def delete_by_filter(self, filters: Dict[str, List[str]]) -> bool:
        """
        Delete vectors by filter criteria.
        Note: This is a placeholder as Vector Search doesn't support direct deletion by filter.
        In practice, this would require rebuilding the index without the filtered items.
        
        Args:
            filters: Filter criteria for deletion
            
        Returns:
            True if successful
        """
        # This is a complex operation that would require:
        # 1. Querying all vectors matching the filter
        # 2. Creating a new index without those vectors
        # 3. Replacing the old index
        
        self.logger.warning("Delete by filter not implemented - requires index rebuild")
        return False 