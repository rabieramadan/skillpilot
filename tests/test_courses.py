"""Phase 2 — Courses & weekly materials (`/api/courses/*`)."""


def _create_course(client, **overrides):
    payload = {'title': 'Demo course', 'num_weeks': 3}
    payload.update(overrides)
    r = client.post('/api/courses/create', json=payload)
    assert r.status_code == 200, r.get_json()
    return r.get_json()['course']['id']


def test_list_requires_login(client):
    r = client.get('/api/courses/list')
    assert r.status_code == 401


def test_create_requires_instructor(client, login_as):
    login_as('student')
    r = client.post('/api/courses/create', json={'title': 'no'})
    assert r.status_code == 403


def test_create_course_happy(client, login_as):
    login_as('teacher')
    cid = _create_course(client, title='Intro')
    listing = client.get('/api/courses/list').get_json()
    titles = {c['title']: c for c in listing['courses']}
    assert 'Intro' in titles
    assert titles['Intro']['week_count'] == 3


def test_get_course_blocks_unenrolled_student(client, login_as, db, app):
    login_as('teacher', 'teach1')
    cid = _create_course(client, title='Hidden')

    login_as('student', 'lurker')
    r = client.get(f'/api/courses/{cid}')
    assert r.status_code == 403


def test_get_course_for_enrolled_student(client, login_as, db, app):
    login_as('teacher', 'teach2')
    cid = _create_course(client, title='Open')

    student_id = login_as('student', 'enrolled')
    from app.models import Enrollment
    with app.app_context():
        db.session.add(Enrollment(
            user_id=student_id, course_id=cid, status='approved',
        ))
        db.session.commit()

    r = client.get(f'/api/courses/{cid}')
    assert r.status_code == 200
    body = r.get_json()
    assert body['course']['title'] == 'Open'


def test_student_sees_only_enrolled_courses(client, login_as, db, app):
    login_as('teacher', 'teach3')
    public_id = _create_course(client, title='PublicCourse')
    other_id = _create_course(client, title='OtherCourse')

    student_id = login_as('student', 'mike')
    from app.models import Enrollment
    with app.app_context():
        db.session.add(Enrollment(
            user_id=student_id, course_id=public_id, status='active',
        ))
        db.session.commit()

    titles = {c['title'] for c in client.get('/api/courses/list').get_json()['courses']}
    assert titles == {'PublicCourse'}


def test_add_material_requires_teacher(client, login_as):
    login_as('teacher', 'tch')
    cid = _create_course(client, title='Mat course')

    login_as('student', 'stu')
    r = client.post(
        f'/api/courses/{cid}/weeks/1/materials',
        json={'title': 'noop'},
    )
    assert r.status_code == 403


def test_add_material_happy(client, login_as):
    login_as('teacher')
    cid = _create_course(client, title='WithMat')
    r = client.post(
        f'/api/courses/{cid}/weeks/1/materials',
        json={'title': 'Lesson 1', 'material_type': 'document',
              'topics': ['intro']},
    )
    assert r.status_code == 200
    assert r.get_json()['material']['title'] == 'Lesson 1'


def test_add_material_unknown_week(client, login_as):
    login_as('teacher')
    cid = _create_course(client, num_weeks=2)
    r = client.post(
        f'/api/courses/{cid}/weeks/99/materials',
        json={'title': 'orphan'},
    )
    assert r.status_code == 404


def test_assignment_submit_and_grade_flow(client, login_as, db, app):
    teacher_id = login_as('teacher', 'tprof')
    cid = _create_course(client, title='Assn course')
    create = client.post(
        f'/api/courses/{cid}/weeks/1/assignments',
        json={'title': 'HW1', 'max_attempts': 2, 'is_published': True},
    )
    assert create.status_code == 200
    aid = create.get_json()['assignment']['id']

    student_id = login_as('student', 'studentA')
    from app.models import Enrollment
    with app.app_context():
        db.session.add(Enrollment(
            user_id=student_id, course_id=cid, status='approved',
        ))
        db.session.commit()

    # Submit
    sub = client.post(
        f'/api/courses/{cid}/assignments/{aid}/submit',
        json={'submission_text': 'My answer'},
    )
    assert sub.status_code == 200
    sid = sub.get_json()['submission']['id']

    # Get assignment - should include submission
    detail = client.get(f'/api/courses/{cid}/assignments/{aid}')
    assert detail.status_code == 200
    assert detail.get_json()['submission']['id'] == sid

    # Grade as teacher
    login_as('teacher', 'tprof')
    g = client.post(
        f'/api/courses/{cid}/assignments/{aid}/submissions/{sid}/grade',
        json={'score': 87.5, 'feedback': 'Nice work'},
    )
    assert g.status_code == 200

    # Verify graded state visible to student
    login_as('student', 'studentA')
    detail2 = client.get(f'/api/courses/{cid}/assignments/{aid}').get_json()
    assert detail2['submission']['score'] == 87.5
    assert detail2['submission']['status'] == 'graded'


def test_submission_listing_requires_teacher(client, login_as):
    login_as('teacher', 't')
    cid = _create_course(client)
    create = client.post(
        f'/api/courses/{cid}/weeks/1/assignments',
        json={'title': 'A'},
    )
    aid = create.get_json()['assignment']['id']

    login_as('student', 's')
    r = client.get(f'/api/courses/{cid}/assignments/{aid}/submissions')
    assert r.status_code == 403
