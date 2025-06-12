"""
Shared Pydantic models for data ingestion pipeline.

This module defines type-safe data models for all components in the pipeline:
managers, ingestors, and retrievers across Vector Store, Database, and Knowledge Graph systems.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
from uuid import UUID
from enum import Enum


# ====================================================================
# ENUMS AND BASE TYPES
# ====================================================================

class SourceType(str, Enum):
    """Supported source types."""
    GITHUB = "github_repo"
    DRIVE = "drive_folder"
    DRIVE_FILE = "drive_file"
    WEB = "web_source"
    LOCAL = "local"


class IngestionStatus(str, Enum):
    """Ingestion status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EntityType(str, Enum):
    """Knowledge graph entity types."""
    PERSON = "person"
    ORGANIZATION = "organization"
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    LOCATION = "location"
    EVENT = "event"
    OTHER = "other"


# ====================================================================
# CORE DATA MODELS
# ====================================================================

class ChunkMetadata(BaseModel):
    """Metadata for document chunks."""
    source_type: SourceType
    source_identifier: str = Field(..., max_length=512)
    chunk_index: int = Field(..., ge=0)
    total_chunks: int = Field(..., ge=1)
    content_hash: Optional[str] = Field(None, max_length=64)
    last_modified: Optional[datetime] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = Field(None, ge=0)
    language: Optional[str] = Field(None, max_length=10)
    
    @field_validator('total_chunks')
    @classmethod
    def total_chunks_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('total_chunks must be positive')
        return v
    
    @field_validator('chunk_index')
    @classmethod
    def chunk_index_must_be_valid(cls, v):
        # Note: In V2, cross-field validation should use model_validator
        # This is a simplified version for chunk_index only
        if v < 0:
            raise ValueError('chunk_index must be non-negative')
        return v
    
    @model_validator(mode='after')
    def validate_chunk_index_vs_total(self):
        """Validate chunk_index is less than total_chunks."""
        if self.chunk_index >= self.total_chunks:
            raise ValueError('chunk_index must be less than total_chunks')
        return self


class ChunkData(BaseModel):
    """Core chunk data structure."""
    chunk_uuid: UUID
    source_type: SourceType
    source_identifier: str
    chunk_text_summary: Optional[str] = Field(None, max_length=1000)
    chunk_metadata: Dict[str, Any] = Field(default_factory=dict)
    ingestion_timestamp: datetime
    source_last_modified_at: Optional[datetime] = None
    source_content_hash: Optional[str] = None
    last_indexed_at: Optional[datetime] = None
    ingestion_status: IngestionStatus = IngestionStatus.COMPLETED
    
    model_config = ConfigDict(
        # json_encoders is deprecated in V2, use model_serializer for custom serialization if needed
        extra='forbid'  # Prevent extra fields
    )


# ====================================================================
# VECTOR STORE MODELS
# ====================================================================

class VectorRetrievalResult(BaseModel):
    """Result from vector similarity search."""
    chunk_uuid: UUID
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    distance_metric: str = Field(default="cosine")
    
    @field_validator('similarity_score')
    @classmethod
    def score_must_be_valid(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Similarity score must be between 0 and 1')
        return v


class EmbeddingData(BaseModel):
    """Data structure for embeddings with metadata."""
    chunk_uuid: UUID
    embedding: List[float] = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('embedding')
    @classmethod
    def embedding_must_have_consistent_dimensions(cls, v):
        if len(v) == 0:
            raise ValueError('Embedding cannot be empty')
        return v


# ====================================================================
# DATABASE MODELS
# ====================================================================

class ContextualChunk(BaseModel):
    """Chunk with surrounding context."""
    primary_chunk: ChunkData
    context_chunks: List[ChunkData] = Field(default_factory=list)
    context_window_size: int = Field(default=2, ge=0)
    source_document_info: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('context_chunks')
    @classmethod
    def context_chunks_must_be_reasonable(cls, v):
        if len(v) > 20:  # Reasonable limit
            raise ValueError('Too many context chunks (max 20)')
        return v


class EnrichedChunk(BaseModel):
    """Chunk enriched with additional retrieval data."""
    chunk_data: ChunkData
    vector_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    graph_entities: List[str] = Field(default_factory=list)
    related_chunks: List[UUID] = Field(default_factory=list)
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    ranking_position: Optional[int] = Field(None, ge=1)
    
    @field_validator('vector_score', 'relevance_score')
    @classmethod
    def scores_must_be_valid(cls, v):
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError('Scores must be between 0 and 1')
        return v


# ====================================================================
# KNOWLEDGE GRAPH MODELS
# ====================================================================

class Entity(BaseModel):
    """Knowledge graph entity."""
    id: str = Field(..., min_length=1, max_length=200)
    entity_type: EntityType
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    properties: Dict[str, Any] = Field(default_factory=dict)
    source_chunks: List[UUID] = Field(default_factory=list)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    @field_validator('confidence_score')
    @classmethod
    def confidence_must_be_valid(cls, v):
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError('Confidence score must be between 0 and 1')
        return v


class Relationship(BaseModel):
    """Knowledge graph relationship."""
    from_entity: str = Field(..., min_length=1)
    to_entity: str = Field(..., min_length=1)
    relationship_type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    properties: Dict[str, Any] = Field(default_factory=dict)
    source_chunks: List[UUID] = Field(default_factory=list)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    @field_validator('confidence_score')
    @classmethod
    def confidence_must_be_valid(cls, v):
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError('Confidence score must be between 0 and 1')
        return v
    
    @model_validator(mode='before')
    @classmethod
    def entities_must_be_different(cls, values):
        if isinstance(values, dict):
            from_entity = values.get('from_entity')
            to_entity = values.get('to_entity')
            if from_entity == to_entity:
                raise ValueError('from_entity and to_entity must be different')
        return values


class GraphContext(BaseModel):
    """Knowledge graph context for a query."""
    query_entities: List[Entity] = Field(default_factory=list)
    related_entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    entity_chunks_mapping: Dict[str, List[UUID]] = Field(default_factory=dict)
    graph_depth: int = Field(default=1, ge=0, le=5)
    total_entities_found: int = Field(default=0, ge=0)
    
    @field_validator('graph_depth')
    @classmethod
    def depth_must_be_reasonable(cls, v):
        if v > 5:
            raise ValueError('Graph depth too large (max 5)')
        return v


# ====================================================================
# UNIFIED RETRIEVAL MODELS
# ====================================================================

class RetrievalContext(BaseModel):
    """Complete retrieval context from all systems."""
    query: str = Field(..., min_length=1, max_length=1000)
    vector_results: List[VectorRetrievalResult] = Field(default_factory=list)
    enriched_chunks: List[EnrichedChunk] = Field(default_factory=list)
    graph_context: Optional[GraphContext] = None
    total_sources: int = Field(default=0, ge=0)
    processing_time_ms: float = Field(default=0.0, ge=0.0)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    @field_validator('processing_time_ms')
    @classmethod
    def processing_time_must_be_reasonable(cls, v):
        if v > 60000:  # 60 seconds seems too long
            raise ValueError('Processing time seems unreasonably long')
        return v


class LLMRetrievalContext(BaseModel):
    """Structured context optimized for LLM consumption."""
    query: str
    relevant_chunks: List[EnrichedChunk] = Field(default_factory=list)
    knowledge_entities: List[Entity] = Field(default_factory=list)
    total_sources: int = Field(default=0, ge=0)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    context_summary: Optional[str] = None
    source_types: List[SourceType] = Field(default_factory=list)
    
    def to_prompt_context(self, max_chunks: int = 10) -> str:
        """Convert to LLM-ready text format."""
        context_parts = []
        
        # Add query context
        context_parts.append(f"Query: {self.query}")
        context_parts.append(f"Sources Found: {self.total_sources}")
        context_parts.append(f"Confidence: {self.confidence_score:.2f}")
        context_parts.append("")
        
        # Add relevant chunks
        chunks_to_show = self.relevant_chunks[:max_chunks]
        for i, chunk in enumerate(chunks_to_show, 1):
            chunk_text = f"[Context {i}]"
            if chunk.chunk_data.chunk_text_summary:
                chunk_text += f"\n{chunk.chunk_data.chunk_text_summary}"
            
            # Add source info
            source_info = f"Source: {chunk.chunk_data.source_type.value}"
            if chunk.chunk_data.source_identifier:
                source_info += f" - {chunk.chunk_data.source_identifier}"
            chunk_text += f"\n{source_info}"
            
            # Add relevance score
            if chunk.relevance_score:
                chunk_text += f" (Relevance: {chunk.relevance_score:.2f})"
            
            context_parts.append(chunk_text)
        
        # Add entities if available
        if self.knowledge_entities:
            context_parts.append("")
            context_parts.append("Related Entities:")
            for entity in self.knowledge_entities[:5]:  # Limit entities
                entity_text = f"- {entity.name} ({entity.entity_type.value})"
                if entity.description:
                    entity_text += f": {entity.description}"
                context_parts.append(entity_text)
        
        return "\n".join(context_parts)
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Generate JSON schema for LLM function calling."""
        return self.model_json_schema()
    
    model_config = ConfigDict(
        # json_encoders is deprecated in V2, use model_serializer for custom serialization if needed
        extra='forbid'  # Prevent extra fields
    )


# ====================================================================
# BATCH OPERATION MODELS
# ====================================================================

class BatchOperationResult(BaseModel):
    """Result of batch operations."""
    successful_count: int = Field(default=0, ge=0)
    total_count: int = Field(default=0, ge=0)
    failed_items: List[str] = Field(default_factory=list)
    processing_time_ms: float = Field(default=0.0, ge=0.0)
    error_messages: List[str] = Field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_count == 0:
            return 0.0
        return (self.successful_count / self.total_count) * 100.0
    
    @model_validator(mode='after')
    def successful_cannot_exceed_total(self):
        """Ensure successful_count doesn't exceed total_count."""
        if self.successful_count > self.total_count:
            raise ValueError('successful_count cannot exceed total_count')
        return self


# ====================================================================
# HEALTH CHECK MODELS
# ====================================================================

class ComponentHealth(BaseModel):
    """Health status of a component."""
    component_name: str
    is_healthy: bool = False
    last_check: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = Field(None, ge=0.0)
    additional_info: Dict[str, Any] = Field(default_factory=dict)


class SystemHealth(BaseModel):
    """Overall system health status."""
    vector_store: ComponentHealth
    database: ComponentHealth
    knowledge_graph: ComponentHealth
    overall_healthy: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @model_validator(mode='after')
    def calculate_overall_health(self):
        """Calculate overall health from component health."""
        components = [self.vector_store, self.database, self.knowledge_graph]
        
        all_healthy = all(
            comp and comp.is_healthy 
            for comp in components 
            if comp is not None
        )
        
        self.overall_healthy = all_healthy
        return self 