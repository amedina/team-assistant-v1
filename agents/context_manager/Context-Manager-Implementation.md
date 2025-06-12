# Context Manager Agent Implementation

## Overview

The Context Manager Agent is a specialized AI agent within a multi-agent system built with Google's ADK (Agent Development Kit). It serves as the central component for contextual information retrieval, focusing on Privacy Sandbox and related Google privacy technologies.

## Architecture

### System Design
This agent follows the **Coordinator Pattern** within a 4-agent system:
- **Coordinator Agent** - Routes queries to appropriate specialized agents
- **Greeter Agent** - Handles casual conversations and greetings
- **Search Agent** - Performs web searches for current information
- **Context Manager Agent** - Provides contextual responses from knowledge base

### Implementation Strategy
**Approach**: Incremental Implementation (Option 2)
- ✅ **Phase 1**: Vector Search + Database Integration (Current)
- 🔄 **Phase 2**: Knowledge Graph Integration (Future)

## Core Components

### 1. ContextManager Class

The main orchestrator class that handles:
- Configuration management
- Storage manager initialization
- Query processing workflow
- Context synthesis and response generation

```python
class ContextManager:
    def __init__(self):
        # Load system configuration
        # Initialize storage managers
        # Set up logging
    
    async def initialize(self) -> bool:
        # Initialize Vector Store Manager
        # Initialize Database Manager
        # (Knowledge Graph Manager - future)
```

### 2. Storage Layer Integration

#### Vector Store Manager (✅ Implemented)
- **Technology**: Vertex AI Vector Search
- **Purpose**: Semantic similarity search
- **Method**: `retrieve_relative_documents(query, top_k=10)`
- **Returns**: Document IDs with similarity scores

#### Database Manager (✅ Implemented)
- **Technology**: Google Cloud PostgreSQL
- **Purpose**: Document metadata storage
- **Method**: `retrieve_document_metadata(document_ids)`
- **Returns**: Structured metadata (title, source, timestamps, etc.)

#### Knowledge Graph Manager (🔄 Future)
- **Technology**: Neo4j Knowledge Graph
- **Purpose**: Entity relationships and graph context
- **Method**: `retrieve_entity_relations(document_ids)` (prepared)
- **Status**: Placeholder implementation ready for Phase 2

### 3. Core Workflow

The agent follows this exact processing pipeline:

```python
async def process_query(self, user_query: str) -> str:
    # 1. Vector similarity search
    relevant_docs = await self.retrieve_relative_documents(user_query)
    
    # 2. Get document metadata
    doc_ids = [doc['id'] for doc in relevant_docs]
    metadata = await self.retrieve_document_metadata(doc_ids)
    
    # 3. Extract entity relationships (Phase 2)
    # entity_relations = await self.retrieve_entity_relations(doc_ids)
    
    # 4. Combine into structured context
    context = self.combine_relevant_context(relevant_docs, metadata)
    
    # 5. Generate response using LLM with context
    response = self.generate_response(user_query, context)
    
    return response
```

## Key Methods Implemented

### Required Custom Tools (Specification Compliance)

1. **`retrieve_relative_documents(query: str)`**
   - ✅ Implemented using VectorStoreManager
   - Performs semantic similarity search
   - Returns document IDs and similarity scores
   - Handles edge cases (no results, API failures)

2. **`retrieve_document_metadata(document_ids: List[str])`**
   - ✅ Implemented using DatabaseManager
   - Fetches metadata from PostgreSQL
   - Returns structured metadata dictionaries
   - Efficient batch processing

3. **`retrieve_entity_relations(document_ids: List[str])`**
   - 🔄 Prepared for future implementation
   - Currently returns placeholder structure
   - Ready for Neo4j integration in Phase 2

4. **`combine_relevant_context(docs, metadata, relations)`**
   - ✅ Implemented with LLMRetrievalContext
   - Merges all information into structured format
   - Optimized for LLM consumption
   - Handles missing/incomplete data gracefully

## ADK Integration

### Custom Tool Creation
The agent uses ADK's `FunctionTool` pattern for seamless integration:

```python
async def process_context_query(query: str) -> str:
    """
    Process queries related to Privacy Sandbox using contextual knowledge.
    """
    context_manager = await get_context_manager()
    return await context_manager.process_query(query)

# Create ADK tool
context_query_tool = FunctionTool(process_context_query)
```

### Agent Configuration
```python
context_manager_agent = Agent(
    name="context_manager_agent",
    model="gemini-2.5-pro-preview-05-06",
    instruction=specialized_privacy_sandbox_instruction,
    tools=[context_query_tool],
)
```

## Specialization Areas

The Context Manager Agent specializes in:

- **Privacy Sandbox APIs** - Implementation guides and documentation
- **PSAT (Privacy Sandbox Analysis Tool)** - Usage and technical details
- **Web Privacy Technologies** - Standards and best practices
- **Google Privacy Initiatives** - Official documentation and guides
- **Technical Implementation** - Code examples and integration patterns

## Response Generation Strategy

### Confidence-Based Responses
- **High Confidence (>0.7)**: "Based on my knowledge of Privacy Sandbox..."
- **Medium Confidence (0.4-0.7)**: "Here's what I found that might be relevant..."
- **Lower Confidence (<0.4)**: "I found some potentially related information..."

### Source Attribution
Every response includes:
- Source type identification
- Document identifiers
- Relevance confidence scores
- Number of sources consulted

### Fallback Strategy
- No relevant context → Suggests web search via Search Agent
- Technical errors → Graceful error messages
- Low confidence → Offers follow-up question prompts

## Configuration Requirements

### Required Configuration Files
- `config/data_sources_config.yaml` - Data pipeline configuration
- Environment variables for database passwords

### Storage Systems
1. **Vertex AI Vector Search**
   - Index ID: Configured in pipeline_config
   - Endpoint: Regional deployment
   - Embedding Model: text-embedding-005

2. **Cloud SQL PostgreSQL**
   - Instance connection name
   - Database credentials
   - Schema: document_chunks, ingestion_stats

3. **Neo4j (Future)**
   - Connection URI
   - Authentication credentials
   - Database name

## Error Handling & Reliability

### Initialization Safety
- Configuration validation before startup
- Storage manager health checks
- Graceful degradation if components unavailable

### Runtime Resilience
- Exception handling in all async operations
- Fallback responses for system failures
- Comprehensive logging for debugging

### Resource Management
- Proper async context management
- Connection pooling via managers
- Clean shutdown procedures

## Performance Characteristics

### Target Metrics (Specification Requirements)
- **Response Time**: < 5 seconds for typical queries
- **Availability**: Graceful degradation without system failure
- **Scalability**: Thread-safe for concurrent requests

### Optimization Strategies
- Lazy initialization pattern
- Batch processing for metadata retrieval
- Efficient context synthesis
- Configurable result limits (top_k=10 default)

## Development Status

### ✅ Completed (Phase 1)
- [x] ContextManager class implementation
- [x] Vector Store integration
- [x] Database Manager integration
- [x] Core query processing workflow
- [x] ADK tool integration
- [x] Response generation with source attribution
- [x] Error handling and logging
- [x] Configuration management

### 🔄 Future (Phase 2)
- [ ] Neo4j Knowledge Graph integration
- [ ] Entity relationship extraction
- [ ] Graph-based context enhancement
- [ ] Advanced semantic reasoning
- [ ] Performance optimization based on usage patterns

## Usage Examples

### Basic Query Processing
```python
# Via ADK Agent (typical usage)
coordinator_agent.run("What is the Privacy Sandbox?")

# Direct usage (for testing)
context_manager = await get_context_manager()
response = await context_manager.process_query("How do I implement PSAT?")
```

### Integration Testing
```python
# Test import
from agents.context_manager.context_manager_agent import context_manager_agent

# Test coordinator integration
from app.agent import coordinator_agent
print(f"Loaded with {len(coordinator_agent.tools)} tools")
```

## Maintenance & Monitoring

### Health Checks
- Storage manager connectivity
- Configuration validation
- Response time monitoring

### Logging
- Structured logging with context
- Query processing metrics
- Error tracking and alerting

### Updates
The system is designed for easy updates:
- Configuration changes via YAML
- Storage layer upgrades through managers
- Model updates via ADK configuration

## Conclusion

The Context Manager Agent successfully implements the core requirements for contextual information retrieval with a focus on Privacy Sandbox topics. The incremental approach allows for immediate functionality while providing a clear path for knowledge graph integration in Phase 2.

The implementation follows Google ADK patterns, maintains high code quality standards, and provides robust error handling suitable for production deployment. 