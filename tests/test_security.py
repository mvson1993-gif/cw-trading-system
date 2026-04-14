# tests/test_security.py

import pytest
from cw_trading_system.utils.security import (
    CredentialManager, InputValidator, RateLimiter
)


class TestCredentialManager:
    """Tests for credential management."""

    def test_encrypt_decrypt_credential(self):
        """Test credential encryption and decryption."""
        original = "super_secret_key_12345"
        encrypted = CredentialManager.encrypt_credential(original)
        assert encrypted != original
        assert encrypted.strip() != ""

        decrypted = CredentialManager.decrypt_credential(encrypted)
        assert decrypted == original

    def test_hash_credential(self):
        """Test credential hashing."""
        value = "password123"
        hash1 = CredentialManager.hash_credential(value)
        hash2 = CredentialManager.hash_credential(value)
        
        # Same input should produce same hash
        assert hash1 == hash2
        
        # Different input should produce different hash
        hash3 = CredentialManager.hash_credential("password124")
        assert hash1 != hash3

    def test_generate_api_key(self):
        """Test API key generation."""
        key1 = CredentialManager.generate_api_key()
        key2 = CredentialManager.generate_api_key()
        
        # Keys should be different (random)
        assert key1 != key2
        assert len(key1) > 20
        assert len(key2) > 20


class TestInputValidator:
    """Tests for input validation."""

    def test_validate_symbol_valid(self):
        """Test valid symbol validation."""
        assert InputValidator.validate_symbol("HPG.VN") == "HPG.VN"
        assert InputValidator.validate_symbol("aapl") == "AAPL"
        assert InputValidator.validate_symbol("  TEST  ") == "TEST"

    def test_validate_symbol_invalid(self):
        """Test invalid symbol rejection."""
        with pytest.raises(ValueError):
            InputValidator.validate_symbol("")
        
        with pytest.raises(ValueError):
            InputValidator.validate_symbol("A" * 50)  # Too long
        
        with pytest.raises(ValueError):
            InputValidator.validate_symbol("TEST@#$")  # Invalid chars

    def test_validate_quantity_valid(self):
        """Test valid quantity validation."""
        assert InputValidator.validate_quantity(1000000) == 1000000
        assert InputValidator.validate_quantity(0) == 0
        assert InputValidator.validate_quantity(10000) == 10000

    def test_validate_quantity_invalid(self):
        """Test invalid quantity rejection."""
        with pytest.raises(ValueError):
            InputValidator.validate_quantity(-100)
        
        with pytest.raises(ValueError):
            InputValidator.validate_quantity(11_000_000_000)  # Exceeds max
        
        with pytest.raises(ValueError):
            InputValidator.validate_quantity("1000")  # Wrong type

    def test_validate_price_valid(self):
        """Test valid price validation."""
        assert InputValidator.validate_price(100.0) == 100.0
        assert InputValidator.validate_price(0.0) == 0.0
        assert InputValidator.validate_price(25.5) == 25.5

    def test_validate_price_invalid(self):
        """Test invalid price rejection."""
        with pytest.raises(ValueError):
            InputValidator.validate_price(-10.0)
        
        with pytest.raises(ValueError):
            InputValidator.validate_price(2_000_000.0)  # Exceeds max

    def test_validate_percentage_valid(self):
        """Test valid percentage validation."""
        assert InputValidator.validate_percentage(0.5) == 0.5
        assert InputValidator.validate_percentage(-0.1) == -0.1
        assert InputValidator.validate_percentage(0.0) == 0.0

    def test_validate_percentage_invalid(self):
        """Test invalid percentage rejection."""
        with pytest.raises(ValueError):
            InputValidator.validate_percentage(1.5)  # Exceeds max
        
        with pytest.raises(ValueError):
            InputValidator.validate_percentage(-1.5)  # Below min

    def test_validate_date_valid(self):
        """Test valid date validation."""
        assert InputValidator.validate_date("2024-12-31") == "2024-12-31"
        assert InputValidator.validate_date("2024-01-01") == "2024-01-01"

    def test_validate_date_invalid(self):
        """Test invalid date rejection."""
        with pytest.raises(ValueError):
            InputValidator.validate_date("2024/12/31")  # Wrong format
        
        with pytest.raises(ValueError):
            InputValidator.validate_date("invalid")

    def test_validate_email_valid(self):
        """Test valid email validation."""
        assert InputValidator.validate_email("test@example.com") == "test@example.com"
        assert InputValidator.validate_email("  USER@DOMAIN.ORG  ") == "user@domain.org"

    def test_validate_email_invalid(self):
        """Test invalid email rejection."""
        with pytest.raises(ValueError):
            InputValidator.validate_email("invalid.email")
        
        with pytest.raises(ValueError):
            InputValidator.validate_email("@example.com")
        
        with pytest.raises(ValueError):
            InputValidator.validate_email("test@")

    def test_validate_phone_valid(self):
        """Test valid phone validation."""
        assert InputValidator.validate_phone("1234567890") == "1234567890"
        assert InputValidator.validate_phone("+1 (234) 567-8901") == "+12345678901"

    def test_validate_phone_invalid(self):
        """Test invalid phone rejection."""
        with pytest.raises(ValueError):
            InputValidator.validate_phone("123")  # Too short
        
        with pytest.raises(ValueError):
            InputValidator.validate_phone("abc-def-ghij")  # Non-numeric

    def test_validate_user_input_valid(self):
        """Test valid user input validation."""
        assert "test" in InputValidator.validate_user_input("This is a test").lower()

    def test_validate_user_input_sql_injection(self):
        """Test SQL injection prevention."""
        # Test patterns that are in DANGEROUS_CHARS
        with pytest.raises(ValueError):
            InputValidator.validate_user_input("'; DROP TABLE users; --")

    def test_validate_user_input_path_traversal(self):
        """Test path traversal prevention."""
        with pytest.raises(ValueError):
            InputValidator.validate_user_input("../../etc/passwd")

    def test_validate_user_input_code_injection(self):
        """Test code injection prevention."""
        with pytest.raises(ValueError):
            InputValidator.validate_user_input("<script>alert('xss')</script>")

    def test_sanitize_dict_valid(self):
        """Test valid dictionary sanitization."""
        data = {
            "symbol": "AAPL",
            "quantity": 100,
            "price": 150.25
        }
        result = InputValidator.sanitize_dict(data)
        assert result == data

    def test_sanitize_dict_nested(self):
        """Test nested dictionary sanitization."""
        data = {
            "order": {
                "symbol": "AAPL",
                "details": {
                    "quantity": 100
                }
            }
        }
        result = InputValidator.sanitize_dict(data)
        assert result["order"]["symbol"] == "AAPL"
        assert result["order"]["details"]["quantity"] == 100

    def test_sanitize_dict_max_depth(self):
        """Test max depth protection."""
        # Create deeply nested dict
        data = {"a": {"b": {"c": {"d": {"e": {"f": "value"}}}}}}
        
        with pytest.raises(ValueError):
            InputValidator.sanitize_dict(data, max_depth=2)


class TestRateLimiter:
    """Tests for rate limiting."""

    def test_rate_limiter_allow(self):
        """Test normal rate limiting."""
        limiter = RateLimiter(max_requests=3, window_seconds=1)
        client = "test_client"
        
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is False  # Exceeds limit

    def test_rate_limiter_multiple_clients(self):
        """Test rate limiting for multiple clients."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is False
        
        assert limiter.is_allowed("client2") is True
        assert limiter.is_allowed("client2") is True
        assert limiter.is_allowed("client2") is False

    def test_rate_limiter_get_wait_time(self):
        """Test wait time calculation."""
        limiter = RateLimiter(max_requests=1, window_seconds=10)
        client = "test_client"
        
        # First request should be allowed
        assert limiter.is_allowed(client) is True
        
        # Second request should be rate limited
        assert limiter.is_allowed(client) is False
        wait_time = limiter.get_wait_time(client)
        assert 0 < wait_time <= 10