from flask import Blueprint, request, jsonify, current_app, session, send_file
from werkzeug.utils import secure_filename
import os
from app.services.ai_service import AIService
from app.services.presentation_service import PresentationService
from app.utils.file_handler import FileHandler
import time
import uuid

api_bp = Blueprint('api', __name__)
presentation_service = None

# Define allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'ppt', 'pptx', 'xls', 'xlsx', 'csv', 'mp3', 'mp4', 'webm', 'ogg', 'wav'}


def is_app_frozen():
    """Check if the application is in frozen/maintenance mode"""
    try:
        from app.models import SiteSettings
        settings = SiteSettings.query.first()
        return settings.app_frozen if settings else False
    except Exception:
        return False


def get_freeze_message(lang='en'):
    """Get the freeze message in the specified language"""
    try:
        from app.models import SiteSettings
        settings = SiteSettings.query.first()
        if not settings:
            return 'The platform is currently under maintenance.'
        return settings.freeze_message_ar if lang == 'ar' else settings.freeze_message
    except Exception:
        return 'The platform is currently under maintenance.'


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api_bp.route('/heygen/status/<video_id>', methods=['GET'])
def heygen_status(video_id):
    """Poll HeyGen for video render status."""
    try:
        from config.config import Config
        from app.models import ApiCredential
        api_key = Config.HEYGEN_API_KEY
        if not api_key:
            cred = ApiCredential.query.filter_by(provider='heygen', is_active=True).first()
            if cred:
                from app.utils.encryption import decrypt_api_key
                try:
                    api_key = decrypt_api_key(cred.encrypted_key)
                except Exception:
                    api_key = None
        if not api_key:
            return jsonify({'error': 'HeyGen API key not configured'}), 400
        svc = AIService()
        result = svc.heygen_status(video_id, api_key)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/chat/<provider>', methods=['POST'])
def chat_with_ai(provider):
    # Check if app is frozen - block chat except for superadmin/admin
    if is_app_frozen():
        from flask import session
        role = session.get('role', '').lower()
        if role not in ['superadmin', 'super_admin', 'admin']:
            lang = request.form.get('language', 'en')[:2]
            return jsonify({'error': get_freeze_message(lang), 'app_frozen': True}), 503
    
    try:
        # Get form data
        message = request.form.get('message', '')
        api_key = request.form.get('api_key', '')
        version = request.form.get('version', '')
        conversation_history = request.form.get('conversation_history', '[]')
        language = request.form.get('language', 'en')  # Default to English
        
        # Parse conversation history (JSON string)
        import json
        try:
            history = json.loads(conversation_history)
            print(f"DEBUG: Received conversation history with {len(history)} messages")
        except:
            history = []
            print("DEBUG: No valid conversation history provided")
        
        print(f"DEBUG: Language: {language}")
        
        # If no API key provided, fetch from config
        if not api_key:
            from config.config import Config
            config = Config()
            # DALL-E uses OpenAI API key
            if provider.lower() == 'dalle':
                api_key = config.OPENAI_API_KEY
                print(f"DEBUG: Using OpenAI API key for DALL-E")
            # All AWS Bedrock models use the same Bedrock credentials
            elif provider.lower() in ['bedrock', 'llama_bedrock', 'mistral_bedrock', 'amazon_nova', 'cohere_bedrock', 'ai21_bedrock', 'stable_diffusion']:
                api_key = config.BEDROCK_API_KEY
                print(f"DEBUG: Using Bedrock API key for {provider}")
            else:
                api_key = getattr(config, f'{provider.upper()}_API_KEY', None)
                print(f"DEBUG: Fetched API key from config for {provider}")

        print(f"DEBUG: Received message: {message}")
        print(f"DEBUG: Provider: {provider}")
        print(f"DEBUG: Files in request: {request.files}")

        # Handle file uploads
        uploaded_files = []
        if 'files' in request.files:
            files = request.files.getlist('files')
            print(f"DEBUG: Found {len(files)} files")

            for file in files:
                if file.filename != '' and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Add timestamp to avoid conflicts
                    timestamp = str(int(time.time()))
                    filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

                    # Ensure upload directory exists
                    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

                    # Save file
                    file.save(file_path)
                    uploaded_files.append(file_path)
                    print(f"DEBUG: Saved file: {file_path}")

        print(f"DEBUG: Total uploaded files: {len(uploaded_files)}")

        # Extract file content for memory persistence
        file_context = ""
        if uploaded_files:
            temp_service = AIService()
            for file_path in uploaded_files:
                try:
                    extracted = temp_service._extract_file_content(file_path)
                    if extracted:
                        file_context += f"\n\n[File: {os.path.basename(file_path)}]\n{extracted[:15000]}"
                except Exception as e:
                    print(f"DEBUG: Could not extract content from {file_path}: {e}")

        # Process with AI service
        ai_service = AIService()
        response = ai_service.chat(provider, message, api_key, uploaded_files, history, version, language)
        
        # Include file context in response for frontend to store in history
        if file_context:
            response['file_context'] = file_context.strip()
        
        # Ensure response text is properly encoded (fixes ">" character issues)
        if 'text' in response and response['text']:
            # Clean and sanitize the response text
            text = response['text']
            if isinstance(text, str):
                # Ensure proper Unicode handling
                response['text'] = text.encode('utf-8', errors='replace').decode('utf-8')
        
        # Check if request is from admin (check for admin key in headers or request)
        is_admin = request.headers.get('X-Admin-Key') == current_app.config.get('ADMIN_KEY') or \
                   request.args.get('admin_key') == current_app.config.get('ADMIN_KEY')
        
        # If there's an error and user is not admin, sanitize error message
        if 'error' in response and not is_admin:
            # Store original error for logging
            original_error = response.get('error', '')
            print(f"DEBUG: Sanitizing error for non-admin user: {original_error}")
            # Return simplified message for all errors
            response = {
                'error': 'This AI model is not configured or unavailable. Please try another model.'
            }

        # Clean up uploaded files after processing
        for file_path in uploaded_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not delete file {file_path}: {e}")

        # v2: passively record sentiment from learner messages so cohort
        # analytics & at-risk scans have real signal data. Best-effort,
        # never blocks the chat reply.
        try:
            from flask import session as _sess
            uid = _sess.get('user_id')
            if uid and message and not response.get('error'):
                from app.routes.insights import _score_sentiment
                from app.models import db as _db, SentimentSignal
                lang = (language or 'en')[:2]
                score, label = _score_sentiment(message, lang)
                if label != 'neutral' or abs(score or 0) > 0.0:
                    _db.session.add(SentimentSignal(
                        user_id=uid, source='chat',
                        text_sample=(message or '')[:280],
                        language=lang,
                        sentiment_label=label,
                        sentiment_score=score,
                    ))
                    _db.session.commit()
        except Exception as _se:
            try:
                from app.models import db as _db
                _db.session.rollback()
            except Exception:
                pass
            current_app.logger.debug(f"sentiment hook skipped: {_se}")

        return jsonify(response)

    except Exception as e:
        current_app.logger.error(f"Chat error: {str(e)}")
        print(f"ERROR: {str(e)}")
        
        # Check if request is from admin
        is_admin = request.headers.get('X-Admin-Key') == current_app.config.get('ADMIN_KEY') or \
                   request.args.get('admin_key') == current_app.config.get('ADMIN_KEY')
        
        # Return appropriate error message based on user role
        if is_admin:
            return jsonify({'error': str(e)}), 500
        else:
            return jsonify({'error': 'This AI model is not configured or unavailable. Please try another model.'}), 500


@api_bp.route('/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        api_key = data.get('api_key', '')

        ai_service = AIService()
        response = ai_service.generate_image(prompt, api_key)
        
        # Check if request is from admin
        is_admin = request.headers.get('X-Admin-Key') == current_app.config.get('ADMIN_KEY') or \
                   request.args.get('admin_key') == current_app.config.get('ADMIN_KEY')
        
        # If there's an error and user is not admin, sanitize error message
        if 'error' in response and not is_admin:
            original_error = response.get('error', '')
            print(f"DEBUG: Sanitizing image generation error for non-admin user: {original_error}")
            response = {
                'error': 'Image generation is not configured or unavailable. Please check your configuration.'
            }

        return jsonify(response)

    except Exception as e:
        current_app.logger.error(f"Image generation error: {str(e)}")
        
        # Check if request is from admin
        is_admin = request.headers.get('X-Admin-Key') == current_app.config.get('ADMIN_KEY') or \
                   request.args.get('admin_key') == current_app.config.get('ADMIN_KEY')
        
        # Return appropriate error message based on user role
        if is_admin:
            return jsonify({'error': str(e)}), 500
        else:
            return jsonify({'error': 'Image generation is not configured or unavailable. Please check your configuration.'}), 500


@api_bp.route('/presentmate/generate', methods=['POST'])
def presentmate_generate():
    """Generate slides content from user's text or files"""
    try:
        global presentation_service
        if presentation_service is None:
            ai_service = AIService()
            presentation_service = PresentationService(ai_service)
        
        # Get form data
        message = request.form.get('message', '')
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        # Handle file uploads if any
        uploaded_files = []
        if 'files' in request.files:
            files = request.files.getlist('files')
            for file in files:
                if file.filename != '' and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = str(int(time.time()))
                    filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file.save(file_path)
                    uploaded_files.append(file_path)
        
        # Generate slides content
        response = presentation_service.generate_slides_content(
            message, 
            uploaded_files if uploaded_files else None
        )
        
        # Clean up uploaded files
        for file_path in uploaded_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not delete file {file_path}: {e}")
        
        return jsonify(response)
    
    except Exception as e:
        current_app.logger.error(f"PresentMate generate error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/presentmate/convert', methods=['POST'])
def presentmate_convert():
    """Convert generated slides to specified format"""
    try:
        global presentation_service
        if presentation_service is None:
            ai_service = AIService()
            presentation_service = PresentationService(ai_service)
        
        # Get request data
        data = request.get_json()
        session_id = data.get('session_id')
        format_type = data.get('format', 'json')
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        # Convert to format
        response = presentation_service.convert_to_format(session_id, format_type)
        
        return jsonify(response)
    
    except Exception as e:
        current_app.logger.error(f"PresentMate convert error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/presentmate/download/<path:filename>', methods=['GET'])
def presentmate_download(filename):
    """Download generated presentation file"""
    try:
        # Use absolute path from project root (parent of 'app' directory)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        file_path = os.path.join(project_root, 'generated_presentations', filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found', 'path': file_path}), 404
    
    except Exception as e:
        current_app.logger.error(f"PresentMate download error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/downloads/dalle/<path:filename>', methods=['GET'])
def dalle_image_download(filename):
    """Download DALL-E generated image"""
    try:
        # Use absolute path from project root (parent of 'app' directory)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        file_path = os.path.join(project_root, 'uploads', filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'Image file not found', 'path': file_path}), 404
    
    except Exception as e:
        current_app.logger.error(f"DALL-E download error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/download-file', methods=['POST'])
def download_generated_file():
    """Create and download AI-generated file content"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        filename = data.get('filename', 'generated_file.txt')
        
        if not content:
            return jsonify({'error': 'No content provided'}), 400
        
        # Create file in memory
        import io
        
        # Determine content type based on extension
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'txt'
        
        content_types = {
            'py': 'text/x-python',
            'js': 'application/javascript',
            'html': 'text/html',
            'css': 'text/css',
            'json': 'application/json',
            'md': 'text/markdown',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'xml': 'application/xml',
            'sql': 'application/sql',
            'sh': 'application/x-sh',
            'yaml': 'application/x-yaml',
            'yml': 'application/x-yaml',
        }
        
        content_type = content_types.get(ext, 'text/plain')
        
        # Create BytesIO buffer with UTF-8 content
        buffer = io.BytesIO()
        buffer.write(content.encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype=content_type,
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        current_app.logger.error(f"File download error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============================================
# SYSTEM-WIDE STANDARD FEEDBACK TEMPLATE
# ============================================

@api_bp.route('/system/feedback-template', methods=['GET'])
def get_system_feedback_template():
    """
    Get the FIXED, STANDARDIZED feedback survey template.
    This is a system-wide template that is identical for ALL courses.
    No course ID required - this template is global.
    
    Returns:
        - Template name (English and Arabic)
        - Version number
        - All 14 standard feedback questions organized by category
        - Category metadata
    """
    try:
        from app.constants.feedback_template import get_standard_feedback_template
        
        template = get_standard_feedback_template()
        
        return jsonify({
            'success': True,
            'template': template,
            'message': 'This is the system-wide standardized feedback template used across all courses'
        })
        
    except Exception as e:
        current_app.logger.error(f"Feedback template error: {str(e)}")
        return jsonify({'error': str(e)}), 500