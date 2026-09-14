"""
SkillPilot v2 — Personalization API (Phase 1 Foundation)

Provides the new `/api/v1/personalization/*` surface used by the
modern dashboard. All endpoints are additive; no existing route
or response shape is modified.

Endpoints:
  GET  /api/v1/personalization/profile           - current user's learner profile
  PUT  /api/v1/personalization/profile           - update profile (goals, prefs, a11y)
  GET  /api/v1/personalization/skills            - learner skill graph + mastery
  GET  /api/v1/personalization/paths             - learner's learning paths
  POST /api/v1/personalization/paths             - create a path (system or teacher)
  PATCH /api/v1/personalization/paths/<id>/steps/<step_id> - update step status
  GET  /api/v1/personalization/ethics            - EthicSense profile snapshot
  GET  /api/v1/personalization/home              - aggregated home payload
"""

from datetime import datetime

from flask import Blueprint, jsonify, request, session

from app.utils.decorators import login_required

personalization_bp = Blueprint(
    'personalization', __name__, url_prefix='/api/v1/personalization'
)

# Allowed enum values — used for strict request validation
_ALLOWED_DIFFICULTY = {'beginner', 'intermediate', 'advanced', 'adaptive'}
_ALLOWED_LANG = {'en', 'ar'}
_ALLOWED_MODALITIES = {'video', 'reading', 'interactive', 'avatar', 'audio'}
_ALLOWED_STEP_TYPES = {
    'course', 'material', 'exam', 'survey',
    'external', 'reflection', 'ethics_scenario',
}
_ALLOWED_STEP_STATUS = {'pending', 'in_progress', 'completed', 'skipped'}
_ALLOWED_PATH_GENERATED_BY = {'system', 'teacher', 'ai'}


# ---------- helpers ---------------------------------------------------------

def _get_or_create_profile(user_id):
    from app.models import db, LearnerProfile
    profile = LearnerProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = LearnerProfile(user_id=user_id)
        db.session.add(profile)
        db.session.commit()
    return profile


def _profile_to_dict(p):
    return {
        'id': p.id,
        'user_id': p.user_id,
        'primary_goal': p.primary_goal,
        'primary_goal_ar': p.primary_goal_ar,
        'target_role': p.target_role,
        'interests': p.interests or [],
        'preferred_language': p.preferred_language,
        'preferred_difficulty': p.preferred_difficulty,
        'preferred_modalities': p.preferred_modalities or [],
        'daily_study_minutes': p.daily_study_minutes,
        'timezone': p.timezone,
        'accessibility': {
            'high_contrast': p.high_contrast,
            'dyslexia_mode': p.dyslexia_mode,
            'text_to_speech': p.text_to_speech,
            'reduce_motion': p.reduce_motion,
            'font_scale': p.font_scale,
        },
        'engagement': {
            'engagement_score': p.engagement_score,
            'streak_days': p.streak_days,
            'last_active_at': p.last_active_at.isoformat() if p.last_active_at else None,
        },
        'ethics': {
            'overall_score': p.ethics_overall_score,
            'last_assessed_at': p.ethics_last_assessed_at.isoformat()
            if p.ethics_last_assessed_at else None,
        },
        'onboarding_completed': p.onboarding_completed,
    }


# ---------- profile --------------------------------------------------------

@personalization_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    try:
        profile = _get_or_create_profile(session['user_id'])
        return jsonify({'success': True, 'profile': _profile_to_dict(profile)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@personalization_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    try:
        from app.models import db
        profile = _get_or_create_profile(session['user_id'])
        data = request.get_json(silent=True) or {}

        # ---- validation -------------------------------------------------
        if 'preferred_language' in data and data['preferred_language'] not in _ALLOWED_LANG:
            return jsonify({'error': 'preferred_language must be one of: '
                            + ', '.join(sorted(_ALLOWED_LANG))}), 400
        if ('preferred_difficulty' in data
                and data['preferred_difficulty'] not in _ALLOWED_DIFFICULTY):
            return jsonify({'error': 'preferred_difficulty must be one of: '
                            + ', '.join(sorted(_ALLOWED_DIFFICULTY))}), 400
        if 'daily_study_minutes' in data:
            try:
                m = int(data['daily_study_minutes'])
                if not 0 <= m <= 720:
                    raise ValueError()
                data['daily_study_minutes'] = m
            except (TypeError, ValueError):
                return jsonify({'error': 'daily_study_minutes must be an integer 0..720'}), 400
        for k in ('interests', 'preferred_modalities'):
            if k in data and not isinstance(data[k], list):
                return jsonify({'error': f'{k} must be a list'}), 400
        if 'preferred_modalities' in data:
            bad = [m for m in data['preferred_modalities']
                   if m not in _ALLOWED_MODALITIES]
            if bad:
                return jsonify({'error': f'invalid modalities: {bad}'}), 400

        # ---- apply ------------------------------------------------------
        scalar_fields = (
            'primary_goal', 'primary_goal_ar', 'target_role',
            'preferred_language', 'preferred_difficulty', 'timezone',
            'daily_study_minutes',
        )
        for f in scalar_fields:
            if f in data:
                setattr(profile, f, data[f])

        if 'interests' in data:
            profile.interests = [str(x)[:80] for x in data['interests']][:50]
        if 'preferred_modalities' in data:
            profile.preferred_modalities = list(data['preferred_modalities'])

        a11y = data.get('accessibility') or {}
        for f in ('high_contrast', 'dyslexia_mode', 'text_to_speech', 'reduce_motion'):
            if f in a11y:
                setattr(profile, f, bool(a11y[f]))
        if 'font_scale' in a11y:
            try:
                profile.font_scale = max(0.8, min(1.6, float(a11y['font_scale'])))
            except (TypeError, ValueError):
                pass

        if data.get('mark_onboarded'):
            profile.onboarding_completed = True
            profile.onboarded_at = datetime.utcnow()

        db.session.commit()
        return jsonify({'success': True, 'profile': _profile_to_dict(profile)})
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ---------- skills ---------------------------------------------------------

@personalization_bp.route('/skills', methods=['GET'])
@login_required
def get_skills():
    try:
        from app.models import LearnerSkill, Skill

        rows = (
            LearnerSkill.query
            .filter_by(user_id=session['user_id'])
            .all()
        )
        skills = []
        for ls in rows:
            s = ls.skill
            if not s:
                continue
            level_max = max(1, s.level_max or 5)
            skills.append({
                'id': ls.id,
                'skill_id': s.id,
                'code': s.code,
                'name': s.name,
                'name_ar': s.name_ar,
                'category': s.category,
                'domain': s.domain,
                'level': ls.level,
                'level_max': level_max,
                'mastery_percent': round(100.0 * ls.level / level_max, 1),
                'target_level': ls.target_level,
                'confidence': ls.confidence,
                'source': ls.source,
            })
        skills.sort(key=lambda x: (-(x['mastery_percent'] or 0), x['name'] or ''))
        return jsonify({'success': True, 'skills': skills, 'count': len(skills)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------- learning paths -------------------------------------------------

def _step_to_dict(step):
    return {
        'id': step.id,
        'order_index': step.order_index,
        'step_type': step.step_type,
        'target_id': step.target_id,
        'title': step.title,
        'title_ar': step.title_ar,
        'estimated_minutes': step.estimated_minutes,
        'primary_skill_code': step.primary_skill_code,
        'rationale': step.rationale,
        'status': step.status,
        'started_at': step.started_at.isoformat() if step.started_at else None,
        'completed_at': step.completed_at.isoformat() if step.completed_at else None,
    }


def _path_to_dict(path, include_steps=True):
    payload = {
        'id': path.id,
        'title': path.title,
        'title_ar': path.title_ar,
        'description': path.description,
        'description_ar': path.description_ar,
        'goal': path.goal,
        'target_skill_codes': path.target_skill_codes or [],
        'estimated_minutes': path.estimated_minutes,
        'difficulty': path.difficulty,
        'status': path.status,
        'progress_percent': path.progress_percent,
        'generated_by': path.generated_by,
        'created_at': path.created_at.isoformat() if path.created_at else None,
    }
    if include_steps:
        payload['steps'] = [_step_to_dict(s) for s in path.steps]
    return payload


@personalization_bp.route('/paths', methods=['GET'])
@login_required
def list_paths():
    try:
        from app.models import LearningPath
        status = request.args.get('status')
        q = LearningPath.query.filter_by(user_id=session['user_id'])
        if status:
            q = q.filter_by(status=status)
        paths = q.order_by(LearningPath.created_at.desc()).all()
        return jsonify({
            'success': True,
            'paths': [_path_to_dict(p) for p in paths],
            'count': len(paths),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@personalization_bp.route('/paths', methods=['POST'])
@login_required
def create_path():
    try:
        from app.models import db, LearningPath, PathStep
        data = request.get_json(silent=True) or {}
        if not data.get('title') or not isinstance(data['title'], str):
            return jsonify({'error': 'title (string) is required'}), 400

        difficulty = data.get('difficulty', 'adaptive')
        if difficulty not in _ALLOWED_DIFFICULTY:
            return jsonify({'error': 'difficulty must be one of: '
                            + ', '.join(sorted(_ALLOWED_DIFFICULTY))}), 400

        generated_by = data.get('generated_by', 'system')
        if generated_by not in _ALLOWED_PATH_GENERATED_BY:
            return jsonify({'error': 'generated_by must be one of: '
                            + ', '.join(sorted(_ALLOWED_PATH_GENERATED_BY))}), 400

        target_codes = data.get('target_skill_codes') or []
        if not isinstance(target_codes, list):
            return jsonify({'error': 'target_skill_codes must be a list'}), 400

        steps_payload = data.get('steps') or []
        if not isinstance(steps_payload, list):
            return jsonify({'error': 'steps must be a list'}), 400
        for i, step in enumerate(steps_payload):
            if not isinstance(step, dict):
                return jsonify({'error': f'steps[{i}] must be an object'}), 400
            st = step.get('step_type', 'material')
            if st not in _ALLOWED_STEP_TYPES:
                return jsonify({'error': f'steps[{i}].step_type invalid; allowed: '
                                + ', '.join(sorted(_ALLOWED_STEP_TYPES))}), 400

        path = LearningPath(
            user_id=session['user_id'],
            title=data['title'][:255],
            title_ar=data.get('title_ar'),
            description=data.get('description'),
            description_ar=data.get('description_ar'),
            goal=data.get('goal'),
            target_skill_codes=[str(c)[:64] for c in target_codes][:100],
            estimated_minutes=data.get('estimated_minutes'),
            difficulty=difficulty,
            generated_by=generated_by,
            generator_model=data.get('generator_model'),
        )
        db.session.add(path)
        db.session.flush()

        for idx, step in enumerate(steps_payload):
            db.session.add(PathStep(
                path_id=path.id,
                order_index=step.get('order_index', idx),
                step_type=step.get('step_type', 'material'),
                target_id=step.get('target_id'),
                title=step.get('title'),
                title_ar=step.get('title_ar'),
                estimated_minutes=step.get('estimated_minutes'),
                primary_skill_code=step.get('primary_skill_code'),
                rationale=step.get('rationale'),
            ))

        db.session.commit()
        return jsonify({'success': True, 'path': _path_to_dict(path)}), 201
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@personalization_bp.route('/paths/<path_id>/steps/<step_id>', methods=['PATCH'])
@login_required
def update_step(path_id, step_id):
    try:
        from app.models import db, LearningPath, PathStep
        path = LearningPath.query.filter_by(
            id=path_id, user_id=session['user_id']
        ).first()
        if not path:
            return jsonify({'error': 'Path not found'}), 404

        step = PathStep.query.filter_by(id=step_id, path_id=path_id).first()
        if not step:
            return jsonify({'error': 'Step not found'}), 404

        data = request.get_json(silent=True) or {}
        new_status = data.get('status')
        if new_status is None or new_status not in _ALLOWED_STEP_STATUS:
            return jsonify({'error': 'status must be one of: '
                            + ', '.join(sorted(_ALLOWED_STEP_STATUS))}), 400

        step.status = new_status
        now = datetime.utcnow()
        if new_status == 'in_progress' and not step.started_at:
            step.started_at = now
        if new_status == 'completed':
            step.completed_at = now

        # recompute path progress
        all_steps = path.steps.all()
        if all_steps:
            done = sum(1 for s in all_steps if s.status in ('completed', 'skipped'))
            path.progress_percent = round(100.0 * done / len(all_steps), 1)
            if done == len(all_steps):
                path.status = 'completed'
                path.completed_at = datetime.utcnow()

        db.session.commit()
        return jsonify({'success': True, 'step': _step_to_dict(step),
                        'path_progress': path.progress_percent})
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ---------- ethics snapshot ------------------------------------------------

@personalization_bp.route('/ethics', methods=['GET'])
@login_required
def get_ethics():
    try:
        from app.models import LearnerEthicsProfile, EthicsCompetency
        rows = LearnerEthicsProfile.query.filter_by(user_id=session['user_id']).all()
        items = []
        total = 0.0
        for r in rows:
            c = r.competency
            if not c:
                continue
            items.append({
                'competency_code': c.code,
                'competency_name': c.name,
                'competency_name_ar': c.name_ar,
                'pillar': c.pillar,
                'score': r.score,
                'confidence': r.confidence,
                'evidence_count': r.evidence_count,
            })
            total += (r.score or 0)
        overall = round(total / len(items), 1) if items else None
        return jsonify({
            'success': True,
            'overall_score': overall,
            'competencies': items,
            'catalog_size': EthicsCompetency.query.filter_by(is_active=True).count(),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------- adaptive progress (skill deltas + next step) -------------------

@personalization_bp.route('/adaptive-progress', methods=['GET'])
@login_required
def get_adaptive_progress():
    """Recent LearnerSkill level changes + next pending PathStep.

    Powers the learner-facing "Adaptive progress" dashboard widget so the
    learner can see, at a glance, which skills grew after recent tutor
    sessions / material completions and which step the adaptive engine now
    wants them to take next.

    Query params:
        days (int, default 7): window for recent skill deltas (1..90)
        course_id (str, optional): scope deltas to one course
        limit (int, default 5): max delta rows returned (1..20)
    """
    try:
        from datetime import timedelta
        from app.models import (
            LearnerSkill, LearnerSkillHistory, Skill,
            LearningPath, PathStep,
        )

        user_id = session['user_id']

        try:
            days = max(1, min(90, int(request.args.get('days', 7))))
        except (TypeError, ValueError):
            days = 7
        try:
            limit = max(1, min(20, int(request.args.get('limit', 5))))
        except (TypeError, ValueError):
            limit = 5
        course_id = request.args.get('course_id') or None

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Aggregate all history rows in window into per-skill deltas.
        hist_q = (LearnerSkillHistory.query
                  .filter(LearnerSkillHistory.user_id == user_id,
                          LearnerSkillHistory.created_at >= cutoff))
        if course_id:
            hist_q = hist_q.filter(LearnerSkillHistory.course_id == course_id)
        rows = hist_q.order_by(LearnerSkillHistory.created_at.asc()).all()

        per_skill = {}
        for r in rows:
            slot = per_skill.setdefault(r.skill_id, {
                'skill_id': r.skill_id,
                'first_previous_level': r.previous_level or 0,
                'latest_new_level': r.new_level or 0,
                'level_max': r.level_max or 5,
                'last_changed_at': r.created_at,
                'last_source': r.source,
                'last_course_id': r.course_id,
                'change_count': 0,
            })
            slot['latest_new_level'] = r.new_level or 0
            slot['level_max'] = r.level_max or slot['level_max']
            slot['last_changed_at'] = r.created_at
            slot['last_source'] = r.source
            slot['last_course_id'] = r.course_id
            slot['change_count'] += 1

        deltas = []
        for sid, slot in per_skill.items():
            prev = slot['first_previous_level']
            curr = slot['latest_new_level']
            delta = curr - prev
            if delta == 0:
                continue
            skill = Skill.query.get(sid)
            if not skill:
                continue
            level_max = max(1, slot['level_max'])
            deltas.append({
                'skill_id': sid,
                'skill_code': skill.code,
                'skill_name': skill.name,
                'skill_name_ar': skill.name_ar,
                'previous_level': prev,
                'new_level': curr,
                'delta': delta,
                'level_max': level_max,
                'previous_mastery_percent': round(100.0 * prev / level_max, 1),
                'new_mastery_percent': round(100.0 * curr / level_max, 1),
                'last_changed_at': slot['last_changed_at'].isoformat()
                if slot['last_changed_at'] else None,
                'last_source': slot['last_source'],
                'last_course_id': slot['last_course_id'],
                'change_count': slot['change_count'],
            })
        # Surface biggest gains first; ties broken by most recent change
        # (descending timestamp — newer first).
        def _sort_key(d):
            ts = d.get('last_changed_at') or ''
            # Negate via a tuple where the second element sorts strings
            # in reverse using Python's stable sort: do an initial pass
            # by timestamp desc, then by -delta asc.
            return (-d['delta'], ts)
        # Two-pass stable sort: newest first, then by largest delta.
        deltas.sort(key=lambda d: d.get('last_changed_at') or '', reverse=True)
        deltas.sort(key=lambda d: -d['delta'])
        gained = [d for d in deltas if d['delta'] > 0][:limit]
        lost = [d for d in deltas if d['delta'] < 0]

        # Top current skills snapshot for context.
        top_rows = (LearnerSkill.query
                    .filter_by(user_id=user_id)
                    .order_by(LearnerSkill.level.desc())
                    .limit(5).all())
        top_skills = []
        for ls in top_rows:
            s = ls.skill
            if not s:
                continue
            lm = max(1, s.level_max or 5)
            top_skills.append({
                'code': s.code,
                'name': s.name,
                'level': ls.level or 0,
                'level_max': lm,
                'mastery_percent': round(100.0 * (ls.level or 0) / lm, 1),
            })

        # Next recommended PathStep after the most recent rerank.
        path_q = LearningPath.query.filter_by(user_id=user_id, status='active')
        active_path = path_q.order_by(LearningPath.updated_at.desc()).first()
        next_step = None
        if active_path:
            step = (PathStep.query
                    .filter(PathStep.path_id == active_path.id,
                            PathStep.status.in_(('pending', 'in_progress')))
                    .order_by(PathStep.order_index.asc())
                    .first())
            if step:
                next_step = {
                    'path_id': active_path.id,
                    'path_title': active_path.title,
                    'step_id': step.id,
                    'order_index': step.order_index,
                    'step_type': step.step_type,
                    'title': step.title,
                    'title_ar': step.title_ar,
                    'estimated_minutes': step.estimated_minutes,
                    'primary_skill_code': step.primary_skill_code,
                    'rationale': step.rationale,
                    'status': step.status,
                }

        return jsonify({
            'success': True,
            'window_days': days,
            'course_id': course_id,
            'gained_skills': gained,
            'declined_skills': lost,
            'top_skills': top_skills,
            'next_step': next_step,
            'has_history': bool(rows),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------- aggregated home ------------------------------------------------

@personalization_bp.route('/home', methods=['GET'])
@login_required
def get_home():
    """Single payload powering the modern personalized home view."""
    try:
        from app.models import LearningPath, LearnerSkill, LearnerEthicsProfile
        user_id = session['user_id']
        profile = _get_or_create_profile(user_id)

        active_path = (
            LearningPath.query
            .filter_by(user_id=user_id, status='active')
            .order_by(LearningPath.updated_at.desc())
            .first()
        )

        top_skills = (
            LearnerSkill.query
            .filter_by(user_id=user_id)
            .order_by(LearnerSkill.level.desc())
            .limit(6).all()
        )

        ethics_count = LearnerEthicsProfile.query.filter_by(user_id=user_id).count()

        return jsonify({
            'success': True,
            'profile': _profile_to_dict(profile),
            'active_path': _path_to_dict(active_path) if active_path else None,
            'top_skills': [
                {
                    'code': ls.skill.code if ls.skill else None,
                    'name': ls.skill.name if ls.skill else None,
                    'name_ar': ls.skill.name_ar if ls.skill else None,
                    'level': ls.level,
                    'level_max': (ls.skill.level_max if ls.skill else 5) or 5,
                }
                for ls in top_skills if ls.skill
            ],
            'ethics_tracked': ethics_count,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
