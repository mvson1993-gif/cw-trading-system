# engine/simulation_engine.py

from datetime import date
from .pricing_engine import bs_call_price


# =========================
# TIME TO MATURITY
# =========================

def compute_T(expiry):
    return max((date.fromisoformat(expiry) - date.today()).days / 365, 0.0001)


# =========================
# SIMULATE SINGLE SCENARIO
# =========================

def simulate_cw_pnl(md, ticker, strike, expiry, issue_price, shock_pct):

    S0 = md.get_spot(ticker)
    S1 = S0 * (1 + shock_pct)

    T = compute_T(expiry)
    sigma = md.get_vol(ticker, strike, T)

    # price today vs shocked
    price_0 = bs_call_price(S0, strike, T, 0.03, sigma)
    price_1 = bs_call_price(S1, strike, T, 0.03, sigma)

    # issuer is SHORT
    pnl = issue_price - price_1

    return {
        "spot_start": round(S0, 2),
        "spot_end": round(S1, 2),
        "price_start": round(price_0, 4),
        "price_end": round(price_1, 4),
        "pnl": round(pnl, 4)
    }


# =========================
# MULTI-SCENARIO GRID
# =========================

def simulate_grid(md, ticker, strike, expiry, issue_price, shocks):

    results = []

    for s in shocks:

        res = simulate_cw_pnl(
            md, ticker, strike, expiry, issue_price, s
        )

        results.append({
            "Shock": f"{int(s*100)}%",
            "Spot End": res["spot_end"],
            "CW Price": res["price_end"],
            "PnL": res["pnl"]
        })

    return results
