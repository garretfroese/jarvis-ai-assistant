"""
File Upload and Processing API Routes for Jarvis
Handles file upload, processing, and analysis endpoints
"""

from flask import Blueprint, request, jsonify, send_file
import os
import base64
from werkzeug.utils import secure_filename
from ..services.file_processor import FileProcessor
from ..utils.security import require_auth

files_bp = Blueprint('files', __name__)
file_processor = FileProcessor()

def validate_input(required_fields):
    """Simple input validation decorator"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            data = request.get_json() or {}
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

@files_bp.route('/api/files/upload', methods=['POST'])
@require_auth
def upload_file():
    """Upload and process a file"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        # Read file data
        file_data = file.read()
        filename = secure_filename(file.filename)
        
        # Validate file
        validation = file_processor.validate_file(filename, len(file_data))
        if not validation['valid']:
            return jsonify({
                'status': 'error',
                'message': validation['error']
            }), 400
        
        # Save file
        save_result = file_processor.save_file(file_data, filename)
        if not save_result['success']:
            return jsonify({
                'status': 'error',
                'message': save_result['error']
            }), 500
        
        # Process file
        process_result = file_processor.process_file(
            save_result['file_path'], 
            save_result['original_filename']
        )
        
        if not process_result['success']:
            # Clean up file if processing failed
            try:
                os.remove(save_result['file_path'])
            except:
                pass
            
            return jsonify({
                'status': 'error',
                'message': process_result['error']
            }), 500
        
        # Return success with file info and content
        return jsonify({
            'status': 'success',
            'message': 'File uploaded and processed successfully',
            'file_info': {
                'filename': save_result['filename'],
                'original_filename': save_result['original_filename'],
                'size': save_result['size'],
                'type': validation['file_type']
            },
            'content': process_result.get('content', ''),
            'metadata': process_result.get('metadata', {}),
            'summary': file_processor.get_file_summary(
                save_result['file_path'], 
                save_result['original_filename']
            )
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Upload failed: {str(e)}'
        }), 500

@files_bp.route('/api/files/upload-base64', methods=['POST'])
@require_auth
@validate_input(['filename', 'data'])
def upload_file_base64():
    """Upload file via base64 data"""
    try:
        data = request.get_json()
        filename = secure_filename(data.get('filename'))
        file_data_b64 = data.get('data')
        
        # Decode base64 data
        try:
            file_data = base64.b64decode(file_data_b64)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': 'Invalid base64 data'
            }), 400
        
        # Validate file
        validation = file_processor.validate_file(filename, len(file_data))
        if not validation['valid']:
            return jsonify({
                'status': 'error',
                'message': validation['error']
            }), 400
        
        # Save file
        save_result = file_processor.save_file(file_data, filename)
        if not save_result['success']:
            return jsonify({
                'status': 'error',
                'message': save_result['error']
            }), 500
        
        # Process file
        process_result = file_processor.process_file(
            save_result['file_path'], 
            save_result['original_filename']
        )
        
        if not process_result['success']:
            # Clean up file if processing failed
            try:
                os.remove(save_result['file_path'])
            except:
                pass
            
            return jsonify({
                'status': 'error',
                'message': process_result['error']
            }), 500
        
        return jsonify({
            'status': 'success',
            'message': 'File uploaded and processed successfully',
            'file_info': {
                'filename': save_result['filename'],
                'original_filename': save_result['original_filename'],
                'size': save_result['size'],
                'type': validation['file_type']
            },
            'content': process_result.get('content', ''),
            'metadata': process_result.get('metadata', {}),
            'summary': file_processor.get_file_summary(
                save_result['file_path'], 
                save_result['original_filename']
            )
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Upload failed: {str(e)}'
        }), 500

@files_bp.route('/api/files/analyze', methods=['POST'])
@require_auth
@validate_input(['content', 'analysis_type'])
def analyze_content():
    """Analyze file content with specific analysis type"""
    try:
        data = request.get_json()
        content = data.get('content')
        analysis_type = data.get('analysis_type', 'summary')
        
        # Define analysis prompts
        analysis_prompts = {
            'summary': 'Please provide a concise summary of this document, highlighting the key points and main topics.',
            'action_items': 'Extract all action items, tasks, and to-do items from this document. List them clearly.',
            'key_insights': 'Identify the key insights, important findings, and notable information from this document.',
            'questions': 'Generate relevant questions that could be answered based on the content of this document.',
            'entities': 'Extract all important entities (people, organizations, dates, locations, etc.) mentioned in this document.',
            'sentiment': 'Analyze the sentiment and tone of this document. Is it positive, negative, neutral, formal, casual, etc.?',
            'topics': 'Identify the main topics and themes discussed in this document.',
            'structure': 'Analyze the structure and organization of this document. How is the information presented?'
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts['summary'])
        
        return jsonify({
            'status': 'success',
            'analysis_type': analysis_type,
            'prompt': prompt,
            'content_preview': content[:500] + '...' if len(content) > 500 else content,
            'ready_for_gpt': True
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Analysis preparation failed: {str(e)}'
        }), 500

@files_bp.route('/api/files/supported-types', methods=['GET'])
def get_supported_types():
    """Get list of supported file types"""
    return jsonify({
        'status': 'success',
        'supported_types': list(file_processor.allowed_extensions.keys()),
        'max_file_size': file_processor.max_file_size,
        'max_file_size_mb': file_processor.max_file_size / (1024 * 1024)
    })

@files_bp.route('/api/files/cleanup', methods=['POST'])
@require_auth
def cleanup_files():
    """Clean up old uploaded files"""
    try:
        data = request.get_json() or {}
        max_age_hours = data.get('max_age_hours', 24)
        
        file_processor.cleanup_old_files(max_age_hours)
        
        return jsonify({
            'status': 'success',
            'message': f'Cleaned up files older than {max_age_hours} hours'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Cleanup failed: {str(e)}'
        }), 500

@files_bp.route('/api/files/process-url', methods=['POST'])
@require_auth
@validate_input(['url'])
def process_url():
    """Process a file from URL"""
    try:
        import requests
        from urllib.parse import urlparse
        
        data = request.get_json()
        url = data.get('url')
        
        # Parse URL to get filename
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        if not filename:
            filename = 'downloaded_file'
        
        # Download file
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        file_data = response.content
        
        # Validate file
        validation = file_processor.validate_file(filename, len(file_data))
        if not validation['valid']:
            return jsonify({
                'status': 'error',
                'message': validation['error']
            }), 400
        
        # Save and process file
        save_result = file_processor.save_file(file_data, filename)
        if not save_result['success']:
            return jsonify({
                'status': 'error',
                'message': save_result['error']
            }), 500
        
        process_result = file_processor.process_file(
            save_result['file_path'], 
            save_result['original_filename']
        )
        
        if not process_result['success']:
            try:
                os.remove(save_result['file_path'])
            except:
                pass
            
            return jsonify({
                'status': 'error',
                'message': process_result['error']
            }), 500
        
        return jsonify({
            'status': 'success',
            'message': 'File downloaded and processed successfully',
            'url': url,
            'file_info': {
                'filename': save_result['filename'],
                'original_filename': save_result['original_filename'],
                'size': save_result['size'],
                'type': validation['file_type']
            },
            'content': process_result.get('content', ''),
            'metadata': process_result.get('metadata', {}),
            'summary': file_processor.get_file_summary(
                save_result['file_path'], 
                save_result['original_filename']
            )
        })
        
    except requests.RequestException as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to download file: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Processing failed: {str(e)}'
        }), 500

