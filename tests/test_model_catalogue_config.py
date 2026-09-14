"""The catalogue is config, not code.

These tests pin the properties that make model churn a config edit: a
provider defined only in YAML is callable, edits survive a round-trip with
comments intact, a bad edit is refused before it reaches disk, and the file
is re-read when it changes underneath a running process.

Every test works on a temporary copy of config.yaml, so none of them touch
the real one.
"""

import os
import textwrap

import pytest
import yaml

from app.services import model_registry as registry


MINIMAL = textwrap.dedent('''\
    # A comment at the top that must survive every edit.
    api_keys:
      openai: ""

    app:
      debug: false
      prompt_suggestion_provider: openai

    ai_models:
      # A comment inside the catalogue.
      demo:
        label: "Demo Provider"
        driver: openai_compatible
        base_url: "https://api.demo.example/v1"
        enabled: true
        env_vars: [DEMO_API_KEY]
        default_model: "demo-large"
        fallbacks: ["demo-large", "demo-small"]
        models:
          - id: "demo-large"
            label: "Demo Large"
            summary: "The capable one."
            context_tokens: 200000
            max_output_tokens: 8000
            vision: true
            sampling: true
            price_per_million: {input: 1.0, output: 4.0}
          - id: "demo-small"
            label: "Demo Small"
            max_output_tokens: 4000
        aliases:
          "demo-ancient": "demo-large"
    ''')


@pytest.fixture
def catalogue(tmp_path, monkeypatch):
    """Point the registry at a throwaway config.yaml."""
    path = tmp_path / 'config.yaml'
    path.write_text(MINIMAL, encoding='utf-8')
    monkeypatch.setenv('SKILLPILOT_CONFIG', str(path))
    monkeypatch.delenv('SKILLPILOT_MODEL_DEMO', raising=False)
    registry.reload_config()
    yield path
    registry.reload_config()


def read(path):
    return yaml.safe_load(path.read_text(encoding='utf-8'))


class TestLoading:
    def test_a_provider_defined_only_in_yaml_is_usable(self, catalogue):
        spec = registry.get_provider('demo')
        assert spec is not None
        assert spec.driver == 'openai_compatible'
        assert registry.default_model('demo') == 'demo-large'
        assert registry.base_url('demo') == 'https://api.demo.example/v1'

    def test_capabilities_come_from_the_file(self, catalogue):
        model = registry.get_model('demo', 'demo-large')
        assert model.vision is True
        assert model.sampling is True
        assert model.context_tokens == 200000
        assert registry.price_per_1k('demo', 'demo-large') == {
            'input': 0.001, 'output': 0.004}

    def test_aliases_from_the_file_resolve(self, catalogue):
        assert registry.resolve('demo', 'demo-ancient') == 'demo-large'

    def test_status_reports_the_file_it_read(self, catalogue):
        status = registry.catalogue_status()
        assert status['source'] == str(catalogue)
        assert status['provider_count'] == 1
        assert status['model_count'] == 2
        assert status['warnings'] == []

    def test_a_missing_file_falls_back_instead_of_crashing(self, tmp_path, monkeypatch):
        monkeypatch.setenv('SKILLPILOT_CONFIG', str(tmp_path / 'absent.yaml'))
        registry.reload_config()
        try:
            status = registry.catalogue_status()
            assert status['source'] == 'built-in'
            # Still usable: the admin screens must stay reachable.
            assert registry.default_model('openai')
        finally:
            registry.reload_config()

    def test_broken_yaml_falls_back_instead_of_crashing(self, tmp_path, monkeypatch):
        broken = tmp_path / 'config.yaml'
        broken.write_text('ai_models: [this is not: valid: yaml', encoding='utf-8')
        monkeypatch.setenv('SKILLPILOT_CONFIG', str(broken))
        registry.reload_config()
        try:
            assert registry.catalogue_status()['source'] == 'built-in'
        finally:
            registry.reload_config()


class TestSelfHealing:
    """A hand edit that is wrong in a small way should not take the site down."""

    def _write(self, path, mutate):
        data = MINIMAL
        for old, new in mutate:
            data = data.replace(old, new)
        path.write_text(data, encoding='utf-8')
        registry.reload_config()

    def test_a_default_naming_an_uncatalogued_model_is_corrected(self, catalogue):
        self._write(catalogue, [('default_model: "demo-large"',
                                 'default_model: "demo-typo"')])
        assert registry.default_model('demo') in ('demo-large', 'demo-small')
        assert any('demo-typo' in w for w in registry.catalogue_status()['warnings'])

    def test_an_alias_pointing_nowhere_is_dropped(self, catalogue):
        self._write(catalogue, [('"demo-ancient": "demo-large"',
                                 '"demo-ancient": "demo-gone"')])
        assert registry.resolve('demo', 'demo-ancient') == 'demo-ancient'
        assert any('demo-gone' in w for w in registry.catalogue_status()['warnings'])

    def test_an_unknown_driver_is_reported_not_hidden(self, catalogue):
        self._write(catalogue, [('driver: openai_compatible', 'driver: telepathy')])
        spec = registry.get_provider('demo')
        assert spec is not None and spec.supported is False
        assert any('telepathy' in w for w in registry.catalogue_status()['warnings'])


class TestWriting:
    def test_saving_a_model_preserves_comments(self, catalogue):
        registry.save_model('demo', {'id': 'demo-new', 'label': 'Demo New'})
        text = catalogue.read_text(encoding='utf-8')
        assert '# A comment at the top that must survive every edit.' in text
        assert '# A comment inside the catalogue.' in text
        assert 'demo-new' in text

    def test_saving_makes_the_model_available_immediately(self, catalogue):
        registry.save_model('demo', {'id': 'demo-new', 'label': 'Demo New',
                                     'vision': True, 'max_output_tokens': 9000})
        model = registry.get_model('demo', 'demo-new')
        assert model.vision is True and model.max_output_tokens == 9000

    def test_saving_with_make_default_switches_the_default(self, catalogue):
        registry.save_model('demo', {'id': 'demo-new'}, make_default=True)
        assert registry.default_model('demo') == 'demo-new'
        assert read(catalogue)['ai_models']['demo']['default_model'] == 'demo-new'

    def test_saving_an_existing_id_updates_rather_than_duplicates(self, catalogue):
        registry.save_model('demo', {'id': 'demo-small', 'label': 'Renamed'})
        ids = [m['id'] for m in read(catalogue)['ai_models']['demo']['models']]
        assert ids.count('demo-small') == 1
        assert registry.get_model('demo', 'demo-small').label == 'Renamed'

    def test_re_adding_a_retired_id_clears_its_alias(self, catalogue):
        """Otherwise the model would be aliased away from itself."""
        registry.save_model('demo', {'id': 'demo-ancient', 'label': 'Back'})
        assert registry.resolve('demo', 'demo-ancient') == 'demo-ancient'

    def test_retiring_keeps_the_old_id_working(self, catalogue):
        registry.delete_model('demo', 'demo-small')
        assert registry.get_model('demo', 'demo-small') is None
        assert registry.resolve('demo', 'demo-small') == 'demo-large'

    def test_retiring_the_default_hands_over_to_a_fallback(self, catalogue):
        registry.delete_model('demo', 'demo-large')
        assert registry.default_model('demo') == 'demo-small'
        assert registry.resolve('demo', 'demo-large') == 'demo-small'

    def test_enabling_and_disabling_a_provider(self, catalogue):
        registry.set_provider_enabled('demo', False)
        assert registry.get_provider('demo').enabled is False
        registry.set_provider_enabled('demo', True)
        assert registry.get_provider('demo').enabled is True

    def test_app_settings_round_trip(self, catalogue):
        registry.set_app_setting('prompt_suggestion_provider', 'demo')
        assert registry.get_app_setting('prompt_suggestion_provider') == 'demo'
        assert '# A comment at the top that must survive every edit.' in \
            catalogue.read_text(encoding='utf-8')


class TestWriteGuards:
    """A bad edit must be refused before it reaches disk."""

    def test_an_invalid_id_is_refused(self, catalogue):
        before = catalogue.read_text(encoding='utf-8')
        with pytest.raises(registry.CatalogueError, match='not a valid model id'):
            registry.save_model('demo', {'id': 'has spaces'})
        assert catalogue.read_text(encoding='utf-8') == before

    def test_an_unknown_provider_is_refused(self, catalogue):
        with pytest.raises(registry.CatalogueError, match='no provider'):
            registry.save_model('nosuch', {'id': 'x'})

    def test_a_default_that_is_not_catalogued_is_refused(self, catalogue):
        with pytest.raises(registry.CatalogueError, match='not in'):
            registry.set_default_model('demo', 'never-existed')

    def test_removing_the_last_model_is_refused(self, catalogue):
        registry.delete_model('demo', 'demo-small')
        with pytest.raises(registry.CatalogueError, match='only model'):
            registry.delete_model('demo', 'demo-large')

    def test_removing_a_model_that_is_not_there_is_refused(self, catalogue):
        with pytest.raises(registry.CatalogueError, match='no model called'):
            registry.delete_model('demo', 'imaginary')

    @pytest.mark.skipif(
        hasattr(os, 'geteuid') and os.geteuid() == 0,
        reason='root ignores file permissions, so a read-only file is still '
               'writable here. The check itself is exercised below.')
    def test_a_read_only_file_gives_a_useful_message(self, catalogue):
        os.chmod(catalogue, 0o444)
        try:
            with pytest.raises(registry.CatalogueError, match='not writable'):
                registry.save_model('demo', {'id': 'demo-new'})
        finally:
            os.chmod(catalogue, 0o644)

    def test_a_missing_directory_is_reported_not_crashed(self, tmp_path, monkeypatch):
        """The message must say what to fix, not surface an OSError."""
        monkeypatch.setenv('SKILLPILOT_CONFIG',
                           str(tmp_path / 'nowhere' / 'config.yaml'))
        registry.reload_config()
        try:
            with pytest.raises(registry.CatalogueError):
                registry.save_model('openai', {'id': 'x'})
        finally:
            registry.reload_config()


class TestHotReload:
    def test_an_external_edit_is_picked_up(self, catalogue):
        assert registry.default_model('demo') == 'demo-large'

        # Simulate a text-editor change, or another worker saving.
        text = catalogue.read_text(encoding='utf-8').replace(
            'default_model: "demo-large"', 'default_model: "demo-small"')
        catalogue.write_text(text, encoding='utf-8')
        os.utime(catalogue, (0, 0))  # force a different mtime

        assert registry.default_model('demo') == 'demo-small'

    def test_an_environment_override_still_wins(self, catalogue, monkeypatch):
        monkeypatch.setenv('SKILLPILOT_MODEL_DEMO', 'demo-small')
        assert registry.default_model('demo') == 'demo-small'


class TestDispatch:
    def test_a_yaml_only_provider_gets_a_handler(self, catalogue):
        """The payoff: a new vendor needs no Python change."""
        from app.services.ai_service import AIService
        assert AIService()._handler_for('demo') is not None

    def test_a_disabled_provider_is_refused_with_an_explanation(self, catalogue):
        from app.services.ai_service import AIService
        registry.set_provider_enabled('demo', False)
        result = AIService().chat('demo', 'hi', 'key')
        assert 'error' in result and 'switched off' in result['error']

    def test_an_unknown_driver_is_refused_with_an_explanation(self, catalogue):
        from app.services.ai_service import AIService
        text = catalogue.read_text(encoding='utf-8').replace(
            'driver: openai_compatible', 'driver: telepathy')
        catalogue.write_text(text, encoding='utf-8')
        os.utime(catalogue, (0, 0))
        result = AIService().chat('demo', 'hi', 'key')
        assert 'error' in result and 'telepathy' in result['error']


class TestCapabilityInheritance:
    """A model added with only an id must still be callable.

    Sending `temperature` to a provider whose models reject it is a 400 on
    every request, so an omitted capability inherits from the provider's
    current default rather than falling back to a permissive guess.
    """

    def test_a_bare_save_inherits_the_request_shape(self, catalogue, tmp_path):
        # A provider whose default rejects temperature, as current reasoning
        # models do.
        catalogue.write_text(textwrap.dedent("""\
            ai_models:
              demo:
                label: "Demo"
                driver: openai_compatible
                base_url: "https://api.demo.example/v1"
                default_model: "demo-large"
                models:
                  - id: "demo-large"
                    label: "Demo Large"
                    vision: true
                    sampling: false
                    max_completion_tokens: true
                    max_output_tokens: 64000
            """), encoding='utf-8')
        registry.reload_config()
        assert registry.get_model('demo', 'demo-large').sampling is False

        registry.save_model('demo', {'id': 'demo-next'})
        added = registry.get_model('demo', 'demo-next')
        assert added.sampling is False
        assert added.max_completion_tokens is True
        assert added.vision is True
        assert added.max_output_tokens == 64000

    def test_an_explicit_capability_still_wins(self, catalogue):
        registry.save_model('demo', {'id': 'demo-next', 'vision': False,
                                     'max_output_tokens': 1234})
        added = registry.get_model('demo', 'demo-next')
        assert added.vision is False
        assert added.max_output_tokens == 1234
