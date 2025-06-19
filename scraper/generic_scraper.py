from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Playwright, Browser
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin
import re

class GenericScraper:
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,  # Run in headless mode
            args=['--disable-dev-shm-usage']  # Helpful for Linux/Docker environments
        )
        return self  # Important: __aenter__ must return the instance
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            print(f"Error in GenericScraper __aexit__: {e}")
            # Optionally re-raise or handle as appropriate
            pass
    
    def _clean_text(self, text: str) -> str:
        # This method doesn't need to be async as it doesn't do I/O
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def _extract_author(self, soup: BeautifulSoup, url: str) -> str:
        # This method doesn't need to be async as it works with already fetched data
        meta_tags = [
            {"name": "author"},
            {"property": "article:author"},
            {"property": "og:author"},
        ]

        for tag in meta_tags:
            meta = soup.find("meta", attrs=tag)
            if meta and meta.get("content"):
                return meta["content"].strip()

        author_tag = soup.select_one('a[rel="author"], span.author, div.author')
        if author_tag:
            return author_tag.get_text(strip=True)

        return urlparse(url).netloc.replace("www.", "")
    
    def _extract_code_blocks(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        # This method doesn't need to be async as it works with already fetched data
        code_blocks = []
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                lang = ''
                for class_ in code.get('class', []):
                    if class_.startswith(('language-', 'lang-')):
                        lang = class_.split('-')[1]
                        break
                
                code_blocks.append({
                    'language': lang,
                    'content': self._clean_text(code.get_text())
                })
        return code_blocks
    
    def _convert_to_markdown(self, soup: BeautifulSoup) -> str:
        # This method doesn't need to be async as it works with already fetched data
        markdown = []
        
        # Extract title
        title = soup.find('h1')
        if title:
            markdown.append(f"# {self._clean_text(title.get_text())}\n")
        
        # Process other elements
        for element in soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6', 'p', 'pre', 'ul', 'ol']):
            if element.name.startswith('h'):
                level = element.name[1]
                markdown.append(f"{'#' * int(level)} {self._clean_text(element.get_text())}\n")
            
            elif element.name == 'p':
                markdown.append(f"{self._clean_text(element.get_text())}\n\n")
            
            elif element.name == 'pre':
                code = element.find('code')
                if code:
                    lang = ''
                    for class_ in code.get('class', []):
                        if class_.startswith(('language-', 'lang-')):
                            lang = class_.split('-')[1]
                            break
                    markdown.append(f"```{lang}\n{code.get_text()}\n```\n")
            
            elif element.name in ['ul', 'ol']:
                for li in element.find_all('li'):
                    prefix = '* ' if element.name == 'ul' else '1. '
                    markdown.append(f"{prefix}{self._clean_text(li.get_text())}\n")
                markdown.append('\n')
        
        return ''.join(markdown)
    
    def _get_pagination_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        # This method doesn't need to be async as it works with already fetched data
        pagination_links = []
        pagination = soup.find_all(['a', 'link'], href=True, text=re.compile(r'\d+|next|→'))
        
        for link in pagination:
            href = link['href']
            if href.startswith(('/', 'http')):
                full_url = urljoin(base_url, href)
                pagination_links.append(full_url)
        
        return pagination_links
    
    async def scrape(self, url: str) -> Dict:
        try:
            page = await self.browser.new_page()
            # Set shorter timeouts for better user experience
            page.set_default_timeout(15000)  # 15 seconds timeout
            
            try:
                # Add headers to mimic a real browser
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
                })
                
                # More efficient page load strategy
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                
                # Wait for specific content instead of networkidle
                await page.wait_for_selector('h1, article, .post-content, .entry-content', timeout=10000)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                title = soup.find('h1')
                title_text = self._clean_text(title.get_text()) if title else 'Untitled'
                
                author = self._extract_author(soup, url)
                markdown_content = self._convert_to_markdown(soup)
                
                # Determine content type based on URL and content
                content_type = 'blog'
                url_lower = url.lower()
                
                if 'interviewing.io' in url_lower:
                    if 'topics#companies' in url_lower:
                        content_type = 'company_guide'
                    elif 'learn#interview-guides' in url_lower or '/blog/' in url_lower:
                        content_type = 'blog'
                elif 'nilmamano.com' in url_lower and 'category/dsa' in url_lower:
                    content_type = 'blog'
                elif 'quill.co/blog' in url_lower:
                    content_type = 'blog'
                
                return {
                    'title': title_text,
                    'content': markdown_content,
                    'content_type': content_type,
                    'source_url': url,
                    'author': author,
                    'user_id': ''
                }
            finally:
                await page.close()
                
        except Exception as e:
            return {
                'content_type': 'error',
                'content': f"Failed to scrape URL: {str(e)}"
            }