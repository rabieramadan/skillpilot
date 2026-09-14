"""Phase 8 — Enterprise, audit, compliance, accessibility."""


def test_org_create_requires_superadmin(client, login_as):
    login_as('admin')
    r = client.post('/api/v1/enterprise/organizations',
                    json={'code': 'o1', 'name': 'O1'})
    assert r.status_code == 403


def test_org_create_and_list(client, login_as):
    login_as('superadmin')
    r = client.post('/api/v1/enterprise/organizations',
                    json={'code': 'o1', 'name': 'O1'})
    assert r.status_code == 201

    login_as('admin')
    r2 = client.get('/api/v1/enterprise/organizations')
    assert r2.status_code == 200
    assert any(o['code'] == 'o1' for o in r2.get_json()['organizations'])


def test_api_key_create_list_revoke(client, login_as):
    login_as('admin')
    r = client.post('/api/v1/keys', json={
        'name': 'k1', 'scopes': ['read:courses'],
    })
    assert r.status_code == 201
    body = r.get_json()
    raw = body['api_key']
    kid = body['id']
    assert raw.startswith('sp_')

    r2 = client.get('/api/v1/keys')
    assert any(k['id'] == kid for k in r2.get_json()['keys'])

    r3 = client.post(f'/api/v1/keys/{kid}/revoke')
    assert r3.status_code == 200

    # Revoked keys are filtered out
    r4 = client.get('/api/v1/keys')
    assert not [k for k in r4.get_json()['keys'] if k['id'] == kid]


def test_api_key_create_rejects_bad_scopes(client, login_as):
    login_as('admin')
    r = client.post('/api/v1/keys',
                    json={'name': 'k', 'scopes': 'read:courses'})
    assert r.status_code == 400


def test_audit_events_logged_for_org_create(client, login_as):
    login_as('superadmin')
    client.post('/api/v1/enterprise/organizations',
                json={'code': 'oA', 'name': 'OA'})

    login_as('admin')
    r = client.get('/api/v1/audit/events',
                   query_string={'action': 'org.create'})
    assert r.status_code == 200
    assert any(e['action'] == 'org.create' for e in r.get_json()['events'])


def test_consent_record_and_list(client, login_as):
    login_as('student')
    r = client.post('/api/v1/compliance/consent',
                    json={'consent_type': 'privacy', 'granted': True})
    assert r.status_code == 201

    r2 = client.post('/api/v1/compliance/consent',
                     json={'consent_type': 'invalid'})
    assert r2.status_code == 400

    r3 = client.get('/api/v1/compliance/consent')
    assert r3.status_code == 200
    assert r3.get_json()['count'] == 1


def test_data_request_create(client, login_as):
    login_as('student')
    r = client.post('/api/v1/compliance/data-requests',
                    json={'request_type': 'export'})
    assert r.status_code == 201
    r2 = client.post('/api/v1/compliance/data-requests',
                     json={'request_type': 'shred'})
    assert r2.status_code == 400


def test_export_me(client, login_as):
    login_as('student')
    r = client.get('/api/v1/compliance/export/me')
    assert r.status_code == 200
    body = r.get_json()
    assert body['user']['role'] == 'student'


def test_accessibility_get_creates_default(client, login_as):
    login_as('student')
    r = client.get('/api/v1/accessibility/profile')
    assert r.status_code == 200
    a = r.get_json()['accessibility']
    assert a['high_contrast'] is False
    assert a['font_scale'] == 1.0


def test_accessibility_update_clamps_font_scale(client, login_as):
    login_as('student')
    client.get('/api/v1/accessibility/profile')  # ensure row exists
    r = client.put('/api/v1/accessibility/profile',
                   json={'high_contrast': True, 'font_scale': 5.0})
    assert r.status_code == 200
    r2 = client.get('/api/v1/accessibility/profile')
    a = r2.get_json()['accessibility']
    assert a['high_contrast'] is True
    assert a['font_scale'] == 1.6  # clamped


def test_tts_requires_text(client, login_as):
    login_as('student')
    r = client.post('/api/v1/accessibility/tts', json={})
    assert r.status_code == 400


def test_openapi_spec_public(client):
    r = client.get('/api/v1/spec')
    assert r.status_code == 200
    body = r.get_json()
    assert body['openapi'].startswith('3.')
    assert '/public/courses' in body['paths']
