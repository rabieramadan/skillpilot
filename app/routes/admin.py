from flask import Blueprint, request, jsonify, session
from functools import wraps

from app.services import model_registry as registry

admin_bp = Blueprint('admin', __name__)

# Session-based admin authentication
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def _provider_view(key, spec):
    """One provider in the shape the chat UI's model picker expects.

    The picker predates the catalogue and reads `versions` / `default_version`.
    Rather than rewrite it, the catalogue is projected into that shape here.
    """
    from app.utils.api_key_helper import get_api_key
    try:
        has_key = bool(get_api_key(key))
    except Exception:
        has_key = False

    versions = [{
        'id': model['id'],
        'name': model['label'],
        'summary': model['summary'],
        'enabled': True,
        'max_tokens': model['max_output_tokens'],
        'vision': model['vision'],
    } for model in registry.available_models(key)]

    return {
        'enabled': spec.enabled,
        'label': spec.label,
        'versions': versions,
        'default_version': registry.default_model(key),
        'has_api_key': has_key,
        'api_key_missing': not has_key,
    }


@admin_bp.route('/models', methods=['GET'])
def get_models():
    """The model catalogue, for the chat UI's picker.

    Read-only and unauthenticated on purpose: every signed-in user needs it to
    populate the model menu. Editing goes through /api/ai-models, which
    requires an admin session.
    """
    providers = {}
    for key in registry.list_providers():
        spec = registry.get_provider(key)
        if spec is None or key in ('images', 'bedrock'):
            continue
        providers[key] = _provider_view(key, spec)

    return jsonify({
        'models': providers,
        'prompt_suggestion_model': registry.get_app_setting(
            'prompt_suggestion_provider', 'openai'),
        'source': 'config.yaml',
    })


@admin_bp.route('/models', methods=['PUT'])
@admin_required
def update_models():
    """Removed: the catalogue is no longer a JSON blob to overwrite."""
    return jsonify({
        'error': 'Models are now defined in the ai_models block of config.yaml. '
                 'Use the AI Models screen, or the /api/ai-models endpoints, '
                 'which validate and test changes before saving.'
    }), 410


@admin_bp.route('/models/<provider>/toggle', methods=['POST'])
@admin_required
def toggle_model_provider(provider):
    """Switch a whole provider on or off."""
    spec = registry.get_provider(provider)
    if spec is None:
        return jsonify({'error': 'Provider not found'}), 404
    try:
        registry.set_provider_enabled(provider, not spec.enabled)
    except registry.CatalogueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'success': True,
                    'enabled': registry.get_provider(provider).enabled})


@admin_bp.route('/models/<provider>/version/<version_id>/toggle', methods=['POST'])
@admin_required
def toggle_model_version(provider, version_id):
    """Removed: a model is either in the catalogue or retired from it."""
    return jsonify({
        'error': 'Models are no longer individually enabled. Retire a model '
                 'from the AI Models screen instead — it is removed from the '
                 'menus but anything still requesting it keeps working.'
    }), 410


@admin_bp.route('/models/<provider>/default-version', methods=['POST'])
@admin_required
def set_default_version(provider):
    """Point a provider's default at one of its catalogued models."""
    data = request.get_json(silent=True) or {}
    version_id = str(data.get('version_id') or '').strip()
    try:
        registry.set_default_model(provider, version_id)
    except registry.CatalogueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'success': True, 'default_version': version_id})


@admin_bp.route('/prompt-suggestion-model', methods=['POST'])
@admin_required
def set_prompt_suggestion_model():
    """Choose which provider writes prompt suggestions."""
    data = request.get_json(silent=True) or {}
    provider = str(data.get('model') or '').strip()
    if registry.get_provider(provider) is None:
        return jsonify({'error': f'There is no provider called "{provider}".'}), 400
    try:
        registry.set_app_setting('prompt_suggestion_provider', provider)
    except registry.CatalogueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'success': True, 'model': provider})
