# utils/security.py

import os
import logging
from typing import Optional
import hashlib
import secrets
from cryptography.fernet import Fernet
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Encryption key for sensitive data
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Generate a new key if not provided (for development only)
    logger.warning("ENCRYPTION_KEY not set. Generating a temporary key for development.")
    ENCRYPTION_KEY = Fernet.generate_key().decode()

cipher_suite = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


class CredentialManager:
    """Manages secure credential storage and retrieval."""

    @staticmethod
    def encrypt_credential(value: str) -> str:
        """Encrypt a credential value."""
        try:
            encrypted = cipher_suite.encrypt(value.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Failed to encrypt credential: {e}")
            raise ValueError("Credential encryption failed")

    @staticmethod
    def decrypt_credential(encrypted_value: str) -> str:
        """Decrypt a credential value."""
        try:
            decrypted = cipher_suite.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            raise ValueError("Credential decryption failed")

    @staticmethod
    def hash_credential(value: str) -> str:
        """Hash a credential for storage (one-way)."""
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def generate_api_key(length: int = 32) -> str:
        """Generate a secure API key."""
        return secrets.token_urlsafe(length)


class InputValidator:
    """Validates and sanitizes user input."""

    # Dangerous characters that could be used for injection attacks
    DANGEROUS_CHARS = {
        "sql_injection": ["';", "--", "/*", "*/", "xp_", "sp_"],
        "path_traversal": ["../", "..\\", "~"],
        "code_injection": ["${", "#{", "<script", "javascript:"]
    }

    @staticmethod
    def validate_symbol(symbol: str, max_length: int = 20) -> str:
        """Validate and sanitize stock symbol."""
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        
        symbol = symbol.strip().upper()
        
        if len(symbol) > max_length:
            raise ValueError(f"Symbol too long (max {max_length} characters)")
        
        # Allow alphanumeric and common separators
        if not all(c.isalnum() or c in ['.', '-', '_'] for c in symbol):
            raise ValueError("Symbol contains invalid characters")
        
        return symbol

    @staticmethod
    def validate_quantity(quantity: int, min_qty: int = 0, max_qty: int = 10_000_000_000) -> int:
        """Validate quantity."""
        if not isinstance(quantity, int):
            raise ValueError("Quantity must be an integer")
        
        if quantity < min_qty or quantity > max_qty:
            raise ValueError(f"Quantity must be between {min_qty} and {max_qty}")
        
        return quantity

    @staticmethod
    def validate_price(price: float, min_price: float = 0.0, max_price: float = 1_000_000.0) -> float:
        """Validate price."""
        if not isinstance(price, (int, float)):
            raise ValueError("Price must be a number")
        
        price = float(price)
        
        if price < min_price or price > max_price:
            raise ValueError(f"Price must be between {min_price} and {max_price}")
        
        return round(price, 8)  # Limit decimal places

    @staticmethod
    def validate_percentage(value: float, min_val: float = -1.0, max_val: float = 1.0) -> float:
        """Validate percentage/ratio."""
        if not isinstance(value, (int, float)):
            raise ValueError("Percentage must be a number")
        
        value = float(value)
        
        if value < min_val or value > max_val:
            raise ValueError(f"Percentage must be between {min_val} and {max_val}")
        
        return round(value, 4)

    @staticmethod
    def validate_date(date_str: str) -> str:
        """Validate date format."""
        from datetime import datetime
        
        try:
            # Try to parse as ISO format
            datetime.fromisoformat(date_str)
            return date_str
        except ValueError:
            raise ValueError("Date must be in ISO format (YYYY-MM-DD)")

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email address."""
        import re
        
        email = email.strip().lower()
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")
        
        if len(email) > 254:  # RFC 5321
            raise ValueError("Email too long")
        
        return email

    @staticmethod
    def validate_phone(phone: str) -> str:
        """Validate phone number."""
        import re
        
        phone = phone.strip()
        # Remove common separators
        phone = re.sub(r'[\s\-\(\)\.]+', '', phone)
        
        if not re.match(r'^\+?[0-9]{10,15}$', phone):
            raise ValueError("Invalid phone number format")
        
        return phone

    @staticmethod
    def validate_user_input(user_input: str, max_length: int = 1000, allow_special: bool = False) -> str:
        """Validate and sanitize generic user input."""
        if not isinstance(user_input, str):
            raise ValueError("Input must be a string")
        
        user_input = user_input.strip()
        
        if len(user_input) == 0:
            raise ValueError("Input cannot be empty")
        
        if len(user_input) > max_length:
            raise ValueError(f"Input too long (max {max_length} characters)")
        
        # Check for dangerous patterns
        for category, patterns in InputValidator.DANGEROUS_CHARS.items():
            for pattern in patterns:
                if pattern.lower() in user_input.lower():
                    logger.warning(f"Attempted {category} in input: {user_input[:50]}")
                    raise ValueError(f"Input contains invalid characters (detected {category})")
        
        # Remove control characters
        user_input = ''.join(char for char in user_input if ord(char) >= 32 or char == '\n')
        
        return user_input

    @staticmethod
    def sanitize_dict(data: dict, max_depth: int = 10) -> dict:
        """Recursively sanitize dictionary input."""
        if max_depth <= 0:
            raise ValueError("Input nesting too deep")
        
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")
        
        sanitized = {}
        for key, value in data.items():
            # Validate key
            if not isinstance(key, str):
                raise ValueError("Dictionary keys must be strings")
            
            key = InputValidator.validate_user_input(key, max_length=100)
            
            # Recursively sanitize values
            if isinstance(value, dict):
                sanitized[key] = InputValidator.sanitize_dict(value, max_depth - 1)
            elif isinstance(value, list):
                sanitized[key] = [
                    InputValidator.sanitize_dict(item, max_depth - 1) 
                    if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized


class RateLimiter:
    """Simple rate limiting for API endpoints."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    def is_allowed(self, client_id: str) -> bool:
        """Check if a client can make a request."""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests outside the window
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < timedelta(seconds=self.window_seconds)
        ]
        
        if len(self.requests[client_id]) < self.max_requests:
            self.requests[client_id].append(now)
            return True
        
        return False

    def get_wait_time(self, client_id: str) -> float:
        """Get how long to wait before next request is allowed."""
        from datetime import datetime, timedelta
        
        if client_id not in self.requests or len(self.requests[client_id]) < self.max_requests:
            return 0.0
        
        oldest_request = self.requests[client_id][0]
        wait_until = oldest_request + timedelta(seconds=self.window_seconds)
        wait_time = (wait_until - datetime.now()).total_seconds()
        
        return max(0.0, wait_time)


# Global instances
credential_manager = CredentialManager()
input_validator = InputValidator()
api_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)