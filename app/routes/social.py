"""
SkillPilot v2 — Phase 5: Engagement, social learning, parent portal, live classrooms.

Additive blueprints:
  /api/v1/engagement/*  badges, XP, streaks, leaderboards
  /api/v1/social/*      forums, peer review, cohorts
  /api/v1/guardian/*    parent/guardian portal
  /api/v1/live/*        live virtual classrooms
"""
from datetime import datetime, date, timedelta
import secrets

from flask import Blueprint, jsonify, request, session

from app.utils.decorators import (
    login_required, teacher_required, admin_required, is_teacher,
)


engagement_bp = Blueprint('engagement_v2', __name__, url_prefix='/api/v1/engagement')
social_bp = Blueprint('social_v2', __name__, url_prefix='/api/v1/social')
guardian_bp = Blueprint('guardian_v2', __name__, url_prefix='/api/v1/guardian')
live_bp = Blueprint('live_v2', __name__, url_prefix='/api/v1/live')

_LIVE_PROVIDERS = {'zoom', 'teams', 'meet', 'jitsi'}


# ============== Engagement (badges / XP / streak / leaderboard) ============

@engagement_bp.route('/badges', methods=['GET'])
@login_required
def list_badges():
    from app.models import Badge
    rows = Badge.query.filter_by(is_active=True).all()
    return jsonify({'success': True, 'count': len(rows), 'badges': [{
        'id': b.id, 'code': b.code, 'name': b.name, 'name_ar': b.name_ar,
        'description': b.description, 'icon_url': b.icon_url,
        'category': b.category, 'xp_reward': b.xp_reward,
    } for b in rows]})


@engagement_bp.route('/badges', methods=['POST'])
@admin_required
def create_badge():
    try:
        from app.models import db, Badge
        data = request.get_json(silent=True) or {}
        if not data.get('code') or not data.get('name'):
            return jsonify({'error': 'code and name required'}), 400
        b = Badge(
            code=data['code'][:64], name=data['name'][:120],
            name_ar=data.get('name_ar'),
            description=data.get('description'),
            description_ar=data.get('description_ar'),
            icon_url=data.get('icon_url'),
            category=data.get('category', 'learning'),
            xp_reward=int(data.get('xp_reward') or 0),
            criteria=data.get('criteria') or {},
        )
        db.session.add(b); db.session.commit()
        return jsonify({'success': True, 'id': b.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@engagement_bp.route('/badges/award', methods=['POST'])
@teacher_required
def award_badge():
    try:
        from app.models import db, Badge, UserBadge, XPEvent
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id'); badge_code = data.get('badge_code')
        if not user_id or not badge_code:
            return jsonify({'error': 'user_id and badge_code required'}), 400
        b = Badge.query.filter_by(code=badge_code).first()
        if not b:
            return jsonify({'error': 'badge not found'}), 404
        existing = UserBadge.query.filter_by(user_id=user_id, badge_id=b.id).first()
        if existing:
            return jsonify({'success': True, 'already': True})
        ub = UserBadge(user_id=user_id, badge_id=b.id, awarded_for=data.get('reason'))
        db.session.add(ub)
        if b.xp_reward:
            db.session.add(XPEvent(user_id=user_id, amount=b.xp_reward,
                                   source='badge', source_id=b.id,
                                   note=f'badge:{b.code}'))
        db.session.commit()
        return jsonify({'success': True, 'badge': b.code, 'xp_added': b.xp_reward})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@engagement_bp.route('/me', methods=['GET'])
@login_required
def my_engagement():
    from app.models import db, UserBadge, XPEvent, LearnerProfile
    uid = session['user_id']
    badges = (UserBadge.query.filter_by(user_id=uid).all())
    xp_total = db.session.query(db.func.coalesce(db.func.sum(XPEvent.amount), 0)) \
                         .filter_by(user_id=uid).scalar() or 0
    profile = LearnerProfile.query.filter_by(user_id=uid).first()
    return jsonify({
        'success': True,
        'xp_total': int(xp_total),
        'streak_days': profile.streak_days if profile else 0,
        'badges': [{'code': ub.badge.code, 'name': ub.badge.name,
                    'awarded_at': ub.awarded_at.isoformat()} for ub in badges if ub.badge],
    })


@engagement_bp.route('/streak/checkin', methods=['POST'])
@login_required
def streak_checkin():
    try:
        from app.models import db, LearnerProfile
        uid = session['user_id']
        p = LearnerProfile.query.filter_by(user_id=uid).first()
        if not p:
            p = LearnerProfile(user_id=uid)
            db.session.add(p); db.session.flush()
        today = date.today()
        last = p.last_active_at.date() if p.last_active_at else None
        if last == today:
            pass  # already counted
        elif last == today - timedelta(days=1):
            p.streak_days = (p.streak_days or 0) + 1
        else:
            p.streak_days = 1
        p.last_active_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'streak_days': p.streak_days})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@engagement_bp.route('/leaderboard', methods=['GET'])
@login_required
def leaderboard():
    from app.models import db, XPEvent, User
    scope = request.args.get('scope', 'all')          # all|course|cohort
    limit = min(100, int(request.args.get('limit', 25)))
    q = (db.session.query(
            XPEvent.user_id,
            db.func.coalesce(db.func.sum(XPEvent.amount), 0).label('xp'))
         .group_by(XPEvent.user_id)
         .order_by(db.func.sum(XPEvent.amount).desc())
         .limit(limit))
    rows = q.all()
    user_ids = [r[0] for r in rows]
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}
    return jsonify({'success': True, 'scope': scope, 'leaderboard': [{
        'rank': i + 1, 'user_id': r[0],
        'name': (users.get(r[0]).full_name if users.get(r[0]) else None),
        'xp': int(r[1]),
    } for i, r in enumerate(rows)]})


# ============== Forums + Peer review + Cohorts =============================

@social_bp.route('/forums/threads', methods=['GET'])
@login_required
def forum_list_threads():
    from app.models import ForumThread
    course_id = request.args.get('course_id')
    q = ForumThread.query
    if course_id:
        q = q.filter_by(course_id=course_id)
    rows = q.order_by(ForumThread.pinned.desc(), ForumThread.updated_at.desc()).limit(200).all()
    return jsonify({'success': True, 'count': len(rows), 'threads': [{
        'id': t.id, 'course_id': t.course_id, 'title': t.title,
        'language': t.language, 'pinned': t.pinned, 'locked': t.locked,
        'post_count': t.post_count, 'author_id': t.author_id,
        'updated_at': t.updated_at.isoformat() if t.updated_at else None,
    } for t in rows]})


@social_bp.route('/forums/threads', methods=['POST'])
@login_required
def forum_create_thread():
    try:
        from app.models import db, ForumThread, ForumPost, XPEvent
        data = request.get_json(silent=True) or {}
        if not data.get('title') or not data.get('body'):
            return jsonify({'error': 'title and body required'}), 400
        t = ForumThread(
            course_id=data.get('course_id'),
            cohort_id=data.get('cohort_id'),
            author_id=session['user_id'],
            title=data['title'][:255],
            body=data['body'],
            language=data.get('language', 'en'),
        )
        db.session.add(t); db.session.flush()
        post = ForumPost(thread_id=t.id, author_id=session['user_id'], body=data['body'])
        db.session.add(post)
        t.post_count = 1
        db.session.add(XPEvent(user_id=session['user_id'], amount=5,
                               source='forum', source_id=t.id, note='thread_create'))
        db.session.commit()
        return jsonify({'success': True, 'id': t.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@social_bp.route('/forums/threads/<thread_id>/posts', methods=['GET'])
@login_required
def forum_list_posts(thread_id):
    from app.models import ForumPost
    rows = ForumPost.query.filter_by(thread_id=thread_id).order_by(ForumPost.created_at.asc()).all()
    return jsonify({'success': True, 'count': len(rows), 'posts': [{
        'id': p.id, 'author_id': p.author_id, 'body': p.body,
        'parent_post_id': p.parent_post_id, 'sentiment': p.sentiment,
        'created_at': p.created_at.isoformat() if p.created_at else None,
    } for p in rows]})


@social_bp.route('/forums/threads/<thread_id>/posts', methods=['POST'])
@login_required
def forum_create_post(thread_id):
    try:
        from app.models import db, ForumThread, ForumPost, XPEvent
        data = request.get_json(silent=True) or {}
        if not data.get('body'):
            return jsonify({'error': 'body required'}), 400
        t = ForumThread.query.filter_by(id=thread_id).first()
        if not t:
            return jsonify({'error': 'thread not found'}), 404
        if t.locked:
            return jsonify({'error': 'thread locked'}), 403
        p = ForumPost(thread_id=thread_id, author_id=session['user_id'],
                      body=data['body'], parent_post_id=data.get('parent_post_id'))
        db.session.add(p)
        t.post_count = (t.post_count or 0) + 1
        t.updated_at = datetime.utcnow()
        db.session.add(XPEvent(user_id=session['user_id'], amount=2,
                               source='forum', source_id=p.id, note='reply'))
        db.session.commit()
        return jsonify({'success': True, 'id': p.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@social_bp.route('/peer-reviews', methods=['POST'])
@login_required
def peer_review_create():
    try:
        from app.models import db, PeerReview, XPEvent
        data = request.get_json(silent=True) or {}
        sub_id = data.get('submission_id')
        if not sub_id:
            return jsonify({'error': 'submission_id required'}), 400
        rubric = data.get('rubric_scores') or {}
        overall = None
        if rubric:
            try:
                vals = [float(v) for v in rubric.values()]
                overall = round(sum(vals) / len(vals), 2) if vals else None
            except (TypeError, ValueError):
                return jsonify({'error': 'rubric_scores must be numeric'}), 400
        pr = PeerReview(
            submission_id=sub_id, reviewer_id=session['user_id'],
            rubric_scores=rubric, comment=data.get('comment'),
            overall_score=overall, status='completed',
            completed_at=datetime.utcnow(),
        )
        db.session.add(pr)
        db.session.add(XPEvent(user_id=session['user_id'], amount=8,
                               source='peer_review', source_id=pr.id))
        db.session.commit()
        return jsonify({'success': True, 'id': pr.id, 'overall_score': overall}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@social_bp.route('/peer-reviews', methods=['GET'])
@login_required
def peer_review_list():
    from app.models import PeerReview
    sub_id = request.args.get('submission_id')
    q = PeerReview.query
    if sub_id:
        q = q.filter_by(submission_id=sub_id)
    rows = q.order_by(PeerReview.created_at.desc()).limit(200).all()
    return jsonify({'success': True, 'count': len(rows), 'reviews': [{
        'id': r.id, 'submission_id': r.submission_id, 'reviewer_id': r.reviewer_id,
        'overall_score': r.overall_score, 'status': r.status,
        'comment': r.comment,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    } for r in rows]})


@social_bp.route('/cohorts', methods=['POST'])
@teacher_required
def cohort_create():
    try:
        from app.models import db, Cohort
        data = request.get_json(silent=True) or {}
        if not data.get('name'):
            return jsonify({'error': 'name required'}), 400
        c = Cohort(
            course_id=data.get('course_id'),
            name=data['name'][:255],
            name_ar=data.get('name_ar'),
            instructor_id=session['user_id'],
            capacity=data.get('capacity'),
        )
        db.session.add(c); db.session.commit()
        return jsonify({'success': True, 'id': c.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@social_bp.route('/cohorts', methods=['GET'])
@login_required
def cohort_list():
    from app.models import Cohort
    course_id = request.args.get('course_id')
    q = Cohort.query
    if course_id:
        q = q.filter_by(course_id=course_id)
    rows = q.order_by(Cohort.created_at.desc()).all()
    return jsonify({'success': True, 'count': len(rows), 'cohorts': [{
        'id': c.id, 'course_id': c.course_id, 'name': c.name,
        'instructor_id': c.instructor_id, 'capacity': c.capacity,
    } for c in rows]})


@social_bp.route('/cohorts/<cid>/members', methods=['POST'])
@teacher_required
def cohort_add_member(cid):
    try:
        from app.models import db, CohortMember
        data = request.get_json(silent=True) or {}
        uid = data.get('user_id')
        if not uid:
            return jsonify({'error': 'user_id required'}), 400
        m = CohortMember(cohort_id=cid, user_id=uid)
        db.session.add(m); db.session.commit()
        return jsonify({'success': True, 'id': m.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============== Guardian / Parent portal ===================================

@guardian_bp.route('/links', methods=['POST'])
@login_required
def guardian_link_create():
    """Guardian initiates a link request to a learner; learner approves."""
    try:
        from app.models import db, GuardianLink
        data = request.get_json(silent=True) or {}
        learner_id = data.get('learner_user_id')
        if not learner_id:
            return jsonify({'error': 'learner_user_id required'}), 400
        gl = GuardianLink(
            guardian_user_id=session['user_id'],
            learner_user_id=learner_id,
            relationship=data.get('relationship', 'parent'),
            consent_token=secrets.token_urlsafe(24),
            can_view_grades=bool(data.get('can_view_grades', True)),
            can_view_attendance=bool(data.get('can_view_attendance', True)),
            can_view_ethics=bool(data.get('can_view_ethics', True)),
            can_message_instructor=bool(data.get('can_message_instructor', False)),
        )
        db.session.add(gl); db.session.commit()
        return jsonify({'success': True, 'id': gl.id, 'consent_token': gl.consent_token}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@guardian_bp.route('/links/approve', methods=['POST'])
@login_required
def guardian_link_approve():
    try:
        from app.models import db, GuardianLink
        data = request.get_json(silent=True) or {}
        token = data.get('consent_token')
        if not token:
            return jsonify({'error': 'consent_token required'}), 400
        gl = GuardianLink.query.filter_by(consent_token=token).first()
        if not gl or gl.learner_user_id != session['user_id']:
            return jsonify({'error': 'invalid token'}), 404
        gl.status = 'active'
        gl.consent_granted_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@guardian_bp.route('/dashboard', methods=['GET'])
@login_required
def guardian_dashboard():
    """Returns aggregated read-only progress for all learners linked to this guardian."""
    from app.models import (
        GuardianLink, User, Enrollment, Attendance, Exam, ExamResult,
        LearnerEthicsProfile,
    )
    links = GuardianLink.query.filter_by(
        guardian_user_id=session['user_id'], status='active').all()
    children = []
    for gl in links:
        learner = User.query.filter_by(id=gl.learner_user_id).first()
        if not learner:
            continue
        enrollments = Enrollment.query.filter_by(user_id=learner.id).all() if gl.can_view_grades else []
        recent_attendance = []
        if gl.can_view_attendance:
            recent_attendance = (Attendance.query.filter_by(user_id=learner.id)
                                 .order_by(Attendance.created_at.desc()).limit(20).all()
                                 if hasattr(Attendance, 'created_at') else
                                 Attendance.query.filter_by(user_id=learner.id).limit(20).all())
        ethics = []
        if gl.can_view_ethics:
            ethics = LearnerEthicsProfile.query.filter_by(user_id=learner.id).all()
        children.append({
            'learner_id': learner.id,
            'name': learner.full_name,
            'enrollments': [{
                'course_id': e.course_id,
                'progress_percent': getattr(e, 'progress_percent', None),
                'certificate_issued': getattr(e, 'certificate_issued', False),
            } for e in enrollments],
            'attendance_count': len(recent_attendance),
            'ethics': [{
                'competency_id': p.competency_id, 'score': p.score,
            } for p in ethics],
            'permissions': {
                'grades': gl.can_view_grades,
                'attendance': gl.can_view_attendance,
                'ethics': gl.can_view_ethics,
                'message_instructor': gl.can_message_instructor,
            },
        })
    return jsonify({'success': True, 'children': children, 'count': len(children),
                    'parent_resources': [
                        {'title': 'Talking about AI ethics at home',
                         'language': 'en', 'url': '/static/resources/parent_ai_ethics_en.pdf'},
                        {'title': 'الحديث عن أخلاقيات الذكاء الاصطناعي في المنزل',
                         'language': 'ar', 'url': '/static/resources/parent_ai_ethics_ar.pdf'},
                    ]})


# ============== Live virtual classrooms ====================================

@live_bp.route('/sessions', methods=['POST'])
@teacher_required
def live_schedule():
    try:
        from app.models import db, LiveSession
        data = request.get_json(silent=True) or {}
        if not data.get('title') or not data.get('starts_at'):
            return jsonify({'error': 'title and starts_at required'}), 400
        provider = data.get('provider', 'jitsi')
        if provider not in _LIVE_PROVIDERS:
            return jsonify({'error': f'provider must be one of {sorted(_LIVE_PROVIDERS)}'}), 400
        try:
            starts = datetime.fromisoformat(data['starts_at'].replace('Z', '+00:00'))
        except Exception:
            return jsonify({'error': 'starts_at must be ISO-8601'}), 400
        ends = None
        if data.get('ends_at'):
            try:
                ends = datetime.fromisoformat(data['ends_at'].replace('Z', '+00:00'))
            except Exception:
                return jsonify({'error': 'ends_at must be ISO-8601'}), 400
        # Sensible default join URL for jitsi if none provided
        join_url = data.get('join_url')
        if not join_url and provider == 'jitsi':
            slug = secrets.token_urlsafe(8)
            join_url = f'https://meet.jit.si/SkillPilot-{slug}'
        s = LiveSession(
            course_id=data.get('course_id'),
            cohort_id=data.get('cohort_id'),
            instructor_id=session['user_id'],
            title=data['title'][:255], title_ar=data.get('title_ar'),
            provider=provider,
            join_url=join_url, host_url=data.get('host_url'),
            embed_url=data.get('embed_url') or join_url,
            starts_at=starts, ends_at=ends,
            duration_minutes=data.get('duration_minutes'),
            attached_lesson_id=data.get('attached_lesson_id'),
        )
        db.session.add(s); db.session.commit()
        return jsonify({'success': True, 'id': s.id, 'join_url': s.join_url}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@live_bp.route('/sessions', methods=['GET'])
@login_required
def live_list():
    from app.models import LiveSession
    course_id = request.args.get('course_id')
    upcoming = request.args.get('upcoming', '0') == '1'
    q = LiveSession.query
    if course_id:
        q = q.filter_by(course_id=course_id)
    if upcoming:
        q = q.filter(LiveSession.starts_at >= datetime.utcnow())
    rows = q.order_by(LiveSession.starts_at.asc()).limit(200).all()
    return jsonify({'success': True, 'count': len(rows), 'sessions': [{
        'id': s.id, 'course_id': s.course_id, 'cohort_id': s.cohort_id,
        'instructor_id': s.instructor_id, 'title': s.title, 'title_ar': s.title_ar,
        'provider': s.provider, 'join_url': s.join_url, 'embed_url': s.embed_url,
        'starts_at': s.starts_at.isoformat() if s.starts_at else None,
        'ends_at': s.ends_at.isoformat() if s.ends_at else None,
        'status': s.status, 'recording_url': s.recording_url,
    } for s in rows]})


@live_bp.route('/sessions/<sid>/join', methods=['POST'])
@login_required
def live_join(sid):
    try:
        from app.models import db, LiveSession, LiveAttendance
        s = LiveSession.query.filter_by(id=sid).first()
        if not s:
            return jsonify({'error': 'not found'}), 404
        att = LiveAttendance.query.filter_by(session_id=sid, user_id=session['user_id']).first()
        if not att:
            att = LiveAttendance(session_id=sid, user_id=session['user_id'],
                                 source='auto')
            db.session.add(att)
        else:
            att.joined_at = datetime.utcnow()
        if s.status == 'scheduled':
            s.status = 'live'
        db.session.commit()
        return jsonify({'success': True, 'join_url': s.join_url, 'embed_url': s.embed_url})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@live_bp.route('/sessions/<sid>/leave', methods=['POST'])
@login_required
def live_leave(sid):
    try:
        from app.models import db, LiveAttendance
        att = LiveAttendance.query.filter_by(session_id=sid, user_id=session['user_id']).first()
        if not att:
            return jsonify({'error': 'no attendance record'}), 404
        att.left_at = datetime.utcnow()
        if att.joined_at:
            att.duration_seconds = int((att.left_at - att.joined_at).total_seconds())
        db.session.commit()
        return jsonify({'success': True, 'duration_seconds': att.duration_seconds})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@live_bp.route('/sessions/<sid>/recording', methods=['POST'])
@teacher_required
def live_recording(sid):
    try:
        from app.models import db, LiveSession
        data = request.get_json(silent=True) or {}
        url = data.get('recording_url')
        if not url:
            return jsonify({'error': 'recording_url required'}), 400
        s = LiveSession.query.filter_by(id=sid).first()
        if not s:
            return jsonify({'error': 'not found'}), 404
        s.recording_url = url
        s.status = 'ended'
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@live_bp.route('/sessions/<sid>/attendance', methods=['GET'])
@teacher_required
def live_attendance(sid):
    from app.models import LiveAttendance
    rows = LiveAttendance.query.filter_by(session_id=sid).all()
    return jsonify({'success': True, 'count': len(rows), 'attendance': [{
        'user_id': a.user_id,
        'joined_at': a.joined_at.isoformat() if a.joined_at else None,
        'left_at': a.left_at.isoformat() if a.left_at else None,
        'duration_seconds': a.duration_seconds, 'source': a.source,
    } for a in rows]})
