import pytest
import os
from cw_trading_system.data.monitor_store import load_logs, save_logs, record_snapshot


class TestMonitorStore:
    def test_load_logs_empty(self, tmp_path):
        import cw_trading_system.data.monitor_store as ms
        original_path = ms._monitor_repo.file_path
        ms._monitor_repo.file_path = str(tmp_path / "monitor_log.json")
        ms._monitor_repo._ensure_file_exists()

        logs = load_logs()
        assert logs == []
        
        ms._monitor_repo.file_path = original_path

    def test_save_and_load_logs(self, tmp_path):
        import cw_trading_system.data.monitor_store as ms
        original_path = ms._monitor_repo.file_path
        ms._monitor_repo.file_path = str(tmp_path / "monitor_log.json")
        ms._monitor_repo._ensure_file_exists()

        logs = [{"test": "data"}]
        save_logs(logs)
        loaded = load_logs()
        assert loaded == logs
        
        ms._monitor_repo.file_path = original_path

    def test_record_snapshot(self, tmp_path):
        import cw_trading_system.data.monitor_store as ms
        original_path = ms._monitor_repo.file_path
        ms._monitor_repo.file_path = str(tmp_path / "monitor_log.json")
        ms._monitor_repo._ensure_file_exists()

        risk = {
            "total": {
                "delta": 1.5,
                "gamma": 0.02,
                "vega": 0.1,
                "theta": -0.05
            }
        }
        pnl = {"total_pnl": 10000}

        record_snapshot(risk, pnl)

        logs = load_logs()
        assert len(logs) == 1
        assert logs[0]["delta"] == 1.5
        assert logs[0]["gamma"] == 0.02
        assert logs[0]["vega"] == 0.1
        assert logs[0]["theta"] == -0.05
        assert logs[0]["pnl"] == 10000
        assert "time" in logs[0]
        
        ms._monitor_repo.file_path = original_path