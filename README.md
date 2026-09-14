# SkillPilot

An AI-powered learning management system built with Flask and PostgreSQL:
courses, exams, surveys, certificates and an adaptive tutor, in English and
Arabic, across superadmin / admin / teacher / student roles.

Eight AI providers are supported. Every feature that talks to a model goes
through one gateway, so adding a provider or switching a default is a
configuration change rather than a code change.

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip

cp .env.example .env                           # then fill in the values
python run.py                                  # development, port 5000
```

For production use `serve.py`, which runs the same app under Waitress:

```bash
python serve.py --port 5000 --threads 8
```

`docs/DEPLOYMENT.md` covers the multi-worker Windows and nginx setup,
`docs/ARCHITECTURE.md` the application structure, and `docs/PYCHARM.md` local
IDE configuration.

## Configuration

Settings resolve in this order, highest first:

1. environment variables, loaded from `.env` (falling back to `.env.server`)
2. `config.yaml`
3. the defaults in `config/config.py` and `app/services/model_registry.py`

`.env` holds the secrets and is never committed — `.env.example` lists every
variable the application reads. `config.yaml` holds everything else and is
safe to commit; leave its `api_keys` block empty.

Required for a working install:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql://user:password@host:5432/skillpilot` |
| `SECRET_KEY` | Session signing. 64 random hex characters. Without it sessions do not survive a restart and do not work across workers. |
| `ADMIN_PASSWORD` | Super-admin login. Empty (the default) disables password-only super-admin access. |

At least one AI provider key is needed for the AI features; the platform
enables only the providers that have one.

## AI models

`app/services/model_registry.py` is the single source of truth for every model
the platform can call. It holds, per provider, the current model identifiers
and their capabilities, an alias table mapping retired identifiers onto their
replacements, fallback chains, and published pricing.

This matters because providers retire models on their own schedules. The
alias table means a model chosen a year ago and stored in the database still
resolves to something callable; the fallback chain means a retirement that
happens between releases degrades to the next model instead of showing a
student a 404.

To change the default model for a provider, in increasing order of
permanence:

```bash
# 1. Per deployment
SKILLPILOT_MODEL_OPENAI=gpt-6-astra
```

```yaml
# 2. Per installation, in config.yaml
models:
  openai:
    default_model: gpt-6-astra
```

```python
# 3. For everyone, in app/services/model_registry.py
_OPENAI = Provider(default='gpt-6-astra', ...)
```

When a provider ships a new generation, edit the registry only: add the model
to `models`, point `default` at it, and add the superseded identifier to
`aliases`. Nothing else in the codebase names a model.

`GET /api/models/catalogue` returns the live catalogue — including which
providers have a key configured — so admin screens can build model pickers
from real data instead of hardcoded option lists.

### Supported providers

| Provider | Key | Notes |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | Chat and image generation |
| Anthropic Claude | `ANTHROPIC_API_KEY` or `CLAUDE_API_KEY` | |
| Google Gemini | `GEMINI_API_KEY` | |
| xAI Grok | `XAI_API_KEY` or `GROK_API_KEY` | |
| DeepSeek | `DEEPSEEK_API_KEY` | |
| Perplexity | `PERPLEXITY_API_KEY` | Answers grounded in live search, with citations |
| AWS Bedrock | `BEDROCK_API_KEY` | `access_key|secret_key|region` |
| HeyGen | `HEYGEN_API_KEY` | AI presenter video |

## How a model call works

```
route / service
   └─ AIService.chat(provider, message, ...)     app/services/ai_service.py
        ├─ composes the system prompt (platform rules + language + task)
        ├─ reads attachments once, for any provider
        └─ ai_transport.chat_*(...)              app/services/ai_transport.py
             ├─ model_registry.resolve(...)      current identifier
             ├─ builds the request in the shape that model accepts
             ├─ retries 429/5xx/timeouts with backoff; never retries 401/400
             ├─ falls forward through model_registry.fallback_chain(...)
             └─ returns ChatResult, or raises AIError with a message
                fit to show a user
```

Callers get `{'text', 'provider', 'model', 'timestamp', ...}` on success and
`{'error', ...}` on failure, and never have to handle an HTTP response or an
SDK object.

## Tests

```bash
python -m pytest
```

## Repository layout

```
app/
  routes/        Flask blueprints, one per feature area
  services/      business logic; model_registry and ai_transport live here
  utils/         file handling, encryption, serializers, decorators
config/          configuration loading
docs/            architecture, deployment, security audit
migrations/      one-off schema migrations
scripts/         seeding, demo data, smoke tests
static/          CSS, JS, images, fonts
templates/       Jinja2 templates
tests/           pytest suite
```
