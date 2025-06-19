import pdfplumber
from typing import Dict, List
import re
from PyPDF2 import PdfReader # Added for metadata extraction
import os # Added to help with title generation

class PDFParser:
    def __init__(self):
        self.min_chapter_length = 500  # Minimum characters for a chapter
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing extra whitespace and normalizing newlines."""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def _detect_chapters(self, text: str) -> List[Dict[str, str]]:
        """Detect chapter boundaries and split content into chapters."""
        chapters = []
        current_chapter = {'title': '', 'content': []}
        
        lines = text.split('\n')
        for line in lines:
            # Check for chapter headers (common patterns)
            chapter_match = re.match(
                r'^(?:Chapter|CHAPTER|Section|SECTION)\s+\d+[.:)]?\s*(.+)$',
                line.strip()
            )
            
            # Also check for numbered headers
            if not chapter_match:
                chapter_match = re.match(r'^\d+\.\s+(.+)$', line.strip())
            
            if chapter_match:
                # If we have content in the current chapter, save it
                if current_chapter['content'] and len(''.join(current_chapter['content'])) > self.min_chapter_length:
                    chapters.append({
                        'title': current_chapter['title'],
                        'content': '\n'.join(current_chapter['content'])
                    })
                
                # Start new chapter
                current_chapter = {
                    'title': chapter_match.group(1).strip(),
                    'content': []
                }
            else:
                # Add line to current chapter content
                if line.strip():
                    current_chapter['content'].append(line)
        
        # Add the last chapter
        if current_chapter['content'] and len(''.join(current_chapter['content'])) > self.min_chapter_length:
            chapters.append({
                'title': current_chapter['title'],
                'content': '\n'.join(current_chapter['content'])
            })
        
        return chapters
    
    def _convert_to_markdown(self, text: str, hyperlinks: List[Dict] = None) -> str:
        """Convert extracted text to markdown format, including hyperlinks."""
        markdown = []
        lines = text.split('\n')
        in_code_block = False
    
        # Create a sorted list of hyperlink positions for efficient lookup
        # Hyperlinks from pdfplumber usually have 'uri' and 'top'/'bottom' attributes
        # We'll simplify by just inserting the link at the start of its text if not already present
        # A more robust solution would involve character-level text replacement
        processed_hyperlinks = []
        if hyperlinks:
            for link in hyperlinks:
                # Ensure the link has a URI and some text associated with it
                # pdfplumber's hyperlink objects might vary; adjust as needed
                link_text = link.get('text', link.get('title', '')) # Get text or title
                uri = link.get('uri')
                if uri and link_text:
                    # Attempt to find this text in the main text to avoid duplication
                    # This is a simple check; more advanced logic might be needed
                    if link_text not in text:
                        processed_hyperlinks.append(f"[{link_text}]({uri})")
                    elif not f"[{link_text}]({uri})" in text and not f"]({uri})" in link_text:
                         # If link_text is already in text, but not as a markdown link, try to wrap it
                         # This is tricky and might need a more sophisticated approach
                         pass # For now, we'll rely on pdfplumber's text output
    
        # Prepend any unique hyperlinks that weren't part of the main text flow
        if processed_hyperlinks:
            markdown.append('\n'.join(processed_hyperlinks) + '\n\n')
    
        for line in lines:
            # Detect and format headers
            if re.match(r'^(?:Chapter|CHAPTER|Section|SECTION)\s+\d+', line.strip()):
                markdown.append(f"\n# {line.strip()}\n")
            elif re.match(r'^\d+\.\s+', line.strip()):
                markdown.append(f"\n## {line.strip()}\n")
            
            # Detect code blocks (simple heuristic)
            elif re.match(r'^\s{4,}\w+', line) or re.match(r'^[\\[\\]{}()\w]+\s*[=:]', line):
                if not in_code_block:
                    markdown.append('\n```\n')
                    in_code_block = True
                markdown.append(line)
            elif in_code_block and not line.strip():
                markdown.append('```\n')
                in_code_block = False
            
            # Regular paragraphs
            else:
                if in_code_block:
                    markdown.append('```\n')
                    in_code_block = False
                markdown.append(f"{line}\n")
        
        return ''.join(markdown)

    def parse(self, pdf_path: str) -> Dict:
        """Parse PDF content and return structured data."""
        all_text = []
        hyperlinks_data = [] # To store hyperlink objects
        title = 'Untitled Document' # Default title
        author = "Simhadri Pavan Kumar" # Default author

        try:
            reader = PdfReader(pdf_path)
            meta = reader.metadata
            if meta:
                author = meta.get('/Author', author) # Get author from metadata
                title = meta.get('/Title', title)    # Get title from metadata
        except Exception:
            # PyPDF2 might fail on some PDFs, proceed without metadata
            pass

        with pdfplumber.open(pdf_path) as pdf:
            # If title is still default, try to get it from the first page's text
            if title == 'Untitled Document' and pdf.pages:
                first_page_text_lines = pdf.pages[0].extract_text().split('\n')
                for line in first_page_text_lines:
                    if line.strip() and len(line.strip()) > 5: # Basic check for a meaningful line
                        title = line.strip()
                        break
            if title == 'Untitled Document': # Fallback to filename if still no title
                title = os.path.basename(pdf_path)

            for i, page in enumerate(pdf.pages):
                text = page.extract_text(x_tolerance=2, y_tolerance=2) # x_tolerance and y_tolerance can help with layout
                if text:
                    all_text.append(text)
                # Extract hyperlinks from the page
                # pdfplumber's hyperlink objects are under page.hyperlinks
                if page.hyperlinks:
                    for link in page.hyperlinks:
                        # Ensure we have a URI and try to get some descriptive text
                        link_obj = {
                            'uri': link.get('uri'),
                            'text': page.crop((link['x0'], link['top'], link['x1'], link['bottom'])).extract_text() or link.get('uri')
                        }
                        hyperlinks_data.append(link_obj)
        
        full_text = '\n'.join(all_text)
        
        # Content Type Detection
        content_type = 'other'
        if "Education" in full_text and "Skills" in full_text:
            content_type = "resume"
        elif "Chapter" in full_text or "CHAPTER" in full_text:
            content_type = "book"
        # Add more specific checks if needed, e.g., for 'paper'
        elif "Abstract" in full_text and "References" in full_text:
            content_type = "paper"

        # Detect chapters (or sections for resumes/papers)
        chapters = self._detect_chapters(full_text)
        
        if not chapters:
            chapters = [{
                'title': 'Document Content' if content_type != 'resume' else 'Summary', # More appropriate for resume
                'content': full_text
            }]
        
        markdown_chapters = []
        for chapter in chapters:
            # Pass hyperlinks to the conversion method
            markdown_chapters.append({
                'title': chapter['title'],
                'content': self._convert_to_markdown(chapter['content'], hyperlinks_data)
            })
        
        final_markdown = '\n\n'.join(
            f"# {chapter['title']}\n\n{chapter['content']}"
            for chapter in markdown_chapters
        )
        
        # If the main title is still 'Untitled Document' and we have chapters, use the first chapter's title
        if title == 'Untitled Document' and markdown_chapters and markdown_chapters[0]['title'] != 'Document Content':
            title = markdown_chapters[0]['title']
        elif title.lower() == 'document content' and markdown_chapters and markdown_chapters[0]['title']:
             title = markdown_chapters[0]['title'] # Prefer actual chapter title

        return {
            'title': title,
            'content': final_markdown,
            'content_type': content_type,
            'source_url': pdf_path,
            'author': author,
            'user_id': ''
        }
    
    def _detect_content_type(self, text: str) -> str:
        """Detect content type based on keywords and structure."""
        text_lower = text.lower()
        
        # Define keyword patterns
        patterns = {
            'interview_guide': [
                r'interview\s+prep',
                r'interview\s+question',
                r'coding\s+interview',
                r'technical\s+interview'
            ],
            'book': [
                r'chapter\s+\d+',
                r'table\s+of\s+contents',
                r'appendix',
                r'bibliography'
            ]
        }
        
        for content_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, text_lower):
                    return content_type
        
        return 'other'