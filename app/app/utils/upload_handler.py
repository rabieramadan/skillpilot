"""
File Upload Handler for Teacher Materials
Handles secure file uploads for documents, PDFs, videos, audio, and images
"""

import os
import uuid
import mimetypes
from datetime import datetime
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads/materials'

ALLOWED_EXTENSIONS = {
    'document': {'doc', 'docx', 'txt', 'rtf', 'odt'},
    'pdf': {'pdf'},
    'video': {'mp4', 'mov', 'avi', 'webm', 'mkv'},
    'audio': {'mp3', 'wav', 'ogg', 'm4a', 'flac'},
    'image': {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'},
    'spreadsheet': {'xls', 'xlsx', 'csv'},
    'presentation': {'ppt', 'pptx'}
}

ALL_ALLOWED_EXTENSIONS = set()
for exts in ALLOWED_EXTENSIONS.values():
    ALL_ALLOWED_EXTENSIONS.update(exts)

MAX_FILE_SIZE = 100 * 1024 * 1024


def get_file_extension(filename):
    """Get lowercase file extension from filename"""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def allowed_file(filename):
    """Check if file has an allowed extension"""
    return get_file_extension(filename) in ALL_ALLOWED_EXTENSIONS


def get_material_type(filename):
    """Determine material type from file extension"""
    ext = get_file_extension(filename)
    for material_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return material_type
    return 'document'


def get_mime_type(filename):
    """Get MIME type from filename"""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        return mime_type
    
    ext = get_file_extension(filename)
    custom_mimes = {
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'ppt': 'application/vnd.ms-powerpoint',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'odt': 'application/vnd.oasis.opendocument.text',
        'rtf': 'application/rtf',
        'mp3': 'audio/mpeg',
        'm4a': 'audio/mp4',
        'flac': 'audio/flac',
        'webm': 'video/webm',
        'mkv': 'video/x-matroska'
    }
    return custom_mimes.get(ext, 'application/octet-stream')


def generate_unique_filename(original_filename, week_id):
    """Generate unique filename preserving extension"""
    ext = get_file_extension(original_filename)
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = secure_filename(original_filename.rsplit('.', 1)[0])[:50]
    return f"{week_id}_{timestamp}_{unique_id}_{safe_name}.{ext}"


def ensure_upload_folder():
    """Ensure upload folder exists"""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    return UPLOAD_FOLDER


def save_uploaded_file(file, week_id):
    """
    Save an uploaded file and return metadata
    
    Args:
        file: Werkzeug FileStorage object
        week_id: ID of the week for organizing files
        
    Returns:
        dict with file_url, file_name, file_size, mime_type, material_type
        or None if file is invalid
    """
    if not file or not file.filename:
        return {'error': 'No file provided'}
    
    original_filename = file.filename
    
    if not allowed_file(original_filename):
        ext = get_file_extension(original_filename)
        return {'error': f'File type .{ext} is not allowed. Allowed types: {", ".join(sorted(ALL_ALLOWED_EXTENSIONS))}'}
    
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return {'error': f'File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB'}
    
    if file_size == 0:
        return {'error': 'File is empty'}
    
    folder = ensure_upload_folder()
    
    unique_filename = generate_unique_filename(original_filename, week_id)
    file_path = os.path.join(folder, unique_filename)
    
    try:
        file.save(file_path)
    except Exception as e:
        return {'error': f'Failed to save file: {str(e)}'}
    
    file_url = f'/uploads/materials/{unique_filename}'
    
    return {
        'success': True,
        'file_url': file_url,
        'file_name': original_filename,
        'file_size': file_size,
        'mime_type': get_mime_type(original_filename),
        'material_type': get_material_type(original_filename)
    }


def delete_file(file_url):
    """Delete a file by its URL"""
    if not file_url:
        return False
    
    if file_url.startswith('/uploads/materials/'):
        filename = file_url.replace('/uploads/materials/', '')
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except Exception as e:
                print(f"Error deleting file: {e}")
                return False
    
    return False


def get_file_info(file_url):
    """Get file information from URL"""
    if not file_url:
        return None
    
    if file_url.startswith('/uploads/materials/'):
        filename = file_url.replace('/uploads/materials/', '')
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(file_path):
            return {
                'exists': True,
                'size': os.path.getsize(file_path),
                'path': file_path
            }
    
    return {'exists': False}
