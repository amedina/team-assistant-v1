"""
Text Processor for document processing and chunking.
Central engine for transforming raw data into structured format with intelligent chunking.
"""

import re
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import spacy
from langchain.text_splitter import RecursiveCharacterTextSplitter
import nltk
from nltk.tokenize import sent_tokenize

from data_ingestion.managers.knowledge_graph_manager import Entity, Relationship

logger = logging.getLogger(__name__)

@dataclass
class TextChunk:
    """Text chunk with metadata."""
    chunk_uuid: str
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any]
    entities: Optional[List[Entity]] = None
    relationships: Optional[List[Relationship]] = None

@dataclass
class ProcessedDocument:
    """Result of document processing."""
    source_id: str
    document_id: str
    title: str
    chunks: List[TextChunk]
    total_chunks: int
    processing_stats: Dict[str, Any]

class TextProcessor:
    """
    Central document processing engine.
    
    Responsibilities:
    - Text chunking with overlapping segments
    - Entity and relationship extraction
    - Content type handling (text, PDF, etc.)
    - Intelligent sentence-based chunking
    """
    
    def __init__(self, 
                 chunk_size: int = 1000,  # Reduced from 1500 to stay within token limits
                 chunk_overlap: int = 100,  # Reduced overlap proportionally
                 enable_entity_extraction: bool = True):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.enable_entity_extraction = enable_entity_extraction
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Token limits for embedding models (conservative estimate: ~4 chars per token)
        self.max_tokens = 15000  # Conservative limit (below the 20k model limit)
        self.max_chars_estimate = self.max_tokens * 4  # ~60k chars
        
        # Initialize NLP components
        self._nlp_model: Optional[spacy.Language] = None
        self._text_splitter: Optional[RecursiveCharacterTextSplitter] = None
        
        # Ensure NLTK data is available
        self._ensure_nltk_data()
    
    def _ensure_nltk_data(self):
        """Ensure required NLTK data is downloaded."""
        try:
            import nltk
            nltk.data.find('tokenizers/punkt')
            # Try newer punkt_tab format
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            try:
                nltk.download('punkt_tab', quiet=True)
            except:
                nltk.download('punkt', quiet=True)
    
    @property
    def nlp_model(self) -> spacy.Language:
        """Lazy initialization of spaCy model."""
        if self._nlp_model is None:
            try:
                # Try to load the model
                self._nlp_model = spacy.load("en_core_web_sm")
            except OSError:
                # Model not found, use blank model
                self.logger.warning("spaCy model 'en_core_web_sm' not found. Entity extraction will be limited.")
                self._nlp_model = spacy.blank("en")
        return self._nlp_model
    
    @property
    def text_splitter(self) -> RecursiveCharacterTextSplitter:
        """Lazy initialization of text splitter."""
        if self._text_splitter is None:
            self._text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""]
            )
        return self._text_splitter
    
    async def process_document(self, 
                             document: Dict[str, Any],
                             extract_entities: bool = None) -> ProcessedDocument:
        """
        Process a document into chunks with metadata.
        
        Args:
            document: Document data with content, title, metadata
            extract_entities: Whether to extract entities (overrides instance setting)
            
        Returns:
            ProcessedDocument with chunks and processing statistics
        """
        start_time = datetime.now()
        
        try:
            # Extract document information
            content = document.get('content', '')
            title = document.get('title', 'Untitled')
            source_id = document.get('source_id', '')
            document_id = document.get('document_id', str(uuid.uuid4()))
            metadata = document.get('metadata', {})
            
            # Clean and prepare text
            cleaned_content = self._clean_text(content)
            
            if not cleaned_content.strip():
                self.logger.warning(f"Document {document_id} has no content after cleaning")
                return ProcessedDocument(
                    source_id=source_id,
                    document_id=document_id,
                    title=title,
                    chunks=[],
                    total_chunks=0,
                    processing_stats={'error': 'No content', 'processing_time': 0}
                )
            
            # Create chunks
            chunks = await self._create_chunks(
                text=cleaned_content,
                source_id=source_id,
                document_id=document_id,
                base_metadata=metadata
            )
            
            # Extract entities and relationships if enabled
            should_extract = extract_entities if extract_entities is not None else self.enable_entity_extraction
            if should_extract:
                chunks = await self._extract_entities_from_chunks(chunks)
            
            # Calculate processing statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            stats = {
                'processing_time': processing_time,
                'original_length': len(content),
                'cleaned_length': len(cleaned_content),
                'total_chunks': len(chunks),
                'avg_chunk_size': sum(len(chunk.text) for chunk in chunks) / len(chunks) if chunks else 0
            }
            
            self.logger.info(f"Processed document {document_id}: {len(chunks)} chunks in {processing_time:.2f}s")
            
            return ProcessedDocument(
                source_id=source_id,
                document_id=document_id,
                title=title,
                chunks=chunks,
                total_chunks=len(chunks),
                processing_stats=stats
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process document {document.get('document_id', 'unknown')}: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return ProcessedDocument(
                source_id=document.get('source_id', ''),
                document_id=document.get('document_id', str(uuid.uuid4())),
                title=document.get('title', 'Error'),
                chunks=[],
                total_chunks=0,
                processing_stats={'error': str(e), 'processing_time': processing_time}
            )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove null bytes that cause PostgreSQL encoding errors
        text = text.replace('\x00', '')
        
        # Remove other problematic control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\r\n\t]+', '\n', text)
        
        # Remove repeated punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[-]{3,}', '---', text)
        
        # Remove extremely long lines that might cause token issues
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # If line is extremely long, truncate it
            if len(line) > 5000:  # Very long line, likely garbage
                line = line[:5000] + "..."
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        return text.strip()
    
    async def _create_chunks(self, 
                           text: str, 
                           source_id: str,
                           document_id: str,
                           base_metadata: Dict[str, Any]) -> List[TextChunk]:
        """Create text chunks with intelligent splitting."""
        try:
            # Use sentence-aware splitting when possible
            chunks = self._sentence_aware_split(text)
            
            # Create TextChunk objects
            text_chunks = []
            for i, (chunk_text, start_pos, end_pos) in enumerate(chunks):
                chunk_uuid = str(uuid.uuid4())
                
                # Create chunk metadata
                chunk_metadata = {
                    **base_metadata,
                    'source_id': source_id,
                    'document_id': document_id,
                    'chunk_index': i,
                    'start_char': start_pos,
                    'end_char': end_pos,
                    'chunk_length': len(chunk_text),
                    'created_at': datetime.now().isoformat()
                }
                
                # Create text summary (first 200 chars)
                text_summary = chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
                chunk_metadata['text_summary'] = text_summary
                
                # Validate chunk size for embedding model compatibility
                if len(chunk_text) > self.max_chars_estimate:
                    self.logger.warning(f"Chunk {i} is too large ({len(chunk_text)} chars), truncating to {self.max_chars_estimate}")
                    chunk_text = chunk_text[:self.max_chars_estimate] + "..."
                    chunk_metadata['truncated'] = True
                    chunk_metadata['original_length'] = len(chunk_text)
                
                text_chunk = TextChunk(
                    chunk_uuid=chunk_uuid,
                    text=chunk_text,
                    chunk_index=i,
                    start_char=start_pos,
                    end_char=end_pos,
                    metadata=chunk_metadata
                )
                
                text_chunks.append(text_chunk)
            
            return text_chunks
            
        except Exception as e:
            self.logger.error(f"Failed to create chunks: {e}")
            return []
    
    def _sentence_aware_split(self, text: str) -> List[Tuple[str, int, int]]:
        """Split text using sentence boundaries when possible."""
        try:
            # Try sentence-based splitting first
            sentences = sent_tokenize(text)
            
            chunks = []
            current_chunk = ""
            current_start = 0
            current_pos = 0
            
            for sentence in sentences:
                # Find sentence position in original text
                sentence_start = text.find(sentence, current_pos)
                if sentence_start == -1:
                    sentence_start = current_pos
                
                # Check if adding this sentence would exceed chunk size
                if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunks.append((current_chunk.strip(), current_start, sentence_start))
                    
                    # Start new chunk with overlap
                    overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                    current_start = sentence_start - len(overlap_text)
                else:
                    # Add sentence to current chunk
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                        current_start = sentence_start
                
                current_pos = sentence_start + len(sentence)
            
            # Add final chunk
            if current_chunk.strip():
                chunks.append((current_chunk.strip(), current_start, len(text)))
            
            return chunks
            
        except Exception as e:
            self.logger.warning(f"Sentence-aware splitting failed, falling back to character splitting: {e}")
            return self._character_split(text)
    
    def _character_split(self, text: str) -> List[Tuple[str, int, int]]:
        """Fallback character-based splitting."""
        try:
            split_texts = self.text_splitter.split_text(text)
            
            chunks = []
            current_pos = 0
            
            for chunk_text in split_texts:
                start_pos = text.find(chunk_text, current_pos)
                if start_pos == -1:
                    start_pos = current_pos
                
                end_pos = start_pos + len(chunk_text)
                chunks.append((chunk_text, start_pos, end_pos))
                current_pos = end_pos - self.chunk_overlap
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"Character splitting failed: {e}")
            # Ultimate fallback: simple character-based chunks
            chunks = []
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                chunk_text = text[i:i + self.chunk_size]
                chunks.append((chunk_text, i, i + len(chunk_text)))
            return chunks
    
    async def _extract_entities_from_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """Extract entities and relationships from text chunks."""
        try:
            for chunk in chunks:
                entities, relationships = await self._extract_entities_and_relationships(chunk.text, chunk.chunk_uuid)
                chunk.entities = entities
                chunk.relationships = relationships
                
                # Add entity count to metadata
                chunk.metadata['entity_count'] = len(entities) if entities else 0
                chunk.metadata['relationship_count'] = len(relationships) if relationships else 0
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"Entity extraction failed: {e}")
            return chunks
    
    async def _extract_entities_and_relationships(self, text: str, chunk_uuid: str) -> Tuple[List[Entity], List[Relationship]]:
        """Extract entities and relationships from text using NLP."""
        entities = []
        relationships = []
        
        try:
            # Process text with spaCy
            doc = self.nlp_model(text)
            
            # Extract named entities
            for ent in doc.ents:
                entity_id = f"{ent.label_}:{ent.text}".lower().replace(" ", "_")
                entity = Entity(
                    id=entity_id,
                    type=ent.label_,
                    name=ent.text,
                    properties={
                        'start_char': ent.start_char,
                        'end_char': ent.end_char,
                        'confidence': getattr(ent, 'confidence', 1.0)
                    },
                    source_chunks=[chunk_uuid]
                )
                entities.append(entity)
            
            # Extract simple relationships (placeholder implementation)
            # In a real implementation, you might use dependency parsing or other NLP techniques
            relationships = self._extract_simple_relationships(doc, entities, chunk_uuid)
            
        except Exception as e:
            self.logger.warning(f"NLP processing failed for chunk: {e}")
        
        return entities, relationships
    
    def _extract_simple_relationships(self, doc, entities: List[Entity], chunk_uuid: str) -> List[Relationship]:
        """Extract simple relationships between entities."""
        relationships = []
        
        try:
            # Simple relationship extraction based on proximity and dependency parsing
            entity_positions = {ent.name: ent for ent in entities}
            
            # Look for entities that appear close to each other
            for i, ent1 in enumerate(entities):
                for ent2 in entities[i+1:]:
                    # Calculate distance between entities in text
                    pos1 = ent1.properties.get('start_char', 0)
                    pos2 = ent2.properties.get('start_char', 0)
                    distance = abs(pos2 - pos1)
                    
                    # If entities are close, create a relationship
                    if distance < 100:  # Within 100 characters
                        relationship = Relationship(
                            from_entity=ent1.id,
                            to_entity=ent2.id,
                            relationship_type="MENTIONED_WITH",
                            properties={
                                'distance': distance,
                                'confidence': 0.5
                            },
                            source_chunks=[chunk_uuid]
                        )
                        relationships.append(relationship)
            
        except Exception as e:
            self.logger.warning(f"Relationship extraction failed: {e}")
        
        return relationships
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics and configuration."""
        return {
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'entity_extraction_enabled': self.enable_entity_extraction,
            'nlp_model_loaded': self._nlp_model is not None,
            'text_splitter_initialized': self._text_splitter is not None
        } 