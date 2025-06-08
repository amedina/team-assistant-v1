"""
Knowledge Graph Manager for Neo4j operations.
Handles entities, relationships, and graph queries derived from ingested data.
"""

import logging
import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import neo4j
from neo4j import AsyncGraphDatabase

from config.configuration import Neo4jConfig

logger = logging.getLogger(__name__)

@dataclass
class Entity:
    """Entity data structure for knowledge graph."""
    id: str
    type: str
    name: str
    properties: Dict[str, Any]
    source_chunks: List[str]  # UUIDs of chunks where this entity was found

@dataclass
class Relationship:
    """Relationship data structure for knowledge graph."""
    from_entity: str
    to_entity: str
    relationship_type: str
    properties: Dict[str, Any]
    source_chunks: List[str]  # UUIDs of chunks where this relationship was found

@dataclass
class GraphSearchResult:
    """Result from graph search query."""
    entities: List[Entity]
    relationships: List[Relationship]
    paths: List[Dict[str, Any]]

class KnowledgeGraphManager:
    """
    Manager for Neo4j Knowledge Graph operations.
    
    Responsibilities:
    - Managing entities and relationships
    - Graph queries and traversals
    - Batch processing with MERGE operations
    - Graph analytics and statistics
    """
    
    def __init__(self, config: Neo4jConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._driver: Optional[neo4j.AsyncDriver] = None
        
    async def initialize(self):
        """Initialize Neo4j driver and database schema."""
        try:
            # Create async driver
            self._driver = AsyncGraphDatabase.driver(
                self.config.uri,
                auth=(self.config.user, self.config.password),
                max_connection_lifetime=30 * 60,  # 30 minutes
                max_connection_pool_size=50,
                connection_acquisition_timeout=30
            )
            
            # Test connection
            await self.health_check()
            
            # Initialize schema
            await self._initialize_schema()
            
            self.logger.info("Knowledge Graph manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Knowledge Graph manager: {e}")
            raise
    
    @property
    def driver(self) -> neo4j.AsyncDriver:
        """Get Neo4j driver."""
        if self._driver is None:
            raise RuntimeError("Knowledge Graph manager not initialized. Call initialize() first.")
        return self._driver
    
    def _serialize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize properties for Neo4j storage.
        Neo4j only accepts primitive types or arrays of primitives.
        """
        serialized = {}
        
        for key, value in properties.items():
            if value is None:
                continue
            elif isinstance(value, (str, int, float, bool)):
                # Primitive types - store directly
                serialized[key] = value
            elif isinstance(value, list):
                # Arrays - check if all elements are primitives
                if all(isinstance(item, (str, int, float, bool, type(None))) for item in value):
                    serialized[key] = [item for item in value if item is not None]
                else:
                    # Complex array - serialize as JSON
                    serialized[f"{key}_json"] = json.dumps(value)
            elif isinstance(value, dict):
                # Nested object - serialize as JSON
                serialized[f"{key}_json"] = json.dumps(value)
            else:
                # Other types - convert to string
                serialized[key] = str(value)
        
        return serialized
    
    async def _initialize_schema(self):
        """Initialize Neo4j schema with constraints and indexes."""
        schema_queries = [
            # Constraints for uniqueness
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT chunk_uuid_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.uuid IS UNIQUE",
            
            # Indexes for performance
            "CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX chunk_source_idx IF NOT EXISTS FOR (c:Chunk) ON (c.source_id)",
            
            # Full-text search indexes
            "CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.description]",
        ]
        
        async with self.driver.session(database=self.config.database) as session:
            for query in schema_queries:
                try:
                    await session.run(query)
                except Exception as e:
                    # Constraint already exists - this is expected
                    if "already exists" not in str(e).lower():
                        self.logger.warning(f"Schema query failed: {query} - {e}")
            
            self.logger.info("Knowledge Graph schema initialized")
    
    async def upsert_entity(self, entity: Entity) -> bool:
        """
        Upsert a single entity.
        
        Args:
            entity: Entity to upsert
            
        Returns:
            True if successful
        """
        try:
            async with self.driver.session(database=self.config.database) as session:
                # Serialize properties for Neo4j compatibility
                serialized_properties = self._serialize_properties(entity.properties)
                
                # Build dynamic SET clause for properties
                set_clauses = ["e.type = $type", "e.name = $name", "e.source_chunks = $source_chunks", "e.updated_at = datetime()"]
                parameters = {
                    'id': entity.id,
                    'type': entity.type,
                    'name': entity.name,
                    'source_chunks': entity.source_chunks
                }
                
                # Add individual properties to the SET clause
                for key, value in serialized_properties.items():
                    set_clauses.append(f"e.{key} = ${key}")
                    parameters[key] = value
                
                query = f"""
                MERGE (e:Entity {{id: $id}})
                SET {', '.join(set_clauses)}
                RETURN e
                """
                
                await session.run(query, **parameters)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to upsert entity {entity.id}: {e}")
            return False
    
    async def batch_upsert_entities(self, entities: List[Entity]) -> Tuple[int, int]:
        """
        Batch upsert entities.
        
        Args:
            entities: List of entities to upsert
            
        Returns:
            Tuple of (successful_count, total_count)
        """
        if not entities:
            return 0, 0
        
        successful_count = 0
        batch_size = self.config.batch_size
        
        try:
            async with self.driver.session(database=self.config.database) as session:
                # Process in batches
                for i in range(0, len(entities), batch_size):
                    batch = entities[i:i + batch_size]
                    
                    # Prepare batch data
                    batch_data = []
                    for entity in batch:
                        # Serialize properties for Neo4j compatibility
                        serialized_properties = self._serialize_properties(entity.properties)
                        entity_data = {
                            'id': entity.id,
                            'type': entity.type,
                            'name': entity.name,
                            'source_chunks': entity.source_chunks
                        }
                        # Add serialized properties directly
                        entity_data.update(serialized_properties)
                        batch_data.append(entity_data)
                    
                    # Build dynamic SET clause for properties
                    # Get all unique property keys from batch
                    all_prop_keys = set()
                    for entity_data in batch_data:
                        for key in entity_data.keys():
                            if key not in ['id', 'type', 'name', 'source_chunks']:
                                all_prop_keys.add(key)
                    
                    # Build SET clauses
                    set_clauses = [
                        "e.type = entity.type",
                        "e.name = entity.name", 
                        "e.source_chunks = entity.source_chunks",
                        "e.updated_at = datetime()"
                    ]
                    
                    # Add property clauses
                    for prop_key in all_prop_keys:
                        set_clauses.append(f"e.{prop_key} = entity.{prop_key}")
                    
                    # Execute batch upsert
                    query = f"""
                    UNWIND $entities as entity
                    MERGE (e:Entity {{id: entity.id}})
                    SET {', '.join(set_clauses)}
                    """
                    
                    await session.run(query, entities=batch_data)
                    successful_count += len(batch)
                    
                    # Small delay between batches
                    await asyncio.sleep(0.1)
                
                self.logger.info(f"Batch upserted {successful_count} entities")
                
        except Exception as e:
            self.logger.error(f"Batch entity upsert failed: {e}")
            # Fallback to individual upserts
            successful_count = 0
            for entity in entities:
                if await self.upsert_entity(entity):
                    successful_count += 1
        
        return successful_count, len(entities)
    
    async def find_entities(self, 
                          entity_type: Optional[str] = None,
                          name_pattern: Optional[str] = None,
                          limit: int = 100) -> List[Entity]:
        """
        Find entities by various criteria.
        
        Args:
            entity_type: Filter by entity type
            name_pattern: Filter by name pattern (contains)
            limit: Maximum results to return
            
        Returns:
            List of Entity objects
        """
        try:
            conditions = []
            params = {'limit': limit}
            
            if entity_type:
                conditions.append("e.type = $entity_type")
                params['entity_type'] = entity_type
            
            if name_pattern:
                conditions.append("toLower(e.name) CONTAINS toLower($name_pattern)")
                params['name_pattern'] = name_pattern
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            query = f"""
            MATCH (e:Entity)
            {where_clause}
            RETURN e.id as id, e.type as type, e.name as name, 
                   e.properties as properties, e.source_chunks as source_chunks
            LIMIT $limit
            """
            
            async with self.driver.session(database=self.config.database) as session:
                result = await session.run(query, **params)
                records = await result.data()
                
                entities = []
                for record in records:
                    entity = Entity(
                        id=record['id'],
                        type=record['type'],
                        name=record['name'],
                        properties=record['properties'] or {},
                        source_chunks=record['source_chunks'] or []
                    )
                    entities.append(entity)
                
                return entities
                
        except Exception as e:
            self.logger.error(f"Failed to find entities: {e}")
            return []
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        try:
            async with self.driver.session(database=self.config.database) as session:
                stats = {}
                
                # Entity counts
                result = await session.run("MATCH (e:Entity) RETURN count(e) as count")
                record = await result.single()
                stats['total_entities'] = record['count'] if record else 0
                
                # Entity types
                result = await session.run("""
                    MATCH (e:Entity) 
                    RETURN e.type as type, count(e) as count 
                    ORDER BY count DESC
                """)
                records = await result.data()
                stats['entity_types'] = {r['type']: r['count'] for r in records}
                
                # Relationship counts
                result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
                record = await result.single()
                stats['total_relationships'] = record['count'] if record else 0
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get graph stats: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check Neo4j health."""
        try:
            async with self.driver.session(database=self.config.database) as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                return record['test'] == 1
                
        except Exception as e:
            self.logger.error(f"Knowledge Graph health check failed: {e}")
            return False
    
    async def close(self):
        """Close Neo4j driver."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self.logger.info("Neo4j driver closed") 