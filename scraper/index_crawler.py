from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from typing import Set, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndexCrawler:
    def __init__(self, base_url: str, max_depth: int = 2, headless: bool = True):
        self.base_url = base_url.rstrip('/')
        self.max_depth = max_depth
        self.visited_urls = set()
        self.headless = headless
        self.playwright = None
        self.browser = None

    def start(self):
        """Initialize the browser"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-dev-shm-usage', '--no-sandbox']
            )
            return self
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    def stop(self):
        """Clean up resources"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise

    def _extract_links(self, current_url: str, page_content: str) -> Set[str]:
        """Extract valid links from page content"""
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

                # Only include links from the same domain and that are blog posts
                if (parsed_url.netloc == base_domain and
                    any(pattern in parsed_url.path.lower() for pattern in ['/blog/', '/post/', '/article/', '/guide/'])):
                    links.add(full_url)

        except Exception as e:
            logger.error(f"Error extracting links from {current_url}: {e}")

        return links

    def crawl(self, depth: int = 0) -> List[str]:
        """Crawl the base URL and return all found article links"""
        if depth >= self.max_depth:
            return list(self.visited_urls)

        try:
            if not self.browser:
                self.start()

            page = self.browser.new_page()
            try:
                page.goto(self.base_url, wait_until="networkidle", timeout=30000)
                page_content = page.content()
                
                # Extract links from the current page
                new_links = self._extract_links(self.base_url, page_content)
                
                # Add new links to visited set
                self.visited_urls.update(new_links)
                
                # Recursively crawl new links
                for link in new_links:
                    if link not in self.visited_urls:
                        try:
                            page.goto(link, wait_until="networkidle", timeout=30000)
                            page_content = page.content()
                            sub_links = self._extract_links(link, page_content)
                            self.visited_urls.update(sub_links)
                        except Exception as e:
                            logger.error(f"Error crawling {link}: {e}")
                            continue
            finally:
                page.close()

        except Exception as e:
            logger.error(f"Error during crawl: {e}")
        finally:
            self.stop()

        return list(self.visited_urls)

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