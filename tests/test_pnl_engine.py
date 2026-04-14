import pytest
from unittest.mock import Mock
from cw_trading_system.engine.pnl_engine import calculate_pnl
from cw_trading_system.data.positions import CWPosition, HedgePosition, Portfolio


class TestPnlEngine:
    def test_calculate_pnl_empty(self):
        portfolio = Portfolio([], [])
        market_data = Mock()
        pnl = calculate_pnl(portfolio, market_data)
        assert pnl["cw_pnl"] == 0.0
        assert pnl["hedge_pnl"] == 0.0
        assert pnl["total_pnl"] == 0.0
        assert pnl["cw_price"] is None

    def test_calculate_pnl_cw_only(self):
        cw = [CWPosition("HPG", "HPG2406", 1000, 1.0, 100, "2024-06-01", 10.0, 0.3)]
        hedge = []
        portfolio = Portfolio(cw, hedge)

        market_data = Mock()
        market_data.get_spot.return_value = 100
        market_data.get_vol.return_value = 0.2

        pnl = calculate_pnl(portfolio, market_data)

        # CW P&L should be calculated
        assert "cw_pnl" in pnl
        assert "hedge_pnl" in pnl
        assert pnl["hedge_pnl"] == 0.0
        assert pnl["cw_price"] is not None

    def test_calculate_pnl_hedge_only(self):
        cw = []
        hedge = [HedgePosition("HPG", 1000, 95.0)]
        portfolio = Portfolio(cw, hedge)

        market_data = Mock()
        market_data.get_spot.return_value = 100  # Current price

        pnl = calculate_pnl(portfolio, market_data)

        # Hedge P&L: (100 - 95) * 1000 = 5000
        assert pnl["hedge_pnl"] == 5000.0
        assert pnl["cw_pnl"] == 0.0
        assert pnl["total_pnl"] == 5000.0

    def test_calculate_pnl_combined(self):
        cw = [CWPosition("HPG", "HPG2406", 1000, 1.0, 100, "2024-06-01", 10.0, 0.3)]
        hedge = [HedgePosition("HPG", 1000, 95.0)]
        portfolio = Portfolio(cw, hedge)

        market_data = Mock()
        market_data.get_spot.return_value = 100
        market_data.get_vol.return_value = 0.2

        pnl = calculate_pnl(portfolio, market_data)

        assert pnl["total_pnl"] == pnl["cw_pnl"] + pnl["hedge_pnl"]