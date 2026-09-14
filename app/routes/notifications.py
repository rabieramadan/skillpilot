"""SkillPilot in-app notifications API.

Mounted at /api/v1/notifications/* — additive surface used by the bell in
the top bar and by admins to flush queued email digests.
"""
from datetime import datetime
from flask import Blueprint, jsonify, request, session

from app.utils.decorators import login_required


notifications_bp = Blueprint('notifications_v2', __name__, url_prefix='/api/v1/notifications')


@notifications_bp.route('', methods=['GET'])
@login_required
def list_notifications():
    from app.models import Notification
    uid = session['user_id']
    only_unread = request.args.get('unread', '0') == '1'
    q = Notification.query.filter_by(user_id=uid)
    if only_unread:
        q = q.filter(Notification.read_at.is_(None))
    rows = q.order_by(Notification.created_at.desc()).limit(200).all()
    return jsonify({
        'success': True,
        'unread': sum(1 for r in rows if not r.read_at),
        'items': [{
            'id': r.id, 'kind': r.kind, 'title': r.title, 'body': r.body,
            'url': r.url, 'severity': r.severity,
            'payload': r.payload or {},
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'read_at': r.read_at.isoformat() if r.read_at else None,
        } for r in rows],
    })


@notifications_bp.route('/unread-count', methods=['GET'])
@login_required
def unread_count():
    from app.models import Notification
    n = Notification.query.filter_by(user_id=session['user_id'], read_at=None).count()
    return jsonify({'success': True, 'unread': n})


@notifications_bp.route('/<int:nid>/read', methods=['POST'])
@login_required
def mark_read(nid):
    from app.models import db, Notification
    n = Notification.query.filter_by(id=nid, user_id=session['user_id']).first()
    if not n:
        return jsonify({'error': 'not_found'}), 404
    if not n.read_at:
        n.read_at = datetime.utcnow()
        db.session.commit()
    return jsonify({'success': True})


@notifications_bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_read():
    from app.models import db, Notification
    now = datetime.utcnow()
    Notification.query.filter_by(user_id=session['user_id'], read_at=None)\
        .update({Notification.read_at: now})
    db.session.commit()
    return jsonify({'success': True})


@notifications_bp.route('/digest/run', methods=['POST'])
@login_required
def run_digest():
    if (session.get('role') or '').lower() not in ('admin', 'superadmin', 'super_admin'):
        return jsonify({'error': 'forbidden'}), 403
    from app.services.notification_service import send_pending_digests
    return jsonify(send_pending_digests())
