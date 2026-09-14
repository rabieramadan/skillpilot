"""Phase 3 — Smart Assessment & Proctoring (`/api/assessments/*`)."""
import uuid


def _make_skill(db, app, code='skill.demo'):
    from app.models import Skill
    with app.app_context():
        s = Skill(id=str(uuid.uuid4()), code=code, name='Demo', level_max=5)
        db.session.add(s)
        db.session.commit()
        return s.id


def _attach_learner_skill(db, app, user_id, skill_id, level=2, confidence=0.6):
    from app.models import LearnerSkill
    with app.app_context():
        ls = LearnerSkill(user_id=user_id, skill_id=skill_id,
                          level=level, confidence=confidence)
        db.session.add(ls)
        db.session.commit()


def test_signals_is_public(client):
    r = client.get('/api/assessments/signals')
    assert r.status_code == 200
    body = r.get_json()
    assert body['success'] is True
    assert isinstance(body['signals'], list) and body['signals']
    assert 'camera video' in body['never_collected']
    assert body['opt_out_supported'] is True


def test_retention_due_requires_login(client):
    r = client.get('/api/assessments/retention/due')
    assert r.status_code == 401


def test_retention_due_empty_for_new_learner(client, login_as):
    login_as('student')
    r = client.get('/api/assessments/retention/due')
    assert r.status_code == 200
    assert r.get_json()['count'] == 0


def test_retention_start_unknown_skill(client, login_as):
    login_as('student')
    r = client.post('/api/assessments/retention/missing/start', json={})
    assert r.status_code == 404


def test_retention_start_without_mastery(client, login_as, db, app):
    login_as('student')
    sid = _make_skill(db, app, code='no.mastery')
    r = client.post(f'/api/assessments/retention/{sid}/start', json={})
    assert r.status_code == 400


def test_retention_start_strips_answer_key(client, login_as, db, app):
    user_id = login_as('student')
    sid = _make_skill(db, app, code='start.ok')
    _attach_learner_skill(db, app, user_id, sid)

    r = client.post(f'/api/assessments/retention/{sid}/start',
                    json={'num_questions': 3})
    assert r.status_code == 201
    body = r.get_json()
    assert body['success'] is True
    assert body['skill']['id'] == sid
    # Public quiz must not leak the correct answer.
    for q in body['quiz']['questions']:
        assert 'correct_answer' not in q
        assert 'correct_answer_ar' not in q
    # Attempt payload also must not leak the stored quiz key.
    assert body['attempt']['rubric_results'] == {}


def test_create_attempt_requires_login(client):
    r = client.post('/api/assessments/attempts', json={})
    assert r.status_code == 401


def test_create_attempt_happy(client, login_as):
    login_as('student')
    r = client.post('/api/assessments/attempts', json={
        'attempt_kind': 'initial',
        'consent_proctoring': True,
        'consent_signals': ['focus'],
    })
    assert r.status_code == 201
    body = r.get_json()
    assert body['attempt']['status'] == 'in_progress'
    assert body['attempt']['consent_proctoring'] is True


def test_get_attempt_blocks_other_user(client, login_as):
    user_a = login_as('student', 'sa')
    aid = client.post('/api/assessments/attempts',
                      json={}).get_json()['attempt']['id']

    login_as('student', 'sb')
    r = client.get(f'/api/assessments/attempts/{aid}')
    assert r.status_code == 403


def test_log_event_requires_consent(client, login_as):
    login_as('student')
    aid = client.post('/api/assessments/attempts',
                      json={'consent_proctoring': False}).get_json()['attempt']['id']
    r = client.post(f'/api/assessments/attempts/{aid}/events',
                    json={'event_type': 'tab_blur'})
    assert r.status_code == 403


def test_log_event_validates_type(client, login_as):
    login_as('student')
    aid = client.post('/api/assessments/attempts',
                      json={'consent_proctoring': True}).get_json()['attempt']['id']
    r = client.post(f'/api/assessments/attempts/{aid}/events',
                    json={'event_type': 'invented'})
    assert r.status_code == 400


def test_log_event_skipped_when_opted_out(client, login_as):
    login_as('student')
    aid = client.post('/api/assessments/attempts',
                      json={'consent_proctoring': True,
                            'accommodation_opt_out': True}).get_json()['attempt']['id']
    r = client.post(f'/api/assessments/attempts/{aid}/events',
                    json={'event_type': 'tab_blur'})
    assert r.status_code == 200
    assert r.get_json()['skipped'] is True


def test_finalize_attempt_marks_submitted(client, login_as):
    login_as('student')
    aid = client.post('/api/assessments/attempts',
                      json={}).get_json()['attempt']['id']
    r = client.post(f'/api/assessments/attempts/{aid}/finalize', json={})
    assert r.status_code == 200
    assert r.get_json()['attempt']['status'] == 'submitted'


def test_grade_rubric_oneoff_requires_login(client):
    r = client.post('/api/assessments/grade/rubric', json={})
    assert r.status_code == 401


def test_grade_rubric_oneoff_returns_result(client, login_as):
    login_as('student')
    r = client.post('/api/assessments/grade/rubric', json={
        'question': 'What is fairness?',
        'answer': 'Treating people equitably.',
    })
    assert r.status_code == 200
    body = r.get_json()
    assert body['success'] is True
    assert 'result' in body
