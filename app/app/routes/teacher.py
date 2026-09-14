"""
Teacher Dashboard Routes
Endpoints for teacher course management, student tracking, grading, and AI reports
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
import uuid
import os

teacher_bp = Blueprint('teacher', __name__, url_prefix='/api/teacher')


def get_db():
    """Get database session"""
    try:
        from app.models import db
        return db
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def teacher_required(f):
    """Decorator to require teacher/instructor role or higher (admin roles can also access)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401
        
        role = session.get('role', '').lower()
        allowed_roles = ['instructor', 'teacher', 'institution_admin', 'admin', 'super_admin', 'superadmin']
        if role not in allowed_roles:
            return jsonify({'error': 'Teacher access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# MY COURSES
# ============================================

@teacher_bp.route('/courses', methods=['GET'])
@teacher_required
def get_my_courses():
    """Get all courses assigned to the current teacher"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import CourseInstructor, Course
        from app.utils.class_serializers import serialize_class_for_teacher
        
        user_id = session.get('user_id')

        course_assignments = CourseInstructor.query.filter_by(user_id=user_id).all()
        course_ids = [ca.course_id for ca in course_assignments]

        courses = Course.query.filter(
            Course.id.in_(course_ids)
        ).all()
        
        courses_list = [serialize_class_for_teacher(course) for course in courses]
        
        return jsonify({
            'success': True,
            'classes': courses_list
        })
    except Exception as e:
        print(f"Error getting teacher courses: {e}")
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/courses', methods=['POST'])
@teacher_required
def create_teacher_course():
    """Allow teacher to create a new class/course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course, CourseInstructor, CourseWeek
        from datetime import datetime
        
        user_id = session.get('user_id')

        data = request.get_json() or {}
        
        title = data.get('title', '').strip()
        if not title:
            return jsonify({'error': 'Class title is required'}), 400
        
        # Generate course code
        code_base = ''.join(word[0].upper() for word in title.split()[:3])
        code = f"{code_base}_{str(uuid.uuid4())[:4].upper()}"
        
        # Parse dates
        start_date = None
        end_date = None
        if data.get('start_date'):
            try:
                start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            except:
                pass
        if data.get('end_date'):
            try:
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            except:
                pass
        
        # Create the course
        course = Course(
            id=str(uuid.uuid4()),
            title=title,
            code=code,
            description=data.get('description', ''),
            start_date=start_date,
            end_date=end_date,
            institution_id=data.get('institution_id'),
            is_published=False,  # Start as draft, admin can publish
            certificate_enabled=data.get('certificate_enabled', True),
            passing_threshold=data.get('passing_threshold', 60.0)
        )
        
        db.session.add(course)
        
        # Assign the teacher as instructor
        instructor_assignment = CourseInstructor(
            id=str(uuid.uuid4()),
            course_id=course.id,
            user_id=user_id
        )
        db.session.add(instructor_assignment)
        
        # Create default weeks (e.g., 8 weeks)
        num_weeks = data.get('num_weeks', 8)
        for week_num in range(1, num_weeks + 1):
            week = CourseWeek(
                id=str(uuid.uuid4()),
                course_id=course.id,
                week_number=week_num,
                title=f"Week {week_num}",
                description=f"Content for week {week_num}"
            )
            db.session.add(week)
        
        # Automatically create exit survey for training evaluation
        from app.services.auto_survey import create_exit_survey_for_course
        exit_survey = create_exit_survey_for_course(db, course.id, course.title)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Class created successfully with exit survey',
            'class': {
                'id': course.id,
                'title': course.title,
                'code': course.code,
                'is_published': course.is_published,
                'exit_survey_created': exit_survey is not None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating teacher course: {e}")
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/courses/<course_id>', methods=['GET'])
@teacher_required
def get_course_details(course_id):
    """Get detailed course information including weeks, materials, assignments"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course, CourseInstructor, Assignment, Enrollment
        from app.utils.class_serializers import (
            serialize_base_class,
            serialize_weeks_with_materials,
            serialize_exams_for_class,
            serialize_class_stats
        )
        
        user_id = session.get('user_id')
        
        assignment = CourseInstructor.query.filter_by(
            course_id=course_id,
            user_id=user_id
        ).first()
        
        if not assignment:
            return jsonify({'error': 'Access denied to this course'}), 403
        
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        weeks_data = serialize_weeks_with_materials(course_id, for_teacher=True)
        exams_data = serialize_exams_for_class(course_id, for_teacher=True)
        stats = serialize_class_stats(course_id)
        
        enrollment_stats = {
            'total': stats['students']['total'],
            'active': stats['students']['active'],
            'pending': stats['students']['pending'],
            'completed': Enrollment.query.filter_by(course_id=course_id, status='completed').count()
        }
        
        course_data = serialize_base_class(course)
        
        return jsonify({
            'success': True,
            'class': course_data,
            'weeks': weeks_data,
            'exams': exams_data,
            'enrollment_stats': enrollment_stats
        })
    except Exception as e:
        print(f"Error getting course details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/courses/<course_id>/sessions', methods=['PUT'])
@teacher_required
def update_course_sessions(course_id):
    """Update course meeting/session links"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course, CourseInstructor
        
        user_id = session.get('user_id')
        
        # Verify access
        assignment = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not assignment:
            return jsonify({'error': 'Access denied'}), 403
        
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        data = request.get_json()
        
        if 'meet_link' in data:
            course.meet_link = data['meet_link']
        if 'zoom_link' in data:
            course.zoom_link = data['zoom_link']
        if 'youtube_broadcast_link' in data:
            course.youtube_broadcast_link = data['youtube_broadcast_link']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Session links updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================
# WEEKLY MATERIALS MANAGEMENT
# ============================================

@teacher_bp.route('/courses/<course_id>/weeks', methods=['POST'])
@teacher_required
def create_week(course_id):
    """Create a new week in the course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course, CourseInstructor, CourseWeek
        
        user_id = session.get('user_id')
        
        # Verify access
        assignment = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not assignment:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        # Get next week number
        max_week = db.session.query(db.func.max(CourseWeek.week_number)).filter_by(course_id=course_id).scalar() or 0
        
        week = CourseWeek(
            id=str(uuid.uuid4()),
            course_id=course_id,
            week_number=max_week + 1,
            title=data.get('title', f'Week {max_week + 1}'),
            description=data.get('description'),
            is_published=data.get('is_published', False)
        )
        
        db.session.add(week)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'week': {
                'id': week.id,
                'week_number': week.week_number,
                'title': week.title,
                'description': week.description,
                'is_published': week.is_published
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/weeks/<week_id>/materials', methods=['POST'])
@teacher_required
def add_material(week_id):
    """Add a material to a week (JSON data only, no file)"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import CourseWeek, WeekMaterial, CourseInstructor
        
        user_id = session.get('user_id')
        
        week = CourseWeek.query.filter_by(id=week_id).first()
        if not week:
            return jsonify({'error': 'Week not found'}), 404
        
        assignment = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        if not assignment:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        max_order = db.session.query(db.func.max(WeekMaterial.order_index)).filter_by(week_id=week_id).scalar() or 0
        
        visibility_state = data.get('visibility_state', 'draft')
        available_at = None
        if data.get('available_at'):
            available_at = datetime.fromisoformat(data['available_at'].replace('Z', '+00:00'))
        
        approved_at = None
        approved_by = None
        if visibility_state == 'approved':
            approved_at = datetime.utcnow()
            approved_by = user_id
        
        material = WeekMaterial(
            id=str(uuid.uuid4()),
            week_id=week_id,
            title=data.get('title'),
            description=data.get('description'),
            material_type=data.get('material_type', 'link'),
            file_url=data.get('file_url'),
            external_url=data.get('external_url'),
            content_html=data.get('content_html'),
            duration_minutes=data.get('duration_minutes'),
            difficulty_level=data.get('difficulty_level', 'intermediate'),
            topics=data.get('topics', []),
            order_index=max_order + 1,
            is_required=data.get('is_required', True),
            is_published=visibility_state == 'approved',
            visibility_state=visibility_state,
            available_at=available_at,
            approved_at=approved_at,
            approved_by=approved_by
        )
        
        db.session.add(material)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'material': {
                'id': material.id,
                'title': material.title,
                'material_type': material.material_type,
                'visibility_state': material.visibility_state,
                'available_at': material.available_at.isoformat() if material.available_at else None
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/weeks/<week_id>/materials/upload', methods=['POST'])
@teacher_required
def upload_material(week_id):
    """Upload a file as material to a week"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import CourseWeek, WeekMaterial, CourseInstructor
        from app.utils.upload_handler import save_uploaded_file
        
        user_id = session.get('user_id')
        
        week = CourseWeek.query.filter_by(id=week_id).first()
        if not week:
            return jsonify({'error': 'Week not found'}), 404
        
        assignment = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        if not assignment:
            return jsonify({'error': 'Access denied'}), 403
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        
        upload_result = save_uploaded_file(file, week_id)
        
        if 'error' in upload_result:
            return jsonify({'error': upload_result['error']}), 400
        
        title = request.form.get('title', file.filename)
        description = request.form.get('description', '')
        visibility_state = request.form.get('visibility_state', 'draft')
        is_required = request.form.get('is_required', 'true').lower() == 'true'
        
        available_at = None
        if request.form.get('available_at'):
            available_at = datetime.fromisoformat(request.form['available_at'].replace('Z', '+00:00'))
        
        approved_at = None
        approved_by = None
        if visibility_state == 'approved':
            approved_at = datetime.utcnow()
            approved_by = user_id
        
        max_order = db.session.query(db.func.max(WeekMaterial.order_index)).filter_by(week_id=week_id).scalar() or 0
        
        material = WeekMaterial(
            id=str(uuid.uuid4()),
            week_id=week_id,
            title=title,
            description=description,
            material_type=upload_result['material_type'],
            file_url=upload_result['file_url'],
            file_name=upload_result['file_name'],
            file_size=upload_result['file_size'],
            mime_type=upload_result['mime_type'],
            order_index=max_order + 1,
            is_required=is_required,
            is_published=visibility_state == 'approved',
            visibility_state=visibility_state,
            available_at=available_at,
            approved_at=approved_at,
            approved_by=approved_by
        )
        
        db.session.add(material)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'material': {
                'id': material.id,
                'title': material.title,
                'material_type': material.material_type,
                'file_url': material.file_url,
                'file_name': material.file_name,
                'file_size': material.file_size,
                'visibility_state': material.visibility_state,
                'available_at': material.available_at.isoformat() if material.available_at else None
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error uploading material: {e}")
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/materials/<material_id>', methods=['GET'])
@teacher_required
def get_material(material_id):
    """Get a single material details for editing"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import WeekMaterial, CourseWeek, CourseInstructor
        
        user_id = session.get('user_id')
        
        material = WeekMaterial.query.filter_by(id=material_id).first()
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        week = CourseWeek.query.filter_by(id=material.week_id).first()
        instructor_check = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'success': True,
            'material': {
                'id': material.id,
                'week_id': material.week_id,
                'title': material.title,
                'description': material.description,
                'material_type': material.material_type,
                'file_url': material.file_url,
                'file_name': material.file_name,
                'external_url': material.external_url,
                'visibility_state': material.visibility_state or 'draft',
                'available_at': material.available_at.isoformat() if material.available_at else None,
                'is_published': material.is_published,
                'duration_minutes': material.duration_minutes
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/materials/<material_id>', methods=['PUT'])
@teacher_required
def update_material(material_id):
    """Update a material"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import WeekMaterial, CourseWeek, CourseInstructor
        
        user_id = session.get('user_id')
        
        material = WeekMaterial.query.filter_by(id=material_id).first()
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        week = CourseWeek.query.filter_by(id=material.week_id).first()
        assignment = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        if not assignment:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        for field in ['title', 'description', 'material_type', 'file_url', 'external_url', 
                      'content_html', 'duration_minutes', 'difficulty_level', 'topics', 
                      'order_index', 'is_required']:
            if field in data:
                setattr(material, field, data[field])
        
        if 'visibility_state' in data:
            old_state = material.visibility_state
            new_state = data['visibility_state']
            material.visibility_state = new_state
            
            if new_state == 'approved' and old_state != 'approved':
                material.approved_at = datetime.utcnow()
                material.approved_by = user_id
                material.is_published = True
            elif new_state == 'draft':
                material.is_published = False
            elif new_state == 'scheduled':
                material.is_published = False
        
        if 'available_at' in data:
            if data['available_at']:
                material.available_at = datetime.fromisoformat(data['available_at'].replace('Z', '+00:00'))
            else:
                material.available_at = None
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Material updated',
            'material': {
                'id': material.id,
                'visibility_state': material.visibility_state,
                'is_published': material.is_published,
                'available_at': material.available_at.isoformat() if material.available_at else None
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/materials/<material_id>/approve', methods=['POST'])
@teacher_required
def approve_material(material_id):
    """Approve a material to make it visible to students"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import WeekMaterial, CourseWeek, CourseInstructor
        
        user_id = session.get('user_id')
        
        material = WeekMaterial.query.filter_by(id=material_id).first()
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        week = CourseWeek.query.filter_by(id=material.week_id).first()
        assignment = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        if not assignment:
            return jsonify({'error': 'Access denied'}), 403
        
        material.visibility_state = 'approved'
        material.approved_at = datetime.utcnow()
        material.approved_by = user_id
        material.is_published = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Material approved and published'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/materials/<material_id>/schedule', methods=['POST'])
@teacher_required
def schedule_material(material_id):
    """Schedule a material to become visible at a future time"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import WeekMaterial, CourseWeek, CourseInstructor
        
        user_id = session.get('user_id')
        
        material = WeekMaterial.query.filter_by(id=material_id).first()
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        week = CourseWeek.query.filter_by(id=material.week_id).first()
        assignment = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        if not assignment:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data.get('available_at'):
            return jsonify({'error': 'Schedule date required'}), 400
        
        available_at = datetime.fromisoformat(data['available_at'].replace('Z', '+00:00'))
        
        material.visibility_state = 'scheduled'
        material.available_at = available_at
        material.is_published = False
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Material scheduled',
            'available_at': available_at.isoformat()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/materials/<material_id>', methods=['DELETE'])
@teacher_required
def delete_material(material_id):
    """Delete a material"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import WeekMaterial, CourseWeek, CourseInstructor
        
        user_id = session.get('user_id')
        
        material = WeekMaterial.query.filter_by(id=material_id).first()
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        week = CourseWeek.query.filter_by(id=material.week_id).first()
        assignment = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        if not assignment:
            return jsonify({'error': 'Access denied'}), 403
        
        db.session.delete(material)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Material deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================
# ASSIGNMENTS MANAGEMENT
# ============================================

@teacher_bp.route('/weeks/<week_id>/assignments', methods=['POST'])
@teacher_required
def create_assignment(week_id):
    """Create an assignment for a week"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import CourseWeek, Assignment, CourseInstructor
        
        user_id = session.get('user_id')
        
        week = CourseWeek.query.filter_by(id=week_id).first()
        if not week:
            return jsonify({'error': 'Week not found'}), 404
        
        assignment_check = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        if not assignment_check:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        visibility_state = data.get('visibility_state', 'draft')
        available_at = None
        if data.get('available_at'):
            available_at = datetime.fromisoformat(data['available_at'].replace('Z', '+00:00'))
        
        approved_at = None
        approved_by = None
        if visibility_state == 'approved':
            approved_at = datetime.utcnow()
            approved_by = user_id
        
        assignment = Assignment(
            id=str(uuid.uuid4()),
            week_id=week_id,
            title=data.get('title'),
            description=data.get('description'),
            instructions=data.get('instructions'),
            assignment_type=data.get('assignment_type', 'submission'),
            due_date=datetime.fromisoformat(data['due_date'].replace('Z', '+00:00')) if data.get('due_date') else None,
            open_date=datetime.fromisoformat(data['open_date'].replace('Z', '+00:00')) if data.get('open_date') else None,
            close_date=datetime.fromisoformat(data['close_date'].replace('Z', '+00:00')) if data.get('close_date') else None,
            max_points=data.get('max_points', 100),
            weight=data.get('weight', 1.0),
            allow_late=data.get('allow_late', False),
            late_penalty_percent=data.get('late_penalty_percent', 10),
            max_attempts=data.get('max_attempts', 1),
            allowed_file_types=data.get('allowed_file_types', []),
            topics=data.get('topics', []),
            is_published=visibility_state == 'approved',
            visibility_state=visibility_state,
            available_at=available_at,
            approved_at=approved_at,
            approved_by=approved_by
        )
        
        db.session.add(assignment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'visibility_state': assignment.visibility_state,
                'available_at': assignment.available_at.isoformat() if assignment.available_at else None,
                'due_date': assignment.due_date.isoformat() if assignment.due_date else None
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error creating assignment: {e}")
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/assignments/<assignment_id>', methods=['PUT'])
@teacher_required
def update_assignment(assignment_id):
    """Update an assignment"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Assignment, CourseWeek, CourseInstructor
        
        user_id = session.get('user_id')
        
        assignment = Assignment.query.filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        week = CourseWeek.query.filter_by(id=assignment.week_id).first()
        instructor_check = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        for field in ['title', 'description', 'instructions', 'assignment_type', 'max_points',
                      'weight', 'allow_late', 'late_penalty_percent', 'max_attempts',
                      'allowed_file_types', 'topics']:
            if field in data:
                setattr(assignment, field, data[field])
        
        if 'due_date' in data:
            assignment.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00')) if data['due_date'] else None
        if 'open_date' in data:
            assignment.open_date = datetime.fromisoformat(data['open_date'].replace('Z', '+00:00')) if data['open_date'] else None
        if 'close_date' in data:
            assignment.close_date = datetime.fromisoformat(data['close_date'].replace('Z', '+00:00')) if data['close_date'] else None
        
        if 'visibility_state' in data:
            old_state = assignment.visibility_state
            new_state = data['visibility_state']
            assignment.visibility_state = new_state
            
            if new_state == 'approved' and old_state != 'approved':
                assignment.approved_at = datetime.utcnow()
                assignment.approved_by = user_id
                assignment.is_published = True
            elif new_state == 'draft':
                assignment.is_published = False
            elif new_state == 'scheduled':
                assignment.is_published = False
        
        if 'available_at' in data:
            if data['available_at']:
                assignment.available_at = datetime.fromisoformat(data['available_at'].replace('Z', '+00:00'))
            else:
                assignment.available_at = None
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Assignment updated',
            'assignment': {
                'id': assignment.id,
                'visibility_state': assignment.visibility_state,
                'is_published': assignment.is_published,
                'available_at': assignment.available_at.isoformat() if assignment.available_at else None
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/assignments/<assignment_id>/approve', methods=['POST'])
@teacher_required
def approve_assignment(assignment_id):
    """Approve an assignment to make it visible to students"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Assignment, CourseWeek, CourseInstructor
        
        user_id = session.get('user_id')
        
        assignment = Assignment.query.filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        week = CourseWeek.query.filter_by(id=assignment.week_id).first()
        instructor_check = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        assignment.visibility_state = 'approved'
        assignment.approved_at = datetime.utcnow()
        assignment.approved_by = user_id
        assignment.is_published = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Assignment approved and published'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/assignments/<assignment_id>/schedule', methods=['POST'])
@teacher_required
def schedule_assignment(assignment_id):
    """Schedule an assignment to become visible at a future time"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Assignment, CourseWeek, CourseInstructor
        
        user_id = session.get('user_id')
        
        assignment = Assignment.query.filter_by(id=assignment_id).first()
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        week = CourseWeek.query.filter_by(id=assignment.week_id).first()
        instructor_check = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data.get('available_at'):
            return jsonify({'error': 'Schedule date required'}), 400
        
        available_at = datetime.fromisoformat(data['available_at'].replace('Z', '+00:00'))
        
        assignment.visibility_state = 'scheduled'
        assignment.available_at = available_at
        assignment.is_published = False
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Assignment scheduled',
            'available_at': available_at.isoformat()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================
# SUBMISSIONS & GRADING
# ============================================

@teacher_bp.route('/courses/<course_id>/submissions', methods=['GET'])
@teacher_required
def get_course_submissions(course_id):
    """Get all submissions for a course that need grading"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import CourseInstructor, CourseWeek, Assignment, AssignmentSubmission, User
        
        user_id = session.get('user_id')
        
        # Verify access
        instructor_check = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get all weeks for this course
        weeks = CourseWeek.query.filter_by(course_id=course_id).all()
        week_ids = [w.id for w in weeks]
        
        # Get all assignments for these weeks
        assignments = Assignment.query.filter(Assignment.week_id.in_(week_ids)).all()
        assignment_map = {a.id: a for a in assignments}
        assignment_ids = [a.id for a in assignments]
        
        # Get submissions
        submissions = AssignmentSubmission.query.filter(
            AssignmentSubmission.assignment_id.in_(assignment_ids),
            AssignmentSubmission.status.in_(['submitted', 'graded'])
        ).order_by(AssignmentSubmission.submitted_at.desc()).all()
        
        submissions_list = []
        for sub in submissions:
            student = User.query.filter_by(id=sub.user_id).first()
            assignment = assignment_map.get(sub.assignment_id)
            
            submissions_list.append({
                'id': sub.id,
                'student': {
                    'id': student.id if student else None,
                    'username': student.username if student else 'Unknown',
                    'full_name': student.full_name if student else 'Unknown'
                },
                'assignment': {
                    'id': assignment.id if assignment else None,
                    'title': assignment.title if assignment else 'Unknown',
                    'max_points': assignment.max_points if assignment else 0
                },
                'submission_text': sub.submission_text[:200] if sub.submission_text else None,
                'file_url': sub.file_url,
                'file_name': sub.file_name,
                'status': sub.status,
                'submitted_at': sub.submitted_at.isoformat() if sub.submitted_at else None,
                'score': sub.score,
                'feedback': sub.feedback,
                'is_late': sub.is_late
            })
        
        return jsonify({
            'success': True,
            'submissions': submissions_list,
            'stats': {
                'total': len(submissions_list),
                'pending': sum(1 for s in submissions_list if s['status'] == 'submitted'),
                'graded': sum(1 for s in submissions_list if s['status'] == 'graded')
            }
        })
    except Exception as e:
        print(f"Error getting submissions: {e}")
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/submissions/<submission_id>/grade', methods=['POST'])
@teacher_required
def grade_submission(submission_id):
    """Grade a student submission"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import AssignmentSubmission, Assignment, CourseWeek, CourseInstructor
        
        user_id = session.get('user_id')
        
        submission = AssignmentSubmission.query.filter_by(id=submission_id).first()
        if not submission:
            return jsonify({'error': 'Submission not found'}), 404
        
        # Verify access through assignment -> week -> course
        assignment = Assignment.query.filter_by(id=submission.assignment_id).first()
        week = CourseWeek.query.filter_by(id=assignment.week_id).first()
        instructor_check = CourseInstructor.query.filter_by(course_id=week.course_id, user_id=user_id).first()
        
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        submission.score = data.get('score')
        submission.feedback = data.get('feedback')
        submission.status = 'graded'
        submission.graded_by = user_id
        submission.graded_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Submission graded successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================
# EXAMS/QUIZZES MANAGEMENT
# ============================================

@teacher_bp.route('/courses/<course_id>/exams', methods=['POST'])
@teacher_required
def create_exam(course_id):
    """Create an exam/quiz for the course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, CourseInstructor
        
        user_id = session.get('user_id')
        
        instructor_check = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        exam = Exam(
            id=str(uuid.uuid4()),
            course_id=course_id,
            week_id=data.get('week_id'),
            title=data.get('title'),
            description=data.get('description'),
            exam_type=data.get('exam_type', 'quiz'),
            open_date=datetime.fromisoformat(data['open_date']) if data.get('open_date') else None,
            close_date=datetime.fromisoformat(data['close_date']) if data.get('close_date') else None,
            time_limit_minutes=data.get('time_limit_minutes'),
            passing_threshold=data.get('passing_threshold', 50),
            max_attempts=data.get('max_attempts', 1),
            shuffle_questions=data.get('shuffle_questions', False),
            show_results=data.get('show_results', True),
            is_published=data.get('is_published', False)
        )
        
        db.session.add(exam)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'exam': {'id': exam.id, 'title': exam.title}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/exams/<exam_id>/questions', methods=['POST'])
@teacher_required
def add_exam_question(exam_id):
    """Add a question to an exam"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, ExamQuestion, CourseInstructor
        
        user_id = session.get('user_id')
        
        exam = Exam.query.filter_by(id=exam_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        instructor_check = CourseInstructor.query.filter_by(course_id=exam.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        # Get next order index
        max_order = db.session.query(db.func.max(ExamQuestion.order_index)).filter_by(exam_id=exam_id).scalar() or 0
        
        question = ExamQuestion(
            id=str(uuid.uuid4()),
            exam_id=exam_id,
            question_text=data.get('question_text'),
            question_type=data.get('question_type', 'multiple_choice'),
            options=data.get('options', []),
            correct_answer=data.get('correct_answer'),
            points=data.get('points', 1.0),
            topic=data.get('topic'),
            difficulty=data.get('difficulty', 'medium'),
            order_index=max_order + 1
        )
        
        db.session.add(question)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'question': {'id': question.id}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/exams/<exam_id>/questions', methods=['GET'])
@teacher_required
def get_exam_questions(exam_id):
    """Get all questions for an exam"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, ExamQuestion, CourseInstructor
        
        user_id = session.get('user_id')
        
        exam = Exam.query.filter_by(id=exam_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        instructor_check = CourseInstructor.query.filter_by(course_id=exam.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        questions = ExamQuestion.query.filter_by(exam_id=exam_id).order_by(ExamQuestion.order_index).all()
        
        return jsonify({
            'success': True,
            'exam': {
                'id': exam.id,
                'title': exam.title
            },
            'questions': [{
                'id': q.id,
                'question_text': q.question_text,
                'question_type': q.question_type,
                'options': q.options,
                'correct_answer': q.correct_answer,
                'points': q.points,
                'topic': q.topic,
                'difficulty': q.difficulty,
                'order_index': q.order_index
            } for q in questions]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/exams/<exam_id>/questions/<question_id>', methods=['DELETE'])
@teacher_required
def delete_exam_question(exam_id, question_id):
    """Delete a question from an exam"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, ExamQuestion, CourseInstructor
        
        user_id = session.get('user_id')
        
        exam = Exam.query.filter_by(id=exam_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        instructor_check = CourseInstructor.query.filter_by(course_id=exam.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        question = ExamQuestion.query.filter_by(id=question_id, exam_id=exam_id).first()
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        db.session.delete(question)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Question deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/exams/<exam_id>/questions/<question_id>', methods=['PUT', 'PATCH'])
@teacher_required
def update_exam_question(exam_id, question_id):
    """Update an exam question"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, ExamQuestion, CourseInstructor
        
        user_id = session.get('user_id')
        
        exam = Exam.query.filter_by(id=exam_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        instructor_check = CourseInstructor.query.filter_by(course_id=exam.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        question = ExamQuestion.query.filter_by(id=question_id, exam_id=exam_id).first()
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'question_text' in data:
            question.question_text = data['question_text']
        if 'question_text_ar' in data:
            question.question_text_ar = data['question_text_ar']
        if 'question_type' in data:
            question.question_type = data['question_type']
        if 'options' in data:
            question.options = data['options']
        if 'options_ar' in data:
            question.options_ar = data['options_ar']
        if 'correct_answer' in data:
            question.correct_answer = data['correct_answer']
        if 'points' in data:
            question.points = int(data['points'])
        if 'order_index' in data:
            question.order_index = int(data['order_index'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Question updated successfully',
            'question': {
                'id': question.id,
                'question_text': question.question_text,
                'question_text_ar': getattr(question, 'question_text_ar', None),
                'question_type': question.question_type,
                'options': question.options,
                'options_ar': getattr(question, 'options_ar', None),
                'correct_answer': question.correct_answer,
                'points': question.points,
                'order_index': question.order_index
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================
# STUDENTS LIST & PROGRESS
# ============================================

@teacher_bp.route('/courses/<course_id>/students', methods=['GET'])
@teacher_required
def get_course_students(course_id):
    """Get all students enrolled in a course with their progress"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import CourseInstructor, Enrollment, User, AssignmentSubmission, Assignment, CourseWeek, LearningProgress, WeekMaterial
        
        user_id = session.get('user_id')
        
        instructor_check = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get enrolled students (both 'approved' and 'active' statuses)
        enrollments = Enrollment.query.filter(
            Enrollment.course_id == course_id,
            Enrollment.status.in_(['approved', 'active'])
        ).all()
        
        students_list = []
        for enrollment in enrollments:
            student = User.query.filter_by(id=enrollment.user_id).first()
            if not student:
                continue
            
            # Calculate student progress
            weeks = CourseWeek.query.filter_by(course_id=course_id).all()
            week_ids = [w.id for w in weeks]
            
            # Materials progress
            materials = WeekMaterial.query.filter(WeekMaterial.week_id.in_(week_ids)).all()
            material_ids = [m.id for m in materials]
            completed_materials = LearningProgress.query.filter(
                LearningProgress.user_id == student.id,
                LearningProgress.material_id.in_(material_ids),
                LearningProgress.status == 'completed'
            ).count()
            
            # Assignment submissions
            assignments = Assignment.query.filter(Assignment.week_id.in_(week_ids)).all()
            assignment_ids = [a.id for a in assignments]
            submissions = AssignmentSubmission.query.filter(
                AssignmentSubmission.user_id == student.id,
                AssignmentSubmission.assignment_id.in_(assignment_ids),
                AssignmentSubmission.status.in_(['submitted', 'graded'])
            ).all()
            
            graded_submissions = [s for s in submissions if s.status == 'graded' and s.score is not None]
            avg_score = sum(s.score for s in graded_submissions) / len(graded_submissions) if graded_submissions else None
            
            students_list.append({
                'id': student.id,
                'username': student.username,
                'full_name': student.full_name,
                'email': student.email,
                'avatar_url': student.avatar_url,
                'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
                'progress': {
                    'overall_percent': enrollment.progress_percent or 0,
                    'current_week': enrollment.current_week or 1,
                    'materials_completed': completed_materials,
                    'materials_total': len(materials),
                    'assignments_submitted': len(submissions),
                    'assignments_total': len(assignments),
                    'average_score': round(avg_score, 1) if avg_score else None
                }
            })
        
        return jsonify({
            'success': True,
            'students': students_list
        })
    except Exception as e:
        print(f"Error getting students: {e}")
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/courses/<course_id>/students/<student_id>/details', methods=['GET'])
@teacher_required
def get_student_details(course_id, student_id):
    """Get detailed progress for a specific student"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import (CourseInstructor, User, Enrollment, CourseWeek, WeekMaterial, 
                               LearningProgress, Assignment, AssignmentSubmission, Exam, ExamResult)
        
        user_id = session.get('user_id')
        
        instructor_check = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        student = User.query.filter_by(id=student_id).first()
        enrollment = Enrollment.query.filter_by(user_id=student_id, course_id=course_id).first()
        
        if not student or not enrollment:
            return jsonify({'error': 'Student not found in this course'}), 404
        
        # Get materials progress
        weeks = CourseWeek.query.filter_by(course_id=course_id).order_by(CourseWeek.week_number).all()
        
        weeks_progress = []
        for week in weeks:
            materials = WeekMaterial.query.filter_by(week_id=week.id).all()
            material_progress = []
            
            for mat in materials:
                progress = LearningProgress.query.filter_by(user_id=student_id, material_id=mat.id).first()
                material_progress.append({
                    'id': mat.id,
                    'title': mat.title,
                    'type': mat.material_type,
                    'status': progress.status if progress else 'not_started',
                    'progress_percent': progress.progress_percent if progress else 0,
                    'time_spent': progress.time_spent_seconds if progress else 0
                })
            
            assignments = Assignment.query.filter_by(week_id=week.id).all()
            assignment_status = []
            
            for assign in assignments:
                submission = AssignmentSubmission.query.filter_by(
                    user_id=student_id, assignment_id=assign.id
                ).order_by(AssignmentSubmission.attempt_number.desc()).first()
                
                assignment_status.append({
                    'id': assign.id,
                    'title': assign.title,
                    'max_points': assign.max_points,
                    'due_date': assign.due_date.isoformat() if assign.due_date else None,
                    'submitted': submission is not None and submission.status in ['submitted', 'graded'],
                    'status': submission.status if submission else 'not_started',
                    'score': submission.score if submission else None,
                    'feedback': submission.feedback if submission else None
                })
            
            weeks_progress.append({
                'week_number': week.week_number,
                'title': week.title,
                'materials': material_progress,
                'assignments': assignment_status
            })
        
        # Get exam results
        exams = Exam.query.filter_by(course_id=course_id).all()
        exam_results = []
        
        for exam in exams:
            result = ExamResult.query.filter_by(user_id=student_id, exam_id=exam.id).first()
            exam_results.append({
                'id': exam.id,
                'title': exam.title,
                'type': exam.exam_type,
                'taken': result is not None,
                'score': result.score if result else None,
                'percentage': result.percentage if result else None,
                'passed': result.passed if result else None
            })
        
        return jsonify({
            'success': True,
            'student': {
                'id': student.id,
                'username': student.username,
                'full_name': student.full_name,
                'email': student.email,
                'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None
            },
            'weeks_progress': weeks_progress,
            'exam_results': exam_results,
            'summary': {
                'overall_progress': enrollment.progress_percent or 0,
                'current_week': enrollment.current_week or 1,
                'final_grade': enrollment.final_grade
            }
        })
    except Exception as e:
        print(f"Error getting student details: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# TEACHER-STUDENT CHAT
# ============================================

@teacher_bp.route('/courses/<course_id>/chat/<student_id>/messages', methods=['GET'])
@teacher_required
def get_chat_messages(course_id, student_id):
    """Get chat messages between teacher and student for a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import TeacherStudentMessage, CourseInstructor, User
        
        user_id = session.get('user_id')
        
        instructor_check = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        messages = TeacherStudentMessage.query.filter_by(
            course_id=course_id,
            teacher_id=user_id,
            student_id=student_id
        ).order_by(TeacherStudentMessage.created_at.asc()).all()
        
        # Mark unread messages as read
        for msg in messages:
            if not msg.is_read and msg.sender_id != user_id:
                msg.is_read = True
                msg.read_at = datetime.utcnow()
        
        db.session.commit()
        
        student = User.query.filter_by(id=student_id).first()
        
        return jsonify({
            'success': True,
            'student': {
                'id': student.id,
                'full_name': student.full_name,
                'username': student.username
            } if student else None,
            'messages': [{
                'id': m.id,
                'message': m.message,
                'message_type': m.message_type,
                'sender_id': m.sender_id,
                'is_teacher': m.sender_id == user_id,
                'created_at': m.created_at.isoformat(),
                'is_read': m.is_read
            } for m in messages]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/courses/<course_id>/chat/<student_id>/send', methods=['POST'])
@teacher_required
def send_chat_message(course_id, student_id):
    """Send a message to a student"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import TeacherStudentMessage, CourseInstructor
        
        user_id = session.get('user_id')
        
        instructor_check = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        message = TeacherStudentMessage(
            id=str(uuid.uuid4()),
            course_id=course_id,
            teacher_id=user_id,
            student_id=student_id,
            sender_id=user_id,
            message=data.get('message'),
            message_type=data.get('message_type', 'text'),
            file_url=data.get('file_url')
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'created_at': message.created_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================
# AI PERFORMANCE REPORTS
# ============================================

@teacher_bp.route('/courses/<course_id>/students/<student_id>/ai-report', methods=['POST'])
@teacher_required
def generate_ai_report(course_id, student_id):
    """Generate an AI-powered performance report for a student"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import (CourseInstructor, User, Course, Enrollment, CourseWeek, WeekMaterial,
                               LearningProgress, Assignment, AssignmentSubmission, Exam, ExamResult,
                               AIPerformanceReport)
        
        user_id = session.get('user_id')
        
        instructor_check = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        student = User.query.filter_by(id=student_id).first()
        course = Course.query.filter_by(id=course_id).first()
        enrollment = Enrollment.query.filter_by(user_id=student_id, course_id=course_id).first()
        
        if not student or not enrollment:
            return jsonify({'error': 'Student not found in this course'}), 404
        
        # Gather student performance data
        weeks = CourseWeek.query.filter_by(course_id=course_id).all()
        week_ids = [w.id for w in weeks]
        
        # Materials completion
        materials = WeekMaterial.query.filter(WeekMaterial.week_id.in_(week_ids)).all()
        material_ids = [m.id for m in materials]
        completed_materials = LearningProgress.query.filter(
            LearningProgress.user_id == student_id,
            LearningProgress.material_id.in_(material_ids),
            LearningProgress.status == 'completed'
        ).count()
        
        # Assignment performance
        assignments = Assignment.query.filter(Assignment.week_id.in_(week_ids)).all()
        assignment_ids = [a.id for a in assignments]
        submissions = AssignmentSubmission.query.filter(
            AssignmentSubmission.user_id == student_id,
            AssignmentSubmission.assignment_id.in_(assignment_ids),
            AssignmentSubmission.status == 'graded'
        ).all()
        
        assignment_scores = []
        for sub in submissions:
            assign = next((a for a in assignments if a.id == sub.assignment_id), None)
            if assign and sub.score is not None:
                assignment_scores.append({
                    'title': assign.title,
                    'score': sub.score,
                    'max_points': assign.max_points,
                    'percentage': (sub.score / assign.max_points * 100) if assign.max_points > 0 else 0,
                    'topics': assign.topics or []
                })
        
        avg_assignment_score = sum(a['percentage'] for a in assignment_scores) / len(assignment_scores) if assignment_scores else 0
        
        # Exam results
        exams = Exam.query.filter_by(course_id=course_id).all()
        exam_results = []
        for exam in exams:
            result = ExamResult.query.filter_by(user_id=student_id, exam_id=exam.id).first()
            if result:
                exam_results.append({
                    'title': exam.title,
                    'type': exam.exam_type,
                    'score': result.score,
                    'percentage': result.percentage,
                    'passed': result.passed
                })
        
        avg_exam_score = sum(e['percentage'] for e in exam_results) / len(exam_results) if exam_results else 0
        
        # Build AI prompt
        performance_data = f"""
Student: {student.full_name}
Course: {course.title}

Progress Summary:
- Overall Progress: {enrollment.progress_percent or 0}%
- Materials Completed: {completed_materials} of {len(materials)}
- Assignments Submitted: {len(submissions)} of {len(assignments)}
- Average Assignment Score: {avg_assignment_score:.1f}%

Assignment Performance:
{chr(10).join([f"- {a['title']}: {a['score']}/{a['max_points']} ({a['percentage']:.1f}%)" for a in assignment_scores]) if assignment_scores else "No graded assignments yet"}

Exam Results:
{chr(10).join([f"- {e['title']}: {e['percentage']:.1f}% ({'Passed' if e['passed'] else 'Not Passed'})" for e in exam_results]) if exam_results else "No exams taken yet"}

Topics with weak performance (below 70%):
{chr(10).join([f"- {a['title']}: {a['percentage']:.1f}%" for a in assignment_scores if a['percentage'] < 70]) if assignment_scores else "None identified"}
"""
        
        ai_prompt = f"""You are an educational advisor. Based on the following student performance data, provide a comprehensive assessment. Be specific and actionable.

{performance_data}

Provide your analysis in the following JSON format:
{{
    "performance_summary": "A 2-3 sentence overall assessment",
    "strengths": ["List 2-4 specific strengths"],
    "areas_for_improvement": ["List 2-4 specific areas needing work"],
    "recommended_actions": ["List 3-5 specific actionable steps the student should take"],
    "suggested_learning_methods": ["List 2-3 learning strategies suited to this student"],
    "extra_assignments_suggested": ["List 2-3 types of additional practice that would help"]
}}

Be encouraging but honest. Focus on specific, actionable recommendations."""

        # Call AI service
        try:
            from app.services.ai_service import AIService
            ai_service = AIService()
            
            # Get API key from environment
            openai_key = os.environ.get('OPENAI_API_KEY')
            
            if openai_key:
                response = ai_service._chat_openai(
                    message=ai_prompt,
                    api_key=openai_key,
                    version='gpt-4o-mini'
                )
                
                if response.get('success'):
                    ai_response = response.get('message', '')
                    
                    # Parse JSON from response
                    import json
                    import re
                    
                    # Try to extract JSON from response
                    json_match = re.search(r'\{[\s\S]*\}', ai_response)
                    if json_match:
                        try:
                            report_data = json.loads(json_match.group())
                        except:
                            report_data = {
                                'performance_summary': ai_response,
                                'strengths': [],
                                'areas_for_improvement': [],
                                'recommended_actions': [],
                                'suggested_learning_methods': [],
                                'extra_assignments_suggested': []
                            }
                    else:
                        report_data = {
                            'performance_summary': ai_response,
                            'strengths': [],
                            'areas_for_improvement': [],
                            'recommended_actions': [],
                            'suggested_learning_methods': [],
                            'extra_assignments_suggested': []
                        }
                else:
                    # Fallback to basic analysis
                    report_data = generate_basic_report(student, enrollment, completed_materials, len(materials), 
                                                       len(submissions), len(assignments), avg_assignment_score)
            else:
                report_data = generate_basic_report(student, enrollment, completed_materials, len(materials),
                                                   len(submissions), len(assignments), avg_assignment_score)
        except Exception as ai_error:
            print(f"AI service error: {ai_error}")
            report_data = generate_basic_report(student, enrollment, completed_materials, len(materials),
                                               len(submissions), len(assignments), avg_assignment_score)
        
        # Save report to database
        report = AIPerformanceReport(
            id=str(uuid.uuid4()),
            student_id=student_id,
            course_id=course_id,
            generated_by=user_id,
            performance_summary=report_data.get('performance_summary'),
            strengths=report_data.get('strengths', []),
            areas_for_improvement=report_data.get('areas_for_improvement', []),
            recommended_actions=report_data.get('recommended_actions', []),
            suggested_learning_methods=report_data.get('suggested_learning_methods', []),
            extra_assignments_suggested=report_data.get('extra_assignments_suggested', []),
            current_progress=enrollment.progress_percent or 0,
            average_score=avg_assignment_score,
            assignments_completed=len(submissions),
            materials_completed=completed_materials
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'report': {
                'id': report.id,
                'student_name': student.full_name,
                'course_title': course.title,
                'performance_summary': report.performance_summary,
                'strengths': report.strengths,
                'areas_for_improvement': report.areas_for_improvement,
                'recommended_actions': report.recommended_actions,
                'suggested_learning_methods': report.suggested_learning_methods,
                'extra_assignments_suggested': report.extra_assignments_suggested,
                'metrics': {
                    'progress': report.current_progress,
                    'average_score': report.average_score,
                    'assignments_completed': report.assignments_completed,
                    'materials_completed': report.materials_completed
                },
                'generated_at': report.created_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error generating AI report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def generate_basic_report(student, enrollment, completed_materials, total_materials, 
                         completed_assignments, total_assignments, avg_score):
    """Generate a basic report without AI"""
    progress = enrollment.progress_percent or 0
    
    # Determine performance level
    if avg_score >= 85:
        level = "excellent"
        summary = f"{student.full_name} is performing excellently in this course with an average score of {avg_score:.1f}%."
    elif avg_score >= 70:
        level = "good"
        summary = f"{student.full_name} is performing well with an average score of {avg_score:.1f}%. Some areas could use additional focus."
    elif avg_score >= 50:
        level = "moderate"
        summary = f"{student.full_name} has a moderate performance level ({avg_score:.1f}%). Additional support and practice is recommended."
    else:
        level = "needs_improvement"
        summary = f"{student.full_name} is struggling with course material ({avg_score:.1f}%). Immediate intervention and additional support is recommended."
    
    return {
        'performance_summary': summary,
        'strengths': [
            "Consistent engagement with course content" if progress > 50 else "Enrolled and beginning the course",
            f"Completed {completed_assignments} assignments" if completed_assignments > 0 else "Ready to start assignments"
        ],
        'areas_for_improvement': [
            "Complete more course materials" if completed_materials < total_materials * 0.5 else "Review challenging topics",
            "Focus on improving assignment scores" if avg_score < 70 else "Maintain current performance level"
        ],
        'recommended_actions': [
            "Review course materials weekly",
            "Complete all assignments before due dates",
            "Seek help from instructor on challenging topics",
            "Practice with additional resources"
        ],
        'suggested_learning_methods': [
            "Active note-taking during video lectures",
            "Practice problems after each topic",
            "Form study groups with classmates"
        ],
        'extra_assignments_suggested': [
            "Review exercises for weak topics",
            "Practice quizzes before exams",
            "Additional reading materials"
        ]
    }


# ============================================
# SURVEY MANAGEMENT
# ============================================

@teacher_bp.route('/courses/<course_id>/surveys', methods=['GET'])
@teacher_required
def get_course_surveys(course_id):
    """Get all surveys for a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyQuestion, SurveyResponse, CourseInstructor, Enrollment
        
        user_id = session.get('user_id')
        
        instructor_check = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        surveys = Survey.query.filter_by(course_id=course_id).all()
        
        total_students = Enrollment.query.filter_by(
            course_id=course_id,
            status='approved'
        ).count()
        
        result = []
        for survey in surveys:
            questions_count = SurveyQuestion.query.filter_by(survey_id=survey.id).count()
            responses_count = SurveyResponse.query.filter_by(survey_id=survey.id).count()
            
            result.append({
                'id': survey.id,
                'title': survey.title,
                'description': survey.description,
                'survey_type': survey.survey_type,
                'is_required': survey.is_required,
                'is_published': survey.is_published,
                'created_at': survey.created_at.isoformat() if survey.created_at else None,
                'questions_count': questions_count,
                'statistics': {
                    'total_students': total_students,
                    'response_count': responses_count,
                    'response_rate': round((responses_count / total_students * 100), 1) if total_students > 0 else 0
                }
            })
        
        return jsonify({
            'success': True,
            'surveys': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/courses/<course_id>/surveys', methods=['POST'])
@teacher_required
def create_course_survey(course_id):
    """Create a new survey for a course"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyQuestion, CourseInstructor, Course
        
        user_id = session.get('user_id')
        
        instructor_check = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        data = request.get_json()
        survey_type = data.get('survey_type', 'training_feedback')
        
        survey = Survey(
            id=str(uuid.uuid4()),
            course_id=course_id,
            title=data.get('title'),
            description=data.get('description'),
            survey_type=survey_type,
            is_required=data.get('is_required', False),
            is_published=data.get('is_published', False)
        )
        
        db.session.add(survey)
        
        # Add questions if provided in request
        questions = data.get('questions', [])
        questions_added = 0
        
        if questions:
            for idx, q in enumerate(questions):
                question = SurveyQuestion(
                    id=str(uuid.uuid4()),
                    survey_id=survey.id,
                    question_text=q.get('question_text'),
                    question_type=q.get('question_type', 'multiple_choice'),
                    options=q.get('options', []),
                    is_required=q.get('is_required', True),
                    order_index=idx
                )
                db.session.add(question)
                questions_added += 1
        
        # Auto-add standard feedback questions for exit surveys and training feedback surveys
        if survey_type in ['exit_survey', 'training_feedback'] and not questions:
            from app.constants.feedback_template import get_feedback_questions_for_survey
            feedback_questions = get_feedback_questions_for_survey()
            for q in feedback_questions:
                question = SurveyQuestion(
                    id=str(uuid.uuid4()),
                    survey_id=survey.id,
                    question_text=q['question_text'],
                    question_text_ar=q['question_text_ar'],
                    question_type=q['question_type'],
                    options=q['options'],
                    options_ar=q['options_ar'],
                    is_required=q['is_required'],
                    order_index=q['order_index'],
                    is_ai_generated=False
                )
                db.session.add(question)
                questions_added += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'survey': {
                'id': survey.id,
                'title': survey.title,
                'questions_added': questions_added
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/surveys/<survey_id>', methods=['GET'])
@teacher_required
def get_survey_detail(survey_id):
    """Get survey details with questions"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyQuestion, CourseInstructor
        
        user_id = session.get('user_id')
        
        survey = Survey.query.filter_by(id=survey_id).first()
        if not survey:
            return jsonify({'error': 'Survey not found'}), 404
        
        instructor_check = CourseInstructor.query.filter_by(course_id=survey.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        questions = SurveyQuestion.query.filter_by(survey_id=survey_id).order_by(SurveyQuestion.order_index).all()
        
        return jsonify({
            'success': True,
            'survey': {
                'id': survey.id,
                'title': survey.title,
                'description': survey.description,
                'survey_type': survey.survey_type,
                'is_required': survey.is_required,
                'is_published': survey.is_published
            },
            'questions': [{
                'id': q.id,
                'question_text': q.question_text,
                'question_text_ar': q.question_text_ar,
                'question_type': q.question_type,
                'options': q.options,
                'options_ar': q.options_ar,
                'is_required': q.is_required,
                'order_index': q.order_index
            } for q in questions]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/surveys/<survey_id>', methods=['PUT'])
@teacher_required
def update_survey(survey_id):
    """Update survey details"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, CourseInstructor
        
        user_id = session.get('user_id')
        
        survey = Survey.query.filter_by(id=survey_id).first()
        if not survey:
            return jsonify({'error': 'Survey not found'}), 404
        
        instructor_check = CourseInstructor.query.filter_by(course_id=survey.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        if 'title' in data:
            survey.title = data['title']
        if 'description' in data:
            survey.description = data['description']
        if 'survey_type' in data:
            survey.survey_type = data['survey_type']
        if 'is_required' in data:
            survey.is_required = data['is_required']
        if 'is_published' in data:
            is_pub = data['is_published']
            if isinstance(is_pub, bool):
                survey.is_published = is_pub
            else:
                survey.is_published = str(is_pub).lower() in ('true', '1', 'yes')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Survey updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/surveys/<survey_id>/questions', methods=['POST'])
@teacher_required
def add_survey_question(survey_id):
    """Add a question to a survey"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyQuestion, CourseInstructor
        
        user_id = session.get('user_id')
        
        survey = Survey.query.filter_by(id=survey_id).first()
        if not survey:
            return jsonify({'error': 'Survey not found'}), 404
        
        instructor_check = CourseInstructor.query.filter_by(course_id=survey.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        max_order = db.session.query(db.func.max(SurveyQuestion.order_index)).filter_by(survey_id=survey_id).scalar() or 0
        
        question = SurveyQuestion(
            id=str(uuid.uuid4()),
            survey_id=survey_id,
            question_text=data.get('question_text'),
            question_text_ar=data.get('question_text_ar'),
            question_type=data.get('question_type', 'multiple_choice'),
            options=data.get('options', []),
            options_ar=data.get('options_ar', []),
            correct_answer=data.get('correct_answer'),
            is_required=data.get('is_required', True),
            order_index=max_order + 1
        )
        
        db.session.add(question)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'question': {'id': question.id}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/surveys/<survey_id>/questions/<question_id>', methods=['PUT'])
@teacher_required
def update_survey_question(survey_id, question_id):
    """Update a survey question"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyQuestion, CourseInstructor
        
        user_id = session.get('user_id')
        
        survey = Survey.query.filter_by(id=survey_id).first()
        if not survey:
            return jsonify({'error': 'Survey not found'}), 404
        
        instructor_check = CourseInstructor.query.filter_by(course_id=survey.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        question = SurveyQuestion.query.filter_by(id=question_id, survey_id=survey_id).first()
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        data = request.get_json()
        print(f"[DEBUG] Update survey question {question_id}: {data}")
        
        if 'question_text' in data:
            question.question_text = data['question_text']
        if 'question_text_ar' in data:
            question.question_text_ar = data['question_text_ar']
        if 'question_type' in data:
            question.question_type = data['question_type']
        if 'options' in data:
            question.options = data['options']
        if 'options_ar' in data:
            question.options_ar = data['options_ar']
        if 'correct_answer' in data:
            question.correct_answer = data['correct_answer']
            print(f"[DEBUG] Set correct_answer to: {data['correct_answer']}")
        if 'is_required' in data:
            question.is_required = data['is_required']
        
        db.session.commit()
        print(f"[DEBUG] Question saved. correct_answer now: {question.correct_answer}")
        
        return jsonify({
            'success': True,
            'message': 'Question updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/surveys/<survey_id>/questions/<question_id>', methods=['DELETE'])
@teacher_required
def delete_survey_question(survey_id, question_id):
    """Delete a question from a survey"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyQuestion, CourseInstructor
        
        user_id = session.get('user_id')
        
        survey = Survey.query.filter_by(id=survey_id).first()
        if not survey:
            return jsonify({'error': 'Survey not found'}), 404
        
        instructor_check = CourseInstructor.query.filter_by(course_id=survey.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        question = SurveyQuestion.query.filter_by(id=question_id, survey_id=survey_id).first()
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        db.session.delete(question)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Question deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/surveys/<survey_id>', methods=['DELETE'])
@teacher_required
def delete_survey(survey_id):
    """Delete a survey"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyQuestion, SurveyResponse, CourseInstructor
        
        user_id = session.get('user_id')
        
        survey = Survey.query.filter_by(id=survey_id).first()
        if not survey:
            return jsonify({'error': 'Survey not found'}), 404
        
        instructor_check = CourseInstructor.query.filter_by(course_id=survey.course_id, user_id=user_id).first()
        if not instructor_check:
            return jsonify({'error': 'Access denied'}), 403
        
        # Delete related records
        SurveyQuestion.query.filter_by(survey_id=survey_id).delete()
        SurveyResponse.query.filter_by(survey_id=survey_id).delete()
        
        db.session.delete(survey)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Survey deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================
# AI QUESTION GENERATION
# ============================================

@teacher_bp.route('/courses/<course_id>/generate-questions', methods=['POST'])
@teacher_required
def generate_questions_from_file(course_id):
    """
    Generate bilingual (Arabic/English) questions from uploaded file using AI
    
    Request body (multipart/form-data):
        - file: The uploaded file (PDF, DOCX, TXT, PPTX)
        - num_true_false: Number of True/False questions (default: 5)
        - num_mcq: Number of Multiple Choice questions (default: 5)
        - target_type: 'exam' or 'survey' (default: 'exam')
        - target_id: ID of the exam or survey to add questions to (optional)
        - difficulty: 'easy', 'medium', 'hard' (default: 'medium')
        - topic: Optional topic name
    """
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import CourseInstructor, Course, Exam, Survey, ExamQuestion, SurveyQuestion
        from app.services.question_generator import QuestionGenerator
        from app.services.ai_service import AIService
        from config.config import Config
        
        user_id = session.get('user_id')
        
        instructor_check = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not instructor_check:
            role = session.get('role', '').lower()
            if role not in ['institution_admin', 'admin', 'super_admin', 'superadmin']:
                return jsonify({'error': 'Access denied'}), 403
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        allowed_extensions = ['txt', 'pdf', 'doc', 'docx', 'ppt', 'pptx']
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'File type not supported. Allowed: {", ".join(allowed_extensions)}'}), 400
        
        num_true_false = int(request.form.get('num_true_false', 5))
        num_mcq = int(request.form.get('num_mcq', 5))
        target_type = request.form.get('target_type', 'exam')
        target_id = request.form.get('target_id')
        difficulty = request.form.get('difficulty', 'medium')
        topic = request.form.get('topic', '')
        
        file_content = file.read()
        
        ai_service = AIService()
        config = Config()
        generator = QuestionGenerator(ai_service, config)
        
        text_content = generator.extract_text_from_file(file_content, file_ext)
        
        if not text_content or len(text_content) < 50:
            return jsonify({'error': 'Could not extract sufficient text from file'}), 400
        
        result = generator.generate_questions(
            content=text_content,
            num_true_false=num_true_false,
            num_mcq=num_mcq,
            question_type=target_type,
            difficulty=difficulty,
            topic=topic
        )
        
        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Question generation failed')}), 500
        
        generated_questions = result.get('questions', [])
        saved_questions = []
        
        def convert_answer_to_index(answer, question_type):
            """Convert letter answer (A/B/C/D) to numeric index (0/1/2/3)"""
            if question_type == 'true_false':
                if str(answer).upper() in ['TRUE', 'T', 'A', '0']:
                    return 0
                elif str(answer).upper() in ['FALSE', 'F', 'B', '1']:
                    return 1
                return 0
            else:
                letter_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4}
                if str(answer).upper() in letter_map:
                    return letter_map[str(answer).upper()]
                try:
                    return int(answer)
                except (ValueError, TypeError):
                    return 0
        
        if target_id:
            if target_type == 'exam':
                exam = Exam.query.filter_by(id=target_id, course_id=course_id).first()
                if not exam:
                    return jsonify({'error': 'Exam not found'}), 404
                
                max_order = db.session.query(db.func.max(ExamQuestion.order_index)).filter_by(exam_id=target_id).scalar() or 0
                
                for idx, q in enumerate(generated_questions):
                    q_type = 'true_false' if q.get('type') == 'true_false' else 'multiple_choice'
                    correct_idx = convert_answer_to_index(q.get('correct_answer', ''), q_type)
                    
                    new_question = ExamQuestion(
                        id=str(uuid.uuid4()),
                        exam_id=target_id,
                        question_text=q.get('question_en', ''),
                        question_text_ar=q.get('question_ar', ''),
                        question_type=q_type,
                        options=q.get('options_en', []),
                        options_ar=q.get('options_ar', []),
                        correct_answer=correct_idx,
                        difficulty=q.get('difficulty', difficulty),
                        topic=topic,
                        order_index=max_order + idx + 1,
                        is_ai_generated=True,
                        source_file=file.filename
                    )
                    db.session.add(new_question)
                    saved_questions.append({
                        'id': new_question.id,
                        'question_en': new_question.question_text,
                        'question_ar': new_question.question_text_ar,
                        'type': new_question.question_type
                    })
                
            elif target_type == 'survey':
                survey = Survey.query.filter_by(id=target_id, course_id=course_id).first()
                if not survey:
                    return jsonify({'error': 'Survey not found'}), 404
                
                max_order = db.session.query(db.func.max(SurveyQuestion.order_index)).filter_by(survey_id=target_id).scalar() or 0
                
                for idx, q in enumerate(generated_questions):
                    new_question = SurveyQuestion(
                        id=str(uuid.uuid4()),
                        survey_id=target_id,
                        question_text=q.get('question_en', ''),
                        question_text_ar=q.get('question_ar', ''),
                        question_type='true_false' if q.get('type') == 'true_false' else 'multiple_choice',
                        options=q.get('options_en', []),
                        options_ar=q.get('options_ar', []),
                        order_index=max_order + idx + 1,
                        is_ai_generated=True,
                        source_file=file.filename
                    )
                    db.session.add(new_question)
                    saved_questions.append({
                        'id': new_question.id,
                        'question_en': new_question.question_text,
                        'question_ar': new_question.question_text_ar,
                        'type': new_question.question_type
                    })
            
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Generated {len(generated_questions)} questions',
            'questions': generated_questions if not target_id else saved_questions,
            'saved_to_target': target_id is not None
        })
        
    except Exception as e:
        if db:
            db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/courses/<course_id>/feedback-template', methods=['GET'])
@teacher_required
def get_feedback_survey_template(course_id):
    """
    Get the FIXED, STANDARDIZED feedback survey template.
    This template is the same for ALL courses across the system.
    The course_id is only used for access control validation.
    """
    try:
        from app.constants.feedback_template import get_standard_feedback_template
        
        template = get_standard_feedback_template()
        
        return jsonify({
            'success': True,
            'template': template,
            'questions': template['questions'],
            'categories': template['categories'],
            'is_standard': True,
            'version': template['version']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/courses/<course_id>/surveys/<survey_id>/add-feedback-questions', methods=['POST'])
@teacher_required
def add_feedback_questions_to_survey(course_id, survey_id):
    """
    Add the FIXED, STANDARDIZED feedback survey questions to an existing survey.
    Uses the system-wide template that is the same for ALL courses.
    
    Request body (JSON):
        - categories: List of categories to include ['course_materials', 'teacher', 'venue', 'overall', 'feedback']
                     If not provided, ALL categories are included (full standard template)
    """
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyQuestion, CourseInstructor
        from app.constants.feedback_template import get_feedback_questions_for_survey, FEEDBACK_TEMPLATE_VERSION
        
        user_id = session.get('user_id')
        
        survey = Survey.query.filter_by(id=survey_id, course_id=course_id).first()
        if not survey:
            return jsonify({'error': 'Survey not found'}), 404
        
        instructor_check = CourseInstructor.query.filter_by(course_id=course_id, user_id=user_id).first()
        if not instructor_check:
            role = session.get('role', '').lower()
            if role not in ['institution_admin', 'admin', 'super_admin', 'superadmin']:
                return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json(silent=True) or {}
        selected_categories = data.get('categories', ['course_materials', 'teacher', 'venue', 'overall', 'feedback'])
        
        feedback_questions = get_feedback_questions_for_survey()
        
        filtered_questions = [q for q in feedback_questions if q.get('category') in selected_categories]
        
        max_order = db.session.query(db.func.max(SurveyQuestion.order_index)).filter_by(survey_id=survey_id).scalar() or 0
        
        added_questions = []
        for idx, q in enumerate(filtered_questions):
            new_question = SurveyQuestion(
                id=str(uuid.uuid4()),
                survey_id=survey_id,
                question_text=q.get('question_text', ''),
                question_text_ar=q.get('question_text_ar', ''),
                question_type=q.get('question_type', 'likert'),
                options=q.get('options', []),
                options_ar=q.get('options_ar', []),
                order_index=max_order + idx + 1,
                is_ai_generated=False,
                is_required=q.get('is_required', True)
            )
            db.session.add(new_question)
            added_questions.append({
                'id': new_question.id,
                'template_id': q.get('template_id'),
                'question_en': new_question.question_text,
                'question_ar': new_question.question_text_ar,
                'type': new_question.question_type,
                'category': q.get('category'),
                'is_required': new_question.is_required
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Added {len(added_questions)} standard feedback questions to survey',
            'questions': added_questions,
            'template_version': FEEDBACK_TEMPLATE_VERSION,
            'is_standard_template': True
        })
        
    except Exception as e:
        if db:
            db.session.rollback()
        return jsonify({'error': str(e)}), 500
