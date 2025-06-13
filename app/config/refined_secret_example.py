"""
Refined Secret Resolution Example

This example demonstrates the improved security approach where secrets are resolved from:
1. Google Cloud Secret Manager (primary)
2. Environment variables (fallback)

No secrets are stored in configuration files for maximum security.
"""

import os
from app.config.configuration import get_config_manager, SecretConfig

def demonstrate_refined_secret_resolution():
    """Demonstrate the refined secure secret resolution."""
    
    # Create a configuration manager with secret support
    secret_config = SecretConfig(
        project_id="ps-agent-sandbox",
        enable_fallback_env=True,
        cache_ttl_minutes=5
    )
    
    config_manager = get_config_manager(secret_config=secret_config)
    
    print("=== Refined Secret Resolution (Security-First Approach) ===\n")
    
    # 1. Neo4j Password Resolution
    print("1. Neo4j Password Resolution:")
    try:
        neo4j_secrets = config_manager.resolve_neo4j_secrets()
        print(f"   ✅ Resolved neo4j_password: {'*' * len(neo4j_secrets['neo4j_password'])}")
        print("   🔒 Resolution order:")
        print("   - Primary: Secret Manager (neo4j-password)")
        print("   - Fallback: Environment Variable (NEO4J_PASSWORD)")
        print("   - Default: '' (empty string)")
    except Exception as e:
        print(f"   ❌ Error resolving neo4j password: {e}")
    
    print()
    
    # 2. Database Password Resolution  
    print("2. Database Password Resolution:")
    try:
        db_secrets = config_manager.resolve_database_secrets()
        print(f"   ✅ Resolved db_pass: {'*' * len(db_secrets['db_pass'])}")
        print("   🔒 Resolution order:")
        print("   - Primary: Secret Manager (db-pass)")
        print("   - Fallback: Environment Variable (DB_PASS)")
        print("   - Default: '' (empty string)")
    except Exception as e:
        print(f"   ❌ Error resolving database password: {e}")
    
    print()
    
    # 3. Custom Secret Resolution
    print("3. Custom Secret Resolution:")
    try:
        api_key = config_manager.resolve_secret(
            secret_key='github-token',
            env_key='GITHUB_TOKEN',
            default_value='default-key'
        )
        print(f"   ✅ Resolved GitHub token: {'*' * len(api_key)}")
        print("   🔒 Resolution order:")
        print("   - Primary: Secret Manager (github-token)")
        print("   - Fallback: Environment Variable (GITHUB_TOKEN)")
        print("   - Default: 'default-key'")
    except Exception as e:
        print(f"   ❌ Error resolving GitHub token: {e}")
    
    print()
    
    # 4. Load full system configuration with secret resolution
    print("4. Full System Configuration:")
    try:
        system_config = config_manager.config
        if system_config.pipeline_config.neo4j:
            print(f"   Neo4j URI: {system_config.pipeline_config.neo4j.uri}")
            print(f"   Neo4j User: {system_config.pipeline_config.neo4j.user}")
            print(f"   Neo4j Password: {'*' * len(system_config.pipeline_config.neo4j.password)} (from secure source)")
        
        if system_config.pipeline_config.database:
            print(f"   Database Name: {system_config.pipeline_config.database.db_name}")
            print(f"   Database User: {system_config.pipeline_config.database.db_user}")
            print(f"   Database Pass: {'*' * len(system_config.pipeline_config.database.db_pass)} (from secure source)")
            
    except Exception as e:
        print(f"   ❌ Error loading system configuration: {e}")

def demonstrate_environment_override():
    """Show how environment variables work as secure fallbacks."""
    
    print("\n=== Environment Variable Fallback Demo ===\n")
    
    # Temporarily set environment variables to demonstrate fallback
    original_neo4j = os.environ.get('NEO4J_PASSWORD')
    original_db = os.environ.get('DB_PASS')
    
    try:
        # Set demo environment variables
        os.environ['NEO4J_PASSWORD'] = 'env_neo4j_demo_password'
        os.environ['DB_PASS'] = 'env_db_demo_password'
        
        config_manager = get_config_manager()
        
        print("🔧 Demonstrating environment variable fallback...")
        print("   (This simulates when Secret Manager is unavailable)")
        
        # Test Neo4j password resolution (will try Secret Manager first, then env var)
        try:
            neo4j_secrets = config_manager.resolve_neo4j_secrets()
            source = "Secret Manager" if len(neo4j_secrets['neo4j_password']) > 20 else "Environment Variable"
            print(f"   Neo4j password source: {source}")
        except Exception as e:
            print(f"   Neo4j resolution failed: {e}")
        
        # Test database password resolution
        try:
            db_secrets = config_manager.resolve_database_secrets()
            source = "Secret Manager" if len(db_secrets['db_pass']) > 20 else "Environment Variable"
            print(f"   Database password source: {source}")
        except Exception as e:
            print(f"   Database resolution failed: {e}")
            
    finally:
        # Clean up environment variables
        if original_neo4j is not None:
            os.environ['NEO4J_PASSWORD'] = original_neo4j
        else:
            os.environ.pop('NEO4J_PASSWORD', None)
            
        if original_db is not None:
            os.environ['DB_PASS'] = original_db
        else:
            os.environ.pop('DB_PASS', None)

def demonstrate_security_benefits():
    """Explain the security benefits of this approach."""
    
    print("\n=== Security Benefits ===\n")
    
    security_benefits = [
        "🔒 No secrets stored in configuration files",
        "🔒 No secrets committed to version control",
        "🔒 Centralized secret management via Google Cloud Secret Manager",
        "🔒 Automatic secret rotation support",
        "🔒 Audit trail for secret access",
        "🔒 Environment-based fallback for development/testing",
        "🔒 Clear separation between configuration and secrets",
        "🔒 Reduced risk of accidental secret exposure"
    ]
    
    print("Benefits of the refined approach:")
    for benefit in security_benefits:
        print(f"   {benefit}")
    
    print("\n📋 Configuration File Changes:")
    print("   ✅ Removed: db_pass field")
    print("   ✅ Removed: neo4j_password field")
    print("   ✅ Added: Security comments explaining where secrets come from")
    
    print("\n🔧 Setup Requirements:")
    print("   1. Configure secrets in Google Cloud Secret Manager:")
    print("      - Secret: 'db-pass' (for database password)")
    print("      - Secret: 'neo4j-password' (for Neo4j password)")
    print("      - Secret: 'github-token' (for GitHub access)")
    print("   2. Or set environment variables:")
    print("      - DB_PASS (database password)")
    print("      - NEO4J_PASSWORD (Neo4j password)")
    print("      - GITHUB_TOKEN (GitHub access token)")

if __name__ == "__main__":
    demonstrate_refined_secret_resolution()
    demonstrate_environment_override()
    demonstrate_security_benefits() 