"""Phase 5 — Engagement, social, guardian, live."""


def test_badges_award_grants_xp(client, login_as, app, db):
    # Create a learner to award
    from app.models import User
    with app.app_context():
        learner = User(
            username='learner1', full_name='L', role='student',
            password_hash='x',
        )
        db.session.add(learner)
        db.session.commit()
        learner_id = learner.id

    # Badge creation is admin-only
    login_as('admin')
    r = client.post('/api/v1/engagement/badges',
                    json={'code': 'B1', 'name': 'B', 'xp_reward': 10})
    assert r.status_code == 201

    # Awarding allowed for teachers and above
    login_as('teacher')
    r2 = client.post('/api/v1/engagement/badges/award',
                     json={'user_id': learner_id, 'badge_code': 'B1'})
    assert r2.status_code == 200
    assert r2.get_json()['xp_added'] == 10

    # Idempotent (no double award)
    r3 = client.post('/api/v1/engagement/badges/award',
                     json={'user_id': learner_id, 'badge_code': 'B1'})
    assert r3.get_json().get('already') is True


def test_streak_checkin_increments(client, login_as):
    login_as('student')
    r = client.post('/api/v1/engagement/streak/checkin')
    assert r.status_code == 200
    assert r.get_json()['streak_days'] == 1
    # Second check-in same day: stays at 1
    r2 = client.post('/api/v1/engagement/streak/checkin')
    assert r2.get_json()['streak_days'] == 1


def test_leaderboard_ranks_by_xp(client, login_as, app, db):
    login_as('student')  # only need to be logged in
    from app.models import User, XPEvent
    with app.app_context():
        for name, xp in [('alpha', 5), ('beta', 100), ('gamma', 50)]:
            u = User(username=name, full_name=name, role='student',
                     password_hash='x')
            db.session.add(u)
            db.session.flush()
            db.session.add(XPEvent(user_id=u.id, amount=xp, source='exam'))
        db.session.commit()
    r = client.get('/api/v1/engagement/leaderboard')
    assert r.status_code == 200
    board = r.get_json()['leaderboard']
    assert board[0]['xp'] >= board[-1]['xp']
    names = [row['name'] for row in board if row['name'] in
             {'alpha', 'beta', 'gamma'}]
    assert names[0] == 'beta'


def test_forum_thread_and_post(client, login_as):
    login_as('student')
    r = client.post('/api/v1/social/forums/threads',
                    json={'title': 'T', 'body': 'hello'})
    assert r.status_code == 201
    tid = r.get_json()['id']

    r2 = client.post(f'/api/v1/social/forums/threads/{tid}/posts',
                     json={'body': 'reply'})
    assert r2.status_code == 201

    r3 = client.get(f'/api/v1/social/forums/threads/{tid}/posts')
    assert r3.get_json()['count'] == 2  # initial + reply


def test_forum_post_requires_body(client, login_as):
    login_as('student')
    r = client.post('/api/v1/social/forums/threads',
                    json={'title': 'T', 'body': 'b'})
    tid = r.get_json()['id']
    r2 = client.post(f'/api/v1/social/forums/threads/{tid}/posts', json={})
    assert r2.status_code == 400


def test_guardian_link_flow(client, login_as, login, app, db, make_user):
    # Guardian creates link
    guardian_id = login_as('student', 'guardian1')
    learner = make_user('student', 'learner1')

    r = client.post('/api/v1/guardian/links',
                    json={'learner_user_id': learner['id']})
    assert r.status_code == 201
    token = r.get_json()['consent_token']

    # Learner approves
    login(learner['id'], learner['role'])
    r2 = client.post('/api/v1/guardian/links/approve',
                     json={'consent_token': token})
    assert r2.status_code == 200

    # Guardian sees the dashboard with the linked child
    login(guardian_id, 'student')
    r3 = client.get('/api/v1/guardian/dashboard')
    assert r3.status_code == 200
    body = r3.get_json()
    assert body['count'] == 1
    assert body['children'][0]['learner_id'] == learner['id']


def test_live_session_schedule_and_join(client, login_as):
    teacher = login_as('teacher')
    r = client.post('/api/v1/live/sessions', json={
        'title': 'Class', 'starts_at': '2030-01-01T10:00:00Z',
        'provider': 'jitsi',
    })
    assert r.status_code == 201
    sid = r.get_json()['id']
    assert 'meet.jit.si' in r.get_json()['join_url']

    r2 = client.get('/api/v1/live/sessions')
    assert any(s['id'] == sid for s in r2.get_json()['sessions'])

    r3 = client.post(f'/api/v1/live/sessions/{sid}/join')
    assert r3.status_code == 200


def test_live_session_invalid_provider(client, login_as):
    login_as('teacher')
    r = client.post('/api/v1/live/sessions', json={
        'title': 'X', 'starts_at': '2030-01-01T10:00:00Z',
        'provider': 'webex',
    })
    assert r.status_code == 400


def test_live_session_unauthenticated(client):
    r = client.post('/api/v1/live/sessions',
                    json={'title': 'X', 'starts_at': '2030-01-01T10:00:00Z'})
    assert r.status_code == 401
