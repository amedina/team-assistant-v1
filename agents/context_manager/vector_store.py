# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Reusing existing retrieval functionality - now from utils
import os
import logging
from typing import Dict, List, Any, Optional

import google
import vertexai
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_google_community.vertex_rank import VertexAIRank

# Reuse existing components from utils (moved from root_agent)
from utils.retrievers import get_compressor, get_retriever
from utils.templates import format_docs
from utils.config_loader import get_vector_search_config

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages vector store operations - moved from root_agent with extensions."""
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-west1",
        embedding_model: str = "text-embedding-005",
        config_file: str = "config/data_sources_config.yaml",
    ):
        # Handle Google Cloud authentication gracefully
        try:
            self.credentials, detected_project_id = google.auth.default()
            
            # Get project_id from config file first, then constructor, then auth, then environment
            config_project_id = None
            try:
                vs_config = get_vector_search_config(config_file)
                config_project_id = vs_config.project_id
            except:
                pass  # Will use other sources
            
            self.project_id = project_id or config_project_id or detected_project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
            
        except Exception as e:
            logger.warning(f"Google Cloud authentication not available: {e}")
            self.credentials = None
            
            # Get project_id from config file first, then constructor, then environment
            config_project_id = None
            try:
                vs_config = get_vector_search_config(config_file)
                config_project_id = vs_config.project_id
            except:
                pass  # Will use other sources
            
            self.project_id = project_id or config_project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        
        # Check if we have a valid project_id
        if not self.project_id:
            logger.warning("No project_id found - vector store operations will be disabled")
            self.enabled = False
            return
        
        self.enabled = True
        self.config_file = config_file
        
        # Load Vector Search configuration from unified config loader
        try:
            vs_config = get_vector_search_config(config_file)
            
            # Use config values, with constructor parameters as overrides
            self.location = location if location != "us-west1" else vs_config.location
            self.embedding_model = embedding_model if embedding_model != "text-embedding-005" else vs_config.embedding_model
            
            # Vector Search configuration from config file (single source of truth)
            self.vector_search_index = vs_config.index_resource_name
            self.vector_search_index_endpoint = vs_config.endpoint_resource_name
            self.vector_search_bucket = vs_config.bucket
            
            logger.info(f"Using Vector Search config from {config_file}: index={vs_config.index_id}, endpoint={vs_config.endpoint_id}")
            
        except Exception as e:
            logger.warning(f"Failed to load Vector Search configuration from {config_file}: {e}")
            logger.warning("Falling back to environment variables for Vector Search configuration")
            
            # Fallback to environment variables with warnings
            self.vector_search_index = os.getenv("VECTOR_SEARCH_INDEX", "psat-agent-vector-search")
            self.vector_search_index_endpoint = os.getenv("VECTOR_SEARCH_INDEX_ENDPOINT", "psat-agent-vector-search-endpoint")
            self.vector_search_bucket = os.getenv("VECTOR_SEARCH_BUCKET", "ps-agent-vs-bucket")
            
            if self.vector_search_index == "psat-agent-vector-search":
                logger.warning("Using default Vector Search index - consider updating config/data_sources_config.yaml")
            if self.vector_search_index_endpoint == "psat-agent-vector-search-endpoint":
                logger.warning("Using default Vector Search endpoint - consider updating config/data_sources_config.yaml")
        
        # Set environment variables (only if project_id is valid)
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", self.project_id)
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
        
        try:
            # Initialize Vertex AI
            vertexai.init(project=self.project_id, location=self.location)
            
            # Create embedding instance (reusing existing setup)
            self.embedding = VertexAIEmbeddings(
                project=self.project_id, 
                location=self.location, 
                model_name=self.embedding_model
            )
            
            # Initialize components (reusing existing functions)
            self.retriever = self._setup_retriever()
            self.compressor = self._setup_compressor()
            
        except Exception as e:
            logger.warning(f"Failed to initialize vector store components: {e}")
            self.enabled = False
        
    def _setup_retriever(self) -> VectorStoreRetriever:
        """Setup vector retriever using existing get_retriever function."""
        return get_retriever(
            project_id=self.project_id,
            region=self.location,
            vector_search_bucket=self.vector_search_bucket,
            vector_search_index=self.vector_search_index,
            vector_search_index_endpoint=self.vector_search_index_endpoint,
            embedding=self.embedding,
        )
    
    def _setup_compressor(self) -> VertexAIRank:
        """Setup document compressor using existing get_compressor function."""
        return get_compressor(project_id=self.project_id)
    
    def retrieve_documents(self, query: str) -> str:
        """
        Retrieve and rank documents - returns properly formatted context for RAG.
        
        Args:
            query (str): The user's question or search query.
            
        Returns:
            str: Formatted context with "Context provided:" header for LLM RAG processing.
        """
        try:
            # Use the retriever to fetch relevant documents based on the query
            retrieved_docs = self.retriever.invoke(query)
            
            # Re-rank docs with Vertex AI Rank for better relevance
            ranked_docs = self.compressor.compress_documents(
                documents=retrieved_docs, query=query
            )
            
            # Apply deduplication to avoid identical documents
            if not ranked_docs:
                return f"No relevant documents found for query: {query}"
            
            # Deduplicate documents based on content similarity
            seen_content = set()
            unique_docs = []
            
            for doc in ranked_docs:
                # Use first 200 characters as deduplication key
                content_key = doc.page_content[:200].strip()
                if content_key not in seen_content:
                    seen_content.add(content_key)
                    unique_docs.append(doc)
                    
                    # Limit to top 3 unique documents
                    if len(unique_docs) >= 3:
                        break
            
            # Format documents with proper RAG structure using the template
            # This includes "Context provided:" header that tells the LLM to use this context
            formatted_docs = format_docs.format(docs=unique_docs)
            
            return formatted_docs
            
        except Exception as e:
            error_msg = f"Calling retrieval tool with query:\n\n{query}\n\nraised the following error:\n\n{type(e)}: {e}"
            logger.error(error_msg)
            return error_msg
    
    def retrieve_raw_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve raw documents without formatting - useful for processing.
        
        Args:
            query (str): The search query.
            limit (int): Maximum number of documents to return.
            
        Returns:
            List[Dict]: List of document objects with metadata.
        """
        try:
            # Get raw documents
            retrieved_docs = self.retriever.invoke(query)
            
            # Re-rank documents
            ranked_docs = self.compressor.compress_documents(
                documents=retrieved_docs, query=query
            )
            
            # Convert to dict format
            documents = []
            for doc in ranked_docs[:limit]:
                documents.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": getattr(doc, 'score', None)
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error retrieving raw documents: {e}")
            return []
    
    def update_vector_store_config(
        self, 
        vector_search_index: Optional[str] = None,
        vector_search_index_endpoint: Optional[str] = None,
        vector_search_bucket: Optional[str] = None,
        config_file: Optional[str] = None
    ):
        """
        Update vector store configuration and reinitialize components.
        
        Note: For consistency, consider updating config/data_sources_config.yaml instead
        of using this method, as the config file is the single source of truth.
        """
        # If config_file is provided, reload from config
        if config_file:
            self.config_file = config_file
            try:
                vs_config = get_vector_search_config(config_file)
                self.vector_search_index = vs_config.index_resource_name
                self.vector_search_index_endpoint = vs_config.endpoint_resource_name
                self.vector_search_bucket = vs_config.bucket
                logger.info(f"Reloaded Vector Search config from {config_file}")
            except Exception as e:
                logger.error(f"Failed to reload config from {config_file}: {e}")
                return
        else:
            # Legacy: Allow direct parameter updates (but warn about consistency)
            if vector_search_index or vector_search_index_endpoint or vector_search_bucket:
                logger.warning("Updating Vector Search config directly. Consider updating config/data_sources_config.yaml for consistency.")
            
            if vector_search_index:
                self.vector_search_index = vector_search_index
            if vector_search_index_endpoint:
                self.vector_search_index_endpoint = vector_search_index_endpoint
            if vector_search_bucket:
                self.vector_search_bucket = vector_search_bucket
            
        # Reinitialize with new config
        self.retriever = self._setup_retriever()
        logger.info("Vector store configuration updated")
    
    def test_connection(self) -> bool:
        """Test if vector store is accessible."""
        try:
            # Try a simple query to test the connection
            test_docs = self.retriever.invoke("test")
            logger.info("Vector store connection test successful")
            return True
        except Exception as e:
            logger.error(f"Vector store connection test failed: {e}")
            return False 