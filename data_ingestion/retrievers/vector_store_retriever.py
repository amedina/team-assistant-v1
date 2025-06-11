"""
Vector Store Retriever - specialized for similarity search and retrieval operations.

This component handles:
- Query embedding generation
- Similarity search execution
- Result ranking and filtering
- Query optimization and result processing
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
from uuid import UUID

from config.configuration import VectorSearchConfig
from ..models import VectorRetrievalResult, ComponentHealth

logger = logging.getLogger(__name__)


class VectorStoreRetriever:
    """
    Specialized component for vector similarity retrieval operations.
    
    This class focuses purely on read operations:
    - Converting queries to embeddings
    - Executing similarity searches
    - Processing and ranking results
    - Optimizing retrieval performance
    - Caching frequent queries (future enhancement)
    """
    
    def __init__(self, 
                 config: VectorSearchConfig,
                 index: MatchingEngineIndex,
                 endpoint: MatchingEngineIndexEndpoint,
                 embedding_model):
        """
        Initialize VectorStoreRetriever with shared resources.
        
        Args:
            config: Vector search configuration
            index: Shared MatchingEngineIndex instance
            endpoint: Shared MatchingEngineIndexEndpoint instance
            embedding_model: Shared embedding model for query processing
        """
        self.config = config
        self.index = index
        self.endpoint = endpoint
        self.embedding_model = embedding_model
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Retrieval state
        self._deployed_index_id: Optional[str] = None
        self._is_ready = False
        
        # Retrieval statistics
        self._total_queries = 0
        self._total_results_returned = 0
        self._average_response_time_ms = 0.0
    
    async def initialize(self) -> bool:
        """
        Initialize retriever and validate search capabilities.
        
        Returns:
            True if initialization successful and search is ready
        """
        try:
            # Get deployed index ID for search operations
            self._deployed_index_id = await self._get_deployed_index_id()
            
            if not self._deployed_index_id:
                self.logger.error("No deployed index found - search not available")
                return False
            
            # Test search functionality with a dummy query
            test_success = await self._test_search_capability()
            
            if test_success:
                self._is_ready = True
                self.logger.info(f"VectorStoreRetriever initialized with deployed index: {self._deployed_index_id}")
                return True
            else:
                self.logger.error("Search capability test failed")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to initialize VectorStoreRetriever: {e}")
            return False
    
    async def _get_deployed_index_id(self) -> Optional[str]:
        """Get the deployed index ID for search operations."""
        try:
            index_info = self.index.to_dict()
            deployed_indexes = index_info.get("deployedIndexes", [])
            
            target_endpoint = self.config.endpoint_resource_name
            for deployed in deployed_indexes:
                if deployed.get("indexEndpoint") == target_endpoint:
                    return deployed.get("deployedIndexId")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get deployed index ID: {e}")
            return None
    
    async def _test_search_capability(self) -> bool:
        """Test search functionality with a dummy embedding."""
        try:
            # Create a dummy embedding for testing
            dummy_embedding = [0.1] * 768  # Standard embedding dimension
            
            response = self.endpoint.find_neighbors(
                deployed_index_id=self._deployed_index_id,
                queries=[dummy_embedding],
                num_neighbors=1
            )
            
            # If we get a response without errors, search is working
            return response is not None
            
        except Exception as e:
            self.logger.warning(f"Search capability test failed: {e}")
            return False
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a single query string.
        
        Args:
            query: Query string to embed
            
        Returns:
            Embedding vector for the query
            
        Raises:
            Exception: If embedding generation fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        try:
            embeddings = self.embedding_model.get_embeddings([query.strip()])
            return embeddings[0].values
            
        except Exception as e:
            self.logger.error(f"Failed to generate query embedding: {e}")
            raise
    
    async def retrieve(self, 
                     query: str, 
                     top_k: int = 10,
                     filters: Optional[Dict[str, List[str]]] = None,
                     min_similarity: float = 0.0) -> List[VectorRetrievalResult]:
        """
        Retrieve similar vectors for a query string.
        
        Args:
            query: Search query string
            top_k: Number of results to return (max 1000)
            filters: Optional filters (not currently supported by Vertex AI)
            min_similarity: Minimum similarity score threshold
            
        Returns:
            List of VectorRetrievalResult objects sorted by similarity
            
        Raises:
            RuntimeError: If retriever not initialized or search fails
        """
        start_time = datetime.now()
        
        if not self._is_ready:
            raise RuntimeError("VectorStoreRetriever not initialized. Call initialize() first.")
        
        if not query or not query.strip():
            return []
        
        if top_k <= 0 or top_k > 1000:
            raise ValueError("top_k must be between 1 and 1000")
        
        try:
            self.logger.debug(f"Retrieving vectors for query: '{query[:50]}...'")
            
            # Generate query embedding
            query_embedding = await self.generate_query_embedding(query)
            
            # Perform similarity search
            response = self.endpoint.find_neighbors(
                deployed_index_id=self._deployed_index_id,
                queries=[query_embedding],
                num_neighbors=top_k
            )
            
            # Process results
            results = []
            if response and len(response) > 0:
                for neighbor in response[0]:
                    # Convert distance to similarity score (ensure distance is float)
                    distance = float(neighbor.distance) if isinstance(neighbor.distance, str) else neighbor.distance
                    similarity_score = 1.0 - distance
                    
                    # Apply minimum similarity threshold
                    if similarity_score < min_similarity:
                        continue
                    
                    # Extract chunk UUID - handle both string and UUID formats
                    chunk_uuid = neighbor.id
                    if isinstance(chunk_uuid, str):
                        try:
                            chunk_uuid = UUID(chunk_uuid)
                        except ValueError:
                            self.logger.warning(f"Invalid UUID format: {chunk_uuid}")
                            continue
                    
                    result = VectorRetrievalResult(
                        chunk_uuid=chunk_uuid,
                        similarity_score=max(0.0, min(1.0, similarity_score)),  # Clamp to [0, 1]
                        metadata=getattr(neighbor, 'metadata', {}),
                        distance_metric="cosine"
                    )
                    results.append(result)
            
            # Sort by similarity score (highest first)
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            
            # Update statistics
            self._total_queries += 1
            self._total_results_returned += len(results)
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_average_response_time(response_time)
            
            self.logger.info(f"Retrieved {len(results)} vectors for query in {response_time:.1f}ms")
            return results
            
        except Exception as e:
            self.logger.error(f"Vector retrieval failed for query '{query[:50]}...': {e}")
            raise RuntimeError(f"Vector search failed: {e}") from e
    
    async def batch_retrieve(self, 
                           queries: List[str], 
                           top_k: int = 10,
                           min_similarity: float = 0.0) -> Dict[str, List[VectorRetrievalResult]]:
        """
        Retrieve similar vectors for multiple queries in batch.
        
        Args:
            queries: List of query strings
            top_k: Number of results per query
            min_similarity: Minimum similarity score threshold
            
        Returns:
            Dictionary mapping queries to their results
            
        Raises:
            RuntimeError: If retriever not initialized or search fails
        """
        if not self._is_ready:
            raise RuntimeError("VectorStoreRetriever not initialized. Call initialize() first.")
        
        if not queries:
            return {}
        
        try:
            self.logger.info(f"Batch retrieving for {len(queries)} queries")
            
            # Generate embeddings for all queries
            query_embeddings = []
            valid_queries = []
            
            for query in queries:
                if query and query.strip():
                    try:
                        embedding = await self.generate_query_embedding(query)
                        query_embeddings.append(embedding)
                        valid_queries.append(query)
                    except Exception as e:
                        self.logger.warning(f"Skipping invalid query '{query[:30]}...': {e}")
                        continue
            
            if not query_embeddings:
                return {}
            
            # Perform batch search
            response = self.endpoint.find_neighbors(
                deployed_index_id=self._deployed_index_id,
                queries=query_embeddings,
                num_neighbors=top_k
            )
            
            # Process results for each query
            results = {}
            
            for i, query in enumerate(valid_queries):
                query_results = []
                
                if response and i < len(response) and response[i]:
                    for neighbor in response[i]:
                        distance = float(neighbor.distance) if isinstance(neighbor.distance, str) else neighbor.distance
                        similarity_score = 1.0 - distance
                        
                        if similarity_score < min_similarity:
                            continue
                        
                        try:
                            chunk_uuid = UUID(neighbor.id) if isinstance(neighbor.id, str) else neighbor.id
                            
                            result = VectorRetrievalResult(
                                chunk_uuid=chunk_uuid,
                                similarity_score=max(0.0, min(1.0, similarity_score)),
                                metadata=getattr(neighbor, 'metadata', {}),
                                distance_metric="cosine"
                            )
                            query_results.append(result)
                            
                        except ValueError:
                            self.logger.warning(f"Invalid UUID in batch result: {neighbor.id}")
                            continue
                
                # Sort by similarity score
                query_results.sort(key=lambda x: x.similarity_score, reverse=True)
                results[query] = query_results
            
            # Update statistics
            self._total_queries += len(valid_queries)
            total_results = sum(len(r) for r in results.values())
            self._total_results_returned += total_results
            
            self.logger.info(f"Batch retrieval completed: {len(valid_queries)} queries, {total_results} total results")
            return results
            
        except Exception as e:
            self.logger.error(f"Batch vector retrieval failed: {e}")
            raise RuntimeError(f"Batch vector search failed: {e}") from e
    
    async def retrieve_by_embedding(self, 
                                  query_embedding: List[float], 
                                  top_k: int = 10,
                                  min_similarity: float = 0.0) -> List[VectorRetrievalResult]:
        """
        Retrieve similar vectors using a pre-computed embedding.
        
        Args:
            query_embedding: Pre-computed query embedding
            top_k: Number of results to return
            min_similarity: Minimum similarity score threshold
            
        Returns:
            List of VectorRetrievalResult objects
        """
        if not self._is_ready:
            raise RuntimeError("VectorStoreRetriever not initialized. Call initialize() first.")
        
        if not query_embedding or len(query_embedding) == 0:
            raise ValueError("Query embedding cannot be empty")
        
        try:
            response = self.endpoint.find_neighbors(
                deployed_index_id=self._deployed_index_id,
                queries=[query_embedding],
                num_neighbors=top_k
            )
            
            results = []
            if response and len(response) > 0:
                for neighbor in response[0]:
                    distance = float(neighbor.distance) if isinstance(neighbor.distance, str) else neighbor.distance
                    similarity_score = 1.0 - distance
                    
                    if similarity_score < min_similarity:
                        continue
                    
                    try:
                        chunk_uuid = UUID(neighbor.id) if isinstance(neighbor.id, str) else neighbor.id
                        
                        result = VectorRetrievalResult(
                            chunk_uuid=chunk_uuid,
                            similarity_score=max(0.0, min(1.0, similarity_score)),
                            metadata=getattr(neighbor, 'metadata', {}),
                            distance_metric="cosine"
                        )
                        results.append(result)
                        
                    except ValueError:
                        self.logger.warning(f"Invalid UUID in embedding search: {neighbor.id}")
                        continue
            
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            return results
            
        except Exception as e:
            self.logger.error(f"Embedding-based retrieval failed: {e}")
            raise RuntimeError(f"Embedding search failed: {e}") from e
    
    def _update_average_response_time(self, response_time_ms: float):
        """Update the running average response time."""
        if self._total_queries == 1:
            self._average_response_time_ms = response_time_ms
        else:
            # Simple moving average
            alpha = 0.1  # Weight for new measurements
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
            if not self._is_ready:
                return ComponentHealth(
                    component_name="VectorStoreRetriever",
                    is_healthy=False,
                    error_message="Retriever not initialized"
                )
            
            # Test with a simple search
            test_success = await self._test_search_capability()
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ComponentHealth(
                component_name="VectorStoreRetriever",
                is_healthy=test_success,
                response_time_ms=response_time,
                additional_info={
                    "deployed_index_id": self._deployed_index_id,
                    "total_queries": self._total_queries,
                    "average_response_time_ms": self._average_response_time_ms,
                    "total_results_returned": self._total_results_returned
                }
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return ComponentHealth(
                component_name="VectorStoreRetriever",
                is_healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get retrieval statistics.
        
        Returns:
            Dictionary with retrieval performance statistics
        """
        return {
            "total_queries": self._total_queries,
            "total_results_returned": self._total_results_returned,
            "average_response_time_ms": self._average_response_time_ms,
            "average_results_per_query": (
                self._total_results_returned / self._total_queries 
                if self._total_queries > 0 else 0.0
            ),
            "is_ready": self._is_ready,
            "deployed_index_id": self._deployed_index_id
        }
    
    async def close(self):
        """Close retriever and clean up resources."""
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
            self.logger.debug(f"Retriever cleanup (expected): {e}")
        
        self._is_ready = False
        self.logger.info(f"VectorStoreRetriever closed. Final stats: {self.get_statistics()}") 