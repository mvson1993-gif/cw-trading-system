# engine/strike_optimizer.py

from datetime import date


# =========================
# TIME
# =========================

def compute_T(expiry):
    return max((date.fromisoformat(expiry) - date.today()).days / 365, 0.0001)


# =========================
# GENERATE STRIKES
# =========================

def generate_strikes(spot):

    multipliers = [0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2]

    return [round(spot * m, 1) for m in multipliers]


# =========================
# EVALUATE ONE STRIKE
# =========================

def evaluate_strike(portfolio, md, ticker, strike, expiry, qty, cr, gamma_limit):

    from engine.pricing_engine import price_cw
    from engine.issuance_risk_engine import compute_portfolio_gamma
    from models.greeks import compute_greeks

    S = md.get_spot(ticker)
    T = compute_T(expiry)
    sigma = md.get_vol(ticker, strike, T)

    # pricing
    pricing = price_cw(md, ticker, strike, expiry)
    edge = pricing["edge"]

    # gamma
    g = compute_greeks(S, strike, T, 0.03, sigma)
    candidate_gamma = g["gamma"] * qty * cr

    current_gamma = compute_portfolio_gamma(portfolio, md)
    new_gamma = current_gamma + candidate_gamma

    # feasibility
    feasible = abs(new_gamma) <= gamma_limit

    return {
        "strike": strike,
        "edge": edge,
        "gamma": candidate_gamma,
        "new_gamma": new_gamma,
        "feasible": feasible
    }


# =========================
# OPTIMIZER
# =========================

def optimize_strikes(portfolio, md, ticker, expiry, qty, cr, gamma_limit, lambda_risk=0.0001):

    spot = md.get_spot(ticker)

    strikes = generate_strikes(spot)

    results = []

    for K in strikes:

        res = evaluate_strike(
            portfolio, md, ticker, K, expiry, qty, cr, gamma_limit
        )

        if res["feasible"]:

            score = res["edge"] - lambda_risk * abs(res["gamma"])

            res["score"] = score
            results.append(res)

    # sort best first
    results.sort(key=lambda x: x["score"], reverse=True)

    return results
