"""
SkillPilot v2 — Phase 4: AI course authoring + SCORM/xAPI

Additive blueprint mounted at /api/v1/authoring/* and /api/v1/scorm/*
plus /api/v1/xapi/*.

Endpoints
  POST   /api/v1/authoring/drafts              create draft (optionally AI-generated)
  GET    /api/v1/authoring/drafts              list current author drafts
  GET    /api/v1/authoring/drafts/<id>         draft detail
  PUT    /api/v1/authoring/drafts/<id>         update draft
  POST   /api/v1/authoring/drafts/<id>/score   compute quality score
  POST   /api/v1/authoring/drafts/<id>/publish publish to a Course
  POST   /api/v1/authoring/drafts/<id>/restore restore previous version

  GET    /api/v1/authoring/versions            list versions for a content item
  POST   /api/v1/authoring/versions            snapshot a content item

  POST   /api/v1/scorm/import                  register an imported SCORM package
  GET    /api/v1/scorm/packages                list packages
  GET    /api/v1/scorm/packages/<id>/manifest  manifest of a package
  POST   /api/v1/scorm/export                  export a course to SCORM (record metadata)

  POST   /api/v1/xapi/statements               emit an xAPI statement (records + queues to LRS)
  GET    /api/v1/xapi/statements               list recent statements
"""
from datetime import datetime
import os
import tempfile

from flask import Blueprint, jsonify, request, session, send_file, current_app

from app.utils.decorators import (
    login_required, teacher_required, admin_required, is_admin,
)


def _draft_or_403(draft_id):
    """Load a draft and enforce author-or-admin access. Returns (draft, error_response)."""
    from app.models import AuthoringDraft
    d = AuthoringDraft.query.filter_by(id=draft_id).first()
    if not d:
        return None, (jsonify({'error': 'not found'}), 404)
    if d.author_id != session.get('user_id') and not is_admin():
        return None, (jsonify({'error': 'forbidden'}), 403)
    return d, None


authoring_bp = Blueprint('authoring_v2', __name__, url_prefix='/api/v1/authoring')
scorm_bp = Blueprint('scorm_v2', __name__, url_prefix='/api/v1/scorm')
xapi_bp = Blueprint('xapi_v2', __name__, url_prefix='/api/v1/xapi')


_ALLOWED_LANG = {'en', 'ar'}
_ALLOWED_DRAFT_STATUS = {'draft', 'review', 'published', 'archived'}
_ALLOWED_SCORM_VERSIONS = {'1.2', '2004'}
_ALLOWED_VERSION_TYPES = {'course', 'material', 'exam', 'survey', 'draft'}


def _draft_to_dict(d):
    return {
        'id': d.id,
        'author_id': d.author_id,
        'course_id': d.course_id,
        'title': d.title,
        'title_ar': d.title_ar,
        'topic': d.topic,
        'language': d.language,
        'target_audience': d.target_audience,
        'learning_outcomes': d.learning_outcomes or [],
        'weeks': d.weeks or [],
        'ethics_tags': d.ethics_tags or [],
        'quality_score': d.quality_score,
        'quality_breakdown': d.quality_breakdown,
        'generator_model': d.generator_model,
        'status': d.status,
        'published_course_id': d.published_course_id,
        'published_at': d.published_at.isoformat() if d.published_at else None,
        'created_at': d.created_at.isoformat() if d.created_at else None,
        'updated_at': d.updated_at.isoformat() if d.updated_at else None,
    }


def _generate_outline(topic, language='en', weeks=4):
    """Heuristic AI-style outline. Uses AIService if present, otherwise a
    deterministic stub so tests/dev work without API keys."""
    try:
        from app.services.ai_service import AIService
        svc = AIService()
        prompt = (
            f"Create a {weeks}-week course outline for '{topic}'. "
            f"Return JSON: {{outcomes:[..], weeks:[{{title, materials:[..], "
            f"exam_questions:[..], survey_questions:[..]}}]}}. Language: {language}."
        )
        if hasattr(svc, 'generate_text'):
            txt = svc.generate_text(prompt)
            import json as _json
            try:
                return _json.loads(txt), 'ai'
            except Exception:
                pass
    except Exception:
        pass
    # Deterministic fallback outline
    outcomes = [
        f"Understand foundations of {topic}",
        f"Apply core practices of {topic}",
        f"Evaluate ethical implications related to {topic}",
    ]
    week_blocks = []
    for i in range(1, weeks + 1):
        week_blocks.append({
            'title': f"Week {i}: {topic} — Module {i}",
            'materials': [
                {'type': 'reading', 'title': f"Reading {i}.1"},
                {'type': 'video', 'title': f"Video {i}.1"},
            ],
            'exam_questions': [
                {'question': f"Key concept of week {i}?", 'type': 'mcq'},
            ],
            'survey_questions': [
                {'question': f"How clear was week {i}?", 'type': 'likert'},
            ],
        })
    return {'outcomes': outcomes, 'weeks': week_blocks}, 'stub'


def _score_draft(d):
    """Compute a 0..100 content quality score with breakdown."""
    breakdown = {}
    score = 0.0
    # Coverage
    weeks = d.weeks or []
    breakdown['weeks_count'] = len(weeks)
    score += min(30, len(weeks) * 6)
    # Outcomes
    outs = d.learning_outcomes or []
    breakdown['outcomes_count'] = len(outs)
    score += min(20, len(outs) * 5)
    # Bilingual completeness
    bilingual = bool(d.title_ar)
    breakdown['has_arabic_title'] = bilingual
    score += 10 if bilingual else 0
    # Materials per week
    mat_total = sum(len(w.get('materials') or []) for w in weeks if isinstance(w, dict))
    breakdown['materials_total'] = mat_total
    score += min(20, mat_total * 2)
    # Assessment presence
    has_exam = any((w.get('exam_questions') or []) for w in weeks if isinstance(w, dict))
    has_survey = any((w.get('survey_questions') or []) for w in weeks if isinstance(w, dict))
    breakdown['has_exam'] = has_exam
    breakdown['has_survey'] = has_survey
    score += (10 if has_exam else 0) + (5 if has_survey else 0)
    # EthicSense
    eth = d.ethics_tags or []
    breakdown['ethics_tags_count'] = len(eth)
    score += min(5, len(eth))
    return round(min(100.0, score), 1), breakdown


# ---------- drafts ---------------------------------------------------------

@authoring_bp.route('/drafts', methods=['POST'])
@teacher_required
def create_draft():
    try:
        from app.models import db, AuthoringDraft, ContentVersion
        data = request.get_json(silent=True) or {}
        if not data.get('title'):
            return jsonify({'error': 'title is required'}), 400
        lang = data.get('language', 'en')
        if lang not in _ALLOWED_LANG:
            return jsonify({'error': f'language must be one of {sorted(_ALLOWED_LANG)}'}), 400

        weeks_count = int(data.get('weeks_count') or 4)
        outline = None
        gen_model = None
        if data.get('use_ai'):
            outline, gen_model = _generate_outline(
                data.get('topic') or data['title'], lang, max(1, min(16, weeks_count))
            )

        d = AuthoringDraft(
            author_id=session['user_id'],
            course_id=data.get('course_id'),
            title=data['title'][:255],
            title_ar=data.get('title_ar'),
            topic=data.get('topic'),
            language=lang,
            target_audience=data.get('target_audience'),
            learning_outcomes=(outline or {}).get('outcomes') if outline else (data.get('learning_outcomes') or []),
            weeks=(outline or {}).get('weeks') if outline else (data.get('weeks') or []),
            ethics_tags=data.get('ethics_tags') or [],
            generator_model=gen_model,
        )
        db.session.add(d)
        db.session.flush()

        db.session.add(ContentVersion(
            content_type='draft', content_id=d.id, version_number=1,
            snapshot=_draft_to_dict(d), change_note='initial',
            created_by=session['user_id'],
        ))
        db.session.commit()
        return jsonify({'success': True, 'draft': _draft_to_dict(d)}), 201
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@authoring_bp.route('/drafts', methods=['GET'])
@teacher_required
def list_drafts():
    try:
        from app.models import AuthoringDraft
        status = request.args.get('status')
        q = AuthoringDraft.query.filter_by(author_id=session['user_id'])
        if status:
            if status not in _ALLOWED_DRAFT_STATUS:
                return jsonify({'error': 'invalid status'}), 400
            q = q.filter_by(status=status)
        items = q.order_by(AuthoringDraft.updated_at.desc()).all()
        return jsonify({'success': True, 'drafts': [_draft_to_dict(x) for x in items],
                        'count': len(items)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@authoring_bp.route('/drafts/<draft_id>', methods=['GET'])
@teacher_required
def get_draft(draft_id):
    d, err = _draft_or_403(draft_id)
    if err:
        return err
    return jsonify({'success': True, 'draft': _draft_to_dict(d)})


@authoring_bp.route('/drafts/<draft_id>', methods=['PUT'])
@teacher_required
def update_draft(draft_id):
    try:
        from app.models import db, ContentVersion
        d, err = _draft_or_403(draft_id)
        if err:
            return err
        data = request.get_json(silent=True) or {}
        for f in ('title', 'title_ar', 'topic', 'target_audience', 'language'):
            if f in data:
                setattr(d, f, data[f])
        for f in ('learning_outcomes', 'weeks', 'ethics_tags'):
            if f in data:
                setattr(d, f, data[f] or [])
        if 'status' in data and data['status'] in _ALLOWED_DRAFT_STATUS:
            d.status = data['status']
        # snapshot
        last = (ContentVersion.query
                .filter_by(content_type='draft', content_id=d.id)
                .order_by(ContentVersion.version_number.desc()).first())
        next_v = (last.version_number + 1) if last else 1
        db.session.add(ContentVersion(
            content_type='draft', content_id=d.id, version_number=next_v,
            snapshot=_draft_to_dict(d), change_note=data.get('change_note', 'edit'),
            created_by=session['user_id'],
        ))
        db.session.commit()
        return jsonify({'success': True, 'draft': _draft_to_dict(d), 'version': next_v})
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@authoring_bp.route('/drafts/<draft_id>/score', methods=['POST'])
@teacher_required
def score_draft(draft_id):
    try:
        from app.models import db
        d, err = _draft_or_403(draft_id)
        if err:
            return err
        s, b = _score_draft(d)
        d.quality_score = s
        d.quality_breakdown = b
        db.session.commit()
        return jsonify({'success': True, 'quality_score': s, 'breakdown': b})
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@authoring_bp.route('/drafts/<draft_id>/publish', methods=['POST'])
@teacher_required
def publish_draft(draft_id):
    """Publish draft into a real Course (creates a placeholder course if needed).
    The publishing user is recorded as a CourseInstructor (the existing
    many-to-many model) — Course itself has no `created_by` column."""
    try:
        from app.models import db, Course, CourseInstructor
        d, err = _draft_or_403(draft_id)
        if err:
            return err
        course = None
        if d.course_id:
            course = Course.query.filter_by(id=d.course_id).first()
        if not course:
            course = Course(
                title=d.title,
                title_ar=d.title_ar,
                description=(d.topic or '')[:1000],
                is_published=False,
            )
            db.session.add(course)
            db.session.flush()
            d.course_id = course.id
            # Link the publishing teacher as instructor (best-effort).
            try:
                db.session.add(CourseInstructor(
                    course_id=course.id,
                    user_id=session['user_id'],
                    role='instructor',
                ))
            except Exception:
                pass
        d.status = 'published'
        d.published_at = datetime.utcnow()
        d.published_course_id = course.id
        db.session.commit()
        return jsonify({'success': True, 'course_id': course.id, 'draft': _draft_to_dict(d)})
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@authoring_bp.route('/drafts/<draft_id>/restore', methods=['POST'])
@teacher_required
def restore_draft(draft_id):
    try:
        from app.models import db, ContentVersion
        version = (request.get_json(silent=True) or {}).get('version')
        if not version:
            return jsonify({'error': 'version is required'}), 400
        d, err = _draft_or_403(draft_id)
        if err:
            return err
        v = ContentVersion.query.filter_by(
            content_type='draft', content_id=d.id, version_number=int(version)
        ).first()
        if not v:
            return jsonify({'error': 'version not found'}), 404
        snap = v.snapshot or {}
        for f in ('title', 'title_ar', 'topic', 'language', 'target_audience',
                  'learning_outcomes', 'weeks', 'ethics_tags'):
            if f in snap:
                setattr(d, f, snap[f])
        db.session.commit()
        return jsonify({'success': True, 'draft': _draft_to_dict(d)})
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ---------- versions -------------------------------------------------------

@authoring_bp.route('/versions', methods=['GET'])
@teacher_required
def list_versions():
    try:
        from app.models import ContentVersion
        ct = request.args.get('content_type')
        cid = request.args.get('content_id')
        if not ct or not cid:
            return jsonify({'error': 'content_type and content_id are required'}), 400
        if ct not in _ALLOWED_VERSION_TYPES:
            return jsonify({'error': f'content_type must be one of {sorted(_ALLOWED_VERSION_TYPES)}'}), 400
        rows = (ContentVersion.query
                .filter_by(content_type=ct, content_id=cid)
                .order_by(ContentVersion.version_number.desc()).all())
        return jsonify({
            'success': True,
            'count': len(rows),
            'versions': [{
                'id': v.id, 'version_number': v.version_number,
                'change_note': v.change_note,
                'created_by': v.created_by,
                'created_at': v.created_at.isoformat() if v.created_at else None,
            } for v in rows],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@authoring_bp.route('/versions', methods=['POST'])
@teacher_required
def snapshot_version():
    try:
        from app.models import db, ContentVersion
        data = request.get_json(silent=True) or {}
        ct = data.get('content_type'); cid = data.get('content_id')
        snap = data.get('snapshot')
        if not ct or not cid or not isinstance(snap, dict):
            return jsonify({'error': 'content_type, content_id, snapshot are required'}), 400
        if ct not in _ALLOWED_VERSION_TYPES:
            return jsonify({'error': 'invalid content_type'}), 400
        last = (ContentVersion.query
                .filter_by(content_type=ct, content_id=cid)
                .order_by(ContentVersion.version_number.desc()).first())
        next_v = (last.version_number + 1) if last else 1
        v = ContentVersion(content_type=ct, content_id=cid, version_number=next_v,
                           snapshot=snap, change_note=data.get('change_note'),
                           created_by=session['user_id'])
        db.session.add(v); db.session.commit()
        return jsonify({'success': True, 'version_number': next_v, 'id': v.id}), 201
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ---------- SCORM ----------------------------------------------------------

@scorm_bp.route('/import', methods=['POST'])
@teacher_required
def scorm_import():
    """Register an already-uploaded SCORM package by storage_path metadata.
    For real uploads use POST /api/v1/scorm/upload (multipart)."""
    try:
        from app.models import db, ScormPackage
        data = request.get_json(silent=True) or {}
        version = data.get('scorm_version', '2004')
        if version not in _ALLOWED_SCORM_VERSIONS:
            return jsonify({'error': 'scorm_version must be 1.2 or 2004'}), 400
        pkg = ScormPackage(
            course_id=data.get('course_id'),
            package_name=data.get('package_name') or 'package.zip',
            scorm_version=version,
            direction='import',
            storage_path=data.get('storage_path'),
            manifest=data.get('manifest') or {},
            size_bytes=data.get('size_bytes'),
            status='ready',
            created_by=session['user_id'],
        )
        db.session.add(pkg); db.session.commit()
        return jsonify({'success': True, 'id': pkg.id}), 201
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@scorm_bp.route('/upload', methods=['POST'])
@teacher_required
def scorm_upload():
    """Multipart upload of a SCORM 1.2/2004 ZIP. Unpacks the manifest,
    registers materials, and returns a package summary."""
    try:
        from app.services.scorm_service import import_package
        f = request.files.get('file')
        if f is None or not f.filename:
            return jsonify({'error': 'file (multipart) is required'}), 400
        course_id = request.form.get('course_id') or request.args.get('course_id')
        # Persist to a temp file first so import_package can stream it.
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name
        try:
            result = import_package(
                tmp_path, course_id=course_id, user_id=session['user_id'],
                package_name=f.filename,
            )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return jsonify({
            'success': True,
            'id': result['package_id'],
            'materials_added': result['materials_added'],
            'manifest': {
                'scorm_version': result['manifest'].get('scorm_version'),
                'title': result['manifest'].get('title'),
                'item_count': len(result['manifest'].get('items') or []),
            },
        }), 201
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@scorm_bp.route('/packages', methods=['GET'])
@teacher_required
def scorm_list():
    from app.models import ScormPackage
    q = ScormPackage.query
    if not is_admin():
        q = q.filter(ScormPackage.created_by == session['user_id'])
    rows = q.order_by(ScormPackage.created_at.desc()).limit(200).all()
    return jsonify({'success': True, 'count': len(rows), 'packages': [{
        'id': p.id, 'course_id': p.course_id, 'package_name': p.package_name,
        'scorm_version': p.scorm_version, 'direction': p.direction,
        'status': p.status,
        'created_at': p.created_at.isoformat() if p.created_at else None,
    } for p in rows]})


def _scorm_pkg_or_403(pkg_id):
    """Load a SCORM package and enforce owner-or-admin access."""
    from app.models import ScormPackage
    p = ScormPackage.query.filter_by(id=pkg_id).first()
    if not p:
        return None, (jsonify({'error': 'not found'}), 404)
    if p.created_by != session.get('user_id') and not is_admin():
        return None, (jsonify({'error': 'forbidden'}), 403)
    return p, None


@scorm_bp.route('/packages/<pkg_id>/manifest', methods=['GET'])
@teacher_required
def scorm_manifest(pkg_id):
    p, err = _scorm_pkg_or_403(pkg_id)
    if err:
        return err
    return jsonify({'success': True, 'manifest': p.manifest or {}})


@scorm_bp.route('/export', methods=['POST'])
@teacher_required
def scorm_export():
    """Bundle a Course's weeks + materials into a downloadable SCORM ZIP."""
    try:
        from app.services.scorm_service import export_course
        data = request.get_json(silent=True) or {}
        course_id = data.get('course_id')
        if not course_id:
            return jsonify({'error': 'course_id required'}), 400
        version = data.get('scorm_version', '2004')
        if version not in _ALLOWED_SCORM_VERSIONS:
            return jsonify({'error': 'scorm_version must be 1.2 or 2004'}), 400
        result = export_course(course_id, scorm_version=version,
                                user_id=session['user_id'])
        return jsonify({
            'success': True, 'id': result['package_id'],
            'download_url': result['download_url'],
            'item_count': result['item_count'],
        }), 201
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@scorm_bp.route('/packages/<pkg_id>/download', methods=['GET'])
@teacher_required
def scorm_download(pkg_id):
    """Stream a previously-exported SCORM ZIP (owner or admin only)."""
    p, err = _scorm_pkg_or_403(pkg_id)
    if err:
        return err
    if p.direction != 'export' or not p.storage_path or not os.path.exists(p.storage_path):
        return jsonify({'error': 'package not available for download'}), 404
    return send_file(p.storage_path, as_attachment=True,
                      download_name=p.package_name or f'{pkg_id}.zip',
                      mimetype='application/zip')


# ---------- xAPI -----------------------------------------------------------

@xapi_bp.route('/statements', methods=['POST'])
@login_required
def xapi_emit():
    try:
        from app.models import db, XApiStatement
        from app.services.xapi_service import deliver_statement
        data = request.get_json(silent=True) or {}
        verb = data.get('verb')
        statement = data.get('statement')
        if not verb or not isinstance(statement, dict):
            return jsonify({'error': 'verb and statement (object) required'}), 400
        # Trusted LRS endpoint is server-controlled only. Client-supplied
        # `lrs_endpoint` values are ignored to prevent SSRF (an authenticated
        # user could otherwise coerce the server into POSTing to internal
        # network targets).
        lrs = os.environ.get('XAPI_LRS_ENDPOINT')
        s = XApiStatement(
            actor_user_id=session['user_id'],
            verb=verb,
            object_type=data.get('object_type'),
            object_id=data.get('object_id'),
            object_name=data.get('object_name'),
            result=data.get('result'),
            context=data.get('context'),
            statement=statement,
            lrs_endpoint=lrs,
            delivery_status='pending',
        )
        db.session.add(s); db.session.flush()
        # Forward to LRS (best-effort). Result mutates `s` in-place.
        try:
            deliver_statement(s)
        except Exception as de:
            s.delivery_status = 'failed'
            s.delivery_error = str(de)[:2000]
        db.session.commit()
        return jsonify({'success': True, 'id': s.id,
                         'delivery_status': s.delivery_status,
                         'delivery_error': s.delivery_error}), 201
    except Exception as e:
        from app.models import db as _db
        _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@xapi_bp.route('/retry', methods=['POST'])
@teacher_required
def xapi_retry():
    """Re-attempt LRS delivery for failed statements.

    Teachers (and other non-admin instructors) can only retry their own
    failed statements. Admins retry across all actors. Scope is determined
    server-side from the session — clients cannot widen it.
    """
    try:
        from app.services.xapi_service import retry_failed
        data = request.get_json(silent=True) or {}
        limit = max(1, min(500, int(data.get('limit', 50))))
        actor_id = None if is_admin() else session['user_id']
        return jsonify({'success': True,
                         **retry_failed(limit=limit, actor_user_id=actor_id)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@xapi_bp.route('/statements', methods=['GET'])
@login_required
def xapi_list():
    from app.models import XApiStatement
    rows = (XApiStatement.query
            .filter_by(actor_user_id=session['user_id'])
            .order_by(XApiStatement.created_at.desc()).limit(200).all())
    return jsonify({'success': True, 'count': len(rows), 'statements': [{
        'id': s.id, 'verb': s.verb, 'object_type': s.object_type,
        'object_id': s.object_id, 'object_name': s.object_name,
        'delivery_status': s.delivery_status,
        'created_at': s.created_at.isoformat() if s.created_at else None,
    } for s in rows]})
