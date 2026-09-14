"""
SkillPilot - Site Settings Routes
Superadmin-only routes for managing site branding and configuration
"""

from flask import Blueprint, request, jsonify, session, current_app
import os
import uuid
from werkzeug.utils import secure_filename

site_settings_bp = Blueprint('site_settings', __name__)


def superadmin_required(f):
    """Decorator for superadmin-only routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401
        role = session.get('role', '').lower().replace(' ', '_')
        if role not in ['superadmin', 'super_admin']:
            return jsonify({'error': 'Superadmin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def get_site_settings():
    """Get or create site settings singleton"""
    try:
        from app.models import db, SiteSettings
        settings = SiteSettings.query.first()
        if not settings:
            settings = SiteSettings()
            db.session.add(settings)
            db.session.commit()
        return settings
    except Exception as e:
        print(f"Error getting site settings: {e}")
        return None


@site_settings_bp.route('/api/site-settings', methods=['GET'])
def get_settings():
    """Get current site settings (public endpoint for branding)"""
    try:
        settings = get_site_settings()
        if not settings:
            # Return defaults if no settings exist
            return jsonify({
                'success': True,
                'settings': {
                    'site_name': 'SkillPilot',
                    'site_name_ar': 'سكيل بايلوت',
                    'logo_url': None,
                    'logo_url_2': None,
                    'favicon_url': None,
                    'primary_color': '#1B5E20',
                    'secondary_color': '#2E7D32',
                    'hero_title': 'AI-Powered Training Platform',
                    'hero_title_ar': 'منصة تدريب مدعومة بالذكاء الاصطناعي',
                    'hero_subtitle': 'Empower your learning journey with cutting-edge AI technology',
                    'hero_subtitle_ar': 'مكّن رحلتك التعليمية بتقنية الذكاء الاصطناعي المتطورة',
                    'hero_image_url': None,
                    'footer_text': None,
                    'contact_email': None,
                    'allow_student_registration': True,
                    'allow_teacher_registration': True,
                    'paypal_link': None
                }
            })

        return jsonify({
            'success': True,
            'settings': {
                'id': settings.id,
                'site_name': settings.site_name,
                'site_name_ar': settings.site_name_ar,
                'logo_url': settings.logo_url,
                'logo_url_2': settings.logo_url_2,
                'favicon_url': settings.favicon_url,
                'primary_color': settings.primary_color,
                'secondary_color': settings.secondary_color,
                'hero_title': settings.hero_title,
                'hero_title_ar': settings.hero_title_ar,
                'hero_subtitle': settings.hero_subtitle,
                'hero_subtitle_ar': settings.hero_subtitle_ar,
                'hero_image_url': settings.hero_image_url,
                'footer_text': settings.footer_text,
                'contact_email': settings.contact_email,
                'allow_student_registration': settings.allow_student_registration,
                'allow_teacher_registration': settings.allow_teacher_registration,
                'attendance_tracking_enabled': getattr(settings, 'attendance_tracking_enabled', True),
                'paypal_link': settings.paypal_link,
                'updated_at': settings.updated_at.isoformat() if settings.updated_at else None
            }
        })
    except Exception as e:
        print(f"Error getting site settings: {e}")
        return jsonify({'error': str(e)}), 500


@site_settings_bp.route('/api/site-settings', methods=['PUT'])
@superadmin_required
def update_settings():
    """Update site settings (superadmin only)"""
    try:
        from app.models import db, SiteSettings

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        settings = get_site_settings()
        if not settings:
            settings = SiteSettings()
            db.session.add(settings)

        # Update branding fields
        if 'site_name' in data:
            settings.site_name = data['site_name']
        if 'site_name_ar' in data:
            settings.site_name_ar = data['site_name_ar']
        if 'logo_url' in data:
            settings.logo_url = data['logo_url']
        if 'logo_url_2' in data:
            settings.logo_url_2 = data['logo_url_2']
        if 'favicon_url' in data:
            settings.favicon_url = data['favicon_url']
        if 'primary_color' in data:
            settings.primary_color = data['primary_color']
        if 'secondary_color' in data:
            settings.secondary_color = data['secondary_color']

        # Update hero section
        if 'hero_title' in data:
            settings.hero_title = data['hero_title']
        if 'hero_title_ar' in data:
            settings.hero_title_ar = data['hero_title_ar']
        if 'hero_subtitle' in data:
            settings.hero_subtitle = data['hero_subtitle']
        if 'hero_subtitle_ar' in data:
            settings.hero_subtitle_ar = data['hero_subtitle_ar']
        if 'hero_image_url' in data:
            settings.hero_image_url = data['hero_image_url']

        # Update footer/contact
        if 'footer_text' in data:
            settings.footer_text = data['footer_text']
        if 'contact_email' in data:
            settings.contact_email = data['contact_email']

        # Update registration settings
        if 'allow_student_registration' in data:
            settings.allow_student_registration = data['allow_student_registration']
        if 'allow_teacher_registration' in data:
            settings.allow_teacher_registration = data['allow_teacher_registration']

        # Update feature toggles
        if 'attendance_tracking_enabled' in data:
            settings.attendance_tracking_enabled = bool(data['attendance_tracking_enabled'])

        # Update payment
        if 'paypal_link' in data:
            settings.paypal_link = data['paypal_link']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Site settings updated successfully'
        })
    except Exception as e:
        print(f"Error updating site settings: {e}")
        return jsonify({'error': str(e)}), 500


@site_settings_bp.route('/api/site-settings/upload-logo', methods=['POST'])
@superadmin_required
def upload_logo():
    """Upload a logo image (superadmin only)"""
    try:
        from app.models import db

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            return jsonify({'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}), 400

        # Generate unique filename
        filename = f"logo_{uuid.uuid4().hex[:8]}.{ext}"

        # Save to static/images folder
        upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'branding')
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, secure_filename(filename))
        file.save(filepath)

        # Return the URL path
        logo_url = f"/static/images/branding/{filename}"

        # Get logo type from form data
        logo_type = request.form.get('logo_type', 'primary')  # primary, secondary, favicon, hero

        # Update site settings if requested
        if request.form.get('update_settings') == 'true':
            settings = get_site_settings()
            if settings:
                if logo_type == 'primary':
                    settings.logo_url = logo_url
                elif logo_type == 'secondary':
                    settings.logo_url_2 = logo_url
                elif logo_type == 'favicon':
                    settings.favicon_url = logo_url
                elif logo_type == 'hero':
                    settings.hero_image_url = logo_url
                db.session.commit()

        return jsonify({
            'success': True,
            'url': logo_url,
            'filename': filename,
            'message': 'Logo uploaded successfully'
        })
    except Exception as e:
        print(f"Error uploading logo: {e}")
        return jsonify({'error': str(e)}), 500


@site_settings_bp.route('/api/site-settings/registration', methods=['GET'])
def get_registration_settings():
    """Get registration settings (public endpoint)"""
    try:
        settings = get_site_settings()
        return jsonify({
            'success': True,
            'allow_student_registration': settings.allow_student_registration if settings else True,
            'allow_teacher_registration': settings.allow_teacher_registration if settings else True,
            'attendance_tracking_enabled': getattr(settings, 'attendance_tracking_enabled', True) if settings else True
        })
    except Exception as e:
        return jsonify({
            'success': True,
            'allow_student_registration': True,
            'allow_teacher_registration': True,
            'attendance_tracking_enabled': True
        })
