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

Two files, both kept on the server and neither committed:

| File | Holds | Template in the repo |
|---|---|---|
| `config.yaml` | AI provider keys and the model catalogue | `config.example.yaml` |
| `.env` | Database URL and session secret | `.env.example` |

`config.yaml` is git-ignored because it carries live credentials;
`config.example.yaml` is the tracked copy, with the same model catalogue and
the keys blank. The installer creates `config.yaml` from it on a fresh
install.

**API keys** resolve in one place — `app/utils/api_key_helper.get_api_key()` —
checking three sources, first match wins:

1. an **environment variable** (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, …), for
   overriding one key on one deployment
2. **`config.yaml`** under `api_keys:` — where they normally live
3. the **`api_credentials` table**, Fernet-encrypted, written by
   Admin → AI Settings

Everything uses that one lookup, so what the admin screen reports as
configured is what the platform will actually use. Changes to `config.yaml`
take effect without a restart. No screen or API response ever returns a key.

> The database encryption key is derived from `SESSION_SECRET`. Changing that
> value makes every key stored through Admin → AI Settings undecryptable, so
> set it once and leave it.

Everything else resolves as: environment variable, then `config.yaml`, then
the defaults in `config/config.py`. Required for a working install:

| Variable | Where | Purpose |
|---|---|---|
| `DATABASE_URL` | `.env` | `postgresql://user:password@host:5432/skillpilot` |
| `SECRET_KEY` / `SESSION_SECRET` | `.env` | Session signing and key encryption. 64 random hex characters. |
| `ADMIN_PASSWORD` | `.env` | Super-admin login. Empty (the default) disables password-only access. |

At least one AI provider key is needed for the AI features; the platform
enables only the providers that have one.

## AI models

**Every model the platform can call is defined in `config.yaml`, under
`ai_models:`.** No Python file names a model. Keeping up with a provider's
releases is a config change, never a code change and never a redeploy.

Each provider entry holds its models and their capabilities, an alias table
mapping retired identifiers onto their replacements, a fallback chain, and
published pricing. That matters because providers retire models on their own
schedules: the alias table means a model chosen a year ago and stored in the
database still resolves to something callable, and the fallback chain means a
retirement that happens between releases degrades to the next model rather
than showing a student a 404.

The file is re-read when its timestamp changes, so an edit takes effect
without a restart — including an edit made by another worker process.

### Admin > AI Models

The screen (also under **Manage Models** on the super-admin dashboard) is the
normal way to change any of this. For each provider it can:

- **Discover** — ask the provider which models the configured key can actually
  reach. This is what to trust when a vendor's announcement and its API
  disagree, which is usually the case for a few days around a launch.
- **Test** — send one short prompt to a candidate model and report the reply,
  the latency and the tokens, or the exact provider error with a sentence on
  what to do about it. A model can be announced, documented and listed and
  still be unavailable on a given plan or region; this is the only way to
  know.
- **Save** — offered only after a test passes, and only on explicit
  confirmation. Optionally makes it the provider's default in the same step.
- **Retire** — removes a model from the menus while keeping the identifier
  working: anything that already stored it is served by the replacement.

Changes are written back to `config.yaml` with its comments intact. A bad
edit is refused before it reaches disk, and a file that will not parse at all
leaves the platform running on a minimal built-in catalogue with a warning in
the log rather than failing to boot.

### Editing by hand

```yaml
ai_models:
  openai:
    label: "OpenAI"
    driver: openai_compatible                  # how to talk to it
    base_url: "https://api.openai.com/v1"
    discovery_url: "https://api.openai.com/v1/models"
    env_vars: [OPENAI_API_KEY]
    default_model: "gpt-5.6-terra"
    fallbacks: ["gpt-5.6-terra", "gpt-5.6-luna"]
    models:
      - id: "gpt-5.6-terra"                    # exactly as the provider spells it
        label: "GPT-5.6 Terra"
        max_output_tokens: 128000
        vision: true
        sampling: false                        # rejects `temperature`
        max_completion_tokens: true            # wants max_completion_tokens
        price_per_million: {input: 2.0, output: 12.0}
    aliases:
      "gpt-4o": "gpt-5.6-terra"                # retired id, still works
```

**Adding a whole new vendor needs no code either.** Most new providers speak
the OpenAI `/chat/completions` shape: copy an `openai_compatible` block,
change `base_url` and `env_vars`, add the key to `.env`, and it is callable
everywhere in the platform. The other drivers are `anthropic`, `gemini`,
`openai_images` and `bedrock`.

To override a default for one deployment without editing the file:

```bash
SKILLPILOT_MODEL_OPENAI=gpt-6-astra
SKILLPILOT_MODEL_CLAUDE=claude-opus-5
```

`GET /api/models/catalogue` returns the live catalogue, so model menus in the
UI are built from real data rather than hardcoded lists.

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

## Data safety

Nothing in the normal deployment path deletes data:

- `create_app()` calls `db.create_all()`, which only adds missing tables, and
  syncs new columns with `ADD COLUMN IF NOT EXISTS`. It never drops anything.
- `run_seed_users.py` only creates accounts that do not exist. An existing
  account keeps its password, role and name. Pass `--reset-passwords` to opt
  into the old behaviour.
- The installer is safe to re-run and reports what it found: how many accounts
  are already in the database, and which data directories it can see.

The data the code cannot recreate lives in three places: the PostgreSQL
database, the `uploads/` `certificates/` `course_files/` `exam_data/`
directories, and about two dozen `*.json` files in the project root that some
features use instead of the database. `backup.sh` / `backup.bat` captures all
three plus `config.yaml` and `.env`, and writes a `RESTORE.txt` beside them.

```bash
./backup.sh                 # -> backups/skillpilot-<timestamp>/
./backup.sh /mnt/backups    # or somewhere else
```

Upgrading: unzip into a *new* folder, copy the data directories, the root
`*.json` files, `config.yaml` and `.env` across, then run the installer. Keep
the old `.env`: a new `SESSION_SECRET` logs everyone out and makes any key
stored through Admin → AI Settings undecryptable.

## Tests

```bash
python -m pytest
```

## Repository layout

```
app/
  routes/        Flask blueprints, one per feature area
  services/      business logic
    model_registry.py   loads and edits the config.yaml model catalogue
    ai_transport.py     how the platform calls each provider
  utils/         file handling, encryption, serializers, decorators
    api_key_helper.py   the one place an API key is resolved
config.yaml      API keys, settings and the model catalogue (git-ignored)
config.example.yaml   tracked template for the above
config/          configuration loading
docs/            architecture, deployment, security audit
migrations/      one-off schema migrations
scripts/         seeding, demo data, smoke tests
static/          CSS, JS, images, fonts
templates/       Jinja2 templates
tests/           pytest suite
```
