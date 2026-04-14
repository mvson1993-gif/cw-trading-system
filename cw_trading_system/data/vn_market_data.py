# data/vn_market_data.py

import requests
import time
import json
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import websocket
import threading
from ..config.settings import VN_MARKET_CONFIG
from ..utils.logging import get_logger
from ..utils.performance import timed
from .cache import DataCache

logger = get_logger(__name__)


class VNMarketDataError(Exception):
    """VN Market Data API error."""
    pass


class VNDirectAPI:
    """VNDirect API client for VN market data."""

    def __init__(self):
        self.base_url = VN_MARKET_CONFIG.vndirect_base_url
        self.api_key = VN_MARKET_CONFIG.vndirect_api_key
        self.api_secret = VN_MARKET_CONFIG.vndirect_api_secret
        self.session = requests.Session()
        self.cache = DataCache()
        self._auth_token = None
        self._token_expiry = None

    def _authenticate(self) -> str:
        """Authenticate with VNDirect API."""
        if self._auth_token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._auth_token

        try:
            auth_url = f"{self.base_url}/auth"
            auth_data = {
                "api_key": self.api_key,
                "api_secret": self.api_secret
            }

            response = self.session.post(auth_url, json=auth_data, timeout=30)
            response.raise_for_status()

            data = response.json()
            self._auth_token = data.get("access_token")
            # Assume token expires in 1 hour
            self._token_expiry = datetime.now() + timedelta(hours=1)

            self.session.headers.update({"Authorization": f"Bearer {self._auth_token}"})
            return self._auth_token

        except Exception as e:
            logger.error(f"VNDirect authentication failed: {e}")
            raise VNMarketDataError(f"Authentication failed: {e}")

    def get_spot_price(self, ticker: str) -> Optional[float]:
        """Get spot price for a ticker."""
        try:
            if not VN_MARKET_CONFIG.vndirect_enabled:
                return None

            self._authenticate()

            url = f"{self.base_url}/v1/stocks/{ticker}/price"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            price = data.get("lastPrice") or data.get("closePrice")

            if price and isinstance(price, (int, float)):
                return float(price)

        except Exception as e:
            logger.warning(f"VNDirect spot price fetch failed for {ticker}: {e}")

        return None

    def get_historical_data(self, ticker: str, days: int = 30) -> Optional[Dict]:
        """Get historical OHLCV data."""
        try:
            if not VN_MARKET_CONFIG.vndirect_enabled:
                return None

            self._authenticate()

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            params = {
                "symbol": ticker,
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d")
            }

            url = f"{self.base_url}/v1/stocks/{ticker}/historical"
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.warning(f"VNDirect historical data fetch failed for {ticker}: {e}")

        return None


class SSIAPI:
    """SSI API client for VN market data."""

    def __init__(self):
        self.base_url = VN_MARKET_CONFIG.ssi_base_url
        self.api_key = VN_MARKET_CONFIG.ssi_api_key
        self.api_secret = VN_MARKET_CONFIG.ssi_api_secret
        self.session = requests.Session()
        self.cache = DataCache()

    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        return {
            "X-API-Key": self.api_key,
            "X-API-Secret": self.api_secret,
            "Content-Type": "application/json"
        }

    def get_spot_price(self, ticker: str) -> Optional[float]:
        """Get spot price for a ticker."""
        try:
            if not VN_MARKET_CONFIG.ssi_enabled:
                return None

            url = f"{self.base_url}/v1/market/stock/{ticker}"
            response = self.session.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()

            data = response.json()
            price = data.get("lastPrice") or data.get("closePrice")

            if price and isinstance(price, (int, float)):
                return float(price)

        except Exception as e:
            logger.warning(f"SSI spot price fetch failed for {ticker}: {e}")

        return None

    def get_market_overview(self) -> Optional[Dict]:
        """Get market overview data."""
        try:
            if not VN_MARKET_CONFIG.ssi_enabled:
                return None

            url = f"{self.base_url}/v1/market/overview"
            response = self.session.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.warning(f"SSI market overview fetch failed: {e}")

        return None


class FTSAPI:
    """FTS API client for VN market data."""

    def __init__(self):
        self.base_url = VN_MARKET_CONFIG.fts_base_url
        self.api_key = VN_MARKET_CONFIG.fts_api_key
        self.api_secret = VN_MARKET_CONFIG.fts_api_secret
        self.session = requests.Session()
        self.cache = DataCache()

    def _authenticate(self) -> None:
        """Authenticate with FTS API."""
        try:
            auth_url = f"{self.base_url}/oauth/token"
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret
            }

            response = self.session.post(auth_url, data=auth_data, timeout=30)
            response.raise_for_status()

            data = response.json()
            token = data.get("access_token")

            self.session.headers.update({"Authorization": f"Bearer {token}"})

        except Exception as e:
            logger.error(f"FTS authentication failed: {e}")
            raise VNMarketDataError(f"Authentication failed: {e}")

    def get_spot_price(self, ticker: str) -> Optional[float]:
        """Get spot price for a ticker."""
        try:
            if not VN_MARKET_CONFIG.fts_enabled:
                return None

            if not self.session.headers.get("Authorization"):
                self._authenticate()

            url = f"{self.base_url}/api/v1/stocks/{ticker}/quote"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            price = data.get("last") or data.get("close")

            if price and isinstance(price, (int, float)):
                return float(price)

        except Exception as e:
            logger.warning(f"FTS spot price fetch failed for {ticker}: {e}")

        return None


class WebSocketStreamer:
    """WebSocket client for real-time market data streaming."""

    def __init__(self, callback=None):
        self.ws_url = VN_MARKET_CONFIG.websocket_url
        self.ws = None
        self.callback = callback or self._default_callback
        self.is_connected = False
        self.subscribed_tickers = set()
        self.thread = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    def _default_callback(self, data: Dict) -> None:
        """Default callback for received data."""
        logger.info(f"Received WebSocket data: {data}")

    def connect(self) -> bool:
        """Connect to WebSocket."""
        if not VN_MARKET_CONFIG.websocket_enabled:
            logger.info("WebSocket streaming disabled")
            return False

        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )

            self.thread = threading.Thread(target=self.ws.run_forever)
            self.thread.daemon = True
            self.thread.start()

            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if self.is_connected:
                logger.info("WebSocket connected successfully")
                return True
            else:
                logger.error("WebSocket connection timeout")
                return False

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        if self.ws:
            self.ws.close()
        self.is_connected = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def subscribe(self, tickers: List[str]) -> None:
        """Subscribe to ticker updates."""
        if not self.is_connected:
            logger.warning("WebSocket not connected, cannot subscribe")
            return

        try:
            subscription_msg = {
                "action": "subscribe",
                "symbols": tickers
            }

            self.ws.send(json.dumps(subscription_msg))
            self.subscribed_tickers.update(tickers)
            logger.info(f"Subscribed to tickers: {tickers}")

        except Exception as e:
            logger.error(f"Subscription failed: {e}")

    def unsubscribe(self, tickers: List[str]) -> None:
        """Unsubscribe from ticker updates."""
        if not self.is_connected:
            return

        try:
            unsubscription_msg = {
                "action": "unsubscribe",
                "symbols": tickers
            }

            self.ws.send(json.dumps(unsubscription_msg))
            self.subscribed_tickers.difference_update(tickers)
            logger.info(f"Unsubscribed from tickers: {tickers}")

        except Exception as e:
            logger.error(f"Unsubscription failed: {e}")

    def _on_open(self, ws) -> None:
        """WebSocket open callback."""
        self.is_connected = True
        self.reconnect_attempts = 0
        logger.info("WebSocket connection opened")

    def _on_message(self, ws, message) -> None:
        """WebSocket message callback."""
        try:
            data = json.loads(message)
            self.callback(data)
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    def _on_error(self, ws, error) -> None:
        """WebSocket error callback."""
        logger.error(f"WebSocket error: {error}")
        self.is_connected = False

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """WebSocket close callback."""
        logger.info(f"WebSocket connection closed: {close_status_code}, {close_msg}")
        self.is_connected = False

        # Auto-reconnect logic
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Attempting to reconnect ({self.reconnect_attempts}/{self.max_reconnect_attempts})")
            time.sleep(2 ** self.reconnect_attempts)  # Exponential backoff
            self.connect()


class VNMarketDataProvider:
    """Unified VN market data provider with fallback chain."""

    def __init__(self):
        self.providers = {
            "vndirect": VNDirectAPI(),
            "ssi": SSIAPI(),
            "fts": FTSAPI()
        }
        self.websocket_streamer = WebSocketStreamer(callback=self._websocket_callback)
        self.real_time_prices = {}  # Cache for real-time prices

    def _websocket_callback(self, data: Dict) -> None:
        """Handle real-time WebSocket data."""
        try:
            if "symbol" in data and "price" in data:
                ticker = data["symbol"]
                price = data["price"]
                self.real_time_prices[ticker] = {
                    "price": price,
                    "timestamp": time.time()
                }
                logger.debug(f"Real-time price update: {ticker} = {price}")
        except Exception as e:
            logger.error(f"Error processing WebSocket callback: {e}")

    def get_spot_price(self, ticker: str) -> Optional[float]:
        """Get spot price using provider priority chain."""

        # Check real-time cache first (if WebSocket connected)
        if ticker in self.real_time_prices:
            entry = self.real_time_prices[ticker]
            if time.time() - entry['timestamp'] < 60:  # 1 minute freshness
                return entry['price']

        # Try providers in priority order
        for provider_name in VN_MARKET_CONFIG.provider_priority:
            if provider_name == "mock":
                continue  # Skip mock, handled by main market_data.py

            provider = self.providers.get(provider_name)
            if provider:
                price = provider.get_spot_price(ticker)
                if price is not None:
                    logger.info(f"Got price from {provider_name}: {ticker} = {price}")
                    return price

        logger.warning(f"No price found for {ticker} from VN providers")
        return None

    def get_historical_data(self, ticker: str, days: int = 30) -> Optional[Dict]:
        """Get historical data from primary provider."""
        provider = self.providers.get("vndirect")  # VNDirect has best historical data
        if provider:
            return provider.get_historical_data(ticker, days)
        return None

    def get_market_overview(self) -> Optional[Dict]:
        """Get market overview from SSI."""
        provider = self.providers.get("ssi")
        if provider:
            return provider.get_market_overview()
        return None

    def start_real_time_streaming(self, tickers: List[str]) -> bool:
        """Start real-time streaming for tickers."""
        if self.websocket_streamer.connect():
            self.websocket_streamer.subscribe(tickers)
            return True
        return False

    def stop_real_time_streaming(self) -> None:
        """Stop real-time streaming."""
        self.websocket_streamer.disconnect()