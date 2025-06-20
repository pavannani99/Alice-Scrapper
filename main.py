from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import uvicorn
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from urllib.parse import urlparse
import asyncio

# Import our scraper modules
from scraper.generic_scraper import GenericScraper
from scraper.substack import SubstackScraper
from scraper.pdf_parser import PDFParser
from exporter.to_json import KnowledgeBaseExporter
from scraper.index_crawler import IndexCrawler

app = FastAPI(
    title="Technical Content Scraper",
    description="A scalable scraper system to import technical knowledge into a structured format"
)

# Thread pool for running sync code
thread_pool = ThreadPoolExecutor()

class ScrapingRequest(BaseModel):
    url: str
    team_id: Optional[str] = "default"

async def scrape_url_with_crawler(url: str) -> List[Dict]:
    """Handle scraping with index crawler for landing pages"""
    all_scraped_items = []
    
    async with IndexCrawler(base_url=url) as crawler:
        links = await crawler.crawl()
        if links:
            with GenericScraper() as scraper:
                for link in links:
                    try:
                        data = scraper.scrape(link)
                        if data and data.get("content_type") != "error":
                            all_scraped_items.append(data)
                    except Exception as e:
                        print(f"Error scraping link {link}: {e}")
        
    return all_scraped_items

def scrape_single_url(url: str) -> Dict:
    """Handle scraping a single URL"""
    try:
        with GenericScraper() as scraper:
            data = scraper.scrape(url)
            if not data:
                raise Exception("No data returned from scraper")
            return data
    except Exception as e:
        return {
            "content_type": "error",
            "content": str(e)
        }

@app.post("/scrape/url")
async def scrape_url_endpoint(request: ScrapingRequest):
    try:
        # Clean and validate URL
        url = request.url.strip()
        # Remove any duplicate protocols
        url = url.replace("https://https://", "https://")
        url = url.replace("http://http://", "http://")
        
        # Remove any trailing colons
        url = url.rstrip(":")
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            raise HTTPException(
                status_code=400,
                detail="Invalid URL format. URL must include protocol (http/https) and domain"
            )
        
        # Initialize variables
        all_scraped_items: List[Dict[str, Any]] = []
        
        # Run the synchronous scraping in a thread pool
        try:
            # For index pages, use the IndexCrawler
            is_index_page = any(pattern in parsed_url.path.lower() for pattern in [
                '/blog', '/posts', '/articles', '/guides', 'topics', 'learn'
            ])
            
            if is_index_page:
                items = await asyncio.get_event_loop().run_in_executor(
                    thread_pool,
                    partial(scrape_url_with_crawler, url=url)
                )
                if items:
                    all_scraped_items.extend(items)
                else:
                    # Fallback to single page if no items found
                    data = await asyncio.get_event_loop().run_in_executor(
                        thread_pool,
                        partial(scrape_single_url, url=url)
                    )
                    if data.get("content_type") != "error":
                        all_scraped_items.append(data)
                    else:
                        raise HTTPException(
                            status_code=500,
                            detail=data.get("content", "Failed to scrape URL")
                        )
            else:
                # For single pages, use the GenericScraper
                data = await asyncio.get_event_loop().run_in_executor(
                    thread_pool,
                    partial(scrape_single_url, url=url)
                )
                if data.get("content_type") != "error":
                    all_scraped_items.append(data)
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=data.get("content", "Failed to scrape URL")
                    )
                    
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error during scraping: {str(e)}"
            )

        if not all_scraped_items:
            raise HTTPException(
                status_code=404,
                detail="Could not scrape any content from the URL."
            )

        # Export to JSON format
        exporter = KnowledgeBaseExporter()
        result = exporter.to_json(all_scraped_items, team_id=request.team_id)
        return JSONResponse(content=result)

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/pdf")
async def scrape_pdf_endpoint(file: UploadFile, team_id: str = Form(default="default")):
    try:
        contents = await file.read()
        parser = PDFParser()
        temp_pdf_path = Path(f"temp_{file.filename}")
        with open(temp_pdf_path, 'wb') as f:
            f.write(contents)

        # Run PDF parsing in thread pool
        pdf_content_items = await asyncio.get_event_loop().run_in_executor(
            thread_pool,
            parser.parse,
            str(temp_pdf_path)
        )
        
        temp_pdf_path.unlink()  # Cleanup

        if not pdf_content_items:
            raise HTTPException(status_code=500, detail="Failed to parse PDF content.")

        exporter = KnowledgeBaseExporter()
        result = exporter.to_json(pdf_content_items, team_id=team_id)
        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)