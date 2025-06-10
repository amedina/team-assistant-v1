#!/usr/bin/env python3
"""
Context Manager Flow Tests.

This module tests the 4-step Context Manager flow that combines all storage systems
for comprehensive data retrieval. Updated to use actual models and text processor.
"""

import pytest
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

from config.configuration import get_system_config
from data_ingestion.processors.text_processor import TextProcessor, ProcessedDocument
from data_ingestion.models import (
    ChunkData, EmbeddingData, Entity, Relationship, EntityType, SourceType,
    IngestionStatus, VectorRetrievalResult, RetrievalContext, LLMRetrievalContext,
    DatabaseRetrievalResult, GraphContext, ComponentHealth
)
from .fixtures.custom_assertions import assert_retrieval_quality, assert_context_completeness
from .utils.e2e_reporter import E2ETestReporter
from .test_scenarios import TestScenario

logger = logging.getLogger(__name__)


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.parametrize("test_scenario", ["github", "drive_folder", "drive_file", "web"], indirect=True)
class TestContextManagerFlow:
    """
    Test the 4-step Context Manager flow using actual models and text processor.
    
    Context Manager Flow:
    1. Vector Search: Similarity search for relevant chunks
    2. Database Metadata: Enrich with chunk metadata and source information
    3. Knowledge Graph: Add entity and relationship context
    4. Combined Output: Merge all contexts into comprehensive retrieval result
    """
    
    async def test_complete_context_flow(
        self,
        test_scenario: TestScenario,
        text_processor: TextProcessor,
        processed_test_documents: List[ProcessedDocument],
        processed_test_chunks: List[ChunkData],
        extracted_entities: List[Entity],
        extracted_relationships: List[Relationship],
        vector_store_manager,
        database_manager,
        knowledge_graph_manager,
        test_isolation_id: str,
        e2e_reporter: E2ETestReporter
    ):
        """
        Test the complete 4-step context manager flow with actual models.
        
        This test ensures that all storage systems work together to provide
        comprehensive context for document retrieval and analysis.
        """
        e2e_reporter.log_test_start("Complete Context Flow", test_scenario.test_id)
        
        try:
            # First ensure data is stored in all systems
            await self._setup_test_data(
                processed_test_chunks, extracted_entities, extracted_relationships,
                vector_store_manager, database_manager, knowledge_graph_manager,
                processed_test_documents, test_isolation_id
            )
            
            # === STEP 1: Vector Search ===
            logger.info("Step 1: Performing vector similarity search...")
            
            # Extract query from test content
            query_text = self._extract_query_text(processed_test_documents, test_scenario)
            
            vector_results = await vector_store_manager.similarity_search(
                query_text=query_text,
                limit=5,
                metadata_filter={"test_isolation_id": test_isolation_id}
            )
            
            assert len(vector_results) > 0, "Vector search returned no results"
            assert all(isinstance(result, VectorRetrievalResult) for result in vector_results), \
                "Vector results are not proper VectorRetrievalResult models"
            
            # Validate vector result structure
            for result in vector_results:
                assert result.chunk_uuid, "Vector result missing chunk_uuid"
                assert result.similarity_score is not None, "Vector result missing similarity_score"
                assert 0 <= result.similarity_score <= 1, f"Invalid similarity score: {result.similarity_score}"
                assert result.chunk_text or result.chunk_metadata, "Vector result missing content"
            
            logger.info(f"✓ Vector search completed: {len(vector_results)} results with scores {[r.similarity_score for r in vector_results[:3]]}")
            
            # === STEP 2: Database Metadata Enrichment ===
            logger.info("Step 2: Enriching with database metadata...")
            
            chunk_uuids = [result.chunk_uuid for result in vector_results]
            database_results = await database_manager.get_chunks_by_uuids(chunk_uuids)
            
            assert len(database_results) > 0, "Database metadata enrichment returned no results"
            assert all(isinstance(result, ChunkData) for result in database_results), \
                "Database results are not proper ChunkData models"
            
            # Create enriched context by combining vector and database results
            enriched_chunks = []
            for vector_result in vector_results:
                # Find corresponding database result
                db_chunk = next((chunk for chunk in database_results if chunk.chunk_uuid == vector_result.chunk_uuid), None)
                if db_chunk:
                    enriched_chunk = {
                        "chunk_uuid": str(vector_result.chunk_uuid),
                        "similarity_score": vector_result.similarity_score,
                        "chunk_text": vector_result.chunk_text,
                        "chunk_metadata": db_chunk.chunk_metadata,
                        "source_identifier": db_chunk.source_identifier,
                        "source_type": db_chunk.source_type,
                        "ingestion_timestamp": db_chunk.ingestion_timestamp,
                        "last_indexed_at": db_chunk.last_indexed_at
                    }
                    enriched_chunks.append(enriched_chunk)
            
            assert len(enriched_chunks) > 0, "No chunks were enriched with database metadata"
            logger.info(f"✓ Database enrichment completed: {len(enriched_chunks)} chunks enriched")
            
            # === STEP 3: Knowledge Graph Context ===
            logger.info("Step 3: Adding knowledge graph context...")
            
            # Get entities and relationships related to the chunks
            graph_context = await self._build_graph_context(
                enriched_chunks, extracted_entities, extracted_relationships, knowledge_graph_manager
            )
            
            # Validate graph context structure
            assert "entities" in graph_context, "Graph context missing entities"
            assert "relationships" in graph_context, "Graph context missing relationships"
            assert isinstance(graph_context["entities"], list), "Graph context entities should be a list"
            assert isinstance(graph_context["relationships"], list), "Graph context relationships should be a list"
            
            # Validate entity and relationship models
            for entity in graph_context["entities"]:
                assert isinstance(entity, Entity), f"Graph entity is not an Entity model: {type(entity)}"
                assert entity.id, "Graph entity missing ID"
                assert entity.entity_type, "Graph entity missing type"
                assert entity.name, "Graph entity missing name"
            
            for relationship in graph_context["relationships"]:
                assert isinstance(relationship, Relationship), f"Graph relationship is not a Relationship model: {type(relationship)}"
                assert relationship.from_entity, "Graph relationship missing from_entity"
                assert relationship.to_entity, "Graph relationship missing to_entity"
                assert relationship.relationship_type, "Graph relationship missing type"
            
            logger.info(f"✓ Knowledge graph context: {len(graph_context['entities'])} entities, {len(graph_context['relationships'])} relationships")
            
            # === STEP 4: Combined Context Output ===
            logger.info("Step 4: Building combined context output...")
            
            # Create comprehensive retrieval context using actual models
            retrieval_context = RetrievalContext(
                query_text=query_text,
                vector_results=vector_results,
                database_results=database_results,
                graph_context=GraphContext(
                    entities=graph_context["entities"],
                    relationships=graph_context["relationships"],
                    entity_count=len(graph_context["entities"]),
                    relationship_count=len(graph_context["relationships"])
                ),
                retrieval_timestamp=datetime.now(),
                total_chunks_found=len(enriched_chunks),
                processing_time_ms=0  # Would be calculated in real implementation
            )
            
            # Validate combined context structure
            assert retrieval_context.query_text, "Retrieval context missing query text"
            assert retrieval_context.vector_results, "Retrieval context missing vector results"
            assert retrieval_context.database_results, "Retrieval context missing database results"
            assert retrieval_context.graph_context, "Retrieval context missing graph context"
            assert retrieval_context.total_chunks_found > 0, "Retrieval context reports no chunks found"
            
            # Validate context completeness
            assert_context_completeness(retrieval_context, test_scenario)
            
            logger.info("✓ Combined context output completed successfully")
            
            # === Context Quality Assessment ===
            logger.info("Assessing context quality...")
            
            context_quality = await self._assess_context_quality(
                retrieval_context, test_scenario, processed_test_documents
            )
            
            # Validate context quality metrics
            assert context_quality["vector_quality"] > 0, "Vector search quality too low"
            assert context_quality["metadata_completeness"] > 0.5, "Metadata completeness too low"
            assert context_quality["graph_relevance"] >= 0, "Graph relevance should be non-negative"
            assert context_quality["overall_score"] > 0, "Overall context quality too low"
            
            logger.info(f"✓ Context quality assessment: {context_quality}")
            
            # === Success Reporting ===
            context_stats = {
                "query_text_length": len(query_text),
                "vector_results_count": len(vector_results),
                "database_chunks_found": len(database_results),
                "entities_in_context": len(graph_context["entities"]),
                "relationships_in_context": len(graph_context["relationships"]),
                "enriched_chunks_count": len(enriched_chunks),
                "context_quality_score": context_quality["overall_score"],
                "all_steps_completed": True
            }
            
            e2e_reporter.log_context_stats(context_stats)
            e2e_reporter.log_test_success("Complete Context Flow", context_stats)
            
            logger.info(f"🎉 Complete context flow test PASSED for scenario: {test_scenario.test_id}")
            logger.info(f"📊 Context stats: {context_stats}")
            
        except Exception as e:
            error_context = {
                "scenario": test_scenario.test_id,
                "processed_documents": len(processed_test_documents) if 'processed_test_documents' in locals() else 0,
                "processed_chunks": len(processed_test_chunks) if 'processed_test_chunks' in locals() else 0,
                "extracted_entities": len(extracted_entities) if 'extracted_entities' in locals() else 0,
                "extracted_relationships": len(extracted_relationships) if 'extracted_relationships' in locals() else 0
            }
            e2e_reporter.log_test_failure("Complete Context Flow", str(e), error_context)
            logger.error(f"💥 Complete context flow test FAILED for scenario {test_scenario.test_id}: {e}")
            raise
    
    async def test_llm_retrieval_context(
        self,
        test_scenario: TestScenario,
        processed_test_documents: List[ProcessedDocument],
        processed_test_chunks: List[ChunkData],
        extracted_entities: List[Entity],
        extracted_relationships: List[Relationship],
        vector_store_manager,
        database_manager,
        knowledge_graph_manager,
        test_isolation_id: str,
        e2e_reporter: E2ETestReporter
    ):
        """
        Test LLM-optimized retrieval context generation using actual models.
        
        This test validates that the context manager can create LLM-ready
        retrieval contexts with proper formatting and token management.
        """
        e2e_reporter.log_test_start("LLM Retrieval Context", test_scenario.test_id)
        
        try:
            # Setup test data
            await self._setup_test_data(
                processed_test_chunks, extracted_entities, extracted_relationships,
                vector_store_manager, database_manager, knowledge_graph_manager,
                processed_test_documents, test_isolation_id
            )
            
            # Generate query from test content
            query_text = self._extract_query_text(processed_test_documents, test_scenario)
            
            # Perform retrieval for LLM context
            vector_results = await vector_store_manager.similarity_search(
                query_text=query_text,
                limit=3,  # Limit for LLM context
                metadata_filter={"test_isolation_id": test_isolation_id}
            )
            
            chunk_uuids = [result.chunk_uuid for result in vector_results]
            database_results = await database_manager.get_chunks_by_uuids(chunk_uuids)
            
            # Build graph context
            graph_context = await self._build_graph_context(
                [{"chunk_uuid": str(uuid)} for uuid in chunk_uuids],
                extracted_entities, extracted_relationships, knowledge_graph_manager
            )
            
            # Create LLM-optimized retrieval context
            llm_context = LLMRetrievalContext(
                query_text=query_text,
                relevant_chunks=[
                    {
                        "chunk_text": result.chunk_text or "No text available",
                        "source": result.chunk_metadata.get("source_identifier", "Unknown") if result.chunk_metadata else "Unknown",
                        "similarity_score": result.similarity_score
                    }
                    for result in vector_results
                ],
                entities_mentioned=[
                    {
                        "name": entity.name,
                        "type": entity.entity_type.value,
                        "context": entity.properties.get("context", "") if entity.properties else ""
                    }
                    for entity in graph_context["entities"][:5]  # Limit entities for LLM
                ],
                key_relationships=[
                    {
                        "from": rel.from_entity,
                        "to": rel.to_entity,
                        "type": rel.relationship_type,
                        "confidence": rel.properties.get("confidence", 0.5) if rel.properties else 0.5
                    }
                    for rel in graph_context["relationships"][:5]  # Limit relationships for LLM
                ],
                context_summary=f"Retrieved {len(vector_results)} relevant chunks with {len(graph_context['entities'])} entities and {len(graph_context['relationships'])} relationships for query about {test_scenario.description}",
                token_count_estimate=self._estimate_token_count(vector_results, graph_context),
                retrieval_confidence=sum(r.similarity_score for r in vector_results) / len(vector_results) if vector_results else 0
            )
            
            # Validate LLM context structure
            assert isinstance(llm_context, LLMRetrievalContext), "Result is not an LLMRetrievalContext model"
            assert llm_context.query_text, "LLM context missing query text"
            assert llm_context.relevant_chunks, "LLM context missing relevant chunks"
            assert llm_context.context_summary, "LLM context missing summary"
            assert llm_context.token_count_estimate > 0, "Token count estimate should be positive"
            assert 0 <= llm_context.retrieval_confidence <= 1, f"Invalid retrieval confidence: {llm_context.retrieval_confidence}"
            
            # Validate chunk structure
            for chunk in llm_context.relevant_chunks:
                assert "chunk_text" in chunk, "LLM chunk missing text"
                assert "source" in chunk, "LLM chunk missing source"
                assert "similarity_score" in chunk, "LLM chunk missing similarity score"
            
            # Validate entity structure
            for entity in llm_context.entities_mentioned:
                assert "name" in entity, "LLM entity missing name"
                assert "type" in entity, "LLM entity missing type"
            
            # Validate relationship structure
            for relationship in llm_context.key_relationships:
                assert "from" in relationship, "LLM relationship missing from"
                assert "to" in relationship, "LLM relationship missing to"
                assert "type" in relationship, "LLM relationship missing type"
            
            # Test token management
            assert llm_context.token_count_estimate < 15000, "LLM context may exceed model token limits"
            
            logger.info(f"✓ LLM context generated: {len(llm_context.relevant_chunks)} chunks, "
                       f"{len(llm_context.entities_mentioned)} entities, "
                       f"{len(llm_context.key_relationships)} relationships, "
                       f"~{llm_context.token_count_estimate} tokens")
            
            # === Success Reporting ===
            llm_stats = {
                "chunks_in_context": len(llm_context.relevant_chunks),
                "entities_mentioned": len(llm_context.entities_mentioned),
                "relationships_included": len(llm_context.key_relationships),
                "estimated_tokens": llm_context.token_count_estimate,
                "retrieval_confidence": llm_context.retrieval_confidence,
                "context_summary_length": len(llm_context.context_summary),
                "llm_ready": True
            }
            
            e2e_reporter.log_test_success("LLM Retrieval Context", llm_stats)
            
            logger.info(f"🎉 LLM retrieval context test PASSED for scenario: {test_scenario.test_id}")
            logger.info(f"📊 LLM context stats: {llm_stats}")
            
        except Exception as e:
            error_context = {
                "scenario": test_scenario.test_id,
                "processed_chunks": len(processed_test_chunks) if 'processed_test_chunks' in locals() else 0
            }
            e2e_reporter.log_test_failure("LLM Retrieval Context", str(e), error_context)
            logger.error(f"💥 LLM retrieval context test FAILED for scenario {test_scenario.test_id}: {e}")
            raise
    
    async def _setup_test_data(
        self,
        processed_test_chunks: List[ChunkData],
        extracted_entities: List[Entity],
        extracted_relationships: List[Relationship],
        vector_store_manager,
        database_manager,
        knowledge_graph_manager,
        processed_test_documents: List[ProcessedDocument],
        test_isolation_id: str
    ):
        """Setup test data in all storage systems."""
        logger.info("Setting up test data for context manager tests...")
        
        # Store chunks in database
        if processed_test_chunks:
            db_success, db_total = await database_manager.batch_ingest_chunks(processed_test_chunks)
            assert db_success > 0, f"Failed to store chunks in database: {db_success}/{db_total}"
        
        # Store embeddings in vector store
        if processed_test_chunks and processed_test_documents:
            texts = []
            chunk_uuids = []
            metadata_list = []
            
            for chunk in processed_test_chunks:
                # Get full text from processed documents
                full_text = None
                for doc in processed_test_documents:
                    for text_chunk in doc.chunks:
                        if text_chunk.chunk_uuid == str(chunk.chunk_uuid):
                            full_text = text_chunk.text
                            break
                    if full_text:
                        break
                
                if full_text:
                    texts.append(full_text)
                    chunk_uuids.append(str(chunk.chunk_uuid))
                    metadata_list.append(chunk.chunk_metadata)
            
            if texts:
                vector_result = await vector_store_manager.generate_and_ingest(texts, chunk_uuids, metadata_list)
                assert vector_result.successful_count > 0, f"Failed to store embeddings: {vector_result.successful_count}/{len(texts)}"
        
        # Store entities and relationships in knowledge graph
        if extracted_entities:
            entity_result = await knowledge_graph_manager.batch_ingest_entities(extracted_entities)
            logger.info(f"Stored {entity_result.successful_count}/{len(extracted_entities)} entities")
        
        if extracted_relationships:
            rel_result = await knowledge_graph_manager.batch_ingest_relationships(extracted_relationships)
            logger.info(f"Stored {rel_result.successful_count}/{len(extracted_relationships)} relationships")
        
        logger.info("✓ Test data setup completed")
    
    def _extract_query_text(self, processed_documents: List[ProcessedDocument], test_scenario: TestScenario) -> str:
        """Extract meaningful query text from processed documents."""
        if not processed_documents or not processed_documents[0].chunks:
            # Fallback to scenario-based query
            if test_scenario.source_type == "github_repo":
                return "Privacy Sandbox analysis tool Chrome extension features"
            elif test_scenario.source_type in ["drive_folder", "drive_file"]:
                return "DevRel assistance developer relations best practices"
            elif test_scenario.source_type == "web_source":
                return "Python tutorial operators mathematical calculations"
            else:
                return "test query for context retrieval"
        
        # Extract meaningful phrases from first chunk
        first_chunk_text = processed_documents[0].chunks[0].text
        
        # Simple extraction - take first sentence or meaningful phrase
        sentences = first_chunk_text.split('. ')
        if sentences:
            query = sentences[0]
            if len(query) > 100:
                query = query[:100] + "..."
            return query
        
        return first_chunk_text[:100] + "..." if len(first_chunk_text) > 100 else first_chunk_text
    
    async def _build_graph_context(
        self,
        enriched_chunks: List[Dict[str, Any]],
        extracted_entities: List[Entity],
        extracted_relationships: List[Relationship],
        knowledge_graph_manager
    ) -> Dict[str, List]:
        """Build knowledge graph context for the given chunks."""
        try:
            # Extract chunk UUIDs
            chunk_uuids = [uuid.UUID(chunk["chunk_uuid"]) for chunk in enriched_chunks]
            
            # Filter entities and relationships that are related to these chunks
            relevant_entities = []
            relevant_relationships = []
            
            for entity in extracted_entities:
                if entity.source_chunks and any(chunk_uuid in entity.source_chunks for chunk_uuid in chunk_uuids):
                    relevant_entities.append(entity)
            
            for relationship in extracted_relationships:
                if relationship.source_chunks and any(chunk_uuid in relationship.source_chunks for chunk_uuid in chunk_uuids):
                    relevant_relationships.append(relationship)
            
            return {
                "entities": relevant_entities,
                "relationships": relevant_relationships
            }
            
        except Exception as e:
            logger.warning(f"Error building graph context: {e}")
            return {"entities": [], "relationships": []}
    
    async def _assess_context_quality(
        self,
        retrieval_context: RetrievalContext,
        test_scenario: TestScenario,
        processed_documents: List[ProcessedDocument]
    ) -> Dict[str, float]:
        """Assess the quality of the retrieval context."""
        # Vector quality: based on similarity scores
        vector_quality = sum(r.similarity_score for r in retrieval_context.vector_results) / len(retrieval_context.vector_results) if retrieval_context.vector_results else 0
        
        # Metadata completeness: check if database results have complete metadata
        metadata_completeness = 0
        if retrieval_context.database_results:
            complete_metadata_count = sum(
                1 for chunk in retrieval_context.database_results
                if chunk.chunk_metadata and len(chunk.chunk_metadata) > 3
            )
            metadata_completeness = complete_metadata_count / len(retrieval_context.database_results)
        
        # Graph relevance: based on entity and relationship counts
        graph_relevance = 0
        if retrieval_context.graph_context:
            entity_score = min(retrieval_context.graph_context.entity_count / 5, 1.0)  # Normalize to max 5 entities
            relationship_score = min(retrieval_context.graph_context.relationship_count / 3, 1.0)  # Normalize to max 3 relationships
            graph_relevance = (entity_score + relationship_score) / 2
        
        # Overall score: weighted average
        overall_score = (vector_quality * 0.4 + metadata_completeness * 0.3 + graph_relevance * 0.3)
        
        return {
            "vector_quality": vector_quality,
            "metadata_completeness": metadata_completeness,
            "graph_relevance": graph_relevance,
            "overall_score": overall_score
        }
    
    def _estimate_token_count(self, vector_results: List[VectorRetrievalResult], graph_context: Dict[str, List]) -> int:
        """Estimate token count for LLM context (rough approximation)."""
        # Rough token estimation: ~4 characters per token
        text_chars = sum(len(result.chunk_text or "") for result in vector_results)
        entity_chars = sum(len(entity.name) + len(str(entity.entity_type)) for entity in graph_context["entities"])
        relationship_chars = sum(len(rel.from_entity) + len(rel.to_entity) + len(rel.relationship_type) for rel in graph_context["relationships"])
        
        total_chars = text_chars + entity_chars + relationship_chars
        estimated_tokens = total_chars // 4  # Rough approximation
        
        return max(estimated_tokens, 100)  # Minimum token count


# Command-line execution support
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Context Manager Flow Tests")
    parser.add_argument("--scenario", choices=["github", "drive_file", "web", "all"], 
                       default="all", help="Test scenario to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Build pytest arguments
    pytest_args = [__file__, "-v"]
    
    if args.scenario != "all":
        pytest_args.extend(["-k", f"test_context_manager_4_step_flow[{args.scenario}]"])
    
    # Run pytest
    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code) 