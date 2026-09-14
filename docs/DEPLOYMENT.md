# SkillPilot LMS - Windows Deployment Guide

## System Requirements

- **OS**: Windows 10/11 or Windows Server 2016+
- **Python**: 3.9+ (3.9.x recommended)
- **Database**: PostgreSQL 13+
- **Web Server**: Nginx for Windows
- **RAM**: Minimum 8GB, Recommended 16GB+
- **CPU**: 4+ cores recommended

## Capacity

This configuration supports:
- **Normal load**: 500+ concurrent users
- **Peak load**: Up to 2000 concurrent connections
- **Throughput**: ~120 requests/second

---

## Installation Steps

### 1. Install Prerequisites

```powershell
# Install Python 3.9
# Download from: https://www.python.org/downloads/release/python-3913/

# Install PostgreSQL
# Download from: https://www.postgresql.org/download/windows/

# Install Nginx for Windows
# Download from: https://nginx.org/en/download.html
# Extract to C:\nginx
```

### 2. Setup Project Directory

```powershell
# Create project folder
mkdir C:\SkillPilot
cd C:\SkillPilot

# Extract deployment files here
# Copy all application files (app/, static/, templates/, etc.)
```

### 3. Create Virtual Environment

```powershell
cd C:\SkillPilot
python -m venv venv
venv\Scripts\activate
pip install -r requirements_production.txt
```

### 4. Configure Database

```sql
-- In PostgreSQL (psql or pgAdmin):
CREATE DATABASE skillpilot;
CREATE USER skillpilot_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE skillpilot TO skillpilot_user;
```

### 5. Configure Environment

Edit `.env` file:
```
DATABASE_URL=postgresql://skillpilot_user:your_secure_password@localhost:5432/skillpilot
SESSION_SECRET=generate-a-long-random-string-here
FLASK_ENV=production
```

### 6. Initialize Database

```powershell
cd C:\SkillPilot
venv\Scripts\activate
flask db upgrade
python -c "from app import create_app; app = create_app(); app.app_context().push(); from app.models import db; db.create_all()"
```

### 7. Configure Nginx

1. Copy `nginx.conf` to `C:\nginx\conf\nginx.conf`
2. Update paths in nginx.conf:
   - Change `C:/SkillPilot/static/` to your actual static folder path
   - Change `C:/SkillPilot/uploads/` to your uploads folder path

### 8. Start Services

```powershell
# Run the startup script
C:\SkillPilot\start_servers.bat
```

---

## Architecture Overview

```
                    ┌─────────────┐
                    │   Client    │
                    │  Browsers   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx    │
                    │  Port 80    │
                    │  (Reverse   │
                    │   Proxy)    │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │Waitress │      │Waitress │      │Waitress │  ... (4 instances)
    │Port 5001│      │Port 5002│      │Port 5003│
    │8 threads│      │8 threads│      │8 threads│
    └────┬────┘      └────┬────┘      └────┬────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                    ┌──────▼──────┐
                    │ PostgreSQL  │
                    │  Database   │
                    └─────────────┘
```

---

## Performance Tuning

### For 500+ Concurrent Users

The default configuration includes:
- **4 Waitress workers** × 8 threads = 32 concurrent request handlers
- **Nginx connection limit**: 2048 per worker
- **Database connection pooling**: Configure in SQLAlchemy

### PostgreSQL Tuning (postgresql.conf)

```ini
# Memory
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 64MB

# Connections
max_connections = 200

# Write performance
wal_buffers = 64MB
checkpoint_completion_target = 0.9
```

### Scaling Beyond 500 Users

1. **Add more Waitress workers**:
   - Edit `start_servers.bat` to add ports 5005, 5006, etc.
   - Update `nginx.conf` upstream block

2. **Enable Redis caching** (optional):
   ```powershell
   pip install redis flask-caching
   ```

3. **Use connection pooling**:
   ```python
   # In app config
   SQLALCHEMY_POOL_SIZE = 20
   SQLALCHEMY_MAX_OVERFLOW = 40
   SQLALCHEMY_POOL_RECYCLE = 300
   ```

---

## Monitoring

### Check Running Services

```powershell
# View Nginx status
tasklist /fi "imagename eq nginx.exe"

# View Python workers
tasklist /fi "imagename eq python.exe"

# Check ports
netstat -ano | findstr "5001 5002 5003 5004"
```

### Log Files

- Nginx access: `C:\nginx\logs\access.log`
- Nginx errors: `C:\nginx\logs\error.log`
- Application logs: Configure in Flask

---

## Troubleshooting

### Port Already in Use

```powershell
netstat -ano | findstr :5001
taskkill /pid <PID> /f
```

### Database Connection Errors

1. Check PostgreSQL service is running
2. Verify DATABASE_URL in `.env`
3. Check firewall allows port 5432

### Nginx Won't Start

1. Check nginx.conf syntax: `nginx -t`
2. Verify paths exist (static, uploads folders)
3. Check port 80 is available

---

## Outbound access the browser needs

The server itself only needs to reach the AI providers, but **the pages
load six libraries from public CDNs**, so the *user's browser* needs those
too. If a campus network blocks them, the platform still runs and every
API still works, but parts of the interface quietly stop: icons vanish,
charts and the workflow canvas do not draw, chat answers render as raw
markdown, and PDF export reports that it is unavailable.

| Host | Used for |
|---|---|
| `cdnjs.cloudflare.com` | Font Awesome icons, highlight.js, jsPDF export |
| `cdn.jsdelivr.net` | Chart.js, marked, Drawflow (the agent canvas) |
| `fonts.googleapis.com`, `fonts.gstatic.com` | Inter and Tajawal fonts |

Allow those three origins from the client network, or mirror the files on
the server and point the `<script>`/`<link>` tags in `templates/` at
`/static/` instead — nothing else in the code depends on where they come
from.

Two of the tags (`marked` and `Drawflow`) do not name a version, so they
track whatever the CDN publishes. Pinning them to a fixed version is worth
doing before a term starts, so an upstream release cannot change the
platform under you.

---

## Security Checklist

- [ ] Change default SESSION_SECRET
- [ ] Use strong database password
- [ ] Enable HTTPS in production
- [ ] Configure firewall rules
- [ ] Set up regular database backups
- [ ] Update admin password from default

---

## Support

For issues, check:
1. Application logs
2. Nginx error logs
3. PostgreSQL logs
4. Windows Event Viewer
