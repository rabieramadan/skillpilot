"""
SkillPilot v2 — Phase 2: Adaptive AI Tutor API.

Provides `/api/v1/tutor/*` endpoints that turn the personalization data
foundation (LearnerProfile / Skill / LearnerSkill / LearningPath /
PathStep) plus the existing course materials into a real adaptive tutor:

  GET  /api/v1/tutor/context?course_id=...
       → returns the grounding context the tutor will use (course +
         weeks + materials + learner skill levels + weak topics)

  POST /api/v1/tutor/chat
       → course-aware chat reply scoped to the active course's
         materials, the learner's level and weak topics. Routes the
         actual generation through the existing multi-provider
         AIService so OpenAI/Claude/Gemini/Grok/DeepSeek/Perplexity/
         Bedrock all keep working unchanged.

  POST /api/v1/tutor/avatar
       → optional HeyGen avatar instructor video for a tutor reply.

  POST /api/v1/tutor/recompute
       → re-runs the adaptive engine: recomputes LearnerSkill levels
         and re-ranks PathSteps so weak skills surface first.

These endpoints are purely additive — no existing route, payload or
response shape is modified.
"""

import re

from flask import Blueprint, jsonify, request, session

from app.utils.decorators import login_required
from app.services.ai_service import AIService
from app.services.recommendation_engine import (
    RecommendationEngine, AdaptiveEngine, trigger_adaptive_recompute,
)


tutor_bp = Blueprint('tutor_v1', __name__, url_prefix='/api/v1/tutor')


# --- helpers ---------------------------------------------------------------

def _user_can_access_course(user_id: str, course_id: str) -> bool:
    """Allow students enrolled in the course, plus staff roles."""
    role = (session.get('role') or 'student').lower().replace(' ', '_')
    if role in ('super_admin', 'superadmin', 'admin', 'institution_admin',
                'instructor', 'teacher'):
        return True
    try:
        from app.models import Enrollment
        return Enrollment.query.filter(
            Enrollment.user_id == user_id,
            Enrollment.course_id == course_id,
            Enrollment.status.in_(['active', 'approved']),
        ).first() is not None
    except Exception:
        return False


def _build_course_context(course_id: str, material_ids=None):
    """Pull a compact, JSON-serializable snapshot of the course materials."""
    from app.models import Course, CourseWeek, WeekMaterial

    course = Course.query.get(course_id)
    if not course:
        return None

    weeks_payload = []
    weeks = (CourseWeek.query
             .filter_by(course_id=course_id)
             .order_by(CourseWeek.week_number).all())
    for w in weeks:
        mats_q = WeekMaterial.query.filter_by(week_id=w.id)
        if material_ids:
            mats_q = mats_q.filter(WeekMaterial.id.in_(material_ids))
        mats = mats_q.order_by(WeekMaterial.order_index).all()
        if material_ids and not mats:
            continue
        weeks_payload.append({
            'week_number': w.week_number,
            'title': w.title,
            'materials': [{
                'id': m.id,
                'title': m.title,
                'description': (m.description or '')[:300],
                'material_type': m.material_type,
                'difficulty_level': m.difficulty_level,
                'topics': m.topics or [],
            } for m in mats],
        })

    return {
        'id': course.id,
        'code': course.code,
        'title': course.title,
        'description': course.description,
        'weeks': weeks_payload,
    }


def _build_learner_context(user_id: str, course_id: str):
    """Pull the per-learner snapshot used to calibrate tutor difficulty."""
    from app.models import LearnerProfile, LearnerSkill, Skill, User

    user = User.query.get(user_id)
    profile = LearnerProfile.query.filter_by(user_id=user_id).first()

    perf = RecommendationEngine(user_id, course_id).analyze_performance()

    skill_rows = (LearnerSkill.query
                  .filter_by(user_id=user_id)
                  .order_by(LearnerSkill.updated_at.desc())
                  .limit(25).all())
    skill_levels = []
    for ls in skill_rows:
        sk = ls.skill or Skill.query.get(ls.skill_id)
        if not sk:
            continue
        skill_levels.append({
            'code': sk.code,
            'name': sk.name,
            'level': ls.level or 0,
            'level_max': sk.level_max or 5,
            'confidence': ls.confidence or 0.0,
        })

    return {
        'display_name': (user.full_name if user and hasattr(user, 'full_name')
                         else (user.email if user else 'Learner')),
        'preferred_difficulty': (profile.preferred_difficulty
                                 if profile else 'adaptive'),
        'primary_goal': profile.primary_goal if profile else None,
        'overall_score': perf.get('overall_score'),
        'weak_topics': perf.get('weaknesses') or [],
        'strong_topics': perf.get('strengths') or [],
        'skill_levels': skill_levels,
    }


def _resolve_api_key(provider: str):
    """Resolve provider key via env -> ApiCredential (same as /api/chat)."""
    p = (provider or '').lower()
    try:
        from app.utils.api_key_helper import get_api_key
        # Map dalle -> openai for key sharing.
        lookup = 'openai' if p == 'dalle' else p
        key = get_api_key(lookup)
        if key:
            return key
    except Exception:
        pass
    # Fallback: Config env vars (covers bedrock + any provider not in helper map).
    try:
        from config.config import Config
        config = Config()
        if p == 'dalle':
            return config.OPENAI_API_KEY
        if p in ('bedrock', 'llama_bedrock', 'mistral_bedrock',
                 'amazon_nova', 'cohere_bedrock', 'ai21_bedrock',
                 'stable_diffusion'):
            return config.BEDROCK_API_KEY
        return getattr(config, f'{p.upper()}_API_KEY', None)
    except Exception:
        return None


_CITATION_RE = re.compile(r'\[\[\s*CITATIONS\s*:\s*([^\]]*)\]\]', re.IGNORECASE)


def _extract_citations(reply_text: str, course_ctx: dict):
    """Pull the [[CITATIONS: ...]] marker (if any) from the model reply.

    Returns (clean_text, citations_list). Falls back to scanning material
    titles in the reply when the model omits the marker. Each citation is
    a dict {id, title, week_number, week_title, url}.
    """
    if not reply_text:
        return reply_text, []

    # Build lookup of valid materials in the grounded course context.
    materials_by_id = {}
    for w in course_ctx.get('weeks') or []:
        for m in w.get('materials') or []:
            materials_by_id[str(m.get('id'))] = {
                'week_number': w.get('week_number'),
                'week_title': w.get('title'),
                'title': m.get('title'),
            }

    cited_ids = []
    clean_text = reply_text

    match = _CITATION_RE.search(reply_text)
    if match:
        clean_text = _CITATION_RE.sub('', reply_text).rstrip()
        raw = match.group(1).strip()
        if raw and raw.lower() != 'none':
            for tok in re.split(r'[\s,;]+', raw):
                tok = tok.strip().strip('"\'')
                if tok and tok in materials_by_id and tok not in cited_ids:
                    cited_ids.append(tok)

    # Fallback: scan reply text for material titles when no IDs were found.
    if not cited_ids:
        lowered = clean_text.lower()
        for mid, info in materials_by_id.items():
            title = (info.get('title') or '').strip()
            if len(title) >= 4 and title.lower() in lowered and mid not in cited_ids:
                cited_ids.append(mid)

    citations = []
    for mid in cited_ids[:8]:
        info = materials_by_id[mid]
        citations.append({
            'id': mid,
            'title': info.get('title'),
            'week_number': info.get('week_number'),
            'week_title': info.get('week_title'),
            'url': _material_url(mid, course_ctx.get('id')),
        })
    return clean_text, citations


def _material_url(material_id: str, course_id: str):
    """Best-effort link to the material for the student UI."""
    try:
        from app.models import WeekMaterial, CourseWeek
        m = WeekMaterial.query.get(material_id)
        if not m:
            return None
        if m.external_url:
            return m.external_url
        if m.file_url:
            return m.file_url
        # Fall back to the class materials page anchored at this material.
        week = CourseWeek.query.get(m.week_id) if m.week_id else None
        cid = course_id or (week.course_id if week else None)
        if cid:
            return f"/student/class/{cid}/materials#material-{material_id}"
    except Exception:
        pass
    return None


# --- endpoints -------------------------------------------------------------

@tutor_bp.route('/context', methods=['GET'])
@login_required
def get_context():
    """Return the exact grounding payload the tutor will use."""
    course_id = request.args.get('course_id')
    if not course_id:
        return jsonify({'error': 'course_id is required'}), 400
    user_id = session['user_id']
    if not _user_can_access_course(user_id, course_id):
        return jsonify({'error': 'Not enrolled in this course'}), 403
    try:
        course = _build_course_context(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        learner = _build_learner_context(user_id, course_id)
        return jsonify({'success': True,
                        'course': course,
                        'learner': learner})
    except Exception as e:
        import logging; logging.exception('tutor error'); return jsonify({'error': 'Internal tutor error'}), 500


@tutor_bp.route('/chat', methods=['POST'])
@login_required
def tutor_chat():
    """Course-aware adaptive chat reply.

    JSON body:
        course_id: str (required)
        message: str (required)
        provider: str (default 'openai')
        version: str (optional model id)
        material_ids: list[str] (optional — restrict grounding)
        conversation_history: list[{role,content}] (optional)
        language: 'en'|'ar' (default 'en')
        want_avatar: bool (default false) — if true and HeyGen is
                     configured, also kick off an avatar video for the
                     tutor's reply and return its video_id.
    """
    try:
        body = request.get_json(silent=True) or {}
        course_id = body.get('course_id')
        message = (body.get('message') or '').strip()
        if not course_id or not message:
            return jsonify({'error': 'course_id and message are required'}), 400

        user_id = session['user_id']
        if not _user_can_access_course(user_id, course_id):
            return jsonify({'error': 'Not enrolled in this course'}), 403

        provider = (body.get('provider') or 'openai').lower()
        version = body.get('version')
        language = (body.get('language') or 'en')[:2]
        history = body.get('conversation_history') or []
        material_ids = body.get('material_ids') or None
        want_avatar = bool(body.get('want_avatar'))

        course_ctx = _build_course_context(course_id, material_ids)
        if not course_ctx:
            return jsonify({'error': 'Course not found'}), 404
        learner_ctx = _build_learner_context(user_id, course_id)

        system_prompt = AIService.build_tutor_system_prompt(
            course_ctx, learner_ctx, language=language,
        )

        api_key = _resolve_api_key(provider)
        if not api_key:
            return jsonify({
                'error': f'{provider} is not configured on the server.'
            }), 400

        ai = AIService()
        reply = ai.chat(
            provider=provider,
            message=message,
            api_key=api_key,
            files=None,
            conversation_history=history,
            version=version,
            language=language,
            system_prompt=system_prompt,
        )

        # Extract citation marker (or fall back to title scan) so the UI
        # can render a "Sources from your course" panel.
        if reply.get('text') and not reply.get('error'):
            clean_text, citations = _extract_citations(reply['text'], course_ctx)
            reply['text'] = clean_text
            reply['citations'] = citations

        # Optional avatar instructor — re-uses existing HeyGen integration.
        if want_avatar and reply.get('text') and not reply.get('error'):
            try:
                heygen_key = _resolve_api_key('heygen')
                if heygen_key:
                    avatar = ai._generate_heygen_video(
                        message=reply['text'],
                        api_key=heygen_key,
                        language=language,
                    )
                    if not avatar.get('error'):
                        reply['avatar'] = {
                            'video_id': avatar.get('video_id'),
                            'status': avatar.get('status'),
                            'status_url': (
                                f"/api/heygen/status/{avatar.get('video_id')}"
                                if avatar.get('video_id') else None
                            ),
                        }
            except Exception as _e:
                reply['avatar_error'] = str(_e)

        # Fire-and-forget adaptive recompute so the learner's "Adaptive
        # progress" widget reflects the tutor session without requiring an
        # explicit /recompute call. Failures are swallowed.
        if not reply.get('error'):
            trigger_adaptive_recompute(user_id, course_id, source='tutor')

        # Compact context summary so the UI can show what was grounded.
        reply['context_summary'] = {
            'course_id': course_ctx['id'],
            'course_title': course_ctx['title'],
            'weeks_grounded': len(course_ctx.get('weeks') or []),
            'materials_grounded': sum(
                len(w.get('materials') or []) for w in course_ctx.get('weeks') or []
            ),
            'weak_topics': learner_ctx.get('weak_topics') or [],
            'overall_score': learner_ctx.get('overall_score'),
            'preferred_difficulty': learner_ctx.get('preferred_difficulty'),
        }
        return jsonify(reply)
    except Exception as e:
        import logging; logging.exception('tutor error'); return jsonify({'error': 'Internal tutor error'}), 500


@tutor_bp.route('/avatar', methods=['POST'])
@login_required
def tutor_avatar():
    """Generate a HeyGen avatar video for an arbitrary tutor script.

    JSON body: { text: str (required), language: 'en'|'ar' (default 'en') }
    """
    body = request.get_json(silent=True) or {}
    text = (body.get('text') or '').strip()
    language = (body.get('language') or 'en')[:2]
    if not text:
        return jsonify({'error': 'text is required'}), 400
    try:
        api_key = _resolve_api_key('heygen')
        if not api_key:
            return jsonify({'error': 'HeyGen is not configured'}), 400
        ai = AIService()
        result = ai._generate_heygen_video(
            message=text, api_key=api_key, language=language,
        )
        if result.get('video_id'):
            result['status_url'] = f"/api/heygen/status/{result['video_id']}"
        return jsonify(result)
    except Exception as e:
        import logging; logging.exception('tutor error'); return jsonify({'error': 'Internal tutor error'}), 500


@tutor_bp.route('/recompute', methods=['POST'])
@login_required
def tutor_recompute():
    """Re-run the adaptive engine: recompute skill levels + rerank steps."""
    body = request.get_json(silent=True) or {}
    course_id = body.get('course_id')
    path_id = body.get('path_id')
    user_id = session['user_id']
    if course_id and not _user_can_access_course(user_id, course_id):
        return jsonify({'error': 'Not enrolled in this course'}), 403
    try:
        engine = AdaptiveEngine(user_id, course_id)
        return jsonify({'success': True, 'result': engine.run(path_id)})
    except Exception as e:
        import logging; logging.exception('tutor error'); return jsonify({'error': 'Internal tutor error'}), 500
