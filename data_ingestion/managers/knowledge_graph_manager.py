"""
Knowledge Graph Manager - Coordinator for Neo4j knowledge graph operations.
Implements the Manager-as-Coordinator pattern with shared resource management.

This component acts as a facade that:
- Manages shared Neo4j driver and database connections
- Coordinates between KnowledgeGraphIngestor and KnowledgeGraphRetriever  
- Provides unified interface for knowledge graph operations
- Handles schema initialization and health checks
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import neo4j
from neo4j import AsyncGraphDatabase

from config.configuration import Neo4jConfig
from data_ingestion.models.models import (
    Entity, Relationship, GraphContext, ComponentHealth, 
    EntityType, BatchOperationResult
)
from data_ingestion.ingestors.knowledge_graph_ingestor import KnowledgeGraphIngestor
from data_ingestion.retrievers.knowledge_graph_retriever import KnowledgeGraphRetriever

# Suppress Neo4j notifications and other verbose logging
logging.getLogger('neo4j.pool').setLevel(logging.WARNING)
logging.getLogger('neo4j.io').setLevel(logging.WARNING)
logging.getLogger('neo4j.notifications').setLevel(logging.WARNING)
logging.getLogger('neo4j').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class KnowledgeGraphManager:
    """
    Coordinator/Facade for Neo4j Knowledge Graph operations.
    
    Responsibilities:
    - Managing shared Neo4j driver and database connections
    - Coordinating between ingestor and retriever components
    - Providing unified interface for knowledge graph operations
    - Schema lifecycle management and health monitoring
    """
    
    def __init__(self, config: Neo4jConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Shared resources
        self._driver: Optional[neo4j.AsyncDriver] = None
        
        # Specialized components (initialized after shared resources)
        self.ingestor: Optional[KnowledgeGraphIngestor] = None
        self.retriever: Optional[KnowledgeGraphRetriever] = None
        
        # Manager state
        self._initialized = False
        
    async def initialize(self) -> bool:
        """
        Initialize shared Neo4j resources and component coordination.
        
        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing KnowledgeGraphManager and shared resources...")
            
            # Initialize shared resources
            await self._initialize_shared_resources()
            
            # Initialize specialized components with shared resources
            self.ingestor = KnowledgeGraphIngestor(
                config=self.config,
                driver=self._driver
            )
            
            self.retriever = KnowledgeGraphRetriever(
                config=self.config,
                driver=self._driver
            )
            
            # Initialize components
            ingestor_ready = await self.ingestor.initialize()
            retriever_ready = await self.retriever.initialize()
            
            self._initialized = ingestor_ready and retriever_ready
            
            if self._initialized:
                self.logger.info("KnowledgeGraphManager initialization completed successfully")
            else:
                self.logger.error("KnowledgeGraphManager initialization failed - components not ready")
            
            return self._initialized
            
        except Exception as e:
            self.logger.error(f"Failed to initialize KnowledgeGraphManager: {e}")
            return False
    
    async def _initialize_shared_resources(self):
        """Initialize shared Neo4j driver and database schema."""
        # Create async driver
        self._driver = AsyncGraphDatabase.driver(
            self.config.uri,
            auth=(self.config.user, self.config.password),
            max_connection_lifetime=30 * 60,  # 30 minutes
            max_connection_pool_size=50,
            connection_acquisition_timeout=30
        )
        
        # Test connection
        await self._test_connection()
        
        # Initialize schema
        await self._initialize_schema()
        
        self.logger.info("Shared Neo4j resources initialized successfully")
    
    async def _test_connection(self):
        """Test Neo4j connection."""
        async with self._driver.session(database=self.config.database) as session:
            result = await session.run("RETURN 1 as test")
            record = await result.single()
            if record['test'] != 1:
                raise RuntimeError("Neo4j connection test failed")
        
        self.logger.info("Neo4j connection test successful")
    
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
        
        async with self._driver.session(database=self.config.database) as session:
            for query in schema_queries:
                try:
                    await session.run(query)
                except Exception as e:
                    # Constraint already exists - this is expected
                    if "already exists" not in str(e).lower():
                        self.logger.warning(f"Schema query failed: {query} - {e}")
        
        self.logger.info("Knowledge Graph schema initialized")
    
    # =================================================================
    # INGESTION COORDINATION METHODS
    # =================================================================
    
    async def ingest_entity(self, entity: Entity) -> bool:
        """
        Coordinate entity ingestion through the ingestor component.
        
        Args:
            entity: Entity to store
            
        Returns:
            True if successful
        """
        if not self._initialized:
            raise RuntimeError("KnowledgeGraphManager not initialized. Call initialize() first.")
        
        return await self.ingestor.store_entity(entity)
    
    async def batch_ingest_entities(self, entities: List[Entity]) -> BatchOperationResult:
        """
        Coordinate batch entity ingestion through the ingestor component.
        
        Args:
            entities: List of entities to store
            
        Returns:
            BatchOperationResult with operation statistics
        """
        if not self._initialized:
            raise RuntimeError("KnowledgeGraphManager not initialized. Call initialize() first.")
        
        return await self.ingestor.batch_store_entities(entities)
    
    async def ingest_relationship(self, relationship: Relationship) -> bool:
        """
        Coordinate relationship ingestion through the ingestor component.
        
        Args:
            relationship: Relationship to store
            
        Returns:
            True if successful
        """
        if not self._initialized:
            raise RuntimeError("KnowledgeGraphManager not initialized. Call initialize() first.")
        
        return await self.ingestor.store_relationship(relationship)
    
    async def batch_ingest_relationships(self, relationships: List[Relationship]) -> BatchOperationResult:
        """
        Coordinate batch relationship ingestion through the ingestor component.
        
        Args:
            relationships: List of relationships to store
            
        Returns:
            BatchOperationResult with operation statistics
        """
        if not self._initialized:
            raise RuntimeError("KnowledgeGraphManager not initialized. Call initialize() first.")
        
        return await self.ingestor.batch_store_relationships(relationships)
    
    async def ingest_graph_data(self, 
                              entities: List[Entity], 
                              relationships: List[Relationship]) -> Dict[str, BatchOperationResult]:
        """
        Coordinate complete graph data ingestion through the ingestor component.
        
        Args:
            entities: List of entities to store
            relationships: List of relationships to store
            
        Returns:
            Dictionary with results for entities and relationships
        """
        if not self._initialized:
            raise RuntimeError("KnowledgeGraphManager not initialized. Call initialize() first.")
        
        results = {}
        
        # Ingest entities first
        if entities:
            results['entities'] = await self.ingestor.batch_store_entities(entities)
        
        # Then ingest relationships
        if relationships:
            results['relationships'] = await self.ingestor.batch_store_relationships(relationships)
        
        return results
    
    # =================================================================
    # RETRIEVAL COORDINATION METHODS
    # =================================================================
    
    async def find_entities(self, 
                          entity_type: Optional[EntityType] = None,
                          name_pattern: Optional[str] = None,
                          limit: int = 100) -> List[Entity]:
        """
        Coordinate entity search through the retriever component.
        
        Args:
            entity_type: Filter by entity type
            name_pattern: Filter by name pattern (contains)
            limit: Maximum results to return
            
        Returns:
            List of Entity objects
        """
        if not self._initialized:
            raise RuntimeError("KnowledgeGraphManager not initialized. Call initialize() first.")
        
        if name_pattern:
            # Use text-based search
            return await self.retriever.get_entities_by_query(name_pattern, [entity_type] if entity_type else None, limit)
        elif entity_type:
            # Use type-based search
            return await self.retriever.search_entities_by_type(entity_type, limit)
        else:
            # No specific criteria, return empty list
            self.logger.warning("No search criteria provided to find_entities")
            return []
    
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Coordinate single entity retrieval through the retriever component.
        
        Args:
            entity_id: ID of entity to retrieve
            
        Returns:
            Entity object or None if not found
        """
        if not self._initialized:
            raise RuntimeError("KnowledgeGraphManager not initialized. Call initialize() first.")
        
        entities = await self.retriever.get_entities_by_ids([entity_id])
        return entities[0] if entities else None
    
    async def find_relationships(self, 
                               from_entity: Optional[str] = None,
                               to_entity: Optional[str] = None,
                               relationship_type: Optional[str] = None,
                               limit: int = 100) -> List[Relationship]:
        """
        Coordinate relationship search through the retriever component.
        
        Args:
            from_entity: Filter by source entity ID
            to_entity: Filter by target entity ID
            relationship_type: Filter by relationship type
            limit: Maximum results to return
            
        Returns:
            List of Relationship objects
        """
        if not self._initialized:
            raise RuntimeError("KnowledgeGraphManager not initialized. Call initialize() first.")
        
        # Build entity IDs list based on filters
        entity_ids = []
        if from_entity:
            entity_ids.append(from_entity)
        if to_entity and to_entity != from_entity:
            entity_ids.append(to_entity)
        
        if not entity_ids:
            self.logger.warning("No entity filters provided to find_relationships")
            return []
        
        # Get relationships for the specified entities
        relationships = await self.retriever.get_relationships_for_entities(entity_ids, max_depth=1)
        
        # Apply additional filtering if needed
        filtered_relationships = []
        for rel in relationships:
            # Filter by from_entity if specified
            if from_entity and rel.from_entity != from_entity:
                continue
            
            # Filter by to_entity if specified
            if to_entity and rel.to_entity != to_entity:
                continue
            
            # Filter by relationship_type if specified
            if relationship_type and rel.relationship_type != relationship_type:
                continue
            
            filtered_relationships.append(rel)
            
            # Apply limit
            if len(filtered_relationships) >= limit:
                break
        
        return filtered_relationships
    
    async def get_entity_neighborhood(self, 
                                    entity_id: str,
                                    max_depth: int = 2,
                                    max_entities: int = 50) -> GraphContext:
        """
        Coordinate entity neighborhood retrieval through the retriever component.
        
        Args:
            entity_id: Central entity ID
            max_depth: Maximum traversal depth
            max_entities: Maximum entities to return
            
        Returns:
            GraphContext with entities and relationships
        """
        if not self._initialized:
            raise RuntimeError("KnowledgeGraphManager not initialized. Call initialize() first.")
        
        # Use contextual graph with the entity as the query focus
        entity = await self.get_entity(entity_id)
        if not entity:
            return GraphContext(
                query_entities=[],
                related_entities=[],
                relationships=[],
                entity_chunks_mapping={},
                graph_depth=max_depth,
                total_entities_found=0
            )
        
        # Use the entity name as query to get contextual graph
        return await self.retriever.get_contextual_graph(
            query=entity.name,
            chunk_uuids=entity.source_chunks,
            max_entities=max_entities,
            max_depth=max_depth
        )
    
    async def search_entities_by_text(self, 
                                    query: str,
                                    entity_types: Optional[List[EntityType]] = None,
                                    limit: int = 20) -> List[Entity]:
        """
        Coordinate text-based entity search through the retriever component.
        
        Args:
            query: Search query text
            entity_types: Optional filter by entity types
            limit: Maximum results to return
            
        Returns:
            List of Entity objects ranked by relevance
        """
        if not self._initialized:
            raise RuntimeError("KnowledgeGraphManager not initialized. Call initialize() first.")
        
        return await self.retriever.get_entities_by_query(query, entity_types, limit)
    
    async def get_graph_context_for_chunks(self, 
                                         chunk_uuids: List[str],
                                         max_depth: int = 1) -> GraphContext:
        """
        Coordinate graph context retrieval for specific chunks through the retriever component.
        
        Args:
            chunk_uuids: List of chunk UUIDs
            max_depth: Graph traversal depth
            
        Returns:
            GraphContext with relevant entities and relationships
        """
        if not self._initialized:
            raise RuntimeError("KnowledgeGraphManager not initialized. Call initialize() first.")
        
        # Convert string UUIDs to UUID objects
        from uuid import UUID
        uuid_objects = []
        for chunk_uuid in chunk_uuids:
            try:
                uuid_objects.append(UUID(chunk_uuid))
            except ValueError:
                self.logger.warning(f"Invalid UUID format: {chunk_uuid}")
                continue
        
        if not uuid_objects:
            return GraphContext(
                query_entities=[],
                related_entities=[],
                relationships=[],
                entity_chunks_mapping={},
                graph_depth=max_depth,
                total_entities_found=0
            )
        
        # Use contextual graph to get entities and relationships for these chunks
        return await self.retriever.get_contextual_graph(
            query="",  # Empty query since we're focusing on chunks
            chunk_uuids=uuid_objects,
            max_entities=50,
            max_depth=max_depth
        )
    
    # =================================================================
    # ANALYTICS AND MONITORING METHODS
    # =================================================================
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive graph statistics from retriever component.
        
        Returns:
            Dictionary with graph statistics
        """
        if not self._initialized:
            return {"error": "Manager not initialized"}
        
        return self.retriever.get_statistics()
    
    async def get_ingestion_statistics(self) -> Dict[str, Any]:
        """
        Get ingestion statistics from ingestor component.
        
        Returns:
            Dictionary with ingestion statistics
        """
        if not self._initialized:
            return {"error": "Manager not initialized"}
        
        return self.ingestor.get_statistics()
    
    async def health_check(self) -> ComponentHealth:
        """
        Coordinate comprehensive health check of knowledge graph system.
        
        Returns:
            ComponentHealth with overall system status
        """
        start_time = datetime.now()
        
        try:
            if not self._initialized:
                return ComponentHealth(
                    component_name="KnowledgeGraphManager",
                    is_healthy=False,
                    error_message="Manager not initialized"
                )
            
            # Check component health
            ingestor_health = await self.ingestor.health_check()
            retriever_health = await self.retriever.health_check()
            
            is_healthy = ingestor_health.is_healthy and retriever_health.is_healthy
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            additional_info = {
                "ingestor_healthy": ingestor_health.is_healthy,
                "retriever_healthy": retriever_health.is_healthy,
                "ingestor_stats": self.ingestor.get_statistics(),
                "retriever_stats": self.retriever.get_statistics()
            }
            
            return ComponentHealth(
                component_name="KnowledgeGraphManager",
                is_healthy=is_healthy,
                response_time_ms=response_time,
                additional_info=additional_info
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return ComponentHealth(
                component_name="KnowledgeGraphManager",
                is_healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics from all components.
        
        Returns:
            Dictionary with system statistics
        """
        if not self._initialized:
            return {"error": "Manager not initialized"}
        
        return {
            "manager_initialized": self._initialized,
            "ingestion_stats": self.ingestor.get_statistics(),
            "retrieval_stats": self.retriever.get_statistics(),
            "shared_resources": {
                "driver_initialized": self._driver is not None
            }
        }
    
    async def close(self):
        """Close manager and clean up Neo4j resources."""
        try:
            import warnings
            
            # Suppress aiohttp warnings during cleanup (even though Neo4j doesn't use aiohttp)
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*Unclosed client session.*")
                warnings.filterwarnings("ignore", message=".*Unclosed connector.*")
                
                if self.ingestor:
                    await self.ingestor.close()
                if self.retriever:
                    await self.retriever.close()
                
                if self._driver:
                    await self._driver.close()
                
                # Small delay for any cleanup operations
                import asyncio
                await asyncio.sleep(0.1)
            
            self._initialized = False
            self.logger.info("KnowledgeGraphManager closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during KnowledgeGraphManager cleanup: {e}") 