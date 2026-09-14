# SkillPilot - PyCharm Setup Guide

## Quick Setup

### 1. Open Project in PyCharm

1. Open PyCharm
2. File > Open > Select `C:\SkillPilot` folder
3. Wait for PyCharm to index files

### 2. Configure Python Interpreter

1. File > Settings > Project > Python Interpreter
2. Click gear icon > Add > Virtualenv Environment
3. Select "New environment" with Python 3.9
4. Location: `C:\SkillPilot\venv`
5. Click OK

### 3. Install Dependencies

1. Open Terminal in PyCharm (View > Tool Windows > Terminal)
2. Run: `pip install -r requirements_production.txt`

### 4. Configure Environment Variables

1. Run > Edit Configurations
2. Click + > Python
3. Name: "SkillPilot Server"
4. Script path: `run.py`
5. Environment variables:
   ```
   DATABASE_URL=postgresql://user:pass@localhost:5432/skillpilot
   SESSION_SECRET=your-secret-key
   FLASK_ENV=development
   PORT=5000
   ```
6. Apply

---

## Run Configurations

### Server (Development)
- **Script**: `run.py`
- **Environment**: `FLASK_ENV=development`
- **Runs on**: http://localhost:5000

### Server (Production)
- **Script**: `run.py`
- **Environment**: `FLASK_ENV=production`
- **Uses**: Waitress with multiple threads

### Database Migration
- **Script**: `run_migration.py`
- **Run when**: Schema changes (new columns, tables)

### System Tests
- **Script**: `run_tests.py`
- **Run when**: Verify all features work

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@localhost:5432/skillpilot` |
| `SESSION_SECRET` | Flask session key | `your-long-random-string` |
| `FLASK_ENV` | Environment mode | `development` or `production` |
| `PORT` | Server port | `5000` |
| `HOST` | Server host | `0.0.0.0` |
| `WORKERS` | Number of workers | `4` |
| `THREADS` | Threads per worker | `8` |

---

## Debugging in PyCharm

1. Set breakpoints by clicking in the gutter
2. Right-click `run.py` > Debug
3. Server starts in debug mode with breakpoints enabled

---

## Database Tools

PyCharm Professional has built-in database tools:

1. View > Tool Windows > Database
2. Click + > Data Source > PostgreSQL
3. Enter connection details
4. Browse tables, run queries, view data

---

## Common Tasks

### Add a new model field:
1. Edit `app/models.py`
2. Run `run_migration.py`
3. Restart server

### Test changes:
1. Run `run_tests.py`
2. Check all tests pass

### Deploy to production:
1. Set `FLASK_ENV=production`
2. Run `run.py`
3. Configure nginx reverse proxy
