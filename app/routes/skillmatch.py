"""
SkillPilot v2 — Phase 7: SkillMatch + Teacher Professional Development.

Mounted at:
  /api/v1/skillmatch/*   occupations, labour-market, readiness scoring
  /api/v1/pd/*           teacher professional development tracks
"""
from datetime import datetime
import secrets

from flask import Blueprint, jsonify, request, session

from app.utils.decorators import login_required, teacher_required, admin_required


skillmatch_bp = Blueprint('skillmatch_v2', __name__, url_prefix='/api/v1/skillmatch')
pd_bp = Blueprint('pd_v2', __name__, url_prefix='/api/v1/pd')


_LM_SOURCES = {'oman_mol', 'ncsi', 'job_portal', 'manual', 'other'}
_PD_TRACK_TYPES = {'ai_literacy', 'pedagogy', 'ethicsense_trainer', 'general'}


# ---------- Occupations + Skill mappings ----------------------------------

@skillmatch_bp.route('/occupations', methods=['GET'])
@login_required
def occupation_list():
    from app.models import Occupation
    sector = request.args.get('sector')
    q = Occupation.query.filter_by(is_active=True)
    if sector:
        q = q.filter_by(sector=sector)
    rows = q.order_by(Occupation.name.asc()).limit(500).all()
    return jsonify({'success': True, 'count': len(rows), 'occupations': [{
        'id': o.id, 'code': o.code, 'name': o.name, 'name_ar': o.name_ar,
        'sector': o.sector, 'esco_code': o.esco_code, 'onet_code': o.onet_code,
    } for o in rows]})


@skillmatch_bp.route('/occupations', methods=['POST'])
@admin_required
def occupation_create():
    try:
        from app.models import db, Occupation
        data = request.get_json(silent=True) or {}
        if not data.get('code') or not data.get('name'):
            return jsonify({'error': 'code and name required'}), 400
        o = Occupation(
            code=data['code'][:40], name=data['name'][:255],
            name_ar=data.get('name_ar'),
            description=data.get('description'),
            description_ar=data.get('description_ar'),
            sector=data.get('sector'),
            esco_code=data.get('esco_code'),
            onet_code=data.get('onet_code'),
        )
        db.session.add(o); db.session.commit()
        return jsonify({'success': True, 'id': o.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@skillmatch_bp.route('/occupations/<oid>/skills', methods=['POST'])
@admin_required
def occupation_set_skills(oid):
    try:
        from app.models import db, Occupation, OccupationSkill, Skill
        if not Occupation.query.filter_by(id=oid).first():
            return jsonify({'error': 'occupation not found'}), 404
        data = request.get_json(silent=True) or {}
        skills = data.get('skills') or []
        OccupationSkill.query.filter_by(occupation_id=oid).delete()
        for s in skills:
            code = s.get('skill_code')
            sk = Skill.query.filter_by(code=code).first() if code else None
            if not sk:
                continue
            db.session.add(OccupationSkill(
                occupation_id=oid, skill_id=sk.id,
                target_level=int(s.get('target_level', 3)),
                importance=float(s.get('importance', 1.0)),
                is_essential=bool(s.get('is_essential', True)),
            ))
        db.session.commit()
        return jsonify({'success': True, 'mapped': len(skills)})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ---------- Labour-market data --------------------------------------------

@skillmatch_bp.route('/labour-market', methods=['POST'])
@admin_required
def labour_market_ingest():
    """Ingest a batch of labour-market signals from any pluggable source."""
    try:
        from app.models import db, LabourMarketSignal, Occupation
        data = request.get_json(silent=True) or {}
        items = data.get('signals') or []
        if not isinstance(items, list):
            return jsonify({'error': 'signals must be a list'}), 400
        ingested = 0
        for it in items:
            src = it.get('source')
            if src not in _LM_SOURCES:
                continue
            occ_id = None
            if it.get('occupation_code'):
                occ = Occupation.query.filter_by(code=it['occupation_code']).first()
                occ_id = occ.id if occ else None
            db.session.add(LabourMarketSignal(
                occupation_id=occ_id,
                sector=it.get('sector'),
                region=it.get('region', 'OM'),
                source=src, period=it.get('period'),
                open_postings=it.get('open_postings'),
                median_salary=it.get('median_salary'),
                growth_rate_5yr=it.get('growth_rate_5yr'),
                growth_rate_10yr=it.get('growth_rate_10yr'),
                demand_index=it.get('demand_index'),
                raw_payload=it.get('raw'),
            ))
            ingested += 1
        db.session.commit()
        return jsonify({'success': True, 'ingested': ingested})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@skillmatch_bp.route('/labour-market/sync', methods=['POST'])
@admin_required
def labour_market_sync():
    """Trigger an immediate ingestion run from Oman MoL, NCSI, and the
    public job-portal feed. Returns per-source counts.

    By default the run is guarded by a distributed lock so multiple workers
    cannot double-run. Pass `?force=1` to bypass the lock (e.g., admin retry
    after a stuck previous run)."""
    try:
        from app.services.labour_market_service import (
            run_sync_once, run_sync_with_lock,
        )
        force = request.args.get('force') in ('1', 'true', 'yes')
        if force:
            return jsonify({'success': True, 'forced': True,
                            **run_sync_once()})
        res = run_sync_with_lock()
        if not res.get('ran'):
            return jsonify({'success': True, 'ran': False,
                            'reason': res.get('reason')}), 202
        body = {'success': True, 'ran': True}
        if 'result' in res:
            body.update(res['result'])
        if 'error' in res:
            body['error'] = res['error']
        return jsonify(body)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@skillmatch_bp.route('/labour-market/sync/status', methods=['GET'])
@admin_required
def labour_market_sync_status():
    """Expose the last successful run + last error for the labour-market
    scheduled job so admins can verify the cadence in production."""
    try:
        from app.services.labour_market_service import get_status
        return jsonify({'success': True, 'status': get_status()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@skillmatch_bp.route('/labour-market', methods=['GET'])
@login_required
def labour_market_list():
    from app.models import LabourMarketSignal, Occupation
    occ_code = request.args.get('occupation_code')
    sector = request.args.get('sector')
    region = request.args.get('region')
    q = LabourMarketSignal.query
    if occ_code:
        occ = Occupation.query.filter_by(code=occ_code).first()
        if occ:
            q = q.filter_by(occupation_id=occ.id)
    if sector: q = q.filter_by(sector=sector)
    if region: q = q.filter_by(region=region)
    rows = q.order_by(LabourMarketSignal.captured_at.desc()).limit(500).all()
    return jsonify({'success': True, 'count': len(rows), 'signals': [{
        'id': s.id, 'occupation_id': s.occupation_id,
        'sector': s.sector, 'region': s.region, 'source': s.source,
        'period': s.period, 'open_postings': s.open_postings,
        'median_salary': s.median_salary,
        'growth_rate_5yr': s.growth_rate_5yr, 'growth_rate_10yr': s.growth_rate_10yr,
        'demand_index': s.demand_index,
        'captured_at': s.captured_at.isoformat() if s.captured_at else None,
    } for s in rows]})


# ---------- Readiness scoring ---------------------------------------------

@skillmatch_bp.route('/readiness', methods=['GET'])
@login_required
def readiness():
    """
    Compute job-readiness score for current learner against an occupation.
    Combines learner skill levels vs occupation skill targets, weighted by importance.
    """
    from app.models import (
        Occupation, OccupationSkill, LearnerSkill, Skill, LabourMarketSignal,
    )
    occ_code = request.args.get('occupation_code')
    if not occ_code:
        return jsonify({'error': 'occupation_code required'}), 400
    occ = Occupation.query.filter_by(code=occ_code).first()
    if not occ:
        return jsonify({'error': 'occupation not found'}), 404

    requirements = (OccupationSkill.query.filter_by(occupation_id=occ.id).all())
    learner_levels = {
        ls.skill_id: ls for ls in LearnerSkill.query
        .filter_by(user_id=session['user_id']).all()
    }
    if not requirements:
        return jsonify({'success': True, 'score': None,
                        'message': 'No skills mapped to this occupation yet.'})
    total_weight = sum(r.importance for r in requirements) or 1.0
    achieved = 0.0
    gaps = []
    for r in requirements:
        sk = Skill.query.filter_by(id=r.skill_id).first()
        ls = learner_levels.get(r.skill_id)
        cur = ls.level if ls else 0
        max_lvl = (sk.level_max if sk else 5) or 5
        ratio = min(1.0, cur / max(1, r.target_level))
        achieved += ratio * r.importance
        if cur < r.target_level:
            gaps.append({
                'skill_code': sk.code if sk else None,
                'skill_name': sk.name if sk else None,
                'current_level': cur,
                'target_level': r.target_level,
                'level_max': max_lvl,
                'importance': r.importance,
                'is_essential': r.is_essential,
            })
    score = round(100.0 * achieved / total_weight, 1)
    latest_signal = (LabourMarketSignal.query.filter_by(occupation_id=occ.id)
                     .order_by(LabourMarketSignal.captured_at.desc()).first())
    return jsonify({
        'success': True,
        'occupation': {'code': occ.code, 'name': occ.name, 'sector': occ.sector},
        'readiness_score': score,
        'gaps': sorted(gaps, key=lambda g: -g['importance']),
        'market_signal': {
            'period': latest_signal.period if latest_signal else None,
            'demand_index': latest_signal.demand_index if latest_signal else None,
            'growth_rate_5yr': latest_signal.growth_rate_5yr if latest_signal else None,
            'growth_rate_10yr': latest_signal.growth_rate_10yr if latest_signal else None,
        },
    })


# ---------- Teacher PD ----------------------------------------------------

@pd_bp.route('/tracks', methods=['GET'])
@login_required
def pd_list():
    from app.models import TeacherPDTrack
    rows = TeacherPDTrack.query.filter_by(is_active=True).all()
    return jsonify({'success': True, 'count': len(rows), 'tracks': [{
        'id': t.id, 'code': t.code, 'name': t.name, 'name_ar': t.name_ar,
        'description': t.description, 'track_type': t.track_type,
        'estimated_hours': t.estimated_hours, 'credential_name': t.credential_name,
        'is_trainer_of_trainers': t.is_trainer_of_trainers,
    } for t in rows]})


@pd_bp.route('/tracks', methods=['POST'])
@admin_required
def pd_create():
    try:
        from app.models import db, TeacherPDTrack
        data = request.get_json(silent=True) or {}
        if not data.get('code') or not data.get('name'):
            return jsonify({'error': 'code and name required'}), 400
        tt = data.get('track_type', 'general')
        if tt not in _PD_TRACK_TYPES:
            return jsonify({'error': f'track_type must be one of {sorted(_PD_TRACK_TYPES)}'}), 400
        t = TeacherPDTrack(
            code=data['code'][:64], name=data['name'][:255],
            name_ar=data.get('name_ar'),
            description=data.get('description'),
            description_ar=data.get('description_ar'),
            track_type=tt,
            estimated_hours=data.get('estimated_hours'),
            credential_name=data.get('credential_name'),
            is_trainer_of_trainers=bool(data.get('is_trainer_of_trainers', False)),
            syllabus=data.get('syllabus') or [],
        )
        db.session.add(t); db.session.commit()
        return jsonify({'success': True, 'id': t.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@pd_bp.route('/enroll', methods=['POST'])
@login_required
def pd_enroll():
    try:
        from app.models import db, TeacherPDTrack, TeacherPDEnrollment
        data = request.get_json(silent=True) or {}
        code = data.get('track_code')
        if not code:
            return jsonify({'error': 'track_code required'}), 400
        t = TeacherPDTrack.query.filter_by(code=code).first()
        if not t:
            return jsonify({'error': 'track not found'}), 404
        existing = TeacherPDEnrollment.query.filter_by(
            track_id=t.id, user_id=session['user_id']).first()
        if existing:
            return jsonify({'success': True, 'already': True, 'id': existing.id})
        e = TeacherPDEnrollment(track_id=t.id, user_id=session['user_id'])
        db.session.add(e); db.session.commit()
        return jsonify({'success': True, 'id': e.id}), 201
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@pd_bp.route('/enrollments', methods=['GET'])
@login_required
def pd_my_enrollments():
    from app.models import TeacherPDEnrollment, TeacherPDTrack
    rows = TeacherPDEnrollment.query.filter_by(user_id=session['user_id']).all()
    out = []
    for e in rows:
        t = TeacherPDTrack.query.filter_by(id=e.track_id).first()
        out.append({
            'id': e.id, 'track_id': e.track_id,
            'track_code': t.code if t else None,
            'track_name': t.name if t else None,
            'status': e.status, 'progress_percent': e.progress_percent,
            'final_score': e.final_score, 'certificate_url': e.certificate_url,
            'issued_at': e.issued_at.isoformat() if e.issued_at else None,
        })
    return jsonify({'success': True, 'count': len(out), 'enrollments': out})


@pd_bp.route('/enrollments/<eid>/progress', methods=['POST'])
@login_required
def pd_update_progress(eid):
    try:
        from app.models import db, TeacherPDEnrollment
        data = request.get_json(silent=True) or {}
        e = TeacherPDEnrollment.query.filter_by(id=eid, user_id=session['user_id']).first()
        if not e:
            return jsonify({'error': 'not found'}), 404
        if 'progress_percent' in data:
            try:
                e.progress_percent = max(0.0, min(100.0, float(data['progress_percent'])))
            except (TypeError, ValueError):
                return jsonify({'error': 'progress_percent must be numeric'}), 400
        if e.progress_percent and e.progress_percent < 100:
            e.status = 'in_progress'
        db.session.commit()
        return jsonify({'success': True, 'progress_percent': e.progress_percent,
                        'status': e.status})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@pd_bp.route('/enrollments/<eid>/issue-certificate', methods=['POST'])
@admin_required
def pd_issue_cert(eid):
    """Mark a PD track as completed and issue a verifiable certificate id."""
    try:
        from app.models import db, TeacherPDEnrollment
        data = request.get_json(silent=True) or {}
        e = TeacherPDEnrollment.query.filter_by(id=eid).first()
        if not e:
            return jsonify({'error': 'not found'}), 404
        e.status = 'certified'
        e.final_score = float(data.get('final_score', 100.0))
        e.progress_percent = 100.0
        e.completed_at = datetime.utcnow()
        e.issued_at = datetime.utcnow()
        cert_id = secrets.token_urlsafe(12)
        e.certificate_id = cert_id
        e.certificate_url = data.get('certificate_url') or f'/certificates/pd/{cert_id}.pdf'
        db.session.commit()
        return jsonify({'success': True, 'certificate_id': cert_id,
                        'certificate_url': e.certificate_url})
    except Exception as e:
        from app.models import db as _db; _db.session.rollback()
        return jsonify({'error': str(e)}), 500


@pd_bp.route('/certificates/<cert_id>/verify', methods=['GET'])
def pd_verify_cert(cert_id):
    """Public verification endpoint."""
    from app.models import TeacherPDEnrollment, TeacherPDTrack, User
    e = TeacherPDEnrollment.query.filter_by(certificate_id=cert_id).first()
    if not e:
        return jsonify({'verified': False}), 404
    t = TeacherPDTrack.query.filter_by(id=e.track_id).first()
    u = User.query.filter_by(id=e.user_id).first()
    return jsonify({
        'verified': True,
        'certificate_id': cert_id,
        'holder_name': u.full_name if u else None,
        'track_code': t.code if t else None,
        'track_name': t.name if t else None,
        'credential_name': t.credential_name if t else None,
        'issued_at': e.issued_at.isoformat() if e.issued_at else None,
        'final_score': e.final_score,
    })
