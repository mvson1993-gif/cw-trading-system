# engine/pricing_engine.py

import math
from datetime import date
from scipy.stats import norm


# =========================
# BLACK-SCHOLES CALL PRICE
# =========================

def bs_call_price(S, K, T, r, sigma):

    if T <= 0:
        return max(S - K, 0)

    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)

    return price


# =========================
# TIME TO MATURITY
# =========================

def compute_T(expiry):
    return max((date.fromisoformat(expiry) - date.today()).days / 365, 0.0001)


# =========================
# FAIR VALUE
# =========================

def compute_fair_value(md, ticker, strike, expiry, r=0.03):

    S = md.get_spot(ticker)
    T = compute_T(expiry)
    sigma = md.get_vol(ticker, strike, T)

    price = bs_call_price(S, strike, T, r, sigma)

    return {
        "spot": S,
        "T": T,
        "sigma": sigma,
        "fair_value": price
    }


# =========================
# ISSUANCE PRICE
# =========================

def compute_issuance_price(fair_value, markup=0.10):

    return fair_value * (1 + markup)


# =========================
# FULL PRICING PACKAGE
# =========================

def price_cw(md, ticker, strike, expiry, markup=0.10):

    fv = compute_fair_value(md, ticker, strike, expiry)

    issuance_price = compute_issuance_price(fv["fair_value"], markup)

    edge = issuance_price - fv["fair_value"]

    return {
        "spot": round(fv["spot"], 2),
        "T": round(fv["T"], 3),
        "sigma": round(fv["sigma"], 4),
        "fair_value": round(fv["fair_value"], 4),
        "issuance_price": round(issuance_price, 4),
        "edge": round(edge, 4)
    }
