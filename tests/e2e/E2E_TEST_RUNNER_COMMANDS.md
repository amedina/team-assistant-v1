# E2E Test Runner Commands Reference

This document provides a comprehensive guide to all available test commands using the Team Assistant E2E Test Runner (`tests/e2e/test_runner.py`).

## Table of Contents

- [Quick Start](#quick-start)
- [Command Structure](#command-structure)
- [Complete Test Suite](#complete-test-suite)
- [Scenario-Based Testing](#scenario-based-testing)
- [Component-Based Testing](#component-based-testing)
- [Storage Target Testing](#storage-target-testing)
- [Phase-Based Testing](#phase-based-testing)
- [Combined Testing Options](#combined-testing-options)
- [Execution Control Options](#execution-control-options)
- [Test Categories Reference](#test-categories-reference)
- [Recommended Test Sequences](#recommended-test-sequences)
- [Troubleshooting](#troubleshooting)

## Quick Start

```bash
# Run all tests with verbose output
python tests/e2e/test_runner.py --verbose

# Test a specific scenario
python tests/e2e/test_runner.py --scenario github --verbose

# Test specific components
python tests/e2e/test_runner.py --components models --verbose
```

## Command Structure

```bash
python tests/e2e/test_runner.py [OPTIONS]
```

### Available Options

| Option | Description | Values |
|--------|-------------|---------|
| `--scenario` | Test specific data source scenario | `github`, `drive`, `drive_file`, `web` |
| `--components` | Test specific system components | `models`, `processors`, `connectors`, `text_processing`, `retrieval`, `storage` |
| `--targets` | Test specific storage targets | `vector`, `database`, `knowledge_graph` |
| `--phase` | Test specific pipeline phase | `ingestion`, `retrieval`, `full` |
| `--verbose` | Enable verbose output | N/A |
| `--quiet` | Suppress detailed output | N/A |
| `--fail-fast` | Stop on first failure | N/A |
| `--strict-validation` | Enable all validation checks | N/A |

## Complete Test Suite

### Run All Tests

```bash
# Default - run all tests
python tests/e2e/test_runner.py

# With verbose output
python tests/e2e/test_runner.py --verbose

# With strict validation
python tests/e2e/test_runner.py --strict-validation --verbose

# With fail-fast mode
python tests/e2e/test_runner.py --fail-fast --verbose

# Quiet mode (minimal output)
python tests/e2e/test_runner.py --quiet
```

## Scenario-Based Testing

Test specific data source types and their ingestion/retrieval workflows.

### Individual Scenarios

```bash
# GitHub Repository Testing
python tests/e2e/test_runner.py --scenario github --verbose

# Google Drive Folder Testing (ingestion-only)
python tests/e2e/test_runner.py --scenario drive --verbose

# Individual Google Drive File Testing
python tests/e2e/test_runner.py --scenario drive_file --verbose

# Web Page Scraping Testing
python tests/e2e/test_runner.py --scenario web --verbose
```

### Scenario Details

| Scenario | Source Type | Operations | Description |
|----------|-------------|------------|-------------|
| `github` | GitHub Repository | Ingestion + Retrieval | Tests GitHub connector, file processing, and search |
| `drive` | Google Drive Folder | Ingestion Only | Tests bulk Drive folder processing |
| `drive_file` | Individual Drive File | Ingestion + Retrieval | Tests single Drive file processing |
| `web` | Web Page | Ingestion + Retrieval | Tests web scraping and content processing |

## Component-Based Testing

Test specific system components in isolation.

### Individual Components

```bash
# Data Models Testing
python tests/e2e/test_runner.py --components models --verbose

# Text Processors Testing
python tests/e2e/test_runner.py --components processors --verbose

# Data Connectors Testing
python tests/e2e/test_runner.py --components connectors --verbose

# Text Processing Pipeline Testing
python tests/e2e/test_runner.py --components text_processing --verbose

# Retrieval System Testing
python tests/e2e/test_runner.py --components retrieval --verbose

# Storage Operations Testing
python tests/e2e/test_runner.py --components storage --verbose
```

### Multiple Components

```bash
# Test models and processors together
python tests/e2e/test_runner.py --components models,processors --verbose

# Test storage and retrieval systems
python tests/e2e/test_runner.py --components storage,retrieval --verbose

# Test all core components
python tests/e2e/test_runner.py --components models,processors,connectors --verbose
```

### Component Details

| Component | What It Tests | Test Modules |
|-----------|---------------|--------------|
| `models` | Pydantic data models, type safety, validation | `test_components.py::TestModels` |
| `processors` | Text processing, chunking, entity extraction | `test_components.py::TestTextProcessor` |
| `connectors` | GitHub, Drive, Web data connectors | `test_components.py::TestConnectors` |
| `text_processing` | Complete text processing pipeline | `test_components.py::TestTextProcessor` |
| `retrieval` | Search and query functionality | `test_integration.py::TestContextManager` |
| `storage` | All storage system operations | `test_storage.py` |

## Storage Target Testing

Test specific storage systems independently.

### Individual Storage Targets

```bash
# Vector Store Testing (Vertex AI)
python tests/e2e/test_runner.py --targets vector --verbose

# Database Testing (PostgreSQL)
python tests/e2e/test_runner.py --targets database --verbose

# Knowledge Graph Testing (Neo4j)
python tests/e2e/test_runner.py --targets knowledge_graph --verbose
```

### Multiple Storage Targets

```bash
# Test vector store and database
python tests/e2e/test_runner.py --targets vector,database --verbose

# Test vector store and knowledge graph
python tests/e2e/test_runner.py --targets vector,knowledge_graph --verbose

# Test database and knowledge graph
python tests/e2e/test_runner.py --targets database,knowledge_graph --verbose

# Test all storage targets
python tests/e2e/test_runner.py --targets vector,database,knowledge_graph --verbose
```

### Storage Target Details

| Target | Technology | What It Tests | Test Modules |
|--------|------------|---------------|--------------|
| `vector` | Vertex AI Vector Search | Embedding generation, similarity search | `test_storage.py::TestVectorStore` |
| `database` | PostgreSQL | Metadata storage, chunk management | `test_storage.py::TestDatabase` |
| `knowledge_graph` | Neo4j | Entity/relationship storage, graph queries | `test_storage.py::TestKnowledgeGraph` |

## Phase-Based Testing

Test specific phases of the data processing pipeline.

```bash
# Ingestion Phase Testing
python tests/e2e/test_runner.py --phase ingestion --verbose

# Retrieval Phase Testing
python tests/e2e/test_runner.py --phase retrieval --verbose

# Full Pipeline Testing (default)
python tests/e2e/test_runner.py --phase full --verbose
```

### Phase Details

| Phase | What It Tests | Included Modules |
|-------|---------------|------------------|
| `ingestion` | Document processing and storage | `test_components.py`, `test_storage.py` |
| `retrieval` | Search and query operations | `test_storage.py`, `test_integration.py` |
| `full` | Complete end-to-end pipeline | All test modules |

## Combined Testing Options

Combine multiple filters for targeted testing.

### Scenario + Storage Combinations

```bash
# Test GitHub scenario with specific storage targets
python tests/e2e/test_runner.py --scenario github --targets vector,database --verbose

# Test Drive file with vector storage only
python tests/e2e/test_runner.py --scenario drive_file --targets vector --verbose

# Test web scenario with knowledge graph
python tests/e2e/test_runner.py --scenario web --targets knowledge_graph --verbose
```

### Scenario + Component Combinations

```bash
# Test GitHub scenario with specific components
python tests/e2e/test_runner.py --scenario github --components models,processors --verbose

# Test Drive file with text processing
python tests/e2e/test_runner.py --scenario drive_file --components text_processing --verbose
```

### Phase + Target Combinations

```bash
# Test ingestion phase with vector storage
python tests/e2e/test_runner.py --phase ingestion --targets vector --verbose

# Test retrieval phase with all storage targets
python tests/e2e/test_runner.py --phase retrieval --targets vector,database,knowledge_graph --verbose
```

### Complex Combinations

```bash
# Comprehensive targeted testing
python tests/e2e/test_runner.py --scenario github --components storage,retrieval --targets vector --phase full --verbose

# Development workflow testing
python tests/e2e/test_runner.py --components models,processors --phase ingestion --fail-fast --verbose
```

## Execution Control Options

Control how tests are executed and reported.

### Verbosity Control

```bash
# Verbose output (detailed logging)
python tests/e2e/test_runner.py --verbose

# Quiet output (minimal logging)
python tests/e2e/test_runner.py --quiet

# Default output (standard logging)
python tests/e2e/test_runner.py
```

### Failure Handling

```bash
# Stop on first failure
python tests/e2e/test_runner.py --fail-fast --verbose

# Continue through all failures (default)
python tests/e2e/test_runner.py --verbose
```

### Validation Strictness

```bash
# Strict validation (all checks must pass)
python tests/e2e/test_runner.py --strict-validation --verbose

# Standard validation (default)
python tests/e2e/test_runner.py --verbose
```

### Combined Execution Controls

```bash
# Maximum strictness and verbosity
python tests/e2e/test_runner.py --strict-validation --fail-fast --verbose

# Development mode (quick feedback)
python tests/e2e/test_runner.py --fail-fast --quiet

# Production validation mode
python tests/e2e/test_runner.py --strict-validation --verbose
```

## Test Categories Reference

### By Test Purpose

| Purpose | Command | Use Case |
|---------|---------|----------|
| **Development** | `--components models --verbose` | Validate data model changes |
| **Integration** | `--phase full --verbose` | Test complete system integration |
| **Performance** | `--targets vector --strict-validation` | Validate search performance |
| **Reliability** | `--fail-fast --strict-validation` | Quick system health check |
| **Deployment** | `--strict-validation --verbose` | Pre-deployment validation |

### By Time Investment

| Duration | Command | What It Tests |
|----------|---------|---------------|
| **Quick (< 2 min)** | `--components models` | Data model validation |
| **Medium (2-5 min)** | `--targets vector` | Single storage system |
| **Long (5-10 min)** | `--scenario github` | Complete scenario workflow |
| **Full (10+ min)** | `--strict-validation --verbose` | Comprehensive system validation |

## Recommended Test Sequences

### For Daily Development

```bash
# 1. Quick model validation
python tests/e2e/test_runner.py --components models --verbose

# 2. Component integration check
python tests/e2e/test_runner.py --components storage --fail-fast --verbose

# 3. Single scenario validation
python tests/e2e/test_runner.py --scenario github --verbose
```

### For Feature Development

```bash
# 1. Component-specific testing
python tests/e2e/test_runner.py --components processors,connectors --verbose

# 2. Storage integration testing
python tests/e2e/test_runner.py --targets vector,database --verbose

# 3. End-to-end scenario testing
python tests/e2e/test_runner.py --scenario drive_file --verbose
```

### For Release Validation

```bash
# 1. Full system health check
python tests/e2e/test_runner.py --strict-validation --fail-fast --verbose

# 2. All scenarios validation
python tests/e2e/test_runner.py --scenario github --strict-validation --verbose
python tests/e2e/test_runner.py --scenario drive_file --strict-validation --verbose
python tests/e2e/test_runner.py --scenario web --strict-validation --verbose

# 3. Complete system validation
python tests/e2e/test_runner.py --strict-validation --verbose
```

### For Debugging Issues

```bash
# 1. Isolate component
python tests/e2e/test_runner.py --components [failing_component] --verbose

# 2. Test specific storage
python tests/e2e/test_runner.py --targets [failing_target] --verbose

# 3. Minimal scenario test
python tests/e2e/test_runner.py --scenario [failing_scenario] --fail-fast --verbose
```

## Troubleshooting

### Common Issues and Solutions

| Issue | Command to Diagnose | Solution |
|-------|-------------------|----------|
| **Models failing** | `--components models --verbose` | Check Pydantic model definitions |
| **Storage connection** | `--targets vector --verbose` | Verify service configurations |
| **Text processing** | `--components processors --verbose` | Check spaCy/NLTK dependencies |
| **Connector issues** | `--components connectors --verbose` | Verify API credentials |
| **Performance issues** | `--strict-validation --verbose` | Check response time thresholds |

### Diagnostic Commands

```bash
# System health check
python tests/e2e/test_runner.py --strict-validation --fail-fast --verbose

# Component isolation
python tests/e2e/test_runner.py --components models,processors,connectors --verbose

# Storage system check
python tests/e2e/test_runner.py --targets vector,database,knowledge_graph --verbose

# Minimal test run
python tests/e2e/test_runner.py --scenario github --fail-fast --quiet
```

### Performance Optimization

```bash
# Fast feedback loop
python tests/e2e/test_runner.py --components models --fail-fast --quiet

# Parallel component testing
python tests/e2e/test_runner.py --components storage,retrieval --verbose

# Focused scenario testing
python tests/e2e/test_runner.py --scenario drive_file --targets vector --verbose
```

---

**Note**: All commands should be run from the project root directory. Ensure your environment is properly configured with all required dependencies and credentials before running tests. 