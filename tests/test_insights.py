"""Phase 6 — Insights, sentiment, at-risk."""
from datetime import datetime, timedelta


def test_sentiment_scoring_deterministic(client, login_as):
    login_as('student')

    r_pos = client.post('/api/v1/insights/sentiment',
                        json={'text': 'This is great and helpful, I love it!',
                              'language': 'en'})
    assert r_pos.status_code == 201
    assert r_pos.get_json()['sentiment'] == 'positive'

    r_neg = client.post('/api/v1/insights/sentiment',
                        json={'text': 'This is awful and frustrating, I hate it.',
                              'language': 'en'})
    assert r_neg.status_code == 201
    assert r_neg.get_json()['sentiment'] == 'negative'

    r_neu = client.post('/api/v1/insights/sentiment',
                        json={'text': 'Some neutral statement about a thing.',
                              'language': 'en'})
    assert r_neu.get_json()['sentiment'] == 'neutral'


def test_sentiment_summary_requires_teacher(client, login_as):
    login_as('student')
    r = client.get('/api/v1/insights/sentiment/summary')
    assert r.status_code == 403


def test_atrisk_scan_flags_low_progress_low_score(client, login_as, app, db):
    login_as('teacher')

    from app.models import User, Course, Enrollment, Exam, ExamResult
    with app.app_context():
        u = User(username='atrisk', full_name='AR', role='student',
                 password_hash='x')
        c = Course(title='C')
        db.session.add_all([u, c])
        db.session.flush()
        # Low progress
        db.session.add(Enrollment(user_id=u.id, course_id=c.id,
                                   progress_percent=5.0))
        # Low recent exam scores
        ex = Exam(course_id=c.id, title='Q')
        db.session.add(ex)
        db.session.flush()
        for s in (10.0, 20.0, 30.0):
            db.session.add(ExamResult(exam_id=ex.id, user_id=u.id, score=s))
        db.session.commit()
        target_uid = u.id

    r = client.post('/api/v1/insights/at-risk/scan', json={})
    assert r.status_code == 200
    assert r.get_json()['alerts_created'] >= 1

    r2 = client.get('/api/v1/insights/at-risk')
    alerts = r2.get_json()['alerts']
    mine = [a for a in alerts if a['user_id'] == target_uid]
    assert mine, 'expected an at-risk alert for the seeded learner'
    a = mine[0]
    # low_progress (25) + low_exam_avg (30) -> risk >= 55 -> 'high'
    assert a['risk_score'] >= 55
    assert a['risk_level'] in ('high', 'critical')
    factor_names = {f['factor'] for f in a['factors']}
    assert 'low_progress' in factor_names
    assert 'low_exam_avg' in factor_names


def test_atrisk_scan_skips_healthy_learner(client, login_as, app, db):
    login_as('teacher')
    from app.models import User, Course, Enrollment
    with app.app_context():
        u = User(username='healthy', full_name='H', role='student',
                 password_hash='x')
        c = Course(title='C')
        db.session.add_all([u, c])
        db.session.flush()
        db.session.add(Enrollment(user_id=u.id, course_id=c.id,
                                   progress_percent=95.0))
        db.session.commit()
        uid = u.id

    client.post('/api/v1/insights/at-risk/scan', json={})
    r = client.get('/api/v1/insights/at-risk')
    assert not [a for a in r.get_json()['alerts'] if a['user_id'] == uid]


def test_atrisk_acknowledge_and_resolve(client, login_as, app, db):
    login_as('teacher')
    from app.models import AtRiskAlert
    with app.app_context():
        a = AtRiskAlert(user_id='u1', risk_score=80.0, risk_level='high',
                        factors=[], recommended_actions=[])
        db.session.add(a); db.session.commit()
        aid = a.id
    r = client.post(f'/api/v1/insights/at-risk/{aid}/acknowledge')
    assert r.status_code == 200
    r2 = client.post(f'/api/v1/insights/at-risk/{aid}/resolve')
    assert r2.status_code == 200


def test_cohort_snapshot_returns_payload(client, login_as):
    login_as('teacher')
    r = client.get('/api/v1/insights/cohort')
    assert r.status_code == 200
    assert 'snapshot' in r.get_json()


def test_atrisk_requires_teacher(client, login_as):
    login_as('student')
    r = client.post('/api/v1/insights/at-risk/scan', json={})
    assert r.status_code == 403
