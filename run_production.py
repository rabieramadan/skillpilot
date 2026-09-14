from waitress import serve
from run import app

if __name__ == '__main__':
    print("Starting SkillPilot on http://127.0.0.1:8000")
    serve(app, host='127.0.0.1', port=8000, threads=6)