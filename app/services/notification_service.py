"""SkillPilot notification service.

Single entry point for emitting in-app notifications and queueing email
digests. Email is fire-and-forget: if SMTP is not configured in
KeyValueSetting('smtp_config'), the notification is still recorded in-app
and the email_sent_at column simply stays NULL until the operator
configures SMTP and runs the digest mailer.
"""
from datetime import datetime, timedelta
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _kv_get(key, default=None):
    from app.models import KeyValueSetting
    row = KeyValueSetting.query.filter_by(key=key).first()
    if not row or row.value is None:
        return default
    try:
        return json.loads(row.value)
    except Exception:
        return row.value


def notify(user_id, kind, title, body=None, url=None, payload=None, severity='info'):
    """Create an in-app notification row. Returns the new Notification."""
    from app.models import db, Notification
    n = Notification(
        user_id=user_id, kind=kind, title=title[:240], body=body,
        url=url, payload=payload or {}, severity=severity,
    )
    db.session.add(n)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return None
    return n


def notify_many(user_ids, **kwargs):
    out = []
    seen = set()
    for uid in user_ids:
        if not uid or uid in seen:
            continue
        seen.add(uid)
        n = notify(uid, **kwargs)
        if n:
            out.append(n)
    return out


def _smtp_open():
    """Open an SMTP connection from KeyValueSetting('smtp_config').

    Returns (smtp, cfg) on success or (None, reason_str) when SMTP isn't
    configured or fails. Callers must smtp.quit() when done.
    """
    cfg = _kv_get('smtp_config', {}) or {}
    if not cfg.get('host') or not cfg.get('from_email'):
        return None, 'smtp_not_configured'
    try:
        smtp = smtplib.SMTP(cfg['host'], int(cfg.get('port') or 587), timeout=20)
        if cfg.get('use_tls', True):
            smtp.starttls()
        if cfg.get('username') and cfg.get('password'):
            smtp.login(cfg['username'], cfg['password'])
        return smtp, cfg
    except Exception as e:
        return None, f'smtp_connect_failed: {e}'


def send_email(to_email, subject, body_text, body_html=None):
    """Send a single transactional email immediately. Fail-soft.

    Returns {'sent': bool, 'reason': str}. Used for password-reset links
    and explicit class broadcasts where waiting for the digest is wrong.
    """
    if not to_email:
        return {'sent': False, 'reason': 'no_recipient'}
    smtp, cfg_or_reason = _smtp_open()
    if smtp is None:
        return {'sent': False, 'reason': cfg_or_reason}
    cfg = cfg_or_reason
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject[:240]
        msg['From'] = cfg['from_email']
        msg['To'] = to_email
        msg.attach(MIMEText(body_text or '', 'plain', 'utf-8'))
        if body_html:
            msg.attach(MIMEText(body_html, 'html', 'utf-8'))
        smtp.sendmail(cfg['from_email'], [to_email], msg.as_string())
        return {'sent': True, 'reason': 'ok'}
    except Exception as e:
        return {'sent': False, 'reason': f'send_failed: {e}'}
    finally:
        try: smtp.quit()
        except Exception: pass


def notify_course_audience(course_id, kind, title, body=None, url=None,
                           severity='info', payload=None,
                           include_students=True, include_teachers=True,
                           include_admins=True, exclude_user_ids=None):
    """Push an in-app notification to everyone tied to a course.

    Audience: enrolled students (status approved/active/completed),
    assigned course instructors, and (optionally) all super_admin /
    admin users. Returns a summary dict — never raises (model imports
    are scoped per-block so a renamed/missing table can't take down the
    caller).
    """
    excl = set(exclude_user_ids or [])
    user_ids = []

    if include_students:
        try:
            from app.models import Enrollment  # local import — fail-soft
            for e in Enrollment.query.filter(
                Enrollment.course_id == course_id,
                Enrollment.status.in_(['approved', 'active', 'completed']),
            ).all():
                if e.user_id and e.user_id not in excl:
                    user_ids.append(e.user_id)
        except Exception as ex:
            print(f"[notify_course_audience] students lookup skipped: {ex}")

    if include_teachers:
        try:
            from app.models import CourseInstructor  # local import — fail-soft
            for ci in CourseInstructor.query.filter_by(course_id=course_id).all():
                if ci.user_id and ci.user_id not in excl:
                    user_ids.append(ci.user_id)
        except Exception as ex:
            print(f"[notify_course_audience] teachers lookup skipped: {ex}")

    if include_admins:
        try:
            from app.models import User  # local import — fail-soft
            for u in User.query.filter(
                User.role.in_(['super_admin', 'superadmin', 'admin', 'institution_admin']),
            ).all():
                if u.id and u.id not in excl:
                    user_ids.append(u.id)
        except Exception as ex:
            print(f"[notify_course_audience] admins lookup skipped: {ex}")

    delivered = notify_many(
        user_ids, kind=kind, title=title, body=body,
        url=url, payload=payload or {}, severity=severity,
    )
    return {'count': len(delivered), 'audience': len(set(user_ids))}


def send_pending_digests(within_minutes=1440, limit=200):
    """Flush pending unread notifications as digest emails.

    Returns {'sent': N, 'skipped': M, 'reason': str}. Safe to call from a
    cron / Replit scheduled deployment. No-op when SMTP is not configured.
    """
    cfg = _kv_get('smtp_config', {}) or {}
    if not cfg.get('host') or not cfg.get('from_email'):
        return {'sent': 0, 'skipped': 0, 'reason': 'smtp_not_configured'}
    from app.models import db, Notification, User
    cutoff = datetime.utcnow() - timedelta(minutes=within_minutes)
    rows = (Notification.query
            .filter(Notification.email_sent_at.is_(None))
            .filter(Notification.created_at >= cutoff)
            .order_by(Notification.user_id, Notification.created_at.desc())
            .limit(limit).all())
    if not rows:
        return {'sent': 0, 'skipped': 0, 'reason': 'no_pending'}

    by_user = {}
    for n in rows:
        by_user.setdefault(n.user_id, []).append(n)

    sent = skipped = 0
    try:
        smtp = smtplib.SMTP(cfg['host'], int(cfg.get('port') or 587), timeout=20)
        if cfg.get('use_tls', True):
            smtp.starttls()
        if cfg.get('username') and cfg.get('password'):
            smtp.login(cfg['username'], cfg['password'])
    except Exception as e:
        return {'sent': 0, 'skipped': len(rows), 'reason': f'smtp_connect_failed: {e}'}

    try:
        for uid, items in by_user.items():
            user = User.query.get(uid)
            if not user or not getattr(user, 'email', None):
                skipped += len(items); continue
            lines = [f"- {x.title}" + (f" — {x.body}" if x.body else '') for x in items]
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"SkillPilot: {len(items)} new notification(s)"
            msg['From'] = cfg['from_email']
            msg['To'] = user.email
            msg.attach(MIMEText("\n".join(lines), 'plain'))
            try:
                smtp.sendmail(cfg['from_email'], [user.email], msg.as_string())
                now = datetime.utcnow()
                for x in items:
                    x.email_sent_at = now
                sent += len(items)
            except Exception:
                skipped += len(items)
        db.session.commit()
    finally:
        try: smtp.quit()
        except Exception: pass
    return {'sent': sent, 'skipped': skipped, 'reason': 'ok'}
