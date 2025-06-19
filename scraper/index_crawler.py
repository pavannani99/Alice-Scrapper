from playwright.async_api import async_playwright
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndexCrawler:
    def __init__(self, base_url, max_depth=2, headless=True):
        self.base_url = base_url.rstrip('/')
        self.max_depth = max_depth
        self.visited_urls = set()
        self.headless = headless
        self.playwright = None
        self.browser = None    async def __aenter__(self):
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-dev-shm-usage', '--no-sandbox']
            )
            return self
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise    async def _extract_links(self, current_url, page_content):
        soup = BeautifulSoup(page_content, 'html.parser')
        links = set()
        base_domain = urlparse(self.base_url).netloc

        try:
            for anchor in soup.find_all('a', href=True):
                href = anchor['href'].strip()
                if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue

                full_url = urljoin(current_url, href)
                parsed_url = urlparse(full_url)
                
                if parsed_url.scheme not in ('http', 'https'):
                    continue

                clean_url = parsed_url._replace(fragment="").geturl()
                
                if urlparse(clean_url).netloc == base_domain and clean_url != current_url:
                    links.add(clean_url)
        except Exception as e:
            logger.error(f"Error extracting links from {current_url}: {e}")
            
        return linksasync def crawl(self, url: Optional[str] = None, depth: int = 0) -> List[str]:
        """Crawl the website starting from the given URL.
        
        Args:
            url (Optional[str]): The URL to crawl. If None, uses base_url
            depth (int): Current crawl depth
            
        Returns:
            List[str]: List of unique URLs found
        """
        if url is None:
            url = self.base_url
            
        url = url.rstrip('/')  # Normalize URL
        
        if url in self.visited_urls or depth > self.max_depth:
            return []
            
        if not self.browser:
            raise RuntimeError("Browser not initialized. Use 'async with' context manager.")
            
        logger.info(f"Crawling: {url} (depth: {depth})")
        self.visited_urls.add(url)
        all_found_links = [url]
        
        try:
            page = await self.browser.new_page()
            await page.set_default_timeout(30000)  # 30 second timeout
            
            try:
                # Configure page
                await page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/94.0.4606.81 Safari/537.36"
                })
                
                # Navigate to page
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )
                
                if not response:
                    logger.error(f"Failed to get response from {url}")
                    return all_found_links
                    
                if response.status >= 400:
                    logger.error(f"HTTP {response.status} error for {url}")
                    return all_found_links
                
                # Get page content
                content = await page.content()
                extracted_links = await self._extract_links(url, content)
                
                # Recursively crawl extracted links
                for link in extracted_links:
                    if link not in self.visited_urls:
                        try:
                            found_in_subtree = await self.crawl(link, depth + 1)
                            all_found_links.extend(found_in_subtree)
                        except Exception as e:
                            logger.error(f"Error crawling {link}: {e}")
                            
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                
            finally:
                await page.close()
                
        except Exception as e:
            logger.error(f"Failed to create page for {url}: {e}")
              # Return deduplicated list of links
        return list(set(all_found_links))

async def test_crawler(url: str) -> None:
    """Test function to verify crawler functionality.
    
    Args:
        url (str): URL to test crawling
    """
    try:
        async with IndexCrawler(base_url=url, max_depth=1) as crawler:
            logger.info(f"Starting crawl of {url}")
            links = await crawler.crawl()
            logger.info(f"Found {len(links)} links:")
            for link in links:
                logger.info(f"  - {link}")
    except Exception as e:
        logger.error(f"Crawler test failed: {e}")
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = "https://interviewing.io/blog"
    
    asyncio.run(test_crawler(test_url))

# Example Usage (for testing)
async def main():
    # Replace with the base URL of the site you want to crawl
    # For example, the interviewing.io blog or topics pages
    target_base_url = "https://interviewing.io/blog" 
    # target_base_url = "https://interviewing.io/topics#companies"
    # target_base_url = "https://nilmamano.com/blog/category/dsa"

    crawler = IndexCrawler(base_url=target_base_url, max_depth=1) # max_depth=1 to limit scope for testing
    async with crawler: # Use async with for proper setup/teardown
        all_links = await crawler.crawl()
        print("\nFound URLs:")
        for link in all_links:
            print(link)
        print(f"\nTotal unique URLs found: {len(all_links)}")

if __name__ == "__main__":
    asyncio.run(main())