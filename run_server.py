"""
SkillPilot LMS - Development/Production Server
Run directly from PyCharm: Right-click > Run 'run_server'

Configuration:
    - Set environment variables in PyCharm Run Configuration
    - Or use .env file in project root
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main():
    # Configuration
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    workers = int(os.environ.get('WORKERS', 4))
    threads = int(os.environ.get('THREADS', 8))
    env = os.environ.get('FLASK_ENV', 'development')
    
    print("=" * 60)
    print("  SkillPilot LMS Server")
    print("=" * 60)
    print(f"  Environment: {env}")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Workers: {workers} x {threads} threads = {workers * threads} concurrent")
    print("=" * 60)
    print()
    
    from app import create_app
    app = create_app()
    
    if env == 'development':
        # Development mode - Flask built-in server with debug
        print("Starting Flask development server...")
        app.run(host=host, port=port, debug=True, threaded=True)
    else:
        # Production mode - Waitress WSGI server
        print("Starting Waitress production server...")
        from waitress import serve
        serve(
            app,
            host=host,
            port=port,
            threads=threads * workers,
            connection_limit=500,
            channel_timeout=120,
            expose_tracebacks=False,
            ident='SkillPilot-LMS',
        )

if __name__ == '__main__':
    main()
