from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import uvicorn
import asyncio # Import asyncio

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

# Removed the global thread_pool executor. 
# For CPU-bound tasks like PDF parsing, we can use asyncio.to_thread (Python 3.9+)
# or loop.run_in_executor with None for the default executor if appropriate.

class ScrapingRequest(BaseModel):
    url: str
    team_id: Optional[str] = "default"

from urllib.parse import urlparse

from fastapi.background import BackgroundTasks
from asyncio import TimeoutError
import asyncio

@app.post("/scrape/url")
async def scrape_url_endpoint(request: ScrapingRequest):
    try:
        # Clean and validate URL
        url = request.url.strip()
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
        
        # Set a timeout for the entire scraping operation
        async with asyncio.timeout(60) as _:  # 60 second timeout for entire operation
            if "substack.com" in request.url:
                async with SubstackScraper() as scraper:
                    data = await scraper.scrape_page(request.url)
                    if data and data.get("content_type") != "error":
                        all_scraped_items.append(data)
                    elif data:
                        raise HTTPException(status_code=500, detail=f"Error scraping Substack: {data.get('content')}")
            
            # Handle known technical blog platforms
            elif any(pattern in request.url for pattern in [
                'interviewing.io/blog',
                'interviewing.io/topics#companies',
                'interviewing.io/learn#interview-guides',
                'nilmamano.com/blog/category/dsa',
                'quill.co/blog'
            ]):
                # For index pages, use the IndexCrawler
                if any(pattern in request.url for pattern in ['topics#companies', 'learn#interview-guides', '/blog']):
                    async with IndexCrawler(base_url=request.url) as crawler:
                        links = await crawler.crawl()
                        if links:
                            async with GenericScraper() as scraper:
                                for link in links:
                                    try:
                                        data = await scraper.scrape(link)
                                        if data and data.get("content_type") != "error":
                                            all_scraped_items.append(data)
                                    except Exception as e:
                                        print(f"Error scraping link {link}: {e}")
                else:
                    # For single pages, use the GenericScraper
                    async with GenericScraper() as scraper:
                        data = await scraper.scrape(request.url)
                        if data and data.get("content_type") != "error":
                            all_scraped_items.append(data)
            
            else:  # Default to GenericScraper for other URLs
                async with GenericScraper() as scraper:
                    data = await scraper.scrape(request.url)
                    if data and data.get("content_type") == "error":
                        raise HTTPException(status_code=500, detail=data.get("content", "Failed to scrape URL"))
                    all_scraped_items.append(data)

            if not all_scraped_items:
                raise HTTPException(status_code=404, detail="Could not scrape any content from the URL.")

            exporter = KnowledgeBaseExporter()
            result = exporter.to_json(all_scraped_items, team_id=request.team_id) 
            return JSONResponse(content=result)

    except HTTPException as he:
        raise he  # Re-raise HTTPException
    except Exception as e:
        error_msg = str(e)
        status_code = 500
        detail = f"An unexpected error occurred: {error_msg}"
        
        if isinstance(e, NotImplementedError):
            detail = "Browser automation error. Please make sure Playwright is properly installed."
            print("Try running: python -m playwright install chromium")
        elif "timeout" in error_msg.lower():
            status_code = 504
            detail = "Request timed out. The page might be too large or slow to respond."
        elif "not found" in error_msg.lower() or ("status_code=404" in error_msg.lower()):
            status_code = 404
            detail = "Page not found or content extraction failed. Please check the URL."
        
        raise HTTPException(status_code=status_code, detail=detail)

@app.post("/scrape/pdf")
async def scrape_pdf_endpoint(file: UploadFile, team_id: str = Form(default="default")):
    try:
        contents = await file.read()
        # For CPU-bound tasks like PDF parsing, use asyncio.to_thread (Python 3.9+)
        # or loop.run_in_executor.
        parser = PDFParser()
        # pdf_path is not strictly needed if parser can take bytes, but let's assume it needs a path
        temp_pdf_path = Path(f"temp_{file.filename}")
        with open(temp_pdf_path, 'wb') as f:
            f.write(contents)

        # This is a synchronous method, run it in a thread
        # In Python 3.9+ you can use: pdf_content_items = await asyncio.to_thread(parser.parse, str(temp_pdf_path))
        # For older versions or more control:
        loop = asyncio.get_event_loop()
        pdf_content_items = await loop.run_in_executor(None, parser.parse, str(temp_pdf_path)) # None uses default executor
        
        temp_pdf_path.unlink() # Cleanup

        if not pdf_content_items:
            raise HTTPException(status_code=500, detail="Failed to parse PDF content.")

        exporter = KnowledgeBaseExporter()
        # Assuming parser.parse returns a list of items (e.g., one per chapter/page chunk)
        # Change this line in the /scrape/pdf endpoint:
        # Old version causing error:
        # result = exporter.to_json_list(pdf_content_items, team_id=team_id)
        
        # New working version:
        result = exporter.to_json(pdf_content_items, team_id=team_id)
        return JSONResponse(content=result)
    except Exception as e:
        # Ensure temp file is cleaned up on error too
        if 'temp_pdf_path' in locals() and temp_pdf_path.exists():
            temp_pdf_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/scrape/index") # This endpoint might be redundant if /scrape/url handles index URLs
async def scrape_index_endpoint(request: ScrapingRequest):
    try:
        if not request.url.startswith('http'):
            raise HTTPException(status_code=400, detail="Invalid URL format for index crawling")

        all_scraped_items: List[Dict[str, Any]] = []
        async with IndexCrawler(base_url=request.url) as crawler:
            # crawl() should return a list of URLs to scrape
            links_to_scrape = await crawler.crawl(request.url)
        
        if not links_to_scrape:
            raise HTTPException(status_code=404, detail=f"No links found to scrape at {request.url}")

        # Now scrape each link using GenericScraper
        async with GenericScraper() as page_scraper:
            for link in links_to_scrape:
                try:
                    print(f"Scraping content from: {link}")
                    item_data = await page_scraper.scrape(link)
                    if item_data and item_data.get("content_type") != "error":
                        all_scraped_items.append(item_data)
                    elif item_data:
                        print(f"Skipping link {link} due to scraping error: {item_data.get('content')}")
                except Exception as e:
                    print(f"Error scraping individual link {link} from index: {e}")
        
        if not all_scraped_items:
            raise HTTPException(status_code=404, detail=f"Could not scrape content from any links found at {request.url}")

        exporter = KnowledgeBaseExporter()
        result = exporter.to_json_list(all_scraped_items, team_id=request.team_id)
        return JSONResponse(content=result)

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during index scraping: {str(e)}")

# Removed startup and shutdown events related to the global thread_pool
# FastAPI handles the asyncio event loop automatically.

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)