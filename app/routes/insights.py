"""
SkillPilot v2 — Phase 6: Analytics, sentiment, at-risk alerts.

Mounted at /api/v1/insights/* — additive, never modifies existing analytics.
"""
from datetime import datetime, timedelta, date, time
import csv
import io

from flask import Blueprint, jsonify, request, session, Response

from app.utils.decorators import login_required, teacher_required


insights_bp = Blueprint('insights_v2', __name__, url_prefix='/api/v1/insights')


def _csv_safe(v):
    """CSV formula-injection guard: prefix any cell that begins with
    =, +, -, @, TAB, or CR with a single quote so spreadsheet apps don't
    interpret it as a formula."""
    if v is None:
        return ''
    s = str(v)
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s


def _csv_row(cells):
    return [_csv_safe(c) for c in cells]


# ---------- helpers --------------------------------------------------------

_NEG = {
    'en': ['hate', 'awful', 'terrible', 'frustrated', 'confus', 'stuck', 'lost',
           'angry', 'fail', 'difficult', 'boring', 'cannot', "can't", 'hard'],
    'ar': ['سيء', 'صعب', 'محبط', 'كره', 'فشل', 'مستحيل', 'ممل'],
}
_POS = {
    'en': ['great', 'love', 'awesome', 'excellent', 'clear', 'helpful', 'fun',
           'enjoy', 'thanks', 'understood', 'easy', 'amazing'],
    'ar': ['ممتاز', 'رائع', 'جيد', 'سهل', 'شكرا', 'محبوب', 'سعيد'],
}


def _score_sentiment(text, lang='en'):
    if not text:
        return 0.0, 'neutral'
    t = text.lower()
    pos = sum(1 for w in _POS.get(lang, _POS['en']) if w in t)
    neg = sum(1 for w in _NEG.get(lang, _NEG['en']) if w in t)
    if pos == 0 and neg == 0:
        return 0.0, 'neutral'
    score = (pos - neg) / max(1, (pos + neg))
    label = 'positive' if score > 0.2 else ('negative' if score < -0.2 else 'neutral')
    return round(score, 3), label


# ---------- cohort analytics ----------------------------------------------

@insights_bp.route('/cohort', methods=['GET'])
@teacher_required
def cohort_analytics():
    """Compute or return latest cohort/course analytics rollup."""
    from app.models import (
        db, Enrollment, ExamResult, CohortAnalyticsSnapshot, AtRiskAlert,
        SentimentSignal, XPEvent, Attendance,
    )
    course_id = request.args.get('course_id')
    cohort_id = request.args.get('cohort_id')
    refresh = request.args.get('refresh', '0') == '1'

    if not refresh:
        snap_q = CohortAnalyticsSnapshot.query
        if course_id: snap_q = snap_q.filter_by(course_id=course_id)
        if cohort_id: snap_q = snap_q.filter_by(cohort_id=cohort_id)
        latest = snap_q.order_by(CohortAnalyticsSnapshot.captured_at.desc()).first()
        if latest:
            return jsonify({'success': True, 'snapshot': _snap_to_dict(latest), 'cached': True})

    from app.models import CohortMember
    enr_q = Enrollment.query
    if course_id:
        enr_q = enr_q.filter_by(course_id=course_id)
    if cohort_id:
        member_ids = [m.user_id for m in
                      CohortMember.query.filter_by(cohort_id=cohort_id).all()]
        enr_q = enr_q.filter(Enrollment.user_id.in_(member_ids)) \
                if member_ids else enr_q.filter(db.false())
    enrollments = enr_q.all()
    learner_count = len(enrollments)
    completed = sum(1 for e in enrollments if (getattr(e, 'progress_percent', 0) or 0) >= 100)
    avg_progress = (sum((getattr(e, 'progress_percent', 0) or 0) for e in enrollments) / learner_count) \
                   if learner_count else 0.0

    from app.models import Exam
    exam_q = ExamResult.query
    if course_id:
        exam_q = exam_q.join(Exam, Exam.id == ExamResult.exam_id)\
                       .filter(Exam.course_id == course_id)
    exam_results = exam_q.limit(2000).all()
    avg_exam_score = (sum((r.score or 0) for r in exam_results) / len(exam_results)) \
                     if exam_results else None

    sentiments = SentimentSignal.query.order_by(SentimentSignal.created_at.desc()).limit(500).all()
    avg_sent = (sum((s.sentiment_score or 0) for s in sentiments) / len(sentiments)) \
               if sentiments else None

    user_ids = {e.user_id for e in enrollments}
    at_risk_count = AtRiskAlert.query.filter(
        AtRiskAlert.status == 'open',
        AtRiskAlert.user_id.in_(list(user_ids)) if user_ids else False,
    ).count() if user_ids else 0

    snap = CohortAnalyticsSnapshot(
        course_id=course_id, cohort_id=cohort_id,
        learner_count=learner_count,
        active_learner_count=sum(1 for e in enrollments
                                 if (getattr(e, 'progress_percent', 0) or 0) > 0),
        avg_progress_percent=round(avg_progress, 1),
        avg_exam_score=round(avg_exam_score, 1) if avg_exam_score is not None else None,
        completion_rate=round(100.0 * completed / learner_count, 1) if learner_count else 0.0,
        avg_sentiment=round(avg_sent, 3) if avg_sent is not None else None,
        at_risk_count=at_risk_count,
        heatmap=_build_weekly_heatmap(
            user_ids=user_ids, course_id=course_id, weeks_back=8,
            XPEvent=XPEvent, ExamResult=ExamResult, Exam=Exam,
            Attendance=Attendance, Enrollment=Enrollment,
        ),
        item_analytics={},
    )
    db.session.add(snap); db.session.commit()
    return jsonify({'success': True, 'snapshot': _snap_to_dict(snap), 'cached': False})


def _build_weekly_heatmap(user_ids, course_id, weeks_back,
                          XPEvent, ExamResult, Exam, Attendance, Enrollment):
    """Build per-week engagement / progress / exam-attempt / attendance counts.

    Returns {'weeks': [{'week': 'YYYY-MM-DD', 'cells': [{label, value}, ...]}, ...]}.
    Weeks are anchored to Monday and ordered oldest -> newest. Cells are
    restricted to the supplied cohort (user_ids) and course where applicable.
    """
    today = date.today()
    monday_this_week = today - timedelta(days=today.weekday())
    week_starts = [monday_this_week - timedelta(weeks=i)
                   for i in range(weeks_back - 1, -1, -1)]
    user_id_list = list(user_ids) if user_ids else []

    weeks = []
    for ws in week_starts:
        we = ws + timedelta(days=7)
        ws_dt = datetime.combine(ws, time.min)
        we_dt = datetime.combine(we, time.min)

        if user_id_list:
            engagement = (XPEvent.query
                          .filter(XPEvent.user_id.in_(user_id_list),
                                  XPEvent.created_at >= ws_dt,
                                  XPEvent.created_at < we_dt)
                          .count())
            exam_q = (ExamResult.query
                      .filter(ExamResult.user_id.in_(user_id_list),
                              ExamResult.submitted_at >= ws_dt,
                              ExamResult.submitted_at < we_dt))
            if course_id:
                exam_q = exam_q.join(Exam, Exam.id == ExamResult.exam_id)\
                               .filter(Exam.course_id == course_id)
            exam_attempts = exam_q.count()

            att_q = Attendance.query.filter(
                Attendance.user_id.in_(user_id_list),
                Attendance.attendance_date >= ws,
                Attendance.attendance_date < we,
                Attendance.status == 'present',
            )
            if course_id:
                att_q = att_q.filter(Attendance.course_id == course_id)
            attendance_present = att_q.count()

            progress_q = Enrollment.query.filter(
                Enrollment.user_id.in_(user_id_list),
                Enrollment.completed_at >= ws_dt,
                Enrollment.completed_at < we_dt,
            )
            if course_id:
                progress_q = progress_q.filter(Enrollment.course_id == course_id)
            completions = progress_q.count()
        else:
            engagement = exam_attempts = attendance_present = completions = 0

        weeks.append({
            'week': ws.isoformat(),
            'cells': [
                {'label': 'Engagement (XP events)', 'value': engagement},
                {'label': 'Exam attempts', 'value': exam_attempts},
                {'label': 'Attendance (present)', 'value': attendance_present},
                {'label': 'Completions', 'value': completions},
            ],
        })
    return {'weeks': weeks}


def _snap_to_dict(s):
    return {
        'id': s.id, 'course_id': s.course_id, 'cohort_id': s.cohort_id,
        'captured_at': s.captured_at.isoformat() if s.captured_at else None,
        'learner_count': s.learner_count, 'active_learner_count': s.active_learner_count,
        'avg_progress_percent': s.avg_progress_percent,
        'avg_exam_score': s.avg_exam_score, 'completion_rate': s.completion_rate,
        'avg_sentiment': s.avg_sentiment, 'at_risk_count': s.at_risk_count,
        'heatmap': s.heatmap, 'item_analytics': s.item_analytics,
    }


@insights_bp.route('/item-analytics', methods=['GET'])
@teacher_required
def item_analytics():
    """Per-question difficulty (% correct) and discrimination signal."""
    from app.models import db, ExamResult, ExamQuestion
    exam_id = request.args.get('exam_id')
    if not exam_id:
        return jsonify({'error': 'exam_id required'}), 400
    questions = ExamQuestion.query.filter_by(exam_id=exam_id).all()
    results = ExamResult.query.filter_by(exam_id=exam_id).all()
    items = []
    for q in questions:
        # ExamResult.answers is expected to be JSON {question_id: {is_correct: bool, score: float}}
        seen = 0; correct = 0
        for r in results:
            ans = (getattr(r, 'answers', None) or {})
            if not isinstance(ans, dict):
                continue
            entry = ans.get(q.id) or ans.get(str(q.id))
            if entry is None:
                continue
            seen += 1
            if isinstance(entry, dict):
                if entry.get('is_correct'):
                    correct += 1
            elif isinstance(entry, (int, float)):
                if entry >= (q.points or 1) * 0.5:
                    correct += 1
        difficulty = round(correct / seen, 3) if seen else None
        items.append({
            'question_id': q.id,
            'prompt': (getattr(q, 'question_text', None) or '')[:160],
            'attempts': seen, 'correct': correct, 'p_correct': difficulty,
            'flag': 'too_easy' if (difficulty or 0) > 0.95 else
                    ('too_hard' if (difficulty or 1) < 0.20 else 'ok'),
        })
    return jsonify({'success': True, 'exam_id': exam_id, 'items': items})


# ---------- sentiment -----------------------------------------------------

@insights_bp.route('/sentiment', methods=['POST'])
@login_required
def sentiment_record():
    try:
        from app.models import db, SentimentSignal
        data = request.get_json(silent=True) or {}
        text = data.get('text') or ''
        lang = data.get('language', 'en')
        score, label = _score_sentiment(text, lang)
        s = SentimentSignal(
            user_id=session['user_id'],
            source=data.get('source', 'chat'),
            source_id=data.get('source_id'),
            text_excerpt=text[:1000],
            sentiment_label=label,
            sentiment_score=score,
            detected_emotions=data.get('emotions') or [],
            language=lang,
        )
        db.session.add(s); db.session.commit()
        return jsonify({'success': True, 'sentiment': label, 'score': score, 'id': s.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@insights_bp.route('/sentiment/summary', methods=['GET'])
@teacher_required
def sentiment_summary():
    from app.models import db, SentimentSignal
    days = int(request.args.get('days', 14))
    since = datetime.utcnow() - timedelta(days=days)
    rows = SentimentSignal.query.filter(SentimentSignal.created_at >= since).all()
    total = len(rows)
    pos = sum(1 for r in rows if r.sentiment_label == 'positive')
    neg = sum(1 for r in rows if r.sentiment_label == 'negative')
    neu = total - pos - neg
    avg = (sum((r.sentiment_score or 0) for r in rows) / total) if total else None
    return jsonify({
        'success': True,
        'window_days': days, 'sample_size': total,
        'positive': pos, 'neutral': neu, 'negative': neg,
        'average_score': round(avg, 3) if avg is not None else None,
    })


# ---------- at-risk -------------------------------------------------------

@insights_bp.route('/at-risk/scan', methods=['POST'])
@teacher_required
def atrisk_scan():
    """Heuristic at-risk model. Combines progress, exam scores, sentiment."""
    try:
        from app.models import (
            db, Enrollment, ExamResult, SentimentSignal, AtRiskAlert, LearnerProfile,
        )
        course_id = (request.get_json(silent=True) or {}).get('course_id')
        enr_q = Enrollment.query
        if course_id:
            enr_q = enr_q.filter_by(course_id=course_id)
        enrollments = enr_q.all()
        created = 0
        for e in enrollments:
            factors = []
            risk = 0.0
            progress = (getattr(e, 'progress_percent', 0) or 0)
            if progress < 30:
                f = 25; factors.append({'factor': 'low_progress', 'value': progress, 'weight': f}); risk += f
            # Recent exam performance
            recent = (ExamResult.query.filter_by(user_id=e.user_id)
                      .order_by(ExamResult.id.desc()).limit(3).all())
            if recent:
                avg = sum((r.score or 0) for r in recent) / len(recent)
                if avg < 60:
                    f = 30; factors.append({'factor': 'low_exam_avg', 'value': round(avg,1), 'weight': f}); risk += f
            # Negative sentiment
            recent_sent = (SentimentSignal.query.filter_by(user_id=e.user_id)
                           .order_by(SentimentSignal.created_at.desc()).limit(10).all())
            if recent_sent:
                avg_s = sum((s.sentiment_score or 0) for s in recent_sent) / len(recent_sent)
                if avg_s < -0.2:
                    f = 20; factors.append({'factor': 'negative_sentiment', 'value': round(avg_s,2), 'weight': f}); risk += f
            # Engagement
            p = LearnerProfile.query.filter_by(user_id=e.user_id).first()
            if p and (p.engagement_score or 0) < 30:
                f = 15; factors.append({'factor': 'low_engagement', 'value': p.engagement_score, 'weight': f}); risk += f
            # Stale
            last_active = p.last_active_at if p else None
            if last_active and (datetime.utcnow() - last_active).days > 14:
                f = 10; factors.append({'factor': 'inactive_14d', 'value': (datetime.utcnow()-last_active).days, 'weight': f}); risk += f

            if risk < 25:
                continue
            level = 'low'
            if risk >= 70: level = 'critical'
            elif risk >= 50: level = 'high'
            elif risk >= 35: level = 'medium'
            existing = AtRiskAlert.query.filter_by(user_id=e.user_id, course_id=e.course_id, status='open').first()
            if existing:
                existing.risk_score = round(risk, 1)
                existing.risk_level = level
                existing.factors = factors
                continue
            alert = AtRiskAlert(
                user_id=e.user_id, course_id=e.course_id,
                risk_score=round(risk, 1), risk_level=level, factors=factors,
                recommended_actions=[
                    'Schedule 1:1 with instructor',
                    'Recommend supportive learning path',
                    'Send encouragement message',
                ],
            )
            db.session.add(alert); created += 1
        db.session.commit()
        return jsonify({'success': True, 'alerts_created': created})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@insights_bp.route('/at-risk', methods=['GET'])
@teacher_required
def atrisk_list():
    from app.models import AtRiskAlert
    status = request.args.get('status', 'open')
    rows = AtRiskAlert.query.filter_by(status=status).order_by(AtRiskAlert.risk_score.desc()).limit(500).all()
    return jsonify({'success': True, 'count': len(rows), 'alerts': [{
        'id': a.id, 'user_id': a.user_id, 'course_id': a.course_id,
        'risk_score': a.risk_score, 'risk_level': a.risk_level,
        'factors': a.factors, 'recommended_actions': a.recommended_actions,
        'status': a.status,
        'created_at': a.created_at.isoformat() if a.created_at else None,
    } for a in rows]})


@insights_bp.route('/at-risk/<aid>/acknowledge', methods=['POST'])
@teacher_required
def atrisk_ack(aid):
    try:
        from app.models import db, AtRiskAlert
        a = AtRiskAlert.query.filter_by(id=aid).first()
        if not a:
            return jsonify({'error': 'not found'}), 404
        a.status = 'acknowledged'
        a.acknowledged_by = session['user_id']
        a.acknowledged_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@insights_bp.route('/at-risk/<aid>/resolve', methods=['POST'])
@teacher_required
def atrisk_resolve(aid):
    try:
        from app.models import db, AtRiskAlert
        a = AtRiskAlert.query.filter_by(id=aid).first()
        if not a:
            return jsonify({'error': 'not found'}), 404
        a.status = 'resolved'
        a.resolved_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ---------- exports -------------------------------------------------------

@insights_bp.route('/at-risk.csv', methods=['GET'])
@teacher_required
def atrisk_csv():
    """Export current at-risk alerts as CSV."""
    from app.models import AtRiskAlert, User, Course
    status = request.args.get('status', 'open')
    rows = AtRiskAlert.query.filter_by(status=status)\
        .order_by(AtRiskAlert.risk_score.desc()).limit(2000).all()
    user_cache = {u.id: u for u in User.query.filter(
        User.id.in_({r.user_id for r in rows})).all()} if rows else {}
    course_cache = {c.id: c for c in Course.query.filter(
        Course.id.in_({r.course_id for r in rows if r.course_id})).all()} if rows else {}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['alert_id', 'user_id', 'user_name', 'course_id', 'course_title',
                'risk_level', 'risk_score', 'status', 'top_factors',
                'recommended_actions', 'created_at'])
    for r in rows:
        u = user_cache.get(r.user_id); c = course_cache.get(r.course_id) if r.course_id else None
        factors = ', '.join((f.get('factor') or '') for f in (r.factors or []))[:300]
        actions = ' | '.join(r.recommended_actions or [])[:300]
        w.writerow(_csv_row([r.id, r.user_id, u.full_name if u else '',
                    r.course_id or '', c.title if c else '',
                    r.risk_level, r.risk_score, r.status, factors, actions,
                    r.created_at.isoformat() if r.created_at else '']))
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=at_risk_alerts.csv'})


@insights_bp.route('/cohort.csv', methods=['GET'])
@teacher_required
def cohort_csv():
    """Export latest cohort analytics snapshots as CSV."""
    from app.models import CohortAnalyticsSnapshot, Course
    course_id = request.args.get('course_id')
    q = CohortAnalyticsSnapshot.query
    if course_id:
        q = q.filter_by(course_id=course_id)
    rows = q.order_by(CohortAnalyticsSnapshot.captured_at.desc()).limit(2000).all()
    course_cache = {c.id: c for c in Course.query.filter(
        Course.id.in_({r.course_id for r in rows if r.course_id})).all()} if rows else {}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['snapshot_id', 'course_id', 'course_title', 'cohort_id',
                'learner_count', 'active_learner_count', 'avg_progress_percent',
                'avg_exam_score', 'completion_rate', 'avg_sentiment',
                'at_risk_count', 'captured_at'])
    for r in rows:
        c = course_cache.get(r.course_id) if r.course_id else None
        w.writerow(_csv_row([r.id, r.course_id or '', c.title if c else '',
                    r.cohort_id or '',
                    r.learner_count, r.active_learner_count,
                    r.avg_progress_percent, r.avg_exam_score,
                    r.completion_rate, r.avg_sentiment, r.at_risk_count,
                    r.captured_at.isoformat() if r.captured_at else '']))
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=cohort_analytics.csv'})


@insights_bp.route('/gradebook.csv', methods=['GET'])
@teacher_required
def gradebook_csv():
    """Export a gradebook (per-learner exam scores) as CSV."""
    from app.models import db, ExamResult, Exam, User, Course, Enrollment
    course_id = request.args.get('course_id')
    exam_q = ExamResult.query
    if course_id:
        exam_q = exam_q.join(Exam, Exam.id == ExamResult.exam_id)\
                       .filter(Exam.course_id == course_id)
    rows = exam_q.order_by(ExamResult.id.desc()).limit(10000).all()
    user_cache = {u.id: u for u in User.query.filter(
        User.id.in_({r.user_id for r in rows})).all()} if rows else {}
    exam_cache = {e.id: e for e in Exam.query.filter(
        Exam.id.in_({r.exam_id for r in rows})).all()} if rows else {}
    course_ids = {e.course_id for e in exam_cache.values() if e.course_id}
    course_cache = {c.id: c for c in Course.query.filter(
        Course.id.in_(course_ids)).all()} if course_ids else {}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['result_id', 'user_id', 'user_name', 'exam_id', 'exam_title',
                'course_id', 'course_title', 'score', 'submitted_at'])
    for r in rows:
        u = user_cache.get(r.user_id); e = exam_cache.get(r.exam_id)
        c = course_cache.get(e.course_id) if e and e.course_id else None
        w.writerow(_csv_row([r.id, r.user_id, u.full_name if u else '',
                    r.exam_id, e.title if e else '',
                    e.course_id if e else '', c.title if c else '',
                    r.score,
                    r.created_at.isoformat() if getattr(r, 'created_at', None) else '']))
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=gradebook.csv'})


@insights_bp.route('/reports/roi.csv', methods=['GET'])
@teacher_required
def roi_csv():
    from app.models import Enrollment, ExamResult, User, Course
    course_id = request.args.get('course_id')
    enr_q = Enrollment.query
    if course_id:
        enr_q = enr_q.filter_by(course_id=course_id)
    enrollments = enr_q.limit(5000).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['user_id', 'user_name', 'course_id', 'course_title', 'progress_percent',
                'certificate_issued', 'best_exam_score'])
    user_cache = {u.id: u for u in User.query.filter(
        User.id.in_({e.user_id for e in enrollments})).all()} if enrollments else {}
    course_cache = {c.id: c for c in Course.query.filter(
        Course.id.in_({e.course_id for e in enrollments})).all()} if enrollments else {}
    for e in enrollments:
        best = (ExamResult.query.filter_by(user_id=e.user_id)
                .order_by(ExamResult.score.desc()).first())
        u = user_cache.get(e.user_id); c = course_cache.get(e.course_id)
        w.writerow(_csv_row([e.user_id, u.full_name if u else '',
                    e.course_id, c.title if c else '',
                    getattr(e, 'progress_percent', 0) or 0,
                    'yes' if getattr(e, 'certificate_issued', False) else 'no',
                    best.score if best else '']))
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=roi_report.csv'})
