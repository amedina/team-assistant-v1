from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Iterator, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class SourceDocument:
    """Represents a document from a data source."""
    source_id: str
    document_id: str
    title: str
    content: str
    metadata: Dict[str, Any]
    last_modified: Optional[datetime] = None
    content_type: str = "text"
    url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing."""
        return {
            "source_id": self.source_id,
            "document_id": self.document_id,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "content_type": self.content_type,
            "url": self.url
        }

@dataclass
class ConnectionStatus:
    """Represents the status of a connector."""
    is_connected: bool
    last_check: datetime
    error_message: Optional[str] = None
    documents_available: Optional[int] = None

class BaseConnector(ABC):
    """Base class for all data source connectors."""
    
    def __init__(self, source_config: Dict[str, Any]):
        self.source_config = source_config
        self.source_id = source_config.get("source_id")
        self.source_type = source_config.get("source_type")
        self.enabled = source_config.get("enabled", True)
        self.config = source_config.get("config", {})
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the data source."""
        pass
    
    @abstractmethod
    async def fetch_documents(self, 
                            last_sync: Optional[datetime] = None,
                            limit: Optional[int] = None) -> AsyncIterator[SourceDocument]:
        """Fetch documents from the data source."""
        pass
    
    @abstractmethod
    async def get_document_count(self) -> int:
        """Get total number of documents available."""
        pass
    
    @abstractmethod
    async def check_connection(self) -> ConnectionStatus:
        """Check if the connection is healthy."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up connection resources."""
        pass
    
    def should_include_file(self, file_path: str, file_size: int = 0) -> bool:
        """Check if a file should be included based on configuration."""
        # Check file extensions
        file_extensions = self.config.get("file_extensions", [])
        if file_extensions:
            if not any(file_path.lower().endswith(ext.lower()) for ext in file_extensions):
                return False
        
        # Check exclude patterns
        exclude_patterns = self.config.get("exclude_patterns", [])
        for pattern in exclude_patterns:
            if pattern in file_path:
                return False
        
        # Check file size limit
        max_size_mb = self.config.get("max_file_size_mb", 50)
        if file_size > max_size_mb * 1024 * 1024:
            return False
            
        return True
    
    def extract_metadata(self, **kwargs) -> Dict[str, Any]:
        """Extract common metadata for documents."""
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "extracted_at": datetime.now().isoformat(),
            **kwargs
        }
