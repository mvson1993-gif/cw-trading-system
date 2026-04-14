# cw_trading_system/data/repositories/trade_repository.py

import json
import os
from datetime import datetime
from typing import Any, Dict, List
from ...errors import DataError
from .base_repository import BaseRepository


class TradeRepository(BaseRepository):
    """Repository for managing trade history with JSON backend."""
    
    def __init__(self, file_path: str = "data/trades.json"):
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Create file with default structure if it doesn't exist."""
        if not os.path.exists(self.file_path):
            os.makedirs(os.path.dirname(self.file_path) or ".", exist_ok=True)
            with open(self.file_path, "w") as f:
                json.dump([], f, indent=4)
    
    def connect(self) -> None:
        """Validate file connection."""
        self._ensure_file_exists()
    
    def disconnect(self) -> None:
        """No-op for JSON backend."""
        pass
    
    def health_check(self) -> bool:
        """Check if file is readable."""
        try:
            with open(self.file_path, "r") as f:
                json.load(f)
            return True
        except (FileNotFoundError, json.JSONDecodeError):
            return False
        except PermissionError as e:
            raise DataError(f"Permission denied when reading trade data: {e}") from e
    
    def _read_data(self) -> List[Dict[str, Any]]:
        """Read raw data from JSON file."""
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _write_data(self, data: List[Dict[str, Any]]) -> None:
        """Write data to JSON file with atomic operation."""
        temporary_file = self.file_path + ".tmp"
        with open(temporary_file, "w") as f:
            json.dump(data, f, indent=4)
        os.replace(temporary_file, self.file_path)
    
    def load_all_trades(self) -> List[Dict[str, Any]]:
        """Load all trades from storage."""
        return self._read_data()
    
    def record_trade(self,
                    underlying: str,
                    action: str,
                    size: int,
                    price: float) -> None:
        """Record a single trade execution."""
        trades = self._read_data()
        
        trades.append({
            "time": datetime.now().isoformat(),
            "underlying": underlying,
            "action": action,
            "size": size,
            "price": price
        })
        
        self._write_data(trades)
    
    def record_trade_batch(self, trade_list: List[Dict[str, Any]]) -> None:
        """Record multiple trades at once."""
        trades = self._read_data()
        
        # Add timestamp to each trade if not present
        for trade in trade_list:
            if "time" not in trade:
                trade["time"] = datetime.now().isoformat()
        
        trades.extend(trade_list)
        self._write_data(trades)
    
    def get_trades_for_underlying(self, underlying: str) -> List[Dict[str, Any]]:
        """Get all trades for a specific underlying."""
        trades = self._read_data()
        return [t for t in trades if t.get("underlying") == underlying]
    
    def get_trades_in_period(self, 
                            start_time: str, 
                            end_time: str) -> List[Dict[str, Any]]:
        """Get trades within a time period."""
        trades = self._read_data()
        return [
            t for t in trades 
            if start_time <= t.get("time", "") <= end_time
        ]
