import asyncio
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncIterator
from urllib.parse import urljoin, urlparse, urlunparse
import httpx
from bs4 import BeautifulSoup
import time

from data_ingestion.connectors.base_connector import BaseConnector, SourceDocument, ConnectionStatus


class WebConnector(BaseConnector):
    """Connector for web pages and websites."""
    
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.client: Optional[httpx.AsyncClient] = None
        
        # Configuration options
        self.urls = self.config.get("urls", [])
        self.crawl_mode = self.config.get("crawl_mode", "single_page")  # single_page, same_domain, or sitemap
        self.max_pages = self.config.get("max_pages", 50)
        self.max_depth = self.config.get("max_depth", 3)
        self.delay_between_requests = self.config.get("delay_between_requests", 1.0)
        self.follow_links = self.config.get("follow_links", True)
        self.respect_robots_txt = self.config.get("respect_robots_txt", True)
        self.user_agent = self.config.get("user_agent", "DevRel-Assistant/1.0 (Web Scraper)")
        
        # Content filtering
        self.allowed_content_types = self.config.get("allowed_content_types", ["text/html"])
        self.selectors = self.config.get("selectors", {})  # CSS selectors for content extraction
        self.exclude_selectors = self.config.get("exclude_selectors", [])  # Elements to exclude
        
        # Rate limiting and politeness
        self.max_concurrent_requests = self.config.get("max_concurrent_requests", 3)
        self.timeout = self.config.get("timeout", 30)
        
        # State tracking
        self.visited_urls = set()
        self.crawled_pages = 0
        
    async def connect(self) -> bool:
        """Establish HTTP client connection."""
        try:
            if not self.urls:
                self.logger.error("No URLs specified in configuration")
                return False
            
            # Initialize HTTP client with custom headers
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            self.client = httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=self.max_concurrent_requests)
            )
            
            # Test connection with first URL
            test_url = self.urls[0]
            response = await self.client.head(test_url)
            response.raise_for_status()
            
            self.logger.info(f"Successfully connected to web source. Starting with {len(self.urls)} URLs")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to web source: {str(e)}")
            return False
    
    async def fetch_documents(self, 
                            last_sync: Optional[datetime] = None,
                            limit: Optional[int] = None) -> AsyncIterator[SourceDocument]:
        """Fetch documents from web sources."""
        if not self.client:
            await self.connect()
        
        documents_processed = 0
        self.visited_urls.clear()
        self.crawled_pages = 0
        
        try:
            # Process based on crawl mode
            if self.crawl_mode == "single_page":
                # Process only the specified URLs
                for url in self.urls:
                    if limit and documents_processed >= limit:
                        break
                    
                    document = await self._fetch_single_page(url)
                    if document:
                        yield document
                        documents_processed += 1
                        
                    # Rate limiting
                    if self.delay_between_requests > 0:
                        await asyncio.sleep(self.delay_between_requests)
            
            elif self.crawl_mode == "same_domain":
                # Crawl within the same domain
                for start_url in self.urls:
                    if limit and documents_processed >= limit:
                        break
                    
                    remaining_limit = limit - documents_processed if limit is not None else None
                    async for document in self._crawl_domain(start_url, remaining_limit):
                        yield document
                        documents_processed += 1
                        
                        if limit and documents_processed >= limit:
                            break
            
            elif self.crawl_mode == "sitemap":
                # Process sitemap URLs
                for sitemap_url in self.urls:
                    if limit and documents_processed >= limit:
                        break
                    
                    remaining_limit = limit - documents_processed if limit is not None else None
                    async for document in self._process_sitemap(sitemap_url, remaining_limit):
                        yield document
                        documents_processed += 1
                        
                        if limit and documents_processed >= limit:
                            break
                            
        except Exception as e:
            self.logger.error(f"Error fetching web documents: {str(e)}")
            return
    
    async def _fetch_single_page(self, url: str) -> Optional[SourceDocument]:
        """Fetch and process a single web page."""
        try:
            if url in self.visited_urls:
                return None
            
            self.visited_urls.add(url)
            self.logger.info(f"Fetching: {url}")
            
            # Fetch the page
            response = await self.client.get(url)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get("content-type", "").split(";")[0]
            if content_type not in self.allowed_content_types:
                self.logger.debug(f"Skipping {url}: unsupported content type {content_type}")
                return None
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract content using selectors
            content = self._extract_content(soup, url)
            if not content.strip():
                self.logger.warning(f"No content extracted from {url}")
                return None
            
            # Extract metadata
            title = self._extract_title(soup, url)
            last_modified = self._extract_last_modified(response, soup)
            
            # Create document
            document = SourceDocument(
                source_id=self.source_id,
                document_id=f"web:{hash(url)}",
                title=title,
                content=content,
                content_type="text",
                url=url,
                last_modified=last_modified,
                metadata=self.extract_metadata(
                    url=url,
                    content_type=content_type,
                    status_code=response.status_code,
                    content_length=len(content),
                    crawl_mode=self.crawl_mode,
                    fetched_at=datetime.now().isoformat()
                )
            )
            
            self.crawled_pages += 1
            return document
            
        except Exception as e:
            self.logger.error(f"Error fetching page {url}: {str(e)}")
            return None
    
    async def _crawl_domain(self, start_url: str, remaining_limit: Optional[int] = None) -> AsyncIterator[SourceDocument]:
        """Crawl pages within the same domain."""
        domain = urlparse(start_url).netloc
        urls_to_visit = [(start_url, 0)]  # (url, depth)
        
        while urls_to_visit and self.crawled_pages < self.max_pages:
            if remaining_limit and self.crawled_pages >= remaining_limit:
                break
            
            url, depth = urls_to_visit.pop(0)
            
            if url in self.visited_urls or depth > self.max_depth:
                continue
            
            # Fetch the page
            document = await self._fetch_single_page(url)
            if document:
                yield document
            
            # Find more URLs to crawl if we haven't reached max depth
            if depth < self.max_depth and self.follow_links:
                try:
                    response = await self.client.get(url)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract links
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        absolute_url = urljoin(url, href)
                        
                        # Only follow links within the same domain
                        if urlparse(absolute_url).netloc == domain:
                            # Clean the URL (remove fragments)
                            parsed = urlparse(absolute_url)
                            clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ''))
                            
                            if clean_url not in self.visited_urls:
                                urls_to_visit.append((clean_url, depth + 1))
                
                except Exception as e:
                    self.logger.error(f"Error extracting links from {url}: {str(e)}")
            
            # Rate limiting
            if self.delay_between_requests > 0:
                await asyncio.sleep(self.delay_between_requests)
    
    async def _process_sitemap(self, sitemap_url: str, remaining_limit: Optional[int] = None) -> AsyncIterator[SourceDocument]:
        """Process URLs from a sitemap."""
        try:
            self.logger.info(f"Processing sitemap: {sitemap_url}")
            response = await self.client.get(sitemap_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'xml')
            
            # Extract URLs from sitemap
            urls = []
            for loc in soup.find_all('loc'):
                if loc.text:
                    urls.append(loc.text.strip())
            
            self.logger.info(f"Found {len(urls)} URLs in sitemap")
            
            # Process each URL
            for url in urls:
                if remaining_limit and self.crawled_pages >= remaining_limit:
                    break
                
                if self.crawled_pages >= self.max_pages:
                    break
                
                document = await self._fetch_single_page(url)
                if document:
                    yield document
                
                # Rate limiting
                if self.delay_between_requests > 0:
                    await asyncio.sleep(self.delay_between_requests)
                    
        except Exception as e:
            self.logger.error(f"Error processing sitemap {sitemap_url}: {str(e)}")
    
    def _extract_content(self, soup: BeautifulSoup, url: str) -> str:
        """Extract text content from HTML using configured selectors."""
        try:
            # Remove unwanted elements
            for selector in self.exclude_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # Use specific selectors if configured
            if self.selectors.get("content"):
                content_elements = soup.select(self.selectors["content"])
                if content_elements:
                    content = "\n\n".join([elem.get_text(strip=True) for elem in content_elements])
                else:
                    self.logger.warning(f"Content selector '{self.selectors['content']}' found no elements in {url}")
                    content = self._extract_default_content(soup)
            else:
                content = self._extract_default_content(soup)
            
            # Clean up the content
            content = re.sub(r'\n\s*\n', '\n\n', content)  # Remove excessive newlines
            content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
            
            return content.strip()
            
        except Exception as e:
            self.logger.error(f"Error extracting content from {url}: {str(e)}")
            return ""
    
    def _extract_default_content(self, soup: BeautifulSoup) -> str:
        """Extract content using default strategy."""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Try to find main content areas
        main_selectors = ["main", "[role='main']", ".main-content", ".content", "#content", "article"]
        
        for selector in main_selectors:
            elements = soup.select(selector)
            if elements:
                return "\n\n".join([elem.get_text(strip=True) for elem in elements])
        
        # Fallback to body content
        body = soup.find('body')
        return body.get_text(strip=True) if body else soup.get_text(strip=True)
    
    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract page title."""
        try:
            # Use configured title selector
            if self.selectors.get("title"):
                title_elements = soup.select(self.selectors["title"])
                if title_elements:
                    return title_elements[0].get_text(strip=True)
            
            # Default title extraction
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.get_text(strip=True)
            
            # Fallback to h1
            h1 = soup.find('h1')
            if h1:
                return h1.get_text(strip=True)
            
            # Last resort: use URL
            return urlparse(url).path.split('/')[-1] or url
            
        except Exception:
            return url
    
    def _extract_last_modified(self, response: httpx.Response, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract last modified date from HTTP headers or HTML meta tags."""
        try:
            # Check HTTP header
            last_modified = response.headers.get("last-modified")
            if last_modified:
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(last_modified)
            
            # Check meta tags
            meta_modified = soup.find('meta', attrs={'name': re.compile(r'(last-?modified|date)', re.I)})
            if meta_modified and meta_modified.get('content'):
                # This would need more sophisticated date parsing
                pass
            
            return None
            
        except Exception:
            return None
    
    async def get_document_count(self) -> int:
        """Get estimated number of documents available."""
        if self.crawl_mode == "single_page":
            return len(self.urls)
        elif self.crawl_mode == "sitemap":
            # Try to count URLs in sitemaps
            total = 0
            for sitemap_url in self.urls:
                try:
                    if not self.client:
                        await self.connect()
                    response = await self.client.get(sitemap_url)
                    soup = BeautifulSoup(response.text, 'xml')
                    total += len(soup.find_all('loc'))
                except Exception:
                    total += 1  # Fallback estimate
            return min(total, self.max_pages)
        else:
            # For domain crawling, return max_pages as estimate
            return min(self.max_pages, 100)  # Conservative estimate
    
    async def check_connection(self) -> ConnectionStatus:
        """Check if the web sources are accessible."""
        try:
            if not self.client:
                connected = await self.connect()
                if not connected:
                    return ConnectionStatus(
                        is_connected=False,
                        last_check=datetime.now(),
                        error_message="Failed to establish HTTP client connection"
                    )
            
            # Test first URL
            if self.urls:
                test_url = self.urls[0]
                response = await self.client.head(test_url)
                response.raise_for_status()
            
            # Get document count estimate
            try:
                doc_count = await self.get_document_count()
            except Exception as e:
                self.logger.warning(f"Could not estimate document count: {e}")
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
                error_message=f"Web connection check failed: {str(e)}"
            )
    
    async def disconnect(self) -> None:
        """Clean up HTTP client connection."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self.visited_urls.clear()
        self.crawled_pages = 0
