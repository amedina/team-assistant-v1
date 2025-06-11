# E2E Test Framework - Complete Command Reference

This document provides a comprehensive list of all available test configurations for the Team Assistant E2E Test Framework, organized from **most specific to most general**.

## 🎯 Available CLI Arguments

### Core Arguments:
- `--scenario`: `github`, `drive`, `drive_file`, `web`
- `--targets`: `vector`, `database`, `knowledge_graph` (comma-separated)
- `--components`: `models`, `processors`, `connectors`, `text_processing`, `retrieval`, `storage` (comma-separated)
- `--phase`: `ingestion`, `retrieval`, `full`

### Execution Control:
- `--verbose`: Detailed output
- `--quiet`: Minimal output  
- `--fail-fast`: Stop on first failure
- `--strict-validation`: Enable all validation checks

---

## 📋 Complete Test Command Configurations

### 🔬 Individual Test Methods (Most Specific)

#### Component Tests
```bash
# Model tests
python -m pytest test_components.py::TestModels::test_model_serialization -v

# Text Processor tests
python -m pytest test_components.py::TestTextProcessor::test_text_chunking -v
python -m pytest test_components.py::TestTextProcessor::test_entity_extraction -v

# Connector tests
python -m pytest test_components.py::TestConnectors::test_github_connector_initialization -v
python -m pytest test_components.py::TestConnectors::test_drive_connector_initialization -v
python -m pytest test_components.py::TestConnectors::test_web_connector_initialization -v
python -m pytest test_components.py::TestConnectors::test_connector_document_fetching -v

# Component Integration tests
python -m pytest test_components.py::TestComponentIntegration::test_processor_connector_integration -v
python -m pytest test_components.py::TestComponentIntegration::test_model_data_flow -v
```

#### Storage Tests
```bash
# Vector Store tests
python -m pytest test_storage.py::TestVectorStore::test_vector_store_initialization -v
python -m pytest test_storage.py::TestVectorStore::test_vector_operations -v

# Database tests
python -m pytest test_storage.py::TestDatabase::test_database_initialization -v
python -m pytest test_storage.py::TestDatabase::test_database_operations -v

# Knowledge Graph tests
python -m pytest test_storage.py::TestKnowledgeGraph::test_knowledge_graph_initialization -v
python -m pytest test_storage.py::TestKnowledgeGraph::test_knowledge_graph_operations -v

# Storage Integration tests
python -m pytest test_storage.py::TestStorageIntegration::test_multi_storage_operations -v
python -m pytest test_storage.py::TestStorageIntegration::test_storage_health_checks -v

# Storage Performance tests
python -m pytest test_storage.py::TestStoragePerformance::test_batch_operations -v
```

#### Integration Tests
```bash
# Pipeline Integration tests
python -m pytest test_integration.py::TestPipelineIntegration::test_end_to_end_pipeline -v
python -m pytest test_integration.py::TestPipelineIntegration::test_pipeline_error_handling -v

# Context Manager Integration tests
python -m pytest test_integration.py::TestContextManagerIntegration::test_context_retrieval_pipeline -v

# System Integration tests
python -m pytest test_integration.py::TestSystemIntegration::test_system_health_monitoring -v
python -m pytest test_integration.py::TestSystemIntegration::test_concurrent_operations -v

# Data Consistency tests
python -m pytest test_integration.py::TestDataConsistency::test_data_flow_consistency -v

# Performance Integration tests
python -m pytest test_integration.py::TestPerformanceIntegration::test_pipeline_performance -v
```

### 🧪 Test Class Level

#### Component Test Classes
```bash
python -m pytest test_components.py::TestModels -v
python -m pytest test_components.py::TestTextProcessor -v
python -m pytest test_components.py::TestConnectors -v
python -m pytest test_components.py::TestComponentIntegration -v
```

#### Storage Test Classes
```bash
python -m pytest test_storage.py::TestVectorStore -v
python -m pytest test_storage.py::TestDatabase -v
python -m pytest test_storage.py::TestKnowledgeGraph -v
python -m pytest test_storage.py::TestStorageIntegration -v
python -m pytest test_storage.py::TestStoragePerformance -v
```

#### Integration Test Classes
```bash
python -m pytest test_integration.py::TestPipelineIntegration -v
python -m pytest test_integration.py::TestContextManagerIntegration -v
python -m pytest test_integration.py::TestSystemIntegration -v
python -m pytest test_integration.py::TestDataConsistency -v
python -m pytest test_integration.py::TestPerformanceIntegration -v
```

### 📂 Component-Specific Tests

#### Individual Components
```bash
python test_runner.py --components models --verbose
python test_runner.py --components processors --verbose
python test_runner.py --components connectors --verbose
python test_runner.py --components text_processing --verbose
python test_runner.py --components retrieval --verbose
python test_runner.py --components storage --verbose
```

#### Component Combinations
```bash
python test_runner.py --components models,processors --verbose
python test_runner.py --components connectors,text_processing --verbose
python test_runner.py --components storage,retrieval --verbose
python test_runner.py --components models,processors,connectors --verbose
python test_runner.py --components text_processing,storage,retrieval --verbose
```

### 🗄️ Storage Target-Specific Tests

#### Individual Storage Targets
```bash
python test_runner.py --targets vector --verbose
python test_runner.py --targets database --verbose
python test_runner.py --targets knowledge_graph --verbose
```

#### Storage Target Combinations
```bash
python test_runner.py --targets vector,database --verbose
python test_runner.py --targets database,knowledge_graph --verbose
python test_runner.py --targets vector,knowledge_graph --verbose
python test_runner.py --targets vector,database,knowledge_graph --verbose
```

### 🎬 Scenario-Specific Tests

#### Individual Scenarios
```bash
python test_runner.py --scenario github --verbose
python test_runner.py --scenario drive --verbose
python test_runner.py --scenario drive_file --verbose
python test_runner.py --scenario web --verbose
```

#### Scenarios with Specific Targets
```bash
python test_runner.py --scenario github --targets vector --verbose
python test_runner.py --scenario drive --targets database --verbose
python test_runner.py --scenario drive_file --targets knowledge_graph --verbose
python test_runner.py --scenario web --targets vector,database --verbose
```

#### Scenarios with Specific Components
```bash
python test_runner.py --scenario github --components processors,storage --verbose
python test_runner.py --scenario drive --components models,connectors --verbose
python test_runner.py --scenario drive_file --components text_processing,retrieval --verbose
python test_runner.py --scenario web --components connectors,processors,storage --verbose
```

### ⚙️ Phase-Specific Tests

#### Individual Phases
```bash
python test_runner.py --phase ingestion --verbose
python test_runner.py --phase retrieval --verbose
python test_runner.py --phase full --verbose
```

#### Phases with Scenarios
```bash
python test_runner.py --phase ingestion --scenario github --verbose
python test_runner.py --phase retrieval --scenario drive_file --verbose
python test_runner.py --phase full --scenario web --verbose
```

#### Phases with Components
```bash
python test_runner.py --phase ingestion --components models,processors --verbose
python test_runner.py --phase retrieval --components storage,retrieval --verbose
python test_runner.py --phase full --components models,processors,storage --verbose
```

#### Phases with Targets
```bash
python test_runner.py --phase ingestion --targets vector,database --verbose
python test_runner.py --phase retrieval --targets vector --verbose
python test_runner.py --phase full --targets vector,database,knowledge_graph --verbose
```

### 📁 Module-Level Tests

#### Individual Test Modules
```bash
python -m pytest test_components.py -v
python -m pytest test_storage.py -v
python -m pytest test_integration.py -v
```

#### Module Combinations
```bash
python -m pytest test_components.py test_storage.py -v
python -m pytest test_storage.py test_integration.py -v
python -m pytest test_components.py test_integration.py -v
```

### 🎯 Execution Control Combinations

#### With Strict Validation
```bash
python test_runner.py --scenario github --strict-validation --verbose
python test_runner.py --components models --strict-validation --fail-fast
python test_runner.py --targets vector,database --strict-validation --verbose
python test_runner.py --phase ingestion --strict-validation --verbose
```

#### With Fail-Fast
```bash
python test_runner.py --scenario drive --fail-fast --verbose
python test_runner.py --phase ingestion --fail-fast
python test_runner.py --components storage --fail-fast --strict-validation
python test_runner.py --targets vector --fail-fast --verbose
```

#### Quiet Mode (for CI/automation)
```bash
python test_runner.py --scenario web --quiet
python test_runner.py --targets vector --quiet --fail-fast
python test_runner.py --components models --quiet
python test_runner.py --phase full --quiet --strict-validation
```

### 🌐 Comprehensive Tests (Most General)

#### Full Test Suite via Test Runner
```bash
python test_runner.py --verbose
python test_runner.py --strict-validation --verbose
python test_runner.py --fail-fast --verbose
python test_runner.py --phase full --strict-validation --verbose
python test_runner.py --quiet --fail-fast
```

#### Full Test Suite via Pytest
```bash
python -m pytest tests/e2e/ -v
python -m pytest tests/e2e/ --tb=long -v
python -m pytest tests/e2e/ -v --maxfail=5
python -m pytest tests/e2e/ -v -x  # fail fast
```

## 🚀 Recommended Execution Strategy

### Sequential Testing (Start → Finish)
1. **Foundation Tests**: Models → Text Processing → Storage initialization
2. **Component Tests**: Individual component functionality  
3. **Storage Tests**: Individual storage layer validation
4. **Integration Tests**: Cross-component and full pipeline validation
5. **Scenario Tests**: End-to-end scenario validation

### Development Workflow
```bash
# Quick component validation
python test_runner.py --components models,processors --verbose

# Storage layer validation  
python test_runner.py --targets vector,database --verbose

# Full integration testing
python test_runner.py --phase full --strict-validation --verbose
```

### CI/Production Workflow
```bash
# Fast failure detection
python test_runner.py --fail-fast --strict-validation --quiet

# Complete validation
python test_runner.py --strict-validation --verbose
```

## 📝 Notes

- All commands should be run from the `tests/e2e/` directory
- Use `--verbose` for detailed output during development
- Use `--quiet` for automated/CI environments
- Use `--fail-fast` to stop on first failure for faster feedback
- Use `--strict-validation` for comprehensive validation in production
- Individual test methods provide the most granular control
- Test runner commands provide higher-level orchestration and reporting 