# Environment Variables Usage Analysis

## Overview

This document provides a comprehensive analysis of environment variables defined in the `.env` file versus those actually used in the codebase. The project uses a hybrid configuration approach, with some values coming from environment variables and others from the YAML configuration file (`config/data_sources_config.yaml`).

## Environment Variables Analysis

### ✅ **ACTIVELY USED** Environment Variables

#### 1. `GOOGLE_CLOUD_PROJECT`
- **Status**: ✅ Used
- **Usage Locations**:
  - `app/agent_engine_app.py:46` - `project_id=os.environ.get("GOOGLE_CLOUD_PROJECT")`
  - `utils/secret_manager.py:27` - `self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")`
  - `data_ingestion/connectors/github_connector.py:260` - `project_id = os.getenv("GOOGLE_CLOUD_PROJECT")`
  - `data_ingestion/connectors/github_connector.py:265` - `project_id = access_token_config.get("project_id") or os.getenv("GOOGLE_CLOUD_PROJECT")`
- **Purpose**: Identifies the Google Cloud project for various services

#### 2. `GOOGLE_APPLICATION_CREDENTIALS`
- **Status**: ✅ Used
- **Usage Locations**:
  - `data_ingestion/connectors/drive_connector.py:109` - `credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')`
- **Purpose**: Path to Google Cloud service account key file

#### 3. `GITHUB_TOKEN`
- **Status**: ✅ Used
- **Usage Locations**:
  - `data_ingestion/connectors/github_connector.py:286` - `fallback_token = os.getenv("GITHUB_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN")`
- **Purpose**: GitHub Personal Access Token for repository access

#### 4. `NEO4J_PASSWORD`
- **Status**: ✅ Used
- **Usage Locations**:
  - `config/configuration.py:172` - `neo4j_password = os.environ.get('NEO4J_PASSWORD') or pipeline_data.get('neo4j_password', '')`
- **Purpose**: Password for Neo4j database connection

### ❌ **UNUSED** Environment Variables

#### 1. `GOOGLE_CLOUD_LOCATION`
- **Status**: ❌ Not used directly from environment
- **Note**: Value is configured in YAML file (`google_cloud_location: "us-west1"`)

#### 2. `GOOGLE_GENAI_USE_VERTEXAI`
- **Status**: ❌ Not used
- **Current Value**: `"us-west1"` (appears to be misconfigured - should be boolean)

#### 3. `GOOGLE_API_KEY`
- **Status**: ❌ Not used
- **Current Value**: API key present but no code references found

#### 4. `VECTOR_SEARCH_INDEX`
- **Status**: ❌ Not used directly from environment
- **Note**: Configuration comes from YAML file (`vector_search_index`)

#### 5. `VECTOR_SEARCH_INDEX_ENDPOINT`
- **Status**: ❌ Not used directly from environment
- **Note**: Configuration comes from YAML file (`vector_search_endpoint`)

#### 6. `VECTOR_SEARCH_BUCKET`
- **Status**: ❌ Not used directly from environment
- **Note**: Configuration comes from YAML file (`vector_search_bucket`)

#### 7. `GOOGLE_CLIENT_SECRETS_PATH`
- **Status**: ❌ Not used
- **Current Value**: Empty string

#### 8. `NEO4J_URI`
- **Status**: ❌ Not used directly from environment
- **Note**: Configuration comes from YAML file (`neo4j_uri`)

#### 9. `NEO4J_USER`
- **Status**: ❌ Not used directly from environment
- **Note**: Configuration comes from YAML file (`neo4j_user`)

#### 10. `GOOGLE_CALENDAR_API_KEY`
- **Status**: ❌ Not used
- **Current Value**: API key present but no code references found

### 📋 **ADDITIONAL** Environment Variables Used (Not in .env)

#### 1. `_AUTH_TOKEN`
- **Status**: Used but missing from .env
- **Usage Location**: `tests/load_test/load_test.py:55` - `headers["Authorization"] = f"Bearer {os.environ['_AUTH_TOKEN']}"`
- **Purpose**: Authentication token for load testing

#### 2. `GITHUB_ACCESS_TOKEN`
- **Status**: Alternative fallback (not in .env)
- **Usage Location**: `data_ingestion/connectors/github_connector.py:286`
- **Purpose**: Alternative name for GitHub token

## Configuration Strategy Analysis

### Current Hybrid Approach
The project uses two configuration sources:
1. **Environment Variables**: For sensitive data and deployment-specific values
2. **YAML Configuration**: For application settings and non-sensitive configuration

### Environment vs YAML Usage Patterns

| Configuration Type | Environment Variable | YAML Configuration |
|-------------------|---------------------|-------------------|
| Google Cloud Project | ✅ `GOOGLE_CLOUD_PROJECT` | ✅ `google_cloud_project` |
| Google Cloud Location | ❌ `GOOGLE_CLOUD_LOCATION` | ✅ `google_cloud_location` |
| Vector Search Config | ❌ Multiple unused vars | ✅ YAML only |
| Neo4j Config | ✅ `NEO4J_PASSWORD` only | ✅ URI, user, other settings |
| GitHub Token | ✅ `GITHUB_TOKEN` | ❌ Not in YAML |

## Recommendations

### 1. Clean Up Unused Environment Variables
Remove the following unused variables from `.env`:
```bash
# Remove these unused variables:
GOOGLE_CLOUD_LOCATION="us-west1"
GOOGLE_GENAI_USE_VERTEXAI="us-west1"
GOOGLE_API_KEY="AIzaSyC-FkvyxBQdEDboBAPafWTGiSFsRPtIR5o"
VECTOR_SEARCH_INDEX="8386573319373062144"
VECTOR_SEARCH_INDEX_ENDPOINT="projects/267266051209/locations/us-west1/indexEndpoints/7620996567092166656"
VECTOR_SEARCH_BUCKET="ps-agent-vs-bucket"
GOOGLE_CLIENT_SECRETS_PATH=""
NEO4J_URI=neo4j://nyx.gagan.pro
NEO4J_USER=neo4j
GOOGLE_CALENDAR_API_KEY=AIzaSyBS3lebMTYQUpEuH05emfL9DL99Mpjkw7U
```

### 2. Add Missing Environment Variables
Add required variables that are used but not defined:
```bash
# Add this for load testing:
_AUTH_TOKEN="your-auth-token-here"
```

### 3. Minimal .env File
The cleaned `.env` file should contain only:
```bash
# Essential environment variables only
GOOGLE_CLOUD_PROJECT="ps-agent-sandbox"
GOOGLE_APPLICATION_CREDENTIALS="/Users/albertomedina/.config/gcloud/application_default_credentials.json"
GITHUB_TOKEN="your-github-token-here"
NEO4J_PASSWORD="your-neo4j-password-here"
_AUTH_TOKEN="your-auth-token-here"
```

### 4. Configuration Consolidation Options

#### Option A: Environment-First Approach
- Move more configuration to environment variables
- Pros: Better for containerization, clearer separation of concerns
- Cons: More environment variables to manage

#### Option B: YAML-First Approach
- Keep only truly sensitive data in environment variables
- Move remaining config to YAML with environment variable overrides
- Pros: Easier configuration management, better for development
- Cons: Mixed configuration sources

#### Option C: Current Hybrid (Recommended)
- Keep sensitive data (passwords, tokens) in environment variables
- Keep application configuration in YAML
- Ensure consistency between both sources

### 5. Implementation Steps

1. **Immediate**: Remove unused environment variables from `.env`
2. **Short-term**: Add missing `_AUTH_TOKEN` for load testing
3. **Medium-term**: Update documentation to reflect actual usage
4. **Long-term**: Consider configuration consolidation strategy

## Security Considerations

- ✅ Sensitive data (passwords, tokens, API keys) should remain in environment variables
- ✅ Application configuration can safely be in YAML files
- ⚠️ Ensure `.env` file is properly gitignored
- ⚠️ Rotate any exposed tokens/keys in unused variables

## Summary

Out of **14 environment variables** defined in `.env`:
- **4 are actively used** (29%)
- **10 are unused** (71%)
- **1 additional variable** is used but not defined

This analysis suggests significant cleanup opportunity while maintaining security best practices. 