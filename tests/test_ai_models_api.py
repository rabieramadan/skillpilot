"""The admin API for the model catalogue.

Covers the flow an administrator actually follows — see what a provider
offers, test a candidate, save it only after confirming — plus the guards
that stop an untested or malformed model reaching config.yaml.

The provider calls are faked, so these run offline. What they pin is the
contract: which shapes go in, which come back, and who is allowed to ask.
"""

import textwrap

import pytest

from app.services import ai_transport, model_registry as registry


CATALOGUE = textwrap.dedent('''\
    api_keys:
      openai: ""

    app:
      prompt_suggestion_provider: openai

    ai_models:
      demo:
        label: "Demo Provider"
        driver: openai_compatible
        base_url: "https://api.demo.example/v1"
        discovery_url: "https://api.demo.example/v1/models"
        enabled: true
        env_vars: [DEMO_API_KEY]
        default_model: "demo-large"
        fallbacks: ["demo-large", "demo-small"]
        models:
          - id: "demo-large"
            label: "Demo Large"
            max_output_tokens: 8000
          - id: "demo-small"
            label: "Demo Small"
            max_output_tokens: 4000
    ''')


@pytest.fixture
def catalogue(tmp_path, monkeypatch):
    path = tmp_path / 'config.yaml'
    path.write_text(CATALOGUE, encoding='utf-8')
    monkeypatch.setenv('SKILLPILOT_CONFIG', str(path))
    monkeypatch.setenv('DEMO_API_KEY', 'test-key')
    registry.reload_config()
    yield path
    registry.reload_config()


@pytest.fixture
def admin(client):
    with client.session_transaction() as session:
        session.update({'user_id': 'admin-1', 'role': 'superadmin',
                        'logged_in': True, 'is_admin': True})
    return client


@pytest.fixture
def student(client):
    with client.session_transaction() as session:
        session.update({'user_id': 'student-1', 'role': 'student',
                        'logged_in': True})
    return client


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.headers = {}
        self.text = str(body)

    def json(self):
        return self._body


def reply(text='model ready', model='demo-large'):
    return FakeResponse(200, {
        'model': model,
        'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 12, 'completion_tokens': 3},
    })


@pytest.fixture
def fake_provider(monkeypatch):
    """Replace the shared HTTP session so no real request is made."""
    calls = []

    class Session:
        responses = [reply()]

        def post(self, url, headers=None, json=None, timeout=None):
            calls.append({'url': url, 'payload': json or {}})
            return self.responses[0] if len(self.responses) == 1 \
                else self.responses.pop(0)

        def get(self, url, headers=None, timeout=None):
            calls.append({'url': url, 'headers': headers or {}})
            return self.responses[0]

    session = Session()
    monkeypatch.setattr(ai_transport, '_session', session)
    monkeypatch.setattr(ai_transport.time, 'sleep', lambda *_: None)
    session.calls = calls
    yield session
    monkeypatch.setattr(ai_transport, '_session', None)


class TestAccess:
    def test_a_student_cannot_read_the_catalogue(self, catalogue, student):
        assert student.get('/api/ai-models').status_code == 403

    def test_a_student_cannot_save_a_model(self, catalogue, student):
        response = student.post('/api/ai-models/save', json={
            'provider': 'demo', 'confirmed': True, 'model': {'id': 'x'}})
        assert response.status_code == 403

    def test_signed_out_is_rejected(self, catalogue, client):
        assert client.get('/api/ai-models').status_code == 401

    def test_an_admin_can_read_the_catalogue(self, catalogue, admin):
        assert admin.get('/api/ai-models').status_code == 200


class TestCatalogueEndpoint:
    def test_it_reports_the_file_and_the_models(self, catalogue, admin):
        body = admin.get('/api/ai-models').get_json()
        assert body['success'] is True
        assert body['registry']['source'] == str(catalogue)
        assert [m['id'] for m in body['providers']['demo']['models']] == \
            ['demo-large', 'demo-small']

    def test_it_never_returns_a_key(self, catalogue, admin):
        body = admin.get('/api/ai-models').get_json()
        rendered = repr(body)
        assert 'test-key' not in rendered
        assert 'env_vars' not in body['providers']['demo']
        # It does say whether one is configured.
        assert body['providers']['demo']['configured'] is True


class TestDiscovery:
    def test_it_marks_which_models_are_already_catalogued(
            self, catalogue, admin, fake_provider):
        fake_provider.responses = [FakeResponse(200, {'data': [
            {'id': 'demo-large'}, {'id': 'demo-next'}]})]
        body = admin.post('/api/ai-models/discover',
                          json={'provider': 'demo'}).get_json()
        assert body['success'] is True
        found = {m['id']: m['in_catalogue'] for m in body['models']}
        assert found == {'demo-large': True, 'demo-next': False}

    def test_it_flags_catalogued_models_the_provider_no_longer_offers(
            self, catalogue, admin, fake_provider):
        fake_provider.responses = [FakeResponse(200, {'data': [{'id': 'demo-large'}]})]
        body = admin.post('/api/ai-models/discover',
                          json={'provider': 'demo'}).get_json()
        assert body['not_listed_by_provider'] == ['demo-small']

    def test_an_unknown_provider_is_a_clear_404(self, catalogue, admin):
        response = admin.post('/api/ai-models/discover', json={'provider': 'nope'})
        assert response.status_code == 404
        assert 'no provider' in response.get_json()['error']


class TestTesting:
    def test_a_working_model_reports_the_reply_and_usage(
            self, catalogue, admin, fake_provider):
        fake_provider.responses = [reply('model ready', 'demo-next')]
        body = admin.post('/api/ai-models/test', json={
            'provider': 'demo', 'model_id': 'demo-next'}).get_json()

        assert body['success'] is True
        assert body['reply'] == 'model ready'
        assert body['usage']['completion_tokens'] == 3
        assert body['in_catalogue'] is False
        assert isinstance(body['elapsed_ms'], int)

    def test_a_rejected_model_is_a_failure_even_though_fallback_answered(
            self, catalogue, admin, fake_provider):
        """The fallback chain rescues the request, which would otherwise hide
        the fact that the identifier the admin typed does not work."""
        fake_provider.responses = [
            FakeResponse(404, {'error': {'message': 'The model does not exist'}}),
            reply('rescued', 'demo-large'),
        ]
        body = admin.post('/api/ai-models/test', json={
            'provider': 'demo', 'model_id': 'demo-typo'}).get_json()

        assert body['success'] is False
        assert 'demo-typo' in body['error']
        assert 'hint' in body

    def test_a_bad_key_is_explained_not_just_reported(
            self, catalogue, admin, fake_provider):
        fake_provider.responses = [FakeResponse(401, {'error': {'message': 'bad key'}})]
        body = admin.post('/api/ai-models/test', json={
            'provider': 'demo', 'model_id': 'demo-large'}).get_json()
        assert body['success'] is False
        assert 'API key' in body['hint']

    def test_a_missing_model_id_is_refused(self, catalogue, admin):
        response = admin.post('/api/ai-models/test', json={'provider': 'demo'})
        assert response.status_code == 400

    def test_a_provider_without_a_key_is_refused_before_calling_out(
            self, catalogue, admin, monkeypatch):
        monkeypatch.delenv('DEMO_API_KEY', raising=False)
        response = admin.post('/api/ai-models/test', json={
            'provider': 'demo', 'model_id': 'demo-large'})
        assert response.status_code == 400
        assert 'API key' in response.get_json()['error']


class TestSaving:
    def test_saving_needs_confirmation(self, catalogue, admin):
        response = admin.post('/api/ai-models/save', json={
            'provider': 'demo', 'model': {'id': 'demo-next'}})
        assert response.status_code == 400
        assert 'confirmed' in response.get_json()['error']
        assert registry.get_model('demo', 'demo-next') is None

    def test_a_confirmed_save_writes_to_the_file(self, catalogue, admin):
        body = admin.post('/api/ai-models/save', json={
            'provider': 'demo', 'confirmed': True,
            'model': {'id': 'demo-next', 'label': 'Demo Next',
                      'max_output_tokens': 9000}}).get_json()

        assert body['success'] is True
        assert 'demo-next' in catalogue.read_text(encoding='utf-8')
        assert registry.get_model('demo', 'demo-next').max_output_tokens == 9000

    def test_save_and_use_switches_the_default_in_one_step(self, catalogue, admin):
        body = admin.post('/api/ai-models/save', json={
            'provider': 'demo', 'confirmed': True, 'make_default': True,
            'model': {'id': 'demo-next'}}).get_json()

        assert body['made_default'] is True
        assert body['providers']['demo']['default_model'] == 'demo-next'
        assert registry.default_model('demo') == 'demo-next'

    def test_an_invalid_id_never_reaches_the_file(self, catalogue, admin):
        before = catalogue.read_text(encoding='utf-8')
        response = admin.post('/api/ai-models/save', json={
            'provider': 'demo', 'confirmed': True, 'model': {'id': 'bad id!'}})
        assert response.status_code == 400
        assert catalogue.read_text(encoding='utf-8') == before

    def test_the_response_carries_the_refreshed_catalogue(self, catalogue, admin):
        body = admin.post('/api/ai-models/save', json={
            'provider': 'demo', 'confirmed': True,
            'model': {'id': 'demo-next'}}).get_json()
        ids = [m['id'] for m in body['providers']['demo']['models']]
        assert 'demo-next' in ids


class TestDefaultsAndRemoval:
    def test_setting_a_default(self, catalogue, admin):
        body = admin.post('/api/ai-models/default', json={
            'provider': 'demo', 'model_id': 'demo-small'}).get_json()
        assert body['success'] is True
        assert registry.default_model('demo') == 'demo-small'

    def test_setting_a_default_to_an_uncatalogued_model_is_refused(
            self, catalogue, admin):
        response = admin.post('/api/ai-models/default', json={
            'provider': 'demo', 'model_id': 'demo-imaginary'})
        assert response.status_code == 400
        assert registry.default_model('demo') == 'demo-large'

    def test_retiring_keeps_the_identifier_working(self, catalogue, admin):
        body = admin.delete('/api/ai-models/demo/demo-small').get_json()
        assert body['success'] is True
        assert registry.get_model('demo', 'demo-small') is None
        assert registry.resolve('demo', 'demo-small') == 'demo-large'

    def test_retiring_the_last_model_is_refused(self, catalogue, admin):
        admin.delete('/api/ai-models/demo/demo-small')
        response = admin.delete('/api/ai-models/demo/demo-large')
        assert response.status_code == 400
        assert registry.get_model('demo', 'demo-large') is not None

    def test_switching_a_provider_off_and_on(self, catalogue, admin):
        body = admin.post('/api/ai-models/demo/enabled',
                          json={'enabled': False}).get_json()
        assert body['success'] is True
        assert registry.get_provider('demo').enabled is False

        admin.post('/api/ai-models/demo/enabled', json={'enabled': True})
        assert registry.get_provider('demo').enabled is True


class TestLegacyPickerEndpoint:
    """The chat UI's model menu still reads /api/admin/models."""

    def test_it_serves_the_catalogue_in_the_old_shape(self, catalogue, client):
        body = client.get('/api/admin/models').get_json()
        assert body['source'] == 'config.yaml'
        demo = body['models']['demo']
        assert demo['default_version'] == 'demo-large'
        assert [v['id'] for v in demo['versions']] == ['demo-large', 'demo-small']

    def test_the_removed_bulk_write_explains_where_to_go(self, catalogue, admin):
        response = admin.put('/api/admin/models', json={})
        assert response.status_code == 410
        assert 'config.yaml' in response.get_json()['error']
