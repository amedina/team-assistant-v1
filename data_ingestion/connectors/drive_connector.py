import asyncio
import os
import io
from datetime import datetime
from typing import Dict, List, Any, Optional, Iterator, AsyncIterator
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.credentials import Credentials
import google.auth
import json

from utils.secret_manager import SecretConfig
from data_ingestion.connectors.base_connector import BaseConnector, SourceDocument, ConnectionStatus

class DriveConnector(BaseConnector):
    """Connector for Google Drive folders."""
    
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.folder_id = self.config.get("folder_id")
        self.include_subfolders = self.config.get("include_subfolders", True)
        self.file_types = self.config.get("file_types", ["google_doc", "google_slide", "pdf", "text"])
        self.max_file_size_mb = self.config.get("max_file_size_mb", 50)
        self.credentials: Optional[Credentials] = None
        self.drive_service = None
        
        # Initialize secret configuration for credential management
        self.secret_config = SecretConfig()
        
    async def connect(self) -> bool:
        """Establish connection to Google Drive API."""
        try:
            if not self.folder_id:
                self.logger.error("No folder_id specified in configuration")
                return False
            
            # Try to get credentials in order of preference
            self.credentials = await self._get_credentials()
            if not self.credentials:
                self.logger.error("Failed to obtain Google Drive credentials")
                return False
            
            # Build Drive service
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            
            # Test connection by trying to get folder info
            try:
                folder_info = self.drive_service.files().get(fileId=self.folder_id).execute()
                self.logger.info(f"Successfully connected to Drive folder: {folder_info.get('name', self.folder_id)}")
            except Exception as drive_error:
                # More specific error handling for Drive API issues
                error_str = str(drive_error)
                if "403" in error_str and "insufficientPermissions" in error_str:
                    self.logger.error(f"Insufficient permissions to access folder {self.folder_id}")
                    self.logger.error("The service account may need:")
                    self.logger.error("1. Google Drive API enabled in the project")
                    self.logger.error("2. Drive read permissions")
                    self.logger.error("3. Access to the specific folder (shared with service account email)")
                elif "404" in error_str:
                    self.logger.error(f"Folder {self.folder_id} not found or not accessible")
                else:
                    self.logger.error(f"Drive API error: {error_str}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Google Drive: {str(e)}")
            return False
    
    async def _get_credentials(self) -> Optional[Credentials]:
        """
        Get Google Cloud credentials using multiple methods in order of preference:
        1. Service account key from Secret Manager
        2. GOOGLE_APPLICATION_CREDENTIALS environment variable
        3. Application Default Credentials (ADC)
        """
        scopes = ['https://www.googleapis.com/auth/drive.readonly']
        
        # Method 1: Try to get service account key from Secret Manager
        service_account_config = self.config.get("service_account")
        if service_account_config:
            try:
                if isinstance(service_account_config, str):
                    # Assume it's a secret ID
                    secret_id = service_account_config
                elif isinstance(service_account_config, dict):
                    secret_id = service_account_config.get("secret_id")
                else:
                    secret_id = None
                
                if secret_id:
                    service_account_json = self.secret_config.get_json_secret(secret_id)
                    if service_account_json:
                        from google.oauth2 import service_account
                        credentials = service_account.Credentials.from_service_account_info(
                            service_account_json, scopes=scopes
                        )
                        self.logger.info(f"Using service account credentials from Secret Manager: {secret_id}")
                        return credentials
            except Exception as e:
                self.logger.warning(f"Failed to get service account from Secret Manager: {e}")
        
        # Method 2: Check if GOOGLE_APPLICATION_CREDENTIALS is set
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path:
            try:
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path, scopes=scopes
                )
                self.logger.info(f"Using service account credentials from file: {credentials_path}")
                return credentials
            except Exception as e:
                self.logger.warning(f"Failed to load credentials from file {credentials_path}: {e}")
        
        # Method 3: Use Application Default Credentials
        try:
            credentials, project = google.auth.default(scopes=scopes)
            self.logger.info(f"Using Application Default Credentials for project: {project}")
            self.logger.info(f"Credential type: {type(credentials).__name__}")
            return credentials
        except Exception as e:
            self.logger.error(f"Failed to get Application Default Credentials: {e}")
        
        return None
    
    async def fetch_documents(self, 
                            last_sync: Optional[datetime] = None,
                            limit: Optional[int] = None) -> AsyncIterator[SourceDocument]:
        """Fetch documents from Google Drive folder."""
        if not self.drive_service:
            await self.connect()
        
        documents_processed = 0
        
        try:
            # Get all files from the folder (and subfolders if enabled)
            files = await self._list_files_in_folder(self.folder_id, last_sync)
            self.logger.info(f"Found {len(files)} total files in Drive folder")
            
            processable_files = [f for f in files if self._should_process_file(f)]
            self.logger.info(f"Will process {len(processable_files)} files (limit: {limit or 'none'})")
            
            for file_info in files:
                if limit and documents_processed >= limit:
                    self.logger.info(f"Reached limit of {limit} documents")
                    break
                    
                # Check if file should be processed
                if not self._should_process_file(file_info):
                    continue
                
                self.logger.info(f"Processing file: {file_info.get('name')} (MIME: {file_info.get('mimeType')})")
                
                # Download and process the file
                document = await self._process_file(file_info)
                if document:
                    yield document
                    documents_processed += 1
                    self.logger.info(f"Successfully processed: {file_info.get('name')} ({documents_processed}/{len(processable_files)})")
                else:
                    self.logger.warning(f"Failed to process: {file_info.get('name')}")
                    
        except Exception as e:
            self.logger.error(f"Error fetching documents from Drive: {str(e)}")
            return
    
    async def get_document_count(self) -> int:
        """Get total number of documents available."""
        if not self.drive_service:
            await self.connect()
        
        try:
            files = await self._list_files_in_folder(self.folder_id)
            return len([f for f in files if self._should_process_file(f)])
        except Exception as e:
            self.logger.error(f"Error getting document count: {str(e)}")
            return 0
    
    async def check_connection(self) -> ConnectionStatus:
        """Check if the connection is healthy."""
        try:
            # Try to connect if not already connected
            if not self.drive_service:
                connected = await self.connect()
                if not connected:
                    return ConnectionStatus(
                        is_connected=False,
                        last_check=datetime.now(),
                        error_message="Failed to connect to Google Drive"
                    )
            
            # Test access to the folder
            folder_info = self.drive_service.files().get(fileId=self.folder_id).execute()
            
            # Get document count
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
                error_message=f"Drive connection check failed: {str(e)}"
            )
    
    async def disconnect(self) -> None:
        """Clean up connection resources."""
        self.credentials = None
        self.drive_service = None
    

    
    async def _list_files_in_folder(self, folder_id: str, last_sync: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """List all files in a folder (and subfolders if enabled)."""
        files = []
        
        try:
            # Build query
            query = f"'{folder_id}' in parents and trashed=false"
            if last_sync:
                last_sync_str = last_sync.isoformat() + "Z"
                query += f" and modifiedTime > '{last_sync_str}'"
            
            # Get files
            page_token = None
            while True:
                results = self.drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink, parents, shortcutDetails)',
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                self.logger.debug(f"Found {len(items)} items in folder {folder_id}")
                for item in items:
                    self.logger.debug(f"  - {item.get('name')} (MIME: {item.get('mimeType')}, Size: {item.get('size', 'unknown')})")
                
                files.extend(items)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            # If include_subfolders is enabled, recursively get files from subfolders
            if self.include_subfolders:
                for file_info in files.copy():  # Use copy to avoid modifying while iterating
                    if file_info.get('mimeType') == 'application/vnd.google-apps.folder':
                        subfolder_files = await self._list_files_in_folder(file_info['id'], last_sync)
                        files.extend(subfolder_files)
            
            return files
            
        except Exception as e:
            self.logger.error(f"Error listing files in folder {folder_id}: {str(e)}")
            return []
    
    def _should_process_file(self, file_info: Dict[str, Any]) -> bool:
        """Check if a file should be processed based on configuration."""
        mime_type = file_info.get('mimeType', '')
        name = file_info.get('name', '')
        size = int(file_info.get('size', 0)) if file_info.get('size') else 0
        
        self.logger.debug(f"Checking file: {name} (MIME: {mime_type}, Size: {size})")
        
        # Skip folders (they're processed separately for recursion)
        if mime_type == 'application/vnd.google-apps.folder':
            self.logger.debug(f"Skipping folder: {name}")
            return False
        
        # Handle shortcuts - they should be processed
        if mime_type == 'application/vnd.google-apps.shortcut':
            self.logger.debug(f"Found shortcut: {name} - will process")
            return True
        
        # Check file type
        file_type_mapping = {
            'application/vnd.google-apps.document': 'google_doc',
            'application/vnd.google-apps.presentation': 'google_slide',
            'application/vnd.google-apps.spreadsheet': 'google_sheet',  # Google Sheets
            'application/pdf': 'pdf',
            'text/plain': 'text',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'text',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'text',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'text',
            'application/msword': 'text',
            'application/vnd.ms-powerpoint': 'text',
            'text/csv': 'text',
            'application/rtf': 'text'
        }
        
        file_type = file_type_mapping.get(mime_type, 'unknown')
        if file_type not in self.file_types:
            self.logger.debug(f"Skipping file {name}: type '{file_type}' not in allowed types {self.file_types}")
            return False
        
        # Check exclude patterns
        exclude_patterns = self.config.get("exclude_patterns", [])
        for pattern in exclude_patterns:
            if pattern in name:
                self.logger.debug(f"Skipping file {name}: matches exclude pattern '{pattern}'")
                return False
        
        # Check file size (convert bytes to MB) - only if size is available
        if size > 0 and size > self.max_file_size_mb * 1024 * 1024:
            self.logger.debug(f"Skipping file {name}: size {size/1024/1024:.1f}MB exceeds limit {self.max_file_size_mb}MB")
            return False
        
        self.logger.debug(f"File {name} will be processed")
        return True
    
    async def _process_file(self, file_info: Dict[str, Any]) -> Optional[SourceDocument]:
        """Download and process a file from Google Drive."""
        try:
            file_id = file_info['id']
            name = file_info['name']
            mime_type = file_info.get('mimeType', '')
            
            # Handle shortcuts by resolving to target file
            actual_file_info = file_info
            if mime_type == 'application/vnd.google-apps.shortcut':
                self.logger.info(f"Resolving shortcut: {name}")
                actual_file_info = await self._resolve_shortcut(file_info)
                if not actual_file_info:
                    self.logger.warning(f"Could not resolve shortcut: {name}")
                    return None
                
                # Update variables with target file info
                file_id = actual_file_info['id']
                mime_type = actual_file_info.get('mimeType', '')
                self.logger.info(f"Shortcut {name} resolved to: {actual_file_info.get('name', 'unknown')} (MIME: {mime_type})")
            
            # Download file content based on type
            content = await self._download_file_content(file_id, mime_type)
            if not content:
                return None
            
            # Create source document (use original name for shortcuts)
            document = SourceDocument(
                source_id=self.source_id,
                document_id=f"drive:{file_id}",
                title=name,  # Keep original shortcut name if it was a shortcut
                content=content,
                content_type="text",
                url=file_info.get('webViewLink'),  # Keep original shortcut URL
                last_modified=self._parse_drive_datetime(actual_file_info.get('modifiedTime')),
                metadata=self.extract_metadata(
                    drive_file_id=file_id,
                    mime_type=mime_type,
                    file_size=actual_file_info.get('size'),
                    folder_id=self.folder_id,
                    drive_url=file_info.get('webViewLink'),
                    file_name=name,
                    is_shortcut=file_info.get('mimeType') == 'application/vnd.google-apps.shortcut',
                    target_file_id=file_id if file_info.get('mimeType') == 'application/vnd.google-apps.shortcut' else None
                )
            )
            
            return document
            
        except Exception as e:
            self.logger.error(f"Error processing file {file_info.get('name', 'unknown')}: {str(e)}")
            return None
    
    async def _download_file_content(self, file_id: str, mime_type: str) -> Optional[str]:
        """Download the content of a file."""
        try:
            if mime_type == 'application/vnd.google-apps.document':
                # Export Google Doc as plain text
                request = self.drive_service.files().export_media(
                    fileId=file_id, 
                    mimeType='text/plain'
                )
            elif mime_type == 'application/vnd.google-apps.presentation':
                # Export Google Slides as plain text
                request = self.drive_service.files().export_media(
                    fileId=file_id, 
                    mimeType='text/plain'
                )
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                # Export Google Sheets as CSV for better content extraction
                request = self.drive_service.files().export_media(
                    fileId=file_id, 
                    mimeType='text/csv'
                )
            else:
                # Download other file types directly
                request = self.drive_service.files().get_media(fileId=file_id)
            
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # Decode content
            content_bytes = file_content.getvalue()
            
            # Try to decode as text
            try:
                content = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content = content_bytes.decode('latin-1')
                except UnicodeDecodeError:
                    self.logger.warning(f"Could not decode file content for {file_id}")
                    return None
            
            return content.strip()
            
        except Exception as e:
            self.logger.error(f"Error downloading file {file_id}: {str(e)}")
            return None
    
    async def _resolve_shortcut(self, shortcut_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolve a Google Drive shortcut to its target file."""
        try:
            shortcut_id = shortcut_info['id']
            
            # Get shortcut details including target ID
            shortcut_details = self.drive_service.files().get(
                fileId=shortcut_id,
                fields='shortcutDetails'
            ).execute()
            
            target_id = shortcut_details.get('shortcutDetails', {}).get('targetId')
            if not target_id:
                self.logger.error(f"No target ID found in shortcut {shortcut_info.get('name')}")
                return None
            
            # Get target file information
            target_file = self.drive_service.files().get(
                fileId=target_id,
                fields='id, name, mimeType, size, modifiedTime, webViewLink, parents'
            ).execute()
            
            return target_file
            
        except Exception as e:
            self.logger.error(f"Error resolving shortcut {shortcut_info.get('name')}: {str(e)}")
            return None
    
    def _parse_drive_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        """Parse Google Drive datetime string."""
        if not datetime_str:
            return None
        
        try:
            # Google Drive uses RFC 3339 format
            from datetime import datetime as dt
            return dt.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except Exception:
            return None
