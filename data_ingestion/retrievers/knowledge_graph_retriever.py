"""
Knowledge Graph Retriever - specialized for Neo4j entity and relationship retrieval.

This component handles:
- Entity retrieval by various criteria
- Relationship traversal and discovery
- Graph context assembly for queries
- Entity-chunk mapping for retrieval integration
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import neo4j
from uuid import UUID

from app.config.configuration import Neo4jConfig
from ..models import Entity, Relationship, GraphContext, ComponentHealth, EntityType

logger = logging.getLogger(__name__)


class KnowledgeGraphRetriever:
    """
    Specialized component for knowledge graph retrieval operations.
    
    This class focuses purely on read operations:
    - Finding entities by name, type, or properties
    - Traversing relationships and discovering connections
    - Building contextual subgraphs for queries
    - Mapping entities to source chunks
    - Graph analytics and insights
    """
    
    def __init__(self, 
                 config: Neo4jConfig,
                 driver: neo4j.AsyncDriver):
        """
        Initialize KnowledgeGraphRetriever with shared Neo4j resources.
        
        Args:
            config: Neo4j configuration
            driver: Shared Neo4j async driver instance
        """
        self.config = config
        self.driver = driver
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Retrieval statistics
        self._total_queries = 0
        self._total_entities_retrieved = 0
        self._total_relationships_retrieved = 0
        self._average_response_time_ms = 0.0
    
    async def initialize(self) -> bool:
        """
        Initialize retriever and validate graph connectivity.
        
        Returns:
            True if initialization successful
        """
        try:
            async with self.driver.session(database=self.config.database) as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                if record and record['test'] == 1:
                    # Count entities
                    count_result = await session.run("MATCH (e:Entity) RETURN count(e) as count")
                    count_record = await count_result.single()
                    entity_count = count_record['count'] if count_record else 0
                    self.logger.info(f"KnowledgeGraphRetriever initialized. Found {entity_count} entities.")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False
    
    async def get_entities_by_query(self, 
                                  query: str, 
                                  entity_types: Optional[List[EntityType]] = None,
                                  limit: int = 20) -> List[Entity]:
        """
        Find entities by query string using text matching.
        
        Args:
            query: Search query string
            entity_types: Optional list of entity types to filter
            limit: Maximum number of entities to return
            
        Returns:
            List of Entity objects matching the query
        """
        start_time = datetime.now()
        
        if not query or not query.strip():
            return []
        
        try:
            # Build query conditions
            conditions = ["toLower(e.name) CONTAINS toLower($query)"]
            parameters = {"query": query.strip(), "limit": limit}
            
            if entity_types:
                type_values = [et.value for et in entity_types]
                conditions.append("e.entity_type IN $entity_types")
                parameters["entity_types"] = type_values
            
            where_clause = " AND ".join(conditions)
            
            cypher_query = f"""
            MATCH (e:Entity)
            WHERE {where_clause}
            RETURN e.id as id, e.entity_type as entity_type, e.name as name,
                   e.description as description, e.source_chunks as source_chunks,
                   COALESCE(e.confidence_score, 1.0) as confidence_score
            ORDER BY e.name
            LIMIT $limit
            """
            
            async with self.driver.session(database=self.config.database) as session:
                result = await session.run(cypher_query, parameters)
                records = await result.data()
                
                entities = []
                for record in records:
                    # Convert source_chunks to UUIDs
                    source_chunks = []
                    if record['source_chunks']:
                        for chunk_str in record['source_chunks']:
                            try:
                                source_chunks.append(UUID(chunk_str))
                            except ValueError:
                                continue
                    
                    # Handle entity_type conversion safely
                    try:
                        entity_type = EntityType(record['entity_type'])
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid entity type '{record['entity_type']}' for entity {record['id']}")
                        continue
                    
                    entity = Entity(
                        id=record['id'],
                        entity_type=entity_type,
                        name=record['name'],
                        description=record['description'],
                        properties={},  # Properties not fetched in basic query for performance
                        source_chunks=source_chunks,
                        confidence_score=record['confidence_score']
                    )
                    entities.append(entity)
                
                # Update statistics
                self._total_queries += 1
                self._total_entities_retrieved += len(entities)
                
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                self._update_average_response_time(response_time)
                
                self.logger.debug(f"Retrieved {len(entities)} entities for query '{query}' in {response_time:.1f}ms")
                return entities
                
        except Exception as e:
            self.logger.error(f"Failed to get entities by query '{query}': {e}")
            return []
    
    async def get_entities_by_ids(self, entity_ids: List[str]) -> List[Entity]:
        """
        Retrieve entities by their IDs.
        
        Args:
            entity_ids: List of entity ID strings
            
        Returns:
            List of Entity objects
        """
        if not entity_ids:
            return []
        
        try:
            async with self.driver.session(database=self.config.database) as session:
                result = await session.run("""
                    MATCH (e:Entity)
                    WHERE e.id IN $entity_ids
                    RETURN e.id as id, e.entity_type as entity_type, e.name as name,
                           e.description as description, e.source_chunks as source_chunks,
                           COALESCE(e.confidence_score, 1.0) as confidence_score
                """, entity_ids=entity_ids)
                
                records = await result.data()
                
                entities = []
                for record in records:
                    source_chunks = []
                    if record['source_chunks']:
                        for chunk_str in record['source_chunks']:
                            try:
                                source_chunks.append(UUID(chunk_str))
                            except ValueError:
                                continue
                    
                    # Handle entity_type conversion safely
                    try:
                        entity_type = EntityType(record['entity_type'])
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid entity type '{record['entity_type']}' for entity {record['id']}")
                        continue
                    
                    entity = Entity(
                        id=record['id'],
                        entity_type=entity_type,
                        name=record['name'],
                        description=record['description'],
                        properties={},
                        source_chunks=source_chunks,
                        confidence_score=record['confidence_score']
                    )
                    entities.append(entity)
                
                return entities
                
        except Exception as e:
            self.logger.error(f"Failed to get entities by IDs: {e}")
            return []
    
    async def get_entities_for_chunks(self, chunk_uuids: List[UUID]) -> Dict[str, List[Entity]]:
        """
        Get entities that are associated with specific chunks.
        
        Args:
            chunk_uuids: List of chunk UUIDs
            
        Returns:
            Dictionary mapping chunk UUID strings to lists of entities
        """
        if not chunk_uuids:
            return {}
        
        try:
            chunk_strings = [str(uuid) for uuid in chunk_uuids]
            
            async with self.driver.session(database=self.config.database) as session:
                result = await session.run("""
                    MATCH (e:Entity)
                    WHERE ANY(chunk IN e.source_chunks WHERE chunk IN $chunk_uuids)
                    RETURN e.id as id, e.entity_type as entity_type, e.name as name,
                           e.description as description, e.source_chunks as source_chunks,
                           COALESCE(e.confidence_score, 1.0) as confidence_score
                """, chunk_uuids=chunk_strings)
                
                records = await result.data()
                
                # Build mapping from chunk UUIDs to entities
                chunk_entity_map = {str(uuid): [] for uuid in chunk_uuids}
                
                for record in records:
                    source_chunks = []
                    if record['source_chunks']:
                        for chunk_str in record['source_chunks']:
                            try:
                                source_chunks.append(UUID(chunk_str))
                            except ValueError:
                                continue
                    
                    # Handle entity_type conversion safely
                    try:
                        entity_type = EntityType(record['entity_type'])
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid entity type '{record['entity_type']}' for entity {record['id']}")
                        continue
                    
                    entity = Entity(
                        id=record['id'],
                        entity_type=entity_type,
                        name=record['name'],
                        description=record['description'],
                        properties={},
                        source_chunks=source_chunks,
                        confidence_score=record['confidence_score']
                    )
                    
                    # Add entity to all chunks it's associated with
                    for chunk_uuid in entity.source_chunks:
                        chunk_str = str(chunk_uuid)
                        if chunk_str in chunk_entity_map:
                            chunk_entity_map[chunk_str].append(entity)
                
                return chunk_entity_map
                
        except Exception as e:
            self.logger.error(f"Failed to get entities for chunks: {e}")
            return {}
    
    async def get_relationships_for_entities(self, 
                                           entity_ids: List[str],
                                           max_depth: int = 1) -> List[Relationship]:
        """
        Get relationships involving specific entities.
        
        Args:
            entity_ids: List of entity IDs
            max_depth: Maximum relationship depth to traverse
            
        Returns:
            List of Relationship objects
        """
        if not entity_ids or max_depth <= 0:
            return []
        
        try:
            # Build depth-aware query
            if max_depth == 1:
                relationship_pattern = "[r:RELATES]"
            else:
                relationship_pattern = f"[r:RELATES*1..{max_depth}]"
            
            async with self.driver.session(database=self.config.database) as session:
                result = await session.run(f"""
                    MATCH (from:Entity)-{relationship_pattern}-(to:Entity)
                    WHERE from.id IN $entity_ids OR to.id IN $entity_ids
                    RETURN from.id as from_entity, to.id as to_entity,
                           r.relationship_type as relationship_type,
                           r.description as description,
                           r.source_chunks as source_chunks,
                           COALESCE(r.confidence_score, 1.0) as confidence_score
                """, entity_ids=entity_ids)
                
                records = await result.data()
                
                relationships = []
                for record in records:
                    source_chunks = []
                    if record['source_chunks']:
                        for chunk_str in record['source_chunks']:
                            try:
                                source_chunks.append(UUID(chunk_str))
                            except ValueError:
                                continue
                    
                    relationship = Relationship(
                        from_entity=record['from_entity'],
                        to_entity=record['to_entity'],
                        relationship_type=record['relationship_type'] or "RELATES",
                        description=record['description'],
                        properties={},
                        source_chunks=source_chunks,
                        confidence_score=record['confidence_score']
                    )
                    relationships.append(relationship)
                
                self._total_relationships_retrieved += len(relationships)
                return relationships
                
        except Exception as e:
            self.logger.error(f"Failed to get relationships for entities: {e}")
            return []
    
    async def get_contextual_graph(self, 
                                 query: str, 
                                 chunk_uuids: List[UUID],
                                 max_entities: int = 10,
                                 max_depth: int = 2) -> GraphContext:
        """
        Build a contextual subgraph for a query and related chunks.
        
        Args:
            query: Search query string
            chunk_uuids: List of relevant chunk UUIDs
            max_entities: Maximum entities to include
            max_depth: Maximum relationship depth
            
        Returns:
            GraphContext with relevant entities and relationships
        """
        try:
            # Find entities related to the query
            query_entities = await self.get_entities_by_query(query, limit=max_entities // 2)
            
            # Find entities related to the chunks
            chunk_entity_map = await self.get_entities_for_chunks(chunk_uuids)
            chunk_entities = []
            for entities_list in chunk_entity_map.values():
                chunk_entities.extend(entities_list)
            
            # Deduplicate entities
            all_entities = query_entities + chunk_entities
            unique_entities = {entity.id: entity for entity in all_entities}.values()
            limited_entities = list(unique_entities)[:max_entities]
            
            # Get relationships between these entities
            entity_ids = [entity.id for entity in limited_entities]
            relationships = await self.get_relationships_for_entities(entity_ids, max_depth)
            
            # Build entity-chunks mapping
            entity_chunks_mapping = {}
            for chunk_str, entities_list in chunk_entity_map.items():
                for entity in entities_list:
                    if entity.id not in entity_chunks_mapping:
                        entity_chunks_mapping[entity.id] = []
                    entity_chunks_mapping[entity.id].append(UUID(chunk_str))
            
            # Separate query entities from chunk entities
            query_entity_ids = {entity.id for entity in query_entities}
            final_query_entities = [e for e in limited_entities if e.id in query_entity_ids]
            final_related_entities = [e for e in limited_entities if e.id not in query_entity_ids]
            
            return GraphContext(
                query_entities=final_query_entities,
                related_entities=final_related_entities,
                relationships=relationships,
                entity_chunks_mapping=entity_chunks_mapping,
                graph_depth=max_depth,
                total_entities_found=len(limited_entities)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get contextual graph: {e}")
            return GraphContext(
                query_entities=[],
                related_entities=[],
                relationships=[],
                entity_chunks_mapping={},
                graph_depth=max_depth,
                total_entities_found=0
            )
    
    async def search_entities_by_type(self, 
                                    entity_type: EntityType,
                                    limit: int = 50) -> List[Entity]:
        """
        Search entities by specific type.
        
        Args:
            entity_type: Type of entities to search for
            limit: Maximum number of entities to return
            
        Returns:
            List of Entity objects of the specified type
        """
        try:
            async with self.driver.session(database=self.config.database) as session:
                result = await session.run("""
                    MATCH (e:Entity)
                    WHERE e.entity_type = $entity_type
                    RETURN e.id as id, e.entity_type as entity_type, e.name as name,
                           e.description as description, e.source_chunks as source_chunks,
                           COALESCE(e.confidence_score, 1.0) as confidence_score
                    ORDER BY COALESCE(e.confidence_score, 1.0) DESC, e.name
                    LIMIT $limit
                """, entity_type=entity_type.value, limit=limit)
                
                records = await result.data()
                
                entities = []
                for record in records:
                    source_chunks = []
                    if record['source_chunks']:
                        for chunk_str in record['source_chunks']:
                            try:
                                source_chunks.append(UUID(chunk_str))
                            except ValueError:
                                continue
                    
                    # Handle entity_type conversion safely
                    try:
                        entity_type_val = EntityType(record['entity_type'])
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid entity type '{record['entity_type']}' for entity {record['id']}")
                        continue
                    
                    entity = Entity(
                        id=record['id'],
                        entity_type=entity_type_val,
                        name=record['name'],
                        description=record['description'],
                        properties={},
                        source_chunks=source_chunks,
                        confidence_score=record['confidence_score']
                    )
                    entities.append(entity)
                
                return entities
                
        except Exception as e:
            self.logger.error(f"Failed to search entities by type {entity_type}: {e}")
            return []
    
    def _update_average_response_time(self, response_time_ms: float):
        """Update the running average response time."""
        if self._total_queries == 1:
            self._average_response_time_ms = response_time_ms
        else:
            alpha = 0.1
            self._average_response_time_ms = (
                alpha * response_time_ms + 
                (1 - alpha) * self._average_response_time_ms
            )
    
    async def health_check(self) -> ComponentHealth:
        """
        Check retriever health and performance.
        
        Returns:
            ComponentHealth with retriever status
        """
        start_time = datetime.now()
        
        try:
            # Test Neo4j connectivity and data availability
            async with self.driver.session(database=self.config.database) as session:
                result = await session.run("MATCH (e:Entity) RETURN count(e) as count LIMIT 1")
                record = await result.single()
                entity_count = record['count'] if record else 0
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ComponentHealth(
                component_name="KnowledgeGraphRetriever",
                is_healthy=True,
                response_time_ms=response_time,
                additional_info={
                    "total_queries": self._total_queries,
                    "average_response_time_ms": self._average_response_time_ms,
                    "total_entities_retrieved": self._total_entities_retrieved,
                    "total_relationships_retrieved": self._total_relationships_retrieved,
                    "entities_in_graph": entity_count
                }
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return ComponentHealth(
                component_name="KnowledgeGraphRetriever",
                is_healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {
            "total_queries": self._total_queries,
            "total_entities_retrieved": self._total_entities_retrieved,
            "total_relationships_retrieved": self._total_relationships_retrieved,
            "average_response_time_ms": self._average_response_time_ms,
            "average_entities_per_query": (
                self._total_entities_retrieved / self._total_queries 
                if self._total_queries > 0 else 0.0
            ),
            "average_relationships_per_query": (
                self._total_relationships_retrieved / self._total_queries 
                if self._total_queries > 0 else 0.0
            )
        }
    
    async def close(self):
        """Close retriever and clean up resources."""
        self.logger.info(f"KnowledgeGraphRetriever closed. Final stats: {self.get_statistics()}") 