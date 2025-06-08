import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from google.cloud import aiplatform
from google.cloud import storage
from google.cloud.aiplatform_v1.services.index_service import IndexServiceClient
from google.cloud.aiplatform_v1.types import UpsertDatapointsRequest
from google.api_core.client_options import ClientOptions
import vertexai
from vertexai.language_models import TextEmbeddingModel
import uuid

logger = logging.getLogger(__name__)

class VectorSearchIngestor:
    """Handles ingestion of document chunks into Google Cloud Vector Search."""
    
    def __init__(self, 
                 project_id: str,
                 location: str,
                 index_id: str,
                 endpoint_id: str,
                 bucket_name: str,
                 embedding_model: str = "text-embedding-005",
                 batch_size: int = 100):
        self.project_id = project_id
        self.location = location
        self.index_id = index_id
        self.endpoint_id = endpoint_id
        self.bucket_name = bucket_name.replace("gs://", "")  # Remove gs:// prefix if present
        self.embedding_model = embedding_model
        self.batch_size = batch_size
        self.logger = logging.getLogger(__name__)
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        
        # Initialize clients
        self.storage_client = storage.Client(project=project_id)
        self.embedding_model_client = TextEmbeddingModel.from_pretrained(embedding_model)
        
        # Initialize Vector Search client
        aiplatform.init(project=project_id, location=location)
        
        # Get project number for Vector Search resource names (required for some APIs)
        self.project_number = self._get_project_number(project_id)
        
        # Get the full resource names if not already in full format
        if not index_id.startswith("projects/"):
            # Use project number for Vector Search resources
            self.index_resource_name = f"projects/{self.project_number}/locations/{location}/indexes/{index_id}"
        else:
            self.index_resource_name = index_id
            
        if not endpoint_id.startswith("projects/"):
            # Use project number for Vector Search resources
            self.endpoint_resource_name = f"projects/{self.project_number}/locations/{location}/indexEndpoints/{endpoint_id}"
        else:
            self.endpoint_resource_name = endpoint_id
        
        self.index_client = aiplatform.MatchingEngineIndex(index_name=self.index_resource_name)
        self.endpoint_client = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=self.endpoint_resource_name)
        
        # Store the deployed_index_id - we'll determine this when needed
        self._deployed_index_id = None
    
    def _get_project_number(self, project_id: str) -> str:
        """Get the project identifier for Vector Search resource names."""
        # Based on diagnosis, the issue was region configuration, not project number vs ID
        # Start with project ID and let the region fix handle the main issue
        self.logger.info(f"Using project ID for resource names: {project_id}")
        return project_id
    
    def _get_deployed_index_id(self) -> str:
        """Get the deployed index ID from the endpoint."""
        try:
            if self._deployed_index_id is not None:
                return self._deployed_index_id
            
            # Get deployed indexes from the endpoint (using direct attribute access)
            deployed_indexes = self.endpoint_client.deployed_indexes or []
            
            # Find the deployed index that matches our index (compare index ID, not full resource path)
            for deployed_index in deployed_indexes:
                if hasattr(deployed_index, 'index'):
                    # Extract index ID from the deployed index resource path
                    deployed_index_id = deployed_index.index.split('/')[-1] if '/' in deployed_index.index else deployed_index.index
                    if deployed_index_id == self.index_id:
                        self._deployed_index_id = deployed_index.id
                        self.logger.info(f"Found deployed index ID: {self._deployed_index_id} (matches index {self.index_id})")
                        return self._deployed_index_id
            
            # If not found, use the index_id as fallback
            self.logger.warning(f"Could not find deployed index for {self.index_resource_name}, using index_id as fallback")
            self._deployed_index_id = self.index_id
            return self._deployed_index_id
            
        except Exception as e:
            self.logger.error(f"Error getting deployed index ID: {e}")
            # Fallback to using the index_id
            return self.index_id
    
    async def ingest_chunks(self, processed_document: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest processed document chunks into Vector Search."""
        try:
            chunks = processed_document.get("chunks", [])
            if not chunks:
                return {"status": "skipped", "reason": "no_chunks", "ingested_count": 0}
            
            # Process chunks in batches
            total_ingested = 0
            batch_results = []
            
            for i in range(0, len(chunks), self.batch_size):
                batch = chunks[i:i + self.batch_size]
                result = await self._ingest_batch(batch)
                batch_results.append(result)
                total_ingested += result.get("ingested_count", 0)
                
                # Add delay between batches to avoid rate limits
                if i + self.batch_size < len(chunks):
                    await asyncio.sleep(1)
            
            return {
                "status": "success",
                "document_id": processed_document["document_id"],
                "total_chunks": len(chunks),
                "ingested_count": total_ingested,
                "batch_results": batch_results,
                "ingested_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error ingesting chunks for document {processed_document.get('document_id')}: {str(e)}")
            return {
                "status": "error",
                "document_id": processed_document.get("document_id"),
                "error": str(e),
                "ingested_count": 0
            }
    
    async def _ingest_batch(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ingest a batch of chunks."""
        try:
            # Generate embeddings for the batch
            embeddings_data = await self._generate_embeddings_batch(chunks)
            
            # Upload to Cloud Storage as JSONL
            blob_name = f"vector_search_data/{datetime.now().strftime('%Y/%m/%d')}/{uuid.uuid4()}.jsonl"
            await self._upload_to_storage(embeddings_data, blob_name)
            
            # Import into Vector Search (this is typically done via batch import)
            # Note: For real-time updates, you'd use the online update API
            import_result = await self._import_to_vector_search(blob_name)
            
            return {
                "status": "success",
                "ingested_count": len(chunks),
                "blob_name": blob_name,
                "import_result": import_result
            }
            
        except Exception as e:
            self.logger.error(f"Error ingesting batch: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "ingested_count": 0
            }
    
    async def _generate_embeddings_batch(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings for a batch of chunks."""
        try:
            # Extract text content for embedding
            texts = [chunk["content"] for chunk in chunks]
            
            # Generate embeddings using Vertex AI
            embeddings_response = self.embedding_model_client.get_embeddings(texts)
            
            # Prepare data for Vector Search format
            embeddings_data = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings_response)):
                # Create the Vector Search format with correct field names
                vector_data = {
                    "id": chunk["chunk_id"],
                    "embedding": embedding.values,  # The actual embedding vector
                    "restricts": [
                        {"namespace": "source_id", "allow_list": [chunk["metadata"].get("source_id", "")]},
                        {"namespace": "content_type", "allow_list": [chunk["metadata"].get("content_type", "text")]},
                        {"namespace": "document_id", "allow_list": [chunk["source_document_id"]]}
                    ],
                    "crowding_tag": {
                        "crowding_attribute": chunk["source_document_id"]
                    },  # Group chunks from same document
                    # Store metadata as string (Vector Search limitation)
                    "metadata": json.dumps({
                        "chunk_id": chunk["chunk_id"],
                        "source_document_id": chunk["source_document_id"],
                        "chunk_index": chunk["chunk_index"],
                        "content": chunk["content"],  # Store FULL content in vector metadata
                        "full_metadata": chunk["metadata"]
                    })
                }
                embeddings_data.append(vector_data)
            
            return embeddings_data
            
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    async def _upload_to_storage(self, data: List[Dict[str, Any]], blob_name: str) -> str:
        """Upload embeddings data to Cloud Storage."""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            
            # Convert to JSONL format (one JSON object per line)
            jsonl_content = "\n".join([json.dumps(item) for item in data])
            
            # Upload to Cloud Storage
            blob.upload_from_string(jsonl_content, content_type="application/json")
            
            self.logger.info(f"Uploaded {len(data)} embeddings to gs://{self.bucket_name}/{blob_name}")
            return f"gs://{self.bucket_name}/{blob_name}"
            
        except Exception as e:
            self.logger.error(f"Error uploading to storage: {str(e)}")
            raise
    
    async def _import_to_vector_search(self, blob_name: str) -> Dict[str, Any]:
        """Import data from Cloud Storage to Vector Search index using real-time upsert."""
        try:
            # Read the JSONL data from Cloud Storage
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name.replace(f"gs://{self.bucket_name}/", ""))
            
            if not blob.exists():
                raise ValueError(f"Blob {blob_name} does not exist in bucket")
            
            # Download and parse the JSONL content
            jsonl_content = blob.download_as_text()
            import json
            embeddings_data = []
            for line in jsonl_content.strip().split('\n'):
                if line.strip():
                    embeddings_data.append(json.loads(line))
            
            if not embeddings_data:
                return {
                    "status": "skipped",
                    "reason": "no_data_to_import",
                    "blob_path": blob_name
                }
            
            # Prepare data for Vector Search upsert
            datapoints = []
            for item in embeddings_data:
                try:
                    # Validate required fields
                    if not item.get("id"):
                        self.logger.warning(f"Skipping item with missing ID: {item}")
                        continue
                    if not item.get("embedding"):
                        self.logger.warning(f"Skipping item with missing embedding: {item.get('id')}")
                        continue
                    
                    # Convert to the format expected by Vector Search upsertDatapoints API
                    # The format should match IndexDatapoint structure using snake_case
                    datapoint = {
                        "datapoint_id": item["id"],
                        "feature_vector": item["embedding"]
                    }
                    
                    # Add restricts if present and valid
                    restricts = item.get("restricts", [])
                    if restricts:
                        # Validate restrict structure
                        valid_restricts = []
                        for restrict in restricts:
                            if isinstance(restrict, dict) and "namespace" in restrict:
                                # Ensure allow_list exists (fix any legacy allow fields)
                                if "allow_list" in restrict:
                                    valid_restricts.append(restrict)
                                elif "allow" in restrict:
                                    # Convert legacy allow to allow_list
                                    self.logger.warning(f"Converting legacy 'allow' to 'allow_list' for namespace: {restrict['namespace']}")
                                    restrict_copy = restrict.copy()
                                    restrict_copy["allow_list"] = restrict_copy.pop("allow")
                                    valid_restricts.append(restrict_copy)
                        if valid_restricts:
                            datapoint["restricts"] = valid_restricts
                    
                    # Add crowding_tag if present and valid
                    crowding_tag = item.get("crowding_tag")
                    if crowding_tag:
                        if isinstance(crowding_tag, dict) and "crowding_attribute" in crowding_tag:
                            datapoint["crowding_tag"] = crowding_tag
                        elif isinstance(crowding_tag, str):
                            # Convert string to proper structure
                            datapoint["crowding_tag"] = {"crowding_attribute": crowding_tag}
                    
                    datapoints.append(datapoint)
                    
                except Exception as e:
                    self.logger.error(f"Error preparing datapoint {item.get('id', 'unknown')}: {str(e)}")
                    continue
            
            # Validate we have datapoints to upsert
            if not datapoints:
                self.logger.warning("No valid datapoints to upsert after validation")
                return {
                    "status": "skipped",
                    "reason": "no_valid_datapoints",
                    "blob_path": blob_name,
                    "upserted_count": 0
                }
            
            # Log sample datapoint for debugging
            self.logger.debug(f"Sample datapoint structure: {datapoints[0]}")
            
            # Perform real-time upsert to Vector Search using the Index client
            self.logger.info(f"Upserting {len(datapoints)} datapoints to Vector Search index")
            
            # Use the index client to upsert datapoints (not the endpoint client)
            # Important: Pass the region explicitly to avoid "global" region error
            client_options = ClientOptions(api_endpoint=f"{self.location}-aiplatform.googleapis.com")
            index_service_client = IndexServiceClient(client_options=client_options)
            
            # Create the upsert request
            request = UpsertDatapointsRequest(
                index=self.index_resource_name,
                datapoints=datapoints
            )
            
            # Perform the upsert
            upsert_response = index_service_client.upsert_datapoints(request=request)
            
            self.logger.info(f"Successfully upserted {len(datapoints)} datapoints to Vector Search")
            
            # Optionally, clean up the temporary blob after successful import
            try:
                blob.delete()
                self.logger.info(f"Cleaned up temporary blob: {blob_name}")
            except Exception as cleanup_error:
                self.logger.warning(f"Could not clean up blob {blob_name}: {cleanup_error}")
            
            return {
                "status": "success",
                "upserted_count": len(datapoints),
                "blob_path": blob_name,
                "upsert_response": str(upsert_response) if upsert_response else "success"
            }
            
        except Exception as e:
            self.logger.error(f"Error importing to Vector Search: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "blob_path": blob_name,
                "upserted_count": 0
            }
    
    async def search_similar(self, 
                           query_text: str, 
                           num_neighbors: int = 10,
                           restricts: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors in the Vector Search index."""
        try:
            # Generate embedding for query
            query_embedding = self.embedding_model_client.get_embeddings([query_text])[0]
            
            # Perform search using the endpoint
            search_response = self.endpoint_client.find_neighbors(
                deployed_index_id=self.index_id,
                queries=[query_embedding.values],
                num_neighbors=num_neighbors,
                restricts=restricts or []
            )
            
            # Process and return results
            results = []
            for neighbor in search_response[0]:  # First query results
                # Parse metadata back from JSON string
                metadata = json.loads(neighbor.datapoint.metadata) if neighbor.datapoint.metadata else {}
                
                result = {
                    "chunk_id": neighbor.datapoint.datapoint_id,
                    "distance": neighbor.distance,
                    "content": metadata.get("content", ""),
                    "source_document_id": metadata.get("source_document_id", ""),
                    "chunk_index": metadata.get("chunk_index", 0),
                    "metadata": metadata.get("full_metadata", {})
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching Vector Search: {str(e)}")
            raise
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the Vector Search index."""
        try:
            # Get index information
            index_info = self.index_client.to_dict()
            
            return {
                "index_id": self.index_id,
                "display_name": index_info.get("display_name", ""),
                "description": index_info.get("description", ""),
                "metadata": index_info.get("metadata", {}),
                "deployed_indexes": "see_endpoint_for_deployment_info",
                "create_time": index_info.get("create_time", ""),
                "update_time": index_info.get("update_time", "")
            }
            
        except Exception as e:
            self.logger.error(f"Error getting index stats: {str(e)}")
            return {"error": str(e)}
    
    async def validate_setup(self) -> Dict[str, Any]:
        """Validate Vector Search setup and configuration."""
        validation_results = {
            "status": "unknown",
            "checks": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Check 1: Bucket access
            try:
                bucket = self.storage_client.bucket(self.bucket_name)
                bucket_exists = bucket.exists()
                validation_results["checks"]["storage_bucket"] = {
                    "status": "pass" if bucket_exists else "fail",
                    "details": f"Bucket gs://{self.bucket_name} {'exists' if bucket_exists else 'does not exist'}"
                }
                if not bucket_exists:
                    validation_results["errors"].append(f"Storage bucket gs://{self.bucket_name} does not exist")
            except Exception as e:
                validation_results["checks"]["storage_bucket"] = {
                    "status": "fail",
                    "details": f"Error accessing bucket: {str(e)}"
                }
                validation_results["errors"].append(f"Storage bucket error: {str(e)}")
            
            # Check 2: Index exists
            try:
                index_info = self.index_client.to_dict()
                validation_results["checks"]["vector_index"] = {
                    "status": "pass",
                    "details": f"Index {self.index_id} found",
                    "display_name": index_info.get("display_name", ""),
                    "create_time": index_info.get("create_time", "")
                }
            except Exception as e:
                validation_results["checks"]["vector_index"] = {
                    "status": "fail",
                    "details": f"Error accessing index: {str(e)}"
                }
                validation_results["errors"].append(f"Vector Search index error: {str(e)}")
            
            # Check 3: Endpoint exists and has deployed index
            try:
                # Use direct attribute access (same as working test)
                deployed_indexes = self.endpoint_client.deployed_indexes or []
                deployed_index_found = False
                
                for deployed_index in deployed_indexes:
                    if hasattr(deployed_index, 'index'):
                        # Extract index ID from the deployed index resource path (handle project ID differences)
                        deployed_index_id = deployed_index.index.split('/')[-1] if '/' in deployed_index.index else deployed_index.index
                        if deployed_index_id == self.index_id:
                            deployed_index_found = True
                            validation_results["checks"]["deployed_index"] = {
                                "status": "pass",
                                "details": f"Index {self.index_id} deployed with ID: {deployed_index.id}",
                                "deployed_index_id": deployed_index.id
                            }
                            break
                
                if not deployed_index_found:
                    validation_results["checks"]["deployed_index"] = {
                        "status": "fail",
                        "details": f"Index {self.index_resource_name} not deployed to endpoint"
                    }
                    validation_results["errors"].append("Index is not deployed to the endpoint")
                
                validation_results["checks"]["endpoint"] = {
                    "status": "pass",
                    "details": f"Endpoint {self.endpoint_id} found with {len(deployed_indexes)} deployed indexes"
                }
                
            except Exception as e:
                validation_results["checks"]["endpoint"] = {
                    "status": "fail",
                    "details": f"Error accessing endpoint: {str(e)}"
                }
                validation_results["errors"].append(f"Vector Search endpoint error: {str(e)}")
            
            # Check 4: Embedding model
            try:
                test_embedding = self.embedding_model_client.get_embeddings(["test validation"])[0]
                validation_results["checks"]["embedding_model"] = {
                    "status": "pass",
                    "details": f"Embedding model {self.embedding_model} working",
                    "dimension": len(test_embedding.values),
                    "test_embedding_length": len(test_embedding.values)
                }
            except Exception as e:
                validation_results["checks"]["embedding_model"] = {
                    "status": "fail",
                    "details": f"Error with embedding model: {str(e)}"
                }
                validation_results["errors"].append(f"Embedding model error: {str(e)}")
            
            # Determine overall status
            failed_checks = [check for check in validation_results["checks"].values() if check["status"] == "fail"]
            if not failed_checks:
                validation_results["status"] = "valid"
            else:
                validation_results["status"] = "invalid"
            
            return validation_results
            
        except Exception as e:
            validation_results["status"] = "error"
            validation_results["errors"].append(f"Validation error: {str(e)}")
            return validation_results
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of Vector Search components."""
        try:
            # Check index status
            index_stats = await self.get_index_stats()
            
            # Check storage bucket access
            bucket = self.storage_client.bucket(self.bucket_name)
            bucket_exists = bucket.exists()
            
            # Check embedding model
            test_embedding = self.embedding_model_client.get_embeddings(["test"])[0]
            embedding_model_working = len(test_embedding.values) > 0
            
            return {
                "status": "healthy" if all([
                    "error" not in index_stats,
                    bucket_exists,
                    embedding_model_working
                ]) else "unhealthy",
                "components": {
                    "vector_search_index": "healthy" if "error" not in index_stats else "unhealthy",
                    "storage_bucket": "healthy" if bucket_exists else "unhealthy",
                    "embedding_model": "healthy" if embedding_model_working else "unhealthy"
                },
                "details": {
                    "index_stats": index_stats,
                    "bucket_name": self.bucket_name,
                    "embedding_model": self.embedding_model,
                    "embedding_dimension": len(test_embedding.values) if embedding_model_working else 0
                },
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
