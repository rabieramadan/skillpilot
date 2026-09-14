"""Phase 7 — SkillMatch readiness + Teacher PD."""


def _seed_occupation_with_skills(db, app):
    from app.models import Occupation, Skill, OccupationSkill
    with app.app_context():
        occ = Occupation(code='dev.data_analyst', name='Data Analyst',
                         sector='tech')
        s1 = Skill(code='sql.basic', name='SQL', level_max=5)
        s2 = Skill(code='py.pandas', name='Pandas', level_max=5)
        db.session.add_all([occ, s1, s2])
        db.session.flush()
        db.session.add_all([
            OccupationSkill(occupation_id=occ.id, skill_id=s1.id,
                            target_level=4, importance=2.0, is_essential=True),
            OccupationSkill(occupation_id=occ.id, skill_id=s2.id,
                            target_level=2, importance=1.0, is_essential=False),
        ])
        db.session.commit()
        return occ.id, s1.id, s2.id


def test_occupation_create_requires_admin(client, login_as):
    login_as('teacher')
    r = client.post('/api/v1/skillmatch/occupations',
                    json={'code': 'x', 'name': 'X'})
    assert r.status_code == 403


def test_readiness_no_skills_yet(client, login_as, db, app):
    _seed_occupation_with_skills(db, app)
    login_as('student')
    r = client.get('/api/v1/skillmatch/readiness',
                   query_string={'occupation_code': 'dev.data_analyst'})
    assert r.status_code == 200
    body = r.get_json()
    # No learner skill rows -> 0 / total = 0
    assert body['readiness_score'] == 0.0
    gap_codes = {g['skill_code'] for g in body['gaps']}
    assert {'sql.basic', 'py.pandas'} <= gap_codes


def test_readiness_full_match(client, login_as, db, app):
    occ_id, s1, s2 = _seed_occupation_with_skills(db, app)
    uid = login_as('student')
    from app.models import LearnerSkill
    with app.app_context():
        db.session.add_all([
            LearnerSkill(user_id=uid, skill_id=s1, level=4),
            LearnerSkill(user_id=uid, skill_id=s2, level=2),
        ])
        db.session.commit()

    r = client.get('/api/v1/skillmatch/readiness',
                   query_string={'occupation_code': 'dev.data_analyst'})
    body = r.get_json()
    assert body['readiness_score'] == 100.0
    assert body['gaps'] == []


def test_readiness_partial_weighted(client, login_as, db, app):
    """sql at 2/4 (importance 2) + pandas at 2/2 (importance 1)
       -> achieved = 0.5*2 + 1.0*1 = 2.0 of total weight 3.0 -> 66.7%."""
    occ_id, s1, s2 = _seed_occupation_with_skills(db, app)
    uid = login_as('student')
    from app.models import LearnerSkill
    with app.app_context():
        db.session.add_all([
            LearnerSkill(user_id=uid, skill_id=s1, level=2),
            LearnerSkill(user_id=uid, skill_id=s2, level=2),
        ])
        db.session.commit()
    r = client.get('/api/v1/skillmatch/readiness',
                   query_string={'occupation_code': 'dev.data_analyst'})
    body = r.get_json()
    assert body['readiness_score'] == 66.7
    assert {g['skill_code'] for g in body['gaps']} == {'sql.basic'}


def test_readiness_unknown_occupation(client, login_as):
    login_as('student')
    r = client.get('/api/v1/skillmatch/readiness',
                   query_string={'occupation_code': 'no.such'})
    assert r.status_code == 404


def test_readiness_requires_login(client):
    r = client.get('/api/v1/skillmatch/readiness',
                   query_string={'occupation_code': 'x'})
    assert r.status_code == 401


def test_pd_track_create_and_enroll(client, login_as):
    login_as('admin')
    r = client.post('/api/v1/pd/tracks', json={
        'code': 'pd.ai', 'name': 'AI Lit', 'track_type': 'ai_literacy',
    })
    assert r.status_code == 201
    login_as('teacher')
    r2 = client.post('/api/v1/pd/enroll', json={'track_code': 'pd.ai'})
    assert r2.status_code in (200, 201)

    r3 = client.get('/api/v1/pd/enrollments')
    assert r3.get_json()['count'] == 1


def test_pd_certificate_verify_public(client, login_as, app, db):
    # Admin creates track + enrollment, then issues cert
    login_as('admin')
    client.post('/api/v1/pd/tracks',
                json={'code': 'pd.x', 'name': 'X', 'track_type': 'pedagogy'})

    teacher_id = login_as('teacher')
    client.post('/api/v1/pd/enroll', json={'track_code': 'pd.x'})

    from app.models import TeacherPDEnrollment
    with app.app_context():
        e = TeacherPDEnrollment.query.filter_by(user_id=teacher_id).first()
        eid = e.id

    login_as('admin')
    r = client.post(f'/api/v1/pd/enrollments/{eid}/issue-certificate',
                    json={'final_score': 92.5})
    assert r.status_code == 200
    cert_id = r.get_json()['certificate_id']

    # Public verification: use a fresh test client with no session cookie
    # to prove the endpoint is truly public (no auth header / no login).
    anon = client.application.test_client()
    rv = anon.get(f'/api/v1/pd/certificates/{cert_id}/verify')
    assert rv.status_code == 200
    body = rv.get_json()
    assert body['verified'] is True
    assert body['final_score'] == 92.5
