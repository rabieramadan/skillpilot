"""
Encryption utilities for secure API key storage
Uses Fernet symmetric encryption with a master key from environment
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet


def get_encryption_key():
    """
    Get or derive encryption key from environment.
    Uses SESSION_SECRET as the base for key derivation.
    Raises an error if SESSION_SECRET is not configured.
    """
    secret = os.environ.get('SESSION_SECRET')
    if not secret:
        raise ValueError("SESSION_SECRET environment variable must be set for API key encryption")
    
    key = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(key)


def get_fernet():
    """Get Fernet instance for encryption/decryption"""
    return Fernet(get_encryption_key())


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for secure storage.
    
    Args:
        api_key: The plaintext API key
        
    Returns:
        Base64-encoded encrypted string
    """
    if not api_key:
        return None
    
    f = get_fernet()
    encrypted = f.encrypt(api_key.encode())
    return encrypted.decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an encrypted API key.
    
    Args:
        encrypted_key: Base64-encoded encrypted string
        
    Returns:
        Plaintext API key
    """
    if not encrypted_key:
        return None
    
    try:
        f = get_fernet()
        decrypted = f.decrypt(encrypted_key.encode())
        return decrypted.decode()
    except Exception:
        return None


def mask_api_key(api_key: str) -> str:
    """
    Mask an API key for display, showing only last 4 characters.
    
    Args:
        api_key: The plaintext API key
        
    Returns:
        Masked string like '••••••••abcd'
    """
    if not api_key:
        return None
    
    if len(api_key) <= 4:
        return '••••'
    
    return '••••••••' + api_key[-4:]
