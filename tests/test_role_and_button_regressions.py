"""Guards for bugs found by sweeping every route and every button.

Three things were broken in ways that never raised an error in a log:

1. The role stored for the super admin is ``superadmin``. Several checks
   compared it against ``super_admin`` — a different string — so the real
   super admin was refused by every endpoint in ``app/routes/classes.py``,
   and the guard that stops the super admin being deleted never fired.
2. The Agentic AI Lab's "Execute Workflow" button posted to
   ``/api/agents/execute``, which matched ``/api/agents/<agent_id>`` and
   returned 405.
3. Shared JS helpers were defined at the end of ``<body>``, after the page
   scripts that call them while parsing.
"""

import pathlib

import pytest

from app.models import User, db


ROLE_SPELLINGS = ['superadmin', 'super_admin']


@pytest.fixture
def superadmin(app, client):
    """A super admin whose session role is spelled as the database spells it."""
    def _login(spelling='superadmin'):
        with app.app_context():
            user = User.query.filter_by(username='boss').first()
            if user is None:
                user = User(username='boss', full_name='The Boss',
                            email='boss@test.local', role=spelling,
                            password_hash='x')
                db.session.add(user)
                db.session.commit()
            user_id = user.id
        with client.session_transaction() as s:
            s['user_id'] = user_id
            s['role'] = spelling
            s['logged_in'] = True
            s['is_admin'] = True
        return user_id
    return _login


class TestTheSuperAdminIsRecognised:
    @pytest.mark.parametrize('spelling', ROLE_SPELLINGS)
    def test_super_admin_only_endpoints_admit_them(self, client, superadmin,
                                                   spelling):
        superadmin(spelling)
        response = client.get('/api/classes/enrollments')
        assert response.status_code != 401, \
            f'a super admin whose role is {spelling!r} was told to log in'

    @pytest.mark.parametrize('spelling', ROLE_SPELLINGS)
    def test_instructor_or_admin_endpoints_admit_them(self, client, superadmin,
                                                      spelling):
        superadmin(spelling)
        response = client.get('/api/classes/any-class-id/enrollments')
        assert response.status_code != 403, \
            f'a super admin whose role is {spelling!r} was refused'

    def test_a_student_is_still_refused(self, client, login_as):
        login_as('student')
        assert client.get('/api/classes/enrollments').status_code == 401

    def test_an_instructor_is_still_refused_super_admin_endpoints(
            self, client, login_as):
        login_as('instructor')
        assert client.get('/api/classes/enrollments').status_code == 401


class TestTheSuperAdminCannotBeDeleted:
    @pytest.mark.parametrize('spelling', ROLE_SPELLINGS)
    def test_the_guard_fires_for_either_spelling(self, app, client, superadmin,
                                                 spelling):
        """It compared against 'super_admin' only, so 'superadmin' slipped
        through and the account could be removed."""
        superadmin(spelling)
        with app.app_context():
            victim = User(username='other_boss', full_name='Also The Boss',
                          email='other@test.local', role=spelling,
                          password_hash='x')
            db.session.add(victim)
            db.session.commit()
            victim_id = victim.id

        response = client.delete(f'/admin/api/users/{victim_id}')

        with app.app_context():
            assert User.query.get(victim_id) is not None, \
                f'a super admin spelled {spelling!r} was deleted'
        assert response.status_code == 400


class TestTheWorkflowExecuteButton:
    def test_an_unsaved_workflow_can_be_run(self, client, login_as):
        """The canvas posts what it has, saved or not."""
        login_as('instructor')
        response = client.post('/api/agents/execute', json={'workflow': {
            'blocks': [{'id': 'b1', 'type': 'variable',
                        'label': 'Name', 'params': {'name': 'topic',
                                                    'value': 'statistics'}}],
            'connections': [],
        }})
        assert response.status_code == 200, response.data
        body = response.get_json()
        assert body['success'] is True
        assert body['variables'] == {'topic': 'statistics'}
        assert body['execution_log']

    def test_an_empty_canvas_is_explained_not_crashed(self, client, login_as):
        login_as('instructor')
        response = client.post('/api/agents/execute',
                               json={'workflow': {'blocks': []}})
        assert response.status_code == 400
        assert 'empty' in response.get_json()['error'].lower()

    def test_a_malformed_block_is_rejected(self, client, login_as):
        login_as('instructor')
        response = client.post('/api/agents/execute',
                               json={'workflow': {'blocks': [{'type': 'variable'}]}})
        assert response.status_code == 400

    def test_it_still_requires_a_login(self, client):
        assert client.post('/api/agents/execute',
                           json={'workflow': {'blocks': []}}).status_code == 401


class TestSharedHelpersLoadFirst:
    def test_eschtml_is_defined_before_the_content_block(self):
        """A page whose script calls escHtml while parsing threw
        'escHtml is not defined' and rendered nothing."""
        source = pathlib.Path('templates/_skp_base.html').read_text(
            encoding='utf-8')
        assert source.index('window.escHtml') < source.index('</head>'), \
            'escHtml must be defined in <head>, before any page script'

    def test_every_page_that_uses_it_inherits_the_base(self):
        users = [p for p in pathlib.Path('templates').glob('*.html')
                 if 'escHtml' in p.read_text(encoding='utf-8')
                 and p.name != '_skp_base.html']
        assert users, 'expected some templates to use escHtml'
        for page in users:
            assert '_skp_base.html' in page.read_text(encoding='utf-8'), \
                f'{page.name} uses escHtml but does not extend the base'


class TestPdfExportDegrades:
    def test_the_export_button_checks_the_library_is_there(self):
        """jsPDF comes from a CDN; destructuring it when absent threw an
        uncaught TypeError and the button silently did nothing."""
        source = pathlib.Path('static/js/app.js').read_text(encoding='utf-8')
        export = source[source.index('exportChat()'):]
        guard = export[:export.index('const { jsPDF }')]
        assert 'window.jspdf' in guard and 'return' in guard, \
            'exportChat() must bail out with a message when jsPDF is missing'


class TestTheDeveloperPortalRevokeButton:
    def test_the_key_is_actually_revoked(self, app, client, login_as, api_key):
        """The button sent DELETE /api/v1/keys/<id>, which matches no route,
        so the key stayed live and the list still showed it."""
        from app.models import ApiKey

        login_as('superadmin')
        _, key_id = api_key(['read'])

        response = client.post(f'/api/v1/keys/{key_id}/revoke')
        assert response.status_code == 200, response.data

        with app.app_context():
            assert ApiKey.query.get(key_id).revoked is True

    def test_the_page_calls_that_endpoint(self):
        source = pathlib.Path('templates/developer_portal.html').read_text(
            encoding='utf-8')
        revoke = source[source.index('async function revokeKey'):]
        revoke = revoke[:revoke.index('\n}')]
        assert "'/revoke'" in revoke or '/revoke' in revoke
        assert "method: 'DELETE'" not in revoke


class TestFaviconIsServed:
    def test_the_browser_gets_an_icon_instead_of_a_404(self, client):
        """Browsers request /favicon.ico on every page whether it is linked
        or not; there was no route, so each page load logged a 404."""
        response = client.get('/favicon.ico')
        assert response.status_code == 200
        assert response.data[:4] == b'\x00\x00\x01\x00', 'not an .ico'
        assert len(response.data) < 50_000, \
            'the icon should be small; it is fetched on every page'
