# End-to-End Testing Implementation for Team Assistant Data Ingestion System

## System Overview

You are helping develop a multi-agent Team Assistant system with a sophisticated data ingestion and retrieval subsystem. The system implements a Coordinator Pattern with three storage layers:

1. **Vertex AI Vector Search Index** - for semantic similarity searches
2. **Google Cloud PostgreSQL Database** - for document metadata storage  
3. **Neo4j Knowledge Graph Database** - for entities and relationships

## Complete Architecture Components

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

**Models (Type Safety Layer):**
- `data_ingestion/models/models.py` - Defines type-safe data models for all pipeline components

**Processors (Document Processing Layer):**
- `data_ingestion/processors/text_processor.py` - Handles document processing, chunking, entity extraction, and metadata enrichment

## Task: Design and Implement Comprehensive E2E Test

### Test Objectives

1. **Full Pipeline Flow Validation:**
   - Document ingested through connector → processed by text processor → stored in all 3 systems → successfully retrieved from each

2. **Model Validation:**
   - Verify type-safe data models are correctly used throughout the pipeline
   - Validate data transformations between different model types
   - Ensure data integrity across all components

3. **Text Processing Validation:**
   - Document loading and text extraction functionality
   - Text chunking with overlap processing
   - Entity and relationship extraction accuracy
   - Metadata enrichment completeness

4. **Context Manager Flow Validation:**
   When a user issues a query, the Context Manager must:
   - 4.1: Get relevant documents via similarity search in vector index
   - 4.2: Get metadata for relevant documents from Database  
   - 4.3: Get entities/relations for relevant documents from Knowledge Graph
   - 4.4: Combine all three components and return structured context output

### Critical Testing Requirements

**NO FALLBACK MECHANISMS:** The tests must implement strict failure reporting with zero tolerance for broken functionality:

- Every component must be tested in isolation and integration
- If any single piece of functionality fails, the entire test must fail immediately
- No graceful degradation or partial success scenarios
- All assertions must be mandatory and comprehensive
- Failed components must generate detailed error reports with exact failure points
- Test execution must halt on first critical failure with full diagnostic information

**STRICT FUNCTIONALITY TESTING:**
- Use ONLY the existing functions, methods, and classes defined in the actual implementation files
- Do NOT create new helper functions or wrapper methods for testing
- Test the actual functionality as implemented, not abstracted versions
- Validate return types, data structures, and method signatures exactly as defined
- Use absolute imports for all module references

### Test Scenarios

Implement tests for these four predefined scenarios with enhanced validation:

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
        "ingestion_only": False,
        "text_processing_validation": {
            "min_extracted_text_length": 500,
            "required_chunk_overlap": True,
            "min_entities_extracted": 2,
            "required_metadata_fields": ["file_type", "repository", "branch", "commit_hash"]
        },
        "model_validation": {
            "connector_output_type": "GitHubDocumentModel",
            "processor_output_type": "ProcessedDocumentModel",
            "ingestor_input_type": "ProcessedDocumentModel",
            "retriever_output_type": "RetrievalResultModel"
        }
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
        "ingestion_only": True,
        "text_processing_validation": {
            "min_extracted_text_length": 1000,
            "required_chunk_overlap": True,
            "min_entities_extracted": 3,
            "required_metadata_fields": ["file_type", "drive_id", "folder_path", "last_modified"]
        },
        "model_validation": {
            "connector_output_type": "DriveDocumentModel",
            "processor_output_type": "ProcessedDocumentModel",
            "ingestor_input_type": "ProcessedDocumentModel"
        }
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
        "ingestion_only": False,
        "text_processing_validation": {
            "min_extracted_text_length": 300,
            "required_chunk_overlap": True,
            "min_entities_extracted": 2,
            "required_metadata_fields": ["file_type", "drive_id", "file_name", "last_modified"]
        },
        "model_validation": {
            "connector_output_type": "DriveDocumentModel",
            "processor_output_type": "ProcessedDocumentModel",
            "ingestor_input_type": "ProcessedDocumentModel",
            "retriever_output_type": "RetrievalResultModel"
        }
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
        "ingestion_only": False,
        "text_processing_validation": {
            "min_extracted_text_length": 400,
            "required_chunk_overlap": True,
            "min_entities_extracted": 1,
            "required_metadata_fields": ["url", "title", "content_type", "scraped_at"]
        },
        "model_validation": {
            "connector_output_type": "WebDocumentModel",
            "processor_output_type": "ProcessedDocumentModel",
            "ingestor_input_type": "ProcessedDocumentModel",
            "retriever_output_type": "RetrievalResultModel"
        }
    }
}
```

### Enhanced Technical Requirements

- **Testing Framework:** pytest with strict assertion modes
- **Service Integration:** Use real instances of all services (Vertex AI, PostgreSQL, Neo4j)
- **Import Strategy:** Use absolute paths for ALL module imports
- **Functionality Testing:** Test ONLY existing functions and methods as implemented
- **Configuration Management:** Use the existing project configuration system
  - Load storage target configurations from `config/data_sources_config.yaml`
  - Define data source configurations as part of the test scenario structure
  - Follow the project's configuration patterns and approach
- **Execution:** Simple Python script that can be run directly
- **Error Handling:** Comprehensive failure reporting with zero tolerance for broken functionality

### Command Line Arguments

The test script must support these parameters:

```bash
# Test specific scenario
python e2e_test.py --scenario github

# Test specific storage targets
python e2e_test.py --scenario github --targets vector,database
python e2e_test.py --scenario drive --targets knowledge_graph

# Test specific components
python e2e_test.py --scenario web --components models,processors,connectors
python e2e_test.py --scenario drive_file --components text_processing,retrieval

# Verbosity control
python e2e_test.py --verbose
python e2e_test.py --quiet

# Test phase control
python e2e_test.py --scenario web --phase ingestion
python e2e_test.py --scenario drive_file --phase retrieval  
python e2e_test.py --scenario github --phase full  # default

# Failure modes
python e2e_test.py --fail-fast  # Stop on first failure
python e2e_test.py --strict-validation  # Enable all validation checks
```

### Enhanced Implementation Steps

1. **Study the existing codebase** to understand current patterns, APIs, and data models
2. **Examine the configuration system** (`config/data_sources_config.yaml`) to understand how storage targets and data sources are configured
3. **Analyze the models architecture** (`data_ingestion/models/models.py`) to understand type definitions and data flow
4. **Study the text processor** (`data_ingestion/processors/text_processor.py`) to understand document processing workflows
5. **Examine isolation tests** (`tests/vector_store_isolation_test.py`, etc.) for patterns to follow
6. **Design the E2E test structure** with proper pytest fixtures and parameterization
7. **Integrate with existing configuration** - load storage configurations from YAML, define test data sources within scenario structure
8. **Implement model validation testing** for type safety and data integrity
9. **Implement text processing validation** for chunking, entity extraction, and metadata enrichment
10. **Implement full pipeline testing** for each connector type
11. **Implement Context Manager flow testing** with the 4-step validation process
12. **Add comprehensive assertions** validating data consistency across all storage systems
13. **Implement command-line argument handling** with proper defaults and validation
14. **Add detailed logging and reporting** for test results and timing metrics
15. **Implement strict failure reporting** with zero tolerance for broken functionality

### Component-Specific Test Requirements

#### Models Testing (`data_ingestion/models/models.py`)
- **Type Safety Validation:** Verify all data models maintain type safety throughout the pipeline
- **Data Transformation Testing:** Validate conversions between different model types
- **Schema Compliance:** Ensure data structures match defined model schemas
- **Serialization/Deserialization:** Test model persistence and retrieval integrity

#### Text Processor Testing (`data_ingestion/processors/text_processor.py`)
- **Document Loading:** Validate text extraction from various document formats
- **Chunking Algorithm:** Test text chunking with configurable overlap settings
- **Entity Extraction:** Verify accurate identification and extraction of entities
- **Relationship Mapping:** Test relationship detection and graph construction
- **Metadata Enrichment:** Validate metadata generation and attachment

#### Integration Testing Requirements
- **Cross-Component Data Flow:** Validate data integrity as it moves between components
- **Performance Benchmarking:** Measure and validate processing times for each component
- **Memory Usage Monitoring:** Track memory consumption during processing
- **Error Propagation:** Test error handling and reporting across the pipeline

### Success Criteria

- All test scenarios pass end-to-end validation with ZERO tolerance for failures
- Data consistency maintained across Vector Store, Database, and Knowledge Graph
- Model type safety validated throughout the entire pipeline
- Text processing functionality verified for accuracy and completeness
- Context Manager retrieval flow produces expected structured output
- All existing functions and methods tested as implemented without modifications
- Flexible execution options work correctly
- Clear reporting of test results and performance metrics
- Comprehensive failure reporting with detailed diagnostic information

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

**Essential Architecture Components:**
10. `data_ingestion/models/models.py` - Type-safe data models for pipeline components
11. `data_ingestion/processors/text_processor.py` - Document processing and chunking functionality

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

### Critical Implementation Guidelines

1. **Absolute Import Requirements:** All module imports must use absolute paths from the project root
2. **Function Testing Mandate:** Test ONLY the existing functions, methods, and classes as defined in the implementation files
3. **Zero Fallback Policy:** No graceful degradation - all functionality must work or tests must fail completely
4. **Type Safety Enforcement:** Validate model usage and type consistency throughout the pipeline
5. **Processing Validation:** Thoroughly test text processing, chunking, and entity extraction functionality
6. **Integration Completeness:** Ensure end-to-end data flow validation across all components

Create a comprehensive, production-ready E2E test that validates the Team Assistant's complete data ingestion and retrieval capabilities while maintaining strict adherence to existing codebase patterns, architecture, and functionality without any fallback mechanisms.