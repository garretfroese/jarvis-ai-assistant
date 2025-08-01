"""
Web Search Plugin for Jarvis
Provides web search capabilities using search engines
"""

import requests
import json
from urllib.parse import quote_plus

# Plugin manifest - metadata about this plugin
manifest = {
    "name": "Web Search",
    "description": "Search the web for information on any topic",
    "version": "1.0.0",
    "author": "Jarvis Team",
    "category": "search",
    "tags": ["web", "search", "internet", "information"],
    "requires_auth": False,
    "enabled": True
}

def run(input_text: str) -> str:
    """
    Perform a web search
    
    Args:
        input_text (str): Search query
        
    Returns:
        str: Search results or error message
    """
    try:
        # Extract search query
        query = extract_search_query(input_text)
        if not query:
            return "Please provide a search query. Example: 'search for Python tutorials'"
        
        # Perform search (mock implementation)
        results = perform_search(query)
        
        return format_search_results(query, results)
        
    except Exception as e:
        return f"Error performing web search: {str(e)}"

def extract_search_query(input_text: str) -> str:
    """Extract search query from user input"""
    # Remove common search-related words
    words_to_remove = ['search', 'for', 'find', 'look', 'up', 'web', 'google']
    words = input_text.split()
    
    # Filter out search-related words
    query_words = []
    skip_next = False
    
    for i, word in enumerate(words):
        if skip_next:
            skip_next = False
            continue
            
        if word.lower() in words_to_remove:
            # Skip "for" after "search"
            if word.lower() == 'search' and i + 1 < len(words) and words[i + 1].lower() == 'for':
                skip_next = True
            continue
        
        query_words.append(word)
    
    return ' '.join(query_words) if query_words else input_text

def perform_search(query: str) -> list:
    """Perform web search (mock implementation)"""
    # This is a mock implementation
    # In a real implementation, you would use a search API like:
    # - Google Custom Search API
    # - Bing Search API
    # - DuckDuckGo API
    
    mock_results = [
        {
            "title": f"Best results for '{query}' - Comprehensive Guide",
            "url": f"https://example.com/guide/{quote_plus(query)}",
            "snippet": f"Learn everything about {query} with our comprehensive guide. Includes tutorials, examples, and best practices."
        },
        {
            "title": f"{query.title()} - Wikipedia",
            "url": f"https://en.wikipedia.org/wiki/{quote_plus(query)}",
            "snippet": f"Wikipedia article about {query}. Get detailed information, history, and references."
        },
        {
            "title": f"Top 10 {query} Tips and Tricks",
            "url": f"https://tips.com/{quote_plus(query)}",
            "snippet": f"Discover the best tips and tricks for {query}. Expert advice and practical solutions."
        }
    ]
    
    return mock_results

def format_search_results(query: str, results: list) -> str:
    """Format search results into a readable response"""
    if not results:
        return f"No search results found for: {query}"
    
    response = f"🔍 Search results for '{query}':\n\n"
    
    for i, result in enumerate(results[:5], 1):  # Limit to top 5 results
        response += f"{i}. **{result['title']}**\n"
        response += f"   {result['url']}\n"
        response += f"   {result['snippet']}\n\n"
    
    return response

def get_search_confidence(input_text: str) -> float:
    """
    Calculate confidence that this input is a search request
    
    Args:
        input_text (str): User input
        
    Returns:
        float: Confidence score between 0.0 and 1.0
    """
    search_keywords = [
        'search', 'find', 'look up', 'google', 'what is', 'who is', 
        'how to', 'where is', 'when did', 'why does', 'information about'
    ]
    
    input_lower = input_text.lower()
    confidence = 0.0
    
    for keyword in search_keywords:
        if keyword in input_lower:
            confidence += 0.3
    
    # Boost confidence for question words
    question_words = ['what', 'who', 'where', 'when', 'why', 'how']
    for word in question_words:
        if input_lower.startswith(word):
            confidence += 0.4
            break
    
    # Cap at 1.0
    return min(confidence, 1.0)

