"""Where an API key comes from, resolved in one place.

Every part of the platform that needs a provider's key calls
:func:`get_api_key`. It looks in three places, in this order:

1. **Environment variables**, loaded from ``.env`` at startup. Highest
   priority so a deployment can override anything without editing files that
   are shared or version-controlled.
2. **``config.yaml``**, under ``api_keys:``. This is where keys normally live
   on the server.
3. **The database**, ``api_credentials``, encrypted with Fernet. This is what
   Admin > AI Settings writes.

There used to be two separate lookups that disagreed: the admin screens
checked the environment and the database, while the chat route checked the
environment and ``config.yaml``. A key saved through the admin screen
therefore showed a green "Configured" badge while chat requests reported no
key at all, and a key in ``config.yaml`` did the reverse. One function now
serves both, so what the admin screen reports is what the platform will use.

Nothing here logs, returns or prints key material.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

#: Environment variables to check per provider, in priority order. Includes
#: the vendor's own standard name alongside the historical SkillPilot one, so
#: existing .env files keep working.
ENV_VARS: Dict[str, List[str]] = {
    'openai': ['OPENAI_API_KEY'],
    'claude': ['ANTHROPIC_API_KEY', 'CLAUDE_API_KEY'],
    'gemini': ['GEMINI_API_KEY', 'GOOGLE_API_KEY'],
    'grok': ['XAI_API_KEY', 'GROK_API_KEY'],
    'deepseek': ['DEEPSEEK_API_KEY'],
    'perplexity': ['PERPLEXITY_API_KEY'],
    'images': ['OPENAI_API_KEY'],
    'dalle': ['OPENAI_API_KEY'],
    'heygen': ['HEYGEN_API_KEY'],
    'dify': ['DIFY_API_KEY'],
    'census': ['CENSUS_API_KEY'],
    'bedrock': ['BEDROCK_API_KEY'],
    'paypal': ['PAYPAL_CLIENT_ID'],
}

#: Providers that share another provider's key in ``config.yaml``.
YAML_ALIASES = {'images': 'openai', 'dalle': 'openai', 'anthropic': 'claude'}


def _normalise(provider: str) -> str:
    return (provider or '').strip().lower()


def _from_environment(provider: str) -> Optional[str]:
    names = list(ENV_VARS.get(provider, []))

    # A provider defined only in config.yaml still has its env_vars listed
    # there, so a brand-new vendor works without editing this file.
    try:
        from app.services import model_registry as registry
        spec = registry.get_provider(provider)
        if spec is not None:
            names.extend(name for name in spec.env_vars if name not in names)
    except Exception:
        pass

    # And whatever the credential store records, for anything else.
    try:
        from app.models import ApiCredential
        recorded = (ApiCredential.PROVIDERS.get(provider) or {}).get('env_var')
        if recorded and recorded not in names:
            names.append(recorded)
    except Exception:
        pass

    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def _from_config_file(provider: str) -> Optional[str]:
    """The ``api_keys:`` block of config.yaml."""
    try:
        from config.config import reload_api_keys
        keys = reload_api_keys()
    except Exception:
        return None

    for candidate in (provider, YAML_ALIASES.get(provider, '')):
        if not candidate:
            continue
        value = keys.get(candidate)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _from_database(provider: str) -> Optional[str]:
    """The encrypted ``api_credentials`` table, written by Admin > AI Settings.

    Needs an application context and a working database, so a failure here is
    not an error — it just means this source has nothing to offer.
    """
    try:
        from app.models import ApiCredential
        from app.utils.encryption import decrypt_api_key

        lookup = YAML_ALIASES.get(provider, provider)
        credential = (ApiCredential.query
                      .filter_by(provider=lookup, is_active=True).first())
        if credential and credential.encrypted_key:
            return decrypt_api_key(credential.encrypted_key)
    except Exception:
        return None
    return None


def get_api_key(provider: str) -> Optional[str]:
    """The API key for ``provider``, or ``None`` if none is configured."""
    provider = _normalise(provider)
    if not provider:
        return None
    return (_from_environment(provider)
            or _from_config_file(provider)
            or _from_database(provider))


def get_api_key_source(provider: str) -> Optional[str]:
    """Which of the three sources supplied the key: for the admin screens.

    Returns ``'environment'``, ``'config.yaml'``, ``'database'`` or ``None``.
    Says where a key came from without revealing any of it — useful when a
    key is not the one someone expected and they need to know which file to
    edit.
    """
    provider = _normalise(provider)
    if not provider:
        return None
    if _from_environment(provider):
        return 'environment'
    if _from_config_file(provider):
        return 'config.yaml'
    if _from_database(provider):
        return 'database'
    return None


def get_all_configured_providers() -> List[str]:
    """Providers that have a usable key, from any source."""
    try:
        from app.services import model_registry as registry
        candidates = list(registry.list_providers())
    except Exception:
        candidates = []

    try:
        from app.models import ApiCredential
        candidates.extend(p for p in ApiCredential.PROVIDERS
                          if p not in candidates)
    except Exception:
        pass

    return [provider for provider in candidates if get_api_key(provider)]
