"""Production scheduling for labour-market sync (Task #17).

Verifies the DB-backed leader lock, status endpoint, audit trail, and the
`scripts/run_labour_market_sync.py` CLI entry point.
"""
from datetime import datetime, timedelta
from unittest.mock import patch


# ---- helpers --------------------------------------------------------------

def _stub_run_sync_once(payload=None):
    payload = payload or {'oman_mol': {'fetched': 0, 'inserted': 0},
                          'ncsi': {'fetched': 0, 'inserted': 0},
                          'job_portal': {'fetched': 0, 'inserted': 0},
                          'ran_at': datetime.utcnow().isoformat()}
    return patch('app.services.labour_market_service.run_sync_once',
                 return_value=payload)


# ---- lock semantics -------------------------------------------------------

def test_lock_acquired_on_first_run(app, db):
    from app.services.labour_market_service import run_sync_with_lock
    from app.models import ScheduledJobRun
    with app.app_context(), _stub_run_sync_once():
        res = run_sync_with_lock(lock_seconds=600)
        assert res['ran'] is True
        assert 'result' in res
        row = ScheduledJobRun.query.filter_by(job_name='labour_market_sync').first()
        assert row is not None
        assert row.success_count == 1
        assert row.last_success_at is not None
        assert row.last_error is None


def test_second_worker_skipped_while_locked(app, db):
    """Simulate a second worker arriving while the first still holds the lock."""
    from app.services.labour_market_service import run_sync_with_lock
    from app.models import ScheduledJobRun
    with app.app_context():
        # Pre-seed an active lock as if another worker just took it.
        db.session.add(ScheduledJobRun(
            job_name='labour_market_sync',
            locked_until=datetime.utcnow() + timedelta(minutes=20),
            locked_by='other:1',
            last_started_at=datetime.utcnow(),
        ))
        db.session.commit()

        with _stub_run_sync_once() as m:
            res = run_sync_with_lock(lock_seconds=600)
        assert res == {'ran': False, 'reason': 'locked_by_other_worker'}
        assert m.called is False


def test_expired_lock_is_taken_over(app, db):
    from app.services.labour_market_service import run_sync_with_lock
    from app.models import ScheduledJobRun
    with app.app_context():
        db.session.add(ScheduledJobRun(
            job_name='labour_market_sync',
            locked_until=datetime.utcnow() - timedelta(minutes=1),  # expired
            locked_by='dead:1',
        ))
        db.session.commit()
        with _stub_run_sync_once():
            res = run_sync_with_lock(lock_seconds=600)
        assert res['ran'] is True
        row = ScheduledJobRun.query.filter_by(job_name='labour_market_sync').first()
        assert row.success_count == 1


def test_failure_is_recorded_and_audited(app, db):
    from app.services.labour_market_service import run_sync_with_lock
    from app.models import ScheduledJobRun, AuditEvent
    with app.app_context():
        with patch('app.services.labour_market_service.run_sync_once',
                   side_effect=RuntimeError('boom')):
            res = run_sync_with_lock(lock_seconds=600)
        assert res['ran'] is True
        assert 'error' in res

        row = ScheduledJobRun.query.filter_by(job_name='labour_market_sync').first()
        assert row.failure_count == 1
        assert row.success_count == 0
        assert row.last_error and 'boom' in row.last_error

        events = AuditEvent.query.filter_by(action='scheduled_job.failure').all()
        assert len(events) == 1
        assert events[0].severity == 'error'


def test_success_emits_audit_event(app, db):
    from app.services.labour_market_service import run_sync_with_lock
    from app.models import AuditEvent
    with app.app_context(), _stub_run_sync_once():
        run_sync_with_lock(lock_seconds=600)
        events = AuditEvent.query.filter_by(action='scheduled_job.success').all()
        assert len(events) == 1


# ---- HTTP endpoints -------------------------------------------------------

def test_sync_endpoint_uses_lock(client, login_as):
    login_as('admin')
    with _stub_run_sync_once():
        r = client.post('/api/v1/skillmatch/labour-market/sync')
    assert r.status_code == 200
    body = r.get_json()
    assert body['success'] is True
    assert body['ran'] is True


def test_sync_endpoint_returns_202_when_locked(app, db, client, login_as):
    from app.models import ScheduledJobRun
    with app.app_context():
        db.session.add(ScheduledJobRun(
            job_name='labour_market_sync',
            locked_until=datetime.utcnow() + timedelta(minutes=20),
            locked_by='other:1',
        ))
        db.session.commit()
    login_as('admin')
    with _stub_run_sync_once() as m:
        r = client.post('/api/v1/skillmatch/labour-market/sync')
    assert r.status_code == 202
    assert r.get_json()['ran'] is False
    assert m.called is False


def test_sync_endpoint_force_bypasses_lock(app, db, client, login_as):
    from app.models import ScheduledJobRun
    with app.app_context():
        db.session.add(ScheduledJobRun(
            job_name='labour_market_sync',
            locked_until=datetime.utcnow() + timedelta(minutes=20),
            locked_by='other:1',
        ))
        db.session.commit()
    login_as('admin')
    with _stub_run_sync_once() as m:
        r = client.post('/api/v1/skillmatch/labour-market/sync?force=1')
    assert r.status_code == 200
    body = r.get_json()
    assert body['forced'] is True
    assert m.called is True


def test_sync_endpoint_requires_admin(client, login_as):
    login_as('teacher')
    r = client.post('/api/v1/skillmatch/labour-market/sync')
    assert r.status_code == 403


def test_status_endpoint_requires_admin(client, login_as):
    login_as('teacher')
    r = client.get('/api/v1/skillmatch/labour-market/sync/status')
    assert r.status_code == 403


def test_status_endpoint_reports_never_run(client, login_as):
    login_as('admin')
    r = client.get('/api/v1/skillmatch/labour-market/sync/status')
    assert r.status_code == 200
    body = r.get_json()
    assert body['success'] is True
    assert body['status']['job_name'] == 'labour_market_sync'
    assert body['status']['never_run'] is True


def test_status_endpoint_reports_last_success(client, login_as, app):
    login_as('admin')
    with app.app_context(), _stub_run_sync_once():
        from app.services.labour_market_service import run_sync_with_lock
        run_sync_with_lock(lock_seconds=600)
    r = client.get('/api/v1/skillmatch/labour-market/sync/status')
    body = r.get_json()['status']
    assert body['never_run'] is False
    assert body['success_count'] == 1
    assert body['last_success_at'] is not None
    assert body['last_error'] is None


# ---- CLI entry point ------------------------------------------------------

def test_cli_runs_with_lock(monkeypatch, capsys):
    """The cron script should boot the app, take the lock, and exit 0."""
    import importlib, sys, os
    # Force a clean app config; reuse the same in-memory DB the test session
    # already configured via conftest.
    import scripts.run_labour_market_sync as cli

    payload = {'oman_mol': {'fetched': 0, 'inserted': 0},
               'ncsi': {'fetched': 0, 'inserted': 0},
               'job_portal': {'fetched': 0, 'inserted': 0},
               'ran_at': datetime.utcnow().isoformat()}
    with patch('app.services.labour_market_service.run_sync_once',
               return_value=payload):
        monkeypatch.setattr(sys, 'argv', ['run_labour_market_sync.py'])
        rc = cli.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert '"ran": true' in out.lower() or '"ran"' in out


def test_cli_force_flag_bypasses_lock(monkeypatch, capsys, app, db):
    import sys
    import scripts.run_labour_market_sync as cli
    from app.models import ScheduledJobRun

    with app.app_context():
        db.session.add(ScheduledJobRun(
            job_name='labour_market_sync',
            locked_until=datetime.utcnow() + timedelta(minutes=30),
            locked_by='other:1',
        ))
        db.session.commit()

    payload = {'ran_at': datetime.utcnow().isoformat()}
    with patch('app.services.labour_market_service.run_sync_once',
               return_value=payload) as m:
        monkeypatch.setattr(sys, 'argv', ['run_labour_market_sync.py', '--force'])
        rc = cli.main()
    assert rc == 0
    assert m.called is True
