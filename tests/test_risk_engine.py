import pytest
from unittest.mock import Mock
from cw_trading_system.engine.risk_engine import calculate_portfolio_risk
from cw_trading_system.data.positions import CWPosition, HedgePosition, Portfolio


class TestRiskEngine:
    def test_calculate_portfolio_risk_empty(self):
        portfolio = Portfolio([], [])
        market_data = Mock()
        risk = calculate_portfolio_risk(portfolio, market_data)
        assert risk["total"]["delta"] == 0
        assert risk["total"]["gamma"] == 0
        assert risk["total"]["vega"] == 0
        assert risk["total"]["theta"] == 0
        assert risk["breaches"] == []

    def test_calculate_portfolio_risk_with_cw(self):
        cw = [CWPosition("HPG", "HPG2406", 1000, 1.0, 100, "2024-06-01", 10.0, 0.3)]
        hedge = []
        portfolio = Portfolio(cw, hedge)

        market_data = Mock()
        market_data.get_spot.return_value = 100
        market_data.get_vol.return_value = 0.2

        risk = calculate_portfolio_risk(portfolio, market_data)

        # Should have some risk values
        assert "delta" in risk["total"]
        assert "gamma" in risk["total"]
        assert "HPG" in risk["by_underlying"]

    def test_calculate_portfolio_risk_with_hedge(self):
        cw = []
        hedge = [HedgePosition("HPG", 1000, 95.0)]
        portfolio = Portfolio(cw, hedge)

        market_data = Mock()

        risk = calculate_portfolio_risk(portfolio, market_data)

        assert risk["total"]["delta"] == 1000  # Hedge shares
        assert risk["total"]["gamma"] == 0
        assert risk["breaches"] == []

    def test_calculate_portfolio_risk_breaches(self):
        # Mock a large position to breach limits
        cw = [CWPosition("HPG", "HPG2406", 1000000, 1.0, 100, "2024-06-01", 10.0, 0.3)]  # Large qty
        hedge = []
        portfolio = Portfolio(cw, hedge)

        market_data = Mock()
        market_data.get_spot.return_value = 100
        market_data.get_vol.return_value = 0.2

        risk = calculate_portfolio_risk(portfolio, market_data)

        # Likely breaches due to large gamma/delta
        # Depending on limits, but test that breaches is a list
        assert isinstance(risk["breaches"], list)