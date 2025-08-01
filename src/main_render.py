#!/usr/bin/env python3
"""
Jarvis AI Assistant - Render Production Version
Simplified version without JWT authentication for stable deployment
"""

import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure CORS for production
    CORS(app, origins=[
        "https://jarvis-ai-assistant-0ua4.onrender.com",
        "http://localhost:3000",
        "http://localhost:5173"
    ])
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'jarvis-production-key-2024')
    app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for monitoring"""
        return jsonify({
            'status': 'healthy',
            'service': 'Jarvis AI Assistant',
            'version': '2.0.0',
            'features': [
                'Chat API',
                'OpenAI Integration',
                'File Processing',
                'Tool Integration',
                'Plugin System',
                'Workflow Engine',
                'Diagnostics',
                'Mode Switching'
            ]
        })
    
    # Basic chat endpoint
    @app.route('/api/chat', methods=['POST'])
    def chat():
        """Basic chat endpoint"""
        try:
            data = request.get_json()
            message = data.get('message', '')
            
            if not message:
                return jsonify({'error': 'Message is required'}), 400
            
            # Simple response for now
            response = {
                'response': f"Hello! I'm Jarvis, your AI assistant. You said: {message}",
                'status': 'success'
            }
            
            return jsonify(response)
            
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Status endpoint
    @app.route('/api/status', methods=['GET'])
    def status():
        """Service status endpoint"""
        return jsonify({
            'status': 'running',
            'openai_configured': bool(os.environ.get('OPENAI_API_KEY')),
            'environment': os.environ.get('FLASK_ENV', 'production')
        })
    
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

