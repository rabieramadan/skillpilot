"""Where an API key comes from, and in what order.

One lookup serves the whole platform: environment, then config.yaml, then the
encrypted database store. These tests pin that order and — more importantly —
that every consumer sees the same answer. They previously did not: the admin
screens read the environment and the database while the chat route read the
environment and config.yaml, so a key saved in one place showed as configured
but was never used.

No test writes a real key anywhere.
"""

import textwrap

import pytest

from app.models import ApiCredential, db
from app.utils import api_key_helper
from app.utils.api_key_helper import (get_all_configured_providers, get_api_key,
                                      get_api_key_source)
from app.utils.encryption import encrypt_api_key

CATALOGUE = textwrap.dedent('''\
    api_keys:
      openai: ""
      demo: ""

    app:
      prompt_suggestion_provider: openai

    ai_models:
      demo:
        label: "Demo Provider"
        driver: openai_compatible
        base_url: "https://api.demo.example/v1"
        env_vars: [DEMO_API_KEY]
        default_model: "demo-large"
        models:
          - id: "demo-large"
            label: "Demo Large"
    ''')

ENV_VALUE = 'key-from-environment'
YAML_VALUE = 'key-from-config-file'
DB_VALUE = 'key-from-database'


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """A throwaway config.yaml, with helpers to set the key in it."""
    path = tmp_path / 'config.yaml'
    path.write_text(CATALOGUE, encoding='utf-8')
    monkeypatch.setenv('SKILLPILOT_CONFIG', str(path))
    for name in ('DEMO_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY',
                 'CLAUDE_API_KEY'):
        monkeypatch.delenv(name, raising=False)

    from app.services import model_registry as registry
    registry.reload_config()

    class ConfigFile:
        """The temporary config.yaml, with a helper to set a key in it."""

        def __init__(self, path):
            self.path = path

        def set_yaml_key(self, provider, value):
            text = self.path.read_text(encoding='utf-8').replace(
                f'  {provider}: ""', f'  {provider}: "{value}"')
            self.path.write_text(text, encoding='utf-8')
            from config.config import reload_api_keys
            reload_api_keys()

    yield ConfigFile(path)
    registry.reload_config()


@pytest.fixture
def stored_key(app):
    """Write an encrypted credential, as Admin > AI Settings does."""
    def store(provider, value=DB_VALUE):
        with app.app_context():
            db.session.add(ApiCredential(provider=provider,
                                         encrypted_key=encrypt_api_key(value),
                                         is_active=True))
            db.session.commit()
    return store


class TestPrecedence:
    def test_the_environment_wins(self, config_file, monkeypatch, stored_key,
                                  app):
        config_file.set_yaml_key('demo', YAML_VALUE)
        stored_key('demo')
        monkeypatch.setenv('DEMO_API_KEY', ENV_VALUE)
        with app.app_context():
            assert get_api_key('demo') == ENV_VALUE
            assert get_api_key_source('demo') == 'environment'

    def test_config_file_beats_the_database(self, config_file, stored_key, app):
        config_file.set_yaml_key('demo', YAML_VALUE)
        stored_key('demo')
        with app.app_context():
            assert get_api_key('demo') == YAML_VALUE
            assert get_api_key_source('demo') == 'config.yaml'

    def test_the_database_is_the_last_resort(self, config_file, stored_key, app):
        stored_key('demo')
        with app.app_context():
            assert get_api_key('demo') == DB_VALUE
            assert get_api_key_source('demo') == 'database'

    def test_nothing_configured_is_none_not_an_error(self, config_file, app):
        with app.app_context():
            assert get_api_key('demo') is None
            assert get_api_key_source('demo') is None

    def test_an_unknown_provider_is_none(self, config_file, app):
        with app.app_context():
            assert get_api_key('nosuchprovider') is None
            assert get_api_key('') is None


class TestEnvironmentVariableNames:
    """Both the vendor's name and the historical SkillPilot one work."""

    @pytest.mark.parametrize('variable', ['ANTHROPIC_API_KEY', 'CLAUDE_API_KEY'])
    def test_claude_accepts_either_name(self, config_file, monkeypatch, app,
                                        variable):
        monkeypatch.setenv(variable, ENV_VALUE)
        with app.app_context():
            assert get_api_key('claude') == ENV_VALUE

    def test_a_provider_added_only_in_yaml_uses_its_declared_variable(
            self, config_file, monkeypatch, app):
        """DEMO_API_KEY is named in config.yaml, nowhere in the code."""
        monkeypatch.setenv('DEMO_API_KEY', ENV_VALUE)
        with app.app_context():
            assert get_api_key('demo') == ENV_VALUE

    def test_image_generation_shares_the_openai_key(self, config_file,
                                                    monkeypatch, app):
        monkeypatch.setenv('OPENAI_API_KEY', ENV_VALUE)
        with app.app_context():
            assert get_api_key('images') == ENV_VALUE
            assert get_api_key('dalle') == ENV_VALUE


class TestHotReload:
    def test_editing_config_yaml_takes_effect_without_a_restart(
            self, config_file, app):
        with app.app_context():
            assert get_api_key('demo') is None
        config_file.set_yaml_key('demo', YAML_VALUE)
        with app.app_context():
            assert get_api_key('demo') == YAML_VALUE


class TestEveryConsumerAgrees:
    """The bug this replaced: screens and routes disagreeing about a key."""

    def test_the_chat_route_sees_a_key_from_config_yaml(self, config_file,
                                                        client, monkeypatch):
        config_file.set_yaml_key('demo', YAML_VALUE)

        seen = {}
        from app.services.ai_service import AIService

        def capture(self, provider, message, api_key, *args, **kwargs):
            seen['provider'] = provider
            seen['api_key'] = api_key
            return {'text': 'ok', 'provider': provider, 'model': 'demo-large'}

        monkeypatch.setattr(AIService, 'chat', capture)
        client.post('/api/chat/demo', data={'message': 'hi'})
        assert seen['api_key'] == YAML_VALUE

    def test_the_chat_route_sees_a_key_from_the_database(self, config_file,
                                                         client, stored_key,
                                                         monkeypatch):
        """This is what used to fail: the admin screen showed 'Configured'
        while the chat route reported no key at all."""
        stored_key('demo')

        seen = {}
        from app.services.ai_service import AIService
        monkeypatch.setattr(AIService, 'chat',
                            lambda self, provider, message, api_key, *a, **k:
                            (seen.update(api_key=api_key) or
                             {'text': 'ok', 'provider': provider, 'model': 'x'}))
        client.post('/api/chat/demo', data={'message': 'hi'})
        assert seen['api_key'] == DB_VALUE

    def test_the_admin_catalogue_and_the_chat_route_agree(self, config_file,
                                                          client, stored_key):
        stored_key('demo')
        with client.session_transaction() as session:
            session.update({'user_id': 'a', 'role': 'superadmin',
                            'logged_in': True, 'is_admin': True})
        body = client.get('/api/ai-models').get_json()
        assert body['providers']['demo']['configured'] is True

    def test_configured_providers_covers_every_source(self, config_file,
                                                      monkeypatch, stored_key,
                                                      app):
        config_file.set_yaml_key('openai', YAML_VALUE)
        stored_key('heygen')
        monkeypatch.setenv('DEMO_API_KEY', ENV_VALUE)
        with app.app_context():
            configured = get_all_configured_providers()
        assert {'openai', 'demo', 'heygen'} <= set(configured)


class TestNoKeyLeaks:
    def test_the_source_helper_reveals_no_key_material(self, config_file, app):
        config_file.set_yaml_key('demo', YAML_VALUE)
        with app.app_context():
            source = get_api_key_source('demo')
        assert source == 'config.yaml'
        assert YAML_VALUE not in source

    def test_the_admin_catalogue_returns_no_key(self, config_file, client):
        config_file.set_yaml_key('demo', YAML_VALUE)
        with client.session_transaction() as session:
            session.update({'user_id': 'a', 'role': 'superadmin',
                            'logged_in': True, 'is_admin': True})
        rendered = client.get('/api/ai-models').get_data(as_text=True)
        assert YAML_VALUE not in rendered

    def test_the_public_model_catalogue_returns_no_key(self, config_file, client):
        config_file.set_yaml_key('demo', YAML_VALUE)
        rendered = client.get('/api/models/catalogue').get_data(as_text=True)
        assert YAML_VALUE not in rendered


class TestResilience:
    def test_a_database_failure_falls_back_to_the_file(self, config_file,
                                                       monkeypatch, app):
        """A key in config.yaml must still work if the database is down."""
        config_file.set_yaml_key('demo', YAML_VALUE)

        def explode(*args, **kwargs):
            raise RuntimeError('database is unreachable')

        monkeypatch.setattr(api_key_helper, '_from_database', explode)
        with app.app_context():
            assert get_api_key('demo') == YAML_VALUE

    def test_lookup_outside_an_application_context_does_not_raise(
            self, config_file):
        """Startup checks run before the app exists."""
        config_file.set_yaml_key('demo', YAML_VALUE)
        assert get_api_key('demo') == YAML_VALUE
