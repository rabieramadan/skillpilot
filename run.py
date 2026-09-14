#!/usr/bin/env python3
"""Development entry point.

``python run.py`` starts the Flask development server. For production use
``serve.py``, which runs the same app under Waitress.
"""

import os

import requests

from app import create_app
from config.config import Config

#: Endpoints that only enumerate models. They cost nothing, so the startup
#: check never spends tokens confirming that a key works. Providers without
#: such an endpoint are reported as configured but not verified, which is
#: more honest than billing the institution on every restart.
CREDENTIAL_CHECKS = (
    ('OpenAI', 'OPENAI_API_KEY',
     'https://api.openai.com/v1/models',
     lambda key: {'Authorization': f'Bearer {key}'}),
    ('Claude', 'CLAUDE_API_KEY',
     'https://api.anthropic.com/v1/models',
     lambda key: {'x-api-key': key, 'anthropic-version': '2023-06-01'}),
    ('Gemini', 'GEMINI_API_KEY',
     'https://generativelanguage.googleapis.com/v1beta/models',
     lambda key: {'x-goog-api-key': key}),
    ('Grok', 'GROK_API_KEY',
     'https://api.x.ai/v1/models',
     lambda key: {'Authorization': f'Bearer {key}'}),
    ('DeepSeek', 'DEEPSEEK_API_KEY',
     'https://api.deepseek.com/models',
     lambda key: {'Authorization': f'Bearer {key}'}),
)

#: Reachable only through a billed request, so they are not probed.
UNVERIFIED_PROVIDERS = (
    ('Perplexity', 'PERPLEXITY_API_KEY'),
    ('Dify', 'DIFY_API_KEY'),
    ('HeyGen', 'HEYGEN_API_KEY'),
    ('Bedrock', 'BEDROCK_API_KEY'),
)


def check_api_connectivity(timeout: float = 8.0) -> None:
    """Report which AI providers are configured and reachable.

    Never prints any part of a key: a startup banner ends up in log
    aggregators and terminal scrollback, and a key prefix is enough to
    identify an account.
    """
    config = Config()
    print('\n' + '=' * 60)
    print('AI provider status')
    print('=' * 60)

    from app.services import model_registry as registry

    for name, attribute, url, headers in CREDENTIAL_CHECKS:
        key = getattr(config, attribute, None)
        if not key:
            print(f'  -  {name:12} no API key configured')
            continue

        provider_key = name.lower()
        model = registry.default_model(provider_key) or 'n/a'
        try:
            response = requests.get(url, headers=headers(key), timeout=timeout)
        except requests.Timeout:
            print(f'  ?  {name:12} timed out after {timeout:.0f}s')
            continue
        except requests.RequestException as exc:
            print(f'  x  {name:12} unreachable: {str(exc)[:80]}')
            continue

        if response.status_code in (200, 201):
            print(f'  OK {name:12} reachable, default model {model}')
        elif response.status_code in (401, 403):
            print(f'  x  {name:12} key rejected (HTTP {response.status_code})')
        else:
            print(f'  ?  {name:12} unexpected HTTP {response.status_code}')

    for name, attribute in UNVERIFIED_PROVIDERS:
        configured = bool(getattr(config, attribute, None))
        state = 'configured (not verified)' if configured else 'no API key configured'
        print(f'  {"-" if not configured else "."}  {name:12} {state}')

    print('=' * 60 + '\n')


app = create_app()


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    print(f'Starting SkillPilot on http://{host}:{port}')
    print('Configure API keys in .env (see .env.example).')

    # Opt-in: the check makes one network request per configured provider.
    if os.environ.get('SKILLPILOT_STARTUP_CHECK', '1') != '0':
        check_api_connectivity()

    app.run(host=host, port=port, debug=debug)
