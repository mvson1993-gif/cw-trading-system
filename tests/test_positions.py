import pytest
from datetime import date
from cw_trading_system.data.positions import CWPosition, HedgePosition, Portfolio


class TestCWPosition:
    def test_time_to_expiry(self):
        # Mock today as 2024-01-01 for testing
        pos = CWPosition("HPG", "HPG2606", 1000, 1.0, 100, "2026-06-01", 10.0, 0.3)
        # Assuming today is before 2024-06-01
        T = pos.time_to_expiry()
        assert T > 0

    def test_time_to_expiry_expired(self):
        pos = CWPosition("HPG", "HPG2000", 1000, 1.0, 100, "2000-01-01", 10.0, 0.3)
        T = pos.time_to_expiry()
        assert T == 0.0001  # Minimum


class TestHedgePosition:
    def test_init(self):
        hedge = HedgePosition("HPG", 1000, 95.0)
        assert hedge.underlying == "HPG"
        assert hedge.shares == 1000
        assert hedge.avg_price == 95.0


class TestPortfolio:
    def test_init_valid(self):
        cw = [CWPosition("HPG", "HPG2606", 1000, 1.0, 100, "2026-06-01", 10.0, 0.3)]
        hedge = [HedgePosition("HPG", 1000, 95.0)]
        portfolio = Portfolio(cw, hedge)
        assert len(portfolio.cw_positions) == 1
        assert len(portfolio.hedge_positions) == 1

    def test_init_invalid_cw_qty(self):
        cw = [CWPosition("HPG", "HPG2606", -1000, 1.0, 100, "2026-06-01", 10.0, 0.3)]
        hedge = []
        with pytest.raises(ValueError, match="Negative CW quantity"):
            Portfolio(cw, hedge)

    def test_init_invalid_strike(self):
        cw = [CWPosition("HPG", "HPG2406", 1000, 1.0, 0, "2024-06-01", 10.0, 0.3)]
        hedge = []
        with pytest.raises(ValueError, match="Invalid strike"):
            Portfolio(cw, hedge)

    def test_init_invalid_conversion_ratio(self):
        cw = [CWPosition("HPG", "HPG2406", 1000, 0, 100, "2024-06-01", 10.0, 0.3)]
        hedge = []
        with pytest.raises(ValueError, match="Invalid conversion ratio"):
            Portfolio(cw, hedge)

    def test_init_invalid_hedge_shares(self):
        cw = []
        hedge = [HedgePosition("HPG", -1000, 95.0)]
        with pytest.raises(ValueError, match="Negative hedge shares"):
            Portfolio(cw, hedge)

    def test_get_underlyings(self):
        cw = [
            CWPosition("HPG", "HPG2606", 1000, 1.0, 100, "2026-06-01", 10.0, 0.3),
            CWPosition("MWG", "MWG2606", 500, 1.0, 150, "2026-06-01", 15.0, 0.35)
        ]
        hedge = []
        portfolio = Portfolio(cw, hedge)
        underlyings = portfolio.get_underlyings()
        assert set(underlyings) == {"HPG", "MWG"}

    def test_get_cw_by_underlying(self):
        cw = [
            CWPosition("HPG", "HPG2606", 1000, 1.0, 100, "2026-06-01", 10.0, 0.3),
            CWPosition("HPG", "HPG2607", 500, 1.0, 105, "2026-07-01", 11.0, 0.3),
            CWPosition("MWG", "MWG2606", 500, 1.0, 150, "2026-06-01", 15.0, 0.35)
        ]
        hedge = []
        portfolio = Portfolio(cw, hedge)
        grouped = portfolio.get_cw_by_underlying()
        assert len(grouped["HPG"]) == 2
        assert len(grouped["MWG"]) == 1

    def test_get_hedge_dict(self):
        cw = []
        hedge = [
            HedgePosition("HPG", 1000, 95.0),
            HedgePosition("MWG", 500, 100.0)
        ]
        portfolio = Portfolio(cw, hedge)
        hedge_dict = portfolio.get_hedge_dict()
        assert hedge_dict["HPG"].shares == 1000
        assert hedge_dict["MWG"].shares == 500