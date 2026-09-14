# SkillPilot — deployment

Everything needed to run the platform is in this folder, including your API
keys. Two steps: install once, then start.

---

## Before you begin

You need two things on the server:

| | Check it with | If missing |
|---|---|---|
| **Python 3.11+** | `python --version` | [python.org/downloads](https://www.python.org/downloads/) — tick **"Add python.exe to PATH"** during setup |
| **PostgreSQL 13+**, running, with a `skillpilot` database | `psql -U postgres -l` | [postgresql.org/download](https://www.postgresql.org/download/) |

The installer also needs internet access once, to download Python packages
from pypi.org. After that the server runs offline apart from the AI providers
themselves.

### Creating the database

If the `skillpilot` database does not exist yet:

```
psql -U postgres -c "CREATE DATABASE skillpilot;"
```

`.env` already carries the connection string for this server, in the form:

```
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/skillpilot
```

Open `.env` and edit that line if your PostgreSQL username, password, host
or port differ. Keep the file out of version control — it holds the real
password.

### Where the settings live

| File | Holds |
|---|---|
| **`config.yaml`** | Your six AI provider keys (`api_keys:`) and the model catalogue (`ai_models:`) |
| **`.env`** | Database URL and the session secret |

Both are already filled in for you. Keep both on the server and out of version
control. On Linux: `chmod 600 config.yaml .env`.

A key is looked for in three places, first match wins: an environment
variable, then `config.yaml`, then the encrypted store behind
Admin → AI Settings. So you can override one key for one server by setting
e.g. `OPENAI_API_KEY=` in `.env` without touching `config.yaml`. Edits to
`config.yaml` take effect without a restart.

`config.example.yaml` is the blank template, in case you need to start over.

## Install (once)

**Windows**

```
install.bat
```

**Linux / macOS**

```
./install.sh
```

The installer creates a `.venv` folder, installs dependencies, verifies the
database connection, creates all tables, and seeds the starting accounts. It
stops with a specific message if anything is wrong rather than half-installing.

---

## Start

**Windows**

```
start.bat
```

**Linux / macOS**

```
./start.sh
```

Then open **http://localhost:5000** (or the server's address on port 5000).

To use a different port, edit `PORT` at the top of `start.bat`, or on
Linux run `PORT=8080 ./start.sh`.

---

## Upgrading an existing installation

**Nothing in this package deletes data.** The installer only adds missing
database tables and columns, and only creates accounts that do not exist —
an account already on the system keeps its password, role and name. Your
courses, enrolments, results, certificates and uploads are untouched.

The risk is not the installer; it is *unzipping over the top* of a working
folder, which would replace `config.yaml` and `.env`. Do this instead:

**1. Back up first.** One command, and it captures everything the code
cannot recreate:

```
backup.sh                 (Windows: backup.bat)
```

It writes `backups/skillpilot-<timestamp>/` containing a full `pg_dump`,
your uploads and certificates, the JSON data files, and your configuration,
with a `RESTORE.txt` explaining how to put it all back.

**2. Unzip somewhere new**, not over the running installation — say
`C:\SkillPilot-new`.

**3. Copy your existing data across** into the new folder:

| Copy from the old folder | Why |
|---|---|
| `.env` | Database URL and `SESSION_SECRET`. **Keep the old file.** A new `SESSION_SECRET` logs everyone out and makes any key stored through Admin → AI Settings undecryptable. |
| `config.yaml` | Your API keys and any model changes you made in the admin screen. The new one has the same keys, but copy yours if you edited the catalogue. |
| `uploads/` | Course materials and files people uploaded. |
| `certificates/`, `certificates_issued/` | Issued certificates. |
| `course_files/` | Files attached to classes. |
| `exam_data/` | Exam and survey submissions. |
| `exports/` | Anything exported from the reports screens. |
| `*.json` in the project root | Survey responses, exit-exam data, attendance, agents, sessions. The application keeps some data in these rather than the database. |

Everything else — `app/`, `static/`, `templates/`, `config/`, `scripts/` —
should come from the new package.

**4. Run the installer** in the new folder:

```
install.sh                (Windows: install.bat)
```

It will report what it found, for example:

```
  OK    Existing database: 143 user accounts found and left untouched.
  OK    Existing data kept in place: uploads/ (312 files), 9 data file(s)...
```

If it says *"Fresh database"* or *"No uploads, certificates or data files
found"* on what should be an upgrade, stop: you are pointing at the wrong
database, or the data was not copied across. Nothing has been lost — the old
folder is still there — but do not start the server until it reports what you
expect.

**5. Start it**, check you can sign in and that a course looks right, then
switch the port or service over.

### If you must unzip over the existing folder

Move the two configuration files aside first and put them back afterwards:

```
copy config.yaml config.yaml.keep
copy .env .env.keep
   ... unzip, answering "yes" to overwrite ...
copy /y config.yaml.keep config.yaml
copy /y .env.keep .env
```

The data directories and `*.json` files are not in the package, so unzipping
leaves them alone. Only `config.yaml` and `.env` are at risk.

### Backups on a schedule

`backup.sh` / `backup.bat` takes a destination as its first argument, so it
works as a scheduled task:

```
backup.bat D:\Backups\SkillPilot
```

Backups contain live credentials — keep them somewhere private, and prune old
ones yourself.

---

## First login

| Role | Username | Password |
|---|---|---|
| Super admin | `admin` | `admin123` |
| Teacher | `demoteacher1`, `demoteacher2` | `demo123` |
| Student | `demostudent1` … `demostudent5` | `demo123` |

**Change the admin password immediately** under Profile, and delete the demo
accounts you do not need from Admin → Users.

---

## If students say they enrolled but cannot open the course

Enrolling used to record the enrolment as *pending*, and nothing in the
platform could move it on — the approval screens were removed when
enrolments became automatic, and the only remaining path to "approved" is
payment verification. Those students were listed as enrolled, saw
"No Classes Yet" under Enrolled Courses, and were refused at the course
itself.

That is fixed: a course with no payment and registration open is usable the
moment a student enrols. Anyone stuck from before is released by:

```
.venv/bin/python -m migrations.release_stranded_enrolments             # report only
.venv/bin/python -m migrations.release_stranded_enrolments --apply     # release them
```

Run it once after upgrading. Without `--apply` it only prints who is
affected. It touches nothing else: enrolments on paid courses still wait for
payment verification, and nothing is deleted. Running it twice is harmless.

---

## Verifying the AI providers

On startup the server prints a provider status block:

```
AI provider status
============================================================
  OK OpenAI       reachable, default model gpt-5.6-terra
  OK Claude       reachable, default model claude-sonnet-5
  OK Gemini       reachable, default model gemini-3.8-flash
  ...
```

This uses each provider's free model-listing endpoint, so it costs nothing.

- `OK` — key works, provider reachable.
- `key rejected` — the key in `.env` is wrong or expired.
- `unreachable` — the server cannot reach that provider; usually a firewall
  or proxy. Allow outbound HTTPS to `api.openai.com`, `api.anthropic.com`,
  `generativelanguage.googleapis.com`, `api.x.ai`, `api.deepseek.com` and
  `api.perplexity.ai`.

Set `SKILLPILOT_STARTUP_CHECK=0` in `.env` to skip the check.

---

## Changing which AI model is used

Every model the platform can call is listed in `config.yaml` under
`ai_models:`. Nothing in the code names a model, so when a provider ships a
new one or retires an old one, no code change and no redeploy is needed.

**From the app.** Sign in as an administrator and open **Administration > AI
Models** (or **Manage Models** on the super-admin dashboard). For each
provider you can:

- **Discover** — list the models your API key can actually reach, straight
  from the provider.
- **Test** — send one short prompt to a model and see the reply, the time it
  took and the tokens used, or the exact error if it fails.
- **Save** — offered only after a test passes, and only when you confirm. You
  can make it the default in the same step.
- **Retire** — take a model out of the menus while keeping it working for
  anything that already refers to it.

Saves are written straight into `config.yaml`, comments and all, and take
effect immediately across every worker.

**By hand.** Edit `config.yaml` in a text editor. The server re-reads it when
the timestamp changes, so there is no need to restart. A mistake degrades
rather than breaking: a retired identifier is mapped to its replacement, a
default naming a model that is not listed falls back to one that is, and a
file that will not parse leaves the platform running on a built-in catalogue
with a warning in `server.log`.

Adding a whole new vendor is also just config — most speak the same API shape
as OpenAI, so copy an `openai_compatible` block, change `base_url` and
`env_vars`, and add the key to `.env`.

To pin a default for this deployment only, without editing the file, add to
`.env`:

```
SKILLPILOT_MODEL_OPENAI=gpt-6-astra
SKILLPILOT_MODEL_CLAUDE=claude-opus-5
```

## Running as a Windows service

To keep the platform running after logoff and start it on boot, use
[NSSM](https://nssm.cc/download):

```
nssm install SkillPilot "C:\SkillPilot\.venv\Scripts\python.exe" "C:\SkillPilot\serve.py --port 5000 --threads 8"
nssm set SkillPilot AppDirectory "C:\SkillPilot"
nssm set SkillPilot Start SERVICE_AUTO_START
net start SkillPilot
```

`install_service.bat` does this for a four-worker setup behind nginx;
`docs/DEPLOYMENT.md` covers that configuration, including the nginx files
shipped in this folder.

For a few hundred concurrent users a single instance with 8 threads is
enough. Add workers on ports 5001–5004 behind nginx only if you measure a
need.

---

## Troubleshooting

**"Python is not on PATH"** — reinstall Python with the "Add to PATH" box
ticked, or use the full path: `C:\Python311\python.exe -m venv .venv`.

**"Cannot connect to the database"** — PostgreSQL is not running, the
`skillpilot` database does not exist, or the password in `.env` is wrong. The
message names which. Test independently with
`psql "$DATABASE_URL" -c "SELECT 1"`, using the value from `.env`.

**Dependency installation fails** — almost always no internet or a proxy
blocking pypi.org. Behind a proxy:
`.venv\Scripts\pip install --proxy http://proxy:port -r requirements.txt`.

**Port 5000 already in use** — `netstat -ano | findstr :5000` to find the
process, or change `PORT` in `start.bat`.

**Server starts but pages are blank** — check `server.log` in this folder.

**An AI feature says "no API key configured"** — that provider's key is
missing from `.env`, or the key was rejected. The startup block says which.

**Everyone gets logged out on restart** — `SECRET_KEY` changed or differs
between workers. All workers on a server must share the value in `.env`.

---

## What is in this folder

```
install.bat / install.sh    one-time setup, safe to re-run
start.bat   / start.sh      run the server
backup.bat  / backup.sh     back up the database, files and configuration
check_install.py            pre-flight checks, run by the installer
serve.py                    production launcher (Waitress)
run.py                      development server
.env                        your configuration and API keys — keep private
config.yaml                 non-secret settings and model overrides
requirements.txt            Python dependencies
app/                        application code
  services/model_registry.py    every AI model the platform can call
  services/ai_transport.py      how it calls them
docs/                       architecture, deployment, security audit
nginx.conf                  reverse-proxy example
tests/                      test suite (python -m pytest)
```

---

## Backups

Run `backup.sh` / `backup.bat` before every upgrade and on a schedule. It
captures the three things that cannot be reinstalled:

1. the PostgreSQL database — users, courses, enrolments, results
2. `uploads/`, `certificates/`, `course_files/`, `exam_data/` and the `*.json`
   data files in the project root
3. `config.yaml` and `.env`

Restoring is described in the `RESTORE.txt` written alongside each backup.
