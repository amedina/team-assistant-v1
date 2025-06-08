# Data Processing and Retrieval System

A comprehensive data ingestion, processing, and retrieval system that combines multiple storage technologies for optimal performance and flexibility.

## System Overview

This system provides end-to-end data processing capabilities with the following architecture:

- **Data Sources**: GitHub repositories, Google Drive folders, and web pages
- **Processing**: Intelligent text chunking with entity/relationship extraction
- **Storage**: Multi-modal storage across Vector Search, PostgreSQL, and Neo4j
- **Retrieval**: Unified interface for semantic search, metadata queries, and graph traversal

## Architecture Components

### 🏗️ Core Managers

#### VectorStoreManager
- **Purpose**: Manages Vertex AI Vector Search operations
- **Features**: Embedding generation, similarity search, batch operations
- **Storage**: Google Cloud Vector Search + Cloud Storage

#### DatabaseManager  
- **Purpose**: Manages PostgreSQL operations for metadata and chunk mapping
- **Features**: Chunk storage, source mapping, query operations
- **Storage**: Cloud SQL PostgreSQL

#### KnowledgeGraphManager
- **Purpose**: Manages Neo4j knowledge graph for entities and relationships
- **Features**: Entity extraction, relationship mapping, graph queries
- **Storage**: Neo4j Graph Database

### 🔄 Processing Pipeline

#### TextProcessor
- **Purpose**: Document processing and intelligent chunking
- **Features**: 
  - Sentence-aware text splitting
  - Entity and relationship extraction using spaCy
  - Metadata enrichment
  - Multiple content type support

#### PipelineManager  
- **Purpose**: Central orchestration of the entire pipeline
- **Features**:
  - Multi-source data ingestion
  - Concurrent processing with rate limiting
  - Health monitoring and statistics
  - Different sync modes (Full, Incremental, Smart)

### 🔌 Data Connectors

#### BaseConnector (Abstract)
- Defines standard interface for all data sources
- Methods: `connect()`, `fetch_documents()`, `check_connection()`, `disconnect()`

#### Concrete Connectors
- **GitHubConnector**: Repository file ingestion via GitHub API
- **DriveConnector**: Google Drive document access
- **WebConnector**: Web scraping and sitemap crawling

## Configuration

The system uses `config/data_sources_config.yaml` for configuration:

```yaml
project_config:
  google_cloud_project: "your-project-id"
  google_cloud_location: "us-west1"

pipeline_config:
  # Vector Search settings
  vector_search_index: "your-index-id"
  vector_search_endpoint: "your-endpoint-resource-name"
  vector_search_bucket: "gs://your-bucket"
  
  # Processing settings
  chunk_size: 800
  chunk_overlap: 100
  embedding_model: "text-embedding-005"
  batch_size: 100
  
  # Database settings
  instance-connection-name: "project:region:instance"
  db_name: "your-database"
  db_user: "postgres"
  db_pass: "your-password"
  
  # Neo4j settings (optional)
  neo4j_uri: "neo4j+s://your-instance.neo4j.io"
  neo4j_user: "neo4j"
  neo4j_password: "your-password"
  enable_knowledge_graph: true

data_sources:
  - source_id: "example-github"
    source_type: "github_repo"
    enabled: true
    config:
      repository: "owner/repo-name"
      branch: "main"
      access_token: "projects/PROJECT/secrets/github-token/versions/latest"
      
  - source_id: "example-drive"
    source_type: "drive_folder"
    enabled: true
    config:
      folder_id: "your-drive-folder-id"
      include_subfolders: true
      
  - source_id: "example-web"
    source_type: "web_source"
    enabled: true
    config:
      urls: ["https://example.com"]
      crawl_mode: "same_domain"
      max_pages: 50
```

## Installation and Setup

### 1. Install Dependencies

```bash
# Install dependencies using uv
uv sync

# Install spaCy English model for entity extraction
uv add "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
```

### 2. Google Cloud Setup

```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### 3. Configure Secrets (Optional)

Store sensitive credentials in Google Cloud Secret Manager:

```bash
# GitHub token
gcloud secrets create github-token --data-file=token.txt

# Database passwords
gcloud secrets create db-password --data-file=password.txt
```

### 4. Database Setup

#### PostgreSQL (Cloud SQL)
```sql
-- Create database and tables (handled automatically by DatabaseManager)
-- The system will create the required schema on first run
```

#### Neo4j (Optional)
```cypher
// Neo4j will be set up automatically by KnowledgeGraphManager
// Constraints and indexes are created on initialization
```

## Usage Examples

### Basic Pipeline Execution

```python
import asyncio
from data_ingestion.pipeline.pipeline_manager import PipelineManager, SyncMode

async def run_pipeline():
    # Initialize pipeline with configuration
    pipeline = PipelineManager()
    await pipeline.initialize()
    
    # Run health check
    health = await pipeline.health_check()
    if not health.overall_status:
        print("System not healthy:", health.issues)
        return
    
    # Process all enabled sources
    stats = await pipeline.run_pipeline(sync_mode=SyncMode.SMART_SYNC)
    
    print(f"Processed {stats.successful_documents} documents")
    print(f"Created {stats.successful_chunks} chunks")
    
    # Cleanup
    await pipeline.cleanup()

# Run the pipeline
asyncio.run(run_pipeline())
```

### Individual Component Usage

```python
from data_ingestion.processors.text_processor import TextProcessor
from data_ingestion.managers.vector_store_manager import VectorStoreManager

# Text processing only
processor = TextProcessor(chunk_size=1000, chunk_overlap=100)

document = {
    'content': "Your document content here...",
    'title': "Document Title",
    'source_id': 'example',
    'metadata': {'category': 'documentation'}
}

processed = await processor.process_document(document)
print(f"Created {len(processed.chunks)} chunks")
```

### Querying the System

```python
# Database queries
chunks = await db_manager.search_chunks(
    source_type="github_repo",
    limit=10
)

# Vector similarity search  
query_embedding = await vector_manager.generate_embeddings(["search query"])
results = await vector_manager.search_similar(
    query_embedding[0],
    num_neighbors=5
)

# Knowledge graph queries
entities = await kg_manager.find_entities(
    entity_type="PERSON",
    limit=10
)
```

## Data Flow

### Ingestion Process

1. **Extract**: Connectors fetch documents from sources
2. **Transform**: TextProcessor chunks and extracts entities
3. **Load**: Parallel storage across all systems:
   - PostgreSQL: Chunk metadata and source mapping
   - Vector Search: Embeddings for semantic search
   - Neo4j: Entities and relationships

### Retrieval Process  

1. **Query**: User submits search query
2. **Vector Search**: Find semantically similar chunks
3. **Database Lookup**: Retrieve rich metadata for chunk UUIDs
4. **Context Assembly**: Combine results for LLM context

## Database Schema

### PostgreSQL Tables

```sql
-- Document chunks with metadata
CREATE TABLE document_chunks (
    chunk_uuid UUID PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL,
    source_identifier VARCHAR(512) NOT NULL, 
    chunk_text_summary TEXT,
    chunk_metadata JSONB,
    ingestion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Ingestion tracking
CREATE TABLE ingestion_stats (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(100) NOT NULL,
    chunks_processed INTEGER NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL
);
```

### Neo4j Schema

```cypher
// Entities with properties
(:Entity {id, type, name, properties, source_chunks})

// Relationships between entities  
(:Entity)-[:RELATIONSHIP_TYPE {properties, source_chunks}]->(:Entity)

// Constraints and indexes are automatically created
```

## Monitoring and Health Checks

The system provides comprehensive monitoring:

```python
# System health check
health = await pipeline.health_check()
print(f"Overall healthy: {health.overall_status}")

# Pipeline statistics
stats = await pipeline.get_pipeline_stats()
print(f"Total chunks: {stats['database_stats']['total_chunks']}")
print(f"Entities: {stats['knowledge_graph_stats']['total_entities']}")
```

## Error Handling and Resilience

- **Graceful Degradation**: Components can operate independently
- **Retry Logic**: Automatic retries for transient failures
- **Batch Processing**: Efficient handling of large datasets
- **Health Monitoring**: Continuous system health assessment

## Security Features

- **Secret Management**: Integration with Google Cloud Secret Manager
- **Authentication**: Service account and OAuth support
- **Encryption**: Data encrypted in transit and at rest
- **Access Control**: Fine-grained permissions per data source

## Performance Optimization

- **Async Processing**: Non-blocking operations throughout
- **Batch Operations**: Efficient bulk data handling
- **Connection Pooling**: Optimized database connections
- **Caching**: Secret and configuration caching
- **Rate Limiting**: Prevents API quota exhaustion

## Running the Example

```bash
# Run the complete example
uv run python example_usage.py

# Choose between:
# F - Full pipeline execution with all sources
# I - Individual component demonstration
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Missing spaCy Model**
   ```bash
   python -m spacy download en_core_web_sm
   ```

3. **Database Connection Issues**
   - Verify Cloud SQL instance is running
   - Check firewall rules and authorized networks
   - Confirm connection string format

4. **Vector Search Issues**  
   - Ensure index is deployed and ready
   - Verify endpoint configuration
   - Check Cloud Storage bucket permissions

## Contributing

When extending the system:

1. Follow the existing patterns for async operations
2. Add comprehensive error handling and logging
3. Include type hints and docstrings
4. Write tests for new components
5. Update configuration schema as needed

## License

This implementation is provided as an example and reference architecture. Adapt according to your specific requirements and constraints. 