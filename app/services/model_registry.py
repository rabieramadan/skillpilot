"""Single source of truth for every AI model SkillPilot can talk to.

Before this module existed, model identifiers were literal strings spread over
roughly ninety call sites across services, routes, templates and JavaScript.
Each provider retires identifiers on its own schedule, so the codebase drifted
into a mix of live, deprecated and long-dead names, and a retirement showed up
as a 404 in front of a student.

Everything now resolves through :func:`resolve`, which also gives the platform
three properties it did not have:

* **Aliasing** — a retired identifier stored in the database or picked from a
  stale dropdown is mapped to its current replacement instead of failing.
* **Fallbacks** — :func:`fallback_chain` yields the next model to try when a
  provider rejects one, so a retirement degrades instead of breaking.
* **Capabilities** — request building asks the catalogue what a model accepts
  (``temperature``, ``max_tokens`` vs ``max_completion_tokens``, images)
  instead of pattern-matching the identifier at the call site.

Precedence for the default model of a provider, highest first:

1. ``SKILLPILOT_MODEL_<PROVIDER>`` environment variable
2. ``models.<provider>.default_model`` in ``config.yaml``
3. ``DEFAULT`` on the :class:`Provider` entry below

Catalogue reviewed: 14 September 2026. When a provider ships a new generation,
edit this file only: add the model to ``models``, point ``default`` at it, and
add the superseded identifier to ``aliases``.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

__all__ = [
    'Model',
    'Provider',
    'PROVIDERS',
    'available_models',
    'default_model',
    'describe',
    'fallback_chain',
    'get_model',
    'is_model_unavailable_error',
    'list_providers',
    'resolve',
]


@dataclass(frozen=True)
class Model:
    """One model as the provider's API expects to be asked for it."""

    id: str
    label: str
    #: Short sentence shown in the admin model picker.
    summary: str = ''
    #: Total context window in tokens, as published by the provider.
    context_tokens: int = 0
    #: Largest ``max_tokens`` the model will accept for a single response.
    max_output_tokens: int = 4096
    #: Model accepts image parts in the request.
    vision: bool = False
    #: Model accepts ``temperature`` / ``top_p``. Newer reasoning models
    #: reject them outright (OpenAI 400s, Gemini 3 silently ignores them).
    sampling: bool = True
    #: OpenAI-compatible providers only: send ``max_completion_tokens``
    #: instead of ``max_tokens``.
    max_completion_tokens: bool = False
    #: Model is kept for compatibility but should not be offered as a default.
    legacy: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'label': self.label,
            'summary': self.summary,
            'context_tokens': self.context_tokens,
            'max_output_tokens': self.max_output_tokens,
            'vision': self.vision,
            'legacy': self.legacy,
        }


@dataclass(frozen=True)
class Provider:
    """A provider, its catalogue, and how to recover when a model is gone."""

    key: str
    label: str
    default: str
    models: List[Model]
    #: Environment variables holding the API key, in priority order.
    env_vars: List[str] = field(default_factory=list)
    #: Retired or renamed identifier -> the identifier that replaces it.
    aliases: Dict[str, str] = field(default_factory=dict)
    #: Preferred model for requests that carry an image.
    vision_default: Optional[str] = None
    #: Tried in order when the provider rejects the requested model.
    fallbacks: List[str] = field(default_factory=list)

    def model_ids(self) -> List[str]:
        return [m.id for m in self.models]


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------
# Only current, generally available identifiers are listed as selectable.
# Superseded names stay in ``aliases`` so saved selections keep working.

_OPENAI = Provider(
    key='openai',
    label='OpenAI',
    default='gpt-5.6-terra',
    vision_default='gpt-5.6-terra',
    env_vars=['OPENAI_API_KEY'],
    models=[
        Model('gpt-6-astra', 'GPT-6 Astra',
              'Flagship reasoning model. Highest quality, highest cost.',
              context_tokens=1_050_000, max_output_tokens=128_000,
              vision=True, sampling=False, max_completion_tokens=True),
        Model('gpt-5.6-sol', 'GPT-5.6 Sol',
              'Frontier tier below Astra. Strong reasoning at lower cost.',
              context_tokens=400_000, max_output_tokens=128_000,
              vision=True, sampling=False, max_completion_tokens=True),
        Model('gpt-5.6-terra', 'GPT-5.6 Terra',
              'Balanced default: good reasoning, sensible price.',
              context_tokens=400_000, max_output_tokens=128_000,
              vision=True, sampling=False, max_completion_tokens=True),
        Model('gpt-5.6-luna', 'GPT-5.6 Luna',
              'Cheapest tier. Use for high-volume classification and drafts.',
              context_tokens=400_000, max_output_tokens=128_000,
              vision=True, sampling=False, max_completion_tokens=True),
        Model('gpt-5.2', 'GPT-5.2',
              'Previous flagship. Kept for reproducing earlier output.',
              context_tokens=400_000, max_output_tokens=128_000,
              vision=True, sampling=False, max_completion_tokens=True,
              legacy=True),
    ],
    aliases={
        # Retired 2025-2026 identifiers still stored in databases and UIs.
        'gpt-3.5-turbo': 'gpt-5.6-luna',
        'gpt-4': 'gpt-5.6-terra',
        'gpt-4-32k': 'gpt-5.6-terra',
        'gpt-4-turbo': 'gpt-5.6-terra',
        'gpt-4-turbo-preview': 'gpt-5.6-terra',
        'gpt-4-vision-preview': 'gpt-5.6-terra',
        'gpt-4o': 'gpt-5.6-terra',
        'gpt-4o-mini': 'gpt-5.6-luna',
        'gpt-4.1': 'gpt-5.6-terra',
        'gpt-4.1-mini': 'gpt-5.6-luna',
        'gpt-4.1-nano': 'gpt-5.6-luna',
        'gpt-5': 'gpt-5.6-terra',
        'gpt-5-mini': 'gpt-5.6-luna',
        'gpt-5-nano': 'gpt-5.6-luna',
        'gpt-5.1': 'gpt-5.6-terra',
        'gpt-5.2-chat-latest': 'gpt-5.6-terra',
        'o1': 'gpt-5.6-sol',
        'o1-mini': 'gpt-5.6-luna',
        'o3': 'gpt-5.6-sol',
        'o3-mini': 'gpt-5.6-luna',
        'o4-mini': 'gpt-5.6-luna',
    },
    fallbacks=['gpt-5.6-terra', 'gpt-5.6-luna', 'gpt-5.2'],
)

_CLAUDE = Provider(
    key='claude',
    label='Anthropic Claude',
    default='claude-sonnet-5',
    vision_default='claude-sonnet-5',
    env_vars=['ANTHROPIC_API_KEY', 'CLAUDE_API_KEY'],
    models=[
        Model('claude-opus-5', 'Claude Opus 5',
              'Most capable Claude. Use for grading, rubrics and analysis.',
              context_tokens=1_000_000, max_output_tokens=64_000,
              vision=True, sampling=False),
        Model('claude-sonnet-5', 'Claude Sonnet 5',
              'Balanced default: near-Opus quality at a fraction of the cost.',
              context_tokens=1_000_000, max_output_tokens=64_000,
              vision=True, sampling=False),
        Model('claude-haiku-4-5', 'Claude Haiku 4.5',
              'Fastest and cheapest. Good for short tutoring turns.',
              context_tokens=200_000, max_output_tokens=32_000,
              vision=True, sampling=True),
    ],
    aliases={
        'claude-3-haiku-20240307': 'claude-haiku-4-5',
        'claude-3-opus-20240229': 'claude-opus-5',
        'claude-3-sonnet-20240229': 'claude-sonnet-5',
        'claude-3-5-haiku-20241022': 'claude-haiku-4-5',
        'claude-3-5-sonnet-20241022': 'claude-sonnet-5',
        'claude-3-7-sonnet-20250219': 'claude-sonnet-5',
        'claude-haiku-3-5-20241022': 'claude-haiku-4-5',
        'claude-opus-4-20250514': 'claude-opus-5',
        'claude-opus-4-1-20250805': 'claude-opus-5',
        'claude-sonnet-4-20250514': 'claude-sonnet-5',
        'claude-sonnet-4-5-20250929': 'claude-sonnet-5',
        'claude-haiku-4-5-20251001': 'claude-haiku-4-5',
        'claude-opus-4-5': 'claude-opus-5',
        'claude-opus-4-6': 'claude-opus-5',
        'claude-sonnet-4-6': 'claude-sonnet-5',
    },
    fallbacks=['claude-sonnet-5', 'claude-haiku-4-5'],
)

_GEMINI = Provider(
    key='gemini',
    label='Google Gemini',
    default='gemini-3.8-flash',
    vision_default='gemini-3.8-flash',
    env_vars=['GEMINI_API_KEY', 'GOOGLE_API_KEY'],
    models=[
        Model('gemini-3.1-pro', 'Gemini 3.1 Pro',
              'Most capable Gemini. Long documents and deep analysis.',
              context_tokens=1_000_000, max_output_tokens=64_000,
              vision=True, sampling=False),
        Model('gemini-3.8-flash', 'Gemini 3.8 Flash',
              'Balanced default: fast, 1M context, tunable thinking.',
              context_tokens=1_000_000, max_output_tokens=64_000,
              vision=True, sampling=False),
        Model('gemini-3.7-flash', 'Gemini 3.7 Flash',
              'Previous Flash generation. Kept for cost comparison.',
              context_tokens=1_000_000, max_output_tokens=64_000,
              vision=True, sampling=False),
        Model('gemini-3.5-flash-lite', 'Gemini 3.5 Flash-Lite',
              'Cheapest Gemini. Bulk classification and short answers.',
              context_tokens=1_000_000, max_output_tokens=32_000,
              vision=True, sampling=False),
    ],
    aliases={
        'gemini-pro': 'gemini-3.8-flash',
        'gemini-pro-vision': 'gemini-3.8-flash',
        'gemini-1.5-flash': 'gemini-3.8-flash',
        'gemini-1.5-pro': 'gemini-3.1-pro',
        'gemini-2.0-flash': 'gemini-3.8-flash',
        'gemini-2.5-flash': 'gemini-3.8-flash',
        'gemini-2.5-pro': 'gemini-3.1-pro',
        'gemini-3-pro-preview': 'gemini-3.1-pro',
        'gemini-3-flash-preview': 'gemini-3.8-flash',
        'gemini-3.5-flash': 'gemini-3.8-flash',
    },
    fallbacks=['gemini-3.8-flash', 'gemini-3.5-flash-lite'],
)

_GROK = Provider(
    key='grok',
    label='xAI Grok',
    default='grok-4.6',
    vision_default='grok-4.6',
    env_vars=['XAI_API_KEY', 'GROK_API_KEY'],
    models=[
        Model('grok-4.6', 'Grok 4.6',
              'Current xAI flagship. Strong coding and tool use.',
              context_tokens=2_000_000, max_output_tokens=32_000,
              vision=True),
        Model('grok-4.5', 'Grok 4.5',
              'Previous flagship. Slightly cheaper.',
              context_tokens=2_000_000, max_output_tokens=32_000,
              vision=True),
        Model('grok-4.3', 'Grok 4.3',
              'Long-context tier with native video input.',
              context_tokens=1_000_000, max_output_tokens=32_000,
              vision=True),
    ],
    aliases={
        'grok-2': 'grok-4.6',
        'grok-3': 'grok-4.6',
        'grok-3-mini': 'grok-4.3',
        'grok-4': 'grok-4.6',
        'grok-4-fast': 'grok-4.3',
        'grok-4.1': 'grok-4.3',
        'grok-4.1-fast': 'grok-4.3',
    },
    fallbacks=['grok-4.6', 'grok-4.3'],
)

_DEEPSEEK = Provider(
    key='deepseek',
    label='DeepSeek',
    default='deepseek-v4-flash',
    env_vars=['DEEPSEEK_API_KEY'],
    models=[
        Model('deepseek-v4-flash', 'DeepSeek V4 Flash',
              'Fast and cheap. Good for code explanation and summaries.',
              context_tokens=1_000_000, max_output_tokens=32_000),
        Model('deepseek-v4-pro', 'DeepSeek V4 Pro',
              'Reasoning tier. Use for hard maths and multi-step problems.',
              context_tokens=1_000_000, max_output_tokens=64_000),
    ],
    aliases={
        # deepseek-chat / deepseek-reasoner were retired on 24 July 2026.
        'deepseek-chat': 'deepseek-v4-flash',
        'deepseek-coder': 'deepseek-v4-flash',
        'deepseek-reasoner': 'deepseek-v4-pro',
        'deepseek-v3': 'deepseek-v4-flash',
        'deepseek-r1': 'deepseek-v4-pro',
    },
    fallbacks=['deepseek-v4-flash'],
)

_PERPLEXITY = Provider(
    key='perplexity',
    label='Perplexity Sonar',
    default='sonar-pro',
    env_vars=['PERPLEXITY_API_KEY'],
    models=[
        Model('sonar', 'Sonar',
              'Lightweight grounded search with citations.',
              context_tokens=128_000, max_output_tokens=8_000),
        Model('sonar-pro', 'Sonar Pro',
              'Deeper retrieval across more sources. Default.',
              context_tokens=200_000, max_output_tokens=8_000),
        Model('sonar-reasoning', 'Sonar Reasoning',
              'Chain-of-thought answers grounded in live search.',
              context_tokens=128_000, max_output_tokens=8_000),
        Model('sonar-reasoning-pro', 'Sonar Reasoning Pro',
              'Reasoning tier with the wider Pro retrieval set.',
              context_tokens=200_000, max_output_tokens=8_000),
        Model('sonar-deep-research', 'Sonar Deep Research',
              'Exhaustive multi-step research. Slow and expensive.',
              context_tokens=200_000, max_output_tokens=16_000),
    ],
    aliases={
        'llama-3-sonar-large-32k-online': 'sonar-pro',
        'llama-3.1-sonar-large-128k-online': 'sonar-pro',
        'llama-3.1-sonar-small-128k-online': 'sonar',
        'pplx-70b-online': 'sonar-pro',
    },
    fallbacks=['sonar-pro', 'sonar'],
)

_IMAGES = Provider(
    key='images',
    label='OpenAI Images',
    default='gpt-image-2',
    env_vars=['OPENAI_API_KEY'],
    models=[
        Model('gpt-image-2', 'GPT Image 2',
              'Current image model. Native reasoning, best prompt adherence.',
              max_output_tokens=0),
        Model('gpt-image-1.5', 'GPT Image 1.5',
              'Previous generation. Cheaper, still high quality.',
              max_output_tokens=0),
        Model('gpt-image-1-mini', 'GPT Image 1 Mini',
              'Cheapest. Use for thumbnails and drafts.',
              max_output_tokens=0),
    ],
    aliases={
        # The DALL-E endpoints were shut down on 12 May 2026.
        'dall-e-2': 'gpt-image-1-mini',
        'dall-e-3': 'gpt-image-2',
        'gpt-image-1': 'gpt-image-1.5',
    },
    fallbacks=['gpt-image-2', 'gpt-image-1.5', 'gpt-image-1-mini'],
)

_BEDROCK = Provider(
    key='bedrock',
    label='AWS Bedrock (Claude)',
    default='anthropic.claude-sonnet-5',
    vision_default='anthropic.claude-sonnet-5',
    env_vars=['BEDROCK_API_KEY'],
    models=[
        Model('anthropic.claude-opus-5', 'Claude Opus 5 (Bedrock)',
              'Most capable Claude on Bedrock.',
              context_tokens=1_000_000, max_output_tokens=64_000,
              vision=True, sampling=False),
        Model('anthropic.claude-sonnet-5', 'Claude Sonnet 5 (Bedrock)',
              'Balanced default on Bedrock.',
              context_tokens=1_000_000, max_output_tokens=64_000,
              vision=True, sampling=False),
        Model('anthropic.claude-haiku-4-5', 'Claude Haiku 4.5 (Bedrock)',
              'Fast and cheap on Bedrock.',
              context_tokens=200_000, max_output_tokens=32_000,
              vision=True),
    ],
    aliases={
        'anthropic.claude-3-haiku-20240307-v1:0': 'anthropic.claude-haiku-4-5',
        'anthropic.claude-3-5-haiku-20241022-v1:0': 'anthropic.claude-haiku-4-5',
        'anthropic.claude-opus-4-20250514-v1:0': 'anthropic.claude-opus-5',
        'anthropic.claude-sonnet-4-20250514-v1:0': 'anthropic.claude-sonnet-5',
        'anthropic.claude-sonnet-4-5-20250929-v1:0': 'anthropic.claude-sonnet-5',
    },
    fallbacks=['anthropic.claude-sonnet-5', 'anthropic.claude-haiku-4-5'],
)

PROVIDERS: Dict[str, Provider] = {
    p.key: p for p in (
        _OPENAI, _CLAUDE, _GEMINI, _GROK, _DEEPSEEK,
        _PERPLEXITY, _IMAGES, _BEDROCK,
    )
}

#: Providers that are reached through an OpenAI-compatible ``/chat/completions``
#: endpoint, and the base URL to use for each.
OPENAI_COMPATIBLE_BASE_URLS: Dict[str, str] = {
    'openai': 'https://api.openai.com/v1',
    'grok': 'https://api.x.ai/v1',
    'deepseek': 'https://api.deepseek.com/v1',
    'perplexity': 'https://api.perplexity.ai',
}

#: Names the rest of the codebase has historically used for a provider.
PROVIDER_ALIASES: Dict[str, str] = {
    'anthropic': 'claude',
    'dalle': 'images',
    'dall-e': 'images',
    'google': 'gemini',
    'openai_images': 'images',
    'xai': 'grok',
}


# ---------------------------------------------------------------------------
# Configuration overrides
# ---------------------------------------------------------------------------

_config_cache: Optional[Dict[str, Any]] = None


def _yaml_models() -> Dict[str, Any]:
    """``models:`` block from config.yaml, read once and cached.

    A missing or malformed file is not an error: the catalogue defaults
    above are always sufficient to run.
    """
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    _config_cache = {}
    path = os.environ.get('SKILLPILOT_CONFIG', 'config.yaml')
    try:
        import yaml  # Imported lazily: the registry must import without PyYAML.
        with open(path, 'r', encoding='utf-8') as handle:
            loaded = yaml.safe_load(handle) or {}
        models = loaded.get('models')
        if isinstance(models, dict):
            _config_cache = models
    except FileNotFoundError:
        pass
    except Exception as exc:  # pragma: no cover - defensive
        print(f'[model_registry] ignoring unreadable {path}: {exc}')
    return _config_cache


def reload_config() -> None:
    """Drop the cached ``config.yaml`` values (used by the admin UI)."""
    global _config_cache
    _config_cache = None


def _normalise_provider(provider: str) -> str:
    key = (provider or '').strip().lower()
    return PROVIDER_ALIASES.get(key, key)


def get_provider(provider: str) -> Optional[Provider]:
    """The :class:`Provider` for ``provider``, or ``None`` if unknown."""
    return PROVIDERS.get(_normalise_provider(provider))


def list_providers() -> List[str]:
    return list(PROVIDERS)


def default_model(provider: str, *, vision: bool = False) -> Optional[str]:
    """Configured default model for ``provider``.

    ``vision=True`` asks for the model that should handle a request carrying
    an image, which may differ from the text default.
    """
    spec = get_provider(provider)
    if spec is None:
        return None

    env_name = f'SKILLPILOT_MODEL_{spec.key.upper()}'
    override = os.environ.get(env_name)
    if override:
        return spec.aliases.get(override.strip(), override.strip())

    yaml_block = _yaml_models().get(spec.key) or {}
    if isinstance(yaml_block, dict):
        key = 'vision_model' if vision else 'default_model'
        configured = yaml_block.get(key) or yaml_block.get('default_model')
        if isinstance(configured, str) and configured.strip():
            # A deployment sitting on an old config.yaml still lands on a
            # live model rather than a retired identifier.
            return spec.aliases.get(configured.strip(), configured.strip())

    if vision and spec.vision_default:
        return spec.vision_default
    return spec.default


def get_model(provider: str, model_id: str) -> Optional[Model]:
    """Catalogue entry for ``model_id``, or ``None`` if it is not listed.

    A ``None`` result is not a failure — administrators may point the app at a
    model newer than this catalogue. Callers fall back to conservative request
    defaults in that case.
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
    """The identifier to actually send to ``provider``.

    ``requested`` may be ``None`` (use the default), a current identifier
    (used as-is), a retired identifier (mapped through ``aliases``), or an
    identifier this catalogue has never heard of (passed through untouched so
    a newly released model works without a code change).
    """
    spec = get_provider(provider)
    if spec is None:
        return (requested or '').strip() or None

    wanted = (requested or '').strip()
    if not wanted:
        return default_model(provider, vision=vision)

    if wanted in spec.aliases:
        wanted = spec.aliases[wanted]

    entry = get_model(spec.key, wanted)
    if entry is not None and entry.vision is False and vision:
        # Requested model cannot see the attached image; use the vision default.
        return default_model(spec.key, vision=True) or wanted
    return wanted


def available_models(provider: str, *, include_legacy: bool = False) -> List[Dict[str, Any]]:
    """Catalogue for the admin model picker, newest tier first."""
    spec = get_provider(provider)
    if spec is None:
        return []
    return [
        m.as_dict() for m in spec.models
        if include_legacy or not m.legacy
    ]


def fallback_chain(provider: str, model_id: Optional[str] = None) -> List[str]:
    """Models to try, in order, starting with ``model_id``.

    Used when a provider rejects a model outright (retired, not enabled for
    the account, wrong region). Duplicates are removed while keeping order.
    """
    spec = get_provider(provider)
    if spec is None:
        return [model_id] if model_id else []

    chain: List[str] = []
    for candidate in [model_id, default_model(spec.key), *spec.fallbacks]:
        if candidate and candidate not in chain:
            chain.append(candidate)
    return chain


#: Provider error text that means "this model identifier will never work",
#: as opposed to a transient failure worth retrying with the same model.
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
    """True when ``error`` says the model identifier itself is the problem."""
    return bool(_UNAVAILABLE_RE.search(str(error or '')))


def describe(providers: Optional[Iterable[str]] = None,
             *, include_legacy: bool = False) -> Dict[str, Any]:
    """Whole catalogue as JSON, for the admin UI and the public API."""
    keys = list(providers) if providers is not None else list_providers()
    out: Dict[str, Any] = {}
    for key in keys:
        spec = get_provider(key)
        if spec is None:
            continue
        out[spec.key] = {
            'label': spec.label,
            'default_model': default_model(spec.key),
            'vision_model': default_model(spec.key, vision=True),
            'env_vars': list(spec.env_vars),
            'models': available_models(spec.key, include_legacy=include_legacy),
        }
    return out
