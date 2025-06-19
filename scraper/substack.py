from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

class SubstackScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.playwright = None

    def start(self):
        """Initialize the browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        return self

    def stop(self):
        """Clean up resources"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def scrape_page(self, url):
        """Scrape a Substack article page"""
        if not self.browser:
            raise Exception("Browser not initialized. Call start() first.")
        
        page = self.browser.new_page()
        try:
            page.goto(url, wait_until="networkidle")
            content = page.content()
            
            # Parse content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Get title
            title = soup.find('h1').get_text().strip() if soup.find('h1') else ''
            
            # Get article content
            article = soup.find('article')
            if not article:
                return {
                    "content_type": "error",
                    "content": "Could not find article content"
                }
            
            # Clean article content
            for tag in article.find_all(['script', 'style']):
                tag.decompose()
                
            content = article.get_text('\n', strip=True)
            
            # Get author
            author_elem = soup.find('a', class_=re.compile(r'author|writer'))
            author = author_elem.get_text().strip() if author_elem else 'Unknown'
            
            return {
                "title": title,
                "content": content,
                "content_type": "blog",
                "source_url": url,
                "author": author,
                "user_id": ""
            }
            
        except Exception as e:
            return {
                "content_type": "error",
                "content": str(e)
            }
        finally:
            page.close()

    def scrape_all_posts(self, archive_url):
        # This is a placeholder. Substack archive pages can be complex.
        # You'd typically need to find links to individual posts from the archive page.
        # For now, let's assume archive_url is a single post or we scrape it directly.
        # A more robust implementation would parse the archive, find post links, and call scrape_page for each.
        print(f"Warning: `scrape_all_posts` for Substack is simplified. Scraping {archive_url} as a single page.")
        return [self.scrape_page(archive_url)]

# Example Usage (for testing, typically called from main.py or similar)
def main():
    # Example Substack post URL
    # Replace with a real Substack URL you want to test
    substack_url = "https://shreycation.substack.com/p/the-art-of-the-cold-email" 
    scraper = SubstackScraper()
    scraper.start() # Initialize the scraper
    try:
        # To scrape a single page
        scraped_data = scraper.scrape_page(substack_url)
        print(scraped_data)

        # To scrape "all" posts (currently simplified to one page)
        # substack_archive_url = "https://yoursubstack.substack.com/archive"
        # all_posts_data = scraper.scrape_all_posts(substack_archive_url)
        # for post_data in all_posts_data:
        #     print(post_data)
    finally:
        scraper.stop() # Ensure resources are cleaned up

if __name__ == "__main__":
    main()