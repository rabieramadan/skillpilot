"""
Shared Class Serializers - Unified data format for classes across all user roles
Ensures synchronized data between super admin, institution admin, teachers, and students
"""

from datetime import datetime


def serialize_base_class(course, include_dates=True):
    """
    Base class serialization - common fields for all roles
    Returns consistent format used by students, teachers, and admins
    """
    return {
        'id': course.id,
        'code': course.code,
        'title': course.title,
        'description': course.description,
        'thumbnail_url': course.thumbnail_url,
        'is_published': course.is_published,
        'passing_threshold': course.passing_threshold,
        'certificate_enabled': course.certificate_enabled,
        'meet_link': course.meet_link,
        'zoom_link': course.zoom_link,
        'youtube_broadcast_link': getattr(course, 'youtube_broadcast_link', None),
        'start_date': course.start_date.isoformat() if course.start_date and include_dates else None,
        'end_date': course.end_date.isoformat() if course.end_date and include_dates else None
    }


def serialize_class_stats(course_id):
    """
    Get class statistics - counts for weeks, surveys, exams, students
    Used by all roles for overview
    """
    from app.models import CourseWeek, Survey, Exam, Enrollment
    
    weeks_count = CourseWeek.query.filter_by(course_id=course_id).count()
    surveys_count = Survey.query.filter_by(course_id=course_id, is_published=True).count()
    exams_count = Exam.query.filter_by(course_id=course_id, is_published=True).count()
    
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    active_students = len([e for e in enrollments if e.status in ['approved', 'active']])
    pending_students = len([e for e in enrollments if e.status == 'pending'])
    total_students = len(enrollments)
    
    return {
        'weeks_count': weeks_count,
        'surveys_count': surveys_count,
        'exams_count': exams_count,
        'students': {
            'active': active_students,
            'pending': pending_students,
            'total': total_students
        }
    }


def serialize_instructors(course_id):
    """Get instructors for a class - used by admins and teachers"""
    from app.models import CourseInstructor, User
    
    instructors = []
    for ci in CourseInstructor.query.filter_by(course_id=course_id).all():
        instructor = User.query.filter_by(id=ci.user_id).first()
        if instructor:
            instructors.append({
                'id': instructor.id,
                'username': instructor.username,
                'full_name': instructor.full_name,
                'email': instructor.email,
                'role': ci.role
            })
    return instructors


def serialize_student_progress(course_id, user_id):
    """
    Get student's progress in a class - completion status for surveys/exams
    Used by student dashboard
    """
    from app.models import Survey, Exam, SurveyResponse, ExamResult
    
    surveys = Survey.query.filter_by(course_id=course_id, is_published=True).all()
    exams = Exam.query.filter_by(course_id=course_id, is_published=True).all()
    
    completed_surveys = SurveyResponse.query.join(Survey).filter(
        Survey.course_id == course_id,
        SurveyResponse.user_id == user_id
    ).count()
    
    completed_exams = ExamResult.query.join(Exam).filter(
        Exam.course_id == course_id,
        ExamResult.user_id == user_id
    ).count()
    
    return {
        'surveys': {
            'total': len(surveys),
            'completed': completed_surveys
        },
        'exams': {
            'total': len(exams),
            'completed': completed_exams
        }
    }


def serialize_class_for_student(course, enrollment, include_progress=True):
    """
    Complete class serialization for student view
    Includes enrollment info and completion progress
    """
    data = serialize_base_class(course)
    stats = serialize_class_stats(course.id)
    
    data.update({
        'weeks_count': stats['weeks_count'],
        'enrollment': {
            'status': enrollment.status,
            'progress_percent': enrollment.progress_percent or 0,
            'current_week': enrollment.current_week or 1,
            'certificate_status': enrollment.certificate_status or 'not_started',
            'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None
        }
    })
    
    if include_progress:
        progress = serialize_student_progress(course.id, enrollment.user_id)
        data['surveys'] = progress['surveys']
        data['exams'] = progress['exams']
    
    return data


def serialize_class_for_teacher(course, include_stats=True):
    """
    Complete class serialization for teacher view
    Includes student counts and management info
    """
    data = serialize_base_class(course)
    
    if include_stats:
        stats = serialize_class_stats(course.id)
        data.update({
            'weeks_count': stats['weeks_count'],
            'surveys_count': stats['surveys_count'],
            'exams_count': stats['exams_count'],
            'enrolled_count': stats['students']['active'],
            'pending_count': stats['students']['pending'],
            'total_students': stats['students']['total']
        })
    
    return data


def serialize_class_for_admin(course, include_instructors=True, include_stats=True):
    """
    Complete class serialization for admin view (institution admin or super admin)
    Includes instructors, student stats, and management info
    """
    data = serialize_base_class(course)
    
    if include_stats:
        stats = serialize_class_stats(course.id)
        data.update({
            'weeks_count': stats['weeks_count'],
            'surveys_count': stats['surveys_count'],
            'exams_count': stats['exams_count'],
            'students': stats['students']
        })
    
    if include_instructors:
        data['instructors'] = serialize_instructors(course.id)
    
    return data


def serialize_class_list_item(course, user_role, user_id=None, enrollment=None):
    """
    Unified class list item serialization based on user role
    Returns consistent format for class cards/lists
    """
    if user_role == 'student' and enrollment:
        return serialize_class_for_student(course, enrollment)
    elif user_role in ['instructor', 'teacher']:
        return serialize_class_for_teacher(course)
    else:
        return serialize_class_for_admin(course)


def serialize_weeks_with_materials(course_id, user_id=None, include_completion=False, for_teacher=False):
    """
    Serialize course weeks with materials and assignments
    If user_id provided and include_completion=True, includes completion status
    If for_teacher=True, includes all materials/assignments regardless of visibility
    For students: Shows materials that are approved, or scheduled with available_at <= now, or is_published=True (legacy)
    """
    from app.models import CourseWeek, WeekMaterial, Assignment, LearningProgress
    from sqlalchemy import or_, and_
    
    weeks = CourseWeek.query.filter_by(course_id=course_id).order_by(CourseWeek.week_number).all()
    weeks_data = []
    now = datetime.utcnow()
    
    for week in weeks:
        if for_teacher:
            # Teachers see all materials regardless of visibility
            materials = WeekMaterial.query.filter_by(week_id=week.id).order_by(WeekMaterial.order_index).all()
        else:
            # Students see: approved materials, scheduled materials past their available_at, or legacy is_published
            materials = WeekMaterial.query.filter(
                WeekMaterial.week_id == week.id
            ).filter(
                or_(
                    WeekMaterial.visibility_state == 'approved',
                    and_(
                        WeekMaterial.visibility_state == 'scheduled',
                        WeekMaterial.available_at <= now
                    ),
                    WeekMaterial.is_published == True  # Legacy support
                )
            ).order_by(WeekMaterial.order_index).all()
        materials_data = []
        
        for mat in materials:
            mat_data = {
                'id': mat.id,
                'title': mat.title,
                'description': mat.description,
                'material_type': mat.material_type,
                'file_url': mat.file_url,
                'file_name': getattr(mat, 'file_name', None),
                'external_url': mat.external_url,
                'duration_minutes': mat.duration_minutes,
                'difficulty_level': mat.difficulty_level,
                'order_index': mat.order_index,
                'is_published': mat.is_published,
                'visibility_state': getattr(mat, 'visibility_state', 'approved'),
                'available_at': mat.available_at.isoformat() if getattr(mat, 'available_at', None) else None
            }
            
            if include_completion and user_id:
                progress = LearningProgress.query.filter_by(user_id=user_id, material_id=mat.id).first()
                mat_data['is_completed'] = progress and progress.status == 'completed'
                mat_data['progress_percent'] = progress.progress_percent if progress else 0
            
            materials_data.append(mat_data)
        
        if for_teacher:
            # Teachers see all assignments regardless of visibility
            assignments = Assignment.query.filter_by(week_id=week.id).all()
        else:
            # Students see: approved assignments, scheduled assignments past their available_at, or legacy is_published
            assignments = Assignment.query.filter(
                Assignment.week_id == week.id
            ).filter(
                or_(
                    Assignment.visibility_state == 'approved',
                    and_(
                        Assignment.visibility_state == 'scheduled',
                        Assignment.available_at <= now
                    ),
                    Assignment.is_published == True  # Legacy support
                )
            ).all()
        assignments_data = []
        
        for assign in assignments:
            assign_data = {
                'id': assign.id,
                'title': assign.title,
                'description': assign.description,
                'instructions': assign.instructions,
                'assignment_type': assign.assignment_type,
                'max_points': assign.max_points,
                'due_date': assign.due_date.isoformat() if assign.due_date else None,
                'is_published': assign.is_published,
                'visibility_state': getattr(assign, 'visibility_state', 'approved' if assign.is_published else 'draft'),
                'available_at': assign.available_at.isoformat() if getattr(assign, 'available_at', None) else None,
                'allow_late': getattr(assign, 'allow_late', False)
            }
            assignments_data.append(assign_data)
        
        weeks_data.append({
            'id': week.id,
            'week_number': week.week_number,
            'title': week.title,
            'description': week.description,
            'is_published': week.is_published,
            'start_date': week.start_date.isoformat() if week.start_date else None,
            'end_date': week.end_date.isoformat() if week.end_date else None,
            'materials': materials_data,
            'materials_count': len(materials_data),
            'assignments': assignments_data,
            'assignments_count': len(assignments_data)
        })
    
    return weeks_data


def serialize_surveys_for_class(course_id, user_id=None, include_responses=False):
    """
    Serialize surveys for a class
    If user_id provided, includes completion status
    """
    from app.models import Survey, SurveyQuestion, SurveyResponse
    
    surveys = Survey.query.filter_by(course_id=course_id, is_published=True).all()
    surveys_data = []
    
    for survey in surveys:
        questions_count = SurveyQuestion.query.filter_by(survey_id=survey.id).count()
        
        survey_data = {
            'id': survey.id,
            'title': survey.title,
            'description': survey.description,
            'survey_type': survey.survey_type,
            'is_required': survey.is_required,
            'questions_count': questions_count
        }
        
        if user_id:
            response = SurveyResponse.query.filter_by(
                survey_id=survey.id,
                user_id=user_id
            ).first()
            survey_data['is_completed'] = response is not None
            survey_data['completed_at'] = response.submitted_at.isoformat() if response and response.submitted_at else None
        
        surveys_data.append(survey_data)
    
    return surveys_data


def serialize_exams_for_class(course_id, user_id=None, include_results=False, for_teacher=False):
    """
    Serialize exams for a class
    If user_id provided, includes attempt info and results
    If for_teacher=True, shows all exams (including drafts)
    """
    from app.models import Exam, ExamQuestion, ExamResult
    
    if for_teacher:
        exams = Exam.query.filter_by(course_id=course_id).all()
    else:
        exams = Exam.query.filter_by(course_id=course_id, is_published=True).all()
    exams_data = []
    
    for exam in exams:
        questions_count = ExamQuestion.query.filter_by(exam_id=exam.id).count()
        
        exam_data = {
            'id': exam.id,
            'title': exam.title,
            'title_ar': getattr(exam, 'title_ar', None),
            'description': exam.description,
            'description_ar': getattr(exam, 'description_ar', None),
            'exam_type': exam.exam_type,
            'passing_threshold': exam.passing_threshold,
            'time_limit_minutes': exam.time_limit_minutes,
            'max_attempts': exam.max_attempts,
            'shuffle_questions': exam.shuffle_questions,
            'show_results': exam.show_results,
            'is_published': exam.is_published,
            'questions_count': questions_count,
            'open_date': exam.open_date.isoformat() if exam.open_date else None,
            'close_date': exam.close_date.isoformat() if exam.close_date else None
        }
        
        if user_id:
            results = ExamResult.query.filter_by(
                exam_id=exam.id,
                user_id=user_id
            ).order_by(ExamResult.attempt_number.desc()).all()
            
            exam_data['attempts_used'] = len(results)
            exam_data['can_take'] = len(results) < (exam.max_attempts or 999)
            
            if results:
                best_result = max(results, key=lambda r: r.score or 0)
                exam_data['best_result'] = {
                    'score': best_result.score,
                    'percentage': best_result.percentage,
                    'passed': best_result.passed,
                    'submitted_at': best_result.submitted_at.isoformat() if best_result.submitted_at else None
                }
            else:
                exam_data['best_result'] = None
        
        exams_data.append(exam_data)
    
    return exams_data


def serialize_exam_statistics(course_id):
    """
    Get exam statistics for a class - used by teachers and admins
    Returns pass/fail counts and averages in format expected by frontend
    """
    from app.models import Exam, ExamResult
    
    exams = Exam.query.filter_by(course_id=course_id).all()
    stats = []
    
    for exam in exams:
        results = ExamResult.query.filter_by(exam_id=exam.id).all()
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        avg_score = sum(r.score or 0 for r in results) / len(results) if results else 0
        pass_rate = round((passed / len(results) * 100), 1) if results else 0
        
        stats.append({
            'id': exam.id,
            'title': exam.title,
            'exam_type': exam.exam_type,
            'passing_threshold': exam.passing_threshold,
            'max_attempts': exam.max_attempts or 3,
            'time_limit_minutes': getattr(exam, 'time_limit_minutes', None),
            'is_published': exam.is_published,
            'statistics': {
                'total_submissions': len(results),
                'passed_count': passed,
                'failed_count': failed,
                'pass_rate': pass_rate,
                'avg_score': round(avg_score, 1)
            }
        })
    
    return stats


def serialize_certificate_status(course, enrollment, user_id=None):
    """
    Get certificate status for a student in a class
    """
    from app.models import ExamResult, Exam
    
    if not enrollment:
        return {
            'status': 'not_enrolled',
            'is_eligible': False,
            'approved_at': None,
            'certificate_url': None
        }
    
    exams = Exam.query.filter_by(course_id=course.id, is_published=True).all()
    all_passed = True
    
    for exam in exams:
        result = ExamResult.query.filter_by(
            exam_id=exam.id,
            user_id=enrollment.user_id
        ).filter(ExamResult.passed == True).first()
        if not result:
            all_passed = False
            break
    
    return {
        'status': enrollment.certificate_status or 'not_started',
        'is_eligible': all_passed,
        'is_issued': getattr(enrollment, 'certificate_issued', False) or False,
        'approved_at': enrollment.certificate_approved_at.isoformat() if getattr(enrollment, 'certificate_approved_at', None) else None,
        'certificate_url': getattr(enrollment, 'certificate_url', None),
        'progress_percent': enrollment.progress_percent or 0
    }


def serialize_student_in_class(student, enrollment, course_id):
    """
    Serialize a student's data within a class context
    Used by teachers and admins viewing student lists
    """
    from app.models import Exam, ExamResult, Survey, SurveyResponse
    
    exams = Exam.query.filter_by(course_id=course_id).all()
    exam_ids = [e.id for e in exams]
    
    exam_results = ExamResult.query.filter(
        ExamResult.user_id == student.id,
        ExamResult.exam_id.in_(exam_ids)
    ).all() if exam_ids else []
    
    surveys = Survey.query.filter_by(course_id=course_id).all()
    survey_ids = [s.id for s in surveys]
    
    survey_responses = SurveyResponse.query.filter(
        SurveyResponse.user_id == student.id,
        SurveyResponse.survey_id.in_(survey_ids)
    ).all() if survey_ids else []
    
    passed_exams = sum(1 for r in exam_results if r.passed)
    avg_score = sum(r.score or 0 for r in exam_results) / len(exam_results) if exam_results else 0
    
    return {
        'id': student.id,
        'username': student.username,
        'full_name': student.full_name,
        'email': student.email,
        'phone': student.phone,
        'enrollment': {
            'id': enrollment.id,
            'status': enrollment.status,
            'payment_status': enrollment.payment_status,
            'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
            'progress_percent': enrollment.progress_percent or 0,
            'current_week': enrollment.current_week or 1,
            'final_grade': enrollment.final_grade,
            'certificate_status': enrollment.certificate_status
        },
        'progress': {
            'exams': {
                'total': len(exams),
                'completed': len(exam_results),
                'passed': passed_exams,
                'average_score': round(avg_score, 2)
            },
            'surveys': {
                'total': len(surveys),
                'completed': len(survey_responses)
            }
        }
    }
