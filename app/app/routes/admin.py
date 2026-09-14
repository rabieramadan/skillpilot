from flask import Blueprint, request, jsonify, session
from functools import wraps
import json
from pathlib import Path

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


def load_models_config():
    config_path = get_models_config_path()
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    
    # Default configuration
    return {
        "prompt_suggestion_model": "openai",
        "models": {
            "openai": {
                "enabled": True,
                "versions": [
                    {"id": "gpt-4.1", "name": "GPT-4.1 (Latest)", "enabled": True, "max_tokens": 16000},
                    {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini", "enabled": True, "max_tokens": 8000},
                    {"id": "gpt-4o", "name": "GPT-4o", "enabled": True, "max_tokens": 4000},
                    {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "enabled": True, "max_tokens": 4000},
                    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "enabled": True, "max_tokens": 4000}
                ],
                "default_version": "gpt-4.1"
            },
            "claude": {
                "enabled": True,
                "versions": [
                    {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5 (Latest)", "enabled": True, "max_tokens": 8000},
                    {"id": "claude-opus-4-1-20250805", "name": "Claude Opus 4.1", "enabled": True, "max_tokens": 8000},
                    {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "enabled": True, "max_tokens": 4000},
                    {"id": "claude-haiku-4-5-20251015", "name": "Claude Haiku 4.5 (Fast)", "enabled": True, "max_tokens": 4000}
                ],
                "default_version": "claude-sonnet-4-5-20250929"
            },
            "gemini": {
                "enabled": True,
                "versions": [
                    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "enabled": True, "max_tokens": 8000},
                    {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "enabled": True, "max_tokens": 4000},
                    {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "enabled": True, "max_tokens": 8000}
                ],
                "default_version": "gemini-2.0-flash"
            },
            "dalle": {
                "enabled": True,
                "versions": [
                    {"id": "dall-e-3", "name": "DALL-E 3", "enabled": True},
                    {"id": "dall-e-2", "name": "DALL-E 2", "enabled": False}
                ],
                "default_version": "dall-e-3"
            },
            "perplexity": {
                "enabled": True,
                "versions": [
                    {"id": "sonar-pro", "name": "Sonar Pro (Advanced Search)", "enabled": True, "max_tokens": 4000},
                    {"id": "sonar", "name": "Sonar (Fast)", "enabled": True, "max_tokens": 4000},
                    {"id": "sonar-reasoning-pro", "name": "Sonar Reasoning Pro", "enabled": True, "max_tokens": 4000},
                    {"id": "sonar-reasoning", "name": "Sonar Reasoning", "enabled": True, "max_tokens": 4000}
                ],
                "default_version": "sonar-pro"
            },
            "grok": {
                "enabled": True,
                "versions": [
                    {"id": "grok-3", "name": "Grok 3", "enabled": True, "max_tokens": 8000},
                    {"id": "grok-3-mini", "name": "Grok 3 Mini", "enabled": True, "max_tokens": 4000}
                ],
                "default_version": "grok-3"
            },
            "deepseek": {
                "enabled": True,
                "versions": [
                    {"id": "deepseek-chat", "name": "DeepSeek Chat V3.2", "enabled": True, "max_tokens": 8000},
                    {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner (Advanced)", "enabled": True, "max_tokens": 64000}
                ],
                "default_version": "deepseek-chat"
            },
            "clarifai": {
                "enabled": True,
                "versions": [
                    {"id": "general-image-recognition", "name": "General Image Recognition", "enabled": True},
                    {"id": "food-recognition", "name": "Food Recognition", "enabled": True},
                    {"id": "nsfw-recognition", "name": "NSFW Detection", "enabled": True},
                    {"id": "celebrity-recognition", "name": "Celebrity Recognition", "enabled": True}
                ],
                "default_version": "general-image-recognition"
            },
            "llama": {
                "enabled": False,
                "versions": [
                    {"id": "llama-2-70b", "name": "Llama 2 70B", "enabled": False, "max_tokens": 4000}
                ],
                "default_version": "llama-2-70b"
            }
        }
    }


def save_models_config(config):
    config_path = get_models_config_path()
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


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
        'deepseek': 'deepseek'
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
