# Technical Content Scraper

A scalable scraper system to import technical knowledge (blogs, guides, PDFs, and books) into a structured Markdown-based knowledgebase format.

## Features

- 🌐 Dynamic scraping from any blog or website
- 📚 PDF parsing with automatic chapter detection
- ✨ Substack-specific support
- 🔄 Automatic conversion to clean, structured Markdown
- 🎯 No source-specific hardcoding
- 🚀 REST API for easy integration
- 📦 Standardized JSON output format

## Project Structure

```
.
├── main.py                 # FastAPI entry point
├── requirements.txt        # Python dependencies
├── scraper/
│   ├── generic_scraper.py # Universal blog scraper
│   ├── substack.py        # Substack-specific scraper
│   └── pdf_parser.py      # PDF parsing and chunking
└── exporter/
    └── to_json.py         # JSON format converter
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd scraper
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

```bash
python main.py
```

The server will start at `http://localhost:8000`

### API Endpoints

1. **Scrape from URL**

```bash
curl -X POST "http://localhost:8000/scrape/url" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/blog-post", "team_id": "your_team_id"}'
```

2. **Scrape from PDF**

```bash
curl -X POST "http://localhost:8000/scrape/pdf" \
     -F "file=@path/to/your/document.pdf" \
     -F "team_id=your_team_id"
```

### Output Format

The API returns JSON in the following format:

```json
{
  "team_id": "your_team_id",
  "items": [
    {
      "title": "Article Title",
      "content": "## Markdown Content...\n\n- Point 1\n- Point 2",
      "content_type": "blog|book|interview_guide|substack|other",
      "source_url": "https://original-source.com",
      "author": "Author Name",
      "user_id": ""
    }
  ]
}
```

## Supported Content Types

- Blog posts
- Technical books (PDF)
- Interview guides
- Substack articles
- General web content

## Development

### Adding New Scrapers

1. Create a new scraper class in the `scraper/` directory
2. Implement the `scrape()` method returning the standard content format
3. Add content type detection in `main.py`

### Testing

Test the implementation with various sources:

- Blog: `https://quill.co/blog`
- Substack: `https://shreycation.substack.com`
- PDF documents
- Interview guides

## License

MIT