# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Load environment variables before imports
from dotenv import load_dotenv
load_dotenv()

import os
import logging
from typing import Dict, List, Any, Optional

# Import Secret Manager utilities
from utils.secret_manager import SecretConfig

logger = logging.getLogger(__name__)


class KnowledgeGraphManager:
    """
    Interface for Neo4j knowledge graph operations.
    
    This class provides a simplified interface for querying the knowledge graph.
    The heavy lifting (entity extraction and ingestion) is handled by the
    data ingestion pipeline components.

    - Connection Management: Auto-detects Neo4j availability with graceful degradation
    - Credential Management: Google Cloud Secret Manager integration with environment variable fallback
    - Query Interface: High-level methods for natural language queries
    - Entity & Relationship Discovery: Structured graph traversal
    - Context Extraction: Rich context around entities and relationships
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        # Initialize secret configuration
        self.secret_config = SecretConfig(project_id)
        
        # Get Neo4j configuration with override support
        if uri or user or password:
            # Use provided overrides
            self.uri = uri or self.secret_config.get_secret("neo4j-uri", env_fallback="NEO4J_URI")
            self.user = user or self.secret_config.get_secret("neo4j-user", env_fallback="NEO4J_USER", default="neo4j")
            self.password = password or self.secret_config.get_secret("neo4j-password", env_fallback="NEO4J_PASSWORD")
        else:
            # Use the convenience method for cleaner configuration
            neo4j_config = self.secret_config.get_neo4j_config()
            self.uri = neo4j_config.get("uri")
            self.user = neo4j_config.get("user", "neo4j")  
            self.password = neo4j_config.get("password")
        
        self.driver = None
        
        # Only initialize if credentials are available
        if self.uri and self.password:
            self._initialize_connection()
        else:
            logger.info("Neo4j credentials not found in Secret Manager or environment variables. Knowledge graph features will be disabled.")
    
    def _initialize_connection(self):
        """Initialize Neo4j connection."""
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Connected to Neo4j knowledge graph")
        except Exception as e:
            logger.warning(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def is_available(self) -> bool:
        """Check if knowledge graph is available."""
        return self.driver is not None
    
    def search_entities(self, query: str, entity_types: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for entities in the knowledge graph.
        
        Args:
            query: Search query
            entity_types: Filter by entity types (technology, concept, person, organization)
            limit: Maximum number of results
            
        Returns:
            List of matching entities
        """
        if not self.is_available():
            return []
            
        try:
            with self.driver.session() as session:
                # Build Cypher query
                cypher_query = """
                MATCH (e:Entity)
                WHERE e.name CONTAINS $query OR e.context CONTAINS $query
                """
                
                params = {"query": query, "limit": limit}
                
                if entity_types:
                    cypher_query += " AND e.type IN $entity_types"
                    params["entity_types"] = entity_types
                
                cypher_query += """
                RETURN e.name as name, e.type as type, e.context as context
                ORDER BY e.name
                LIMIT $limit
                """
                
                result = session.run(cypher_query, params)
                return [
                    {
                        "name": record["name"],
                        "type": record["type"],
                        "context": record["context"],
                    }
                    for record in result
                ]
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return []
    
    def find_relationships(self, entity_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find relationships for a given entity.
        
        Args:
            entity_name: Name of the entity
            limit: Maximum number of relationships
            
        Returns:
            List of relationships
        """
        if not self.is_available():
            return []
            
        try:
            with self.driver.session() as session:
                cypher_query = """
                MATCH (source:Entity {name: $entity_name})-[r]->(target:Entity)
                RETURN source.name as source, type(r) as relationship, target.name as target,
                       r.confidence as confidence, r.original_type as original_type
                UNION
                MATCH (source:Entity)-[r]->(target:Entity {name: $entity_name})
                RETURN source.name as source, type(r) as relationship, target.name as target,
                       r.confidence as confidence, r.original_type as original_type
                LIMIT $limit
                """
                
                result = session.run(cypher_query, entity_name=entity_name, limit=limit)
                return [
                    {
                        "source": record["source"],
                        "relationship": record["original_type"] or record["relationship"],
                        "target": record["target"],
                        "confidence": record["confidence"],
                    }
                    for record in result
                ]
        except Exception as e:
            logger.error(f"Error finding relationships: {e}")
            return []
    
    def get_entity_context(self, entity_name: str) -> str:
        """
        Get contextual information about an entity.
        
        Args:
            entity_name: Name of the entity
            
        Returns:
            Formatted context string
        """
        if not self.is_available():
            return f"Knowledge graph not available. Cannot retrieve context for: {entity_name}"
        
        # Get entity information
        entities = self.search_entities(entity_name, limit=1)
        if not entities:
            return f"Entity not found in knowledge graph: {entity_name}"
        
        entity = entities[0]
        
        # Get relationships
        relationships = self.find_relationships(entity_name, limit=20)
        
        # Format response
        context_parts = []
        context_parts.append(f"**{entity['name']}** ({entity['type']})")
        
        if entity['context']:
            context_parts.append(f"Context: {entity['context']}")
        
        if relationships:
            context_parts.append("\n**Relationships:**")
            for rel in relationships:
                if rel['source'] == entity_name:
                    context_parts.append(f"- {rel['relationship']} → {rel['target']}")
                else:
                    context_parts.append(f"- {rel['source']} → {rel['relationship']} → {entity_name}")
        
        return "\n".join(context_parts)
    
    def explore_topic(self, topic: str, depth: int = 2) -> str:
        """
        Explore a topic by finding related entities and their connections.
        
        Args:
            topic: Topic to explore
            depth: Depth of exploration (1 or 2)
            
        Returns:
            Formatted exploration results
        """
        if not self.is_available():
            return f"Knowledge graph not available. Cannot explore topic: {topic}"
        
        try:
            with self.driver.session() as session:
                # Find entities related to the topic
                cypher_query = """
                MATCH (e:Entity)
                WHERE e.name CONTAINS $topic OR e.context CONTAINS $topic
                RETURN e.name as name, e.type as type, e.context as context
                ORDER BY e.name
                LIMIT 10
                """
                
                result = session.run(cypher_query, topic=topic)
                entities = [
                    {
                        "name": record["name"],
                        "type": record["type"],
                        "context": record["context"],
                    }
                    for record in result
                ]
                
                if not entities:
                    return f"No entities found related to topic: {topic}"
                
                # Format results
                exploration_parts = [f"**Knowledge Graph Exploration: {topic}**\n"]
                
                for entity in entities:
                    exploration_parts.append(f"**{entity['name']}** ({entity['type']})")
                    if entity['context']:
                        exploration_parts.append(f"  Context: {entity['context'][:200]}...")
                    
                    # Get some relationships if depth > 1
                    if depth > 1:
                        relationships = self.find_relationships(entity['name'], limit=5)
                        if relationships:
                            exploration_parts.append("  Related to:")
                            for rel in relationships[:3]:  # Show top 3
                                if rel['source'] == entity['name']:
                                    exploration_parts.append(f"    - {rel['relationship']} → {rel['target']}")
                                else:
                                    exploration_parts.append(f"    - {rel['source']} → {rel['relationship']} → {entity['name']}")
                    
                    exploration_parts.append("")  # Empty line
                
                return "\n".join(exploration_parts)
                
        except Exception as e:
            logger.error(f"Error exploring topic: {e}")
            return f"Error exploring topic {topic}: {e}"
    
    def query_knowledge_graph(self, query: str) -> List[Dict[str, Any]]:
        """
        Query the knowledge graph with a natural language query.
        This method combines entity search and relationship finding to provide comprehensive results.
        
        Args:
            query: Natural language search query
            
        Returns:
            List of results with entities and their connections
        """
        if not self.is_available():
            return []
        
        try:
            # Search for relevant entities
            entities = self.search_entities(query, limit=10)
            
            results = []
            for entity in entities:
                # Get relationships for each entity
                relationships = self.find_relationships(entity['name'], limit=10)
                
                result = {
                    "entity": entity,
                    "connections": relationships
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying knowledge graph: {e}")
            return []
    
    def process_document_for_kg(self, content: str, metadata: Dict[str, Any]) -> bool:
        """
        Process a document to extract entities and relationships for the knowledge graph.
        This is a placeholder for future implementation - the actual processing should be 
        done by the data ingestion pipeline.
        
        Args:
            content: Document content
            metadata: Document metadata
            
        Returns:
            Success status
        """
        if not self.is_available():
            logger.warning("Knowledge graph not available for document processing")
            return False
        
        # TODO: Implement entity extraction and relationship discovery
        # For now, this is a placeholder that logs the processing attempt
        logger.info(f"Processing document for knowledge graph: {metadata.get('id', 'unknown')}")
        logger.info(f"Content length: {len(content)} characters")
        
        # In a real implementation, this would:
        # 1. Extract entities from the content using NLP
        # 2. Identify relationships between entities
        # 3. Store them in the Neo4j database
        # 4. Return success/failure status
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get basic statistics about the knowledge graph."""
        if not self.is_available():
            return {"error": "Knowledge graph not available"}
        
        try:
            with self.driver.session() as session:
                # Count entities by type
                entity_counts = session.run("""
                MATCH (e:Entity)
                RETURN e.type as type, count(e) as count
                ORDER BY count DESC
                """)
                
                # Count relationships
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
                
                # Total entities
                total_entities = session.run("MATCH (e:Entity) RETURN count(e) as count").single()["count"]
                
                return {
                    "total_entities": total_entities,
                    "total_relationships": rel_count,
                    "entities_by_type": {record["type"]: record["count"] for record in entity_counts},
                }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            try:
                self.driver.close()
                logger.info("Neo4j connection closed")
            except Exception as e:
                logger.warning(f"Error closing Neo4j connection: {e}")
            finally:
                self.driver = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed."""
        self.close()
        return False  # Don't suppress exceptions
    
    def __del__(self):
        """Destructor to ensure Neo4j connection is closed."""
        try:
            self.close()
        except Exception:
            # Silently handle any errors during destruction
            pass 