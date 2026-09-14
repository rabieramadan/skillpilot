"""Phase 8 — Public REST API: Bearer auth + per-scope authorization."""


def _bearer(raw):
    return {'Authorization': f'Bearer {raw}'}


def test_public_courses_requires_api_key(client):
    r = client.get('/api/v1/public/courses')
    assert r.status_code == 401


def test_public_courses_rejects_non_bearer(client, api_key):
    raw, _ = api_key(['read:courses'])
    r = client.get('/api/v1/public/courses',
                   headers={'Authorization': f'Basic {raw}'})
    assert r.status_code == 401


def test_public_courses_rejects_unknown_key(client):
    r = client.get('/api/v1/public/courses',
                   headers=_bearer('sp_definitelynotreal'))
    assert r.status_code == 401


def test_public_courses_rejects_missing_scope(client, api_key):
    raw, _ = api_key(['read:learners'])  # wrong scope
    r = client.get('/api/v1/public/courses', headers=_bearer(raw))
    assert r.status_code == 403


def test_public_courses_returns_only_published(client, api_key, app, db):
    from app.models import Course
    with app.app_context():
        db.session.add_all([
            Course(title='Pub', is_published=True),
            Course(title='Draft', is_published=False),
        ])
        db.session.commit()
    raw, _ = api_key(['read:courses'])
    r = client.get('/api/v1/public/courses', headers=_bearer(raw))
    assert r.status_code == 200
    titles = {c['title'] for c in r.get_json()['courses']}
    assert 'Pub' in titles and 'Draft' not in titles


def test_public_learner_skills_requires_scope(client, api_key):
    raw, _ = api_key(['read:courses'])  # missing read:learners
    r = client.get('/api/v1/public/learners/anyuid/skills',
                   headers=_bearer(raw))
    assert r.status_code == 403


def test_public_learner_skills_unbound_key_allowed(client, api_key, app, db):
    from app.models import User, Skill, LearnerSkill
    with app.app_context():
        u = User(username='lk', full_name='LK', role='student',
                 password_hash='x')
        s = Skill(code='py', name='Python')
        db.session.add_all([u, s])
        db.session.flush()
        db.session.add(LearnerSkill(user_id=u.id, skill_id=s.id, level=3))
        db.session.commit()
        uid = u.id

    raw, _ = api_key(['read:learners'])  # no organization_id
    r = client.get(f'/api/v1/public/learners/{uid}/skills',
                   headers=_bearer(raw))
    assert r.status_code == 200
    assert r.get_json()['count'] == 1


def test_public_learner_skills_org_scoped_blocks_outsiders(
        client, api_key, app, db):
    from app.models import User, Organization, OrganizationMember
    with app.app_context():
        org_a = Organization(code='A', name='A')
        org_b = Organization(code='B', name='B')
        learner_a = User(username='la', full_name='L', role='student',
                         password_hash='x')
        learner_b = User(username='lb', full_name='L', role='student',
                         password_hash='x')
        db.session.add_all([org_a, org_b, learner_a, learner_b])
        db.session.flush()
        db.session.add_all([
            OrganizationMember(organization_id=org_a.id,
                                user_id=learner_a.id),
            OrganizationMember(organization_id=org_b.id,
                                user_id=learner_b.id),
        ])
        db.session.commit()
        oa, lb_id, la_id = org_a.id, learner_b.id, learner_a.id

    raw, _ = api_key(['read:learners'], organization_id=oa)

    # Org-A key cannot read an Org-B learner
    r = client.get(f'/api/v1/public/learners/{lb_id}/skills',
                   headers=_bearer(raw))
    assert r.status_code == 403

    # Org-A key CAN read an Org-A learner
    r2 = client.get(f'/api/v1/public/learners/{la_id}/skills',
                    headers=_bearer(raw))
    assert r2.status_code == 200


def test_revoked_key_is_rejected(client, api_key, app, db):
    raw, kid = api_key(['read:courses'])
    from app.models import ApiKey
    with app.app_context():
        k = ApiKey.query.filter_by(id=kid).first()
        k.revoked = True
        db.session.commit()
    r = client.get('/api/v1/public/courses', headers=_bearer(raw))
    assert r.status_code == 401
