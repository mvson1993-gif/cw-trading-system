# engine/monte_carlo_engine.py

import numpy as np
from datetime import date
from scipy.stats import norm


# =========================
# BLACK-SCHOLES DELTA
# =========================

def bs_delta(S, K, T, r, sigma):

    if T <= 0:
        return 1.0 if S > K else 0.0

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

    return norm.cdf(d1)


# =========================
# SIMULATE PRICE PATH (GBM)
# =========================

def simulate_gbm(S0, mu, sigma, T, steps):

    dt = T / steps

    prices = [S0]

    for _ in range(steps):
        z = np.random.normal()
        S = prices[-1] * np.exp(
            (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
        )
        prices.append(S)

    return prices


# =========================
# SINGLE PATH HEDGING PNL
# =========================

def simulate_path_pnl(md, ticker, strike, expiry, issue_price, steps):

    S0 = md.get_spot(ticker)

    T_total = max((date.fromisoformat(expiry) - date.today()).days / 365, 0.0001)
    sigma = md.get_vol(ticker, strike, T_total)

    mu = 0.0  # risk-neutral assumption

    prices = simulate_gbm(S0, mu, sigma, T_total, steps)

    hedge = 0
    cash = issue_price

    for i in range(steps):

        S = prices[i]

        T = max(T_total * (1 - i / steps), 0.0001)

        delta = bs_delta(S, strike, T, 0.03, sigma)

        target = delta
        trade = target - hedge

        cash -= trade * S
        hedge = target

    # final
    S_final = prices[-1]
    payoff = max(S_final - strike, 0)

    cash += hedge * S_final
    cash -= payoff

    return cash


# =========================
# MONTE CARLO SIMULATION
# =========================

def run_monte_carlo(md, ticker, strike, expiry, issue_price, n_sims=1000, steps=30):

    pnls = []

    for _ in range(n_sims):

        pnl = simulate_path_pnl(
            md, ticker, strike, expiry, issue_price, steps
        )

        pnls.append(pnl)

    pnls = np.array(pnls)

    return {
        "mean": float(np.mean(pnls)),
        "std": float(np.std(pnls)),
        "p5": float(np.percentile(pnls, 5)),
        "p95": float(np.percentile(pnls, 95)),
        "all": pnls
    }
