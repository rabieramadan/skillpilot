"""Transport layer for every AI provider SkillPilot talks to.

This module owns the mechanics of a model call — building the request, sending
it, retrying, and turning the answer into one shape — so that the rest of the
application never touches an HTTP body or an SDK response object.

What it guarantees to callers:

* **One response shape.** Every function returns a :class:`ChatResult`, or
  raises :class:`AIError` with a message fit to show a user. No caller has to
  know that OpenAI nests text under ``choices[0].message.content`` while
  Anthropic returns a list of content blocks.
* **Retries that distinguish causes.** Rate limits, timeouts and 5xx are
  retried with exponential backoff and jitter. A bad key or a malformed
  request is not — retrying those just wastes the user's time.
* **Model fallback.** When a provider says the model identifier itself is
  gone, the next model from
  :func:`app.services.model_registry.fallback_chain` is tried and the
  substitution is reported on the result, instead of surfacing a 404.
* **Capability-aware requests.** ``temperature`` and ``max_tokens`` are sent
  only in the form the target model accepts. Current reasoning models reject
  both spellings used by their predecessors.

Everything here is synchronous and stateless apart from a shared
``requests`` session, so it is safe to call from Flask request handlers.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

import requests

from app.services import model_registry as registry

__all__ = [
    'AIError',
    'Attachment',
    'ChatResult',
    'build_attachments',
    'chat_anthropic',
    'chat_gemini',
    'chat_openai_compatible',
    'generate_image',
]

# Anthropic sends this header to pin the wire format; it is independent of the
# model version and only changes when the request shape itself changes.
ANTHROPIC_API_VERSION = '2023-06-01'

DEFAULT_TIMEOUT = 120
#: Search-grounded and deep-research models routinely exceed the normal budget.
LONG_TIMEOUT = 300
MAX_ATTEMPTS = 3

#: Largest amount of extracted document text attached to a single request.
#: Modern context windows are measured in millions of tokens, so the old
#: 5-8k character caps were throwing away most of a lecture PDF.
MAX_DOCUMENT_CHARS = 120_000
#: Cap for one attachment, so a single huge file cannot crowd out the rest.
MAX_CHARS_PER_FILE = 60_000
#: Images are sent inline as base64; anything larger is refused rather than
#: silently truncated into an invalid payload.
MAX_IMAGE_BYTES = 5 * 1024 * 1024


class AIError(Exception):
    """A model call failed.

    ``message`` is safe to show to an end user: it never contains the API key
    and never contains a raw provider payload.
    """

    def __init__(self, message: str, *, provider: str = '', status: Optional[int] = None,
                 retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status = status
        self.retryable = retryable


@dataclass
class Attachment:
    """One uploaded file, already read and normalised for any provider."""

    name: str
    #: ``'image'`` — sent as an image part to models that can see;
    #: ``'text'``  — sent as text, having been extracted from the document.
    kind: str
    mime_type: str = 'application/octet-stream'
    text: str = ''
    data: bytes = b''

    @property
    def is_image(self) -> bool:
        return self.kind == 'image'

    def as_text_block(self) -> str:
        return (
            f'\n\n--- File: {self.name} ({self.mime_type}) ---\n'
            f'{self.text}\n--- end of {self.name} ---'
        )


@dataclass
class ChatResult:
    """A successful answer from any provider."""

    text: str
    provider: str
    model: str
    usage: Dict[str, Any] = field(default_factory=dict)
    citations: List[str] = field(default_factory=list)
    #: Set when the requested model was unavailable and another one answered.
    fallback_from: Optional[str] = None
    finish_reason: str = ''
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def as_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            'text': self.text,
            'provider': self.provider,
            'model': self.model,
            'timestamp': self.timestamp,
        }
        if self.usage:
            payload['usage'] = self.usage
        if self.citations:
            payload['citations'] = self.citations
        if self.fallback_from:
            payload['fallback_from'] = self.fallback_from
        if self.finish_reason:
            payload['finish_reason'] = self.finish_reason
        return payload


# ---------------------------------------------------------------------------
# Shared HTTP
# ---------------------------------------------------------------------------

_session_lock = threading.Lock()
_session: Optional[requests.Session] = None


def _http() -> requests.Session:
    """Process-wide session, so connections are reused across requests."""
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                session = requests.Session()
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=10, pool_maxsize=20, max_retries=0,
                )
                session.mount('https://', adapter)
                session.mount('http://', adapter)
                _session = session
    return _session


def _sleep_for_attempt(attempt: int, retry_after: Optional[str] = None) -> None:
    """Back off before the next attempt.

    A provider-supplied ``Retry-After`` wins; otherwise exponential backoff
    with jitter, so that a burst of simultaneous requests does not retry in
    lockstep.
    """
    if retry_after:
        try:
            time.sleep(min(float(retry_after), 30.0))
            return
        except (TypeError, ValueError):
            pass
    time.sleep(min(2 ** attempt, 8) + random.uniform(0, 0.5))


def _status_is_retryable(status: int) -> bool:
    return status == 408 or status == 409 or status == 429 or status >= 500


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

def build_attachments(paths: Optional[Sequence[str]]) -> List[Attachment]:
    """Read uploaded files once, into a provider-independent form.

    Images are kept as bytes for models that accept them. Everything else is
    reduced to text through :class:`app.utils.file_handler.FileHandler`, which
    knows about PDF, DOCX, XLSX and the rest. A file that cannot be read
    becomes a short note in the prompt rather than an exception, because one
    unreadable attachment should not fail the whole question.
    """
    attachments: List[Attachment] = []
    if not paths:
        return attachments

    budget = MAX_DOCUMENT_CHARS
    for path in paths:
        if not path or not os.path.exists(path):
            continue
        name = os.path.basename(path)
        mime_type, _ = mimetypes.guess_type(path)
        mime_type = mime_type or 'application/octet-stream'

        if mime_type.startswith('image/'):
            try:
                size = os.path.getsize(path)
                if size > MAX_IMAGE_BYTES:
                    attachments.append(Attachment(
                        name=name, kind='text', mime_type=mime_type,
                        text=f'[Image {name} is {size // 1024} KB, which is too '
                             f'large to send. Ask the user for a smaller copy.]',
                    ))
                    continue
                with open(path, 'rb') as handle:
                    attachments.append(Attachment(
                        name=name, kind='image', mime_type=mime_type,
                        data=handle.read(),
                    ))
            except OSError as exc:
                attachments.append(Attachment(
                    name=name, kind='text', mime_type=mime_type,
                    text=f'[Could not read image {name}: {exc}]',
                ))
            continue

        text = _extract_text(path, mime_type)
        if budget <= 0:
            attachments.append(Attachment(
                name=name, kind='text', mime_type=mime_type,
                text=f'[{name} was not included: the attached documents '
                     f'already fill the context budget.]',
            ))
            continue
        allowance = min(MAX_CHARS_PER_FILE, budget)
        if len(text) > allowance:
            text = text[:allowance] + f'\n[... {name} truncated at {allowance} characters ...]'
        budget -= len(text)
        attachments.append(Attachment(
            name=name, kind='text', mime_type=mime_type, text=text,
        ))

    return attachments


def _extract_text(path: str, mime_type: str) -> str:
    name = os.path.basename(path)
    plain = (
        mime_type.startswith('text/')
        or mime_type in ('application/json', 'application/xml', 'application/x-yaml')
    )
    try:
        if plain:
            with open(path, 'r', encoding='utf-8', errors='replace') as handle:
                return handle.read()
        from app.utils.file_handler import FileHandler
        return FileHandler.extract_text(path) or f'[{name} appears to be empty.]'
    except Exception as exc:  # noqa: BLE001 - one bad file must not fail the call
        return f'[Could not extract text from {name} ({mime_type}): {exc}]'


def _text_attachment_block(attachments: Iterable[Attachment]) -> str:
    blocks = [a.as_text_block() for a in attachments if not a.is_image and a.text]
    if not blocks:
        return ''
    return (
        '\n\n=== ATTACHED FILES ===\n'
        'The user attached the following files. Use them as the primary source '
        'and cite the file name when you rely on one.'
        + ''.join(blocks)
    )


def _normalise_history(history: Optional[Sequence[Dict[str, Any]]],
                       limit: int = 20) -> List[Dict[str, str]]:
    """Trim history to alternating user/assistant turns the APIs accept.

    Providers reject empty content and unknown roles, and Anthropic in
    particular rejects two consecutive turns with the same role. Cleaning this
    up here means every adapter gets a sequence it can send as-is.
    """
    cleaned: List[Dict[str, str]] = []
    for entry in (history or [])[-limit:]:
        if not isinstance(entry, dict):
            continue
        role = str(entry.get('role') or 'user').lower()
        if role in ('bot', 'ai', 'model'):
            role = 'assistant'
        if role not in ('user', 'assistant'):
            continue
        content = entry.get('content')
        if not isinstance(content, str):
            content = '' if content is None else str(content)
        content = content.strip()
        if not content:
            continue
        if cleaned and cleaned[-1]['role'] == role:
            # Merge same-role turns rather than dropping one.
            cleaned[-1]['content'] += '\n\n' + content
            continue
        cleaned.append({'role': role, 'content': content})

    # Anthropic requires the first message to come from the user.
    while cleaned and cleaned[0]['role'] != 'user':
        cleaned.pop(0)
    return cleaned


# ---------------------------------------------------------------------------
# OpenAI-compatible providers (OpenAI, xAI Grok, DeepSeek, Perplexity)
# ---------------------------------------------------------------------------

def chat_openai_compatible(
    provider: str,
    *,
    api_key: str,
    user_text: str,
    system: Optional[str] = None,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    attachments: Optional[Sequence[Attachment]] = None,
    model: Optional[str] = None,
    max_tokens: int = 4000,
    temperature: float = 0.7,
    timeout: Optional[int] = None,
    extra_body: Optional[Dict[str, Any]] = None,
) -> ChatResult:
    """Call any provider that speaks the OpenAI ``/chat/completions`` shape."""
    spec = registry.get_provider(provider)
    base_url = registry.OPENAI_COMPATIBLE_BASE_URLS.get(
        spec.key if spec else provider
    )
    if base_url is None:
        raise AIError(f'{provider} is not an OpenAI-compatible provider.',
                      provider=provider)
    if not api_key:
        raise AIError(f'No API key configured for {spec.label if spec else provider}.',
                      provider=provider)

    attachments = list(attachments or [])
    has_image = any(a.is_image for a in attachments)
    wanted = registry.resolve(provider, model, vision=has_image)
    timeout = timeout or (LONG_TIMEOUT if provider == 'perplexity' else DEFAULT_TIMEOUT)

    prompt = (user_text or '').strip()
    prompt += _text_attachment_block(attachments)

    tried: List[str] = []
    last_error: Optional[AIError] = None

    for candidate in registry.fallback_chain(provider, wanted):
        if candidate in tried:
            continue
        tried.append(candidate)
        entry = registry.get_model(provider, candidate)
        content = _openai_content(prompt, attachments, entry)
        messages: List[Dict[str, Any]] = []
        if system:
            messages.append({'role': 'system', 'content': system})
        messages.extend(_normalise_history(history))
        messages.append({'role': 'user', 'content': content})

        payload: Dict[str, Any] = {'model': candidate, 'messages': messages}
        payload.update(_openai_limit_kwargs(entry, max_tokens, temperature))
        if provider == 'perplexity':
            payload['return_citations'] = True
        if extra_body:
            payload.update(extra_body)

        try:
            body = _post_json(
                f'{base_url}/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                payload=payload,
                provider=provider,
                timeout=timeout,
            )
        except AIError as exc:
            last_error = exc
            if registry.is_model_unavailable_error(exc.message):
                continue  # Try the next model in the chain.
            raise

        return _parse_openai_response(
            body, provider=provider, model=candidate,
            fallback_from=wanted if candidate != wanted else None,
        )

    raise last_error or AIError(
        f'No usable model for {provider}. Tried: {", ".join(tried)}.',
        provider=provider,
    )


def _openai_content(prompt: str, attachments: Sequence[Attachment],
                    entry: Optional[registry.Model]) -> Any:
    """Message content: a plain string, or parts when images are attached."""
    images = [a for a in attachments if a.is_image]
    if not images:
        return prompt
    if entry is not None and not entry.vision:
        note = ', '.join(a.name for a in images)
        return f'{prompt}\n\n[Note: {note} could not be shown to this model, ' \
               f'which does not accept images.]'

    parts: List[Dict[str, Any]] = [{'type': 'text', 'text': prompt}]
    for image in images:
        encoded = base64.b64encode(image.data).decode('ascii')
        parts.append({
            'type': 'image_url',
            'image_url': {'url': f'data:{image.mime_type};base64,{encoded}'},
        })
    return parts


def _openai_limit_kwargs(entry: Optional[registry.Model], max_tokens: int,
                         temperature: float) -> Dict[str, Any]:
    """Token limit and sampling arguments in the form the model accepts.

    GPT-5.6 and GPT-6 take ``max_completion_tokens`` and reject ``temperature``
    outright; older and third-party models still take ``max_tokens`` plus a
    temperature. Sending the wrong pair is a 400, not a warning.
    """
    if entry is None:
        # Unknown to the catalogue — use the widely accepted spelling.
        return {'max_tokens': max_tokens, 'temperature': temperature}

    limit = min(max_tokens, entry.max_output_tokens or max_tokens)
    kwargs: Dict[str, Any] = (
        {'max_completion_tokens': limit} if entry.max_completion_tokens
        else {'max_tokens': limit}
    )
    if entry.sampling:
        kwargs['temperature'] = temperature
    return kwargs


def _parse_openai_response(body: Dict[str, Any], *, provider: str, model: str,
                           fallback_from: Optional[str]) -> ChatResult:
    choices = body.get('choices') or []
    if not choices:
        raise AIError(f'{provider} returned no answer.', provider=provider)

    message = (choices[0] or {}).get('message') or {}
    text = message.get('content')
    if isinstance(text, list):
        # Some providers mirror the multi-part request shape in the response.
        text = ''.join(
            part.get('text', '') for part in text if isinstance(part, dict)
        )
    text = (text or '').strip()

    finish = str(choices[0].get('finish_reason') or '')
    if not text:
        if finish == 'length':
            raise AIError(
                f'{provider} hit its output limit before writing an answer. '
                'Shorten the question or raise the token limit.',
                provider=provider,
            )
        if finish == 'content_filter':
            raise AIError(f'{provider} declined to answer this request.',
                          provider=provider)
        raise AIError(f'{provider} returned an empty answer.', provider=provider)

    citations = [
        c if isinstance(c, str) else str(c.get('url', c))
        for c in (body.get('citations') or body.get('search_results') or [])
    ][:10]
    if citations:
        text += '\n\n**Sources:**\n' + '\n'.join(
            f'{i}. {c}' for i, c in enumerate(citations, 1)
        )

    return ChatResult(
        text=text,
        provider=provider,
        model=body.get('model') or model,
        usage=body.get('usage') or {},
        citations=citations,
        fallback_from=fallback_from,
        finish_reason=finish,
    )


def _post_json(url: str, *, headers: Dict[str, str], payload: Dict[str, Any],
               provider: str, timeout: int) -> Dict[str, Any]:
    """POST JSON with retries, translating failures into :class:`AIError`."""
    last: Optional[AIError] = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = _http().post(url, headers=headers, json=payload, timeout=timeout)
        except requests.Timeout:
            last = AIError(f'{provider} did not respond within {timeout}s.',
                           provider=provider, retryable=True)
        except requests.RequestException as exc:
            last = AIError(f'Could not reach {provider}: {exc}',
                           provider=provider, retryable=True)
        else:
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError as exc:
                    raise AIError(f'{provider} returned a malformed response: {exc}',
                                  provider=provider) from exc

            detail = _error_detail(response)
            if response.status_code in (401, 403):
                raise AIError(
                    f'{provider} rejected the API key. Check it in '
                    f'Admin > AI Settings. ({detail})',
                    provider=provider, status=response.status_code,
                )
            if not _status_is_retryable(response.status_code):
                raise AIError(f'{provider} error {response.status_code}: {detail}',
                              provider=provider, status=response.status_code)
            last = AIError(f'{provider} error {response.status_code}: {detail}',
                           provider=provider, status=response.status_code,
                           retryable=True)
            if attempt < MAX_ATTEMPTS - 1:
                _sleep_for_attempt(attempt, response.headers.get('Retry-After'))
                continue

        if attempt < MAX_ATTEMPTS - 1:
            _sleep_for_attempt(attempt)

    raise last or AIError(f'{provider} request failed.', provider=provider)


def _error_detail(response: requests.Response) -> str:
    """Readable one-liner from a provider error body."""
    try:
        body = response.json()
    except (ValueError, json.JSONDecodeError):
        return (response.text or '')[:300]
    error = body.get('error') if isinstance(body, dict) else None
    if isinstance(error, dict):
        return str(error.get('message') or error)[:300]
    if isinstance(error, str):
        return error[:300]
    return json.dumps(body)[:300]


# ---------------------------------------------------------------------------
# Anthropic Claude
# ---------------------------------------------------------------------------

def chat_anthropic(
    *,
    api_key: str,
    user_text: str,
    system: Optional[str] = None,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    attachments: Optional[Sequence[Attachment]] = None,
    model: Optional[str] = None,
    max_tokens: int = 4000,
    temperature: float = 0.7,
    timeout: Optional[int] = None,
) -> ChatResult:
    """Call Claude through the official Anthropic SDK."""
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise AIError('The anthropic package is not installed. '
                      'Run: pip install -r requirements.txt',
                      provider='claude') from exc
    if not api_key:
        raise AIError('No API key configured for Anthropic Claude.', provider='claude')

    attachments = list(attachments or [])
    has_image = any(a.is_image for a in attachments)
    wanted = registry.resolve('claude', model, vision=has_image)

    prompt = (user_text or '').strip() + _text_attachment_block(attachments)
    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=timeout or DEFAULT_TIMEOUT,
        # The SDK's own retry loop already handles 429/5xx/connection errors.
        max_retries=MAX_ATTEMPTS - 1,
    )

    tried: List[str] = []
    last_error: Optional[AIError] = None

    for candidate in registry.fallback_chain('claude', wanted):
        if candidate in tried:
            continue
        tried.append(candidate)
        entry = registry.get_model('claude', candidate)

        content: List[Dict[str, Any]] = []
        if has_image and (entry is None or entry.vision):
            for image in (a for a in attachments if a.is_image):
                content.append({
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': image.mime_type,
                        'data': base64.b64encode(image.data).decode('ascii'),
                    },
                })
        content.append({'type': 'text', 'text': prompt})

        messages = [
            {'role': m['role'], 'content': m['content']}
            for m in _normalise_history(history)
        ]
        messages.append({'role': 'user', 'content': content})

        params: Dict[str, Any] = {
            'model': candidate,
            'max_tokens': min(max_tokens, entry.max_output_tokens) if entry else max_tokens,
            'messages': messages,
        }
        if system:
            params['system'] = system
        # Claude 5 and the 4.6+ family reject temperature outright; only the
        # models the catalogue marks as accepting it get one.
        if entry is None or entry.sampling:
            params['temperature'] = temperature

        try:
            response = client.messages.create(**params)
        except anthropic.NotFoundError:
            last_error = AIError(f'Claude model {candidate} is not available '
                                 'for this account.', provider='claude', status=404)
            continue
        except anthropic.AuthenticationError as exc:
            raise AIError('Anthropic rejected the API key. Check it in '
                          'Admin > AI Settings.', provider='claude', status=401) from exc
        except anthropic.PermissionDeniedError as exc:
            raise AIError('This Anthropic key is not allowed to use '
                          f'{candidate}.', provider='claude', status=403) from exc
        except anthropic.BadRequestError as exc:
            detail = str(exc)
            if registry.is_model_unavailable_error(detail):
                last_error = AIError(detail, provider='claude', status=400)
                continue
            raise AIError(f'Anthropic rejected the request: {detail[:300]}',
                          provider='claude', status=400) from exc
        except anthropic.APIStatusError as exc:
            raise AIError(f'Anthropic error {exc.status_code}: {str(exc)[:300]}',
                          provider='claude', status=exc.status_code) from exc
        except anthropic.APIConnectionError as exc:
            raise AIError(f'Could not reach Anthropic: {exc}',
                          provider='claude', retryable=True) from exc

        return _parse_anthropic_response(
            response, model=candidate,
            fallback_from=wanted if candidate != wanted else None,
        )

    raise last_error or AIError(
        f'No usable Claude model. Tried: {", ".join(tried)}.', provider='claude')


def _parse_anthropic_response(response: Any, *, model: str,
                              fallback_from: Optional[str]) -> ChatResult:
    """Join every text block in the reply.

    Reading ``response.content[0].text`` — which this code used to do — breaks
    the moment the response starts with a thinking or tool-use block, which
    current Claude models routinely do.
    """
    stop_reason = getattr(response, 'stop_reason', '') or ''
    if stop_reason == 'refusal':
        raise AIError('Claude declined to answer this request.', provider='claude')

    chunks: List[str] = []
    for block in getattr(response, 'content', None) or []:
        if getattr(block, 'type', None) == 'text':
            chunks.append(getattr(block, 'text', '') or '')
    text = ''.join(chunks).strip()

    if not text:
        if stop_reason == 'max_tokens':
            raise AIError('Claude hit its output limit before writing an answer. '
                          'Shorten the question or raise the token limit.',
                          provider='claude')
        raise AIError('Claude returned an empty answer.', provider='claude')

    usage = getattr(response, 'usage', None)
    usage_dict: Dict[str, Any] = {}
    if usage is not None:
        usage_dict = {
            'prompt_tokens': getattr(usage, 'input_tokens', None),
            'completion_tokens': getattr(usage, 'output_tokens', None),
        }
        usage_dict = {k: v for k, v in usage_dict.items() if v is not None}

    return ChatResult(
        text=text,
        provider='claude',
        model=getattr(response, 'model', None) or model,
        usage=usage_dict,
        fallback_from=fallback_from,
        finish_reason=stop_reason,
    )


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------

def chat_gemini(
    *,
    api_key: str,
    user_text: str,
    system: Optional[str] = None,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    attachments: Optional[Sequence[Attachment]] = None,
    model: Optional[str] = None,
    max_tokens: int = 4000,
    temperature: float = 0.7,
    timeout: Optional[int] = None,
) -> ChatResult:
    """Call Gemini through the unified Google Gen AI SDK.

    The old ``google-generativeai`` package reached end of life in November
    2025 and cannot reach the Gemini 3 family at all, so this uses
    ``google-genai`` (``from google import genai``).
    """
    try:
        from google import genai
        from google.genai import errors as genai_errors
        from google.genai import types as genai_types
    except ImportError as exc:
        raise AIError('The google-genai package is not installed. '
                      'Run: pip install -r requirements.txt',
                      provider='gemini') from exc
    if not api_key:
        raise AIError('No API key configured for Google Gemini.', provider='gemini')

    attachments = list(attachments or [])
    has_image = any(a.is_image for a in attachments)
    wanted = registry.resolve('gemini', model, vision=has_image)

    prompt = (user_text or '').strip() + _text_attachment_block(attachments)
    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(
            timeout=(timeout or DEFAULT_TIMEOUT) * 1000,  # milliseconds
        ),
    )

    tried: List[str] = []
    last_error: Optional[AIError] = None

    for candidate in registry.fallback_chain('gemini', wanted):
        if candidate in tried:
            continue
        tried.append(candidate)
        entry = registry.get_model('gemini', candidate)

        contents: List[Any] = []
        for turn in _normalise_history(history):
            contents.append(genai_types.Content(
                # Gemini names the assistant role 'model'.
                role='model' if turn['role'] == 'assistant' else 'user',
                parts=[genai_types.Part.from_text(text=turn['content'])],
            ))

        parts = [genai_types.Part.from_text(text=prompt)]
        if has_image and (entry is None or entry.vision):
            for image in (a for a in attachments if a.is_image):
                parts.append(genai_types.Part.from_bytes(
                    data=image.data, mime_type=image.mime_type,
                ))
        contents.append(genai_types.Content(role='user', parts=parts))

        config_kwargs: Dict[str, Any] = {
            'max_output_tokens': min(max_tokens, entry.max_output_tokens) if entry else max_tokens,
        }
        if system:
            config_kwargs['system_instruction'] = system
        # Gemini 3 ignores temperature/top_p; only send it where it still means
        # something, so the request reflects what will actually happen.
        if entry is None or entry.sampling:
            config_kwargs['temperature'] = temperature

        try:
            response = client.models.generate_content(
                model=candidate,
                contents=contents,
                config=genai_types.GenerateContentConfig(**config_kwargs),
            )
        except genai_errors.ClientError as exc:
            detail = str(exc)
            if exc.code == 404 or registry.is_model_unavailable_error(detail):
                last_error = AIError(f'Gemini model {candidate} is not available '
                                     'for this key.', provider='gemini', status=404)
                continue
            if exc.code in (401, 403):
                raise AIError('Google rejected the API key. Check it in '
                              'Admin > AI Settings.',
                              provider='gemini', status=exc.code) from exc
            raise AIError(f'Gemini rejected the request: {detail[:300]}',
                          provider='gemini', status=exc.code) from exc
        except genai_errors.ServerError as exc:
            raise AIError(f'Gemini is unavailable right now: {str(exc)[:200]}',
                          provider='gemini', retryable=True) from exc
        except genai_errors.APIError as exc:
            raise AIError(f'Gemini error: {str(exc)[:300]}', provider='gemini') from exc

        return _parse_gemini_response(
            response, model=candidate,
            fallback_from=wanted if candidate != wanted else None,
        )

    raise last_error or AIError(
        f'No usable Gemini model. Tried: {", ".join(tried)}.', provider='gemini')


def _parse_gemini_response(response: Any, *, model: str,
                           fallback_from: Optional[str]) -> ChatResult:
    text = (getattr(response, 'text', None) or '').strip()
    candidates = getattr(response, 'candidates', None) or []
    finish = ''
    if candidates:
        reason = getattr(candidates[0], 'finish_reason', None)
        # The SDK returns an enum; str() on it yields 'FinishReason.STOP'.
        finish = getattr(reason, 'name', None) or str(reason or '')

    if not text:
        feedback = getattr(response, 'prompt_feedback', None)
        blocked = getattr(feedback, 'block_reason', None) if feedback else None
        if blocked:
            raise AIError(f'Gemini blocked this request ({blocked}).',
                          provider='gemini')
        if 'MAX_TOKENS' in finish:
            raise AIError('Gemini hit its output limit before writing an answer. '
                          'Shorten the question or raise the token limit.',
                          provider='gemini')
        if 'SAFETY' in finish:
            raise AIError('Gemini declined to answer this request.', provider='gemini')
        raise AIError('Gemini returned an empty answer.', provider='gemini')

    usage_dict: Dict[str, Any] = {}
    usage = getattr(response, 'usage_metadata', None)
    if usage is not None:
        usage_dict = {
            'prompt_tokens': getattr(usage, 'prompt_token_count', None),
            'completion_tokens': getattr(usage, 'candidates_token_count', None),
            'total_tokens': getattr(usage, 'total_token_count', None),
        }
        usage_dict = {k: v for k, v in usage_dict.items() if v is not None}

    return ChatResult(
        text=text,
        provider='gemini',
        model=getattr(response, 'model_version', None) or model,
        usage=usage_dict,
        fallback_from=fallback_from,
        finish_reason=finish,
    )


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------

def generate_image(
    *,
    api_key: str,
    prompt: str,
    model: Optional[str] = None,
    size: str = '1024x1024',
    quality: str = 'high',
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate one image and return it as raw bytes plus the model used.

    The DALL-E endpoints were shut down on 12 May 2026; the registry maps
    ``dall-e-2`` / ``dall-e-3`` onto the GPT Image models that replaced them,
    so saved presets keep working.
    """
    if not api_key:
        raise AIError('No OpenAI API key configured for image generation.',
                      provider='images')
    if not (prompt or '').strip():
        raise AIError('An image prompt is required.', provider='images')

    wanted = registry.resolve('images', model)
    tried: List[str] = []
    last_error: Optional[AIError] = None

    for candidate in registry.fallback_chain('images', wanted):
        if candidate in tried:
            continue
        tried.append(candidate)
        payload = {
            'model': candidate,
            'prompt': prompt.strip(),
            'n': 1,
            'size': size,
            'quality': quality,
        }
        try:
            body = _post_json(
                'https://api.openai.com/v1/images/generations',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                payload=payload,
                provider='images',
                timeout=timeout or LONG_TIMEOUT,
            )
        except AIError as exc:
            last_error = exc
            if registry.is_model_unavailable_error(exc.message) or 'quality' in exc.message:
                continue
            raise

        data = (body.get('data') or [{}])[0]
        encoded = data.get('b64_json')
        if not encoded:
            # The GPT Image models always return base64; a URL means an older
            # deployment or a proxy, so follow it once.
            url = data.get('url')
            if not url:
                raise AIError('The image API returned no image.', provider='images')
            try:
                fetched = _http().get(url, timeout=timeout or LONG_TIMEOUT)
                fetched.raise_for_status()
                image_bytes = fetched.content
            except requests.RequestException as exc:
                raise AIError(f'Could not download the generated image: {exc}',
                              provider='images') from exc
        else:
            image_bytes = base64.b64decode(encoded)

        return {
            'image_bytes': image_bytes,
            'model': candidate,
            'revised_prompt': data.get('revised_prompt', ''),
            'fallback_from': wanted if candidate != wanted else None,
            'usage': body.get('usage') or {},
        }

    raise last_error or AIError(
        f'No usable image model. Tried: {", ".join(tried)}.', provider='images')
