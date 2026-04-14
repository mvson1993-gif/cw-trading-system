# cw_trading_system/data/repositories/base_repository.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseRepository(ABC):
    """Abstract base class for all repository implementations."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to data store."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to data store."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if data store is accessible."""
        pass
