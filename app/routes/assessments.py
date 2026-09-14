"""
Phase 3 — Smart Assessment API
==============================

Endpoints (all under `/api/assessments`):

  GET  /signals                              public list of proctoring signals
  GET  /retention/due                        learner's due retention items
  POST /retention/<skill_id>/start           start a retention attempt
  POST /attempts                             start a generic attempt (with consent)
  GET  /attempts/<id>                        attempt detail (own attempt)
  POST /attempts/<id>/events                 log a proctoring event
  POST /attempts/<id>/grade                  submit answers for rubric grading
  POST /attempts/<id>/finalize               finalize, run flag evaluation
  POST /grade/rubric                         one-off rubric grading helper
"""

from datetime import datetime
from flask import Blueprint, jsonify, request, session

from app.services.assessment_service import (
    ALLOWED_EVENT_TYPES,
    PROCTORING_SIGNALS,
    RubricGrader,
    evaluate_flags,
    get_due_retention_items,
    list_proctoring_signals,
)

assessments_bp = Blueprint('assessments', __name__, url_prefix='/api/assessments')


def _current_user_id():
    return session.get('user_id')


def _require_login():
    if not _current_user_id():
        return jsonify({'error': 'Authentication required'}), 401
    return None


def _staff_can_see_attempt(attempt) -> bool:
    """True if the current user is admin, or a teacher of the attempt's course."""
    role = (session.get('role') or '').lower()
    if role in {'admin', 'institution_admin', 'super_admin', 'superadmin'}:
        return True
    if role not in {'teacher', 'instructor'}:
        return False
    if not attempt.exam_id:
        return False
    from app.models import CourseInstructor, Exam
    exam = Exam.query.get(attempt.exam_id)
    if not exam:
        return False
    return CourseInstructor.query.filter_by(
        course_id=exam.course_id, user_id=_current_user_id()
    ).first() is not None


def _attempt_to_dict(attempt, include_events: bool = False):
    data = {
        'id': attempt.id,
        'user_id': attempt.user_id,
        'exam_id': attempt.exam_id,
        'exam_result_id': attempt.exam_result_id,
        'attempt_kind': attempt.attempt_kind,
        'skill_id': attempt.skill_id,
        'consent_proctoring': attempt.consent_proctoring,
        'accommodation_opt_out': attempt.accommodation_opt_out,
        'consent_signals': attempt.consent_signals or [],
        'status': attempt.status,
        'started_at': attempt.started_at.isoformat() if attempt.started_at else None,
        'submitted_at': attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        'time_spent_seconds': attempt.time_spent_seconds,
        'score': attempt.score,
        'total_points': attempt.total_points,
        'percentage': attempt.percentage,
        'rubric_results': attempt.rubric_results or {},
        'flagged': attempt.flagged,
        'flag_reasons': attempt.flag_reasons or [],
        'teacher_review_status': attempt.teacher_review_status,
    }
    if include_events:
        data['events'] = [
            {
                'id': e.id,
                'event_type': e.event_type,
                'severity': e.severity,
                'payload': e.payload or {},
                'created_at': e.created_at.isoformat() if e.created_at else None,
            }
            for e in attempt.events.order_by('created_at').all()
        ]
    return data


# ---------------------------------------------------------------------------
# Transparency
# ---------------------------------------------------------------------------

@assessments_bp.route('/signals', methods=['GET'])
def signals():
    """Public list of every proctoring signal the platform may collect."""
    return jsonify({
        'success': True,
        'signals': list_proctoring_signals(),
        'never_collected': [
            'camera video', 'microphone audio', 'face recognition',
            'keystroke timing', 'mouse movement', 'screen recording',
            'biometric data',
        ],
        'opt_out_supported': True,
    })


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------

@assessments_bp.route('/retention/due', methods=['GET'])
def retention_due():
    err = _require_login()
    if err:
        return err
    from app.models import db
    items = get_due_retention_items(_current_user_id(), db)
    return jsonify({'success': True, 'items': items, 'count': len(items)})


@assessments_bp.route('/retention/<skill_id>/start', methods=['POST'])
def retention_start(skill_id):
    err = _require_login()
    if err:
        return err
    from app.models import AssessmentAttempt, LearnerSkill, Skill, db

    skill = Skill.query.get(skill_id)
    if not skill:
        return jsonify({'error': 'Skill not found'}), 404

    ls = LearnerSkill.query.filter_by(
        user_id=_current_user_id(), skill_id=skill_id
    ).first()
    if not ls:
        return jsonify({'error': 'No mastery record for this skill yet.'}), 400

    body = request.get_json(silent=True) or {}
    attempt = AssessmentAttempt(
        user_id=_current_user_id(),
        skill_id=skill_id,
        attempt_kind='retention',
        consent_proctoring=bool(body.get('consent_proctoring', False)),
        accommodation_opt_out=bool(body.get('accommodation_opt_out', False)),
        consent_signals=body.get('consent_signals') or [],
        status='in_progress',
        started_at=datetime.utcnow(),
    )
    db.session.add(attempt)
    db.session.commit()

    # Actually generate the lightweight retention quiz so the caller can
    # render it immediately. Falls back to a deterministic template when no
    # AI key is configured (see QuestionGenerator.generate_retention_quiz).
    quiz = {'success': False, 'questions': []}
    try:
        from config.config import Config
        from app.services.ai_service import AIService
        from app.services.question_generator import QuestionGenerator

        try:
            ai_service = AIService()
        except Exception:
            ai_service = None
        generator = QuestionGenerator(ai_service, Config())
        skill_name = getattr(skill, 'name', None) or getattr(skill, 'title', None) or 'this skill'
        skill_name_ar = getattr(skill, 'name_ar', None) or getattr(skill, 'title_ar', None)
        try:
            n = int(body.get('num_questions') or 5)
        except (TypeError, ValueError):
            n = 5
        n = max(1, min(n, 10))
        quiz = generator.generate_retention_quiz(
            skill_name=skill_name,
            skill_name_ar=skill_name_ar,
            num_questions=n,
            language=body.get('language') or 'en',
        )
    except Exception as e:
        quiz = {'success': False, 'error': str(e), 'questions': []}

    # Persist the server-authoritative quiz key on the attempt so submission
    # grading does not trust client-provided correct answers.
    questions = (quiz.get('questions') or []) if isinstance(quiz, dict) else []
    attempt.rubric_results = {
        'quiz': [
            {
                'index': i,
                'type': q.get('type') or 'true_false',
                'question': q.get('question') or q.get('question_en'),
                'options': q.get('options') or ['True', 'False'],
                'correct_answer': q.get('correct_answer'),
            }
            for i, q in enumerate(questions)
        ],
    }
    db.session.commit()

    # Strip the answer key from the response sent to the browser.
    public_quiz = dict(quiz) if isinstance(quiz, dict) else {'questions': []}
    public_quiz['questions'] = [
        {k: v for k, v in q.items() if k not in ('correct_answer', 'correct_answer_ar')}
        for q in questions
    ]

    # Never leak the stored answer key to the browser via attempt payload.
    attempt_payload = _attempt_to_dict(attempt)
    attempt_payload['rubric_results'] = {}

    return jsonify({
        'success': True,
        'attempt': attempt_payload,
        'skill': {
            'id': skill.id,
            'code': getattr(skill, 'code', None),
            'name': getattr(skill, 'name', None) or getattr(skill, 'title', None),
        },
        'quiz': public_quiz,
    }), 201


# ---------------------------------------------------------------------------
# Attempts
# ---------------------------------------------------------------------------

@assessments_bp.route('/retention/<attempt_id>/submit', methods=['POST'])
def retention_submit(attempt_id):
    """Grade a retention attempt's MCQ/TF answers, update LearnerSkill, finalize.

    Expected body:
      {
        "responses": [
          {"index": 0, "type": "true_false"|"multiple_choice",
           "correct_answer": "True", "user_answer": "True",
           "question": "...", "options": [..]}
        ]
      }
    """
    err = _require_login()
    if err:
        return err
    from app.models import AssessmentAttempt, LearnerSkill, db
    from app.services.assessment_service import (
        compute_decay,
        evaluate_flags,
    )

    attempt = AssessmentAttempt.query.get(attempt_id)
    if not attempt:
        return jsonify({'error': 'Attempt not found'}), 404
    if attempt.user_id != _current_user_id():
        return jsonify({'error': 'Forbidden'}), 403
    if attempt.attempt_kind != 'retention':
        return jsonify({'error': 'Not a retention attempt'}), 400
    if attempt.status != 'in_progress':
        return jsonify({
            'error': 'Attempt has already been submitted.',
            'status': attempt.status,
        }), 409

    # Server-authoritative answer key, persisted at /retention/<skill>/start.
    stored = (attempt.rubric_results or {}).get('quiz') or []
    if not stored:
        return jsonify({'error': 'No stored quiz for this attempt'}), 400
    key_by_index = {int(q.get('index', i)): q for i, q in enumerate(stored)}

    body = request.get_json(silent=True) or {}
    responses = body.get('responses') or []
    if not isinstance(responses, list):
        return jsonify({'error': 'responses must be a list'}), 400

    def _normalize(val):
        return str(val if val is not None else '').strip().lower()

    # Map client-supplied user answers by index, ignoring any client-supplied
    # correct_answer fields entirely.
    user_by_index = {}
    for i, r in enumerate(responses):
        if not isinstance(r, dict):
            continue
        try:
            idx = int(r.get('index', i))
        except (TypeError, ValueError):
            idx = i
        user_by_index[idx] = r.get('user_answer')

    feedback = []
    correct = 0
    total = 0
    for idx in sorted(key_by_index.keys()):
        q = key_by_index[idx]
        total += 1
        expected_raw = q.get('correct_answer')
        given_raw = user_by_index.get(idx)
        expected = _normalize(expected_raw)
        given = _normalize(given_raw)
        is_correct = bool(expected) and expected == given
        if is_correct:
            correct += 1
        feedback.append({
            'index': idx,
            'question': q.get('question'),
            'type': q.get('type'),
            'options': q.get('options'),
            'user_answer': given_raw,
            'correct_answer': expected_raw,
            'is_correct': is_correct,
        })

    percentage = round((correct / total * 100.0) if total else 0.0, 1)
    score_fraction = (correct / total) if total else 0.0

    # Update LearnerSkill confidence: refresh evidence and blend with score.
    ls = None
    if attempt.skill_id:
        ls = LearnerSkill.query.filter_by(
            user_id=_current_user_id(), skill_id=attempt.skill_id
        ).first()
    confidence_before = float(ls.confidence) if ls and ls.confidence is not None else None
    confidence_after = None
    if ls:
        decayed = compute_decay(ls.confidence or 0.0, ls.last_evidence_at)
        # New confidence = decayed baseline blended with this attempt's score.
        # Strong score (>=80%) restores/raises confidence; weak score pulls down.
        new_conf = max(0.0, min(1.0, 0.4 * decayed + 0.6 * score_fraction))
        ls.confidence = new_conf
        ls.last_evidence_at = datetime.utcnow()
        ls.evidence_count = (ls.evidence_count or 0) + 1
        confidence_after = new_conf

    # Finalize the attempt.
    attempt.score = float(correct)
    attempt.total_points = float(total)
    attempt.percentage = percentage
    attempt.rubric_results = {
        'quiz': stored,
        'retention_feedback': feedback,
        'correct': correct,
        'total': total,
    }
    events = attempt.events.all()
    flags = evaluate_flags(events)
    attempt.flag_reasons = flags
    attempt.flagged = bool(flags)
    attempt.status = 'submitted'
    attempt.submitted_at = datetime.utcnow()
    if attempt.started_at:
        attempt.time_spent_seconds = int(
            (attempt.submitted_at - attempt.started_at).total_seconds()
        )
    db.session.commit()

    return jsonify({
        'success': True,
        'attempt': _attempt_to_dict(attempt),
        'feedback': feedback,
        'correct': correct,
        'total': total,
        'percentage': percentage,
        'confidence_before': confidence_before,
        'confidence_after': confidence_after,
    })


@assessments_bp.route('/attempts', methods=['POST'])
def create_attempt():
    err = _require_login()
    if err:
        return err
    from app.models import AssessmentAttempt, db

    body = request.get_json(silent=True) or {}
    attempt = AssessmentAttempt(
        user_id=_current_user_id(),
        exam_id=body.get('exam_id'),
        exam_result_id=body.get('exam_result_id'),
        attempt_kind=body.get('attempt_kind', 'initial'),
        skill_id=body.get('skill_id'),
        consent_proctoring=bool(body.get('consent_proctoring', False)),
        accommodation_opt_out=bool(body.get('accommodation_opt_out', False)),
        consent_signals=body.get('consent_signals') or [],
        status='in_progress',
        started_at=datetime.utcnow(),
    )
    db.session.add(attempt)
    db.session.commit()
    return jsonify({'success': True, 'attempt': _attempt_to_dict(attempt)}), 201


@assessments_bp.route('/attempts/<attempt_id>', methods=['GET'])
def get_attempt(attempt_id):
    err = _require_login()
    if err:
        return err
    from app.models import AssessmentAttempt

    attempt = AssessmentAttempt.query.get(attempt_id)
    if not attempt:
        return jsonify({'error': 'Attempt not found'}), 404
    if attempt.user_id != _current_user_id() and not _staff_can_see_attempt(attempt):
        return jsonify({'error': 'Forbidden'}), 403
    payload = _attempt_to_dict(attempt, include_events=True)
    # Never expose stored answer keys to the learner before submission.
    if (attempt.attempt_kind == 'retention'
            and attempt.status == 'in_progress'
            and not _staff_can_see_attempt(attempt)):
        rr = dict(payload.get('rubric_results') or {})
        if 'quiz' in rr:
            rr['quiz'] = [
                {k: v for k, v in q.items()
                 if k not in ('correct_answer', 'correct_answer_ar')}
                for q in rr['quiz']
            ]
        payload['rubric_results'] = rr
    return jsonify({'success': True, 'attempt': payload})


@assessments_bp.route('/attempts/<attempt_id>/events', methods=['POST'])
def log_event(attempt_id):
    err = _require_login()
    if err:
        return err
    from app.models import AssessmentAttempt, ProctoringEvent, db

    attempt = AssessmentAttempt.query.get(attempt_id)
    if not attempt:
        return jsonify({'error': 'Attempt not found'}), 404
    if attempt.user_id != _current_user_id():
        return jsonify({'error': 'Forbidden'}), 403
    if attempt.accommodation_opt_out:
        return jsonify({
            'success': True,
            'skipped': True,
            'reason': 'Learner has opted out of proctoring (accommodation).',
        })
    if not attempt.consent_proctoring:
        return jsonify({
            'error': 'Proctoring consent not granted for this attempt.',
        }), 403

    body = request.get_json(silent=True) or {}
    event_type = body.get('event_type')
    if event_type not in ALLOWED_EVENT_TYPES:
        return jsonify({
            'error': 'Unsupported event_type',
            'allowed': sorted(ALLOWED_EVENT_TYPES),
        }), 400

    payload = body.get('payload') or {}
    if not isinstance(payload, dict):
        return jsonify({'error': 'payload must be an object'}), 400
    # Strip anything that even looks biometric, just in case.
    forbidden = {
        'face', 'face_data', 'image', 'video', 'audio', 'camera',
        'microphone', 'biometric', 'fingerprint', 'keystrokes',
        'mouse_path',
    }
    payload = {k: v for k, v in payload.items() if k.lower() not in forbidden}

    event = ProctoringEvent(
        attempt_id=attempt.id,
        event_type=event_type,
        severity=PROCTORING_SIGNALS[event_type]['severity'],
        payload=payload,
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({'success': True, 'event_id': event.id}), 201


@assessments_bp.route('/attempts/<attempt_id>/grade', methods=['POST'])
def grade_attempt(attempt_id):
    """Run rubric grading for short-answer / essay responses.

    Expected body:
      {
        "responses": [
           {"question_id": "...", "question": "...", "answer": "...",
            "rubric": [...], "reference": "...", "language": "en"}
        ]
      }
    """
    err = _require_login()
    if err:
        return err
    from app.models import AssessmentAttempt, db

    attempt = AssessmentAttempt.query.get(attempt_id)
    if not attempt:
        return jsonify({'error': 'Attempt not found'}), 404
    if attempt.user_id != _current_user_id() and not _staff_can_see_attempt(attempt):
        return jsonify({'error': 'Forbidden'}), 403

    body = request.get_json(silent=True) or {}
    responses = body.get('responses') or []
    if not isinstance(responses, list):
        return jsonify({'error': 'responses must be a list'}), 400

    try:
        from app.services.ai_service import AIService
        ai_service = AIService()
    except Exception:
        ai_service = None
    grader = RubricGrader(ai_service=ai_service)

    # Lazy import to avoid circular load.
    from app.models import ExamQuestion

    # Batch-load any referenced questions up front so grading does not do
    # N+1 lookups when responses include question_id.
    question_ids = [r.get('question_id') for r in responses
                    if isinstance(r, dict) and r.get('question_id')]
    questions_by_id = {}
    if question_ids:
        for q in ExamQuestion.query.filter(ExamQuestion.id.in_(question_ids)).all():
            questions_by_id[q.id] = q

    rubric_results = dict(attempt.rubric_results or {})
    total = 0.0
    max_total = 0.0
    for r in responses:
        qid = r.get('question_id') or r.get('id') or f'q{len(rubric_results)+1}'
        # Fall back to the per-question rubric defined by the teacher when
        # the request did not supply one.
        rubric = r.get('rubric')
        question_text = r.get('question', '')
        q = questions_by_id.get(r.get('question_id'))
        if q is not None:
            if not rubric and getattr(q, 'rubric', None):
                rubric = q.rubric
            if not question_text:
                question_text = q.question_text or ''
        graded = grader.grade(
            question=question_text,
            answer=r.get('answer', ''),
            rubric=rubric,
            reference=r.get('reference'),
            language=r.get('language', 'en'),
        )
        rubric_results[qid] = graded
        total += float(graded.get('total', 0))
        max_total += float(graded.get('max_total', 0))

    attempt.rubric_results = rubric_results
    attempt.score = total
    attempt.total_points = max_total
    attempt.percentage = round((total / max_total * 100) if max_total else 0.0, 1)
    db.session.commit()

    return jsonify({
        'success': True,
        'attempt_id': attempt.id,
        'rubric_results': rubric_results,
        'score': attempt.score,
        'total_points': attempt.total_points,
        'percentage': attempt.percentage,
    })


@assessments_bp.route('/attempts/<attempt_id>/finalize', methods=['POST'])
def finalize_attempt(attempt_id):
    err = _require_login()
    if err:
        return err
    from app.models import AssessmentAttempt, db

    attempt = AssessmentAttempt.query.get(attempt_id)
    if not attempt:
        return jsonify({'error': 'Attempt not found'}), 404
    if attempt.user_id != _current_user_id():
        return jsonify({'error': 'Forbidden'}), 403

    events = attempt.events.all()
    flags = evaluate_flags(events)
    attempt.flag_reasons = flags
    attempt.flagged = bool(flags)
    attempt.status = 'submitted' if attempt.status == 'in_progress' else attempt.status
    attempt.submitted_at = attempt.submitted_at or datetime.utcnow()
    if attempt.started_at and attempt.submitted_at:
        attempt.time_spent_seconds = int(
            (attempt.submitted_at - attempt.started_at).total_seconds()
        )
    db.session.commit()
    return jsonify({
        'success': True,
        'attempt': _attempt_to_dict(attempt, include_events=True),
    })


@assessments_bp.route('/grade/rubric', methods=['POST'])
def grade_rubric_oneoff():
    """One-off rubric grading helper (does not persist anything)."""
    err = _require_login()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    try:
        from app.services.ai_service import AIService
        ai_service = AIService()
    except Exception:
        ai_service = None
    grader = RubricGrader(ai_service=ai_service)
    result = grader.grade(
        question=body.get('question', ''),
        answer=body.get('answer', ''),
        rubric=body.get('rubric'),
        reference=body.get('reference'),
        language=body.get('language', 'en'),
    )
    return jsonify({'success': True, 'result': result})
