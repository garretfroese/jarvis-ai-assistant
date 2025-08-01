"""
Weather Lookup Plugin for Jarvis
Provides weather information for specified locations
"""

import requests
import json

# Plugin manifest - metadata about this plugin
manifest = {
    "name": "Weather Lookup",
    "description": "Get current weather information for any location",
    "version": "1.0.0",
    "author": "Jarvis Team",
    "category": "information",
    "tags": ["weather", "location", "information"],
    "requires_auth": False,
    "enabled": True
}

def run(input_text: str) -> str:
    """
    Get weather information for a location
    
    Args:
        input_text (str): Location name or weather query
        
    Returns:
        str: Weather information or error message
    """
    try:
        # Extract location from input
        location = extract_location(input_text)
        if not location:
            return "Please specify a location for weather information. Example: 'weather in New York'"
        
        # For demo purposes, return mock weather data
        # In a real implementation, you would call a weather API
        weather_data = get_mock_weather(location)
        
        return format_weather_response(location, weather_data)
        
    except Exception as e:
        return f"Error getting weather information: {str(e)}"

def extract_location(input_text: str) -> str:
    """Extract location from user input"""
    # Simple extraction logic
    input_lower = input_text.lower()
    
    # Remove common weather-related words
    words_to_remove = ['weather', 'in', 'for', 'at', 'current', 'today', 'forecast']
    words = input_text.split()
    
    # Filter out weather-related words
    location_words = [word for word in words if word.lower() not in words_to_remove]
    
    if location_words:
        return ' '.join(location_words)
    
    return ""

def get_mock_weather(location: str) -> dict:
    """Get mock weather data (replace with real API call)"""
    # This is mock data - in a real implementation, you would call a weather API
    import random
    
    conditions = ["Sunny", "Cloudy", "Partly Cloudy", "Rainy", "Snowy"]
    
    return {
        "temperature": random.randint(15, 85),
        "condition": random.choice(conditions),
        "humidity": random.randint(30, 90),
        "wind_speed": random.randint(5, 25),
        "description": f"Current weather conditions in {location}"
    }

def format_weather_response(location: str, weather_data: dict) -> str:
    """Format weather data into a readable response"""
    return f"""🌤️ Weather in {location}:
    
Temperature: {weather_data['temperature']}°F
Condition: {weather_data['condition']}
Humidity: {weather_data['humidity']}%
Wind Speed: {weather_data['wind_speed']} mph

{weather_data['description']}"""

