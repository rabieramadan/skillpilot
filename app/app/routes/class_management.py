"""
Class Management Routes - Class-centric management for exams, surveys, certificates
Accessible by both teachers (their own classes) and institution admins (all classes)
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime

class_mgmt_bp = Blueprint('class_management', __name__)

def get_db():
    """Get database session"""
    try:
        from app.models import db
        return db
    except:
        return None


def class_access_required(f):
    """Decorator to verify user has access to the class (teacher or admin)"""
    @wraps(f)
    def decorated_function(course_id, *args, **kwargs):
        user_id = session.get('user_id')
        user_role = (session.get('role') or '').lower()

        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        from app.models import Course, CourseInstructor

        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Class not found'}), 404

        # Super admin can access any class
        if user_role in ['super_admin', 'superadmin', 'admin']:
            return f(course_id, *args, **kwargs)

        # Institution admin can access any class
        if user_role == 'institution_admin':
            return f(course_id, *args, **kwargs)

        # Teacher can only access classes they teach
        if user_role in ['instructor', 'teacher']:
            instructor = CourseInstructor.query.filter_by(
                course_id=course_id,
                user_id=user_id
            ).first()
            if instructor:
                return f(course_id, *args, **kwargs)
            return jsonify({'error': 'Access denied - you are not assigned to this class'}), 403

        return jsonify({'error': 'Access denied'}), 403

    return decorated_function


# ============================================
# CLASS DETAIL - GET ALL DATA FOR A CLASS
# ============================================

@class_mgmt_bp.route('/classes/<course_id>', methods=['GET'])
@class_access_required
def get_class_detail(course_id):
    """Get comprehensive class details including students, exams, surveys, certificates"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course
        from app.utils.class_serializers import serialize_class_for_admin
        
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Class not found'}), 404
        
        class_data = serialize_class_for_admin(course, include_instructors=True, include_stats=True)
        
        return jsonify({
            'success': True,
            'class': class_data
        })
    except Exception as e:
        print(f"Error getting class detail: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# STUDENTS MANAGEMENT
# ============================================

@class_mgmt_bp.route('/classes/<course_id>/students', methods=['GET'])
@class_access_required
def get_class_students(course_id):
    """Get all students enrolled in this class with their progress and exam results"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import User, Enrollment
        from app.utils.class_serializers import serialize_student_in_class
        
        enrollments = Enrollment.query.filter_by(course_id=course_id).all()
        
        students = []
        for enrollment in enrollments:
            student = User.query.filter_by(id=enrollment.user_id).first()
            if not student:
                continue
            
            student_data = serialize_student_in_class(student, enrollment, course_id)
            students.append(student_data)
        
        return jsonify({
            'success': True,
            'students': students
        })
    except Exception as e:
        print(f"Error getting class students: {e}")
        return jsonify({'error': str(e)}), 500


@class_mgmt_bp.route('/classes/<course_id>/students/<student_id>', methods=['PATCH'])
@class_access_required
def update_class_student(course_id, student_id):
    """Update student information within a class"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import User, Enrollment
        
        data = request.get_json() or {}
        
        # Verify student is enrolled in this class
        enrollment = Enrollment.query.filter_by(course_id=course_id, user_id=student_id).first()
        if not enrollment:
            return jsonify({'error': 'Student not enrolled in this class'}), 404
        
        student = User.query.filter_by(id=student_id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Update allowed student fields
        if 'full_name' in data:
            student.full_name = data['full_name']
        if 'email' in data:
            student.email = data['email']
        if 'phone' in data:
            student.phone = data['phone']
        
        # Update enrollment fields
        if 'enrollment_status' in data:
            enrollment.status = data['enrollment_status']
        if 'payment_status' in data:
            enrollment.payment_status = data['payment_status']
        if 'progress_percent' in data:
            enrollment.progress_percent = data['progress_percent']
        if 'final_grade' in data:
            enrollment.final_grade = data['final_grade']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Student updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating student: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# EXAM STATISTICS
# ============================================

@class_mgmt_bp.route('/classes/<course_id>/exams', methods=['GET'])
@class_access_required
def get_class_exams(course_id):
    """Get all exams for this class with statistics"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.utils.class_serializers import serialize_exam_statistics
        
        exams_data = serialize_exam_statistics(course_id)
        
        return jsonify({
            'success': True,
            'exams': exams_data
        })
    except Exception as e:
        print(f"Error getting class exams: {e}")
        return jsonify({'error': str(e)}), 500


@class_mgmt_bp.route('/classes/<course_id>/exams/<exam_id>/results', methods=['GET'])
@class_access_required
def get_exam_student_results(course_id, exam_id):
    """Get per-student results for a specific exam"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, ExamResult, User
        
        exam = Exam.query.filter_by(id=exam_id, course_id=course_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        results = ExamResult.query.filter_by(exam_id=exam_id).all()
        
        student_results = []
        for r in results:
            student = User.query.filter_by(id=r.user_id).first()
            student_results.append({
                'id': r.id,
                'student_id': r.user_id,
                'student_name': student.full_name if student else 'Unknown',
                'student_username': student.username if student else '',
                'attempt_number': r.attempt_number,
                'score': r.score,
                'percentage': r.percentage,
                'passed': r.passed,
                'started_at': r.started_at.isoformat() if r.started_at else None,
                'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None,
                'time_spent_seconds': r.time_spent_seconds,
                'certificate_status': getattr(r, 'certificate_status', 'pending'),
                'repeat_allowed': getattr(r, 'repeat_allowed', False)
            })
        
        return jsonify({
            'success': True,
            'exam': {
                'id': exam.id,
                'title': exam.title,
                'passing_threshold': exam.passing_threshold
            },
            'results': student_results
        })
    except Exception as e:
        print(f"Error getting exam results: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# SURVEY STATISTICS
# ============================================

@class_mgmt_bp.route('/classes/<course_id>/surveys', methods=['GET'])
@class_access_required
def get_class_surveys(course_id):
    """Get all surveys for this class with response statistics"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyResponse, Enrollment
        
        surveys = Survey.query.filter_by(course_id=course_id).all()
        
        # Get total enrolled students
        total_students = Enrollment.query.filter_by(
            course_id=course_id,
            status='approved'
        ).count()
        
        result = []
        for survey in surveys:
            responses = SurveyResponse.query.filter_by(survey_id=survey.id).all()
            # Count unique responders (unique user_ids)
            unique_responders = len(set(r.user_id for r in responses))
            total_responses = len(responses)
            
            # Calculate response rate based on unique responders, capped at 100%
            response_rate = min(round((unique_responders / total_students * 100), 1), 100.0) if total_students > 0 else 0
            
            result.append({
                'id': survey.id,
                'title': survey.title,
                'description': survey.description,
                'survey_type': survey.survey_type,
                'is_required': survey.is_required,
                'is_published': survey.is_published,
                'statistics': {
                    'total_students': total_students,
                    'response_count': total_responses,
                    'unique_responders': unique_responders,
                    'response_rate': response_rate
                }
            })
        
        return jsonify({
            'success': True,
            'surveys': result
        })
    except Exception as e:
        print(f"Error getting class surveys: {e}")
        return jsonify({'error': str(e)}), 500


@class_mgmt_bp.route('/classes/<course_id>/surveys/<survey_id>/responses', methods=['GET'])
@class_access_required
def get_survey_responses(course_id, survey_id):
    """Get per-student responses for a specific survey"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyResponse, User
        
        survey = Survey.query.filter_by(id=survey_id, course_id=course_id).first()
        if not survey:
            return jsonify({'error': 'Survey not found'}), 404
        
        responses = SurveyResponse.query.filter_by(survey_id=survey_id).all()
        
        response_list = []
        for r in responses:
            student = User.query.filter_by(id=r.user_id).first()
            response_list.append({
                'id': r.id,
                'student_id': r.user_id,
                'student_name': student.full_name if student else 'Unknown',
                'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None,
                'answers': r.answers
            })
        
        return jsonify({
            'success': True,
            'survey': {
                'id': survey.id,
                'title': survey.title
            },
            'responses': response_list
        })
    except Exception as e:
        print(f"Error getting survey responses: {e}")
        return jsonify({'error': str(e)}), 500


@class_mgmt_bp.route('/classes/<course_id>/surveys/<survey_id>/details', methods=['GET'])
@class_access_required
def get_survey_details(course_id, survey_id):
    """Get detailed survey with questions and aggregated statistics"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyQuestion, SurveyResponse, Enrollment, User
        from collections import Counter
        
        survey = Survey.query.filter_by(id=survey_id, course_id=course_id).first()
        if not survey:
            return jsonify({'error': 'Survey not found'}), 404
        
        # Get questions
        questions = SurveyQuestion.query.filter_by(survey_id=survey_id).order_by(SurveyQuestion.order_index).all()
        
        # Get all responses
        responses = SurveyResponse.query.filter_by(survey_id=survey_id).all()
        
        # Get total enrolled students
        total_students = Enrollment.query.filter(
            Enrollment.course_id == course_id,
            Enrollment.status.in_(['approved', 'active'])
        ).count()
        
        unique_responders = len(set(r.user_id for r in responses))
        response_rate = min(round((unique_responders / total_students * 100), 1), 100.0) if total_students > 0 else 0
        
        # Build question-level statistics
        questions_data = []
        for q in questions:
            q_stats = {
                'id': q.id,
                'question_text': q.question_text,
                'question_text_ar': q.question_text_ar,
                'question_type': q.question_type,
                'options': q.options or [],
                'options_ar': q.options_ar or [],
                'is_required': q.is_required,
                'response_summary': {}
            }
            
            # Aggregate responses for this question
            if q.question_type in ['multiple_choice', 'single_choice', 'rating', 'likert']:
                answer_counts = Counter()
                for r in responses:
                    if r.answers and str(q.id) in r.answers:
                        answer = r.answers[str(q.id)]
                        if isinstance(answer, list):
                            for a in answer:
                                answer_counts[str(a)] += 1
                        else:
                            answer_counts[str(answer)] += 1
                q_stats['response_summary'] = dict(answer_counts)
            elif q.question_type in ['text', 'long_text']:
                # Collect text responses
                text_responses = []
                for r in responses:
                    if r.answers and str(q.id) in r.answers:
                        answer = r.answers[str(q.id)]
                        if answer and str(answer).strip():
                            student = User.query.filter_by(id=r.user_id).first()
                            text_responses.append({
                                'student_name': student.full_name if student else 'Anonymous',
                                'response': str(answer),
                                'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None
                            })
                q_stats['text_responses'] = text_responses
            
            questions_data.append(q_stats)
        
        # Get individual student responses
        student_responses = []
        for r in responses:
            student = User.query.filter_by(id=r.user_id).first()
            student_responses.append({
                'id': r.id,
                'student_id': r.user_id,
                'student_name': student.full_name if student else 'Unknown',
                'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None,
                'answers': r.answers
            })
        
        return jsonify({
            'success': True,
            'survey': {
                'id': survey.id,
                'title': survey.title,
                'title_ar': getattr(survey, 'title_ar', None),
                'description': survey.description,
                'survey_type': survey.survey_type,
                'is_published': survey.is_published
            },
            'statistics': {
                'total_students': total_students,
                'unique_responders': unique_responders,
                'response_rate': response_rate
            },
            'questions': questions_data,
            'responses': student_responses
        })
    except Exception as e:
        print(f"Error getting survey details: {e}")
        return jsonify({'error': str(e)}), 500


@class_mgmt_bp.route('/classes/<course_id>/exams/<exam_id>/details', methods=['GET'])
@class_access_required
def get_exam_details(course_id, exam_id):
    """Get detailed exam with questions and per-question statistics"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, ExamQuestion, ExamResult, User
        from collections import Counter
        
        exam = Exam.query.filter_by(id=exam_id, course_id=course_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        # Get questions
        questions = ExamQuestion.query.filter_by(exam_id=exam_id).order_by(ExamQuestion.order_index).all()
        
        # Get all results
        results = ExamResult.query.filter_by(exam_id=exam_id).all()
        
        # Calculate overall statistics
        total_submissions = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = total_submissions - passed_count
        avg_score = round(sum(r.percentage or 0 for r in results) / total_submissions, 1) if total_submissions > 0 else 0
        pass_rate = round((passed_count / total_submissions * 100), 1) if total_submissions > 0 else 0
        
        # Build question data
        questions_data = []
        for q in questions:
            q_data = {
                'id': q.id,
                'question_text': q.question_text,
                'question_text_ar': q.question_text_ar,
                'question_type': q.question_type,
                'options': q.options or [],
                'options_ar': q.options_ar or [],
                'correct_answer': q.correct_answer,
                'points': q.points or 1
            }
            questions_data.append(q_data)
        
        # Get per-student results
        student_results = []
        for r in results:
            student = User.query.filter_by(id=r.user_id).first()
            student_results.append({
                'id': r.id,
                'student_id': r.user_id,
                'student_name': student.full_name if student else 'Unknown',
                'student_username': student.username if student else '',
                'attempt_number': r.attempt_number,
                'score': r.score,
                'percentage': r.percentage,
                'passed': r.passed,
                'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None,
                'answers': getattr(r, 'answers', None)
            })
        
        return jsonify({
            'success': True,
            'exam': {
                'id': exam.id,
                'title': exam.title,
                'title_ar': getattr(exam, 'title_ar', None),
                'description': exam.description,
                'exam_type': exam.exam_type,
                'passing_threshold': exam.passing_threshold,
                'max_attempts': exam.max_attempts,
                'time_limit_minutes': exam.time_limit_minutes,
                'is_published': exam.is_published
            },
            'statistics': {
                'total_submissions': total_submissions,
                'passed_count': passed_count,
                'failed_count': failed_count,
                'avg_score': avg_score,
                'pass_rate': pass_rate
            },
            'questions': questions_data,
            'results': student_results
        })
    except Exception as e:
        print(f"Error getting exam details: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# CERTIFICATES MANAGEMENT
# ============================================

@class_mgmt_bp.route('/classes/<course_id>/certificates', methods=['GET'])
@class_access_required
def get_class_certificates(course_id):
    """Get certificate status for all students in this class"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import User, Enrollment, Exam, ExamResult
        
        enrollments = Enrollment.query.filter_by(course_id=course_id).all()
        exams = Exam.query.filter_by(course_id=course_id).all()
        exam_ids = [e.id for e in exams]
        
        certificates = []
        for enrollment in enrollments:
            student = User.query.filter_by(id=enrollment.user_id).first()
            if not student:
                continue
            
            # Get BEST exam result per exam for this student (highest percentage)
            best_results = []
            for exam in exams:
                best_result = ExamResult.query.filter(
                    ExamResult.user_id == student.id,
                    ExamResult.exam_id == exam.id
                ).order_by(ExamResult.percentage.desc()).first()
                if best_result:
                    best_results.append(best_result)
            
            exam_results = best_results
            
            # Calculate overall pass status based on best scores
            all_passed = all(r.passed for r in exam_results) if exam_results else False
            any_failed = any(not r.passed for r in exam_results) if exam_results else False
            
            # Determine certificate eligibility
            cert_status = getattr(enrollment, 'certificate_status', 'not_eligible')
            if all_passed and exam_results and cert_status == 'not_eligible':
                cert_status = 'pending'
            
            certificates.append({
                'enrollment_id': enrollment.id,
                'student_id': student.id,
                'student_name': student.full_name,
                'student_username': student.username,
                'student_email': student.email,
                'enrollment_status': enrollment.status,
                'progress_percent': enrollment.progress_percent or 0,
                'final_grade': enrollment.final_grade,
                'exams_passed': sum(1 for r in exam_results if r.passed),
                'total_exams': len(exam_ids),
                'all_exams_passed': all_passed,
                'any_failed': any_failed,
                'certificate_status': cert_status,
                'certificate_issued': enrollment.certificate_issued,
                'certificate_issued_at': enrollment.certificate_issued_at.isoformat() if enrollment.certificate_issued_at else None,
                'exam_results': [{
                    'exam_id': r.exam_id,
                    'exam_title': next((e.title for e in exams if e.id == r.exam_id), 'Unknown'),
                    'score': r.score,
                    'total_points': r.total_points,
                    'percentage': r.percentage,
                    'passed': r.passed,
                    'certificate_status': getattr(r, 'certificate_status', 'pending'),
                    'repeat_allowed': getattr(r, 'repeat_allowed', False),
                    'is_best_score': True  # This is already the best score per exam
                } for r in exam_results]
            })
        
        return jsonify({
            'success': True,
            'certificates': certificates
        })
    except Exception as e:
        print(f"Error getting class certificates: {e}")
        return jsonify({'error': str(e)}), 500


@class_mgmt_bp.route('/classes/<course_id>/certificates/<enrollment_id>/approve', methods=['POST'])
@class_access_required
def approve_certificate(course_id, enrollment_id):
    """Approve a certificate for a student"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Enrollment
        
        enrollment = Enrollment.query.filter_by(id=enrollment_id, course_id=course_id).first()
        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404
        
        user_id = session.get('user_id')
        
        enrollment.certificate_status = 'approved'
        enrollment.certificate_issued = True
        enrollment.certificate_issued_at = datetime.utcnow()
        enrollment.certificate_approved_by = user_id
        enrollment.certificate_approved_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Certificate approved and issued'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error approving certificate: {e}")
        return jsonify({'error': str(e)}), 500


@class_mgmt_bp.route('/classes/<course_id>/certificates/<enrollment_id>/force-issue', methods=['POST'])
@class_access_required
def force_issue_certificate(course_id, enrollment_id):
    """Force issue a certificate even if student failed exams"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Enrollment
        
        enrollment = Enrollment.query.filter_by(id=enrollment_id, course_id=course_id).first()
        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404
        
        user_id = session.get('user_id')
        
        enrollment.certificate_status = 'force_issued'
        enrollment.certificate_issued = True
        enrollment.certificate_issued_at = datetime.utcnow()
        enrollment.certificate_approved_by = user_id
        enrollment.certificate_approved_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Certificate force issued'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error force issuing certificate: {e}")
        return jsonify({'error': str(e)}), 500


@class_mgmt_bp.route('/classes/<course_id>/exams/<exam_id>/results/<result_id>/allow-repeat', methods=['POST'])
@class_access_required
def allow_exam_repeat(course_id, exam_id, result_id):
    """Allow a student to repeat an exam"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, ExamResult
        
        # Verify exam belongs to this course
        exam = Exam.query.filter_by(id=exam_id, course_id=course_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found in this class'}), 404
        
        result = ExamResult.query.filter_by(id=result_id, exam_id=exam_id).first()
        if not result:
            return jsonify({'error': 'Exam result not found'}), 404
        
        user_id = session.get('user_id')
        data = request.get_json() or {}
        
        result.repeat_allowed = True
        result.repeat_allowed_by = user_id
        result.repeat_allowed_at = datetime.utcnow()
        if 'max_attempts' in data:
            result.max_repeat_attempts = data['max_attempts']
        else:
            result.max_repeat_attempts = (result.max_repeat_attempts or 1) + 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Repeat exam allowed',
            'max_attempts': result.max_repeat_attempts
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error allowing exam repeat: {e}")
        return jsonify({'error': str(e)}), 500


@class_mgmt_bp.route('/classes/<course_id>/exams/<exam_id>/results/<result_id>/approve-certificate', methods=['POST'])
@class_access_required
def approve_exam_certificate(course_id, exam_id, result_id):
    """Approve certificate for a specific exam result"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, ExamResult
        
        exam = Exam.query.filter_by(id=exam_id, course_id=course_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found in this class'}), 404
        
        result = ExamResult.query.filter_by(id=result_id, exam_id=exam_id).first()
        if not result:
            return jsonify({'error': 'Exam result not found'}), 404
        
        user_id = session.get('user_id')
        
        result.certificate_status = 'approved'
        result.certificate_approved_by = user_id
        result.certificate_approved_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Exam certificate approved'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error approving exam certificate: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# EXAM EDITING
# ============================================

@class_mgmt_bp.route('/classes/<course_id>/exams/<exam_id>', methods=['GET'])
@class_access_required
def get_exam_detail(course_id, exam_id):
    """Get exam details for editing"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam
        
        exam = Exam.query.filter_by(id=exam_id, course_id=course_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        return jsonify({
            'success': True,
            'exam': {
                'id': exam.id,
                'title': exam.title,
                'description': exam.description,
                'exam_type': exam.exam_type,
                'passing_threshold': exam.passing_threshold,
                'max_attempts': exam.max_attempts,
                'time_limit_minutes': exam.time_limit_minutes,
                'is_published': exam.is_published,
                'open_date': exam.open_date.isoformat() if exam.open_date else None,
                'close_date': exam.close_date.isoformat() if exam.close_date else None,
                'shuffle_questions': getattr(exam, 'shuffle_questions', False),
                'shuffle_answers': getattr(exam, 'shuffle_answers', False),
                'show_results': getattr(exam, 'show_results', True)
            }
        })
    except Exception as e:
        print(f"Error getting exam detail: {e}")
        return jsonify({'error': str(e)}), 500


@class_mgmt_bp.route('/classes/<course_id>/exams/<exam_id>', methods=['PATCH'])
@class_access_required
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
            exam.time_limit_minutes = int(data['time_limit_minutes']) if data['time_limit_minutes'] else None
        if 'is_published' in data:
            # Handle boolean correctly - check for actual boolean or string 'true'/'false'
            is_pub = data['is_published']
            if isinstance(is_pub, bool):
                exam.is_published = is_pub
            else:
                exam.is_published = str(is_pub).lower() in ('true', '1', 'yes')
        if 'open_date' in data:
            exam.open_date = datetime.fromisoformat(data['open_date']) if data['open_date'] else None
        if 'close_date' in data:
            exam.close_date = datetime.fromisoformat(data['close_date']) if data['close_date'] else None
        if 'shuffle_questions' in data:
            if hasattr(exam, 'shuffle_questions'):
                shuffle_q = data['shuffle_questions']
                if isinstance(shuffle_q, bool):
                    exam.shuffle_questions = shuffle_q
                else:
                    exam.shuffle_questions = str(shuffle_q).lower() in ('true', '1', 'yes')
        if 'shuffle_answers' in data:
            if hasattr(exam, 'shuffle_answers'):
                shuffle_a = data['shuffle_answers']
                if isinstance(shuffle_a, bool):
                    exam.shuffle_answers = shuffle_a
                else:
                    exam.shuffle_answers = str(shuffle_a).lower() in ('true', '1', 'yes')
        if 'show_results' in data:
            if hasattr(exam, 'show_results'):
                show_r = data['show_results']
                if isinstance(show_r, bool):
                    exam.show_results = show_r
                else:
                    exam.show_results = str(show_r).lower() in ('true', '1', 'yes')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Exam updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating exam: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# STUDENT EXAM RESULTS
# ============================================

@class_mgmt_bp.route('/classes/<course_id>/students/<student_id>/exams', methods=['GET'])
@class_access_required
def get_student_exams(course_id, student_id):
    """Get all exam results for a specific student in this class"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import User, Exam, ExamResult, Enrollment
        
        # Verify student is enrolled
        enrollment = Enrollment.query.filter_by(course_id=course_id, user_id=student_id).first()
        if not enrollment:
            return jsonify({'error': 'Student not enrolled in this class'}), 404
        
        student = User.query.filter_by(id=student_id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Get all exams for this course
        exams = Exam.query.filter_by(course_id=course_id).all()
        
        exam_data = []
        for exam in exams:
            # Get all results for this student on this exam
            results = ExamResult.query.filter_by(
                exam_id=exam.id,
                user_id=student_id
            ).order_by(ExamResult.attempt_number).all()
            
            exam_data.append({
                'exam_id': exam.id,
                'exam_title': exam.title,
                'exam_type': exam.exam_type,
                'passing_threshold': exam.passing_threshold,
                'max_attempts': exam.max_attempts,
                'attempts': [{
                    'id': r.id,
                    'attempt_number': r.attempt_number,
                    'score': r.score,
                    'percentage': r.percentage,
                    'passed': r.passed,
                    'started_at': r.started_at.isoformat() if r.started_at else None,
                    'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None,
                    'time_spent_seconds': r.time_spent_seconds,
                    'answers': r.answers,
                    'certificate_status': getattr(r, 'certificate_status', 'pending'),
                    'repeat_allowed': getattr(r, 'repeat_allowed', False)
                } for r in results],
                'best_score': max([r.score or 0 for r in results]) if results else 0,
                'latest_passed': results[-1].passed if results else False,
                'attempts_count': len(results)
            })
        
        return jsonify({
            'success': True,
            'student': {
                'id': student.id,
                'full_name': student.full_name,
                'username': student.username,
                'email': student.email
            },
            'exams': exam_data
        })
    except Exception as e:
        print(f"Error getting student exams: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# CERTIFICATE VIEWING/GENERATION
# ============================================

@class_mgmt_bp.route('/classes/<course_id>/certificates/<enrollment_id>/view', methods=['GET'])
@class_access_required
def view_certificate(course_id, enrollment_id):
    """Get certificate data for viewing/download"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import User, Course, Enrollment, Exam, ExamResult

        enrollment = Enrollment.query.filter_by(id=enrollment_id, course_id=course_id).first()
        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404

        # Check if certificate is issued
        if not enrollment.certificate_issued:
            return jsonify({'error': 'Certificate not yet issued'}), 400

        student = User.query.filter_by(id=enrollment.user_id).first()
        course = Course.query.filter_by(id=course_id).first()

        # Get exam results
        exams = Exam.query.filter_by(course_id=course_id).all()
        exam_ids = [e.id for e in exams]
        exam_results = ExamResult.query.filter(
            ExamResult.user_id == enrollment.user_id,
            ExamResult.exam_id.in_(exam_ids)
        ).all() if exam_ids else []

        avg_score = sum(r.score or 0 for r in exam_results) / len(exam_results) if exam_results else 0

        return jsonify({
            'success': True,
            'certificate': {
                'enrollment_id': enrollment.id,
                'certificate_number': f"CERT-{enrollment.id[:8].upper()}",
                'student_name': student.full_name if student else 'Unknown',
                'student_email': student.email if student else '',
                'course_title': course.title if course else 'Unknown Course',
                'course_code': course.code if course else '',
                'institution_name': 'SkillPilot Academy',
                'institution_logo': None,
                'issue_date': enrollment.certificate_issued_at.isoformat() if enrollment.certificate_issued_at else None,
                'completion_date': enrollment.completed_at.isoformat() if hasattr(enrollment, 'completed_at') and enrollment.completed_at else None,
                'final_grade': enrollment.final_grade or round(avg_score, 1),
                'status': enrollment.certificate_status or 'issued',
                'exams_completed': len(exam_results),
                'total_exams': len(exam_ids),
                'avg_score': round(avg_score, 1)
            }
        })
    except Exception as e:
        print(f"Error viewing certificate: {e}")
        return jsonify({'error': str(e)}), 500


@class_mgmt_bp.route('/classes/<course_id>/certificates/<enrollment_id>/download', methods=['GET'])
@class_access_required
def download_certificate(course_id, enrollment_id):
    """Generate and download professional PDF certificate with security features"""
    from flask import send_file
    import io
    import os
    
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import User, Course, Enrollment, Exam, ExamResult
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import inch, mm
        from reportlab.lib.colors import HexColor, black, white
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import qrcode
        from PIL import Image

        enrollment = Enrollment.query.filter_by(id=enrollment_id, course_id=course_id).first()
        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404

        # Check if certificate is issued
        if not enrollment.certificate_issued:
            return jsonify({'error': 'Certificate not yet issued'}), 400

        student = User.query.filter_by(id=enrollment.user_id).first()
        course = Course.query.filter_by(id=course_id).first()
        
        # Get exam results for grade calculation
        exams = Exam.query.filter_by(course_id=course_id).all()
        exam_ids = [e.id for e in exams]
        exam_results = ExamResult.query.filter(
            ExamResult.user_id == enrollment.user_id,
            ExamResult.exam_id.in_(exam_ids)
        ).all() if exam_ids else []
        
        avg_score = sum(r.score or 0 for r in exam_results) / len(exam_results) if exam_results else 0
        final_grade = enrollment.final_grade or round(avg_score, 1)
        
        # Generate certificate number
        cert_number = f"CERT-{enrollment.id[:8].upper()}" if isinstance(enrollment.id, str) else f"CERT-{enrollment.id:08d}"
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Use landscape A4
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(buffer, pagesize=landscape(A4))
        
        # Define colors - Professional teal/blue theme matching NATD branding
        primary_color = HexColor('#1a5c5e')  # Teal from NATD logo
        secondary_color = HexColor('#2d7d80')
        gold_color = HexColor('#c4a35a')  # Gold accent
        dark_blue = HexColor('#1a3a5c')
        
        # ========================================
        # CERTIFICATE BORDER - Security Pattern
        # ========================================
        
        # Outer decorative border
        c.setStrokeColor(primary_color)
        c.setLineWidth(3)
        c.rect(20, 20, page_width - 40, page_height - 40)
        
        # Inner decorative border
        c.setStrokeColor(gold_color)
        c.setLineWidth(1.5)
        c.rect(35, 35, page_width - 70, page_height - 70)
        
        # Corner ornaments
        corner_size = 25
        for x, y in [(40, 40), (page_width - 65, 40), (40, page_height - 65), (page_width - 65, page_height - 65)]:
            c.setFillColor(gold_color)
            c.circle(x + corner_size/2, y + corner_size/2, corner_size/3, fill=1, stroke=0)
        
        # ========================================
        # HEADER - INSTITUTIONAL LOGOS
        # ========================================
        
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        images_path = os.path.join(base_path, 'static', 'images')
        
        # LEFT side - AIAC logo + NATD logo together (equal sizes, below corner dots)
        logo_size = 75  # Equal size for left logos
        logo_y = page_height - 140  # Position below the corner dots
        
        aiac_logo_path = os.path.join(images_path, 'aiac-logo.png')
        if os.path.exists(aiac_logo_path):
            try:
                c.drawImage(aiac_logo_path, 50, logo_y, width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Error loading AIAC logo: {e}")
        
        natd_logo_path = os.path.join(images_path, 'NATD_Logo.png')
        if os.path.exists(natd_logo_path):
            try:
                c.drawImage(natd_logo_path, 130, logo_y, width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Error loading NATD logo: {e}")
        
        # RIGHT side - University logo (ac-logo) - larger to match other logos visually
        ac_logo_path = os.path.join(images_path, 'ac-logo.png')
        if os.path.exists(ac_logo_path):
            try:
                ac_logo_size = 115  # Larger size to visually match other logos
                c.drawImage(ac_logo_path, page_width - 165, logo_y - 20, width=ac_logo_size, height=ac_logo_size, preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Error loading University logo: {e}")
        
        # ========================================
        # CERTIFICATE TITLE
        # ========================================
        
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(page_width / 2, page_height - 90, "CERTIFICATE")
        
        c.setFillColor(gold_color)
        c.setFont("Helvetica", 16)
        c.drawCentredString(page_width / 2, page_height - 115, "OF COMPLETION")
        
        # Decorative line under title
        c.setStrokeColor(gold_color)
        c.setLineWidth(2)
        c.line(page_width/2 - 120, page_height - 125, page_width/2 + 120, page_height - 125)
        
        # ========================================
        # CERTIFICATE BODY
        # ========================================
        
        # "This is to certify that" text
        c.setFillColor(black)
        c.setFont("Helvetica", 14)
        c.drawCentredString(page_width / 2, page_height - 160, "This is to certify that")
        
        # Student Name - Large and prominent, auto-adjust font size to fit
        student_name = student.full_name if student else 'Unknown Student'
        c.setFillColor(primary_color)
        
        # Calculate font size to fit within certificate borders (max width ~600px)
        max_name_width = page_width - 120  # Leave 60px margin on each side
        name_font_size = 28
        c.setFont("Helvetica-Bold", name_font_size)
        name_width = c.stringWidth(student_name, "Helvetica-Bold", name_font_size)
        
        # Reduce font size if name is too long
        while name_width > max_name_width and name_font_size > 16:
            name_font_size -= 2
            c.setFont("Helvetica-Bold", name_font_size)
            name_width = c.stringWidth(student_name, "Helvetica-Bold", name_font_size)
        
        c.drawCentredString(page_width / 2, page_height - 195, student_name)
        
        # Decorative underline for name
        c.setStrokeColor(gold_color)
        c.setLineWidth(1)
        underline_width = min(name_width + 40, max_name_width)
        c.line(page_width/2 - underline_width/2, page_height - 205, page_width/2 + underline_width/2, page_height - 205)
        
        # "has successfully completed" text
        c.setFillColor(black)
        c.setFont("Helvetica", 14)
        c.drawCentredString(page_width / 2, page_height - 235, "has successfully completed the training program")
        
        # Course Title - Prominent display
        course_title = course.title if course else 'Training Program'
        c.setFillColor(dark_blue)
        c.setFont("Helvetica-Bold", 22)
        
        # Handle long course titles
        if len(course_title) > 50:
            # Split into two lines
            words = course_title.split()
            mid = len(words) // 2
            line1 = ' '.join(words[:mid])
            line2 = ' '.join(words[mid:])
            c.drawCentredString(page_width / 2, page_height - 270, line1)
            c.drawCentredString(page_width / 2, page_height - 295, line2)
        else:
            c.drawCentredString(page_width / 2, page_height - 275, course_title)
        
        # ========================================
        # SIGNATURE & STAMP SECTION
        # ========================================
        
        sig_y = 120
        
        # LEFT side - Chair Signature (touching the line below)
        signature_path = os.path.join(images_path, 'signature.png')
        if os.path.exists(signature_path):
            try:
                # Position signature to touch the line below (sig_y is the line position)
                c.drawImage(signature_path, 80, sig_y - 5, width=120, height=50, preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Error loading signature: {e}")
        
        # LEFT side - Chair Stamp (aiac-stamp.png) centered above the signature
        chair_stamp_path = os.path.join(images_path, 'aiac-stamp.png')
        if os.path.exists(chair_stamp_path):
            try:
                chair_stamp_size = 80
                # Center stamp over signature line (line is from x=60 to x=220, center = 140)
                stamp_x = 140 - chair_stamp_size / 2  # Center at x=140
                # Position stamp higher to avoid covering signature (sig_y + 70)
                c.drawImage(chair_stamp_path, stamp_x, sig_y + 70, width=chair_stamp_size, height=chair_stamp_size, preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Error loading Chair stamp: {e}")
        
        # Signature line (left side)
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.line(60, sig_y, 220, sig_y)
        
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(140, sig_y - 15, "Prof. Rabie A. Ramadan")
        c.setFont("Helvetica", 9)
        c.drawCentredString(140, sig_y - 28, "AI Applications Chair")
        c.drawCentredString(140, sig_y - 40, "University of Nizwa")
        
        # CENTER - Date of Issue (moved up to avoid stamp intersection)
        c.setFillColor(black)
        c.setFont("Helvetica", 10)
        issue_date = enrollment.certificate_issued_at.strftime('%B %d, %Y') if enrollment.certificate_issued_at else datetime.utcnow().strftime('%B %d, %Y')
        c.drawCentredString(page_width / 2, sig_y + 100, "Date of Issue")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(page_width / 2, sig_y + 82, issue_date)
        
        # CENTER - QR Code for verification
        qr_size = 90
        
        # Generate QR code
        verification_url = f"https://skillpilot.replit.app/verify/{cert_number}"
        qr = qrcode.QRCode(version=1, box_size=5, border=1)
        qr.add_data(verification_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # Position QR code in center
        center_x = page_width / 2
        c.drawImage(ImageReader(qr_buffer), center_x - qr_size/2, sig_y - 15, width=qr_size, height=qr_size, mask='auto')
        
        c.setFillColor(secondary_color)
        c.setFont("Helvetica", 8)
        c.drawCentredString(center_x, sig_y - 30, "Scan to Verify")
        
        # Certificate number (below QR)
        c.setFont("Helvetica", 9)
        c.setFillColor(secondary_color)
        c.drawCentredString(page_width / 2, sig_y - 45, f"Certificate No: {cert_number}")
        
        # RIGHT side - Academy Director Signature (signature2.png)
        signature2_path = os.path.join(images_path, 'signature2.png')
        if os.path.exists(signature2_path):
            try:
                # Position signature to touch the line below
                c.drawImage(signature2_path, page_width - 200, sig_y - 5, width=120, height=50, preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Error loading academy signature: {e}")
        
        # RIGHT side - NATD Stamp centered above the signature
        natd_stamp_path = os.path.join(images_path, 'NATD_stamp.png')
        if os.path.exists(natd_stamp_path):
            try:
                natd_stamp_size = 80
                # Center stamp over signature line (line center = page_width - 140)
                stamp_x = (page_width - 140) - natd_stamp_size / 2
                # Position stamp higher to avoid covering signature (sig_y + 70)
                c.drawImage(natd_stamp_path, stamp_x, sig_y + 70, width=natd_stamp_size, height=natd_stamp_size, preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Error loading NATD stamp: {e}")
        
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
        
        # ========================================
        # FOOTER - Watermark & Security Text
        # ========================================
        
        c.setFillColor(HexColor('#cccccc'))
        c.setFont("Helvetica", 8)
        c.drawCentredString(page_width / 2, 35, "This certificate is digitally generated and verifiable. Any unauthorized alteration renders this certificate void.")
        
        # Institution names at bottom
        c.setFillColor(secondary_color)
        c.setFont("Helvetica", 8)
        c.drawCentredString(page_width / 2, 22, "University of Nizwa - AI Applications Chair | Nizwa Academy for Training and Development")
        
        # Save PDF
        c.save()
        buffer.seek(0)
        
        # Create filename
        safe_name = ''.join(c for c in student_name if c.isalnum() or c in ' -_').strip()
        filename = f"Certificate_{safe_name}_{cert_number}.pdf"
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error generating certificate PDF: {e}")
        return jsonify({'error': f'Failed to generate certificate: {str(e)}'}), 500
