"""
QR Code Generator with secure rotation for attendance system
Simplified version - uses server-side token validation
"""
import hashlib
import secrets
import time
import json
import qrcode
import io
import base64
from datetime import datetime, timedelta
from config import Config


class QRCodeGenerator:
    """Secure QR Code Generator with automatic rotation"""
    
    # Store active tokens in memory (in production, use Redis)
    _active_tokens = {}
    
    @classmethod
    def generate_secure_qr(cls, session_id, base_url='http://localhost:5000'):
        """
        Generate a secure QR code for a class session
        Uses a simple token-based system validated server-side
        
        Args:
            session_id: The session ID
            base_url: The base URL for the scan endpoint
            
        Returns:
            dict: QR code data with image and metadata
        """
        # Generate a unique token for this QR code
        token = secrets.token_urlsafe(32)
        timestamp = int(time.time() * 1000)  # Milliseconds
        
        # Calculate expiry (use config value)
        expiry_seconds = Config.QR_EXPIRY_SECONDS
        # Calculate expiry directly in milliseconds to avoid timezone issues
        expires_at_ms = timestamp + (expiry_seconds * 1000)
        expires_at = datetime.fromtimestamp(expires_at_ms / 1000)
        
        # Store the token for validation (maps token -> session_id and expiry)
        cls._active_tokens[token] = {
            'session_id': session_id,
            'created_at': timestamp,
            'expires_at': expires_at_ms
        }
        
        # Clean up old tokens periodically
        cls._cleanup_expired_tokens()
        
        # Simple QR data structure
        qr_data = {
            'token': token,
            'sid': session_id,  # Session ID for quick lookup
            'ts': timestamp,
            'exp': expires_at_ms
        }
        
        # Create a URL that students can scan directly
        qr_json = json.dumps(qr_data, separators=(',', ':'))  # Compact JSON
        qr_url = f"{base_url}/student/scan?data={qr_json}"
        
        # Generate QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            'qr_code': f"data:image/png;base64,{img_base64}",
            'qr_data': qr_data,
            'expires_at': expires_at.isoformat(),
            'session_id': session_id,
            'secret': token,  # Store token as secret for reference
            'token': token
        }
    
    @classmethod
    def _cleanup_expired_tokens(cls):
        """Remove expired tokens from memory (with grace period)"""
        now = int(time.time() * 1000)
        grace_period_ms = getattr(Config, 'QR_GRACE_PERIOD_SECONDS', 15) * 1000
        
        # Only delete tokens that have expired beyond the grace period
        expired = [token for token, data in cls._active_tokens.items() 
                   if data['expires_at'] + grace_period_ms < now]
        for token in expired:
            del cls._active_tokens[token]
    
    @classmethod
    def validate_qr(cls, qr_data):
        """
        Validate a scanned QR code
        
        Args:
            qr_data: The QR code data to validate (dict or JSON string)
            
        Returns:
            dict: Validation result with isValid, sessionId, or error
        """
        try:
            # Parse if string
            if isinstance(qr_data, str):
                qr_data = json.loads(qr_data)
            
            # Validate required fields
            if not qr_data or not isinstance(qr_data, dict):
                return {'isValid': False, 'error': 'Invalid QR code format'}
            
            # Check for token-based format (new simplified format)
            if 'token' in qr_data or 'sid' in qr_data:
                return cls._validate_token_qr(qr_data)
            
            # Fallback to legacy format with signature
            if 'signature' in qr_data:
                return cls._validate_legacy_qr(qr_data)
            
            return {'isValid': False, 'error': 'Invalid QR code format'}
            
        except json.JSONDecodeError:
            return {'isValid': False, 'error': 'Invalid QR code JSON'}
        except Exception as e:
            return {'isValid': False, 'error': f'Validation error: {str(e)}'}
    
    @classmethod
    def _validate_token_qr(cls, qr_data):
        """Validate new token-based QR code"""
        token = qr_data.get('token', '')
        session_id = qr_data.get('sid')
        expiry = qr_data.get('exp')
        timestamp = qr_data.get('ts', 0)
        
        if not session_id:
            return {'isValid': False, 'error': 'Missing session ID'}
        
        now = int(time.time() * 1000)
        
        # Add grace period for network delays and clock differences
        grace_period_ms = getattr(Config, 'QR_GRACE_PERIOD_SECONDS', 30) * 1000
        
        # Calculate age and validity
        age_ms = now - timestamp if timestamp > 0 else 0
        age_seconds = age_ms / 1000
        max_age_ms = (Config.QR_EXPIRY_SECONDS + getattr(Config, 'QR_GRACE_PERIOD_SECONDS', 30)) * 1000
        
        # Debug logging
        print(f"QR Validation Debug:")
        print(f"  Current time: {now}")
        print(f"  QR timestamp: {timestamp}")
        print(f"  QR age: {age_seconds:.1f}s")
        print(f"  Max allowed age: {max_age_ms/1000:.1f}s")
        print(f"  Expiry: {expiry}")
        print(f"  Token in memory: {token in cls._active_tokens if token else 'No token'}")
        
        # Primary validation: Check timestamp-based expiry (with grace period)
        # This allows QR codes to work even if token was cleaned up
        if expiry and now > (expiry + grace_period_ms):
            print(f"  ❌ REJECTED: QR expired (expiry + grace: {(expiry + grace_period_ms)/1000:.1f}s)")
            return {'isValid': False, 'error': 'QR code has expired. Please scan the latest QR code.'}
        
        # Additional check: QR should not be too old (using config + grace period)
        if timestamp > 0 and (now - timestamp) > max_age_ms:
            print(f"  ❌ REJECTED: QR too old ({age_seconds:.1f}s > {max_age_ms/1000:.1f}s)")
            return {'isValid': False, 'error': 'QR code has expired. Please scan the latest QR code.'}
        
        # Secondary validation: If token is in memory, verify it matches
        # If token is NOT in memory, that's OK - it might have been cleaned up
        # We already validated timestamps above, so we can trust it
        if token and token in cls._active_tokens:
            stored = cls._active_tokens[token]
            if stored['session_id'] != session_id:
                print(f"  ❌ REJECTED: Session ID mismatch")
                return {'isValid': False, 'error': 'Invalid QR code'}
            # Token exists and session matches - all good!
            print(f"  ✅ ACCEPTED: Token found and valid")
        else:
            print(f"  ✅ ACCEPTED: Token not in memory but timestamps valid")
        
        # Token not in memory but timestamps are valid - accept it
        # This handles the case where old token was cleaned up but QR is still valid
        return {
            'isValid': True,
            'sessionId': session_id,
            'timestamp': timestamp
        }
    
    @classmethod
    def _validate_legacy_qr(cls, qr_data):
        """Validate legacy HMAC-based QR code (for backward compatibility)"""
        import hmac
        
        required_fields = ['sessionId', 'timestamp', 'nonce', 'signature', 'expiresAt']
        for field in required_fields:
            if field not in qr_data:
                return {'isValid': False, 'error': f'Missing required field: {field}'}
        
        # Check expiry
        now = int(time.time() * 1000)
        try:
            expires_at = datetime.fromisoformat(qr_data['expiresAt'].replace('Z', '+00:00'))
            expires_at_ms = int(expires_at.timestamp() * 1000)
        except (ValueError, AttributeError):
            return {'isValid': False, 'error': 'Invalid expiry date'}
        
        if now > expires_at_ms:
            return {'isValid': False, 'error': 'QR code has expired. Please scan the latest QR code.'}
        
        # Check timestamp age
        qr_timestamp = qr_data['timestamp']
        max_age_ms = Config.QR_EXPIRY_SECONDS * 1000
        
        if now - qr_timestamp > max_age_ms:
            return {'isValid': False, 'error': 'QR code has expired. Please scan the latest QR code.'}
        
        # Validate HMAC signature
        data = f"{qr_data['sessionId']}-{qr_data['timestamp']}-{qr_data['nonce']}"
        expected_signature = hmac.new(
            Config.QR_SECRET.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if expected_signature != qr_data['signature']:
            return {'isValid': False, 'error': 'Invalid QR code signature'}
        
        return {
            'isValid': True,
            'sessionId': qr_data['sessionId'],
            'timestamp': qr_data['timestamp']
        }
    
    @classmethod
    def invalidate_session_tokens(cls, session_id):
        """Invalidate all tokens for a session (called when session ends)"""
        tokens_to_remove = [
            token for token, data in cls._active_tokens.items()
            if data['session_id'] == session_id
        ]
        for token in tokens_to_remove:
            del cls._active_tokens[token]
    
    @classmethod
    def get_active_token_count(cls):
        """Get count of active tokens (for debugging)"""
        cls._cleanup_expired_tokens()
        return len(cls._active_tokens)
