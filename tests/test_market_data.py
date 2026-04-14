import pytest
from unittest.mock import patch, MagicMock
from cw_trading_system.data.market_data import SpotProvider, VolatilityProvider, MarketDataService, MarketDataMonitor
from cw_trading_system.data.market_data_scheduler import MarketDataScheduler


class TestSpotProvider:
    @patch('yfinance.Ticker')
    def test_init(self, mock_ticker):
        sp = SpotProvider()
        assert "HPG.VN" in sp.mock_prices
        assert "MWG.VN" in sp.mock_prices

    @patch('yfinance.Ticker')
    def test_get_spot_live_success(self, mock_ticker_class):
        mock_ticker = MagicMock()
        mock_ticker.info = {'regularMarketPrice': 30.0}
        mock_ticker_class.return_value = mock_ticker

        sp = SpotProvider()
        spot = sp.get_spot("HPG.VN")
        assert spot == 30.0
        mock_ticker_class.assert_called_with("HPG.VN")

    @patch('yfinance.Ticker')
    def test_get_spot_live_failure_fallback(self, mock_ticker_class):
        mock_ticker_class.side_effect = Exception("API error")

        sp = SpotProvider()
        spot = sp.get_spot("HPG.VN")
        assert spot == 25.0  # fallback

    @patch('yfinance.Ticker')
    def test_get_spot_unknown(self, mock_ticker_class):
        mock_ticker_class.side_effect = Exception("API error")

        sp = SpotProvider()
        # Now returns default price instead of raising error for robustness
        spot = sp.get_spot("UNKNOWN")
        assert spot == 100.0  # default fallback price


class TestVolatilityProvider:
    def test_init(self):
        vp = VolatilityProvider()
        assert "HPG.VN" in vp.market_vol
        assert "MWG.VN" in vp.market_vol
        assert vp.override_vol == {}

    def test_get_vol_market(self):
        vp = VolatilityProvider()
        vol = vp.get_vol("HPG.VN")
        assert vol == 0.32

    def test_get_vol_override(self):
        vp = VolatilityProvider()
        vp.set_override("HPG.VN", 0.40)
        vol = vp.get_vol("HPG.VN")
        assert vol == 0.40

    def test_get_vol_unknown(self):
        vp = VolatilityProvider()
        vol = vp.get_vol("UNKNOWN")
        # Should return DEFAULT_VOL from settings
        from cw_trading_system.config.settings import DEFAULT_VOL
        assert vol == DEFAULT_VOL

    def test_set_override(self):
        vp = VolatilityProvider()
        vp.set_override("TEST", 0.50)
        assert vp.override_vol["TEST"] == 0.50


class TestMarketDataService:
    @patch('yfinance.Ticker')
    def test_get_spot(self, mock_ticker_class):
        mock_ticker = MagicMock()
        mock_ticker.info = {'regularMarketPrice': 35.0}
        mock_ticker_class.return_value = mock_ticker

        mds = MarketDataService()
        spot = mds.get_spot("HPG.VN")
        assert spot == 35.0

    def test_get_vol_simple(self):
        mds = MarketDataService()
        vol = mds.get_vol("HPG.VN")
        assert vol == 0.32  # from market_vol


class TestMarketDataMonitor:
    def test_check_data_freshness(self):
        mds = MarketDataService()
        monitor = MarketDataMonitor(mds)
        
        results = monitor.check_data_freshness(["HPG.VN"])
        
        assert "HPG.VN" in results
        assert results["HPG.VN"]["status"] == "fresh"
        assert "spot" in results["HPG.VN"]


class TestMarketDataScheduler:
    def test_init(self):
        scheduler = MarketDataScheduler()
        assert not scheduler.is_running
        assert scheduler.tickers == ["HPG.VN", "MWG.VN"]

    def test_get_monitor_status(self):
        scheduler = MarketDataScheduler()
        status = scheduler.get_monitor_status()
        assert 'is_running' in status
        assert 'last_check' in status
        assert 'market_alerts' in status
        assert 'risk_alerts' in status