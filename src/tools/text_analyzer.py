"""
Text Analyzer Plugin for Jarvis
Analyzes text for various metrics and insights
"""

import re
from collections import Counter

# Plugin manifest - metadata about this plugin
manifest = {
    "name": "Text Analyzer",
    "description": "Analyze text for word count, readability, sentiment, and other metrics",
    "version": "1.0.0",
    "author": "Jarvis Team",
    "category": "analysis",
    "tags": ["text", "analysis", "metrics", "readability"],
    "requires_auth": False,
    "enabled": True
}

def run(input_text: str) -> str:
    """
    Analyze text and return various metrics
    
    Args:
        input_text (str): Text to analyze
        
    Returns:
        str: Analysis results
    """
    try:
        if not input_text.strip():
            return "Please provide text to analyze."
        
        # Perform various text analyses
        analysis = {
            "word_count": count_words(input_text),
            "character_count": len(input_text),
            "sentence_count": count_sentences(input_text),
            "paragraph_count": count_paragraphs(input_text),
            "average_words_per_sentence": calculate_avg_words_per_sentence(input_text),
            "readability_score": calculate_readability_score(input_text),
            "most_common_words": get_most_common_words(input_text, 5),
            "sentiment": analyze_sentiment(input_text)
        }
        
        return format_analysis_response(analysis)
        
    except Exception as e:
        return f"Error analyzing text: {str(e)}"

def count_words(text: str) -> int:
    """Count words in text"""
    words = re.findall(r'\b\w+\b', text.lower())
    return len(words)

def count_sentences(text: str) -> int:
    """Count sentences in text"""
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])

def count_paragraphs(text: str) -> int:
    """Count paragraphs in text"""
    paragraphs = text.split('\n\n')
    return len([p for p in paragraphs if p.strip()])

def calculate_avg_words_per_sentence(text: str) -> float:
    """Calculate average words per sentence"""
    word_count = count_words(text)
    sentence_count = count_sentences(text)
    
    if sentence_count == 0:
        return 0
    
    return round(word_count / sentence_count, 2)

def calculate_readability_score(text: str) -> str:
    """Calculate a simple readability score"""
    avg_words_per_sentence = calculate_avg_words_per_sentence(text)
    
    if avg_words_per_sentence < 10:
        return "Very Easy"
    elif avg_words_per_sentence < 15:
        return "Easy"
    elif avg_words_per_sentence < 20:
        return "Moderate"
    elif avg_words_per_sentence < 25:
        return "Difficult"
    else:
        return "Very Difficult"

def get_most_common_words(text: str, count: int = 5) -> list:
    """Get most common words in text"""
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
        'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
    }
    
    words = re.findall(r'\b\w+\b', text.lower())
    filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
    
    word_counts = Counter(filtered_words)
    return word_counts.most_common(count)

def analyze_sentiment(text: str) -> str:
    """Simple sentiment analysis based on keywords"""
    positive_words = {
        'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 
        'awesome', 'brilliant', 'perfect', 'love', 'like', 'happy', 'joy',
        'pleased', 'satisfied', 'delighted', 'thrilled', 'excited'
    }
    
    negative_words = {
        'bad', 'terrible', 'awful', 'horrible', 'disgusting', 'hate', 
        'dislike', 'angry', 'sad', 'disappointed', 'frustrated', 'annoyed',
        'upset', 'worried', 'concerned', 'problem', 'issue', 'wrong'
    }
    
    words = re.findall(r'\b\w+\b', text.lower())
    
    positive_count = sum(1 for word in words if word in positive_words)
    negative_count = sum(1 for word in words if word in negative_words)
    
    if positive_count > negative_count:
        return "Positive"
    elif negative_count > positive_count:
        return "Negative"
    else:
        return "Neutral"

def format_analysis_response(analysis: dict) -> str:
    """Format analysis results into a readable response"""
    response = "📊 Text Analysis Results:\n\n"
    
    response += f"📝 Basic Metrics:\n"
    response += f"  • Words: {analysis['word_count']}\n"
    response += f"  • Characters: {analysis['character_count']}\n"
    response += f"  • Sentences: {analysis['sentence_count']}\n"
    response += f"  • Paragraphs: {analysis['paragraph_count']}\n\n"
    
    response += f"📈 Readability:\n"
    response += f"  • Average words per sentence: {analysis['average_words_per_sentence']}\n"
    response += f"  • Readability level: {analysis['readability_score']}\n\n"
    
    response += f"🎭 Sentiment: {analysis['sentiment']}\n\n"
    
    if analysis['most_common_words']:
        response += f"🔤 Most Common Words:\n"
        for word, count in analysis['most_common_words']:
            response += f"  • {word}: {count}\n"
    
    return response

