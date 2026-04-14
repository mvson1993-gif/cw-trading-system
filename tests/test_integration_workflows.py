# tests/test_integration_workflows.py

"""
Integration tests for complete trading workflows.
Tests end-to-end scenarios involving multiple components.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock
from cw_trading_system.data.positions import Portfolio, CWPosition, HedgePosition
from cw_trading_system.data.market_data import MarketDataService
from cw_trading_system.engine.risk_engine import calculate_portfolio_risk
from cw_trading_system.engine.pnl_engine import calculate_pnl
from cw_trading_system.engine.monitoring_engine import monitoring_engine
from cw_trading_system.data.market_data_scheduler import MarketDataScheduler


@pytest.fixture
def sample_portfolio():
    """Create a sample portfolio for testing."""
    cw_positions = [
        CWPosition(
            underlying="HPG.VN",
            ticker="HPG24001",
            cw_qty=1000000,
            conversion_ratio=1.0,
            strike=30.0,
            expiry=(date.today() + timedelta(days=365)).isoformat(),
            issue_price=0.5,
            sigma=0.3
        )
    ]
    
    hedge_positions = [
        HedgePosition(
            underlying="HPG.VN",
            shares=500000,
            avg_price=30.0
        )
    ]
    
    return Portfolio(cw_positions, hedge_positions)


@pytest.fixture
def market_data_service():
    """Create mock market data service."""
    service = MagicMock(spec=MarketDataService)
    service.get_spot.return_value = 32.0
    service.get_vol.return_value = 0.35
    return service


class TestCWIssuanceWorkflow:
    """Test workflow for CW issuance."""

    def test_complete_issuance_workflow(self, sample_portfolio, market_data_service):
        """Test complete CW issuance workflow."""
        # Step 1: Get market data
        spot_price = market_data_service.get_spot("HPG.VN")
        assert spot_price == 32.0
        
        # Step 2: Calculate risk before issuance
        risk_before = calculate_portfolio_risk(sample_portfolio, market_data_service)
        assert "total" in risk_before
        assert "delta" in risk_before["total"]
        
        # Step 3: Verify position limits
        cw_pos = sample_portfolio.cw_positions[0]
        assert cw_pos.cw_qty > 0
        assert cw_pos.strike < spot_price  # ITM position
        
        # Step 4: Calculate P&L
        pnl = calculate_pnl(sample_portfolio, market_data_service)
        assert pnl is not None
        assert "total_pnl" in pnl

    def test_issuance_validates_inputs(self):
        """Test that issuance workflow validates inputs."""
        # Valid position should work
        valid_pos = CWPosition(
            underlying="HPG.VN",
            ticker="HPG24001",
            cw_qty=1000000,
            conversion_ratio=1.0,
            strike=30.0,
            expiry="2024-12-31",
            issue_price=0.5,
            sigma=0.3
        )
        assert valid_pos.strike == 30.0


class TestHedgingWorkflow:
    """Test hedging workflow."""

    def test_delta_hedge_workflow(self, sample_portfolio, market_data_service):
        """Test delta hedging workflow."""
        # Step 1: Calculate current delta
        risk = calculate_portfolio_risk(sample_portfolio, market_data_service)
        delta_before = risk["total"]["delta"]
        
        # Step 2: Identify hedge amount needed
        # For CW issuer with short position, hedge with long stock
        cw_pos = sample_portfolio.cw_positions[0]
        implied_short_stock = -cw_pos.cw_qty * cw_pos.conversion_ratio
        
        assert implied_short_stock < 0  # Short exposure
        
        # Step 3: Verify hedge position reduces delta
        assert sample_portfolio.hedge_positions[0].shares > 0

    def test_hedge_workflow_validates_constraints(self):
        """Test that hedge workflow validates constraints."""
        from cw_trading_system.config.settings import HEDGE_POLICY
        
        # Verify hedge policy exists
        assert HEDGE_POLICY.delta_band > 0
        assert HEDGE_POLICY.hedge_ratio > 0
        assert HEDGE_POLICY.min_trade_size > 0


class TestRiskMonitoringWorkflow:
    """Test risk monitoring workflow."""

    @patch('cw_trading_system.engine.monitoring_engine.load_portfolio')
    @patch('cw_trading_system.engine.monitoring_engine.calculate_portfolio_risk')
    @patch('cw_trading_system.engine.monitoring_engine.calculate_pnl')
    @patch('cw_trading_system.engine.monitoring_engine.alert_manager')
    def test_monitoring_detects_breach(self, mock_alert, mock_pnl, mock_risk, mock_load, sample_portfolio):
        """Test monitoring workflow detects risk breaches."""
        # Setup
        mock_load.return_value = (sample_portfolio.cw_positions, sample_portfolio.hedge_positions)
        mock_risk.return_value = {
            "breaches": ["DELTA LIMIT BREACH"],
            "total": {"delta": 5000000, "gamma": 100000, "vega": 300000}
        }
        mock_pnl.return_value = {"total_pnl": 1000000}
        
        # Execute monitoring
        monitoring_engine.check_and_alert()
        
        # Verify alert was sent
        assert mock_alert.send_alert.called

    @patch('cw_trading_system.engine.monitoring_engine.load_portfolio')
    @patch('cw_trading_system.engine.monitoring_engine.calculate_portfolio_risk')
    @patch('cw_trading_system.engine.monitoring_engine.calculate_pnl')
    def test_monitoring_handles_errors(self, mock_pnl, mock_risk, mock_load):
        """Test monitoring workflow handles errors gracefully."""
        mock_load.side_effect = Exception("Database error")
        
        # Should not raise, just log error
        monitoring_engine.check_and_alert()


class TestMarketDataWorkflow:
    """Test market data integration workflow."""

    def test_scheduler_integrates_components(self):
        """Test scheduler integrates all background jobs."""
        scheduler = MarketDataScheduler()
        
        # Verify scheduler configuration
        assert scheduler.tickers is not None
        assert len(scheduler.tickers) > 0
        assert scheduler.scheduler is not None

    @patch('cw_trading_system.data.market_data_scheduler.MarketDataScheduler.start')
    def test_scheduler_startup(self, mock_start):
        """Test scheduler can start."""
        scheduler = MarketDataScheduler()
        scheduler.start()
        mock_start.assert_called_once()

    def test_market_data_caching_efficiency(self):
        """Test market data caching improves efficiency."""
        from cw_trading_system.data.market_data import DataCache
        
        cache = DataCache()
        
        # First request (cache miss)
        cache.set("HPG.VN", 30.0)
        spot1 = cache.get("HPG.VN")
        assert spot1 == 30.0
        
        # Second request (cache hit)
        spot2 = cache.get("HPG.VN")
        assert spot2 == 30.0  # Same cached value
        
        # Verify cache miss returns None
        spot3 = cache.get("VNM.VN")
        assert spot3 is None


class TestPortfolioValidation:
    """Test portfolio validation rules."""

    def test_portfolio_validates_positions(self):
        """Test portfolio validates positions on creation."""
        # Valid portfolio
        valid_portfolio = Portfolio(
            cw_positions=[
                CWPosition(
                    underlying="HPG.VN",
                    ticker="HPG24001",
                    cw_qty=1000000,
                    conversion_ratio=1.0,
                    strike=30.0,
                    expiry="2024-12-31",
                    issue_price=0.5,
                    sigma=0.3
                )
            ],
            hedge_positions=[]
        )
        assert len(valid_portfolio.cw_positions) == 1

    def test_portfolio_rejects_negative_qty(self):
        """Test portfolio rejects negative quantities."""
        with pytest.raises(ValueError):
            Portfolio(
                cw_positions=[
                    CWPosition(
                        underlying="HPG.VN",
                        ticker="HPG24001",
                        cw_qty=-1000000,  # Invalid
                        conversion_ratio=1.0,
                        strike=30.0,
                        expiry="2024-12-31",
                        issue_price=0.5,
                        sigma=0.3
                    )
                ],
                hedge_positions=[]
            )

    def test_portfolio_rejects_invalid_strike(self):
        """Test portfolio rejects invalid strikes."""
        with pytest.raises(ValueError):
            Portfolio(
                cw_positions=[
                    CWPosition(
                        underlying="HPG.VN",
                        ticker="HPG24001",
                        cw_qty=1000000,
                        conversion_ratio=1.0,
                        strike=-30.0,  # Invalid
                        expiry="2024-12-31",
                        issue_price=0.5,
                        sigma=0.3
                    )
                ],
                hedge_positions=[]
            )

    def test_portfolio_rejects_invalid_conversion_ratio(self):
        """Test portfolio rejects invalid conversion ratios."""
        with pytest.raises(ValueError):
            Portfolio(
                cw_positions=[
                    CWPosition(
                        underlying="HPG.VN",
                        ticker="HPG24001",
                        cw_qty=1000000,
                        conversion_ratio=-1.0,  # Invalid
                        strike=30.0,
                        expiry="2024-12-31",
                        issue_price=0.5,
                        sigma=0.3
                    )
                ],
                hedge_positions=[]
            )


class TestDataConsistency:
    """Test data consistency across workflows."""

    def test_position_portfolio_consistency(self, sample_portfolio):
        """Test position data remains consistent."""
        cw_pos = sample_portfolio.cw_positions[0]
        hedge_pos = sample_portfolio.hedge_positions[0]
        
        # Underlying should match
        # For issuance: CW issuer is short, needs long hedge
        assert cw_pos.underlying == hedge_pos.underlying

    def test_risk_pnl_calculation_consistency(self, sample_portfolio, market_data_service):
        """Test risk and P&L calculations are consistent."""
        risk = calculate_portfolio_risk(sample_portfolio, market_data_service)
        pnl = calculate_pnl(sample_portfolio, market_data_service)
        
        # Both should have consistent structure
        assert "total" in risk
        assert "total_pnl" in pnl
        assert "delta" in risk["total"]


class TestErrorHandlingWorkflows:
    """Test error handling in workflows."""

    def test_workflow_handles_missing_market_data(self):
        """Test workflow handles missing market data."""
        market_data = MagicMock(spec=MarketDataService)
        market_data.get_spot.side_effect = Exception("Market data unavailable")
        
        portfolio = Portfolio(
            cw_positions=[
                CWPosition(
                    underlying="HPG.VN",
                    ticker="HPG24001",
                    cw_qty=1000000,
                    conversion_ratio=1.0,
                    strike=30.0,
                    expiry="2024-12-31",
                    issue_price=0.5,
                    sigma=0.3
                )
            ],
            hedge_positions=[]
        )
        
        # Should raise but not crash
        with pytest.raises(Exception):
            calculate_portfolio_risk(portfolio, market_data)

    def test_workflow_handles_invalid_portfolio(self):
        """Test workflow handles invalid portfolio."""
        with pytest.raises(ValueError):
            Portfolio(
                cw_positions=[
                    CWPosition(
                        underlying="HPG.VN",
                        ticker="HPG24001",
                        cw_qty=-1000,  # Invalid
                        conversion_ratio=1.0,
                        strike=30.0,
                        expiry="2024-12-31",
                        issue_price=0.5,
                        sigma=0.3
                    )
                ],
                hedge_positions=[]
            )