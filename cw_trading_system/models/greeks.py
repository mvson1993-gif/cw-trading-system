# models/greeks.py

import math
from .black_scholes import compute_d1, compute_d2, norm_cdf


# =========================
# NORMAL PDF
# =========================

def norm_pdf(x: float) -> float:
    return (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x)


# =========================
# GREEKS CALCULATION
# =========================

def compute_greeks(S, K, T, r, sigma):

    # ---- Edge handling (critical) ----
    if T <= 0 or sigma <= 0:
        return {
            "delta": 1.0 if S > K else 0.0,
            "gamma": 0.0,
            "vega": 0.0,
            "theta": 0.0
        }

    d1 = compute_d1(S, K, T, r, sigma)
    d2 = compute_d2(d1, sigma, T)

    pdf_d1 = norm_pdf(d1)

    # ---- Greeks ----
    delta = norm_cdf(d1)

    gamma = pdf_d1 / (S * sigma * math.sqrt(T))

    vega = S * pdf_d1 * math.sqrt(T)

    theta = (
        - (S * pdf_d1 * sigma) / (2 * math.sqrt(T))
        - r * K * math.exp(-r * T) * norm_cdf(d2)
    )

    return {
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta
    }
