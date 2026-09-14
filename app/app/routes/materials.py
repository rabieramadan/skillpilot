"""
AIACMate Pro - Course Materials Routes
Handles uploading, viewing, and managing course materials
"""

from flask import Blueprint, request, jsonify, session, send_file, current_app
from werkzeug.utils import secure_filename
from functools import wraps
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

materials_bp = Blueprint('materials', __name__, url_prefix='/api/materials')

COURSE_FILES_FILE = 'course_files.json'
COURSE_FILES_DIR = 'course_files'
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
    'txt', 'csv', 'json', 'xml',
    'jpg', 'jpeg', 'png', 'gif', 'svg',
    'mp4', 'mov', 'avi', 'mp3', 'wav',
    'zip', 'rar', '7z'
}


def authenticated_required(f):
    """Decorator to require any authenticated user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') and not session.get('is_admin'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def instructor_or_admin_required(f):
    """Decorator to require instructor or admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        if not is_admin and not user_id:
            return jsonify({'error': 'Authentication required'}), 401
            
        if not is_admin:
            users_data = load_users()
            user = next((u for u in users_data.get('users', []) if u['user_id'] == user_id), None)
            if not user or user.get('role') != 'Instructor':
                return jsonify({'error': 'Instructor or admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# Data Access Functions
# ============================================

def load_course_files():
    """Load course files metadata from JSON file"""
    if os.path.exists(COURSE_FILES_FILE):
        with open(COURSE_FILES_FILE, 'r') as f:
            return json.load(f)
    return {'files': []}


def save_course_files(data):
    """Save course files metadata to JSON file"""
    with open(COURSE_FILES_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_users():
    """Load users from JSON file"""
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            return json.load(f)
    return {'users': []}


def load_enrollments():
    """Load enrollments from JSON file"""
    if os.path.exists('enrollments.json'):
        with open('enrollments.json', 'r') as f:
            return json.load(f)
    return {'enrollments': []}


def load_classes():
    """Load classes from JSON file"""
    if os.path.exists('classes.json'):
        with open('classes.json', 'r') as f:
            return json.load(f)
    return {'classes': []}


def load_instructors():
    """Load instructors from JSON file"""
    if os.path.exists('instructors.json'):
        with open('instructors.json', 'r') as f:
            return json.load(f)
    return {'instructors': []}


def can_access_class(user_id, class_id, is_admin):
    """Check if user can access a class (enrolled or teaches it)"""
    if is_admin:
        return True
    
    # Check if student is enrolled
    enrollments = load_enrollments()
    if any(e['user_id'] == user_id and e['class_id'] == class_id 
           for e in enrollments.get('enrollments', [])):
        return True
    
    # Check if instructor teaches this class
    instructors = load_instructors()
    classes = load_classes()
    
    instructor_record = next((i for i in instructors.get('instructors', []) 
                             if i['user_id'] == user_id), None)
    
    if instructor_record:
        class_obj = next((c for c in classes.get('classes', []) 
                         if c['class_id'] == class_id), None)
        if class_obj and instructor_record['instructor_id'] in class_obj.get('instructor_ids', []):
            return True
    
    return False


def can_manage_class(user_id, class_id, is_admin):
    """Check if user can manage/upload to a class (instructor or admin only)"""
    if is_admin:
        return True
    
    # Check if instructor teaches this class
    instructors = load_instructors()
    classes = load_classes()
    
    instructor_record = next((i for i in instructors.get('instructors', []) 
                             if i['user_id'] == user_id), None)
    
    if instructor_record:
        class_obj = next((c for c in classes.get('classes', []) 
                         if c['class_id'] == class_id), None)
        if class_obj and instructor_record['instructor_id'] in class_obj.get('instructor_ids', []):
            return True
    
    return False


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_size_mb(filepath):
    """Get file size in MB"""
    return os.path.getsize(filepath) / (1024 * 1024)


# ============================================
# Course Materials Routes
# ============================================

@materials_bp.route('/upload', methods=['POST'])
@instructor_or_admin_required
def upload_material():
    """Upload a course material file"""
    
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    class_id = request.form.get('class_id')
    description = request.form.get('description', '')
    
    if not class_id:
        return jsonify({'error': 'Class ID is required'}), 400
    
    # Check if user can manage this class
    if not can_manage_class(user_id, class_id, is_admin):
        return jsonify({'error': 'You do not have permission to upload to this class'}), 403
    
    if not file.filename or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    # Create course files directory if it doesn't exist
    os.makedirs(COURSE_FILES_DIR, exist_ok=True)
    
    # Generate unique filename
    original_filename = secure_filename(file.filename)  # file.filename is guaranteed to be str here
    file_id = str(uuid.uuid4())
    file_extension = original_filename.rsplit('.', 1)[1].lower()
    stored_filename = f"{file_id}.{file_extension}"
    file_path = os.path.join(COURSE_FILES_DIR, stored_filename)
    
    # Save file
    file.save(file_path)
    
    # Get file size
    file_size_mb = get_file_size_mb(file_path)
    
    # Get uploader info
    is_admin = session.get('is_admin', False)
    uploader_id = 'admin' if is_admin else session.get('user_id')
    uploader_name = 'Admin' if is_admin else session.get('full_name', 'Unknown')
    
    # Create file metadata
    file_metadata = {
        'file_id': file_id,
        'class_id': class_id,
        'original_filename': original_filename,
        'stored_filename': stored_filename,
        'file_type': file_extension,
        'file_size_mb': round(file_size_mb, 2),
        'description': description,
        'uploaded_by_id': uploader_id,
        'uploaded_by_name': uploader_name,
        'uploaded_at': datetime.now().isoformat()
    }
    
    # Save metadata
    course_files_data = load_course_files()
    course_files_data['files'].append(file_metadata)
    save_course_files(course_files_data)
    
    return jsonify({
        'success': True,
        'message': 'File uploaded successfully',
        'file': file_metadata
    })


@materials_bp.route('/class/<class_id>', methods=['GET'])
@authenticated_required
def get_class_materials(class_id):
    """Get all materials for a specific class"""
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    # Check if user can access this class
    if not can_access_class(user_id, class_id, is_admin):
        return jsonify({'error': 'You do not have permission to access this class'}), 403
    
    course_files_data = load_course_files()
    
    # Filter files for this class
    class_files = [f for f in course_files_data.get('files', []) if f['class_id'] == class_id]
    
    # Sort by upload date (newest first)
    class_files.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)
    
    return jsonify({
        'success': True,
        'class_id': class_id,
        'files': class_files,
        'count': len(class_files)
    })


@materials_bp.route('/download/<file_id>', methods=['GET'])
@authenticated_required
def download_material(file_id):
    """Download a course material file"""
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    course_files_data = load_course_files()
    
    # Find file metadata
    file_metadata = next((f for f in course_files_data.get('files', []) if f['file_id'] == file_id), None)
    
    if not file_metadata:
        return jsonify({'error': 'File not found'}), 404
    
    # Check if user can access the class this file belongs to
    if not can_access_class(user_id, file_metadata['class_id'], is_admin):
        return jsonify({'error': 'You do not have permission to download this file'}), 403
    
    file_path = os.path.join(COURSE_FILES_DIR, file_metadata['stored_filename'])
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found on disk'}), 404
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=file_metadata['original_filename']
    )


@materials_bp.route('/<file_id>', methods=['DELETE'])
@instructor_or_admin_required
def delete_material(file_id):
    """Delete a course material file"""
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    course_files_data = load_course_files()
    
    # Find file metadata
    file_metadata = next((f for f in course_files_data.get('files', []) if f['file_id'] == file_id), None)
    
    if not file_metadata:
        return jsonify({'error': 'File not found'}), 404
    
    # Check if user can manage the class this file belongs to
    if not can_manage_class(user_id, file_metadata['class_id'], is_admin):
        return jsonify({'error': 'You do not have permission to delete files from this class'}), 403
    
    # Delete file from disk
    file_path = os.path.join(COURSE_FILES_DIR, file_metadata['stored_filename'])
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Remove metadata
    course_files_data['files'] = [f for f in course_files_data.get('files', []) if f['file_id'] != file_id]
    save_course_files(course_files_data)
    
    return jsonify({
        'success': True,
        'message': 'File deleted successfully'
    })


@materials_bp.route('/stats', methods=['GET'])
@authenticated_required
def get_materials_stats():
    """Get statistics about course materials"""
    course_files_data = load_course_files()
    files = course_files_data.get('files', [])
    
    # Calculate stats
    total_files = len(files)
    total_size_mb = sum(f.get('file_size_mb', 0) for f in files)
    
    # Count by file type
    file_types = {}
    for f in files:
        file_type = f.get('file_type', 'unknown')
        file_types[file_type] = file_types.get(file_type, 0) + 1
    
    # Count by class
    classes = {}
    for f in files:
        class_id = f.get('class_id', 'unknown')
        classes[class_id] = classes.get(class_id, 0) + 1
    
    return jsonify({
        'success': True,
        'stats': {
            'total_files': total_files,
            'total_size_mb': round(total_size_mb, 2),
            'file_types': file_types,
            'files_by_class': classes
        }
    })
