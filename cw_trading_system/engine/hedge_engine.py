# engine/hedge_engine.py

from config.settings import HEDGE_POLICY


def generate_hedge_actions(risk_output):

    actions = []

    band = HEDGE_POLICY.delta_band
    hedge_ratio = HEDGE_POLICY.hedge_ratio
    min_size = HEDGE_POLICY.min_trade_size

    by_underlying = risk_output["by_underlying"]

    for underlying, r in by_underlying.items():

        delta = r["delta"]

        # -------------------------
        # WITHIN BAND → NO ACTION
        # -------------------------
        if abs(delta) <= band:
            actions.append({
                "underlying": underlying,
                "action": "HOLD",
                "size": 0,
                "reason": "Within delta band"
            })
            continue

        # -------------------------
        # OUTSIDE BAND → HEDGE
        # -------------------------
        target_hedge = -delta * hedge_ratio

        trade_size = int(target_hedge)

        # enforce minimum trade size
        if abs(trade_size) < min_size:
            actions.append({
                "underlying": underlying,
                "action": "HOLD",
                "size": 0,
                "reason": "Below minimum trade size"
            })
            continue

        # determine direction
        if trade_size > 0:
            action = "BUY"
        else:
            action = "SELL"

        actions.append({
            "underlying": underlying,
            "action": action,
            "size": abs(trade_size),
            "reason": "Delta hedge"
        })

    return actions
