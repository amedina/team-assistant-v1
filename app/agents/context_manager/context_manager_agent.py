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

import logging
import asyncio
from typing import Dict, List, Any, Optional
import json
import os
from datetime import datetime

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool

from app.data_ingestion.managers.vector_store_manager import VectorStoreManager
from app.data_ingestion.managers.database_manager import DatabaseManager
from app.data_ingestion.managers.knowledge_graph_manager import KnowledgeGraphManager
from app.config.configuration import get_system_config
from app.data_ingestion.models.models import LLMRetrievalContext, EnrichedChunk

from app.agents.greeter.greeter_agent import greeter_agent
from app.agents.search.search_agent import search_agent


logger = logging.getLogger(__name__)

# Wrap the agents as tools
search_tool = AgentTool(agent=search_agent)
greeter_tool = AgentTool(agent=greeter_agent)


class ContextManager:
    """
    Context Manager that handles vector search and knowledge graph operations.
    Focused purely on context retrieval and knowledge management.
    """
    
    def __init__(self):
        """Initialize the Context Manager with data storage managers."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load configuration
        try:
            self.config = get_system_config()
            self.logger.info("Configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
        
        # Initialize storage managers
        self.vector_store: Optional[VectorStoreManager] = None
        self.db: Optional[DatabaseManager] = None
        self.knowledge_graph: Optional[KnowledgeGraphManager] = None  # For later implementation
        
        # Manager state
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize all storage managers."""
        try:
            self.logger.info("Initializing ContextManager...")
            
            # Initialize Vector Store Manager
            if self.config.pipeline_config.vector_search:
                self.vector_store = VectorStoreManager(self.config.pipeline_config.vector_search)
                vector_initialized = await self.vector_store.initialize()
                if not vector_initialized:
                    self.logger.error("Failed to initialize Vector Store Manager")
                    return False
                self.logger.info("✅ Vector Store Manager initialized successfully")
            
            # Initialize Database Manager  
            if self.config.pipeline_config.database:
                self.db = DatabaseManager(self.config.pipeline_config.database)
                db_initialized = await self.db.initialize()
                if not db_initialized:
                    self.logger.error("Failed to initialize Database Manager")
                    return False
                self.logger.info("✅ Database Manager initialized successfully")
            
            # Initialize Knowledge Graph Manager (for later - currently commented out)
            # if self.config.pipeline_config.neo4j and self.config.pipeline_config.enable_knowledge_graph:
            #     self.knowledge_graph = KnowledgeGraphManager(self.config.pipeline_config.neo4j)
            #     kg_initialized = await self.knowledge_graph.initialize()
            #     if not kg_initialized:
            #         self.logger.error("Failed to initialize Knowledge Graph Manager")
            #         return False
            #     self.logger.info("✅ Knowledge Graph Manager initialized successfully")
            
            self._initialized = True
            self.logger.info("✅ ContextManager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ContextManager: {e}")
            return False
    
    async def retrieve_relative_documents(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve documents relative to user query using vector similarity search.
        
        Args:
            query: User query string
            top_k: Number of results to return
            
        Returns:
            List of relevant document dictionaries with IDs and similarity scores
        """
        if not self._initialized or not self.vector_store:
            raise RuntimeError("ContextManager not initialized or vector store unavailable")
        
        try:
            self.logger.info(f"Performing vector search for query: '{query}' (top_k={top_k})")
            
            # Perform semantic similarity search
            vector_results = await self.vector_store.search(
                query=query,
                top_k=top_k,
                min_similarity=0.1  # Filter out very low similarity results
            )
            
            # Transform results to expected format
            relevant_docs = []
            for result in vector_results:
                relevant_docs.append({
                    'id': str(result.chunk_uuid),
                    'similarity_score': result.similarity_score,
                    'metadata': result.metadata,
                    'distance_metric': result.distance_metric
                })
            
            self.logger.info(f"Found {len(relevant_docs)} relevant documents")
            return relevant_docs
            
        except Exception as e:
            self.logger.error(f"Error in retrieve_relative_documents: {e}")
            return []
    
    async def retrieve_document_metadata(self, document_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieve document metadata from PostgreSQL database.
        
        Args:
            document_ids: List of document UUIDs to fetch metadata for
            
        Returns:
            List of structured metadata dictionaries
        """
        if not self._initialized or not self.db:
            raise RuntimeError("ContextManager not initialized or database unavailable")
        
        try:
            self.logger.info(f"Retrieving metadata for {len(document_ids)} documents")
            
            # Fetch chunks data from database
            chunks_data = await self.db.get_chunks(document_ids)
            
            # Transform to metadata format
            metadata_list = []
            for chunk in chunks_data:
                metadata = {
                    'chunk_uuid': str(chunk.chunk_uuid),
                    'source_type': chunk.source_type.value,
                    'source_identifier': chunk.source_identifier,
                    'chunk_text_summary': chunk.chunk_text_summary,
                    'chunk_metadata': chunk.chunk_metadata,
                    'ingestion_timestamp': chunk.ingestion_timestamp.isoformat() if chunk.ingestion_timestamp else None,
                    'source_last_modified_at': chunk.source_last_modified_at.isoformat() if chunk.source_last_modified_at else None,
                    'source_content_hash': chunk.source_content_hash,
                    'ingestion_status': chunk.ingestion_status.value
                }
                metadata_list.append(metadata)
            
            self.logger.info(f"Retrieved metadata for {len(metadata_list)} documents")
            return metadata_list
            
        except Exception as e:
            self.logger.error(f"Error in retrieve_document_metadata: {e}")
            return []
    
    async def retrieve_entity_relations(self, document_ids: List[str]) -> Dict[str, Any]:
        """
        Extract entities and relationships from Neo4j for given documents.
        
        NOTE: This is prepared for future implementation when knowledge graph is enabled.
        Currently returns empty structure.
        
        Args:
            document_ids: List of document UUIDs
            
        Returns:
            Graph structure with nodes and edges (currently empty)
        """
        self.logger.info(f"retrieve_entity_relations called for {len(document_ids)} documents")
        self.logger.info("Knowledge Graph integration not yet implemented - returning empty structure")
        
        # TODO: Implement when knowledge graph is ready
        # if not self._initialized or not self.knowledge_graph:
        #     self.logger.warning("Knowledge Graph not available")
        #     return {"entities": [], "relationships": [], "graph_context": None}
        # 
        # try:
        #     # Get graph context for the document chunks
        #     graph_context = await self.knowledge_graph.get_graph_context_for_chunks(
        #         chunk_uuids=document_ids,
        #         max_depth=2
        #     )
        #     
        #     return {
        #         "entities": [entity.dict() for entity in graph_context.query_entities + graph_context.related_entities],
        #         "relationships": [rel.dict() for rel in graph_context.relationships],
        #         "graph_context": graph_context.dict()
        #     }
        # except Exception as e:
        #     self.logger.error(f"Error in retrieve_entity_relations: {e}")
        #     return {"entities": [], "relationships": [], "graph_context": None}
        
        return {
            "entities": [],
            "relationships": [],
            "graph_context": None,
            "note": "Knowledge Graph integration will be implemented in next phase"
        }
    
    def combine_relevant_context(self, docs: List[Dict[str, Any]], metadata: List[Dict[str, Any]], 
                               relations: Dict[str, Any] = None) -> LLMRetrievalContext:
        """
        Merge all retrieved information into structured context object optimized for LLM consumption.
        
        Args:
            docs: Document results from vector search
            metadata: Metadata from database
            relations: Entity relations from knowledge graph (optional)
            
        Returns:
            LLMRetrievalContext object formatted for optimal LLM consumption
        """
        try:
            self.logger.info(f"Combining context from {len(docs)} docs and {len(metadata)} metadata entries")
            
            # Create metadata lookup
            metadata_lookup = {item['chunk_uuid']: item for item in metadata}
            
            # Create enriched chunks
            enriched_chunks = []
            for doc in docs:
                doc_id = doc['id']
                chunk_metadata = metadata_lookup.get(doc_id)
                
                if chunk_metadata:
                    # Create EnrichedChunk (simplified for now)
                    from app.data_ingestion.models.models import ChunkData, SourceType, IngestionStatus
                    from uuid import UUID
                    from datetime import datetime
                    
                    # Parse timestamps
                    ingestion_ts = datetime.fromisoformat(chunk_metadata['ingestion_timestamp']) if chunk_metadata.get('ingestion_timestamp') else datetime.now()
                    last_modified = datetime.fromisoformat(chunk_metadata['source_last_modified_at']) if chunk_metadata.get('source_last_modified_at') else None
                    
                    chunk_data = ChunkData(
                        chunk_uuid=UUID(chunk_metadata['chunk_uuid']),
                        source_type=SourceType(chunk_metadata['source_type']),
                        source_identifier=chunk_metadata['source_identifier'],
                        chunk_text_summary=chunk_metadata['chunk_text_summary'],
                        chunk_metadata=chunk_metadata['chunk_metadata'] or {},
                        ingestion_timestamp=ingestion_ts,
                        source_last_modified_at=last_modified,
                        source_content_hash=chunk_metadata.get('source_content_hash'),
                        ingestion_status=IngestionStatus(chunk_metadata['ingestion_status'])
                    )
                    
                    enriched_chunk = EnrichedChunk(
                        chunk_data=chunk_data,
                        vector_score=doc['similarity_score'],
                        relevance_score=doc['similarity_score'],  # Use similarity as relevance for now
                        ranking_position=len(enriched_chunks) + 1
                    )
                    enriched_chunks.append(enriched_chunk)
            
            # Calculate overall confidence based on similarity scores
            confidence_score = 0.0
            if docs:
                confidence_score = sum(doc['similarity_score'] for doc in docs) / len(docs)
            
            # Determine source types
            source_types = list(set(SourceType(meta['source_type']) for meta in metadata))
            
            # Create LLM context
            llm_context = LLMRetrievalContext(
                query="",  # Will be set when used
                relevant_chunks=enriched_chunks,
                knowledge_entities=[],  # Will be populated when knowledge graph is implemented
                total_sources=len(set(meta['source_identifier'] for meta in metadata)),
                confidence_score=confidence_score,
                source_types=source_types
            )
            
            self.logger.info(f"Created LLM context with {len(enriched_chunks)} chunks, confidence: {confidence_score:.2f}")
            return llm_context
            
        except Exception as e:
            self.logger.error(f"Error in combine_relevant_context: {e}")
            # Return empty context on error
            return LLMRetrievalContext(
                query="",
                relevant_chunks=[],
                knowledge_entities=[],
                total_sources=0,
                confidence_score=0.0,
                source_types=[]
            )
    
    async def process_query(self, user_query: str) -> str:
        """
        Main query processing method following the core logic flow.
        
        Args:
            user_query: User's query string
            
        Returns:
            Generated response with context
        """
        try:
            self.logger.info(f"Processing query: '{user_query}'")
            
            if not self._initialized:
                return "I'm sorry, but my knowledge systems are not currently available. Please try again later."
            
            # 1. Vector similarity search
            relevant_docs = await self.retrieve_relative_documents(user_query, top_k=10)
            
            if not relevant_docs:
                return ("I don't have specific information about that topic in my knowledge base. "
                       "This might be outside my area of expertise in Privacy Sandbox and related APIs. "
                       "Would you like me to search the web for current information instead?")
            
            # 2. Get document metadata
            doc_ids = [doc['id'] for doc in relevant_docs]
            metadata = await self.retrieve_document_metadata(doc_ids)
            
            # 3. Extract entity relationships (placeholder for now)
            # entity_relations = await self.retrieve_entity_relations(doc_ids)
            
            # 4. Combine into structured context
            context = self.combine_relevant_context(relevant_docs, metadata)
            context.query = user_query  # Set the query
            
            # 5. Generate response using LLM with context
            response = self.generate_response(user_query, context)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing query '{user_query}': {e}")
            return ("I encountered an error while processing your request. "
                   "Please try again or rephrase your question.")
    
    def generate_response(self, user_query: str, context: LLMRetrievalContext) -> str:
        """
        Generate response using retrieved context.
        
        Args:
            user_query: Original user query
            context: Retrieved and structured context
            
        Returns:
            Generated response string
        """
        try:
            # Convert context to prompt-ready format
            context_text = context.to_prompt_context(max_chunks=8)
            logger.error(f"Context text: {context_text}")
            
            # Build response based on available context
            if context.relevant_chunks:
                # We have relevant information
                response_parts = []
                
                # Add confidence indicator
                if context.confidence_score > 0.7:
                    confidence_indicator = "Based on my knowledge of Privacy Sandbox and related topics:"
                elif context.confidence_score > 0.4:
                    confidence_indicator = "Here's what I found that might be relevant:"
                else:
                    confidence_indicator = "I found some potentially related information:"
                
                response_parts.append(confidence_indicator)
                response_parts.append("")
                
                # Add key information from most relevant chunks
                for i, chunk in enumerate(context.relevant_chunks[:3], 1):
                    if chunk.chunk_data.chunk_text_summary:
                        chunk_info = f"{i}. {chunk.chunk_data.chunk_text_summary}"
                        
                        # Add source info
                        source_info = f"   (Source: {chunk.chunk_data.source_type.value}"
                        if chunk.chunk_data.source_identifier:
                            source_info += f" - {chunk.chunk_data.source_identifier}"
                        source_info += ")"
                        
                        response_parts.append(chunk_info)
                        response_parts.append(source_info)
                        response_parts.append("")
                
                # Add summary
                total_sources = context.total_sources
                logger.error(f"Total sources: {total_sources}")  

                response_parts.append(f"This information comes from {total_sources} source{'s' if total_sources != 1 else ''} "
                                    f"in my Privacy Sandbox knowledge base.")
                
                if context.confidence_score < 0.5:
                    response_parts.append("\nIf you need more specific information, feel free to ask follow-up questions!")
                
                return "\n".join(response_parts)
            
            else:
                return ("I don't have specific information about that topic in my Privacy Sandbox knowledge base. "
                       "Would you like me to search for current information instead?")
                
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return "I encountered an error while generating a response. Please try asking your question differently."
    
    async def close(self):
        """Clean up resources."""
        try:
            if self.vector_store:
                await self.vector_store.close()
            if self.db:
                await self.db.close()
            if self.knowledge_graph:
                await self.knowledge_graph.close()
            self.logger.info("ContextManager closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing ContextManager: {e}")


# Global context manager instance (lazy initialization)
_context_manager = None

async def get_context_manager() -> ContextManager:
    """Get or create the global context manager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
        await _context_manager.initialize()
    return _context_manager


# Custom Tools for ADK Integration
async def process_context_query(query: str) -> str:
    """
    Process queries related to Privacy Sandbox, Google's privacy initiatives, 
    and related APIs using contextual knowledge from documentation and resources.
    
    Args:
        query: The user's query about Privacy Sandbox or related topics
        
    Returns:
        Detailed, contextual response based on ingested knowledge
    """
    logger.info(f"Processing query: {query}")
    try:
        context_manager = await get_context_manager()
        return await context_manager.process_query(query)
    except Exception as e:
        logger.error(f"Error in process_context_query: {e}")
        return ("I'm experiencing technical difficulties accessing my knowledge base. "
               "Please try again in a moment.")


# Create the context query tool using FunctionTool
context_query_tool = FunctionTool(process_context_query)


# Create the context manager agent with proper RAG instruction
instruction = """You are a helpful AI assistant specializing in Google's Privacy Sandbox and related privacy technologies. 

Your expertise covers:
- Online Privacy
- Privacy Sandbox APIs and implementation
- PSAT (Privacy Sandbox Analysis Tool) 
- Web privacy technologies and standards
- Google's privacy initiatives and documentation
- Technical implementation guides and best practices

When users ask questions related to these topics, use your context_query_tool tool to provide detailed, accurate, and contextual responses based on your knowledge base.

Maintain a warm, helpful, and professional tone. Always cite your sources when providing specific technical information."""

# Create the agent with proper RAG-focused tools  
context_manager_agent = Agent(
    name="ContextManager",
    model="gemini-2.5-flash-preview-05-20",
    instruction=instruction,
    tools=[context_query_tool],
)

# Export as root_agent for Agent Engine compatibility
root_agent = context_manager_agent 