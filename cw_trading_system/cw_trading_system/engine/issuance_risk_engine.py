# engine/issuance_risk_engine.py

from datetime import date


# =========================
# TIME TO MATURITY
# =========================

def compute_T(expiry):
    return max((date.fromisoformat(expiry) - date.today()).days / 365, 0.0001)


# =========================
# CURRENT PORTFOLIO GAMMA
# =========================

def compute_portfolio_gamma(portfolio, md):

    total_gamma = 0

    for p in portfolio.cw_positions:

        S = md.get_spot(p.ticker)
        T = compute_T(p.expiry)
        sigma = md.get_vol(p.ticker, p.strike, T)

        from models.greeks import compute_greeks
        g = compute_greeks(S, p.strike, T, 0.03, sigma)

        scale = p.cw_qty * p.conversion_ratio
        total_gamma += g["gamma"] * scale

    return total_gamma


# =========================
# CANDIDATE CW GAMMA
# =========================

def compute_candidate_gamma(md, ticker, strike, expiry, qty, cr):

    S = md.get_spot(ticker)
    T = compute_T(expiry)
    sigma = md.get_vol(ticker, strike, T)

    from models.greeks import compute_greeks
    g = compute_greeks(S, strike, T, 0.03, sigma)

    return g["gamma"] * qty * cr


# =========================
# DECISION ENGINE
# =========================

def evaluate_issuance_risk(portfolio, md, ticker, strike, expiry, qty, cr, gamma_limit):

    current_gamma = compute_portfolio_gamma(portfolio, md)

    candidate_gamma = compute_candidate_gamma(
        md, ticker, strike, expiry, qty, cr
    )

    new_gamma = current_gamma + candidate_gamma

    decision = "APPROVE"
    reason = "Within gamma limit"

    if abs(new_gamma) > gamma_limit:
        decision = "REJECT"
        reason = "Gamma limit breached"

    return {
        "current_gamma": round(current_gamma, 2),
        "candidate_gamma": round(candidate_gamma, 2),
        "new_gamma": round(new_gamma, 2),
        "limit": gamma_limit,
        "decision": decision,
        "reason": reason
    }
