# engine/hedging_simulation.py

import math
from datetime import date, timedelta
from scipy.stats import norm


# =========================
# BLACK-SCHOLES DELTA
# =========================

def bs_delta(S, K, T, r, sigma):

    if T <= 0:
        return 1.0 if S > K else 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))

    return norm.cdf(d1)


# =========================
# TIME GRID
# =========================

def generate_time_grid(expiry, steps=30):

    today = date.today()
    expiry_date = date.fromisoformat(expiry)

    total_days = (expiry_date - today).days

    dt = max(total_days // steps, 1)

    dates = [today + timedelta(days=i * dt) for i in range(steps)]

    return dates


# =========================
# PRICE PATH (deterministic)
# =========================

def generate_price_path(S0, shock_pct, steps):

    S1 = S0 * (1 + shock_pct)

    path = []

    for i in range(steps):
        w = i / (steps - 1)
        price = S0 * (1 - w) + S1 * w
        path.append(price)

    return path


# =========================
# MAIN HEDGING SIMULATION
# =========================

def simulate_delta_hedge(md, ticker, strike, expiry, issue_price, shock_pct):

    S0 = md.get_spot(ticker)

    steps = 30

    prices = generate_price_path(S0, shock_pct, steps)
    dates = generate_time_grid(expiry, steps)

    hedge_position = 0
    cash = issue_price  # premium received

    history = []

    for i in range(steps - 1):

        S = prices[i]

        T = max((date.fromisoformat(expiry) - dates[i]).days / 365, 0.0001)
        sigma = md.get_vol(ticker, strike, T)

        delta = bs_delta(S, strike, T, 0.03, sigma)

        # issuer is SHORT option → hedge = +delta shares
        target_hedge = delta

        trade = target_hedge - hedge_position

        # execute hedge
        cash -= trade * S
        hedge_position = target_hedge

        history.append({
            "step": i,
            "spot": round(S, 2),
            "delta": round(delta, 4),
            "hedge": round(hedge_position, 4),
            "cash": round(cash, 2)
        })

    # final settlement
    S_final = prices[-1]
    payoff = max(S_final - strike, 0)

    # close hedge
    cash += hedge_position * S_final

    # subtract payoff (issuer pays)
    cash -= payoff

    return {
        "final_spot": round(S_final, 2),
        "payoff": round(payoff, 4),
        "final_pnl": round(cash, 2),
        "history": history
    }
