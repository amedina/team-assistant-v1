# System Overview

You are helping develop a multi-agent Team Assistant system with a sophisticated data ingestion and retrieval subsystem. 

The system implements a Coordinator Pattern with three storage layers:

1. **Vertex AI Vector Search Index** - for semantic similarity searches
2. **Google Cloud PostgreSQL Database** - for document metadata storage  
3. **Neo4j Knowledge Graph Database** - for entities and relationships

## Data Ingestion and Retrieval Components

**Managers (Orchestration Layer):**
- @data_ingestion/managers/vector_store_manager.py
- @data_ingestion/managers/database_manager.py
- @data_ingestion/managers/knowledge_graph_manager.py

**Ingestors (Storage Layer):**
- @data_ingestion/ingestors/vector_store_ingestor.py
- @data_ingestion/ingestors/database_ingestor.py
- @data_ingestion/ingestors/knowledge_graph_ingestor.py

**Retrievers (Query Layer):**
- @data_ingestion/retrievers/vector_store_retriever.py
- @data_ingestion/retrievers/database_retriever.py
- @data_ingestion/retrievers/knowledge_graph_retriever.py

**Data Connectors:**
- @ata_ingestion/connectors/base_connector.py
- @data_ingestion/connectors/drive_connector.py
- @data_ingestion/connectors/github_connector.py
- @data_ingestion/connectors/web_connector.py

**Models (Type Safety Layer):**
- @data_ingestion/models/models.py - Defines type-safe data models for all pipeline components

**Processors (Document Processing Layer):**
- @data_ingestion/processors/text_processor.py - Handles document processing, chunking, entity extraction, and metadata enrichment

**Data Pipeline**
- @data_ingestion/pipeline/pipeline_manager.py
- @data_ingestion/pipeline/pipeline_cli.py

## Agents

**Coordinator Agent**
- @app/agent.py

**Search Agent**
- @agents/search/search_agent.py

**Greeter Agent**
- @agents/greeter/greeter_agent.py

**Context Manager Agent**
- @agents/greeter/greeter_agent.py

# Task

You task consists of:

1. Review the folder @deployment and the Makefile and explain the details of the deployment component of the system. 

2. Understand what is the purpose of "make backend"

3. Determine how to deploy the Agent in @app/ to Agend Engine using "make backend"

