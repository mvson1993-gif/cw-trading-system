# data/market_data.py

from typing import Dict
from config.settings import DEFAULT_VOL
from models.vol_surface import VolSurface

# =========================
# SPOT DATA PROVIDER
# =========================

class SpotProvider:

    def __init__(self):
        # placeholder for future API
        self.mock_prices = {
            "HPG.VN": 25.0,
            "MWG.VN": 58.0
        }

    def get_spot(self, ticker: str) -> float:
        if ticker in self.mock_prices:
            return self.mock_prices[ticker]

        raise ValueError(f"No spot data for {ticker}")


# =========================
# VOLATILITY PROVIDER
# =========================

class VolatilityProvider:

    def __init__(self):

        # manual trader overrides
        self.override_vol: Dict[str, float] = {}

        # mock market vol (replace later)
        self.market_vol = {
            "HPG.VN": 0.32,
            "MWG.VN": 0.28
        }

    def set_override(self, ticker: str, vol: float):
        self.override_vol[ticker] = vol

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

        # ---- spot (mock for now) ----
        self.spot_data = {
            "HPG.VN": 25.0,
            "MWG.VN": 60.0
        }

        # ---- vol surface ----
        self.vol_surface = VolSurface()

    # =========================
    # SPOT
    # =========================

    def get_spot(self, ticker: str) -> float:

        return self.spot_data.get(ticker, 25.0)

    # =========================
    # VOL
    # =========================

    def get_vol(self, ticker: str, strike=None, T=None) -> float:

        spot = self.get_spot(ticker)

        # if we have full info → use surface
        if strike is not None and T is not None:
            return self.vol_surface.get_vol(ticker, strike, spot, T)

        # fallback (legacy)
        return 0.30
