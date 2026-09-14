"""
AIACMate Pro - Class Management Routes
Handles instructors, classes, and student enrollments
"""

from flask import Blueprint, request, jsonify, session, send_file, make_response
from datetime import datetime
import json
import os
import csv
import io
from pathlib import Path
from functools import wraps
from werkzeug.utils import secure_filename

classes_bp = Blueprint('classes', __name__, url_prefix='/api/classes')

# File paths
INSTRUCTORS_FILE = 'instructors.json'
CLASSES_FILE = 'classes.json'
ENROLLMENTS_FILE = 'enrollments.json'
USERS_FILE = 'users.json'
COURSE_FILES_FILE = 'course_files.json'
COURSE_FILES_DIR = 'course_files'
CLASS_EXAMS_FILE = 'class_exams.json'
CLASS_EXAM_SUBMISSIONS_FILE = 'class_exam_submissions.json'


def admin_required(f):
    """Decorator to require SUPER ADMIN authentication (not institution admin)
    CRITICAL: For multi-tenant isolation, ONLY super_admin role has global access
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        role = session.get('role', '').lower().replace(' ', '_')
        # ONLY super_admin role has global access - 'admin' is institution admin
        if role != 'super_admin':
            return jsonify({'error': 'Super admin authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def instructor_or_admin_required(f):
    """Decorator to require instructor or super admin authentication
    CRITICAL: Institution admins should use /api/courses/* for their institution
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        role = session.get('role', '').lower().replace(' ', '_')
        
        # ONLY super_admin has global access - check role ONLY
        if role == 'super_admin':
            return f(*args, **kwargs)
        
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
            
        # Check if user is instructor
        if role != 'instructor':
            users = load_users()
            user = next((u for u in users.get('users', []) if u['user_id'] == user_id), None)
            if not user or user.get('role', '').lower() != 'instructor':
                return jsonify({'error': 'Instructor or super admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def authenticated_required(f):
    """Decorator to require any authenticated user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') and not session.get('is_admin') and not session.get('logged_in'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# Data Access Functions
# ============================================

def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {'users': []}


def load_instructors():
    """Load instructors from JSON file"""
    if os.path.exists(INSTRUCTORS_FILE):
        with open(INSTRUCTORS_FILE, 'r') as f:
            return json.load(f)
    return {'instructors': []}


def save_instructors(data):
    """Save instructors to JSON file"""
    with open(INSTRUCTORS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_classes():
    """Load classes from JSON file"""
    if os.path.exists(CLASSES_FILE):
        with open(CLASSES_FILE, 'r') as f:
            return json.load(f)
    return {'classes': []}


def save_classes(data):
    """Save classes to JSON file"""
    with open(CLASSES_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_enrollments():
    """Load enrollments from JSON file"""
    if os.path.exists(ENROLLMENTS_FILE):
        with open(ENROLLMENTS_FILE, 'r') as f:
            return json.load(f)
    return {'enrollments': []}


def save_enrollments(data):
    """Save enrollments to JSON file"""
    with open(ENROLLMENTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_class_exams():
    """Load class exams from JSON file"""
    if os.path.exists(CLASS_EXAMS_FILE):
        with open(CLASS_EXAMS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'exams': []}


def save_class_exams(data):
    """Save class exams to JSON file"""
    with open(CLASS_EXAMS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_class_exam_submissions():
    """Load class exam submissions from JSON file"""
    if os.path.exists(CLASS_EXAM_SUBMISSIONS_FILE):
        with open(CLASS_EXAM_SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'submissions': []}


def save_class_exam_submissions(data):
    """Save class exam submissions to JSON file"""
    with open(CLASS_EXAM_SUBMISSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_id(prefix, existing_items):
    """Generate unique ID for items"""
    if not existing_items:
        return f"{prefix}_1"
    
    # Extract numbers from existing IDs and find max
    numbers = []
    for item in existing_items:
        item_id = item.get('instructor_id') or item.get('class_id') or item.get('enrollment_id')
        if item_id and item_id.startswith(prefix):
            try:
                num = int(item_id.split('_')[1])
                numbers.append(num)
            except:
                pass
    
    next_num = max(numbers) + 1 if numbers else 1
    return f"{prefix}_{next_num}"


def generate_class_code(semester, counter):
    """Generate class code based on semester and counter
    Format: PROMPT-2025F-001, PROMPT-2025S-002, etc.
    """
    # Extract year and semester code from semester string
    # e.g., "Fall 2025" -> "2025F", "Spring 2025" -> "2025S"
    semester_parts = semester.split()
    if len(semester_parts) >= 2:
        year = semester_parts[-1]  # Last part is usually the year
        season = semester_parts[0][0].upper()  # First letter of season
        semester_code = f"{year}{season}"
    else:
        # Fallback to current year and F
        semester_code = f"{datetime.now().year}F"
    
    # Format counter with leading zeros
    counter_str = str(counter).zfill(3)
    
    return f"PROMPT-{semester_code}-{counter_str}"


def save_users(users_data):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users_data, f, indent=2)


# ============================================
# Instructor Routes
# ============================================

@classes_bp.route('/instructors', methods=['GET'])
@authenticated_required
def get_instructors():
    """Get all instructors with their user info"""
    try:
        instructors_data = load_instructors()
        users_data = load_users()
        
        # Enrich instructor data with user info
        enriched_instructors = []
        for instructor in instructors_data.get('instructors', []):
            user = next((u for u in users_data.get('users', []) if u['user_id'] == instructor['user_id']), None)
            if user:
                enriched_instructors.append({
                    'instructor_id': instructor['instructor_id'],
                    'user_id': instructor['user_id'],
                    'full_name': user['full_name'],
                    'email': user['email'],
                    'bio': instructor.get('bio', ''),
                    'expertise': instructor.get('expertise', []),
                    'created_at': instructor.get('created_at', '')
                })
        
        return jsonify({'instructors': enriched_instructors})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/instructors', methods=['POST'])
@admin_required
def create_instructor():
    """Create new instructor (admin only)"""
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        bio = data.get('bio', '')
        expertise = data.get('expertise', [])
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Verify user exists and update their role to Instructor
        users_data = load_users()
        user = next((u for u in users_data.get('users', []) if u['user_id'] == user_id), None)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update user role to Instructor
        user['role'] = 'Instructor'
        with open(USERS_FILE, 'w') as f:
            json.dump(users_data, f, indent=2)
        
        # Check if instructor already exists
        instructors_data = load_instructors()
        existing = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == user_id), None)
        if existing:
            return jsonify({'error': 'Instructor already exists'}), 400
        
        # Create instructor record
        instructor_id = generate_id('inst', instructors_data.get('instructors', []))
        new_instructor = {
            'instructor_id': instructor_id,
            'user_id': user_id,
            'bio': bio,
            'expertise': expertise,
            'created_at': datetime.now().isoformat()
        }
        
        instructors_data.setdefault('instructors', []).append(new_instructor)
        save_instructors(instructors_data)
        
        return jsonify({
            'success': True,
            'instructor': new_instructor
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/instructors/<instructor_id>', methods=['PUT'])
@admin_required
def update_instructor(instructor_id):
    """Update instructor info (admin only)"""
    try:
        data = request.json or {}
        
        instructors_data = load_instructors()
        instructor = next((i for i in instructors_data.get('instructors', []) if i['instructor_id'] == instructor_id), None)
        
        if not instructor:
            return jsonify({'error': 'Instructor not found'}), 404
        
        # Update fields
        if 'bio' in data:
            instructor['bio'] = data['bio']
        if 'expertise' in data:
            instructor['expertise'] = data['expertise']
        
        save_instructors(instructors_data)
        
        return jsonify({
            'success': True,
            'instructor': instructor
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# Class Routes
# ============================================

@classes_bp.route('/list', methods=['GET'])
@authenticated_required
def get_classes():
    """Get classes (filtered by role) - Supports multiple instructors
    NOTE: This legacy JSON-based API is for super_admin only.
    Institution users should use /api/courses/* which has proper multi-tenant isolation.
    """
    try:
        classes_data = load_classes()
        instructors_data = load_instructors()
        users_data = load_users()
        
        user_id = session.get('user_id')
        role = session.get('role', 'student')
        
        all_classes = classes_data.get('classes', [])
        
        # Normalize role to lowercase for consistent checks
        role = role.lower().replace(' ', '_') if role else 'student'
        
        # MULTI-TENANT ISOLATION: Only super_admin sees all classes in legacy API
        # Institution admins/instructors should use /api/courses/* instead
        if role == 'super_admin':
            # Super admin sees all classes
            pass
        elif role == 'instructor':
            # Instructors only see classes where they are assigned
            user_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == user_id), None)
            if user_instructor:
                all_classes = [c for c in all_classes if user_instructor['instructor_id'] in c.get('instructor_ids', [])]
            else:
                all_classes = []
        else:
            # Institution admins and students should use /api/courses/* for proper isolation
            # Return empty for non-super-admin roles using legacy API
            all_classes = []
        
        # Enrich with instructor info (multiple instructors per class)
        enriched_classes = []
        for cls in all_classes:
            instructor_ids = cls.get('instructor_ids', [])
            instructor_names = []
            
            # Get all instructor names for this class
            for inst_id in instructor_ids:
                instructor = next((i for i in instructors_data.get('instructors', []) if i['instructor_id'] == inst_id), None)
                if instructor:
                    instructor_user = next((u for u in users_data.get('users', []) if u['user_id'] == instructor['user_id']), None)
                    if instructor_user:
                        instructor_names.append(instructor_user['full_name'])
            
            enriched_classes.append({
                **cls,
                'instructor_names': instructor_names,
                'instructor_name': ', '.join(instructor_names) if instructor_names else 'Unknown'  # For backwards compatibility
            })
        
        return jsonify({'classes': enriched_classes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>', methods=['GET'])
@authenticated_required
def get_class(class_id):
    """Get a single class by ID with enriched instructor information"""
    try:
        classes_data = load_classes()
        instructors_data = load_instructors()
        users_data = load_users()
        
        # Find the class
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Enrich with instructor info
        instructor_ids = cls.get('instructor_ids', [])
        instructor_names = []
        
        for instructor_id in instructor_ids:
            instructor = next((i for i in instructors_data.get('instructors', []) if i['instructor_id'] == instructor_id), None)
            if instructor:
                user = next((u for u in users_data.get('users', []) if u['user_id'] == instructor['user_id']), None)
                if user:
                    instructor_names.append(user.get('full_name', 'Unknown'))
        
        enriched_class = {
            **cls,
            'instructor_name': ', '.join(instructor_names) if instructor_names else 'No instructor assigned'
        }
        
        return jsonify({'class': enriched_class})
    except Exception as e:
        print(f"Error getting class: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/create', methods=['POST'])
@admin_required
def create_class():
    """Create new class (admin only) - Supports multiple instructors"""
    try:
        data = request.json or {}
        title = data.get('title')
        description = data.get('description', '')
        semester = data.get('semester', '')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        schedule = data.get('schedule', '')
        capacity = data.get('capacity', 30)
        course_type = data.get('course_type', '')
        pricing_type = data.get('pricing_type', 'free')
        price = data.get('price')
        payment_url = data.get('payment_url', '')
        course_content = data.get('course_content', '')
        is_enabled = data.get('is_enabled', True)
        
        # Meeting/broadcast links
        meet_link = data.get('meet_link', '')
        zoom_link = data.get('zoom_link', '')
        youtube_broadcast_link = data.get('youtube_broadcast_link', '')
        
        if not title:
            return jsonify({'error': 'Class title is required'}), 400
        if not semester:
            return jsonify({'error': 'Semester is required'}), 400
        
        # Validate pricing
        if pricing_type not in ['free', 'paid']:
            pricing_type = 'free'
        
        if pricing_type == 'paid':
            if price is None or price < 0:
                return jsonify({'error': 'Valid price (≥0) is required for paid courses'}), 400
            # Ensure price is numeric
            try:
                price = float(price)
            except (ValueError, TypeError):
                return jsonify({'error': 'Price must be a valid number'}), 400
        else:
            price = None  # Free courses have no price
        
        # Admin can specify one or more instructors
        instructor_id_list = data.get('instructor_ids', [])
        if not instructor_id_list:
            # Fallback to single instructor_id for backwards compatibility
            single_instructor_id = data.get('instructor_id')
            if single_instructor_id:
                instructor_id_list = [single_instructor_id]
            else:
                return jsonify({'error': 'At least one instructor is required'}), 400
        instructor_ids = instructor_id_list if isinstance(instructor_id_list, list) else [instructor_id_list]
        
        # Verify all instructors exist
        instructors_data = load_instructors()
        for inst_id in instructor_ids:
            instructor = next((i for i in instructors_data.get('instructors', []) if i['instructor_id'] == inst_id), None)
            if not instructor:
                return jsonify({'error': f'Instructor {inst_id} not found'}), 404
        
        # Create class
        classes_data = load_classes()
        class_id = generate_id('class', classes_data.get('classes', []))
        
        # Get and increment class counter for code generation
        current_counter = classes_data.get('class_counter', 0)
        counter = int(current_counter) + 1 if current_counter else 1
        class_code = generate_class_code(semester, counter)
        
        new_class = {
            'class_id': class_id,
            'class_code': class_code,
            'instructor_ids': instructor_ids,
            'title': title,
            'description': description,
            'semester': semester,
            'start_date': start_date,
            'end_date': end_date,
            'schedule': schedule,
            'capacity': capacity,
            'course_type': course_type,
            'pricing_type': pricing_type,
            'price': price,
            'payment_url': payment_url,
            'course_content': course_content,
            'is_enabled': is_enabled,
            'meet_link': meet_link,
            'zoom_link': zoom_link,
            'youtube_broadcast_link': youtube_broadcast_link,
            'created_at': datetime.now().isoformat()
        }
        
        classes_data.setdefault('classes', []).append(new_class)
        classes_data['class_counter'] = counter
        save_classes(classes_data)
        
        return jsonify({
            'success': True,
            'class': new_class
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>', methods=['PUT'])
@instructor_or_admin_required
def update_class(class_id):
    """Update class (instructor or admin)"""
    try:
        data = request.json or {}
        
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check ownership if not admin
        if not session.get('is_admin'):
            # Check if user is one of the class instructors
            instructor_user_id = session.get('user_id')
            instructors_data = load_instructors()
            user_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == instructor_user_id), None)
            if not user_instructor or user_instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Not authorized to update this class'}), 403
        
        # Update fields
        if 'title' in data:
            cls['title'] = data['title']
        if 'description' in data:
            cls['description'] = data['description']
        if 'schedule' in data:
            cls['schedule'] = data['schedule']
        if 'capacity' in data:
            cls['capacity'] = data['capacity']
        
        # Update meeting/broadcast links
        if 'meet_link' in data:
            cls['meet_link'] = data['meet_link']
        if 'zoom_link' in data:
            cls['zoom_link'] = data['zoom_link']
        if 'youtube_broadcast_link' in data:
            cls['youtube_broadcast_link'] = data['youtube_broadcast_link']
        
        save_classes(classes_data)
        
        return jsonify({
            'success': True,
            'class': cls
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>', methods=['DELETE'])
@instructor_or_admin_required
def delete_class(class_id):
    """Delete class (instructor or admin)"""
    try:
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check ownership if not admin
        if not session.get('is_admin'):
            # Check if user is one of the class instructors
            instructor_user_id = session.get('user_id')
            instructors_data = load_instructors()
            user_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == instructor_user_id), None)
            if not user_instructor or user_instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Not authorized to delete this class'}), 403
        
        # Remove class
        classes_data['classes'] = [c for c in classes_data.get('classes', []) if c['class_id'] != class_id]
        save_classes(classes_data)
        
        # Remove all enrollments for this class
        enrollments_data = load_enrollments()
        enrollments_data['enrollments'] = [e for e in enrollments_data.get('enrollments', []) if e['class_id'] != class_id]
        save_enrollments(enrollments_data)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@classes_bp.route('/<class_id>/toggle-visibility', methods=['PATCH'])
@admin_required
def toggle_course_visibility(class_id):
    """Toggle course visibility (show/hide from students) - Admin only"""
    try:
        data = request.json or {}
        is_enabled = data.get('is_enabled', True)
        
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Update visibility
        cls['is_enabled'] = is_enabled
        save_classes(classes_data)
        
        return jsonify({
            'success': True,
            'is_enabled': is_enabled
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# Enrollment Routes
# ============================================

@classes_bp.route('/<class_id>/enrollments', methods=['GET'])
@instructor_or_admin_required
def get_class_enrollments(class_id):
    """Get enrollments for a specific class"""
    try:
        # Verify class exists and check ownership
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check ownership if not admin
        if not session.get('is_admin'):
            # Check if user is one of the class instructors
            instructor_user_id = session.get('user_id')
            instructors_data = load_instructors()
            user_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == instructor_user_id), None)
            if not user_instructor or user_instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Not authorized to view this class'}), 403
        
        enrollments_data = load_enrollments()
        users_data = load_users()
        
        class_enrollments = [e for e in enrollments_data.get('enrollments', []) if e['class_id'] == class_id]
        
        # Enrich with student info
        enriched_enrollments = []
        for enrollment in class_enrollments:
            # Handle both old and new enrollment formats
            student_user_id = enrollment.get('student_user_id') or enrollment.get('user_id')
            student = next((u for u in users_data.get('users', []) if u['user_id'] == student_user_id), None)
            if student:
                # Handle both status formats
                status = enrollment.get('status')
                if not status and enrollment.get('enrollment_status'):
                    status = 'approved' if enrollment.get('enrollment_status') == 'active' else enrollment.get('enrollment_status')
                if not status:
                    status = 'active'
                
                enriched_enrollments.append({
                    'enrollment_id': enrollment.get('enrollment_id'),
                    'student_user_id': student_user_id,
                    'student_name': student['full_name'],
                    'student_email': student['email'],
                    'status': status,
                    'enrolled_at': enrollment.get('enrolled_at', '')
                })
        
        return jsonify({'enrollments': enriched_enrollments})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/enrollments/my', methods=['GET'])
@authenticated_required
def get_my_enrollments():
    """Get current user's enrollments"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User authentication required'}), 401
        
        enrollments_data = load_enrollments()
        classes_data = load_classes()
        users_data = load_users()
        
        # Handle both old and new enrollment formats
        my_enrollments = [e for e in enrollments_data.get('enrollments', []) 
                         if e.get('student_user_id') == user_id or e.get('user_id') == user_id]
        
        # Enrich with class info and multiple instructors
        instructors_data = load_instructors()
        enriched_enrollments = []
        
        for enrollment in my_enrollments:
            cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == enrollment.get('class_id')), None)
            if cls:
                # Get all instructor names for this class
                instructor_ids = cls.get('instructor_ids', [])
                instructor_names = []
                
                for inst_id in instructor_ids:
                    instructor = next((i for i in instructors_data.get('instructors', []) if i['instructor_id'] == inst_id), None)
                    if instructor:
                        instructor_user = next((u for u in users_data.get('users', []) if u['user_id'] == instructor['user_id']), None)
                        if instructor_user:
                            instructor_names.append(instructor_user['full_name'])
                
                # Determine status (handle both old and new formats)
                status = enrollment.get('status', 'requested')
                if enrollment.get('enrollment_status') == 'active':
                    status = 'approved'
                
                # Get enrollment date (handle both formats)
                enrolled_at = enrollment.get('enrolled_at') or enrollment.get('requested_at', '')
                
                enriched_enrollments.append({
                    'enrollment_id': enrollment.get('enrollment_id', ''),
                    'class_id': enrollment.get('class_id'),
                    'class_code': cls.get('class_code', ''),
                    'class_title': cls.get('title', ''),
                    'class_description': cls.get('description', ''),
                    'class_schedule': cls.get('schedule', ''),
                    'semester': cls.get('semester', ''),
                    'course_type': cls.get('course_type', 'prompt_engineering'),
                    'instructor_names': instructor_names,
                    'instructor_name': ', '.join(instructor_names) if instructor_names else 'Unknown',
                    'status': status,
                    'request_type': enrollment.get('request_type', ''),
                    'requested_at': enrollment.get('requested_at', ''),
                    'enrolled_at': enrolled_at,
                    'approved_at': enrollment.get('approved_at'),
                    'approved_by': enrollment.get('approved_by')
                })
        
        return jsonify({'enrollments': enriched_enrollments})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/enroll', methods=['POST'])
@authenticated_required
def enroll_in_class():
    """Request enrolment in a class.

    Creates the enrolment as `pending`; an administrator approves it before
    the student can open the course. The response message says so — callers
    must show it rather than assuming success means access was granted.
    """
    try:
        from app.models import Course, Enrollment, User, db
        import hashlib

        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'error': 'User authentication required'}), 401

        # Ensure user exists in database (sync from JSON if needed)
        db_user = User.query.filter_by(id=user_id).first()
        if not db_user:
            # Check if user_id is a hex string (JSON user)
            if isinstance(user_id, str) and len(user_id) == 32:
                # Try to find user by username in database
                username = session.get('username')
                if username:
                    db_user = User.query.filter_by(username=username).first()
                    if not db_user:
                        # Create user in database from session data
                        def hash_password(password):
                            return hashlib.sha256(password.encode()).hexdigest()
                        
                        db_user = User(
                            username=username,
                            email=session.get('email', ''),
                            full_name=session.get('full_name', username),
                            password_hash='synced_from_json',  # placeholder
                            role='student'
                        )
                        db.session.add(db_user)
                        db.session.commit()
                        print(f"Created database user for enrollment: {db_user.id}")
                    
                    # Update session with database user ID
                    session['user_id'] = db_user.id
                    user_id = db_user.id
                else:
                    return jsonify({'error': 'User session is invalid. Please log in again.'}), 401
            else:
                return jsonify({'error': 'User not found in database. Please log in again.'}), 401

        data = request.json or {}
        class_id = data.get('class_id')

        if not class_id:
            return jsonify({'error': 'Class ID is required'}), 400

        # Find the course (try by ID, then by code, then partial match)
        course = Course.query.filter_by(id=class_id).first()
        if not course:
            course = Course.query.filter_by(code=class_id).first()
        if not course:
            course = Course.query.filter(Course.code.like(f"{class_id}%")).first()
        if not course:
            course = Course.query.filter(Course.code.like(f"%{class_id}%")).first()

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        if not course.is_published:
            return jsonify({'error': 'This course is currently not available'}), 403

        # Check per-course registration status
        if course.registration_open is False:
            return jsonify({'error': 'Registration for this course is currently closed by the admin.'}), 403

        # Check global registration pause
        try:
            from app.models import KeyValueSetting
            global_pause = KeyValueSetting.query.filter_by(key='registration_paused').first()
            if global_pause and global_pause.value == '1':
                return jsonify({'error': 'Course registration is temporarily paused. Please try again later.'}), 503
        except Exception:
            pass
        
        # Check if already enrolled
        existing = Enrollment.query.filter_by(
            user_id=user_id,
            course_id=course.id
        ).first()
        
        if existing:
            if existing.status in ['approved', 'active']:
                return jsonify({'error': 'Already enrolled in this class'}), 400
            # Update existing enrollment — always pending until admin approves
            existing.status = 'pending'
            existing.payment_status = 'not_required' if not course.requires_payment else 'pending'
            existing.enrolled_at = datetime.utcnow()
            db.session.commit()
            return jsonify({
                'success': True,
                'enrollment': {'class_id': course.id, 'status': 'pending'},
                'message': 'Registration submitted! Awaiting admin approval.',
                'requires_payment': course.requires_payment,
                'price': course.price or 0
            })

        # Create new enrollment — always pending until admin approves
        new_enrollment = Enrollment(
            user_id=user_id,
            course_id=course.id,
            status='pending',
            payment_status='not_required' if not course.requires_payment else 'pending',
            enrolled_at=datetime.utcnow()
        )
        db.session.add(new_enrollment)
        db.session.commit()
        return jsonify({
            'success': True,
            'enrollment': {'class_id': course.id, 'status': 'pending'},
            'message': 'Registration submitted! Awaiting admin approval.',
            'requires_payment': course.requires_payment,
            'price': course.price or 0
        })
        
    except Exception as e:
        print(f"Enrollment error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/enrollments/<enrollment_id>', methods=['DELETE'])
@authenticated_required
def unenroll(enrollment_id):
    """Unenroll from a class - Database only"""
    try:
        from app.models import Enrollment, Course, db

        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False) or session.get('role') in ['institution_admin', 'super_admin']

        # Find enrollment in database
        enrollment = Enrollment.query.filter_by(id=enrollment_id).first()

        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404

        # Check authorization - admins can delete any, users can delete their own
        if not is_admin and enrollment.user_id != user_id:
            return jsonify({'error': 'Not authorized to delete this enrollment'}), 403

        # Remove enrollment
        db.session.delete(enrollment)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        print(f"Unenroll error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/available', methods=['GET'])
@authenticated_required
def get_available_classes():
    """Get all available classes for enrollment (student view) - Database only"""
    try:
        from app.models import Course, Enrollment, User

        user_id = session.get('user_id')

        # Get all published courses
        all_courses = Course.query.filter(
            Course.is_published == True
        ).all()
        
        # Get user's enrollments
        user_enrollments = Enrollment.query.filter_by(user_id=user_id).all()
        user_enrollment_map = {e.course_id: e for e in user_enrollments}
        
        available_classes = []
        
        for course in all_courses:
            # Count approved enrollments for this course
            enrollment_count = Enrollment.query.filter(
                Enrollment.course_id == course.id,
                Enrollment.status.in_(['approved', 'active'])
            ).count()
            
            user_enrollment = user_enrollment_map.get(course.id)
            enrollment_status = user_enrollment.status if user_enrollment else None
            
            available_classes.append({
                'class_id': course.id,
                'title': course.title,
                'description': course.description or '',
                'course_type': 'prompt_engineering',
                'capacity': 30,
                'is_free': not course.requires_payment,
                'price': course.price or 0,
                'instructor_names': [],
                'instructor_name': 'Instructor',
                'current_enrollment': enrollment_count,
                'enrollment_status': enrollment_status,
                'is_enrolled': enrollment_status in ['approved', 'active'],
                'is_pending': enrollment_status == 'pending',
                'is_rejected': enrollment_status == 'rejected',
                'is_full': enrollment_count >= 30
            })
        
        return jsonify({'classes': available_classes})
    except Exception as e:
        print(f"Error getting available classes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/enrollments/<enrollment_id>/approve', methods=['POST'])
@instructor_or_admin_required
def approve_enrollment(enrollment_id):
    """Approve enrollment request (instructor or admin)"""
    try:
        enrollments_data = load_enrollments()
        enrollment = next((e for e in enrollments_data.get('enrollments', []) if e['enrollment_id'] == enrollment_id), None)
        
        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404
        
        if enrollment['status'] != 'requested':
            return jsonify({'error': 'Enrollment is not in requested status'}), 400
        
        # Check ownership if not admin
        if not session.get('is_admin'):
            classes_data = load_classes()
            cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == enrollment['class_id']), None)
            if not cls:
                return jsonify({'error': 'Class not found'}), 404
            
            # Check if user is one of the class instructors
            instructor_user_id = session.get('user_id')
            instructors_data = load_instructors()
            user_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == instructor_user_id), None)
            if not user_instructor or user_instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Not authorized to approve this enrollment'}), 403
        
        # Update enrollment status
        enrollment['status'] = 'approved'
        enrollment['approved_at'] = datetime.now().isoformat()
        enrollment['approved_by'] = session.get('username') or 'admin'
        
        save_enrollments(enrollments_data)
        
        return jsonify({
            'success': True,
            'enrollment': enrollment
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/enrollments/<enrollment_id>/reject', methods=['POST'])
@instructor_or_admin_required
def reject_enrollment(enrollment_id):
    """Reject enrollment request (instructor or admin)"""
    try:
        enrollments_data = load_enrollments()
        enrollment = next((e for e in enrollments_data.get('enrollments', []) if e['enrollment_id'] == enrollment_id), None)
        
        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404
        
        if enrollment['status'] != 'requested':
            return jsonify({'error': 'Enrollment is not in requested status'}), 400
        
        # Check ownership if not admin
        if not session.get('is_admin'):
            classes_data = load_classes()
            cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == enrollment['class_id']), None)
            if not cls:
                return jsonify({'error': 'Class not found'}), 404
            
            # Check if user is one of the class instructors
            instructor_user_id = session.get('user_id')
            instructors_data = load_instructors()
            user_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == instructor_user_id), None)
            if not user_instructor or user_instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Not authorized to reject this enrollment'}), 403
        
        # Update enrollment status
        enrollment['status'] = 'rejected'
        enrollment['rejected_at'] = datetime.now().isoformat()
        enrollment['rejected_by'] = session.get('username') or 'admin'
        
        save_enrollments(enrollments_data)
        
        return jsonify({
            'success': True,
            'enrollment': enrollment
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/enrollments/assign', methods=['POST'])
@admin_required
def assign_student_to_class():
    """Admin directly assigns a student to a class (bypasses approval)"""
    try:
        data = request.json or {}
        class_id = data.get('class_id')
        student_user_id = data.get('student_user_id')
        
        if not class_id or not student_user_id:
            return jsonify({'error': 'Class ID and student user ID are required'}), 400
        
        # Verify class and student exist
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        users_data = load_users()
        student = next((u for u in users_data.get('users', []) if u['user_id'] == student_user_id), None)
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Check if already enrolled
        enrollments_data = load_enrollments()
        existing = next((e for e in enrollments_data.get('enrollments', []) 
                        if e['class_id'] == class_id and e['student_user_id'] == student_user_id), None)
        
        if existing:
            if existing['status'] == 'approved':
                return jsonify({'error': 'Student already enrolled in this class'}), 400
            else:
                # Update existing enrollment to approved
                existing['status'] = 'approved'
                existing['request_type'] = 'assigned_by_admin'
                existing['approved_at'] = datetime.now().isoformat()
                existing['approved_by'] = 'admin'
                save_enrollments(enrollments_data)
                return jsonify({
                    'success': True,
                    'enrollment': existing
                })
        
        # Check capacity
        approved_enrollments = len([e for e in enrollments_data.get('enrollments', []) 
                                    if e['class_id'] == class_id and e.get('status') == 'approved'])
        if approved_enrollments >= cls.get('capacity', 30):
            return jsonify({'error': 'Class is full'}), 400
        
        # Create approved enrollment
        enrollment_id = generate_id('enroll', enrollments_data.get('enrollments', []))
        new_enrollment = {
            'enrollment_id': enrollment_id,
            'class_id': class_id,
            'student_user_id': student_user_id,
            'status': 'approved',
            'request_type': 'assigned_by_admin',
            'requested_at': datetime.now().isoformat(),
            'approved_at': datetime.now().isoformat(),
            'approved_by': 'admin'
        }
        
        enrollments_data.setdefault('enrollments', []).append(new_enrollment)
        save_enrollments(enrollments_data)
        
        return jsonify({
            'success': True,
            'enrollment': new_enrollment
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/add-instructor', methods=['POST'])
@admin_required
def add_instructor_to_class(class_id):
    """Admin adds an instructor to a class"""
    try:
        data = request.json or {}
        instructor_id = data.get('instructor_id')
        
        if not instructor_id:
            return jsonify({'error': 'Instructor ID is required'}), 400
        
        # Verify class exists
        classes_data = load_classes()
        class_obj = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not class_obj:
            return jsonify({'error': 'Class not found'}), 404
        
        # Verify instructor exists
        instructors_data = load_instructors()
        instructor = next((i for i in instructors_data.get('instructors', []) if i['instructor_id'] == instructor_id), None)
        if not instructor:
            return jsonify({'error': 'Instructor not found'}), 404
        
        # Check if instructor is already assigned
        if 'instructor_ids' not in class_obj:
            class_obj['instructor_ids'] = [class_obj.get('instructor_id')] if class_obj.get('instructor_id') else []
        
        if instructor_id in class_obj['instructor_ids']:
            return jsonify({'error': 'Instructor is already assigned to this class'}), 400
        
        # Add instructor to class
        class_obj['instructor_ids'].append(instructor_id)
        save_classes(classes_data)
        
        return jsonify({
            'success': True,
            'message': 'Instructor added to class successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/remove-instructor', methods=['POST'])
@admin_required
def remove_instructor_from_class(class_id):
    """Admin removes an instructor from a class"""
    try:
        data = request.json or {}
        instructor_id = data.get('instructor_id')
        
        if not instructor_id:
            return jsonify({'error': 'Instructor ID is required'}), 400
        
        # Verify class exists
        classes_data = load_classes()
        class_obj = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not class_obj:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check if instructor is assigned
        if 'instructor_ids' not in class_obj:
            class_obj['instructor_ids'] = [class_obj.get('instructor_id')] if class_obj.get('instructor_id') else []
        
        if instructor_id not in class_obj['instructor_ids']:
            return jsonify({'error': 'Instructor is not assigned to this class'}), 400
        
        # Don't allow removing the last instructor
        if len(class_obj['instructor_ids']) <= 1:
            return jsonify({'error': 'Cannot remove the last instructor from a class'}), 400
        
        # Remove instructor from class
        class_obj['instructor_ids'].remove(instructor_id)
        save_classes(classes_data)
        
        return jsonify({
            'success': True,
            'message': 'Instructor removed from class successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/enroll', methods=['POST'])
@admin_required
def admin_enroll_student(class_id):
    """Admin directly enrolls a student in a class"""
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        status = data.get('status', 'approved')  # Admin enrollments are auto-approved
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Verify class exists
        classes_data = load_classes()
        class_obj = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not class_obj:
            return jsonify({'error': 'Class not found'}), 404
        
        # Verify user exists
        users_data = load_users()
        user = next((u for u in users_data.get('users', []) if u['user_id'] == user_id), None)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user is already enrolled
        enrollments_data = load_enrollments()
        existing_enrollment = next((e for e in enrollments_data.get('enrollments', []) 
                                   if e['class_id'] == class_id and e['user_id'] == user_id), None)
        
        if existing_enrollment:
            return jsonify({'error': 'User is already enrolled in this class'}), 400
        
        # Create enrollment
        enrollment_id = generate_id('enroll', enrollments_data.get('enrollments', []))
        new_enrollment = {
            'enrollment_id': enrollment_id,
            'class_id': class_id,
            'user_id': user_id,
            'status': status,
            'enrolled_at': datetime.now().isoformat(),
            'approved_at': datetime.now().isoformat() if status == 'approved' else None
        }
        
        enrollments_data.setdefault('enrollments', []).append(new_enrollment)
        save_enrollments(enrollments_data)
        
        return jsonify({
            'success': True,
            'enrollment': new_enrollment
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/users/promote-to-instructor', methods=['POST'])
@admin_required
def promote_to_instructor():
    """Admin promotes a student to instructor"""
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        bio = data.get('bio', '')
        expertise = data.get('expertise', [])
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Verify user exists
        users_data = load_users()
        user = next((u for u in users_data.get('users', []) if u['user_id'] == user_id), None)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if already an instructor
        instructors_data = load_instructors()
        existing_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == user_id), None)
        if existing_instructor:
            return jsonify({'error': 'User is already an instructor'}), 400
        
        # Update user role to Instructor
        user['role'] = 'Instructor'
        save_users(users_data)
        
        # Create instructor profile
        instructor_id = generate_id('inst', instructors_data.get('instructors', []))
        new_instructor = {
            'instructor_id': instructor_id,
            'user_id': user_id,
            'bio': bio,
            'expertise': expertise if isinstance(expertise, list) else [expertise] if expertise else [],
            'created_at': datetime.now().isoformat()
        }
        
        instructors_data.setdefault('instructors', []).append(new_instructor)
        save_instructors(instructors_data)
        
        return jsonify({
            'success': True,
            'instructor': new_instructor,
            'user': user
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/students-data', methods=['GET'])
@instructor_or_admin_required
def get_class_students_data(class_id):
    """Get enrolled students with their attendance, survey, and exit exam data (instructor/admin only)"""
    try:
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # Verify class exists
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check authorization - instructor must be assigned to this class
        if not is_admin:
            instructors_data = load_instructors()
            user_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == user_id), None)
            if not user_instructor or user_instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Not authorized to view this class data'}), 403
        
        # Get enrolled students (handle both enrollment formats)
        enrollments_data = load_enrollments()
        class_enrollments = [e for e in enrollments_data.get('enrollments', []) 
                           if e.get('class_id') == class_id and 
                           (e.get('status') == 'approved' or e.get('enrollment_status') == 'active')]
        
        # Load all data files
        users_data = load_users()
        attendance_data = load_attendance()
        survey_data = load_survey_data()
        exit_exam_data = load_exit_exam_data()
        
        # Build student data
        students_data = []
        for enrollment in class_enrollments:
            student_user_id = enrollment.get('student_user_id') or enrollment.get('user_id')
            student = next((u for u in users_data.get('users', []) if u['user_id'] == student_user_id), None)
            
            if not student:
                continue
            
            # Get attendance records for this student
            student_attendance = [a for a in attendance_data.get('attendance', []) 
                                if a.get('user_id') == student_user_id]
            
            # Get survey data for this student
            student_survey = next((s for s in survey_data.get('users', []) 
                                 if s.get('id') == student_user_id), None)
            
            # Get exit exam data for this student
            student_exam = next((e for e in exit_exam_data.get('users', []) 
                               if e.get('id') == student_user_id), None)
            
            students_data.append({
                'user_id': student_user_id,
                'username': student.get('username'),
                'full_name': student.get('full_name'),
                'email': student.get('email'),
                'role': student.get('role'),
                'enrolled_at': enrollment.get('approved_at'),
                'attendance': {
                    'total_records': len(student_attendance),
                    'records': student_attendance
                },
                'survey': {
                    'completed': student_survey is not None,
                    'submitted_at': student_survey.get('submitted_at') if student_survey else None,
                    'answers': student_survey.get('answers', []) if student_survey else []
                },
                'exit_exam': {
                    'completed': student_exam is not None,
                    'submitted_at': student_exam.get('submitted_at') if student_exam else None,
                    'score': student_exam.get('score') if student_exam else None,
                    'total_questions': student_exam.get('total_questions') if student_exam else None,
                    'certificate_status': student_exam.get('certificate_status') if student_exam else None
                }
            })
        
        return jsonify({
            'success': True,
            'class_id': class_id,
            'class_title': cls.get('title'),
            'students': students_data
        })
    except Exception as e:
        print(f"Error getting class students data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def load_attendance():
    """Load attendance data from JSON file"""
    attendance_file = 'attendance.json'
    if os.path.exists(attendance_file):
        with open(attendance_file, 'r') as f:
            return json.load(f)
    return {'attendance': []}


def load_survey_data():
    """Load survey data from JSON file"""
    survey_file = 'users_survey_data.json'
    if os.path.exists(survey_file):
        with open(survey_file, 'r') as f:
            return json.load(f)
    return {'users': []}


def load_exit_exam_data():
    """Load exit exam data from JSON file"""
    exam_file = 'users_exit_exam_data.json'
    if os.path.exists(exam_file):
        with open(exam_file, 'r') as f:
            return json.load(f)
    return {'users': []}


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


# ============================================
# Course File Management Routes
# ============================================

@classes_bp.route('/<class_id>/files', methods=['POST'])
@instructor_or_admin_required
def upload_course_file(class_id):
    """Upload a file to a course (instructors and admins)"""
    try:
        from werkzeug.utils import secure_filename
        
        # Check if class exists
        classes_data = load_classes()
        class_obj = next((c for c in classes_data.get('classes', []) if c.get('class_id') == class_id), None)
        if not class_obj:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Create course files directory if it doesn't exist
        os.makedirs(COURSE_FILES_DIR, exist_ok=True)
        
        # Sanitize filename to prevent path traversal
        original_filename = secure_filename(file.filename)
        if not original_filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Generate unique filename with sanitized original
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_filename = f"{class_id}_{timestamp}_{original_filename}"
        file_path = os.path.join(COURSE_FILES_DIR, safe_filename)
        
        # Ensure file path is within the course files directory (additional security check)
        file_path = os.path.abspath(file_path)
        course_files_dir = os.path.abspath(COURSE_FILES_DIR)
        if not file_path.startswith(course_files_dir + os.sep):
            return jsonify({'error': 'Invalid file path'}), 400
        
        # Save file
        file.save(file_path)
        
        # Save metadata (store sanitized filename for display)
        files_data = load_course_files()
        uploaded_by = session.get('user_id', 'admin') if not session.get('is_admin') else 'admin'
        file_metadata = {
            'id': f"file_{timestamp}_{class_id}",
            'class_id': class_id,
            'filename': original_filename,  # Already sanitized
            'stored_filename': safe_filename,
            'file_path': file_path,
            'uploaded_by': uploaded_by,
            'uploaded_at': datetime.now().isoformat(),
            'file_size': os.path.getsize(file_path)
        }
        
        files_data['files'].append(file_metadata)
        save_course_files(files_data)
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file': file_metadata
        }), 200
        
    except Exception as e:
        print(f"Error uploading course file: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/files', methods=['GET'])
@authenticated_required
def get_course_files(class_id):
    """Get all files for a course (enrolled students and admins can access)"""
    try:
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # Check if class exists
        classes_data = load_classes()
        class_obj = next((c for c in classes_data.get('classes', []) if c.get('class_id') == class_id), None)
        if not class_obj:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check if user is enrolled in the class (unless admin)
        if not is_admin:
            enrollments_data = load_enrollments()
            is_enrolled = any(
                e.get('class_id') == class_id and 
                e.get('student_user_id') == user_id and 
                e.get('status') == 'approved'
                for e in enrollments_data.get('enrollments', [])
            )
            
            if not is_enrolled:
                return jsonify({'error': 'Not enrolled in this class'}), 403
        
        # Get files for this class
        files_data = load_course_files()
        class_files = [
            f for f in files_data.get('files', []) 
            if f['class_id'] == class_id
        ]
        
        return jsonify({
            'success': True,
            'files': class_files
        }), 200
        
    except Exception as e:
        print(f"Error getting course files: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/files/<file_id>', methods=['DELETE'])
@instructor_or_admin_required
def delete_course_file(class_id, file_id):
    """Delete a file from a course (instructors and admins)"""
    try:
        files_data = load_course_files()
        file_obj = next((f for f in files_data.get('files', []) if f['id'] == file_id and f['class_id'] == class_id), None)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        # Delete physical file
        if os.path.exists(file_obj['file_path']):
            os.remove(file_obj['file_path'])
        
        # Remove from metadata
        files_data['files'] = [f for f in files_data['files'] if f['id'] != file_id]
        save_course_files(files_data)
        
        return jsonify({
            'success': True,
            'message': 'File deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"Error deleting course file: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/files/<file_id>/download', methods=['GET'])
@authenticated_required
def download_course_file(class_id, file_id):
    """Download a course file (enrolled students and admins can access)"""
    try:
        from flask import send_file
        
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # Check if user is enrolled in the class (unless admin)
        if not is_admin:
            enrollments_data = load_enrollments()
            is_enrolled = any(
                e.get('class_id') == class_id and 
                e.get('student_user_id') == user_id and 
                e.get('status') == 'approved'
                for e in enrollments_data.get('enrollments', [])
            )
            
            if not is_enrolled:
                return jsonify({'error': 'Not enrolled in this class'}), 403
        
        # Get file metadata
        files_data = load_course_files()
        file_obj = next((f for f in files_data.get('files', []) if f['id'] == file_id and f['class_id'] == class_id), None)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        # Send file
        return send_file(
            file_obj['file_path'],
            as_attachment=True,
            download_name=file_obj['filename']
        )
        
    except Exception as e:
        print(f"Error downloading course file: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# Class Management - Remove/Block Students
# ============================================

@classes_bp.route('/<class_id>/students/<student_user_id>/status', methods=['PUT'])
@instructor_or_admin_required
def update_student_enrollment_status(class_id, student_user_id):
    """Update student enrollment status (approve/block/reject) - Admin & Instructor"""
    try:
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        data = request.json or {}
        new_status = data.get('status')  # 'approved', 'blocked', 'rejected'
        
        if new_status not in ['approved', 'blocked', 'rejected']:
            return jsonify({'error': 'Invalid status. Must be approved, blocked, or rejected'}), 400
        
        # Verify class exists
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check authorization - instructor must be assigned to this class
        if not is_admin:
            instructors_data = load_instructors()
            user_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == user_id), None)
            if not user_instructor or user_instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Not authorized to manage students in this class'}), 403
        
        # Find and update enrollment
        enrollments_data = load_enrollments()
        enrollment = next((e for e in enrollments_data.get('enrollments', []) 
                          if e['class_id'] == class_id and e['student_user_id'] == student_user_id), None)
        
        if not enrollment:
            return jsonify({'error': 'Student not enrolled in this class'}), 404
        
        # Update status
        old_status = enrollment.get('status', 'unknown')
        enrollment['status'] = new_status
        enrollment['modified_at'] = datetime.now().isoformat()
        enrollment['modified_by'] = 'admin' if is_admin else user_id
        
        if new_status == 'approved':
            enrollment['approved_at'] = datetime.now().isoformat()
            enrollment['approved_by'] = 'admin' if is_admin else user_id
        elif new_status == 'blocked':
            enrollment['blocked_at'] = datetime.now().isoformat()
            enrollment['blocked_by'] = 'admin' if is_admin else user_id
        
        save_enrollments(enrollments_data)
        
        return jsonify({
            'success': True,
            'message': f'Student status updated from {old_status} to {new_status}',
            'enrollment': enrollment
        })
        
    except Exception as e:
        print(f"Error updating student status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/students/<student_user_id>', methods=['DELETE'])
@instructor_or_admin_required
def remove_student_from_class(class_id, student_user_id):
    """Remove/delete a student from a class (instructor/admin only)"""
    try:
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # Verify class exists
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check authorization - instructor must be assigned to this class
        if not is_admin:
            instructors_data = load_instructors()
            user_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == user_id), None)
            if not user_instructor or user_instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Not authorized to remove students from this class'}), 403
        
        # Find and remove enrollment
        enrollments_data = load_enrollments()
        enrollment = next((e for e in enrollments_data.get('enrollments', []) 
                          if e['class_id'] == class_id and e['student_user_id'] == student_user_id), None)
        
        if not enrollment:
            return jsonify({'error': 'Student not enrolled in this class'}), 404
        
        # Remove enrollment
        enrollments_data['enrollments'] = [e for e in enrollments_data.get('enrollments', []) 
                                          if not (e['class_id'] == class_id and e['student_user_id'] == student_user_id)]
        save_enrollments(enrollments_data)
        
        return jsonify({
            'success': True,
            'message': 'Student removed from class successfully'
        })
        
    except Exception as e:
        print(f"Error removing student: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/students/<student_user_id>/certificate', methods=['POST'])
@instructor_or_admin_required
def issue_student_certificate(class_id, student_user_id):
    """Issue/approve certificate for a student (instructor/admin only)"""
    try:
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # Verify class exists
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check authorization
        if not is_admin:
            instructors_data = load_instructors()
            user_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == user_id), None)
            if not user_instructor or user_instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Not authorized to issue certificates for this class'}), 403
        
        # Load student data
        users_data = load_users()
        student = next((u for u in users_data.get('users', []) if u['user_id'] == student_user_id), None)
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Get certificate type from request
        data = request.get_json() or {}
        cert_type = data.get('type', 'exit_exam')  # 'entry_survey' or 'exit_exam'
        
        # Update certificate status based on type
        if cert_type == 'entry_survey':
            survey_data = load_survey_data()
            student_survey = next((s for s in survey_data.get('users', []) if s.get('id') == student_user_id), None)
            
            if not student_survey:
                return jsonify({'error': 'Student has not completed entry survey'}), 400
            
            student_survey['certificate_status'] = 'pass'
            student_survey['admin_override'] = True
            
            with open('users_survey_data.json', 'w') as f:
                json.dump(survey_data, f, indent=2)
                
        elif cert_type == 'exit_exam':
            exam_data = load_exit_exam_data()
            student_exam = next((e for e in exam_data.get('users', []) if e.get('id') == student_user_id), None)
            
            if not student_exam:
                return jsonify({'error': 'Student has not completed exit exam'}), 400
            
            student_exam['certificate_status'] = 'pass'
            student_exam['admin_override'] = True
            
            with open('users_exit_exam_data.json', 'w') as f:
                json.dump(exam_data, f, indent=2)
        else:
            return jsonify({'error': 'Invalid certificate type'}), 400
        
        return jsonify({
            'success': True,
            'message': f'Certificate approved for {student.get("full_name")}',
            'type': cert_type
        })
        
    except Exception as e:
        print(f"Error issuing certificate: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/details', methods=['GET'])
@instructor_or_admin_required
def get_class_full_details(class_id):
    """Get complete class details including students, files, and metadata"""
    try:
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # Verify class exists
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check authorization
        if not is_admin:
            instructors_data = load_instructors()
            user_instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == user_id), None)
            if not user_instructor or user_instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Not authorized to view this class'}), 403
        
        # Get enrolled students with detailed data (handle both enrollment formats)
        enrollments_data = load_enrollments()
        class_enrollments = [e for e in enrollments_data.get('enrollments', []) 
                           if e.get('class_id') == class_id and 
                           (e.get('status') == 'approved' or e.get('enrollment_status') == 'active')]
        
        users_data = load_users()
        attendance_data = load_attendance()
        survey_data = load_survey_data()
        exit_exam_data = load_exit_exam_data()
        
        students_data = []
        for enrollment in class_enrollments:
            student_user_id = enrollment.get('student_user_id') or enrollment.get('user_id')
            student = next((u for u in users_data.get('users', []) if u['user_id'] == student_user_id), None)
            
            if not student:
                continue
            
            student_attendance = [a for a in attendance_data.get('attendance', []) 
                                if a.get('user_id') == student_user_id]
            student_survey = next((s for s in survey_data.get('users', []) 
                                 if s.get('id') == student_user_id), None)
            student_exam = next((e for e in exit_exam_data.get('users', []) 
                               if e.get('id') == student_user_id), None)
            
            students_data.append({
                'user_id': student_user_id,
                'username': student.get('username'),
                'full_name': student.get('full_name'),
                'email': student.get('email'),
                'phone': student.get('phone'),
                'organization': student.get('organization'),
                'role': student.get('role'),
                'enrolled_at': enrollment.get('approved_at'),
                'attendance': {
                    'total': len(student_attendance),
                    'records': student_attendance
                },
                'entry_survey': {
                    'completed': student_survey is not None,
                    'submitted_at': student_survey.get('timestamp') if student_survey else None,
                    'score': student_survey.get('score') if student_survey else None,
                    'certificate_status': student_survey.get('certificate_status') if student_survey else None
                },
                'exit_exam': {
                    'completed': student_exam is not None,
                    'submitted_at': student_exam.get('timestamp') if student_exam else None,
                    'score': student_exam.get('score') if student_exam else None,
                    'percentage': round((student_exam.get('score', 0) / student_exam.get('total_questions', 1)) * 100, 1) if student_exam else 0,
                    'certificate_status': student_exam.get('certificate_status') if student_exam else None
                }
            })
        
        # Get class files
        files_data = load_course_files()
        class_files = [f for f in files_data.get('files', []) if f['class_id'] == class_id]
        
        # Get instructor details
        instructors_data = load_instructors()
        instructor_details = []
        for inst_id in cls.get('instructor_ids', []):
            instructor = next((i for i in instructors_data.get('instructors', []) if i['instructor_id'] == inst_id), None)
            if instructor:
                user = next((u for u in users_data.get('users', []) if u['user_id'] == instructor['user_id']), None)
                if user:
                    instructor_details.append({
                        'instructor_id': inst_id,
                        'name': user.get('full_name'),
                        'email': user.get('email'),
                        'bio': instructor.get('bio'),
                        'expertise': instructor.get('expertise', [])
                    })
        
        return jsonify({
            'success': True,
            'class': {
                'class_id': cls['class_id'],
                'title': cls['title'],
                'description': cls.get('description'),
                'semester': cls.get('semester'),
                'year': cls.get('year'),
                'class_code': cls.get('class_code'),
                'capacity': cls.get('capacity'),
                'created_at': cls.get('created_at'),
                'instructors': instructor_details,
                'total_enrolled': len(students_data),
                'files': class_files
            },
            'students': students_data
        })
        
    except Exception as e:
        print(f"Error getting class details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# Course Types & Multi-Course Management
# ============================================

COURSE_TYPES_FILE = 'course_types.json'

def load_course_types():
    """Load course types from JSON file"""
    if os.path.exists(COURSE_TYPES_FILE):
        with open(COURSE_TYPES_FILE, 'r') as f:
            return json.load(f)
    return {'course_types': []}


@classes_bp.route('/course-types', methods=['GET'])
@authenticated_required
def get_course_types():
    """Get all available course types"""
    try:
        data = load_course_types()
        return jsonify({
            'success': True,
            'course_types': data.get('course_types', [])
        })
    except Exception as e:
        print(f"Error loading course types: {e}")
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/my-courses', methods=['GET'])
@authenticated_required
def get_my_courses():
    """Get user's enrolled and available courses - Database only"""
    try:
        from app.models import Course, Enrollment, User

        user_id = session.get('user_id')
        course_types = load_course_types()

        # Enrolments that matter to the student: granted, or waiting on an
        # admin. A pending request used to be fetched here and then dropped,
        # so the course fell back into "Available" with an Enrol button and
        # the student's request appeared to have vanished.
        user_enrollments = Enrollment.query.filter(
            Enrollment.user_id == user_id,
            Enrollment.status.in_(['approved', 'active', 'pending'])
        ).all()
        enrollment_by_course = {e.course_id: e for e in user_enrollments}

        # Get all published courses
        all_courses = Course.query.filter(
            Course.is_published == True
        ).all()
        
        enrolled_courses = []
        available_courses = []
        
        for course in all_courses:
            class_info = {
                'class_id': course.id,
                'title': course.title,
                'description': course.description or '',
                'course_type': 'prompt_engineering',
                'semester': '',
                'schedule': '',
                'is_free': not course.requires_payment,
                'price': course.price or 0.0,
                'preview_description': course.description or '',
                'preview_toc': '',
                'preview_image': course.thumbnail_url or ''
            }
            
            enrollment = enrollment_by_course.get(course.id)
            if enrollment is None:
                available_courses.append(class_info)
                continue

            granted = enrollment.status in ('approved', 'active')
            class_info['status'] = enrollment.status
            class_info['awaiting_approval'] = not granted
            class_info['enrollment_date'] = (
                enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None)
            class_info['payment_verified'] = enrollment.payment_status in (
                'paid', 'not_required', 'waived')
            # A pending course is listed so the student can see the request was
            # received. Access to its content is a separate check, and still
            # requires an approved or active enrolment.
            class_info['can_open'] = granted
            enrolled_courses.append(class_info)
        
        return jsonify({
            'success': True,
            'enrolled_courses': enrolled_courses,
            'available_courses': available_courses,
            'pending_count': sum(1 for c in enrolled_courses
                                 if c.get('awaiting_approval')),
            'course_types': course_types.get('course_types', [])
        })
        
    except Exception as e:
        print(f"Error getting my courses: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/verify-payment', methods=['POST'])
@admin_required
def verify_payment():
    """Admin: Verify payment and grant course access - Database only"""
    try:
        from app.models import Enrollment, Course, db

        data = request.json
        user_id = data.get('user_id')
        class_id = data.get('class_id')

        if not user_id or not class_id:
            return jsonify({'error': 'User ID and Class ID required'}), 400

        # Find enrollment in database
        enrollment = Enrollment.query.filter_by(
            user_id=user_id,
            course_id=class_id
        ).first()

        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404

        # Update enrollment
        enrollment.payment_status = 'paid'
        enrollment.status = 'approved'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Payment verified and course access granted'
        })
        
    except Exception as e:
        print(f"Error verifying payment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/enrollments', methods=['GET'])
@admin_required
def get_all_enrollments():
    """Admin: Get all enrollments (for payment verification) - Database only"""
    try:
        from app.models import Enrollment, Course, User

        # Get all enrollments
        enrollments = Enrollment.query.all()
        
        enriched_enrollments = []
        for enrollment in enrollments:
            # Get student info
            student = User.query.get(enrollment.user_id)
            student_name = student.full_name if student else 'Unknown Student'
            student_username = student.username if student else ''
            
            # Get course info
            course = Course.query.get(enrollment.course_id)
            course_title = course.title if course else 'Unknown Course'
            course_code = course.code if course else ''
            pricing_type = 'paid' if course and course.requires_payment else 'free'
            price = course.price if course else 0
            
            # Format enrollment date
            formatted_date = 'N/A'
            if enrollment.enrolled_at:
                formatted_date = enrollment.enrolled_at.strftime('%Y-%m-%d %H:%M')
            
            enriched_enrollments.append({
                'enrollment_id': enrollment.id,
                'user_id': enrollment.user_id,
                'class_id': enrollment.course_id,
                'status': enrollment.status,
                'payment_status': enrollment.payment_status,
                'payment_verified': enrollment.payment_status in ['paid', 'not_required', 'waived'],
                'student_name': student_name,
                'student_username': student_username,
                'course_title': course_title,
                'course_code': course_code,
                'pricing_type': pricing_type,
                'price': price,
                'enrollment_date_formatted': formatted_date
            })
        
        return jsonify({
            'success': True,
            'enrollments': enriched_enrollments
        })
        
    except Exception as e:
        print(f"Error getting enrollments: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/user-course-types', methods=['GET'])
@authenticated_required
def get_user_course_types():
    """Get course types user is enrolled in (for role-based UI)"""
    try:
        user_id = session.get('user_id')
        
        # If no user_id (e.g., admin or instructor), return empty course types
        if not user_id:
            return jsonify({
                'success': True,
                'course_types': []
            })
        
        # Load data
        classes_data = load_classes()
        enrollments_data = load_enrollments()
        
        # Get user's active enrollments
        user_enrollments = [e for e in enrollments_data.get('enrollments', []) 
                          if e.get('user_id') == user_id and 
                          e.get('enrollment_status') == 'active' and
                          e.get('payment_verified', True)]
        
        enrolled_class_ids = [e['class_id'] for e in user_enrollments]
        
        # Get course types from enrolled classes
        course_types = set()
        for cls in classes_data.get('classes', []):
            if cls['class_id'] in enrolled_class_ids:
                course_types.add(cls.get('course_type', 'prompt_engineering'))
        
        return jsonify({
            'success': True,
            'course_types': list(course_types)
        })
        
    except Exception as e:
        print(f"Error getting user course types: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/students-by-class/<class_id>', methods=['GET'])
@instructor_or_admin_required
def get_students_by_class(class_id):
    """Get all students enrolled in a specific class (for Admin Students per Class view)"""
    try:
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # Load data
        classes_data = load_classes()
        enrollments_data = load_enrollments()
        users_data = load_users()
        
        # Find the class
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check if instructor has access to this class
        if not is_admin:
            instructors_data = load_instructors()
            instructor = next((i for i in instructors_data.get('instructors', []) 
                             if i['user_id'] == user_id), None)
            if not instructor or instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Access denied to this class'}), 403
        
        # Get students enrolled in this class
        class_enrollments = [e for e in enrollments_data.get('enrollments', []) 
                            if e['class_id'] == class_id]
        
        students = []
        for enrollment in class_enrollments:
            user = next((u for u in users_data.get('users', []) 
                        if u['user_id'] == enrollment['user_id']), None)
            if user:
                students.append({
                    'user_id': user['user_id'],
                    'full_name': user.get('full_name'),
                    'email': user.get('email'),
                    'enrollment_status': enrollment.get('enrollment_status'),
                    'payment_verified': enrollment.get('payment_verified', True),
                    'enrolled_at': enrollment.get('enrolled_at')
                })
        
        return jsonify({
            'success': True,
            'class': {
                'class_id': cls['class_id'],
                'title': cls['title'],
                'course_type': cls.get('course_type')
            },
            'students': students,
            'total': len(students)
        })
        
    except Exception as e:
        print(f"Error getting students by class: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# CLASS EXAM ROUTES
# ============================================

@classes_bp.route('/<class_id>/exam/template', methods=['GET'])
@instructor_or_admin_required
def download_exam_template(class_id):
    """Download CSV template for exam questions"""
    try:
        # Create CSV template
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Question Number', 'Question Text', 'Option A', 'Option B', 'Option C', 'Option D', 'Correct Answer (A/B/C/D)', 'Points'])
        
        # Write sample data
        writer.writerow(['1', 'What is prompt engineering?', 'Writing code', 'Designing AI prompts', 'Testing software', 'Database design', 'B', '5'])
        writer.writerow(['2', 'Which model is best for image generation?', 'GPT-4', 'DALL-E', 'Claude', 'Gemini', 'B', '5'])
        writer.writerow(['3', 'What does API stand for?', 'Application Programming Interface', 'Advanced Programming Interface', 'Automated Process Integration', 'Application Process Interface', 'A', '5'])
        
        # Convert to bytes
        output.seek(0)
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=exam_template_{class_id}.csv'
        
        return response
        
    except Exception as e:
        print(f"Error generating exam template: {e}")
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/exam/upload', methods=['POST'])
@instructor_or_admin_required
def upload_exam(class_id):
    """Upload exam questions from CSV file"""
    try:
        # Verify class exists and user has access
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # CRITICAL: Check instructor ownership - Only instructors of THIS class or admins can upload
        if not is_admin:
            instructors_data = load_instructors()
            instructor = next((i for i in instructors_data.get('instructors', []) 
                             if i['user_id'] == user_id), None)
            if not instructor or instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Only instructors assigned to this class can upload exams'}), 403
        
        # Check for file
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # SECURITY: Validate file type and size
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are allowed'}), 400
        
        # Check file size (max 5MB)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 5 * 1024 * 1024:  # 5MB limit
            return jsonify({'error': 'File size exceeds 5MB limit'}), 400
        
        if file_size == 0:
            return jsonify({'error': 'File is empty'}), 400
        
        # Parse CSV with encoding fallback
        try:
            content = file.stream.read()
            try:
                decoded_content = content.decode('UTF-8')
            except UnicodeDecodeError:
                decoded_content = content.decode('latin-1')  # Fallback encoding
            
            stream = io.StringIO(decoded_content, newline=None)
            csv_reader = csv.reader(stream)
        except Exception as e:
            return jsonify({'error': f'Failed to read CSV file: {str(e)}'}), 400
        
        questions = []
        headers = next(csv_reader, None)  # Skip header
        
        if not headers:
            return jsonify({'error': 'CSV file is empty'}), 400
        
        for row_num, row in enumerate(csv_reader, start=2):
            if len(row) < 8:
                return jsonify({'error': f'Row {row_num} has insufficient columns. Expected 8 columns.'}), 400
            
            question_num, question_text, option_a, option_b, option_c, option_d, correct_answer, points = row
            
            # Validate correct answer
            correct_answer = correct_answer.strip().upper()
            if correct_answer not in ['A', 'B', 'C', 'D']:
                return jsonify({'error': f'Row {row_num}: Correct answer must be A, B, C, or D'}), 400
            
            # Validate points
            try:
                points = float(points)
            except ValueError:
                return jsonify({'error': f'Row {row_num}: Points must be a number'}), 400
            
            questions.append({
                'question_number': question_num.strip(),
                'question_text': question_text.strip(),
                'options': {
                    'A': option_a.strip(),
                    'B': option_b.strip(),
                    'C': option_c.strip(),
                    'D': option_d.strip()
                },
                'correct_answer': correct_answer,
                'points': points
            })
        
        if not questions:
            return jsonify({'error': 'No valid questions found in CSV'}), 400
        
        # Save exam
        exams_data = load_class_exams()
        
        # Remove existing exam for this class
        exams_data['exams'] = [e for e in exams_data.get('exams', []) if e['class_id'] != class_id]
        
        # Add new exam
        exam = {
            'exam_id': f"exam_{class_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'class_id': class_id,
            'questions': questions,
            'total_points': sum(q['points'] for q in questions),
            'uploaded_by': user_id if not is_admin else 'admin',
            'uploaded_at': datetime.now().isoformat(),
            'is_active': True
        }
        
        exams_data['exams'].append(exam)
        save_class_exams(exams_data)
        
        return jsonify({
            'success': True,
            'message': f'Exam uploaded successfully with {len(questions)} questions',
            'exam': exam
        })
        
    except Exception as e:
        print(f"Error uploading exam: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/exam', methods=['GET'])
@authenticated_required
def get_class_exam(class_id):
    """Get exam for a class (students see questions only, instructors see full exam)"""
    try:
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # Verify class exists
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Load exam
        exams_data = load_class_exams()
        exam = next((e for e in exams_data.get('exams', []) 
                    if e['class_id'] == class_id and e.get('is_active', True)), None)
        
        if not exam:
            return jsonify({'error': 'No exam found for this class'}), 404
        
        # Check if user is instructor or admin
        is_instructor = False
        if not is_admin and user_id:
            instructors_data = load_instructors()
            instructor = next((i for i in instructors_data.get('instructors', []) 
                             if i['user_id'] == user_id), None)
            is_instructor = instructor and instructor['instructor_id'] in cls.get('instructor_ids', [])
        
        # For students, hide correct answers
        if not is_admin and not is_instructor:
            # Check if student is enrolled
            enrollments_data = load_enrollments()
            is_enrolled = any(e for e in enrollments_data.get('enrollments', []) 
                            if e['class_id'] == class_id and e.get('student_user_id') == user_id)
            
            if not is_enrolled:
                return jsonify({'error': 'You must be enrolled in this class to take the exam'}), 403
            
            # Remove correct answers for students
            student_questions = []
            for q in exam['questions']:
                student_questions.append({
                    'question_number': q['question_number'],
                    'question_text': q['question_text'],
                    'options': q['options'],
                    'points': q['points']
                })
            
            return jsonify({
                'success': True,
                'exam': {
                    'exam_id': exam['exam_id'],
                    'class_id': exam['class_id'],
                    'questions': student_questions,
                    'total_points': exam['total_points']
                }
            })
        
        # Instructors and admins see everything
        return jsonify({
            'success': True,
            'exam': exam
        })
        
    except Exception as e:
        print(f"Error getting class exam: {e}")
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/exam/submit', methods=['POST'])
@authenticated_required
def submit_class_exam(class_id):
    """Submit exam answers"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User authentication required'}), 401
        
        # CRITICAL: Verify student is enrolled in the class
        enrollments_data = load_enrollments()
        is_enrolled = any(e for e in enrollments_data.get('enrollments', []) 
                        if e['class_id'] == class_id and e.get('student_user_id') == user_id 
                        and e.get('status') == 'approved')
        
        if not is_enrolled:
            return jsonify({'error': 'You must be enrolled in this class to submit an exam'}), 403
        
        data = request.json or {}
        answers = data.get('answers', {})
        
        if not answers:
            return jsonify({'error': 'No answers provided'}), 400
        
        # Load exam
        exams_data = load_class_exams()
        exam = next((e for e in exams_data.get('exams', []) 
                    if e['class_id'] == class_id and e.get('is_active', True)), None)
        
        if not exam:
            return jsonify({'error': 'No active exam found for this class'}), 404
        
        # SECURITY: Validate that all answers correspond to actual questions
        valid_question_numbers = {q['question_number'] for q in exam['questions']}
        for q_num in answers.keys():
            if q_num not in valid_question_numbers:
                return jsonify({'error': f'Invalid question number: {q_num}'}), 400
        
        # Calculate score
        total_points = 0
        earned_points = 0
        results = []
        
        for question in exam['questions']:
            q_num = question['question_number']
            correct_answer = question['correct_answer']
            points = question['points']
            user_answer = answers.get(q_num, '').strip().upper()
            
            is_correct = user_answer == correct_answer
            points_earned = points if is_correct else 0
            
            total_points += points
            earned_points += points_earned
            
            results.append({
                'question_number': q_num,
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'points': points,
                'points_earned': points_earned
            })
        
        score_percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        
        # Save submission
        submissions_data = load_class_exam_submissions()
        
        submission = {
            'submission_id': f"sub_{class_id}_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'exam_id': exam['exam_id'],
            'class_id': class_id,
            'user_id': user_id,
            'answers': answers,
            'results': results,
            'total_points': total_points,
            'earned_points': earned_points,
            'score_percentage': round(score_percentage, 2),
            'submitted_at': datetime.now().isoformat()
        }
        
        submissions_data['submissions'].append(submission)
        save_class_exam_submissions(submissions_data)
        
        return jsonify({
            'success': True,
            'submission': submission,
            'message': f'Exam submitted successfully! Score: {score_percentage:.1f}%'
        })
        
    except Exception as e:
        print(f"Error submitting exam: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/exam/statistics', methods=['GET'])
@instructor_or_admin_required
def get_exam_statistics(class_id):
    """Get comprehensive statistics for exam results"""
    try:
        # CRITICAL: Verify instructor has access to this class
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check instructor ownership
        if not is_admin:
            instructors_data = load_instructors()
            instructor = next((i for i in instructors_data.get('instructors', []) 
                             if i['user_id'] == user_id), None)
            if not instructor or instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Only instructors assigned to this class can view statistics'}), 403
        
        # Load data
        submissions_data = load_class_exam_submissions()
        exams_data = load_class_exams()
        users_data = load_users()
        
        # Get exam for this class
        exam = next((e for e in exams_data.get('exams', []) 
                    if e['class_id'] == class_id), None)
        
        if not exam:
            return jsonify({'error': 'No exam found for this class'}), 404
        
        # Get all submissions for this class
        class_submissions = [s for s in submissions_data.get('submissions', []) 
                            if s['class_id'] == class_id]
        
        if not class_submissions:
            return jsonify({
                'success': True,
                'statistics': {
                    'total_submissions': 0,
                    'average_score': 0,
                    'pass_rate': 0,
                    'score_distribution': [],
                    'question_difficulty': [],
                    'student_results': []
                }
            })
        
        # Calculate statistics
        scores = [s['percentage'] for s in class_submissions]
        passing_threshold = 50  # 50% to pass
        passed = sum(1 for s in scores if s >= passing_threshold)
        
        # Score distribution (bins: 0-20, 20-40, 40-60, 60-80, 80-100)
        score_bins = {'0-20': 0, '20-40': 0, '40-60': 0, '60-80': 0, '80-100': 0}
        for score in scores:
            if score < 20:
                score_bins['0-20'] += 1
            elif score < 40:
                score_bins['20-40'] += 1
            elif score < 60:
                score_bins['40-60'] += 1
            elif score < 80:
                score_bins['60-80'] += 1
            else:
                score_bins['80-100'] += 1
        
        # Question difficulty (percentage of students who got each question wrong)
        question_stats = {}
        for idx, question in enumerate(exam['questions']):
            # Support both old format (question_number) and new format (id)
            q_id = str(question.get('id', question.get('question_number', idx + 1)))
            q_num = idx + 1
            total_attempts = 0
            correct_attempts = 0
            
            for submission in class_submissions:
                # Check if student answered this question
                if q_id in submission.get('answers', {}):
                    total_attempts += 1
                    student_answer = submission['answers'][q_id]
                    # Support both old format (correct_answer) and new format (correct)
                    correct_answer = question.get('correct', question.get('correct_answer', ''))
                    if student_answer == correct_answer:
                        correct_attempts += 1
            
            difficulty = ((total_attempts - correct_attempts) / total_attempts * 100) if total_attempts > 0 else 0
            # Support both old format (question_text) and new format (question)
            q_text = question.get('question', question.get('question_text', f'Question {q_num}'))
            question_stats[q_id] = {
                'question_number': q_num,
                'question_text': q_text,
                'difficulty_percentage': round(difficulty, 1),
                'correct_rate': round((correct_attempts / total_attempts * 100) if total_attempts > 0 else 0, 1)
            }
        
        # Student results with names
        student_results = []
        for submission in class_submissions:
            user = next((u for u in users_data.get('users', []) 
                        if u['user_id'] == submission['student_user_id']), None)
            student_results.append({
                'user_id': submission['student_user_id'],
                'student_name': user['full_name'] if user else 'Unknown',
                'percentage': submission['percentage'],
                'score': submission['score'],
                'total_points': submission['total_points'],
                'submitted_at': submission['submitted_at']
            })
        
        # Sort by score (highest first)
        student_results.sort(key=lambda x: x['percentage'], reverse=True)
        
        statistics = {
            'total_submissions': len(class_submissions),
            'average_score': round(sum(scores) / len(scores), 2),
            'highest_score': max(scores),
            'lowest_score': min(scores),
            'pass_rate': round((passed / len(class_submissions) * 100), 2),
            'score_distribution': [
                {'range': '0-20%', 'count': score_bins['0-20']},
                {'range': '20-40%', 'count': score_bins['20-40']},
                {'range': '40-60%', 'count': score_bins['40-60']},
                {'range': '60-80%', 'count': score_bins['60-80']},
                {'range': '80-100%', 'count': score_bins['80-100']}
            ],
            'question_difficulty': list(question_stats.values()),
            'student_results': student_results
        }
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
        
    except Exception as e:
        print(f"Error getting exam statistics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/survey/statistics', methods=['GET'])
@instructor_or_admin_required
def get_survey_statistics(class_id):
    """Get comprehensive statistics for entry survey results for a specific class"""
    try:
        # CRITICAL: Verify instructor has access to this class
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check instructor ownership
        if not is_admin:
            instructors_data = load_instructors()
            instructor = next((i for i in instructors_data.get('instructors', []) 
                             if i['user_id'] == user_id), None)
            if not instructor or instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Only instructors assigned to this class can view statistics'}), 403
        
        # Load data
        enrollments_data = load_enrollments()
        users_data = load_users()
        
        # Get students enrolled in this class
        class_enrollments = [e for e in enrollments_data.get('enrollments', []) 
                            if e['class_id'] == class_id]
        student_ids = [e.get('student_user_id') or e.get('user_id') for e in class_enrollments]
        
        if not student_ids:
            return jsonify({
                'success': True,
                'statistics': {
                    'total_responses': 0,
                    'response_rate': 0,
                    'question_responses': []
                }
            })
        
        # Load survey data (from global survey system)
        survey_data_file = 'users_survey_data.json'
        if not os.path.exists(survey_data_file):
            return jsonify({
                'success': True,
                'statistics': {
                    'total_responses': 0,
                    'response_rate': 0,
                    'question_responses': []
                }
            })
        
        with open(survey_data_file, 'r', encoding='utf-8') as f:
            survey_data = json.load(f)
        
        # Filter responses for students in this class
        class_survey_responses = [u for u in survey_data.get('users', []) 
                                 if u.get('user_id') in student_ids]
        
        if not class_survey_responses:
            return jsonify({
                'success': True,
                'statistics': {
                    'total_responses': 0,
                    'response_rate': round((0 / len(student_ids) * 100), 2) if student_ids else 0,
                    'question_responses': []
                }
            })
        
        # Aggregate responses by question
        question_stats = {}
        
        for response in class_survey_responses:
            answers = response.get('answers', {})
            for q_id, answer in answers.items():
                if q_id not in question_stats:
                    question_stats[q_id] = {
                        'question_id': q_id,
                        'responses': [],
                        'response_distribution': {}
                    }
                
                question_stats[q_id]['responses'].append(answer)
                
                # Count response distribution
                if answer in question_stats[q_id]['response_distribution']:
                    question_stats[q_id]['response_distribution'][answer] += 1
                else:
                    question_stats[q_id]['response_distribution'][answer] = 1
        
        # Format for frontend charts
        question_responses = []
        for q_id, stats in question_stats.items():
            question_responses.append({
                'question_id': q_id,
                'total_responses': len(stats['responses']),
                'distribution': [
                    {'answer': answer, 'count': count}
                    for answer, count in stats['response_distribution'].items()
                ]
            })
        
        statistics = {
            'total_responses': len(class_survey_responses),
            'total_students': len(student_ids),
            'response_rate': round((len(class_survey_responses) / len(student_ids) * 100), 2),
            'question_responses': question_responses
        }
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
        
    except Exception as e:
        print(f"Error getting survey statistics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/exit-exam/statistics', methods=['GET'])
@instructor_or_admin_required
def get_exit_exam_statistics(class_id):
    """Get Exit Exam statistics for students enrolled in a specific class"""
    try:
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        if not is_admin:
            instructors_data = load_instructors()
            instructor = next((i for i in instructors_data.get('instructors', []) 
                             if i['user_id'] == user_id), None)
            if not instructor or instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Only instructors assigned to this class can view statistics'}), 403
        
        enrollments_data = load_enrollments()
        users_data = load_users()
        
        class_enrollments = [e for e in enrollments_data.get('enrollments', []) 
                            if e['class_id'] == class_id]
        student_ids = [e.get('student_user_id') or e.get('user_id') for e in class_enrollments]
        
        if not student_ids:
            return jsonify({
                'success': True,
                'statistics': {
                    'total_submissions': 0,
                    'total_students': 0,
                    'completion_rate': 0,
                    'average_score': 0,
                    'pass_rate': 0,
                    'student_results': []
                }
            })
        
        exit_exam_file = 'users_exit_exam_data.json'
        if not os.path.exists(exit_exam_file):
            return jsonify({
                'success': True,
                'statistics': {
                    'total_submissions': 0,
                    'total_students': len(student_ids),
                    'completion_rate': 0,
                    'average_score': 0,
                    'pass_rate': 0,
                    'student_results': []
                }
            })
        
        with open(exit_exam_file, 'r', encoding='utf-8') as f:
            exit_exam_data = json.load(f)
        
        class_exit_exams = [u for u in exit_exam_data.get('users', []) 
                           if u.get('user_id') in student_ids]
        
        if not class_exit_exams:
            return jsonify({
                'success': True,
                'statistics': {
                    'total_submissions': 0,
                    'total_students': len(student_ids),
                    'completion_rate': 0,
                    'average_score': 0,
                    'pass_rate': 0,
                    'student_results': []
                }
            })
        
        scores = [u.get('score', 0) for u in class_exit_exams]
        passing_threshold = 6
        passed = sum(1 for s in scores if s >= passing_threshold)
        
        score_bins = {'0-2': 0, '3-4': 0, '5-6': 0, '7-8': 0, '9-10': 0}
        for score in scores:
            if score <= 2:
                score_bins['0-2'] += 1
            elif score <= 4:
                score_bins['3-4'] += 1
            elif score <= 6:
                score_bins['5-6'] += 1
            elif score <= 8:
                score_bins['7-8'] += 1
            else:
                score_bins['9-10'] += 1
        
        student_results = []
        for exam in class_exit_exams:
            user = next((u for u in users_data.get('users', []) 
                        if u['user_id'] == exam.get('user_id')), None)
            student_results.append({
                'user_id': exam.get('user_id'),
                'student_name': user['full_name'] if user else exam.get('name', 'Unknown'),
                'score': exam.get('score', 0),
                'total_questions': 10,
                'percentage': exam.get('score', 0) * 10,
                'passed': exam.get('score', 0) >= passing_threshold,
                'has_certificate': exam.get('certificate_generated', False),
                'submitted_at': exam.get('completed_at', exam.get('timestamp', ''))
            })
        
        student_results.sort(key=lambda x: x['score'], reverse=True)
        
        statistics = {
            'total_submissions': len(class_exit_exams),
            'total_students': len(student_ids),
            'completion_rate': round((len(class_exit_exams) / len(student_ids) * 100), 2),
            'average_score': round(sum(scores) / len(scores), 2) if scores else 0,
            'highest_score': max(scores) if scores else 0,
            'lowest_score': min(scores) if scores else 0,
            'pass_rate': round((passed / len(class_exit_exams) * 100), 2) if class_exit_exams else 0,
            'score_distribution': [
                {'range': '0-2', 'count': score_bins['0-2']},
                {'range': '3-4', 'count': score_bins['3-4']},
                {'range': '5-6', 'count': score_bins['5-6']},
                {'range': '7-8', 'count': score_bins['7-8']},
                {'range': '9-10', 'count': score_bins['9-10']}
            ],
            'student_results': student_results
        }
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
        
    except Exception as e:
        print(f"Error getting exit exam statistics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@classes_bp.route('/<class_id>/exit-survey/statistics', methods=['GET'])
@instructor_or_admin_required
def get_exit_survey_statistics(class_id):
    """Get Training Feedback (Exit Survey) statistics for students enrolled in a specific class"""
    try:
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        classes_data = load_classes()
        cls = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        if not cls:
            return jsonify({'error': 'Class not found'}), 404
        
        if not is_admin:
            instructors_data = load_instructors()
            instructor = next((i for i in instructors_data.get('instructors', []) 
                             if i['user_id'] == user_id), None)
            if not instructor or instructor['instructor_id'] not in cls.get('instructor_ids', []):
                return jsonify({'error': 'Only instructors assigned to this class can view statistics'}), 403
        
        enrollments_data = load_enrollments()
        users_data = load_users()
        
        class_enrollments = [e for e in enrollments_data.get('enrollments', []) 
                            if e['class_id'] == class_id]
        student_ids = [e.get('student_user_id') or e.get('user_id') for e in class_enrollments]
        
        if not student_ids:
            return jsonify({
                'success': True,
                'statistics': {
                    'total_responses': 0,
                    'total_students': 0,
                    'response_rate': 0,
                    'average_rating': 0,
                    'question_responses': []
                }
            })
        
        exit_survey_file = 'exit_survey_responses.json'
        if not os.path.exists(exit_survey_file):
            return jsonify({
                'success': True,
                'statistics': {
                    'total_responses': 0,
                    'total_students': len(student_ids),
                    'response_rate': 0,
                    'average_rating': 0,
                    'question_responses': []
                }
            })
        
        with open(exit_survey_file, 'r', encoding='utf-8') as f:
            exit_survey_data = json.load(f)
        
        class_responses = [r for r in exit_survey_data.get('responses', []) 
                          if r.get('user_id') in student_ids]
        
        if not class_responses:
            return jsonify({
                'success': True,
                'statistics': {
                    'total_responses': 0,
                    'total_students': len(student_ids),
                    'response_rate': 0,
                    'average_rating': 0,
                    'question_responses': []
                }
            })
        
        question_stats = {}
        all_ratings = []
        
        for response in class_responses:
            answers = response.get('answers', {})
            for q_id, answer in answers.items():
                if q_id not in question_stats:
                    question_stats[q_id] = {
                        'question_id': q_id,
                        'responses': [],
                        'response_distribution': {}
                    }
                
                question_stats[q_id]['responses'].append(answer)
                
                if answer in question_stats[q_id]['response_distribution']:
                    question_stats[q_id]['response_distribution'][answer] += 1
                else:
                    question_stats[q_id]['response_distribution'][answer] = 1
                
                if isinstance(answer, (int, float)):
                    all_ratings.append(answer)
                elif isinstance(answer, str) and answer.isdigit():
                    all_ratings.append(int(answer))
        
        question_responses = []
        for q_id, stats in question_stats.items():
            question_responses.append({
                'question_id': q_id,
                'total_responses': len(stats['responses']),
                'distribution': [
                    {'answer': str(answer), 'count': count}
                    for answer, count in stats['response_distribution'].items()
                ]
            })
        
        statistics = {
            'total_responses': len(class_responses),
            'total_students': len(student_ids),
            'response_rate': round((len(class_responses) / len(student_ids) * 100), 2),
            'average_rating': round(sum(all_ratings) / len(all_ratings), 2) if all_ratings else 0,
            'question_responses': question_responses
        }
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
        
    except Exception as e:
        print(f"Error getting exit survey statistics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
