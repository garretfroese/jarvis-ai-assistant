import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from src.routes.chat_simple import chat_bp
from src.routes.chatrelay import chatrelay_bp
from src.routes.modes import modes_bp
from src.routes.files import files_bp
from src.routes.diagnostics import diagnostics_bp
from src.routes.logs import logs_bp
from src.routes.plugins import plugins_bp

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.getenv('SESSION_SECRET', 'jarvis-secret-key-2024')

# Enable CORS for all routes with credentials support
CORS(app, 
     origins=["*"],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Register blueprints
app.register_blueprint(chat_bp, url_prefix='/api')
app.register_blueprint(chatrelay_bp, url_prefix='/api')
app.register_blueprint(modes_bp)
app.register_blueprint(files_bp)
app.register_blueprint(diagnostics_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(plugins_bp)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return jsonify({"error": "Static folder not configured"}), 500
    
    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        return send_from_directory(static_folder_path, 'index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check OpenAI API key
        openai_configured = bool(os.getenv('OPENAI_API_KEY'))
        
        # Check enabled tools
        enabled_tools = os.getenv('ENABLED_TOOLS', '').split(',')
        
        return jsonify({
            "status": "healthy",
            "service": "Jarvis AI Assistant",
            "version": "2.0.0",
            "environment": os.getenv('FLASK_ENV', 'development'),
            "openai_configured": openai_configured,
            "enabled_tools": enabled_tools,
            "features": [
                "chat_interface",
                "mode_switching", 
                "file_processing",
                "command_logging",
                "plugin_management",
                "system_diagnostics",
                "workflow_automation",
                "chatrelay_webhooks"
            ],
            "authentication": {
                "enabled": False,
                "provider": "none",
                "note": "Simplified deployment without OAuth"
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    return jsonify({
        "api_status": "operational",
        "endpoints": [
            "/health",
            "/api/chat",
            "/api/modes",
            "/api/files",
            "/api/logs", 
            "/api/plugins",
            "/api/diagnose"
        ]
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)

