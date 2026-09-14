"""English <-> Arabic translation for course and assessment content.

Translation goes through :mod:`app.services.ai_transport` like every other
model call, so it inherits retries, model fallback and the current model
identifier. It used to call ``gpt-4o-mini`` directly with ``temperature`` and
``max_tokens``, all three of which current OpenAI models reject.

Every function degrades to returning its input unchanged when no key is
configured or the model call fails. A page that shows untranslated text is
strictly better than a page that raises.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence

from app.services.ai_transport import AIError, chat_openai_compatible, extract_json

LANGUAGE_NAMES = {'en': 'English', 'ar': 'Arabic'}

#: Translation is a mechanical task, so the cheapest tier is the right one.
#: Named explicitly rather than taken from the default so that switching the
#: platform's chat model does not silently change translation cost.
TRANSLATION_MODEL = 'gpt-5.6-luna'

_SYSTEM_PROMPT = (
    'You are a professional translator working on university course '
    'material.\n'
    '- Translate from {source} into {target}. Preserve meaning, register and '
    'formatting exactly.\n'
    '- Keep code, mathematical notation, URLs, file names and proper nouns in '
    'their original form.\n'
    '- Do not explain, annotate, summarise or answer the content. Return the '
    'translation and nothing else.'
)


def _api_key() -> Optional[str]:
    return os.environ.get('OPENAI_API_KEY') or None


def _language_name(code: str, fallback: str = 'English') -> str:
    return LANGUAGE_NAMES.get((code or '').lower(), fallback)


def _translate(prompt: str, system: str, *, max_tokens: int = 4000) -> Optional[str]:
    """One translation call, or ``None`` if it could not be made."""
    api_key = _api_key()
    if not api_key:
        print('[translation] OPENAI_API_KEY is not set; leaving text untranslated.')
        return None
    try:
        result = chat_openai_compatible(
            'openai',
            api_key=api_key,
            user_text=prompt,
            system=system,
            model=TRANSLATION_MODEL,
            max_tokens=max_tokens,
        )
    except AIError as exc:
        print(f'[translation] {exc.message}')
        return None
    return result.text.strip()


def translate_text(text: str, source_lang: str = 'en',
                   target_lang: str = 'ar') -> str:
    """Translate one string, returning it unchanged on any failure."""
    if not text or not str(text).strip():
        return text

    system = _SYSTEM_PROMPT.format(
        source=_language_name(source_lang),
        target=_language_name(target_lang, 'Arabic'),
    )
    return _translate(str(text), system) or text


def translate_to_arabic(text: str) -> str:
    return translate_text(text, source_lang='en', target_lang='ar')


def translate_to_english(text: str) -> str:
    return translate_text(text, source_lang='ar', target_lang='en')


def translate_course_content(title: str, description: str = None,
                             source_lang: str = 'en') -> Dict[str, str]:
    """Translate a course title and description in one pass."""
    target_lang = 'ar' if source_lang == 'en' else 'en'
    return {
        'title': translate_text(title, source_lang, target_lang) if title else '',
        'description': (translate_text(description, source_lang, target_lang)
                        if description else ''),
    }


def translate_survey_exam_content(questions: Sequence[Dict[str, Any]],
                                  source_lang: str = 'en') -> List[Dict[str, Any]]:
    """Translate question text and options, one batch per question set.

    Each question used to cost one API call per field, so a 40-question exam
    with four options each was 200 round trips. Collecting the strings into a
    single batch makes it one.
    """
    if not questions:
        return []

    target_lang = 'ar' if source_lang == 'en' else 'en'

    # Collect every translatable string, remembering where it came from.
    strings: List[str] = []
    slots: List[tuple] = []
    for index, question in enumerate(questions):
        for field in ('text', 'question_text'):
            value = question.get(field)
            if isinstance(value, str) and value.strip():
                slots.append((index, field, None))
                strings.append(value)
        options = question.get('options')
        if isinstance(options, list):
            for position, option in enumerate(options):
                if isinstance(option, str) and option.strip():
                    slots.append((index, 'options', position))
                    strings.append(option)

    translations = batch_translate(strings, source_lang, target_lang)

    out = [dict(question) for question in questions]
    for (index, field, position), translated in zip(slots, translations):
        if field == 'options':
            bucket = out[index].setdefault(
                'options_translated', [''] * len(questions[index]['options']))
            bucket[position] = translated
        else:
            out[index][f'{field}_translated'] = translated
    return out


def batch_translate(texts: Sequence[str], source_lang: str = 'en',
                    target_lang: str = 'ar') -> List[str]:
    """Translate many strings in one call, preserving order.

    Falls back to the untranslated input rather than to one call per string:
    a failure usually means no key or a provider outage, and firing hundreds
    of individual requests into that makes it worse.
    """
    items = list(texts or [])
    if not items:
        return []

    system = (
        _SYSTEM_PROMPT.format(
            source=_language_name(source_lang),
            target=_language_name(target_lang, 'Arabic'),
        )
        + '\n\nYou will receive a JSON array of strings. Return a JSON array '
          'of exactly the same length, in the same order, containing only the '
          'translations. Return the array alone, with no prose and no code '
          'fence.'
    )
    prompt = json.dumps(items, ensure_ascii=False)

    raw = _translate(prompt, system, max_tokens=min(16000, 200 + len(prompt) * 3))
    if raw is None:
        return items

    parsed = extract_json(raw, expect='array')
    if parsed is None or len(parsed) != len(items):
        print(f'[translation] expected {len(items)} translations, '
              f'got {len(parsed) if parsed is not None else "unparseable output"}; '
              'leaving the batch untranslated.')
        return items
    return [str(value) for value in parsed]


def auto_translate_model_fields(model_instance, fields_mapping: Dict[str, str]):
    """Fill empty Arabic columns from their English counterparts.

    ``fields_mapping`` maps source field to target field, e.g.
    ``{'title': 'title_ar', 'description': 'description_ar'}``. A target that
    already has a value is left alone, so a human translation is never
    overwritten.
    """
    for source_field, target_field in fields_mapping.items():
        source_value = getattr(model_instance, source_field, None)
        if source_value and not getattr(model_instance, target_field, None):
            setattr(model_instance, target_field, translate_to_arabic(source_value))
    return model_instance
