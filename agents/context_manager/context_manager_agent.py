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
from typing import Dict, List, Any, Optional
import json
import os

from google.adk.agents import Agent

from .vector_store import VectorStoreManager
from .knowledge_graph import KnowledgeGraphManager

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Context Manager that handles vector search and knowledge graph operations.
    Focused purely on context retrieval and knowledge management.
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-west1",
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
    ):
        # Use environment variable for project_id if not provided
        if project_id is None:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        
        # Initialize vector store manager (core component)
        try:
            self.vector_store = VectorStoreManager(
                project_id=project_id,
                location=location
            )
            self.vector_search_available = True
            logger.info("✅ Vector Search initialized successfully")
        except Exception as e:
            logger.error(f"❌ Vector Search initialization failed: {e}")
            self.vector_search_available = False
            raise RuntimeError(f"Cannot initialize ContextManager without working Vector Search: {e}")
        
        # Initialize knowledge graph manager (optional component)
        try:
            self.knowledge_graph = KnowledgeGraphManager(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password
            )
            self.kg_available = self.knowledge_graph.is_available()
            if self.kg_available:
                logger.info("✅ Knowledge graph initialized successfully")
            else:
                logger.info("ℹ️ Knowledge graph not available, using vector search only")
        except Exception as e:
            logger.warning(f"Knowledge graph initialization failed: {e}")
            self.kg_available = False
        
        logger.info("✅ ContextManager initialized successfully")


# Create tool functions that the agent can use
def retrieve_documents(query: str) -> str:
    """
    Retrieve relevant documents from vector search to provide context for answering the user's question.
    
    Args:
        query (str): The user's question or search query.
        
    Returns:
        str: Raw document content that the agent should use to answer the user's question.
    """
    try:
        # Get raw document content from vector store
        raw_docs = get_context_manager().vector_store.retrieve_documents(query)
        
        # If no documents found or error, return indication for agent to handle
        if not raw_docs or "Calling retrieval tool" in raw_docs:
            return f"No relevant documents found for query: {query}"
        
        # Return raw docs for the agent to process and use in its response
        return raw_docs
        
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        return f"Error retrieving documents for query: {query}. Error: {str(e)}"


def retrieve_knowledge_graph(query: str) -> str:
    """
    Retrieve relationship information from the knowledge graph to provide context.
    
    Args:
        query (str): The user's question or search query.
        
    Returns:
        str: Knowledge graph information that the agent should use to answer the user's question.
    """
    context_manager = get_context_manager()
    if not context_manager.kg_available:
        return "Knowledge graph is not available."
    
    try:
        # Query the knowledge graph
        kg_results = context_manager.knowledge_graph.query_knowledge_graph(query)
        
        if not kg_results:
            return f"No relationship information found in knowledge graph for: {query}"
        
        # Format the results for the agent to use
        formatted_results = "Knowledge Graph Information:\n\n"
        for i, result in enumerate(kg_results[:5], 1):  # Limit to top 5 results
            entity = result["entity"]
            connections = result["connections"]
            
            formatted_results += f"Entity {i}: {entity.get('name', 'Unknown')} ({entity.get('type', 'Unknown')})\n"
            
            if entity.get('properties'):
                formatted_results += f"Properties: {json.dumps(entity['properties'], indent=2)}\n"
            
            if connections:
                formatted_results += "Related entities:\n"
                for conn in connections[:3]:  # Limit connections
                    if conn and conn.get('connected_entity'):
                        related = conn['connected_entity']
                        rel_type = conn.get('relationship', {}).get('type', 'RELATED')
                        formatted_results += f"  - {rel_type}: {related.get('name', 'Unknown')}\n"
            
            formatted_results += "\n"
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error querying knowledge graph: {e}")
        return f"Error retrieving knowledge graph information for: {query}. Error: {str(e)}"


def search_hybrid_context(query: str) -> str:
    """
    Search both vector store and knowledge graph to provide comprehensive context.
    
    Args:
        query (str): The user's question or search query.
        
    Returns:
        str: Combined context from multiple sources that the agent should use to answer the user's question.
    """
    # Get search results from both sources
    doc_results = retrieve_documents(query)
    kg_results = retrieve_knowledge_graph(query) if get_context_manager().kg_available else ""
    
    # Combine results for the agent to use
    combined_context = "Comprehensive Search Results:\n\n"
    
    # Add document results
    if doc_results and not doc_results.startswith("No relevant documents") and not doc_results.startswith("Error"):
        combined_context += "=== DOCUMENT SEARCH RESULTS ===\n"
        combined_context += doc_results + "\n\n"
    
    # Add knowledge graph results
    if kg_results and not kg_results.startswith("Knowledge graph is not available") and not kg_results.startswith("No relationship information"):
        combined_context += "=== KNOWLEDGE GRAPH RESULTS ===\n"
        combined_context += kg_results + "\n\n"
    
    # If no results from either source
    if (doc_results.startswith("No relevant documents") or doc_results.startswith("Error")) and \
       (kg_results.startswith("Knowledge graph is not available") or kg_results.startswith("No relationship information") or not kg_results):
        combined_context += f"No specific information found for: {query}\n"
    
    return combined_context


# Create the context manager agent with proper RAG instruction
instruction = """You are a Context Manager for the DevRel Assistant system. Your job is to help users by finding relevant information and providing helpful, conversational responses based on the context you retrieve.

**IMPORTANT: How RAG (Retrieval-Augmented Generation) Works Here:**

When a user asks a question:
1. **Call your tools** to retrieve relevant context (e.g., `retrieve_documents("user question")`)
2. **Your tools will return formatted context** with headers like "## Context provided:" followed by relevant documents
3. **Use that retrieved context** to provide a helpful, conversational answer to the user's question
4. **Do NOT just repeat the raw context** - instead, synthesize it into a clear, helpful response

**Your Tools:**
- `retrieve_documents`: Gets relevant documentation and guides with proper context formatting
- `retrieve_knowledge_graph`: Gets relationship information between concepts  
- `search_hybrid_context`: Gets comprehensive information from all sources

**Response Guidelines:**
- **Always call a tool first** to get relevant context for the user's question
- **Read the retrieved context carefully** and use it to inform your response
- **Answer conversationally** - explain concepts clearly using the information you found
- **Be helpful and informative** - don't just dump context, but use it to craft useful answers
- **If no relevant info found**, acknowledge this and suggest alternatives

**Example Flow:**
User: "What is PSAT?"
1. You call: `retrieve_documents("What is PSAT?")`
2. Tool returns: "## Context provided: <Document 0> PSAT is a tool for Privacy Sandbox... </Document 0>"
3. You respond: "Based on the documentation, PSAT (Privacy Sandbox Analysis Tool) is..."

**Remember**: Your goal is to be a helpful assistant that uses retrieved context to provide accurate, conversational responses about DevRel topics."""

# Lazy initialization pattern
_context_manager = None

def get_context_manager():
    """Get or create the global context manager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager

# Create the agent with proper RAG-focused tools
context_manager_agent = Agent(
    name="context_manager_agent",
    model="gemini-1.5-flash",
    instruction=instruction,
    tools=[
        retrieve_documents,           # Retrieve context for the agent to use
        retrieve_knowledge_graph,     # Retrieve relationship context
        search_hybrid_context,        # Retrieve comprehensive context
    ],
)

# Export as root_agent for Agent Engine compatibility
root_agent = context_manager_agent 