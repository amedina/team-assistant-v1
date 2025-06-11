## 🎯 **AVAILABLE CLI ARGUMENTS**

### **Core Arguments:**

- `--scenario`: `github`, `drive`, `drive_file`, `web`
- `--targets`: `vector`, `database`, `knowledge_graph` (comma-separated)
- `--components`: `models`, `processors`, `connectors`, `text_processing`, `retrieval`, `storage` (comma-separated)
- `--phase`: `ingestion`, `retrieval`, `full`

### **Execution Control:**

- `--verbose`: Detailed output
- `--quiet`: Minimal output
- `--fail-fast`: Stop on first failure
- `--strict-validation`: Enable all validation checks

---

## 📋 **COMPLETE TEST COMMAND CONFIGURATIONS**

### (Most Specific → Most General)

### **🔬 INDIVIDUAL TEST METHODS (Most Specific)**

```bash
# Single specific test methods
python -m pytest test_components.py::TestModels::test_model_serialization -v ✅

python -m pytest test_components.py::TestTextProcessor::test_text_chunking -v ✅
python -m pytest test_components.py::TestTextProcessor::test_entity_extraction -v ✅

python -m pytest test_components.py::TestConnectors::test_github_connector_initialization -v ✅
python -m pytest test_components.py::TestConnectors::test_drive_connector_initialization -v ✅
python -m pytest test_components.py::TestConnectors::test_web_connector_initialization -v ✅
python -m pytest test_components.py::TestConnectors::test_connector_document_fetching -v ✅

python -m pytest test_components.py::TestComponentIntegration::test_processor_connector_integration -v ✅
python -m pytest test_components.py::TestComponentIntegration::test_model_data_flow -v ✅

python -m pytest test_storage.py::TestVectorStore::test_vector_store_initialization -v ✅
python -m pytest test_storage.py::TestVectorStore::test_vector_operations -v ✅

python -m pytest test_storage.py::TestDatabase::test_database_initialization -v ✅
python -m pytest test_storage.py::TestDatabase::test_database_operations -v ✅

python -m pytest test_storage.py::TestKnowledgeGraph::test_knowledge_graph_initialization -v ✅
python -m pytest test_storage.py::TestKnowledgeGraph::test_knowledge_graph_operations -v ✅

python -m pytest test_storage.py::TestStorageIntegration::test_multi_storage_operations -v ✅
python -m pytest test_storage.py::TestStorageIntegration::test_storage_health_checks -v ✅
python -m pytest test_storage.py::TestStoragePerformance::test_batch_operations -v ✅

python -m pytest tests/e2e/test_integration.py::TestFullPipeline::test_end_to_end_document_flow -v ✅

python -m pytest tests/e2e/test_integration.py::TestContextManager::test_context_manager_four_step_flow -v ✅

python -m pytest tests/e2e/test_integration.py::TestScenarioValidation::test_scenario_retrieval_validation -v ✅

python -m pytest tests/e2e/test_integration.py::TestSystemHealth::test_comprehensive_system_health -v

```

### **🧪 TEST CLASS LEVEL**

```bash
# Individual test classes
python -m pytest test_components.py::TestModels -v ✅
python -m pytest test_components.py::TestTextProcessor -v
python -m pytest test_components.py::TestConnectors -v
python -m pytest test_components.py::TestComponentIntegration -v

python -m pytest test_storage.py::TestVectorStore -v
python -m pytest test_storage.py::TestDatabase -v
python -m pytest test_storage.py::TestKnowledgeGraph -v
python -m pytest test_storage.py::TestStorageIntegration -v
python -m pytest test_storage.py::TestStoragePerformance -v

python -m pytest test_integration.py::TestPipelineIntegration -v
python -m pytest test_integration.py::TestContextManagerIntegration -v
python -m pytest test_integration.py::TestSystemIntegration -v
python -m pytest test_integration.py::TestDataConsistency -v
python -m pytest test_integration.py::TestPerformanceIntegration -v
```

### **📂 COMPONENT-SPECIFIC TESTS**

```bash
# Individual components via test runner
python test_runner.py --components models --verbose
python test_runner.py --components processors --verbose
python test_runner.py --components connectors --verbose
python test_runner.py --components text_processing --verbose
python test_runner.py --components retrieval --verbose
python test_runner.py --components storage --verbose

# Component combinations
python test_runner.py --components models,processors --verbose
python test_runner.py --components connectors,text_processing --verbose
python test_runner.py --components storage,retrieval --verbose
```

### **🗄️ STORAGE TARGET-SPECIFIC TESTS**

```bash
# Individual storage targets
python test_runner.py --targets vector --verbose
python test_runner.py --targets database --verbose
python test_runner.py --targets knowledge_graph --verbose

# Storage target combinations
python test_runner.py --targets vector,database --verbose
python test_runner.py --targets database,knowledge_graph --verbose
python test_runner.py --targets vector,knowledge_graph --verbose
python test_runner.py --targets vector,database,knowledge_graph --verbose
```

### **🎬 SCENARIO-SPECIFIC TESTS**

```bash
# Individual scenarios
python test_runner.py --scenario github --verbose
python test_runner.py --scenario drive --verbose
python test_runner.py --scenario drive_file --verbose
python test_runner.py --scenario web --verbose

# Scenarios with specific targets
python test_runner.py --scenario github --targets vector --verbose
python test_runner.py --scenario drive --targets database --verbose
python test_runner.py --scenario drive_file --targets knowledge_graph --verbose
python test_runner.py --scenario web --targets vector,database --verbose

# Scenarios with specific components
python test_runner.py --scenario github --components processors,storage --verbose
python test_runner.py --scenario drive --components models,connectors --verbose
```

### **⚙️ PHASE-SPECIFIC TESTS**

```bash
# Individual phases
python test_runner.py --phase ingestion --verbose
python test_runner.py --phase retrieval --verbose
python test_runner.py --phase full --verbose

# Phases with scenarios
python test_runner.py --phase ingestion --scenario github --verbose
python test_runner.py --phase retrieval --scenario drive_file --verbose

# Phases with components
python test_runner.py --phase ingestion --components models,processors --verbose
python test_runner.py --phase retrieval --components storage,retrieval --verbose
```

### **📁 MODULE-LEVEL TESTS**

```bash
# Individual test modules
python -m pytest test_components.py -v
python -m pytest test_storage.py -v
python -m pytest test_integration.py -v

# Module combinations
python -m pytest test_components.py test_storage.py -v
python -m pytest test_storage.py test_integration.py -v
```

### **🎯 EXECUTION CONTROL COMBINATIONS**

```bash
# With strict validation
python test_runner.py --scenario github --strict-validation --verbose
python test_runner.py --components models --strict-validation --fail-fast
python test_runner.py --targets vector,database --strict-validation --verbose

# With fail-fast
python test_runner.py --scenario drive --fail-fast --verbose
python test_runner.py --phase ingestion --fail-fast
python test_runner.py --components storage --fail-fast --strict-validation

# Quiet mode for CI/automation
python test_runner.py --scenario web --quiet
python test_runner.py --targets vector --quiet --fail-fast
```

### **🌐 COMPREHENSIVE TESTS (Most General)**

```bash
# Full test suite
python test_runner.py --verbose
python test_runner.py --strict-validation --verbose
python test_runner.py --fail-fast --verbose
python test_runner.py --phase full --strict-validation --verbose

# All tests via pytest
python -m pytest tests/e2e/ -v
python -m pytest tests/e2e/ --tb=long -v
```

---

## 🚀 **RECOMMENDED EXECUTION ORDER**

I recommend we start with the **most specific tests** and work our way up to validate the foundation before testing complex integrations:

1. **Start with Models** → **Text Processing** → **Storage** → **Integration**
2. **Individual components** before **combinations**
3. **Single targets** before **multi-target** tests
4. **Basic scenarios** before **complex scenarios**
