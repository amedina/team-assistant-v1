# Team Assistant E2E Test Framework

This directory contains the comprehensive End-to-End (E2E) test framework for the Team Assistant's data ingestion and retrieval system. The framework validates the complete pipeline flow across all three storage layers: Vector Store (Vertex AI), Database (PostgreSQL), and Knowledge Graph (Neo4j).

## Framework Architecture

The E2E test framework follows a modular design with clear separation of concerns:

```
tests/e2e/
├── test_e2e_data_pipeline.py     # Main E2E pipeline tests
├── test_context_manager.py       # Context Manager flow tests
├── test_scenarios.py             # Test scenario definitions
├── fixtures/                     # Pytest fixtures
│   ├── __init__.py
│   ├── configuration.py         # Configuration fixtures
│   ├── managers.py              # Manager lifecycle fixtures
│   └── test_data.py             # Test data fixtures
├── utils/                        # Utility modules
│   ├── __init__.py
│   ├── assertions.py            # Custom assertions
│   └── reporting.py             # Test reporting utilities
└── README.md                    # This file
```

## Test Scenarios

The framework includes four predefined test scenarios:

### 1. GitHub Repository (`github`)
- **Source**: `GoogleChromeLabs/ps-analysis-tool`
- **Target File**: README.md
- **Query**: "privacy sandbox analysis tool"
- **Min Chunks**: 3
- **Min Similarity**: 0.2

### 2. Google Drive Folder (`drive`)
- **Source**: DevRel Assistance Documents folder
- **Mode**: Ingestion-only testing
- **Min Chunks**: 5
- **Max Response Time**: 30s

### 3. Google Drive File (`drive_file`)
- **Source**: Individual Drive document
- **Query**: "DevRel guidance assistance development"
- **Min Chunks**: 2
- **Min Similarity**: 0.15

### 4. Web Source (`web`)
- **Source**: Python Tutorial Introduction
- **Query**: "python operator calculate powers"
- **Min Chunks**: 2
- **Min Similarity**: 0.15

## Test Phases

### Full Pipeline (`--phase full`)
Complete end-to-end validation including:
1. Document fetching from source
2. Data ingestion to all storage systems
3. Data retrieval from all storage systems
4. Context Manager flow integration

### Ingestion Only (`--phase ingestion`)
Focuses on data ingestion performance and consistency:
1. Document processing and chunking
2. Parallel ingestion to Vector Store, Database, and Knowledge Graph
3. Data consistency validation across systems

### Retrieval Only (`--phase retrieval`)
Tests query and retrieval capabilities:
1. Vector similarity search
2. Database metadata retrieval
3. Knowledge Graph entity/relationship queries
4. Context Manager 4-step flow

## Context Manager Flow

The framework validates the complete 4-step Context Manager flow:

1. **Vector Search**: Get relevant documents via similarity search
2. **Database Metadata**: Retrieve metadata for relevant documents
3. **Knowledge Graph**: Get entities/relationships for relevant documents
4. **Context Combination**: Combine all components into structured output

## Usage

### Command Line Interface

Run tests using the main entry point script:

```bash
# Test all scenarios with full pipeline
python tests/e2e/e2e_test.py

# Test specific scenario
python tests/e2e/e2e_test.py --scenario github

# Test with specific storage targets
python tests/e2e/e2e_test.py --scenario github --targets vector,database

# Test specific phase
python tests/e2e/e2e_test.py --scenario web --phase ingestion
python tests/e2e/e2e_test.py --scenario drive_file --phase retrieval

# Verbose output
python tests/e2e/e2e_test.py --verbose

# Quiet output
python tests/e2e/e2e_test.py --quiet
```

### Direct Pytest Execution

You can also run tests directly with pytest:

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Run specific test file
pytest tests/e2e/test_e2e_data_pipeline.py -v

# Run specific scenario
pytest tests/e2e/test_e2e_data_pipeline.py::TestE2EDataPipeline::test_full_pipeline_scenario[github] -v

# Run Context Manager tests
pytest tests/e2e/test_context_manager.py -v
```

## Configuration Requirements

### 1. System Configuration
Ensure `config/data_sources_config.yaml` is properly configured with:
- Vector Search index and endpoint
- PostgreSQL database connection
- Neo4j knowledge graph connection
- Data source configurations

### 2. Authentication
Set up proper authentication for:
- Google Cloud (Application Default Credentials)
- GitHub access tokens (via Secret Manager)
- Neo4j credentials

### 3. Dependencies
Install required packages:
```bash
pip install pytest pytest-asyncio
```

## Test Fixtures

### Configuration Fixtures (`fixtures/configuration.py`)
- `system_config`: Loads system configuration
- `storage_targets`: Determines available storage targets
- `test_isolation_id`: Generates unique test isolation ID
- `validate_configuration`: Validates system configuration

### Manager Fixtures (`fixtures/managers.py`)
- `vector_store_manager`: Initializes Vector Store Manager
- `database_manager`: Initializes Database Manager
- `knowledge_graph_manager`: Initializes Knowledge Graph Manager
- `active_managers`: Provides filtered managers for testing
- `manager_health_check`: Performs health checks

### Test Data Fixtures (`fixtures/test_data.py`)
- `test_scenario`: Provides scenario configuration
- `connector_instance`: Creates connector instances
- `test_documents`: Fetches documents from sources
- `processed_test_chunks`: Processes documents into chunks

## Custom Assertions

The framework includes specialized assertions in `utils/assertions.py`:

- `assert_ingestion_success()`: Validates ingestion across storage systems
- `assert_retrieval_results()`: Validates retrieval results
- `assert_context_manager_flow()`: Validates Context Manager output
- `assert_keyword_presence()`: Validates content keywords
- `assert_performance_metrics()`: Validates timing requirements

## Test Reporting

### Console Output
Real-time test progress with colored output:
- ✅ Passed tests
- ❌ Failed tests
- ⚠️ Warnings
- 📊 Summary statistics

### Generated Reports
Tests generate comprehensive reports in `test_results/`:
- **JSON Report**: Machine-readable test results
- **HTML Report**: Human-readable test report with charts
- **Console Summary**: Detailed console output

### Report Structure
```json
{
  "test_session_id": "e2e_20231215_143022_a1b2c3d4",
  "overall_success": true,
  "success_rate": 0.75,
  "total_scenarios": 4,
  "successful_scenarios": 3,
  "failed_scenarios": 1,
  "test_metrics": {
    "GITHUB-001": {
      "success": true,
      "duration_ms": 5420,
      "chunks_ingested": 3,
      "chunks_retrieved": 5
    }
  }
}
```

## Performance Expectations

### Response Time Targets
- **GitHub**: < 5 seconds
- **Drive File**: < 6 seconds
- **Web**: < 4 seconds
- **Drive Folder**: < 30 seconds

### Success Rate Targets
- **Ingestion**: > 80% success rate
- **Retrieval**: > 90% relevance accuracy
- **Overall**: > 75% test pass rate

## Troubleshooting

### Common Issues

1. **Configuration Errors**
   ```
   Configuration validation failed:
     - Vector Search configuration is missing
   ```
   **Solution**: Check `config/data_sources_config.yaml` for missing fields

2. **Authentication Failures**
   ```
   Failed to initialize VectorStoreManager: 403 Forbidden
   ```
   **Solution**: Verify Google Cloud credentials and permissions

3. **Connection Timeouts**
   ```
   Neo4j connection test failed
   ```
   **Solution**: Check Neo4j URI and network connectivity

4. **Missing Dependencies**
   ```
   DriveConnector not available - skipping drive test
   ```
   **Solution**: Install missing connector dependencies

### Debug Mode
Run with verbose logging for detailed diagnostics:
```bash
python tests/e2e/e2e_test.py --verbose --scenario github
```

### Test Isolation
Each test run uses a unique isolation ID to prevent data conflicts:
- Test data is tagged with isolation ID
- Cleanup processes use isolation ID
- Multiple test runs can execute concurrently

## Development

### Adding New Scenarios
1. Define scenario in `test_scenarios.py`
2. Add connector configuration in `create_data_source_config()`
3. Update test parametrization in test files

### Adding New Assertions
1. Add assertion function to `utils/assertions.py`
2. Follow existing patterns for error reporting
3. Include soft assertion options for warnings

### Extending Reporting
1. Modify `TestMetrics` dataclass in `utils/reporting.py`
2. Update report generation methods
3. Add new visualization elements to HTML reports

## Integration with CI/CD

The E2E tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run E2E Tests
  run: |
    python tests/e2e/e2e_test.py --scenario github --quiet
    python tests/e2e/e2e_test.py --scenario web --phase ingestion --quiet
```

For production environments, consider:
- Running tests against staging instances
- Using test-specific data sources
- Implementing test data cleanup
- Setting appropriate timeouts

## Contributing

When contributing to the E2E test framework:

1. Follow the modular architecture
2. Add comprehensive docstrings
3. Include proper error handling
4. Update this README for new features
5. Ensure test isolation and cleanup

# E2E Testing Framework - Enhanced with Models and Text Processor

## Overview

This comprehensive E2E testing framework validates the complete Team Assistant data ingestion pipeline, now **enhanced with actual models and text processor integration** for realistic document processing and type-safe data validation.

## Architecture Integration

### Core Components Tested

#### 1. **Models** (`data_ingestion/models/models.py`)
- **Type-safe Pydantic models** for all pipeline components
- **Data validation** and constraints enforcement
- **Enum types** for source types, ingestion status, entity types
- **Unified data structures** across all storage systems

**Key Models Used:**
- `ChunkData` - Core chunk information with metadata
- `Entity` - Knowledge graph entities with types and properties
- `Relationship` - Entity relationships with source tracking
- `VectorRetrievalResult` - Vector search results with similarity scores
- `RetrievalContext` - Combined context from all storage systems
- `LLMRetrievalContext` - LLM-optimized retrieval format
- `ComponentHealth` - System health monitoring

#### 2. **Text Processor** (`data_ingestion/processors/text_processor.py`)
- **Document processing** with intelligent chunking
- **Entity extraction** using spaCy NLP models
- **Relationship extraction** between entities
- **Text cleaning** and normalization
- **Metadata enrichment** for chunks

**Processing Capabilities:**
- Sentence-aware text splitting with overlap
- Entity recognition (PERSON, ORGANIZATION, LOCATION, etc.)
- Relationship inference based on entity proximity
- Content validation and token limit management
- Processing statistics and error handling

#### 3. **Pipeline Manager** (`data_ingestion/pipeline/pipeline_manager.py`)
- **Coordinator pattern** implementation
- **End-to-end flow orchestration**
- **Batch operations** with error handling
- **Health monitoring** across all components

## Test Structure

### Test Scenarios with Real Processing

```python
@pytest.mark.parametrize("test_scenario", ["github", "drive_folder", "drive_file", "web"], indirect=True)
```

Each scenario now uses:
- **Real connectors** to fetch documents
- **Actual TextProcessor** for document processing
- **Type-safe models** for data validation
- **Realistic content** for entity extraction

### Enhanced Test Flow

#### 1. **Document Processing** (`test_data.py`)
```python
@pytest.fixture
async def processed_test_documents(
    test_documents: List[SourceDocument], 
    text_processor: TextProcessor,
    test_isolation_id: str
) -> List[ProcessedDocument]:
```

- Converts `SourceDocument` objects to processed documents
- Uses actual `TextProcessor.process_document()` method
- Extracts entities and relationships from content
- Generates processing statistics and metadata

#### 2. **Model Conversion** (`test_data.py`)
```python
@pytest.fixture
def processed_test_chunks(processed_test_documents: List[ProcessedDocument]) -> List[ChunkData]:
```

- Converts `ProcessedDocument` chunks to `ChunkData` models
- Validates Pydantic model constraints
- Ensures type safety and data integrity
- Preserves entity and relationship references

#### 3. **Pipeline Testing** (`test_e2e_data_pipeline.py`)

**Enhanced Tests:**
- `test_full_pipeline_flow` - Complete E2E with models
- `test_text_processor_integration` - Document processing validation
- `test_model_validation` - Type safety and constraints

**Validation Points:**
- TextProcessor configuration and capabilities
- Entity extraction quality and types
- Relationship inference accuracy
- Model constraint enforcement
- Cross-system data consistency

#### 4. **Context Manager Testing** (`test_context_manager.py`)

**4-Step Flow with Models:**
1. **Vector Search** → `VectorRetrievalResult` models
2. **Database Enrichment** → `ChunkData` models
3. **Knowledge Graph Context** → `Entity`/`Relationship` models
4. **Combined Output** → `RetrievalContext` model

**LLM Context Generation:**
- `LLMRetrievalContext` model for optimized LLM input
- Token count estimation and management
- Context summarization and relevance scoring

## Key Features

### 1. **Realistic Data Processing**

Instead of mock data, tests now use:
```python
# Real document processing
processed_doc = await text_processor.process_document(doc_dict, extract_entities=True)

# Actual entity extraction
for chunk in processed_doc.chunks:
    if chunk.entities:
        entities.extend(chunk.entities)
    if chunk.relationships:
        relationships.extend(chunk.relationships)
```

### 2. **Type-Safe Validation**

All data structures use Pydantic models:
```python
# ChunkData validation
assert isinstance(chunk, ChunkData), f"Expected ChunkData, got {type(chunk)}"
assert isinstance(chunk.chunk_uuid, uuid.UUID), "chunk_uuid should be a UUID"
assert isinstance(chunk.source_type, SourceType), "source_type should be a SourceType enum"

# Entity validation
assert isinstance(entity, Entity), f"Expected Entity, got {type(entity)}"
assert isinstance(entity.entity_type, EntityType), "entity_type should be an EntityType enum"
```

### 3. **Enhanced Content Generation**

Mock documents now include realistic content for entity extraction:
```python
# GitHub scenario - Privacy Sandbox content
"""# Privacy Sandbox Analysis Tool
This is a Chrome extension that helps developers analyze Privacy Sandbox features and APIs.
## Features
- Analysis of Chrome Privacy Sandbox APIs including Topics API, FLEDGE, Trust Tokens
- Developer tools integration for real-time analysis"""

# Drive scenario - DevRel content
"""# DevRel Assistance and Development Guidelines
This document provides comprehensive guidance for developer relations assistance.
## DevRel Best Practices
- Developer-focused assistance programs that provide direct support
- Community engagement strategies that build strong developer relationships"""
```

### 4. **Comprehensive Validation**

Tests now validate:
- **Processing Statistics**: Chunk counts, entity counts, processing times
- **Entity Types**: PERSON, ORGANIZATION, LOCATION, TECHNOLOGY, etc.
- **Relationship Types**: MENTIONED_WITH, proximity-based relationships
- **Model Constraints**: UUID validation, enum types, required fields
- **Cross-Model References**: Entity-chunk relationships, relationship-chunk references

## Running Tests

### Full Test Suite
```bash
python tests/e2e/e2e_test.py --scenario all --target all --phase all --verbose
```

### Specific Model Testing
```bash
python tests/e2e/e2e_test.py --scenario github --target all --phase pipeline --verbose
```

### Text Processor Validation
```bash
python tests/e2e/e2e_test.py --scenario drive_folder --target all --phase context --verbose
```

## Configuration

### TextProcessor Settings (E2E)
```python
TextProcessor(
    chunk_size=800,           # Smaller chunks for testing
    chunk_overlap=100,        # Overlap for context
    enable_entity_extraction=True  # Full NLP processing
)
```

### Test Data Validation
```python
validation_results = {
    "documents_processed": len(processed_test_documents),
    "chunks_count": len(processed_test_chunks),
    "entities_count": len(extracted_entities),
    "relationships_count": len(extracted_relationships),
    "meets_minimum_chunks": len(processed_test_chunks) >= test_scenario.min_chunks_expected,
    "has_entities": len(extracted_entities) > 0,
    "has_relationships": len(extracted_relationships) > 0
}
```

## Benefits of Model Integration

### 1. **Realistic Testing**
- Actual document processing pipeline
- Real entity extraction and relationship inference
- Authentic content chunking and metadata generation

### 2. **Type Safety**
- Compile-time validation of data structures
- Pydantic model constraints enforcement
- Enum type validation for consistent values

### 3. **Better Error Detection**
- Model validation catches schema issues
- Type mismatches detected early
- Data integrity violations prevented

### 4. **Production Parity**
- Tests use same models as production code
- Identical processing logic validation
- Real-world data structure testing

## Future Enhancements

### 1. **Advanced Entity Types**
- Custom entity recognition training
- Domain-specific entity extraction
- Confidence scoring improvements

### 2. **Relationship Inference**
- Semantic relationship extraction
- Context-aware relationship types
- Multi-hop relationship discovery

### 3. **Processing Optimization**
- Batch processing validation
- Performance testing with models
- Memory usage optimization testing

### 4. **Model Evolution**
- Schema migration testing
- Backward compatibility validation
- Model versioning support

This enhanced E2E testing framework provides comprehensive validation of the complete data ingestion pipeline using actual production components, ensuring high-quality, type-safe data processing throughout the system.

## Command-Line Interface Parameters

### Overview

The E2E testing framework provides a flexible command-line interface for running targeted tests based on your development and validation needs. All tests are executed through the main entry point:

```bash
python tests/e2e/e2e_test.py [options]
```

### Complete Parameter Reference

#### **`--scenario`** | **Test Scenario Selection**

**Purpose:** Selects which data source scenario(s) to test

**Options:**
- `github` - GitHub repository ingestion and retrieval
- `drive` - Google Drive folder ingestion (ingestion-only)
- `drive_file` - Individual Google Drive file processing  
- `web` - Web page content ingestion and retrieval
- `all` - Run all available scenarios *(default)*

**Examples:**
```bash
# Test GitHub repository scenario
python tests/e2e/e2e_test.py --scenario github

# Test Google Drive folder ingestion
python tests/e2e/e2e_test.py --scenario drive

# Test individual Drive file processing
python tests/e2e/e2e_test.py --scenario drive_file

# Test web page ingestion
python tests/e2e/e2e_test.py --scenario web

# Run all scenarios (default behavior)
python tests/e2e/e2e_test.py --scenario all
python tests/e2e/e2e_test.py  # equivalent
```

**Scenario Details:**
| Scenario | Source Type | Retrieval Testing | Description |
|----------|-------------|------------------|-------------|
| `github` | `github_repo` | ✅ Yes | Privacy Sandbox Analysis Tool repository |
| `drive` | `drive_folder` | ❌ Ingestion only | DevRel Assistance Documents folder |
| `drive_file` | `drive_file` | ✅ Yes | Individual DevRel guidance document |
| `web` | `web_source` | ✅ Yes | Python tutorial web page |

---

#### **`--phase`** | **Test Phase Control**

**Purpose:** Controls which testing phases are executed

**Options:**
- `ingestion` - Document fetching, processing, and storage validation
- `retrieval` - Data retrieval and context generation validation
- `full` - Complete end-to-end flow *(default)*

**Examples:**
```bash
# Test only ingestion phase
python tests/e2e/e2e_test.py --phase ingestion --scenario github

# Test only retrieval phase  
python tests/e2e/e2e_test.py --phase retrieval --scenario web

# Test complete end-to-end flow (default)
python tests/e2e/e2e_test.py --phase full --scenario github
python tests/e2e/e2e_test.py --scenario github  # equivalent
```

**Phase Breakdown:**

##### **`--phase ingestion`**
**What it tests:**
- ✅ Document connector functionality
- ✅ TextProcessor document chunking
- ✅ Entity extraction with spaCy
- ✅ Relationship inference
- ✅ Database chunk storage
- ✅ Vector Store embedding generation
- ✅ Knowledge Graph entity/relationship storage
- ✅ Model validation (ChunkData, Entity, Relationship)
- ❌ Similarity search (skipped)
- ❌ Context manager flow (skipped)

**Best for:** Development, CI/CD validation, storage system testing

##### **`--phase retrieval`**
**What it tests:**
- ✅ Vector Store similarity search
- ✅ Database metadata retrieval
- ✅ Knowledge Graph context enrichment
- ✅ Context Manager 4-step flow
- ✅ LLM context generation
- ✅ Retrieval quality assessment
- ❌ Document ingestion (assumes data exists)

**Best for:** Query performance testing, context quality validation

##### **`--phase full`** *(default)*
**What it tests:**
- ✅ Complete ingestion flow
- ✅ Complete retrieval flow
- ✅ End-to-end data consistency
- ✅ Cross-system integration

**Best for:** Release validation, comprehensive system testing

---

#### **`--targets`** | **Storage System Filtering**

**Purpose:** Filters which storage systems to test (comma-separated)

**Options:**
- `vector` - Vector Store (Vertex AI Vector Search)
- `database` - PostgreSQL Database  
- `knowledge_graph` - Neo4j Knowledge Graph
- *(no value)* - Test all available targets *(default)*

**Examples:**
```bash
# Test only Vector Store and Database
python tests/e2e/e2e_test.py --targets vector,database --scenario github

# Test only Knowledge Graph
python tests/e2e/e2e_test.py --targets knowledge_graph --scenario web

# Test only Vector Store
python tests/e2e/e2e_test.py --targets vector --scenario drive_file

# Test all storage systems (default)
python tests/e2e/e2e_test.py --scenario github
```

**Target Combinations:**
```bash
# Vector + Database (no knowledge graph)
python tests/e2e/e2e_test.py --targets vector,database

# Database + Knowledge Graph (no vector)  
python tests/e2e/e2e_test.py --targets database,knowledge_graph

# All three systems
python tests/e2e/e2e_test.py --targets vector,database,knowledge_graph
python tests/e2e/e2e_test.py  # equivalent (default)
```

**Note:** Target filtering requires custom fixture configuration and will filter results during execution rather than skipping tests entirely.

---

#### **`--verbose` / `-v`** | **Verbose Output**

**Purpose:** Enable detailed logging and output

**Examples:**
```bash
# Verbose output with detailed logs
python tests/e2e/e2e_test.py --verbose --scenario github
python tests/e2e/e2e_test.py -v --scenario github  # short form

# Normal output (default)
python tests/e2e/e2e_test.py --scenario github
```

**Verbose Output Includes:**
- Detailed test execution steps
- Component initialization logs
- Processing statistics and timings
- Entity extraction details
- Similarity scores and retrieval metrics
- Error context and debugging information

---

#### **`--quiet` / `-q`** | **Quiet Output**

**Purpose:** Suppress most output (warnings and errors only)

**Examples:**
```bash
# Minimal output for CI/CD
python tests/e2e/e2e_test.py --quiet --scenario all
python tests/e2e/e2e_test.py -q --scenario all  # short form

# Normal output (default)
python tests/e2e/e2e_test.py --scenario all
```

**Quiet Output Shows:**
- Test pass/fail status
- Critical errors and warnings
- Final test summary
- Performance metrics (minimal)

---

### Parameter Combinations & Use Cases

#### **Development Workflow**
```bash
# Quick ingestion validation during development
python tests/e2e/e2e_test.py --phase ingestion --scenario github --verbose

# Test specific storage system
python tests/e2e/e2e_test.py --targets vector --scenario web --verbose

# Fast iteration testing
python tests/e2e/e2e_test.py --phase ingestion --targets database --scenario drive_file
```

#### **CI/CD Pipeline**
```bash
# Fast validation for all scenarios
python tests/e2e/e2e_test.py --phase ingestion --scenario all --quiet

# Full validation before deployment
python tests/e2e/e2e_test.py --phase full --scenario all --quiet

# Storage-specific validation
python tests/e2e/e2e_test.py --targets vector,database --scenario all --quiet
```

#### **Performance Testing**
```bash
# Retrieval performance validation
python tests/e2e/e2e_test.py --phase retrieval --scenario all --verbose

# Vector search performance
python tests/e2e/e2e_test.py --targets vector --scenario github,web --verbose

# Knowledge graph performance
python tests/e2e/e2e_test.py --targets knowledge_graph --scenario all --verbose
```

#### **Debugging & Troubleshooting**
```bash
# Detailed debugging output
python tests/e2e/e2e_test.py --scenario github --verbose

# Test specific failure scenario
python tests/e2e/e2e_test.py --phase ingestion --scenario drive --verbose

# Isolate storage system issues
python tests/e2e/e2e_test.py --targets database --scenario web --verbose
```

### Phase-Scenario Compatibility

| Scenario | Ingestion | Retrieval | Full | Notes |
|----------|-----------|-----------|------|-------|
| `github` | ✅ | ✅ | ✅ | Full pipeline support |
| `drive` | ✅ | ❌* | ✅ | *Ingestion-only by design |
| `drive_file` | ✅ | ✅ | ✅ | Full pipeline support |
| `web` | ✅ | ✅ | ✅ | Full pipeline support |
| `all` | ✅ | ✅** | ✅ | **Skips retrieval for drive folder |

### Output Examples

#### **Normal Output**
```
🧪 Team Assistant E2E Test Suite
==================================================
📋 Scenario: github
🎯 Phase: full
🎪 Targets: all available
📢 Verbosity: normal

🚀 Starting pipeline execution with mode: full
📊 Processing 1 data source(s)...
✅ Pipeline execution completed in 45.2s
```

#### **Verbose Output**
```
🧪 Team Assistant E2E Test Suite
==================================================
📋 Scenario: github  
🎯 Phase: ingestion
📝 Description: Document fetching, processing, and storage validation
🎪 Targets: vector,database
📢 Verbosity: verbose

🔧 Running pytest with args: tests/e2e/test_e2e_data_pipeline.py::TestE2EDataPipeline::test_ingestion_only -vv -k [github]

2024-01-15 10:30:15 - test_e2e_data_pipeline - INFO - ✓ Document processing validation passed: 1 docs → 3 chunks
2024-01-15 10:30:18 - test_e2e_data_pipeline - INFO - ✓ Database storage successful: 3/3 chunks
2024-01-15 10:30:22 - test_e2e_data_pipeline - INFO - ✓ Vector store storage successful: 3/3 embeddings
```

#### **Quiet Output**
```
🧪 Team Assistant E2E Test Suite
==================================================
📋 Scenario: all
🎯 Phase: full
🎪 Targets: all available
📢 Verbosity: quiet

✅ E2E tests completed successfully!
```

This parameter reference provides complete control over E2E test execution, enabling efficient development workflows, targeted debugging, and comprehensive validation strategies. 