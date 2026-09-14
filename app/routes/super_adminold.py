"""
Super Admin Routes - Dedicated login and dashboard for super admins only
Single-institution mode - manages all users and courses without institution filtering
"""

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from functools import wraps
import hashlib

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

        # Don't allow deleting super_admin
        if user.role == 'super_admin':
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
        if 'is_published' in data:
            course.is_published = data['is_published']

        db.commit()

        return jsonify({
            'success': True,
            'message': 'Course updated successfully'
        })
    except Exception as e:
        db.rollback()
        print(f"Update course error: {e}")
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
            'custom_css': getattr(settings, 'custom_css', '') or ''
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

    providers = [
        {'id': 'openai', 'name': 'OpenAI', 'key': 'OPENAI_API_KEY', 'models': ['gpt-4.1', 'gpt-4.1-mini', 'gpt-4o', 'gpt-4-turbo'], 'description': 'GPT models for chat and content generation'},
        {'id': 'claude', 'name': 'Claude', 'key': 'CLAUDE_API_KEY', 'models': ['claude-sonnet-4.5', 'claude-opus-4.1', 'claude-haiku-4.5'], 'description': 'Anthropic Claude for advanced reasoning'},
        {'id': 'gemini', 'name': 'Gemini', 'key': 'GEMINI_API_KEY', 'models': ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'], 'description': 'Google Gemini for multimodal AI'},
        {'id': 'perplexity', 'name': 'Perplexity', 'key': 'PERPLEXITY_API_KEY', 'models': ['sonar-pro', 'sonar', 'sonar-reasoning-pro', 'sonar-reasoning'], 'description': 'Perplexity for real-time web search AI'},
        {'id': 'grok', 'name': 'Grok', 'key': 'GROK_API_KEY', 'models': ['grok-3', 'grok-3-mini'], 'description': 'xAI Grok for conversational AI'},
        {'id': 'deepseek', 'name': 'DeepSeek', 'key': 'DEEPSEEK_API_KEY', 'models': ['deepseek-chat', 'deepseek-reasoner'], 'description': 'DeepSeek V3.2 for chat and reasoning'}
    ]

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
            db.session.add(credential)
        
        if api_key:
            credential.encrypted_key = encrypt_api_key(api_key)
        
        credential.is_active = data.get('is_active', True)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{ApiCredential.PROVIDERS[provider_id]["name"]} API key saved successfully'
        })
    except Exception as e:
        db.session.rollback()
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
            db.session.delete(credential)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'{ApiCredential.PROVIDERS[provider_id]["name"]} API key deleted'
            })
        else:
            return jsonify({'error': 'Credential not found'}), 404
    except Exception as e:
        db.session.rollback()
        print(f"Delete AI credential error: {e}")
        return jsonify({'error': str(e)}), 500


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
    writer = csv.writer(output)
    writer.writerow(['name'])
    writer.writerow(['John Smith'])
    writer.writerow(['Jane Doe'])
    writer.writerow(['Ahmed Al-Rashid'])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=certificate_template.csv'}
    )


@super_admin_bp.route('/api/certificates/csv-generate', methods=['POST'])
@super_admin_required
def csv_bulk_generate_certificates():
    """Generate certificates from CSV file - supports both registered and non-registered students"""
    from datetime import datetime
    import csv
    import io
    import uuid
    import hashlib
    
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500

    # Check if file was uploaded - support both 'file' and 'csv_file' field names
    file = request.files.get('file') or request.files.get('csv_file')
    course_id = request.form.get('course_id')
    issue_date_str = request.form.get('issue_date')
    
    if not file or file.filename == '':
        return jsonify({'error': 'No CSV file uploaded'}), 400
    
    if not course_id:
        return jsonify({'error': 'Course ID is required'}), 400

    try:
        from app.models import User, Course, Enrollment
        
        # Verify course exists
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Parse issue date or use current date
        if issue_date_str:
            try:
                issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d')
            except ValueError:
                issue_date = datetime.utcnow()
        else:
            issue_date = datetime.utcnow()
        
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)
        
        # Find the name column (supports multiple formats)
        name_column = None
        email_column = None
        fieldnames = reader.fieldnames or []
        
        for col in ['name', 'student_name', 'full_name', 'Name', 'Student_Name', 'Full_Name', 'FULL_NAME', 'NAME', 'STUDENT_NAME']:
            if col in fieldnames:
                name_column = col
                break
        
        for col in ['email', 'Email', 'EMAIL', 'student_email', 'Student_Email']:
            if col in fieldnames:
                email_column = col
                break
        
        if not name_column:
            return jsonify({'error': 'CSV must have a column named "name", "student_name", or "full_name"'}), 400
        
        results = []
        success_count = 0
        new_student_count = 0
        already_issued_count = 0
        
        for row in reader:
            student_name = row.get(name_column, '').strip()
            student_email = row.get(email_column, '').strip() if email_column else None
            
            if not student_name:
                continue
            
            is_new_student = False
            student = None
            
            print(f"Processing CSV row: '{student_name}'")  # Debug log
            
            # Expire all cached objects to ensure fresh database queries
            db.expire_all()
            
            # Try to find existing student by EXACT name match only (case-insensitive)
            from sqlalchemy import func
            matching_students = db.query(User).filter(
                func.lower(User.full_name) == func.lower(student_name)
            ).all()
            
            if matching_students:
                student = matching_students[0]
                print(f"  -> Found existing student: {student.full_name} (id: {student.id})")
            
            # If not found, do NOT use email matching (emails may be reused/fake in CSV)
            # Just create a new student for unmatched names
            
            if not student:
                print(f"  -> No match found, will create new student")
            
            # If student not found, create a new student account
            if not student:
                is_new_student = True
                new_student_count += 1
                # Generate a unique username from the name
                base_username = student_name.lower().replace(' ', '_').replace("'", '')[:20]
                username = base_username
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                # Create password hash (default password is the username)
                password_hash = hashlib.sha256(username.encode()).hexdigest()
                
                student = User(
                    id=str(uuid.uuid4()),
                    username=username,
                    password_hash=password_hash,
                    full_name=student_name,
                    email=student_email or f"{username}@generated.local",
                    role='student',
                    is_active=True
                )
                db.add(student)
                db.flush()  # Get the ID
            
            # Find or create enrollment
            enrollment = Enrollment.query.filter_by(
                user_id=student.id,
                course_id=course_id
            ).first()
            
            if not enrollment:
                # Create enrollment
                enrollment = Enrollment(
                    id=str(uuid.uuid4()),
                    user_id=student.id,
                    course_id=course_id,
                    status='completed',
                    progress_percent=100.0
                )
                db.add(enrollment)
                db.flush()
            
            if enrollment.certificate_issued:
                already_issued_count += 1
                results.append({
                    'name': student_name,
                    'status': 'existing',
                    'reason': 'Certificate already issued',
                    'enrollment_id': str(enrollment.id)
                })
            else:
                # Issue certificate
                enrollment.certificate_issued = True
                enrollment.certificate_issued_at = issue_date
                enrollment.certificate_status = 'issued'
                enrollment.status = 'completed'
                enrollment.progress_percent = 100.0
                
                success_count += 1
                results.append({
                    'name': student_name,
                    'status': 'success',
                    'student_id': str(student.id),
                    'enrollment_id': str(enrollment.id),
                    'is_new_student': is_new_student
                })
        
        db.commit()
        
        # Collect all enrollment IDs (both new and existing) for ZIP generation
        all_enrollment_ids = [r['enrollment_id'] for r in results if 'enrollment_id' in r]
        
        if not all_enrollment_ids:
            return jsonify({
                'success': True,
                'message': 'No certificates to generate',
                'success_count': 0,
                'new_student_count': new_student_count,
                'already_issued_count': already_issued_count,
                'results': results
            })
        
        # Generate ZIP file with all certificates
        import zipfile
        from flask import send_file
        
        zip_buffer = io.BytesIO()
        used_filenames = {}
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for enrollment_id in all_enrollment_ids:
                enrollment = Enrollment.query.filter_by(id=enrollment_id).first()
                if not enrollment:
                    continue
                
                student = User.query.filter_by(id=enrollment.user_id).first()
                course_obj = Course.query.filter_by(id=enrollment.course_id).first()
                
                if not student or not course_obj:
                    continue
                
                try:
                    pdf_buffer = generate_certificate_pdf(enrollment, student, course_obj)
                    
                    student_name_safe = student.full_name or student.username or 'Student'
                    course_title_safe = course_obj.title or course_obj.code or 'Course'
                    safe_name = ''.join(c for c in student_name_safe if c.isalnum() or c in ' -_').strip()
                    safe_course = ''.join(c for c in course_title_safe if c.isalnum() or c in ' -_').strip()[:30]
                    base_filename = f"Certificate_{safe_name}_{safe_course}"
                    
                    # Handle duplicate filenames by adding a counter
                    if base_filename in used_filenames:
                        used_filenames[base_filename] += 1
                        filename = f"{base_filename}_{used_filenames[base_filename]}.pdf"
                    else:
                        used_filenames[base_filename] = 1
                        filename = f"{base_filename}.pdf"
                    
                    zip_file.writestr(filename, pdf_buffer.read())
                except Exception as e:
                    print(f"Error generating certificate for {enrollment_id}: {e}")
                    continue
        
        zip_buffer.seek(0)
        
        course_name_safe = ''.join(c for c in (course.title or course.code or 'Course') if c.isalnum() or c in ' -_').strip()[:30]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"Certificates_{course_name_safe}_{timestamp}.zip"
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
    except Exception as e:
        db.rollback()
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


def generate_certificate_pdf(enrollment, student, course):
    """Generate a PDF certificate and return the buffer - matches the original class_management design"""
    import io
    import os
    from datetime import datetime
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.colors import HexColor, black
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import qrcode
    
    # Get exam results for grade calculation
    from app.models import Exam, ExamResult
    exams = Exam.query.filter_by(course_id=course.id).all()
    exam_ids = [e.id for e in exams]
    exam_results = ExamResult.query.filter(
        ExamResult.user_id == enrollment.user_id,
        ExamResult.exam_id.in_(exam_ids)
    ).all() if exam_ids else []
    
    avg_score = sum(r.score or 0 for r in exam_results) / len(exam_results) if exam_results else 0
    final_grade = enrollment.final_grade or round(avg_score, 1)
    
    cert_number = f"CERT-{str(enrollment.id)[:8].upper()}"
    
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
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(page_width / 2, page_height - 90, "CERTIFICATE")
    
    c.setFillColor(gold_color)
    c.setFont("Helvetica", 16)
    c.drawCentredString(page_width / 2, page_height - 115, "OF COMPLETION")
    
    c.setStrokeColor(gold_color)
    c.setLineWidth(2)
    c.line(page_width/2 - 120, page_height - 125, page_width/2 + 120, page_height - 125)
    
    # Body
    c.setFillColor(black)
    c.setFont("Helvetica", 14)
    c.drawCentredString(page_width / 2, page_height - 160, "This is to certify that")
    
    student_name = (student.full_name or student.username or 'Unknown Student') if student else 'Unknown Student'
    c.setFillColor(primary_color)
    
    max_name_width = page_width - 120
    name_font_size = 28
    c.setFont("Helvetica-Bold", name_font_size)
    name_width = c.stringWidth(student_name, "Helvetica-Bold", name_font_size)
    
    while name_width > max_name_width and name_font_size > 16:
        name_font_size -= 2
        c.setFont("Helvetica-Bold", name_font_size)
        name_width = c.stringWidth(student_name, "Helvetica-Bold", name_font_size)
    
    c.drawCentredString(page_width / 2, page_height - 195, student_name)
    
    c.setStrokeColor(gold_color)
    c.setLineWidth(1)
    underline_width = min(name_width + 40, max_name_width)
    c.line(page_width/2 - underline_width/2, page_height - 205, page_width/2 + underline_width/2, page_height - 205)
    
    c.setFillColor(black)
    c.setFont("Helvetica", 14)
    c.drawCentredString(page_width / 2, page_height - 235, "has successfully completed the training program")
    
    course_title = (course.title or course.code or 'Training Program') if course else 'Training Program'
    c.setFillColor(dark_blue)
    c.setFont("Helvetica-Bold", 22)
    
    if len(course_title) > 50:
        words = course_title.split()
        mid = len(words) // 2
        line1 = ' '.join(words[:mid])
        line2 = ' '.join(words[mid:])
        c.drawCentredString(page_width / 2, page_height - 270, line1)
        c.drawCentredString(page_width / 2, page_height - 295, line2)
    else:
        c.drawCentredString(page_width / 2, page_height - 275, course_title)
    
    # Signature section
    sig_y = 120
    
    # LEFT side - Chair Signature
    signature_path = os.path.join(images_path, 'signature.png')
    if os.path.exists(signature_path):
        try:
            c.drawImage(signature_path, 80, sig_y - 5, width=120, height=50, preserveAspectRatio=True, mask='auto')
        except:
            pass
    
    # LEFT side - Chair Stamp (centered above signature)
    chair_stamp_path = os.path.join(images_path, 'aiac-stamp.png')
    if os.path.exists(chair_stamp_path):
        try:
            # Centered above signature (signature centered at x=140)
            stamp_width = 80
            stamp_height = 80
            stamp_x = 140 - stamp_width/2
            stamp_y = sig_y + 55
            c.drawImage(chair_stamp_path, stamp_x, stamp_y, width=stamp_width, height=stamp_height, preserveAspectRatio=True)
        except:
            pass
    
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(60, sig_y, 220, sig_y)
    
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(140, sig_y - 15, "Prof. Rabie A. Ramadan")
    c.setFont("Helvetica", 9)
    c.drawCentredString(140, sig_y - 28, "AI Applications Chair")
    c.drawCentredString(140, sig_y - 40, "University of Nizwa")
    
    # CENTER - Date of Issue
    issue_date = enrollment.certificate_issued_at
    if issue_date:
        date_str = issue_date.strftime("%B %d, %Y")
    else:
        date_str = datetime.utcnow().strftime("%B %d, %Y")
    
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    c.drawCentredString(page_width / 2, sig_y + 100, "Date of Issue")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(page_width / 2, sig_y + 82, date_str)
    
    # CENTER - QR Code for verification
    qr_size = 90
    verification_url = f"https://skillpilot.replit.app/verify/{cert_number}"
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
    c.setFont("Helvetica", 8)
    c.drawCentredString(center_x, sig_y - 30, "Scan to Verify")
    
    # Certificate number (below QR)
    c.setFont("Helvetica", 9)
    c.setFillColor(secondary_color)
    c.drawCentredString(page_width / 2, sig_y - 45, f"Certificate No: {cert_number}")
    
    # RIGHT side - Academy Director Signature
    signature2_path = os.path.join(images_path, 'signature2.png')
    if os.path.exists(signature2_path):
        try:
            c.drawImage(signature2_path, page_width - 200, sig_y - 5, width=120, height=50, preserveAspectRatio=True, mask='auto')
        except:
            pass
    
    # RIGHT side - NATD Stamp
    natd_stamp_path = os.path.join(images_path, 'NATD_stamp.png')
    if os.path.exists(natd_stamp_path):
        try:
            c.drawImage(natd_stamp_path, page_width - 180, sig_y + 35, width=110, height=110, preserveAspectRatio=True, mask='auto')
        except:
            pass
    
    # Signature line for NATD (right side)
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(page_width - 220, sig_y, page_width - 60, sig_y)
    
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(page_width - 140, sig_y - 15, "Academy Director")
    c.setFont("Helvetica", 9)
    c.drawCentredString(page_width - 140, sig_y - 28, "Nizwa Academy for")
    c.drawCentredString(page_width - 140, sig_y - 40, "Training and Development")
    
    # Footer
    c.setFillColor(HexColor('#cccccc'))
    c.setFont("Helvetica", 8)
    c.drawCentredString(page_width / 2, 35, "This certificate is digitally generated and verifiable. Any unauthorized alteration renders this certificate void.")
    
    c.setFillColor(secondary_color)
    c.setFont("Helvetica", 8)
    c.drawCentredString(page_width / 2, 22, "University of Nizwa - AI Applications Chair | Nizwa Academy for Training and Development")
    
    c.save()
    buffer.seek(0)
    return buffer


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
            
            exams_list.append({
                'id': str(exam.id),
                'title': exam.title,
                'title_ar': getattr(exam, 'title_ar', ''),
                'description': exam.description,
                'exam_type': exam.exam_type,
                'passing_threshold': exam.passing_threshold,
                'max_attempts': exam.max_attempts,
                'time_limit_minutes': exam.time_limit_minutes,
                'is_published': exam.is_published,
                'shuffle_questions': getattr(exam, 'shuffle_questions', False),
                'shuffle_answers': getattr(exam, 'shuffle_answers', False),
                'total_submissions': total_submissions,
                'passed_count': passed_count
            })

        return jsonify({'exams': exams_list})
    except Exception as e:
        print(f"Get course exams error: {e}")
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
        if 'description' in data:
            exam.description = data['description']
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
        
        return jsonify({
            'success': True,
            'exam': {'id': str(exam.id), 'title': exam.title}
        })
    except Exception as e:
        db.rollback()
        print(f"Create exam error: {e}")
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
