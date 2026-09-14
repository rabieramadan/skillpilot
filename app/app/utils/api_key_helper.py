"""
Helper functions to get API keys from database or environment.
Environment variables take priority over database-stored keys.
"""

import os


def get_api_key(provider: str) -> str:
    """
    Get API key for a provider, checking environment first, then database.
    
    Args:
        provider: Provider ID (openai, claude, gemini, perplexity, grok, deepseek)
        
    Returns:
        API key string or None if not found
    """
    from app.models import ApiCredential
    from app.utils.encryption import decrypt_api_key
    
    provider_info = ApiCredential.PROVIDERS.get(provider)
    if not provider_info:
        return None
    
    env_key = os.environ.get(provider_info['env_var'])
    if env_key:
        return env_key
    
    try:
        credential = ApiCredential.query.filter_by(provider=provider, is_active=True).first()
        if credential and credential.encrypted_key:
            return decrypt_api_key(credential.encrypted_key)
    except Exception as e:
        print(f"Error getting API key from database for {provider}: {e}")
    
    return None


def get_all_configured_providers() -> list:
    """
    Get a list of all providers that have API keys configured.
    
    Returns:
        List of provider IDs with configured keys
    """
    from app.models import ApiCredential
    from app.utils.encryption import decrypt_api_key
    
    configured = []
    
    for provider_id, provider_info in ApiCredential.PROVIDERS.items():
        env_key = os.environ.get(provider_info['env_var'])
        if env_key:
            configured.append(provider_id)
            continue
        
        try:
            credential = ApiCredential.query.filter_by(provider=provider_id, is_active=True).first()
            if credential and credential.encrypted_key:
                decrypted = decrypt_api_key(credential.encrypted_key)
                if decrypted:
                    configured.append(provider_id)
        except Exception:
            pass
    
    return configured
