# Team Assistant E2E Test Suite

Comprehensive End-to-End testing framework for the Team Assistant data ingestion and retrieval system. This test suite validates the complete pipeline flow across all three storage layers: Vertex AI Vector Search, PostgreSQL Database, and Neo4j Knowledge Graph.

## Architecture Overview

The E2E test suite implements a **Modular Test Suite Architecture** with the following components:

### Core Modules

- **`test_scenarios.py`** - Test scenario configurations and validation rules
- **`fixtures.py`** - Shared test fixtures, utilities, and validation functions
- **`test_components.py`** - Component-level tests (models, processors, connectors)
- **`test_storage.py`** - Storage layer tests (vector store, database, knowledge graph)
- **`test_integration.py`** - Full pipeline integration and context manager tests
- **`test_runner.py`** - Main orchestration and command-line interface

### Test Scenarios

Four predefined test scenarios with enhanced validation:

1. **GitHub Repository** (`github`) - Enhanced GitHub repository file ingestion and retrieval
2. **Google Drive Folder** (`drive`) - Google Drive folder ingestion validation (ingestion-only)
3. **Google Drive File** (`drive_file`) - Individual Google Drive file processing
4. **Web Source** (`web`) - Enhanced web page ingestion and retrieval

## Usage

### Quick Start

```bash
# Run all tests
python tests/e2e/e2e_test.py

# Run specific scenario
python tests/e2e/e2e_test.py --scenario github

# Run with verbose output
python tests/e2e/e2e_test.py --verbose --strict-validation
```

### Command Line Options

#### Scenario Selection
```bash
# Test specific scenario
python tests/e2e/e2e_test.py --scenario github
python tests/e2e/e2e_test.py --scenario drive
python tests/e2e/e2e_test.py --scenario drive_file
python tests/e2e/e2e_test.py --scenario web
```

#### Storage Target Testing
```bash
# Test specific storage systems
python tests/e2e/e2e_test.py --scenario github --targets vector,database
python tests/e2e/e2e_test.py --scenario drive --targets knowledge_graph
python tests/e2e/e2e_test.py --targets vector  # All scenarios, vector store only
```

#### Component Testing
```bash
# Test specific components
python tests/e2e/e2e_test.py --components models,processors
python tests/e2e/e2e_test.py --components connectors,text_processing
python tests/e2e/e2e_test.py --components storage,retrieval
```

#### Test Phase Control
```bash
# Test specific phases
python tests/e2e/e2e_test.py --phase ingestion     # Components + Storage ingestion
python tests/e2e/e2e_test.py --phase retrieval     # Storage retrieval + Integration
python tests/e2e/e2e_test.py --phase full          # Complete pipeline (default)
```

#### Execution Control
```bash
# Verbosity control
python tests/e2e/e2e_test.py --verbose            # Detailed output
python tests/e2e/e2e_test.py --quiet              # Minimal output

# Failure handling
python tests/e2e/e2e_test.py --fail-fast          # Stop on first failure
python tests/e2e/e2e_test.py --strict-validation  # Enable all validation checks
```

### Advanced Usage Examples

```bash
# Debug specific component issues
python tests/e2e/e2e_test.py --components models --verbose --fail-fast

# Test vector store performance
python tests/e2e/e2e_test.py --targets vector --scenario web --strict-validation

# Validate ingestion pipeline only
python tests/e2e/e2e_test.py --phase ingestion --verbose

# Quick health check
python tests/e2e/e2e_test.py --components storage --quiet

# Full validation with strict checks
python tests/e2e/e2e_test.py --strict-validation --verbose --fail-fast
```

## Test Architecture

### Component Tests (`test_components.py`)

- **Model Validation** - Type safety, serialization, data integrity
- **Text Processing** - Chunking, entity extraction, metadata enrichment
- **Connector Tests** - GitHub, Drive, Web connector functionality
- **Integration Tests** - Component interaction validation

### Storage Tests (`test_storage.py`)

- **Vector Store Tests** - Embedding generation, similarity search, batch operations
- **Database Tests** - Chunk storage, metadata queries, source statistics
- **Knowledge Graph Tests** - Entity/relationship storage, graph traversal
- **Cross-Storage Integration** - Data consistency across all systems

### Integration Tests (`test_integration.py`)

- **Full Pipeline Tests** - End-to-end document processing and storage
- **Context Manager Tests** - 4-step validation process:
  1. Vector similarity search
  2. Database metadata retrieval
  3. Knowledge graph entity/relationship lookup
  4. Structured context output generation
- **Scenario Validation** - Predefined scenario testing with enhanced validation

### Test Fixtures (`fixtures.py`)

- **Manager Fixtures** - Vector store, database, knowledge graph managers
- **Processor Fixtures** - Text processor with entity extraction
- **Connector Fixtures** - GitHub, Drive, Web connectors
- **Validation Functions** - Text processing, retrieval results, model types
- **Utility Functions** - Test data generation, execution timing, health checks

## Validation Framework

### Text Processing Validation

- Minimum extracted text length
- Required chunk overlap processing
- Entity extraction thresholds
- Required metadata fields

### Model Type Validation

- Type safety enforcement
- Data model compliance
- Serialization/deserialization integrity
- Schema validation

### Retrieval Validation

- Result count thresholds
- Similarity score validation
- Keyword presence verification
- Response time constraints

### Storage Validation

- Cross-system data consistency
- Batch operation success rates
- Health check validation
- Performance benchmarks

## Strict Failure Reporting

The test suite implements **zero tolerance for broken functionality**:

- **Mandatory Assertions** - All functionality must work completely
- **No Graceful Degradation** - Partial failures cause complete test failure
- **Comprehensive Error Reporting** - Detailed failure diagnostics
- **Immediate Failure Halt** - Tests stop on first critical failure (with `--fail-fast`)

## Configuration Integration

The test suite integrates with the existing project configuration system:

- **Storage Configurations** - Loaded from `config/data_sources_config.yaml`
- **Pipeline Settings** - Uses existing pipeline configuration patterns
- **Service Integration** - Real instances of Vertex AI, PostgreSQL, Neo4j

## Performance Monitoring

- **Execution Timing** - Per-test and overall execution metrics
- **Memory Usage** - Component memory consumption tracking
- **Response Times** - Validation against scenario-defined thresholds
- **Throughput Metrics** - Batch operation performance measurement

## Error Handling and Diagnostics

### Error Categories

1. **Configuration Errors** - Service connection or configuration issues
2. **Component Failures** - Individual component functionality failures
3. **Integration Failures** - Cross-component communication issues
4. **Performance Failures** - Response time or throughput threshold violations
5. **Validation Failures** - Data integrity or type safety violations

### Diagnostic Information

- **Exact Failure Points** - Precise location and context of failures
- **Component State** - Health status of all system components
- **Data Flow Traces** - Pipeline processing step validation
- **Performance Metrics** - Timing and resource usage information

## Development and Debugging

### Running Individual Test Modules

```bash
# Component tests only
pytest tests/e2e/test_components.py -v

# Storage tests only  
pytest tests/e2e/test_storage.py -v

# Integration tests only
pytest tests/e2e/test_integration.py -v

# Specific test class
pytest tests/e2e/test_components.py::TestModels -v
```

### Debugging Failed Tests

```bash
# Maximum verbosity with immediate failure
python tests/e2e/e2e_test.py --verbose --fail-fast --strict-validation

# Component-specific debugging
python tests/e2e/e2e_test.py --components models --verbose

# Storage-specific debugging
python tests/e2e/e2e_test.py --targets vector --verbose --fail-fast
```

### Test Data and Cleanup

- **Test Data Generation** - Automated test document creation
- **UUID Generation** - Unique identifiers for test isolation
- **Resource Cleanup** - Automatic cleanup of test resources
- **Session Management** - Proper initialization and teardown

## Success Criteria

- **Zero Failed Tests** - All tests must pass completely
- **System Health** - All storage systems must be healthy
- **Performance Compliance** - All response times within defined thresholds
- **Data Integrity** - Complete consistency across all storage layers
- **Type Safety** - Full model validation throughout pipeline

## Continuous Integration

The test suite is designed for CI/CD integration:

- **Exit Codes** - Proper exit code reporting (0 = success, 1 = failure)
- **Machine-Readable Output** - Structured test result reporting
- **Parallel Execution** - Safe concurrent test execution
- **Resource Management** - Proper cleanup for CI environments

## Troubleshooting

### Common Issues

1. **Service Connection Failures** - Check configuration and credentials
2. **Timeout Errors** - Increase timeout thresholds or check system performance
3. **Memory Issues** - Monitor memory usage during large batch operations
4. **Concurrent Access** - Ensure proper resource locking in multi-test scenarios

### Getting Help

1. **Verbose Output** - Always start debugging with `--verbose`
2. **Component Isolation** - Test individual components to isolate issues
3. **Health Checks** - Verify system health before running tests
4. **Configuration Validation** - Ensure all services are properly configured

---

This E2E test suite provides comprehensive validation of the Team Assistant's data ingestion and retrieval capabilities with strict adherence to existing codebase patterns and zero tolerance for broken functionality. 