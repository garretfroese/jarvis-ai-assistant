import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from src.routes.chat_simple import chat_bp
from src.routes.chatrelay import chatrelay_bp
from src.routes.modes import modes_bp
from src.routes.files import files_bp
from src.routes.diagnostics import diagnostics_bp
from src.routes.logs import logs_bp
from src.routes.plugins import plugins_bp
from src.routes.auth import auth_bp
from src.routes.users import users_bp
from src.utils.auth_middleware import require_auth, optional_auth

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

# Register authentication blueprints first
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)

# Register other blueprints
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
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

# Health check endpoint
@app.route('/health')
@optional_auth
def health_check():
    from src.services.google_auth import google_auth
    
    auth_status = google_auth.get_auth_status()
    
    return {
        "status": "healthy",
        "version": "4.0.0",
        "features": [
            "chat",
            "openai_integration",
            "streaming_responses",
            "conversation_memory",
            "mode_switching",
            "file_processing",
            "system_diagnostics",
            "webhook_relay",
            "action_execution",
            "command_logging",
            "log_dashboard",
            "plugin_system",
            "plugin_management",
            "google_oauth_auth",
            "user_management",
            "role_based_access",
            "session_management"
        ],
        "authentication": {
            "enabled": True,
            "provider": "google_oauth",
            "configured": auth_status['configured'],
            "active_sessions": auth_status['active_sessions']
        }
    }

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)

