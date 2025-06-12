# 🎯 Context Manager Agent - Implementation Task

You are completing the **Context Manager Agent** for a multi-agent system built with Google's ADK. This agent retrieves and synthesizes contextual information from multiple data sources to answer user queries about online privacy and Google's Privacy Sandbox.

## 🏗️ Current State & Your Mission

**File to Complete:** [@agents/context_manager/context_manager_agent.py] 
- ✅ Base structure exists in minimal form
- ❌ Core functionality needs implementation  
- 🎯 **Your job**: Complete the missing methods and logic

## 🔧 Implementation Priorities

### Phase 1: Essential Methods (Implement First)
1. **`retrieve_relative_documents(query: str)`** - Vector similarity search
2. **`retrieve_document_metadata(document_ids: List[str])`** - PostgreSQL metadata fetch  
3. **`combine_relevant_context(docs, metadata)`** - Context synthesis
4. **`process_query(user_query: str)`** - Main orchestration method

### Phase 2: Future Enhancement  
- `retrieve_entity_relations()` - Knowledge graph (comment out for now)

## 📋 Technical Implementation Guide

### Required Class Structure
```python
class ContextManager:
    """
    Context Manager for Privacy Sandbox knowledge retrieval.
    Integrates vector search, metadata, and knowledge graph data.
    """
    
    def __init__(self, config_manager):
        # Initialize from [@config/data_sources_config.yaml]
        self.vector_store = VectorStoreManager(config_manager.vector_config)
        self.db = DatabaseManager(config_manager.db_config)  
        # self.knowledge_graph = KnowledgeGraphManager(...)  # Phase 2
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("✅ ContextManager initialized successfully")
```

### Core Workflow Implementation
**Implement this exact flow in `process_query():`**

```python
def process_query(self, user_query: str) -> str:
    try:
        # 1. Vector similarity search  
        relevant_docs = self.retrieve_relative_documents(user_query)
        
        # 2. Get document metadata
        if relevant_docs:
            doc_ids = [doc['id'] for doc in relevant_docs]
            metadata = self.retrieve_document_metadata(doc_ids)
        else:
            metadata = []
            
        # 3. Skip entity relations for now (Phase 2)
        # entity_relations = self.retrieve_entity_relations(doc_ids)
        
        # 4. Combine into structured context
        context = self.combine_relevant_context(relevant_docs, metadata)
        
        # 5. Generate warm, conversational response
        response = self.generate_response(user_query, context)
        
        return response
        
    except Exception as e:
        self.logger.error(f"Query processing failed: {e}")
        return self._fallback_response(user_query)
```

## 🔍 Method Implementation Requirements

### 1. `retrieve_relative_documents(query: str)`
```python
def retrieve_relative_documents(self, query: str, top_k: int = 5) -> List[Dict]:
    """
    Perform semantic similarity search using vector store.
    
    Returns: List of docs with structure:
    [{'id': 'doc_123', 'score': 0.95, 'content': '...', 'title': '...'}, ...]
    """
    # Use: self.vector_store.search(query, top_k)
    # Handle: Empty results, API failures, malformed responses
    # Log: Search metrics and results count
```

### 2. `retrieve_document_metadata(document_ids: List[str])`
```python
def retrieve_document_metadata(self, document_ids: List[str]) -> List[Dict]:
    """
    Fetch structured metadata from PostgreSQL for given document IDs.
    
    Returns: List of metadata objects:
    [{'id': 'doc_123', 'title': '...', 'source': '...', 'date': '...', 'tags': [...], 'url': '...'}, ...]
    """
    # Use: self.db.get_chunks_metadata(document_ids) or similar
    # Handle: Batch queries for efficiency, missing documents
    # Return: Structured metadata objects
```

### 3. `combine_relevant_context(docs, metadata)`
```python
def combine_relevant_context(self, docs: List[Dict], metadata: List[Dict]) -> str:
    """
    ⭐ CRITICAL: Format context for optimal LLM consumption.
    
    Create a well-structured context string that:
    - Prioritizes by relevance scores
    - Groups related information  
    - Uses clear section headers
    - Handles missing data gracefully
    
    Returns: Formatted context string ready for LLM prompt
    """
    # Structure should be optimized for Gemini LLM
    # Include document titles, sources, key content
    # Prioritize higher relevance scores
    # Add section breaks and clear formatting
```

### 4. `generate_response(query, context)`
```python
def generate_response(self, query: str, context: str) -> str:
    """
    Generate warm, conversational response using retrieved context.
    
    Requirements:
    - Use Gemini LLM with context + query
    - Maintain warm, helpful tone  
    - Synthesize information (don't just dump data)
    - Include source references when helpful
    """
    # Build prompt: system_prompt + context + user_query
    # Call LLM with proper error handling
    # Format response conversationally
```

## 🔧 Integration Guidelines

### Understanding Required Dependencies

**STUDY THESE FILES FIRST:**
- [@data_ingestion/managers/vector_store_manager.py] - Learn the search API and data formats
- [@data_ingestion/managers/database_manager.py] - Understand metadata structure and query methods  
- [@config/data_sources_config.yaml] - Configuration parameters and connection details
- [@app/agent.py] - Agent patterns and ADK conventions to follow

### Configuration Integration
```python
# Access config via the config_manager passed to __init__
vector_config = config_manager.get('vector_store')
db_config = config_manager.get('database') 
```

### Error Handling Strategy
1. **Graceful degradation**: Work with partial data when some services fail
2. **Meaningful fallbacks**: Route to Search Agent [@agents/search] if no context found
3. **User-friendly errors**: Never expose technical errors to users
4. **Comprehensive logging**: Log all operations for debugging

### Response Tone Requirements
- **Warm and conversational** - Like talking to a knowledgeable friend
- **Synthesize, don't dump** - Explain concepts using retrieved information  
- **Cite sources naturally** - "According to the Privacy Sandbox documentation..."
- **Admit limitations** - "I don't have specific information about that, but I can search the web..."

## ✅ Success Criteria & Testing

**Your implementation succeeds when:**

1. **Functional Integration**: All three storage layers work correctly
2. **Relevant Responses**: Provides accurate Privacy Sandbox information  
3. **Error Resilience**: Handles failures without breaking user experience
4. **Performance**: Responds within 5 seconds for typical queries
5. **Code Quality**: Follows ADK patterns with proper logging and type hints

**Test Queries to Validate:**
- "What is the Privacy Sandbox?"
- "How do Topics API work?"  
- "What's the difference between FLEDGE and Topics?"
- "How can I implement Trust Tokens?"

## 🚀 Implementation Order

1. **Setup**: Initialize managers and configuration
2. **Vector Search**: Implement `retrieve_relative_documents()`
3. **Metadata**: Implement `retrieve_document_metadata()`  
4. **Context Synthesis**: Implement `combine_relevant_context()` (most critical!)
5. **Response Generation**: Implement `generate_response()`
6. **Orchestration**: Complete `process_query()` main method
7. **Error Handling**: Add comprehensive exception handling
8. **Testing**: Validate with sample queries

## 📝 Code Quality Checklist

- [ ] Type hints on all methods
- [ ] Comprehensive docstrings  
- [ ] Proper error handling and logging
- [ ] Configuration-driven initialization
- [ ] Async/await patterns where needed
- [ ] Thread-safe operations
- [ ] Unit tests for each method

---

**🎯 Focus Areas**: The `combine_relevant_context()` method is CRITICAL - it determines how well the LLM can use your retrieved information. Spend extra time making this context structure optimal for Gemini's consumption.

**Next Step**: Start with [@agents/context_manager/context_manager_agent.py] and implement the methods in the order specified above.