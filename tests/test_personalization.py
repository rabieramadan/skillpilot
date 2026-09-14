"""Phase 1 — Personalization API (`/api/v1/personalization/*`)."""


def test_profile_requires_login(client):
    r = client.get('/api/v1/personalization/profile')
    assert r.status_code == 401


def test_profile_get_autocreates(client, login_as):
    login_as('student')
    r = client.get('/api/v1/personalization/profile')
    assert r.status_code == 200
    body = r.get_json()
    assert body['success'] is True
    assert body['profile']['preferred_difficulty'] in (None, 'adaptive')


def test_profile_update_happy(client, login_as):
    login_as('student')
    r = client.put('/api/v1/personalization/profile', json={
        'primary_goal': 'Learn AI',
        'preferred_language': 'en',
        'preferred_difficulty': 'intermediate',
        'daily_study_minutes': 30,
        'interests': ['ml', 'nlp'],
        'preferred_modalities': ['video', 'reading'],
        'accessibility': {'high_contrast': True, 'font_scale': 1.2},
        'mark_onboarded': True,
    })
    assert r.status_code == 200
    p = r.get_json()['profile']
    assert p['primary_goal'] == 'Learn AI'
    assert p['preferred_difficulty'] == 'intermediate'
    assert p['daily_study_minutes'] == 30
    assert 'ml' in p['interests']
    assert 'video' in p['preferred_modalities']
    assert p['accessibility']['high_contrast'] is True
    assert p['onboarding_completed'] is True


def test_profile_update_rejects_bad_language(client, login_as):
    login_as('student')
    r = client.put('/api/v1/personalization/profile',
                   json={'preferred_language': 'fr'})
    assert r.status_code == 400


def test_profile_update_rejects_bad_difficulty(client, login_as):
    login_as('student')
    r = client.put('/api/v1/personalization/profile',
                   json={'preferred_difficulty': 'wizard'})
    assert r.status_code == 400


def test_profile_update_rejects_bad_minutes(client, login_as):
    login_as('student')
    r = client.put('/api/v1/personalization/profile',
                   json={'daily_study_minutes': 9999})
    assert r.status_code == 400


def test_skills_empty_listing(client, login_as):
    login_as('student')
    r = client.get('/api/v1/personalization/skills')
    assert r.status_code == 200
    body = r.get_json()
    assert body['count'] == 0
    assert body['skills'] == []


def test_paths_requires_title(client, login_as):
    login_as('student')
    r = client.post('/api/v1/personalization/paths', json={})
    assert r.status_code == 400


def test_paths_create_and_list(client, login_as):
    login_as('student')
    r = client.post('/api/v1/personalization/paths', json={
        'title': 'My path',
        'difficulty': 'beginner',
        'generated_by': 'system',
        'target_skill_codes': ['skill.a', 'skill.b'],
        'steps': [
            {'step_type': 'material', 'title': 'Watch intro'},
            {'step_type': 'reflection', 'title': 'Reflect'},
        ],
    })
    assert r.status_code == 201
    path = r.get_json()['path']
    assert path['title'] == 'My path'
    assert len(path['steps']) == 2
    pid = path['id']

    r2 = client.get('/api/v1/personalization/paths')
    assert r2.status_code == 200
    listing = r2.get_json()
    assert listing['count'] == 1
    assert listing['paths'][0]['id'] == pid


def test_path_step_status_transitions(client, login_as):
    login_as('student')
    r = client.post('/api/v1/personalization/paths', json={
        'title': 'P',
        'steps': [
            {'step_type': 'material', 'title': 'A'},
            {'step_type': 'material', 'title': 'B'},
        ],
    })
    path = r.get_json()['path']
    pid = path['id']
    step_a = path['steps'][0]['id']

    bad = client.patch(
        f'/api/v1/personalization/paths/{pid}/steps/{step_a}',
        json={'status': 'wat'},
    )
    assert bad.status_code == 400

    ok = client.patch(
        f'/api/v1/personalization/paths/{pid}/steps/{step_a}',
        json={'status': 'completed'},
    )
    assert ok.status_code == 200
    body = ok.get_json()
    assert body['step']['status'] == 'completed'
    assert body['path_progress'] == 50.0


def test_paths_isolated_per_user(client, login_as):
    user_a = login_as('student', 'student_a')
    client.post('/api/v1/personalization/paths', json={'title': 'A'})

    user_b = login_as('student', 'student_b')
    assert user_b != user_a
    listing = client.get('/api/v1/personalization/paths').get_json()
    assert listing['count'] == 0


def test_home_requires_login(client):
    r = client.get('/api/v1/personalization/home')
    assert r.status_code == 401


def test_home_returns_profile(client, login_as):
    login_as('student')
    r = client.get('/api/v1/personalization/home')
    assert r.status_code == 200
    body = r.get_json()
    assert 'profile' in body
    assert body['ethics_tracked'] == 0
