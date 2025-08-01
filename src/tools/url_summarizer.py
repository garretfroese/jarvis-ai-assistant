"""
URL Summarizer Plugin for Jarvis
Fetches content from URLs and provides intelligent summaries
"""

import requests
import re
from urllib.parse import urlparse

# Plugin manifest - metadata about this plugin
manifest = {
    "name": "URL Summarizer",
    "description": "Fetch and summarize content from web pages and articles",
    "version": "1.0.0",
    "author": "Jarvis Team",
    "category": "content",
    "tags": ["url", "summarize", "content", "articles", "web"],
    "requires_auth": False,
    "enabled": True
}

def run(input_text: str) -> str:
    """
    Summarize content from a URL
    
    Args:
        input_text (str): URL or request to summarize a page
        
    Returns:
        str: Summary of the content or error message
    """
    try:
        # Extract URL from input
        url = extract_url(input_text)
        if not url:
            return "Please provide a valid URL to summarize. Example: 'summarize https://example.com/article'"
        
        # Validate URL
        if not is_valid_url(url):
            return f"Invalid URL provided: {url}"
        
        # Fetch and analyze content
        content = fetch_content(url)
        summary = generate_summary(content)
        
        return format_summary_response(url, summary)
        
    except Exception as e:
        return f"Error summarizing URL: {str(e)}"

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

def fetch_content(url: str) -> dict:
    """Fetch content from URL (mock implementation)"""
    # This is a mock implementation
    # In a real implementation, you would:
    # 1. Fetch the actual URL content
    # 2. Parse HTML with BeautifulSoup
    # 3. Extract main content using readability algorithms
    # 4. Clean and structure the text
    
    try:
        # Mock content based on URL
        domain = urlparse(url).netloc
        
        # Generate mock article content
        mock_content = {
            "title": f"Sample Article from {domain}",
            "author": "Sample Author",
            "publish_date": "2024-08-01",
            "content": generate_mock_article_content(url),
            "word_count": 850,
            "reading_time": "4 min read",
            "tags": ["technology", "innovation", "business"],
            "status": "success"
        }
        
        return mock_content
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def generate_mock_article_content(url: str) -> str:
    """Generate mock article content for demonstration"""
    domain = urlparse(url).netloc
    
    return f"""This is a comprehensive article from {domain} discussing important topics in technology and innovation. 

The article covers several key points:

1. **Technology Trends**: The latest developments in artificial intelligence, machine learning, and automation are reshaping industries across the globe. Companies are investing heavily in these technologies to stay competitive.

2. **Business Impact**: Organizations that successfully integrate new technologies are seeing significant improvements in efficiency, customer satisfaction, and revenue growth. The digital transformation is no longer optional but essential.

3. **Future Outlook**: Experts predict that the next decade will bring even more revolutionary changes, with emerging technologies like quantum computing and advanced robotics becoming mainstream.

4. **Challenges and Opportunities**: While these advances present incredible opportunities, they also bring challenges including workforce adaptation, ethical considerations, and the need for new regulatory frameworks.

The article concludes with actionable insights for businesses looking to navigate this rapidly evolving landscape and recommendations for staying ahead of the curve."""

def generate_summary(content: dict) -> dict:
    """Generate an intelligent summary of the content"""
    if content.get("status") == "error":
        return content
    
    # Mock AI-powered summarization
    # In a real implementation, you would use:
    # - OpenAI GPT for summarization
    # - Extractive summarization algorithms
    # - Key phrase extraction
    
    full_text = content.get("content", "")
    
    # Generate key points (mock implementation)
    key_points = [
        "Technology trends are reshaping industries globally",
        "Digital transformation is essential for business success",
        "AI and machine learning are driving efficiency improvements",
        "Future developments will include quantum computing and robotics",
        "Organizations need to balance opportunities with challenges"
    ]
    
    # Generate short summary
    short_summary = "This article discusses how emerging technologies like AI and machine learning are transforming businesses, highlighting both opportunities and challenges in the digital transformation landscape."
    
    return {
        "short_summary": short_summary,
        "key_points": key_points,
        "main_topics": content.get("tags", []),
        "reading_time": content.get("reading_time", "Unknown"),
        "word_count": content.get("word_count", 0),
        "status": "success"
    }

def format_summary_response(url: str, summary: dict) -> str:
    """Format summary into a readable response"""
    if summary.get("status") == "error":
        return f"Failed to summarize {url}: {summary.get('error', 'Unknown error')}"
    
    response = f"📄 Summary of: {url}\n\n"
    
    if summary.get("short_summary"):
        response += f"**Summary:**\n{summary['short_summary']}\n\n"
    
    if summary.get("key_points"):
        response += "**Key Points:**\n"
        for i, point in enumerate(summary['key_points'], 1):
            response += f"{i}. {point}\n"
        response += "\n"
    
    if summary.get("main_topics"):
        response += f"**Topics:** {', '.join(summary['main_topics'])}\n"
    
    if summary.get("reading_time"):
        response += f"**Reading Time:** {summary['reading_time']}\n"
    
    if summary.get("word_count"):
        response += f"**Word Count:** {summary['word_count']}\n"
    
    return response

def get_summarization_confidence(input_text: str) -> float:
    """
    Calculate confidence that this input is a summarization request
    
    Args:
        input_text (str): User input
        
    Returns:
        float: Confidence score between 0.0 and 1.0
    """
    summarization_keywords = [
        'summarize', 'summary', 'tldr', 'brief', 'overview', 'digest',
        'key points', 'main points', 'what does', 'explain', 'breakdown'
    ]
    
    input_lower = input_text.lower()
    confidence = 0.0
    
    # Check for summarization keywords
    for keyword in summarization_keywords:
        if keyword in input_lower:
            confidence += 0.4
    
    # Check for URLs
    url_pattern = r'https?://[^\s]+'
    if re.search(url_pattern, input_text):
        confidence += 0.5
    
    # Boost confidence for "summarize" + URL combination
    if 'summarize' in input_lower and re.search(url_pattern, input_text):
        confidence = 0.9
    
    # Cap at 1.0
    return min(confidence, 1.0)

