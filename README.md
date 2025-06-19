# Technical Content Scraper

A scalable scraper system to import technical knowledge from various sources (blogs, PDFs, Substack articles) into a structured Markdown format.

## Features

- 🌐 Automated scraping from technical blogs (interviewing.io, nilmamano.com, etc.)
- 📚 Smart PDF parsing with chapter detection and metadata extraction
- ✍️ Specialized Substack article scraping
- 🔄 Automatic content structuring to Markdown
- 🎯 Index page crawling support
- 🚀 FastAPI-based REST API
- 🖥️ Streamlit web interface

## Project Structure

```
.
├── app.py                  # Streamlit web interface
├── main.py                # FastAPI application
├── requirements.txt       # Project dependencies
├── scraper/
│   ├── generic_scraper.py # Universal content scraper
│   ├── substack.py       # Substack-specific scraper
│   ├── pdf_parser.py     # PDF processing
│   └── index_crawler.py  # URL crawling for index pages
├── exporter/
│   └── to_json.py        # JSON output formatter
└── samples/              # Example output formats
```

## Installation

1. Set up Python environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
python -m playwright install chromium
```

## Usage

### Start the Backend Server

```bash
python main.py
```
The API server runs at `http://localhost:8000`

### Launch the Web Interface

```bash
streamlit run app.py
```

### API Endpoints

1. **Scrape URL Content**
```bash
curl -X POST "http://localhost:8000/scrape/url" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://interviewing.io/blog/post-title", "team_id": "default"}'
```

2. **Process PDF Document**
```bash
curl -X POST "http://localhost:8000/scrape/pdf" \
     -F "file=@document.pdf" \
     -F "team_id=default"
```

3. **Crawl Index Pages**
```bash
curl -X POST "http://localhost:8000/scrape/index" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://interviewing.io/topics#companies", "team_id": "default"}'
```

## Supported Sources

- Technical Blogs:
  - interviewing.io/blog
  - interviewing.io/topics#companies
  - nilmamano.com/blog/category/dsa
  - quill.co/blog
- PDF Documents (with automatic chapter detection)
- Substack Articles

## Output Format

```json
{
  "team_id": "default",
  "items": [
    {
      "title": "Article Title",
      "content": "## Markdown Content\n\nStructured content...",
      "content_type": "blog|book|substack|other",
      "source_url": "https://source.url",
      "author": "Author Name",
      "user_id": ""
    }
  ]
}
```

## Development

### Libraries Used

- FastAPI for API endpoints
- Playwright for browser automation
- PDFPlumber for PDF processing
- BeautifulSoup4 for HTML parsing
- Streamlit for web interface

## Requirements

- Python 3.9+
- See `requirements.txt` for full package list

## License

MIT