from flask import (Blueprint, render_template, request, jsonify, session,
                   redirect, url_for, send_from_directory, current_app)
from app.services.ai_service import AIService
import os
import json
from datetime import datetime

main_bp = Blueprint('main', __name__)


@main_bp.route('/uploads/materials/<path:filename>')
def serve_material(filename):
    """Serve uploaded material files"""
    upload_dir = os.path.join(os.getcwd(), 'uploads', 'materials')
    return send_from_directory(upload_dir, filename)


@main_bp.route('/verify/<cert_number>')
def verify_certificate(cert_number):
    """Public certificate verification page reached by scanning the QR
    code printed on every certificate.

    Class-mode certificates use the format CERT-<first 8 chars of
    Enrollment.id, uppercase>, so we look up by matching prefix.
    No-class-mode certificates are not stored in the database (no
    Enrollment row) and therefore cannot be verified — those scans get
    a friendly "not found" page.
    """
    from app.models import db, Enrollment, User, Course, IssuedCertificate
    cert_number_clean = (cert_number or '').strip().upper()
    enrollment = None
    student = None
    course = None
    issued = None

    # Lookup #1: registry table — covers both class-mode and CSV-only
    # bulk certificates because both branches now insert into it.
    try:
        issued = IssuedCertificate.query.filter_by(cert_number=cert_number_clean).first()
    except Exception:
        issued = None  # table may not exist yet on very old installs

    # Lookup #2: legacy fallback — class-mode certs printed before the
    # registry existed are still derivable from Enrollment.id.
    if not issued and cert_number_clean.startswith('CERT-') and len(cert_number_clean) >= 13:
        prefix = cert_number_clean[5:13].lower()
        enrollment = (
            Enrollment.query
            .filter(Enrollment.certificate_issued.is_(True))
            .filter(Enrollment.id.ilike(prefix + '%'))
            .first()
        )
        if enrollment:
            student = User.query.filter_by(id=enrollment.user_id).first()
            course = Course.query.filter_by(id=enrollment.course_id).first()

    return render_template(
        'verify_certificate.html',
        cert_number=cert_number_clean,
        enrollment=enrollment,
        student=student,
        course=course,
        issued=issued,
    )

@main_bp.route('/favicon.ico')
def favicon():
    """Browsers ask for this on every page whether or not it is linked, and a
    missing one logged a 404 for each page load. Serve the site logo."""
    return send_from_directory(
        os.path.join(current_app.root_path, '..', 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')


@main_bp.route('/')
def landing():
    """Landing page - Future Coverage AI Training & Applications portal"""
    # If user is already logged in, redirect to app
    if session.get('user_id') or session.get('is_admin'):
        return redirect(url_for('main.app_page'))
    
    # Render the new Future Coverage landing page
    return render_template('future_coverage.html')


@main_bp.route('/skillpilot-landing')
def skillpilot_landing():
    """SkillPilot-specific landing page (original landing page)"""
    from app.models import db, SiteSettings, Course, User, Enrollment
    
    # If user is already logged in, redirect to app
    if session.get('user_id') or session.get('is_admin'):
        return redirect(url_for('main.app_page'))
    
    # Get language from query param or session
    lang = request.args.get('lang', session.get('language', 'en'))
    session['language'] = lang
    
    # Get site settings - with DB guard
    try:
        settings = SiteSettings.query.first()
        if not settings:
            settings = SiteSettings()
            db.session.add(settings)
            db.session.commit()
    except Exception as e:
        print(f"Database error loading site settings: {e}")
        # Fallback to default settings object if DB not available
        settings = SiteSettings()
    
    # Parse social links JSON
    try:
        settings.social_links_parsed = json.loads(settings.social_links) if settings.social_links else {}
    except:
        settings.social_links_parsed = {}
    
    # Get published courses with DB guard
    courses = []
    stats = {'courses': '10+', 'students': '500+', 'certificates': '100+'}
    
    try:
        courses = Course.query.filter_by(is_published=True).limit(6).all()
        
        # Get raw stats
        course_count = Course.query.filter_by(is_published=True).count()
        student_count = User.query.filter_by(role='student').count()
        cert_count = Enrollment.query.filter_by(certificate_issued=True).count()
        
        # Format stats for display
        stats['courses'] = f"{course_count}+" if course_count > 0 else '10+'
        stats['students'] = f"{student_count}+" if student_count > 100 else '500+'
        stats['certificates'] = f"{cert_count}+" if cert_count > 0 else '100+'
    except Exception as e:
        print(f"Database error loading courses/stats: {e}")
    
    return render_template('landing.html', 
                         settings=settings, 
                         courses=courses,
                         stats=stats,
                         lang=lang,
                         current_year=datetime.now().year)

@main_bp.route('/app')
@main_bp.route('/app/')
def app_page():
    """Main application (requires authentication)"""
    # Check if user or admin is logged in
    if not session.get('user_id') and not session.get('is_admin'):
        return redirect(url_for('main.landing'))
    ai_chat_hidden = False
    try:
        from app.models import KeyValueSetting
        s = KeyValueSetting.query.filter_by(key='ai_chat_hidden').first()
        ai_chat_hidden = bool(s and s.value == '1')
    except Exception:
        pass
    return render_template('index.html', ai_chat_hidden=ai_chat_hidden)

@main_bp.route('/admin-login')
def admin_login():
    """Redirect to main admin login page"""
    return redirect('/admin/login')


@main_bp.route('/reset-password')
def reset_password_page():
    """Public landing for the emailed password-reset link.

    The page reads ?token=... from the URL, asks for + confirms the new
    password, and POSTs to /api/auth/reset-password.
    """
    token = (request.args.get('token') or '').strip()
    return render_template('reset_password.html', token=token)


# ----- v2 Phase 4–8 UI surfaces ---------------------------------------------

@main_bp.route('/guardian')
def guardian_portal():
    """Parent / guardian dashboard (calls /api/v1/guardian/dashboard)."""
    if not session.get('user_id'):
        return redirect(url_for('main.landing'))
    return render_template('guardian_dashboard.html')


@main_bp.route('/links')
def guardian_link_approve_page():
    """Learner-facing page to approve a guardian link request via consent token."""
    if not session.get('user_id'):
        return redirect(url_for('main.landing'))
    return render_template('links.html')


def _is_teacher_or_admin():
    if session.get('is_admin'):
        return True
    role = (session.get('role') or '').lower()
    return role in ('teacher', 'admin', 'instructor')


_FORBIDDEN_HTML = (
    '<!doctype html><html><head><meta charset="utf-8"><title>Forbidden</title>'
    '<link rel="stylesheet" href="/static/css/design-system.css"></head>'
    '<body data-skp-modern style="padding:48px;">'
    '<div class="skp-card" style="max-width:520px;margin:0 auto;text-align:center;">'
    '<h2>Teacher access required</h2>'
    '<p class="skp-card__meta">This page is available to instructors and admins only.</p>'
    '<p><a class="skp-btn skp-btn--secondary" href="/app">Back to app</a></p>'
    '</div></body></html>'
)


@main_bp.route('/authoring')
def authoring_wizard():
    """Instructor AI course-authoring wizard (calls /api/v1/authoring/drafts)."""
    if not session.get('user_id') and not session.get('is_admin'):
        return redirect(url_for('main.landing'))
    if not _is_teacher_or_admin():
        return _FORBIDDEN_HTML, 403
    return render_template('authoring_wizard.html')


@main_bp.route('/insights')
def cohort_insights():
    """Cohort analytics + at-risk view (calls /api/v1/insights/*)."""
    if not session.get('user_id') and not session.get('is_admin'):
        return redirect(url_for('main.landing'))
    if not _is_teacher_or_admin():
        return _FORBIDDEN_HTML, 403
    return render_template('cohort_analytics.html')


@main_bp.route('/integrations')
def integrations_page():
    """Teacher SCORM/xAPI integrations dashboard.
    Wraps POST /api/v1/scorm/upload, POST /api/v1/scorm/export,
    GET /api/v1/scorm/packages/<id>/download, GET /api/v1/xapi/statements,
    POST /api/v1/xapi/retry.
    """
    if not session.get('user_id') and not session.get('is_admin'):
        return redirect(url_for('main.landing'))
    if not _is_teacher_or_admin():
        return _FORBIDDEN_HTML, 403
    return render_template('integrations.html')


@main_bp.route('/community')
def community_page():
    """Forum threads + XP leaderboard (calls /api/v1/social + /api/v1/engagement)."""
    if not session.get('user_id'):
        return redirect(url_for('main.landing'))
    return render_template('community.html')

@main_bp.route('/health')
def health():
    return jsonify({
        'status': 'OK',
        'message': 'AIACMate Python server is running'
    })
