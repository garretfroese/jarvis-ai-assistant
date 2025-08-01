"""
Web Scraper Plugin for Jarvis
Scrapes content from web pages and extracts useful information
"""

import requests
from urllib.parse import urlparse
import re

# Plugin manifest - metadata about this plugin
manifest = {
    "name": "Web Scraper",
    "description": "Extract content and information from web pages",
    "version": "1.0.0",
    "author": "Jarvis Team",
    "category": "web",
    "tags": ["scraping", "web", "content", "extraction"],
    "requires_auth": False,
    "enabled": True
}

def run(input_text: str) -> str:
    """
    Scrape content from a web page
    
    Args:
        input_text (str): URL or request to scrape a page
        
    Returns:
        str: Scraped content or error message
    """
    try:
        # Extract URL from input
        url = extract_url(input_text)
        if not url:
            return "Please provide a valid URL to scrape. Example: 'scrape https://example.com'"
        
        # Validate URL
        if not is_valid_url(url):
            return f"Invalid URL provided: {url}"
        
        # Scrape the page
        content = scrape_page(url)
        
        return format_scraped_content(url, content)
        
    except Exception as e:
        return f"Error scraping web page: {str(e)}"

def extract_url(input_text: str) -> str:
    """Extract URL from user input"""
    # Look for URLs in the input
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, input_text)
    
    if urls:
        return urls[0]
    
    # Check if input looks like a domain
    words = input_text.split()
    for word in words:
        if '.' in word and not word.startswith('.') and not word.endswith('.'):
            # Add https:// if not present
            if not word.startswith(('http://', 'https://')):
                return f"https://{word}"
            return word
    
    return ""

def is_valid_url(url: str) -> bool:
    """Validate if the URL is properly formatted"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def scrape_page(url: str) -> dict:
    """Scrape content from a web page (mock implementation)"""
    # This is a mock implementation
    # In a real implementation, you would use libraries like:
    # - BeautifulSoup for HTML parsing
    # - Selenium for JavaScript-heavy sites
    # - Scrapy for complex scraping tasks
    
    try:
        # Mock HTTP request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # In a real implementation, you would make the actual request:
        # response = requests.get(url, headers=headers, timeout=10)
        # response.raise_for_status()
        
        # Mock scraped content
        domain = urlparse(url).netloc
        
        mock_content = {
            "title": f"Sample Page from {domain}",
            "description": f"This is a sample description of content from {url}",
            "text_content": f"Sample text content extracted from {url}. This would contain the main text content of the page, cleaned and formatted for easy reading.",
            "links": [
                f"{url}/page1",
                f"{url}/page2",
                f"{url}/about"
            ],
            "images": [
                f"{url}/image1.jpg",
                f"{url}/image2.png"
            ],
            "word_count": 150,
            "status": "success"
        }
        
        return mock_content
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def format_scraped_content(url: str, content: dict) -> str:
    """Format scraped content into a readable response"""
    if content.get("status") == "error":
        return f"Failed to scrape {url}: {content.get('error', 'Unknown error')}"
    
    response = f"🌐 Scraped content from: {url}\n\n"
    
    if content.get("title"):
        response += f"**Title:** {content['title']}\n\n"
    
    if content.get("description"):
        response += f"**Description:** {content['description']}\n\n"
    
    if content.get("text_content"):
        # Truncate long content
        text = content['text_content']
        if len(text) > 500:
            text = text[:500] + "..."
        response += f"**Content:**\n{text}\n\n"
    
    if content.get("word_count"):
        response += f"**Word Count:** {content['word_count']}\n"
    
    if content.get("links"):
        response += f"**Links Found:** {len(content['links'])}\n"
    
    if content.get("images"):
        response += f"**Images Found:** {len(content['images'])}\n"
    
    return response

def get_scraping_confidence(input_text: str) -> float:
    """
    Calculate confidence that this input is a scraping request
    
    Args:
        input_text (str): User input
        
    Returns:
        float: Confidence score between 0.0 and 1.0
    """
    scraping_keywords = [
        'scrape', 'extract', 'get content', 'fetch', 'grab', 'pull data',
        'content from', 'text from', 'information from'
    ]
    
    input_lower = input_text.lower()
    confidence = 0.0
    
    # Check for scraping keywords
    for keyword in scraping_keywords:
        if keyword in input_lower:
            confidence += 0.4
    
    # Check for URLs
    url_pattern = r'https?://[^\s]+'
    if re.search(url_pattern, input_text):
        confidence += 0.5
    
    # Check for domain-like strings
    if '.' in input_text and any(tld in input_text for tld in ['.com', '.org', '.net', '.io', '.co']):
        confidence += 0.3
    
    # Cap at 1.0
    return min(confidence, 1.0)

