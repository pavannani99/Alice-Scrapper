import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from typing import Set, List, Deque
from collections import deque

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndexCrawler:
    def __init__(self, base_url: str, max_depth: int = 2, headless: bool = True):
        self.base_url = base_url.rstrip('/')
        self.max_depth = max_depth
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.visited_urls: Set[str] = set()

    async def __aenter__(self):
        """Initialize the browser using an async context manager"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-dev-shm-usage', '--no-sandbox']
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources using an async context manager"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def _extract_links(self, current_url: str, page_content: str) -> Set[str]:
        """Extract valid links from page content"""
        soup = BeautifulSoup(page_content, 'html.parser')
        links = set()
        base_domain = urlparse(self.base_url).netloc

        for anchor in soup.find_all('a', href=True):
            href = anchor['href'].strip()
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue

            full_url = urljoin(current_url, href)
            parsed_url = urlparse(full_url)

            if (parsed_url.netloc == base_domain and
                any(pattern in parsed_url.path.lower() for pattern in ['/blog/', '/post/', '/article/', '/guide/'])):
                links.add(full_url)
        return links

    async def crawl(self) -> List[str]:
        """Crawl the base URL and return all found article links using BFS."""
        if not self.browser:
            raise Exception("Browser not started. Use 'async with IndexCrawler(...) as crawler:'")

        queue: Deque[(str, int)] = deque([(self.base_url, 0)])
        found_links: Set[str] = set()

        page = await self.browser.new_page()
        try:
            while queue:
                current_url, depth = queue.popleft()

                if current_url in self.visited_urls or depth >= self.max_depth:
                    continue

                self.visited_urls.add(current_url)
                logger.info(f"Crawling: {current_url} at depth {depth}")

                try:
                    await page.goto(current_url, wait_until="networkidle", timeout=30000)
                    page_content = await page.content()
                    
                    parsed_url = urlparse(current_url)
                    if any(pattern in parsed_url.path.lower() for pattern in ['/blog/', '/post/', '/article/', '/guide/']):
                        found_links.add(current_url)

                    new_links = self._extract_links(current_url, page_content)
                    for link in new_links:
                        if link not in self.visited_urls:
                            queue.append((link, depth + 1))
                except Exception as e:
                    logger.error(f"Error crawling {current_url}: {e}")
                    continue
        finally:
            await page.close()

        return list(found_links)

def test_crawler(url: str) -> None:
    """Test function to verify crawler functionality."""
    try:
        with IndexCrawler(base_url=url, max_depth=1) as crawler:
            logger.info(f"Starting crawl of {url}")
            links = crawler.crawl()
            logger.info(f"Found {len(links)} links:")
            for link in links:
                logger.info(f"  - {link}")
    except Exception as e:
        logger.error(f"Crawler test failed: {e}")

def main():
    """Main function for standalone testing."""
    target_base_url = "https://interviewing.io/blog"
    
    with IndexCrawler(base_url=target_base_url, max_depth=1) as crawler:
        all_links = crawler.crawl()
        print("\nFound URLs:")
        for link in all_links:
            print(link)
        print(f"\nTotal unique URLs found: {len(all_links)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        test_crawler(test_url)
    else:
        main()