import os
import yaml
from dotenv import load_dotenv

# Load .env file (try .env first, then .env.server for Windows server deployment)
if os.path.exists('.env'):
    load_dotenv('.env')
elif os.path.exists('.env.server'):
    load_dotenv('.env.server')
else:
    load_dotenv()  # Default behavior

# Load config.yaml if it exists
try:
    with open('config.yaml', 'r') as f:
        yaml_config = yaml.safe_load(f) or {}
except FileNotFoundError:
    yaml_config = {}

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # App settings
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    ADMIN_SESSION_TIMEOUT = 3600 * 24  # 24 hours
    
    # AI Keys
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY')
    GROK_API_KEY = os.environ.get('GROK_API_KEY')
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    DIFY_API_KEY = os.environ.get('DIFY_API_KEY')
    HEYGEN_API_KEY = os.environ.get('HEYGEN_API_KEY')
    BEDROCK_API_KEY = os.environ.get('BEDROCK_API_KEY')
    
    # Inject YAML values
    for key, value in yaml_config.items():
        # This will not work directly to set class attributes dynamically in this scope easily
        # without locals() hacks.
        # Instead, we'll just set them after class creation if needed, 
        # but for now let's assume the keys above are sufficient.
        pass

# Post-definition injection (if we really need dynamic values from yaml)
for key, value in yaml_config.items():
    if not hasattr(Config, key):
        setattr(Config, key, value)
