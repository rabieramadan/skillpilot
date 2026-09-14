"""
Cron / Replit Scheduled Deployment entry point for the labour-market sync.

Run from a single-leader scheduler (Replit Scheduled Deployment, cron, or any
external job runner). The DB-backed lock guarantees that even if two
schedulers fire concurrently, only one will perform the actual data pull.

Usage:
    python scripts/run_labour_market_sync.py            # lock-guarded run
    python scripts/run_labour_market_sync.py --force    # bypass the lock

Exit codes:
    0  - ran successfully or skipped because another worker held the lock
    1  - ran but the sync raised an error (already recorded in DB + audit)
    2  - unrecoverable bootstrap error (Flask app could not be created)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force', action='store_true',
                        help='Bypass the distributed lock and run immediately.')
    parser.add_argument('--lock-seconds', type=int, default=1800,
                        help='How long to hold the lock for (default 1800s).')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )
    log = logging.getLogger('labour_market_cron')

    try:
        from app import create_app
        from app.services.labour_market_service import (
            run_sync_once, run_sync_with_lock,
        )
    except Exception as e:
        print(f'bootstrap failed: {e}', file=sys.stderr)
        return 2

    app = create_app()
    with app.app_context():
        if args.force:
            result = {'ran': True, 'forced': True, 'result': run_sync_once()}
        else:
            result = run_sync_with_lock(lock_seconds=args.lock_seconds)
        log.info('labour-market scheduled run: %s', result)
        print(json.dumps(result, default=str))
        if result.get('error'):
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
