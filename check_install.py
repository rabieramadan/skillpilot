#!/usr/bin/env python3
"""Pre-flight check run by install.bat / install.sh.

Verifies, in the order a failure would actually bite:

1. every dependency imports
2. .env is readable and the required settings are present
3. the database accepts a connection
4. the schema can be created

Exits non-zero with a message that says what to change and where. Nothing
here prints a key, or any part of one.
"""

import importlib
import os
import sys

REQUIRED_MODULES = [
    ('flask', 'flask'),
    ('flask_sqlalchemy', 'flask-sqlalchemy'),
    ('flask_login', 'flask-login'),
    ('flask_migrate', 'flask-migrate'),
    ('flask_cors', 'flask-cors'),
    ('sqlalchemy', 'sqlalchemy'),
    ('psycopg2', 'psycopg2-binary'),
    ('waitress', 'waitress'),
    ('dotenv', 'python-dotenv'),
    ('yaml', 'pyyaml'),
    ('ruamel.yaml', 'ruamel.yaml'),
    ('anthropic', 'anthropic'),
    ('google.genai', 'google-genai'),
    ('pdfplumber', 'pdfplumber'),
    ('pypdf', 'pypdf'),
    ('docx', 'python-docx'),
    ('pptx', 'python-pptx'),
    ('openpyxl', 'openpyxl'),
    ('reportlab', 'reportlab'),
    ('PIL', 'pillow'),
    ('qrcode', 'qrcode'),
    ('arabic_reshaper', 'arabic-reshaper'),
    ('bidi', 'python-bidi'),
    ('cryptography', 'cryptography'),
    ('defusedxml', 'defusedxml'),
    ('signxml', 'signxml'),
    ('lxml', 'lxml'),
    ('requests', 'requests'),
]

OK = '  OK   '
BAD = '  FAIL '


def fail(message: str) -> None:
    print(f'\n{BAD} {message}\n')
    sys.exit(1)


def check_dependencies() -> None:
    missing = []
    for module, package in REQUIRED_MODULES:
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)
    if missing:
        fail('These packages did not install:\n'
             f'         {", ".join(missing)}\n'
             '         Run:  .venv\\Scripts\\pip install -r requirements.txt\n'
             '         (Linux/macOS:  .venv/bin/pip install -r requirements.txt)')
    print(f'{OK} All {len(REQUIRED_MODULES)} dependencies import correctly.')


def check_configuration():
    from config.config import Config

    if not os.environ.get('DATABASE_URL'):
        fail('DATABASE_URL is not set in .env.\n'
             '         Expected something like:\n'
             '         DATABASE_URL=postgresql://postgres:PASSWORD@localhost:5432/skillpilot')

    secret = os.environ.get('SECRET_KEY') or os.environ.get('SESSION_SECRET') or ''
    if len(secret) < 32 or secret.lower().startswith(('change', 'your-')):
        fail('SECRET_KEY in .env is missing or still the placeholder.\n'
             '         Generate one with:\n'
             '           python -c "import secrets; print(secrets.token_hex(32))"\n'
             '         and put it in .env as SECRET_KEY=...\n'
             '         Without it, users are logged out on every restart and\n'
             '         sessions break across multiple workers.')
    if not Config.ADMIN_PASSWORD:
        print('  NOTE  ADMIN_PASSWORD is not set, so password-only super-admin '
              'login is disabled. Sign in with the seeded admin account '
              'instead. This is the safe default.')

    print(f'{OK} .env is readable and the required settings are present.')
    return Config


def check_api_keys() -> None:
    """Report which providers have a key, and which file it came from.

    Never prints a key or any part of one.
    """
    from app.utils.api_key_helper import get_api_key_source

    providers = ['openai', 'claude', 'gemini', 'grok', 'deepseek', 'perplexity']
    found = []
    for provider in providers:
        source = get_api_key_source(provider)
        if source:
            found.append(f'{provider} ({source})')

    if found:
        print(f'{OK} AI provider keys: {", ".join(found)}.')
    else:
        print('  WARN  No AI provider key found. The platform will run, but '
              'every AI feature will report "no API key configured".\n'
              '        Add your keys to the api_keys: block of config.yaml.')


def check_database() -> None:
    from sqlalchemy import create_engine, text

    url = os.environ['DATABASE_URL']
    safe = url.split('@')[-1] if '@' in url else url
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
    except Exception as exc:
        detail = str(exc).splitlines()[0][:200]
        fail(f'Cannot connect to the database at {safe}\n'
             f'         {detail}\n\n'
             '         Check that:\n'
             '           - PostgreSQL is running\n'
             '           - the database named at the end of DATABASE_URL exists\n'
             '             (create it with:  createdb skillpilot)\n'
             '           - the username and password in .env are correct\n'
             '           - the host and port are reachable')
    print(f'{OK} Database connection succeeded ({safe}).')


def check_catalogue() -> None:
    """The model catalogue must load, and ideally be editable from the app."""
    from app.services import model_registry as registry

    status = registry.catalogue_status()
    if status['source'] == 'built-in':
        print('  WARN  config.yaml has no usable ai_models block, so the '
              'built-in fallback catalogue is in use. Restore the ai_models '
              'section from the shipped config.yaml.')
        for line in status['warnings']:
            print(f'        {line}')
        return

    print(f'{OK} Model catalogue: {status["provider_count"]} providers, '
          f'{status["model_count"]} models, from config.yaml.')
    for line in status['warnings']:
        print(f'  WARN  {line}')
    if not status['writable']:
        print('  NOTE  config.yaml is not writable by this user, so Admin > '
              'AI Models can show the catalogue but not save changes.')


#: Everything the platform writes that is not in the database. Losing any of
#: it is silent — the app simply starts with nothing — so the installer says
#: out loud what it found.
DATA_DIRS = ['uploads', 'certificates', 'certificates_issued', 'course_files',
             'exam_data', 'exports']


def check_existing_data() -> None:
    """Report data already on disk, so nothing goes missing unnoticed."""
    import glob

    found = []
    for directory in DATA_DIRS:
        if os.path.isdir(directory):
            count = sum(len(files) for _, _, files in os.walk(directory))
            if count:
                found.append(f'{directory}/ ({count} files)')

    json_files = [f for f in glob.glob('*.json')
                  if f not in ('package.json', 'package-lock.json')]
    if json_files:
        found.append(f'{len(json_files)} data file(s) in the project root')

    if found:
        print(f'{OK} Existing data kept in place: {", ".join(found)}.')
    else:
        print('  NOTE  No uploads, certificates or data files found yet. That '
              'is expected on a first install; on an upgrade it means you are '
              'in a new folder and should copy them across.')


def check_schema() -> None:
    from app import create_app
    from app.models import db
    from sqlalchemy import inspect

    app = create_app()
    if app.config.get('SKP_DB_INIT_ERROR'):
        fail('The schema could not be created:\n'
             f'         {app.config["SKP_DB_INIT_ERROR"][:300]}')

    with app.app_context():
        db.create_all()
        tables = inspect(db.engine).get_table_names()
    if not tables:
        fail('The schema is empty after create_all(). The database user '
             'probably lacks CREATE privileges.')
    print(f'{OK} Schema ready: {len(tables)} tables.')

    # Say whether this is a fresh database or an existing one. create_all()
    # only ever adds missing tables and columns; nothing here drops anything.
    try:
        from app.models import User
        with app.app_context():
            users = User.query.count()
        if users:
            print(f'{OK} Existing database: {users} user accounts found and '
                  'left untouched.')
        else:
            print(f'{OK} Fresh database — starting accounts will be created.')
    except Exception:
        pass


def main() -> None:
    print()
    check_dependencies()
    check_configuration()
    check_api_keys()
    check_database()
    check_schema()
    check_catalogue()
    check_existing_data()
    print('\n  Pre-flight checks passed.\n')


if __name__ == '__main__':
    main()
