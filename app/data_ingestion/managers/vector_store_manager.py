"""
Vector Store Manager - Coordinator for vector search operations.
Implements the Manager-as-Coordinator pattern with shared resource management.

This component acts as a facade that:
- Manages shared resources (storage client, index, endpoint, embedding model)
- Coordinates between VectorStoreIngestor and VectorStoreRetriever
- Provides unified interface for vector operations
- Handles initialization and health checks
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from google.cloud import storage
from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint

from app.config.configuration import VectorSearchConfig
from app.data_ingestion.models import (
    VectorRetrievalResult, EmbeddingData, BatchOperationResult, 
    ComponentHealth, SystemHealth
)
from app.data_ingestion.ingestors.vector_store_ingestor import VectorStoreIngestor
from app.data_ingestion.retrievers.vector_store_retriever import VectorStoreRetriever

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    Coordinator/Facade for Vertex AI Vector Search operations.
    
    Responsibilities:
    - Managing shared resources (clients, models, connections)
    - Coordinating between ingestor and retriever components
    - Providing unified interface for vector operations
    - Resource lifecycle management and health monitoring
    """
    
    def __init__(self, config: VectorSearchConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize AI Platform
        aiplatform.init(
            project=config.project_id,
            location=config.location
        )
        
        # Shared resources (lazy initialization)
        self._storage_client: Optional[storage.Client] = None
        self._index: Optional[MatchingEngineIndex] = None
        self._endpoint: Optional[MatchingEngineIndexEndpoint] = None
        self._embedding_model = None
        
        # Specialized components (initialized after shared resources)
        self.ingestor: Optional[VectorStoreIngestor] = None
        self.retriever: Optional[VectorStoreRetriever] = None
        
        # Manager state
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize shared resources and component coordination.
        
        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing VectorStoreManager and shared resources...")
            
            # Initialize shared resources
            await self._initialize_shared_resources()
            
            # Initialize specialized components with shared resources
            self.ingestor = VectorStoreIngestor(
                config=self.config,
                storage_client=self._storage_client,
                index=self._index,
                embedding_model=self._embedding_model
            )
            
            self.retriever = VectorStoreRetriever(
                config=self.config,
                index=self._index,
                endpoint=self._endpoint,
                embedding_model=self._embedding_model
            )
            
            # Initialize components
            ingestor_ready = await self.ingestor.initialize()
            retriever_ready = await self.retriever.initialize()
            
            self._initialized = ingestor_ready and retriever_ready
            
            if self._initialized:
                self.logger.info("VectorStoreManager initialization completed successfully")
            else:
                self.logger.error("VectorStoreManager initialization failed - components not ready")
            
            return self._initialized
            
        except Exception as e:
            self.logger.error(f"Failed to initialize VectorStoreManager: {e}")
            return False
    
    async def _initialize_shared_resources(self):
        """Initialize shared resources used by both ingestor and retriever."""
        # Initialize storage client
        self._storage_client = storage.Client(project=self.config.project_id)
        
        # Initialize Vector Search index
        self._index = aiplatform.MatchingEngineIndex(
            index_name=self.config.index_resource_name
        )
        
        # Initialize Vector Search endpoint
        self._endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=self.config.endpoint_resource_name
        )
        
        # Initialize embedding model
        from vertexai.language_models import TextEmbeddingModel
        self._embedding_model = TextEmbeddingModel.from_pretrained(self.config.embedding_model)
        
        self.logger.info("Shared resources initialized successfully")
    
    # =================================================================
    # INGESTION COORDINATION METHODS
    # =================================================================
    
    async def ingest_embeddings(self, embedding_data: List[EmbeddingData]) -> BatchOperationResult:
        """
        Coordinate embedding ingestion through the ingestor component.
        
        Args:
            embedding_data: List of EmbeddingData objects to store
            
        Returns:
            BatchOperationResult with operation statistics
        """
        if not self._initialized:
            raise RuntimeError("VectorStoreManager not initialized. Call initialize() first.")
        
        return await self.ingestor.store_embeddings(embedding_data)
    
    async def generate_and_ingest(self, 
                                texts: List[str], 
                                chunk_uuids: List[str],
                                metadata_list: List[Dict[str, Any]]) -> BatchOperationResult:
        """
        Coordinate embedding generation and ingestion in one operation.
        
        Args:
            texts: List of text strings to embed and store
            chunk_uuids: List of chunk UUIDs (must match texts length)
            metadata_list: List of metadata dictionaries (must match texts length)
            
        Returns:
            BatchOperationResult with operation statistics
        """
        if not self._initialized:
            raise RuntimeError("VectorStoreManager not initialized. Call initialize() first.")
        
        return await self.ingestor.generate_and_store_embeddings(texts, chunk_uuids, metadata_list)
    
    async def batch_ingest(self, embedding_data: List[EmbeddingData]) -> BatchOperationResult:
        """
        Coordinate batch ingestion through the ingestor component.
        
        Args:
            embedding_data: List of embedding data to ingest
            
        Returns:
            BatchOperationResult with operation statistics
        """
        if not self._initialized:
            raise RuntimeError("VectorStoreManager not initialized. Call initialize() first.")
        
        # Use ingestor's batch processing capabilities
        batch_size = 1000
        total_result = BatchOperationResult(
            successful_count=0,
            total_count=len(embedding_data),
            processing_time_ms=0.0
        )
        
        start_time = datetime.now()
        
        for i in range(0, len(embedding_data), batch_size):
            batch = embedding_data[i:i + batch_size]
            batch_result = await self.ingestor.store_embeddings(batch)
            
            # Aggregate results
            total_result.successful_count += batch_result.successful_count
            total_result.failed_items.extend(batch_result.failed_items)
            total_result.error_messages.extend(batch_result.error_messages)
            
            # Small delay between batches
            await asyncio.sleep(0.5)
        
        total_result.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return total_result
    
    # =================================================================
    # RETRIEVAL COORDINATION METHODS
    # =================================================================
    
    async def search(self, 
                   query: str, 
                   top_k: int = 10,
                   filters: Optional[Dict[str, List[str]]] = None,
                   min_similarity: float = 0.0) -> List[VectorRetrievalResult]:
        """
        Coordinate vector similarity search through the retriever component.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            filters: Optional filters (not currently supported by Vertex AI)
            min_similarity: Minimum similarity score threshold
            
        Returns:
            List of VectorRetrievalResult objects
        """
        if not self._initialized:
            raise RuntimeError("VectorStoreManager not initialized. Call initialize() first.")
        
        return await self.retriever.retrieve(query, top_k, filters, min_similarity)
    
    async def search_by_embedding(self, 
                                query_embedding: List[float], 
                                top_k: int = 10,
                                min_similarity: float = 0.0) -> List[VectorRetrievalResult]:
        """
        Coordinate vector search using pre-computed embedding.
        
        Args:
            query_embedding: Pre-computed query embedding
            top_k: Number of results to return
            min_similarity: Minimum similarity score threshold
            
        Returns:
            List of VectorRetrievalResult objects
        """
        if not self._initialized:
            raise RuntimeError("VectorStoreManager not initialized. Call initialize() first.")
        
        return await self.retriever.retrieve_by_embedding(query_embedding, top_k, min_similarity)
    
    async def batch_search(self, 
                         queries: List[str], 
                         top_k: int = 10,
                         min_similarity: float = 0.0) -> Dict[str, List[VectorRetrievalResult]]:
        """
        Coordinate batch search through the retriever component.
        
        Args:
            queries: List of query strings
            top_k: Number of results per query
            min_similarity: Minimum similarity score threshold
            
        Returns:
            Dictionary mapping queries to their results
        """
        if not self._initialized:
            raise RuntimeError("VectorStoreManager not initialized. Call initialize() first.")
        
        return await self.retriever.batch_retrieve(queries, top_k, min_similarity)
    
    # =================================================================
    # HEALTH AND MONITORING METHODS
    # =================================================================
    
    async def health_check(self) -> ComponentHealth:
        """
        Coordinate comprehensive health check of vector store system.
        
        Returns:
            ComponentHealth with overall system status
        """
        start_time = datetime.now()
        
        try:
            if not self._initialized:
                return ComponentHealth(
                    component_name="VectorStoreManager",
                    is_healthy=False,
                    error_message="Manager not initialized"
                )
            
            # Check component health
            ingestor_health = await self.ingestor.initialize()  # Re-check ingestor
            retriever_health = await self.retriever.health_check()
            
            is_healthy = ingestor_health and retriever_health.is_healthy
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            additional_info = {
                "ingestor_healthy": ingestor_health,
                "retriever_healthy": retriever_health.is_healthy,
                "ingestor_stats": self.ingestor.get_statistics(),
                "retriever_stats": self.retriever.get_statistics()
            }
            
            return ComponentHealth(
                component_name="VectorStoreManager",
                is_healthy=is_healthy,
                response_time_ms=response_time,
                additional_info=additional_info
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return ComponentHealth(
                component_name="VectorStoreManager",
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
                "storage_client_initialized": self._storage_client is not None,
                "index_initialized": self._index is not None,
                "endpoint_initialized": self._endpoint is not None,
                "embedding_model_initialized": self._embedding_model is not None
            }
        }
    
    async def get_index_info(self) -> Dict[str, Any]:
        """
        Get information about the vector index.
        
        Returns:
            Dictionary with index information
        """
        if not self._initialized:
            return {"error": "Manager not initialized"}
        
        try:
            index_info = self._index.to_dict()
            
            # Get deployed index information
            deployed_indexes = index_info.get("deployedIndexes", [])
            deployed_index_id = None
            
            target_endpoint = self.config.endpoint_resource_name
            for deployed in deployed_indexes:
                if deployed.get("indexEndpoint") == target_endpoint:
                    deployed_index_id = deployed.get("deployedIndexId")
                    break
            
            # Get index stats from metadata
            index_stats = index_info.get("indexStats", {})
            
            return {
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
            
        except Exception as e:
            self.logger.error(f"Failed to get index info: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close manager and clean up resources."""
        try:
            import gc
            import warnings
            
            # Suppress aiohttp warnings during cleanup
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*Unclosed client session.*")
                warnings.filterwarnings("ignore", message=".*Unclosed connector.*")
                
                # Close specialized components first
                if self.ingestor:
                    await self.ingestor.close()
                if self.retriever:
                    await self.retriever.close()
                
                # Close shared Google Cloud clients that use aiohttp sessions
                if self._storage_client:
                    try:
                        # Google Cloud Storage client doesn't have async close, but has synchronous close
                        if hasattr(self._storage_client, 'close'):
                            self._storage_client.close()
                        # Also try to close the underlying HTTP client if accessible
                        elif hasattr(self._storage_client, '_http_internal') and hasattr(self._storage_client._http_internal, 'close'):
                            self._storage_client._http_internal.close()
                    except Exception as e:
                        self.logger.debug(f"Storage client cleanup (expected): {e}")
                
                # Close embedding model if it has cleanup methods
                if self._embedding_model:
                    try:
                        # Try to close any internal HTTP clients in the embedding model
                        if hasattr(self._embedding_model, '_client') and hasattr(self._embedding_model._client, 'close'):
                            self._embedding_model._client.close()
                        elif hasattr(self._embedding_model, '_prediction_client'):
                            # Some Vertex AI models have a prediction client
                            if hasattr(self._embedding_model._prediction_client, 'transport') and hasattr(self._embedding_model._prediction_client.transport, '_grpc_channel'):
                                # Close gRPC channel if available
                                self._embedding_model._prediction_client.transport._grpc_channel.close()
                    except Exception as e:
                        self.logger.debug(f"Embedding model cleanup (expected): {e}")
                
                # Try to close any active aiohttp sessions from Google Cloud libraries
                try:
                    # Force close any active aiohttp sessions
                    import aiohttp
                    
                    # Get the current event loop
                    try:
                        loop = asyncio.get_running_loop()
                        
                        # Try to close any active client sessions
                        for obj in gc.get_objects():
                            if isinstance(obj, aiohttp.ClientSession) and not obj.closed:
                                try:
                                    await obj.close()
                                except:
                                    pass
                                    
                    except RuntimeError:
                        # No running event loop
                        pass
                        
                except ImportError:
                    # aiohttp not available
                    pass
                except Exception as e:
                    self.logger.debug(f"Aiohttp cleanup (expected): {e}")
                
                # Give any pending async operations time to complete
                await asyncio.sleep(0.2)
                
                # Force garbage collection to help close any lingering clients
                gc.collect()
                
                # Additional cleanup wait
                await asyncio.sleep(0.1)
            
            # Clear references to shared resources
            self._storage_client = None
            self._index = None
            self._endpoint = None  
            self._embedding_model = None
            
            self._initialized = False
            self.logger.info("VectorStoreManager closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during VectorStoreManager cleanup: {e}") 