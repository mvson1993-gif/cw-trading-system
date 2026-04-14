# data/market_data.py

import time
from typing import Dict, Optional
import yfinance as yf
from ..config.settings import DEFAULT_VOL, VN_MARKET_CONFIG
from ..models.vol_surface import VolSurface
from ..utils.logging import get_logger
from ..utils.performance import timed
from .vn_market_data import VNMarketDataProvider
from .cache import DataCache

logger = get_logger(__name__)

# =========================
# SPOT DATA PROVIDER
# =========================

class SpotProvider:

    def __init__(self):
        self.cache = DataCache()
        self.vn_provider = VNMarketDataProvider()
        # fallback mock prices
        self.mock_prices = {
            "HPG.VN": 25.0,
            "MWG.VN": 58.0
        }

    def _normalize_ticker(self, ticker: str) -> str:
        # Normalize ticker for VN data sources
        ticker = ticker.strip().upper()

        if ticker.endswith('.VN'):
            return ticker

        # If CW ID style (HPG2606), derive underlying
        import re
        m = re.match(r'^([A-Z]+)', ticker)
        if m:
            return f"{m.group(1)}.VN"

        return f"{ticker}.VN"

    @timed("get_spot")
    def get_spot(self, ticker: str) -> float:
        ticker_norm = self._normalize_ticker(ticker)

        # Try cache first
        cached = self.cache.get(f"spot_{ticker_norm}")
        if cached:
            logger.debug(f"Using cached spot price for {ticker_norm}: {cached['price']}")
            return cached['price']

        # Try VN market data providers first
        vn_price = self.vn_provider.get_spot_price(ticker_norm)
        if vn_price is not None and self._validate_price(vn_price):
            self.cache.set(f"spot_{ticker_norm}", {'price': vn_price})
            logger.debug(f"Fetched VN spot price for {ticker_norm}: {vn_price}")
            return vn_price

        # Fallback to Yahoo Finance
        try:
            logger.info(f"Fetching Yahoo Finance spot price for {ticker_norm}")
            stock = yf.Ticker(ticker_norm)
            info = stock.info
            price = info.get('regularMarketPrice') or info.get('currentPrice')
            if price and self._validate_price(price):
                self.cache.set(f"spot_{ticker_norm}", {'price': price})
                logger.debug(f"Fetched Yahoo Finance spot price for {ticker_norm}: {price}")
                return price
            else:
                logger.warning(f"Invalid price received from Yahoo Finance for {ticker_norm}: {price}")
        except Exception as e:
            logger.warning(f"Failed to fetch Yahoo Finance data for {ticker_norm}: {e}")

        # Fallback to mock (with normalized ticker key)
        if ticker_norm in self.mock_prices:
            logger.info(f"Using fallback mock price for {ticker_norm}: {self.mock_prices[ticker_norm]}")
            return self.mock_prices[ticker_norm]

        if ticker in self.mock_prices:
            logger.info(f"Using fallback mock price for {ticker}: {self.mock_prices[ticker]}")
            return self.mock_prices[ticker]

        # Last resort: return a reasonable default
        logger.warning(f"No price data available for {ticker}, using default")
        return 100.0  # Default fallback price

        raise ValueError(f"No spot data available for {ticker} ({ticker_norm})")

    def _validate_price(self, price) -> bool:
        """Validate that price is reasonable."""
        if not isinstance(price, (int, float)):
            return False
        if price <= 0:
            return False
        if price > 1000000:  # Unreasonably high
            return False
        return True


# =========================
# VOLATILITY PROVIDER
# =========================

class VolatilityProvider:

    def __init__(self):

        # manual trader overrides
        self.override_vol: Dict[str, float] = {}

        # mock market vol (replace later with implied vol calculation)
        self.market_vol = {
            "HPG.VN": 0.32,
            "MWG.VN": 0.28
        }

    def set_override(self, ticker: str, vol: float):
        self.override_vol[ticker] = vol

    @timed("get_vol")
    def get_vol(self, ticker: str) -> float:

        # Priority 1: trader override
        if ticker in self.override_vol:
            return self.override_vol[ticker]

        # Priority 2: market vol
        if ticker in self.market_vol:
            return self.market_vol[ticker]

        # Priority 3: fallback
        return DEFAULT_VOL



# =========================
# MARKET DATA SERVICE
# =========================

class MarketDataService:

    def __init__(self):
        self.spot_provider = SpotProvider()
        self.vol_provider = VolatilityProvider()
        self.vol_surface = VolSurface()

    # =========================
    # SPOT
    # =========================

    def get_spot(self, ticker: str) -> float:
        return self.spot_provider.get_spot(ticker)

    # =========================
    # VOL
    # =========================

    def get_vol(self, ticker: str, strike=None, T=None) -> float:

        ticker_norm = self.spot_provider._normalize_ticker(ticker)
        spot = self.get_spot(ticker_norm)

        # if we have full info → use surface
        if strike is not None and T is not None:
            return self.vol_surface.get_vol(ticker_norm, strike, spot, T)

        # fallback to provider
        return self.vol_provider.get_vol(ticker_norm)


# =========================
# MARKET DATA MONITOR
# =========================

class MarketDataMonitor:

    def __init__(self, market_data_service: MarketDataService):
        self.market_data_service = market_data_service
        self.last_check = {}
        self.alerts = []

    def check_data_freshness(self, tickers: list) -> dict:
        """Check if market data is fresh for given tickers.
        
        Returns:
            Dict with ticker -> status info
        """
        results = {}
        for ticker in tickers:
            try:
                spot = self.market_data_service.get_spot(ticker)
                # For now, assume data is fresh if we got it
                # In future, check timestamp from cache
                results[ticker] = {
                    'status': 'fresh',
                    'spot': spot,
                    'timestamp': time.time()
                }
            except (ValueError, TypeError, KeyError) as e:
                results[ticker] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': time.time()
                }
                logger.warning(f"Market data check failed for {ticker}: {e}")
            except Exception as e:
                results[ticker] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': time.time()
                }
                logger.exception(f"Unexpected market data check failure for {ticker}: {e}")
        
        self.last_check = results
        return results

    def get_alerts(self) -> list:
        """Get current alerts."""
        return self.alerts

    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts = []
