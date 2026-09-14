from flask import Flask, session
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from config.config import Config
import os
from datetime import timedelta


class ReverseProxyMiddleware:
    """
    Middleware to handle reverse proxy with URL prefix.
    Reads X-Script-Name header from nginx to set SCRIPT_NAME correctly.
    This allows url_for() to generate URLs with the correct prefix.
    """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Get the script name from nginx header (e.g., /skillpilot)
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            # Ensure PATH_INFO doesn't duplicate the prefix and is never empty
            path_info = environ.get('PATH_INFO', '')
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):] or '/'
        
        # Handle forwarded scheme (http/https)
        scheme = environ.get('HTTP_X_FORWARDED_PROTO', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        
        return self.app(environ, start_response)


def create_app(config_class=Config):
    # Create Flask app with explicit template and static folder paths
    app = Flask(__name__,
                template_folder='../templates',  # Go up one level to find templates
                static_folder='../static')  # Go up one level to find static

    app.config.from_object(config_class)
    
    # Apply reverse proxy middleware - handles X-Script-Name from nginx
    # This allows Flask url_for() to generate URLs with the prefix (e.g., /skillpilot)
    app.wsgi_app = ReverseProxyMiddleware(app.wsgi_app)
    # ProxyFix handles X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Host
    # Note: We don't use x_prefix=1 because our middleware handles X-Script-Name
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    
    # Configure session
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=config_class.ADMIN_SESSION_TIMEOUT)
    
    # Configure PostgreSQL database
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 10,
            'pool_recycle': 300,
            'pool_pre_ping': True
        }
        
        # Initialize database
        from app.models import db
        db.init_app(app)

    # Initialize extensions
    CORS(app, supports_credentials=True)

    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.prompts import prompts_bp
    from app.routes.sessions import sessions_bp
    from app.routes.analytics import analytics_bp
    from app.routes.survey import survey_bp
    from app.routes.classes import classes_bp
    from app.routes.students import students_bp
    from app.routes.materials import materials_bp
    from app.routes.agents import agents_bp
    from app.routes.ethics import ethics_bp
    from app.routes.courses import courses_bp
    from app.routes.recommendations import recommendations_bp
    from app.routes.super_admin import super_admin_bp
    from app.routes.site_settings import site_settings_bp
    from app.routes.teacher import teacher_bp
    from app.routes.class_management import class_mgmt_bp
    from app.routes.student_class import student_class_bp
    from app.routes.attendance import attendance_bp
    from app.routes.ai_tools import ai_tools_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(prompts_bp, url_prefix='/api/prompts')
    app.register_blueprint(sessions_bp, url_prefix='/api/sessions')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(survey_bp)
    app.register_blueprint(classes_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(ethics_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(super_admin_bp)  # Routes under /admin
    app.register_blueprint(site_settings_bp)  # Site branding settings
    app.register_blueprint(teacher_bp)  # Routes under /api/teacher
    app.register_blueprint(class_mgmt_bp, url_prefix='/api')  # Class management routes
    app.register_blueprint(student_class_bp)  # Student class-centric routes
    app.register_blueprint(attendance_bp)  # Attendance management routes
    app.register_blueprint(ai_tools_bp)  # AI Tools for all users

    return app
