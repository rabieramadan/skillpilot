"""The model catalogue: loaded from config.yaml, editable at runtime.

Every provider and model the platform can call is defined in the
``ai_models:`` block of ``config.yaml``. No Python file names a model. When a
vendor ships a new model or retires an old one, the fix is a config edit —
by hand, or through Admin > AI Models, which tests the model against the live
API before writing it here.

Three properties the rest of the platform relies on:

* **Aliasing** — a retired identifier stored in the database or picked from a
  stale menu is mapped to its replacement instead of failing.
* **Fallbacks** — when a provider rejects a model outright, the next one in
  the chain is tried, so a retirement degrades instead of breaking.
* **Capabilities** — request building asks the catalogue what a model accepts
  (``temperature``, ``max_tokens`` vs ``max_completion_tokens``, images)
  rather than pattern-matching its name.

The file is re-read when its timestamp changes, so an edit — from another
worker process, or from a text editor — is picked up without a restart.

Precedence for a provider's default model, highest first:

1. ``SKILLPILOT_MODEL_<PROVIDER>`` environment variable
2. ``ai_models.<provider>.default_model`` in config.yaml
3. the built-in bootstrap entry, used only when config.yaml is unusable
"""

from __future__ import annotations

import copy
import os
import re
import tempfile
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

__all__ = [
    'CatalogueError',
    'Model',
    'Provider',
    'available_models',
    'catalogue_status',
    'default_model',
    'delete_model',
    'describe',
    'discovery_url',
    'get_app_setting',
    'set_app_setting',
    'fallback_chain',
    'get_model',
    'get_provider',
    'is_model_unavailable_error',
    'list_providers',
    'price_per_1k',
    'provider_for_model',
    'reload_config',
    'resolve',
    'save_model',
    'set_default_model',
    'set_provider_enabled',
]


class CatalogueError(Exception):
    """A catalogue edit was rejected. The message is safe to show an admin."""


#: Drivers this build knows how to speak. A provider in config.yaml naming
#: anything else is loaded but reported as unusable, rather than silently
#: dropped — an admin who mistypes should see why.
KNOWN_DRIVERS = (
    'openai_compatible',
    'anthropic',
    'gemini',
    'openai_images',
    'bedrock',
)

_ID_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:+\-/]{0,127}$')


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Model:
    """One model, exactly as its provider expects to be asked for it."""

    id: str
    label: str
    summary: str = ''
    context_tokens: int = 0
    max_output_tokens: int = 4096
    vision: bool = False
    #: False when the model rejects ``temperature`` / ``top_p``.
    sampling: bool = True
    #: True when the model wants ``max_completion_tokens`` instead of
    #: ``max_tokens`` (OpenAI reasoning models).
    max_completion_tokens: bool = False
    #: Kept working, hidden from menus.
    legacy: bool = False
    #: USD per million tokens as ``(input, output)``; ``None`` when unpriced.
    price_per_million: Optional[Tuple[float, float]] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'label': self.label,
            'summary': self.summary,
            'context_tokens': self.context_tokens,
            'max_output_tokens': self.max_output_tokens,
            'vision': self.vision,
            'sampling': self.sampling,
            'max_completion_tokens': self.max_completion_tokens,
            'legacy': self.legacy,
            'price_per_million': (
                {'input': self.price_per_million[0],
                 'output': self.price_per_million[1]}
                if self.price_per_million else None
            ),
        }


@dataclass(frozen=True)
class Provider:
    """A provider, its catalogue, and how to recover when a model is gone."""

    key: str
    label: str
    driver: str
    default: str
    models: List[Model]
    enabled: bool = True
    base_url: str = ''
    discovery_url: str = ''
    env_vars: List[str] = field(default_factory=list)
    aliases: Dict[str, str] = field(default_factory=dict)
    vision_default: Optional[str] = None
    fallbacks: List[str] = field(default_factory=list)

    def model_ids(self) -> List[str]:
        return [m.id for m in self.models]

    @property
    def supported(self) -> bool:
        return self.driver in KNOWN_DRIVERS


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
# Used only when config.yaml is missing, unreadable, or has no usable
# ai_models block. Deliberately minimal: enough to keep the platform running
# and the admin screens reachable so the real catalogue can be restored.

BOOTSTRAP: Dict[str, Any] = {
    'openai': {
        'label': 'OpenAI', 'driver': 'openai_compatible',
        'base_url': 'https://api.openai.com/v1',
        'discovery_url': 'https://api.openai.com/v1/models',
        'env_vars': ['OPENAI_API_KEY'],
        'default_model': 'gpt-5.6-terra',
        'fallbacks': ['gpt-5.6-terra', 'gpt-5.6-luna'],
        'models': [
            {'id': 'gpt-5.6-terra', 'label': 'GPT-5.6 Terra', 'vision': True,
             'sampling': False, 'max_completion_tokens': True,
             'max_output_tokens': 128000},
            {'id': 'gpt-5.6-luna', 'label': 'GPT-5.6 Luna', 'vision': True,
             'sampling': False, 'max_completion_tokens': True,
             'max_output_tokens': 128000},
        ],
    },
    'claude': {
        'label': 'Anthropic Claude', 'driver': 'anthropic',
        'discovery_url': 'https://api.anthropic.com/v1/models',
        'env_vars': ['ANTHROPIC_API_KEY', 'CLAUDE_API_KEY'],
        'default_model': 'claude-sonnet-5',
        'fallbacks': ['claude-sonnet-5'],
        'models': [
            {'id': 'claude-sonnet-5', 'label': 'Claude Sonnet 5', 'vision': True,
             'sampling': False, 'max_output_tokens': 64000},
        ],
    },
    'gemini': {
        'label': 'Google Gemini', 'driver': 'gemini',
        'discovery_url': 'https://generativelanguage.googleapis.com/v1beta/models',
        'env_vars': ['GEMINI_API_KEY', 'GOOGLE_API_KEY'],
        'default_model': 'gemini-3.8-flash',
        'fallbacks': ['gemini-3.8-flash'],
        'models': [
            {'id': 'gemini-3.8-flash', 'label': 'Gemini 3.8 Flash', 'vision': True,
             'sampling': False, 'max_output_tokens': 64000},
        ],
    },
}

#: Names other parts of the codebase have historically used for a provider.
PROVIDER_ALIASES: Dict[str, str] = {
    'anthropic': 'claude',
    'dalle': 'images',
    'dall-e': 'images',
    'google': 'gemini',
    'openai_images': 'images',
    'xai': 'grok',
}

#: Prefix -> provider, for identifiers newer than the catalogue.
_PROVIDER_PREFIXES = (
    ('anthropic.claude', 'bedrock'),
    ('claude', 'claude'),
    ('gpt-image', 'images'),
    ('dall-e', 'images'),
    ('gpt', 'openai'),
    ('o1', 'openai'),
    ('o3', 'openai'),
    ('o4', 'openai'),
    ('gemini', 'gemini'),
    ('grok', 'grok'),
    ('deepseek', 'deepseek'),
    ('sonar', 'perplexity'),
)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

@dataclass
class _Catalogue:
    providers: Dict[str, Provider]
    reverse: Dict[str, str]
    source: str
    warnings: List[str]
    mtime: float


_lock = threading.RLock()
_cache: Optional[_Catalogue] = None


def config_path() -> str:
    return os.environ.get('SKILLPILOT_CONFIG', 'config.yaml')


def _mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_price(raw: Any) -> Optional[Tuple[float, float]]:
    if isinstance(raw, dict):
        try:
            return float(raw['input']), float(raw['output'])
        except (KeyError, TypeError, ValueError):
            return None
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        try:
            return float(raw[0]), float(raw[1])
        except (TypeError, ValueError):
            return None
    return None


def _parse_model(raw: Any, warnings: List[str], provider_key: str) -> Optional[Model]:
    if not isinstance(raw, dict):
        warnings.append(f'{provider_key}: skipped a model entry that is not a mapping.')
        return None
    model_id = str(raw.get('id') or '').strip()
    if not model_id:
        warnings.append(f'{provider_key}: skipped a model with no id.')
        return None
    return Model(
        id=model_id,
        label=str(raw.get('label') or model_id).strip(),
        summary=str(raw.get('summary') or '').strip(),
        context_tokens=_as_int(raw.get('context_tokens'), 0),
        max_output_tokens=_as_int(raw.get('max_output_tokens'), 4096),
        vision=_as_bool(raw.get('vision'), False),
        sampling=_as_bool(raw.get('sampling'), True),
        max_completion_tokens=_as_bool(raw.get('max_completion_tokens'), False),
        legacy=_as_bool(raw.get('legacy'), False),
        price_per_million=_parse_price(raw.get('price_per_million')),
    )


def _parse_provider(key: str, raw: Any, warnings: List[str]) -> Optional[Provider]:
    if not isinstance(raw, dict):
        warnings.append(f'{key}: provider entry is not a mapping; ignored.')
        return None

    models = [m for m in (_parse_model(m, warnings, key)
                          for m in (raw.get('models') or [])) if m]
    if not models:
        warnings.append(f'{key}: no usable models; provider ignored.')
        return None

    seen = set()
    unique = []
    for model in models:
        if model.id in seen:
            warnings.append(f'{key}: duplicate model id {model.id}; kept the first.')
            continue
        seen.add(model.id)
        unique.append(model)

    aliases = {}
    for old, new in (raw.get('aliases') or {}).items():
        old, new = str(old).strip(), str(new).strip()
        if not old or not new:
            continue
        if old in seen:
            warnings.append(f'{key}: alias {old} shadows a live model; ignored.')
            continue
        if new not in seen:
            warnings.append(f'{key}: alias {old} -> {new}, which is not '
                            'catalogued; ignored.')
            continue
        aliases[old] = new

    default = str(raw.get('default_model') or '').strip()
    if default not in seen:
        replacement = aliases.get(default) or unique[0].id
        if default:
            warnings.append(f'{key}: default_model {default} is not catalogued; '
                            f'using {replacement}.')
        default = replacement

    vision_default = str(raw.get('vision_model') or '').strip() or None
    if vision_default and vision_default not in seen:
        vision_default = aliases.get(vision_default)

    fallbacks = []
    for candidate in (raw.get('fallbacks') or []):
        candidate = str(candidate).strip()
        candidate = candidate if candidate in seen else aliases.get(candidate, '')
        if candidate and candidate not in fallbacks:
            fallbacks.append(candidate)

    driver = str(raw.get('driver') or 'openai_compatible').strip()
    if driver not in KNOWN_DRIVERS:
        warnings.append(f'{key}: unknown driver "{driver}"; this build cannot '
                        f'call it. Known drivers: {", ".join(KNOWN_DRIVERS)}.')

    base_url = str(raw.get('base_url') or '').strip().rstrip('/')
    if driver == 'openai_compatible' and not base_url:
        warnings.append(f'{key}: driver openai_compatible needs a base_url.')

    return Provider(
        key=key,
        label=str(raw.get('label') or key.title()).strip(),
        driver=driver,
        default=default,
        models=unique,
        enabled=_as_bool(raw.get('enabled'), True),
        base_url=base_url,
        discovery_url=str(raw.get('discovery_url') or '').strip(),
        env_vars=[str(v).strip() for v in (raw.get('env_vars') or []) if str(v).strip()],
        aliases=aliases,
        vision_default=vision_default,
        fallbacks=fallbacks,
    )


def _build(raw_providers: Dict[str, Any], source: str,
           warnings: List[str], mtime: float) -> _Catalogue:
    providers: Dict[str, Provider] = {}
    for key, raw in (raw_providers or {}).items():
        key = str(key).strip().lower()
        if not key:
            continue
        provider = _parse_provider(key, raw, warnings)
        if provider is not None:
            providers[key] = provider

    reverse: Dict[str, str] = {}
    for provider in providers.values():
        for model in provider.models:
            reverse.setdefault(model.id, provider.key)
        for old in provider.aliases:
            reverse.setdefault(old, provider.key)

    return _Catalogue(providers=providers, reverse=reverse, source=source,
                      warnings=warnings, mtime=mtime)


def _read_config_block() -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """The raw ``ai_models`` mapping from config.yaml, plus any warnings."""
    path = config_path()
    warnings: List[str] = []
    try:
        import yaml
    except ImportError:
        return None, ['PyYAML is not installed; using the built-in catalogue.']

    try:
        with open(path, 'r', encoding='utf-8') as handle:
            loaded = yaml.safe_load(handle) or {}
    except FileNotFoundError:
        return None, [f'{path} not found; using the built-in catalogue.']
    except yaml.YAMLError as exc:
        return None, [f'{path} is not valid YAML ({exc}); '
                      'using the built-in catalogue.']
    except OSError as exc:
        return None, [f'{path} could not be read ({exc}); '
                      'using the built-in catalogue.']

    block = loaded.get('ai_models')
    if not isinstance(block, dict) or not block:
        return None, [f'{path} has no ai_models block; '
                      'using the built-in catalogue.']
    return block, warnings


def _load() -> _Catalogue:
    path = config_path()
    mtime = _mtime(path)
    block, warnings = _read_config_block()
    if block is None:
        catalogue = _build(copy.deepcopy(BOOTSTRAP), 'built-in', warnings, mtime)
        for line in warnings:
            print(f'[model_registry] {line}')
        return catalogue

    catalogue = _build(block, path, warnings, mtime)
    if not catalogue.providers:
        warnings.append('No usable providers in ai_models; '
                        'falling back to the built-in catalogue.')
        catalogue = _build(copy.deepcopy(BOOTSTRAP), 'built-in', warnings, mtime)
    for line in warnings:
        print(f'[model_registry] {line}')
    return catalogue


def _catalogue() -> _Catalogue:
    """The current catalogue, re-reading config.yaml if it changed on disk.

    The timestamp check is what lets one worker process see a model another
    worker just saved, and what lets a hand edit take effect without a
    restart.
    """
    global _cache
    with _lock:
        if _cache is None or _cache.mtime != _mtime(config_path()):
            _cache = _load()
        return _cache


def reload_config() -> None:
    """Force a re-read on the next access."""
    global _cache
    with _lock:
        _cache = None


def catalogue_status() -> Dict[str, Any]:
    """Where the catalogue came from and anything wrong with it."""
    catalogue = _catalogue()
    return {
        'source': catalogue.source,
        'path': os.path.abspath(config_path()),
        'writable': _is_writable(),
        'provider_count': len(catalogue.providers),
        'model_count': sum(len(p.models) for p in catalogue.providers.values()),
        'warnings': list(catalogue.warnings),
    }


def _is_writable() -> bool:
    path = config_path()
    try:
        if os.path.exists(path):
            return os.access(path, os.W_OK) and os.access(
                os.path.dirname(os.path.abspath(path)) or '.', os.W_OK)
        return os.access(os.path.dirname(os.path.abspath(path)) or '.', os.W_OK)
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _normalise_provider(provider: str) -> str:
    key = (provider or '').strip().lower()
    return PROVIDER_ALIASES.get(key, key)


def get_provider(provider: str) -> Optional[Provider]:
    return _catalogue().providers.get(_normalise_provider(provider))


def list_providers(*, include_disabled: bool = True) -> List[str]:
    return [key for key, spec in _catalogue().providers.items()
            if include_disabled or spec.enabled]


def default_model(provider: str, *, vision: bool = False) -> Optional[str]:
    """Configured default model for ``provider``."""
    spec = get_provider(provider)
    if spec is None:
        return None

    override = os.environ.get(f'SKILLPILOT_MODEL_{spec.key.upper()}')
    if override and override.strip():
        wanted = override.strip()
        return spec.aliases.get(wanted, wanted)

    if vision and spec.vision_default:
        return spec.vision_default
    return spec.default


def get_model(provider: str, model_id: str) -> Optional[Model]:
    """Catalogue entry for ``model_id``, or ``None`` if it is not listed.

    ``None`` is not a failure: an administrator may point the platform at a
    model newer than the catalogue, and callers fall back to conservative
    request defaults.
    """
    spec = get_provider(provider)
    if spec is None:
        return None
    for model in spec.models:
        if model.id == model_id:
            return model
    return None


def resolve(provider: str, requested: Optional[str] = None, *,
            vision: bool = False) -> Optional[str]:
    """The identifier to actually send to ``provider``."""
    spec = get_provider(provider)
    if spec is None:
        return (requested or '').strip() or None

    wanted = (requested or '').strip()
    if not wanted:
        return default_model(provider, vision=vision)

    wanted = spec.aliases.get(wanted, wanted)

    entry = get_model(spec.key, wanted)
    if entry is not None and vision and not entry.vision:
        return default_model(spec.key, vision=True) or wanted
    return wanted


def available_models(provider: str, *, include_legacy: bool = False) -> List[Dict[str, Any]]:
    spec = get_provider(provider)
    if spec is None:
        return []
    return [m.as_dict() for m in spec.models if include_legacy or not m.legacy]


def fallback_chain(provider: str, model_id: Optional[str] = None) -> List[str]:
    """Models to try, in order, starting with ``model_id``."""
    spec = get_provider(provider)
    if spec is None:
        return [model_id] if model_id else []

    chain: List[str] = []
    for candidate in [model_id, default_model(spec.key), *spec.fallbacks]:
        if candidate and candidate not in chain:
            chain.append(candidate)
    return chain


def provider_for_model(model_id: str, default: str = 'openai') -> str:
    """Which provider serves ``model_id``."""
    catalogue = _catalogue()
    wanted = (model_id or '').strip()
    if not wanted:
        return default
    if wanted in catalogue.reverse:
        return catalogue.reverse[wanted]
    if wanted in catalogue.providers:
        return wanted
    if wanted in PROVIDER_ALIASES:
        return PROVIDER_ALIASES[wanted]

    lowered = wanted.lower()
    for prefix, provider in _PROVIDER_PREFIXES:
        if lowered.startswith(prefix):
            return provider
    return default


def price_per_1k(provider: str, model_id: Optional[str]) -> Optional[Dict[str, float]]:
    """Input/output price per 1,000 tokens, or ``None`` if unpriced."""
    resolved = resolve(provider, model_id)
    if not resolved:
        return None
    entry = get_model(provider, resolved)
    if entry is None or entry.price_per_million is None:
        return None
    return {'input': entry.price_per_million[0] / 1000.0,
            'output': entry.price_per_million[1] / 1000.0}


def base_url(provider: str) -> Optional[str]:
    spec = get_provider(provider)
    return spec.base_url or None if spec else None


def provider_option(provider: str, option: str, default: Any = None) -> Any:
    """Any extra key set on a provider in config.yaml.

    Lets a deployment tune a provider — an output-token cap, an image size —
    without a code change and without the registry needing to know in advance
    what the option is called.
    """
    path = config_path()
    try:
        import yaml
        with open(path, 'r', encoding='utf-8') as handle:
            block = (yaml.safe_load(handle) or {}).get('ai_models') or {}
    except Exception:
        return default
    entry = block.get(_normalise_provider(provider))
    if not isinstance(entry, dict) or option not in entry:
        return default
    return entry[option]


def output_budget(provider: str, default: int = 8000) -> int:
    """Largest response to ask ``provider`` for.

    A provider may cap this in config.yaml with ``max_tokens``; the transport
    then caps again at whatever the chosen model actually accepts.
    """
    try:
        return max(1, int(provider_option(provider, 'max_tokens', default)))
    except (TypeError, ValueError):
        return default


def discovery_url(provider: str) -> Optional[str]:
    spec = get_provider(provider)
    return spec.discovery_url or None if spec else None


def providers_with_driver(driver: str) -> List[str]:
    return [key for key, spec in _catalogue().providers.items()
            if spec.driver == driver]


#: Provider error text meaning "this model identifier will never work", as
#: opposed to a transient failure worth retrying with the same model.
_UNAVAILABLE_PATTERNS = (
    r'model[_ ]not[_ ]found',
    r'does not exist',
    r'is not available',
    r'unknown model',
    r'invalid model',
    r'unsupported model',
    r'no longer (?:available|supported)',
    r'has been (?:deprecated|retired|removed|shut down)',
    r'not[_ ]found[_ ]error',
    r'do not have access to (?:the )?model',
)
_UNAVAILABLE_RE = re.compile('|'.join(_UNAVAILABLE_PATTERNS), re.IGNORECASE)


def is_model_unavailable_error(error: Any) -> bool:
    return bool(_UNAVAILABLE_RE.search(str(error or '')))


def describe(providers: Optional[Iterable[str]] = None,
             *, include_legacy: bool = False) -> Dict[str, Any]:
    """Whole catalogue as JSON, for the admin screens and the public API."""
    keys = list(providers) if providers is not None else list_providers()
    out: Dict[str, Any] = {}
    for key in keys:
        spec = get_provider(key)
        if spec is None:
            continue
        out[spec.key] = {
            'label': spec.label,
            'driver': spec.driver,
            'supported': spec.supported,
            'enabled': spec.enabled,
            'base_url': spec.base_url,
            'has_discovery': bool(spec.discovery_url),
            'default_model': default_model(spec.key),
            'vision_model': default_model(spec.key, vision=True),
            'env_vars': list(spec.env_vars),
            'fallbacks': list(spec.fallbacks),
            'aliases': dict(spec.aliases),
            'models': available_models(spec.key, include_legacy=include_legacy),
        }
    return out


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def _yaml_rt():
    """A round-trip YAML handler that preserves comments, or ``None``."""
    try:
        from ruamel.yaml import YAML
    except ImportError:
        return None
    handler = YAML()
    handler.preserve_quotes = True
    handler.width = 4096
    handler.indent(mapping=2, sequence=4, offset=2)
    return handler


def _mutate(apply_change, node: str = 'ai_models') -> None:
    """Load config.yaml, apply ``apply_change``, validate, write atomically.

    ``node`` selects what ``apply_change`` receives: the ``ai_models`` block
    by default, or the whole document for edits elsewhere in the file.

    Nothing is written unless the result still parses into at least one
    working provider — a bad edit can never take the platform down.
    """
    path = config_path()
    if not _is_writable():
        raise CatalogueError(
            f'{os.path.abspath(path)} is not writable by the server process. '
            'Grant write permission, or edit the file directly and the change '
            'will be picked up automatically.'
        )

    with _lock:
        handler = _yaml_rt()
        if handler is None:
            raise CatalogueError(
                'Saving needs the ruamel.yaml package, which preserves the '
                'comments in config.yaml. Install it with: '
                'pip install -r requirements.txt'
            )

        try:
            with open(path, 'r', encoding='utf-8') as source:
                document = handler.load(source) or {}
        except FileNotFoundError:
            raise CatalogueError(f'{path} does not exist.')
        except Exception as exc:
            raise CatalogueError(f'{path} could not be parsed: {exc}')

        if node == 'ai_models':
            block = document.get('ai_models')
            if not isinstance(block, dict):
                raise CatalogueError(
                    f'{path} has no ai_models block to edit. Restore it from '
                    'the shipped config.yaml before saving from the admin '
                    'screen.'
                )
            apply_change(block)
        else:
            apply_change(document)

        # Validate before writing: parse the edited block exactly as a load
        # would, and refuse anything that leaves no working provider.
        import io
        probe = io.StringIO()
        handler.dump(document, probe)
        try:
            import yaml
            reparsed = yaml.safe_load(probe.getvalue()) or {}
        except Exception as exc:
            raise CatalogueError(f'The edit produced invalid YAML: {exc}')

        warnings: List[str] = []
        candidate = _build(reparsed.get('ai_models') or {}, path, warnings, 0.0)
        if not candidate.providers:
            raise CatalogueError(
                'The edit would leave no usable provider, so it was not '
                'saved. ' + (warnings[0] if warnings else '')
            )

        directory = os.path.dirname(os.path.abspath(path)) or '.'
        handle, temporary = tempfile.mkstemp(dir=directory, prefix='.config.yaml.')
        try:
            with os.fdopen(handle, 'w', encoding='utf-8') as out:
                handler.dump(document, out)
            if os.path.exists(path):
                try:  # Keep the original file mode.
                    os.chmod(temporary, os.stat(path).st_mode & 0o777)
                except OSError:
                    pass
            os.replace(temporary, path)
        except Exception as exc:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise CatalogueError(f'Could not write {path}: {exc}')

        reload_config()


def _require_provider(block: Dict[str, Any], provider: str) -> Dict[str, Any]:
    key = _normalise_provider(provider)
    entry = block.get(key)
    if not isinstance(entry, dict):
        raise CatalogueError(f'There is no provider called "{provider}" in the '
                             'catalogue.')
    return entry


def _validate_model_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    model_id = str(payload.get('id') or '').strip()
    if not model_id:
        raise CatalogueError('A model id is required.')
    if not _ID_PATTERN.match(model_id):
        raise CatalogueError(
            f'"{model_id}" is not a valid model id. Use the identifier exactly '
            'as the provider documents it: letters, digits and . _ - : + /'
        )

    cleaned: Dict[str, Any] = {
        'id': model_id,
        'label': str(payload.get('label') or model_id).strip()[:120],
    }
    summary = str(payload.get('summary') or '').strip()[:300]
    if summary:
        cleaned['summary'] = summary

    context_tokens = _as_int(payload.get('context_tokens'), 0)
    if context_tokens > 0:
        cleaned['context_tokens'] = context_tokens

    max_output = _as_int(payload.get('max_output_tokens'), 4096)
    cleaned['max_output_tokens'] = max(1, min(max_output, 1_000_000))
    cleaned['vision'] = _as_bool(payload.get('vision'), False)
    cleaned['sampling'] = _as_bool(payload.get('sampling'), True)
    if _as_bool(payload.get('max_completion_tokens'), False):
        cleaned['max_completion_tokens'] = True
    if _as_bool(payload.get('legacy'), False):
        cleaned['legacy'] = True

    price = _parse_price(payload.get('price_per_million'))
    if price:
        cleaned['price_per_million'] = {'input': price[0], 'output': price[1]}
    return cleaned


def save_model(provider: str, payload: Dict[str, Any], *,
               make_default: bool = False) -> Dict[str, Any]:
    """Add a model, or update it if the id is already catalogued.

    ``make_default`` also points the provider's ``default_model`` at it, which
    is what the admin screen does once a test call has succeeded.

    Capabilities the caller leaves out are inherited from the provider's
    current default model. That matters: a model added straight from the
    Discover list carries only an id, and guessing ``sampling: true`` for a
    provider whose models reject ``temperature`` would turn every request
    into a 400. Siblings from one vendor share a request shape far more often
    than not, so the current default is the right thing to copy.
    """
    inherited = dict(payload)
    template = get_model(provider, default_model(provider) or '')
    if template is not None:
        for attribute in ('vision', 'sampling', 'max_completion_tokens',
                          'max_output_tokens', 'context_tokens'):
            if inherited.get(attribute) in (None, ''):
                inherited[attribute] = getattr(template, attribute)

    cleaned = _validate_model_payload(inherited)

    def change(block):
        entry = _require_provider(block, provider)
        models = entry.setdefault('models', [])
        for index, existing in enumerate(models):
            if isinstance(existing, dict) and str(existing.get('id')) == cleaned['id']:
                models[index] = cleaned
                break
        else:
            models.append(cleaned)

        # A previously retired id being added back must lose its alias, or it
        # would be mapped away from itself on the next request.
        aliases = entry.get('aliases')
        if isinstance(aliases, dict) and cleaned['id'] in aliases:
            del aliases[cleaned['id']]

        if make_default:
            entry['default_model'] = cleaned['id']

    _mutate(change)
    return cleaned


def delete_model(provider: str, model_id: str, *,
                 alias_to: Optional[str] = None) -> None:
    """Remove a model from the menus.

    ``alias_to`` records it as an alias of a model that is still current, so
    anything already storing the old id keeps working. This is what to do
    when a vendor retires a model; deleting outright is only right for an
    entry added in error.
    """
    model_id = str(model_id or '').strip()
    if not model_id:
        raise CatalogueError('A model id is required.')

    def change(block):
        entry = _require_provider(block, provider)
        models = entry.get('models') or []
        remaining = [m for m in models
                     if not (isinstance(m, dict) and str(m.get('id')) == model_id)]
        if len(remaining) == len(models):
            raise CatalogueError(f'{provider} has no model called "{model_id}".')
        if not remaining:
            raise CatalogueError(
                f'"{model_id}" is the only model left for {provider}. Add a '
                'replacement before removing it, or disable the provider.'
            )
        entry['models'] = remaining

        # Who takes over: the caller's choice, else the current default, else
        # the first surviving entry in the configured fallback chain — which
        # is the deployment's own stated preference — and only then whatever
        # is left.
        surviving = [str(m.get('id')) for m in remaining]
        replacement = alias_to or str(entry.get('default_model') or '')
        if replacement == model_id or replacement not in surviving:
            chain = [str(f) for f in (entry.get('fallbacks') or [])]
            replacement = next((f for f in chain if f in surviving), surviving[0])
        if replacement:
            entry.setdefault('aliases', {})[model_id] = replacement

        if str(entry.get('default_model') or '') == model_id:
            entry['default_model'] = replacement or str(remaining[0].get('id'))
        if str(entry.get('vision_model') or '') == model_id:
            entry['vision_model'] = replacement or str(remaining[0].get('id'))
        entry['fallbacks'] = [f for f in (entry.get('fallbacks') or [])
                              if str(f) != model_id] or [entry['default_model']]

    _mutate(change)


def set_default_model(provider: str, model_id: str, *,
                      vision: bool = False) -> None:
    """Point a provider's default (or vision default) at a catalogued model."""
    model_id = str(model_id or '').strip()

    def change(block):
        entry = _require_provider(block, provider)
        ids = {str(m.get('id')) for m in (entry.get('models') or [])
               if isinstance(m, dict)}
        if model_id not in ids:
            raise CatalogueError(
                f'"{model_id}" is not in {provider}\'s catalogue. Add and test '
                'it first.'
            )
        entry['vision_model' if vision else 'default_model'] = model_id

    _mutate(change)


def set_provider_enabled(provider: str, enabled: bool) -> None:
    """Show or hide a whole provider."""
    def change(block):
        _require_provider(block, provider)['enabled'] = bool(enabled)

    _mutate(change)


def get_app_setting(key: str, default: Any = None) -> Any:
    """A value from the top-level ``app:`` block of config.yaml."""
    path = config_path()
    try:
        import yaml
        with open(path, 'r', encoding='utf-8') as handle:
            block = (yaml.safe_load(handle) or {}).get('app') or {}
    except Exception:
        return default
    return block.get(key, default)


def set_app_setting(key: str, value: Any) -> None:
    """Write a value into the ``app:`` block, comments preserved.

    Keeps settings an administrator can change in the same file as the model
    catalogue, rather than splitting them between a config file and a
    database table.
    """
    def change(document):
        block = document.get('app')
        if not isinstance(block, dict):
            raise CatalogueError(f'{config_path()} has no app: block to edit.')
        block[key] = value

    _mutate(change, node='app')


def __getattr__(name: str) -> Any:
    """Serve the historical module-level tables from the live catalogue.

    ``PROVIDERS``, ``PRICE_PER_MILLION`` and ``OPENAI_COMPATIBLE_BASE_URLS``
    were plain dicts before the catalogue moved into config.yaml. They are
    still read in a few places and in the tests, so they are computed on
    access rather than frozen at import time.
    """
    if name == 'PROVIDERS':
        return dict(_catalogue().providers)
    if name == 'PRICE_PER_MILLION':
        return {
            model.id: model.price_per_million
            for provider in _catalogue().providers.values()
            for model in provider.models
            if model.price_per_million is not None
        }
    if name == 'OPENAI_COMPATIBLE_BASE_URLS':
        return {
            key: spec.base_url
            for key, spec in _catalogue().providers.items()
            if spec.driver == 'openai_compatible' and spec.base_url
        }
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
