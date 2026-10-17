"""
Pure Python JWT implementation for Cloudflare Workers
Uses only standard library modules (hmac, hashlib, base64, json, time)
"""

import hmac
import hashlib
import base64
import json
import time
from typing import Dict, Any, Optional


def _base64url_encode(data: bytes) -> str:
    """URL-safe base64 encoding without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _base64url_decode(data: str) -> bytes:
    """URL-safe base64 decoding with padding restoration."""
    # Add padding back if needed
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)


def encode_jwt(payload: Dict[str, Any], secret: str, algorithm: str = 'HS256') -> str:
    """
    Encode a JWT token.
    
    Args:
        payload: Dictionary containing claims (e.g., user_id, exp)
        secret: Secret key for signing
        algorithm: Signing algorithm (default: HS256)
    
    Returns:
        Encoded JWT token as string
    """
    if algorithm != 'HS256':
        raise ValueError("Only HS256 algorithm is supported")
    
    # Create header
    header = {
        "alg": algorithm,
        "typ": "JWT"
    }
    
    # Encode header and payload
    header_encoded = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_encoded = _base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    
    # Create signature
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature_encoded = _base64url_encode(signature)
    
    # Return complete JWT
    return f"{message}.{signature_encoded}"


def decode_jwt(token: str, secret: str, verify: bool = True) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token string
        secret: Secret key for verification
        verify: Whether to verify signature (default: True)
    
    Returns:
        Decoded payload dictionary or None if invalid
    """
    try:
        # Split token into parts
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        header_encoded, payload_encoded, signature_encoded = parts
        
        # Verify signature if requested
        if verify:
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
            expected_signature_encoded = _base64url_encode(expected_signature)
            
            if not hmac.compare_digest(signature_encoded, expected_signature_encoded):
                return None
        
        # Decode payload
        payload_json = _base64url_decode(payload_encoded)
        payload = json.loads(payload_json)
        
        # Check expiration
        if 'exp' in payload:
            if payload['exp'] < time.time():
                return None
        
        return payload
        
    except Exception:
        return None


def create_access_token(data: Dict[str, Any], secret: str, expires_in: int = 3600) -> str:
    """
    Create an access token with expiration.
    
    Args:
        data: Data to encode in the token
        secret: Secret key for signing
        expires_in: Expiration time in seconds (default: 1 hour)
    
    Returns:
        Encoded JWT token
    """
    payload = data.copy()
    payload['exp'] = int(time.time()) + expires_in
    payload['iat'] = int(time.time())
    return encode_jwt(payload, secret)
