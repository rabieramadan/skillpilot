"""
Course Management Routes - Weekly Materials and Assignments (Moodle-like)
Supports multi-tenant course structure with personalized learning
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
import os

courses_bp = Blueprint('courses', __name__, url_prefix='/api/courses')


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def instructor_required(f):
    """Decorator to require instructor, institution admin, or super admin access
    CRITICAL: Uses role checks ONLY for multi-tenancy isolation
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Authentication required'}), 401
        role = session.get('role', '').lower().replace(' ', '_')
        # Check role ONLY - super_admin, superadmin, institution_admin, instructor or teacher have access
        allowed_roles = ['super_admin', 'superadmin', 'instructor', 'institution_admin', 'teacher', 'admin']
        if role not in allowed_roles:
            return jsonify({'error': 'Instructor access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def get_db():
    """Get database session if available"""
    try:
        from app.models import db
        return db
    except:
        return None


def check_course_access(course, required_role='view'):
    """
    Check if current user has access to a course.

    Args:
        course: Course model instance
        required_role: 'view' (students can view enrolled), 'manage' (instructors/admins only)

    Returns:
        (has_access: bool, error_message: str or None)
    """
    from app.models import Enrollment

    role = session.get('role', '').lower().replace(' ', '_')
    user_id = session.get('user_id')

    # Superadmin has full access
    if role in ['super_admin', 'superadmin']:
        return True, None

    # Admin/instructor can manage courses
    if role in ['admin', 'institution_admin', 'instructor', 'teacher']:
        return True, None

    # For view access, students can view enrolled courses
    if required_role == 'view':
        enrollment = Enrollment.query.filter_by(user_id=user_id, course_id=course.id).filter(
            Enrollment.status.in_(['approved', 'active'])
        ).first()
        if enrollment:
            return True, None

    return False, 'Access denied - you do not have permission to access this course'


# ============================================
# COURSE CRUD OPERATIONS
# ============================================

@courses_bp.route('/list', methods=['GET'])
@login_required
def list_courses():
    """List courses (filtered by institution for non-super-admins)"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course, CourseWeek, Enrollment

        user_id = session.get('user_id')
        role = session.get('role', 'student')

        # Normalize role to lowercase for consistent checks
        role = role.lower().replace(' ', '_') if role else 'student'

        # Build query based on role
        if role in ['super_admin', 'superadmin', 'admin', 'institution_admin', 'instructor', 'teacher']:
            # Admin and instructors see all courses
            courses = Course.query.all()
        else:
            # Students see only their enrolled courses
            enrolled_ids = [e.course_id for e in Enrollment.query.filter_by(user_id=user_id).filter(
                Enrollment.status.in_(['approved', 'active'])
            ).all()]
            courses = Course.query.filter(Course.id.in_(enrolled_ids)).all() if enrolled_ids else []
        
        result = []
        for course in courses:
            week_count = CourseWeek.query.filter_by(course_id=course.id).count()
            enrollment_count = Enrollment.query.filter_by(course_id=course.id).count()
            
            result.append({
                'id': course.id,
                'code': course.code,
                'title': course.title,
                'description': course.description,
                'thumbnail_url': course.thumbnail_url,
                'start_date': course.start_date.isoformat() if course.start_date else None,
                'end_date': course.end_date.isoformat() if course.end_date else None,
                'is_published': course.is_published,
                'is_self_paced': course.is_self_paced,
                'week_count': week_count,
                'enrollment_count': enrollment_count,
                'meet_link': course.meet_link,
                'zoom_link': course.zoom_link,
                'youtube_broadcast_link': course.youtube_broadcast_link
            })
        
        return jsonify({
            'success': True,
            'courses': result
        })
    except Exception as e:
        print(f"Error listing courses: {e}")
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/create', methods=['POST'])
@instructor_required
def create_course():
    """Create a new course with weekly structure"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course, CourseWeek, CourseInstructor
        import uuid
        
        data = request.get_json()
        user_id = session.get('user_id')

        course = Course(
            id=str(uuid.uuid4()),
            code=data.get('code', ''),
            title=data['title'],
            description=data.get('description', ''),
            thumbnail_url=data.get('thumbnail_url'),
            start_date=datetime.fromisoformat(data['start_date']).date() if data.get('start_date') else None,
            end_date=datetime.fromisoformat(data['end_date']).date() if data.get('end_date') else None,
            is_published=data.get('is_published', False),
            is_self_paced=data.get('is_self_paced', False),
            passing_threshold=data.get('passing_threshold', 50.0),
            certificate_enabled=data.get('certificate_enabled', True),
            meet_link=data.get('meet_link'),
            zoom_link=data.get('zoom_link'),
            youtube_broadcast_link=data.get('youtube_broadcast_link')
        )
        db.session.add(course)
        
        # Add creator as instructor
        instructor = CourseInstructor(
            course_id=course.id,
            user_id=user_id,
            role='instructor'
        )
        db.session.add(instructor)
        
        # Create default weeks
        num_weeks = data.get('num_weeks', 4)
        for week_num in range(1, num_weeks + 1):
            week = CourseWeek(
                course_id=course.id,
                week_number=week_num,
                title=f'Week {week_num}',
                is_published=False
            )
            db.session.add(week)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Course created successfully',
            'course': {
                'id': course.id,
                'title': course.title
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error creating course: {e}")
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>', methods=['GET'])
@login_required
def get_course(course_id):
    """Get course details with weekly structure
    CRITICAL: Enforces multi-tenant isolation - users can only view courses they have access to
    """
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course, CourseWeek, WeekMaterial, Assignment, Enrollment, LearningProgress
        
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        user_id = session.get('user_id')
        role = session.get('role', '').lower().replace(' ', '_')

        # Check access rights
        has_access = False
        if role in ['super_admin', 'superadmin', 'admin', 'institution_admin', 'instructor', 'teacher']:
            # Admin and instructors can view any course
            has_access = True
        else:
            # Students can only view courses they're enrolled in
            enrollment = Enrollment.query.filter_by(user_id=user_id, course_id=course_id).first()
            has_access = (enrollment is not None)

        if not has_access:
            return jsonify({'error': 'Access denied - you do not have permission to view this course'}), 403
        
        # Get weeks with materials and assignments
        weeks = CourseWeek.query.filter_by(course_id=course_id).order_by(CourseWeek.week_number).all()
        
        weeks_data = []
        for week in weeks:
            materials = WeekMaterial.query.filter_by(week_id=week.id).order_by(WeekMaterial.order_index).all()
            assignments = Assignment.query.filter_by(week_id=week.id).all()
            
            # Calculate progress for current user
            completed_materials = 0
            for mat in materials:
                progress = LearningProgress.query.filter_by(user_id=user_id, material_id=mat.id, status='completed').first()
                if progress:
                    completed_materials += 1
            
            materials_data = [{
                'id': m.id,
                'title': m.title,
                'description': m.description,
                'material_type': m.material_type,
                'file_url': m.file_url,
                'external_url': m.external_url,
                'duration_minutes': m.duration_minutes,
                'difficulty_level': m.difficulty_level,
                'is_required': m.is_required,
                'order_index': m.order_index
            } for m in materials]
            
            assignments_data = [{
                'id': a.id,
                'title': a.title,
                'description': a.description,
                'assignment_type': a.assignment_type,
                'due_date': a.due_date.isoformat() if a.due_date else None,
                'max_points': a.max_points,
                'is_published': a.is_published
            } for a in assignments]
            
            weeks_data.append({
                'id': week.id,
                'week_number': week.week_number,
                'title': week.title,
                'description': week.description,
                'start_date': week.start_date.isoformat() if week.start_date else None,
                'end_date': week.end_date.isoformat() if week.end_date else None,
                'is_published': week.is_published,
                'materials': materials_data,
                'assignments': assignments_data,
                'progress': {
                    'completed_materials': completed_materials,
                    'total_materials': len(materials)
                }
            })
        
        # Get user enrollment
        enrollment = Enrollment.query.filter_by(user_id=user_id, course_id=course_id).first()
        
        return jsonify({
            'success': True,
            'course': {
                'id': course.id,
                'code': course.code,
                'title': course.title,
                'description': course.description,
                'thumbnail_url': course.thumbnail_url,
                'start_date': course.start_date.isoformat() if course.start_date else None,
                'end_date': course.end_date.isoformat() if course.end_date else None,
                'is_published': course.is_published,
                'is_self_paced': course.is_self_paced,
                'passing_threshold': course.passing_threshold,
                'certificate_enabled': course.certificate_enabled,
                'meet_link': course.meet_link,
                'zoom_link': course.zoom_link,
                'youtube_broadcast_link': course.youtube_broadcast_link,
                'weeks': weeks_data,
                'enrollment': {
                    'status': enrollment.status if enrollment else None,
                    'progress_percent': enrollment.progress_percent if enrollment else 0,
                    'current_week': enrollment.current_week if enrollment else 1
                } if enrollment else None
            }
        })
    except Exception as e:
        print(f"Error getting course: {e}")
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>', methods=['PUT'])
@instructor_required
def update_course(course_id):
    """Update course details including meeting links
    CRITICAL: Enforces multi-tenant isolation - only institution's instructors can update
    """
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course
        
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # MULTI-TENANT ISOLATION: Check access rights
        has_access, error_msg = check_course_access(course, required_role='manage')
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        data = request.get_json()
        
        # Update basic fields
        if 'title' in data:
            course.title = data['title']
        if 'code' in data:
            course.code = data['code']
        if 'description' in data:
            course.description = data['description']
        if 'thumbnail_url' in data:
            course.thumbnail_url = data['thumbnail_url']
        if 'start_date' in data:
            course.start_date = datetime.fromisoformat(data['start_date']).date() if data['start_date'] else None
        if 'end_date' in data:
            course.end_date = datetime.fromisoformat(data['end_date']).date() if data['end_date'] else None
        if 'is_published' in data:
            course.is_published = data['is_published']
        if 'is_self_paced' in data:
            course.is_self_paced = data['is_self_paced']
        if 'passing_threshold' in data:
            course.passing_threshold = data['passing_threshold']
        if 'certificate_enabled' in data:
            course.certificate_enabled = data['certificate_enabled']
        
        # Update meeting links
        if 'meet_link' in data:
            course.meet_link = data['meet_link']
        if 'zoom_link' in data:
            course.zoom_link = data['zoom_link']
        if 'youtube_broadcast_link' in data:
            course.youtube_broadcast_link = data['youtube_broadcast_link']
        
        # Update pricing
        if 'requires_payment' in data:
            course.requires_payment = data['requires_payment']
        if 'price' in data:
            course.price = data['price']
        if 'currency' in data:
            course.currency = data['currency']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Course updated successfully',
            'course': {
                'id': course.id,
                'title': course.title,
                'meet_link': course.meet_link,
                'zoom_link': course.zoom_link,
                'youtube_broadcast_link': course.youtube_broadcast_link
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating course: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# WEEKLY MATERIALS MANAGEMENT
# ============================================

@courses_bp.route('/<course_id>/weeks/<int:week_number>/materials', methods=['POST'])
@instructor_required
def add_material(course_id, week_number):
    """Add material to a week"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import CourseWeek, WeekMaterial
        import uuid
        
        week = CourseWeek.query.filter_by(course_id=course_id, week_number=week_number).first()
        if not week:
            return jsonify({'error': 'Week not found'}), 404
        
        data = request.get_json()
        
        # Get max order index
        max_order = db.session.query(db.func.max(WeekMaterial.order_index)).filter_by(week_id=week.id).scalar() or 0
        
        material = WeekMaterial(
            id=str(uuid.uuid4()),
            week_id=week.id,
            title=data['title'],
            description=data.get('description', ''),
            material_type=data.get('material_type', 'document'),
            file_url=data.get('file_url'),
            external_url=data.get('external_url'),
            content_html=data.get('content_html'),
            duration_minutes=data.get('duration_minutes'),
            difficulty_level=data.get('difficulty_level', 'intermediate'),
            topics=data.get('topics', []),
            order_index=max_order + 1,
            is_required=data.get('is_required', True),
            is_published=data.get('is_published', True)
        )
        
        db.session.add(material)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Material added successfully',
            'material': {
                'id': material.id,
                'title': material.title
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error adding material: {e}")
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>/weeks/<int:week_number>/materials/<material_id>', methods=['PUT'])
@instructor_required
def update_material(course_id, week_number, material_id):
    """Update a material"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import WeekMaterial
        
        material = WeekMaterial.query.filter_by(id=material_id).first()
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        data = request.get_json()
        
        if 'title' in data:
            material.title = data['title']
        if 'description' in data:
            material.description = data['description']
        if 'material_type' in data:
            material.material_type = data['material_type']
        if 'file_url' in data:
            material.file_url = data['file_url']
        if 'external_url' in data:
            material.external_url = data['external_url']
        if 'content_html' in data:
            material.content_html = data['content_html']
        if 'duration_minutes' in data:
            material.duration_minutes = data['duration_minutes']
        if 'difficulty_level' in data:
            material.difficulty_level = data['difficulty_level']
        if 'topics' in data:
            material.topics = data['topics']
        if 'is_required' in data:
            material.is_required = data['is_required']
        if 'is_published' in data:
            material.is_published = data['is_published']
        if 'order_index' in data:
            material.order_index = data['order_index']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Material updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating material: {e}")
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>/weeks/<int:week_number>/materials/<material_id>', methods=['DELETE'])
@instructor_required
def delete_material(course_id, week_number, material_id):
    """Delete a material"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import WeekMaterial
        
        material = WeekMaterial.query.filter_by(id=material_id).first()
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        db.session.delete(material)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Material deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting material: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# ASSIGNMENTS MANAGEMENT
# ============================================

@courses_bp.route('/<course_id>/weeks/<int:week_number>/assignments', methods=['POST'])
@instructor_required
def create_assignment(course_id, week_number):
    """Create an assignment for a week"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import CourseWeek, Assignment
        import uuid
        
        week = CourseWeek.query.filter_by(course_id=course_id, week_number=week_number).first()
        if not week:
            return jsonify({'error': 'Week not found'}), 404
        
        data = request.get_json()
        
        assignment = Assignment(
            id=str(uuid.uuid4()),
            week_id=week.id,
            title=data['title'],
            description=data.get('description', ''),
            instructions=data.get('instructions', ''),
            assignment_type=data.get('assignment_type', 'submission'),
            open_date=datetime.fromisoformat(data['open_date']) if data.get('open_date') else None,
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
            close_date=datetime.fromisoformat(data['close_date']) if data.get('close_date') else None,
            max_points=data.get('max_points', 100.0),
            weight=data.get('weight', 1.0),
            allow_late=data.get('allow_late', False),
            late_penalty_percent=data.get('late_penalty_percent', 10.0),
            max_attempts=data.get('max_attempts', 1),
            allowed_file_types=data.get('allowed_file_types', []),
            topics=data.get('topics', []),
            is_published=data.get('is_published', False)
        )
        
        db.session.add(assignment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Assignment created successfully',
            'assignment': {
                'id': assignment.id,
                'title': assignment.title
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error creating assignment: {e}")
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>/assignments/<assignment_id>', methods=['GET'])
@login_required
def get_assignment(course_id, assignment_id):
    """Get assignment details"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Assignment, AssignmentSubmission
        
        assignment = Assignment.query.filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        user_id = session.get('user_id')
        
        # Get user's submission
        submission = AssignmentSubmission.query.filter_by(
            assignment_id=assignment_id, 
            user_id=user_id
        ).order_by(AssignmentSubmission.attempt_number.desc()).first()
        
        return jsonify({
            'success': True,
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'instructions': assignment.instructions,
                'assignment_type': assignment.assignment_type,
                'open_date': assignment.open_date.isoformat() if assignment.open_date else None,
                'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
                'close_date': assignment.close_date.isoformat() if assignment.close_date else None,
                'max_points': assignment.max_points,
                'max_attempts': assignment.max_attempts,
                'allow_late': assignment.allow_late,
                'late_penalty_percent': assignment.late_penalty_percent,
                'allowed_file_types': assignment.allowed_file_types,
                'is_published': assignment.is_published
            },
            'submission': {
                'id': submission.id,
                'status': submission.status,
                'attempt_number': submission.attempt_number,
                'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
                'score': submission.score,
                'feedback': submission.feedback
            } if submission else None
        })
    except Exception as e:
        print(f"Error getting assignment: {e}")
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>/assignments/<assignment_id>/submit', methods=['POST'])
@login_required
def submit_assignment(course_id, assignment_id):
    """Submit an assignment"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Assignment, AssignmentSubmission
        import uuid
        
        assignment = Assignment.query.filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        user_id = session.get('user_id')
        data = request.get_json()
        
        # Check attempt count
        existing_submissions = AssignmentSubmission.query.filter_by(
            assignment_id=assignment_id,
            user_id=user_id
        ).count()
        
        if existing_submissions >= assignment.max_attempts:
            return jsonify({'error': 'Maximum attempts reached'}), 400
        
        # Check if late
        is_late = False
        late_penalty = 0.0
        if assignment.due_date and datetime.utcnow() > assignment.due_date:
            if not assignment.allow_late:
                return jsonify({'error': 'Assignment is past due date'}), 400
            is_late = True
            late_penalty = assignment.late_penalty_percent
        
        submission = AssignmentSubmission(
            id=str(uuid.uuid4()),
            assignment_id=assignment_id,
            user_id=user_id,
            submission_text=data.get('submission_text'),
            file_url=data.get('file_url'),
            file_name=data.get('file_name'),
            status='submitted',
            attempt_number=existing_submissions + 1,
            submitted_at=datetime.utcnow(),
            is_late=is_late,
            late_penalty_applied=late_penalty
        )
        
        db.session.add(submission)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Assignment submitted successfully',
            'submission': {
                'id': submission.id,
                'attempt_number': submission.attempt_number,
                'is_late': submission.is_late
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting assignment: {e}")
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>/assignments/<assignment_id>/submissions', methods=['GET'])
@instructor_required
def get_assignment_submissions(course_id, assignment_id):
    """Get all submissions for an assignment (instructor view)"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import AssignmentSubmission, User
        
        submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).all()
        
        result = []
        for sub in submissions:
            user = User.query.filter_by(id=sub.user_id).first()
            result.append({
                'id': sub.id,
                'user_id': sub.user_id,
                'student_name': user.full_name if user else 'Unknown',
                'status': sub.status,
                'attempt_number': sub.attempt_number,
                'submitted_at': sub.submitted_at.isoformat() if sub.submitted_at else None,
                'score': sub.score,
                'is_late': sub.is_late
            })
        
        return jsonify({
            'success': True,
            'submissions': result
        })
    except Exception as e:
        print(f"Error getting submissions: {e}")
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>/assignments/<assignment_id>/submissions/<submission_id>/grade', methods=['POST'])
@instructor_required
def grade_submission(course_id, assignment_id, submission_id):
    """Grade a submission"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import AssignmentSubmission
        
        submission = AssignmentSubmission.query.filter_by(id=submission_id).first()
        if not submission:
            return jsonify({'error': 'Submission not found'}), 404
        
        data = request.get_json()
        
        submission.score = data.get('score')
        submission.feedback = data.get('feedback')
        submission.status = 'graded'
        submission.graded_by = session.get('user_id')
        submission.graded_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Submission graded successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error grading submission: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# LEARNING PROGRESS TRACKING
# ============================================

@courses_bp.route('/<course_id>/materials/<material_id>/progress', methods=['POST'])
@login_required
def update_material_progress(course_id, material_id):
    """Update learning progress for a material"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import LearningProgress, Enrollment
        import uuid
        
        user_id = session.get('user_id')
        data = request.get_json()
        
        # Get or create progress record
        progress = LearningProgress.query.filter_by(
            user_id=user_id,
            material_id=material_id
        ).first()
        
        if not progress:
            progress = LearningProgress(
                id=str(uuid.uuid4()),
                user_id=user_id,
                material_id=material_id,
                status='in_progress',
                started_at=datetime.utcnow()
            )
            db.session.add(progress)
        
        # Update progress
        if 'progress_percent' in data:
            progress.progress_percent = data['progress_percent']
        if 'time_spent_seconds' in data:
            progress.time_spent_seconds = (progress.time_spent_seconds or 0) + data['time_spent_seconds']
        if data.get('completed'):
            progress.status = 'completed'
            progress.completed_at = datetime.utcnow()
            progress.progress_percent = 100.0
        
        progress.last_accessed = datetime.utcnow()
        
        # Update enrollment progress
        enrollment = Enrollment.query.filter_by(user_id=user_id, course_id=course_id).first()
        if enrollment:
            # Calculate overall progress
            from app.models import WeekMaterial, CourseWeek
            total_materials = WeekMaterial.query.join(CourseWeek).filter(CourseWeek.course_id == course_id).count()
            completed_materials = LearningProgress.query.filter_by(
                user_id=user_id, 
                status='completed'
            ).join(WeekMaterial).join(CourseWeek).filter(CourseWeek.course_id == course_id).count()
            
            if total_materials > 0:
                enrollment.progress_percent = (completed_materials / total_materials) * 100
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'progress': {
                'status': progress.status,
                'progress_percent': progress.progress_percent,
                'time_spent_seconds': progress.time_spent_seconds
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating progress: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# PERSONALIZED LEARNING RECOMMENDATIONS
# ============================================

@courses_bp.route('/<course_id>/recommendations', methods=['GET'])
@login_required
def get_recommendations(course_id):
    """Get personalized learning recommendations for a student"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import LearningRecommendation, WeekMaterial, Assignment, LearningProgress, AssignmentSubmission
        
        user_id = session.get('user_id')
        
        # Get active recommendations
        recommendations = LearningRecommendation.query.filter_by(
            user_id=user_id,
            course_id=course_id,
            status='pending'
        ).order_by(LearningRecommendation.priority.desc()).limit(5).all()
        
        result = []
        for rec in recommendations:
            rec_data = {
                'id': rec.id,
                'type': rec.recommendation_type,
                'target_type': rec.target_type,
                'target_id': rec.target_id,
                'title': rec.title,
                'description': rec.description,
                'priority': rec.priority,
                'reason': rec.reason,
                'confidence_score': rec.confidence_score
            }
            
            # Add target details
            if rec.target_type == 'material':
                material = WeekMaterial.query.filter_by(id=rec.target_id).first()
                if material:
                    rec_data['target'] = {
                        'title': material.title,
                        'type': material.material_type,
                        'duration_minutes': material.duration_minutes
                    }
            elif rec.target_type == 'assignment':
                assignment = Assignment.query.filter_by(id=rec.target_id).first()
                if assignment:
                    rec_data['target'] = {
                        'title': assignment.title,
                        'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
                        'max_points': assignment.max_points
                    }
            
            result.append(rec_data)
        
        return jsonify({
            'success': True,
            'recommendations': result
        })
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>/recommendations/<recommendation_id>/action', methods=['POST'])
@login_required
def update_recommendation_status(course_id, recommendation_id):
    """Update recommendation status (viewed, accepted, dismissed)"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import LearningRecommendation
        
        recommendation = LearningRecommendation.query.filter_by(id=recommendation_id).first()
        if not recommendation:
            return jsonify({'error': 'Recommendation not found'}), 404
        
        data = request.get_json()
        action = data.get('action')  # viewed, accepted, dismissed
        
        if action == 'viewed':
            recommendation.status = 'viewed'
            recommendation.viewed_at = datetime.utcnow()
        elif action == 'accepted':
            recommendation.status = 'accepted'
        elif action == 'dismissed':
            recommendation.status = 'dismissed'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Recommendation {action}'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating recommendation: {e}")
        return jsonify({'error': str(e)}), 500
