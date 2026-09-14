from flask import Flask, jsonify, request, session
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
    # Cookie hardening — auto-enable Secure when running behind HTTPS in prod.
    _is_prod = (os.environ.get('FLASK_ENV') == 'production'
                or os.environ.get('REPLIT_DEPLOYMENT') == '1'
                or os.environ.get('SKP_FORCE_SECURE_COOKIES') == '1')
    app.config['SESSION_COOKIE_SECURE'] = _is_prod
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=config_class.ADMIN_SESSION_TIMEOUT)
    
    # Configure PostgreSQL database
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        # SQLite (used in tests) does not support pool_size with the default
        # StaticPool, so only apply pool tuning to real (e.g. PostgreSQL) URIs.
        if database_url.startswith('sqlite'):
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
        else:
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
    from app.routes.ai_models import ai_models_bp
    from app.routes.prompts import prompts_bp
    from app.routes.sessions import sessions_bp
    from app.routes.analytics import analytics_bp
    from app.routes.survey import survey_bp
    from app.routes.classes import classes_bp
    from app.routes.students import students_bp
    from app.routes.materials import materials_bp
    from app.routes.agents import agents_bp
    from app.routes.ethics import ethics_bp, ethics_pages_bp
    from app.routes.courses import courses_bp
    from app.routes.recommendations import recommendations_bp
    from app.routes.super_admin import super_admin_bp
    from app.routes.site_settings import site_settings_bp
    from app.routes.teacher import teacher_bp
    from app.routes.class_management import class_mgmt_bp
    from app.routes.student_class import student_class_bp
    from app.routes.attendance import attendance_bp
    from app.routes.ai_tools import ai_tools_bp
    from app.routes.personalization import personalization_bp
    from app.routes.tutor import tutor_bp
    from app.routes.assessments import assessments_bp
    # v2 Phases 4–8 (additive)
    from app.routes.authoring import authoring_bp, scorm_bp, xapi_bp
    from app.routes.social import (
        engagement_bp, social_bp, guardian_bp, live_bp,
    )
    from app.routes.insights import insights_bp
    from app.routes.notifications import notifications_bp
    from app.routes.developer import developer_bp
    from app.routes.skillmatch import skillmatch_bp, pd_bp
    from app.routes.enterprise import (
        enterprise_bp, sso_bp, keys_bp, audit_bp, compliance_bp,
        accessibility_bp, public_api_bp, spec_bp,
    )

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    # The blueprint carries its own /api/ai-models prefix.
    app.register_blueprint(ai_models_bp)
    app.register_blueprint(prompts_bp, url_prefix='/api/prompts')
    app.register_blueprint(sessions_bp, url_prefix='/api/sessions')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(survey_bp)
    app.register_blueprint(classes_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(ethics_bp)
    app.register_blueprint(ethics_pages_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(super_admin_bp)  # Routes under /admin
    app.register_blueprint(site_settings_bp)  # Site branding settings
    app.register_blueprint(teacher_bp)  # Routes under /api/teacher
    app.register_blueprint(class_mgmt_bp, url_prefix='/api')  # Class management routes
    app.register_blueprint(student_class_bp)  # Student class-centric routes
    app.register_blueprint(attendance_bp)  # Attendance management routes
    app.register_blueprint(ai_tools_bp)  # AI Tools for all users
    app.register_blueprint(personalization_bp)  # v2 Phase 1 personalization API
    app.register_blueprint(tutor_bp)  # v2 Phase 2 adaptive tutor API
    app.register_blueprint(assessments_bp)  # v2 Phase 3 smart assessment + proctoring
    # v2 Phases 4–8 (additive — never overlaps existing /api/* paths)
    app.register_blueprint(authoring_bp)
    app.register_blueprint(scorm_bp)
    app.register_blueprint(xapi_bp)
    app.register_blueprint(engagement_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(guardian_bp)
    app.register_blueprint(live_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(developer_bp)
    app.register_blueprint(skillmatch_bp)
    app.register_blueprint(pd_bp)
    app.register_blueprint(enterprise_bp)
    app.register_blueprint(sso_bp)
    app.register_blueprint(keys_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(compliance_bp)
    app.register_blueprint(accessibility_bp)
    app.register_blueprint(public_api_bp)
    app.register_blueprint(spec_bp)

    # Phases 1 + 4–8 — auto-create new tables.
    # Safe & idempotent: SQLAlchemy's create_all() only creates tables that
    # are missing and never alters or drops existing ones.
    # Failures are logged loudly so deployment problems aren't silently masked.
    if database_url:
        import logging, traceback
        _log = logging.getLogger(__name__)
        try:
            from app.models import db as _db
            with app.app_context():
                _db.create_all()
                # Lightweight in-place column additions for existing tables.
                # SQLAlchemy's create_all() only creates *missing tables*; it
                # never ALTERs existing ones. We sync optional columns from the
                # model metadata to the live DB so newly-added model columns
                # don't break runtime queries (poisoned transactions cascade
                # into "loading information" failures across the UI).
                try:
                    from sqlalchemy import inspect, text
                    from sqlalchemy.schema import CreateColumn
                    insp = inspect(_db.engine)
                    db_tables = set(insp.get_table_names())
                    dialect = _db.engine.dialect.name
                    added = []
                    for tbl_name, tbl in _db.metadata.tables.items():
                        if tbl_name not in db_tables:
                            continue
                        existing = {c['name'] for c in insp.get_columns(tbl_name)}
                        for col in tbl.columns:
                            if col.name in existing:
                                continue
                            if not col.nullable and col.server_default is None and col.default is None:
                                _log.warning(
                                    "[init] skipping NOT NULL column without default: %s.%s",
                                    tbl_name, col.name)
                                continue
                            try:
                                col_sql = str(CreateColumn(col).compile(_db.engine))
                                with _db.engine.begin() as conn:
                                    conn.execute(text(
                                        f'ALTER TABLE "{tbl_name}" ADD COLUMN IF NOT EXISTS {col_sql}'
                                        if dialect == 'postgresql'
                                        else f'ALTER TABLE {tbl_name} ADD COLUMN {col_sql}'
                                    ))
                                added.append(f"{tbl_name}.{col.name}")
                            except Exception as _col_err:
                                _log.warning(
                                    "[init] add column %s.%s skipped: %s",
                                    tbl_name, col.name, _col_err)
                    if added:
                        _log.info("[init] auto-added missing columns: %s", ", ".join(added))
                        print(f"[init] auto-added missing columns: {', '.join(added)}", flush=True)
                except Exception as _mig_err:
                    _log.warning("[init] column auto-sync skipped: %s", _mig_err)
        except Exception as _e:
            tb = traceback.format_exc()
            _log.error("[init] create_all() FAILED — personalization tables "
                       "may be missing; new endpoints will error at runtime: %s\n%s",
                       _e, tb)
            print(f"[init] CRITICAL: create_all() failed: {_e}\n{tb}", flush=True)
            app.config['SKP_DB_INIT_ERROR'] = str(_e)

    # Optional background ingestion of labour-market signals (Phase 7).
    # Opt-in via env var; no-op when unset.
    try:
        from app.services.labour_market_service import start_scheduler
        start_scheduler(app)
    except Exception as _sch_err:
        import logging
        logging.getLogger(__name__).warning(
            "[init] labour-market scheduler not started: %s", _sch_err)

    # ---- PWA: serve service worker + manifest from root ---------------------
    # Browsers restrict a service worker's scope to its own URL path. To let
    # `/static/sw.js` control the entire site, we re-serve it from `/sw.js`
    # (and add `Service-Worker-Allowed: /` for belt-and-braces). The manifest
    # is also exposed at `/manifest.json` so installability checks pass even
    # when reverse proxies strip /static prefixes.
    from flask import send_from_directory as _sfd
    import os as _os
    _STATIC_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'static')

    @app.route('/sw.js')
    def _serve_sw():
        resp = _sfd(_STATIC_DIR, 'sw.js', mimetype='text/javascript')
        resp.headers['Service-Worker-Allowed'] = '/'
        resp.headers['Cache-Control'] = 'no-cache'
        return resp

    @app.route('/manifest.json')
    def _serve_manifest():
        return _sfd(_STATIC_DIR, 'manifest.json', mimetype='application/manifest+json')

    @app.route('/clear-cache')
    def _clear_cache_page():
        """One-click page to unregister the service worker and hard-reload."""
        html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Clearing cache…</title>
<style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;
height:100vh;margin:0;background:#f0fdf4;flex-direction:column;gap:16px;}
h2{color:#0d9488;}p{color:#555;}#status{font-weight:600;color:#166534;}</style>
</head>
<body>
<h2>🔄 Clearing browser cache…</h2>
<p>This takes a moment. You will be redirected automatically.</p>
<p id="status">Unregistering service worker…</p>
<script>
(async function() {
  const s = document.getElementById('status');
  try {
    if ('serviceWorker' in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations();
      for (const r of regs) await r.unregister();
      s.textContent = 'Service worker removed. Clearing caches…';
    }
    if ('caches' in window) {
      const keys = await caches.keys();
      await Promise.all(keys.map(k => caches.delete(k)));
      s.textContent = 'All caches cleared. Redirecting…';
    }
  } catch(e) { s.textContent = 'Done (some items may remain). Redirecting…'; }
  setTimeout(() => { window.location.href = '/'; }, 1200);
})();
</script>
</body></html>"""
        from flask import Response
        return Response(html, mimetype='text/html',
                        headers={'Cache-Control': 'no-store, no-cache, must-revalidate'})

    # ---- Defensive HTTP security headers ----------------------------------
    # Defence-in-depth against the ~280 innerHTML sites still in static/js/*.
    # CSP is intentionally permissive (allows 'unsafe-inline') because the
    # codebase relies on inline scripts/styles in many Jinja templates;
    # tightening to a nonce-based CSP is tracked as future work.
    @app.after_request
    def _set_security_headers(resp):
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        resp.headers.setdefault(
            'Permissions-Policy',
            'geolocation=(), microphone=(), camera=(self), payment=(self)'
        )
        if _is_prod:
            resp.headers.setdefault(
                'Strict-Transport-Security',
                'max-age=31536000; includeSubDomains'
            )
        # Don't apply CSP to static assets (would block legitimate inline
        # styles in some legacy admin templates pending refactor).
        if not (resp.mimetype or '').startswith(('image/', 'font/')):
            resp.headers.setdefault(
                'Content-Security-Policy',
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self' data: https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
                "connect-src 'self' https:; "
                "frame-ancestors 'self'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        return resp

    # ---- API errors must be JSON ------------------------------------------
    # Flask answers an error with an HTML page. Every screen in this platform
    # reads its API responses with `r.json()`, so any 404, 405, 415 or crash
    # reached the user as
    #     Unexpected token '<', "<!doctype "... is not valid JSON
    # which says nothing about what went wrong. Under /api/ the same errors
    # are returned as JSON, with the HTML pages left alone everywhere else.
    from werkzeug.exceptions import HTTPException

    def _is_api_request() -> bool:
        return '/api/' in request.path

    @app.errorhandler(HTTPException)
    def _http_error(error):
        if not _is_api_request():
            return error
        return jsonify({
            'error': error.description or error.name,
            'status': error.code,
        }), error.code or 500

    @app.errorhandler(Exception)
    def _unexpected_error(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception('Unhandled error on %s', request.path)
        if not _is_api_request():
            raise error
        # The detail goes to the log, not to the browser.
        return jsonify({
            'error': 'The server hit an unexpected error handling this '
                     'request. Check server.log for the details.',
            'status': 500,
        }), 500

    return app
