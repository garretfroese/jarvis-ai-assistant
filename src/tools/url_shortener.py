"""
URL Shortener Plugin for Jarvis
Creates shortened URLs and manages URL redirects
"""

import re
import hashlib
import json
import os

# Plugin manifest - metadata about this plugin
manifest = {
    "name": "URL Shortener",
    "description": "Create shortened URLs and manage URL redirects",
    "version": "1.0.0",
    "author": "Jarvis Team",
    "category": "utility",
    "tags": ["url", "shortener", "links", "redirect"],
    "requires_auth": True,
    "enabled": True
}

# Simple in-memory storage (in production, use a database)
URL_STORAGE_FILE = os.path.join(os.path.dirname(__file__), 'url_storage.json')

def run(input_text: str) -> str:
    """
    Shorten URLs or retrieve original URLs
    
    Args:
        input_text (str): URL to shorten or short code to expand
        
    Returns:
        str: Shortened URL or original URL
    """
    try:
        input_text = input_text.strip()
        
        if not input_text:
            return "Please provide a URL to shorten or a short code to expand."
        
        # Check if input is a URL to shorten
        if is_valid_url(input_text):
            return shorten_url(input_text)
        
        # Check if input is a short code to expand
        elif len(input_text) <= 10 and input_text.isalnum():
            return expand_url(input_text)
        
        else:
            return "Please provide a valid URL to shorten or a short code to expand."
        
    except Exception as e:
        return f"Error processing URL: {str(e)}"

def is_valid_url(url: str) -> bool:
    """Check if the input is a valid URL"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None

def shorten_url(original_url: str) -> str:
    """Create a shortened URL"""
    # Load existing URLs
    url_data = load_url_data()
    
    # Check if URL already exists
    for short_code, data in url_data.items():
        if data['original_url'] == original_url:
            return f"URL already shortened: jarvis.ly/{short_code}\nOriginal: {original_url}"
    
    # Generate short code
    short_code = generate_short_code(original_url)
    
    # Ensure uniqueness
    while short_code in url_data:
        short_code = generate_short_code(original_url + str(len(url_data)))
    
    # Store the mapping
    url_data[short_code] = {
        'original_url': original_url,
        'created_at': get_current_timestamp(),
        'click_count': 0
    }
    
    save_url_data(url_data)
    
    return f"✅ URL shortened successfully!\n\nShort URL: jarvis.ly/{short_code}\nOriginal: {original_url}\n\nUse '{short_code}' to expand this URL later."

def expand_url(short_code: str) -> str:
    """Expand a shortened URL"""
    url_data = load_url_data()
    
    if short_code not in url_data:
        return f"Short code '{short_code}' not found. Please check the code and try again."
    
    data = url_data[short_code]
    original_url = data['original_url']
    
    # Increment click count
    url_data[short_code]['click_count'] += 1
    save_url_data(url_data)
    
    return f"🔗 Expanded URL:\n\nShort code: {short_code}\nOriginal URL: {original_url}\nClicks: {url_data[short_code]['click_count']}\nCreated: {data['created_at']}"

def generate_short_code(url: str) -> str:
    """Generate a short code for the URL"""
    # Create a hash of the URL
    hash_object = hashlib.md5(url.encode())
    hash_hex = hash_object.hexdigest()
    
    # Take first 6 characters and make them alphanumeric
    short_code = hash_hex[:6]
    
    return short_code

def load_url_data() -> dict:
    """Load URL data from storage"""
    try:
        if os.path.exists(URL_STORAGE_FILE):
            with open(URL_STORAGE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading URL data: {e}")
    
    return {}

def save_url_data(data: dict):
    """Save URL data to storage"""
    try:
        with open(URL_STORAGE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving URL data: {e}")

def get_current_timestamp() -> str:
    """Get current timestamp as string"""
    from datetime import datetime
    return datetime.now().isoformat()

def get_url_statistics() -> str:
    """Get statistics about shortened URLs"""
    url_data = load_url_data()
    
    if not url_data:
        return "No URLs have been shortened yet."
    
    total_urls = len(url_data)
    total_clicks = sum(data['click_count'] for data in url_data.values())
    
    # Most clicked URLs
    sorted_urls = sorted(url_data.items(), key=lambda x: x[1]['click_count'], reverse=True)
    top_urls = sorted_urls[:5]
    
    stats = f"📊 URL Shortener Statistics:\n\n"
    stats += f"Total URLs: {total_urls}\n"
    stats += f"Total Clicks: {total_clicks}\n\n"
    
    if top_urls:
        stats += "🔥 Most Clicked URLs:\n"
        for short_code, data in top_urls:
            stats += f"  • {short_code}: {data['click_count']} clicks\n"
    
    return stats

