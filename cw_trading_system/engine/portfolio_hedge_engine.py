# engine/portfolio_hedge_engine.py

from datetime import date


# =========================
# AGGREGATE PORTFOLIO GREEKS
# =========================

def aggregate_greeks(portfolio, md):

    total_delta = 0
    total_gamma = 0

    for p in portfolio.cw_positions:

        S = md.get_spot(p.ticker)
        T = max((date.fromisoformat(p.expiry) - date.today()).days / 365, 0.0001)
        sigma = md.get_vol(p.ticker, p.strike, T)

        from models.greeks import compute_greeks
        greeks = compute_greeks(S, p.strike, T, 0.03, sigma)

        scale = p.cw_qty * p.conversion_ratio

        total_delta += greeks["delta"] * scale
        total_gamma += greeks["gamma"] * scale

    # subtract hedge positions
    for ticker, h in portfolio.hedge_positions.items():
        total_delta -= h.shares

    return {
        "delta": total_delta,
        "gamma": total_gamma
    }


# =========================
# HEDGE DECISION WITH BAND
# =========================

def hedge_with_band(delta, lower=-50000, upper=50000):

    if lower <= delta <= upper:
        return {
            "action": "NO TRADE",
            "size": 0
        }

    hedge_size = -delta

    return {
        "action": "HEDGE",
        "size": round(hedge_size, 0)
    }


# =========================
# MULTI-UNDERLYING HEDGE
# =========================

def hedge_by_underlying(portfolio, md, band=50000):

    results = {}

    for p in portfolio.cw_positions:

        u = p.underlying

        if u not in results:
            results[u] = {
                "delta": 0
            }

        S = md.get_spot(p.ticker)
        T = max((date.fromisoformat(p.expiry) - date.today()).days / 365, 0.0001)
        sigma = md.get_vol(p.ticker, p.strike, T)

        from models.greeks import compute_greeks
        greeks = compute_greeks(S, p.strike, T, 0.03, sigma)

        scale = p.cw_qty * p.conversion_ratio

        results[u]["delta"] += greeks["delta"] * scale

    # subtract hedge
    for u, h in portfolio.hedge_positions.items():
        results.setdefault(u, {"delta": 0})
        results[u]["delta"] -= h.shares

    # apply hedge band
    for u in results:
        d = results[u]["delta"]

        if abs(d) < band:
            results[u]["action"] = "HOLD"
            results[u]["hedge"] = 0
        else:
            results[u]["action"] = "TRADE"
            results[u]["hedge"] = round(-d, 0)

    return results
