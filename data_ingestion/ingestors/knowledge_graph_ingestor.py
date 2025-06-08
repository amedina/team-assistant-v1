"""
Knowledge Graph Ingestor - specialized for Neo4j entity and relationship ingestion.

This component handles:
- Entity storage and deduplication
- Relationship creation and management
- Batch processing with MERGE operations
- Graph schema management
"""

import logging
import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
import neo4j

from config.configuration import Neo4jConfig
from ..models import Entity, Relationship, BatchOperationResult

logger = logging.getLogger(__name__)


class KnowledgeGraphIngestor:
    """
    Specialized component for knowledge graph ingestion operations.
    
    This class focuses purely on write operations:
    - Storing entities with properties
    - Creating relationships between entities
    - Batch processing with MERGE operations
    - Graph schema management and optimization
    - Deduplication and conflict resolution
    """
    
    def __init__(self, 
                 config: Neo4jConfig,
                 driver: neo4j.AsyncDriver):
        """
        Initialize KnowledgeGraphIngestor with shared Neo4j resources.
        
        Args:
            config: Neo4j configuration
            driver: Shared Neo4j async driver instance
        """
        self.config = config
        self.driver = driver
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Ingestion statistics
        self._total_entities_processed = 0
        self._total_entities_successful = 0
        self._total_relationships_processed = 0
        self._total_relationships_successful = 0
        self._batch_size = 50
    
    async def initialize(self) -> bool:
        """
        Initialize ingestor and ensure graph schema.
        
        Returns:
            True if initialization successful
        """
        try:
            # Test Neo4j connectivity
            async with self.driver.session(database=self.config.database) as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                if not record or record['test'] != 1:
                    raise RuntimeError("Neo4j connectivity test failed")
            
            # Ensure schema constraints and indexes
            await self._ensure_schema()
            
            self.logger.info("KnowledgeGraphIngestor initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize KnowledgeGraphIngestor: {e}")
            return False
    
    async def _ensure_schema(self):
        """Ensure necessary constraints and indexes exist."""
        schema_queries = [
            # Constraints for uniqueness
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT chunk_uuid_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.uuid IS UNIQUE",
            
            # Indexes for performance
            "CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
            "CREATE INDEX entity_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX chunk_source_idx IF NOT EXISTS FOR (c:Chunk) ON (c.source_id)",
        ]
        
        async with self.driver.session(database=self.config.database) as session:
            for query in schema_queries:
                try:
                    await session.run(query)
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        self.logger.warning(f"Schema query warning: {query} - {e}")
        
        self.logger.info("Graph schema ensured")
    
    def _serialize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize properties for Neo4j storage."""
        serialized = {}
        
        for key, value in properties.items():
            if value is None:
                continue
            elif isinstance(value, (str, int, float, bool)):
                serialized[key] = value
            elif isinstance(value, list):
                if all(isinstance(item, (str, int, float, bool, type(None))) for item in value):
                    serialized[key] = [item for item in value if item is not None]
                else:
                    serialized[f"{key}_json"] = json.dumps(value)
            elif isinstance(value, dict):
                serialized[f"{key}_json"] = json.dumps(value)
            else:
                serialized[key] = str(value)
        
        return serialized
    
    async def store_entity(self, entity: Entity) -> bool:
        """
        Store a single entity in the graph.
        
        Args:
            entity: Entity object to store
            
        Returns:
            True if successful
        """
        try:
            async with self.driver.session(database=self.config.database) as session:
                # Serialize properties for Neo4j compatibility
                serialized_properties = self._serialize_properties(entity.properties)
                
                # Build dynamic SET clause
                set_clauses = [
                    "e.entity_type = $entity_type",
                    "e.name = $name", 
                    "e.source_chunks = $source_chunks",
                    "e.updated_at = datetime()"
                ]
                
                parameters = {
                    'id': entity.id,
                    'entity_type': entity.entity_type.value,
                    'name': entity.name,
                    'source_chunks': [str(uuid) for uuid in entity.source_chunks]
                }
                
                # Add description if present
                if entity.description:
                    set_clauses.append("e.description = $description")
                    parameters['description'] = entity.description
                
                # Add confidence score if present
                if entity.confidence_score is not None:
                    set_clauses.append("e.confidence_score = $confidence_score")
                    parameters['confidence_score'] = entity.confidence_score
                
                # Add serialized properties
                for key, value in serialized_properties.items():
                    set_clauses.append(f"e.{key} = ${key}")
                    parameters[key] = value
                
                query = f"""
                MERGE (e:Entity {{id: $id}})
                SET {', '.join(set_clauses)}
                RETURN e
                """
                
                await session.run(query, parameters)
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to store entity {entity.id}: {e}")
            return False
    
    async def batch_store_entities(self, entities: List[Entity]) -> BatchOperationResult:
        """
        Store multiple entities in batch.
        
        Args:
            entities: List of Entity objects to store
            
        Returns:
            BatchOperationResult with operation statistics
        """
        start_time = datetime.now()
        
        if not entities:
            return BatchOperationResult(
                successful_count=0,
                total_count=0,
                processing_time_ms=0.0
            )
        
        try:
            self.logger.info(f"Starting batch storage of {len(entities)} entities")
            
            successful_count = 0
            validation_errors = []
            
            # Process in batches to avoid memory issues
            for i in range(0, len(entities), self._batch_size):
                batch = entities[i:i + self._batch_size]
                
                try:
                    batch_success = await self._batch_upsert_entities(batch)
                    successful_count += batch_success
                except Exception as e:
                    validation_errors.append(f"Batch {i//self._batch_size + 1}: {str(e)}")
                    continue
            
            # Update statistics
            self._total_entities_processed += len(entities)
            self._total_entities_successful += successful_count
            
            # Ensure successful_count doesn't exceed total_count
            successful_count = min(successful_count, len(entities))
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = BatchOperationResult(
                successful_count=successful_count,
                total_count=len(entities),
                failed_items=[f"Entity {i}" for i in range(len(entities)) if i >= successful_count],
                processing_time_ms=processing_time,
                error_messages=validation_errors
            )
            
            self.logger.info(f"Entity batch storage completed: {successful_count}/{len(entities)} successful")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Batch entity storage failed: {e}")
            
            return BatchOperationResult(
                successful_count=0,
                total_count=len(entities),
                processing_time_ms=processing_time,
                error_messages=[str(e)]
            )
    
    async def _batch_upsert_entities(self, entities: List[Entity]) -> int:
        """Perform optimized batch upsert of entities."""
        try:
            # Prepare batch data
            batch_data = []
            for entity in entities:
                serialized_properties = self._serialize_properties(entity.properties)
                entity_data = {
                    'id': entity.id,
                    'entity_type': entity.entity_type.value,
                    'name': entity.name,
                    'source_chunks': [str(uuid) for uuid in entity.source_chunks]
                }
                
                if entity.description:
                    entity_data['description'] = entity.description
                if entity.confidence_score is not None:
                    entity_data['confidence_score'] = entity.confidence_score
                
                entity_data.update(serialized_properties)
                batch_data.append(entity_data)
            
            # Build dynamic SET clause for all possible properties
            all_prop_keys = set()
            for entity_data in batch_data:
                all_prop_keys.update(entity_data.keys())
            
            set_clauses = [
                "e.entity_type = entity.entity_type",
                "e.name = entity.name",
                "e.source_chunks = entity.source_chunks",
                "e.updated_at = datetime()"
            ]
            
            # Add optional properties
            for prop_key in all_prop_keys:
                if prop_key not in ['id', 'entity_type', 'name', 'source_chunks']:
                    set_clauses.append(f"e.{prop_key} = entity.{prop_key}")
            
            query = f"""
            UNWIND $entities as entity
            MERGE (e:Entity {{id: entity.id}})
            SET {', '.join(set_clauses)}
            """
            
            async with self.driver.session(database=self.config.database) as session:
                await session.run(query, entities=batch_data)
            
            return len(entities)
            
        except Exception as e:
            self.logger.error(f"Batch entity upsert failed: {e}")
            # Fallback to individual storage
            successful_count = 0
            for entity in entities:
                if await self.store_entity(entity):
                    successful_count += 1
            return successful_count
    
    async def store_relationship(self, relationship: Relationship) -> bool:
        """
        Store a single relationship in the graph.
        
        Args:
            relationship: Relationship object to store
            
        Returns:
            True if successful
        """
        try:
            async with self.driver.session(database=self.config.database) as session:
                # Serialize properties
                serialized_properties = self._serialize_properties(relationship.properties)
                
                # Build relationship properties
                rel_properties = {
                    'relationship_type': relationship.relationship_type,
                    'source_chunks': [str(uuid) for uuid in relationship.source_chunks],
                    'created_at': 'datetime()'
                }
                
                if relationship.description:
                    rel_properties['description'] = relationship.description
                if relationship.confidence_score is not None:
                    rel_properties['confidence_score'] = relationship.confidence_score
                
                # Add serialized properties
                rel_properties.update(serialized_properties)
                
                # Build property assignment string
                prop_assignments = []
                parameters = {
                    'from_entity': relationship.from_entity,
                    'to_entity': relationship.to_entity
                }
                
                for key, value in rel_properties.items():
                    if key == 'created_at':
                        prop_assignments.append(f"r.{key} = {value}")
                    else:
                        prop_assignments.append(f"r.{key} = ${key}")
                        parameters[key] = value
                
                query = f"""
                MATCH (from:Entity {{id: $from_entity}})
                MATCH (to:Entity {{id: $to_entity}})
                MERGE (from)-[r:RELATES]->(to)
                SET {', '.join(prop_assignments)}
                RETURN r
                """
                
                await session.run(query, parameters)
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to store relationship {relationship.from_entity}->{relationship.to_entity}: {e}")
            return False
    
    async def batch_store_relationships(self, relationships: List[Relationship]) -> BatchOperationResult:
        """
        Store multiple relationships in batch.
        
        Args:
            relationships: List of Relationship objects to store
            
        Returns:
            BatchOperationResult with operation statistics
        """
        start_time = datetime.now()
        
        if not relationships:
            return BatchOperationResult(
                successful_count=0,
                total_count=0,
                processing_time_ms=0.0
            )
        
        try:
            self.logger.info(f"Starting batch storage of {len(relationships)} relationships")
            
            successful_count = 0
            validation_errors = []
            
            # Process in batches
            for i in range(0, len(relationships), self._batch_size):
                batch = relationships[i:i + self._batch_size]
                
                try:
                    batch_success = await self._batch_create_relationships(batch)
                    successful_count += batch_success
                except Exception as e:
                    validation_errors.append(f"Batch {i//self._batch_size + 1}: {str(e)}")
                    continue
            
            # Update statistics
            self._total_relationships_processed += len(relationships)
            self._total_relationships_successful += successful_count
            
            # Ensure successful_count doesn't exceed total_count
            successful_count = min(successful_count, len(relationships))
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = BatchOperationResult(
                successful_count=successful_count,
                total_count=len(relationships),
                processing_time_ms=processing_time,
                error_messages=validation_errors
            )
            
            self.logger.info(f"Relationship batch storage completed: {successful_count}/{len(relationships)} successful")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Batch relationship storage failed: {e}")
            
            return BatchOperationResult(
                successful_count=0,
                total_count=len(relationships),
                processing_time_ms=processing_time,
                error_messages=[str(e)]
            )
    
    async def _batch_create_relationships(self, relationships: List[Relationship]) -> int:
        """Perform optimized batch creation of relationships."""
        try:
            # Prepare batch data
            batch_data = []
            for rel in relationships:
                serialized_properties = self._serialize_properties(rel.properties)
                rel_data = {
                    'from_entity': rel.from_entity,
                    'to_entity': rel.to_entity,
                    'relationship_type': rel.relationship_type,
                    'source_chunks': [str(uuid) for uuid in rel.source_chunks]
                }
                
                if rel.description:
                    rel_data['description'] = rel.description
                if rel.confidence_score is not None:
                    rel_data['confidence_score'] = rel.confidence_score
                
                rel_data.update(serialized_properties)
                batch_data.append(rel_data)
            
            # Build property assignments
            all_prop_keys = set()
            for rel_data in batch_data:
                all_prop_keys.update(rel_data.keys())
            
            prop_assignments = []
            for prop_key in all_prop_keys:
                if prop_key not in ['from_entity', 'to_entity']:
                    prop_assignments.append(f"r.{prop_key} = rel.{prop_key}")
            
            prop_assignments.append("r.created_at = datetime()")
            
            query = f"""
            UNWIND $relationships as rel
            MATCH (from:Entity {{id: rel.from_entity}})
            MATCH (to:Entity {{id: rel.to_entity}})
            MERGE (from)-[r:RELATES]->(to)
            SET {', '.join(prop_assignments)}
            """
            
            async with self.driver.session(database=self.config.database) as session:
                await session.run(query, relationships=batch_data)
            
            return len(relationships)
            
        except Exception as e:
            self.logger.error(f"Batch relationship creation failed: {e}")
            # Fallback to individual storage
            successful_count = 0
            for relationship in relationships:
                if await self.store_relationship(relationship):
                    successful_count += 1
            return successful_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        return {
            "total_entities_processed": self._total_entities_processed,
            "total_entities_successful": self._total_entities_successful,
            "total_relationships_processed": self._total_relationships_processed,
            "total_relationships_successful": self._total_relationships_successful,
            "entity_success_rate": (
                self._total_entities_successful / self._total_entities_processed * 100
                if self._total_entities_processed > 0 else 0.0
            ),
            "relationship_success_rate": (
                self._total_relationships_successful / self._total_relationships_processed * 100
                if self._total_relationships_processed > 0 else 0.0
            ),
            "batch_size": self._batch_size
        }
    
    async def close(self):
        """Close ingestor and clean up resources."""
        self.logger.info(f"KnowledgeGraphIngestor closed. Final stats: {self.get_statistics()}") 