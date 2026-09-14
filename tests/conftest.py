"""
Test harness for SkillPilot Phases 4–8 APIs.

Spins up the Flask app against an in-memory SQLite database and exposes
fixtures for creating users, logging them in via the session cookie, and
minting Bearer API keys for the public REST surface.
"""
import hashlib
import os
import secrets

# Force a clean test environment BEFORE the app is imported so create_app()
# wires SQLAlchemy to SQLite and skips any background schedulers.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.pop('LABOUR_MARKET_SYNC_INTERVAL_HOURS', None)
os.environ.pop('XAPI_LRS_ENDPOINT', None)

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db as _db


@pytest.fixture(scope='session')
def app():
    a = create_app()
    a.config['TESTING'] = True
    a.config['WTF_CSRF_ENABLED'] = False
    return a


@pytest.fixture(autouse=True)
def _fresh_db(app):
    """Reset the schema between tests so each one starts from a clean slate."""
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield
        _db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


# ---------- helpers exposed as fixtures -----------------------------------

def _create_user(role='student', username=None):
    from app.models import User
    if username:
        existing = User.query.filter_by(username=username).first()
        if existing:
            return existing
    u = User(
        username=username or f'{role}_{secrets.token_hex(3)}',
        full_name=f'{role.title()} User',
        email=f'{role}_{secrets.token_hex(3)}@test.local',
        role=role,
        password_hash=generate_password_hash('pw'),
    )
    _db.session.add(u)
    _db.session.commit()
    return u


@pytest.fixture
def make_user(app):
    """Factory: returns a User row inside an app context."""
    def _factory(role='student', username=None):
        with app.app_context():
            u = _create_user(role, username)
            return {'id': u.id, 'role': u.role, 'username': u.username}
    return _factory


@pytest.fixture
def login(client):
    """Force a Flask session as the given (user_id, role).

    Sets ``logged_in`` and ``is_admin`` too so legacy blueprints (courses,
    survey, etc.) that key off those keys also recognise the user.
    """
    def _login(user_id, role):
        with client.session_transaction() as s:
            s['user_id'] = user_id
            s['role'] = role
            s['logged_in'] = True
            normalised = (role or '').lower().replace(' ', '_')
            s['is_admin'] = normalised in (
                'admin', 'super_admin', 'superadmin', 'institution_admin'
            )
    return _login


@pytest.fixture
def login_as(client, make_user, login):
    """Create a user with the given role and log them in. Returns user_id."""
    def _login_as(role='student', username=None):
        u = make_user(role, username)
        login(u['id'], u['role'])
        return u['id']
    return _login_as


@pytest.fixture
def api_key(app):
    """Mint a public-API Bearer key. Returns (raw_key, key_id)."""
    def _factory(scopes, organization_id=None):
        from app.models import ApiKey
        with app.app_context():
            raw = 'sp_' + secrets.token_urlsafe(20)
            h = hashlib.sha256(raw.encode()).hexdigest()
            k = ApiKey(
                name='test', prefix=raw[:8], key_hash=h,
                scopes=scopes, organization_id=organization_id,
            )
            _db.session.add(k)
            _db.session.commit()
            return raw, k.id
    return _factory


@pytest.fixture
def db(app):
    """Expose the SQLAlchemy instance for tests that need to insert fixtures."""
    return _db
