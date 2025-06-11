# **Data Pipeline Execution Guide - Comprehensive Setup and Validation Approach**

## **System Architecture Overview**

The pipeline implements a **Coordinator Pattern** with three storage layers:

1. **Vertex AI Vector Search Index** - Semantic similarity searches
2. **Google Cloud PostgreSQL Database** - Document metadata storage  
3. **Neo4j Knowledge Graph Database** - Entities and relationships

**Key Components:**
- `PipelineCLI` - Command-line interface for pipeline management
- `PipelineManager` - Central control unit for data processing
- **Managers** (Orchestration Layer): Vector Store, Database, Knowledge Graph
- **Ingestors** (Storage Layer): Component-specific data storage
- **Retrievers** (Query Layer): Data retrieval and search
- **Connectors** (Data Sources): GitHub, Google Drive, Web sources
- **Processors** (Document Processing): Text processing, chunking, entity extraction

The CLI provides five main commands:
- `run` - Execute the data ingestion pipeline
- `status` - Check component health
- `stats` - Get pipeline statistics  
- `test` - Test connectivity
- `validate` - Validate system setup

**Execution Modes:**
The system supports three sync modes:
- **Smart Sync**: Processes only changed content (default)
- **Incremental Sync**: Processes only new content  
- **Full Sync**: Processes all content

## **Step-by-Step Implementation**

### **Step 1: System Setup Validation**

Before running the pipeline, validate that all components are properly configured and accessible:

```bash
# Navigate to the data_ingestion/pipeline directory
cd data_ingestion/pipeline

# Validate complete system setup and configuration
python pipeline_cli.py validate

# Expected output will show:
# ✅ Vector Store Connection: PASS
# ✅ Database Connection: PASS  
# ✅ Knowledge Graph Connection: PASS
# ✅ Configuration: VALID
```

**What this validates:**
- Vector Search (Vertex AI) connectivity
- PostgreSQL database connectivity
- Neo4j knowledge graph connectivity
- Configuration file validity
- Required credentials and permissions

### **Step 2: Component Health Check**

Verify all pipeline components are healthy and operational:

```bash
# Check overall system health
python pipeline_cli.py status

# Save detailed health report
python pipeline_cli.py status --output-file health_report.json
```

**Expected healthy output:**
```
PIPELINE HEALTH STATUS
✅ Overall Status: HEALTHY
✅ Vector Search: healthy
✅ Database: healthy  
✅ Knowledge Graph: healthy
```

### **Step 3: Test Component Connectivity**

Explicitly test connections to all storage systems:

```bash
# Test connectivity to all components
python pipeline_cli.py test

# Expected output:
# ✅ Vector Store Connection: PASS
# ✅ Database Connection: PASS
# ✅ Neo4j Connection: PASS
# ✅ Overall Connectivity: PASS
```

### **Step 4: Review Pipeline Statistics**

Understand the current state of your data before running the pipeline:

```bash
# Get comprehensive pipeline statistics
python pipeline_cli.py stats --output-file current_stats.json

# This shows:
# - Enabled data sources count
# - Current chunk counts by source type
# - Knowledge graph entity/relationship counts
# - Recent activity summary
```

### **Step 5: Execute Pipeline with Smart Sync (Recommended First Run)**

Start with smart sync mode to process only changed content:

```bash
# Run pipeline in smart sync mode (default)
python pipeline_cli.py run

# Alternative with explicit mode specification
python pipeline_cli.py run --mode smart

# For testing with limited documents
python pipeline_cli.py --quiet run --limit 10
```

**Smart Sync Benefits:**
- Only processes changed/new content
- Faster execution
- Minimizes unnecessary reprocessing
- Good for regular incremental updates

### **Step 6: Monitor Pipeline Execution**

The pipeline provides real-time feedback during execution:

```bash
# Run with verbose logging for detailed monitoring
python pipeline_cli.py --verbose run

# Run in quiet mode for clean summary output
python pipeline_cli.py --quiet run --output-file execution_results.json
```

**Expected execution flow:**
```
🚀 Starting pipeline execution with mode: smart_sync
📊 Processing 3 data source(s)...
  📁 Processing: ps-analysis-tool
    ✅ Completed: 15 documents from ps-analysis-tool
  📁 Processing: devrel-docs  
    ✅ Completed: 8 documents from devrel-docs
  📁 Processing: github-repo-main
    ✅ Completed: 22 documents from github-repo-main
✅ Pipeline execution completed in 45.2s
```

### **Step 7: Validate Successful Execution**

After pipeline completion, verify data was stored correctly:

```bash
# Check updated statistics
python pipeline_cli.py stats

# Re-run health check to ensure system stability
python pipeline_cli.py status
```

**Success indicators:**
- Zero storage/processing errors
- All chunks stored across ALL storage systems
- Updated entity/relationship counts (if knowledge graph enabled)
- Successful document processing counts

## **Advanced Execution Options**

### **Full Sync Mode (Complete Reprocessing)**

```bash
# Process all content regardless of previous processing
python pipeline_cli.py run --mode full

# Full sync with specific sources only
python pipeline_cli.py run --mode full --source-filter "ps-analysis-tool,devrel-docs"
```

### **Incremental Sync Mode (New Content Only)**

```bash
# Process only new content since last sync
python pipeline_cli.py run --mode incremental
```

### **Source Filtering**

```bash
# Process specific data sources only
python pipeline_cli.py run --source-filter "ps-analysis-tool"

# Multiple sources
python pipeline_cli.py run --source-filter "ps-analysis-tool,devrel-docs,github-repo-main"
```

## **Configuration Management**

### **Custom Configuration File**

```bash
# Use custom configuration file
python pipeline_cli.py --config /path/to/custom_config.yaml validate
python pipeline_cli.py --config /path/to/custom_config.yaml run
```

### **Output Management**

```bash
# Save all outputs to files
python pipeline_cli.py run --output-file pipeline_results.json
python pipeline_cli.py stats --output-file stats_report.json
python pipeline_cli.py status --output-file health_check.json
```

## **Error Handling and Troubleshooting**

### **Exit Codes**
The CLI uses meaningful exit codes:
- **0**: Success (all processable data stored successfully)
- **1**: Partial success with storage errors OR complete failure

### **Common Issues and Solutions**

1. **Component Connection Failures**
   ```bash
   # Test individual components
   python pipeline_cli.py test
   # Check configuration
   python pipeline_cli.py validate
   ```

2. **Storage System Errors**
   ```bash
   # Run with verbose logging to identify issues
   python pipeline_cli.py --verbose run --limit 5
   ```

3. **Configuration Issues**
   ```bash
   # Validate configuration thoroughly
   python pipeline_cli.py validate --output-file validation_report.json
   ```

## **Production Deployment Workflow**

### **Complete Production Setup**

```bash
# 1. Validate system setup
python pipeline_cli.py validate

# 2. Test all connections
python pipeline_cli.py test

# 3. Get baseline statistics  
python pipeline_cli.py stats --output-file baseline_stats.json

# 4. Run initial full sync
python pipeline_cli.py --quiet run --mode full --output-file initial_sync.json

# 5. Verify successful completion
python pipeline_cli.py stats --output-file post_sync_stats.json
python pipeline_cli.py status
```

### **Regular Incremental Updates**

```bash
# Daily/regular incremental sync
python pipeline_cli.py --quiet run --mode smart --output-file daily_sync_$(date +%Y%m%d).json
```

## **Monitoring and Maintenance**

### **Health Monitoring Script**
```bash
#!/bin/bash
# health_check.sh
python pipeline_cli.py status --output-file health_$(date +%Y%m%d_%H%M).json
if [ $? -eq 0 ]; then
    echo "✅ System healthy"
else 
    echo "❌ System issues detected"
    # Send alerts/notifications
fi
```

### **Statistics Tracking**
```bash
# Weekly statistics report
python pipeline_cli.py stats --output-file weekly_stats_$(date +%Y%m%d).json
```

## **CLI Command Reference**

### **Global Options**
- `--config`: Path to configuration file (default: `config/data_sources_config.yaml`)
- `--output-file`: Save detailed output to JSON file
- `--verbose, -v`: Enable verbose logging (shows all INFO messages)
- `--quiet, -q`: Quiet mode - only show warnings, errors, and final summary

### **Commands**

#### **`run` - Execute Pipeline**
```bash
python pipeline_cli.py run [OPTIONS]
```
Options:
- `--mode {smart,incremental,full}`: Pipeline execution mode (default: smart)
- `--source-filter`: Comma-separated list of source IDs to process
- `--limit`: Limit the number of documents to process (useful for testing)

#### **`status` - Check Health**
```bash
python pipeline_cli.py status [OPTIONS]
```
Shows overall system health and individual component status.

#### **`stats` - Get Statistics**
```bash
python pipeline_cli.py stats [OPTIONS]
```
Displays comprehensive pipeline and data statistics.

#### **`test` - Test Connectivity**
```bash
python pipeline_cli.py test [OPTIONS]
```
Tests connectivity to all pipeline components.

#### **`validate` - Validate Setup**
```bash
python pipeline_cli.py validate [OPTIONS]
```
Validates system setup and configuration.

## **Examples**

```bash
# Validate system setup (recommended first step)
python pipeline_cli.py validate

# Run smart sync pipeline (default - processes only changed content)
python pipeline_cli.py run

# Run in quiet mode (only warnings, errors, and summary)
python pipeline_cli.py --quiet run

# Run full sync pipeline (processes all content)
python pipeline_cli.py run --mode full

# Run with document limit for testing
python pipeline_cli.py --quiet run --limit 5

# Run incremental sync for specific sources
python pipeline_cli.py run --mode incremental --source-filter "ps-analysis-tool,devrel-docs"

# Run with verbose logging (shows all INFO messages)
python pipeline_cli.py --verbose run

# Check system health
python pipeline_cli.py status

# Test connectivity
python pipeline_cli.py test

# Get statistics
python pipeline_cli.py stats --output-file stats.json
```

This comprehensive approach ensures reliable pipeline execution with proper validation, monitoring, and error handling throughout the process. 