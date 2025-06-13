"""
Example demonstrating the new secret resolution functionality in ConfigurationManager.

This example shows how secrets can be resolved with the following fallback chain:
1. Google Cloud Secret Manager
2. Environment variables (os.environ.get())
3. Pipeline data (pipeline_data.get())
4. Default values
"""

import os
from app.config.configuration import get_config_manager
from app.utils.secret_manager import SecretConfig

def demonstrate_secret_resolution():
    """Demonstrate different ways to resolve secrets."""
    
    # Create a configuration manager with secret support
    secret_config = SecretConfig(
        project_id="ps-agent-sandbox",
        enable_fallback_env=True,
        cache_ttl_minutes=5
    )
    
    config_manager = get_config_manager(secret_config=secret_config)
    
    # Example pipeline data (as would come from YAML config)
    pipeline_data = {
        'neo4j_password': 'yaml_neo4j_password',
        'db_pass': 'yaml_db_password',
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j'
    }
    
    print("=== Secret Resolution Examples ===\n")
    
    # 1. Neo4j Password Resolution
    print("1. Neo4j Password Resolution:")
    try:
        neo4j_secrets = config_manager.resolve_neo4j_secrets(pipeline_data)
        print(f"   Resolved neo4j_password: {neo4j_secrets['neo4j_password']}")
        print("   Resolution order tried:")
        print("   - Secret Manager: neo4j-password")
        print("   - Environment Variable: NEO4J_PASSWORD")
        print("   - Pipeline Data: neo4j_password")
        print("   - Default: '' (empty string)")
    except Exception as e:
        print(f"   Error resolving neo4j password: {e}")
    
    print()
    
    # 2. Database Password Resolution  
    print("2. Database Password Resolution:")
    try:
        db_secrets = config_manager.resolve_database_secrets(pipeline_data)
        print(f"   Resolved db_pass: {db_secrets['db_pass']}")
        print("   Resolution order tried:")
        print("   - Secret Manager: db-password")
        print("   - Environment Variable: DB_PASS")
        print("   - Pipeline Data: db_pass (preferred)")
        print("   - Pipeline Data: neo4j_password (legacy fallback)")
        print("   - Default: '' (empty string)")
    except Exception as e:
        print(f"   Error resolving database password: {e}")
    
    print()
    
    # 3. Custom Secret Resolution
    print("3. Custom Secret Resolution:")
    try:
        custom_secret = config_manager.resolve_secret(
            secret_key='custom-api-key',
            env_key='CUSTOM_API_KEY',
            pipeline_data={'custom_api_key': 'pipeline_api_key_value'},
            pipeline_key='custom_api_key',
            default_value='default-api-key'
        )
        print(f"   Resolved custom secret: {custom_secret}")
        print("   Resolution order tried:")
        print("   - Secret Manager: db-password")
        print("   - Environment Variable: DB_PASS")
        print("   - Pipeline Data: db_pass (preferred)")
        print("   - Pipeline Data: db_pass (legacy fallback)")
        print("   - Default: '' (empty string)")
    except Exception as e:
        print(f"   Error resolving custom secret: {e}")
    
    print()
    
    # 4. Load full system configuration with secret resolution
    print("4. Full System Configuration:")
    try:
        system_config = config_manager.config
        if system_config.pipeline_config.neo4j:
            print(f"   Neo4j URI: {system_config.pipeline_config.neo4j.uri}")
            print(f"   Neo4j User: {system_config.pipeline_config.neo4j.user}")
            print(f"   Neo4j Password: {'*' * len(system_config.pipeline_config.neo4j.password)}")
        
        if system_config.pipeline_config.database:
            print(f"   Database Pass: {'*' * len(system_config.pipeline_config.database.db_pass)}")
            
    except Exception as e:
        print(f"   Error loading system configuration: {e}")

def demonstrate_environment_priority():
    """Demonstrate how environment variables take precedence over pipeline data."""
    
    print("\n=== Environment Variable Priority Example ===\n")
    
    # Set some environment variables
    os.environ['NEO4J_PASSWORD'] = 'env_neo4j_password'
    os.environ['DB_PASS'] = 'env_db_password'
    
    config_manager = get_config_manager()
    
    pipeline_data = {
        'neo4j_password': 'yaml_neo4j_password',  # This should be overridden by env var
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j'
    }
    
    # Test Neo4j password resolution
    neo4j_secrets = config_manager.resolve_neo4j_secrets(pipeline_data)
    print(f"Neo4j password from environment: {neo4j_secrets['neo4j_password']}")
    print("(Should be 'env_neo4j_password', not 'yaml_neo4j_password')")
    
    # Test database password resolution
    db_secrets = config_manager.resolve_database_secrets(pipeline_data)
    print(f"Database password from environment: {db_secrets['db_pass']}")
    print("(Should be 'env_db_password')")
    
    # Clean up environment variables
    os.environ.pop('NEO4J_PASSWORD', None)
    os.environ.pop('DB_PASS', None)

def demonstrate_yaml_integration():
    """Show how the new system works with YAML configuration files."""
    
    print("\n=== YAML Configuration Integration ===\n")
    
    # Example of how the YAML would look
    yaml_example = """
project_config:
  google_cloud_project: "your-project"
  google_cloud_location: "us-west1"

pipeline_config:
  neo4j_uri: "bolt://localhost:7687"
  neo4j_user: "neo4j"
  neo4j_password: "fallback_password_from_yaml"  # Will be overridden by secret resolution
  
  instance-connection-name: "project:region:instance"
  db_name: "your_database"
  db_user: "db_user"
  neo4j_password: "fallback_db_password"  # Used as fallback for db_pass
"""
    
    print("Example YAML configuration:")
    print(yaml_example)
    print("\nWith the new secret resolution system:")
    print("- neo4j_password will be resolved from Secret Manager -> ENV -> YAML -> Default")
    print("- db_pass will be resolved from Secret Manager -> ENV -> neo4j_password (YAML) -> Default")
    print("- This maintains backward compatibility while adding secure secret management")

if __name__ == "__main__":
    demonstrate_secret_resolution()
    demonstrate_environment_priority()
    demonstrate_yaml_integration()