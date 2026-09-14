"""Admin > AI Settings must tell the truth, and never hand the page HTML.

Two faults met on this screen. It read only the environment and the encrypted
database table, so a key living in ``config.yaml`` -- where the installer puts
them -- was reported "Not set / No key configured" while the platform was
happily using it. And the guard on those endpoints branched on
``request.is_json``, which only describes what the caller *sent*: a GET or a
DELETE never matched, so an expired or under-privileged session was answered
with a 302 to the login page. The screen ran ``await r.json()`` on the HTML
and showed the administrator::

    Unexpected token '<', "<!doctype "... is not valid JSON
"""

import pathlib

import pytest

from app.models import User, db


@pytest.fixture
def signed_in(app, client):
    def _login(role='superadmin'):
        with app.app_context():
            user = User.query.filter_by(username=f'u_{role}').first()
            if user is None:
                user = User(username=f'u_{role}', full_name='U',
                            email=f'{role}@test.local', role=role,
                            password_hash='x')
                db.session.add(user)
                db.session.commit()
            user_id = user.id
        with client.session_transaction() as s:
            s.update(user_id=user_id, role=role, logged_in=True,
                     is_admin=True)
        return user_id
    return _login


def provider(body, name):
    return next(p for p in body['providers'] if p['id'] == name)


class TestAKeyInConfigYamlIsReportedAsConfigured:
    def test_the_screen_agrees_with_the_key_resolver(self, app, client,
                                                     signed_in, monkeypatch):
        """Whatever get_api_key() would use is what the screen must show."""
        from app.utils import api_key_helper

        monkeypatch.setattr(api_key_helper, '_from_environment',
                            lambda p: None)
        monkeypatch.setattr(api_key_helper, '_from_config_file',
                            lambda p: 'a-key-from-the-file' if p == 'claude' else None)
        monkeypatch.setattr(api_key_helper, '_from_database', lambda p: None)

        signed_in('superadmin')
        response = client.get('/admin/api/ai-config')
        assert response.status_code == 200
        claude = provider(response.get_json(), 'claude')

        assert claude['configured'] is True, \
            'a key in config.yaml was reported as not set'
        assert claude['source'] == 'config.yaml'
        assert claude['key_preview']

    def test_a_provider_with_no_key_anywhere_is_still_not_set(
            self, client, signed_in, monkeypatch):
        from app.utils import api_key_helper
        for source in ('_from_environment', '_from_config_file',
                       '_from_database'):
            monkeypatch.setattr(api_key_helper, source, lambda p: None)

        signed_in('superadmin')
        claude = provider(client.get('/admin/api/ai-config').get_json(),
                          'claude')
        assert claude['configured'] is False
        assert claude['source'] == 'none'
        assert claude['key_preview'] == ''

    def test_the_environment_still_wins(self, client, signed_in, monkeypatch):
        from app.utils import api_key_helper
        monkeypatch.setattr(api_key_helper, '_from_environment',
                            lambda p: 'from-env' if p == 'claude' else None)
        monkeypatch.setattr(api_key_helper, '_from_config_file',
                            lambda p: 'from-file')
        monkeypatch.setattr(api_key_helper, '_from_database', lambda p: None)

        signed_in('superadmin')
        claude = provider(client.get('/admin/api/ai-config').get_json(),
                          'claude')
        assert claude['source'] == 'env'

    def test_no_response_ever_carries_the_key_itself(self, client, signed_in,
                                                     monkeypatch):
        from app.utils import api_key_helper
        secret = 'sk-do-not-leak-this-value-0123456789'
        monkeypatch.setattr(api_key_helper, '_from_config_file',
                            lambda p: secret)
        monkeypatch.setattr(api_key_helper, '_from_environment', lambda p: None)
        monkeypatch.setattr(api_key_helper, '_from_database', lambda p: None)

        signed_in('superadmin')
        body = client.get('/admin/api/ai-config').get_data(as_text=True)
        assert secret not in body
        assert secret[4:20] not in body


class TestTheScreenIsNeverHandedHtml:
    """Every refusal on an API path must be JSON the page can read."""

    ENDPOINTS = [
        ('GET', '/admin/api/ai-config'),
        ('DELETE', '/admin/api/ai-credentials/claude'),
        ('POST', '/admin/api/test-api-key'),
        ('POST', '/admin/api/ai-credentials'),
    ]

    @pytest.mark.parametrize('method,path', ENDPOINTS)
    def test_a_signed_out_caller_gets_json(self, client, method, path):
        response = client.open(path, method=method)
        assert response.status_code in (401, 403), response.status_code
        assert response.is_json, \
            f'{method} {path} answered {response.content_type}, not JSON'
        assert 'error' in response.get_json()

    @pytest.mark.parametrize('method,path', ENDPOINTS)
    def test_a_non_super_admin_gets_json(self, client, signed_in, method, path):
        signed_in('instructor')
        response = client.open(path, method=method)
        assert response.status_code == 403
        assert response.is_json, \
            f'{method} {path} answered {response.content_type}, not JSON'

    def test_the_body_is_not_a_redirect_to_a_login_page(self, client):
        """This is the exact shape that produced the error message."""
        response = client.get('/admin/api/ai-config')
        body = response.get_data(as_text=True)
        assert not body.lstrip().lower().startswith('<!doctype'), \
            'the page would report: Unexpected token \'<\''
        assert response.status_code != 302

    def test_the_html_page_itself_still_redirects(self, client):
        """Only the API answers JSON; a browser hitting the page is sent
        to the login screen as before."""
        response = client.get('/admin/integrations')
        assert response.status_code == 302
        assert 'login' in response.headers.get('Location', '').lower()

    def test_a_super_admin_is_let_through(self, client, signed_in):
        signed_in('superadmin')
        assert client.get('/admin/api/ai-config').status_code == 200


class TestTheScreenReadsResponsesDefensively:
    def test_it_parses_through_one_helper(self):
        page = pathlib.Path('templates/admin_integrations.html').read_text(
            encoding='utf-8')
        assert 'async function readJson' in page
        assert 'await r.json()' not in page, \
            'every response must go through readJson so HTML is explained'

    def test_it_knows_config_yaml_as_a_source(self):
        page = pathlib.Path('templates/admin_integrations.html').read_text(
            encoding='utf-8')
        assert "'config.yaml'" in page, \
            'a key from config.yaml would be mislabelled as DB'


class TestApiErrorsAreAlwaysJson:
    """Flask answers errors with an HTML page, and every screen here parses
    responses as JSON. Under /api/ the errors are JSON instead, so a failure
    says what went wrong rather than "Unexpected token '<'"."""

    @pytest.mark.parametrize('method,path,expected', [
        ('GET', '/api/there-is-no-such-endpoint', 404),
        ('POST', '/api/classes/my-courses', 405),
        ('POST', '/api/auth/login', 415),
    ])
    def test_the_error_is_readable(self, client, method, path, expected):
        response = client.open(path, method=method)
        assert response.status_code == expected
        assert response.is_json, \
            f'{method} {path} answered {response.content_type}'
        body = response.get_json()
        assert body['error']
        assert body['status'] == expected

    def test_an_ordinary_page_still_gets_an_html_error(self, client):
        """Only /api/ changes; a person typing a bad URL sees a page."""
        response = client.get('/no-such-page')
        assert response.status_code == 404
        assert 'text/html' in response.content_type

    def test_an_unhandled_crash_is_json_without_leaking_detail(self):
        """A fresh app, because routes cannot be added to one that has
        already served a request."""
        from app import create_app

        fresh = create_app()
        fresh.config['TESTING'] = False        # exercise the handler, not the
        fresh.config['PROPAGATE_EXCEPTIONS'] = False   # test re-raise path

        @fresh.route('/api/_boom_for_tests')
        def boom():
            raise RuntimeError('a secret-looking internal detail')

        response = fresh.test_client().get('/api/_boom_for_tests')
        assert response.status_code == 500
        assert response.is_json, response.content_type
        assert 'secret-looking' not in response.get_data(as_text=True)
        assert 'server.log' in response.get_json()['error']


class TestTheTestButtonUsesTheCatalogue:
    """Testing a key must not fail because the test named a retired model.

    Each provider test used to build its own request with a model id written
    inline. Those went stale: a valid Claude key reported
    "404 not_found_error: model: claude-sonnet-4-20250514", which reads as a
    bad key rather than a model that no longer exists.
    """

    def test_no_model_id_is_written_into_the_admin_routes(self):
        import re

        source = pathlib.Path('app/routes/super_admin.py').read_text(
            encoding='utf-8')
        code = '\n'.join(
            line for line in source.splitlines()
            if not line.lstrip().startswith('#'))
        # Docstrings quote the old ids while explaining the fix; strip them.
        code = re.sub(r'"""(?:.|\n)*?"""', '', code)

        for retired in ('claude-sonnet-4-20250514', 'gemini-2.5-flash',
                        'grok-3-mini', 'gpt-4.1'):
            assert retired not in code, \
                f'{retired} is named in code; it belongs in config.yaml'

    def test_the_model_comes_from_the_catalogue(self, monkeypatch):
        from app.routes import super_admin
        from app.services import model_registry as registry

        seen = {}

        def fake_chat(**kwargs):
            seen.update(kwargs)
            from app.services.ai_transport import ChatResult
            return ChatResult(text='hello', provider='claude',
                              model=kwargs['model'])

        monkeypatch.setattr(
            'app.services.ai_transport.chat_anthropic', fake_chat)

        result = super_admin._test_chat_provider('claude', 'a-key', 'hi')
        assert result['success'] is True
        assert seen['model'] == registry.default_model('claude'), \
            'the test used a model the catalogue does not name as default'

    def test_a_provider_error_is_reported_with_the_model(self, monkeypatch):
        from app.routes import super_admin
        from app.services.ai_transport import AIError

        def boom(**kwargs):
            raise AIError('the provider said no')

        monkeypatch.setattr(
            'app.services.ai_transport.chat_anthropic', boom)

        result = super_admin._test_chat_provider('claude', 'a-key', 'hi')
        assert result['success'] is False
        assert 'the provider said no' in result['message']
        assert result['model']

    def test_an_unknown_provider_is_refused_cleanly(self):
        from app.routes import super_admin

        result = super_admin._test_chat_provider('nope', 'k', 'hi')
        assert result['success'] is False
        assert 'catalogue' in result['message']

    def test_a_fallback_is_disclosed(self, monkeypatch):
        """If the default was unavailable, say which model actually answered."""
        from app.routes import super_admin
        from app.services.ai_transport import ChatResult

        monkeypatch.setattr(
            'app.services.ai_transport.chat_anthropic',
            lambda **k: ChatResult(text='hi', provider='claude',
                                   model='the-stand-in',
                                   fallback_from='the-default'))

        result = super_admin._test_chat_provider('claude', 'k', 'hi')
        assert result['success'] is True
        assert 'the-stand-in' in result['message']
        assert 'the-default' in result['message']


class TestNonChatProvidersAreTestedProperly:
    def test_an_image_provider_is_checked_without_generating_anything(
            self, monkeypatch):
        """Image models cannot answer a prompt, and making a picture to prove
        a key works costs money. Listing models uses the same credential and
        is free."""
        from app.routes import super_admin

        class Response:
            status_code = 200
            text = ''

            @staticmethod
            def json():
                return {'data': [{'id': 'a'}, {'id': 'b'}]}

        called = {}

        class Session:
            @staticmethod
            def get(url, **kwargs):
                called['url'] = url
                return Response()

        monkeypatch.setattr('app.services.ai_transport._http',
                            lambda: Session())

        result = super_admin._test_chat_provider('images', 'a-key', 'hi')
        assert result['success'] is True
        assert '2 models visible' in result['message']
        assert called['url'].startswith('https://')

    def test_a_rejected_key_is_reported(self, monkeypatch):
        from app.routes import super_admin

        class Response:
            status_code = 401
            text = 'invalid api key'

        monkeypatch.setattr(
            'app.services.ai_transport._http',
            lambda: type('S', (), {'get': staticmethod(
                lambda url, **k: Response())})())

        result = super_admin._test_chat_provider('images', 'bad', 'hi')
        assert result['success'] is False
        assert '401' in result['message']

    def test_the_prompt_budget_leaves_room_for_an_answer(self):
        """64 tokens was not enough for a reasoning model: the thinking used
        it up and the empty reply looked like a broken key."""
        import re

        source = pathlib.Path('app/routes/super_admin.py').read_text(
            encoding='utf-8')
        block = source[source.index('def _test_chat_provider'):]
        block = block[:block.index('\ndef ')]
        budget = int(re.search(r'max_tokens=(\d+)', block).group(1))
        assert budget >= 256, f'max_tokens={budget} is too tight to answer'
