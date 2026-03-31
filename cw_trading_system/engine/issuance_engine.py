# engine/issuance_engine.py

from datetime import date


# =========================
# CORE METRICS
# =========================

def compute_moneyness(spot, strike):
    return strike / spot


def compute_time_to_maturity(expiry):
    return max((date.fromisoformat(expiry) - date.today()).days / 365, 0.0001)


# =========================
# RISK SCORING
# =========================

def assess_risk(moneyness, T):

    # far OTM = convex risk
    if moneyness > 1.15:
        risk = "HIGH"
    elif moneyness > 1.05:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    # long maturity increases uncertainty
    if T > 0.5 and risk != "HIGH":
        risk = "MEDIUM"

    return risk


# =========================
# VOL MARKUP STRATEGY
# =========================

def suggested_vol(base_vol, moneyness):

    # issuer skew logic
    if moneyness > 1.2:
        return base_vol + 0.05   # strong markup
    elif moneyness > 1.1:
        return base_vol + 0.03
    elif moneyness > 1.0:
        return base_vol + 0.01
    else:
        return base_vol          # ATM competitive


# =========================
# EXPECTED EDGE
# =========================

def expected_edge(implied_vol, assumed_realized_vol=0.25):
    return implied_vol - assumed_realized_vol


# =========================
# MAIN EVALUATION
# =========================

def evaluate_issuance(md, ticker, strike, expiry):

    spot = md.get_spot(ticker)
    T = compute_time_to_maturity(expiry)

    base_vol = md.get_vol(ticker, strike, T)

    moneyness = compute_moneyness(spot, strike)

    # issuer-adjusted vol
    implied_vol = suggested_vol(base_vol, moneyness)

    # risk classification
    risk = assess_risk(moneyness, T)

    # expected edge
    edge = expected_edge(implied_vol)

    return {
        "ticker": ticker,
        "spot": round(spot, 2),
        "strike": strike,
        "moneyness": round(moneyness, 3),
        "T": round(T, 3),
        "base_vol": round(base_vol, 4),
        "implied_vol": round(implied_vol, 4),
        "edge": round(edge, 4),
        "risk": risk
    }


# =========================
# STRIKE SCANNER
# =========================

def scan_strikes(md, ticker, expiry, strike_list):

    results = []

    for K in strike_list:
        res = evaluate_issuance(md, ticker, K, expiry)
        results.append(res)

    return results
