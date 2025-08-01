"""
Minimal Jarvis AI Assistant for Render Deployment
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        "message": "Jarvis AI Assistant is running!",
        "status": "healthy",
        "version": "1.0.0"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "jarvis-ai-assistant"
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        # Simple echo response for now
        return jsonify({
            "response": f"Echo: {message}",
            "status": "success"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

