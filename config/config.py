"""Application configuration.

Values are resolved in this order, highest first:

1. Environment variables (loaded from ``.env``, falling back to ``.env.server``)
2. ``config.yaml``
3. The defaults in :class:`Config`

Only UPPERCASE attributes reach ``app.config`` — that is how Flask's
``from_object`` works — so every setting the application reads through
``current_app.config[...]`` must be declared here in uppercase.
"""

from __future__ import annotations

import os
import secrets
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
# .env is the normal file; .env.server exists for the Windows deployment.
if os.path.exists('.env'):
    load_dotenv('.env')
elif os.path.exists('.env.server'):
    load_dotenv('.env.server')
else:
    load_dotenv()

CONFIG_PATH = os.environ.get('SKILLPILOT_CONFIG', 'config.yaml')


def _load_yaml(path: str) -> Dict[str, Any]:
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return yaml.safe_load(handle) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as exc:
        print(f'[config] {path} is not valid YAML, ignoring it: {exc}')
        return {}


yaml_config: Dict[str, Any] = _load_yaml(CONFIG_PATH)
_api_keys: Dict[str, Any] = yaml_config.get('api_keys') or {}
_api_keys_path: str = CONFIG_PATH
try:
    _api_keys_mtime: float = os.path.getmtime(CONFIG_PATH)
except OSError:
    _api_keys_mtime = 0.0
_admin: Dict[str, Any] = yaml_config.get('admin') or {}
_app_settings: Dict[str, Any] = yaml_config.get('app') or {}
_files: Dict[str, Any] = yaml_config.get('files') or {}


def reload_api_keys() -> Dict[str, Any]:
    """The ``api_keys:`` block, re-read if config.yaml changed on disk.

    Keys live in config.yaml on the server, so editing that file must not
    require a restart — the model catalogue in the same file already behaves
    this way.
    """
    global _api_keys, _api_keys_mtime, _api_keys_path
    # Read the path per call rather than at import: tests point
    # SKILLPILOT_CONFIG at a temporary file after this module is loaded.
    path = os.environ.get('SKILLPILOT_CONFIG', 'config.yaml')
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return _api_keys if path == _api_keys_path else {}
    if mtime != _api_keys_mtime or path != _api_keys_path:
        block = _load_yaml(path).get('api_keys')
        _api_keys = block if isinstance(block, dict) else {}
        _api_keys_mtime = mtime
        _api_keys_path = path
    return _api_keys


def _key(*env_names: str, yaml_name: Optional[str] = None) -> Optional[str]:
    """First non-empty value across the given env vars, then config.yaml."""
    for name in env_names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    if yaml_name:
        value = reload_api_keys().get(yaml_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _is_production() -> bool:
    return (os.environ.get('FLASK_ENV') == 'production'
            or os.environ.get('REPLIT_DEPLOYMENT') == '1'
            or os.environ.get('SKP_FORCE_SECURE_COOKIES') == '1')


def _secret_key() -> str:
    """Session signing key.

    A random per-process key is generated when none is configured. That keeps
    development working, but it logs out every user on restart and breaks
    multi-worker deployments, so production is told loudly to set one.
    """
    configured = os.environ.get('SECRET_KEY') or os.environ.get('SESSION_SECRET')
    if configured and configured.strip():
        return configured.strip()
    if _is_production():
        print('[config] WARNING: SECRET_KEY is not set. Sessions will not '
              'survive a restart and will not work across multiple workers. '
              'Set SECRET_KEY in .env to a 64-character random string.')
    return secrets.token_hex(32)


class Config:
    # --- Core --------------------------------------------------------------
    SECRET_KEY = _secret_key()
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Application -------------------------------------------------------
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = int(
        os.environ.get('MAX_CONTENT_LENGTH')
        or int(_files.get('max_size_mb', 50)) * 1024 * 1024
    )
    ADMIN_SESSION_TIMEOUT = int(
        os.environ.get('ADMIN_SESSION_TIMEOUT') or _admin.get('session_timeout') or 3600 * 24
    )
    DEBUG = bool(_app_settings.get('debug', False)) and not _is_production()

    # Super-admin password checked by /api/auth/login. Declared here because
    # Flask only copies UPPERCASE attributes into app.config; without it the
    # login route raised KeyError on every attempt.
    ADMIN_PASSWORD = (
        os.environ.get('ADMIN_PASSWORD')
        or (_admin.get('password') if isinstance(_admin.get('password'), str) else None)
        or ''
    )

    # --- AI provider keys --------------------------------------------------
    # Accept both the vendor-standard variable and the historical SkillPilot
    # one so existing .env files keep working.
    OPENAI_API_KEY = _key('OPENAI_API_KEY', yaml_name='openai')
    CLAUDE_API_KEY = _key('ANTHROPIC_API_KEY', 'CLAUDE_API_KEY', yaml_name='claude')
    ANTHROPIC_API_KEY = CLAUDE_API_KEY
    GEMINI_API_KEY = _key('GEMINI_API_KEY', 'GOOGLE_API_KEY', yaml_name='gemini')
    PERPLEXITY_API_KEY = _key('PERPLEXITY_API_KEY', yaml_name='perplexity')
    GROK_API_KEY = _key('XAI_API_KEY', 'GROK_API_KEY', yaml_name='grok')
    DEEPSEEK_API_KEY = _key('DEEPSEEK_API_KEY', yaml_name='deepseek')
    DIFY_API_KEY = _key('DIFY_API_KEY', yaml_name='dify')
    HEYGEN_API_KEY = _key('HEYGEN_API_KEY', yaml_name='heygen')
    CENSUS_API_KEY = _key('CENSUS_API_KEY', yaml_name='census')
    BEDROCK_API_KEY = _key('BEDROCK_API_KEY', yaml_name='bedrock')

    # --- Raw config.yaml ---------------------------------------------------
    # Exposed so services can read blocks such as `models:` and
    # `prompt_engineering:` without re-reading the file.
    YAML_CONFIG = yaml_config


# Any UPPERCASE top-level key in config.yaml that Config does not already
# define is copied across, so a deployment can add settings without a code
# change. Lowercase blocks (api_keys, models, files, ...) are deliberately
# skipped: they are structured data, not Flask settings.
for _name, _value in yaml_config.items():
    if _name.isupper() and not hasattr(Config, _name):
        setattr(Config, _name, _value)
