# engine/risk_engine.py

from collections import defaultdict
import logging
from ..config.settings import RISK_FREE_RATE, RISK_LIMITS
from ..models.greeks import compute_greeks
from ..utils.performance import timed

logger = logging.getLogger(__name__)


@timed("calculate_portfolio_risk")
def calculate_portfolio_risk(portfolio, market_data):

    risk_by_underlying = defaultdict(lambda: {
        "delta": 0.0,
        "gamma": 0.0,
        "vega": 0.0,
        "theta": 0.0
    })

    for pos in portfolio.cw_positions:

        try:
            S = market_data.get_spot(pos.underlying)
        except ValueError as e:
            logger.warning(f"Skipping CW position {pos.ticker} without spot data: {e}")
            continue

        sigma = pos.sigma
        T = pos.time_to_expiry()

        greeks = compute_greeks(S, pos.strike, T, RISK_FREE_RATE, sigma)

        sign = -1  # issuer = short

        CR = pos.conversion_ratio
        Q = pos.cw_qty

        delta_exp = sign * greeks["delta"] * Q * CR
        gamma_exp = sign * greeks["gamma"] * Q * (CR ** 2)
        vega_exp  = sign * greeks["vega"]  * Q * CR
        theta_exp = sign * greeks["theta"] * Q * CR

        u = pos.underlying

        risk_by_underlying[u]["delta"] += delta_exp
        risk_by_underlying[u]["gamma"] += gamma_exp
        risk_by_underlying[u]["vega"]  += vega_exp
        risk_by_underlying[u]["theta"] += theta_exp

    # Hedge (stock = delta only)
    hedge_dict = portfolio.get_hedge_dict()

    for u, hedge in hedge_dict.items():
        risk_by_underlying[u]["delta"] += hedge.shares

    # Aggregate
    total = {"delta": 0, "gamma": 0, "vega": 0, "theta": 0}

    for u, r in risk_by_underlying.items():
        for k in total:
            total[k] += r[k]

    # Limits
    breaches = []

    if abs(total["delta"]) > RISK_LIMITS.max_delta:
        breaches.append("DELTA LIMIT BREACH")

    if abs(total["gamma"]) > RISK_LIMITS.max_gamma:
        breaches.append("GAMMA LIMIT BREACH")

    if abs(total["vega"]) > RISK_LIMITS.max_vega:
        breaches.append("VEGA LIMIT BREACH")

    return {
        "by_underlying": dict(risk_by_underlying),
        "total": total,
        "breaches": breaches
    }
