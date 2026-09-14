"""Phase 2 — Adaptive AI Tutor (`/api/v1/tutor/*`)."""
import uuid


def _make_course(db, app, **overrides):
    from app.models import Course
    with app.app_context():
        c = Course(id=str(uuid.uuid4()),
                   title=overrides.get('title', 'TutorCourse'),
                   code='T1', is_published=True)
        db.session.add(c)
        db.session.commit()
        return c.id


def test_context_requires_login(client):
    r = client.get('/api/v1/tutor/context')
    assert r.status_code == 401


def test_context_requires_course_id(client, login_as):
    login_as('student')
    r = client.get('/api/v1/tutor/context')
    assert r.status_code == 400


def test_context_blocks_unenrolled_student(client, login_as, db, app):
    login_as('student')
    cid = _make_course(db, app)
    r = client.get('/api/v1/tutor/context', query_string={'course_id': cid})
    assert r.status_code == 403


def test_context_for_teacher_returns_payload(client, login_as, db, app):
    login_as('teacher')
    cid = _make_course(db, app, title='ContextCourse')
    r = client.get('/api/v1/tutor/context', query_string={'course_id': cid})
    assert r.status_code == 200
    body = r.get_json()
    assert body['course']['id'] == cid
    assert 'learner' in body


def test_context_404_for_unknown_course(client, login_as):
    login_as('teacher')
    r = client.get('/api/v1/tutor/context',
                   query_string={'course_id': 'nope-id'})
    # Teacher has implicit access; course missing -> 404
    assert r.status_code == 404


def test_chat_requires_login(client):
    r = client.post('/api/v1/tutor/chat', json={})
    assert r.status_code == 401


def test_chat_requires_course_and_message(client, login_as):
    login_as('student')
    r = client.post('/api/v1/tutor/chat', json={})
    assert r.status_code == 400


def test_chat_blocks_unenrolled_student(client, login_as, db, app):
    login_as('student')
    cid = _make_course(db, app)
    r = client.post('/api/v1/tutor/chat',
                    json={'course_id': cid, 'message': 'hi'})
    assert r.status_code == 403


def test_chat_returns_400_when_provider_missing_key(client, login_as, db, app, monkeypatch):
    """When provider key is missing, tutor should refuse cleanly with 400."""
    from app.routes import tutor as tutor_mod
    monkeypatch.setattr(tutor_mod, '_resolve_api_key', lambda provider: None)
    login_as('teacher')
    cid = _make_course(db, app)
    r = client.post('/api/v1/tutor/chat',
                    json={'course_id': cid, 'message': 'hi',
                          'provider': 'openai'})
    assert r.status_code == 400
    body = r.get_json()
    assert 'not configured' in body['error']


def test_avatar_requires_text(client, login_as):
    login_as('student')
    r = client.post('/api/v1/tutor/avatar', json={})
    assert r.status_code == 400


def test_avatar_requires_login(client):
    r = client.post('/api/v1/tutor/avatar', json={'text': 'hi'})
    assert r.status_code == 401


def test_recompute_requires_login(client):
    r = client.post('/api/v1/tutor/recompute', json={})
    assert r.status_code == 401


def test_recompute_blocks_unenrolled_student(client, login_as, db, app):
    login_as('student')
    cid = _make_course(db, app)
    r = client.post('/api/v1/tutor/recompute', json={'course_id': cid})
    assert r.status_code == 403


def test_recompute_for_teacher_runs(client, login_as, db, app):
    login_as('teacher')
    cid = _make_course(db, app)
    r = client.post('/api/v1/tutor/recompute', json={'course_id': cid})
    assert r.status_code == 200
    assert r.get_json()['success'] is True
