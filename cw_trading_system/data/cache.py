# data/cache.py

"""
Caching utilities for market data and API responses.
"""

import time
from typing import Dict, Optional


class DataCache:
    """Simple TTL-based cache for API responses."""

    def __init__(self, default_ttl: int = 300):
        self.cache: Dict[str, Dict] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Dict]:
        """Get cached data if not expired."""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.default_ttl:
                return entry['data']
            else:
                del self.cache[key]
        return None

    def set(self, key: str, data: Dict, ttl: Optional[int] = None) -> None:
        """Set cache data with optional custom TTL."""
        ttl_seconds = ttl or self.default_ttl
        self.cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl_seconds
        }

    def clear(self) -> None:
        """Clear all cached data."""
        self.cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns number of entries removed."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry['timestamp'] > entry.get('ttl', self.default_ttl)
        ]

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)