from flask import Blueprint, request, jsonify, session, current_app, redirect
from functools import wraps
import json
import os
import hashlib
import secrets
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

USERS_FILE = 'users.json'
ATTENDANCE_FILE = 'attendance.json'


def is_app_frozen():
    """Check if the application is in frozen/maintenance mode"""
    try:
        from app.models import SiteSettings
        settings = SiteSettings.query.first()
        return settings.app_frozen if settings else False
    except Exception as e:
        print(f"Error checking app freeze status: {e}")
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


def admin_required(f):
    """Decorator to require admin authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['POST'])
def login():
    """Admin login endpoint - SUPER ADMIN PASSWORD ACCESS"""
    data = request.json or {}
    password = data.get('password')

    if not password:
        return jsonify({'error': 'Password is required'}), 400

    # Check password against configuration
    if password == current_app.config['ADMIN_PASSWORD']:
        # This is the super admin password
        session['is_admin'] = True
        session['role'] = 'superadmin'
        session['logged_in'] = True
        session.permanent = True
        return jsonify({
            'success': True,
            'message': 'Admin login successful',
            'is_admin': True
        })
    else:
        return jsonify({'error': 'Invalid password'}), 401


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Admin logout endpoint - clears ALL session privileges"""
    # Clear ALL session keys for security
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })


@auth_bp.route('/check', methods=['GET'])
def check_auth():
    """Check if user is authenticated as admin or regular user"""
    user_id = session.get('user_id')
    role = (session.get('role') or '').lower()
    has_approved_enrollment = False
    if user_id and role == 'student':
        try:
            from app.models import Enrollment, db
            has_approved_enrollment = db.session.query(
                Enrollment.query.filter(
                    Enrollment.user_id == user_id,
                    Enrollment.status.in_(['approved', 'active', 'completed'])
                ).exists()
            ).scalar()
        except Exception:
            has_approved_enrollment = False
    return jsonify({
        'is_admin': session.get('is_admin', False),
        'is_logged_in': session.get('logged_in', False) or user_id is not None,
        'user_id': user_id,
        'username': session.get('username'),
        'full_name': session.get('full_name'),
        'role': session.get('role', ''),
        'has_approved_enrollment': has_approved_enrollment,
    })


# ============================================
# User Registration and Authentication
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


def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_username(full_name, email):
    """Generate a unique username from full name and email"""
    # Take first part of email and first letter of last name
    email_part = email.split('@')[0].lower()
    name_parts = full_name.split()
    
    if len(name_parts) > 1:
        username = f"{name_parts[0].lower()}.{name_parts[-1][0].lower()}"
    else:
        username = name_parts[0].lower()
    
    # Add random suffix to ensure uniqueness
    username = f"{username}_{secrets.token_hex(2)}"
    return username


def generate_password():
    """Generate a random 8-character password"""
    # Generate password with letters and numbers
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(secrets.choice(chars) for _ in range(8))


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user with custom username and password"""
    if is_app_frozen():
        lang = request.headers.get('Accept-Language', 'en')[:2]
        return jsonify({'error': get_freeze_message(lang), 'app_frozen': True}), 503
    
    data = request.json or {}
    
    # Required fields
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    organization = data.get('organization', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    security_q1 = data.get('security_q1', '').strip()
    security_q2 = data.get('security_q2', '').strip()
    security_q3 = data.get('security_q3', '').strip()
    
    # Validation
    if not all([full_name, email, username, password]):
        return jsonify({'error': 'Full name, email, username, and password are required'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400
    
    if not all([security_q1, security_q2, security_q3]):
        return jsonify({'error': 'All three security questions are required'}), 400
    
    # Load existing users
    users_data = load_users()
    
    # Check if email already exists
    if any(u['email'] == email for u in users_data['users']):
        return jsonify({'error': 'Email already registered'}), 400
    
    # Check if username already exists in JSON
    if any(u['username'] == username for u in users_data['users']):
        return jsonify({'error': 'Username already taken'}), 400
    
    # Also check PostgreSQL database for existing username/email
    try:
        from app.models import db, User
        db_user_check = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if db_user_check:
            if db_user_check.username == username:
                return jsonify({'error': 'Username already taken'}), 400
            if db_user_check.email == email:
                return jsonify({'error': 'Email already registered'}), 400
    except Exception as e:
        print(f"Database check failed: {e}")
    
    # Generate a UUID for the user_id (use proper integer ID for database)
    json_user_id = secrets.token_hex(16)
    
    # Create user in PostgreSQL database FIRST (for enrollments to work)
    db_user_id = None
    try:
        from app.models import db, User
        
        new_db_user = User(
            username=username,
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role='student',
            phone=phone
        )
        db.session.add(new_db_user)
        db.session.commit()
        db_user_id = new_db_user.id
        print(f"Created database user with ID: {db_user_id}")
    except Exception as e:
        print(f"Failed to create database user: {e}")
        import traceback
        traceback.print_exc()
        # Continue with JSON-only registration as fallback
    
    # Create new user in JSON file - ALWAYS as Student role
    user = {
        'user_id': json_user_id,
        'db_user_id': db_user_id,  # Store database ID for reference
        'username': username,
        'password': hash_password(password),  # Hash the password
        'full_name': full_name,
        'email': email,
        'phone': phone,
        'organization': organization,
        'role': 'Student',
        'security_q1': hash_password(security_q1.lower()),  # Hash and lowercase for case-insensitive comparison
        'security_q2': hash_password(security_q2.lower()),
        'security_q3': hash_password(security_q3.lower()),
        'registered_at': datetime.now().isoformat(),
        'last_login': None
    }
    
    users_data['users'].append(user)
    save_users(users_data)
    
    # Return the database user ID if available (for enrollments)
    return jsonify({
        'success': True,
        'message': 'Registration successful',
        'username': username,
        'user_id': db_user_id if db_user_id else json_user_id,
        'full_name': full_name
    })


@auth_bp.route('/user/login', methods=['POST'])
def user_login():
    """User login endpoint"""
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not all([username, password]):
        return jsonify({'error': 'Username and password are required'}), 400
    
    # Check if app is frozen - allow superadmin/admin login
    if is_app_frozen():
        try:
            from app.models import User
            check_user = User.query.filter_by(username=username).first()
            if check_user and check_user.role and check_user.role.lower() in ['superadmin', 'super_admin', 'admin']:
                pass
            else:
                lang = request.headers.get('Accept-Language', 'en')[:2]
                return jsonify({'error': get_freeze_message(lang), 'app_frozen': True}), 503
        except Exception:
            lang = request.headers.get('Accept-Language', 'en')[:2]
            return jsonify({'error': get_freeze_message(lang), 'app_frozen': True}), 503
    
    # First try PostgreSQL database
    db_user = None
    try:
        from app.models import db, User
        db_user = User.query.filter_by(username=username).first()
        if db_user and db_user.password_hash == hash_password(password):
            # Update last login
            db_user.last_login = datetime.now()
            db.session.commit()

            # Normalize role to lowercase for consistent checks
            normalized_role = (db_user.role or '').lower().replace(' ', '_')

            session['user_id'] = db_user.id
            session['username'] = db_user.username
            session['full_name'] = db_user.full_name
            session['email'] = db_user.email or ''
            session['role'] = normalized_role
            # superadmin and admin get is_admin=True
            session['is_admin'] = normalized_role in ['superadmin', 'super_admin', 'admin', 'institution_admin']
            session['logged_in'] = True
            session.permanent = True

            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'user_id': db_user.id,
                    'username': db_user.username,
                    'full_name': db_user.full_name,
                    'email': db_user.email or '',
                    'role': db_user.role or ''
                }
            })
    except Exception as e:
        print(f"Database login attempt failed: {e}")
    
    # Fallback to JSON file
    users_data = load_users()
    
    # Find user
    user = next((u for u in users_data['users'] if u['username'] == username), None)
    
    if not user or user['password'] != hash_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Update last login
    user['last_login'] = datetime.now().isoformat()
    save_users(users_data)
    
    # Sync JSON user with PostgreSQL database (for enrollments to work)
    db_user_id = user.get('db_user_id')
    if not db_user_id:
        try:
            from app.models import db, User
            # Check if user already exists in database by username
            existing_db_user = User.query.filter_by(username=user['username']).first()
            if existing_db_user:
                db_user_id = existing_db_user.id
            else:
                # Create user in database
                new_db_user = User(
                    username=user['username'],
                    email=user['email'],
                    full_name=user['full_name'],
                    password_hash=user['password'],
                    role='student',
                    phone=user.get('phone', '')
                )
                db.session.add(new_db_user)
                db.session.commit()
                db_user_id = new_db_user.id
                print(f"Synced JSON user to database with ID: {db_user_id}")
            
            # Store database ID in JSON for future logins
            user['db_user_id'] = db_user_id
            save_users(users_data)
        except Exception as e:
            print(f"Failed to sync user to database: {e}")
            import traceback
            traceback.print_exc()
    
    # Create session - Use database ID if available for enrollments to work
    # Normalize role to lowercase for consistent checks
    normalized_role = (user.get('role', '') or '').lower().replace(' ', '_')
    
    session['user_id'] = db_user_id if db_user_id else user['user_id']
    session['username'] = user['username']
    session['full_name'] = user['full_name']
    session['email'] = user['email']
    session['organization'] = user.get('organization', '')
    session['role'] = normalized_role
    # superadmin and admin get is_admin=True
    session['is_admin'] = normalized_role in ['superadmin', 'super_admin', 'admin', 'institution_admin']
    session['logged_in'] = True
    session.permanent = True
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user': {
            'user_id': db_user_id if db_user_id else user['user_id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'email': user['email'],
            'organization': user.get('organization', ''),
            'role': user.get('role', '')
        }
    })


@auth_bp.route('/user/logout', methods=['POST'])
def user_logout():
    """User logout endpoint - clears ALL session privileges"""
    # Clear ALL session keys for complete logout
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })


# ============================================
# Attendance Management
# ============================================

def load_attendance():
    """Load attendance records from JSON file"""
    if os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, 'r') as f:
            return json.load(f)
    return {'attendance_records': []}


def save_attendance(data):
    """Save attendance records to JSON file"""
    with open(ATTENDANCE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


@auth_bp.route('/attendance/record', methods=['POST'])
def record_attendance():
    """Record user attendance"""
    if not session.get('user_id'):
        return jsonify({'error': 'User not logged in'}), 401
    
    data = request.json or {}
    notes = data.get('notes', '').strip()
    
    attendance_data = load_attendance()
    
    # Create attendance record
    record = {
        'attendance_id': secrets.token_hex(16),
        'user_id': session['user_id'],
        'username': session['username'],
        'full_name': session['full_name'],
        'timestamp': datetime.now().isoformat(),
        'notes': notes
    }
    
    attendance_data['attendance_records'].append(record)
    save_attendance(attendance_data)
    
    return jsonify({
        'success': True,
        'message': 'Attendance recorded successfully',
        'record': record
    })


@auth_bp.route('/attendance/user', methods=['GET'])
def get_user_attendance():
    """Get attendance records for current user"""
    if not session.get('user_id'):
        return jsonify({'error': 'User not logged in'}), 401
    
    attendance_data = load_attendance()
    user_records = [r for r in attendance_data['attendance_records'] if r['user_id'] == session['user_id']]
    
    return jsonify({
        'success': True,
        'records': user_records,
        'count': len(user_records)
    })


@auth_bp.route('/attendance/all', methods=['GET'])
@admin_required
def get_all_attendance():
    """Get all attendance records (admin only)"""
    attendance_data = load_attendance()
    return jsonify({
        'success': True,
        'records': attendance_data['attendance_records'],
        'count': len(attendance_data['attendance_records'])
    })


@auth_bp.route('/users', methods=['GET'])
def get_users():
    """Get all users (authenticated users can see this for class management)"""
    users_data = load_users()
    # Remove password hashes and security questions from response
    sensitive_fields = ['password', 'security_q1', 'security_q2', 'security_q3', 'reset_token', 'reset_token_expires']
    safe_users = [{k: v for k, v in u.items() if k not in sensitive_fields} for u in users_data['users']]
    return jsonify({
        'success': True,
        'users': safe_users,
        'count': len(safe_users)
    })


@auth_bp.route('/users/all', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users (admin only) - legacy endpoint"""
    users_data = load_users()
    # Remove password hashes and security questions from response
    sensitive_fields = ['password', 'security_q1', 'security_q2', 'security_q3', 'reset_token', 'reset_token_expires']
    safe_users = [{k: v for k, v in u.items() if k not in sensitive_fields} for u in users_data['users']]
    return jsonify({
        'success': True,
        'users': safe_users,
        'count': len(safe_users)
    })


# ============================================
# Password Reset with Security Questions
# ============================================

@auth_bp.route('/password/verify-security', methods=['POST'])
def verify_security_questions():
    """Verify security questions for password reset"""
    data = request.json or {}
    username = data.get('username', '').strip()
    security_q1 = data.get('security_q1', '').strip()
    security_q2 = data.get('security_q2', '').strip()
    security_q3 = data.get('security_q3', '').strip()
    
    if not all([username, security_q1, security_q2, security_q3]):
        return jsonify({'error': 'All fields are required'}), 400
    
    users_data = load_users()
    user = next((u for u in users_data['users'] if u['username'] == username), None)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user has security questions set (legacy users won't have them)
    if not all([user.get('security_q1'), user.get('security_q2'), user.get('security_q3')]):
        return jsonify({
            'error': 'Password reset via security questions is not available for your account. Please contact an administrator to reset your password.'
        }), 400
    
    # Verify security questions (case-insensitive)
    if (user.get('security_q1') == hash_password(security_q1.lower()) and
        user.get('security_q2') == hash_password(security_q2.lower()) and
        user.get('security_q3') == hash_password(security_q3.lower())):
        
        # Generate temporary reset token
        reset_token = secrets.token_hex(32)
        user['reset_token'] = reset_token
        user['reset_token_expires'] = (datetime.now().timestamp() + 3600)  # 1 hour expiry
        save_users(users_data)
        
        return jsonify({
            'success': True,
            'reset_token': reset_token,
            'message': 'Security questions verified'
        })
    else:
        return jsonify({'error': 'Security answers are incorrect'}), 401


@auth_bp.route('/password/reset', methods=['POST'])
def reset_password():
    """Reset password using reset token"""
    data = request.json or {}
    reset_token = data.get('reset_token', '')
    new_password = data.get('new_password', '')
    
    if not all([reset_token, new_password]):
        return jsonify({'error': 'Reset token and new password are required'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400
    
    users_data = load_users()
    user = next((u for u in users_data['users'] if u.get('reset_token') == reset_token), None)
    
    if not user:
        return jsonify({'error': 'Invalid reset token'}), 400
    
    # Check token expiry
    if user.get('reset_token_expires', 0) < datetime.now().timestamp():
        return jsonify({'error': 'Reset token has expired'}), 400
    
    # Update password and clear reset token
    user['password'] = hash_password(new_password)
    user.pop('reset_token', None)
    user.pop('reset_token_expires', None)
    save_users(users_data)
    
    return jsonify({
        'success': True,
        'message': 'Password reset successful'
    })


# ============================================
# User Profile Management
# ============================================

@auth_bp.route('/user/profile', methods=['GET'])
def get_user_profile():
    """Get current user's profile"""
    if not session.get('user_id'):
        return jsonify({'error': 'User not logged in'}), 401
    
    # Try PostgreSQL first (for institution users)
    try:
        from app.models import User, db
        user_obj = User.query.filter_by(id=session['user_id']).first()
        if user_obj:
            dob = getattr(user_obj, 'date_of_birth', None)
            return jsonify({
                'success': True,
                'user': {
                    'user_id': user_obj.id,
                    'username': user_obj.username,
                    'full_name': user_obj.full_name,
                    'full_name_ar': getattr(user_obj, 'full_name_ar', '') or '',
                    'email': user_obj.email,
                    'phone': getattr(user_obj, 'phone', '') or '',
                    'bio': getattr(user_obj, 'bio', '') or '',
                    'role': user_obj.role,
                    'language': getattr(user_obj, 'language', 'en'),
                    'job_title': getattr(user_obj, 'job_title', '') or '',
                    'profession': getattr(user_obj, 'profession', '') or '',
                    'organization': getattr(user_obj, 'organization', '') or '',
                    'country': getattr(user_obj, 'country', '') or '',
                    'region': getattr(user_obj, 'region', '') or '',
                    'gender': getattr(user_obj, 'gender', '') or '',
                    'education_level': getattr(user_obj, 'education_level', '') or '',
                    'date_of_birth': dob.isoformat() if dob else ''
                }
            })
    except Exception as e:
        print(f"PostgreSQL lookup error: {e}")
    
    # Fall back to JSON file for legacy users
    users_data = load_users()
    user = next((u for u in users_data['users'] if u['user_id'] == session['user_id']), None)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Remove sensitive data
    safe_user = {k: v for k, v in user.items() if k not in ['password', 'security_q1', 'security_q2', 'security_q3', 'reset_token', 'reset_token_expires']}
    
    return jsonify({
        'success': True,
        'user': safe_user
    })


@auth_bp.route('/user/profile', methods=['PUT'])
def update_user_profile():
    """Update current user's profile"""
    if not session.get('user_id'):
        return jsonify({'error': 'User not logged in'}), 401
    
    data = request.json or {}
    
    # Try PostgreSQL first (for institution users)
    try:
        from app.models import User, db
        user_obj = User.query.filter_by(id=session['user_id']).first()
        if user_obj:
            try:
                name_changed = False
                old_name = user_obj.full_name or ''
                
                if 'full_name' in data:
                    new_name = data['full_name'].strip()
                    if old_name != new_name:
                        name_changed = True
                    user_obj.full_name = new_name
                if 'email' in data:
                    new_email = data['email'].strip()
                    existing = User.query.filter(User.email == new_email, User.id != user_obj.id).first()
                    if existing:
                        return jsonify({'error': 'Email already in use'}), 400
                    user_obj.email = new_email
                if 'phone' in data and hasattr(user_obj, 'phone'):
                    user_obj.phone = (data.get('phone') or '').strip()
                if 'language' in data and hasattr(user_obj, 'language'):
                    user_obj.language = (data.get('language') or 'en').strip()
                if 'bio' in data and hasattr(user_obj, 'bio'):
                    user_obj.bio = (data.get('bio') or '').strip()
                if 'full_name_ar' in data and hasattr(user_obj, 'full_name_ar'):
                    user_obj.full_name_ar = (data.get('full_name_ar') or '').strip()

                # Personal recognition fields used by EthicalSense
                for fld in ('job_title', 'profession', 'organization', 'country', 'region', 'gender', 'education_level'):
                    if fld in data and hasattr(user_obj, fld):
                        setattr(user_obj, fld, (data.get(fld) or '').strip() or None)

                if 'date_of_birth' in data and hasattr(user_obj, 'date_of_birth'):
                    raw_dob = (data.get('date_of_birth') or '').strip()
                    if raw_dob:
                        try:
                            from datetime import datetime as _dt
                            user_obj.date_of_birth = _dt.strptime(raw_dob, '%Y-%m-%d').date()
                        except Exception:
                            pass
                    else:
                        user_obj.date_of_birth = None

                db.session.commit()
                
                # Update session
                session['full_name'] = user_obj.full_name
                session['email'] = user_obj.email
                
                dob2 = getattr(user_obj, 'date_of_birth', None)
                return jsonify({
                    'success': True,
                    'message': 'Profile updated successfully',
                    'name_changed': name_changed,
                    'user': {
                        'user_id': user_obj.id,
                        'username': user_obj.username,
                        'full_name': user_obj.full_name,
                        'full_name_ar': getattr(user_obj, 'full_name_ar', '') or '',
                        'email': user_obj.email,
                        'phone': getattr(user_obj, 'phone', '') or '',
                        'bio': getattr(user_obj, 'bio', '') or '',
                        'role': user_obj.role,
                        'language': getattr(user_obj, 'language', 'en'),
                        'job_title': getattr(user_obj, 'job_title', '') or '',
                        'profession': getattr(user_obj, 'profession', '') or '',
                        'organization': getattr(user_obj, 'organization', '') or '',
                        'country': getattr(user_obj, 'country', '') or '',
                        'region': getattr(user_obj, 'region', '') or '',
                        'gender': getattr(user_obj, 'gender', '') or '',
                        'education_level': getattr(user_obj, 'education_level', '') or '',
                        'date_of_birth': dob2.isoformat() if dob2 else ''
                    }
                })
            except Exception as update_error:
                db.session.rollback()
                print(f"PostgreSQL update error: {update_error}")
                return jsonify({'error': 'Failed to update profile'}), 500
    except Exception as e:
        print(f"PostgreSQL lookup error: {e}")
    
    # Fall back to JSON file for legacy users
    users_data = load_users()
    user = next((u for u in users_data['users'] if u['user_id'] == session['user_id']), None)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Track if name changed for certificate regeneration
    name_changed = False
    old_name = user.get('full_name', '')
    new_name = old_name
    
    # Update allowed fields
    if 'full_name' in data:
        new_name = data['full_name'].strip()
        if old_name != new_name:
            name_changed = True
        user['full_name'] = new_name
    if 'email' in data:
        new_email = data['email'].strip()
        # Check if email is already used by another user
        if any(u['email'] == new_email and u['user_id'] != user['user_id'] for u in users_data['users']):
            return jsonify({'error': 'Email already in use'}), 400
        user['email'] = new_email
    if 'phone' in data:
        user['phone'] = data['phone'].strip()
    if 'organization' in data:
        user['organization'] = data['organization'].strip()
    
    save_users(users_data)
    
    # If name changed, update it in survey and exam data for certificate regeneration
    if name_changed:
        user_id = session['user_id']
        
        # Update name in entry survey data
        try:
            from app.routes.survey import load_survey_data, save_survey_data
            survey_data = load_survey_data()
            for survey_user in survey_data.get('users', []):
                if survey_user.get('id') == user_id:
                    if 'user_info' not in survey_user:
                        survey_user['user_info'] = {}
                    survey_user['user_info']['name'] = new_name
                    break
            save_survey_data(survey_data)
        except Exception as e:
            print(f"Error updating survey data: {e}")
        
        # Update name in exit exam data
        try:
            from app.routes.survey import load_exit_exam_data, save_exit_exam_data
            exam_data = load_exit_exam_data()
            for exam_user in exam_data.get('users', []):
                if exam_user.get('id') == user_id:
                    if 'user_info' not in exam_user:
                        exam_user['user_info'] = {}
                    exam_user['user_info']['name'] = new_name
                    break
            save_exit_exam_data(exam_data)
        except Exception as e:
            print(f"Error updating exam data: {e}")
    
    # Update session
    session['full_name'] = user['full_name']
    session['email'] = user['email']
    
    message = 'Profile updated successfully'
    if name_changed:
        message += '. Your certificates will automatically reflect the new name.'
    
    return jsonify({
        'success': True,
        'message': message,
        'name_changed': name_changed,
        'user': {k: v for k, v in user.items() if k not in ['password', 'security_q1', 'security_q2', 'security_q3']}
    })


@auth_bp.route('/user/change-password', methods=['POST'])
def change_password():
    """Change current user's password"""
    if not session.get('user_id'):
        return jsonify({'error': 'User not logged in'}), 401
    
    data = request.json or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not all([current_password, new_password]):
        return jsonify({'error': 'Current and new password are required'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters long'}), 400
    
    users_data = load_users()
    user = next((u for u in users_data['users'] if u['user_id'] == session['user_id']), None)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Verify current password
    if user['password'] != hash_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    # Update password
    user['password'] = hash_password(new_password)
    save_users(users_data)
    
    return jsonify({
        'success': True,
        'message': 'Password changed successfully'
    })


# ============================================
# Admin User Management
# ============================================

@auth_bp.route('/admin/users/<user_id>', methods=['PUT'])
@admin_required
def admin_update_user(user_id):
    """Admin update any user's information"""
    data = request.json or {}
    users_data = load_users()
    user = next((u for u in users_data['users'] if u['user_id'] == user_id), None)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Update allowed fields
    if 'full_name' in data:
        user['full_name'] = data['full_name'].strip()
    if 'email' in data:
        new_email = data['email'].strip()
        if any(u['email'] == new_email and u['user_id'] != user_id for u in users_data['users']):
            return jsonify({'error': 'Email already in use'}), 400
        user['email'] = new_email
    if 'phone' in data:
        user['phone'] = data['phone'].strip()
    if 'organization' in data:
        user['organization'] = data['organization'].strip()
    if 'role' in data:
        user['role'] = data['role']
    
    save_users(users_data)
    
    return jsonify({
        'success': True,
        'message': 'User updated successfully',
        'user': {k: v for k, v in user.items() if k not in ['password', 'security_q1', 'security_q2', 'security_q3']}
    })


@auth_bp.route('/admin/users/<user_id>/reset-password', methods=['POST'])
@admin_required
def admin_reset_user_password(user_id):
    """Admin reset any user's password"""
    data = request.json or {}
    new_password = data.get('new_password', '')
    
    if not new_password:
        # Generate random password if not provided
        new_password = generate_password()
    
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400
    
    users_data = load_users()
    user = next((u for u in users_data['users'] if u['user_id'] == user_id), None)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user['password'] = hash_password(new_password)
    save_users(users_data)
    
    return jsonify({
        'success': True,
        'message': 'Password reset successfully',
        'new_password': new_password
    })


# ============================================
# Self-Service Password Reset
# ============================================

@auth_bp.route('/forgot-password/check', methods=['POST'])
def forgot_password_check():
    """Check if user exists and get security questions"""
    data = request.json or {}
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    # Try PostgreSQL database first
    try:
        from app.models import db, User
        db_user = User.query.filter_by(username=username).first()
        if db_user:
            return jsonify({
                'success': True,
                'user_found': True,
                'source': 'database',
                'has_email': bool(db_user.email),
                'email_hint': db_user.email[:3] + '***' + db_user.email.split('@')[-1] if db_user.email else None
            })
    except Exception as e:
        print(f"Database user check failed: {e}")
    
    # Fallback to JSON file
    users_data = load_users()
    user = next((u for u in users_data['users'] if u['username'] == username), None)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'success': True,
        'user_found': True,
        'source': 'json',
        'has_security_questions': all([
            user.get('security_q1'),
            user.get('security_q2'),
            user.get('security_q3')
        ]),
        'has_email': bool(user.get('email')),
        'email_hint': user['email'][:3] + '***' + user['email'].split('@')[-1] if user.get('email') else None
    })


@auth_bp.route('/forgot-password/verify', methods=['POST'])
def forgot_password_verify():
    """Verify security questions and reset password"""
    data = request.json or {}
    username = data.get('username', '').strip()
    security_q1 = data.get('security_q1', '').strip().lower()
    security_q2 = data.get('security_q2', '').strip().lower()
    security_q3 = data.get('security_q3', '').strip().lower()
    new_password = data.get('new_password', '')
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    if not all([security_q1, security_q2, security_q3]):
        return jsonify({'error': 'All security answers are required'}), 400
    
    if not new_password or len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
    
    # Try JSON file first (users registered through the app)
    users_data = load_users()
    user = next((u for u in users_data['users'] if u['username'] == username), None)
    
    if user:
        # Verify security questions (already lowercased at input, hash matches stored lowercase hashes)
        if (user.get('security_q1') != hash_password(security_q1) or
            user.get('security_q2') != hash_password(security_q2) or
            user.get('security_q3') != hash_password(security_q3)):
            return jsonify({'error': 'Security answers do not match'}), 401
        
        # Reset password
        user['password'] = hash_password(new_password)
        save_users(users_data)
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully. You can now login with your new password.'
        })
    
    # Try PostgreSQL database
    try:
        from app.models import db, User
        db_user = User.query.filter_by(username=username).first()
        if db_user:
            # Database users don't have security questions, return error
            return jsonify({'error': 'Password reset via security questions not available for this account. Please contact administrator.'}), 400
    except Exception as e:
        print(f"Database user check failed: {e}")
    
    return jsonify({'error': 'User not found'}), 404


def _generate_password_reset_token(user, request_ip=None):
    """Create a PasswordResetToken row and return the raw token (1-hour TTL)."""
    from app.models import db, PasswordResetToken
    from datetime import timedelta
    import hashlib
    import secrets
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(hours=1),
        ip_address=request_ip,
    )
    db.session.add(reset_token)
    db.session.commit()
    return raw_token


def _send_password_reset_email(user, raw_token):
    """Email the reset link to the user. Returns send_email() result dict."""
    from app.services.notification_service import send_email
    base = (request.url_root or '').rstrip('/')
    link = f"{base}/reset-password?token={raw_token}"
    subject = 'SkillPilot — Password reset link (valid for 1 hour)'
    name = (user.full_name or user.username or 'there')
    body_text = (
        f"Hi {name},\n\n"
        f"We received a request to reset the password for your SkillPilot account "
        f"({user.username}).\n\n"
        f"Use the link below within the next hour to choose a new password:\n"
        f"{link}\n\n"
        f"If you did not request this, you can safely ignore this email — your "
        f"password will not change.\n\n"
        f"— SkillPilot"
    )
    body_html = (
        f"<p>Hi {name},</p>"
        f"<p>We received a request to reset the password for your SkillPilot account "
        f"<strong>{user.username}</strong>.</p>"
        f"<p>Use the link below within the next hour to choose a new password:</p>"
        f'<p><a href="{link}" style="background:#1a5c5e;color:#fff;padding:10px 18px;'
        f'border-radius:6px;text-decoration:none;">Reset my password</a></p>'
        f"<p style=\"font-size:.9em;color:#555;\">If the button doesn\u2019t work, paste this URL into your browser:<br>"
        f"<code>{link}</code></p>"
        f"<p style=\"font-size:.9em;color:#555;\">If you did not request this, you can safely ignore this email — your password will not change.</p>"
    )
    return send_email(user.email, subject, body_text, body_html)


@auth_bp.route('/forgot-password/admin-reset', methods=['POST'])
@admin_required
def forgot_password_admin_reset():
    """Generate a password reset token (admin assist) and email it if SMTP is configured.

    Admin-only — this endpoint can mint a reset token for any account, so it
    must never be reachable without an authenticated admin session. Self-service
    flow is `/forgot-password/email-link`.
    """
    data = request.json or {}
    username = data.get('username', '').strip()

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    try:
        from app.models import User
        db_user = User.query.filter_by(username=username).first()
        if not db_user:
            return jsonify({'error': 'User not found'}), 404

        raw_token = _generate_password_reset_token(db_user, request.remote_addr)

        email_status = {'sent': False, 'reason': 'no_email_on_account'}
        if db_user.email:
            email_status = _send_password_reset_email(db_user, raw_token)

        response = {
            'success': True,
            'message': 'Password reset token generated',
            'expires_in': '1 hour',
            'email_sent': bool(email_status.get('sent')),
            'email_reason': email_status.get('reason'),
        }
        # Only show the raw token to admins when email could not be delivered,
        # so they can hand it over manually. When email succeeded, hide it.
        if not email_status.get('sent'):
            response['token'] = raw_token
            response['note'] = (
                'Email could not be delivered automatically. Share this token '
                'securely with the user, or configure SMTP under '
                '/admin/system → Email & SMTP.'
            )
        return jsonify(response)
    except Exception as e:
        print(f"Password reset token generation failed: {e}")
        return jsonify({'error': 'Failed to generate reset token'}), 500


@auth_bp.route('/forgot-password/email-link', methods=['POST'])
def forgot_password_email_link():
    """Self-service: user enters their username/email; we email a reset link.

    Always returns a generic success message so attackers can\u2019t enumerate
    accounts. The actual delivery status is logged server-side.
    """
    data = request.json or {}
    identifier = (data.get('username') or data.get('email') or '').strip()
    generic_response = jsonify({
        'success': True,
        'message': ('If an account with that username or email exists and has a '
                    'verified email address, a password reset link has just been sent.')
    })
    if not identifier:
        return generic_response

    try:
        from app.models import User
        user = (User.query.filter_by(username=identifier).first()
                or User.query.filter_by(email=identifier).first())
        if not user or not user.email:
            return generic_response
        raw_token = _generate_password_reset_token(user, request.remote_addr)
        result = _send_password_reset_email(user, raw_token)
        # Avoid logging the username/email — privacy/PII.
        print(f"[forgot-password] reset link sent: ok={result.get('sent')} reason={result.get('reason')}")
    except Exception as e:
        print(f"Self-service password reset failed: {e}")
    return generic_response


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password_with_token():
    """Reset password using a valid token"""
    data = request.json or {}
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '')
    
    if not token:
        return jsonify({'error': 'Reset token is required'}), 400
    
    if not new_password or len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
    
    try:
        from app.models import db, User, PasswordResetToken
        import hashlib
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        reset_token = PasswordResetToken.query.filter_by(
            token_hash=token_hash,
            used_at=None
        ).first()
        
        if not reset_token:
            return jsonify({'error': 'Invalid or expired token'}), 400
        
        if reset_token.expires_at < datetime.utcnow():
            return jsonify({'error': 'Token has expired'}), 400
        
        # Reset the password
        user = User.query.get(reset_token.user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.password_hash = hash_password(new_password)
        reset_token.used_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully. You can now login with your new password.'
        })
    except Exception as e:
        print(f"Password reset failed: {e}")
        return jsonify({'error': 'Failed to reset password'}), 500
