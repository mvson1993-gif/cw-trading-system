# data/monitor_store.py

from datetime import datetime
from .repositories import MonitorRepository

# Initialize repository instance
_monitor_repo = MonitorRepository(file_path="data/monitor_log.json")


def load_logs():
    """Load all monitoring snapshots from repository.
    
    Returns:
        List of snapshot records
    """
    return _monitor_repo.load_all_snapshots()


def save_logs(logs):
    """Save logs list to repository (replaces entire store).
    
    Args:
        logs: List of log dictionaries
    """
    _monitor_repo._write_data(logs)


def record_snapshot(risk, pnl):
    """Record a risk and P&L snapshot.
    
    Args:
        risk: Risk metrics dict with structure {"total": {"delta": ..., "gamma": ..., ...}}
        pnl: P&L dict with structure {"total_pnl": ...}
    """
    _monitor_repo.record_snapshot(risk, pnl)
