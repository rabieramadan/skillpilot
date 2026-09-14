from flask import Blueprint, request, jsonify, session
from functools import wraps
import json
from pathlib import Path

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


def get_models_config_path():
    return Path(__file__).parent.parent.parent / 'models_config.json'


def default_models_config():
    """Model picker contents, derived from the central registry.

    This used to be a hand-written literal listing gpt-4o, dall-e-3,
    deepseek-chat and other identifiers that no longer resolve. Deriving it
    means the admin screen can only ever offer models the platform can
    actually call.
    """
    providers = {}
    for key in registry.list_providers():
        # 'images' is presented under its historical name so that saved
        # selections and the frontend keep matching.
        display_key = 'dalle' if key == 'images' else key
        versions = []
        for model in registry.available_models(key):
            versions.append({
                'id': model['id'],
                'name': model['label'],
                'summary': model['summary'],
                'enabled': True,
                'max_tokens': model['max_output_tokens'],
            })
        providers[display_key] = {
            'enabled': True,
            'versions': versions,
            'default_version': registry.default_model(key),
        }

    # Providers that are not model catalogues but still appear in the picker.
    providers['heygen'] = {
        'enabled': True,
        'versions': [{'id': 'heygen-avatar-v2', 'name': 'HeyGen Avatar Video',
                      'summary': 'Generates an AI presenter video from a script.',
                      'enabled': True, 'max_tokens': 1500}],
        'default_version': 'heygen-avatar-v2',
    }
    providers['dify'] = {
        'enabled': False,
        'versions': [{'id': 'dify-app', 'name': 'Dify Application',
                      'summary': 'Routes to a Dify app you have configured.',
                      'enabled': True, 'max_tokens': 4000}],
        'default_version': 'dify-app',
    }

    return {'prompt_suggestion_model': 'openai', 'models': providers}


def _migrate_saved_config(config):
    """Map identifiers saved by an earlier release onto current ones.

    An administrator who pinned ``gpt-4o`` a year ago should not have the
    picker stuck on a model the API no longer serves. Retired identifiers are
    translated through the registry aliases and duplicates are dropped.
    """
    changed = False
    for display_key, provider in (config.get('models') or {}).items():
        registry_key = 'images' if display_key == 'dalle' else display_key
        if registry.get_provider(registry_key) is None:
            continue

        seen = set()
        migrated = []
        for version in provider.get('versions') or []:
            current = registry.resolve(registry_key, version.get('id'))
            if not current or current in seen:
                changed = True
                continue
            seen.add(current)
            if current != version.get('id'):
                changed = True
                entry = registry.get_model(registry_key, current)
                version['id'] = current
                if entry is not None:
                    version['name'] = entry.label
                    version['summary'] = entry.summary
                    version['max_tokens'] = entry.max_output_tokens
            migrated.append(version)

        # Offer anything new in the catalogue that the saved file predates.
        for model in registry.available_models(registry_key):
            if model['id'] not in seen:
                migrated.append({
                    'id': model['id'],
                    'name': model['label'],
                    'summary': model['summary'],
                    'enabled': True,
                    'max_tokens': model['max_output_tokens'],
                })
                changed = True

        provider['versions'] = migrated
        default = registry.resolve(registry_key, provider.get('default_version'))
        if default != provider.get('default_version'):
            provider['default_version'] = default
            changed = True

    return config, changed


def load_models_config():
    """Saved model configuration, migrated to current identifiers."""
    config_path = get_models_config_path()
    if not config_path.exists():
        return default_models_config()

    try:
        with open(config_path, 'r', encoding='utf-8') as handle:
            config = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f'[admin] {config_path} is unreadable ({exc}); using defaults.')
        return default_models_config()

    config, changed = _migrate_saved_config(config)
    if changed:
        try:
            save_models_config(config)
        except OSError as exc:
            print(f'[admin] could not write migrated {config_path}: {exc}')
    return config


def save_models_config(config):
    config_path = get_models_config_path()
    with open(config_path, 'w', encoding='utf-8') as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)


@admin_bp.route('/models', methods=['GET'])
def get_models():
    """Get all models configuration with API key status"""
    from app.utils.api_key_helper import get_api_key
    
    config = load_models_config()
    
    # Map provider names in config to API key provider IDs
    provider_key_map = {
        'openai': 'openai',
        'claude': 'claude',
        'gemini': 'gemini',
        'perplexity': 'perplexity',
        'grok': 'grok',
        'deepseek': 'deepseek',
        'heygen': 'heygen'
    }
    
    # Mark providers as inactive if no API key is configured
    for provider_name, config_data in config.get('models', {}).items():
        api_provider = provider_key_map.get(provider_name.lower())
        if api_provider:
            has_key = bool(get_api_key(api_provider))
            config_data['has_api_key'] = has_key
            # If no API key, mark as not available for chat
            if not has_key:
                config_data['api_key_missing'] = True
        else:
            config_data['has_api_key'] = False
            config_data['api_key_missing'] = True
    
    return jsonify(config)


@admin_bp.route('/models', methods=['PUT'])
@admin_required
def update_models():
    """Update models configuration"""
    try:
        new_config = request.get_json()
        save_models_config(new_config)
        return jsonify({'success': True, 'config': new_config})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/models/<provider>/toggle', methods=['POST'])
@admin_required
def toggle_model_provider(provider):
    """Enable/disable a model provider"""
    try:
        config = load_models_config()
        if provider in config['models']:
            config['models'][provider]['enabled'] = not config['models'][provider]['enabled']
            save_models_config(config)
            return jsonify({'success': True, 'enabled': config['models'][provider]['enabled']})
        return jsonify({'error': 'Provider not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/models/<provider>/version/<version_id>/toggle', methods=['POST'])
@admin_required
def toggle_model_version(provider, version_id):
    """Enable/disable a specific model version"""
    try:
        config = load_models_config()
        if provider in config['models']:
            for version in config['models'][provider]['versions']:
                if version['id'] == version_id:
                    version['enabled'] = not version['enabled']
                    save_models_config(config)
                    return jsonify({'success': True, 'enabled': version['enabled']})
        return jsonify({'error': 'Version not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/models/<provider>/default-version', methods=['POST'])
@admin_required
def set_default_version(provider):
    """Set default version for a provider"""
    try:
        data = request.get_json()
        version_id = data.get('version_id')
        
        config = load_models_config()
        if provider in config['models']:
            config['models'][provider]['default_version'] = version_id
            save_models_config(config)
            return jsonify({'success': True, 'default_version': version_id})
        return jsonify({'error': 'Provider not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/prompt-suggestion-model', methods=['POST'])
@admin_required
def set_prompt_suggestion_model():
    """Set the AI model to use for prompt suggestions"""
    try:
        data = request.get_json()
        model = data.get('model')
        
        config = load_models_config()
        if model in config['models']:
            config['prompt_suggestion_model'] = model
            save_models_config(config)
            return jsonify({'success': True, 'model': model})
        return jsonify({'error': 'Invalid model'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
