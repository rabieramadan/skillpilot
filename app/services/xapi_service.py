"""
xAPI LRS forwarding service.

Forwards `XApiStatement` rows to a configured Learning Record Store (LRS)
via HTTP POST with HTTP Basic auth, exponential-backoff retries, and
delivery-status tracking.

Environment configuration:
  XAPI_LRS_ENDPOINT   default LRS statements URL
  XAPI_LRS_USERNAME   HTTP Basic username (LRS key)
  XAPI_LRS_PASSWORD   HTTP Basic password (LRS secret)
  XAPI_LRS_VERSION    xAPI version header (default '1.0.3')
  XAPI_LRS_TIMEOUT    HTTP timeout in seconds (default 8)
  XAPI_LRS_MAX_RETRIES default 3
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Callable, Optional

try:
    import requests
except Exception:  # pragma: no cover - requests is in pyproject
    requests = None  # type: ignore


# A transport is any callable matching ``requests.post``'s signature that
# returns an object exposing ``status_code`` and ``text``. Injecting a
# transport (and a ``sleep`` shim) makes the LRS forwarder unit-testable
# without real network I/O.
Transport = Callable[..., object]


def _lrs_config(override_endpoint: Optional[str] = None) -> dict:
    return {
        'endpoint': override_endpoint or os.environ.get('XAPI_LRS_ENDPOINT'),
        'username': os.environ.get('XAPI_LRS_USERNAME'),
        'password': os.environ.get('XAPI_LRS_PASSWORD'),
        'version': os.environ.get('XAPI_LRS_VERSION', '1.0.3'),
        'timeout': float(os.environ.get('XAPI_LRS_TIMEOUT', '8')),
        'max_retries': int(os.environ.get('XAPI_LRS_MAX_RETRIES', '3')),
    }


def deliver_statement(
    statement_row,
    *,
    override_endpoint: Optional[str] = None,
    transport: Optional[Transport] = None,
    sleep: Optional[Callable[[float], None]] = None,
) -> dict:
    """POST a single statement to the LRS.

    Updates the row's `delivery_status`, `sent_at`, `delivery_error` in-place
    (caller commits). Returns {ok, status_code, error}.

    Parameters
    ----------
    transport: optional callable used in place of ``requests.post`` for
        unit tests. Must accept ``(url, json, headers, auth, timeout)`` and
        return an object exposing ``status_code`` and ``text``.
    sleep: optional callable used in place of ``time.sleep`` so tests can
        skip the exponential backoff between retries.
    """
    cfg = _lrs_config(override_endpoint or statement_row.lrs_endpoint)
    endpoint = cfg['endpoint']
    if not endpoint:
        statement_row.delivery_status = 'sent'  # No LRS configured; consider local-only.
        statement_row.sent_at = datetime.utcnow()
        statement_row.delivery_error = None
        return {'ok': True, 'status_code': None, 'error': None,
                'note': 'no LRS endpoint configured; recorded locally'}

    if transport is None:
        if requests is None:
            statement_row.delivery_status = 'failed'
            statement_row.delivery_error = 'requests library not installed'
            return {'ok': False, 'status_code': None,
                    'error': statement_row.delivery_error}
        transport = requests.post

    sleep = sleep or time.sleep

    headers = {
        'Content-Type': 'application/json',
        'X-Experience-API-Version': cfg['version'],
    }
    auth = ((cfg['username'], cfg['password'])
            if cfg['username'] and cfg['password'] else None)
    # Refuse to send Basic-Auth credentials over plain HTTP — mitigates
    # the HoundDog finding that creds were exposed via cleartext transport.
    if auth and not str(endpoint).lower().startswith('https://'):
        statement_row.delivery_status = 'failed'
        statement_row.delivery_error = (
            'refusing to send xAPI Basic-Auth credentials over non-HTTPS endpoint'
        )
        return {'ok': False, 'status_code': None,
                'error': statement_row.delivery_error}
    payload = statement_row.statement or {}

    last_err = None
    last_code = None
    for attempt in range(cfg['max_retries']):
        try:
            r = transport(endpoint, json=payload, headers=headers,
                          auth=auth, timeout=cfg['timeout'])
            last_code = r.status_code
            if 200 <= r.status_code < 300:
                statement_row.delivery_status = 'sent'
                statement_row.sent_at = datetime.utcnow()
                statement_row.delivery_error = None
                return {'ok': True, 'status_code': r.status_code, 'error': None}
            # 4xx: do not retry except 408/429
            if 400 <= r.status_code < 500 and r.status_code not in (408, 429):
                last_err = f'LRS rejected ({r.status_code}): {r.text[:300]}'
                break
            last_err = f'LRS error ({r.status_code}): {r.text[:300]}'
        except Exception as e:
            last_err = f'transport error: {e}'
        # backoff
        sleep(min(8, 0.5 * (2 ** attempt)))

    statement_row.delivery_status = 'failed'
    statement_row.delivery_error = (last_err or 'unknown failure')[:2000]
    return {'ok': False, 'status_code': last_code, 'error': last_err}


def retry_failed(
    limit: int = 50,
    actor_user_id: Optional[str] = None,
    *,
    transport: Optional[Transport] = None,
    sleep: Optional[Callable[[float], None]] = None,
) -> dict:
    """Re-attempt delivery for up to `limit` failed statements.

    When `actor_user_id` is provided, only that actor's failed statements are
    retried. Pass `None` only for trusted callers (e.g. admins) to retry
    statements across all actors.
    """
    from app.models import db, XApiStatement
    q = XApiStatement.query.filter(XApiStatement.delivery_status == 'failed')
    if actor_user_id is not None:
        q = q.filter(XApiStatement.actor_user_id == actor_user_id)
    rows = q.order_by(XApiStatement.created_at.asc()).limit(limit).all()
    sent = 0
    failed = 0
    for s in rows:
        res = deliver_statement(s, transport=transport, sleep=sleep)
        if res.get('ok'):
            sent += 1
        else:
            failed += 1
    db.session.commit()
    return {'attempted': len(rows), 'sent': sent, 'failed': failed}
