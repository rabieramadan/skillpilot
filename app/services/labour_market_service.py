"""
Labour-market data ingestion.

Pulls signals from public sources into the `LabourMarketSignal` table:
  * Oman Ministry of Labour open-data CSV / JSON feed (URL configurable via
    `OMAN_MOL_FEED_URL`, defaults to a known open-data endpoint).
  * National Centre for Statistics & Information Oman (NCSI) open-data
    endpoint (`NCSI_FEED_URL`).
  * One public job portal — the open Remotive job listings API
    (`https://remotive.com/api/remote-jobs`) used as a stand-in for live
    market demand by occupation.
  * Anthropic Claude — qualitative demand/growth estimates for a curated
    list of sectors relevant to Oman + global remote work. Activated when
    `ANTHROPIC_API_KEY` (or a stored Claude credential) is present. Sectors
    can be overridden via `CLAUDE_LABOUR_SECTORS` (comma-separated).

Each adapter is best-effort and degrades gracefully if the remote source is
unreachable. The scheduler runs in a background daemon thread inside the
Flask process; it is opt-in via `LABOUR_MARKET_SYNC_INTERVAL_HOURS`.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
from datetime import datetime, timedelta
from typing import Iterable, Optional

from app.services import model_registry as registry

JOB_NAME = 'labour_market_sync'

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = float(os.environ.get('LABOUR_MARKET_HTTP_TIMEOUT', '12'))


def _http_get(url: str) -> Optional[str]:
    if not requests or not url:
        return None
    try:
        r = requests.get(url, timeout=_HTTP_TIMEOUT,
                         headers={'User-Agent': 'SkillPilot/1.0 (+labour-market)'})
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.warning('labour-market fetch failed (%s): %s', url, e)
        return None


def _norm_period() -> str:
    now = datetime.utcnow()
    q = (now.month - 1) // 3 + 1
    return f'Q{q}-{now.year}'


def _save_signals(items: Iterable[dict]) -> int:
    """Insert raw signal dicts. Returns count of inserted rows."""
    from app.models import db, LabourMarketSignal, Occupation
    n = 0
    for it in items:
        occ_id = None
        code = it.get('occupation_code')
        if code:
            occ = Occupation.query.filter_by(code=code).first()
            occ_id = occ.id if occ else None
        db.session.add(LabourMarketSignal(
            occupation_id=occ_id,
            sector=it.get('sector'),
            region=it.get('region', 'OM'),
            source=it.get('source'),
            period=it.get('period') or _norm_period(),
            open_postings=it.get('open_postings'),
            median_salary=it.get('median_salary'),
            growth_rate_5yr=it.get('growth_rate_5yr'),
            growth_rate_10yr=it.get('growth_rate_10yr'),
            demand_index=it.get('demand_index'),
            raw_payload=it.get('raw'),
        ))
        n += 1
    db.session.commit()
    return n


# ---------- adapters ------------------------------------------------------

def fetch_oman_mol() -> list:
    url = os.environ.get('OMAN_MOL_FEED_URL',
                         'https://data.gov.om/api/explore/v2.1/catalog/datasets/labour-market-indicators/exports/json')
    body = _http_get(url)
    if not body:
        return []
    out = []
    try:
        data = json.loads(body)
        rows = data if isinstance(data, list) else data.get('results', [])
        for row in rows[:500]:
            occ = row.get('occupation') or row.get('occupation_code') or row.get('isco_code')
            sector = row.get('sector') or row.get('economic_activity')
            postings = row.get('vacancies') or row.get('open_postings')
            salary = row.get('median_salary') or row.get('average_wage')
            out.append({
                'source': 'oman_mol',
                'occupation_code': str(occ) if occ else None,
                'sector': sector, 'region': 'OM',
                'open_postings': int(postings) if postings else None,
                'median_salary': float(salary) if salary else None,
                'demand_index': row.get('demand_index'),
                'raw': row,
            })
    except Exception as e:
        logger.warning('oman_mol parse failed: %s', e)
    return out


def fetch_ncsi() -> list:
    url = os.environ.get('NCSI_FEED_URL',
                         'https://data.gov.om/api/explore/v2.1/catalog/datasets/employment-by-economic-activity/exports/json')
    body = _http_get(url)
    if not body:
        return []
    out = []
    try:
        data = json.loads(body)
        rows = data if isinstance(data, list) else data.get('results', [])
        for row in rows[:500]:
            sector = row.get('economic_activity') or row.get('sector')
            employed = row.get('employed') or row.get('total_employment')
            growth5 = row.get('growth_rate_5yr') or row.get('growth_5')
            growth10 = row.get('growth_rate_10yr') or row.get('growth_10')
            out.append({
                'source': 'ncsi',
                'sector': sector, 'region': 'OM',
                'open_postings': int(employed) if employed else None,
                'growth_rate_5yr': float(growth5) if growth5 else None,
                'growth_rate_10yr': float(growth10) if growth10 else None,
                'raw': row,
            })
    except Exception as e:
        logger.warning('ncsi parse failed: %s', e)
    return out


def fetch_job_portal() -> list:
    url = os.environ.get('JOB_PORTAL_FEED_URL',
                         'https://remotive.com/api/remote-jobs')
    body = _http_get(url)
    if not body:
        return []
    out = []
    try:
        data = json.loads(body)
        jobs = data.get('jobs') or []
        # Aggregate by category as a proxy for demand index.
        from collections import Counter
        cat_count = Counter(j.get('category') or 'general' for j in jobs)
        total = sum(cat_count.values()) or 1
        period = _norm_period()
        for cat, count in cat_count.items():
            out.append({
                'source': 'job_portal',
                'sector': cat, 'region': 'GLOBAL',
                'period': period,
                'open_postings': count,
                'demand_index': round(100.0 * count / total, 2),
                'raw': {'category': cat, 'count': count,
                         'total_jobs_in_feed': total},
            })
    except Exception as e:
        logger.warning('job_portal parse failed: %s', e)
    return out


def fetch_claude() -> list:
    """Ask Claude for structured labour-market signals.

    Best-effort and bounded: a single short prompt, JSON-only response,
    capped at 30 rows. If the API key is missing or the call fails the
    adapter returns an empty list and the rest of the sync is unaffected.
    """
    try:
        from app.utils.api_key_helper import get_api_key
        api_key = get_api_key('claude') or os.environ.get('ANTHROPIC_API_KEY')
    except Exception:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return []

    try:
        import anthropic  # type: ignore
    except Exception:
        logger.warning('anthropic library not installed; skipping Claude adapter')
        return []

    sectors_env = os.environ.get('CLAUDE_LABOUR_SECTORS')
    if sectors_env:
        sectors = [s.strip() for s in sectors_env.split(',') if s.strip()]
    else:
        sectors = [
            'Information Technology', 'Software Engineering', 'Data Science',
            'Artificial Intelligence', 'Cybersecurity', 'Cloud Computing',
            'Healthcare', 'Nursing', 'Renewable Energy', 'Oil & Gas',
            'Construction', 'Tourism & Hospitality', 'Logistics & Supply Chain',
            'Finance & Banking', 'Education & Training', 'Marketing & Sales',
        ]
    region = os.environ.get('CLAUDE_LABOUR_REGION', 'OM')
    period = _norm_period()
    model = os.environ.get('CLAUDE_LABOUR_MODEL') or registry.default_model('claude')
    timeout = float(os.environ.get('CLAUDE_LABOUR_TIMEOUT', '30'))

    prompt = (
        "You are a labour-market analyst. Return a JSON object (no prose, no "
        "markdown) of the form {\"signals\": [...]} where each signal is:\n"
        "{\"sector\": str, \"occupation\": str, \"open_postings\": int, "
        "\"median_salary\": number|null, \"growth_rate_5yr\": number, "
        "\"demand_index\": number (0-100)}.\n"
        f"Region: {region}. Period: {period}. Sectors to cover: {sectors}.\n"
        "Use your best general knowledge of current trends. Salaries in USD. "
        "Growth rates as percent (e.g. 4.5 for 4.5%). Cap at 30 signals."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        resp = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{'role': 'user', 'content': prompt}],
        )
        text = ''.join(b.text for b in resp.content if getattr(b, 'type', '') == 'text')
    except Exception as e:
        logger.warning('claude labour-market call failed: %s', e)
        return []

    text = text.strip()
    if text.startswith('```'):
        text = text.strip('`')
        if text.lower().startswith('json'):
            text = text[4:]
    try:
        data = json.loads(text)
    except Exception as e:
        logger.warning('claude labour-market JSON parse failed: %s', e)
        return []

    rows = data.get('signals') if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []

    out = []
    for row in rows[:30]:
        if not isinstance(row, dict):
            continue
        try:
            postings = row.get('open_postings')
            salary = row.get('median_salary')
            growth5 = row.get('growth_rate_5yr')
            demand = row.get('demand_index')
            out.append({
                'source': 'claude',
                'sector': str(row.get('sector') or '')[:160] or None,
                'region': region,
                'period': period,
                'open_postings': int(postings) if postings not in (None, '') else None,
                'median_salary': float(salary) if salary not in (None, '') else None,
                'growth_rate_5yr': float(growth5) if growth5 not in (None, '') else None,
                'demand_index': float(demand) if demand not in (None, '') else None,
                'raw': {
                    'occupation': row.get('occupation'),
                    'sector': row.get('sector'),
                    'model': model,
                    'generated_by': 'anthropic_claude',
                },
            })
        except (TypeError, ValueError):
            continue
    return out


# ---------- orchestration -------------------------------------------------

def run_sync_once() -> dict:
    """Run all adapters once. Returns counts per source.

    Pure data-pull entry point; does NOT acquire a distributed lock.
    Use `run_sync_with_lock()` for production / cron / scheduled invocations
    so multiple workers don't double-run the sync.
    """
    results = {}
    for name, fn in (('oman_mol', fetch_oman_mol),
                     ('ncsi', fetch_ncsi),
                     ('job_portal', fetch_job_portal),
                     ('claude', fetch_claude)):
        try:
            items = fn()
            inserted = _save_signals(items) if items else 0
            results[name] = {'fetched': len(items), 'inserted': inserted}
        except Exception as e:
            logger.exception('labour-market adapter failed: %s', name)
            results[name] = {'error': str(e)}
    results['ran_at'] = datetime.utcnow().isoformat()
    return results


# ---------- distributed lock + status tracking ---------------------------

def _worker_id() -> str:
    try:
        return f'{socket.gethostname()}:{os.getpid()}'
    except Exception:
        return f'unknown:{os.getpid()}'


def _audit(action: str, severity: str, details: dict) -> None:
    """Best-effort audit log. Never raises."""
    try:
        from app.models import db, AuditEvent
        db.session.add(AuditEvent(
            action=action, resource_type='scheduled_job',
            resource_id=JOB_NAME, severity=severity, details=details,
        ))
        db.session.commit()
    except Exception:
        try:
            from app.models import db as _db
            _db.session.rollback()
        except Exception:
            pass
        logger.exception('audit write failed for %s', action)


def _acquire_lock(lock_seconds: int) -> bool:
    """Try to take the distributed lock for `JOB_NAME`. Returns True on success.

    Uses a row in `scheduled_job_runs` as the lock; works across SQLite,
    PostgreSQL, and MySQL because the contention is resolved by an UPDATE
    that filters on the previous `locked_until` value.
    """
    from app.models import db, ScheduledJobRun
    now = datetime.utcnow()
    new_until = now + timedelta(seconds=lock_seconds)
    me = _worker_id()
    try:
        row = ScheduledJobRun.query.filter_by(job_name=JOB_NAME).first()
        if row is None:
            try:
                db.session.add(ScheduledJobRun(
                    job_name=JOB_NAME, locked_until=new_until, locked_by=me,
                    last_started_at=now,
                ))
                db.session.commit()
                return True
            except Exception:
                # Concurrent insert lost the race — fall through to UPDATE.
                db.session.rollback()
                row = ScheduledJobRun.query.filter_by(job_name=JOB_NAME).first()
                if row is None:
                    return False

        # Conditional update: only succeed if no live lock exists.
        from sqlalchemy import or_
        result = db.session.query(ScheduledJobRun).filter(
            ScheduledJobRun.job_name == JOB_NAME,
            or_(ScheduledJobRun.locked_until.is_(None),
                ScheduledJobRun.locked_until <= now),
        ).update({
            'locked_until': new_until,
            'locked_by': me,
            'last_started_at': now,
        }, synchronize_session=False)
        db.session.commit()
        return result == 1
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.exception('failed to acquire labour-market lock')
        return False


def _record_result(success: bool, result: Optional[dict], error: Optional[str]) -> None:
    from app.models import db, ScheduledJobRun
    now = datetime.utcnow()
    try:
        row = ScheduledJobRun.query.filter_by(job_name=JOB_NAME).first()
        if row is None:
            row = ScheduledJobRun(job_name=JOB_NAME)
            db.session.add(row)
        row.run_count = (row.run_count or 0) + 1
        row.last_result = result
        if success:
            row.success_count = (row.success_count or 0) + 1
            row.last_success_at = now
            row.last_error = None
        else:
            row.failure_count = (row.failure_count or 0) + 1
            row.last_error_at = now
            row.last_error = (error or '')[:4000]
        # Release the lock so the next scheduled invocation can run.
        row.locked_until = now
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.exception('failed to record labour-market run result')


def run_sync_with_lock(lock_seconds: int = 1800) -> dict:
    """Run the sync iff this worker wins the distributed lock.

    Returns:
        {'ran': True, 'result': {...}}                   on lock-and-run
        {'ran': False, 'reason': 'locked_by_other_worker'} otherwise
    """
    if not _acquire_lock(lock_seconds):
        return {'ran': False, 'reason': 'locked_by_other_worker'}
    try:
        result = run_sync_once()
        _record_result(True, result, None)
        _audit('scheduled_job.success', 'info',
               {'job': JOB_NAME, 'result': result})
        return {'ran': True, 'result': result}
    except Exception as e:
        logger.exception('labour-market sync failed under lock')
        _record_result(False, None, str(e))
        _audit('scheduled_job.failure', 'error',
               {'job': JOB_NAME, 'error': str(e)})
        return {'ran': True, 'error': str(e)}


def get_status() -> dict:
    """Return the latest scheduled-run status row as a JSON-friendly dict."""
    from app.models import ScheduledJobRun
    row = ScheduledJobRun.query.filter_by(job_name=JOB_NAME).first()
    if row is None:
        return {'job_name': JOB_NAME, 'configured': _interval_hours() > 0,
                'never_run': True}
    def _iso(dt):
        return dt.isoformat() if dt else None
    return {
        'job_name': JOB_NAME,
        'configured': _interval_hours() > 0,
        'never_run': False,
        'locked_until': _iso(row.locked_until),
        'locked_by': row.locked_by,
        'last_started_at': _iso(row.last_started_at),
        'last_success_at': _iso(row.last_success_at),
        'last_error_at': _iso(row.last_error_at),
        'last_error': row.last_error,
        'last_result': row.last_result,
        'run_count': row.run_count or 0,
        'success_count': row.success_count or 0,
        'failure_count': row.failure_count or 0,
    }


# ---------- in-process scheduler (dev / single-worker fallback) -----------

_scheduler_started = False
_scheduler_lock = threading.Lock()


def _interval_hours() -> float:
    try:
        return float(os.environ.get('LABOUR_MARKET_SYNC_INTERVAL_HOURS') or 0)
    except (TypeError, ValueError):
        return 0.0


def start_scheduler(app) -> None:
    """Start (idempotently) the background daemon thread that runs the
    ingestion loop. Opt-in via `LABOUR_MARKET_SYNC_INTERVAL_HOURS`.

    The loop now uses `run_sync_with_lock()` so it is safe to run in a
    multi-worker deployment: only the worker that wins the DB lock per
    interval will actually pull data. Production deployments should prefer
    invoking `scripts/run_labour_market_sync.py` from a Replit Scheduled
    Deployment / cron, but the in-process loop remains as a fallback.
    """
    global _scheduler_started
    interval_hours = _interval_hours()
    if interval_hours <= 0:
        return
    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True

    interval_secs = max(300, int(interval_hours * 3600))

    def _loop():
        # Initial delay so app finishes booting.
        time.sleep(30)
        while True:
            try:
                with app.app_context():
                    res = run_sync_with_lock(lock_seconds=interval_secs)
                    if res.get('ran'):
                        logger.info('labour-market sync: %s', res)
                    else:
                        logger.info('labour-market sync skipped (%s)',
                                    res.get('reason'))
            except Exception:
                logger.exception('labour-market sync loop error')
            time.sleep(interval_secs)

    t = threading.Thread(target=_loop, name='labour-market-sync', daemon=True)
    t.start()
