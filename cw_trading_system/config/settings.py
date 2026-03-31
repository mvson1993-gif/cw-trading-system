# config/settings.py

from dataclasses import dataclass

# =========================
# MARKET ASSUMPTIONS
# =========================

RISK_FREE_RATE = 0.05   # 5% VN risk-free proxy
TRADING_DAYS = 252

# Vol fallback if missing
DEFAULT_VOL = 0.30


# =========================
# RISK LIMITS (DESK LEVEL)
# =========================

@dataclass
class RiskLimits:
    max_delta: float = 2_000_000        # shares equivalent
    max_gamma: float = 50_000           # sensitivity cap
    max_vega: float = 200_000
    max_position_per_cw: int = 5_000_000
    max_loss_daily: float = -5_000_000_000  # VND


RISK_LIMITS = RiskLimits()


# =========================
# HEDGING POLICY
# =========================

@dataclass
class HedgePolicy:
    delta_band: float = 100_000     # no hedge if within band
    hedge_ratio: float = 1.0        # 100% hedge
    min_trade_size: int = 10_000    # avoid micro trades


HEDGE_POLICY = HedgePolicy()


# =========================
# STRESS SCENARIOS
# =========================

STRESS_SHOCKS = [
    -0.10,
    -0.05,
    0.05,
    0.10
]


# =========================
# PRICING SETTINGS
# =========================

@dataclass
class PricingConfig:
    use_intrinsic_proxy: bool = True
    vol_shift: float = 0.0     # for stress later


PRICING_CONFIG = PricingConfig()
