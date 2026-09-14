"""
SkillPilot - Centralized Authentication Decorators
Single-institution architecture with simplified role system
"""

from functools import wraps
from flask import session, jsonify


def superadmin_required(f):
    """
    Decorator for routes that require superadmin access only.
    Superadmin has full platform control including site branding/settings.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401

        role = session.get('role', '').lower().replace(' ', '_')
        if role not in ['superadmin', 'super_admin']:
            return jsonify({'error': 'Superadmin access required'}), 403

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator for routes that require admin or superadmin access.
    Admin has elevated permissions (users, courses, certificates, exams)
    but cannot change site branding/settings.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401

        role = session.get('role', '').lower().replace(' ', '_')
        allowed_roles = ['superadmin', 'super_admin', 'admin', 'institution_admin']

        if role not in allowed_roles:
            return jsonify({'error': 'Admin access required'}), 403

        return f(*args, **kwargs)
    return decorated_function


def teacher_required(f):
    """
    Decorator for routes that require teacher, admin, or superadmin access.
    Teachers can manage their courses, view student progress, and grade.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401

        role = session.get('role', '').lower().replace(' ', '_')
        allowed_roles = [
            'superadmin', 'super_admin',
            'admin', 'institution_admin',
            'teacher', 'instructor'
        ]

        if role not in allowed_roles:
            return jsonify({'error': 'Teacher access required'}), 403

        return f(*args, **kwargs)
    return decorated_function


def login_required(f):
    """
    Decorator for routes that require any authenticated user.
    All roles (superadmin, admin, teacher, student) can access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401

        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """
    Decorator for student-only routes.
    Superadmin can also access for testing/support purposes.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401

        role = session.get('role', '').lower().replace(' ', '_')
        allowed_roles = ['student', 'superadmin', 'super_admin']

        if role not in allowed_roles:
            return jsonify({'error': 'Student access required'}), 403

        return f(*args, **kwargs)
    return decorated_function


def teacher_or_admin_required(f):
    """
    Decorator for routes accessible by teachers and admins.
    Alias for teacher_required with clearer naming.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401

        role = session.get('role', '').lower().replace(' ', '_')
        allowed_roles = [
            'superadmin', 'super_admin',
            'admin', 'institution_admin',
            'teacher', 'instructor'
        ]

        if role not in allowed_roles:
            return jsonify({'error': 'Teacher or admin access required'}), 403

        return f(*args, **kwargs)
    return decorated_function


# Helper functions for role checking
def is_superadmin():
    """Check if current user is superadmin"""
    role = session.get('role', '').lower().replace(' ', '_')
    return role in ['superadmin', 'super_admin']


def is_admin():
    """Check if current user is admin or superadmin"""
    role = session.get('role', '').lower().replace(' ', '_')
    return role in ['superadmin', 'super_admin', 'admin', 'institution_admin']


def is_teacher():
    """Check if current user is teacher, admin, or superadmin"""
    role = session.get('role', '').lower().replace(' ', '_')
    return role in ['superadmin', 'super_admin', 'admin', 'institution_admin', 'teacher', 'instructor']


def get_current_role():
    """Get the current user's normalized role"""
    return session.get('role', '').lower().replace(' ', '_')


def get_current_user_id():
    """Get the current user's ID"""
    return session.get('user_id')
