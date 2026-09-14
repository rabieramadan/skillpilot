"""Enrolling must record the enrolment, show it, and let the student in.

Two faults made a student's enrolment useless. Every self-enrolment was
written as ``pending``, and nothing could move it on — the approve and reject
endpoints read the legacy ``enrollments.json`` and expect the status
``requested``, so they never saw a database row, and the admin screens dropped
the pending queue deliberately. And the course listing fetched pending rows
and then discarded them, so the course fell back into "Available courses".

Together: the student was told the enrolment worked, saw it in one screen,
saw "No Classes Yet" in another, and got 403 on the course itself.

These tests pin all three screens agreeing, and the payment gate surviving.
"""

import pytest

from app.models import Course, Enrollment, db


@pytest.fixture
def course(app):
    def _make(title='Statistics 101', published=True, requires_payment=False,
              registration_open=True):
        with app.app_context():
            row = Course(title=title, code=title.replace(' ', '')[:12],
                         description='A course', is_published=published,
                         requires_payment=requires_payment,
                         registration_open=registration_open,
                         price=25.0 if requires_payment else 0.0)
            db.session.add(row)
            db.session.commit()
            return row.id
    return _make


def my_courses(client):
    response = client.get('/api/classes/my-courses')
    assert response.status_code == 200, response.data
    return response.get_json()


def my_classes(client):
    response = client.get('/api/student/classes')
    assert response.status_code == 200, response.data
    return [c.get('title') for c in (response.get_json().get('classes') or [])]


def titles(courses):
    return sorted(c['title'] for c in courses)


class TestAFreeCourseIsUsableImmediately:
    """Nothing gates a free course with registration open, so nothing waits."""

    def test_all_three_screens_agree(self, client, login_as, course):
        login_as('student')
        course_id = course()

        assert my_courses(client)['enrolled_courses'] == []
        assert my_classes(client) == []

        response = client.post('/api/classes/enroll',
                               json={'class_id': course_id})
        assert response.status_code == 200, response.data

        listed = my_courses(client)
        assert titles(listed['enrolled_courses']) == ['Statistics 101']
        assert listed['available_courses'] == []
        assert my_classes(client) == ['Statistics 101'], \
            'the course was listed as enrolled but My Classes was empty'

    def test_the_course_opens(self, client, login_as, course):
        login_as('student')
        course_id = course()
        client.post('/api/classes/enroll', json={'class_id': course_id})

        response = client.get(f'/api/student/class/{course_id}/dashboard')
        assert response.status_code == 200, \
            'enrolled, listed, and still refused at the door'

    def test_it_is_marked_usable_not_waiting(self, client, login_as, course):
        login_as('student')
        client.post('/api/classes/enroll', json={'class_id': course()})

        entry = my_courses(client)['enrolled_courses'][0]
        assert entry['status'] == 'active'
        assert entry['awaiting_approval'] is False
        assert entry['can_open'] is True
        assert entry['enrollment_date']
        assert my_courses(client)['pending_count'] == 0

    def test_the_message_does_not_promise_a_wait(self, client, login_as,
                                                 course):
        """The screen shows this message, so it must match what happened."""
        login_as('student')
        response = client.post('/api/classes/enroll',
                               json={'class_id': course()})
        body = response.get_json()
        assert body['enrollment']['status'] == 'active'
        assert 'approval' not in body['message'].lower()


class TestAPaidCourseStillWaitsForPayment:
    def test_it_is_pending_and_closed_until_verified(self, client, login_as,
                                                     course):
        login_as('student')
        course_id = course(title='Paid Course', requires_payment=True)
        client.post('/api/classes/enroll', json={'class_id': course_id})

        entry = my_courses(client)['enrolled_courses'][0]
        assert entry['status'] == 'pending'
        assert entry['awaiting_approval'] is True
        assert entry['can_open'] is False
        assert entry['payment_verified'] is False
        assert my_courses(client)['pending_count'] == 1
        assert my_classes(client) == []
        assert client.get(
            f'/api/student/class/{course_id}/dashboard').status_code == 403

    def test_it_is_still_listed_while_it_waits(self, client, login_as, course):
        """Waiting is not the same as vanishing: it stays in the list."""
        login_as('student')
        client.post('/api/classes/enroll',
                    json={'class_id': course(title='Paid Course',
                                             requires_payment=True)})
        listed = my_courses(client)
        assert titles(listed['enrolled_courses']) == ['Paid Course']
        assert listed['available_courses'] == []

    def test_the_message_says_payment_is_the_gate(self, client, login_as,
                                                  course):
        login_as('student')
        response = client.post('/api/classes/enroll',
                               json={'class_id': course(title='Paid Course',
                                                        requires_payment=True)})
        assert 'payment' in response.get_json()['message'].lower()

    def test_verifying_the_payment_opens_it(self, app, client, login_as,
                                            login, make_user, course):
        student_id = login_as('student')
        course_id = course(title='Paid Course', requires_payment=True)
        client.post('/api/classes/enroll', json={'class_id': course_id})

        admin = make_user('superadmin')
        login(admin['id'], 'superadmin')
        verified = client.post('/api/classes/verify-payment',
                               json={'user_id': student_id,
                                     'class_id': course_id})
        assert verified.status_code == 200, verified.data

        login(student_id, 'student')
        entry = my_courses(client)['enrolled_courses'][0]
        assert entry['can_open'] is True
        assert my_classes(client) == ['Paid Course']
        assert client.get(
            f'/api/student/class/{course_id}/dashboard').status_code == 200


class TestEnrollingTwice:
    def test_clicking_twice_does_not_duplicate_the_row(self, app, client,
                                                       login_as, course):
        user_id = login_as('student')
        course_id = course()
        client.post('/api/classes/enroll', json={'class_id': course_id})
        client.post('/api/classes/enroll', json={'class_id': course_id})

        with app.app_context():
            assert Enrollment.query.filter_by(
                user_id=user_id, course_id=course_id).count() == 1
        assert len(my_courses(client)['enrolled_courses']) == 1

    def test_an_active_course_cannot_be_enrolled_in_again(self, client,
                                                          login_as, course):
        login_as('student')
        course_id = course()
        client.post('/api/classes/enroll', json={'class_id': course_id})

        again = client.post('/api/classes/enroll', json={'class_id': course_id})
        assert again.status_code == 400
        assert 'already' in again.get_json()['error'].lower()

    def test_a_withdrawn_enrolment_is_not_reopened_by_asking_again(
            self, app, client, login_as, course):
        """Re-enrolling used to overwrite any status, including a block."""
        user_id = login_as('student')
        course_id = course()
        client.post('/api/classes/enroll', json={'class_id': course_id})
        with app.app_context():
            row = Enrollment.query.filter_by(user_id=user_id,
                                             course_id=course_id).first()
            row.status = 'blocked'
            db.session.commit()

        again = client.post('/api/classes/enroll', json={'class_id': course_id})
        assert again.status_code == 403
        with app.app_context():
            assert Enrollment.query.filter_by(
                user_id=user_id, course_id=course_id).first().status == 'blocked'


class TestOtherStudentsAreUnaffected:
    def test_one_students_enrolment_is_not_visible_to_another(
            self, client, login_as, course):
        course_id = course()
        login_as('student', username='first_student')
        client.post('/api/classes/enroll', json={'class_id': course_id})

        login_as('student', username='second_student')
        seen = my_courses(client)
        assert seen['enrolled_courses'] == []
        assert titles(seen['available_courses']) == ['Statistics 101']
        assert my_classes(client) == []


class TestClosedRegistrationIsStillRefused:
    def test_a_closed_course_cannot_be_joined(self, client, login_as, course):
        login_as('student')
        course_id = course(registration_open=False)
        response = client.post('/api/classes/enroll',
                               json={'class_id': course_id})
        assert response.status_code == 403
        assert my_classes(client) == []

    def test_an_unpublished_course_cannot_be_joined(self, client, login_as,
                                                    course):
        login_as('student')
        response = client.post('/api/classes/enroll',
                               json={'class_id': course(published=False)})
        assert response.status_code == 403
