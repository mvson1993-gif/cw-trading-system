import pytest
import os
from cw_trading_system.data.trade_store import load_trades, save_trades, record_trade


class TestTradeStore:
    def test_load_trades_empty(self, tmp_path):
        import cw_trading_system.data.trade_store as ts
        original_path = ts._trade_repo.file_path
        ts._trade_repo.file_path = str(tmp_path / "trades.json")
        ts._trade_repo._ensure_file_exists()

        trades = load_trades()
        assert trades == []
        
        ts._trade_repo.file_path = original_path

    def test_save_and_load_trades(self, tmp_path):
        import cw_trading_system.data.trade_store as ts
        original_path = ts._trade_repo.file_path
        ts._trade_repo.file_path = str(tmp_path / "trades.json")
        ts._trade_repo._ensure_file_exists()

        trades = [{"test": "data"}]
        save_trades(trades)
        loaded = load_trades()
        assert loaded == trades
        
        ts._trade_repo.file_path = original_path

    def test_record_trade(self, tmp_path):
        import cw_trading_system.data.trade_store as ts
        original_path = ts._trade_repo.file_path
        ts._trade_repo.file_path = str(tmp_path / "trades.json")
        ts._trade_repo._ensure_file_exists()

        record_trade("HPG", "BUY", 1000, 25.0)

        trades = load_trades()
        assert len(trades) == 1
        assert trades[0]["underlying"] == "HPG"
        assert trades[0]["action"] == "BUY"
        assert trades[0]["size"] == 1000
        assert trades[0]["price"] == 25.0
        assert "time" in trades[0]
        
        ts._trade_repo.file_path = original_path