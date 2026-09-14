"""Deploying must never destroy what is already there.

The installer runs ``run_seed_users.py`` every time. It used to overwrite the
password of any account whose username it recognised, so re-running the
installer on a live server silently reset the administrator's password back
to ``admin123`` — reverting a deliberate change and handing superadmin to
anyone who knew the default.

These tests pin that it now only fills in what is missing, and that the
schema work the app does at startup is additive.
"""

import hashlib

from app.models import User, db

import run_seed_users


def make_user(username, password, role='student', full_name='Someone'):
    db.session.add(User(
        username=username,
        password_hash=hashlib.sha256(password.encode()).hexdigest(),
        role=role, full_name=full_name, email=f'{username}@example.com'))
    db.session.commit()


def password_of(username):
    return User.query.filter_by(username=username).first().password_hash


class TestExistingAccountsSurvive:
    def test_an_existing_password_is_not_reset(self, app):
        with app.app_context():
            make_user('admin', 'TheOperatorsOwnPassword', role='superadmin')
            before = password_of('admin')

            outcome = run_seed_users.ensure_user(
                'admin', 'admin123', 'superadmin', 'System Administrator')

            assert outcome == 'kept'
            assert password_of('admin') == before

    def test_an_edited_role_and_name_are_not_reverted(self, app):
        with app.app_context():
            make_user('demoteacher1', 'whatever', role='admin',
                      full_name='Dr Real Person')

            run_seed_users.ensure_user('demoteacher1', 'demo123', 'instructor',
                                       'Demo Teacher One')

            user = User.query.filter_by(username='demoteacher1').first()
            assert user.role == 'admin'
            assert user.full_name == 'Dr Real Person'

    def test_a_missing_account_is_still_created(self, app):
        with app.app_context():
            outcome = run_seed_users.ensure_user(
                'admin', 'admin123', 'superadmin', 'System Administrator')
            assert outcome == 'created'
            assert User.query.filter_by(username='admin').first() is not None

    def test_seeding_twice_creates_one_account(self, app):
        with app.app_context():
            run_seed_users.ensure_user('admin', 'admin123', 'superadmin', 'A')
            run_seed_users.ensure_user('admin', 'admin123', 'superadmin', 'A')
            assert User.query.filter_by(username='admin').count() == 1

    def test_unrelated_accounts_are_never_touched(self, app):
        """The real risk: a live system full of real users."""
        with app.app_context():
            for n in range(5):
                make_user(f'student{n}', f'password{n}')
            before = {f'student{n}': password_of(f'student{n}')
                      for n in range(5)}

            for username, password, role, name in \
                    [run_seed_users.SEED_ADMIN] + run_seed_users.SEED_DEMO:
                run_seed_users.ensure_user(username, password, role, name)

            assert User.query.count() == 5 + 1 + len(run_seed_users.SEED_DEMO)
            for username, hashed in before.items():
                assert password_of(username) == hashed


class TestResetIsOptIn:
    def test_reset_passwords_still_works_when_asked(self, app):
        with app.app_context():
            make_user('admin', 'SomethingElse', role='superadmin')

            outcome = run_seed_users.ensure_user(
                'admin', 'admin123', 'superadmin', 'System Administrator',
                reset_passwords=True)

            assert outcome == 'reset'
            assert password_of('admin') == \
                hashlib.sha256(b'admin123').hexdigest()

    def test_reset_does_not_change_role_or_name(self, app):
        with app.app_context():
            make_user('admin', 'SomethingElse', role='superadmin',
                      full_name='Named By Hand')

            run_seed_users.ensure_user('admin', 'admin123', 'superadmin',
                                       'System Administrator',
                                       reset_passwords=True)

            user = User.query.filter_by(username='admin').first()
            assert user.full_name == 'Named By Hand'


class TestStartupIsAdditive:
    def test_creating_the_app_does_not_drop_existing_rows(self, app):
        """create_all() runs on every start; it must only add."""
        with app.app_context():
            make_user('someone', 'secret')
            before = User.query.count()

        # A second create_app() is what a restart does.
        from app import create_app
        create_app()

        with app.app_context():
            assert User.query.count() == before
            assert User.query.filter_by(username='someone').first() is not None

    def test_nothing_in_startup_calls_drop_all(self):
        """A regression guard: drop_all() anywhere in the startup path would
        empty the database on restart."""
        import pathlib
        source = pathlib.Path('app/__init__.py').read_text(encoding='utf-8')
        assert 'drop_all' not in source
        assert 'DROP TABLE' not in source.upper().replace('IF EXISTS', '')
