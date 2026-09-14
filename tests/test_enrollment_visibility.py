"""A student's enrolment request must not disappear.

Clicking "Enroll Now" creates a *pending* enrolment: an administrator has to
approve it before the course can be opened. The listing endpoint used to
filter those out, so the course dropped straight back into "Available
courses" with an Enrol button — the student saw a success message and then no
trace of what they had just done, and every re-click quietly rewrote the same
pending row.

These tests pin the contract the student screen depends on: a pending
enrolment is listed, it is flagged as not yet usable, and listing it grants
no access.
"""

import pytest

from app.models import Course, Enrollment, db


@pytest.fixture
def course(app):
    def _make(title='Statistics 101', published=True, requires_payment=False):
        with app.app_context():
            row = Course(title=title, code=title.replace(' ', '')[:12],
                         description='A course', is_published=published,
                         requires_payment=requires_payment,
                         price=25.0 if requires_payment else 0.0)
            db.session.add(row)
            db.session.commit()
            return row.id
    return _make


def my_courses(client):
    response = client.get('/api/classes/my-courses')
    assert response.status_code == 200, response.data
    return response.get_json()


def titles(courses):
    return sorted(c['title'] for c in courses)


class TestEnrollingPutsTheCourseInMyCourses:
    def test_the_course_moves_out_of_available(self, client, login_as, course):
        login_as('student')
        course_id = course()

        before = my_courses(client)
        assert titles(before['available_courses']) == ['Statistics 101']
        assert before['enrolled_courses'] == []

        enrolled = client.post('/api/classes/enroll',
                               json={'class_id': course_id})
        assert enrolled.status_code == 200, enrolled.data

        after = my_courses(client)
        assert titles(after['enrolled_courses']) == ['Statistics 101']
        assert after['available_courses'] == [], \
            'the course reappeared as available after enrolling'

    def test_it_is_marked_as_awaiting_approval(self, client, login_as, course):
        login_as('student')
        course_id = course()
        client.post('/api/classes/enroll', json={'class_id': course_id})

        entry = my_courses(client)['enrolled_courses'][0]
        assert entry['status'] == 'pending'
        assert entry['awaiting_approval'] is True
        assert entry['can_open'] is False
        assert entry['enrollment_date']

    def test_the_pending_count_is_reported(self, client, login_as, course):
        login_as('student')
        client.post('/api/classes/enroll', json={'class_id': course()})
        assert my_courses(client)['pending_count'] == 1

    def test_the_response_says_it_is_pending(self, client, login_as, course):
        """The screen shows this message, so it must not claim access."""
        login_as('student')
        response = client.post('/api/classes/enroll',
                               json={'class_id': course()})
        body = response.get_json()
        assert body['enrollment']['status'] == 'pending'
        assert 'approval' in body['message'].lower()


class TestApprovalChangesTheState:
    def test_an_approved_enrolment_can_be_opened(self, app, client, login_as,
                                                 course):
        user_id = login_as('student')
        course_id = course()
        client.post('/api/classes/enroll', json={'class_id': course_id})

        with app.app_context():
            row = Enrollment.query.filter_by(user_id=user_id,
                                             course_id=course_id).first()
            row.status = 'approved'
            db.session.commit()

        entry = my_courses(client)['enrolled_courses'][0]
        assert entry['awaiting_approval'] is False
        assert entry['can_open'] is True
        assert my_courses(client)['pending_count'] == 0

    def test_a_pending_enrolment_does_not_grant_content_access(
            self, client, login_as, course):
        """Listing the course must not be mistaken for granting it."""
        login_as('student')
        course_id = course()
        client.post('/api/classes/enroll', json={'class_id': course_id})

        response = client.get(f'/api/student/class/{course_id}/dashboard')
        assert response.status_code in (403, 404), \
            'a pending enrolment opened the course'


class TestReEnrolling:
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

    def test_an_approved_course_cannot_be_enrolled_in_again(
            self, app, client, login_as, course):
        user_id = login_as('student')
        course_id = course()
        client.post('/api/classes/enroll', json={'class_id': course_id})
        with app.app_context():
            row = Enrollment.query.filter_by(user_id=user_id,
                                             course_id=course_id).first()
            row.status = 'approved'
            db.session.commit()

        again = client.post('/api/classes/enroll', json={'class_id': course_id})
        assert again.status_code == 400
        assert 'already' in again.get_json()['error'].lower()


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
