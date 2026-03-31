# engine/portfolio_monte_carlo.py

import numpy as np
from datetime import date
from scipy.stats import norm


# =========================
# DELTA
# =========================

def bs_delta(S, K, T, r, sigma):

    if T <= 0:
        return 1.0 if S > K else 0.0

    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    return norm.cdf(d1)


# =========================
# SIMULATE PATH
# =========================

def simulate_path(portfolio, md, steps=30):

    # group by underlying
    underlyings = {}

    for p in portfolio.cw_positions:
        u = p.underlying
        if u not in underlyings:
            underlyings[u] = md.get_spot(p.ticker)

    paths = {}

    for u, S0 in underlyings.items():

        sigma = 0.3
        dt = 1/252

        prices = [S0]

        for _ in range(steps):
            z = np.random.normal()
            S = prices[-1] * np.exp(-0.5*sigma**2*dt + sigma*np.sqrt(dt)*z)
            prices.append(S)

        paths[u] = prices

    return paths


# =========================
# PORTFOLIO PNL
# =========================

def simulate_portfolio_pnl(portfolio, md, steps=30):

    paths = simulate_path(portfolio, md, steps)

    cash = 0
    hedge_positions = {u: 0 for u in paths}

    # initial premium
    for p in portfolio.cw_positions:
        cash += p.issue_price * p.cw_qty

    for i in range(steps):

        for p in portfolio.cw_positions:

            u = p.underlying
            S = paths[u][i]

            T = max((date.fromisoformat(p.expiry) - date.today()).days/365, 0.0001)
            sigma = md.get_vol(p.ticker, p.strike, T)

            delta = bs_delta(S, p.strike, T, 0.03, sigma)
            target = delta * p.cw_qty * p.conversion_ratio

            trade = target - hedge_positions[u]

            cash -= trade * S
            hedge_positions[u] = target

    # final settlement
    for p in portfolio.cw_positions:

        u = p.underlying
        S = paths[u][-1]

        payoff = max(S - p.strike, 0) * p.cw_qty * p.conversion_ratio
        cash -= payoff

    return cash


# =========================
# RUN MC
# =========================

def run_portfolio_mc(portfolio, md, n_sims=500):

    pnls = []

    for _ in range(n_sims):
        pnl = simulate_portfolio_pnl(portfolio, md)
        pnls.append(pnl)

    pnls = np.array(pnls)

    return {
        "mean": float(np.mean(pnls)),
        "std": float(np.std(pnls)),
        "p5": float(np.percentile(pnls, 5)),
        "p95": float(np.percentile(pnls, 95)),
        "all": pnls
    }
