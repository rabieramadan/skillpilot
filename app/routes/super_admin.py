"""
Super Admin Routes - Dedicated login and dashboard for super admins only
Single-institution mode - manages all users and courses without institution filtering
"""

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, Response
from functools import wraps
import hashlib
import csv
import io

super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/admin')


def get_db():
    """Get database session"""
    try:
        from app.models import db
        return db.session
    except Exception as e:
        print(f"Database error: {e}")
        return None


def super_admin_required(f):
    """Decorator to require super_admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('super_admin.login_page'))

        role = session.get('role', '').lower()
        if role not in ['super_admin', 'superadmin']:
            if request.is_json:
                return jsonify({'error': 'Super admin access required'}), 403
            return redirect(url_for('super_admin.login_page'))

        return f(*args, **kwargs)
    return decorated_function


def admin_dashboard_required(f):
    """Decorator to allow both admin and superadmin access to dashboard"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('super_admin.login_page'))

        role = session.get('role', '').lower()
        if role not in ['super_admin', 'superadmin', 'admin', 'institution_admin']:
            if request.is_json:
                return jsonify({'error': 'Admin access required'}), 403
            return redirect(url_for('super_admin.login_page'))

        return f(*args, **kwargs)
    return decorated_function


def is_superadmin_role():
    """Check if current user has superadmin role"""
    role = session.get('role', '').lower()
    return role in ['super_admin', 'superadmin']


@super_admin_bp.route('/', methods=['GET'])
@super_admin_bp.route('', methods=['GET'])
def admin_root():
    """Redirect /admin to login or dashboard"""
    role = session.get('role', '').lower()
    if session.get('logged_in') and role in ['super_admin', 'superadmin', 'admin', 'institution_admin']:
        return redirect(url_for('super_admin.dashboard'))
    return redirect(url_for('super_admin.login_page'))


@super_admin_bp.route('/login', methods=['GET'])
def login_page():
    """Render admin login page"""
    # If already logged in as admin or super admin, redirect to dashboard
    role = session.get('role', '').lower()
    if session.get('logged_in') and role in ['super_admin', 'superadmin', 'admin', 'institution_admin']:
        return redirect(url_for('super_admin.dashboard'))
    return render_template('admin_login.html')


@super_admin_bp.route('/login', methods=['POST'])
def login():
    """Admin/Super admin login"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User
        from datetime import datetime

        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400

        # Find user
        user = User.query.filter_by(username=username).first()

        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Check password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user.password_hash != password_hash:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Check if user is admin or super_admin
        user_role = user.role.lower()
        allowed_roles = ['super_admin', 'superadmin', 'admin', 'institution_admin']
        if user_role not in allowed_roles:
            return jsonify({'error': 'Admin access only. Teachers and students should use the main portal.'}), 403

        # Determine if superadmin
        is_superadmin = user_role in ['super_admin', 'superadmin']
        session_role = 'superadmin' if is_superadmin else 'admin'

        # Set session
        session['user_id'] = user.id
        session['username'] = user.username
        session['full_name'] = user.full_name
        session['email'] = user.email
        session['role'] = session_role
        session['is_admin'] = True
        session['is_superadmin'] = is_superadmin
        session['logged_in'] = True

        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()

        return jsonify({
            'success': True,
            'redirect': '/admin/dashboard',
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'role': session_role
            }
        })
    except Exception as e:
        print(f"Admin login error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/logout', methods=['POST'])
def logout():
    """Super admin logout"""
    session.clear()
    return jsonify({'success': True, 'redirect': url_for('super_admin.login')})


@super_admin_bp.route('/dashboard', methods=['GET'])
@admin_dashboard_required
def dashboard():
    """Render admin dashboard"""
    is_superadmin = is_superadmin_role()
    return render_template('admin_dashboard.html', is_superadmin=is_superadmin, user_role=session.get('role', 'admin'))


# ============================================
# API ENDPOINTS FOR DASHBOARD
# ============================================

@super_admin_bp.route('/api/warnings', methods=['GET'])
@admin_dashboard_required
def get_warnings():
    """Return flagged exam attempts + open AtRiskAlerts for the warnings dashboard."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        from app.models import ExamResult, Exam, User, Course, AtRiskAlert

        # --- Flagged exam attempts (violation_count > 0) ---
        flagged_results = (
            ExamResult.query
            .filter(ExamResult.violation_count > 0)
            .order_by(ExamResult.submitted_at.desc())
            .limit(200)
            .all()
        )
        flags = []
        for r in flagged_results:
            student = User.query.get(r.user_id)
            exam = Exam.query.get(r.exam_id)
            course = Course.query.get(exam.course_id) if exam else None
            # Summarise proctoring event types
            events = r.proctoring_events or []
            type_counts = {}
            for ev in events:
                t = ev.get('type', 'unknown')
                type_counts[t] = type_counts.get(t, 0) + 1
            summary = ', '.join(f"{k}×{v}" for k, v in type_counts.items()) if type_counts else ''
            flags.append({
                'result_id': r.id,
                'student_name': (student.full_name or student.username) if student else '—',
                'student_username': student.username if student else '—',
                'exam_title': exam.title if exam else '—',
                'course_title': course.title if course else '—',
                'course_id': exam.course_id if exam else None,
                'exam_id': r.exam_id,
                'attempt_number': r.attempt_number,
                'violation_count': r.violation_count or 0,
                'events_summary': summary,
                'percentage': round(r.percentage or 0, 1),
                'passed': r.passed,
                'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None,
            })

        # --- At-risk alerts (open) ---
        alerts = (
            AtRiskAlert.query
            .filter_by(status='open')
            .order_by(AtRiskAlert.risk_score.desc())
            .limit(200)
            .all()
        )
        at_risk = []
        for a in alerts:
            student = User.query.get(a.user_id)
            course = Course.query.get(a.course_id) if a.course_id else None
            # Build a readable reason from factors JSON
            factors = a.factors or []
            reason = ', '.join(f.get('factor', '') for f in factors if f.get('factor')) if factors else ''
            at_risk.append({
                'alert_id': a.id,
                'student_name': (student.full_name or student.username) if student else '—',
                'student_username': student.username if student else '—',
                'course_title': course.title if course else '—',
                'risk_score': a.risk_score,
                'risk_level': a.risk_level or 'low',
                'reason': reason,
                'created_at': a.created_at.isoformat() if a.created_at else None,
            })

        return jsonify({'flags': flags, 'at_risk': at_risk})
    except Exception as e:
        print(f"Warnings error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/warnings/acknowledge-alert/<alert_id>', methods=['POST'])
@admin_dashboard_required
def acknowledge_alert(alert_id):
    """Mark an at-risk alert as acknowledged."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        from app.models import AtRiskAlert
        a = AtRiskAlert.query.get(alert_id)
        if not a:
            return jsonify({'error': 'Alert not found'}), 404
        a.status = 'acknowledged'
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/stats', methods=['GET'])
@admin_dashboard_required
def get_dashboard_stats():
    """Get overall platform statistics"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User, Course, Enrollment

        stats = {
            'total_courses': Course.query.count(),
            'total_students': User.query.filter_by(role='student', is_active=True).count(),
            'total_teachers': User.query.filter(User.role.in_(['instructor', 'teacher']), User.is_active == True).count(),
            'total_admins': User.query.filter(User.role.in_(['admin', 'institution_admin']), User.is_active == True).count(),
            'total_enrollments': Enrollment.query.count()
        }

        return jsonify(stats)
    except Exception as e:
        print(f"Get stats error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# USER MANAGEMENT (CRUD)
# ============================================

@super_admin_bp.route('/api/users', methods=['GET'])
@admin_dashboard_required
def get_all_users():
    """Get all users"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User

        users = User.query.order_by(User.created_at.desc()).all()
        users_list = [{
            'id': str(u.id),
            'username': u.username,
            'full_name': u.full_name,
            'email': u.email,
            'role': u.role,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'last_login': u.last_login.isoformat() if u.last_login else None
        } for u in users]

        return jsonify({'users': users_list})
    except Exception as e:
        print(f"Get users error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/users', methods=['POST'])
@admin_dashboard_required
def create_user():
    """Create a new user (admin, teacher, or student)"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User
        from datetime import datetime

        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip()
        role = data.get('role', 'student')

        if not all([username, password, full_name]):
            return jsonify({'error': 'Username, password, and full name are required'}), 400

        # Valid roles: superadmin, admin, teacher, student (plus legacy names for compatibility)
        valid_roles = ['superadmin', 'super_admin', 'admin', 'institution_admin', 'teacher', 'instructor', 'student']
        if role not in valid_roles:
            return jsonify({'error': 'Invalid role'}), 400

        # Check if username exists
        existing = User.query.filter_by(username=username).first()
        if existing:
            return jsonify({'error': 'Username already exists'}), 400

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        user = User(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            email=email,
            role=role,
            is_active=True,
            is_approved=True,
            created_at=datetime.utcnow()
        )

        db.add(user)
        db.commit()

        return jsonify({
            'success': True,
            'message': f'{role.replace("_", " ").title()} created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        })
    except Exception as e:
        db.rollback()
        print(f"Create user error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/users/<user_id>', methods=['GET'])
@admin_dashboard_required
def get_user_details(user_id):
    """Get user details"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'success': True,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'phone': user.phone,
                'bio': user.bio,
                'is_active': user.is_active,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
        })
    except Exception as e:
        print(f"Get user details error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/users/<user_id>', methods=['PUT'])
@admin_dashboard_required
def update_user(user_id):
    """Update a user"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()

        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'email' in data:
            user.email = data['email']
        if 'phone' in data:
            user.phone = data['phone']
        if 'role' in data:
            user.role = data['role']
        if 'password' in data and data['password']:
            user.password_hash = hashlib.sha256(data['password'].encode()).hexdigest()

        db.commit()

        return jsonify({
            'success': True,
            'message': 'User updated successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Update user error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/users/<user_id>/block', methods=['POST'])
@admin_dashboard_required
def block_user(user_id):
    """Block/unblock a user"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        block = data.get('block', True)

        user.is_active = not block
        db.commit()

        action = 'blocked' if block else 'unblocked'
        return jsonify({
            'success': True,
            'message': f'User {action} successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Block user error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/users/<user_id>', methods=['DELETE'])
@admin_dashboard_required
def delete_user(user_id):
    """Delete a user"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User, Enrollment, CourseInstructor

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Don't allow deleting the super admin. The stored role is
        # 'superadmin'; comparing against 'super_admin' alone matched nothing,
        # so this guard never fired and the account could be removed.
        if (user.role or '').lower().replace(' ', '_') in (
                'superadmin', 'super_admin'):
            return jsonify({'error': 'Cannot delete super admin'}), 400

        # Remove enrollments if student
        if user.role == 'student':
            Enrollment.query.filter_by(user_id=user_id).delete()

        # Remove course assignments if instructor/teacher
        if user.role in ['instructor', 'teacher']:
            CourseInstructor.query.filter_by(user_id=user_id).delete()

        db.delete(user)
        db.commit()

        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Delete user error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# COURSE MANAGEMENT
# ============================================

@super_admin_bp.route('/api/courses', methods=['GET'])
@admin_dashboard_required
def get_all_courses():
    """Get all courses"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course

        courses = Course.query.order_by(Course.created_at.desc()).all()
        courses_list = [{
            'id': str(c.id),
            'title': c.title,
            'title_ar': c.title_ar,
            'code': c.code,
            'description': c.description,
            'is_published': c.is_published,
            'is_self_paced': c.is_self_paced,
            'registration_open': c.registration_open if c.registration_open is not None else True,
            'start_date': c.start_date.isoformat() if c.start_date else None,
            'end_date': c.end_date.isoformat() if c.end_date else None,
            'created_at': c.created_at.isoformat() if c.created_at else None
        } for c in courses]

        return jsonify({'courses': courses_list})
    except Exception as e:
        print(f"Get courses error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses', methods=['POST'])
@admin_dashboard_required
def create_course():
    """Create a new course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course
        from datetime import datetime

        data = request.get_json()
        title = data.get('title', '').strip()

        if not title:
            return jsonify({'error': 'Course title is required'}), 400

        course = Course(
            title=title,
            title_ar=data.get('title_ar', ''),
            code=data.get('code', ''),
            description=data.get('description', ''),
            description_ar=data.get('description_ar', ''),
            institution_id=data.get('institution_id'),
            is_published=data.get('is_published', False),
            created_at=datetime.utcnow()
        )

        db.add(course)
        db.flush()  # Get the course ID before creating survey

        # Automatically create exit survey for training evaluation
        from app.services.auto_survey import create_exit_survey_for_course
        exit_survey = create_exit_survey_for_course(db, course.id, course.title)

        db.commit()

        return jsonify({
            'success': True,
            'message': 'Course created successfully with exit survey',
            'course': {
                'id': course.id,
                'title': course.title,
                'code': course.code,
                'exit_survey_created': exit_survey is not None
            }
        })
    except Exception as e:
        db.rollback()
        print(f"Create course error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>', methods=['PUT'])
@admin_dashboard_required
def update_course(course_id):
    """Update a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course

        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        data = request.get_json()

        if 'title' in data:
            course.title = data['title']
        if 'title_ar' in data:
            course.title_ar = data['title_ar']
        if 'code' in data:
            course.code = data['code']
        if 'description' in data:
            course.description = data['description']
        if 'description_ar' in data:
            course.description_ar = data['description_ar']
        publish_changed = False
        new_publish_state = None
        if 'is_published' in data:
            new_publish_state = bool(data['is_published'])
            publish_changed = (bool(course.is_published) != new_publish_state)
            course.is_published = new_publish_state

        if 'registration_open' in data:
            course.registration_open = bool(data['registration_open'])

        db.commit()

        if publish_changed:
            try:
                from app.services.notification_service import notify_course_audience
                if new_publish_state:
                    notify_course_audience(
                        course_id,
                        kind='course_published',
                        title=f'Course published: {course.title}',
                        body=('This course is now live. Open it to see weekly '
                              'materials, exams, and assignments.'),
                        url=f'/app#course-{course_id}',
                        severity='success',
                        payload={'course_id': course_id, 'course_code': course.code},
                    )
                else:
                    notify_course_audience(
                        course_id,
                        kind='course_unpublished',
                        title=f'Course unpublished: {course.title}',
                        body='An administrator has temporarily hidden this course from learners.',
                        url=f'/app#course-{course_id}',
                        severity='warning',
                        payload={'course_id': course_id, 'course_code': course.code},
                        include_students=False,
                    )
            except Exception as ne:
                print(f"[notify] course publish toggle: {ne}")

        return jsonify({
            'success': True,
            'message': 'Course updated successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Update course error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/registration', methods=['PATCH'])
@admin_dashboard_required
def toggle_course_registration(course_id):
    """Open or close registration for a single course."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        from app.models import Course
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        data = request.get_json() or {}
        course.registration_open = bool(data.get('registration_open', True))
        db.commit()
        state = 'open' if course.registration_open else 'closed'
        return jsonify({'success': True, 'registration_open': course.registration_open,
                        'message': f'Registration {state} for "{course.title}"'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/registration/global', methods=['POST'])
@admin_dashboard_required
def toggle_global_registration():
    """Pause or resume registration across ALL courses."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        from app.models import KeyValueSetting
        data = request.get_json() or {}
        paused = bool(data.get('paused', False))
        setting = KeyValueSetting.query.filter_by(key='registration_paused').first()
        if setting:
            setting.value = '1' if paused else '0'
        else:
            setting = KeyValueSetting(key='registration_paused', value='1' if paused else '0')
            db.add(setting)
        db.commit()
        state = 'paused' if paused else 'open'
        return jsonify({'success': True, 'paused': paused,
                        'message': f'Global registration is now {state}'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/registration/global', methods=['GET'])
@admin_dashboard_required
def get_global_registration():
    """Return current global registration pause state."""
    try:
        from app.models import KeyValueSetting
        setting = KeyValueSetting.query.filter_by(key='registration_paused').first()
        paused = setting and setting.value == '1'
        return jsonify({'paused': paused})
    except Exception as e:
        return jsonify({'paused': False})


@super_admin_bp.route('/api/settings/ai-chat-visibility', methods=['GET', 'POST'])
@admin_dashboard_required
def ai_chat_visibility():
    """GET: return current AI chat visibility state. POST: update it."""
    from app.models import KeyValueSetting
    if request.method == 'GET':
        try:
            setting = KeyValueSetting.query.filter_by(key='ai_chat_hidden').first()
            hidden = bool(setting and setting.value == '1')
            return jsonify({'hidden': hidden})
        except Exception:
            return jsonify({'hidden': False})
    # POST
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        data = request.get_json() or {}
        hidden = bool(data.get('hidden', False))
        setting = KeyValueSetting.query.filter_by(key='ai_chat_hidden').first()
        if setting:
            setting.value = '1' if hidden else '0'
        else:
            setting = KeyValueSetting(key='ai_chat_hidden', value='1' if hidden else '0')
            db.add(setting)
        db.commit()
        return jsonify({'success': True, 'hidden': hidden,
                        'message': 'AI chat hidden' if hidden else 'AI chat visible'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>', methods=['DELETE'])
@admin_dashboard_required
def delete_course(course_id):
    """Delete a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import (Course, Enrollment, CourseInstructor, Attendance,
                                CourseWeek, WeekMaterial, Assignment, AssignmentSubmission,
                                Exam, ExamQuestion, ExamResult, Survey, SurveyQuestion, SurveyResponse)

        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Delete all dependent records in correct order
        # 1. Attendance records
        Attendance.query.filter_by(course_id=course_id).delete()

        # 2. Survey responses, questions, and surveys
        surveys = Survey.query.filter_by(course_id=course_id).all()
        for survey in surveys:
            SurveyResponse.query.filter_by(survey_id=survey.id).delete()
            SurveyQuestion.query.filter_by(survey_id=survey.id).delete()
        Survey.query.filter_by(course_id=course_id).delete()

        # 3. Exam results, questions, and exams
        exams = Exam.query.filter_by(course_id=course_id).all()
        for exam in exams:
            ExamResult.query.filter_by(exam_id=exam.id).delete()
            ExamQuestion.query.filter_by(exam_id=exam.id).delete()
        Exam.query.filter_by(course_id=course_id).delete()

        # 4. Assignment submissions, assignments, materials, and weeks
        weeks = CourseWeek.query.filter_by(course_id=course_id).all()
        for week in weeks:
            assignments = Assignment.query.filter_by(week_id=week.id).all()
            for assignment in assignments:
                AssignmentSubmission.query.filter_by(assignment_id=assignment.id).delete()
            Assignment.query.filter_by(week_id=week.id).delete()
            WeekMaterial.query.filter_by(week_id=week.id).delete()
        CourseWeek.query.filter_by(course_id=course_id).delete()

        # 5. Enrollments and instructor assignments
        Enrollment.query.filter_by(course_id=course_id).delete()
        CourseInstructor.query.filter_by(course_id=course_id).delete()

        # Finally delete the course
        db.delete(course)
        db.commit()

        return jsonify({
            'success': True,
            'message': 'Course deleted successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Delete course error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>', methods=['GET'])
@admin_dashboard_required
def get_course_details(course_id):
    """Get course details"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course, CourseInstructor, User

        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Get assigned instructors
        instructor_records = CourseInstructor.query.filter_by(course_id=course_id).all()
        instructors = []
        for ir in instructor_records:
            teacher = User.query.get(ir.user_id)
            if teacher:
                instructors.append({
                    'id': str(teacher.id),
                    'username': teacher.username,
                    'full_name': teacher.full_name
                })

        return jsonify({
            'success': True,
            'course': {
                'id': str(course.id),
                'code': course.code,
                'title': course.title,
                'title_ar': course.title_ar,
                'description': course.description,
                'is_published': course.is_published,
                'instructors': instructors
            }
        })
    except Exception as e:
        print(f"Get course details error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/students', methods=['GET'])
@admin_dashboard_required
def get_course_students(course_id):
    """Get students enrolled in a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course, Enrollment, User

        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        enrollments = Enrollment.query.filter_by(course_id=course_id).all()

        result = []
        for enrollment in enrollments:
            student = User.query.get(enrollment.user_id)
            if student:
                result.append({
                    'id': student.id,
                    'username': student.username,
                    'full_name': student.full_name,
                    'email': student.email,
                    'enrollment_status': enrollment.status,
                    'payment_status': enrollment.payment_status if hasattr(enrollment, 'payment_status') else None,
                    'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None
                })

        return jsonify({
            'course': {
                'id': course.id,
                'code': course.code,
                'title': course.title
            },
            'students': result
        })
    except Exception as e:
        print(f"Get course students error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/available-teachers', methods=['GET'])
@admin_dashboard_required
def get_available_teachers(course_id):
    """Get teachers available to assign to a course (not already assigned)"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course, User, CourseInstructor

        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Get all instructors (support both 'teacher' and 'instructor' roles)
        all_teachers = User.query.filter(
            User.role.in_(['teacher', 'instructor']),
            User.is_active == True
        ).all()

        # Get already assigned teacher IDs
        assigned_ids = set()
        assignments = CourseInstructor.query.filter_by(course_id=course_id).all()
        for a in assignments:
            assigned_ids.add(str(a.user_id))

        # Filter out already assigned
        available = []
        for t in all_teachers:
            if str(t.id) not in assigned_ids:
                available.append({
                    'id': str(t.id),
                    'username': t.username,
                    'full_name': t.full_name,
                    'email': t.email
                })

        return jsonify({
            'success': True,
            'teachers': available
        })
    except Exception as e:
        print(f"Get available teachers error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/teachers', methods=['POST'])
@admin_dashboard_required
def add_teacher_to_course(course_id):
    """Assign a teacher to a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course, User, CourseInstructor
        from datetime import datetime

        data = request.get_json()
        teacher_id = data.get('teacher_id')

        if not teacher_id:
            return jsonify({'error': 'Teacher ID is required'}), 400

        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        teacher = User.query.get(teacher_id)
        if not teacher or teacher.role not in ['teacher', 'instructor']:
            return jsonify({'error': 'Teacher not found'}), 404

        # Check if already assigned
        existing = CourseInstructor.query.filter_by(
            course_id=course_id,
            user_id=teacher_id
        ).first()

        if existing:
            return jsonify({'error': 'Teacher already assigned to this course'}), 400

        assignment = CourseInstructor(
            course_id=course_id,
            user_id=teacher_id
        )

        db.add(assignment)
        db.commit()

        return jsonify({
            'success': True,
            'message': 'Teacher assigned to course successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Add teacher to course error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/teachers/<teacher_id>', methods=['DELETE'])
@admin_dashboard_required
def remove_teacher_from_course(course_id, teacher_id):
    """Remove a teacher from a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import CourseInstructor

        assignment = CourseInstructor.query.filter_by(
            course_id=course_id,
            user_id=teacher_id
        ).first()

        if not assignment:
            return jsonify({'error': 'Teacher not assigned to this course'}), 404

        db.delete(assignment)
        db.commit()

        return jsonify({
            'success': True,
            'message': 'Teacher removed from course successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Remove teacher from course error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/assign-teacher', methods=['POST'])
@admin_dashboard_required
def assign_teacher_to_course(course_id):
    """Assign a teacher to a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course, User, CourseInstructor
        from datetime import datetime

        data = request.get_json()
        teacher_id = data.get('teacher_id')

        if not teacher_id:
            return jsonify({'error': 'Teacher ID is required'}), 400

        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        teacher = User.query.get(teacher_id)
        if not teacher or teacher.role not in ['teacher', 'instructor']:
            return jsonify({'error': 'Teacher not found'}), 404

        # Check if already assigned
        existing = CourseInstructor.query.filter_by(
            course_id=course_id,
            user_id=teacher_id
        ).first()

        if existing:
            return jsonify({'error': 'Teacher already assigned to this course'}), 400

        assignment = CourseInstructor(
            course_id=course_id,
            user_id=teacher_id
        )

        db.add(assignment)
        db.commit()

        return jsonify({
            'success': True,
            'message': 'Teacher assigned to course successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Assign teacher error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/unassign-teacher', methods=['POST'])
@admin_dashboard_required
def unassign_teacher_from_course(course_id):
    """Remove a teacher from a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import CourseInstructor

        data = request.get_json()
        teacher_id = data.get('teacher_id')

        if not teacher_id:
            return jsonify({'error': 'Teacher ID is required'}), 400

        assignment = CourseInstructor.query.filter_by(
            course_id=course_id,
            user_id=teacher_id
        ).first()

        if not assignment:
            return jsonify({'error': 'Teacher not assigned to this course'}), 404

        db.delete(assignment)
        db.commit()

        return jsonify({
            'success': True,
            'message': 'Teacher removed from course successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Unassign teacher error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# SEARCH FUNCTIONALITY
# ============================================

@super_admin_bp.route('/api/search', methods=['GET'])
@admin_dashboard_required
def global_search():
    """Search users and courses"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User, Course

        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'all')  # all, users, courses

        if not query or len(query) < 2:
            return jsonify({'error': 'Search query must be at least 2 characters'}), 400

        results = {
            'users': [],
            'courses': []
        }

        search_pattern = f'%{query}%'

        # Search users
        if search_type in ['all', 'users']:
            users = User.query.filter(
                (User.username.ilike(search_pattern)) |
                (User.full_name.ilike(search_pattern)) |
                (User.email.ilike(search_pattern))
            ).limit(20).all()

            results['users'] = [{
                'id': u.id,
                'username': u.username,
                'full_name': u.full_name,
                'email': u.email,
                'role': u.role,
                'is_active': u.is_active
            } for u in users]

        # Search courses
        if search_type in ['all', 'courses']:
            courses = Course.query.filter(
                (Course.title.ilike(search_pattern)) |
                (Course.code.ilike(search_pattern))
            ).limit(20).all()

            results['courses'] = [{
                'id': c.id,
                'title': c.title,
                'code': c.code,
                'is_published': c.is_published
            } for c in courses]

        return jsonify(results)
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# ENROLLMENT MANAGEMENT
# ============================================

@super_admin_bp.route('/api/enrollments', methods=['GET'])
@admin_dashboard_required
def get_all_enrollments():
    """Get all enrollments"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User, Course, Enrollment

        enrollments = Enrollment.query.order_by(Enrollment.enrolled_at.desc()).all()
        enrollments_list = []
        
        for e in enrollments:
            student = User.query.get(e.user_id)
            course = Course.query.get(e.course_id)
            enrollments_list.append({
                'id': str(e.id),
                'student_id': str(e.user_id),
                'student_name': student.full_name if student else 'Unknown',
                'course_id': str(e.course_id),
                'course_title': course.title if course else 'Unknown',
                'status': e.status,
                'progress': e.progress_percent or 0,
                'enrollment_date': e.enrolled_at.isoformat() if e.enrolled_at else None,
                'is_active': e.status == 'active'
            })

        return jsonify({'enrollments': enrollments_list})
    except Exception as e:
        print(f"Get enrollments error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/enrollments', methods=['POST'])
@admin_dashboard_required
def enroll_student():
    """Enroll a student in a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User, Course, Enrollment
        from datetime import datetime

        data = request.get_json()
        student_id = data.get('student_id')
        course_id = data.get('course_id')

        if not student_id or not course_id:
            return jsonify({'error': 'Student ID and Course ID are required'}), 400

        student = User.query.get(student_id)
        if not student or student.role != 'student':
            return jsonify({'error': 'Student not found'}), 404

        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Check if already enrolled
        existing = Enrollment.query.filter_by(
            user_id=student_id,
            course_id=course_id
        ).first()

        if existing:
            return jsonify({'error': 'Student already enrolled in this course'}), 400

        enrollment = Enrollment(
            user_id=student_id,
            course_id=course_id,
            status='active',
            enrolled_at=datetime.utcnow()
        )

        db.add(enrollment)
        db.commit()

        return jsonify({
            'success': True,
            'message': 'Student enrolled successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Enroll student error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/enrollments/pending', methods=['GET'])
@admin_dashboard_required
def get_pending_enrollments():
    """Return all enrollments with status=pending."""
    try:
        from app.models import db as _db, Enrollment, User, Course
        rows = (
            _db.session.query(Enrollment, User, Course)
            .join(User,   User.id   == Enrollment.user_id)
            .join(Course, Course.id == Enrollment.course_id)
            .filter(Enrollment.status == 'pending')
            .order_by(Enrollment.enrolled_at.asc())
            .all()
        )
        result = []
        for enr, usr, crs in rows:
            result.append({
                'enrollment_id': enr.id,
                'student_id':    usr.id,
                'student_name':  usr.full_name or usr.username,
                'student_username': usr.username,
                'course_id':     crs.id,
                'course_title':  crs.title,
                'course_code':   crs.code or '',
                'enrolled_at':   enr.enrolled_at.strftime('%Y-%m-%d %H:%M') if enr.enrolled_at else '',
            })
        return jsonify({'pending': result, 'count': len(result)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/enrollments/<enrollment_id>/approve', methods=['POST'])
@admin_dashboard_required
def approve_enrollment(enrollment_id):
    """Approve a pending enrollment."""
    try:
        from app.models import db as _db, Enrollment, User, Course
        enr = Enrollment.query.get(enrollment_id)
        if not enr:
            return jsonify({'error': 'Enrollment not found'}), 404
        enr.status = 'approved'
        _db.session.commit()
        # In-app notification to student
        try:
            from app.services.notification_service import notify
            crs = Course.query.get(enr.course_id)
            notify(
                user_id=enr.user_id,
                kind='enrollment_approved',
                title='Registration Approved',
                body=f'Your registration for "{crs.title if crs else "the course"}" has been approved.',
                severity='success'
            )
        except Exception:
            pass
        return jsonify({'success': True, 'message': 'Enrollment approved'})
    except Exception as e:
        try:
            from app.models import db as _db2
            _db2.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/enrollments/<enrollment_id>/reject', methods=['POST'])
@admin_dashboard_required
def reject_enrollment(enrollment_id):
    """Reject (delete) a pending enrollment."""
    try:
        from app.models import db as _db, Enrollment, Course
        enr = Enrollment.query.get(enrollment_id)
        if not enr:
            return jsonify({'error': 'Enrollment not found'}), 404
        data = request.get_json() or {}
        reason = data.get('reason', '')
        # Notify student before deleting
        try:
            from app.services.notification_service import notify
            crs = Course.query.get(enr.course_id)
            msg = f'Your registration for "{crs.title if crs else "the course"}" was not approved.'
            if reason:
                msg += f' Reason: {reason}'
            notify(
                user_id=enr.user_id,
                kind='enrollment_rejected',
                title='Registration Not Approved',
                body=msg,
                severity='warning'
            )
        except Exception:
            pass
        _db.session.delete(enr)
        _db.session.commit()
        return jsonify({'success': True, 'message': 'Enrollment rejected'})
    except Exception as e:
        try:
            from app.models import db as _db2
            _db2.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/enrollments/<enrollment_id>', methods=['DELETE'])
@admin_dashboard_required
def unenroll_student(enrollment_id):
    """Remove student from a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Enrollment

        enrollment = Enrollment.query.get(enrollment_id)
        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404

        db.delete(enrollment)
        db.commit()

        return jsonify({
            'success': True,
            'message': 'Student unenrolled successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Unenroll student error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# SITE SETTINGS
# ============================================

@super_admin_bp.route('/api/site-settings', methods=['GET'])
@admin_dashboard_required
def get_site_settings():
    """Get site settings including landing page configuration"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import SiteSettings
        import json

        settings = SiteSettings.query.first()
        if not settings:
            return jsonify({
                'site_name': 'SkillPilot',
                'site_name_ar': '',
                'primary_color': '#2563eb',
                'secondary_color': '#1e40af',
                'hero_title': 'AI-Powered Training Platform',
                'hero_title_ar': '',
                'hero_subtitle': '',
                'hero_subtitle_ar': '',
                'hero_image_url': ''
            })

        # Parse JSON fields safely
        landing_sections = []
        features_content = []
        testimonials_content = []
        try:
            if settings.landing_sections:
                landing_sections = json.loads(settings.landing_sections)
            if hasattr(settings, 'features_content') and settings.features_content:
                features_content = json.loads(settings.features_content)
            if hasattr(settings, 'testimonials_content') and settings.testimonials_content:
                testimonials_content = json.loads(settings.testimonials_content)
        except json.JSONDecodeError:
            pass

        return jsonify({
            'id': str(settings.id),
            # Branding
            'site_name': settings.site_name or 'SkillPilot',
            'site_name_ar': settings.site_name_ar or '',
            'logo_url': settings.logo_url or '',
            'logo_url_2': getattr(settings, 'logo_url_2', '') or '',
            'favicon_url': settings.favicon_url or '',
            'primary_color': settings.primary_color or '#2563eb',
            'secondary_color': settings.secondary_color or '#1e40af',
            # Legacy tagline fields (map to hero_subtitle for backwards compatibility)
            'tagline': settings.hero_subtitle or 'AI-Powered Learning Platform',
            'tagline_ar': settings.hero_subtitle_ar or '',
            # Hero Section
            'hero_title': settings.hero_title or 'AI-Powered Training Platform',
            'hero_title_ar': settings.hero_title_ar or '',
            'hero_subtitle': settings.hero_subtitle or '',
            'hero_subtitle_ar': settings.hero_subtitle_ar or '',
            'hero_image_url': settings.hero_image_url or '',
            # About Section
            'about_title': getattr(settings, 'about_title', 'About Us') or 'About Us',
            'about_title_ar': getattr(settings, 'about_title_ar', '') or '',
            'about_content': getattr(settings, 'about_content', '') or '',
            'about_content_ar': getattr(settings, 'about_content_ar', '') or '',
            'about_image_url': getattr(settings, 'about_image_url', '') or '',
            # Features Section
            'features_title': getattr(settings, 'features_title', 'Our Features') or 'Our Features',
            'features_title_ar': getattr(settings, 'features_title_ar', '') or '',
            'features_content': features_content,
            # Courses Section
            'courses_section_title': getattr(settings, 'courses_section_title', 'Our Courses') or 'Our Courses',
            'courses_section_title_ar': getattr(settings, 'courses_section_title_ar', '') or '',
            'courses_section_enabled': getattr(settings, 'courses_section_enabled', True),
            # Testimonials Section
            'testimonials_title': getattr(settings, 'testimonials_title', 'What Our Students Say') or 'What Our Students Say',
            'testimonials_title_ar': getattr(settings, 'testimonials_title_ar', '') or '',
            'testimonials_content': testimonials_content,
            'testimonials_enabled': getattr(settings, 'testimonials_enabled', True),
            # CTA Section
            'cta_title': getattr(settings, 'cta_title', 'Start Your Learning Journey') or 'Start Your Learning Journey',
            'cta_title_ar': getattr(settings, 'cta_title_ar', '') or '',
            'cta_subtitle': getattr(settings, 'cta_subtitle', '') or '',
            'cta_subtitle_ar': getattr(settings, 'cta_subtitle_ar', '') or '',
            'cta_button_text': getattr(settings, 'cta_button_text', 'Get Started') or 'Get Started',
            'cta_button_text_ar': getattr(settings, 'cta_button_text_ar', '') or '',
            'cta_button_url': getattr(settings, 'cta_button_url', '') or '',
            # Footer
            'footer_text': settings.footer_text or '',
            'contact_email': settings.contact_email or '',
            # Landing sections (flexible JSON)
            'landing_sections': landing_sections,
            # Registration settings
            'allow_student_registration': settings.allow_student_registration if hasattr(settings, 'allow_student_registration') else True,
            'allow_teacher_registration': settings.allow_teacher_registration if hasattr(settings, 'allow_teacher_registration') else True,
            # Additional branding
            'logo_dark_url': getattr(settings, 'logo_dark_url', '') or '',
            'accent_color': getattr(settings, 'accent_color', '#4CAF50') or '#4CAF50',
            'header_bg_color': getattr(settings, 'header_bg_color', '#1B5E20') or '#1B5E20',
            # Contact Information
            'address': getattr(settings, 'address', '') or '',
            'address_ar': getattr(settings, 'address_ar', '') or '',
            'phone': getattr(settings, 'phone', '') or '',
            # Social Media Links
            'social_links': json.loads(getattr(settings, 'social_links', '{}') or '{}') if getattr(settings, 'social_links', None) else {},
            # Hero Buttons
            'hero_buttons': json.loads(getattr(settings, 'hero_buttons', '[]') or '[]') if getattr(settings, 'hero_buttons', None) else [],
            # Custom CSS
            'custom_css': getattr(settings, 'custom_css', '') or '',
            # Feature Toggles
            'attendance_tracking_enabled': getattr(settings, 'attendance_tracking_enabled', True)
        })
    except Exception as e:
        print(f"Get site settings error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/site-settings', methods=['POST', 'PUT'])
@admin_dashboard_required
def update_site_settings():
    """Update site settings including landing page configuration"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import SiteSettings
        import json

        data = request.get_json()
        settings = SiteSettings.query.first()

        if not settings:
            settings = SiteSettings()
            db.add(settings)

        # Branding fields
        if 'site_name' in data:
            settings.site_name = data['site_name']
        if 'site_name_ar' in data:
            settings.site_name_ar = data['site_name_ar']
        if 'primary_color' in data:
            settings.primary_color = data['primary_color']
        if 'secondary_color' in data:
            settings.secondary_color = data['secondary_color']
        if 'logo_url' in data:
            settings.logo_url = data['logo_url']
        if 'logo_url_2' in data:
            settings.logo_url_2 = data['logo_url_2']
        if 'favicon_url' in data:
            settings.favicon_url = data['favicon_url']

        # Legacy tagline support (map to hero_subtitle)
        if 'tagline' in data:
            settings.hero_subtitle = data['tagline']
        if 'tagline_ar' in data:
            settings.hero_subtitle_ar = data['tagline_ar']

        # Hero Section
        if 'hero_title' in data:
            settings.hero_title = data['hero_title']
        if 'hero_title_ar' in data:
            settings.hero_title_ar = data['hero_title_ar']
        if 'hero_subtitle' in data:
            settings.hero_subtitle = data['hero_subtitle']
        if 'hero_subtitle_ar' in data:
            settings.hero_subtitle_ar = data['hero_subtitle_ar']
        if 'hero_image_url' in data:
            settings.hero_image_url = data['hero_image_url']

        # About Section
        if 'about_title' in data:
            settings.about_title = data['about_title']
        if 'about_title_ar' in data:
            settings.about_title_ar = data['about_title_ar']
        if 'about_content' in data:
            settings.about_content = data['about_content']
        if 'about_content_ar' in data:
            settings.about_content_ar = data['about_content_ar']
        if 'about_image_url' in data:
            settings.about_image_url = data['about_image_url']

        # Features Section
        if 'features_title' in data:
            settings.features_title = data['features_title']
        if 'features_title_ar' in data:
            settings.features_title_ar = data['features_title_ar']
        if 'features_content' in data:
            settings.features_content = json.dumps(data['features_content']) if isinstance(data['features_content'], list) else data['features_content']

        # Courses Section
        if 'courses_section_title' in data:
            settings.courses_section_title = data['courses_section_title']
        if 'courses_section_title_ar' in data:
            settings.courses_section_title_ar = data['courses_section_title_ar']
        if 'courses_section_enabled' in data:
            settings.courses_section_enabled = data['courses_section_enabled']

        # Testimonials Section
        if 'testimonials_title' in data:
            settings.testimonials_title = data['testimonials_title']
        if 'testimonials_title_ar' in data:
            settings.testimonials_title_ar = data['testimonials_title_ar']
        if 'testimonials_content' in data:
            settings.testimonials_content = json.dumps(data['testimonials_content']) if isinstance(data['testimonials_content'], list) else data['testimonials_content']
        if 'testimonials_enabled' in data:
            settings.testimonials_enabled = data['testimonials_enabled']

        # CTA Section
        if 'cta_title' in data:
            settings.cta_title = data['cta_title']
        if 'cta_title_ar' in data:
            settings.cta_title_ar = data['cta_title_ar']
        if 'cta_subtitle' in data:
            settings.cta_subtitle = data['cta_subtitle']
        if 'cta_subtitle_ar' in data:
            settings.cta_subtitle_ar = data['cta_subtitle_ar']
        if 'cta_button_text' in data:
            settings.cta_button_text = data['cta_button_text']
        if 'cta_button_text_ar' in data:
            settings.cta_button_text_ar = data['cta_button_text_ar']
        if 'cta_button_url' in data:
            settings.cta_button_url = data['cta_button_url']

        # Footer
        if 'footer_text' in data:
            settings.footer_text = data['footer_text']
        if 'contact_email' in data:
            settings.contact_email = data['contact_email']

        # Landing sections (flexible JSON)
        if 'landing_sections' in data:
            settings.landing_sections = json.dumps(data['landing_sections']) if isinstance(data['landing_sections'], list) else data['landing_sections']

        # Registration settings
        if 'allow_student_registration' in data:
            settings.allow_student_registration = data['allow_student_registration']
        if 'allow_teacher_registration' in data:
            settings.allow_teacher_registration = data['allow_teacher_registration']
        
        # Additional branding fields
        if 'logo_dark_url' in data:
            settings.logo_dark_url = data['logo_dark_url']
        if 'accent_color' in data:
            settings.accent_color = data['accent_color']
        if 'header_bg_color' in data:
            settings.header_bg_color = data['header_bg_color']
        
        # Contact Information
        if 'address' in data:
            settings.address = data['address']
        if 'address_ar' in data:
            settings.address_ar = data['address_ar']
        if 'phone' in data:
            settings.phone = data['phone']
        
        # Social Media Links
        if 'social_links' in data:
            settings.social_links = json.dumps(data['social_links']) if isinstance(data['social_links'], dict) else data['social_links']
        
        # Hero Buttons
        if 'hero_buttons' in data:
            settings.hero_buttons = json.dumps(data['hero_buttons']) if isinstance(data['hero_buttons'], list) else data['hero_buttons']
        
        # Custom CSS
        if 'custom_css' in data:
            settings.custom_css = data['custom_css']

        # Feature Toggles
        if 'attendance_tracking_enabled' in data:
            settings.attendance_tracking_enabled = bool(data['attendance_tracking_enabled'])

        db.commit()

        return jsonify({
            'success': True,
            'message': 'Site settings updated successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Update site settings error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# APP FREEZE/MAINTENANCE MODE
# ============================================

@super_admin_bp.route('/api/app-status', methods=['GET'])
@super_admin_required
def get_app_status():
    """Get current app freeze status"""
    try:
        from app.models import SiteSettings
        settings = SiteSettings.query.first()
        
        return jsonify({
            'app_frozen': settings.app_frozen if settings else False,
            'freeze_message': settings.freeze_message if settings else '',
            'freeze_message_ar': settings.freeze_message_ar if settings else '',
            'frozen_at': settings.frozen_at.isoformat() if settings and settings.frozen_at else None,
            'frozen_by': settings.frozen_by if settings else None
        })
    except Exception as e:
        print(f"Get app status error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/app-freeze', methods=['POST'])
@super_admin_required
def freeze_app():
    """Freeze the application - block all user access except superadmin"""
    from datetime import datetime
    
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import SiteSettings
        data = request.get_json() or {}
        
        settings = SiteSettings.query.first()
        if not settings:
            settings = SiteSettings()
            db.add(settings)
        
        settings.app_frozen = True
        settings.freeze_message = data.get('message', 'The platform is currently under maintenance. Please try again later.')
        settings.freeze_message_ar = data.get('message_ar', 'المنصة حالياً تحت الصيانة. يرجى المحاولة لاحقاً.')
        settings.frozen_at = datetime.utcnow()
        settings.frozen_by = session.get('username', 'superadmin')
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Application has been frozen. Only superadmins can access the platform.',
            'frozen_at': settings.frozen_at.isoformat()
        })
    except Exception as e:
        db.rollback()
        print(f"Freeze app error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/app-restore', methods=['POST'])
@super_admin_required
def restore_app():
    """Restore the application - allow normal user access"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import SiteSettings
        
        settings = SiteSettings.query.first()
        if not settings:
            return jsonify({'error': 'Site settings not found'}), 404
        
        settings.app_frozen = False
        settings.frozen_at = None
        settings.frozen_by = None
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Application has been restored. Users can now access the platform.'
        })
    except Exception as e:
        db.rollback()
        print(f"Restore app error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# AI CONFIGURATION
# ============================================

@super_admin_bp.route('/api/ai-config', methods=['GET'])
@super_admin_required
def get_ai_config():
    """Get AI provider configuration status - checks both env vars and database"""
    import os
    from app.models import ApiCredential
    from app.utils.encryption import decrypt_api_key, mask_api_key

    # AI provider entries are built from the model registry so this screen can
    # never offer a model the platform cannot call. Non-AI integrations are
    # listed explicitly because they have no model catalogue.
    from app.services import model_registry as registry

    providers = []
    for key in ('openai', 'claude', 'gemini', 'perplexity', 'grok', 'deepseek', 'images'):
        spec = registry.get_provider(key)
        if spec is None:
            continue
        # The environment variable name comes from ApiCredential.PROVIDERS,
        # which is what the rest of the credential system reads and writes.
        credential = ApiCredential.PROVIDERS.get(key, {})
        providers.append({
            'id': spec.key,
            'name': credential.get('name') or spec.label,
            'key': credential.get('env_var') or (spec.env_vars[0] if spec.env_vars else ''),
            'category': 'image' if key == 'images' else 'ai',
            'models': [m['id'] for m in registry.available_models(key)],
            'default_model': registry.default_model(key),
            'description': credential.get('description', ''),
        })

    providers.extend([
        {'id': 'heygen', 'name': 'HeyGen', 'key': 'HEYGEN_API_KEY', 'category': 'video',
         'models': ['avatar.video.v2'], 'description': 'AI avatar video generation'},
        {'id': 'bedrock', 'name': 'AWS Bedrock', 'key': 'BEDROCK_API_KEY', 'category': 'ai',
         'models': [m['id'] for m in registry.available_models('bedrock')],
         'default_model': registry.default_model('bedrock'),
         'description': 'Combined credential format: access_key|secret_key|region'},
        {'id': 'paypal', 'name': 'PayPal', 'key': 'PAYPAL_CLIENT_ID', 'category': 'payment',
         'models': ['orders.v2'],
         'description': 'Payments. Combined format: client_id|client_secret|mode (sandbox|live)'},
    ])

    config = []
    for provider in providers:
        env_key = os.environ.get(provider['key'], '')
        has_env_key = bool(env_key)
        
        db_credential = ApiCredential.query.filter_by(provider=provider['id']).first()
        db_key = None
        has_db_key = False
        if db_credential and db_credential.encrypted_key:
            try:
                db_key = decrypt_api_key(db_credential.encrypted_key)
                has_db_key = bool(db_key)
            except Exception:
                has_db_key = False
        
        effective_key = env_key if has_env_key else (db_key if has_db_key else '')
        has_key = bool(effective_key)
        source = 'env' if has_env_key else ('database' if has_db_key else 'none')
        
        config.append({
            'id': provider['id'],
            'name': provider['name'],
            'env_key': provider['key'],
            'category': provider.get('category', 'ai'),
            'configured': has_key,
            'source': source,
            'key_preview': mask_api_key(effective_key) if has_key else '',
            'models': provider['models'],
            'description': provider['description'],
            'is_active': db_credential.is_active if db_credential else True
        })

    return jsonify({'providers': config})


@super_admin_bp.route('/api/ai-credentials', methods=['POST'])
@super_admin_required
def save_ai_credential():
    """Save or update an AI provider API key"""
    from app.models import ApiCredential, db
    from app.utils.encryption import encrypt_api_key
    
    data = request.get_json()
    provider_id = data.get('provider')
    api_key = data.get('api_key', '').strip()
    
    if not provider_id:
        return jsonify({'error': 'Provider is required'}), 400
    
    if provider_id not in ApiCredential.PROVIDERS:
        return jsonify({'error': 'Invalid provider'}), 400
    
    try:
        credential = ApiCredential.query.filter_by(provider=provider_id).first()
        
        if not credential:
            credential = ApiCredential(provider=provider_id)
            db.add(credential)
        
        if api_key:
            credential.encrypted_key = encrypt_api_key(api_key)
        
        credential.is_active = data.get('is_active', True)
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'{ApiCredential.PROVIDERS[provider_id]["name"]} API key saved successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Save AI credential error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/ai-credentials/<provider_id>', methods=['DELETE'])
@super_admin_required
def delete_ai_credential(provider_id):
    """Delete an AI provider API key from database"""
    from app.models import ApiCredential, db
    
    if provider_id not in ApiCredential.PROVIDERS:
        return jsonify({'error': 'Invalid provider'}), 400
    
    try:
        credential = ApiCredential.query.filter_by(provider=provider_id).first()
        
        if credential:
            db.delete(credential)
            db.commit()
            return jsonify({
                'success': True,
                'message': f'{ApiCredential.PROVIDERS[provider_id]["name"]} API key deleted'
            })
        else:
            return jsonify({'error': 'Credential not found'}), 404
    except Exception as e:
        db.rollback()
        print(f"Delete AI credential error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/test-all-apis', methods=['POST'])
@super_admin_required
def test_all_apis():
    """Test all configured AI provider API keys with a simple prompt"""
    import os
    import time
    import requests as http_requests
    from app.utils.api_key_helper import get_api_key

    test_prompt = "Say hello in one sentence."
    results = []

    provider_tests = [
        {
            'id': 'openai',
            'name': 'OpenAI',
            'model': 'gpt-4.1',
            'test_fn': lambda key: _test_openai(key, test_prompt, http_requests)
        },
        {
            'id': 'claude',
            'name': 'Claude',
            'model': 'claude-sonnet-4-20250514',
            'test_fn': lambda key: _test_claude(key, test_prompt)
        },
        {
            'id': 'gemini',
            'name': 'Gemini',
            'model': 'gemini-2.5-flash',
            'test_fn': lambda key: _test_gemini(key, test_prompt)
        },
        {
            'id': 'perplexity',
            'name': 'Perplexity',
            'model': 'sonar',
            'test_fn': lambda key: _test_perplexity(key, test_prompt, http_requests)
        },
        {
            'id': 'grok',
            'name': 'Grok',
            'model': 'grok-3-mini',
            'test_fn': lambda key: _test_grok(key, test_prompt, http_requests)
        },
        {
            'id': 'deepseek',
            'name': 'DeepSeek',
            'model': 'deepseek-chat',
            'test_fn': lambda key: _test_deepseek(key, test_prompt, http_requests)
        }
    ]

    for provider in provider_tests:
        api_key = get_api_key(provider['id'])
        if not api_key:
            results.append({
                'id': provider['id'],
                'name': provider['name'],
                'model': provider['model'],
                'status': 'skipped',
                'message': 'No API key configured',
                'response_time': 0
            })
            continue

        start_time = time.time()
        try:
            test_result = provider['test_fn'](api_key)
            elapsed = round(time.time() - start_time, 2)
            results.append({
                'id': provider['id'],
                'name': provider['name'],
                'model': provider['model'],
                'status': 'success' if test_result.get('success') else 'error',
                'message': test_result.get('message', ''),
                'response_time': elapsed
            })
        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            results.append({
                'id': provider['id'],
                'name': provider['name'],
                'model': provider['model'],
                'status': 'error',
                'message': str(e)[:200],
                'response_time': elapsed
            })

    success_count = sum(1 for r in results if r['status'] == 'success')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    error_count = sum(1 for r in results if r['status'] == 'error')

    return jsonify({
        'results': results,
        'summary': {
            'total': len(results),
            'success': success_count,
            'skipped': skipped_count,
            'error': error_count
        }
    })


def _test_openai(api_key, prompt, http_requests):
    response = http_requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={'model': 'gpt-4.1', 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 50},
        timeout=30
    )
    if response.status_code == 200:
        text = response.json()['choices'][0]['message']['content']
        return {'success': True, 'message': text[:100]}
    else:
        return {'success': False, 'message': f'HTTP {response.status_code}: {response.text[:150]}'}


def _test_claude(api_key, prompt):
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )
        return {'success': True, 'message': response.content[0].text[:100]}
    except Exception as e:
        return {'success': False, 'message': str(e)[:150]}


def _test_gemini(api_key, prompt):
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return {'success': True, 'message': response.text[:100]}
    except Exception as e:
        return {'success': False, 'message': str(e)[:150]}


def _test_perplexity(api_key, prompt, http_requests):
    response = http_requests.post(
        'https://api.perplexity.ai/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={'model': 'sonar', 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 50},
        timeout=30
    )
    if response.status_code == 200:
        text = response.json()['choices'][0]['message']['content']
        return {'success': True, 'message': text[:100]}
    else:
        return {'success': False, 'message': f'HTTP {response.status_code}: {response.text[:150]}'}


def _test_grok(api_key, prompt, http_requests):
    response = http_requests.post(
        'https://api.x.ai/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={'model': 'grok-3-mini', 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 50},
        timeout=30
    )
    if response.status_code == 200:
        text = response.json()['choices'][0]['message']['content']
        return {'success': True, 'message': text[:100]}
    else:
        return {'success': False, 'message': f'HTTP {response.status_code}: {response.text[:150]}'}


def _test_heygen(api_key, http_requests):
    response = http_requests.get(
        'https://api.heygen.com/v2/avatars',
        headers={'X-Api-Key': api_key, 'Accept': 'application/json'},
        timeout=20,
    )
    if response.status_code == 200:
        try:
            data = response.json()
            count = len(((data or {}).get('data') or {}).get('avatars') or [])
            return {'success': True, 'message': f'Authenticated. {count} avatars available.'}
        except Exception:
            return {'success': True, 'message': 'Authenticated.'}
    return {'success': False, 'message': f'HTTP {response.status_code}: {response.text[:150]}'}


def _test_bedrock(api_key):
    """api_key is expected as access_key|secret_key|region (region defaults to us-east-1)."""
    try:
        parts = (api_key or '').split('|')
        if len(parts) < 2:
            return {'success': False, 'message': 'Format must be access_key|secret_key|region'}
        access_key = parts[0].strip()
        secret_key = parts[1].strip()
        region = parts[2].strip() if len(parts) > 2 and parts[2].strip() else 'us-east-1'
        try:
            import boto3  # type: ignore
        except ImportError:
            return {'success': False, 'message': 'boto3 not installed in environment'}
        client = boto3.client(
            'bedrock',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        resp = client.list_foundation_models()
        models = resp.get('modelSummaries') or []
        return {'success': True, 'message': f'Authenticated to {region}. {len(models)} models available.'}
    except Exception as e:
        return {'success': False, 'message': str(e)[:200]}


def _test_paypal(api_key, http_requests):
    """api_key is expected as client_id|client_secret|mode (sandbox|live)."""
    try:
        parts = (api_key or '').split('|')
        if len(parts) < 2:
            return {'success': False, 'message': 'Format must be client_id|client_secret|mode'}
        client_id = parts[0].strip()
        client_secret = parts[1].strip()
        mode = (parts[2].strip().lower() if len(parts) > 2 and parts[2].strip() else 'sandbox')
        base = 'https://api-m.sandbox.paypal.com' if mode != 'live' else 'https://api-m.paypal.com'
        resp = http_requests.post(
            f'{base}/v1/oauth2/token',
            auth=(client_id, client_secret),
            data={'grant_type': 'client_credentials'},
            headers={'Accept': 'application/json'},
            timeout=20,
        )
        if resp.status_code == 200 and resp.json().get('access_token'):
            return {'success': True, 'message': f'Authenticated to PayPal {mode}.'}
        return {'success': False, 'message': f'HTTP {resp.status_code}: {resp.text[:150]}'}
    except Exception as e:
        return {'success': False, 'message': str(e)[:200]}


@super_admin_bp.route('/api/test-api-key', methods=['POST'])
@super_admin_required
def test_single_api_key():
    """Test a single provider's API key.
    Body: {provider, api_key?}. If api_key omitted, uses the saved (env or db) key."""
    import time
    import requests as http_requests
    from app.utils.api_key_helper import get_api_key as _get_saved
    from app.models import ApiCredential

    data = request.get_json(silent=True) or {}
    provider = (data.get('provider') or '').strip()
    candidate_key = (data.get('api_key') or '').strip()

    if provider not in ApiCredential.PROVIDERS:
        return jsonify({'success': False, 'message': 'Unknown provider'}), 400

    api_key = candidate_key or _get_saved(provider) or ''
    if not api_key:
        return jsonify({'success': False, 'message': 'No API key provided or saved.'}), 400

    test_prompt = "Say hello in one sentence."
    start = time.time()
    try:
        if provider == 'openai':
            result = _test_openai(api_key, test_prompt, http_requests)
        elif provider == 'claude':
            result = _test_claude(api_key, test_prompt)
        elif provider == 'gemini':
            result = _test_gemini(api_key, test_prompt)
        elif provider == 'perplexity':
            result = _test_perplexity(api_key, test_prompt, http_requests)
        elif provider == 'grok':
            result = _test_grok(api_key, test_prompt, http_requests)
        elif provider == 'deepseek':
            result = _test_deepseek(api_key, test_prompt, http_requests)
        elif provider == 'heygen':
            result = _test_heygen(api_key, http_requests)
        elif provider == 'bedrock':
            result = _test_bedrock(api_key)
        elif provider == 'paypal':
            result = _test_paypal(api_key, http_requests)
        else:
            return jsonify({'success': False, 'message': 'No tester for this provider'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)[:200], 'response_time': round(time.time() - start, 2)})

    return jsonify({
        'success': bool(result.get('success')),
        'message': result.get('message', ''),
        'response_time': round(time.time() - start, 2),
        'used_source': 'provided' if candidate_key else 'saved',
    })


@super_admin_bp.route('/integrations', methods=['GET'])
@super_admin_required
def integrations_page():
    return render_template('admin_integrations.html')


def _test_deepseek(api_key, prompt, http_requests):
    response = http_requests.post(
        'https://api.deepseek.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={'model': 'deepseek-chat', 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 50},
        timeout=30
    )
    if response.status_code == 200:
        text = response.json()['choices'][0]['message']['content']
        return {'success': True, 'message': text[:100]}
    else:
        return {'success': False, 'message': f'HTTP {response.status_code}: {response.text[:150]}'}


# ============================================
# BULK CERTIFICATE GENERATION
# ============================================

@super_admin_bp.route('/api/certificates/eligible', methods=['GET'])
@super_admin_required
def get_eligible_certificates():
    """Get all enrollments eligible for certificate generation"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User, Course, Enrollment, Exam, ExamResult
        from sqlalchemy import or_

        # Get enrollments with 100% progress or completed status that haven't received certificates
        enrollments = Enrollment.query.filter(
            or_(Enrollment.progress_percent >= 100, Enrollment.status == 'completed'),
            Enrollment.certificate_issued == False
        ).all()

        eligible = []
        for enrollment in enrollments:
            student = User.query.filter_by(id=enrollment.user_id).first()
            course = Course.query.filter_by(id=enrollment.course_id).first()
            
            if not student or not course:
                continue
            
            exams = Exam.query.filter_by(course_id=enrollment.course_id).all()
            exam_ids = [e.id for e in exams]
            exam_results = ExamResult.query.filter(
                ExamResult.user_id == enrollment.user_id,
                ExamResult.exam_id.in_(exam_ids)
            ).all() if exam_ids else []
            
            avg_score = sum(r.score or 0 for r in exam_results) / len(exam_results) if exam_results else 0
            
            eligible.append({
                'enrollment_id': str(enrollment.id),
                'student_name': student.full_name or student.username,
                'student_email': student.email,
                'course_title': course.title,
                'course_code': course.code,
                'avg_score': round(avg_score, 1),
                'completed_at': enrollment.completed_at.isoformat() if hasattr(enrollment, 'completed_at') and enrollment.completed_at else None
            })

        return jsonify({
            'eligible': eligible,
            'total': len(eligible)
        })
    except Exception as e:
        print(f"Get eligible certificates error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/certificates/bulk-generate', methods=['POST'])
@super_admin_required
def bulk_generate_certificates():
    """Generate certificates for multiple enrollments"""
    from datetime import datetime
    
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    data = request.get_json()
    enrollment_ids = data.get('enrollment_ids', [])
    
    if not enrollment_ids:
        return jsonify({'error': 'No enrollment IDs provided'}), 400

    try:
        from app.models import Enrollment

        success_count = 0
        failed_count = 0
        results = []

        for enrollment_id in enrollment_ids:
            try:
                enrollment = Enrollment.query.filter_by(id=enrollment_id).first()
                if not enrollment:
                    failed_count += 1
                    results.append({'id': enrollment_id, 'status': 'failed', 'reason': 'Not found'})
                    continue
                
                if enrollment.certificate_issued:
                    results.append({'id': enrollment_id, 'status': 'skipped', 'reason': 'Already issued'})
                    continue
                
                enrollment.certificate_issued = True
                enrollment.certificate_issued_at = datetime.utcnow()
                enrollment.certificate_status = 'issued'
                
                success_count += 1
                results.append({'id': enrollment_id, 'status': 'success'})
            except Exception as e:
                failed_count += 1
                results.append({'id': enrollment_id, 'status': 'failed', 'reason': str(e)})

        db.commit()

        return jsonify({
            'success': True,
            'message': f'Generated {success_count} certificates',
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        })
    except Exception as e:
        db.rollback()
        print(f"Bulk generate certificates error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/certificates/csv-template', methods=['GET'])
@super_admin_required
def download_csv_template():
    """Download CSV template for bulk certificate generation"""
    import io
    import csv
    from flask import Response
    
    output = io.StringIO()
    # UTF-8 BOM so Excel opens Arabic correctly
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(['name', 'email', 'course_title', 'completion_date', 'language', 'grade'])
    # English class-less example
    writer.writerow(['John Smith', 'john@example.com', 'Introduction to AI', '2026-05-01', 'en', '92'])
    # Mixed case
    writer.writerow(['Jane Doe', 'jane@example.com', 'Data Science Fundamentals', '2026-05-01', 'en', '88'])
    # Arabic example — name, course title and language all in Arabic
    writer.writerow(['أحمد الراشد', 'ahmed@example.com', 'مقدمة في الذكاء الاصطناعي', '2026-05-01', 'ar', '95'])

    output.seek(0)
    return Response(
        output.getvalue().encode('utf-8'),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=certificate_template.csv'}
    )


@super_admin_bp.route('/api/certificates/csv-generate', methods=['POST'])
@super_admin_required
def csv_bulk_generate_certificates():
    """Generate certificates from a CSV file.

    Two modes:
      - **Class mode** — caller supplies a `course_id` form field; every CSV row
        becomes (or is matched to) an enrollment in that course and the
        certificate is registered in the database (verifiable via QR).
      - **No-class mode** — `course_id` is empty.  Each row's `course_title`
        is used directly; PDFs are still generated and zipped, but they are
        NOT stored in the database.  These stand-alone PDFs are for offline
        / printable use only — the QR code on them will not resolve through
        the /verify/ endpoint because no enrollment record exists.

    Per-row CSV columns (all optional except `name`):
      name, email, course_title, completion_date (YYYY-MM-DD), language (en|ar), grade
    """
    from datetime import datetime
    import csv
    import io
    import uuid
    import hashlib
    import zipfile
    from flask import send_file

    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    file = request.files.get('file') or request.files.get('csv_file')
    course_id = (request.form.get('course_id') or '').strip()
    fallback_issue_date_str = (request.form.get('issue_date') or '').strip()
    fallback_language = (request.form.get('language') or 'en').strip().lower()

    if not file or file.filename == '':
        return jsonify({'error': 'No CSV file uploaded'}), 400

    try:
        from app.models import User, Course, Enrollment

        # Class mode requires a real course
        course = None
        class_mode = bool(course_id)
        if class_mode:
            course = Course.query.filter_by(id=course_id).first()
            if not course:
                return jsonify({'error': 'Course not found'}), 404

        # Fallback issue date for rows that don't supply their own
        if fallback_issue_date_str:
            try:
                fallback_issue_date = datetime.strptime(fallback_issue_date_str, '%Y-%m-%d')
            except ValueError:
                fallback_issue_date = datetime.utcnow()
        else:
            fallback_issue_date = datetime.utcnow()

        # Read CSV — strip UTF-8 BOM if present
        raw = file.stream.read()
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('utf-8', errors='replace')
        reader = csv.DictReader(io.StringIO(text, newline=None))

        # Helper to find a column by any of several aliases (case-insensitive)
        def _col(field_aliases):
            for alias in field_aliases:
                for fn in (reader.fieldnames or []):
                    if fn and fn.strip().lower() == alias.lower():
                        return fn
            return None

        name_col   = _col(['name', 'student_name', 'full_name'])
        email_col  = _col(['email', 'student_email'])
        course_col = _col(['course_title', 'course', 'course_name'])
        date_col   = _col(['completion_date', 'issue_date', 'date'])
        lang_col   = _col(['language', 'lang'])
        grade_col  = _col(['grade', 'score', 'final_grade'])

        if not name_col:
            return jsonify({'error': 'CSV must have a column named "name", "student_name", or "full_name"'}), 400

        if not class_mode and not course_col:
            return jsonify({'error': 'No-class mode requires a "course_title" column in the CSV (or pick a class above)'}), 400

        results = []
        success_count = 0
        new_student_count = 0
        already_issued_count = 0
        # Each entry: dict(name, course, language, issue_date, grade, enrollment_id|None, pdf_bytes)
        renderable = []

        for row in reader:
            student_name = (row.get(name_col) or '').strip()
            if not student_name:
                continue

            student_email = (row.get(email_col) or '').strip() if email_col else None
            row_course_title = (row.get(course_col) or '').strip() if course_col else ''
            row_date_str     = (row.get(date_col) or '').strip() if date_col else ''
            row_language     = (row.get(lang_col) or '').strip().lower() if lang_col else ''
            row_grade        = (row.get(grade_col) or '').strip() if grade_col else ''

            language = row_language or fallback_language or 'en'
            if language not in ('en', 'ar'):
                language = 'en'
            # Auto-promote to Arabic if no explicit per-row language was set
            # and the name, the row course title, OR the registered class title
            # obviously contains Arabic script — otherwise the cert would
            # render those fields as empty boxes.
            db_course_title = (course.title if (class_mode and course) else '') or ''
            if not row_language and (_contains_arabic(student_name)
                                     or _contains_arabic(row_course_title)
                                     or _contains_arabic(db_course_title)):
                language = 'ar'

            if row_date_str:
                try:
                    issue_date = datetime.strptime(row_date_str, '%Y-%m-%d')
                except ValueError:
                    issue_date = fallback_issue_date
            else:
                issue_date = fallback_issue_date

            try:
                grade_val = float(row_grade) if row_grade else None
            except ValueError:
                grade_val = None

            # ----- Class mode: register in DB -----
            if class_mode:
                effective_course_title = course.title or course.code or 'Training Program'

                from sqlalchemy import func
                student = db.query(User).filter(
                    func.lower(User.full_name) == func.lower(student_name)
                ).first()

                if not student:
                    base_username = student_name.lower().replace(' ', '_').replace("'", '')[:20] or 'user'
                    username = base_username
                    counter = 1
                    while User.query.filter_by(username=username).first():
                        username = f"{base_username}_{counter}"
                        counter += 1
                    student = User(
                        id=str(uuid.uuid4()),
                        username=username,
                        password_hash=hashlib.sha256(username.encode()).hexdigest(),
                        full_name=student_name,
                        email=student_email or f"{username}@generated.local",
                        role='student',
                        is_active=True,
                    )
                    db.add(student)
                    db.flush()
                    new_student_count += 1

                enrollment = Enrollment.query.filter_by(
                    user_id=student.id, course_id=course_id
                ).first()
                if not enrollment:
                    enrollment = Enrollment(
                        id=str(uuid.uuid4()),
                        user_id=student.id,
                        course_id=course_id,
                        status='completed',
                        progress_percent=100.0,
                    )
                    db.add(enrollment)
                    db.flush()

                was_already_issued = bool(enrollment.certificate_issued)
                if was_already_issued:
                    already_issued_count += 1
                    results.append({'name': student_name, 'status': 'existing',
                                    'reason': 'Certificate already issued',
                                    'enrollment_id': str(enrollment.id)})
                else:
                    enrollment.certificate_issued = True
                    enrollment.certificate_issued_at = issue_date
                    enrollment.certificate_status = 'issued'
                    enrollment.status = 'completed'
                    enrollment.progress_percent = 100.0
                    if grade_val is not None:
                        enrollment.final_grade = grade_val
                    success_count += 1
                    results.append({'name': student_name, 'status': 'success',
                                    'student_id': str(student.id),
                                    'enrollment_id': str(enrollment.id)})

                renderable.append({
                    'enrollment_id': str(enrollment.id),
                    'student_name': student_name,
                    'course_title': row_course_title or effective_course_title,
                    'issue_date': issue_date,
                    'language': language,
                    'grade': grade_val,
                })

            # ----- No-class mode: render PDFs only, no DB writes -----
            else:
                success_count += 1
                results.append({'name': student_name, 'status': 'success',
                                'mode': 'no_class', 'course_title': row_course_title})
                renderable.append({
                    'enrollment_id': None,
                    'student_name': student_name,
                    'course_title': row_course_title,
                    'issue_date': issue_date,
                    'language': language,
                    'grade': grade_val,
                })

        if class_mode:
            db.commit()

        if not renderable:
            return jsonify({
                'success': True,
                'message': 'No certificates to generate',
                'success_count': 0,
                'new_student_count': new_student_count,
                'already_issued_count': already_issued_count,
                'results': results,
            })

        # ---- Render PDFs into a ZIP ----
        zip_buffer = io.BytesIO()
        used_filenames = {}

        from app.models import IssuedCertificate
        registry_to_add = []  # collect once, commit once at the end
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for item in renderable:
                try:
                    if item['enrollment_id']:
                        enrollment = Enrollment.query.filter_by(id=item['enrollment_id']).first()
                        student    = User.query.filter_by(id=enrollment.user_id).first()
                        course_obj = Course.query.filter_by(id=enrollment.course_id).first()
                        pdf_buffer = generate_certificate_pdf(enrollment, student, course_obj,
                                                              language=item['language'])
                        cert_number = f"CERT-{str(enrollment.id)[:8].upper()}"
                    else:
                        cert_number = f"CERT-{uuid.uuid4().hex[:8].upper()}"
                        pdf_buffer = _render_certificate_pdf(
                            student_name=item['student_name'],
                            course_title=item['course_title'],
                            issue_date=item['issue_date'],
                            cert_number=cert_number,
                            final_grade=item['grade'],
                            language=item['language'],
                        )

                    # Stage registry row — one DB commit at the end (NOT per row)
                    registry_to_add.append(dict(
                        cert_number=cert_number,
                        student_name=item['student_name'],
                        course_title=item.get('course_title'),
                        issued_at=item.get('issue_date') or datetime.utcnow(),
                        final_grade=item.get('grade'),
                        language=item.get('language') or 'en',
                        enrollment_id=item.get('enrollment_id'),
                    ))

                    safe_name   = ''.join(c for c in item['student_name'] if c.isalnum() or c in ' -_').strip() or 'Student'
                    safe_course = ''.join(c for c in (item['course_title'] or 'Course') if c.isalnum() or c in ' -_').strip()[:30] or 'Course'
                    base_filename = f"Certificate_{safe_name}_{safe_course}"
                    if base_filename in used_filenames:
                        used_filenames[base_filename] += 1
                        filename = f"{base_filename}_{used_filenames[base_filename]}.pdf"
                    else:
                        used_filenames[base_filename] = 1
                        filename = f"{base_filename}.pdf"
                    zip_file.writestr(filename, pdf_buffer.read())
                except Exception as e:
                    print(f"Error generating certificate for {item.get('student_name')}: {e}")
                    continue

        # Single bulk commit for all registry rows (idempotent + fail-soft).
        if registry_to_add:
            try:
                existing_nums = {row[0] for row in db.query(IssuedCertificate.cert_number)
                                 .filter(IssuedCertificate.cert_number.in_(
                                     [r['cert_number'] for r in registry_to_add])).all()}
                for r in registry_to_add:
                    if r['cert_number'] not in existing_nums:
                        db.add(IssuedCertificate(**r))
                db.commit()
            except Exception as _reg_err:
                db.rollback()
                print(f"[bulk-cert] registry bulk insert failed: {_reg_err}")

        zip_buffer.seek(0)
        if class_mode:
            label_part = course.title or course.code or 'Course'
        else:
            label_part = 'Standalone'
        zip_label = ''.join(c for c in label_part if c.isalnum() or c in ' -_').strip()[:30] or 'Certificates'
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"Certificates_{zip_label}_{timestamp}.zip",
        )

    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"CSV bulk generate certificates error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/certificates/all', methods=['GET'])
@admin_dashboard_required
def get_all_certificates():
    """Get all issued certificates"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User, Course, Enrollment

        enrollments = Enrollment.query.filter(
            Enrollment.certificate_issued == True
        ).order_by(Enrollment.certificate_issued_at.desc()).all()

        certificates = []
        for enrollment in enrollments:
            student = User.query.filter_by(id=enrollment.user_id).first()
            course = Course.query.filter_by(id=enrollment.course_id).first()
            
            if not student or not course:
                continue
            
            cert_number = f"CERT-{str(enrollment.id)[:8].upper()}"
            
            certificates.append({
                'enrollment_id': str(enrollment.id),
                'certificate_number': cert_number,
                'student_name': student.full_name or student.username,
                'student_email': student.email,
                'course_title': course.title,
                'course_code': course.code,
                'issued_at': enrollment.certificate_issued_at.isoformat() if enrollment.certificate_issued_at else None,
                'status': enrollment.certificate_status or 'issued'
            })

        return jsonify({
            'certificates': certificates,
            'total': len(certificates)
        })
    except Exception as e:
        print(f"Get all certificates error: {e}")
        return jsonify({'error': str(e)}), 500


_ARABIC_FONT_REGISTERED = False

def _ensure_arabic_font():
    """Register Amiri Arabic font with reportlab on first use."""
    global _ARABIC_FONT_REGISTERED
    if _ARABIC_FONT_REGISTERED:
        return True
    try:
        import os
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        reg = os.path.join(base, 'static', 'fonts', 'Amiri-Regular.ttf')
        bold = os.path.join(base, 'static', 'fonts', 'Amiri-Bold.ttf')
        if not os.path.exists(reg):
            print(f"[certificates] !! Amiri-Regular.ttf MISSING at {reg}. "
                  f"Arabic certificates will fall back to Helvetica which does not "
                  f"render Arabic glyphs. Re-extract the patch archive on the server.")
            return False
        pdfmetrics.registerFont(TTFont('Amiri', reg))
        if os.path.exists(bold):
            pdfmetrics.registerFont(TTFont('Amiri-Bold', bold))
        else:
            pdfmetrics.registerFont(TTFont('Amiri-Bold', reg))
        _ARABIC_FONT_REGISTERED = True
        print("[certificates] Amiri Arabic fonts registered with ReportLab")
        return True
    except Exception as e:
        print(f"[certificates] !! Arabic font registration failed: {e!r}")
        return False


_ARABIC_SHAPER_OK = None
_ARABIC_SHAPER_ERROR = None

def _ar(text):
    """Shape an Arabic string for correct RTL display in PDFs.

    Logs loudly the first time shaping fails so a missing
    arabic-reshaper / python-bidi install on the server is obvious in
    the log instead of silently producing disconnected letters.
    """
    global _ARABIC_SHAPER_OK, _ARABIC_SHAPER_ERROR
    if text is None:
        return ''
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        result = get_display(arabic_reshaper.reshape(str(text)))
        if _ARABIC_SHAPER_OK is None:
            _ARABIC_SHAPER_OK = True
            print("[certificates] Arabic shaping OK (arabic-reshaper + python-bidi loaded)")
        return result
    except Exception as e:
        if _ARABIC_SHAPER_OK is not False:
            _ARABIC_SHAPER_OK = False
            _ARABIC_SHAPER_ERROR = str(e)
            print(f"[certificates] !! Arabic shaping DISABLED: {e!r}. "
                  f"Install with: pip install 'arabic-reshaper>=3.0.0' 'python-bidi==0.4.2'. "
                  f"Letters will render disconnected until this is fixed.")
        return str(text)


@super_admin_bp.route('/api/certificates/arabic-health', methods=['GET'])
@admin_dashboard_required
def certificates_arabic_health():
    """Quick diagnostic: is the server able to render Arabic certificates?"""
    import os
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    reg = os.path.join(base, 'static', 'fonts', 'Amiri-Regular.ttf')
    bold = os.path.join(base, 'static', 'fonts', 'Amiri-Bold.ttf')
    out = {
        'amiri_regular_present': os.path.exists(reg),
        'amiri_bold_present': os.path.exists(bold),
        'arabic_reshaper': False,
        'python_bidi': False,
        'shaping_test': None,
        'shaping_test_ok': False,
    }
    try:
        import arabic_reshaper
        out['arabic_reshaper'] = True
        out['arabic_reshaper_version'] = getattr(arabic_reshaper, '__version__', 'unknown')
    except Exception as e:
        out['arabic_reshaper_error'] = str(e)
    try:
        import bidi
        out['python_bidi'] = True
        out['python_bidi_version'] = getattr(bidi, '__version__', 'unknown')
    except Exception as e:
        out['python_bidi_error'] = str(e)
    if out['arabic_reshaper'] and out['python_bidi']:
        try:
            import arabic_reshaper as ar
            from bidi.algorithm import get_display
            sample = 'العربية'
            shaped = get_display(ar.reshape(sample))
            out['shaping_test'] = shaped
            out['shaping_test_ok'] = (shaped != sample)
        except Exception as e:
            out['shaping_test_error'] = str(e)
    out['ready_for_arabic_certificates'] = (
        out['amiri_regular_present'] and out['arabic_reshaper']
        and out['python_bidi'] and out['shaping_test_ok']
    )
    return jsonify(out)


def _contains_arabic(text):
    """Return True if the string contains any Arabic-script characters."""
    if not text:
        return False
    for ch in str(text):
        if '\u0600' <= ch <= '\u06ff' or '\u0750' <= ch <= '\u077f' or '\ufb50' <= ch <= '\ufdff' or '\ufe70' <= ch <= '\ufeff':
            return True
    return False


def _format_arabic_date(dt):
    """Format a date with Arabic month names."""
    months_ar = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
    return f"{dt.day} {months_ar[dt.month - 1]} {dt.year}"


def _render_certificate_pdf(student_name, course_title, issue_date, cert_number,
                             final_grade=None, language='en'):
    """Low-level certificate renderer.  Knows nothing about the database —
    accepts only display strings, so it works for both DB-driven and
    CSV no-class generation, and supports English ('en') or Arabic ('ar')."""
    import io
    import os
    from datetime import datetime as _dt
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.colors import HexColor, black
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import qrcode

    is_ar = (language or 'en').lower().startswith('ar')
    arabic_font_ok = _ensure_arabic_font() if is_ar else False

    # Localised labels
    L = {
        'title':       _ar('شهادة')                         if is_ar else 'CERTIFICATE',
        'subtitle':    _ar('إتمام البرنامج')                if is_ar else 'OF COMPLETION',
        'preamble':    _ar('تشهد أكاديمية نزوى للتدريب بأن') if is_ar else 'This is to certify that',
        'completed':   _ar('قد أتمّ بنجاح البرنامج التدريبي') if is_ar else 'has successfully completed the training program',
        'date_label':  _ar('تاريخ الإصدار')                 if is_ar else 'Date of Issue',
        'scan':        _ar('امسح للتحقق')                   if is_ar else 'Scan to Verify',
        'cert_no':     _ar('رقم الشهادة')                   if is_ar else 'Certificate No',
        'chair_name':  _ar('أ.د. ربيع أ. رمضان')            if is_ar else 'Prof. Rabie A. Ramadan',
        'chair_role':  _ar('كرسي تطبيقات الذكاء الاصطناعي') if is_ar else 'AI Applications Chair',
        'chair_org':   _ar('جامعة نزوى')                   if is_ar else 'University of Nizwa',
        'dir_role':    _ar('مدير الأكاديمية')              if is_ar else 'Academy Director',
        'dir_org1':    _ar('أكاديمية نزوى')                if is_ar else 'Nizwa Academy for',
        'dir_org2':    _ar('للتدريب والتنمية')             if is_ar else 'Training and Development',
        'footer1':     _ar('هذه الشهادة صادرة رقمياً وقابلة للتحقق. أي تعديل غير مصرح به يبطلها.')
                                                            if is_ar else 'This certificate is digitally generated and verifiable. Any unauthorized alteration renders this certificate void.',
        'footer2':     _ar('جامعة نزوى — كرسي تطبيقات الذكاء الاصطناعي | أكاديمية نزوى للتدريب والتنمية')
                                                            if is_ar else 'University of Nizwa - AI Applications Chair | Nizwa Academy for Training and Development',
    }

    if is_ar and arabic_font_ok:
        body_font, bold_font = 'Amiri', 'Amiri-Bold'
    else:
        body_font, bold_font = 'Helvetica', 'Helvetica-Bold'

    buffer = io.BytesIO()
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    
    primary_color = HexColor('#1a5c5e')
    secondary_color = HexColor('#2d7d80')
    gold_color = HexColor('#c4a35a')
    dark_blue = HexColor('#1a3a5c')
    
    # Border
    c.setStrokeColor(primary_color)
    c.setLineWidth(3)
    c.rect(20, 20, page_width - 40, page_height - 40)
    
    c.setStrokeColor(gold_color)
    c.setLineWidth(1.5)
    c.rect(35, 35, page_width - 70, page_height - 70)
    
    # Corner ornaments
    corner_size = 25
    for x, y in [(40, 40), (page_width - 65, 40), (40, page_height - 65), (page_width - 65, page_height - 65)]:
        c.setFillColor(gold_color)
        c.circle(x + corner_size/2, y + corner_size/2, corner_size/3, fill=1, stroke=0)
    
    # Logos
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    images_path = os.path.join(base_path, 'static', 'images')
    
    logo_size = 75
    logo_y = page_height - 140
    
    aiac_logo_path = os.path.join(images_path, 'aiac-logo.png')
    if os.path.exists(aiac_logo_path):
        try:
            c.drawImage(aiac_logo_path, 50, logo_y, width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
        except:
            pass
    
    natd_logo_path = os.path.join(images_path, 'NATD_Logo.png')
    if os.path.exists(natd_logo_path):
        try:
            c.drawImage(natd_logo_path, 130, logo_y, width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
        except:
            pass
    
    ac_logo_path = os.path.join(images_path, 'ac-logo.png')
    if os.path.exists(ac_logo_path):
        try:
            c.drawImage(ac_logo_path, page_width - 165, logo_y - 20, width=115, height=115, preserveAspectRatio=True, mask='auto')
        except:
            pass
    
    # Title
    c.setFillColor(primary_color)
    c.setFont(bold_font, 36)
    c.drawCentredString(page_width / 2, page_height - 90, L['title'])

    c.setFillColor(gold_color)
    c.setFont(body_font, 16)
    c.drawCentredString(page_width / 2, page_height - 115, L['subtitle'])

    c.setStrokeColor(gold_color)
    c.setLineWidth(2)
    c.line(page_width/2 - 120, page_height - 125, page_width/2 + 120, page_height - 125)

    # Body — preamble
    c.setFillColor(black)
    c.setFont(body_font, 14)
    c.drawCentredString(page_width / 2, page_height - 160, L['preamble'])

    # Student name (already supplied as a string parameter)
    raw_student_name = student_name or 'Unknown Student'
    display_name = _ar(raw_student_name) if is_ar else raw_student_name
    c.setFillColor(primary_color)

    max_name_width = page_width - 120
    name_font_size = 28
    c.setFont(bold_font, name_font_size)
    name_width = c.stringWidth(display_name, bold_font, name_font_size)

    while name_width > max_name_width and name_font_size > 16:
        name_font_size -= 2
        c.setFont(bold_font, name_font_size)
        name_width = c.stringWidth(display_name, bold_font, name_font_size)

    c.drawCentredString(page_width / 2, page_height - 195, display_name)

    c.setStrokeColor(gold_color)
    c.setLineWidth(1)
    underline_width = min(name_width + 40, max_name_width)
    c.line(page_width/2 - underline_width/2, page_height - 205, page_width/2 + underline_width/2, page_height - 205)

    # "has successfully completed the training program"
    c.setFillColor(black)
    c.setFont(body_font, 14)
    c.drawCentredString(page_width / 2, page_height - 235, L['completed'])

    # Course title
    raw_course_title = course_title or 'Training Program'
    display_course = _ar(raw_course_title) if is_ar else raw_course_title
    c.setFillColor(dark_blue)
    c.setFont(bold_font, 22)

    if len(raw_course_title) > 50:
        words = raw_course_title.split()
        mid = len(words) // 2
        line1 = ' '.join(words[:mid])
        line2 = ' '.join(words[mid:])
        if is_ar:
            line1 = _ar(line1); line2 = _ar(line2)
        c.drawCentredString(page_width / 2, page_height - 270, line1)
        c.drawCentredString(page_width / 2, page_height - 295, line2)
    else:
        c.drawCentredString(page_width / 2, page_height - 275, display_course)

    # Signature section
    sig_y = 120

    # LEFT side - Chair Signature
    signature_path = os.path.join(images_path, 'signature.png')
    if os.path.exists(signature_path):
        try:
            c.drawImage(signature_path, 80, sig_y - 5, width=120, height=50, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # LEFT side - Chair Stamp (centered above signature)
    chair_stamp_path = os.path.join(images_path, 'aiac-stamp.png')
    if os.path.exists(chair_stamp_path):
        try:
            stamp_width = 80
            stamp_height = 80
            stamp_x = 140 - stamp_width/2
            stamp_y = sig_y + 55
            c.drawImage(chair_stamp_path, stamp_x, stamp_y, width=stamp_width, height=stamp_height, preserveAspectRatio=True)
        except Exception:
            pass

    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(60, sig_y, 220, sig_y)

    c.setFillColor(black)
    c.setFont(bold_font, 10)
    c.drawCentredString(140, sig_y - 15, L['chair_name'])
    c.setFont(body_font, 9)
    c.drawCentredString(140, sig_y - 28, L['chair_role'])
    c.drawCentredString(140, sig_y - 40, L['chair_org'])

    # CENTER - Date of Issue
    if issue_date is None:
        issue_date = _dt.utcnow()
    if is_ar:
        date_str = _ar(_format_arabic_date(issue_date))
    else:
        date_str = issue_date.strftime("%B %d, %Y")

    c.setFillColor(black)
    c.setFont(body_font, 10)
    c.drawCentredString(page_width / 2, sig_y + 100, L['date_label'])
    c.setFont(bold_font, 12)
    c.drawCentredString(page_width / 2, sig_y + 82, date_str)

    # CENTER - QR Code for verification
    qr_size = 90
    verify_base = os.environ.get('CERTIFICATE_VERIFY_BASE_URL', '').rstrip('/')
    if not verify_base:
        try:
            from flask import request as _flask_request
            verify_base = _flask_request.host_url.rstrip('/')
        except Exception:
            verify_base = 'https://futurecoverage.ai'
    verification_url = f"{verify_base}/verify/{cert_number}"
    qr = qrcode.QRCode(version=1, box_size=5, border=1)
    qr.add_data(verification_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    center_x = page_width / 2
    c.drawImage(ImageReader(qr_buffer), center_x - qr_size/2, sig_y - 15, width=qr_size, height=qr_size, mask='auto')

    c.setFillColor(secondary_color)
    c.setFont(body_font, 8)
    c.drawCentredString(center_x, sig_y - 30, L['scan'])

    # Certificate number (below QR) — keep number ASCII for legibility
    c.setFont(body_font, 9)
    c.setFillColor(secondary_color)
    if is_ar:
        # In Arabic mode, omit the Arabic label — show only the bare cert number
        cert_line = cert_number
    else:
        cert_line = f"{L['cert_no']}: {cert_number}"
    c.drawCentredString(page_width / 2, sig_y - 45, cert_line)

    # RIGHT side - Academy Director Signature
    signature2_path = os.path.join(images_path, 'signature2.png')
    if os.path.exists(signature2_path):
        try:
            c.drawImage(signature2_path, page_width - 200, sig_y - 5, width=120, height=50, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # RIGHT side - NATD Stamp
    natd_stamp_path = os.path.join(images_path, 'NATD_stamp.png')
    if os.path.exists(natd_stamp_path):
        try:
            c.drawImage(natd_stamp_path, page_width - 180, sig_y + 35, width=110, height=110, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Signature line for NATD (right side)
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(page_width - 220, sig_y, page_width - 60, sig_y)

    c.setFillColor(black)
    c.setFont(bold_font, 10)
    c.drawCentredString(page_width - 140, sig_y - 15, L['dir_role'])
    c.setFont(body_font, 9)
    c.drawCentredString(page_width - 140, sig_y - 28, L['dir_org1'])
    c.drawCentredString(page_width - 140, sig_y - 40, L['dir_org2'])

    # Footer
    c.setFillColor(HexColor('#cccccc'))
    c.setFont(body_font, 8)
    c.drawCentredString(page_width / 2, 35, L['footer1'])

    c.setFillColor(secondary_color)
    c.setFont(body_font, 8)
    c.drawCentredString(page_width / 2, 22, L['footer2'])

    c.save()
    buffer.seek(0)
    return buffer


def generate_certificate_pdf(enrollment, student, course, language='en'):
    """DB-aware wrapper around _render_certificate_pdf.  Pulls grade and
    issue date from the enrollment row and renders in the requested
    language ('en' or 'ar')."""
    from datetime import datetime
    from app.models import Exam, ExamResult

    exams = Exam.query.filter_by(course_id=course.id).all() if course else []
    exam_ids = [e.id for e in exams]
    exam_results = ExamResult.query.filter(
        ExamResult.user_id == enrollment.user_id,
        ExamResult.exam_id.in_(exam_ids)
    ).all() if (enrollment and exam_ids) else []

    avg_score = sum(r.score or 0 for r in exam_results) / len(exam_results) if exam_results else 0
    final_grade = (enrollment.final_grade if enrollment else None) or round(avg_score, 1)

    cert_number = f"CERT-{str(enrollment.id)[:8].upper()}" if enrollment else f"CERT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    student_name = (student.full_name or student.username or 'Unknown Student') if student else 'Unknown Student'
    course_title = (course.title or course.code or 'Training Program') if course else 'Training Program'
    issue_date = (enrollment.certificate_issued_at if enrollment else None) or datetime.utcnow()

    return _render_certificate_pdf(
        student_name=student_name,
        course_title=course_title,
        issue_date=issue_date,
        cert_number=cert_number,
        final_grade=final_grade,
        language=language,
    )


@super_admin_bp.route('/api/certificates/<enrollment_id>/download', methods=['GET'])
@admin_dashboard_required
def download_single_certificate(enrollment_id):
    """Download a single certificate PDF"""
    from flask import send_file
    
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import User, Course, Enrollment
        
        enrollment = Enrollment.query.filter_by(id=enrollment_id).first()
        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404
        
        if not enrollment.certificate_issued:
            return jsonify({'error': 'Certificate not yet issued'}), 400
        
        student = User.query.filter_by(id=enrollment.user_id).first()
        course = Course.query.filter_by(id=enrollment.course_id).first()
        
        if not student or not course:
            return jsonify({'error': 'Student or course not found'}), 404
        
        buffer = generate_certificate_pdf(enrollment, student, course)
        
        student_name = student.full_name or student.username or 'Student'
        course_title = course.title or course.code or 'Course'
        safe_name = ''.join(c for c in student_name if c.isalnum() or c in ' -_').strip()
        safe_course = ''.join(c for c in course_title if c.isalnum() or c in ' -_').strip()[:30]
        filename = f"Certificate_{safe_name}_{safe_course}.pdf"
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        print(f"Download certificate error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/certificates/download-zip', methods=['POST'])
@super_admin_required
def download_certificates_zip():
    """Download multiple certificates as a ZIP file"""
    from flask import send_file
    import zipfile
    import io
    
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    data = request.get_json() or {}
    enrollment_ids = data.get('enrollment_ids', [])
    
    if not enrollment_ids:
        return jsonify({'error': 'No enrollment IDs provided'}), 400
    
    try:
        from app.models import User, Course, Enrollment
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            success_count = 0
            
            for enrollment_id in enrollment_ids:
                enrollment = Enrollment.query.filter_by(id=enrollment_id).first()
                if not enrollment or not enrollment.certificate_issued:
                    continue
                
                student = User.query.filter_by(id=enrollment.user_id).first()
                course = Course.query.filter_by(id=enrollment.course_id).first()
                
                if not student or not course:
                    continue
                
                try:
                    pdf_buffer = generate_certificate_pdf(enrollment, student, course)
                    
                    student_name = student.full_name or student.username or 'Student'
                    course_title = course.title or course.code or 'Course'
                    safe_name = ''.join(c for c in student_name if c.isalnum() or c in ' -_').strip()
                    safe_course = ''.join(c for c in course_title if c.isalnum() or c in ' -_').strip()[:30]
                    filename = f"Certificate_{safe_name}_{safe_course}.pdf"
                    
                    zip_file.writestr(filename, pdf_buffer.read())
                    success_count += 1
                except Exception as e:
                    print(f"Error generating certificate for {enrollment_id}: {e}")
                    continue
        
        if success_count == 0:
            return jsonify({'error': 'No valid certificates to download'}), 400
        
        zip_buffer.seek(0)
        
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"Certificates_{timestamp}.zip"
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
    except Exception as e:
        print(f"Download certificates ZIP error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# BATCH MONTHLY REPORT (Excel)
# ============================================

# Performance criteria for the rubric block (1-4 scale).
BATCH_REPORT_PERFORMANCE_CRITERIA = [
    'Attendance', 'Punctuality', 'Discipline', 'General',
    'Attitude', 'Class Participation', 'Commitment',
    'Capability & Development', 'Trade Skill', 'Communication',
]


def _grade_label(score):
    """Map a final grade (0-100) to the report's grade label."""
    if score is None:
        return 'No results'
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 'No results'
    if s >= 91:
        return 'Excellent'
    if s >= 81:
        return 'Very Good'
    if s >= 71:
        return 'Good'
    if s >= 61:
        return 'Satisfactory'
    return 'Poor'


def _safe_image(path, max_w=70, max_h=70):
    """Load an image as an openpyxl drawing.Image, sized for the header."""
    try:
        from openpyxl.drawing.image import Image as XLImage
        if not path or not __import__('os').path.exists(path):
            return None
        img = XLImage(path)
        # Scale to fit while keeping aspect ratio
        try:
            ratio = min(max_w / float(img.width or max_w), max_h / float(img.height or max_h))
            if ratio < 1:
                img.width = int((img.width or max_w) * ratio)
                img.height = int((img.height or max_h) * ratio)
            else:
                img.width = max_w
                img.height = max_h
        except Exception:
            img.width = max_w
            img.height = max_h
        return img
    except Exception as exc:
        print(f"batch report: could not load image {path}: {exc}")
        return None


def generate_batch_report_xlsx(course, enrollments, period_start=None, period_end=None,
                                month_label=None, batch_label=None, overrides=None):
    """
    Build a "Batch Monthly Report" .xlsx for a course in the same visual
    language as the certificate (same logos + brand colours), and return
    a BytesIO buffer ready for send_file.
    """
    import io
    import os
    from datetime import datetime, date as _date
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from app.models import Attendance, Exam, ExamResult, User

    # ---- Brand colours (mirror the certificate) ----
    primary = '1A5C5E'
    gold = 'C4A35A'
    dark_blue = '1A3A5C'
    light_band = 'E8F1F1'

    thin = Side(style='thin', color='8AA8A9')
    box = Border(top=thin, bottom=thin, left=thin, right=thin)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Batch Report'
    ws.sheet_view.showGridLines = False

    # ---- Resolve period and exam columns ----
    today = datetime.utcnow().date()
    if not period_end:
        period_end = today
    if not period_start:
        # Default: first day of the period_end month
        period_start = period_end.replace(day=1)

    if not month_label:
        month_label = period_start.strftime('%B %Y')

    # Distinct attendance dates for this course in [period_start, period_end]
    attendance_rows = Attendance.query.filter(
        Attendance.course_id == course.id,
        Attendance.attendance_date >= period_start,
        Attendance.attendance_date <= period_end,
    ).all() if course else []

    working_days = len({a.attendance_date for a in attendance_rows})
    absent_by_user = {}
    for a in attendance_rows:
        if (a.status or '').lower() == 'absent':
            absent_by_user[a.user_id] = absent_by_user.get(a.user_id, 0) + 1

    # Exams (cap to keep the sheet readable)
    exams = (Exam.query.filter_by(course_id=course.id)
             .order_by(Exam.created_at.asc()).all()) if course else []
    exams = exams[:8]
    exam_id_list = [e.id for e in exams]

    # ExamResult lookup keyed by (user_id, exam_id) -> latest score
    result_lookup = {}
    if exam_id_list:
        for er in ExamResult.query.filter(ExamResult.exam_id.in_(exam_id_list)).all():
            key = (er.user_id, er.exam_id)
            prev = result_lookup.get(key)
            if prev is None or (er.score or 0) > (prev.score or 0):
                result_lookup[key] = er

    # ---- Column layout ----
    # Fixed columns then dynamic exam columns + final grade + label
    base_headers = ['ID', 'Name', 'Organization', 'Country',
                    'Absent Days', 'Attendance %', 'Warning Letters']
    perf_headers = list(BATCH_REPORT_PERFORMANCE_CRITERIA)
    exam_headers = [(e.title or e.exam_type or 'Exam')[:24] for e in exams]
    tail_headers = ['Overall Grade (Performance 20% + Tests 80%)', 'Result']

    headers = base_headers + perf_headers + exam_headers + tail_headers
    n_cols = len(headers)
    last_col_letter = get_column_letter(n_cols)

    # ---- Header band: logos + title (same as certificate) ----
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    images_path = os.path.join(base_path, 'static', 'images')
    aiac_logo = _safe_image(os.path.join(images_path, 'aiac-logo.png'), 70, 70)
    natd_logo = _safe_image(os.path.join(images_path, 'NATD_Logo.png'), 70, 70)
    ac_logo = _safe_image(os.path.join(images_path, 'ac-logo.png'), 70, 70)

    # Reserve rows 1-4 for the brand header.
    for r in range(1, 5):
        ws.row_dimensions[r].height = 22
    if aiac_logo:
        ws.add_image(aiac_logo, 'A1')
    if natd_logo:
        ws.add_image(natd_logo, 'B1')

    # Right-side logo: place it in the last column area.
    if ac_logo and n_cols >= 3:
        right_anchor = f"{get_column_letter(max(1, n_cols - 1))}1"
        ws.add_image(ac_logo, right_anchor)

    # Title cells
    ws.merge_cells(start_row=1, start_column=3, end_row=1, end_column=max(3, n_cols - 2))
    title_cell = ws.cell(row=1, column=3, value='University of Nizwa — AI Applications Chair')
    title_cell.font = Font(name='Calibri', size=14, bold=True, color=primary)
    title_cell.alignment = Alignment(horizontal='center', vertical='center')

    ws.merge_cells(start_row=2, start_column=3, end_row=2, end_column=max(3, n_cols - 2))
    sub_cell = ws.cell(row=2, column=3, value='Nizwa Academy for Training and Development')
    sub_cell.font = Font(name='Calibri', size=11, italic=True, color=dark_blue)
    sub_cell.alignment = Alignment(horizontal='center', vertical='center')

    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=n_cols)
    band = ws.cell(row=3, column=1, value='BATCH MONTHLY REPORT')
    band.font = Font(name='Calibri', size=16, bold=True, color='FFFFFF')
    band.fill = PatternFill('solid', fgColor=primary)
    band.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[3].height = 26

    # Gold underline row
    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=n_cols)
    ws.cell(row=4, column=1).fill = PatternFill('solid', fgColor=gold)
    ws.row_dimensions[4].height = 4

    # ---- Info bar (rows 5-7) ----
    course_code = (getattr(course, 'code', None) or '').strip() or '—'
    course_title = (getattr(course, 'title', None) or course_code or 'Training Program')
    start_date = getattr(course, 'start_date', None)
    start_str = start_date.strftime('%d-%b-%Y') if isinstance(start_date, _date) else '—'
    if not batch_label:
        batch_label = course_code or course_title

    info_rows = [
        [('Month', month_label), ('Working Days', working_days),
         ('Nr. of Trainees', len(enrollments))],
        [('Batch', batch_label), ('Program', course_title),
         ('Batch Start Date', start_str)],
    ]

    for r_offset, pairs in enumerate(info_rows):
        row = 5 + r_offset
        ws.row_dimensions[row].height = 20
        # Spread the 3 pairs across the available columns.
        slot_w = max(2, n_cols // 3)
        for i, (label, value) in enumerate(pairs):
            label_col = 1 + i * slot_w
            value_col_start = label_col + 1
            value_col_end = (label_col + slot_w - 1) if i < 2 else n_cols
            lab = ws.cell(row=row, column=label_col, value=label)
            lab.font = Font(name='Calibri', size=10, bold=True, color=primary)
            lab.fill = PatternFill('solid', fgColor=light_band)
            lab.alignment = Alignment(horizontal='right', vertical='center')
            lab.border = box
            if value_col_end >= value_col_start:
                ws.merge_cells(start_row=row, start_column=value_col_start,
                               end_row=row, end_column=value_col_end)
            val = ws.cell(row=row, column=value_col_start, value=value)
            val.font = Font(name='Calibri', size=10, bold=True, color=dark_blue)
            val.alignment = Alignment(horizontal='left', vertical='center', indent=1)
            val.border = box

    # ---- Group headers (row 8) ----
    group_row = 8
    ws.row_dimensions[group_row].height = 20
    perf_start = len(base_headers) + 1
    perf_end = perf_start + len(perf_headers) - 1
    test_start = perf_end + 1
    test_end = test_start + len(exam_headers) - 1 if exam_headers else perf_end

    def _group(c1, c2, label):
        if c2 < c1:
            return
        ws.merge_cells(start_row=group_row, start_column=c1, end_row=group_row, end_column=c2)
        cell = ws.cell(row=group_row, column=c1, value=label)
        cell.font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor=primary)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = box

    _group(1, len(base_headers), 'Trainee & Attendance')
    _group(perf_start, perf_end, 'Performance (1–4 scale)')
    if exam_headers:
        _group(test_start, test_end, 'Test Results (0–100)')
    _group(test_end + 1, n_cols, 'Overall')

    # ---- Column headers (row 9) ----
    head_row = 9
    ws.row_dimensions[head_row].height = 36
    for col_idx, name in enumerate(headers, start=1):
        cell = ws.cell(row=head_row, column=col_idx, value=name)
        cell.font = Font(name='Calibri', size=10, bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor=dark_blue)
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = box

    # ---- Data rows ----
    # Bulk-load all students in one query to avoid N+1.
    user_ids = [getattr(e, 'user_id', None) for e in enrollments if getattr(e, 'user_id', None)]
    user_map = {}
    if user_ids:
        for u in User.query.filter(User.id.in_(user_ids)).all():
            user_map[u.id] = u

    overrides = overrides or {}

    data_start = head_row + 1
    for idx, enr in enumerate(enrollments):
        row = data_start + idx
        uid = getattr(enr, 'user_id', None)
        student = user_map.get(uid)
        absent = absent_by_user.get(uid, 0)
        att_pct = ''
        if working_days > 0:
            att_pct = round(((working_days - absent) / working_days) * 100)

        sid = (getattr(student, 'username', None) or '')[:24] if student else ''
        sname = (getattr(student, 'full_name', None) or getattr(student, 'username', None) or '') if student else ''
        sorg = (getattr(student, 'organization', None) or '') if student else ''
        scountry = (getattr(student, 'country', None) or '') if student else ''

        ov = overrides.get(uid) or overrides.get(getattr(enr, 'id', None)) or {}

        warnings_val = ov.get('warning_letters')
        if warnings_val is None:
            warnings_val = 0

        base_vals = [sid, sname, sorg, scountry, absent, att_pct, warnings_val]

        # Performance scores: pull from overrides if provided, else blank.
        perf_overrides = ov.get('performance') or {}
        perf_vals = []
        for crit in perf_headers:
            v = perf_overrides.get(crit)
            perf_vals.append(v if v not in (None, '') else '')

        # Per-exam scores: prefer override, else computed.
        exam_overrides = ov.get('exam_scores') or {}
        exam_vals = []
        for e in exams:
            v = exam_overrides.get(e.id)
            if v in (None, ''):
                er = result_lookup.get((uid, e.id))
                v = round(er.score, 1) if er and er.score is not None else ''
            exam_vals.append(v)

        # Final grade: override > enrollment.final_grade > average of exam scores.
        final = ov.get('final_grade')
        if final in (None, ''):
            final = getattr(enr, 'final_grade', None)
        if final in (None, '') and exam_vals:
            numeric = [v for v in exam_vals if isinstance(v, (int, float))]
            final = round(sum(numeric) / len(numeric), 1) if numeric else None
        tail_vals = [final if final not in (None, '') else '', _grade_label(final)]

        all_vals = base_vals + perf_vals + exam_vals + tail_vals
        for col_idx, value in enumerate(all_vals, start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.alignment = Alignment(
                horizontal='center' if col_idx not in (2, 3, 4) else 'left',
                vertical='center', indent=1 if col_idx in (2, 3, 4) else 0,
            )
            cell.border = box
            cell.font = Font(name='Calibri', size=10)
        # Zebra stripe
        if idx % 2 == 1:
            for col_idx in range(1, n_cols + 1):
                ws.cell(row=row, column=col_idx).fill = PatternFill('solid', fgColor='F4F8F8')

    # ---- Column widths ----
    widths = {1: 12, 2: 32, 3: 18, 4: 14, 5: 11, 6: 13, 7: 13}
    for c, w in widths.items():
        ws.column_dimensions[get_column_letter(c)].width = w
    for c in range(perf_start, perf_end + 1):
        ws.column_dimensions[get_column_letter(c)].width = 11
    for c in range(test_start, test_end + 1) if exam_headers else []:
        ws.column_dimensions[get_column_letter(c)].width = 14
    ws.column_dimensions[get_column_letter(n_cols - 1)].width = 22
    ws.column_dimensions[last_col_letter].width = 14

    # ---- Legend / notes ----
    notes_row = data_start + max(1, len(enrollments)) + 2
    ws.merge_cells(start_row=notes_row, start_column=1, end_row=notes_row, end_column=n_cols)
    notes = ws.cell(row=notes_row, column=1,
                    value='Notes: Performance is based on assessment by trainers and the training '
                          'manager. Scores used for the Overall Grade are not rounded.')
    notes.font = Font(name='Calibri', size=9, italic=True, color=dark_blue)
    notes.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    ws.row_dimensions[notes_row].height = 26

    legend_row = notes_row + 1
    legend_text = ('Performance scale:  4 Very Good   3 Good   2 Average   1 Below Average   |   '
                   'Grade: 91–100 Excellent · 81–90 Very Good · 71–80 Good · 61–70 Satisfactory · 0–60 Poor')
    ws.merge_cells(start_row=legend_row, start_column=1, end_row=legend_row, end_column=n_cols)
    leg = ws.cell(row=legend_row, column=1, value=legend_text)
    leg.font = Font(name='Calibri', size=9, color=primary)
    leg.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    ws.row_dimensions[legend_row].height = 22

    # ---- Signature block ----
    sig_row = legend_row + 3
    ws.cell(row=sig_row, column=1, value='Instructor:').font = Font(name='Calibri', size=10, bold=True, color=dark_blue)
    sig_mid = max(1, n_cols // 2 + 1)
    ws.cell(row=sig_row, column=sig_mid, value='Training Manager:').font = Font(name='Calibri', size=10, bold=True, color=dark_blue)

    # Underlines for signatures
    for col in (1, sig_mid):
        for c in range(col, min(col + 3, n_cols + 1)):
            ws.cell(row=sig_row + 1, column=c).border = Border(bottom=Side(style='thin', color=dark_blue))

    # ---- Save ----
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


@super_admin_bp.route('/api/courses/<course_id>/batch-report.xlsx', methods=['GET'])
@admin_dashboard_required
def download_batch_report(course_id):
    """Download an Excel "Batch Monthly Report" for a course.

    Optional query params:
      - month=YYYY-MM       (defaults to current month)
      - start=YYYY-MM-DD    (overrides month start)
      - end=YYYY-MM-DD      (overrides month end)
    """
    from flask import send_file
    from datetime import datetime, date
    import calendar

    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course, Enrollment

        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Resolve period
        month_q = (request.args.get('month') or '').strip()
        start_q = (request.args.get('start') or '').strip()
        end_q = (request.args.get('end') or '').strip()
        period_start = period_end = None
        month_label = None

        try:
            if start_q:
                period_start = datetime.strptime(start_q, '%Y-%m-%d').date()
            if end_q:
                period_end = datetime.strptime(end_q, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': "start/end must be in YYYY-MM-DD format"}), 400

        if not period_start and month_q:
            try:
                year, mon = month_q.split('-')
                year, mon = int(year), int(mon)
                period_start = date(year, mon, 1)
                last = calendar.monthrange(year, mon)[1]
                period_end = date(year, mon, last)
                month_label = period_start.strftime('%B %Y')
            except (ValueError, TypeError):
                pass

        if not period_start:
            today = datetime.utcnow().date()
            period_start = today.replace(day=1)
            last = calendar.monthrange(today.year, today.month)[1]
            period_end = today.replace(day=last)
            month_label = period_start.strftime('%B %Y')

        enrollments = (Enrollment.query
                       .filter_by(course_id=course_id)
                       .filter(Enrollment.status.in_(['approved', 'completed']))
                       .all())

        buffer = generate_batch_report_xlsx(
            course=course, enrollments=enrollments,
            period_start=period_start, period_end=period_end,
            month_label=month_label,
        )

        safe_code = ''.join(c for c in (course.code or course.title or 'Course')
                            if c.isalnum() or c in ' -_').strip().replace(' ', '_')[:40] or 'Course'
        period_tag = period_start.strftime('%Y-%m')
        filename = f"BatchReport_{safe_code}_{period_tag}.xlsx"

        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as exc:
        print(f"Batch report error: {exc}")
        return jsonify({'error': str(exc)}), 500


# ---------- Helpers shared by the JSON / XLSX endpoints ----------

def _resolve_batch_period(month_q, start_q, end_q):
    """Return (period_start, period_end, month_label) or raise ValueError."""
    from datetime import datetime, date
    import calendar

    period_start = period_end = None
    month_label = None
    if start_q:
        period_start = datetime.strptime(start_q, '%Y-%m-%d').date()
    if end_q:
        period_end = datetime.strptime(end_q, '%Y-%m-%d').date()

    if not period_start and month_q:
        year, mon = month_q.split('-')
        year, mon = int(year), int(mon)
        period_start = date(year, mon, 1)
        last = calendar.monthrange(year, mon)[1]
        period_end = date(year, mon, last)
        month_label = period_start.strftime('%B %Y')

    if not period_start:
        today = datetime.utcnow().date()
        period_start = today.replace(day=1)
        last = calendar.monthrange(today.year, today.month)[1]
        period_end = today.replace(day=last)
        month_label = period_start.strftime('%B %Y')

    if not month_label:
        month_label = period_start.strftime('%B %Y')
    return period_start, period_end, month_label


def _build_batch_report_payload(course, enrollments, period_start, period_end, month_label):
    """
    Compose the editable preview payload combining ALL data sources:
      - Enrolled trainees (User basics)
      - Attendance (working days, absent days per trainee)
      - At-risk alerts in the period (warning_letters seed)
      - Saved EnrollmentMonthlyRubric edits (override seed)
      - Exam definitions + ExamResult scores
      - Computed final grade (override > enrollment.final_grade > avg of exams)
    """
    from app.models import (
        Attendance, Exam, ExamResult, User,
        AtRiskAlert, EnrollmentMonthlyRubric,
    )

    perf_keys = list(BATCH_REPORT_PERFORMANCE_CRITERIA)

    # --- Attendance (working days + absent counts) ---
    attendance_rows = Attendance.query.filter(
        Attendance.course_id == course.id,
        Attendance.attendance_date >= period_start,
        Attendance.attendance_date <= period_end,
    ).all()
    working_days = len({a.attendance_date for a in attendance_rows})
    absent_by_user = {}
    for a in attendance_rows:
        if (a.status or '').lower() == 'absent':
            absent_by_user[a.user_id] = absent_by_user.get(a.user_id, 0) + 1

    # --- Exams in this course (cap to 8 for sheet width) ---
    exams = (Exam.query.filter_by(course_id=course.id)
             .order_by(Exam.created_at.asc()).all())
    exams = exams[:8]
    exam_id_list = [e.id for e in exams]

    # --- ExamResult lookup (best score per user/exam) ---
    result_lookup = {}
    if exam_id_list:
        for er in ExamResult.query.filter(ExamResult.exam_id.in_(exam_id_list)).all():
            key = (er.user_id, er.exam_id)
            prev = result_lookup.get(key)
            if prev is None or (er.score or 0) > (prev.score or 0):
                result_lookup[key] = er

    # --- Bulk-load students ---
    user_ids = [getattr(e, 'user_id', None) for e in enrollments if getattr(e, 'user_id', None)]
    user_map = {}
    if user_ids:
        for u in User.query.filter(User.id.in_(user_ids)).all():
            user_map[u.id] = u

    # --- Warning seed: count open/acknowledged at-risk alerts in period ---
    warning_seed = {}
    try:
        alerts = AtRiskAlert.query.filter(
            AtRiskAlert.user_id.in_(user_ids) if user_ids else False,
        ).all() if user_ids else []
        for al in alerts:
            uid = al.user_id
            status = (getattr(al, 'status', '') or '').lower()
            if status in ('resolved', 'dismissed'):
                continue
            warning_seed[uid] = warning_seed.get(uid, 0) + 1
    except Exception:
        # Model schema variants — degrade silently to 0.
        warning_seed = {}

    # --- Saved rubric edits (persisted from prior "Save" actions) ---
    enr_ids = [getattr(e, 'id', None) for e in enrollments if getattr(e, 'id', None)]
    saved_rubric = {}
    if enr_ids:
        rows = EnrollmentMonthlyRubric.query.filter(
            EnrollmentMonthlyRubric.enrollment_id.in_(enr_ids),
            EnrollmentMonthlyRubric.period_start == period_start,
        ).all()
        for r in rows:
            saved_rubric[r.enrollment_id] = r

    # --- Compose rows ---
    rows_out = []
    for enr in enrollments:
        uid = getattr(enr, 'user_id', None)
        student = user_map.get(uid)
        absent = absent_by_user.get(uid, 0)
        att_pct = round(((working_days - absent) / working_days) * 100) if working_days > 0 else None

        saved = saved_rubric.get(getattr(enr, 'id', None))
        perf_saved = (saved.performance_scores or {}) if saved else {}

        exam_scores = {}
        for e in exams:
            er = result_lookup.get((uid, e.id))
            if er and er.score is not None:
                exam_scores[e.id] = round(er.score, 1)

        # Computed final
        computed_final = getattr(enr, 'final_grade', None)
        if computed_final is None and exam_scores:
            vals = [v for v in exam_scores.values() if isinstance(v, (int, float))]
            computed_final = round(sum(vals) / len(vals), 1) if vals else None

        warning_letters = (saved.warning_letters if saved else None)
        if warning_letters is None:
            warning_letters = warning_seed.get(uid, 0)

        final_override = saved.final_grade_override if saved else None
        final_value = final_override if final_override is not None else computed_final

        rows_out.append({
            'enrollment_id': getattr(enr, 'id', None),
            'user_id': uid,
            'student_id': (getattr(student, 'username', None) or '')[:24] if student else '',
            'name': (getattr(student, 'full_name', None) or getattr(student, 'username', None) or '') if student else '',
            'organization': (getattr(student, 'organization', None) or '') if student else '',
            'country': (getattr(student, 'country', None) or '') if student else '',
            'absent_days': absent,
            'attendance_pct': att_pct,
            'warning_letters': warning_letters,
            'performance': {k: perf_saved.get(k) for k in perf_keys},
            'exam_scores': exam_scores,
            'final_grade': final_value,
            'final_grade_computed': computed_final,
            'result_label': _grade_label(final_value),
            'notes': (saved.notes if saved else '') or '',
        })

    return {
        'course': {
            'id': course.id,
            'code': getattr(course, 'code', None) or '',
            'title': getattr(course, 'title', None) or '',
            'start_date': course.start_date.isoformat() if getattr(course, 'start_date', None) else None,
        },
        'period': {
            'start': period_start.isoformat(),
            'end': period_end.isoformat(),
            'label': month_label,
        },
        'working_days': working_days,
        'performance_criteria': perf_keys,
        'exams': [{'id': e.id, 'title': (e.title or e.exam_type or 'Exam')[:24]} for e in exams],
        'rows': rows_out,
    }


@super_admin_bp.route('/api/courses/<course_id>/batch-report-data', methods=['GET'])
@admin_dashboard_required
def get_batch_report_data(course_id):
    """Return the editable preview payload as JSON (for the modal form)."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course, Enrollment

        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        try:
            period_start, period_end, month_label = _resolve_batch_period(
                (request.args.get('month') or '').strip(),
                (request.args.get('start') or '').strip(),
                (request.args.get('end') or '').strip(),
            )
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM or YYYY-MM-DD.'}), 400

        enrollments = (Enrollment.query
                       .filter_by(course_id=course_id)
                       .filter(Enrollment.status.in_(['approved', 'completed']))
                       .all())

        payload = _build_batch_report_payload(
            course, enrollments, period_start, period_end, month_label,
        )
        return jsonify(payload)
    except Exception as exc:
        print(f"Batch report data error: {exc}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(exc)}), 500


def _save_batch_report_edits(enrollments, period_start, edits_by_enr, current_user_id):
    """
    Upsert EnrollmentMonthlyRubric rows from the edits dict.
      edits_by_enr[enrollment_id] = {
        'warning_letters': int,
        'performance': {criterion: 1..4},
        'final_grade': float | None,
        'notes': str,
      }
    """
    from app.models import EnrollmentMonthlyRubric

    enr_ids = {getattr(e, 'id', None) for e in enrollments if getattr(e, 'id', None)}
    existing = {
        r.enrollment_id: r for r in
        EnrollmentMonthlyRubric.query.filter(
            EnrollmentMonthlyRubric.enrollment_id.in_(enr_ids),
            EnrollmentMonthlyRubric.period_start == period_start,
        ).all()
    } if enr_ids else {}

    sess = get_db()
    for enr_id, edit in (edits_by_enr or {}).items():
        if enr_id not in enr_ids:
            continue
        row = existing.get(enr_id)
        if row is None:
            row = EnrollmentMonthlyRubric(
                enrollment_id=enr_id,
                period_start=period_start,
            )
            sess.add(row)
        perf = edit.get('performance') or {}
        # Coerce to clean dict of str→int
        clean_perf = {}
        for k, v in perf.items():
            try:
                iv = int(v)
                if 1 <= iv <= 4:
                    clean_perf[k] = iv
            except (TypeError, ValueError):
                continue
        row.performance_scores = clean_perf
        try:
            row.warning_letters = int(edit.get('warning_letters') or 0)
        except (TypeError, ValueError):
            row.warning_letters = 0
        fg = edit.get('final_grade')
        try:
            row.final_grade_override = float(fg) if fg not in (None, '') else None
        except (TypeError, ValueError):
            row.final_grade_override = None
        row.notes = (edit.get('notes') or '')[:2000]
        row.updated_by = current_user_id
    sess.commit()


@super_admin_bp.route('/api/courses/<course_id>/batch-report.xlsx', methods=['POST'])
@admin_dashboard_required
def download_batch_report_with_edits(course_id):
    """
    Same as the GET endpoint, but accepts JSON edits, persists them to
    EnrollmentMonthlyRubric, then generates the Excel file with those
    overrides applied. Body shape:
      { "rows": [
          { "enrollment_id": "...", "warning_letters": 1,
            "performance": { "Attendance": 4, ... },
            "exam_scores": { "<exam_id>": 88, ... },
            "final_grade": 87.5, "notes": "..."
          },
          ...
        ]
      }
    """
    from flask import send_file, session
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course, Enrollment

        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        try:
            period_start, period_end, month_label = _resolve_batch_period(
                (request.args.get('month') or '').strip(),
                (request.args.get('start') or '').strip(),
                (request.args.get('end') or '').strip(),
            )
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM or YYYY-MM-DD.'}), 400

        enrollments = (Enrollment.query
                       .filter_by(course_id=course_id)
                       .filter(Enrollment.status.in_(['approved', 'completed']))
                       .all())

        body = request.get_json(silent=True) or {}
        rows = body.get('rows') or []

        # Build edits keyed by enrollment_id and overrides keyed by user_id.
        edits_by_enr = {}
        overrides_by_user = {}
        for r in rows:
            enr_id = r.get('enrollment_id')
            uid = r.get('user_id')
            if enr_id:
                edits_by_enr[enr_id] = {
                    'warning_letters': r.get('warning_letters'),
                    'performance': r.get('performance') or {},
                    'final_grade': r.get('final_grade'),
                    'notes': r.get('notes') or '',
                }
            if uid:
                # Coerce exam_scores keys to str→numeric
                exam_scores_clean = {}
                for k, v in (r.get('exam_scores') or {}).items():
                    try:
                        exam_scores_clean[k] = float(v) if v not in (None, '') else None
                    except (TypeError, ValueError):
                        pass
                # Performance values to int
                perf_clean = {}
                for k, v in (r.get('performance') or {}).items():
                    try:
                        iv = int(v)
                        if 1 <= iv <= 4:
                            perf_clean[k] = iv
                    except (TypeError, ValueError):
                        pass
                fg = r.get('final_grade')
                try:
                    fg_val = float(fg) if fg not in (None, '') else None
                except (TypeError, ValueError):
                    fg_val = None
                try:
                    wl_val = int(r.get('warning_letters') or 0)
                except (TypeError, ValueError):
                    wl_val = 0
                overrides_by_user[uid] = {
                    'warning_letters': wl_val,
                    'performance': perf_clean,
                    'exam_scores': exam_scores_clean,
                    'final_grade': fg_val,
                }

        # Persist edits first (best-effort; failure shouldn't block the download).
        try:
            _save_batch_report_edits(
                enrollments, period_start, edits_by_enr,
                session.get('user_id'),
            )
        except Exception as save_exc:
            print(f"Batch report: could not persist edits: {save_exc}")
            try:
                db.rollback()  # db here is a scoped_session
            except Exception:
                pass

        buffer = generate_batch_report_xlsx(
            course=course, enrollments=enrollments,
            period_start=period_start, period_end=period_end,
            month_label=month_label,
            overrides=overrides_by_user,
        )

        safe_code = ''.join(c for c in (course.code or course.title or 'Course')
                            if c.isalnum() or c in ' -_').strip().replace(' ', '_')[:40] or 'Course'
        period_tag = period_start.strftime('%Y-%m')
        filename = f"BatchReport_{safe_code}_{period_tag}.xlsx"

        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as exc:
        print(f"Batch report POST error: {exc}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(exc)}), 500


# ============================================
# SURVEYS MANAGEMENT
# ============================================

@super_admin_bp.route('/api/surveys', methods=['GET'])
@admin_dashboard_required
def get_all_surveys():
    """Get all surveys"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Survey

        surveys = Survey.query.order_by(Survey.created_at.desc()).all()
        surveys_list = [{
            'id': str(s.id),
            'title': s.title,
            'title_ar': getattr(s, 'title_ar', ''),
            'description': s.description,
            'survey_type': s.survey_type,
            'is_active': getattr(s, 'is_published', True),
            'course_id': str(s.course_id) if s.course_id else None,
            'created_at': s.created_at.isoformat() if s.created_at else None
        } for s in surveys]

        return jsonify({'surveys': surveys_list})
    except Exception as e:
        print(f"Get surveys error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# EXAMS MANAGEMENT
# ============================================

@super_admin_bp.route('/api/courses/<course_id>/exams', methods=['GET'])
@admin_dashboard_required
def get_course_exams(course_id):
    """Get all exams for a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Exam, ExamResult
        
        exams = Exam.query.filter_by(course_id=course_id).order_by(Exam.created_at.desc()).all()
        exams_list = []
        
        for exam in exams:
            # Get submission stats
            results = ExamResult.query.filter_by(exam_id=exam.id).all()
            total_submissions = len(results)
            passed_count = sum(1 for r in results if r.passed)
            flagged_count = sum(1 for r in results if (getattr(r, 'violation_count', 0) or 0) > 0)
            
            exams_list.append({
                'id': str(exam.id),
                'title': exam.title,
                'title_ar': getattr(exam, 'title_ar', ''),
                'description': exam.description,
                'description_ar': getattr(exam, 'description_ar', ''),
                'exam_type': exam.exam_type,
                'passing_threshold': exam.passing_threshold,
                'max_attempts': exam.max_attempts,
                'time_limit_minutes': exam.time_limit_minutes,
                'is_published': exam.is_published,
                'shuffle_questions': getattr(exam, 'shuffle_questions', False),
                'shuffle_answers': getattr(exam, 'shuffle_answers', False),
                'total_submissions': total_submissions,
                'passed_count': passed_count,
                'flagged_count': flagged_count
            })

        return jsonify({'exams': exams_list})
    except Exception as e:
        print(f"Get course exams error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/exams/<exam_id>/results', methods=['GET'])
@admin_dashboard_required
def get_exam_results_admin(course_id, exam_id):
    """List all attempts for an exam, including anti-cheating flags."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Exam, ExamResult, User

        exam = Exam.query.filter_by(id=exam_id, course_id=course_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404

        results = ExamResult.query.filter_by(exam_id=exam_id).order_by(
            ExamResult.submitted_at.desc()).all()

        user_ids = {r.user_id for r in results}
        users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

        out = []
        for r in results:
            u = users.get(r.user_id)
            events = getattr(r, 'proctoring_events', None) or []
            # Compact per-type counts for the admin table
            event_counts = {}
            for ev in events:
                t = (ev or {}).get('type', 'unknown')
                event_counts[t] = event_counts.get(t, 0) + 1
            out.append({
                'result_id': str(r.id),
                'student_name': (u.full_name or u.username) if u else 'Unknown',
                'student_email': u.email if u else '',
                'attempt_number': r.attempt_number,
                'score': r.score,
                'total_points': r.total_points,
                'percentage': round(r.percentage or 0, 1),
                'passed': bool(r.passed),
                'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None,
                'time_spent_seconds': r.time_spent_seconds,
                'violation_count': getattr(r, 'violation_count', 0) or 0,
                'event_counts': event_counts,
                'proctoring_events': events,
            })

        return jsonify({'exam': {'id': str(exam.id), 'title': exam.title}, 'results': out})
    except Exception as e:
        print(f"Get exam results (admin) error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/exams/<exam_id>', methods=['GET'])
@admin_dashboard_required
def get_exam_detail(course_id, exam_id):
    """Get single exam details"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Exam
        
        exam = Exam.query.filter_by(id=exam_id, course_id=course_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        return jsonify({
            'exam': {
                'id': str(exam.id),
                'title': exam.title,
                'title_ar': getattr(exam, 'title_ar', ''),
                'description': exam.description,
                'description_ar': getattr(exam, 'description_ar', ''),
                'exam_type': exam.exam_type,
                'passing_threshold': exam.passing_threshold,
                'max_attempts': exam.max_attempts,
                'time_limit_minutes': exam.time_limit_minutes,
                'is_published': exam.is_published,
                'shuffle_questions': getattr(exam, 'shuffle_questions', False),
                'shuffle_answers': getattr(exam, 'shuffle_answers', False),
                'show_results': getattr(exam, 'show_results', True)
            }
        })
    except Exception as e:
        print(f"Get exam detail error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/exams/<exam_id>', methods=['PATCH'])
@admin_dashboard_required
def update_exam(course_id, exam_id):
    """Update exam settings"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Exam
        
        exam = Exam.query.filter_by(id=exam_id, course_id=course_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        data = request.get_json() or {}
        
        # Update allowed fields
        if 'title' in data:
            exam.title = data['title']
        if 'title_ar' in data:
            exam.title_ar = data['title_ar']
        if 'description' in data:
            exam.description = data['description']
        if 'description_ar' in data:
            exam.description_ar = data['description_ar']
        if 'exam_type' in data:
            exam.exam_type = data['exam_type']
        if 'passing_threshold' in data:
            exam.passing_threshold = int(data['passing_threshold'])
        if 'max_attempts' in data:
            exam.max_attempts = int(data['max_attempts'])
        if 'time_limit_minutes' in data:
            exam.time_limit_minutes = data['time_limit_minutes']
        if 'is_published' in data:
            exam.is_published = bool(data['is_published'])
        if 'shuffle_questions' in data:
            exam.shuffle_questions = bool(data['shuffle_questions'])
        if 'shuffle_answers' in data:
            exam.shuffle_answers = bool(data['shuffle_answers'])
        
        db.commit()
        
        return jsonify({'success': True, 'message': 'Exam updated successfully'})
    except Exception as e:
        db.rollback()
        print(f"Update exam error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/exams', methods=['POST'])
@admin_dashboard_required
def create_exam(course_id):
    """Create new exam for a course"""
    from datetime import datetime
    import uuid
    
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Exam, Course
        
        # Verify course exists
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        data = request.get_json() or {}
        
        exam = Exam(
            id=str(uuid.uuid4()),
            course_id=course_id,
            title=data.get('title', 'New Exam'),
            description=data.get('description', ''),
            exam_type=data.get('exam_type', 'quiz'),
            passing_threshold=int(data.get('passing_threshold', 70)),
            max_attempts=int(data.get('max_attempts', 3)),
            time_limit_minutes=data.get('time_limit_minutes'),
            is_published=False,
            created_at=datetime.utcnow()
        )
        
        db.add(exam)
        db.commit()

        try:
            from app.services.notification_service import notify_course_audience
            notify_course_audience(
                course_id,
                kind='exam_created',
                title=f'New exam: {exam.title}',
                body=(f'A new {exam.exam_type or "exam"} has been added to '
                      f'{course.title}. Passing threshold: {exam.passing_threshold}%.'),
                url=f'/app#course-{course_id}-exam-{exam.id}',
                severity='info',
                payload={'course_id': course_id, 'exam_id': str(exam.id)},
                include_admins=False,
            )
        except Exception as ne:
            print(f"[notify] exam created: {ne}")

        return jsonify({
            'success': True,
            'exam': {'id': str(exam.id), 'title': exam.title}
        })
    except Exception as e:
        db.rollback()
        print(f"Create exam error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/notify-students', methods=['POST'])
@admin_dashboard_required
def broadcast_notify_class(course_id):
    """Broadcast an in-app notification (and optional email) to selected
    students in a course. Body: {user_ids:[], title, body, severity, send_email}.
    """
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Course, Enrollment, User
        from app.services.notification_service import notify, send_email

        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        body = (data.get('body') or '').strip()
        severity = (data.get('severity') or 'info').strip().lower()
        if severity not in ('info', 'success', 'warning', 'error'):
            severity = 'info'
        send_email_flag = bool(data.get('send_email'))
        requested_ids = data.get('user_ids') or []

        if not title:
            return jsonify({'error': 'Title is required'}), 400

        enrolled_ids = {
            e.user_id for e in Enrollment.query.filter(
                Enrollment.course_id == course_id,
                Enrollment.status.in_(['approved', 'active', 'completed']),
            ).all()
        }
        if requested_ids:
            target_ids = [uid for uid in requested_ids if uid in enrolled_ids]
        else:
            target_ids = list(enrolled_ids)

        if not target_ids:
            return jsonify({'error': 'No matching enrolled students selected'}), 400

        notif_count = 0
        email_sent = 0
        email_failed = 0
        email_reason_sample = None
        users = User.query.filter(User.id.in_(target_ids)).all()
        for user in users:
            n = notify(
                user.id, kind='class_broadcast', title=title,
                body=body, severity=severity,
                url=f'/app#course-{course_id}',
                payload={'course_id': course_id, 'course_code': course.code},
            )
            if n:
                notif_count += 1
            if send_email_flag and user.email:
                result = send_email(
                    user.email,
                    subject=f'[{course.code or course.title}] {title}',
                    body_text=f'{body}\n\n— Sent from SkillPilot ({course.title})',
                    body_html=(f'<p>{body}</p>'
                               f'<hr><p style="color:#666;font-size:.9em;">Sent from '
                               f'SkillPilot — {course.title}</p>'),
                )
                if result.get('sent'):
                    email_sent += 1
                else:
                    email_failed += 1
                    email_reason_sample = email_reason_sample or result.get('reason')

        return jsonify({
            'success': True,
            'notifications_created': notif_count,
            'emails_sent': email_sent,
            'emails_failed': email_failed,
            'email_failure_reason': email_reason_sample,
            'targeted': len(target_ids),
        })
    except Exception as e:
        try: db.rollback()
        except Exception: pass
        print(f"Broadcast notify class error: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/courses/<course_id>/exams/<exam_id>/questions', methods=['GET'])
@admin_dashboard_required
def get_exam_questions(course_id, exam_id):
    """Get all questions for an exam"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import Exam, ExamQuestion
        
        exam = Exam.query.filter_by(id=exam_id, course_id=course_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        questions = ExamQuestion.query.filter_by(exam_id=exam_id).order_by(ExamQuestion.order_index).all()
        
        questions_list = [{
            'id': str(q.id),
            'question_text': q.question_text,
            'question_text_ar': getattr(q, 'question_text_ar', ''),
            'question_type': q.question_type,
            'options': q.options or [],
            'options_ar': getattr(q, 'options_ar', []),
            'correct_answer': q.correct_answer,
            'points': q.points or 1,
            'order_index': q.order_index
        } for q in questions]

        return jsonify({
            'questions': questions_list,
            'total': len(questions_list)
        })
    except Exception as e:
        print(f"Get exam questions error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# BULK USER UPLOAD
# ============================================

@super_admin_bp.route('/api/users/csv-template', methods=['GET'])
@admin_dashboard_required
def download_users_csv_template():
    """Download CSV template for bulk user upload"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['username', 'password', 'full_name', 'full_name_ar', 'email', 'phone', 'role'])
    writer.writerow(['john_doe', 'pass123', 'John Doe', '', 'john@example.com', '+968 1234 5678', 'student'])
    writer.writerow(['jane_smith', 'pass123', 'Jane Smith', '', 'jane@example.com', '', 'student'])
    writer.writerow(['ahmed_ali', 'pass123', 'Ahmed Ali', 'أحمد علي', 'ahmed@example.com', '', 'teacher'])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=bulk_users_template.csv'}
    )


@super_admin_bp.route('/api/users/bulk-upload', methods=['POST'])
@admin_dashboard_required
def bulk_upload_users():
    """Bulk create users from CSV file"""
    db_session = get_db()
    if not db_session:
        return jsonify({'error': 'Database not configured'}), 500

    try:
        from app.models import User
        from datetime import datetime

        if 'csv_file' not in request.files:
            return jsonify({'error': 'No CSV file uploaded'}), 400

        csv_file = request.files['csv_file']
        if not csv_file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV file'}), 400

        default_role = request.form.get('default_role', 'student')
        if default_role not in ['student', 'teacher', 'instructor', 'admin']:
            default_role = 'student'
        default_password = request.form.get('default_password', '')
        enroll_course_id = request.form.get('course_id', '')

        stream = io.StringIO(csv_file.stream.read().decode('utf-8-sig'))
        reader = csv.DictReader(stream)

        valid_roles = ['student', 'teacher', 'instructor', 'admin']
        results = []
        created_count = 0
        skipped_count = 0
        error_count = 0
        created_user_ids = []

        for row_num, row in enumerate(reader, start=2):
            row = {k.strip().lower(): v.strip() if v else '' for k, v in row.items() if k}

            full_name = row.get('full_name', '') or row.get('name', '') or row.get('student_name', '')
            username = row.get('username', '')
            password = row.get('password', '') or default_password
            email = row.get('email', '')
            phone = row.get('phone', '')
            full_name_ar = row.get('full_name_ar', '') or row.get('name_ar', '')
            role = row.get('role', '') or default_role

            if not full_name:
                results.append({'row': row_num, 'status': 'error', 'message': 'Missing name'})
                error_count += 1
                continue

            if not username:
                username = full_name.lower().replace(' ', '_')
                username = ''.join(c for c in username if c.isalnum() or c == '_')

            if not password:
                password = 'skill123'

            if role not in valid_roles:
                role = default_role

            existing = User.query.filter_by(username=username).first()
            if existing:
                base_username = username
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f"{base_username}_{counter}"
                    counter += 1

            password_hash = hashlib.sha256(password.encode()).hexdigest()

            user = User(
                username=username,
                password_hash=password_hash,
                full_name=full_name,
                full_name_ar=full_name_ar if full_name_ar else None,
                email=email if email else None,
                phone=phone if phone else None,
                role=role,
                is_active=True,
                is_approved=True,
                created_at=datetime.utcnow()
            )
            db_session.add(user)
            db_session.flush()
            created_user_ids.append(user.id)

            results.append({
                'row': row_num,
                'status': 'created',
                'username': username,
                'full_name': full_name,
                'role': role
            })
            created_count += 1

        if enroll_course_id and created_user_ids:
            from app.models import Enrollment, Course
            course = Course.query.get(enroll_course_id)
            if course:
                for uid in created_user_ids:
                    u = User.query.get(uid)
                    if u and u.role == 'student':
                        existing_enrollment = Enrollment.query.filter_by(user_id=uid, course_id=enroll_course_id).first()
                        if not existing_enrollment:
                            enrollment = Enrollment(
                                user_id=uid,
                                course_id=enroll_course_id,
                                enrolled_at=datetime.utcnow(),
                                status='approved',
                                progress_percent=0.0
                            )
                            db_session.add(enrollment)

        db_session.commit()

        return jsonify({
            'success': True,
            'message': f'Bulk upload complete: {created_count} created, {skipped_count} skipped, {error_count} errors',
            'summary': {
                'created': created_count,
                'skipped': skipped_count,
                'errors': error_count,
                'total_rows': created_count + skipped_count + error_count
            },
            'results': results
        })
    except Exception as e:
        db_session.rollback()
        print(f"Bulk upload error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# SYSTEM ADMINISTRATION (audit/health/backup/email/scheduled jobs/...)
# ============================================

import os as _os
import sys as _sys
import json as _json
import time as _time
import shutil as _shutil
import smtplib as _smtplib
import platform as _platform
import subprocess as _subprocess
import tempfile as _tempfile
from email.mime.text import MIMEText as _MIMEText
from datetime import datetime as _dt, timedelta as _td

_APP_BOOT_TIME = _time.time()


def _kv_get(key, default=None):
    from app.models import db as _db
    from app.models import KeyValueSetting
    row = _db.session.get(KeyValueSetting, key)
    if not row or row.value is None:
        return default
    try:
        return _json.loads(row.value)
    except Exception:
        return row.value


def _kv_set(key, value, actor=None):
    from app.models import db as _db
    from app.models import KeyValueSetting
    row = _db.session.get(KeyValueSetting, key)
    if not row:
        row = KeyValueSetting(key=key)
        _db.session.add(row)
    row.value = _json.dumps(value) if not isinstance(value, str) else value
    row.updated_by = actor or session.get('username') or 'system'
    _db.session.commit()
    return True


@super_admin_bp.route('/system', methods=['GET'])
@admin_dashboard_required
def system_admin_page():
    """Render the unified System Administration page."""
    return render_template('admin_system.html')


@super_admin_bp.route('/api/system/health', methods=['GET'])
@admin_dashboard_required
def system_health():
    """Server / DB / process health snapshot."""
    from app.models import db as _db
    from sqlalchemy import text as _sql_text
    health = {
        'app': {
            'status': 'ok',
            'uptime_seconds': int(_time.time() - _APP_BOOT_TIME),
            'python_version': _sys.version.split()[0],
            'platform': _platform.platform(),
            'pid': _os.getpid(),
            'now': _dt.utcnow().isoformat() + 'Z',
        },
        'database': {'status': 'unknown'},
        'disk': {},
        'process': {},
    }
    try:
        _db.session.execute(_sql_text('SELECT 1'))
        url = str(_db.engine.url)
        # Mask credentials
        if '@' in url:
            scheme, rest = url.split('://', 1) if '://' in url else ('', url)
            creds, host = rest.split('@', 1) if '@' in rest else ('', rest)
            url = f"{scheme}://***@{host}"
        health['database'] = {
            'status': 'ok',
            'dialect': _db.engine.dialect.name,
            'url': url,
        }
    except Exception as e:
        health['database'] = {'status': 'error', 'error': str(e)}

    try:
        usage = _shutil.disk_usage(_os.getcwd())
        health['disk'] = {
            'total_mb': usage.total // (1024 * 1024),
            'used_mb': usage.used // (1024 * 1024),
            'free_mb': usage.free // (1024 * 1024),
            'percent_used': round(usage.used * 100.0 / usage.total, 1) if usage.total else 0,
        }
    except Exception as e:
        health['disk'] = {'error': str(e)}

    try:
        import resource as _resource  # POSIX only
        ru = _resource.getrusage(_resource.RUSAGE_SELF)
        health['process'] = {
            'user_cpu_seconds': round(ru.ru_utime, 2),
            'system_cpu_seconds': round(ru.ru_stime, 2),
            'max_rss_kb': ru.ru_maxrss,
        }
    except Exception:
        pass

    return jsonify(health)


@super_admin_bp.route('/api/system/db-stats', methods=['GET'])
@admin_dashboard_required
def system_db_stats():
    """Row counts for the major tables admins care about."""
    from app.models import db as _db
    from app.models import (
        User, Course, Enrollment, Exam, Survey, AuditEvent,
        Organization, SsoConfiguration, ApiKey, DataRequest,
        ScheduledJobRun,
    )
    out = {}
    for label, model in [
        ('users', User), ('courses', Course), ('enrollments', Enrollment),
        ('exams', Exam), ('surveys', Survey),
        ('audit_events', AuditEvent), ('organizations', Organization),
        ('sso_configurations', SsoConfiguration), ('api_keys', ApiKey),
        ('data_requests', DataRequest), ('scheduled_jobs', ScheduledJobRun),
    ]:
        try:
            out[label] = _db.session.query(model).count()
        except Exception as e:
            out[label] = {'error': str(e)}
    # Role breakdown
    try:
        from sqlalchemy import func as _f
        roles = _db.session.query(User.role, _f.count(User.id)).group_by(User.role).all()
        out['users_by_role'] = {(r or 'unknown'): c for r, c in roles}
    except Exception as e:
        out['users_by_role'] = {'error': str(e)}
    return jsonify(out)


@super_admin_bp.route('/api/system/backup', methods=['GET'])
@admin_dashboard_required
def system_backup():
    """Download a database backup.

    SQLite -> raw file copy. Postgres -> pg_dump.
    Pass ?include_files=1 to receive a .zip bundle that also contains the
    uploads/materials directory and any generated certificate PDFs.
    """
    import zipfile as _zipfile
    from app.models import db as _db
    url = _db.engine.url
    dialect = _db.engine.dialect.name
    ts = _dt.utcnow().strftime('%Y%m%d_%H%M%S')
    include_files = request.args.get('include_files', '0') == '1'

    def _produce_db_dump():
        """Returns (bytes, suggested_extension)."""
        if dialect == 'sqlite':
            db_path = url.database
            if not db_path or not _os.path.exists(db_path):
                raise FileNotFoundError('SQLite file not found')
            with open(db_path, 'rb') as f:
                return f.read(), 'sqlite'
        if dialect in ('postgresql', 'postgres'):
            if not _shutil.which('pg_dump'):
                raise RuntimeError('pg_dump not available on this server')
            env = _os.environ.copy()
            if url.password:
                env['PGPASSWORD'] = url.password
            cmd = ['pg_dump', '--no-owner', '--no-privileges']
            if url.host:    cmd += ['-h', url.host]
            if url.port:    cmd += ['-p', str(url.port)]
            if url.username: cmd += ['-U', url.username]
            cmd += [url.database]
            proc = _subprocess.run(cmd, env=env, capture_output=True, timeout=180)
            if proc.returncode != 0:
                raise RuntimeError('pg_dump failed: ' + proc.stderr.decode('utf-8', 'replace')[:2000])
            return proc.stdout, 'sql'
        raise RuntimeError(f'Backup not implemented for dialect {dialect}')

    try:
        dump_bytes, ext = _produce_db_dump()
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 501

    if not include_files:
        return Response(
            dump_bytes,
            mimetype='application/octet-stream' if ext == 'sqlite' else 'application/sql',
            headers={'Content-Disposition': f'attachment; filename=skillpilot_backup_{ts}.{ext}'},
        )

    # Build zip: db dump + uploads/materials + uploads/certificates
    buf = io.BytesIO()
    with _zipfile.ZipFile(buf, 'w', _zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f'database/skillpilot_backup_{ts}.{ext}', dump_bytes)
        for sub in ('uploads/materials', 'uploads/certificates', 'uploads'):
            if not _os.path.isdir(sub):
                continue
            base_abs = _os.path.abspath(sub)
            for root, _dirs, files in _os.walk(sub, followlinks=False):
                for fname in files:
                    full = _os.path.join(root, fname)
                    try:
                        if _os.path.islink(full):
                            continue
                        full_abs = _os.path.abspath(full)
                        # Defensive: only include files that resolve under the intended base
                        if _os.path.commonpath([base_abs, full_abs]) != base_abs:
                            continue
                        zf.write(full, arcname=full)
                    except Exception:
                        continue
    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype='application/zip',
        headers={'Content-Disposition': f'attachment; filename=skillpilot_backup_{ts}.zip'},
    )


@super_admin_bp.route('/api/system/email-config', methods=['GET'])
@admin_dashboard_required
def system_email_config_get():
    cfg = _kv_get('smtp_config', {}) or {}
    safe = {k: v for k, v in cfg.items() if k != 'password'}
    safe['password_set'] = bool(cfg.get('password'))
    return jsonify(safe)


@super_admin_bp.route('/api/system/email-config', methods=['PUT'])
@admin_dashboard_required
def system_email_config_set():
    data = request.get_json() or {}
    existing = _kv_get('smtp_config', {}) or {}
    cfg = {
        'host': (data.get('host') or existing.get('host') or '').strip(),
        'port': int(data.get('port') or existing.get('port') or 587),
        'username': (data.get('username') or existing.get('username') or '').strip(),
        'from_email': (data.get('from_email') or existing.get('from_email') or '').strip(),
        'use_tls': bool(data.get('use_tls', existing.get('use_tls', True))),
    }
    # Only overwrite password if explicitly provided
    new_pw = data.get('password')
    if new_pw is not None and new_pw != '':
        cfg['password'] = new_pw
    elif 'password' in existing:
        cfg['password'] = existing['password']
    _kv_set('smtp_config', cfg)
    return jsonify({'success': True})


@super_admin_bp.route('/api/system/email-test', methods=['POST'])
@admin_dashboard_required
def system_email_test():
    """Send a real test email to a recipient using the saved SMTP config."""
    data = request.get_json() or {}
    to_addr = (data.get('to') or '').strip()
    if not to_addr:
        return jsonify({'error': 'Recipient (to) required'}), 400
    cfg = _kv_get('smtp_config', {}) or {}
    if not cfg.get('host') or not cfg.get('from_email'):
        return jsonify({'error': 'SMTP host and from_email must be configured first'}), 400
    msg = _MIMEText(
        'This is a test message from SkillPilot System Administration.\n'
        'If you received this, your outbound email is configured correctly.'
    )
    msg['Subject'] = 'SkillPilot SMTP test'
    msg['From'] = cfg['from_email']
    msg['To'] = to_addr
    try:
        with _smtplib.SMTP(cfg['host'], int(cfg.get('port') or 587), timeout=15) as s:
            if cfg.get('use_tls', True):
                s.starttls()
            if cfg.get('username') and cfg.get('password'):
                s.login(cfg['username'], cfg['password'])
            s.send_message(msg)
        return jsonify({'success': True, 'message': f'Test email sent to {to_addr}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/api/system/email-test-connection', methods=['POST'])
@admin_dashboard_required
def system_email_test_connection():
    """Verify the saved SMTP config by opening a connection and (optionally)
    logging in — no email is actually sent. Useful as a quick "did I type
    the right password?" check while the admin is still on the form.
    """
    cfg = _kv_get('smtp_config', {}) or {}
    if not cfg.get('host'):
        return jsonify({'error': 'SMTP host must be configured first'}), 400
    host = cfg['host']
    port = int(cfg.get('port') or 587)
    use_tls = bool(cfg.get('use_tls', True))
    username = cfg.get('username') or ''
    password = cfg.get('password') or ''
    try:
        with _smtplib.SMTP(host, port, timeout=15) as s:
            s.ehlo()
            if use_tls:
                s.starttls()
                s.ehlo()
            authed = False
            if username and password:
                s.login(username, password)
                authed = True
        return jsonify({
            'success': True,
            'message': (
                f'Connected to {host}:{port}'
                + (' with STARTTLS' if use_tls else '')
                + (' and authenticated' if authed else ' (no credentials, anonymous)')
                + '.'
            ),
        })
    except Exception as e:
        return jsonify({'error': f'{type(e).__name__}: {e}'}), 500


@super_admin_bp.route('/api/system/scheduled-jobs', methods=['GET'])
@admin_dashboard_required
def system_scheduled_jobs():
    from app.models import db as _db
    from app.models import ScheduledJobRun
    rows = _db.session.query(ScheduledJobRun).order_by(ScheduledJobRun.job_name).all()
    return jsonify({
        'jobs': [{
            'job_name': r.job_name,
            'locked_until': r.locked_until.isoformat() + 'Z' if r.locked_until else None,
            'locked_by': r.locked_by,
            'last_started_at': r.last_started_at.isoformat() + 'Z' if r.last_started_at else None,
            'last_success_at': r.last_success_at.isoformat() + 'Z' if r.last_success_at else None,
            'last_error_at': r.last_error_at.isoformat() + 'Z' if r.last_error_at else None,
            'last_error': r.last_error,
            'run_count': r.run_count or 0,
            'success_count': r.success_count or 0,
            'failure_count': r.failure_count or 0,
        } for r in rows]
    })


@super_admin_bp.route('/api/system/audit', methods=['GET'])
@admin_dashboard_required
def system_audit_events():
    from app.models import db as _db
    from app.models import AuditEvent
    limit = min(int(request.args.get('limit', 100) or 100), 500)
    q = _db.session.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)
    out = []
    for e in q.all():
        out.append({
            'id': e.id,
            'action': e.action,
            'actor_user_id': e.actor_user_id,
            'resource_type': e.resource_type,
            'resource_id': e.resource_id,
            'severity': e.severity,
            'ip_address': e.ip_address,
            'created_at': e.created_at.isoformat() + 'Z' if e.created_at else None,
            'details': e.details,
        })
    return jsonify({'events': out, 'count': len(out)})


@super_admin_bp.route('/api/system/role-update', methods=['POST'])
@admin_dashboard_required
def system_role_update():
    """Change a user's role. Admins cannot create new super_admins (only existing super_admin can)."""
    from app.models import db as _db
    from app.models import User
    data = request.get_json() or {}
    user_id = (data.get('user_id') or '').strip()
    new_role = (data.get('role') or '').strip().lower()
    valid = ['student', 'teacher', 'instructor', 'admin', 'institution_admin', 'super_admin', 'superadmin']
    if new_role not in valid:
        return jsonify({'error': 'Invalid role'}), 400
    if new_role in ('super_admin', 'superadmin') and not is_superadmin_role():
        return jsonify({'error': 'Only a super admin can grant super_admin role'}), 403
    user = _db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.role = new_role
    _db.session.commit()
    return jsonify({'success': True, 'user_id': user.id, 'role': user.role})
