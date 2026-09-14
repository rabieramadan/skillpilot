"""
Attendance Management API Routes
Daily attendance tracking per class for teachers and admins
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime, date
from functools import wraps

attendance_bp = Blueprint('attendance', __name__)


def get_db():
    """Get database session"""
    try:
        from app.models import db
        return db.session
    except Exception as e:
        print(f"Database error: {e}")
        return None


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def teacher_or_admin_required(f):
    """Decorator to require teacher or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        role = session.get('role', '').lower()
        if role not in ['super_admin', 'superadmin', 'admin', 'institution_admin', 'instructor', 'teacher']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        return f(*args, **kwargs)
    return decorated_function


def verify_course_access(course_id, user_id, role):
    """
    Verify user has access to the course based on their role.
    Returns (has_access, error_message)
    """
    from app.models import Course

    course = Course.query.get(course_id)
    if not course:
        return False, 'Class not found'

    role = role.lower() if role else ''

    # Admins and teachers have access to all courses
    if role in ['super_admin', 'superadmin', 'admin', 'institution_admin', 'instructor', 'teacher']:
        return True, None

    return False, 'Access denied'


def get_enrolled_student_ids(course_id):
    """Get set of enrolled student IDs for a course"""
    from app.models import Enrollment
    
    enrollments = Enrollment.query.filter(
        Enrollment.course_id == course_id,
        Enrollment.status.in_(['active', 'approved'])
    ).all()
    
    return {e.user_id for e in enrollments}


@attendance_bp.route('/api/attendance/class/<course_id>/dates', methods=['GET'])
@teacher_or_admin_required
def get_attendance_dates(course_id):
    """Get list of dates with attendance records for a class"""
    try:
        from app.models import Attendance, Course
        
        # Verify course access
        user_id = session.get('user_id')
        role = session.get('role', '')

        has_access, error = verify_course_access(course_id, user_id, role)
        if not has_access:
            return jsonify({'error': error}), 403 if error != 'Class not found' else 404

        course = Course.query.get(course_id)

        dates = Attendance.query.filter_by(course_id=course_id)\
            .with_entities(Attendance.attendance_date)\
            .distinct()\
            .order_by(Attendance.attendance_date.desc())\
            .all()
        
        return jsonify({
            'success': True,
            'dates': [d[0].strftime('%Y-%m-%d') for d in dates],
            'course': {
                'id': course.id,
                'title': course.title,
                'title_ar': course.title_ar,
                'code': course.code
            }
        })
    except Exception as e:
        print(f"Get attendance dates error: {e}")
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/api/attendance/class/<course_id>/date/<attendance_date>', methods=['GET'])
@teacher_or_admin_required
def get_daily_attendance(course_id, attendance_date):
    """Get attendance list for a specific date"""
    try:
        from app.models import Attendance, Course, Enrollment, User
        
        # Verify course access
        user_id = session.get('user_id')
        role = session.get('role', '')

        has_access, error = verify_course_access(course_id, user_id, role)
        if not has_access:
            return jsonify({'error': error}), 403 if error != 'Class not found' else 404

        course = Course.query.get(course_id)

        try:
            target_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        enrolled_students = Enrollment.query.filter(
            Enrollment.course_id == course_id,
            Enrollment.status.in_(['active', 'approved'])
        ).all()
        
        attendance_records = {
            a.user_id: a for a in Attendance.query.filter_by(
                course_id=course_id,
                attendance_date=target_date
            ).all()
        }
        
        students_list = []
        for enrollment in enrolled_students:
            student = User.query.get(enrollment.user_id)
            if not student:
                continue
            
            record = attendance_records.get(student.id)
            students_list.append({
                'id': student.id,
                'username': student.username,
                'full_name': student.full_name or student.username,
                'full_name_ar': getattr(student, 'full_name_ar', '') or '',
                'email': student.email,
                'status': record.status if record else 'not_recorded',
                'notes': record.notes if record else '',
                'notes_ar': record.notes_ar if record else '',
                'attendance_id': record.id if record else None
            })
        
        students_list.sort(key=lambda x: x['full_name'].lower())
        
        present_count = sum(1 for s in students_list if s['status'] == 'present')
        absent_count = sum(1 for s in students_list if s['status'] == 'absent')
        late_count = sum(1 for s in students_list if s['status'] == 'late')
        excused_count = sum(1 for s in students_list if s['status'] == 'excused')
        not_recorded = sum(1 for s in students_list if s['status'] == 'not_recorded')
        
        return jsonify({
            'success': True,
            'date': attendance_date,
            'course': {
                'id': course.id,
                'title': course.title,
                'title_ar': course.title_ar,
                'code': course.code
            },
            'students': students_list,
            'summary': {
                'total': len(students_list),
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'excused': excused_count,
                'not_recorded': not_recorded
            }
        })
    except Exception as e:
        print(f"Get daily attendance error: {e}")
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/api/attendance/class/<course_id>/date/<attendance_date>', methods=['POST'])
@teacher_or_admin_required
def record_attendance(course_id, attendance_date):
    """Record or update attendance for multiple students"""
    try:
        from app.models import db, Attendance, Course, Enrollment
        
        # Verify course access
        user_id = session.get('user_id')
        role = session.get('role', '')

        has_access, error = verify_course_access(course_id, user_id, role)
        if not has_access:
            return jsonify({'error': error}), 403 if error != 'Class not found' else 404

        course = Course.query.get(course_id)

        try:
            target_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Get enrolled student IDs for validation
        enrolled_ids = get_enrolled_student_ids(course_id)
        
        data = request.get_json()
        records = data.get('records', [])
        
        if not records:
            return jsonify({'error': 'No attendance records provided'}), 400
        
        user_id = session.get('user_id')
        updated_count = 0
        created_count = 0
        
        skipped_count = 0
        for record in records:
            student_id = record.get('student_id')
            status = record.get('status', 'present')
            notes = record.get('notes', '')
            notes_ar = record.get('notes_ar', '')
            
            if not student_id:
                continue
            
            # Validate student is enrolled in this course
            if student_id not in enrolled_ids:
                skipped_count += 1
                continue
            
            existing = Attendance.query.filter_by(
                course_id=course_id,
                user_id=student_id,
                attendance_date=target_date
            ).first()
            
            if existing:
                existing.status = status
                existing.notes = notes
                existing.notes_ar = notes_ar
                existing.recorded_by = user_id
                existing.recorded_at = datetime.utcnow()
                updated_count += 1
            else:
                new_record = Attendance(
                    course_id=course_id,
                    user_id=student_id,
                    attendance_date=target_date,
                    status=status,
                    notes=notes,
                    notes_ar=notes_ar,
                    recorded_by=user_id,
                    recorded_at=datetime.utcnow()
                )
                db.session.add(new_record)
                created_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Attendance recorded: {created_count} new, {updated_count} updated',
            'created': created_count,
            'updated': updated_count
        })
    except Exception as e:
        from app.models import db
        db.session.rollback()
        print(f"Record attendance error: {e}")
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/api/attendance/class/<course_id>/date/<attendance_date>/student/<student_id>', methods=['PUT'])
@teacher_or_admin_required
def update_student_attendance(course_id, attendance_date, student_id):
    """Update a single student's attendance"""
    try:
        from app.models import db, Attendance, Course
        
        # Verify course access
        user_id = session.get('user_id')
        role = session.get('role', '')

        has_access, error = verify_course_access(course_id, user_id, role)
        if not has_access:
            return jsonify({'error': error}), 403 if error != 'Class not found' else 404

        course = Course.query.get(course_id)

        # Validate student is enrolled
        enrolled_ids = get_enrolled_student_ids(course_id)
        if student_id not in enrolled_ids:
            return jsonify({'error': 'Student is not enrolled in this course'}), 400
        
        try:
            target_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        data = request.get_json()
        status = data.get('status', 'present')
        notes = data.get('notes', '')
        notes_ar = data.get('notes_ar', '')
        
        existing = Attendance.query.filter_by(
            course_id=course_id,
            user_id=student_id,
            attendance_date=target_date
        ).first()
        
        if existing:
            existing.status = status
            existing.notes = notes
            existing.notes_ar = notes_ar
            existing.recorded_by = user_id
            existing.recorded_at = datetime.utcnow()
        else:
            existing = Attendance(
                course_id=course_id,
                user_id=student_id,
                attendance_date=target_date,
                status=status,
                notes=notes,
                notes_ar=notes_ar,
                recorded_by=user_id,
                recorded_at=datetime.utcnow()
            )
            db.session.add(existing)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Attendance updated',
            'attendance': {
                'id': existing.id,
                'status': existing.status,
                'notes': existing.notes
            }
        })
    except Exception as e:
        from app.models import db
        db.session.rollback()
        print(f"Update student attendance error: {e}")
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/api/attendance/class/<course_id>/print/<attendance_date>', methods=['GET'])
@teacher_or_admin_required
def get_printable_attendance(course_id, attendance_date):
    """Get attendance data formatted for printing"""
    try:
        from app.models import Attendance, Course, Enrollment, User

        # Verify course access
        user_id = session.get('user_id')
        role = session.get('role', '')

        has_access, error = verify_course_access(course_id, user_id, role)
        if not has_access:
            return jsonify({'error': error}), 403 if error != 'Class not found' else 404

        course = Course.query.get(course_id)
        
        try:
            target_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        enrolled_students = Enrollment.query.filter(
            Enrollment.course_id == course_id,
            Enrollment.status.in_(['active', 'approved'])
        ).all()
        
        attendance_records = {
            a.user_id: a for a in Attendance.query.filter_by(
                course_id=course_id,
                attendance_date=target_date
            ).all()
        }
        
        students_list = []
        seq = 1
        for enrollment in enrolled_students:
            student = User.query.get(enrollment.user_id)
            if not student:
                continue
            
            record = attendance_records.get(student.id)
            students_list.append({
                'seq': seq,
                'id': student.id,
                'username': student.username,
                'full_name': student.full_name or student.username,
                'full_name_ar': getattr(student, 'full_name_ar', '') or '',
                'email': student.email,
                'status': record.status if record else 'not_recorded',
                'status_display': {
                    'present': 'Present / حاضر',
                    'absent': 'Absent / غائب',
                    'late': 'Late / متأخر',
                    'excused': 'Excused / معذور',
                    'not_recorded': '-- / --'
                }.get(record.status if record else 'not_recorded', '--'),
                'notes': record.notes if record else ''
            })
            seq += 1
        
        students_list.sort(key=lambda x: x['full_name'].lower())
        for i, s in enumerate(students_list):
            s['seq'] = i + 1
        
        present_count = sum(1 for s in students_list if s['status'] == 'present')
        absent_count = sum(1 for s in students_list if s['status'] == 'absent')
        late_count = sum(1 for s in students_list if s['status'] == 'late')
        excused_count = sum(1 for s in students_list if s['status'] == 'excused')
        
        formatted_date = target_date.strftime('%A, %B %d, %Y')
        
        return jsonify({
            'success': True,
            'print_data': {
                'institution': {
                    'name': 'SkillPilot',
                    'logo_url': '',
                    'logo_url_2': ''
                },
                'course': {
                    'id': course.id,
                    'title': course.title,
                    'title_ar': course.title_ar or '',
                    'code': course.code
                },
                'date': attendance_date,
                'date_formatted': formatted_date,
                'students': students_list,
                'summary': {
                    'total': len(students_list),
                    'present': present_count,
                    'absent': absent_count,
                    'late': late_count,
                    'excused': excused_count
                },
                'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            }
        })
    except Exception as e:
        print(f"Get printable attendance error: {e}")
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/api/attendance/class/<course_id>/summary', methods=['GET'])
@teacher_or_admin_required
def get_attendance_summary(course_id):
    """Get attendance summary for a class over a date range"""
    try:
        from app.models import Attendance, Course, Enrollment, User
        from sqlalchemy import func
        
        # Verify course access
        user_id = session.get('user_id')
        role = session.get('role', '')

        has_access, error = verify_course_access(course_id, user_id, role)
        if not has_access:
            return jsonify({'error': error}), 403 if error != 'Class not found' else 404

        course = Course.query.get(course_id)

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Attendance.query.filter_by(course_id=course_id)
        
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.attendance_date >= start)
            except ValueError:
                pass
        
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.attendance_date <= end)
            except ValueError:
                pass
        
        total_days = query.with_entities(Attendance.attendance_date).distinct().count()
        
        per_student = {}
        for record in query.all():
            if record.user_id not in per_student:
                student = User.query.get(record.user_id)
                per_student[record.user_id] = {
                    'student_id': record.user_id,
                    'full_name': student.full_name if student else 'Unknown',
                    'full_name_ar': student.full_name_ar if student else '',
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'excused': 0,
                    'total': 0
                }
            
            per_student[record.user_id][record.status] = per_student[record.user_id].get(record.status, 0) + 1
            per_student[record.user_id]['total'] += 1
        
        for student_id in per_student:
            total = per_student[student_id]['total']
            present = per_student[student_id]['present']
            if total > 0:
                per_student[student_id]['attendance_rate'] = round((present / total) * 100, 1)
            else:
                per_student[student_id]['attendance_rate'] = 0
        
        summary_list = list(per_student.values())
        summary_list.sort(key=lambda x: x['full_name'].lower())
        
        return jsonify({
            'success': True,
            'course': {
                'id': course.id,
                'title': course.title,
                'code': course.code
            },
            'total_days': total_days,
            'students': summary_list
        })
    except Exception as e:
        print(f"Get attendance summary error: {e}")
        return jsonify({'error': str(e)}), 500


# ============== STUDENT SELF-ATTENDANCE ENDPOINTS ==============

@attendance_bp.route('/api/student/attendance/mark', methods=['POST'])
@login_required
def student_mark_attendance():
    """Allow student to mark their own attendance for today"""
    try:
        from app.models import db, Attendance, Enrollment, Course
        
        user_id = session.get('user_id')
        role = session.get('role', '').lower()
        
        # Only students can use this endpoint
        if role != 'student':
            return jsonify({'error': 'This endpoint is for students only'}), 403
        
        data = request.get_json()
        course_id = data.get('course_id')
        
        if not course_id:
            return jsonify({'error': 'Course ID required'}), 400
        
        # Verify student is enrolled in this course
        enrollment = Enrollment.query.filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user_id,
            Enrollment.status.in_(['active', 'approved'])
        ).first()
        
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this course'}), 403
        
        # Get course to check if self-attendance is enabled
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Use today's date
        today = date.today()
        
        # Check if already marked today
        existing = Attendance.query.filter_by(
            course_id=course_id,
            user_id=user_id,
            attendance_date=today
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': 'Attendance already marked for today',
                'attendance': {
                    'id': existing.id,
                    'status': existing.status,
                    'recorded_at': existing.recorded_at.strftime('%Y-%m-%d %H:%M') if existing.recorded_at else None
                }
            }), 400
        
        # Create attendance record
        new_record = Attendance(
            course_id=course_id,
            user_id=user_id,
            attendance_date=today,
            status='present',
            notes='Self-marked by student',
            notes_ar='تم التسجيل ذاتياً من قبل الطالب',
            recorded_by=user_id,
            recorded_at=datetime.utcnow()
        )
        db.session.add(new_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Attendance marked successfully',
            'message_ar': 'تم تسجيل الحضور بنجاح',
            'attendance': {
                'id': new_record.id,
                'status': new_record.status,
                'date': today.strftime('%Y-%m-%d'),
                'recorded_at': new_record.recorded_at.strftime('%Y-%m-%d %H:%M')
            }
        })
    except Exception as e:
        from app.models import db
        db.session.rollback()
        print(f"Student mark attendance error: {e}")
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/api/student/attendance/status/<course_id>', methods=['GET'])
@login_required
def student_attendance_status(course_id):
    """Get student's attendance status for a course"""
    try:
        from app.models import Attendance, Enrollment, Course
        
        user_id = session.get('user_id')
        role = session.get('role', '').lower()
        
        if role != 'student':
            return jsonify({'error': 'This endpoint is for students only'}), 403
        
        # Verify enrollment
        enrollment = Enrollment.query.filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user_id,
            Enrollment.status.in_(['active', 'approved'])
        ).first()
        
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this course'}), 403
        
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Get today's status
        today = date.today()
        today_record = Attendance.query.filter_by(
            course_id=course_id,
            user_id=user_id,
            attendance_date=today
        ).first()
        
        # Get all attendance records for this student in this course
        all_records = Attendance.query.filter_by(
            course_id=course_id,
            user_id=user_id
        ).order_by(Attendance.attendance_date.desc()).all()
        
        # Calculate stats
        present_count = sum(1 for r in all_records if r.status == 'present')
        absent_count = sum(1 for r in all_records if r.status == 'absent')
        late_count = sum(1 for r in all_records if r.status == 'late')
        total = len(all_records)
        
        return jsonify({
            'success': True,
            'course': {
                'id': course.id,
                'title': course.title,
                'title_ar': course.title_ar or ''
            },
            'today': {
                'date': today.strftime('%Y-%m-%d'),
                'marked': today_record is not None,
                'status': today_record.status if today_record else None,
                'can_mark': today_record is None
            },
            'summary': {
                'total_days': total,
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'attendance_rate': round((present_count / total) * 100, 1) if total > 0 else 0
            },
            'history': [{
                'date': r.attendance_date.strftime('%Y-%m-%d'),
                'status': r.status,
                'status_display': {
                    'present': 'Present / حاضر',
                    'absent': 'Absent / غائب',
                    'late': 'Late / متأخر',
                    'excused': 'Excused / معذور'
                }.get(r.status, r.status)
            } for r in all_records[:30]]  # Last 30 records
        })
    except Exception as e:
        print(f"Student attendance status error: {e}")
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/api/student/classes/attendance', methods=['GET'])
@login_required
def student_all_classes_attendance():
    """Get attendance status for all enrolled classes"""
    try:
        from app.models import Attendance, Enrollment, Course
        
        user_id = session.get('user_id')
        role = session.get('role', '').lower()
        
        if role != 'student':
            return jsonify({'error': 'This endpoint is for students only'}), 403
        
        today = date.today()
        
        # Get all active enrollments
        enrollments = Enrollment.query.filter(
            Enrollment.user_id == user_id,
            Enrollment.status.in_(['active', 'approved'])
        ).all()
        
        classes = []
        for enrollment in enrollments:
            course = Course.query.get(enrollment.course_id)
            if not course:
                continue
            
            # Check if marked today
            today_record = Attendance.query.filter_by(
                course_id=course.id,
                user_id=user_id,
                attendance_date=today
            ).first()
            
            # Get attendance summary
            all_records = Attendance.query.filter_by(
                course_id=course.id,
                user_id=user_id
            ).all()
            
            present_count = sum(1 for r in all_records if r.status == 'present')
            total = len(all_records)
            
            classes.append({
                'course_id': course.id,
                'title': course.title,
                'title_ar': course.title_ar or '',
                'code': course.code,
                'today_marked': today_record is not None,
                'today_status': today_record.status if today_record else None,
                'can_mark_today': today_record is None,
                'attendance_rate': round((present_count / total) * 100, 1) if total > 0 else 0,
                'total_days': total
            })
        
        return jsonify({
            'success': True,
            'date': today.strftime('%Y-%m-%d'),
            'classes': classes
        })
    except Exception as e:
        print(f"Student all classes attendance error: {e}")
        return jsonify({'error': str(e)}), 500
