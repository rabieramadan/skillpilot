"""Phase 4 — Authoring & SCORM/xAPI."""


def test_create_draft_requires_login(client):
    r = client.post('/api/v1/authoring/drafts', json={'title': 'X'})
    assert r.status_code == 401


def test_create_draft_requires_teacher(client, login_as):
    login_as('student')
    r = client.post('/api/v1/authoring/drafts', json={'title': 'X'})
    assert r.status_code == 403


def test_create_and_score_draft(client, login_as):
    login_as('teacher')
    r = client.post('/api/v1/authoring/drafts', json={
        'title': 'Intro to AI', 'title_ar': 'مقدمة',
        'topic': 'ai', 'language': 'en',
        'use_ai': True, 'weeks_count': 4,
        'ethics_tags': ['fairness'],
    })
    assert r.status_code == 201
    body = r.get_json()
    draft = body['draft']
    assert draft['title'] == 'Intro to AI'
    assert draft['weeks'] and len(draft['weeks']) == 4
    assert draft['learning_outcomes']
    did = draft['id']

    # Score
    r2 = client.post(f'/api/v1/authoring/drafts/{did}/score')
    assert r2.status_code == 200
    sc = r2.get_json()
    assert 0.0 <= sc['quality_score'] <= 100.0
    assert sc['breakdown']['weeks_count'] == 4
    assert sc['breakdown']['has_arabic_title'] is True


def test_invalid_language_rejected(client, login_as):
    login_as('teacher')
    r = client.post('/api/v1/authoring/drafts',
                    json={'title': 'X', 'language': 'fr'})
    assert r.status_code == 400


def test_publish_draft_creates_course(client, login_as):
    login_as('teacher')
    r = client.post('/api/v1/authoring/drafts',
                    json={'title': 'Pub', 'use_ai': True, 'weeks_count': 2})
    did = r.get_json()['draft']['id']
    r2 = client.post(f'/api/v1/authoring/drafts/{did}/publish')
    assert r2.status_code == 200
    body = r2.get_json()
    assert body['course_id']
    assert body['draft']['status'] == 'published'


def test_versions_listing(client, login_as):
    login_as('teacher')
    r = client.post('/api/v1/authoring/drafts',
                    json={'title': 'V', 'use_ai': True, 'weeks_count': 2})
    did = r.get_json()['draft']['id']
    # Update once -> should create version 2
    client.put(f'/api/v1/authoring/drafts/{did}',
               json={'title': 'V2', 'change_note': 'rename'})
    r2 = client.get(f'/api/v1/authoring/versions',
                    query_string={'content_type': 'draft', 'content_id': did})
    assert r2.status_code == 200
    versions = r2.get_json()['versions']
    assert {v['version_number'] for v in versions} >= {1, 2}


def test_other_teacher_cannot_access_draft(client, login_as, login):
    teacher_a = login_as('teacher', 'teacher_a')
    r = client.post('/api/v1/authoring/drafts', json={'title': 'mine'})
    did = r.get_json()['draft']['id']

    # Switch to another teacher
    other = login_as('teacher', 'teacher_b')
    assert other != teacher_a
    r2 = client.get(f'/api/v1/authoring/drafts/{did}')
    assert r2.status_code == 403


def test_scorm_import_validates_version(client, login_as):
    login_as('teacher')
    r = client.post('/api/v1/scorm/import',
                    json={'package_name': 'p.zip', 'scorm_version': '9000'})
    assert r.status_code == 400


def test_scorm_import_records_metadata(client, login_as):
    login_as('teacher')
    r = client.post('/api/v1/scorm/import', json={
        'package_name': 'p.zip', 'scorm_version': '2004',
        'manifest': {'title': 'Test'}, 'storage_path': '/tmp/p.zip',
    })
    assert r.status_code == 201
    pkg_id = r.get_json()['id']

    r2 = client.get('/api/v1/scorm/packages')
    assert any(p['id'] == pkg_id for p in r2.get_json()['packages'])

    r3 = client.get(f'/api/v1/scorm/packages/{pkg_id}/manifest')
    assert r3.status_code == 200
    assert r3.get_json()['manifest']['title'] == 'Test'


def test_integrations_page_teacher_allowed(client, login_as):
    login_as('teacher')
    r = client.get('/integrations')
    assert r.status_code == 200
    assert b'integrations' in r.data.lower()


def test_integrations_page_student_forbidden(client, login_as):
    login_as('student')
    r = client.get('/integrations')
    assert r.status_code == 403


def test_integrations_page_anonymous_redirects(client):
    r = client.get('/integrations')
    assert r.status_code in (301, 302)


def test_scorm_packages_scoped_to_owner_for_teacher(client, login_as):
    """Teacher A must not see, fetch the manifest of, or download
    SCORM packages created by teacher B."""
    teacher_a = login_as('teacher', 'teacher_a')
    r = client.post('/api/v1/scorm/import', json={
        'package_name': 'A.zip', 'scorm_version': '2004',
        'manifest': {'title': 'A'}, 'storage_path': '/tmp/A.zip',
    })
    a_pkg = r.get_json()['id']

    teacher_b = login_as('teacher', 'teacher_b')
    assert teacher_b != teacher_a
    r = client.post('/api/v1/scorm/import', json={
        'package_name': 'B.zip', 'scorm_version': '2004',
        'manifest': {'title': 'B'}, 'storage_path': '/tmp/B.zip',
    })
    b_pkg = r.get_json()['id']

    # Listing as teacher B returns only B's packages
    r2 = client.get('/api/v1/scorm/packages')
    ids = {p['id'] for p in r2.get_json()['packages']}
    assert b_pkg in ids and a_pkg not in ids

    # Manifest of A's package is forbidden for B
    r3 = client.get(f'/api/v1/scorm/packages/{a_pkg}/manifest')
    assert r3.status_code == 403

    # Download of A's package is forbidden for B
    r4 = client.get(f'/api/v1/scorm/packages/{a_pkg}/download')
    assert r4.status_code == 403


def test_scorm_admin_sees_all_packages(client, login_as):
    login_as('teacher', 'teacher_a')
    client.post('/api/v1/scorm/import', json={
        'package_name': 'A.zip', 'scorm_version': '2004',
        'manifest': {'title': 'A'}, 'storage_path': '/tmp/A.zip',
    })
    login_as('teacher', 'teacher_b')
    client.post('/api/v1/scorm/import', json={
        'package_name': 'B.zip', 'scorm_version': '2004',
        'manifest': {'title': 'B'}, 'storage_path': '/tmp/B.zip',
    })
    login_as('admin', 'admin_x')
    r = client.get('/api/v1/scorm/packages')
    names = {p['package_name'] for p in r.get_json()['packages']}
    assert {'A.zip', 'B.zip'}.issubset(names)


def test_xapi_retry_scoped_to_actor_for_teacher(client, login_as, db, app):
    """A teacher's retry must NOT touch other users' failed statements."""
    from app.models import XApiStatement
    teacher_a = login_as('teacher', 'teacher_a')
    teacher_b_id = None
    with app.app_context():
        # Failed statement owned by another user
        other = XApiStatement(
            actor_user_id='someone-else',
            verb='completed',
            statement={'a': 1},
            delivery_status='failed',
            delivery_error='boom',
        )
        # Failed statement owned by teacher_a
        mine = XApiStatement(
            actor_user_id=teacher_a,
            verb='completed',
            statement={'a': 2},
            delivery_status='failed',
            delivery_error='boom',
        )
        db.session.add_all([other, mine])
        db.session.commit()
        other_id = other.id
        mine_id = mine.id

    r = client.post('/api/v1/xapi/retry', json={'limit': 50})
    assert r.status_code == 200
    body = r.get_json()
    # Only teacher_a's one failed statement should be attempted.
    assert body['attempted'] == 1

    with app.app_context():
        still = XApiStatement.query.filter_by(id=other_id).first()
        assert still.delivery_status == 'failed'  # untouched


def test_xapi_retry_admin_global(client, login_as, db, app):
    """Admins retry across all actors."""
    from app.models import XApiStatement
    login_as('admin', 'admin_x')
    with app.app_context():
        for actor in ('u1', 'u2', 'u3'):
            db.session.add(XApiStatement(
                actor_user_id=actor, verb='completed',
                statement={'k': actor}, delivery_status='failed',
                delivery_error='boom',
            ))
        db.session.commit()
    r = client.post('/api/v1/xapi/retry', json={'limit': 50})
    assert r.status_code == 200
    assert r.get_json()['attempted'] == 3


def test_xapi_retry_denies_students(client, login_as):
    login_as('student')
    r = client.post('/api/v1/xapi/retry', json={'limit': 50})
    assert r.status_code == 403


class _FakeResponse:
    """Stand-in for ``requests.Response`` exposing only what we use."""
    def __init__(self, status_code, text=''):
        self.status_code = status_code
        self.text = text


class _FakeTransport:
    """Records every call and returns canned responses in order.

    Mirrors ``requests.post(url, json=..., headers=..., auth=..., timeout=...)``.
    """
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def __call__(self, url, *, json=None, headers=None, auth=None, timeout=None):
        self.calls.append({'url': url, 'json': json, 'headers': headers,
                            'auth': auth, 'timeout': timeout})
        r = self._responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def _make_pending_statement(db, app, *, actor='actor-a', endpoint='https://lrs.example/xapi/statements'):
    from app.models import XApiStatement
    with app.app_context():
        s = XApiStatement(
            actor_user_id=actor,
            verb='completed',
            statement={'actor': actor, 'verb': 'completed', 'object': 'L1'},
            lrs_endpoint=endpoint,
            delivery_status='pending',
        )
        db.session.add(s)
        db.session.commit()
        sid = s.id
    return sid


def test_deliver_statement_success_path_posts_to_lrs(app, db, monkeypatch):
    """200 OK -> delivery_status=sent, sent_at set, single transport call."""
    from app.models import XApiStatement
    from app.services import xapi_service
    monkeypatch.setenv('XAPI_LRS_USERNAME', 'lrs-key')
    monkeypatch.setenv('XAPI_LRS_PASSWORD', 'lrs-secret')
    monkeypatch.setenv('XAPI_LRS_VERSION', '1.0.3')

    sid = _make_pending_statement(db, app)
    transport = _FakeTransport([_FakeResponse(204)])
    sleeps = []

    with app.app_context():
        s = XApiStatement.query.get(sid)
        res = xapi_service.deliver_statement(
            s, transport=transport, sleep=sleeps.append)
        db.session.commit()

    assert res == {'ok': True, 'status_code': 204, 'error': None}
    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call['url'] == 'https://lrs.example/xapi/statements'
    assert call['auth'] == ('lrs-key', 'lrs-secret')
    assert call['headers']['X-Experience-API-Version'] == '1.0.3'
    assert call['headers']['Content-Type'] == 'application/json'
    assert call['json'] == {'actor': 'actor-a', 'verb': 'completed', 'object': 'L1'}
    assert sleeps == []  # success on first try -> no backoff

    with app.app_context():
        s = XApiStatement.query.get(sid)
        assert s.delivery_status == 'sent'
        assert s.sent_at is not None
        assert s.delivery_error is None


def test_deliver_statement_retries_on_5xx_then_succeeds(app, db):
    """Transient 5xx errors are retried with backoff; success ends the loop."""
    from app.models import XApiStatement
    from app.services import xapi_service

    sid = _make_pending_statement(db, app)
    transport = _FakeTransport([
        _FakeResponse(503, 'overloaded'),
        _FakeResponse(429, 'slow down'),
        _FakeResponse(200, 'ok'),
    ])
    sleeps = []

    with app.app_context():
        s = XApiStatement.query.get(sid)
        res = xapi_service.deliver_statement(
            s, transport=transport, sleep=sleeps.append)
        db.session.commit()

    assert res['ok'] is True
    assert res['status_code'] == 200
    assert len(transport.calls) == 3
    assert len(sleeps) == 2  # one backoff between each of the 3 attempts
    # Exponential backoff: 0.5 * 2**0, 0.5 * 2**1
    assert sleeps == [0.5, 1.0]

    with app.app_context():
        s = XApiStatement.query.get(sid)
        assert s.delivery_status == 'sent'
        assert s.delivery_error is None


def test_deliver_statement_exhausts_retries_and_marks_failed(app, db, monkeypatch):
    """Persistent 5xx after max_retries -> delivery_status=failed with error."""
    from app.models import XApiStatement
    from app.services import xapi_service
    monkeypatch.setenv('XAPI_LRS_MAX_RETRIES', '3')

    sid = _make_pending_statement(db, app)
    transport = _FakeTransport([
        _FakeResponse(500, 'boom1'),
        _FakeResponse(502, 'boom2'),
        _FakeResponse(503, 'boom3'),
    ])
    sleeps = []

    with app.app_context():
        s = XApiStatement.query.get(sid)
        res = xapi_service.deliver_statement(
            s, transport=transport, sleep=sleeps.append)
        db.session.commit()

    assert res['ok'] is False
    assert res['status_code'] == 503
    assert 'LRS error (503)' in res['error']
    assert len(transport.calls) == 3
    assert len(sleeps) == 3  # one sleep after each failed attempt

    with app.app_context():
        s = XApiStatement.query.get(sid)
        assert s.delivery_status == 'failed'
        assert s.sent_at is None
        assert 'boom3' in (s.delivery_error or '')


def test_deliver_statement_4xx_does_not_retry(app, db):
    """Non-retryable 4xx (e.g. 400) breaks immediately — no second POST."""
    from app.models import XApiStatement
    from app.services import xapi_service

    sid = _make_pending_statement(db, app)
    transport = _FakeTransport([
        _FakeResponse(400, 'bad statement'),
        _FakeResponse(200, 'unused'),
    ])
    sleeps = []

    with app.app_context():
        s = XApiStatement.query.get(sid)
        res = xapi_service.deliver_statement(
            s, transport=transport, sleep=sleeps.append)
        db.session.commit()

    assert res['ok'] is False
    assert res['status_code'] == 400
    assert 'LRS rejected (400)' in res['error']
    assert len(transport.calls) == 1
    assert sleeps == []  # break before any backoff

    with app.app_context():
        s = XApiStatement.query.get(sid)
        assert s.delivery_status == 'failed'
        assert 'bad statement' in (s.delivery_error or '')


def test_deliver_statement_transport_exception_is_retried(app, db):
    """Network exceptions are caught, retried, and counted as transport errors."""
    from app.models import XApiStatement
    from app.services import xapi_service

    sid = _make_pending_statement(db, app)
    transport = _FakeTransport([
        ConnectionError('connection refused'),
        _FakeResponse(204),
    ])
    sleeps = []

    with app.app_context():
        s = XApiStatement.query.get(sid)
        res = xapi_service.deliver_statement(
            s, transport=transport, sleep=sleeps.append)
        db.session.commit()

    assert res['ok'] is True
    assert len(transport.calls) == 2
    assert sleeps == [0.5]

    with app.app_context():
        s = XApiStatement.query.get(sid)
        assert s.delivery_status == 'sent'


def test_retry_failed_passes_transport_through(app, db):
    """retry_failed() forwards the injected transport to deliver_statement."""
    from app.models import XApiStatement
    from app.services import xapi_service

    with app.app_context():
        good = XApiStatement(
            actor_user_id='u1', verb='completed',
            statement={'k': 'good'},
            lrs_endpoint='https://lrs.example/xapi/statements',
            delivery_status='failed', delivery_error='boom',
        )
        bad = XApiStatement(
            actor_user_id='u1', verb='completed',
            statement={'k': 'bad'},
            lrs_endpoint='https://lrs.example/xapi/statements',
            delivery_status='failed', delivery_error='boom',
        )
        db.session.add_all([good, bad])
        db.session.commit()
        good_id, bad_id = good.id, bad.id

        transport = _FakeTransport([
            _FakeResponse(204),       # good
            _FakeResponse(500), _FakeResponse(500), _FakeResponse(500),  # bad
        ])
        out = xapi_service.retry_failed(
            limit=10, actor_user_id='u1',
            transport=transport, sleep=lambda _s: None)

    assert out == {'attempted': 2, 'sent': 1, 'failed': 1}
    with app.app_context():
        assert XApiStatement.query.get(good_id).delivery_status == 'sent'
        assert XApiStatement.query.get(bad_id).delivery_status == 'failed'


def test_xapi_emit_route_records_delivery_status_when_lrs_configured(
        client, login_as, db, app, monkeypatch):
    """End-to-end: route -> service -> stubbed transport -> DB updated."""
    from app.models import XApiStatement
    from app.services import xapi_service

    monkeypatch.setenv('XAPI_LRS_ENDPOINT', 'https://lrs.example/xapi/statements')
    transport = _FakeTransport([_FakeResponse(204)])
    real = xapi_service.deliver_statement
    monkeypatch.setattr(
        xapi_service, 'deliver_statement',
        lambda row, **kw: real(row, transport=transport,
                                sleep=lambda _s: None, **kw))
    # The route imports the symbol locally, so patch the route's lookup too.
    from app.routes import authoring as authoring_routes
    monkeypatch.setattr(
        authoring_routes, 'deliver_statement',
        lambda row, **kw: real(row, transport=transport,
                                sleep=lambda _s: None, **kw),
        raising=False)

    login_as('student')
    r = client.post('/api/v1/xapi/statements', json={
        'verb': 'completed',
        'object_type': 'lesson', 'object_id': 'L1',
        'statement': {'actor': 'me', 'verb': 'completed', 'object': 'L1'},
    })
    assert r.status_code == 201
    body = r.get_json()
    assert body['delivery_status'] == 'sent'
    assert len(transport.calls) == 1
    assert transport.calls[0]['url'] == 'https://lrs.example/xapi/statements'

    with app.app_context():
        rows = XApiStatement.query.all()
        assert len(rows) == 1
        assert rows[0].delivery_status == 'sent'
        assert rows[0].sent_at is not None


def test_xapi_emit_and_list_no_lrs(client, login_as):
    login_as('student')
    r = client.post('/api/v1/xapi/statements', json={
        'verb': 'completed',
        'object_type': 'lesson', 'object_id': 'L1',
        'statement': {'actor': 'me', 'verb': 'completed', 'object': 'L1'},
    })
    assert r.status_code == 201
    body = r.get_json()
    # No XAPI_LRS_ENDPOINT configured -> service marks as 'sent' locally.
    assert body['delivery_status'] in ('sent', 'pending')

    r2 = client.get('/api/v1/xapi/statements')
    assert r2.status_code == 200
    assert r2.get_json()['count'] >= 1
