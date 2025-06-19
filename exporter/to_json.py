from typing import Dict, List, Union
import json

class KnowledgeBaseExporter:
    def __init__(self):
        self.supported_content_types = [
            'blog',
            'podcast_transcript',
            'call_transcript',
            'linkedin_post',
            'reddit_comment',
            'book',
            'other'
        ]
    
    def _validate_content_type(self, content_type: str) -> str:
        """Validate and normalize content type."""
        content_type = content_type.lower()
        if content_type not in self.supported_content_types:
            return 'other'
        return content_type
    
    def _validate_content(self, content: Dict) -> Dict:
        """Validate and clean content dictionary."""
        required_fields = ['title', 'content', 'content_type', 'source_url', 'author', 'user_id']
        cleaned_content = {}
        
        for field in required_fields:
            # Get value with empty string as default
            value = content.get(field, '')
            
            # Special handling for content_type
            if field == 'content_type':
                value = self._validate_content_type(value)
            
            # Ensure all values are strings
            cleaned_content[field] = str(value)
        
        return cleaned_content
    
    def to_json(self, content: Union[Dict, List[Dict]], team_id: str = 'default') -> Dict:
        """Convert scraped content to knowledgebase JSON format."""
        # Handle both single items and lists of items
        if isinstance(content, dict):
            content = [content]
        
        # Validate and clean each content item
        cleaned_items = [self._validate_content(item) for item in content]
        
        # Return the standardized format
        return {
            "team_id": team_id,
            "items": cleaned_items
        }