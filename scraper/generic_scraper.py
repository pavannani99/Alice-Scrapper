from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Playwright, Browser
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin
import re

class GenericScraper:
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
    
    def start(self):
        """Initialize the browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,  # Run in headless mode
            args=['--disable-dev-shm-usage']  # Helpful for Linux/Docker environments
        )
        return self
    
    def stop(self):
        """Clean up resources"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            print(f"Error in GenericScraper stop: {e}")
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
    
    def scrape(self, url: str) -> Dict:
        """Scrape content from a URL"""
        try:
            page = self.browser.new_page()
            page.goto(url, wait_until="networkidle")
            
            # Get page content
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract content
            title = soup.find('title').text.strip() if soup.find('title') else ''
            
            # Get main content
            article = soup.find('article') or soup.find(class_=re.compile(r'post|article|content|entry'))
            if not article:
                # Fallback to main tag or div with article-like class
                article = soup.find('main') or soup.find('div', class_=re.compile(r'post|article|content|entry'))
            
            if not article:
                return {
                    "content_type": "error",
                    "content": "Could not find main content"
                }
                
            # Clean content
            for tag in article.find_all(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
                
            content = self._clean_text(article.get_text())
            author = self._extract_author(soup, url)
            
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
            if 'page' in locals():
                page.close()