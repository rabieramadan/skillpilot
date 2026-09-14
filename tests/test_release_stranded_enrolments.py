"""The people who enrolled before the fix must be let in too.

Their rows are sitting at ``pending`` on courses that have no gate, and
nothing in the application can move them: the approve endpoint reads a JSON
file, and the admin screens have no pending queue. The migration releases
exactly those, and nothing else.
"""

import pytest

from app.models import Course, Enrollment, User, db

from migrations import release_stranded_enrolments as migration


@pytest.fixture
def world(app):
    """A free course and a paid one, each with a stuck enrolment."""
    def _build():
        with app.app_context():
            free = Course(title='Free Course', code='FREE', is_published=True,
                          requires_payment=False, price=0.0)
            paid = Course(title='Paid Course', code='PAID', is_published=True,
                          requires_payment=True, price=25.0)
            student = User(username='stranded', full_name='S',
                           email='s@test.local', role='student',
                           password_hash='x')
            other = User(username='fine', full_name='F', email='f@test.local',
                         role='student', password_hash='x')
            db.session.add_all([free, paid, student, other])
            db.session.commit()

            db.session.add_all([
                Enrollment(user_id=student.id, course_id=free.id,
                           status='pending', payment_status='not_required'),
                Enrollment(user_id=student.id, course_id=paid.id,
                           status='pending', payment_status='pending'),
                Enrollment(user_id=other.id, course_id=free.id,
                           status='active', payment_status='not_required'),
            ])
            db.session.commit()
            return {'free': free.id, 'paid': paid.id,
                    'student': student.id, 'other': other.id}
    return _build


def status_of(user_id, course_id):
    return Enrollment.query.filter_by(user_id=user_id,
                                      course_id=course_id).first().status


class TestTheDryRunChangesNothing:
    def test_reporting_leaves_every_row_alone(self, app, world, monkeypatch,
                                              capsys):
        ids = world()
        monkeypatch.setattr(migration.sys, 'argv',
                            ['release_stranded_enrolments'])
        monkeypatch.setattr(migration, 'create_app', lambda: app)

        assert migration.main() == 0

        with app.app_context():
            assert status_of(ids['student'], ids['free']) == 'pending'
        assert 'dry run' in capsys.readouterr().out.lower()


class TestApplyReleasesOnlyWhatIsStuck:
    @pytest.fixture(autouse=True)
    def _run(self, app, world, monkeypatch):
        self.ids = world()
        monkeypatch.setattr(migration.sys, 'argv',
                            ['release_stranded_enrolments', '--apply'])
        monkeypatch.setattr(migration, 'create_app', lambda: app)
        assert migration.main() == 0

    def test_the_free_course_is_released(self, app):
        with app.app_context():
            assert status_of(self.ids['student'], self.ids['free']) == 'active'

    def test_the_paid_course_still_waits_for_payment(self, app):
        with app.app_context():
            assert status_of(self.ids['student'], self.ids['paid']) == 'pending'

    def test_an_already_active_enrolment_is_untouched(self, app):
        with app.app_context():
            assert status_of(self.ids['other'], self.ids['free']) == 'active'

    def test_nothing_is_deleted(self, app):
        with app.app_context():
            assert Enrollment.query.count() == 3
            assert User.query.count() == 2
            assert Course.query.count() == 2

    def test_the_released_student_can_now_open_the_course(self, app, client):
        with client.session_transaction() as s:
            s.update(user_id=self.ids['student'], role='student',
                     logged_in=True)
        response = client.get(
            f"/api/student/class/{self.ids['free']}/dashboard")
        assert response.status_code == 200

        listed = client.get('/api/student/classes').get_json()['classes']
        assert [c['title'] for c in listed] == ['Free Course']


class TestRunningItTwiceIsSafe:
    def test_a_second_apply_finds_nothing_left(self, app, world, monkeypatch,
                                               capsys):
        world()
        monkeypatch.setattr(migration, 'create_app', lambda: app)
        monkeypatch.setattr(migration.sys, 'argv',
                            ['release_stranded_enrolments', '--apply'])
        migration.main()
        capsys.readouterr()

        assert migration.main() == 0
        assert 'nothing to release' in capsys.readouterr().out.lower()
