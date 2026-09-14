"""Tests for the central model catalogue.

These guard the properties the rest of the platform depends on: that a model
identifier saved months ago still resolves to something callable, that a
retirement degrades instead of 404ing, and that nothing unpriced is silently
reported as free.
"""

import pytest

from app.services import model_registry as registry


class TestDefaults:
    def test_every_provider_has_a_default_in_its_own_catalogue(self):
        for key in registry.list_providers():
            default = registry.default_model(key)
            assert default, f'{key} has no default model'
            assert default in registry.get_provider(key).model_ids(), (
                f'{key} defaults to {default}, which is not in its catalogue'
            )

    def test_no_default_points_at_a_legacy_model(self):
        for key in registry.list_providers():
            entry = registry.get_model(key, registry.default_model(key))
            assert entry is not None and not entry.legacy

    def test_environment_variable_overrides_the_default(self, monkeypatch):
        monkeypatch.setenv('SKILLPILOT_MODEL_OPENAI', 'gpt-6-astra')
        assert registry.default_model('openai') == 'gpt-6-astra'

    def test_a_retired_override_is_mapped_forward(self, monkeypatch):
        """An old config.yaml or .env must not take the site down."""
        monkeypatch.setenv('SKILLPILOT_MODEL_OPENAI', 'gpt-4o')
        assert registry.default_model('openai') == 'gpt-5.6-terra'

    def test_unknown_provider_is_reported_not_guessed(self):
        assert registry.get_provider('nope') is None
        assert registry.default_model('nope') is None


class TestAliases:
    @pytest.mark.parametrize('provider,retired', [
        ('openai', 'gpt-3.5-turbo'),
        ('openai', 'gpt-4o'),
        ('openai', 'o3-mini'),
        ('claude', 'claude-3-5-sonnet-20241022'),
        ('claude', 'claude-sonnet-4-5-20250929'),
        ('gemini', 'gemini-1.5-pro'),
        ('gemini', 'gemini-2.5-flash'),
        ('grok', 'grok-3-mini'),
        ('deepseek', 'deepseek-chat'),
        ('images', 'dall-e-3'),
    ])
    def test_retired_identifiers_resolve_to_a_live_model(self, provider, retired):
        resolved = registry.resolve(provider, retired)
        assert resolved in registry.get_provider(provider).model_ids()

    def test_every_alias_target_exists(self):
        """An alias pointing at a model that is not in the catalogue would
        send the request straight back to a 404."""
        for key, spec in registry.PROVIDERS.items():
            available = set(spec.model_ids())
            for old, new in spec.aliases.items():
                assert new in available, f'{key}: {old} -> {new} is not catalogued'

    def test_no_alias_shadows_a_live_model(self):
        for key, spec in registry.PROVIDERS.items():
            live = set(spec.model_ids())
            overlap = live & set(spec.aliases)
            assert not overlap, f'{key}: {overlap} are both live and aliased'

    def test_an_unknown_identifier_passes_through_untouched(self):
        """A model released after this catalogue was written must still work
        when an administrator types it in."""
        assert registry.resolve('openai', 'gpt-9-nova') == 'gpt-9-nova'

    def test_empty_request_falls_back_to_the_default(self):
        assert registry.resolve('claude', None) == registry.default_model('claude')
        assert registry.resolve('claude', '  ') == registry.default_model('claude')


class TestFallbackChain:
    def test_chain_starts_with_the_requested_model(self):
        chain = registry.fallback_chain('openai', 'gpt-6-astra')
        assert chain[0] == 'gpt-6-astra'

    def test_chain_has_no_duplicates(self):
        for key in registry.list_providers():
            chain = registry.fallback_chain(key, registry.default_model(key))
            assert len(chain) == len(set(chain))

    def test_every_fallback_is_catalogued(self):
        for key, spec in registry.PROVIDERS.items():
            available = set(spec.model_ids())
            for candidate in spec.fallbacks:
                assert candidate in available, f'{key}: fallback {candidate} missing'


class TestUnavailableDetection:
    @pytest.mark.parametrize('message', [
        'The model `gpt-4o` does not exist',
        'model_not_found',
        'Invalid model: foo',
        'This model has been deprecated',
        'You do not have access to model claude-opus-5',
    ])
    def test_model_errors_are_recognised(self, message):
        assert registry.is_model_unavailable_error(message)

    @pytest.mark.parametrize('message', [
        'Rate limit exceeded',
        'Internal server error',
        'Request timed out',
        'Incorrect API key provided',
    ])
    def test_other_errors_are_not_treated_as_model_errors(self, message):
        """Misreading these as a retirement would burn the whole fallback
        chain on what is really a transient failure or a bad key."""
        assert not registry.is_model_unavailable_error(message)


class TestProviderRouting:
    @pytest.mark.parametrize('model,expected', [
        ('gpt-5.6-terra', 'openai'),
        ('gpt-4o', 'openai'),
        ('claude-sonnet-5', 'claude'),
        ('claude-3-opus', 'claude'),
        ('gemini-3.8-flash', 'gemini'),
        ('grok-4.6', 'grok'),
        ('deepseek-v4-flash', 'deepseek'),
        ('sonar-pro', 'perplexity'),
        ('dall-e-3', 'images'),
        ('gpt-image-2', 'images'),
        ('anthropic.claude-opus-5', 'bedrock'),
    ])
    def test_known_and_retired_identifiers_route_correctly(self, model, expected):
        assert registry.provider_for_model(model) == expected

    def test_future_identifiers_route_by_vendor_prefix(self):
        assert registry.provider_for_model('gemini-9.9-flash') == 'gemini'
        assert registry.provider_for_model('claude-opus-9') == 'claude'

    def test_bedrock_prefix_wins_over_the_bare_claude_prefix(self):
        assert registry.provider_for_model('anthropic.claude-sonnet-9') == 'bedrock'


class TestPricing:
    def test_priced_models_return_positive_rates(self):
        rates = registry.price_per_1k('claude', 'claude-opus-5')
        assert rates['input'] > 0 and rates['output'] > rates['input']

    def test_retired_identifiers_are_priced_via_their_replacement(self):
        """A session logged against gpt-4o must still be costed."""
        assert registry.price_per_1k('openai', 'gpt-4o') == \
            registry.price_per_1k('openai', 'gpt-5.6-terra')

    def test_unpriced_models_return_none_rather_than_zero(self):
        assert registry.price_per_1k('openai', 'gpt-9-nova') is None

    def test_every_priced_identifier_is_catalogued(self):
        catalogued = {m for spec in registry.PROVIDERS.values() for m in spec.model_ids()}
        for model in registry.PRICE_PER_MILLION:
            assert model in catalogued, f'{model} is priced but not catalogued'


class TestDescribe:
    def test_describe_never_leaks_a_key(self):
        described = registry.describe()
        rendered = repr(described)
        assert 'sk-' not in rendered and 'AIza' not in rendered

    def test_describe_covers_every_provider(self):
        assert set(registry.describe()) == set(registry.list_providers())

    def test_legacy_models_are_hidden_by_default(self):
        offered = {m['id'] for m in registry.available_models('openai')}
        assert 'gpt-5.2' not in offered
        with_legacy = {m['id'] for m in
                       registry.available_models('openai', include_legacy=True)}
        assert 'gpt-5.2' in with_legacy
