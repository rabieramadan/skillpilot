"""
SkillPilot - Student Class-Centric Routes
All student interactions scoped by class/course - surveys, exams, materials, certificates
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime

student_class_bp = Blueprint('student_class', __name__, url_prefix='/api/student')


def get_db():
    """Get database session if available"""
    try:
        from app.models import db
        return db
    except:
        return None


def student_required(f):
    """Decorator to require student authentication - student role or super admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401
        role = (session.get('role') or '').lower().replace(' ', '_')
        # Allow student role or super_admin (super admin can access everything)
        allowed_roles = ['student', 'super_admin', 'superadmin']
        if role not in allowed_roles:
            return jsonify({'error': 'Student access only'}), 403
        return f(*args, **kwargs)
    return decorated_function


def verify_enrollment(user_id, course_id):
    """Verify student is enrolled in the course"""
    from app.models import Enrollment

    enrollment = Enrollment.query.filter_by(
        user_id=user_id,
        course_id=course_id
    ).filter(Enrollment.status.in_(['approved', 'active'])).first()
    return enrollment


@student_class_bp.route('/classes', methods=['GET'])
@student_required
def get_enrolled_classes():
    """Get all classes the student is enrolled in with summary info"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course, Enrollment
        from app.utils.class_serializers import serialize_class_for_student

        user_id = session.get('user_id')

        enrollments = Enrollment.query.filter_by(user_id=user_id).filter(
            Enrollment.status.in_(['approved', 'active'])
        ).all()

        classes = []
        for enrollment in enrollments:
            course = Course.query.filter_by(id=enrollment.course_id).first()
            if not course:
                continue

            class_data = serialize_class_for_student(course, enrollment)
            classes.append(class_data)
        
        return jsonify({
            'success': True,
            'classes': classes
        })
    except Exception as e:
        print(f"Error getting enrolled classes: {e}")
        return jsonify({'error': str(e)}), 500


@student_class_bp.route('/class/<course_id>/dashboard', methods=['GET'])
@student_required
def get_class_dashboard(course_id):
    """Get complete class dashboard - overview, materials, surveys, exams, certificate"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course, LearningProgress
        from app.utils.class_serializers import (
            serialize_base_class,
            serialize_weeks_with_materials,
            serialize_surveys_for_class,
            serialize_exams_for_class,
            serialize_certificate_status
        )

        user_id = session.get('user_id')

        enrollment = verify_enrollment(user_id, course_id)
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this class'}), 403
        
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return jsonify({'error': 'Class not found'}), 404
        
        weeks_data = serialize_weeks_with_materials(course_id, user_id, include_completion=True)
        surveys_data = serialize_surveys_for_class(course_id, user_id)
        exams_data = serialize_exams_for_class(course_id, user_id)
        certificate = serialize_certificate_status(course, enrollment)
        
        total_materials = sum(w['materials_count'] for w in weeks_data)
        completed_materials = sum(
            1 for w in weeks_data for m in w['materials'] if m.get('is_completed')
        )
        
        return jsonify({
            'success': True,
            'class': serialize_base_class(course),
            'enrollment': {
                'status': enrollment.status,
                'progress_percent': enrollment.progress_percent or 0,
                'current_week': enrollment.current_week or 1
            },
            'materials': {
                'weeks': weeks_data,
                'total': total_materials,
                'completed': completed_materials
            },
            'surveys': surveys_data,
            'exams': exams_data,
            'certificate': certificate
        })
    except Exception as e:
        print(f"Error getting class dashboard: {e}")
        return jsonify({'error': str(e)}), 500


@student_class_bp.route('/class/<course_id>/surveys', methods=['GET'])
@student_required
def get_class_surveys(course_id):
    """Get all surveys for a class"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyQuestion, SurveyResponse
        from app.utils.class_serializers import serialize_surveys_for_class

        user_id = session.get('user_id')

        enrollment = verify_enrollment(user_id, course_id)
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this class'}), 403
        
        base_surveys = serialize_surveys_for_class(course_id, user_id)
        
        surveys_data = []
        for survey_base in base_surveys:
            survey = Survey.query.filter_by(id=survey_base['id']).first()
            if not survey:
                continue
                
            response = SurveyResponse.query.filter_by(survey_id=survey.id, user_id=user_id).first()
            questions = SurveyQuestion.query.filter_by(survey_id=survey.id).order_by(SurveyQuestion.order_index).all()
            
            survey_data = survey_base.copy()
            survey_data['questions'] = [{
                'id': q.id,
                'question_text': q.question_text,
                'question_text_ar': getattr(q, 'question_text_ar', None),
                'question_type': q.question_type,
                'options': q.options,
                'options_ar': getattr(q, 'options_ar', None),
                'is_required': q.is_required
            } for q in questions] if not response else []
            
            surveys_data.append(survey_data)
        
        return jsonify({
            'success': True,
            'surveys': surveys_data
        })
    except Exception as e:
        print(f"Error getting class surveys: {e}")
        return jsonify({'error': str(e)}), 500


@student_class_bp.route('/class/<course_id>/surveys/<survey_id>/submit', methods=['POST'])
@student_required
def submit_class_survey(course_id, survey_id):
    """Submit a survey response for a class"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Survey, SurveyResponse, SurveyQuestion
        import uuid

        user_id = session.get('user_id')

        enrollment = verify_enrollment(user_id, course_id)
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this class'}), 403
        
        survey = Survey.query.filter_by(id=survey_id, course_id=course_id).first()
        if not survey:
            return jsonify({'error': 'Survey not found'}), 404
        
        existing = SurveyResponse.query.filter_by(survey_id=survey_id, user_id=user_id).first()
        if existing:
            return jsonify({'error': 'You have already completed this survey'}), 400
        
        data = request.get_json()
        answers = data.get('answers', {})
        
        # Calculate score for scored questions (true_false and multiple_choice with correct_answer)
        questions = SurveyQuestion.query.filter_by(survey_id=survey_id).all()
        print(f"[DEBUG] Survey {survey_id}: {len(questions)} total questions")
        for q in questions:
            print(f"[DEBUG] Question {q.id}: type={q.question_type}, correct_answer={q.correct_answer}")
        scored_questions = [q for q in questions if q.correct_answer is not None and q.question_type in ('true_false', 'multiple_choice')]
        print(f"[DEBUG] Scored questions: {len(scored_questions)}")
        
        correct_count = 0
        total_scored = len(scored_questions)
        
        for q in scored_questions:
            student_answer = answers.get(q.id)
            if student_answer is not None:
                # Normalize answer comparison
                if q.question_type == 'true_false':
                    # Map True/False text to index
                    true_vals = ['True', 'true', 'TRUE', 'صحيح', '0']
                    false_vals = ['False', 'false', 'FALSE', 'خطأ', '1']
                    student_idx = 0 if str(student_answer) in true_vals else (1 if str(student_answer) in false_vals else -1)
                    if student_idx == q.correct_answer:
                        correct_count += 1
                else:
                    # Multiple choice - compare by index or value
                    try:
                        student_idx = int(student_answer) if str(student_answer).isdigit() else -1
                        if student_idx == q.correct_answer:
                            correct_count += 1
                        elif q.options and str(student_answer) in q.options:
                            student_idx = q.options.index(str(student_answer))
                            if student_idx == q.correct_answer:
                                correct_count += 1
                    except (ValueError, IndexError):
                        pass
        
        response = SurveyResponse(
            id=str(uuid.uuid4()),
            survey_id=survey_id,
            user_id=user_id,
            answers=answers,
            submitted_at=datetime.utcnow()
        )
        
        db.session.add(response)
        db.session.commit()
        
        # Calculate percentage
        percentage = round((correct_count / total_scored * 100), 1) if total_scored > 0 else None
        
        result = {
            'success': True,
            'message': 'Survey submitted successfully'
        }
        
        # Include score only if there are scored questions
        if total_scored > 0:
            result['score'] = {
                'correct': correct_count,
                'total': total_scored,
                'percentage': percentage
            }
            print(f"[DEBUG] Returning score: {correct_count}/{total_scored} = {percentage}%")
        else:
            print(f"[DEBUG] No scored questions, not returning score")
        
        print(f"[DEBUG] Full response: {result}")
        return jsonify(result)
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting survey: {e}")
        return jsonify({'error': str(e)}), 500


@student_class_bp.route('/class/<course_id>/exams', methods=['GET'])
@student_required
def get_class_exams(course_id):
    """Get all exams for a class"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, ExamResult
        from app.utils.class_serializers import serialize_exams_for_class

        user_id = session.get('user_id')

        enrollment = verify_enrollment(user_id, course_id)
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this class'}), 403
        
        base_exams = serialize_exams_for_class(course_id, user_id)
        
        exams_data = []
        for exam_base in base_exams:
            exam = Exam.query.filter_by(id=exam_base['id']).first()
            if not exam:
                continue
            
            results = ExamResult.query.filter_by(
                exam_id=exam.id, user_id=user_id
            ).order_by(ExamResult.attempt_number.desc()).all()
            
            exam_data = exam_base.copy()
            exam_data['results'] = [{
                'attempt_number': r.attempt_number,
                'score': r.score,
                'percentage': r.percentage,
                'passed': r.passed,
                'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None
            } for r in results]
            
            exams_data.append(exam_data)
        
        return jsonify({
            'success': True,
            'exams': exams_data
        })
    except Exception as e:
        print(f"Error getting class exams: {e}")
        return jsonify({'error': str(e)}), 500


@student_class_bp.route('/class/<course_id>/exams/<exam_id>/start', methods=['POST'])
@student_required
def start_class_exam(course_id, exam_id):
    """Start an exam - returns questions"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, ExamQuestion, ExamResult
        import random

        user_id = session.get('user_id')

        enrollment = verify_enrollment(user_id, course_id)
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this class'}), 403
        
        exam = Exam.query.filter_by(id=exam_id, course_id=course_id, is_published=True).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        attempts_used = ExamResult.query.filter_by(exam_id=exam_id, user_id=user_id).count()
        if attempts_used >= (exam.max_attempts or 999):
            return jsonify({'error': 'Maximum attempts reached'}), 400
        
        questions = ExamQuestion.query.filter_by(exam_id=exam_id).order_by(ExamQuestion.order_index).all()
        
        # Check if we should shuffle answers
        shuffle_answers = getattr(exam, 'shuffle_answers', False)
        
        questions_data = []
        for q in questions:
            options = q.options.copy() if q.options else []
            options_ar = getattr(q, 'options_ar', None)
            options_ar = options_ar.copy() if options_ar else None
            
            # Store original index mapping for answer shuffling
            original_mapping = None
            
            # Shuffle answer options if enabled (not for true/false)
            if shuffle_answers and q.question_type == 'multiple_choice' and options:
                # Create index pairs to track shuffling
                indices = list(range(len(options)))
                random.shuffle(indices)
                
                # Reorder options according to shuffled indices
                options = [options[i] for i in indices]
                if options_ar:
                    options_ar = [options_ar[i] for i in indices]
                
                # Store mapping so we can translate answer back: new_index -> original_index
                original_mapping = {str(new_idx): str(old_idx) for new_idx, old_idx in enumerate(indices)}
            
            questions_data.append({
                'id': q.id,
                'question_text': q.question_text,
                'question_text_ar': getattr(q, 'question_text_ar', None),
                'question_type': q.question_type,
                'options': options,
                'options_ar': options_ar,
                'points': q.points,
                'answer_mapping': original_mapping  # Frontend will use this to translate answer back
            })
        
        if exam.shuffle_questions:
            random.shuffle(questions_data)
        
        return jsonify({
            'success': True,
            'exam': {
                'id': exam.id,
                'title': exam.title,
                'title_ar': getattr(exam, 'title_ar', None),
                'time_limit_minutes': exam.time_limit_minutes,
                'passing_threshold': exam.passing_threshold
            },
            'questions': questions_data,
            'attempt_number': attempts_used + 1,
            'started_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"Error starting exam: {e}")
        return jsonify({'error': str(e)}), 500


@student_class_bp.route('/class/<course_id>/exams/<exam_id>/submit', methods=['POST'])
@student_required
def submit_class_exam(course_id, exam_id):
    """Submit exam answers"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Exam, ExamQuestion, ExamResult
        import uuid

        user_id = session.get('user_id')

        enrollment = verify_enrollment(user_id, course_id)
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this class'}), 403
        
        exam = Exam.query.filter_by(id=exam_id, course_id=course_id).first()
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        data = request.get_json()
        answers = data.get('answers', {})
        started_at = data.get('started_at')
        time_spent = data.get('time_spent_seconds', 0)
        
        questions = ExamQuestion.query.filter_by(exam_id=exam_id).all()
        total_points = sum(q.points or 0 for q in questions)
        earned_points = 0
        
        def normalize_answer(answer, correct, question_type='multiple_choice'):
            """Normalize answer for comparison - handles letter/index/text formats"""
            # Use explicit None/empty checks - don't treat 0 as falsy
            if answer is None or answer == '' or correct is None or correct == '':
                return None, None
            
            answer_str = str(answer).strip().upper()
            correct_str = str(correct).strip().upper()
            
            # Handle true/false questions specially
            if question_type == 'true_false':
                # Map various true/false formats to canonical form
                true_vals = {'TRUE', 'T', '0', 'A', 'YES', 'Y'}
                false_vals = {'FALSE', 'F', '1', 'B', 'NO', 'N'}
                
                answer_is_true = answer_str in true_vals
                answer_is_false = answer_str in false_vals
                correct_is_true = correct_str in true_vals
                correct_is_false = correct_str in false_vals
                
                if answer_is_true and correct_is_true:
                    return 'TRUE', 'TRUE'
                elif answer_is_false and correct_is_false:
                    return 'FALSE', 'FALSE'
                elif answer_is_true:
                    return 'TRUE', 'FALSE' if correct_is_false else correct_str
                elif answer_is_false:
                    return 'FALSE', 'TRUE' if correct_is_true else correct_str
                else:
                    return answer_str, correct_str
            
            # For multiple choice: Map letters to indices
            letter_to_idx = {'A': '0', 'B': '1', 'C': '2', 'D': '3', 'E': '4'}
            idx_to_letter = {'0': 'A', '1': 'B', '2': 'C', '3': 'D', '4': 'E'}
            
            def extract_letter_or_index(val):
                """Extract letter/index from values like 'B) Some text...' or just 'B' or '1'"""
                val = val.strip()
                # Check if it's just a single letter
                if val in letter_to_idx:
                    return letter_to_idx[val]
                # Check if it's already an index
                if val in idx_to_letter:
                    return val
                # Check if it starts with a letter followed by ) or . (like "B) answer" or "B. answer")
                import re
                match = re.match(r'^([A-E])[)\.\s]', val)
                if match:
                    letter = match.group(1)
                    return letter_to_idx.get(letter, val)
                # Check if it's a digit
                if val.isdigit() and val in idx_to_letter:
                    return val
                return val
            
            answer_normalized = extract_letter_or_index(answer_str)
            correct_normalized = extract_letter_or_index(correct_str)
            
            return answer_normalized, correct_normalized
        
        for q in questions:
            user_answer = answers.get(str(q.id), answers.get(q.id))
            user_norm, correct_norm = normalize_answer(user_answer, q.correct_answer, q.question_type or 'multiple_choice')
            print(f"DEBUG SCORING: Q={q.id[:8]}, type={q.question_type}, user_raw={user_answer}, correct_raw={q.correct_answer}, user_norm={user_norm}, correct_norm={correct_norm}, match={user_norm == correct_norm if user_norm and correct_norm else False}")
            if user_norm is not None and correct_norm is not None and user_norm == correct_norm:
                earned_points += (q.points or 0)
                print(f"DEBUG SCORING: +{q.points or 0} points")
        
        percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        passed = percentage >= (exam.passing_threshold or 60)
        
        attempts_used = ExamResult.query.filter_by(exam_id=exam_id, user_id=user_id).count()
        
        result = ExamResult(
            id=str(uuid.uuid4()),
            exam_id=exam_id,
            user_id=user_id,
            attempt_number=attempts_used + 1,
            answers=answers,
            score=earned_points,
            total_points=total_points,
            percentage=percentage,
            passed=passed,
            started_at=datetime.fromisoformat(started_at) if started_at else datetime.utcnow(),
            submitted_at=datetime.utcnow(),
            time_spent_seconds=time_spent,
            certificate_status='pending' if passed else 'not_eligible'
        )
        
        db.session.add(result)
        
        if passed and enrollment.certificate_status in [None, 'not_started', 'not_eligible']:
            enrollment.certificate_status = 'pending'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'result': {
                'score': earned_points,
                'total_points': total_points,
                'percentage': round(percentage, 1),
                'passed': passed,
                'passing_threshold': exam.passing_threshold
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting exam: {e}")
        return jsonify({'error': str(e)}), 500


@student_class_bp.route('/class/<course_id>/certificate', methods=['GET'])
@student_required
def get_class_certificate(course_id):
    """Get certificate status and details for a class"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course, Enrollment, ExamResult, Exam

        user_id = session.get('user_id')

        enrollment = verify_enrollment(user_id, course_id)
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this class'}), 403
        
        course = Course.query.filter_by(id=course_id).first()
        
        exams = Exam.query.filter_by(course_id=course_id, is_published=True).all()
        exam_results = []
        all_passed = True
        
        for exam in exams:
            best_result = ExamResult.query.filter_by(
                exam_id=exam.id, 
                user_id=user_id
            ).order_by(ExamResult.percentage.desc()).first()
            
            exam_results.append({
                'exam_id': exam.id,
                'exam_title': exam.title,
                'passed': best_result.passed if best_result else False,
                'percentage': best_result.percentage if best_result else 0
            })
            
            if not best_result or not best_result.passed:
                all_passed = False
        
        is_eligible = (
            course.certificate_enabled and 
            (enrollment.progress_percent or 0) >= 80 and 
            all_passed
        )
        
        return jsonify({
            'success': True,
            'certificate': {
                'status': enrollment.certificate_status or 'not_started',
                'is_eligible': is_eligible,
                'certificate_url': enrollment.certificate_url,
                'approved_by': enrollment.certificate_approved_by,
                'approved_at': enrollment.certificate_approved_at.isoformat() if enrollment.certificate_approved_at else None,
                'course_certificate_enabled': course.certificate_enabled,
                'progress_percent': enrollment.progress_percent or 0,
                'exam_results': exam_results,
                'requirements': {
                    'progress_required': 80,
                    'all_exams_passed': all_passed
                }
            }
        })
    except Exception as e:
        print(f"Error getting certificate: {e}")
        return jsonify({'error': str(e)}), 500


@student_class_bp.route('/class/<course_id>/certificate/download', methods=['GET'])
@student_required
def download_student_certificate(course_id):
    """Download certificate PDF for a class"""
    from flask import send_file
    import io
    import os
    
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import Course, Enrollment, Exam, ExamResult, User
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.colors import HexColor, black
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        import qrcode
        
        user_id = session.get('user_id')

        enrollment = verify_enrollment(user_id, course_id)
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this class'}), 403

        if not enrollment.certificate_issued:
            return jsonify({'error': 'Certificate not yet issued for this class'}), 400

        student = User.query.filter_by(id=user_id).first()
        course = Course.query.filter_by(id=course_id).first()
        
        exams = Exam.query.filter_by(course_id=course_id).all()
        exam_ids = [e.id for e in exams]
        exam_results = ExamResult.query.filter(
            ExamResult.user_id == user_id,
            ExamResult.exam_id.in_(exam_ids)
        ).all() if exam_ids else []
        
        avg_score = sum(r.score or 0 for r in exam_results) / len(exam_results) if exam_results else 0
        final_grade = enrollment.final_grade or round(avg_score, 1)
        
        cert_number = f"CERT-{enrollment.id[:8].upper()}" if isinstance(enrollment.id, str) else f"CERT-{enrollment.id:08d}"
        
        buffer = io.BytesIO()
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(buffer, pagesize=landscape(A4))
        
        primary_color = HexColor('#1a5c5e')
        secondary_color = HexColor('#2d7d80')
        gold_color = HexColor('#c4a35a')
        dark_blue = HexColor('#1a3a5c')
        
        c.setStrokeColor(primary_color)
        c.setLineWidth(3)
        c.rect(20, 20, page_width - 40, page_height - 40)
        
        c.setStrokeColor(gold_color)
        c.setLineWidth(1.5)
        c.rect(35, 35, page_width - 70, page_height - 70)
        
        corner_size = 25
        for x, y in [(40, 40), (page_width - 65, 40), (40, page_height - 65), (page_width - 65, page_height - 65)]:
            c.setFillColor(gold_color)
            c.circle(x + corner_size/2, y + corner_size/2, corner_size/3, fill=1, stroke=0)
        
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        images_path = os.path.join(base_path, 'static', 'images')
        
        # LEFT side - AIAC logo + NATD logo together (equal sizes, below corner dots)
        logo_size = 75  # Equal size for left logos
        logo_y = page_height - 140  # Position below the corner dots
        
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
        
        # RIGHT side - University logo (ac-logo) - larger to match other logos visually
        ac_logo_path = os.path.join(images_path, 'ac-logo.png')
        if os.path.exists(ac_logo_path):
            try:
                ac_logo_size = 115  # Larger size to visually match other logos
                c.drawImage(ac_logo_path, page_width - 165, logo_y - 20, width=ac_logo_size, height=ac_logo_size, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(page_width / 2, page_height - 90, "CERTIFICATE")
        
        c.setFillColor(gold_color)
        c.setFont("Helvetica", 16)
        c.drawCentredString(page_width / 2, page_height - 115, "OF COMPLETION")
        
        c.setStrokeColor(gold_color)
        c.setLineWidth(2)
        c.line(page_width/2 - 120, page_height - 125, page_width/2 + 120, page_height - 125)
        
        c.setFillColor(black)
        c.setFont("Helvetica", 14)
        c.drawCentredString(page_width / 2, page_height - 160, "This is to certify that")
        
        # Student Name - auto-adjust font size to fit within borders
        student_name = student.full_name if student else 'Unknown Student'
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
        
        course_title = course.title if course else 'Training Program'
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
        
        sig_y = 120
        
        # LEFT side - Chair Signature (touching the line below)
        signature_path = os.path.join(images_path, 'signature.png')
        if os.path.exists(signature_path):
            try:
                c.drawImage(signature_path, 80, sig_y - 5, width=120, height=50, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        # LEFT side - Chair Stamp (aiac-stamp.png) centered above the signature
        chair_stamp_path = os.path.join(images_path, 'aiac-stamp.png')
        if os.path.exists(chair_stamp_path):
            try:
                chair_stamp_size = 80
                # Center stamp over signature line (line is from x=60 to x=220, center = 140)
                stamp_x = 140 - chair_stamp_size / 2  # Center at x=140
                # Position stamp higher to avoid covering signature (sig_y + 70)
                c.drawImage(chair_stamp_path, stamp_x, sig_y + 70, width=chair_stamp_size, height=chair_stamp_size, preserveAspectRatio=True, mask='auto')
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
        
        # CENTER - Date of Issue (moved up to avoid stamp intersection)
        from datetime import datetime as dt
        c.setFillColor(black)
        c.setFont("Helvetica", 10)
        issue_date = enrollment.certificate_issued_at.strftime('%B %d, %Y') if enrollment.certificate_issued_at else dt.utcnow().strftime('%B %d, %Y')
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
        
        c.setFont("Helvetica", 9)
        c.setFillColor(secondary_color)
        c.drawCentredString(page_width / 2, sig_y - 45, f"Certificate No: {cert_number}")
        
        # RIGHT side - Academy Director Signature (signature2.png)
        signature2_path = os.path.join(images_path, 'signature2.png')
        if os.path.exists(signature2_path):
            try:
                c.drawImage(signature2_path, page_width - 200, sig_y - 5, width=120, height=50, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        # RIGHT side - NATD Stamp centered above the signature
        natd_stamp_path = os.path.join(images_path, 'NATD_stamp.png')
        if os.path.exists(natd_stamp_path):
            try:
                natd_stamp_size = 80
                # Center stamp over signature line (line center = page_width - 140)
                stamp_x = (page_width - 140) - natd_stamp_size / 2
                # Position stamp higher to avoid covering signature (sig_y + 70)
                c.drawImage(natd_stamp_path, stamp_x, sig_y + 70, width=natd_stamp_size, height=natd_stamp_size, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.line(page_width - 220, sig_y, page_width - 60, sig_y)
        
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(page_width - 140, sig_y - 15, "Academy Director")
        c.setFont("Helvetica", 9)
        c.drawCentredString(page_width - 140, sig_y - 28, "Nizwa Academy for")
        c.drawCentredString(page_width - 140, sig_y - 40, "Training and Development")
        
        c.setFillColor(HexColor('#cccccc'))
        c.setFont("Helvetica", 8)
        c.drawCentredString(page_width / 2, 35, "This certificate is digitally generated and verifiable. Any unauthorized alteration renders this certificate void.")
        
        c.setFillColor(secondary_color)
        c.setFont("Helvetica", 8)
        c.drawCentredString(page_width / 2, 22, "University of Nizwa - AI Applications Chair | Nizwa Academy for Training and Development")
        
        c.save()
        buffer.seek(0)
        
        safe_name = ''.join(ch for ch in student_name if ch.isalnum() or ch in ' -_').strip()
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
        print(f"Error generating certificate: {e}")
        return jsonify({'error': f'Failed to generate certificate: {str(e)}'}), 500


@student_class_bp.route('/class/<course_id>/materials', methods=['GET'])
@student_required
def get_class_materials(course_id):
    """Get all materials for a class organized by week"""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        from app.models import CourseWeek, WeekMaterial, LearningProgress

        user_id = session.get('user_id')

        enrollment = verify_enrollment(user_id, course_id)
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this class'}), 403
        
        weeks = CourseWeek.query.filter_by(course_id=course_id).order_by(CourseWeek.week_number).all()
        weeks_data = []
        
        for week in weeks:
            materials = WeekMaterial.query.filter_by(week_id=week.id, is_published=True).order_by(WeekMaterial.order_index).all()
            materials_data = []
            
            for mat in materials:
                progress = LearningProgress.query.filter_by(user_id=user_id, material_id=mat.id).first()
                
                materials_data.append({
                    'id': mat.id,
                    'title': mat.title,
                    'description': mat.description,
                    'material_type': mat.material_type,
                    'file_url': mat.file_url,
                    'external_url': mat.external_url,
                    'duration_minutes': mat.duration_minutes,
                    'is_completed': progress and progress.status == 'completed',
                    'progress_percent': progress.progress_percent if progress else 0,
                    'last_accessed': progress.last_accessed.isoformat() if progress and progress.last_accessed else None
                })
            
            weeks_data.append({
                'id': week.id,
                'week_number': week.week_number,
                'title': week.title,
                'description': week.description,
                'start_date': week.start_date.isoformat() if week.start_date else None,
                'end_date': week.end_date.isoformat() if week.end_date else None,
                'is_published': week.is_published,
                'materials': materials_data
            })
        
        return jsonify({
            'success': True,
            'weeks': weeks_data
        })
    except Exception as e:
        print(f"Error getting class materials: {e}")
        return jsonify({'error': str(e)}), 500
