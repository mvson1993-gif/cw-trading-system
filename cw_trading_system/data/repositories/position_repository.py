# cw_trading_system/data/repositories/position_repository.py

import json
import os
from datetime import date
from typing import List, Tuple
from ...errors import DataError
from .base_repository import BaseRepository
from ..positions import CWPosition, HedgePosition


class PositionRepository(BaseRepository):
    """Repository for managing positions (CW and hedge) with JSON backend."""
    
    def __init__(self, file_path: str = "data/positions.json"):
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Create file with default structure if it doesn't exist."""
        if not os.path.exists(self.file_path):
            os.makedirs(os.path.dirname(self.file_path) or ".", exist_ok=True)
            default_data = {
                "cw_positions": [],
                "hedge_positions": []
            }
            with open(self.file_path, "w") as f:
                json.dump(default_data, f, indent=4)
    
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
            raise DataError(f"Permission denied when reading position data: {e}") from e
    
    def _read_data(self) -> dict:
        """Read raw data from JSON file."""
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"cw_positions": [], "hedge_positions": []}
    
    def _write_data(self, data: dict) -> None:
        """Write data to JSON file with atomic operation."""
        temporary_file = self.file_path + ".tmp"
        with open(temporary_file, "w") as f:
            json.dump(data, f, indent=4)
        os.replace(temporary_file, self.file_path)
    
    def load_portfolio(self) -> Tuple[List[CWPosition], List[HedgePosition]]:
        """Load all positions from storage."""
        data = self._read_data()
        
        cw_positions = [
            CWPosition(**p) for p in data.get("cw_positions", [])
        ]
        hedge_positions = [
            HedgePosition(**h) for h in data.get("hedge_positions", [])
        ]
        
        return cw_positions, hedge_positions
    
    def save_portfolio(self, 
                      cw_positions: List[CWPosition], 
                      hedge_positions: List[HedgePosition]) -> None:
        """Save all positions to storage."""
        data = {
            "cw_positions": [vars(p) for p in cw_positions],
            "hedge_positions": [vars(h) for h in hedge_positions]
        }
        self._write_data(data)
    
    def add_cw_position(self, 
                        new_pos: CWPosition,
                        cw_positions: List[CWPosition],
                        hedge_positions: List[HedgePosition]) -> None:
        """Add a new CW position."""
        cw_positions.append(new_pos)
        self.save_portfolio(cw_positions, hedge_positions)
    
    def remove_cw_position(self, 
                          index: int,
                          cw_positions: List[CWPosition],
                          hedge_positions: List[HedgePosition]) -> None:
        """Remove CW position by index."""
        if 0 <= index < len(cw_positions):
            cw_positions.pop(index)
            self.save_portfolio(cw_positions, hedge_positions)
    
    def add_hedge_position(self,
                          new_pos: HedgePosition,
                          cw_positions: List[CWPosition],
                          hedge_positions: List[HedgePosition]) -> None:
        """Add a new hedge position."""
        hedge_positions.append(new_pos)
        self.save_portfolio(cw_positions, hedge_positions)
    
    def update_hedge_position(self,
                             index: int,
                             updated_pos: HedgePosition,
                             cw_positions: List[CWPosition],
                             hedge_positions: List[HedgePosition]) -> None:
        """Update hedge position by index."""
        if 0 <= index < len(hedge_positions):
            hedge_positions[index] = updated_pos
            self.save_portfolio(cw_positions, hedge_positions)
    
    def remove_expired_positions(self,
                                cw_positions: List[CWPosition],
                                hedge_positions: List[HedgePosition]) -> List[CWPosition]:
        """Remove expired CW positions."""
        today = date.today()
        
        cw_positions = [
            p for p in cw_positions
            if date.fromisoformat(p.expiry) > today
        ]
        
        self.save_portfolio(cw_positions, hedge_positions)
        return cw_positions
