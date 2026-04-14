# engine/stress_engine.py

from ..config.settings import RISK_FREE_RATE
from ..models.black_scholes import call_price


def stress_test_grid(portfolio, market_data, spot_shocks, vol_shocks):

    results = {}

    # =========================
    # BASELINE MARKET
    # =========================

    base_spot = {}
    base_vol = {}

    # collect unique tickers (use underlying shares for CW)
    tickers = set()

    for pos in portfolio.cw_positions:
        tickers.add(pos.underlying)

    for hedge in portfolio.hedge_positions:
        tickers.add(hedge.underlying)

    # store baseline market
    for ticker in tickers:
        try:
            base_spot[ticker] = market_data.get_spot(ticker)
            base_vol[ticker] = market_data.get_vol(ticker)
        except ValueError:
            # if no spot data, use default to avoid crash and continue
            base_spot[ticker] = 0.0
            base_vol[ticker] = 0.0

    # =========================
    # BASELINE VALUATION (IMPORTANT)
    # =========================

    base_cw_value = 0.0
    base_hedge_value = 0.0

    for pos in portfolio.cw_positions:

        ticker = pos.underlying
        S = base_spot.get(ticker, 0.0)
        T = pos.time_to_expiry()
        sigma = market_data.get_vol(ticker, pos.strike, T)

        bs_price = call_price(S, pos.strike, T, RISK_FREE_RATE, sigma)
        cw_price = bs_price / pos.conversion_ratio

        base_cw_value += cw_price * pos.cw_qty

    for hedge in portfolio.hedge_positions:

        ticker = hedge.underlying + ".VN"
        S = base_spot[ticker]

        base_hedge_value += S * hedge.shares

    # =========================
    # GRID COMPUTATION
    # =========================

    for s_shock in spot_shocks:
        for v_shock in vol_shocks:

            cw_value = 0.0
            hedge_value = 0.0

            # -------------------------
            # CW REVALUATION
            # -------------------------

            for pos in portfolio.cw_positions:

                ticker = pos.underlying
                S0 = base_spot.get(ticker, 0.0)
                vol0 = base_vol.get(ticker, 0.0)

                shocked_S = S0 * (1 + s_shock)
                shocked_vol = max(vol0 * (1 + v_shock), 0.0001)

                T = pos.time_to_expiry()

                bs_price = call_price(
                    shocked_S,
                    pos.strike,
                    T,
                    RISK_FREE_RATE,
                    shocked_vol
                )

                cw_price = bs_price / pos.conversion_ratio

                cw_value += cw_price * pos.cw_qty

            # -------------------------
            # HEDGE REVALUATION
            # -------------------------

            for hedge in portfolio.hedge_positions:

                ticker = hedge.underlying + ".VN"
                S0 = base_spot[ticker]

                shocked_S = S0 * (1 + s_shock)

                hedge_value += shocked_S * hedge.shares

            # -------------------------
            # ISSUER P&L CALCULATION
            # -------------------------

            # issuer is SHORT CW → liability increases = loss
            cw_pnl = base_cw_value - cw_value

            # hedge is LONG stock
            hedge_pnl = hedge_value - base_hedge_value

            total_pnl = cw_pnl + hedge_pnl

            results[(s_shock, v_shock)] = {
                "cw_pnl": cw_pnl,
                "hedge_pnl": hedge_pnl,
                "total_pnl": total_pnl
            }

    return results
