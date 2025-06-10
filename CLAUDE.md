# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a team assistant agent built with Google's Agent Development Kit (ADK). It features a coordinator agent that delegates tasks to specialized sub-agents (greeting, search, and context management). The system also includes a comprehensive data ingestion and retrieval pipeline with multi-modal storage.

## Development Commands

### Setup and Installation
```bash
make install          # Install dependencies using uv
```

### Running the Application
```bash
make playground       # Launch ADK web interface on port 8501
make backend         # Deploy agent to Agent Engine
```

### Testing
```bash
make test            # Run unit and integration tests
uv run pytest tests/unit -k test_name  # Run specific test

# For data pipeline tests:
uv run python -m pytest tests/database_isolation_test.py
uv run python -m pytest tests/vector_store_isolation_test.py
uv run python -m pytest tests/knowledge_graph_isolation_test.py
```

### Code Quality
```bash
make lint            # Run all linters (codespell, ruff, mypy)
uv run ruff check . --fix  # Auto-fix linting issues
uv run ruff format .       # Format code
```

### Data Pipeline
```bash
uv run python -m data_ingestion.pipeline.pipeline_cli --help  # Pipeline CLI help
```

## Architecture

### Agent System
- **Coordinator Agent** (app/agent.py:62-78): Main orchestrator using gemini-1.5-pro-latest
- **Sub-agents**: Located in `agents/` directory
  - Greeting Agent: Basic conversational responses
  - Search Agent: Web search capabilities
  - Context Manager Agent: Privacy Sandbox specific knowledge

### Data Processing Pipeline

- **Configuration**: Managed via `config/data_sources_config.yaml` and `config/configuration.py`
- **Storage Systems**:
  - Vector Search: Vertex AI Vector Search for semantic search
  - PostgreSQL: Cloud SQL for metadata and chunk mapping
  - Neo4j: Knowledge graph for entities and relationships
- **Connectors**
Data is ingested and retrieved into/from these storage targets through data connectors:

data_ingestion/connectors/base_connector.py
data_ingestion/connectors/drive_connector.py
data_ingestion/connectors/github_connector.py
data_ingestion/connectors/web_connector.py

- **_Managers (Orchestration Layer)_**:
`data_ingestion/managers/vector_store_manager.py`: Embeddings and similarity search
`data_ingestion/managers/database_manager.py`: Metadata and chunk storage
`data_ingestion/managers/knowledge_graph_manager.py`: Entity/relationship 
`PipelineManager`: Central orchestration management

- **_Ingestors (Storage Layer)_**
data_ingestion/ingestors/vector_store_ingestor.py
data_ingestion/ingestors/database_ingestor.py
data_ingestion/ingestors/knowledge_graph_ingestor.py

- **_Retrievers (Query Layer)_**
data_ingestion/retrievers/vector_store_retrievers.py
data_ingestion/retrievers/database_retrievers.py
data_ingestion/retrievers/knowledge_graph_retrievers.py


### Configuration Management
The system uses YAML-based configuration with environment variable support. The main config file is `config/data_sources_config.yaml`. Configuration is loaded through `ConfigurationManager` in `config/configuration.py:236-341`.

## Development Patterns

### Async Operations
Most data pipeline components use async/await patterns. Example:
```python
async with DatabaseManager(config) as db_manager:
    await db_manager.initialize()
```

### Error Handling
Use structured logging and proper exception handling:
```python
logger = logging.getLogger(__name__)
try:
    # operation
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### Testing Strategy
- Unit tests: Test individual components in isolation
- Integration tests: Test component interactions
- Isolation tests: Test each storage system separately

1. tests tests/vector_store_isolation_test.py
2. tests/knowledge_graph_isolation_test.py
3. tests/database_isolation_test.py

- Use pytest fixtures for setup/teardown

## Key Dependencies
- `google-adk~=1.1.0`: Agent Development Kit
- `google-cloud-aiplatform`: Vertex AI integration
- `asyncpg`: PostgreSQL async operations
- `neo4j`: Graph database client
- `spacy`: NLP for entity extraction
- `uv`: Package management

## Environment Variables
- `GOOGLE_API_KEY`: Google API key
- `NEO4J_PASSWORD`: Neo4j database password (optional, can be in config)
- `GOOGLE_APPLICATION_CREDENTIALS`: should be configured via `gcloud auth`
- `GITHUB_TOKEN`: Github access token

## Deployment
- Dev environment setup: `make setup-dev-env`
- Uses Terraform for infrastructure (see `deployment/terraform/`)
- CI/CD pipelines configured in `deployment/ci/` and `deployment/cd/`