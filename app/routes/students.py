"""
AIACMate Pro - Student Management Routes
Handles student information viewing, editing, and password reset
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import json
import os
import hashlib
import secrets
from datetime import datetime

students_bp = Blueprint('students', __name__, url_prefix='/api/students')

USERS_FILE = 'users.json'
ENROLLMENTS_FILE = 'enrollments.json'
CLASSES_FILE = 'classes.json'
INSTRUCTORS_FILE = 'instructors.json'


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 401
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
            users = load_users()
            user = next((u for u in users.get('users', []) if u['user_id'] == user_id), None)
            if not user or user.get('role') != 'Instructor':
                return jsonify({'error': 'Instructor or admin access required'}), 403
        
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


def save_users(data):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_enrollments():
    """Load enrollments from JSON file"""
    if os.path.exists(ENROLLMENTS_FILE):
        with open(ENROLLMENTS_FILE, 'r') as f:
            return json.load(f)
    return {'enrollments': []}


def load_classes():
    """Load classes from JSON file"""
    if os.path.exists(CLASSES_FILE):
        with open(CLASSES_FILE, 'r') as f:
            return json.load(f)
    return {'classes': []}


def load_instructors():
    """Load instructors from JSON file"""
    if os.path.exists(INSTRUCTORS_FILE):
        with open(INSTRUCTORS_FILE, 'r') as f:
            return json.load(f)
    return {'instructors': []}


def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_password():
    """Generate a random 8-character password"""
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(secrets.choice(chars) for _ in range(8))


def get_instructor_student_ids(instructor_user_id):
    """Get all student IDs enrolled in classes taught by this instructor"""
    enrollments_data = load_enrollments()
    classes_data = load_classes()
    instructors_data = load_instructors()
    
    # Find instructor record by user_id to get instructor_id
    instructor_record = next((i for i in instructors_data.get('instructors', []) 
                             if i['user_id'] == instructor_user_id), None)
    
    if not instructor_record:
        return []
    
    instructor_id = instructor_record['instructor_id']
    
    # Get all classes taught by this instructor (where instructor_id is in instructor_ids)
    instructor_class_ids = []
    for class_obj in classes_data.get('classes', []):
        # Check if this instructor's ID is in the class's instructor_ids list
        if instructor_id in class_obj.get('instructor_ids', []):
            instructor_class_ids.append(class_obj['class_id'])
    
    # Get all student user_ids enrolled in these classes
    student_ids = set()
    for enrollment in enrollments_data.get('enrollments', []):
        if enrollment['class_id'] in instructor_class_ids:
            # Handle both 'student_user_id' and 'user_id' field names for compatibility
            student_id = enrollment.get('student_user_id') or enrollment.get('user_id')
            if student_id:
                student_ids.add(student_id)
    
    return list(student_ids)


# ============================================
# Student Management Routes
# ============================================

@students_bp.route('/', methods=['GET'])
@instructor_or_admin_required
def get_students():
    """
    Get list of students based on role:
    - Admin: See all students
    - Instructor: See only students enrolled in their classes
    """
    users_data = load_users()
    is_admin = session.get('is_admin', False)
    user_id = session.get('user_id')
    
    # Filter for students only
    all_students = [u for u in users_data.get('users', []) if u.get('role') == 'Student']
    
    if is_admin:
        # Admin sees all students
        students = all_students
    else:
        # Instructor sees only their students
        instructor_student_ids = get_instructor_student_ids(user_id)
        students = [s for s in all_students if s['user_id'] in instructor_student_ids]
    
    # Return students with safe information (without password hash)
    safe_students = []
    for student in students:
        safe_students.append({
            'user_id': student['user_id'],
            'username': student['username'],
            'full_name': student['full_name'],
            'email': student['email'],
            'phone': student.get('phone', ''),
            'organization': student.get('organization', ''),
            'role': student['role'],
            'registered_at': student.get('registered_at', ''),
            'last_login': student.get('last_login', '')
        })
    
    return jsonify({
        'success': True,
        'students': safe_students,
        'count': len(safe_students)
    })


@students_bp.route('/<user_id>', methods=['PUT'])
@instructor_or_admin_required
def update_student(user_id):
    """Update student information"""
    data = request.json or {}
    is_admin = session.get('is_admin', False)
    current_user_id = session.get('user_id')
    
    users_data = load_users()
    users = users_data.get('users', [])
    
    # Find the student
    student = next((u for u in users if u['user_id'] == user_id and u['role'] == 'Student'), None)
    
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    # If instructor, verify they can access this student
    if not is_admin:
        instructor_students = get_instructor_student_ids(current_user_id)
        if user_id not in instructor_students:
            return jsonify({'error': 'Access denied - not your student'}), 403
    
    # Update allowed fields
    if 'username' in data:
        # Check username uniqueness
        existing = next((u for u in users if u['username'] == data['username'] and u['user_id'] != user_id), None)
        if existing:
            return jsonify({'error': 'Username already exists'}), 400
        student['username'] = data['username'].strip()
    
    if 'email' in data:
        student['email'] = data['email'].strip()
    
    if 'phone' in data:
        student['phone'] = data['phone'].strip()
    
    if 'full_name' in data:
        student['full_name'] = data['full_name'].strip()
    
    if 'organization' in data:
        student['organization'] = data['organization'].strip()
    
    # Save updated data
    save_users(users_data)
    
    return jsonify({
        'success': True,
        'message': 'Student information updated successfully',
        'student': {
            'user_id': student['user_id'],
            'username': student['username'],
            'full_name': student['full_name'],
            'email': student['email'],
            'phone': student.get('phone', ''),
            'organization': student.get('organization', ''),
            'role': student['role']
        }
    })


@students_bp.route('/<user_id>/reset-password', methods=['POST'])
@instructor_or_admin_required
def reset_password(user_id):
    """Reset student password and return new password"""
    is_admin = session.get('is_admin', False)
    current_user_id = session.get('user_id')
    
    users_data = load_users()
    users = users_data.get('users', [])
    
    # Find the student
    student = next((u for u in users if u['user_id'] == user_id and u['role'] == 'Student'), None)
    
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    # If instructor, verify they can access this student
    if not is_admin:
        instructor_students = get_instructor_student_ids(current_user_id)
        if user_id not in instructor_students:
            return jsonify({'error': 'Access denied - not your student'}), 403
    
    # Generate new password
    new_password = generate_password()
    student['password'] = hash_password(new_password)
    
    # Save updated data
    save_users(users_data)
    
    return jsonify({
        'success': True,
        'message': 'Password reset successfully',
        'new_password': new_password,
        'username': student['username']
    })


# ============================================
# Student Details Routes (Enrollments & Certificates)
# ============================================

EXIT_EXAM_FILE = 'users_exit_exam_data.json'
ETHICS_ASSESSMENTS_FILE = 'ethics_assessments.json'


def load_exit_exam_data():
    """Load exit exam data"""
    if os.path.exists(EXIT_EXAM_FILE):
        with open(EXIT_EXAM_FILE, 'r') as f:
            return json.load(f)
    return {'users': []}


def load_ethics_assessments():
    """Load ethics assessments data"""
    if os.path.exists(ETHICS_ASSESSMENTS_FILE):
        with open(ETHICS_ASSESSMENTS_FILE, 'r') as f:
            return json.load(f)
    return {'assessments': []}


@students_bp.route('/<user_id>/enrollments', methods=['GET'])
@instructor_or_admin_required
def get_student_enrollments(user_id):
    """Get all course enrollments for a student"""
    enrollments_data = load_enrollments()
    classes_data = load_classes()
    
    # Get enrollments for this student
    student_enrollments = [e for e in enrollments_data.get('enrollments', []) 
                          if e.get('student_user_id') == user_id or e.get('user_id') == user_id]
    
    # Enrich with class info
    enriched_enrollments = []
    for enrollment in student_enrollments:
        class_id = enrollment.get('class_id')
        class_info = next((c for c in classes_data.get('classes', []) if c['class_id'] == class_id), None)
        
        enriched_enrollments.append({
            'enrollment_id': enrollment.get('enrollment_id'),
            'class_id': class_id,
            'class_title': class_info.get('title', 'Unknown Class') if class_info else 'Unknown Class',
            'class_code': class_info.get('class_code', '') if class_info else '',
            'status': enrollment.get('status', 'unknown'),
            'requested_at': enrollment.get('requested_at'),
            'approved_at': enrollment.get('approved_at'),
            'course_type': class_info.get('course_type', '') if class_info else ''
        })
    
    return jsonify({
        'success': True,
        'enrollments': enriched_enrollments,
        'count': len(enriched_enrollments)
    })


@students_bp.route('/<user_id>/certificates', methods=['GET'])
@instructor_or_admin_required
def get_student_certificates(user_id):
    """Get all certificates for a student"""
    certificates = []
    
    # Get prompt engineering certificates from exit exam
    exit_exam_data = load_exit_exam_data()
    for exam in exit_exam_data.get('users', []):
        if exam.get('user_info', {}).get('user_id') == user_id:
            if exam.get('certificate_status') == 'pass' or exam.get('pass_status') == 'passed':
                certificates.append({
                    'id': exam.get('id'),
                    'type': 'prompt_engineering',
                    'title': 'Prompt Engineering Certificate',
                    'certificate_number': exam.get('certificate_number'),
                    'score': exam.get('percentage'),
                    'issued_at': exam.get('timestamp'),
                    'status': 'issued'
                })
    
    # Get ethics certificates
    ethics_data = load_ethics_assessments()
    for assessment in ethics_data.get('assessments', []):
        if assessment.get('user_id') == user_id and assessment.get('passed'):
            certificates.append({
                'id': assessment.get('assessment_id'),
                'type': 'ethics',
                'title': f"Ethics Certificate - {assessment.get('category', 'General')}",
                'certificate_number': assessment.get('certificate_number'),
                'score': assessment.get('score_percentage'),
                'issued_at': assessment.get('completed_at'),
                'status': 'issued'
            })
    
    return jsonify({
        'success': True,
        'certificates': certificates,
        'count': len(certificates)
    })


@students_bp.route('/<user_id>/certificates/<cert_id>/regenerate', methods=['POST'])
@instructor_or_admin_required
def regenerate_certificate(user_id, cert_id):
    """Regenerate a certificate with updated student info"""
    # Load user data to get current name
    users_data = load_users()
    student = next((u for u in users_data.get('users', []) if u['user_id'] == user_id), None)
    
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    # Update certificate in exit exam data
    exit_exam_data = load_exit_exam_data()
    updated = False
    
    for exam in exit_exam_data.get('users', []):
        if exam.get('id') == cert_id and exam.get('user_info', {}).get('user_id') == user_id:
            exam['user_info']['name'] = student['full_name']
            exam['user_info']['email'] = student['email']
            exam['regenerated_at'] = datetime.now().isoformat()
            updated = True
            break
    
    if updated:
        with open(EXIT_EXAM_FILE, 'w') as f:
            json.dump(exit_exam_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Certificate regenerated with updated information'
        })
    
    return jsonify({'error': 'Certificate not found'}), 404
