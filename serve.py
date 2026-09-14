"""Production launcher for SkillPilot using Waitress.

Usage:
    python serve.py                  # binds 0.0.0.0:80, 8 threads
    python serve.py --port 5000      # custom port
    python serve.py --threads 16     # more concurrent workers
    set SKP_PORT=80
    python serve.py
"""
import argparse
import logging
import os
import sys
import traceback


def main():
    parser = argparse.ArgumentParser(description="Run SkillPilot under Waitress")
    parser.add_argument('--host', default=os.environ.get('SKP_HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('SKP_PORT', '5000')))
    parser.add_argument('--threads', type=int, default=int(os.environ.get('SKP_THREADS', '8')))
    args = parser.parse_args()

    # Log to both console and a file so errors are never lost
    log_path = os.path.join(os.path.dirname(__file__), 'server.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding='utf-8'),
        ]
    )
    log = logging.getLogger('skillpilot')

    log.info("Creating Flask app …")
    try:
        from app import create_app
        app = create_app()
    except Exception:
        log.error("FATAL: create_app() failed\n" + traceback.format_exc())
        sys.exit(1)

    from waitress import serve
    import waitress

    log.info(f"Waitress binding {args.host}:{args.port} with {args.threads} threads")
    log.info(f"Startup log → {log_path}")

    # Base kwargs supported by all Waitress versions
    kw = dict(
        host=args.host,
        port=args.port,
        threads=args.threads,
        channel_timeout=600,
        cleanup_interval=30,
        max_request_body_size=512 * 1024 * 1024,
    )

    # trusted_proxy / trusted_proxy_headers require Waitress >= 1.4.3
    try:
        try:
            from importlib.metadata import version as _pkg_version
            _wv_str = _pkg_version('waitress')
        except Exception:
            _wv_str = getattr(waitress, '__version__', None) or '0.0.0'
        wv = tuple(int(x) for x in _wv_str.split('.')[:3])
        log.info(f"Waitress version detected: {_wv_str}")
        if wv >= (1, 4, 3):
            kw['trusted_proxy'] = '*'
            kw['trusted_proxy_headers'] = {'x-forwarded-for', 'x-forwarded-proto',
                                           'x-forwarded-host'}
        else:
            log.warning(f"Waitress {_wv_str} < 1.4.3 — skipping trusted_proxy params")
    except Exception:
        log.warning("Could not detect Waitress version — skipping trusted_proxy params")
        pass  # skip proxy params to be safe

    try:
        serve(app, **kw)
    except OSError as e:
        log.error(f"FATAL: cannot bind to {args.host}:{args.port} — {e}")
        log.error("Is port already in use? Run:  netstat -ano | findstr :" + str(args.port))
        sys.exit(1)
    except TypeError as e:
        # Waitress rejected an unknown kwarg — retry without proxy params
        log.warning(f"serve() rejected kwargs ({e}), retrying with minimal params …")
        kw.pop('trusted_proxy', None)
        kw.pop('trusted_proxy_headers', None)
        try:
            serve(app, **kw)
        except Exception:
            log.error("FATAL: Waitress failed even with minimal params\n" + traceback.format_exc())
            sys.exit(1)
    except Exception:
        log.error("FATAL: Waitress crashed\n" + traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
