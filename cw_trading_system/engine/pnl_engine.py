# engine/pnl_engine.py

from config.settings import RISK_FREE_RATE
from models.black_scholes import call_price


def calculate_pnl(portfolio, market_data):

    cw_pnl = 0.0
    hedge_pnl = 0.0
    cw_price = None

    # =========================
    # CW P&L (ISSUER SHORT)
    # =========================

    for pos in portfolio.cw_positions:

        S = market_data.get_spot(pos.ticker)
        sigma = market_data.get_vol(pos.ticker, pos.strike, T)
        T = pos.time_to_expiry()

        bs_price = call_price(S, pos.strike, T, RISK_FREE_RATE, sigma)

        # convert to CW price
        cw_price = bs_price / pos.conversion_ratio

        # issuer sold at issue_price → loses if price increases
        pnl = (pos.issue_price - cw_price) * pos.cw_qty

        cw_pnl += pnl

    # =========================
    # HEDGE P&L (LONG STOCK)
    # =========================

    for hedge in portfolio.hedge_positions:

        ticker = hedge.underlying + ".VN"
        S = market_data.get_spot(ticker)

        pnl = (S - hedge.avg_price) * hedge.shares

        hedge_pnl += pnl

    # =========================
    # TOTAL
    # =========================

    total_pnl = cw_pnl + hedge_pnl

    return {
        "cw_pnl": cw_pnl,
        "hedge_pnl": hedge_pnl,
        "total_pnl": total_pnl,
        "cw_price": cw_price
    }
