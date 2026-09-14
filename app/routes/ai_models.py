"""Admin API for the AI model catalogue.

Lets an administrator keep up with providers changing their model line-ups
without anyone touching the code or restarting the server. The catalogue
lives in the ``ai_models:`` block of config.yaml; these endpoints read it,
test candidate models against the live provider API, and write back.

The intended flow, which the admin screen follows:

1. **Discover** — ask the provider which models the configured key can
   actually reach. No guessing from a changelog.
2. **Test** — send one short prompt to a candidate model and report what came
   back: the answer, the latency, the tokens, or the exact provider error.
3. **Save** — only once a test has passed, and only after the administrator
   confirms. Optionally make it the provider's default in the same step.

Every endpoint requires an admin or super-admin session. Nothing here ever
returns an API key or any part of one.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

from app.services import ai_transport, model_registry as registry
from app.services.ai_transport import AIError
from app.utils.decorators import admin_required

ai_models_bp = Blueprint('ai_models', __name__, url_prefix='/api/ai-models')

#: Sent when a model is tested. Short, cheap, and the answer is trivially
#: checkable by eye, so an administrator can see the model really replied
#: rather than trusting a green tick.
TEST_PROMPT = 'Reply with exactly these two words: model ready'
TEST_TIMEOUT = 60


def _api_key(provider: str) -> Optional[str]:
    """The key for ``provider``, from the environment or the key store."""
    from app.utils.api_key_helper import get_api_key
    try:
        key = get_api_key(provider)
    except Exception:
        key = None
    if key:
        return key

    # Fall back to whatever env var the catalogue says this provider uses, so
    # a provider added to config.yaml works before it is known to the key
    # store.
    import os
    spec = registry.get_provider(provider)
    for name in (spec.env_vars if spec else []):
        value = os.environ.get(name)
        if value:
            return value
    return None


def _catalogue_payload(include_legacy: bool = True) -> Dict[str, Any]:
    providers = registry.describe(include_legacy=include_legacy)
    for key, details in providers.items():
        details['configured'] = bool(_api_key(key))
        details.pop('env_vars', None)
    return {
        'providers': providers,
        'registry': registry.catalogue_status(),
        'drivers': list(registry.KNOWN_DRIVERS),
    }


def _bad_request(message: str, status: int = 400):
    return jsonify({'success': False, 'error': message}), status


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

@ai_models_bp.route('', methods=['GET'])
@ai_models_bp.route('/', methods=['GET'])
@admin_required
def get_catalogue():
    """The full catalogue, with which providers have a usable key."""
    return jsonify({'success': True, **_catalogue_payload()})


@ai_models_bp.route('/reload', methods=['POST'])
@admin_required
def reload_catalogue():
    """Re-read config.yaml, for when it was edited outside the app."""
    registry.reload_config()
    return jsonify({'success': True, **_catalogue_payload()})


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

@ai_models_bp.route('/discover', methods=['POST'])
@admin_required
def discover_models():
    """Ask a provider which models its key can actually reach.

    Uses the provider's own model-listing endpoint, which costs nothing. The
    result is what to trust when a vendor's announcement and its API disagree
    — which is usually the case for a few days around a launch.
    """
    data = request.get_json(silent=True) or {}
    provider = str(data.get('provider') or '').strip()

    spec = registry.get_provider(provider)
    if spec is None:
        return _bad_request(f'There is no provider called "{provider}".', 404)
    if not spec.discovery_url:
        return _bad_request(
            f'{spec.label} has no discovery_url in config.yaml, so its model '
            'list cannot be fetched. Add the model by hand instead.')

    api_key = _api_key(spec.key)
    if not api_key:
        return _bad_request(f'No API key is configured for {spec.label}.')

    headers = {'Accept': 'application/json'}
    if spec.driver == 'anthropic':
        headers.update({'x-api-key': api_key,
                        'anthropic-version': ai_transport.ANTHROPIC_API_VERSION})
    elif spec.driver == 'gemini':
        headers['x-goog-api-key'] = api_key
    else:
        headers['Authorization'] = f'Bearer {api_key}'

    url = spec.discovery_url
    if spec.driver == 'gemini':
        url = f'{url}?pageSize=200'

    # Through the shared session, so discovery reuses connections with the
    # rest of the platform's outbound calls.
    import requests
    try:
        response = ai_transport._http().get(url, headers=headers, timeout=30)
    except requests.RequestException as exc:
        return _bad_request(f'Could not reach {spec.label}: {str(exc)[:200]}', 502)

    if response.status_code in (401, 403):
        return _bad_request(f'{spec.label} rejected the API key.', 502)
    if response.status_code != 200:
        return _bad_request(
            f'{spec.label} returned HTTP {response.status_code} from its model '
            'list.', 502)

    try:
        body = response.json()
    except ValueError:
        return _bad_request(f'{spec.label} returned a malformed model list.', 502)

    known = set(spec.model_ids())
    aliased = set(spec.aliases)
    discovered = []
    for identifier in _extract_model_ids(body, spec.driver):
        discovered.append({
            'id': identifier,
            'in_catalogue': identifier in known,
            'retired_here': identifier in aliased,
        })
    discovered.sort(key=lambda entry: (entry['in_catalogue'], entry['id']))

    missing = [m for m in known
               if m not in {d['id'] for d in discovered}]

    return jsonify({
        'success': True,
        'provider': spec.key,
        'models': discovered,
        # Models this catalogue offers that the provider did not list. Usually
        # means the vendor retired one and the catalogue has not caught up.
        'not_listed_by_provider': sorted(missing),
    })


def _extract_model_ids(body: Any, driver: str) -> list:
    """Pull model identifiers out of whichever list shape came back."""
    identifiers = []
    if driver == 'gemini':
        for entry in (body.get('models') or []):
            methods = entry.get('supportedGenerationMethods') or []
            if methods and 'generateContent' not in methods:
                continue
            name = str(entry.get('name') or '')
            identifiers.append(name.split('/')[-1] if '/' in name else name)
    else:
        # OpenAI and Anthropic both return {"data": [{"id": ...}]}.
        for entry in (body.get('data') or body.get('models') or []):
            if isinstance(entry, dict):
                identifiers.append(str(entry.get('id') or entry.get('name') or ''))
            elif isinstance(entry, str):
                identifiers.append(entry)
    return [i for i in identifiers if i]


# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

@ai_models_bp.route('/test', methods=['POST'])
@admin_required
def test_model():
    """Send one short prompt to a model and report exactly what happened.

    This is a real billed request, but a trivially small one. It is the only
    way to know a model identifier works for *this* account: a model can be
    announced, documented and listed, and still be unavailable on a given
    plan or in a given region.
    """
    data = request.get_json(silent=True) or {}
    provider = str(data.get('provider') or '').strip()
    model_id = str(data.get('model_id') or '').strip()
    prompt = str(data.get('prompt') or TEST_PROMPT).strip()[:2000]

    spec = registry.get_provider(provider)
    if spec is None:
        return _bad_request(f'There is no provider called "{provider}".', 404)
    if not model_id:
        return _bad_request('Which model should be tested?')
    if not spec.supported:
        return _bad_request(
            f'{spec.label} uses driver "{spec.driver}", which this version '
            'cannot call. Valid drivers: '
            f'{", ".join(registry.KNOWN_DRIVERS)}.')

    api_key = _api_key(spec.key)
    if not api_key:
        return _bad_request(f'No API key is configured for {spec.label}.')

    # A model being tested is usually not in the catalogue yet, so describe
    # it from what the caller says it supports. Anything unstated falls back
    # to the safest assumption.
    hints = data.get('capabilities') or {}
    started = time.monotonic()

    try:
        result = _run_test(spec, model_id, prompt, api_key, hints)
    except AIError as exc:
        return jsonify({
            'success': False,
            'provider': spec.key,
            'model_id': model_id,
            'error': exc.message,
            'status': exc.status,
            'hint': _diagnose(exc, spec, model_id),
            'elapsed_ms': int((time.monotonic() - started) * 1000),
        })
    except Exception as exc:  # noqa: BLE001 - never 500 an admin screen
        return jsonify({
            'success': False, 'provider': spec.key, 'model_id': model_id,
            'error': f'Unexpected error: {exc}',
            'elapsed_ms': int((time.monotonic() - started) * 1000),
        })

    elapsed = int((time.monotonic() - started) * 1000)
    answered_as = result.model or model_id
    # A fallback means the requested id did NOT work; another model answered.
    if result.fallback_from and answered_as != model_id:
        return jsonify({
            'success': False,
            'provider': spec.key,
            'model_id': model_id,
            'error': f'"{model_id}" was rejected, so {answered_as} answered '
                     'instead. The identifier is wrong, retired, or not '
                     'enabled for this account.',
            'hint': 'Use Discover to see the identifiers this key can reach.',
            'elapsed_ms': elapsed,
        })

    return jsonify({
        'success': True,
        'provider': spec.key,
        'model_id': model_id,
        'answered_as': answered_as,
        'reply': result.text[:600],
        'usage': result.usage,
        'elapsed_ms': elapsed,
        'in_catalogue': registry.get_model(spec.key, model_id) is not None,
    })


def _run_test(spec, model_id: str, prompt: str, api_key: str, hints: Dict[str, Any]):
    """One test call, routed by the provider's driver."""
    common = dict(api_key=api_key, user_text=prompt,
                  system='You follow instructions exactly and briefly.',
                  model=model_id, max_tokens=256, timeout=TEST_TIMEOUT)

    if spec.driver == 'anthropic':
        return ai_transport.chat_anthropic(**common)
    if spec.driver == 'gemini':
        return ai_transport.chat_gemini(**common)
    if spec.driver == 'openai_compatible':
        return ai_transport.chat_openai_compatible(spec.key, **common)
    if spec.driver == 'openai_images':
        generated = ai_transport.generate_image(
            api_key=api_key, prompt='A plain grey square.', model=model_id,
            timeout=TEST_TIMEOUT)
        return ai_transport.ChatResult(
            text=f'Image generated ({len(generated["image_bytes"])} bytes).',
            provider=spec.key, model=generated['model'],
            fallback_from=generated.get('fallback_from'))
    if spec.driver == 'bedrock':
        from app.services.ai_service import AIService
        response = AIService()._chat_bedrock(prompt, api_key, version=model_id)
        if 'error' in response:
            raise AIError(response['error'], provider=spec.key)
        return ai_transport.ChatResult(
            text=response.get('text', ''), provider=spec.key,
            model=response.get('model_id') or model_id,
            usage=response.get('usage') or {})
    raise AIError(f'No test path for driver "{spec.driver}".', provider=spec.key)


def _diagnose(exc: AIError, spec, model_id: str) -> str:
    """A sentence telling the admin what to do about this failure."""
    if registry.is_model_unavailable_error(exc.message):
        return (f'{spec.label} does not recognise "{model_id}". Check the '
                'spelling against the provider\'s documentation, or use '
                'Discover to list what this key can reach.')
    if exc.status in (401, 403):
        return (f'The {spec.label} API key is wrong, expired, or not entitled '
                'to this model. Check it under AI Settings.')
    if exc.status == 429:
        return ('Rate limited. The key works; try again shortly, or check the '
                'account has quota left.')
    if exc.status and exc.status >= 500:
        return f'{spec.label} is having problems. This is not your config.'
    if exc.retryable:
        return 'A network or timeout problem, not a configuration one.'
    return ''


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

@ai_models_bp.route('/save', methods=['POST'])
@admin_required
def save_model():
    """Add or update a model in config.yaml.

    The admin screen calls this only after a passing test and an explicit
    confirmation, but the guard is here too: ``confirmed`` must be true.
    """
    data = request.get_json(silent=True) or {}
    provider = str(data.get('provider') or '').strip()
    model = data.get('model') or {}
    make_default = bool(data.get('make_default'))

    if not data.get('confirmed'):
        return _bad_request('Saving must be confirmed.')
    if not isinstance(model, dict):
        return _bad_request('The model definition must be an object.')

    try:
        saved = registry.save_model(provider, model, make_default=make_default)
    except registry.CatalogueError as exc:
        return _bad_request(str(exc))

    return jsonify({
        'success': True,
        'saved': saved,
        'made_default': make_default,
        'message': (f'{saved["label"]} saved'
                    + (' and set as the default.' if make_default else '.')),
        **_catalogue_payload(),
    })


@ai_models_bp.route('/default', methods=['POST'])
@admin_required
def set_default():
    """Point a provider's default, or vision default, at a catalogued model."""
    data = request.get_json(silent=True) or {}
    provider = str(data.get('provider') or '').strip()
    model_id = str(data.get('model_id') or '').strip()
    vision = bool(data.get('vision'))

    try:
        registry.set_default_model(provider, model_id, vision=vision)
    except registry.CatalogueError as exc:
        return _bad_request(str(exc))

    which = 'vision default' if vision else 'default'
    return jsonify({
        'success': True,
        'message': f'{model_id} is now the {which} for {provider}.',
        **_catalogue_payload(),
    })


@ai_models_bp.route('/<provider>/<path:model_id>', methods=['DELETE'])
@admin_required
def remove_model(provider: str, model_id: str):
    """Retire a model.

    By default it becomes an alias of the provider's current default, so
    anything that already stored the old identifier keeps working. Pass
    ``?hard=1`` only for an entry added by mistake.
    """
    alias_to = request.args.get('alias_to') or None
    try:
        registry.delete_model(provider, model_id, alias_to=alias_to)
    except registry.CatalogueError as exc:
        return _bad_request(str(exc))

    return jsonify({
        'success': True,
        'message': f'{model_id} retired. Anything still requesting it will be '
                   'served by the replacement.',
        **_catalogue_payload(),
    })


@ai_models_bp.route('/<provider>/enabled', methods=['POST'])
@admin_required
def set_enabled(provider: str):
    """Switch a whole provider on or off."""
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get('enabled'))
    try:
        registry.set_provider_enabled(provider, enabled)
    except registry.CatalogueError as exc:
        return _bad_request(str(exc))

    return jsonify({
        'success': True,
        'message': f'{provider} is now {"enabled" if enabled else "disabled"}.',
        **_catalogue_payload(),
    })
