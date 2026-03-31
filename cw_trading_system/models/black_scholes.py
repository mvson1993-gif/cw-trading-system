# models/black_scholes.py

import math


# =========================
# NORMAL DISTRIBUTION
# =========================

def norm_cdf(x: float) -> float:
    """
    Standard normal cumulative distribution function
    Using Abramowitz-Stegun approximation (stable)
    """
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# =========================
# D1, D2 CALCULATION
# =========================

def compute_d1(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0.0

    return (
        math.log(S / K)
        + (r + 0.5 * sigma ** 2) * T
    ) / (sigma * math.sqrt(T))


def compute_d2(d1, sigma, T):
    return d1 - sigma * math.sqrt(T)


# =========================
# CALL OPTION PRICE
# =========================

def call_price(S, K, T, r, sigma):

    # Edge cases (very important)
    if T <= 0:
        return max(S - K, 0)

    if sigma <= 0:
        return max(S - K * math.exp(-r * T), 0)

    d1 = compute_d1(S, K, T, r, sigma)
    d2 = compute_d2(d1, sigma, T)

    price = (
        S * norm_cdf(d1)
        - K * math.exp(-r * T) * norm_cdf(d2)
    )

    return max(price, 0.0)  # safety floor
