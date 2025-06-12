# End-to-End Testing Implementation for Team Assistant Data Ingestion System

## System Overview

You are helping develop a multi-agent Team Assistant system with a sophisticated data ingestion and retrieval subsystem. The system implements a Coordinator Pattern with three storage layers:

1. **Vertex AI Vector Search Index** - for semantic similarity searches
2. **Google Cloud PostgreSQL Database** - for document metadata storage  
3. **Neo4j Knowledge Graph Database** - for entities and relationships

## Architecture Components

**Managers (Orchestration Layer):**
- `data_ingestion/managers/vector_store_manager.py`
- `data_ingestion/managers/database_manager.py`
- `data_ingestion/managers/knowledge_graph_manager.py`

**Ingestors (Storage Layer):**
- `data_ingestion/ingestors/vector_store_ingestor.py`
- `data_ingestion/ingestors/database_ingestor.py`
- `data_ingestion/ingestors/knowledge_graph_ingestor.py`

**Retrievers (Query Layer):**
- `data_ingestion/retrievers/vector_store_retriever.py`
- `data_ingestion/retrievers/database_retriever.py`
- `data_ingestion/retrievers/knowledge_graph_retriever.py`

**Data Connectors:**
- `data_ingestion/connectors/base_connector.py`
- `data_ingestion/connectors/drive_connector.py`
- `data_ingestion/connectors/github_connector.py`
- `data_ingestion/connectors/web_connector.py`

## Task: Design and Implement Comprehensive E2E Test

### Test Objectives

1. **Full Pipeline Flow Validation:**
   - Document ingested through connector → stored in all 3 systems → successfully retrieved from each

2. **Context Manager Flow Validation:**
   When a user issues a query, the Context Manager must:
   - 2.1: Get relevant documents via similarity search in vector index
   - 2.2: Get metadata for relevant documents from Database  
   - 2.3: Get entities/relations for relevant documents from Knowledge Graph
   - 2.4: Combine all three components and return structured context output

### Test Scenarios

Implement tests for these four predefined scenarios:

```python
TEST_SCENARIOS = {
    "github": {
        "test_id": "GITHUB-001",
        "source_type": "github_repo", 
        "source_identifier": "GoogleChromeLabs/ps-analysis-tool",
        "target_file": "README",
        "query": "privacy sandbox analysis tool",
        "expected_keywords": ["privacy", "sandbox", "analysis", "tool", "chrome"],
        "expected_entities": ["Privacy Sandbox", "Chrome", "analysis", "tool"],
        "expected_source_pattern": "github:GoogleChromeLabs/ps-analysis-tool",
        "min_chunks_expected": 3,
        "min_vector_similarity": 0.2,
        "max_response_time_ms": 5000,
        "description": "Enhanced GitHub repository file ingestion and retrieval validation",
        "ingestion_only": False
    },
    "drive": {
        "test_id": "DRIVE-002",
        "source_type": "drive_folder",
        "source_identifier": "1ptFZLZApmOZw6NWpmxoEGEAKwBaBhIcm",
        "target_file": "DevRel Assistance Documents",
        "query": "N/A - ingestion only",
        "expected_keywords": ["N/A - ingestion only"],
        "expected_entities": ["N/A - ingestion only"],
        "expected_source_pattern": "drive:1ptFZLZApmOZw6NWpmxoEGEAKwBaBhIcm",
        "min_chunks_expected": 5,
        "min_vector_similarity": 0.0,
        "max_response_time_ms": 30000,
        "description": "Google Drive folder ingestion validation (ingestion-only test)",
        "ingestion_only": True
    },
    "drive_file": {
        "test_id": "DRIVE-FILE-003",
        "source_type": "drive_file",
        "source_identifier": "1YFOl19kCN782a-cJF_1LQHcIppcpKzHhsy_y0rr4Ro4",
        "target_file": "Individual Drive File",
        "query": "DevRel guidance assistance development",
        "expected_keywords": ["devrel", "guidance", "documentation", "assistance", "development"],
        "expected_entities": ["DevRel", "assistance", "development"],
        "expected_source_pattern": "drive:1YFOl19kCN782a-cJF_1LQHcIppcpKzHhsy_y0rr4Ro4",
        "min_chunks_expected": 2,
        "min_vector_similarity": 0.15,
        "max_response_time_ms": 6000,
        "description": "Enhanced individual Google Drive file processing validation",
        "ingestion_only": False
    },
    "web": {
        "test_id": "WEB-004",
        "source_type": "web_source",
        "source_identifier": "https://docs.python.org/3/tutorial/introduction.html",
        "target_file": "Python Tutorial Introduction",
        "query": "python operator calculate powers",
        "expected_keywords": ["python", "operator", "calculate", "powers"],
        "expected_entities": ["Python", "operator", "calculate"],
        "expected_source_pattern": "web:https://docs.python.org/3/tutorial/introduction.html",
        "min_chunks_expected": 2,
        "min_vector_similarity": 0.15,
        "max_response_time_ms": 4000,
        "description": "Enhanced web page ingestion and retrieval validation",
        "ingestion_only": False
    }
}
```

### Technical Requirements

- **Testing Framework:** pytest
- **Service Integration:** Use real instances of all services (Vertex AI, PostgreSQL, Neo4j)
- **Configuration Management:** Use the existing project configuration system
  - Load storage target configurations from `config/data_sources_config.yaml`
  - Define data source configurations as part of the test scenario structure
  - Follow the project's configuration patterns and approach
- **Execution:** Simple Python script that can be run directly
- **No Error Scenarios:** Focus on successful flow validation only

### Command Line Arguments

The test script must support these parameters:

```bash
# Test specific scenario
python e2e_test.py --scenario github

# Test specific storage targets
python e2e_test.py --scenario github --targets vector,database
python e2e_test.py --scenario drive --targets knowledge_graph

# Verbosity control
python e2e_test.py --verbose
python e2e_test.py --quiet

# Test phase control
python e2e_test.py --scenario web --phase ingestion
python e2e_test.py --scenario drive_file --phase retrieval  
python e2e_test.py --scenario github --phase full  # default
```

### Implementation Steps

1. **Study the existing codebase** to understand current patterns, APIs, and data models
2. **Examine the configuration system** (`config/data_sources_config.yaml`) to understand how storage targets and data sources are configured
3. **Examine isolation tests** (`tests/vector_store_isolation_test.py`, etc.) for patterns to follow
4. **Design the E2E test structure** with proper pytest fixtures and parameterization
5. **Integrate with existing configuration** - load storage configurations from YAML, define test data sources within scenario structure
6. **Implement full pipeline testing** for each connector type
7. **Implement Context Manager flow testing** with the 4-step validation process
8. **Add comprehensive assertions** validating data consistency across all storage systems
9. **Implement command-line argument handling** with proper defaults and validation
10. **Add detailed logging and reporting** for test results and timing metrics

### Success Criteria

- All test scenarios pass end-to-end validation
- Data consistency maintained across Vector Store, Database, and Knowledge Graph
- Context Manager retrieval flow produces expected structured output
- Flexible execution options work correctly
- Clear reporting of test results and performance metrics

### Files to Study

Please examine these specific implementation files to understand the current system:

**Core Implementation Files:**
1. `data_ingestion/managers/vector_store_manager.py`
2. `data_ingestion/managers/database_manager.py`
3. `data_ingestion/managers/knowledge_graph_manager.py`
4. `data_ingestion/ingestors/vector_store_ingestor.py`
5. `data_ingestion/ingestors/database_ingestor.py`
6. `data_ingestion/ingestors/knowledge_graph_ingestor.py`
7. `data_ingestion/retrievers/vector_store_retriever.py`
8. `data_ingestion/retrievers/database_retriever.py`
9. `data_ingestion/retrievers/knowledge_graph_retriever.py`

**Existing Test Files (for patterns and conventions):**
- `tests/vector_store_isolation_test.py`
- `tests/knowledge_graph_isolation_test.py`
- `tests/database_isolation_test.py`

**Configuration File (for understanding project configuration patterns):**
- `config/data_sources_config.yaml`

**Data Connectors (for understanding data flow):**
- `data_ingestion/connectors/base_connector.py`
- `data_ingestion/connectors/drive_connector.py`
- `data_ingestion/connectors/github_connector.py`
- `data_ingestion/connectors/web_connector.py`

Create a comprehensive, production-ready E2E test that validates the Team Assistant's data ingestion and retrieval capabilities while maintaining consistency with the existing codebase patterns and architecture.