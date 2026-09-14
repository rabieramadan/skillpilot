#!/usr/bin/env python3
from app import create_app
import os
import requests
from config.config import Config

def check_api_connectivity():
    """Check connectivity to all configured AI models"""
    config = Config()
    print("\n" + "="*60)
    print("🔍 CHECKING API CONNECTIVITY")
    print("="*60)
    
    providers = {
        'OpenAI': {
            'key': config.OPENAI_API_KEY,
            'url': 'https://api.openai.com/v1/models',
            'test': lambda key: requests.get(
                'https://api.openai.com/v1/models',
                headers={'Authorization': f'Bearer {key}'},
                timeout=5
            )
        },
        'DALL-E': {
            'key': config.OPENAI_API_KEY,
            'url': None,
            'test': None,
            'note': 'Uses OpenAI API key'
        },
        'Claude': {
            'key': config.CLAUDE_API_KEY,
            'url': 'https://api.anthropic.com/v1/messages',
            'test': lambda key: requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json'
                },
                json={'model': 'claude-sonnet-4-20250514', 'max_tokens': 1, 'messages': [{'role': 'user', 'content': 'hi'}]},
                timeout=5
            )
        },
        'Gemini': {
            'key': config.GEMINI_API_KEY,
            'url': f'https://generativelanguage.googleapis.com/v1/models',
            'test': lambda key: requests.get(
                f'https://generativelanguage.googleapis.com/v1/models?key={key}',
                timeout=5
            )
        },
        'Perplexity': {
            'key': config.PERPLEXITY_API_KEY,
            'url': 'https://api.perplexity.ai/chat/completions',
            'test': lambda key: requests.post(
                'https://api.perplexity.ai/chat/completions',
                headers={'Authorization': f'Bearer {key}'},
                json={'model': 'sonar', 'messages': [{'role': 'user', 'content': 'hi'}]},
                timeout=5
            )
        },
        'Grok': {
            'key': config.GROK_API_KEY,
            'url': 'https://api.x.ai/v1/chat/completions',
            'test': lambda key: requests.post(
                'https://api.x.ai/v1/chat/completions',
                headers={'Authorization': f'Bearer {key}'},
                json={'model': 'grok-3-mini', 'messages': [{'role': 'user', 'content': 'hi'}]},
                timeout=5
            )
        },
        'DeepSeek': {
            'key': config.DEEPSEEK_API_KEY,
            'url': 'https://api.deepseek.com/v1/chat/completions',
            'test': lambda key: requests.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {key}'},
                json={'model': 'deepseek-chat', 'messages': [{'role': 'user', 'content': 'hi'}]},
                timeout=5
            )
        },
        'Dify': {
            'key': config.DIFY_API_KEY,
            'url': 'https://api.dify.ai/v1/chat-messages',
            'test': lambda key: requests.post(
                'https://api.dify.ai/v1/chat-messages',
                headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                json={'query': 'hi', 'inputs': {}, 'response_mode': 'blocking', 'user': 'test'},
                timeout=5
            )
        }
    }
    
    for name, provider in providers.items():
        key = provider['key']
        
        # Special handling for DALL-E (info only, no test)
        if provider.get('note'):
            if key:
                print(f"ℹ️  {name:15} - CONFIGURED ({provider['note']})")
            else:
                print(f"⭕ {name:15} - NOT CONFIGURED ({provider['note']})")
            continue
        
        if key:
            # Debug: Show first 10 characters of key (never show full key)
            key_preview = f"{key[:10]}..." if len(key) > 10 else key
            print(f"🔑 {name:15} - Key: {key_preview} (length: {len(key)})")
            
            try:
                response = provider['test'](key)
                if response.status_code in [200, 201]:
                    print(f"✅ {name:15} - CONNECTED (Status: {response.status_code})")
                else:
                    # Show error details for debugging
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error', {}).get('message', '') if isinstance(error_data.get('error'), dict) else str(error_data.get('error', ''))
                        if error_msg:
                            print(f"⚠️  {name:15} - API KEY INVALID (Status: {response.status_code})")
                            print(f"    Error: {error_msg[:100]}")
                        else:
                            print(f"⚠️  {name:15} - API KEY INVALID (Status: {response.status_code})")
                    except:
                        print(f"⚠️  {name:15} - API KEY INVALID (Status: {response.status_code})")
                        print(f"    Response: {response.text[:100]}")
            except requests.exceptions.Timeout:
                print(f"⏱️  {name:15} - TIMEOUT (Check internet connection)")
            except requests.exceptions.RequestException as e:
                print(f"❌ {name:15} - CONNECTION FAILED")
                print(f"    Error: {str(e)[:100]}")
        else:
            print(f"⭕ {name:15} - NO API KEY CONFIGURED")
    
    print("="*60 + "\n")

app = create_app()

if __name__ == '__main__':
    # Default to 0.0.0.0 to allow access from other machines on the network
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    print(f"🚀 Starting AIACMate Python server on http://{host}:{port}")
    print(f"🌐 Access via server IP: http://YOUR_SERVER_IP:{port}")
    print("📝 Configure your API keys in .env file")
    print("🌐 Open your browser to start chatting with AI models")
    
    # Check API connectivity
    check_api_connectivity()

    app.run(host=host, port=port, debug=debug)
