from playwright.async_api import async_playwright # Changed from sync_api
import asyncio
from bs4 import BeautifulSoup
import re

class SubstackScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.playwright = None

    async def __aenter__(self): # Changed to async context manager
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb): # Changed to async context manager
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def scrape_page(self, url):
        if not self.browser:
            raise Exception("Browser not initialized. Call __aenter__ first.")
        
        page = await self.browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "No title found"
            
            # Substack specific content extraction (example)
            # This might need adjustment based on Substack's current HTML structure
            content_divs = soup.select('div.available-content') # Common class for Substack content
            if not content_divs:
                # Fallback to a more generic content area if specific class not found
                content_divs = soup.select('article') # A common tag for main content
            
            markdown_content = ""
            if content_divs:
                # Process the first found content container
                # You might need more sophisticated logic if there are multiple or nested containers
                main_content_area = content_divs[0]
                for element in main_content_area.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'pre', 'blockquote', 'figure']):
                    if element.name.startswith('h'):
                        level = int(element.name[1])
                        markdown_content += f"{'#' * level} {element.get_text(strip=True)}\n\n"
                    elif element.name == 'p':
                        markdown_content += f"{element.get_text()}\n\n"
                    elif element.name == 'li':
                        # Basic list item, assumes it's part of a ul or ol handled by parent or needs more context
                        markdown_content += f"- {element.get_text(strip=True)}\n"
                    elif element.name == 'pre':
                        code_tag = element.find('code')
                        code_text = code_tag.get_text() if code_tag else element.get_text()
                        # Try to guess language (very basic)
                        lang = code_tag.get('class', [''])[0].replace('language-', '') if code_tag and code_tag.get('class') else ''
                        markdown_content += f"``` {lang}\n{code_text.strip()}\n```\n\n"
                    elif element.name == 'blockquote':
                        markdown_content += f"> {element.get_text(strip=True)}\n\n"
                    elif element.name == 'figure': # For images, typically within figures
                        img_tag = element.find('img')
                        if img_tag and img_tag.get('src'):
                            alt_text = img_tag.get('alt', '')
                            markdown_content += f"![{alt_text}]({img_tag.get('src')})\n\n"
            else:
                markdown_content = "Content not found or structure unrecognized."

            return {
                "title": title,
                "content": markdown_content.strip(),
                "source_url": url,
                "content_type": "blog" # Or more specific if detectable
            }
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return {
                "title": "Error",
                "content": f"Failed to scrape content from {url}. Error: {e}",
                "source_url": url,
                "content_type": "error"
            }
        finally:
            await page.close()

    async def scrape_all_posts(self, archive_url):
        # This is a placeholder. Substack archive pages can be complex.
        # You'd typically need to find links to individual posts from the archive page.
        # For now, let's assume archive_url is a single post or we scrape it directly.
        # A more robust implementation would parse the archive, find post links, and call scrape_page for each.
        print(f"Warning: `scrape_all_posts` for Substack is simplified. Scraping {archive_url} as a single page.")
        return [await self.scrape_page(archive_url)]

# Example Usage (for testing, typically called from main.py or similar)
async def main():
    # Example Substack post URL
    # Replace with a real Substack URL you want to test
    substack_url = "https://shreycation.substack.com/p/the-art-of-the-cold-email" 
    scraper = SubstackScraper()
    async with scraper: # Use async with for proper setup/teardown
        # To scrape a single page
        scraped_data = await scraper.scrape_page(substack_url)
        print(scraped_data)

        # To scrape "all" posts (currently simplified to one page)
        # substack_archive_url = "https://yoursubstack.substack.com/archive"
        # all_posts_data = await scraper.scrape_all_posts(substack_archive_url)
        # for post_data in all_posts_data:
        #     print(post_data)

if __name__ == "__main__":
    asyncio.run(main())