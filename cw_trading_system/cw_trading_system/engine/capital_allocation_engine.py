# engine/capital_allocation_engine.py

from datetime import date


# =========================
# TIME
# =========================

def compute_T(expiry):
    return max((date.fromisoformat(expiry) - date.today()).days / 365, 0.0001)


# =========================
# CAPITAL ESTIMATION
# =========================

def estimate_capital(gamma, vol, notional):

    # convexity risk proxy
    return abs(gamma) * (vol ** 2) * notional


# =========================
# EVALUATE ONE CW
# =========================

def evaluate_cw_opportunity(portfolio, md, ticker, strike, expiry, qty, cr):

    from engine.pricing_engine import price_cw
    from models.greeks import compute_greeks

    S = md.get_spot(ticker)
    T = compute_T(expiry)
    sigma = md.get_vol(ticker, strike, T)

    # pricing
    pricing = price_cw(md, ticker, strike, expiry)

    edge = pricing["edge"]
    issuance_price = pricing["issuance_price"]

    # gamma
    g = compute_greeks(S, strike, T, 0.03, sigma)
    gamma = g["gamma"] * qty * cr

    notional = S * qty * cr

    capital = estimate_capital(gamma, sigma, notional)

    expected_pnl = edge * qty

    roe = expected_pnl / capital if capital > 0 else 0

    return {
        "ticker": ticker,
        "strike": strike,
        "edge": edge,
        "gamma": gamma,
        "capital": capital,
        "expected_pnl": expected_pnl,
        "roe": roe
    }


# =========================
# ALLOCATE CAPITAL
# =========================

def allocate_capital(portfolio, md, candidates, total_capital):

    evaluated = []

    for c in candidates:

        res = evaluate_cw_opportunity(
            portfolio,
            md,
            c["ticker"],
            c["strike"],
            c["expiry"],
            c["qty"],
            c["cr"]
        )

        evaluated.append(res)

    # sort by ROE
    evaluated.sort(key=lambda x: x["roe"], reverse=True)

    allocation = []
    used_capital = 0

    for e in evaluated:

        if used_capital + e["capital"] <= total_capital:

            allocation.append(e)
            used_capital += e["capital"]

    return {
        "selected": allocation,
        "used_capital": used_capital,
        "total_capital": total_capital
    }
