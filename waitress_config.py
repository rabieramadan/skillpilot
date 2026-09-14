"""
SkillPilot LMS - Waitress WSGI Server Configuration
Optimized for 500+ concurrent users on Windows with Python 3.9

Usage:
    python waitress_config.py --port 5001
    python waitress_config.py --port 5002
    python waitress_config.py --port 5003
    python waitress_config.py --port 5004
"""

import os
import sys
import argparse
from waitress import serve

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_app():
    """Create and configure the Flask application"""
    from app import create_app
    app = create_app()
    return app

def main():
    parser = argparse.ArgumentParser(description='Run SkillPilot with Waitress')
    parser.add_argument('--port', type=int, default=5001, help='Port to run on')
    parser.add_argument('--threads', type=int, default=8, help='Number of threads per worker')
    args = parser.parse_args()
    
    app = create_app()
    
    print(f"Starting SkillPilot on port {args.port} with {args.threads} threads...")
    print(f"Process ID: {os.getpid()}")
    
    serve(
        app,
        host='127.0.0.1',
        port=args.port,
        threads=args.threads,
        # Connection settings for high load
        connection_limit=500,
        channel_timeout=120,
        recv_bytes=65536,
        send_bytes=65536,
        # Cleanup settings
        cleanup_interval=30,
        # Expose tracebacks in development only
        expose_tracebacks=False,
        # Identity
        ident='SkillPilot-LMS',
    )

if __name__ == '__main__':
    main()
