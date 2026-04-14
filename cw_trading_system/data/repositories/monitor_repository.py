# cw_trading_system/data/repositories/monitor_repository.py

import json
import os
from datetime import datetime
from typing import Any, Dict, List
from ...errors import DataError
from .base_repository import BaseRepository


class MonitorRepository(BaseRepository):
    """Repository for managing monitoring snapshots (risk, P&L) with JSON backend."""
    
    def __init__(self, file_path: str = "data/monitor_log.json"):
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
            raise DataError(f"Permission denied when reading monitor data: {e}") from e
    
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
    
    def load_all_snapshots(self) -> List[Dict[str, Any]]:
        """Load all monitoring snapshots from storage."""
        return self._read_data()
    
    def record_snapshot(self, risk: Dict[str, Any], pnl: Dict[str, Any]) -> None:
        """Record a risk and P&L snapshot."""
        logs = self._read_data()
        
        logs.append({
            "time": datetime.now().isoformat(),
            "delta": risk.get("total", {}).get("delta", 0),
            "gamma": risk.get("total", {}).get("gamma", 0),
            "vega": risk.get("total", {}).get("vega", 0),
            "theta": risk.get("total", {}).get("theta", 0),
            "pnl": pnl.get("total_pnl", 0)
        })
        
        self._write_data(logs)
    
    def record_snapshot_full(self, snapshot: Dict[str, Any]) -> None:
        """Record a complete snapshot with all fields."""
        if "time" not in snapshot:
            snapshot["time"] = datetime.now().isoformat()
        
        logs = self._read_data()
        logs.append(snapshot)
        self._write_data(logs)
    
    def get_snapshots_in_period(self,
                               start_time: str,
                               end_time: str) -> List[Dict[str, Any]]:
        """Get snapshots within a time period."""
        logs = self._read_data()
        return [
            log for log in logs 
            if start_time <= log.get("time", "") <= end_time
        ]
    
    def get_latest_snapshot(self) -> Dict[str, Any]:
        """Get the most recent snapshot."""
        logs = self._read_data()
        return logs[-1] if logs else {}
    
    def clear_old_snapshots(self, days: int = 90) -> int:
        """Remove snapshots older than specified days."""
        logs = self._read_data()
        cutoff_time = datetime.now().timestamp() - (days * 86400)
        
        original_count = len(logs)
        logs = [
            log for log in logs
            if datetime.fromisoformat(log.get("time", "")).timestamp() > cutoff_time
        ]
        
        self._write_data(logs)
        return original_count - len(logs)
