# Context Manager Agent Implementation Task

You are tasked with completing the Context Manager Agent implementation for a multi-agent system built with Google's ADK. This agent is a critical component that orchestrates data retrieval from multiple storage layers to provide contextual information for user queries.

## System Architecture Overview

This is part of a 4-agent system using a Coordinator Pattern:
- **Coordinator Agent** [@app/agent.py] - Routes queries to appropriate agents
- **Greeter Agent** [@agents/greeter] - Handles casual conversation
- **Search Agent** [@agents/search] - Performs web searches
- **Context Manager** [@agents/context_manager/context_manager_agent.py] - YOU ARE IMPLEMENTING THIS, the file exist is minimal form.

## Data Pipeline Architecture

The Context Manager must integrate with three storage layers:

1. **Vertex AI Vector Search Index** - Semantic similarity searches
   - Manager: [@data_ingestion/managers/vector_store_manager.py]
   
2. **Google Cloud PostgreSQL Database** - Document metadata storage
   - Manager: [@data_ingestion/managers/database_manager.py]
   
3. **Neo4j Knowledge Graph Database** - Entity relationships
   - Manager: [@data_ingestion/managers/knowledge_graph_manager.py]

## Configuration

The implementation already includes a configuration manager, and configuration parameters are defined in the file [@config/data_sources_config.yaml].

## Implementation Requirements

### File to Complete
Complete the implementation in: [@agents/context_manager/context_manager_agent.py]

### Required Custom Tools
Implement these four custom tools as methods within the Context Manager:

1. **`retrieve_relative_documents(query: str)`**
   - Use [@data_ingestion/managers/vector_store_manager.py]
   - Perform semantic similarity search on user query
   - Return list of relevant document IDs and similarity scores
   - Handle edge cases (no results, API failures)

2. **`retrieve_document_metadata(document_ids: List[str])`**
   - Use [@data_ingestion/managers/database_manager.py]
   - Fetch metadata for each document ID from PostgreSQL
   - Return structured metadata (title, source, date, tags, etc.)
   - Batch queries for efficiency

3. **`retrieve_entity_relations(document_ids: List[str])`**
   - Use [@data_ingestion/managers/knowledge_graph_manager.py]
   - Extract entities and relationships from Neo4j for given documents
   - Return graph structure with nodes and edges
   - Include entity types and relationship strengths

4. **`combine_relevant_context(docs, metadata, relations)`**
   - Merge all retrieved information into structured context object
   - Prioritize information by relevance scores
   - Format for optimal LLM consumption <- Key
   - Handle missing or incomplete data gracefully


### Architecture

The ContextManager below shows in pseudo-code a plausible structure.

```python
class ContextManager:
    """
    Context Manager that handles vector search and knowledge graph operations.
    Focused purely on context retrieval and knowledge management.
    """
    
    def __init__(self, ...):

      # Initialize vector search index        
      self.vector_store = VectorStoreManager(...);

      # Initialize datbase manager manager (optional component)      
      self.db = DatabaseManager(...)

      # Initialize knowledge graph manager (optional component)      
      self.knowledge_graph = KnowledgeGraphManager(...)

      logger.info("✅ ContextManager initialized successfully")

   def retrieve_relative_documents(query: str, ...):
      # Retrive documents relative to user query
      relevant_docs = vector_store.search( query )
      return relevant_docs

   def retrieve_document_metadata(ids: List[str],...):
      metadata = db.search_chunks( ... );
      return metadata

   def retrieve_entity_relations(ids: List[str],...)
      # This will be implemented later 
```

### Core Logic Flow
Implement this exact workflow in the main query processing method:

```python
def process_query(self, user_query: str) -> str:

   # 1. Vector similarity search
   relevant_docs = self.retrieve_relative_documents(user_query)
    
   # 2. Get document metadata
   metadata = self.retrieve_document_metadata(
      [doc['id'] for doc in relevant_docs]
   )
    
   #3. Extract entity relationships <-- for later
   #entity_relations = self.retrieve_entity_relations(
   #   [doc['id'] for doc in relevant_docs]
   #)
    
   # 4. Combine into structured context
   context = self.combine_relevant_context(relevant_docs, metadata)
    
   # 5. Generate response using LLM with context
   response = self.generate_response(user_query, context)
    
    return response
```

### Integration Requirements

1 **Google ADK Compliance**
   - Follow ADK agent patterns and conventions
   - Implement proper error handling and logging
   - Use ADK's tool registration system
   - Include proper async/await patterns where applicable

2. **Integration with Existing Storage Managers**
   - Understand very well the implementation and services provided by the manager classes [@data_ingestion/managers]
   - Understand well the data formats being exchange
   - Import and properly instantiate the three data managers

3. **Response Generation**
   - Use the configured LLM model (likely Gemini)
   - Structure prompts to include retrieved context effectively
   - Maintain conversational tone as specified in [@context_manager_agent_v0.md]
   - Implement fallback to Search Agent [@agents/search] if no relevant context found


## Code Quality Requirements

- Follow Python best practices and type hints
- Add comprehensive docstrings for all methods
- Include unit tests for each custom tool
- Ensure thread safety for concurrent requests

### Dependencies to understand
Understand well all the referenced files in these intructions, including:

- [@app/agent.py] - For agent structure and coordination patterns
- [@agents/search] - For Search Agent tool
- [@agents/context_manager/context_manager_agent.py] - Base implementation that you will help with
- [@data_ingestion/managers/vector_store_manager.py] - For vector search API
- [@data_ingestion/managers/database_manager.py] - For PostgreSQL operations
- [@data_ingestion/managers/knowledge_graph_manager.py] - For Neo4j operations

### Success Criteria

The completed Context Manager should:
1. Successfully integrate with all three storage layers
2. Provide relevant, contextual responses to user queries about Google Privacy Sandbox and related APIs
3. Handle errors gracefully without breaking the user experience
4. Maintain response times under 5 seconds for typical queries
5. Follow ADK patterns and be easily maintainable

### Additional Context

This Context Manager specializes in queries related to:

- Online Privacy
- Google's Privacy Sandbox
- Related APIs and technologies
- Technical documentation and implementation guides

The agent should be conversational and helpful, not just returning raw data but synthesizing information into useful, actionable responses. We want to provide a warm and fun vibe. 
---

**Next Steps**: Complete the implementation of [@agents/context_manager/context_manager_agent.py] following this specification. Ensure all custom tools are properly implemented and integrated with the existing data managers.