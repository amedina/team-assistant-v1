"""
Ingestion components for data pipeline.

This module contains specialized ingestor classes focused purely on data ingestion operations:
- VectorStoreIngestor: Embedding generation and vector storage
- DatabaseIngestor: Chunk metadata storage and batch operations
- KnowledgeGraphIngestor: Entity and relationship storage

Ingestors are coordinated by their respective Manager classes.
"""

from .vector_store_ingestor import VectorStoreIngestor
from .database_ingestor import DatabaseIngestor
from .knowledge_graph_ingestor import KnowledgeGraphIngestor

__all__ = [
    'VectorStoreIngestor',
    'DatabaseIngestor', 
    'KnowledgeGraphIngestor'
] 