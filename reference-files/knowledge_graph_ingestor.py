import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import os
from neo4j import GraphDatabase, AsyncGraphDatabase
import json

logger = logging.getLogger(__name__)

class KnowledgeGraphIngestor:
    """Handles ingestion of entities and relationships into Neo4j knowledge graph."""
    
    def __init__(self, 
                 neo4j_uri: str,
                 neo4j_user: str = "neo4j",
                 neo4j_password: Optional[str] = None,
                 database: str = "neo4j",
                 batch_size: int = 100):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD")
        self.database = database
        self.batch_size = batch_size
        self.logger = logging.getLogger(__name__)
        self.driver = None
    
    async def connect(self) -> bool:
        """Establish connection to Neo4j database."""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            # Test connection
            async with self.driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
            
            self.logger.info("Successfully connected to Neo4j database")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Neo4j: {str(e)}")
            return False
    
    async def disconnect(self) -> None:
        """Close the Neo4j connection."""
        if self.driver:
            await self.driver.close()
            self.driver = None
    
    async def ingest_knowledge_graph(self, processed_document: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest entities and relationships from processed document."""
        try:
            if not self.driver:
                await self.connect()
            
            entities = processed_document.get("entities", [])
            relationships = processed_document.get("relationships", [])
            
            if not entities and not relationships:
                return {"status": "skipped", "reason": "no_kg_data", "ingested_entities": 0, "ingested_relationships": 0}
            
            # Ingest entities in batches
            total_entities = 0
            if entities:
                entity_results = await self._ingest_entities_batch(entities)
                total_entities = sum(result.get("ingested_count", 0) for result in entity_results)
            
            # Ingest relationships in batches
            total_relationships = 0
            if relationships:
                rel_results = await self._ingest_relationships_batch(relationships)
                total_relationships = sum(result.get("ingested_count", 0) for result in rel_results)
            
            return {
                "status": "success",
                "document_id": processed_document["document_id"],
                "total_entities": len(entities),
                "total_relationships": len(relationships),
                "ingested_entities": total_entities,
                "ingested_relationships": total_relationships,
                "ingested_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error ingesting knowledge graph for document {processed_document.get('document_id')}: {str(e)}")
            return {
                "status": "error",
                "document_id": processed_document.get("document_id"),
                "error": str(e),
                "ingested_entities": 0,
                "ingested_relationships": 0
            }
    
    async def _ingest_entities_batch(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ingest entities in batches."""
        results = []
        
        for i in range(0, len(entities), self.batch_size):
            batch = entities[i:i + self.batch_size]
            try:
                result = await self._create_entities(batch)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error ingesting entity batch {i}: {str(e)}")
                results.append({"status": "error", "error": str(e), "ingested_count": 0})
        
        return results
    
    async def _ingest_relationships_batch(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ingest relationships in batches."""
        results = []
        
        for i in range(0, len(relationships), self.batch_size):
            batch = relationships[i:i + self.batch_size]
            try:
                result = await self._create_relationships(batch)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error ingesting relationship batch {i}: {str(e)}")
                results.append({"status": "error", "error": str(e), "ingested_count": 0})
        
        return results
    
    async def _create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create entities in Neo4j."""
        try:
            async with self.driver.session(database=self.database) as session:
                # Create entities with MERGE to avoid duplicates
                query = """
                UNWIND $entities AS entity
                CALL apoc.merge.node([entity.entity_type], {id: entity.entity_id}, 
                    {
                        name: entity.name,
                        source_document_id: entity.source_document_id,
                        created_at: datetime(),
                        updated_at: datetime()
                    },
                    {
                        name: entity.name,
                        properties: entity.properties,
                        updated_at: datetime()
                    }
                ) YIELD node
                RETURN count(node) as created_count
                """
                
                result = await session.run(query, entities=entities)
                record = await result.single()
                created_count = record["created_count"] if record else 0
                
                return {
                    "status": "success",
                    "ingested_count": created_count,
                    "batch_size": len(entities)
                }
                
        except Exception as e:
            # Fallback to simpler query if APOC is not available
            return await self._create_entities_simple(entities)
    
    async def _create_entities_simple(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create entities using simple Cypher without APOC."""
        try:
            async with self.driver.session(database=self.database) as session:
                created_count = 0
                
                for entity in entities:
                    # Use dynamic label based on entity type
                    query = f"""
                    MERGE (e:{entity['entity_type']} {{id: $entity_id}})
                    ON CREATE SET 
                        e.name = $name,
                        e.source_document_id = $source_document_id,
                        e.properties = $properties,
                        e.created_at = datetime(),
                        e.updated_at = datetime()
                    ON MATCH SET
                        e.name = $name,
                        e.properties = $properties,
                        e.updated_at = datetime()
                    RETURN e
                    """
                    
                    result = await session.run(query,
                        entity_id=entity["entity_id"],
                        name=entity["name"],
                        source_document_id=entity["source_document_id"],
                        properties=json.dumps(entity["properties"])
                    )
                    
                    if await result.single():
                        created_count += 1
                
                return {
                    "status": "success",
                    "ingested_count": created_count,
                    "batch_size": len(entities)
                }
                
        except Exception as e:
            self.logger.error(f"Error creating entities: {str(e)}")
            raise
    
    async def _create_relationships(self, relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create relationships in Neo4j."""
        try:
            async with self.driver.session(database=self.database) as session:
                created_count = 0
                
                for rel in relationships:
                    # Create relationship with dynamic type
                    query = f"""
                    MATCH (source {{id: $source_id}})
                    MATCH (target {{id: $target_id}})
                    MERGE (source)-[r:{rel['relationship_type']} {{id: $rel_id}}]->(target)
                    ON CREATE SET 
                        r.properties = $properties,
                        r.source_document_id = $source_document_id,
                        r.created_at = datetime(),
                        r.updated_at = datetime()
                    ON MATCH SET
                        r.properties = $properties,
                        r.updated_at = datetime()
                    RETURN r
                    """
                    
                    result = await session.run(query,
                        source_id=rel["source_entity_id"],
                        target_id=rel["target_entity_id"],
                        rel_id=rel["relationship_id"],
                        properties=json.dumps(rel["properties"]),
                        source_document_id=rel["source_document_id"]
                    )
                    
                    if await result.single():
                        created_count += 1
                
                return {
                    "status": "success",
                    "ingested_count": created_count,
                    "batch_size": len(relationships)
                }
                
        except Exception as e:
            self.logger.error(f"Error creating relationships: {str(e)}")
            raise
    
    async def query_knowledge_graph(self, 
                                  query: str, 
                                  parameters: Optional[Dict[str, Any]] = None,
                                  limit: int = 100) -> List[Dict[str, Any]]:
        """Execute a Cypher query against the knowledge graph."""
        try:
            if not self.driver:
                await self.connect()
            
            async with self.driver.session(database=self.database) as session:
                result = await session.run(query, parameters or {})
                records = []
                
                async for record in result:
                    # Convert Neo4j record to dictionary
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        # Handle Neo4j node/relationship objects
                        if hasattr(value, 'items'):
                            record_dict[key] = dict(value.items())
                        elif hasattr(value, '__dict__'):
                            record_dict[key] = value.__dict__
                        else:
                            record_dict[key] = value
                    
                    records.append(record_dict)
                    
                    if len(records) >= limit:
                        break
                
                return records
                
        except Exception as e:
            self.logger.error(f"Error querying knowledge graph: {str(e)}")
            raise
    
    async def find_related_entities(self, 
                                  entity_id: str, 
                                  relationship_types: Optional[List[str]] = None,
                                  max_depth: int = 2) -> List[Dict[str, Any]]:
        """Find entities related to a given entity."""
        try:
            rel_filter = ""
            if relationship_types:
                rel_types = "|".join(relationship_types)
                rel_filter = f":{rel_types}"
            
            query = f"""
            MATCH path = (start {{id: $entity_id}})-[r{rel_filter}*1..{max_depth}]-(related)
            RETURN DISTINCT related, r, length(path) as distance
            ORDER BY distance
            LIMIT 50
            """
            
            results = await self.query_knowledge_graph(query, {"entity_id": entity_id})
            return results
            
        except Exception as e:
            self.logger.error(f"Error finding related entities: {str(e)}")
            raise
    
    async def get_document_context(self, document_id: str) -> Dict[str, Any]:
        """Get all knowledge graph context for a specific document."""
        try:
            query = """
            MATCH (doc:Document {id: $doc_id})
            OPTIONAL MATCH (doc)-[r1]-(related1)
            OPTIONAL MATCH (related1)-[r2]-(related2)
            WHERE related2.source_document_id = $doc_id OR related2 IS NULL
            RETURN doc, 
                   collect(DISTINCT {entity: related1, relationship: r1}) as direct_relations,
                   collect(DISTINCT {entity: related2, relationship: r2}) as indirect_relations
            """
            
            results = await self.query_knowledge_graph(query, {"doc_id": f"doc:{document_id}"})
            
            if results:
                return {
                    "document": results[0].get("doc", {}),
                    "direct_relations": results[0].get("direct_relations", []),
                    "indirect_relations": results[0].get("indirect_relations", []),
                    "total_relations": len(results[0].get("direct_relations", [])) + len(results[0].get("indirect_relations", []))
                }
            else:
                return {"document": None, "direct_relations": [], "indirect_relations": [], "total_relations": 0}
                
        except Exception as e:
            self.logger.error(f"Error getting document context: {str(e)}")
            raise
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        try:
            if not self.driver:
                await self.connect()
            
            stats_queries = {
                "total_nodes": "MATCH (n) RETURN count(n) as count",
                "total_relationships": "MATCH ()-[r]->() RETURN count(r) as count",
                "node_types": "MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC",
                "relationship_types": "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC",
                "documents_count": "MATCH (n:Document) RETURN count(n) as count"
            }
            
            stats = {}
            async with self.driver.session(database=self.database) as session:
                for stat_name, query in stats_queries.items():
                    try:
                        result = await session.run(query)
                        if stat_name in ["node_types", "relationship_types"]:
                            stats[stat_name] = [dict(record) async for record in result]
                        else:
                            record = await result.single()
                            stats[stat_name] = record["count"] if record else 0
                    except Exception as e:
                        stats[stat_name] = f"Error: {str(e)}"
            
            return {
                "database": self.database,
                "statistics": stats,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting graph stats: {str(e)}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the Neo4j connection and database."""
        try:
            if not self.driver:
                await self.connect()
            
            async with self.driver.session(database=self.database) as session:
                # Test basic connectivity
                result = await session.run("RETURN 1 as test")
                test_result = await result.single()
                
                # Get database info
                db_result = await session.run("CALL dbms.components() YIELD name, versions, edition")
                components = [dict(record) async for record in db_result]
                
                # Get basic stats
                stats = await self.get_graph_stats()
                
                return {
                    "status": "healthy",
                    "connection": "active",
                    "database": self.database,
                    "components": components,
                    "statistics": stats.get("statistics", {}),
                    "checked_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed",
                "checked_at": datetime.now().isoformat()
            }
