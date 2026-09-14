from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, send_from_directory
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
    return render_template('index.html')

@main_bp.route('/admin-login')
def admin_login():
    """Redirect to main admin login page"""
    return redirect('/admin/login')

@main_bp.route('/health')
def health():
    return jsonify({
        'status': 'OK',
        'message': 'AIACMate Python server is running'
    })
