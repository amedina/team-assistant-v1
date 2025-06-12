import asyncio
import base64
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Iterator, AsyncIterator
import httpx

# Import our Secret Manager utility instead of direct client
from app.utils.secret_manager import get_secret_value
from app.data_ingestion.connectors.base_connector import BaseConnector, SourceDocument, ConnectionStatus

class GitHubConnector(BaseConnector):
    """Connector for GitHub repositories."""
    
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.client: Optional[httpx.AsyncClient] = None
        self.access_token: Optional[str] = None
        self.repository = self.config.get("repository")
        self.branch = self.config.get("branch", "main")
        self.paths = self.config.get("paths", [])
        
    async def connect(self) -> bool:
        """Establish connection to GitHub API."""
        try:
            # Get access token from Secret Manager
            self.access_token = await self._get_access_token()
            
            # Initialize HTTP client with redirect following enabled
            headers = {
                "Authorization": f"token {self.access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DevRel-Assistant/1.0"
            }
            self.client = httpx.AsyncClient(
                headers=headers, 
                timeout=30.0, 
                follow_redirects=True
            )
            
            # Test connection
            response = await self.client.get(f"https://api.github.com/repos/{self.repository}")
            response.raise_for_status()
            
            self.logger.info(f"Successfully connected to GitHub repository: {self.repository}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to GitHub: {str(e)}")
            return False
    
    async def fetch_documents(self, 
                            last_sync: Optional[datetime] = None,
                            limit: Optional[int] = None) -> AsyncIterator[SourceDocument]:
        """Fetch documents from the GitHub repository."""
        if not self.client:
            await self.connect()
        
        documents_processed = 0
        
        # If no specific paths specified, get all files
        paths_to_process = self.paths if self.paths else [""]
        
        for path in paths_to_process:
            async for document in self._fetch_from_path(path, last_sync):
                if limit and documents_processed >= limit:
                    return
                yield document
                documents_processed += 1
    
    async def _fetch_from_path(self, 
                              path: str, 
                              last_sync: Optional[datetime] = None) -> AsyncIterator[SourceDocument]:
        """Fetch documents from a specific path in the repository."""
        try:
            # Get contents of the path
            url = f"https://api.github.com/repos/{self.repository}/contents/{path}"
            if self.branch != "main":
                url += f"?ref={self.branch}"
                
            response = await self.client.get(url)
            response.raise_for_status()
            contents = response.json()
            
            # Handle single file vs directory
            if not isinstance(contents, list):
                contents = [contents]
            
            for item in contents:
                if item["type"] == "file":
                    # Check if file should be included
                    if not self.should_include_file(item["path"], item.get("size", 0)):
                        continue
                    
                    # Check if file was modified since last sync
                    if last_sync:
                        # Note: GitHub API doesn't provide file modification time in contents API
                        # For full sync accuracy, you'd need to check commits
                        pass
                    
                    document = await self._fetch_file_content(item)
                    if document:
                        yield document
                        
                elif item["type"] == "dir":
                    # Recursively fetch from subdirectory
                    async for sub_document in self._fetch_from_path(item["path"], last_sync):
                        yield sub_document
                        
        except Exception as e:
            self.logger.error(f"Error fetching from path {path}: {str(e)}")
    
    async def _fetch_file_content(self, file_item: Dict[str, Any]) -> Optional[SourceDocument]:
        """Fetch the content of a specific file."""
        try:
            # Get file content
            response = await self.client.get(file_item["download_url"])
            response.raise_for_status()
            
            # Determine content type and decode
            content = response.text
            content_type = "text"
            
            # Handle different file types
            if file_item["name"].lower().endswith(".pdf"):
                content_type = "pdf"
                # For PDF files, you might want to extract text using a PDF library
                content = "PDF content extraction not implemented yet"
            
            # Create document
            document = SourceDocument(
                source_id=self.source_id,
                document_id=f"{self.repository}:{file_item['path']}",
                title=file_item["name"],
                content=content,
                content_type=content_type,
                url=file_item["html_url"],
                metadata=self.extract_metadata(
                    file_path=file_item["path"],
                    file_size=file_item.get("size", 0),
                    repository=self.repository,
                    branch=self.branch,
                    sha=file_item.get("sha"),
                    download_url=file_item.get("download_url")
                )
            )
            
            return document
            
        except Exception as e:
            self.logger.error(f"Error fetching file {file_item['path']}: {str(e)}")
            return None
    
    async def get_document_count(self) -> int:
        """Get total number of documents available."""
        if not self.client:
            await self.connect()
        
        count = 0
        paths_to_process = self.paths if self.paths else [""]
        
        for path in paths_to_process:
            count += await self._count_files_in_path(path)
        
        return count
    
    async def _count_files_in_path(self, path: str) -> int:
        """Count files in a specific path."""
        try:
            url = f"https://api.github.com/repos/{self.repository}/contents/{path}"
            if self.branch != "main":
                url += f"?ref={self.branch}"
                
            response = await self.client.get(url)
            response.raise_for_status()
            contents = response.json()
            
            if not isinstance(contents, list):
                contents = [contents]
            
            count = 0
            for item in contents:
                if item["type"] == "file":
                    if self.should_include_file(item["path"], item.get("size", 0)):
                        count += 1
                elif item["type"] == "dir":
                    count += await self._count_files_in_path(item["path"])
            
            return count
            
        except Exception as e:
            self.logger.error(f"Error counting files in path {path}: {str(e)}")
            return 0
    
    async def check_connection(self) -> ConnectionStatus:
        """Check if the connection is healthy."""
        try:
            # Try to connect if not already connected
            if not self.client:
                connected = await self.connect()
                if not connected:
                    return ConnectionStatus(
                        is_connected=False,
                        last_check=datetime.now(),
                        error_message="Failed to initialize connection"
                    )
            
            # Test API access with the repository
            response = await self.client.get(f"https://api.github.com/repos/{self.repository}")
            response.raise_for_status()
            
            # Try to get document count
            try:
                doc_count = await self.get_document_count()
            except Exception as e:
                self.logger.warning(f"Could not get document count: {e}")
                doc_count = None
            
            return ConnectionStatus(
                is_connected=True,
                last_check=datetime.now(),
                documents_available=doc_count
            )
            
        except Exception as e:
            return ConnectionStatus(
                is_connected=False,
                last_check=datetime.now(),
                error_message=f"Connection check failed: {str(e)}"
            )
    
    async def disconnect(self) -> None:
        """Clean up connection resources."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self.access_token = None
    
    async def _get_access_token(self) -> str:
        """Get GitHub access token from Secret Manager."""
        try:
            # Get access token configuration
            access_token_config = self.config.get("access_token")
            if not access_token_config:
                raise ValueError("No access token configuration found")
            
            # Support different configuration formats
            if isinstance(access_token_config, str):
                if access_token_config.startswith("projects/"):
                    # Parse secret path: projects/PROJECT_ID/secrets/SECRET_NAME/versions/VERSION
                    parts = access_token_config.split("/")
                    if len(parts) < 6:
                        raise ValueError(f"Invalid secret path format: {access_token_config}")
                    
                    project_id = parts[1]
                    secret_name = parts[3]
                    version = parts[5] if len(parts) > 5 else "latest"
                else:
                    # Assume it's just the secret name, use default project
                    secret_name = access_token_config
                    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
                    version = "latest"
            elif isinstance(access_token_config, dict):
                # Configuration as dict: {"secret_id": "github-token", "project_id": "my-project", "version": "latest"}
                secret_name = access_token_config.get("secret_id")
                project_id = access_token_config.get("project_id") or os.getenv("GOOGLE_CLOUD_PROJECT")
                version = access_token_config.get("version", "latest")
            else:
                raise ValueError(f"Invalid access token configuration format: {access_token_config}")
            
            if not secret_name:
                raise ValueError("Secret name not found in configuration")
            if not project_id:
                raise ValueError("Project ID not found in configuration or environment")
            
            # Get secret from Secret Manager using our utility
            token = get_secret_value(secret_name, project_id, version)
            
            if not token or not token.strip():
                raise ValueError("Retrieved token is empty")
                
            return token.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to get access token from Secret Manager: {str(e)}")
            # For development/testing, check if there's a fallback environment variable
            fallback_token = os.getenv("GITHUB_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN")
            if fallback_token:
                self.logger.warning("Using fallback GitHub token from environment variable")
                return fallback_token.strip()
            raise
